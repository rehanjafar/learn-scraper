import sys,tempfile,unittest,os,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import planner_state as state
from morning_context import flatten
class PlannerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.patch=patch.object(state,'ROOT',Path(self.tmp.name));self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def test_private_persistence(self):
  state.record('applications','employer/123',{'submitted':False})
  self.assertFalse(state.get_state()['records']['applications']['employer/123']['value']['submitted'])
  self.assertEqual((Path(self.tmp.name)/'planner_state/state.json').stat().st_mode&0o777,0o600)
 def test_startup_dedup(self):
  state.record('startups','https://www.example.com/about',{'alias':'Example'})
  state.record('startups','example.com',{'alias':'Example Inc'})
  self.assertEqual(list(state.get_state()['records']['startups']),['example.com'])
 def test_progress_requires_evidence(self):
  with self.assertRaises(ValueError):state.record('course_progress','MATH135',{'independent':True},source='inferred')
 def test_storage_symlink_rejected(self):
  os.symlink(self.tmp.name,Path(self.tmp.name)/'planner_state')
  with self.assertRaises(RuntimeError):state.get_state()
 def test_invalid_and_oversize(self):
  with self.assertRaises(ValueError):state.record('invalid','x',{})
  with self.assertRaises(ValueError):state.record('projects','x',{'large':'x'*33000})
 def test_flatten_nested(self):
  self.assertEqual(list(flatten([{'topics':[{'id':1}],'modules':[{'topics':[{'id':2}]}]}])),[{'id':1},{'id':2}])
if __name__=='__main__':unittest.main()
