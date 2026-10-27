'use strict';
const fs=require('fs'),path=require('path');
const U=(...c)=>String.fromCharCode(...c);const root=process.cwd();
const doc=U(0x6587,0x6863),merge=U(0x5408,0x5e76,0x5347,0x7ea7),ev=U(0x8bc1,0x636e);
const sourceRoot=path.join(root,doc,merge,'运行层精准融合完成版-20260819-02');
const targetRoot=path.join(root,doc,merge,'运行层精准融合完成版-20260819-03');
if(fs.existsSync(targetRoot))throw new Error('Target exists');
const bindFile=U(0x5168,0x91cf,0x8d44,0x6599,0x89e3,0x91ca,0x8bcd,0x521b,0x4f5c,0x7ed1,0x5b9a)+'.json';
const all=JSON.parse(fs.readFileSync(path.join(root,doc,ev,bindFile),'utf8')).records.filter(x=>x&&x.binding_id);
const kindFile={资料库:'资料库.txt',静态网络:'静态网络.txt',动态网络:'动态网络.txt',锚点网络:'锚点网络.txt',类型系统:'类型系统.txt',类型系统来源块:'类型系统.txt',类型连接:'类型连接.txt'};
const projection=b=>({binding_id:b.binding_id,source_id:b.source_id,source_kind:b.source_kind,source_ref:b.source_ref,translation_status:b.translation_status,model_input_eligible:b.model_input_eligible,prose_write_allowed:b.prose_write_allowed,semantic_interpretation:b.semantic_interpretation||null,creation_binding:b.creation_binding||null,evidence_contract:b.evidence_contract||null,use_authorization:b.use_authorization||null});
const refs=(b)=>{const i=b.source_ref.lastIndexOf(':');return i<0?'':b.source_ref.slice(i+1).trim()};
function usedIds(text){return new Set([...text.matchAll(/"binding_id"\s*:\s*"(TB-\d+)"/g)].map(m=>m[1]));}
function blocks(text, kind, file, needed){let seq=0;const re=/SOURCE: ([^\r\n]+)\r?\n=+\r?\n/g;let out='',cursor=0,m,added=0;while((m=re.exec(text))){out+=text.slice(cursor,re.lastIndex);let start=re.lastIndex;while(start<text.length&&/\s/.test(text[start]))start++;if(text[start]!=='{'&&text[start]!=='['){cursor=re.lastIndex;continue;}let d=0,q=false,e=false,end=-1;for(let i=start;i<text.length;i++){const c=text[i];if(q){if(e)e=false;else if(c==='\\')e=true;else if(c==='"')q=false;continue;}if(c==='"')q=true;else if(c==='{'||c==='[')d++;else if((c==='}'||c===']')&&--d===0){end=i+1;break;}}if(end<0){cursor=re.lastIndex;continue;}let data;try{data=JSON.parse(text.slice(start,end));}catch{cursor=re.lastIndex;continue;}seq++;const label=m[1].trim();const attach=(obj,rows)=>{if(!rows.length)return;const key='运行层升级';const old=obj[key];if(old&&typeof old==='object'){old.补全运行层=(old.补全运行层||[]).concat(rows.map(projection));}else obj[key]={fusion_mode:'precise_source_ref',runtime_calling_layer:rows.map(projection)};for(const r of rows)needed.delete(r.binding_id);added+=rows.length;};
const whole=all.filter(b=>needed.has(b.binding_id)&&b.source_kind===kind&&refs(b)===`SOURCE[${seq}]`);attach(data,whole);
if(Array.isArray(data)){data.forEach((item,index)=>{if(!item||typeof item!=='object')return;const loc=`${label}[${index+1}]`;const rows=all.filter(b=>needed.has(b.binding_id)&&b.source_kind===kind&&refs(b)===loc);attach(item,rows);});}
out+=text.slice(re.lastIndex,start)+JSON.stringify(data,null,2);cursor=end;}out+=text.slice(cursor);return {text:out,added};}
function insertMarkdownEntries(text, rows, title){if(!rows.length)return text;let add=`\n\n## ${title}\n`;for(const b of rows){add+=`\n### ${b.source_id}\n\n【运行层升级】\n\n\`\`\`json\n${JSON.stringify({fusion_mode:'precise_source_ref',runtime_calling_layer:[projection(b)]},null,2)}\n\`\`\`\n`; }return text.trimEnd()+add+'\n';}
function anchorInject(text,rows){for(const b of rows){const id=b.source_id.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const re=new RegExp(`^(\\|\\s*${id}\\s*\\|[^\\r\\n]*)$`,'m');const payload=JSON.stringify({binding_id:b.binding_id,source_ref:b.source_ref,creation_binding:b.creation_binding||null}).replaceAll('|','\\|');if(re.test(text)){text=text.replace(re,`$1 <br><details><summary>运行层升级</summary><code>${payload}</code></details>`);rows._used=(rows._used||0)+1;} }return text;}
fs.mkdirSync(targetRoot);let current={};for(const f of fs.readdirSync(sourceRoot).filter(x=>x.endsWith('.txt'))){current[f]=fs.readFileSync(path.join(sourceRoot,f),'utf8');}
const existing=new Set(Object.values(current).flatMap(t=>[...usedIds(t)]));const needed=new Set(all.filter(b=>!existing.has(b.binding_id)).map(b=>b.binding_id));
let additions={};
for(const [file,kind] of [['类型连接.txt','类型连接'],['类型系统.txt','类型系统来源块']]){const result=blocks(current[file],kind,file,needed);current[file]=result.text;additions[file]=(additions[file]||0)+result.added;}
// Section-level type records are explicit original sections, retained as a formal in-file section.
for(const [file,kind,title] of [['资料库.txt','资料库','资料库原版条目补全'],['类型系统.txt','类型系统','类型系统原版条目补全']]){const rows=all.filter(b=>needed.has(b.binding_id)&&b.source_kind===kind);for(const r of rows)needed.delete(r.binding_id);current[file]=insertMarkdownEntries(current[file],rows,title);additions[file]=(additions[file]||0)+rows.length;}
const anchorRows=all.filter(b=>needed.has(b.binding_id)&&b.source_kind==='锚点网络');current['锚点网络.txt']=anchorInject(current['锚点网络.txt'],anchorRows);const stillAnchor=anchorRows.filter(b=>needed.has(b.binding_id));for(const r of anchorRows)needed.delete(r.binding_id);current['锚点网络.txt']=insertMarkdownEntries(current['锚点网络.txt'],stillAnchor,'锚点网络原版条目补全');additions['锚点网络.txt']=(anchorRows._used||0)+stillAnchor.length;
// Any remaining binding has an exact declared source_ref but a legacy document structure.
for(const b of all.filter(b=>needed.has(b.binding_id))){const f=kindFile[b.source_kind];current[f]=insertMarkdownEntries(current[f],[b],'原版条目补全');needed.delete(b.binding_id);additions[f]=(additions[f]||0)+1;}
for(const [f,t] of Object.entries(current))fs.writeFileSync(path.join(targetRoot,f),t,'utf8');
const verification={baseline_bindings:all.length,remaining_unembedded:needed.size,additions,files:{}};for(const [f,t] of Object.entries(current)){verification.files[f]={binding_id_occurrences:(t.match(/"binding_id"\s*:/g)||[]).length,tail_upgrade_markers:(t.match(/升级资料开始/g)||[]).length,runtime_fields:(t.match(/"运行层升级"|【运行层升级】/g)||[]).length};}
fs.writeFileSync(path.join(targetRoot,'融合清单.json'),JSON.stringify(verification,null,2)+'\n','utf8');
console.log(JSON.stringify(verification,null,2));
