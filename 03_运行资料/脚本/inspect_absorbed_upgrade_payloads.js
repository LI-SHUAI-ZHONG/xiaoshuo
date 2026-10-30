'use strict';
const fs = require('fs');
const path = require('path');
const U = (...c) => String.fromCharCode(...c);
const root = process.cwd();
const mergeRoot = path.join(root, U(0x6587,0x6863), U(0x5408,0x5e76,0x5347,0x7ea7));
const batch = 'material-absorption-20260818T054129Z';
const backup = fs.readdirSync(path.join(mergeRoot, batch), {withFileTypes:true}).find((x) => x.isDirectory()).name;
const marker = U(0x5206,0x7c7b,0x5347,0x7ea7,0x8d44,0x6599,0x5f00,0x59cb);
function parseTopBlocks(text) {
  const out=[];
  for(let p=text.indexOf(marker); p>=0; p=text.indexOf(marker,p+marker.length)) {
    const start=text.indexOf('{',p); if(start<0) continue;
    let d=0,q=false,e=false;
    for(let i=start;i<text.length;i++) { const x=text[i]; if(q){if(e)e=false;else if(x==='\\')e=true;else if(x==='"')q=false;continue} if(x==='"')q=true;else if(x==='{')d++;else if(x==='}'&&--d===0){try{out.push(JSON.parse(text.slice(start,i+1)))}catch{};break} }
  }
  return out;
}
function walk(value, output, seen = new WeakSet()) {
  if (!value || typeof value !== 'object') return;
  if (seen.has(value)) return;
  seen.add(value);
  if (typeof value.binding_id === 'string' || typeof value.upgrade_id === 'string' || Array.isArray(value.changes) || Object.hasOwn(value, 'candidate_value')) output.push(value);
  for (const child of Object.values(value)) walk(child, output, seen);
}
const stats={}; const samples=[];
for(const file of fs.readdirSync(path.join(mergeRoot,batch,backup))) {
  const text=fs.readFileSync(path.join(mergeRoot,batch,backup,file),'utf8');
  const tops=parseTopBlocks(text); let nested=[]; for(const top of tops) walk(top,nested);
  const keyCounts={}; for(const r of nested){for(const key of Object.keys(r))keyCounts[key]=(keyCounts[key]||0)+1; if(samples.length<30 && (r.binding_id||r.upgrade_id||r.candidate_value)) samples.push({file, keys:Object.keys(r), record:r});}
  stats[file]={top_blocks:tops.length,nested_records:nested.length,key_counts:Object.entries(keyCounts).sort((a,b)=>b[1]-a[1]).slice(0,35)};
}
console.log(JSON.stringify({stats,samples},null,2));
