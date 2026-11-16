/* Only extension-background requests may invoke a read. No webpage messaging. */
browser.runtime.onMessage.addListener(async(job,sender)=>{
 if(sender.id!==browser.runtime.id||sender.tab||(sender.url&&!sender.url.startsWith(browser.runtime.getURL(''))))return;
 if(location.origin!=='https://learn.uwaterloo.ca'||!/^\/d2l\/home(?:[/?#]|$)/.test(location.pathname))return;
 if(job?.type!=='learnRead'||!SafariPolicy.kind(job.path))return;
  try{
   const k=SafariPolicy.kind(job.path);if(!k)throw Error('Blocked request');
   const r=await fetch(location.origin+job.path,{method:'GET',credentials:'same-origin',redirect:'error',cache:'no-store',headers:{Accept:'application/json'},signal:AbortSignal.timeout(10000)});
   if(!r.ok||!r.headers.get('content-type')?.includes('json'))throw Error('Sign-in required or LEARN refused request');
   const reader=r.body.getReader();let bytes=0,chunks=[];
   while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>1500000){await reader.cancel();throw Error('Response too large');}chunks.push(value);}
   const combined=new Uint8Array(bytes);let off=0;for(const c of chunks){combined.set(c,off);off+=c.length;}
   const data=SafariPolicy.project(k,JSON.parse(new TextDecoder().decode(combined)));
   return {data};
  }catch(e){return {error:'LEARN request unavailable. Check your Safari sign-in or the requested course.'};}

});
