import concurrent.futures,json,sys,time,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from safari_reader import Broker,allowed,PORT
class SecurityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with patch('safari_reader.Path.read_text',return_value='synthetic-test-key-not-an-installation-secret'):
   cls.b=Broker()
  cls.b.start()
 @classmethod
 def tearDownClass(cls):cls.b.stop()
 def post(self,path='/next',body={},token=True,origin='safari-web-extension://TEST-UUID',host=None):
  headers={'Content-Type':'application/json','Origin':origin}
  if token:headers['Authorization']='Bearer '+self.b.token
  if host:headers['Host']=host
  request=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=json.dumps(body).encode(),headers=headers)
  try:
   with urllib.request.urlopen(request,timeout=3) as response:return response.status,json.load(response)
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
if __name__=='__main__':unittest.main()
