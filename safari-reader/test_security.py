import concurrent.futures,json,sys,time,unittest,urllib.request,urllib.error,secrets
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from safari_reader import Broker,allowed,PORT,request_signature,response_signature
class SecurityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with patch('safari_reader.load_key',return_value='S'*43):
   cls.b=Broker()
  cls.b.start()
 @classmethod
 def tearDownClass(cls):cls.b.stop()
 def post(self,path='/next',body={},token=True,origin='safari-web-extension://TEST-UUID',host=None,nonce=None,age=0,sign_body=None):
  headers={'Content-Type':'application/json','Origin':origin}
  nonce=nonce or secrets.token_hex(16);timestamp=str(int(time.time())+age);raw=json.dumps(body).encode()
  if token:headers.update({'X-Waterloo-Time':timestamp,'X-Waterloo-Nonce':nonce,'X-Waterloo-Signature':request_signature('S'*43,origin,path,timestamp,nonce,sign_body if sign_body is not None else raw)})
  if host:headers['Host']=host
  request=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=json.dumps(body).encode(),headers=headers)
  try:
   with urllib.request.urlopen(request,timeout=3) as response:
    raw=response.read()
    self.assertEqual(response.headers.get('X-Waterloo-Signature'),response_signature('S'*43,nonce,response.status,raw))
    return response.status,json.loads(raw)
  except urllib.error.HTTPError as error:return error.code,{}
 def test_no_token(self):self.assertEqual(self.post(token=False)[0],403)
 def test_foreign_website(self):self.assertEqual(self.post(origin='https://evil.example')[0],403)
 def test_learn_page_cannot_access_broker_directly(self):self.assertEqual(self.post(origin='https://learn.uwaterloo.ca')[0],403)
 def test_dns_rebinding(self):self.assertEqual(self.post(host='evil.example:18766')[0],403)
 def test_unknown_endpoint(self):self.assertEqual(self.post('/cookies')[0],404)
 def test_forged_result(self):self.assertEqual(self.post('/result',{'id':'missing','data':{}})[0],409)
 def test_malformed_id(self):self.assertEqual(self.post('/result',{'id':[],'data':{}})[0],409)
 def test_url_allowlist(self):
  self.assertTrue(allowed('/d2l/api/lp/1.43/users/whoami'))
  for path in ['https://evil.example/','//evil.example/','/d2l/home','/d2l/api/lp/1.43/users/whoami?token=secret','/d2l/api/le/1.57/1/content/topics/1/file','/d2l/api/le/1.57/1/../users/','/d2l/api/lp/1.43/users/whoami\n']:
   self.assertFalse(allowed(path),path)
 def test_full_request_roundtrip_and_replay(self):
  with concurrent.futures.ThreadPoolExecutor() as pool:
   future=pool.submit(self.b.request,'/d2l/api/lp/1.43/users/whoami',3)
   time.sleep(.05)
   status,job=self.post();self.assertEqual(status,200);self.assertIn('id',job)
   self.assertEqual(self.post()[1],{})
   result={'id':job['id'],'data':{'Identifier':123}}
   self.assertEqual(self.post('/result',result)[0],200)
   self.assertEqual(future.result(),{'Identifier':123})
   self.assertEqual(self.post('/result',result)[0],409)
   self.assertFalse(self.b.jobs)
 def test_timeout_erases_job(self):
  with self.assertRaises(Exception):self.b.request('/d2l/api/lp/1.43/users/whoami',.01)
  self.assertFalse(self.b.jobs)
 def test_expired_and_future_proofs(self):
  self.assertEqual(self.post(age=-120)[0],403)
  self.assertEqual(self.post(age=120)[0],403)
 def test_tampered_body(self):self.assertEqual(self.post(sign_body=b'{"tampered":true}')[0],403)
 def test_request_proof_replay(self):
  nonce=secrets.token_hex(16)
  self.assertEqual(self.post(nonce=nonce)[0],200)
  self.assertEqual(self.post(nonce=nonce)[0],409)
 def test_missing_origin(self):self.assertEqual(self.post(origin='')[0],403)
 def test_private_key_file(self):
  import tempfile
  from safari_reader import load_key
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'safari-reader').mkdir();key=root/'safari-reader/token';key.write_text('S'*43);key.chmod(0o600)
   with patch('safari_reader.ROOT',root):
    self.assertEqual(load_key(),'S'*43)
    key.chmod(0o644)
    with self.assertRaises(RuntimeError):load_key()
    key.unlink();target=root/'target';target.write_text('S'*43);target.chmod(0o600);key.symlink_to(target)
    with self.assertRaises(OSError):load_key()
if __name__=='__main__':unittest.main()
