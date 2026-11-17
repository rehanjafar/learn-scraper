/* Exact course scope. No arbitrary URLs, query strings, encoded paths or parent traversal. */
globalThis.CS135Policy=Object.freeze({
 kind(path){
  if(typeof path!=='string'||path.length>250||/[\r\n%\\?#]/.test(path)||path.split('/').some(p=>p==='.'||p==='..'))return null;
  if(/^\/cs135\/page\/(?:index\.html|calendar\/index\.html|slides\/index\.html|assess\/index\.html|assign\/index\.html)$/.test(path))return 'page';
  if(/^\/cs135\/file\/[A-Za-z0-9][A-Za-z0-9_./-]{0,180}\.pdf$/.test(path))return 'file';
  return null;
 },
 url(path){if(!this.kind(path))throw Error('Blocked CS135 path');return 'https://student.cs.uwaterloo.ca/~cs135/'+path.replace(/^\/cs135\/(page|file)\//,'');}
});
