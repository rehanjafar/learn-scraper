/* Only extension-background requests may invoke a read. No webpage messaging. */
browser.runtime.onMessage.addListener(async(job,sender)=>{
 if(sender.id!==browser.runtime.id||sender.tab||(sender.url&&!sender.url.startsWith(browser.runtime.getURL(''))))return;
 if(location.origin!=='https://learn.uwaterloo.ca'||!/^\/d2l\/home(?:[/?#]|$)/.test(location.pathname))return;
 if(job?.type!=='learnRead'||!SafariPolicy.kind(job.path))return;
  try{
   if(SafariPolicy.kind(job.path)==='file')return await readCourseFile(job.path);
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

async function boundedBytes(response,limit){
 const reader=response.body.getReader();let count=0,chunks=[];
 while(true){const part=await reader.read();if(part.done)break;count+=part.value.length;if(count>limit){await reader.cancel();throw Error('File exceeds size limit');}chunks.push(part.value);}
 const result=new Uint8Array(count);let offset=0;for(const part of chunks){result.set(part,offset);offset+=part.length;}return result;
}
async function readCourseFile(path){
 const match=path.match(/^\/d2l\/api\/le\/1\.57\/([1-9]\d*)\/content\/topics\/([1-9]\d*)\/file$/);if(!match)throw Error('Blocked request');
 const course=Number(match[1]),topic=Number(match[2]);
 const options={method:'GET',credentials:'same-origin',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(12000)};
 const meta=await fetch(location.origin+path.slice(0,-5),{...options,headers:{Accept:'application/json'}});
 if(!meta.ok||!meta.headers.get('content-type')?.includes('json'))throw Error('Topic metadata unavailable');
 const rawMeta=await boundedBytes(meta,100000);const info=JSON.parse(new TextDecoder().decode(rawMeta));
 const url=SafariPolicy.fileURL(course,info.Url);
 const response=await fetch(url,options);if(!response.ok)throw Error('Course file unavailable');
 const data=await boundedBytes(response,4*1024*1024);if(!data.length)throw Error('Empty file');
 const name=decodeURIComponent(new URL(url).pathname.split('/').pop());let format;
 if(/\.pdf$/i.test(name)&&String.fromCharCode(...data.slice(0,5))==='%PDF-')format='pdf';
 else if(/\.(pptx|docx)$/i.test(name)&&data[0]===80&&data[1]===75&&data[2]===3&&data[3]===4)format=name.toLowerCase().endsWith('.pptx')?'pptx':'docx';
 else if(/\.(html?|txt|md|csv|rkt|py|c|h|json)$/i.test(name))format=/\.html?$/i.test(name)?'html':'text';
 else throw Error('Unsupported course file format');
 let binary='';for(let offset=0;offset<data.length;offset+=16384)binary+=String.fromCharCode(...data.subarray(offset,offset+16384));
 const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');
 return {data:{title:String(info.Title||name).slice(0,200),name:name.slice(0,200),source:'https://learn.uwaterloo.ca/d2l/le/content/'+course+'/viewContent/'+topic+'/View',file:{format,size:data.length,sha256:sha,base64:btoa(binary)}}};
}
