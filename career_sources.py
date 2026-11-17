"""Public employer ATS discovery; candidate eligibility and season still require review."""
import concurrent.futures,json,re,urllib.request
from bs4 import BeautifulSoup
BOARDS=['lyft','pinterest','stripe','figma','cloudflare','databricks','datadog','cockroachlabs','confluent','duolingo','hubspot','doordashcanada','khanacademy','towerresearchcapital','superhuman']
def board(name):
 try:
  url='https://boards-api.greenhouse.io/v1/boards/'+name+'/jobs?content=true'
  with urllib.request.urlopen(url,timeout=8) as response:raw=response.read(6000001)
  if len(raw)>6000000:raise ValueError()
  result=[]
  for job in json.loads(raw).get('jobs',[]):
   title=job.get('title','');location=(job.get('location') or {}).get('name','')
   if not re.search(r'\bintern\b|\binternship\b|\bco.?op\b',title,re.I) or not re.search(r'software|developer|engineer|machine learning',title,re.I):continue
   description=BeautifulSoup(job.get('content',''),'html.parser').get_text(' ',strip=True)
   result.append({'company':name,'title':title,'location':location,'url':job['absolute_url'],'updated_at':job.get('updated_at'),'description':description[:15000],'eligibility':'needs review','source':'official employer Greenhouse board'})
  return {'company':name,'status':'checked','roles':result}
 except Exception:return {'company':name,'status':'unavailable','roles':[]}
def collect():
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:return list(pool.map(board,BOARDS))
if __name__=='__main__':print(json.dumps(collect()))
