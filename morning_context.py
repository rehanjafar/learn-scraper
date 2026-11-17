"""Read-only morning context gateway for connected Desktop Commander or a local client."""
import argparse,asyncio,json,re
from datetime import datetime,timezone
from pathlib import Path
from fastmcp import Client
ROOT=Path(__file__).resolve().parent

def flatten(nodes):
    for node in nodes:
        for topic in node.get('topics',[]):yield topic
        yield from flatten(node.get('modules',[]))
async def collect(days=14,materials=3):
    async with Client(ROOT/'safari_server.py') as client:
        await asyncio.sleep(1.5)
        state=(await client.call_tool('planner_state_get',{})).data
        result={'checked_at':datetime.now(timezone.utc).isoformat(),'timezone':state['profile']['timezone'],'profile':state['profile'],'tracker':state['records'],'courses':[],'coverage':{},'calendar_write_status':'not requested; this collector is read-only'}
        async def call(name,args,label):
            try:
                response=await client.call_tool(name,args,raise_on_error=False)
                if response.is_error:raise RuntimeError('Source request unavailable')
                data=response.data
                partial=isinstance(data,dict) and (bool(data.get('has_more') or data.get('truncated')) or (name=='cs135_public' and any(p.get('status')!='checked' for p in data.get('pages',{}).values())))
                result['coverage'][label]={'status':'partial' if partial else 'checked'}
                if not partial:
                    await client.call_tool('planner_state_record',{'category':'source_scans','key':label,'value':{'last_success':result['checked_at']},'source':'verified_source'})
                return response.data
            except Exception:
                result['coverage'][label]={'status':'unavailable','action':'Check browser sign-in, required course tabs, site permission, and the source link.'};return None
        result['cs135']=await call('cs135_public',{'days':days},'CS135/public')
        if result['cs135']:
            for name,page in result['cs135'].get('pages',{}).items():
                result['coverage']['CS135/'+name]={'status':page.get('status','unavailable'),'source':page.get('source')}
            if result['cs135']['pages'].get('assignments',{}).get('status')=='requires_browser_sign_in':
                protected=await call('cs135_page',{'page':'assignments'},'CS135/assignments/browser')
                if protected:
                    result['cs135']['pages']['assignments']=protected
                    result['coverage']['CS135/assignments']={'status':'checked','source':protected['source']}
                    lessons=result['cs135']['pages'].get('lessons',{}).get('lessons',[])
                    relevant=[e['title'] for e in result['cs135'].get('upcoming',[]) if re.fullmatch(r'L\d{2}',e['title'])]
                    selected=next((lesson for code in relevant for lesson in lessons if lesson['lecture']==code),None)
                    if selected and materials>0:
                        prefix='https://student.cs.uwaterloo.ca/~cs135/'
                        document=await call('cs135_file',{'path':selected['url'].removeprefix(prefix),'max_units':6},'CS135/current_lesson')
                        if document:result['cs135']['materials']=[document]
            # Public pages remain useful even if browser pairing/LEARN fails.
        courses=await call('learn_courses',{},'LEARN/enrollments')
        if courses is None:return result
        wanted=state['profile']['courses'];remaining=materials
        for course in courses:
            code=re.sub(r'[^A-Z0-9]','',course['code'].upper())
            if not any(code.startswith(w) for w in wanted):continue
            cid=course['id'];entry={**course,'announcements':await call('learn_announcements',{'course':cid,'limit':8},f'LEARN/{cid}/announcements'),'assignments':await call('learn_assignments',{'course':cid},f'LEARN/{cid}/assignments'),'content':await call('learn_content',{'course':cid},f'LEARN/{cid}/content'),'materials':[]}
            topics=list(flatten(entry['content'] or []))
            candidates=[t for t in topics if re.search(r'syllabus|course schedule|course outline',t['title'],re.I)]
            for topic in candidates:
                if remaining<=0:break
                if not (topic.get('url') or '').startswith(f'https://learn.uwaterloo.ca/content/enforced/{cid}'):
                    entry['materials'].append({'topic':topic['id'],'title':topic['title'],'status':'external or unsupported link','source':topic.get('url')});continue
                remaining-=1
                text=await call('learn_file',{'course':cid,'topic':topic['id'],'max_units':6},f'LEARN/{cid}/file/{topic["id"]}')
                if text:entry['materials'].append(text)
            result['courses'].append(entry)
        result['due_dates']=[]
        for course in result['courses']:
            events=await call('learn_due',{'days':days,'course':course['id']},f'LEARN/{course["id"]}/calendar')
            if events is not None:result['due_dates'].extend(events)
        for label in ('Apple Calendar','Gmail','university Outlook','Quest','WaterlooWorks','Instagram DMs','iMessage','LinkedIn','X','web research'):
            result['coverage'][label]={'status':'not checked by local collector','action':'Use an authorized connected source during the morning briefing; report unavailable access honestly.'}
        return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--days',type=int,choices=range(1,121),default=14);parser.add_argument('--materials',type=int,choices=range(0,9),default=3);parser.add_argument('--summary',action='store_true');args=parser.parse_args()
    data=asyncio.run(collect(args.days,args.materials))
    if args.summary:print(json.dumps({'checked_at':data['checked_at'],'course_count':len(data['courses']),'material_count':sum(sum('units' in m for m in c['materials']) for c in data['courses']),'coverage':data['coverage'],'cs135_lesson_count':len(((data.get('cs135') or {}).get('pages',{}).get('lessons',{})).get('lessons',[]))},ensure_ascii=False))
    else:print(json.dumps(data,ensure_ascii=False))
