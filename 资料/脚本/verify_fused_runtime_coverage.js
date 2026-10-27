'use strict';
const fs=require('fs'),path=require('path');
const U=(...c)=>String.fromCharCode(...c);const root=process.cwd();
const doc=U(0x6587,0x6863),merge=U(0x5408,0x5e76,0x5347,0x7ea7),ev=U(0x8bc1,0x636e);
const bindFile=U(0x5168,0x91cf,0x8d44,0x6599,0x89e3,0x91ca,0x8bcd,0x521b,0x4f5c,0x7ed1,0x5b9a)+'.json';
const bindings=JSON.parse(fs.readFileSync(path.join(root,doc,ev,bindFile),'utf8')).records.filter(x=>x&&x.binding_id);
const out=fs.readdirSync(path.join(root,doc,merge),{withFileTypes:true}).find(x=>x.isDirectory()&&x.name.includes('运行层精准融合完成版-20260819-03')).name;
const seen=new Set();const perFile={};for(const f of fs.readdirSync(path.join(root,doc,merge,out)).filter(x=>x.endsWith('.txt'))){const s=fs.readFileSync(path.join(root,doc,merge,out,f),'utf8');for(const m of s.matchAll(/"binding_id"\s*:\s*"(TB-\d+)"/g))seen.add(m[1]);perFile[f]={tail_markers:(s.match(/升级资料开始/g)||[]).length,runtime_fields:(s.match(/"运行层升级"|【运行层升级】/g)||[]).length,binding_ids:(s.match(/"binding_id"\s*:/g)||[]).length};}
const missing=bindings.filter(b=>!seen.has(b.binding_id));const groups={};for(const b of missing){groups[b.source_kind]=(groups[b.source_kind]||[]);groups[b.source_kind].push({binding_id:b.binding_id,source_id:b.source_id,source_ref:b.source_ref});}
console.log(JSON.stringify({baseline:bindings.length,embedded_binding_ids:seen.size,missing:missing.length,perFile,missing_by_kind:Object.fromEntries(Object.entries(groups).map(([k,v])=>[k,{count:v.length,samples:v.slice(0,5)}]))},null,2));
