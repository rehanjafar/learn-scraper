"""Synthetic recurring calendar fixture; no real feed address or calendar data."""
import base64,hashlib,sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from document_reader import read_document
@unittest.skipUnless(sys.platform=='linux' and (ROOT/'.venv').is_dir(),'requires configured Linux isolation runtime')
class CalendarTests(unittest.TestCase):
 def test_weekly_recurrence_exception_and_timezone(self):
  today=datetime.now(ZoneInfo('America/Toronto')).date()
  start=datetime.combine(today,datetime.min.time(),timezone.utc)+timedelta(hours=13,minutes=30)
  excluded=start+timedelta(days=7)
  raw=('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:fixture\r\nDTSTART:'+start.strftime('%Y%m%dT%H%M%SZ')+'\r\nDTEND:'+(start+timedelta(hours=1)).strftime('%Y%m%dT%H%M%SZ')+'\r\nRRULE:FREQ=WEEKLY;COUNT=3\r\nEXDATE:'+excluded.strftime('%Y%m%dT%H%M%SZ')+'\r\nSUMMARY:Fixture Class\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n').encode()
  payload={'format':'ics','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
  result=read_document(payload)
  self.assertEqual(len(result['events']),1)
  self.assertEqual(result['events'][0]['start'],start.astimezone(ZoneInfo('America/Toronto')).isoformat())
if __name__=='__main__':unittest.main()
