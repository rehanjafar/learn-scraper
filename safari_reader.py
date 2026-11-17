"""Memory-only, authenticated loopback bridge. No cookie access or arbitrary HTTP proxy."""
import hashlib
import os
import stat
import hmac
import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from fastmcp.exceptions import ToolError

ROOT = Path(__file__).resolve().parent
PORT = 18766
PREFIX = f'127.0.0.1:{PORT}'
ORIGIN = re.compile(r'(?:safari-web-extension://[A-Za-z0-9-]+|chrome-extension://[a-p]{32})\Z')
ROUTES = [
 r'/cs135/page/(?:index\.html|calendar/index\.html|slides/index\.html|assess/index\.html|assign/index\.html)',
 r'/cs135/file/[A-Za-z0-9][A-Za-z0-9_./-]{0,180}\.pdf',
 r'/d2l/api/le/1\.57/[1-9]\d*/content/topics/[1-9]\d*/file',
 r'/d2l/api/lp/1\.43/users/whoami',
 r'/d2l/api/lp/1\.43/enrollments/myenrollments/\?orgUnitTypeId=3',
 r'/d2l/api/le/1\.57/[1-9]\d*/grades/values/myGradeValues/',
 r'/d2l/api/le/1\.57/[1-9]\d*/dropbox/folders/',
 r'/d2l/api/le/1\.57/[1-9]\d*/dropbox/folders/[1-9]\d*',
 r'/d2l/api/le/1\.57/[1-9]\d*/dropbox/folders/[1-9]\d*/submissions/',
 r'/d2l/api/le/1\.57/[1-9]\d*/calendar/events/myEvents/\?startDateTime=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.000Z&endDateTime=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.000Z',
 r'/d2l/api/le/1\.57/[1-9]\d*/news/',
 r'/d2l/api/le/1\.57/[1-9]\d*/content/toc',
 r'/d2l/api/le/1\.57/[1-9]\d*/content/topics/[1-9]\d*',
]
def allowed(path):
    return isinstance(path, str) and not any(p in ('.','..') for p in path.split('/')) and len(path)<=300 and any(re.fullmatch(p,path) for p in ROUTES)

def digest(body):
    return hashlib.sha256(body).hexdigest()

def request_signature(key, origin, path, timestamp, nonce, body):
    message='\n'.join(('v1','POST',path,PREFIX,origin,timestamp,nonce,digest(body)))
    return hmac.new(key.encode(),message.encode(),hashlib.sha256).hexdigest()

def response_signature(key, nonce, status, body):
    message='\n'.join(('v1','response',nonce,str(status),digest(body)))
    return hmac.new(key.encode(),message.encode(),hashlib.sha256).hexdigest()

def load_key():
    path=ROOT/'safari-reader/token'
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
            raise RuntimeError('Local pairing key must be a private, user-owned regular file.')
        with os.fdopen(fd,'r',closefd=False) as handle:key=handle.read(128).strip()
    finally:os.close(fd)
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',key):raise RuntimeError('Invalid local pairing key; run setup_local.py.')
    return key

class BoundedServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,*args):
        self.slots=threading.BoundedSemaphore(8)
        super().__init__(*args)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request);return
        try:super().process_request(request,address)
        except BaseException:
            self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()
    def handle_error(self,request,address):
        pass  # Never log request bodies, keys, or private course data.

