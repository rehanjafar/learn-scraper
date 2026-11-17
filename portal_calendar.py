"""Read the privately configured Waterloo Portal ICS feed; never exposes its bearer URL."""
import base64,hashlib,json,os,re,stat,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None

def collect():
 path=ROOT/'planner_state/portal.json'
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>4000:raise ValueError('Private Portal configuration required')
  with os.fdopen(fd,'r',closefd=False) as handle:url=json.load(handle)['url']
 finally:os.close(fd)
 u=urlsplit(url)
 if u.scheme!='https' or u.netloc!='portalapi2.uwaterloo.ca' or u.query or u.fragment or not re.fullmatch(r'/v2/calendar/feed/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/portal\.ics',u.path):raise ValueError('Unexpected Portal feed address')
 try:
  with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url,headers={'Accept':'text/calendar'}),timeout=10) as response:
   raw=response.read(1500001)
  if len(raw)>1500000 or not raw.lstrip().startswith(b'BEGIN:VCALENDAR'):raise ValueError()
  from document_reader import read_document
  file={'format':'ics','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
  parsed=read_document(file)
  return {'source':'Portal Calendar (private university subscription)','status':'checked',**parsed}
 except Exception:raise RuntimeError('Portal Calendar could not be refreshed safely; the private feed address was not logged.') from None
if __name__=='__main__':print(json.dumps(collect()))
