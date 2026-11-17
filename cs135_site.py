"""Bounded, credential-free reads of the official CS135 site; redirects never followed."""
import argparse,json,re,urllib.request,urllib.error
from datetime import datetime,date,timedelta,timezone,time as dt_time
from urllib.parse import urljoin,urlsplit
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup,Comment
BASE='https://student.cs.uwaterloo.ca/~cs135/'
PAGES={'home':'index.html','calendar':'calendar/index.html','lessons':'slides/index.html','assessment':'assess/index.html','assignments':'assign/index.html'}
MONTHS={name:i for i,name in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def course_url(value):
 if not isinstance(value,str) or len(value)>1000 or re.search(r'[\x00-\x20%\\]',value):raise ValueError('Invalid course URL')
 u=urlsplit(urljoin(BASE,value))
 if u.scheme!='https' or u.netloc!='student.cs.uwaterloo.ca' or not u.path.startswith('/~cs135/') or u.username or u.password or u.query or u.fragment or any(p in ('.','..') for p in value.split('/')):raise ValueError('Outside CS135 scope')
 return u.geturl()

def parse_page(html,relative):
 if not isinstance(html,str) or len(html)>1500000:raise ValueError('Page bound exceeded')
 source=course_url(relative);soup=BeautifulSoup(html,'html.parser')
 if soup.select_one('input[type="password"],form[action*="adfs"],form[action*="login"]'):raise ValueError('Sign-in page')
 for node in soup(['script','style','form','input','button','iframe','object','embed','nav','aside','footer']):node.decompose()
 for node in soup.find_all(string=lambda s:isinstance(s,Comment)):node.extract()
 body=soup.select_one('main,#body-inner') or soup
 links=[]
 for a in body.select('a[href]')[:500]:
  try:url=course_url(urljoin(source,a['href']))
  except ValueError:continue
  links.append({'title':a.get_text(' ',strip=True)[:200],'url':url})
  if len(links)>=200:break
 result={'source':source,'title':(body.h1.get_text(' ',strip=True) if body.h1 else 'CS135')[:200],'text':body.get_text(' ',strip=True)[:60000],'links':links}
 if relative==PAGES['calendar']:
  entries=[];terms=[]
  for table in body.select('table.cal')[:12]:
   header=table.find('th');match=re.search(r'([A-Za-z]+)\s+(20\d\d)',header.get_text(' ',strip=True) if header else '')
   if not match or match[1] not in MONTHS:continue
   year=int(match[2]);month=MONTHS[match[1]];terms.append(f'{year}-{month:02}')
   for cell in table.find_all('td')[:50]:
    day=cell.select_one('.date')
    if not day or not day.get_text(strip=True).isdigit():continue
    try:when=date(year,month,int(day.get_text(strip=True)))
    except ValueError:continue
    day.extract();events=[x.strip() for x in cell.get_text('\n',strip=True).splitlines() if x.strip()]
    for event in events[:12]:
     item={'date':when.isoformat(),'title':event[:200],'source':source,'timezone':'America/Toronto'}
     if re.fullmatch(r'A\d{2} Due',event):item['due_at']=datetime.combine(when,dt_time(21),ZoneInfo('America/Toronto')).isoformat()
     entries.append(item)
  result.update(calendar=entries,calendar_months=terms)
 if relative==PAGES['lessons']:
  lessons=[]
  for row in body.select('tr')[:100]:
   cells=row.find_all('td');a=row.find('a',href=True)
   if len(cells)<2 or not a:continue
   lecture=cells[0].get_text(' ',strip=True)
   if not re.fullmatch(r'L\d{2}',lecture):continue
   try:url=course_url(urljoin(source,a['href']))
   except ValueError:continue
   lessons.append({'lecture':lecture,'title':a.get_text(' ',strip=True)[:200],'description':cells[-1].get_text(' ',strip=True)[:1000],'url':url,'content_status':'not read; may require browser sign-in'})
  result['lessons']=lessons
 return result

def fetch_page(name):
 if name not in PAGES:raise ValueError('Unknown course page')
 relative=PAGES[name];source=course_url(relative)
 try:
  request=urllib.request.Request(source,headers={'User-Agent':'WaterlooPlanner/0.4.1 (personal read-only course planner)','Accept':'text/html'})
  with urllib.request.build_opener(NoRedirect).open(request,timeout=10) as response:
   if 'text/html' not in response.headers.get('Content-Type',''):raise ValueError('Expected HTML')
   raw=response.read(1500001)
   if len(raw)>1500000:raise ValueError('Page too large')
   html=raw.decode('utf-8',errors='strict')
  return {'status':'checked',**parse_page(html,relative)}
 except urllib.error.HTTPError as error:
  status='requires_browser_sign_in' if error.code in (301,302,303,307,308,401,403) else 'unavailable'
  error.close();return {'status':status,'source':source}
 except (OSError,ValueError,urllib.error.URLError):return {'status':'unavailable','source':source}

def collect_public(days=14):
 if not 1<=days<=120:raise ValueError('Invalid time window')
 pages={name:fetch_page(name) for name in PAGES}
 today=datetime.now(ZoneInfo('America/Toronto')).date();end=today+timedelta(days=days)
 calendar=pages['calendar'];events=calendar.get('calendar',[])
 return {'checked_at':datetime.now(timezone.utc).isoformat(),'site':BASE,'pages':pages,'upcoming':[e for e in events if today.isoformat()<=e['date']<=end.isoformat()],'term_coverage':'current date covered' if any(m==today.strftime('%Y-%m') for m in calendar.get('calendar_months',[])) else 'current month missing; confirm current course term','content_is_untrusted':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--summary',action='store_true');args=p.parse_args();data=collect_public()
 if args.summary:print(json.dumps({'coverage':{k:v['status'] for k,v in data['pages'].items()},'lesson_count':len(data['pages']['lessons'].get('lessons',[])),'upcoming':data['upcoming'],'term_coverage':data['term_coverage']}))
 else:print(json.dumps(data))
