/* Exact read-only endpoint and output allowlists; no arbitrary URLs or headers. */
(function(g){
const routes=[
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/content\/topics\/[1-9]\d*\/file$/, 'file'],
 [/^\/d2l\/api\/lp\/1\.43\/users\/whoami$/, 'whoami'],
 [/^\/d2l\/api\/lp\/1\.43\/enrollments\/myenrollments\/\?orgUnitTypeId=3$/, 'courses'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/grades\/values\/myGradeValues\/$/, 'grades'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/dropbox\/folders\/$/, 'assignments'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/dropbox\/folders\/[1-9]\d*$/, 'assignment'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/dropbox\/folders\/[1-9]\d*\/submissions\/$/, 'submissions'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/calendar\/events\/myEvents\/\?startDateTime=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.000Z&endDateTime=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.000Z$/, 'calendar'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/news\/$/, 'news'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/content\/toc$/, 'toc'],
 [/^\/d2l\/api\/le\/1\.57\/[1-9]\d*\/content\/topics\/[1-9]\d*$/, 'topic']
];
function kind(path){if(typeof path!=='string'||path.length>300||/[\r\n]/.test(path))return null;return routes.find(([r])=>r.test(path))?.[1]||null;}
function text(v){return typeof v==='string'?v.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,'').replace(/<[^>]*>/g,' ').slice(0,20000):v;}
function scalar(v){return v===null||typeof v==='boolean'||(typeof v==='number'&&Number.isFinite(v))||typeof v==='string';}
function pick(o,keys){const r={};for(const k of keys){if(o&&scalar(o[k]))r[k]=typeof o[k]==='string'?text(o[k]):o[k];}return r;}
function arr(v){if(!Array.isArray(v))throw Error('Unexpected LEARN data');return v.slice(0,1000);}
function rich(o,key){return {Html:text(o?.[key]?.Html||o?.[key]?.Text||'')};}
function url(v){if(typeof v!=='string'||!v)return null;try{const u=new URL(v,'https://learn.uwaterloo.ca');return u.protocol==='https:'&&!u.username&&!u.password&&!/[?&](token|code|session|auth|samlresponse)=/i.test(u.search)?u.href:null;}catch{return null;}}
function folder(o){return {...pick(o,['Id','Name','DueDate','EndDate']),Instructions:rich(o,'Instructions'),Attachments:arr(o.Attachments||[]).map(a=>pick(a,['FileName']))};}
function topic(o){return {...pick(o,['TopicId','Id','Title','TypeIdentifier']),Url:url(o.Url),Description:rich(o,'Description')};}
function module(o,depth=0){if(depth>12)throw Error('Content too deeply nested');return {...pick(o,['Title']),Topics:arr(o.Topics||[]).map(topic),Modules:arr(o.Modules||[]).map(x=>module(x,depth+1))};}
function project(k,d){
 switch(k){
 case 'whoami':return pick(d,['Identifier']);
 case 'courses':return {Items:arr(d.Items).map(e=>({OrgUnit:pick(e.OrgUnit,['Id','Name','Code']),Access:pick(e.Access,['StartDate','EndDate','IsActive','CanAccess'])}))};
 case 'grades':return arr(d).map(g=>pick(g,['GradeObjectName','PointsNumerator','PointsDenominator','WeightedNumerator','WeightedDenominator','DisplayedGrade']));
 case 'assignments':return arr(d).map(folder);
 case 'assignment':return folder(d);
 case 'submissions':return arr(d).map(e=>({Submissions:arr(e.Submissions||[]).map(s=>({...pick(s,['SubmissionDate']),Files:arr(s.Files||[]).map(f=>pick(f,['FileName']))}))}));
 case 'calendar':return {Objects:arr(Array.isArray(d)?d:d.Objects).map(e=>({...pick(e,['Title','StartDateTime','EndDateTime']),Description:text(e.Description),AssociatedEntity:pick(e.AssociatedEntity,['AssociatedEntityType','AssociatedEntityId'])}))};
 case 'news':return arr(d).map(n=>({...pick(n,['Title','StartDate']),Body:rich(n,'Body')}));
 case 'toc':return {Modules:arr(d.Modules).map(m=>module(m))};
 case 'topic':return topic(d);
 default:throw Error('Blocked request');
 }
}
function fileURL(course,value){
 if(!Number.isSafeInteger(course)||course<1||typeof value!=='string'||value.length>2000)throw Error('Blocked file URL');
 const u=new URL(value,'https://learn.uwaterloo.ca');
 if(u.origin!=='https://learn.uwaterloo.ca'||u.username||u.password||u.hash)throw Error('External file links are unsupported');
 let path=u.pathname;for(let i=0;i<2;i++)path=decodeURIComponent(path);
 if(/[\\\x00-\x1f]/.test(path)||path.split('/').some(p=>p==='.'||p==='..')||/%(?:2e|2f|5c|25)/i.test(path))throw Error('Blocked encoded file URL');
 if(!path.startsWith('/content/enforced/'+course+'-')&&!path.startsWith('/content/enforced/'+course+'/'))throw Error('File is outside this course');
 for(const [k,v] of u.searchParams){if(k!=='ou'||v!==String(course))throw Error('Unsupported file query');}
 return u.href;
}
g.SafariPolicy={kind,project,fileURL};
})(globalThis);
