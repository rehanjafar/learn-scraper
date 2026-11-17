importScripts('policy.js','cs135-policy.js','background.js');
chrome.alarms.onAlarm.addListener(a=>{if(a.name==='waterloo-bridge')tick();});
const schedule=()=>chrome.alarms.create('waterloo-bridge',{periodInMinutes:0.5});
chrome.runtime.onInstalled.addListener(schedule);
chrome.runtime.onStartup.addListener(schedule);
schedule();
