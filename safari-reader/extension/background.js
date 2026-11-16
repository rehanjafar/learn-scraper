// Pairing key stays in Safari storage; only request and response proofs cross loopback.
const BASE='http://127.0.0.1:18766';
const encoder=new TextEncoder();
const hex=bytes=>Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
async function sha(body){return hex(await crypto.subtle.digest('SHA-256',encoder.encode(body)));}
async function hmac(key,message){return hex(await crypto.subtle.sign('HMAC',key,encoder.encode(message)));}
async function bridge(path,body){
 const saved=await browser.storage.local.get('localKey');
 if(typeof saved.localKey!=='string'||!/^[A-Za-z0-9_-]{43}$/.test(saved.localKey))throw Error('Pair this extension first.');
 const key=await crypto.subtle.importKey('raw',encoder.encode(saved.localKey),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const timestamp=String(Math.floor(Date.now()/1000));
 const nonce=hex(crypto.getRandomValues(new Uint8Array(16)));
 const origin=location.origin;
 const message=['v1','POST',path,'127.0.0.1:18766',origin,timestamp,nonce,await sha(body)].join('\n');
 const signature=await hmac(key,message);
 const r=await fetch(BASE+path,{method:'POST',credentials:'omit',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(4000),headers:{'Content-Type':'application/json','X-Waterloo-Time':timestamp,'X-Waterloo-Nonce':nonce,'X-Waterloo-Signature':signature},body});
 const reader=r.body.getReader();let bytes=0,chunks=[];
 while(true){const part=await reader.read();if(part.done)break;bytes+=part.value.byteLength;if(bytes>2000000){await reader.cancel();throw Error('Response too large');}chunks.push(part.value);}
 const combined=new Uint8Array(bytes);let offset=0;for(const part of chunks){combined.set(part,offset);offset+=part.length;}
 const text=new TextDecoder().decode(combined);
 const expected=await hmac(key,['v1','response',nonce,String(r.status),await sha(text)].join('\n'));
 if(r.headers.get('X-Waterloo-Signature')!==expected)throw Error('Local server identity could not be verified.');
 if(!r.ok)throw Error('Local reader unavailable');
 return JSON.parse(text);
}
let busy=false;
async function tick(){
 if(busy)return;
 busy=true;
 try{
  const saved=await browser.storage.local.get('localKey');if(!saved.localKey)return;
  // Host permission reveals only matching LEARN tabs; no tabs/history permission is requested.
  const tabs=await browser.tabs.query({url:'https://learn.uwaterloo.ca/d2l/home*'});
  const eligible=tabs.filter(t=>/^https:\/\/learn\.uwaterloo\.ca\/d2l\/home(?:[/?#]|$)/.test(t.url||''));
  const tab=eligible.find(t=>t.active)||eligible[0];if(!tab)return;
  const job=await bridge('/next','{}');if(!job?.id)return;
  let result;
  try{
   if(!SafariPolicy.kind(job.path))throw Error('Blocked request');
   const reply=await Promise.race([browser.tabs.sendMessage(tab.id,{type:'learnRead',path:job.path}),new Promise((_,reject)=>setTimeout(()=>reject(Error('Tab unavailable')),12000))]);
   if(!reply||(!('data' in reply)&&!('error' in reply)))throw Error('Tab unavailable');
   result='data' in reply?{id:job.id,data:reply.data}:{id:job.id,error:'LEARN sign-in required.'};
  }catch(e){result={id:job.id,error:'Keep a signed-in LEARN home tab open in Safari.'};}
  const body=JSON.stringify(result);if(encoder.encode(body).length>1500000)throw Error('Response too large');
  await bridge('/result',body);
 }catch(e){/* Idle without a local server. Never log private data. */}
 finally{busy=false;}
}
setInterval(tick,1000);tick();
