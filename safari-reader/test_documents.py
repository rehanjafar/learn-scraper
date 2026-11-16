"""Synthetic documents only; no account, session, or real course files are used."""
import base64,hashlib,io,json,sys,unittest,zipfile,subprocess,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from document_reader import read_document,sandbox_profile
from resource_guard import run_guarded

def payload(raw,kind):return {'base64':base64.b64encode(raw).decode(),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'format':kind}
def office(name,xml):
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w') as archive:archive.writestr(name,xml)
 return stream.getvalue()
@unittest.skipUnless(sys.platform=='darwin','macOS process sandbox integration')
class DocumentTests(unittest.TestCase):
 def test_text(self):
  r=read_document(payload(b'Synthetic lesson and review plan.','text'));self.assertIn('Synthetic lesson',r['units'][0]['text'])
 def test_html_removes_active_and_form_content(self):
  r=read_document(payload(b'<p>Lesson text</p><script>SECRET_SCRIPT</script><form>SECRET_FORM</form>','html'));self.assertNotIn('SECRET',str(r))
 def test_docx(self):
  raw=office('word/document.xml','<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Word fixture</w:t></w:r></w:p></w:body></w:document>')
  self.assertIn('Word fixture',str(read_document(payload(raw,'docx'))))
 def test_pptx(self):
  raw=office('ppt/slides/slide1.xml','<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:p><a:r><a:t>Slide fixture</a:t></a:r></a:p></p:sld>')
  self.assertIn('Slide fixture',str(read_document(payload(raw,'pptx'))))
 def test_xml_entities_blocked(self):
  raw=office('word/document.xml','<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]><x>&leak;</x>')
  with self.assertRaises(Exception):read_document(payload(raw,'docx'))
 def test_invalid_hash(self):
  p=payload(b'Fixture','text');p['sha256']='0'*64
  with self.assertRaises(Exception):read_document(p)
 def test_pdf_pagination(self):
  from pypdf import PdfWriter
  from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
  writer=PdfWriter()
  for label in ('FIRST','SECOND'):
   page=writer.add_blank_page(width=612,height=792)
   font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
   page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
   content=DecodedStreamObject();content.set_data(f'BT /F1 12 Tf 72 720 Td ({label} fixture) Tj ET'.encode());page[NameObject('/Contents')]=writer._add_object(content)
  stream=io.BytesIO();writer.write(stream)
  result=read_document(payload(stream.getvalue(),'pdf'),2,1)
  self.assertEqual(result['total_units'],2);self.assertIn('SECOND',str(result));self.assertNotIn('FIRST',str(result))
 def test_memory_guard(self):
  with self.assertRaisesRegex(RuntimeError,'resident-memory'):
   run_guarded([sys.executable,'-I','-c','import time;x=bytearray(128*1024*1024);time.sleep(3)'],b'',{'PATH':'/usr/bin:/bin'},max_resident=32*1024*1024,timeout=2)
 def test_time_guard(self):
  with self.assertRaisesRegex(RuntimeError,'elapsed-time'):
   run_guarded([sys.executable,'-I','-c','import time;time.sleep(3)'],b'',{'PATH':'/usr/bin:/bin'},timeout=.2)
 def test_output_guard(self):
  with self.assertRaisesRegex(RuntimeError,'output bound'):
   run_guarded([sys.executable,'-I','-c','import sys;sys.stdout.write("x"*2000000)'],b'',{'PATH':'/usr/bin:/bin'})
 def test_sandbox_denies_network_and_unrelated_files(self):
  with tempfile.TemporaryDirectory() as directory:
   fixture=Path(directory)/'fixture';fixture.write_text('synthetic')
   for action in [f'open({str(fixture)!r}).read()', '__import__("socket").create_connection(("127.0.0.1",18766),timeout=1)']:
    script='try:\n '+action+'\nexcept PermissionError:\n print("DENIED")\nelse:\n raise AssertionError("Access should be denied")'
    r=subprocess.run(['/usr/bin/sandbox-exec','-p',sandbox_profile(),sys.executable,'-I','-c',script],capture_output=True,timeout=4)
    self.assertEqual(r.returncode,0);self.assertEqual(r.stdout.strip(),b'DENIED')
if __name__=='__main__':unittest.main()
