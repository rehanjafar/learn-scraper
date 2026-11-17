if(typeof globalThis.browser==='undefined')globalThis.browser=chrome;
async function status(){const s=await browser.storage.local.get('localKey');document.getElementById('state').textContent=s.localKey?'Paired. Requests run only while the local server and a LEARN home tab are open.':'Not paired.';}
document.getElementById('pair').onclick=async()=>{const key=document.getElementById('key').value.trim();if(!/^[A-Za-z0-9_-]{43}$/.test(key)){document.getElementById('state').textContent='Enter the local setup key.';return;}await browser.storage.local.set({localKey:key});document.getElementById('key').value='';await status();};
document.getElementById('forget').onclick=async()=>{await browser.storage.local.remove('localKey');await status();};status();
