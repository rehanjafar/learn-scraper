// Pairing key is runtime-only in Safari storage; never included in source or app bundle.
const BASE='http://127.0.0.1:18766';
browser.runtime.onMessage.addListener(async (m,sender)=>{
 if(!sender.tab || sender.frameId!==0 || !/^https:\/\/learn\.uwaterloo\.ca\/d2l\/home(?:[/?#]|$)/.test(sender.url||'')) return;
 if(!m || !['poll','result'].includes(m.type)) return;
 const saved=await browser.storage.local.get('localKey');
 const TOKEN=saved.localKey;
 if(typeof TOKEN!=='string'||TOKEN.length<40)throw Error('Pair this extension first.');
 const endpoint=m.type==='poll'?'/next':'/result';
 const body=m.type==='result'?JSON.stringify(m.result):'{}';
 if(body.length>2*1024*1024) throw Error('Response too large');
 const r=await fetch(BASE+endpoint,{method:'POST',credentials:'omit',cache:'no-store',redirect:'error',headers:{'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'},body});
 if(!r.ok) throw Error('Local reader unavailable');
 return await r.json();
});
