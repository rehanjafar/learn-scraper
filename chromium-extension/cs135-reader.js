if(typeof globalThis.browser==='undefined')globalThis.browser=chrome;
browser.runtime.onMessage.addListener(async(job,sender)=>{
 if(sender.id!==browser.runtime.id||sender.tab||(sender.url&&!sender.url.startsWith(browser.runtime.getURL(''))))return;
 if(location.origin!=='https://student.cs.uwaterloo.ca'||!location.pathname.startsWith('/~cs135/'))return;
 if(job?.type!=='cs135Read'||!CS135Policy.kind(job.path))return;
 try{
  const response=await fetch(CS135Policy.url(job.path),{method:'GET',credentials:'same-origin',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw Error('Unavailable');
  const reader=response.body.getReader();let size=0,chunks=[];const cap=CS135Policy.kind(job.path)==='file'?4194304:1500000;
  while(true){const p=await reader.read();if(p.done)break;size+=p.value.length;if(size>cap){await reader.cancel();throw Error('Too large');}chunks.push(p.value);}
  const raw=new Uint8Array(size);let offset=0;for(const c of chunks){raw.set(c,offset);offset+=c.length;}
  const format=CS135Policy.kind(job.path)==='file'?'pdf':'html';
  if(format==='pdf'&&String.fromCharCode(...raw.slice(0,5))!=='%PDF-')throw Error('Not PDF');
  if(format==='html'&&!response.headers.get('content-type')?.includes('text/html'))throw Error('Not HTML');
  if(format==='html'){
   // A template remains inert and is never inserted into the live page.
   const template=document.createElement('template');template.innerHTML=new TextDecoder().decode(raw);
   if(template.content.querySelector('input[type="password"],form[action*="adfs"],form[action*="login"]'))throw Error('Sign-in required');
   for(const node of template.content.querySelectorAll('script,style,form,input,button,iframe,object,embed,img,link,meta,svg'))node.remove();
   const body=template.content.querySelector('main,#body-inner')||template.content;
   const links=[];for(const a of body.querySelectorAll('a[href]')){
    try{const u=new URL(a.getAttribute('href'),CS135Policy.url(job.path));if(u.origin==='https://student.cs.uwaterloo.ca'&&u.pathname.startsWith('/~cs135/')&&!u.search&&!u.hash&&!u.username&&!u.password)links.push({title:(a.textContent||'').trim().slice(0,200),url:u.href});}catch(e){}
    if(links.length>=200)break;
   }
   // Only sanitized course markup is passed to the local structural parser.
   return {data:{source:CS135Policy.url(job.path),html:body.innerHTML.slice(0,1500000),links}};
  }
  let binary='';for(let i=0;i<raw.length;i+=16384)binary+=String.fromCharCode(...raw.subarray(i,i+16384));
  const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),b=>b.toString(16).padStart(2,'0')).join('');
  return {data:{source:CS135Policy.url(job.path),file:{format,size:raw.length,sha256,base64:btoa(binary)}}};
 }catch(e){return {error:'CS135 resource unavailable. Sign in to the official CS135 site in this browser; no login data was exported.'};}
});
