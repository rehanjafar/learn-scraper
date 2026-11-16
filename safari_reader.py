"""Memory-only, authenticated loopback bridge. No cookie access or arbitrary HTTP proxy."""
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
ORIGIN = re.compile(r'safari-web-extension://[A-Za-z0-9-]+\Z')
ROUTES = [
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
    return isinstance(path, str) and len(path)<=300 and any(re.fullmatch(p,path) for p in ROUTES)

class Broker:
    def __init__(self):
        self.token=(ROOT/'safari-reader/token').read_text().strip()
        self.lock=threading.Lock()
        self.jobs={}
        self.last_seen=0
        self.http=None
    def request(self,path,timeout=18):
        if not allowed(path): raise ToolError('This operation is outside the Safari reader allowlist.')
        job={'id':secrets.token_hex(16),'path':path,'claimed':False,'event':threading.Event(),'result':None}
        with self.lock:
            if len(self.jobs)>=32: raise ToolError('Too many pending Safari requests.')
            self.jobs[job['id']]=job
        try:
            if not job['event'].wait(timeout):
                raise ToolError('Open a signed-in LEARN home tab in Safari and enable Waterloo Safari Reader. No session is copied.')
            result=job['result']
            if 'error' in result: raise ToolError(result['error'])
            return result['data']
        finally:
            with self.lock: self.jobs.pop(job['id'],None)
    def start(self):
        broker=self
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.0'
            def log_message(self,*args): pass
            def setup(self):
                super().setup();self.connection.settimeout(3)
            def reply(self,status,data=None):
                body=json.dumps(data or {},allow_nan=False).encode()
                self.send_response(status)
                origin=self.headers.get('Origin','')
                if ORIGIN.fullmatch(origin):
                    self.send_header('Access-Control-Allow-Origin',origin)
                    self.send_header('Vary','Origin')
                self.send_header('Content-Type','application/json')
                self.send_header('Cache-Control','no-store')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers();self.wfile.write(body)
            def boundary(self):
                origin=self.headers.get('Origin','')
                return self.headers.get('Host')==PREFIX and (not origin or ORIGIN.fullmatch(origin))
            def do_OPTIONS(self):
                if not self.boundary() or not ORIGIN.fullmatch(self.headers.get('Origin','')):
                    self.reply(403);return
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
                self.send_header('Access-Control-Allow-Methods','POST')
                self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type')
                self.send_header('Access-Control-Max-Age','600');self.end_headers()
            def do_POST(self):
                if not self.boundary() or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+broker.token):
                    self.reply(403);return
                if self.path not in ('/next','/result'):
                    self.reply(404);return
                try:
                    if self.headers.get_content_type()!='application/json' or self.headers.get('Transfer-Encoding'):
                        self.reply(400);return
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=2000000: self.reply(413);return
                    data=json.loads(self.rfile.read(size),parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                    if not isinstance(data,dict): raise ValueError()
                except (ValueError,TimeoutError):
                    self.reply(400);return
                with broker.lock:
                    broker.last_seen=time.monotonic()
                    if self.path=='/next':
                        job=next((j for j in broker.jobs.values() if not j['claimed']),None)
                        if job:
                            job['claimed']=True
                            self.reply(200,{'id':job['id'],'path':job['path']})
                        else:self.reply(200)
                    else:
                        job=broker.jobs.get(data.get('id','')) if isinstance(data.get('id'),str) else None
                        if not job or not job['claimed'] or job['event'].is_set():
                            self.reply(409);return
                        if set(data) not in ({'id','data'},{'id','error'}):
                            self.reply(400);return
                        job['result']={'error':'LEARN request unavailable. Check your Safari sign-in or course access.'} if 'error' in data else {'data':data['data']}
                        job['event'].set();self.reply(200)
        self.http=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
        threading.Thread(target=self.http.serve_forever,daemon=True).start()
    def stop(self):
        if self.http:self.http.shutdown();self.http.server_close()

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
