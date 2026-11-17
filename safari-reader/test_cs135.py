import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from cs135_site import course_url,parse_page
class CS135Tests(unittest.TestCase):
 def test_scope(self):
  self.assertEqual(course_url('f26-slides/CS135-F26-L17.pdf'),'https://student.cs.uwaterloo.ca/~cs135/f26-slides/CS135-F26-L17.pdf')
  for value in ['https://evil.example/x','https://evil@student.cs.uwaterloo.ca/~cs135/x','/~other/x','../private','assign/../../private','assign/%2e%2e/private','assign/file.pdf?token=x','assign/file.pdf#token','assign\\private']:
   with self.assertRaises(ValueError,msg=value):course_url(value)
 def test_calendar_dates(self):
  html='<table class="cal"><tr><th>November 2026</th></tr><tr><td><span class="date">17</span><br>L17<br>A07 Due</td></tr></table>'
  result=parse_page(html,'calendar/index.html');self.assertEqual(result['calendar'][1]['due_at'],'2026-11-17T21:00:00-05:00');self.assertEqual(result['calendar'][0]['date'],'2026-11-17')
 def test_lecture(self):
  html='<table><tr><td>L17</td><td><a href="../f26-slides/CS135-F26-L17.pdf">Lambda</a></td><td>Anonymous functions</td></tr></table>'
  result=parse_page(html,'slides/index.html');self.assertEqual(result['lessons'][0]['lecture'],'L17')
 def test_no_active_or_form_data(self):
  r=parse_page('<h1>CS135</h1><script>SECRET</script><form>SECRET</form><p>Lesson</p>','index.html');self.assertNotIn('SECRET',str(r))
 def test_login_rejected(self):
  with self.assertRaises(ValueError):parse_page('<form action="https://adfs.example/login"><input type="password"></form>','assign/index.html')
if __name__=='__main__':unittest.main()
