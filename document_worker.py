"""Untrusted-document text extraction. No execution of document code or external links."""
import base64,hashlib,io,json,re,resource,sys,zipfile,os
resource.setrlimit(resource.RLIMIT_CPU,(5,5))
if sys.platform=="darwin":
    if os.environ.get("DOCUMENT_MEMORY_GUARD")!="parent-rss-v1":raise RuntimeError("The tested macOS resident-memory supervisor is required.")
else:
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
MAX_BYTES=4*1024*1024
MAX_TEXT=180000

def extract(payload):
    data=base64.b64decode(payload['base64'],validate=True)
    if not 0<len(data)<=MAX_BYTES or len(data)!=payload['size']:raise ValueError('Invalid document size')
    if hashlib.sha256(data).hexdigest()!=payload['sha256']:raise ValueError('Document integrity mismatch')
    if payload['format']=='ics':
        from icalendar import Calendar
        import recurring_ical_events
        from datetime import datetime,time,timedelta
        from zoneinfo import ZoneInfo
        tz=ZoneInfo('America/Toronto');today=datetime.now(tz).date();start=datetime.combine(today,time(),tz);end=start+timedelta(days=14)
        calendar=Calendar.from_ical(data)
        if len(calendar.subcomponents)>3000:raise ValueError('Calendar bound exceeded')
        events=recurring_ical_events.of(calendar).between(start,end)
        if len(events)>1000:raise ValueError('Calendar event bound exceeded')
        result=[]
        for event in events:
            if str(event.get('STATUS','')).upper()=='CANCELLED':continue
            begin=event.decoded('DTSTART');finish=event.decoded('DTEND',begin)
            if isinstance(begin,datetime):begin=begin.replace(tzinfo=tz) if begin.tzinfo is None else begin.astimezone(tz)
            if isinstance(finish,datetime):finish=finish.replace(tzinfo=tz) if finish.tzinfo is None else finish.astimezone(tz)
            result.append({'title':str(event.get('SUMMARY',''))[:200],'start':begin.isoformat(),'end':finish.isoformat(),'location':str(event.get('LOCATION',''))[:300],'uid_hash':hashlib.sha256(str(event.get('UID','')).encode()).hexdigest()[:24]})
        return {'format':'ics','events':sorted(result,key=lambda e:e['start']),'window_start':start.isoformat(),'window_end':end.isoformat()}
    kind=payload['format'];units=[];warnings=[];truncated=False;total=0
    start=payload.get('start_unit',1);limit=payload.get('max_units',12)
    if not isinstance(start,int) or not 1<=start<=2000 or not isinstance(limit,int) or not 1<=limit<=20:raise ValueError('Invalid page range')
    if kind=='pdf':
        if not data.startswith(b'%PDF-'):raise ValueError('Invalid PDF signature')
        from pypdf import PdfReader
        pdf=PdfReader(io.BytesIO(data),strict=True)
        if pdf.is_encrypted:raise ValueError('Password-protected PDFs are unsupported')
        count=len(pdf.pages);total=count
        if count>2000:raise ValueError("Document has too many pages")
        for number in range(start-1,min(count,start-1+limit)):
            value=pdf.pages[number].extract_text() or ''
            units.append({'label':f'page {number+1}','text':value[:10000]})
        truncated=False
    elif kind in ('pptx','docx'):
        if not data.startswith(b'PK\x03\x04'):raise ValueError('Invalid Office file signature')
        from defusedxml import ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos=archive.infolist()
            if len(infos)>3000:raise ValueError('Too many archive entries')
            names=[i.filename for i in infos]
            if len(names)!=len(set(names)):raise ValueError('Duplicate archive entries')
            if any('vbaProject' in n for n in names):raise ValueError('Macros are unsupported')
            pattern=(r'ppt/slides/slide(\d+)\.xml' if kind=='pptx' else r'word/(?:document|footnotes|endnotes|header\d+|footer\d+)\.xml')
            selected=[i for i in infos if re.fullmatch(pattern,i.filename)]
            selected.sort(key=lambda i:int(re.search(r'\d+',i.filename).group()) if kind=='pptx' else i.filename)
            if not selected:raise ValueError('No supported document text')
            if sum(i.file_size for i in selected)>16*1024*1024:raise ValueError('Expanded document too large')
            total=len(selected)
            for number,info in enumerate(selected[start-1:start-1+limit],start):
                if info.flag_bits & 1 or info.file_size>4*1024*1024:raise ValueError('Unsupported archive entry')
                with archive.open(info) as source:xml=source.read(4*1024*1024+1)
                if len(xml)>4*1024*1024:raise ValueError('Expanded XML too large')
                tree=ET.fromstring(xml,forbid_dtd=True,forbid_entities=True,forbid_external=True)
                paragraphs=[]
                for paragraph in tree.iter():
                    if paragraph.tag.rsplit('}',1)[-1]=='p':
                        texts=[t.text for t in paragraph.iter() if t.tag.rsplit('}',1)[-1]=='t' and t.text]
                        if texts:paragraphs.append(' '.join(texts))
                units.append({'label':f'slide {number}' if kind=='pptx' else info.filename,'text':'\n'.join(paragraphs)[:30000]})
            truncated=False
    elif kind in ('text','html'):
        value=data.decode('utf-8-sig',errors='strict')
        if '\x00' in value:raise ValueError('Binary content is not text')
        if kind=='html':
            from bs4 import BeautifulSoup
            soup=BeautifulSoup(value,'html.parser')
            for node in soup(['script','style','form','input','button','iframe','object','embed']):node.decompose()
            value=soup.get_text(' ',strip=True)
        total=(len(value)+7999)//8000
        units=[{'label':f'text block {i//8000+1}','text':value[i:i+8000]} for i in range((start-1)*8000,min(len(value),(start-1+limit)*8000),8000)]
        truncated=len(value)>MAX_TEXT
    else:raise ValueError('Unsupported file format')
    used=0;bounded=[]
    for unit in units:
        remaining=MAX_TEXT-used
        if remaining<=0:truncated=True;break
        value=unit['text'][:remaining];used+=len(value);bounded.append({'label':unit['label'],'text':value})
    if used<20:warnings.append('Little or no extractable text; scanned pages or images may need separate review.')
    return {'format':kind,'units':bounded,'total_units':total,'start_unit':start,'has_more':start-1+len(bounded)<total,'warnings':warnings,'truncated':truncated}

try:
    raw=sys.stdin.buffer.read(6*1024*1024+1)
    if len(raw)>6*1024*1024:raise ValueError('Input too large')
    print(json.dumps(extract(json.loads(raw)),ensure_ascii=True))
except Exception:
    print(json.dumps({'error':'Document could not be safely extracted; it may be unsupported, malformed, encrypted, or too large.'}))