class Broker:
    def __init__(self):
        self.token=load_key()
        self.lock=threading.Lock()
        self.jobs={}
        self.nonces={}
        self.last_seen=0
        self.http=None
    def request(self,path,timeout=70):
        if not allowed(path):raise ToolError('This operation is outside the Safari reader allowlist.')
        job={'id':secrets.token_hex(16),'path':path,'claimed':False,'event':threading.Event(),'result':None}
        with self.lock:
            if len(self.jobs)>=32:raise ToolError('Too many pending Safari requests.')
            self.jobs[job['id']]=job
        try:
            if not job['event'].wait(timeout):
                raise ToolError('Open a signed-in LEARN home tab in Safari and enable Waterloo Safari Reader. No session is copied.')
            result=job['result']
            if 'error' in result:raise ToolError(result['error'])
            return result['data']
        finally:
            with self.lock:self.jobs.pop(job['id'],None)
    def start(self):
        broker=self
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.0'
            server_version='LocalReader'
            sys_version=''
            authenticated_nonce=None
            def log_message(self,*args):pass
            def setup(self):
                super().setup();self.connection.settimeout(3)
            def reply(self,status,data=None):
                body=json.dumps(data if data is not None else {},allow_nan=False,separators=(',',':')).encode()
                self.send_response(status)
                origin=self.headers.get('Origin','')
                if ORIGIN.fullmatch(origin):
                    self.send_header('Access-Control-Allow-Origin',origin)
                    self.send_header('Vary','Origin')
                    self.send_header('Access-Control-Expose-Headers','X-Waterloo-Signature')
                if self.authenticated_nonce:
                    self.send_header('X-Waterloo-Signature',response_signature(broker.token,self.authenticated_nonce,status,body))
                self.send_header('Content-Type','application/json')
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers();self.wfile.write(body)
            def boundary(self):
                return (len(self.headers.get_all('Host',[]))==1 and self.headers.get('Host')==PREFIX
                        and len(self.headers.get_all('Origin',[]))==1
                        and ORIGIN.fullmatch(self.headers.get('Origin','')) is not None)
            def do_OPTIONS(self):
                if not self.boundary():self.reply(403);return
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
                self.send_header('Access-Control-Allow-Methods','POST')
                self.send_header('Access-Control-Allow-Headers','Content-Type, X-Waterloo-Time, X-Waterloo-Nonce, X-Waterloo-Signature')
                self.send_header('Access-Control-Max-Age','600');self.end_headers()
            def do_POST(self):
                if not self.boundary():self.reply(403);return
                if self.path not in ('/next','/result'):self.reply(404);return
                timestamp=self.headers.get('X-Waterloo-Time','')
                nonce=self.headers.get('X-Waterloo-Nonce','')
                signature=self.headers.get('X-Waterloo-Signature','')
                if (not re.fullmatch(r'\d{10}',timestamp) or abs(time.time()-int(timestamp))>30
                    or not re.fullmatch(r'[0-9a-f]{32}',nonce) or not re.fullmatch(r'[0-9a-f]{64}',signature)):
                    self.reply(403);return
                try:
                    if (self.headers.get_content_type()!='application/json' or self.headers.get('Transfer-Encoding')
                        or len(self.headers.get_all('Content-Length',[]))!=1):
                        self.reply(400);return
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=6000000:self.reply(413);return
                    body=self.rfile.read(size)
                    if len(body)!=size:self.reply(400);return
                except (ValueError,TimeoutError,OSError):self.reply(400);return
                expected=request_signature(broker.token,self.headers['Origin'],self.path,timestamp,nonce,body)
                if not hmac.compare_digest(signature,expected):self.reply(403);return
                with broker.lock:
                    now=time.time()
                    broker.nonces={k:t for k,t in broker.nonces.items() if now-t<60}
                    if nonce in broker.nonces:self.reply(409);return
                    if len(broker.nonces)>=1024:self.reply(429);return
                    broker.nonces[nonce]=now
                self.authenticated_nonce=nonce
                try:
                    data=json.loads(body,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                    if not isinstance(data,dict):raise ValueError()
                except (ValueError,RecursionError):self.reply(400);return
                if self.path=='/next':
                    if data:self.reply(400);return
                    with broker.lock:
                        broker.last_seen=time.monotonic()
                        job=next((j for j in broker.jobs.values() if not j['claimed']),None)
                        if job:job['claimed']=True;reply={'id':job['id'],'path':job['path']}
                        else:reply={}
                    self.reply(200,reply)
                else:
                    with broker.lock:
                        job=broker.jobs.get(data.get('id','')) if isinstance(data.get('id'),str) else None
                        if not job or not job['claimed'] or job['event'].is_set():status=409
                        elif set(data) not in ({'id','data'},{'id','error'}):status=400
                        elif 'data' in data and not isinstance(data['data'],(dict,list)):status=400
                        else:
                            job['result']={'error':'LEARN request unavailable. Check your Safari sign-in or course access.'} if 'error' in data else {'data':data['data']}
                            job['event'].set();status=200
                    self.reply(status)
        self.http=BoundedServer(('127.0.0.1',PORT),Handler)
        threading.Thread(target=self.http.serve_forever,daemon=True).start()
    def stop(self):
        if self.http:self.http.shutdown();self.http.server_close()
        with self.lock:
            for job in self.jobs.values():
                job['result']={'error':'Safari reader disconnected.'};job['event'].set()
            self.nonces.clear()

class SafariLearn:
    """Reuse LEARN formatters, replacing all HTTP with the bounded Safari bridge."""
    def __init__(self,broker):self.broker=broker
    def _api(self,path):return self.broker.request(path)
    def _done(self,course,entity):
        kind,eid=(entity or {}).get('AssociatedEntityType',''),(entity or {}).get('AssociatedEntityId')
        if kind.endswith('Dropbox') and isinstance(eid,int) and eid>0:
            subs=self._api(f'/d2l/api/le/1.57/{course}/dropbox/folders/{eid}/submissions/')
            return any(s.get('Submissions') for s in subs)
        return None  # Quiz completion would require HTML; deliberately unsupported.

from safari_learn import Learn
for _name in ('whoami','courses','grades','assignments','assignment','due','announcements','content','topic'):
    setattr(SafariLearn,_name,getattr(Learn,_name))
