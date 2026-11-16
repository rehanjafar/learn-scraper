/* Runs only in the isolated extension world on the top-level LEARN home page. */
let busy=false;
async function tick(){
 if(busy||location.origin!=='https://learn.uwaterloo.ca'||!/^\/d2l\/home(?:[/?#]|$)/.test(location.pathname))return;
 busy=true;
 try {
  const job=await browser.runtime.sendMessage({type:'poll'});
  if(!job?.id)return;
  let result={id:job.id,error:'Request failed; sign in to LEARN in Safari.'};
  try{
   const k=SafariPolicy.kind(job.path);if(!k)throw Error('Blocked request');
   const r=await fetch(location.origin+job.path,{method:'GET',credentials:'same-origin',redirect:'error',cache:'no-store',headers:{Accept:'application/json'},signal:AbortSignal.timeout(10000)});
   if(!r.ok||!r.headers.get('content-type')?.includes('json'))throw Error('Sign-in required or LEARN refused request');
   const reader=r.body.getReader();let bytes=0,chunks=[];
   while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>1500000){await reader.cancel();throw Error('Response too large');}chunks.push(value);}
   const combined=new Uint8Array(bytes);let off=0;for(const c of chunks){combined.set(c,off);off+=c.length;}
   const data=SafariPolicy.project(k,JSON.parse(new TextDecoder().decode(combined)));
   result={id:job.id,data};
  }catch(e){result.error='LEARN request unavailable. Check your Safari sign-in or the requested course.';}
  await browser.runtime.sendMessage({type:'result',result});
 }catch(e){/* No local server: idle. Never log private data. */}
 finally{busy=false;}
}
setInterval(tick,1000);tick();
