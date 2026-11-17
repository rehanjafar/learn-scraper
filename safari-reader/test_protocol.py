"""Synthetic MCP-to-browser roundtrip; never reads real pairing keys or accounts."""
import asyncio,json,sys,threading,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fastmcp import Client
from safari_reader import request_signature
import secrets,time
with patch('safari_reader.load_key',return_value='T'*43):
 import safari_server

def simulate_browser(stop):
 while not stop.wait(.02):
  try:
   origin='safari-web-extension://TEST-UUID'
   def headers(path,body):
    timestamp=str(int(time.time()));nonce=secrets.token_hex(16)
    return {'Origin':origin,'Content-Type':'application/json','X-Waterloo-Time':timestamp,'X-Waterloo-Nonce':nonce,'X-Waterloo-Signature':request_signature('T'*43,origin,path,timestamp,nonce,body)}
   req=urllib.request.Request('http://127.0.0.1:18766/next',data=b'{}',headers=headers('/next',b'{}'))
   with urllib.request.urlopen(req,timeout=1) as r:job=json.load(r)
   if not job:continue
   assert job['path']=='/d2l/api/lp/1.43/enrollments/myenrollments/?orgUnitTypeId=3'
   body={'id':job['id'],'data':{'Items':[{'OrgUnit':{'Id':123,'Name':'Test Course','Code':'TEST101'},'Access':{'IsActive':True,'CanAccess':True,'StartDate':None,'EndDate':None}}]}}
   req=urllib.request.Request('http://127.0.0.1:18766/result',data=json.dumps(body).encode(),headers=headers('/result',json.dumps(body).encode()))
   with urllib.request.urlopen(req,timeout=1) as r:assert r.status==200
  except (urllib.error.URLError,OSError):pass
async def main():
 stop=threading.Event();thread=threading.Thread(target=simulate_browser,args=(stop,),daemon=True)
 # The in-process FastMCP client owns the bridge lifespan.
 thread.start()
 try:
  async with Client(safari_server.mcp) as client:
   tools=await client.list_tools();assert len(tools)==15
   assert all(t.annotations.read_only_hint for t in tools if t.name!='planner_state_record')
   assert not next(t for t in tools if t.name=='planner_state_record').annotations.read_only_hint
   result=await client.call_tool('learn_courses',{})
   assert not result.is_error and 'TEST101' in str(result)
   invalid=await client.call_tool('learn_grades',{'course':-1},raise_on_error=False)
   assert invalid.is_error
   print('SYNTHETIC_MCP_ROUNDTRIP_PASSED; 14_READ_ONLY_AND_1_LOCAL_TRACKER_TOOL')
 finally:stop.set();thread.join(2)
asyncio.run(main())
