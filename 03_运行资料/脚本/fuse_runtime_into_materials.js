/* Build a new usable material edition. It does not modify the chosen backup. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const U = (...c) => String.fromCharCode(...c);
const root = process.cwd();
const DOC = U(0x6587,0x6863), MERGE = U(0x5408,0x5e76,0x5347,0x7ea7), EVIDENCE = U(0x8bc1,0x636e);
const baseRoot = path.join(root,DOC,MERGE,'material-absorption-20260818T054129Z');
const backup = fs.readdirSync(baseRoot,{withFileTypes:true}).find(x=>x.isDirectory()).name;
const sourceRoot = path.join(baseRoot,backup);
const outRoot = path.join(root,DOC,MERGE,'运行层精准融合完成版-20260819-02');
if(fs.existsSync(outRoot)) throw new Error('Output already exists: '+outRoot);
const marker = `===== ${U(0x5206,0x7c7b,0x5347,0x7ea7,0x8d44,0x6599)}${U(0x5f00,0x59cb)} =====`;
const bindingFile=U(0x5168,0x91cf,0x8d44,0x6599,0x89e3,0x91ca,0x8bcd,0x521b,0x4f5c,0x7ed1,0x5b9a)+'.json';
const bindings=JSON.parse(fs.readFileSync(path.join(root,DOC,EVIDENCE,bindingFile),'utf8')).records.filter(x=>x&&typeof x.binding_id==='string');
if(bindings.length!==13345) throw new Error('Binding baseline count mismatch.');
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
const cleanBase = text => {
  const markerPositions = [text.indexOf(marker)];
  const tailPattern = /^={3,}.*升级资料开始.*$/gm;
  for (let match; (match = tailPattern.exec(text)); ) markerPositions.push(match.index);
  const positions = markerPositions.filter((position) => position >= 0);
  const firstTail = positions.length ? Math.min(...positions) : -1;
  return firstTail >= 0 ? text.slice(0, firstTail).replace(/\s+$/, '') + '\n' : text;
};
function locator(ref){if(typeof ref!=='string')return null;let m=ref.match(/['"]locator['"]\s*:\s*['"]([^'"]+)/);if(m)return m[1];let p=ref.lastIndexOf(':');return p>=0?ref.slice(p+1).trim():null;}
function project(b){return {binding_id:b.binding_id,source_id:b.source_id,source_kind:b.source_kind,source_ref:b.source_ref,translation_status:b.translation_status,model_input_eligible:b.model_input_eligible,prose_write_allowed:b.prose_write_allowed,semantic_interpretation:b.semantic_interpretation||null,creation_binding:b.creation_binding||null,evidence_contract:b.evidence_contract||null,use_authorization:b.use_authorization||null};}
const byKindId=new Map(), byKindLocator=new Map();
for(const b of bindings){let k=`${b.source_kind}\0${b.source_id}`;if(!byKindId.has(k))byKindId.set(k,[]);byKindId.get(k).push(project(b));let l=locator(b.source_ref);if(l){k=`${b.source_kind}\0${l}`;if(!byKindLocator.has(k))byKindLocator.set(k,[]);byKindLocator.get(k).push(project(b));}}
function parseTopEvidence(text){const records=[];for(let p=text.indexOf(marker);p>=0;p=text.indexOf(marker,p+marker.length)){let s=text.indexOf('{',p);if(s<0)continue;let d=0,q=false,e=false;for(let i=s;i<text.length;i++){const c=text[i];if(q){if(e)e=false;else if(c==='\\')e=true;else if(c==='"')q=false;continue;}if(c==='"')q=true;else if(c==='{')d++;else if(c==='}'&&--d===0){try{const o=JSON.parse(text.slice(s,i+1)); if(o&&typeof o.source_id==='string')records.push(o);}catch{}break;}}}return records;}
const sourceEvidence=new Map();
for(const f of fs.readdirSync(sourceRoot)){const raw=fs.readFileSync(path.join(sourceRoot,f),'utf8');for(const e of parseTopEvidence(raw)){const k=`${f}\0${e.source_id}`;if(!sourceEvidence.has(k))sourceEvidence.set(k,[]);sourceEvidence.get(k).push(e);}}
function upgrade(kind,file,id,extraLocator){const runtime=[...(byKindId.get(`${kind}\0${id}`)||[]),...(extraLocator?(byKindLocator.get(`${kind}\0${extraLocator}`)||[]):[])];const evidence=sourceEvidence.get(`${file}\0${id}`)||[];if(!runtime.length&&!evidence.length)return null;return {fusion_mode:'precise_source_binding',canonical_source_id:id,source_locator:extraLocator||null,runtime_calling_layer:runtime,tail_upgrade_evidence:evidence};}
function addToObject(obj,kind,file,id,loc){const u=upgrade(kind,file,id,loc);if(u)obj['运行层升级']=u;return !!u;}
function balanced(text,start){let d=0,q=false,e=false;for(let i=start;i<text.length;i++){const c=text[i];if(q){if(e)e=false;else if(c==='\\')e=true;else if(c==='"')q=false;continue;}if(c==='"')q=true;else if(c==='{'||c==='[')d++;else if((c==='}'||c===']')&&--d===0)return i+1;}return -1;}
function deepInject(value,kind,file){let count=0;if(Array.isArray(value)){for(const x of value)count+=deepInject(x,kind,file);return count;}if(!value||typeof value!=='object')return count;const ids=[value.id,value.stable_id,value.dynamic_combination_id,value.type_id,value.anchor_id].filter(x=>typeof x==='string');for(const id of ids){if(addToObject(value,kind,file,id)) {count++;break;}}for(const x of Object.values(value))count+=deepInject(x,kind,file);return count;}
function fuseJsonFile(file,kind,raw){let base=cleanBase(raw);let prefix='', suffix='', payload=base;const fence=base.indexOf('```json');if(fence>=0){const s=base.indexOf('{',fence);const e=balanced(base,s);prefix=base.slice(0,s);payload=base.slice(s,e);suffix=base.slice(e).replace(/```[\s\S]*$/,'');}
const data=JSON.parse(payload);let count=0;
if(kind===U(0x9759,0x6001,0x7f51,0x7edc)){for(const c of data.connections||[]){const id=`STATIC:${c.source}->${c.target}#${(data.connections.indexOf(c)+1)}`;if(addToObject(c,kind,file,id,`connections[${data.connections.indexOf(c)}]`))count++;}}
else if(kind===U(0x52a8,0x6001,0x7f51,0x7edc)){const list=data['动态网络连接_完整版']?.['连接列表']||[];for(const c of list)if(addToObject(c,kind,file,c.id))count++;}
else count=deepInject(data,kind,file);
return {text:`${prefix}${JSON.stringify(data,null,2)}${suffix}`.replace(/^.*?```json\s*/s,'').trimEnd()+'\n',count};}
function fuseBlockDocuments(file,kind,raw){const base=cleanBase(raw);let cursor=0,out='',count=0;const re=/SOURCE: ([^\r\n]+)\r?\n=+\r?\n/g;let m;while((m=re.exec(base))){out+=base.slice(cursor,re.lastIndex);let start=re.lastIndex;while(start<base.length&&/\s/.test(base[start]))start++;if(base[start]!=='{'&&base[start]!=='['){cursor=re.lastIndex;continue;}let end=balanced(base,start);if(end<0){cursor=re.lastIndex;continue;}let data;try{data=JSON.parse(base.slice(start,end));}catch{cursor=re.lastIndex;continue;}count+=deepInject(data,kind,file);const sourceId=`TYPE-SOURCE:${Math.max(1,[...base.slice(0,m.index).matchAll(/SOURCE: /g)].length+1)}`;const sourceUpgrade=upgrade(kind,file,sourceId,`${m[1]}[${sourceId.slice(12)}]`);if(sourceUpgrade){if(Array.isArray(data))data={原始条目:data,'运行层升级':sourceUpgrade};else data['运行层升级']=data['运行层升级']||sourceUpgrade;count++;}out+=base.slice(re.lastIndex,start)+JSON.stringify(data,null,2);cursor=end;}out+=base.slice(cursor);return {text:out.trimEnd()+'\n',count};}
function fuseLibrary(raw){let text=cleanBase(raw),count=0;const matches=[...text.matchAll(/^###\s+(.+)$/gm)];for(let i=matches.length-1;i>=0;i--){const m=matches[i],id=m[1].trim();const u=upgrade(U(0x8d44,0x6599,0x5e93),'资料库.txt',id,id);if(!u)continue;const next=i+1<matches.length?matches[i+1].index:text.length;const end=text.lastIndexOf('---',next);const insertAt=end>m.index?end:next;text=text.slice(0,insertAt)+`\n【运行层升级】\n\n\`\`\`json\n${JSON.stringify(u,null,2)}\n\`\`\`\n\n`+text.slice(insertAt);count++;}return {text,count};}
function fuseAnchors(raw){let text=cleanBase(raw),count=0;const lines=text.split(/\r?\n/),out=[];for(const line of lines){out.push(line);const m=line.match(/^\|\s*([A-Z]\d+(?:\.\d+)?)\s*\|/);if(!m)continue;const id=m[1],u=upgrade(U(0x951a,0x70b9,0x7f51,0x7edc),'锚点网络.txt',id,id);if(u){out.push(`| ${id} 运行层升级 | \`\`\`json ${JSON.stringify(u)} \`\`\` | 精确绑定 | 已融合 |`);count++;}}return {text:out.join('\n')+'\n',count};}
fs.mkdirSync(outRoot,{recursive:false});const manifest={schema_version:'runtime-layer-inplace-fused-material-1.0',generated_at:new Date().toISOString(),baseline:'文档/合并升级/material-absorption-20260818T054129Z/当前资料备份',original_backup_modified:false,binding_count:bindings.length,files:{},rules:['删除分类升级资料尾部块','运行层嵌入原版条目或原版JSON对象','仅以binding_id/source_id/source_ref精确定位','不使用文本相似度猜测']};
for(const file of fs.readdirSync(sourceRoot).filter(x=>x.endsWith('.txt'))){const raw=fs.readFileSync(path.join(sourceRoot,file),'utf8');let r;if(file==='资料库.txt')r=fuseLibrary(raw);else if(file==='锚点网络.txt')r=fuseAnchors(raw);else if(file==='静态网络.txt')r=fuseJsonFile(file,U(0x9759,0x6001,0x7f51,0x7edc),raw);else if(file==='动态网络.txt')r=fuseJsonFile(file,U(0x52a8,0x6001,0x7f51,0x7edc),raw);else if(file==='类型系统.txt')r=fuseBlockDocuments(file,U(0x7c7b,0x578b,0x7cfb,0x7edf),raw);else if(file==='类型连接.txt')r=fuseBlockDocuments(file,U(0x7c7b,0x578b,0x8fde,0x63a5),raw);else r={text:cleanBase(raw),count:0};fs.writeFileSync(path.join(outRoot,file),r.text,'utf8');manifest.files[file]={baseline_bytes:Buffer.byteLength(raw),fused_bytes:Buffer.byteLength(r.text),tail_marker_removed:cleanBase(raw).length < raw.length,inplace_fused_item_count:r.count,sha256:sha(r.text)};}
fs.writeFileSync(path.join(outRoot,'融合清单.json'),JSON.stringify(manifest,null,2)+'\n','utf8');
fs.writeFileSync(path.join(outRoot,'README.md'),'# 运行层精准融合完成版\n\n本目录是可直接使用的新资料版本。每份文件均以指定的当前资料备份为基线，删除了原文件中从“分类升级资料开始”起的无序尾部块，并将运行层内容写入其精确对应的原版条目或 JSON 对象的“运行层升级”字段。\n\n原始当前资料备份未被修改。\n','utf8');
console.log(JSON.stringify(manifest,null,2));
