from pathlib import Path
import ast,json,re
R=Path(r'D:\搭建');O=Path(r'D:\诊断报告_20261101');P=R/'03_运行资料/脚本/执行管道.py'; t=P.read_text(encoding='utf-8-sig');tree=ast.parse(t)
def save(n,s):
 assert len(s.encode())<60000;(O/n).write_text(s,encoding='utf-8')
 with (O/'进度.md').open('a',encoding='utf-8') as f:f.write(f'\n- 已完成 `{n}`（静态取证，未执行源程序）。\n')
def chunkwrite(prefix,blocks):
 buf='# '+prefix+'\n\n';i=1
 for b in ''.join(blocks).splitlines(keepends=True):
  if len((buf+b).encode())>55000:save(f'{prefix}_{i:02}.md',buf);i+=1;buf='# '+prefix+'（续）\n\n'
  buf+=b
 save(f'{prefix}_{i:02}.md',buf)
blocks=[]
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and re.match('execute_\\d+',n.name):
  inputs=[];outputs=[]
  for c in ast.walk(n):
   if isinstance(c,ast.Call):
    name=ast.unparse(c.func)
    if name in ['require','read_json','read_text','read_bytes','first_existing']:inputs.append((c.lineno,ast.unparse(c)))
    if name in ['write_output','write_package','register_artifact'] or name.endswith('.write_text'):outputs.append((c.lineno,ast.unparse(c)[:350]))
  blocks.append(f'## {n.name}（03_运行资料/脚本/执行管道.py:{n.lineno}-{n.end_lineno}）\n\n输入读取/要求：\n\n'+''.join(f'- L{ln}: `{s}`\n' for ln,s in sorted(inputs))+'\n输出调用：\n\n'+''.join(f'- L{ln}: `{s}`\n' for ln,s in sorted(outputs))+'\n')
chunkwrite('05F_模块输入输出',blocks)
blocks=[];summary=[]
ps=list((R/'03_运行资料/配置').glob('*'))+list((R/'03_运行资料/文档/创作设计').glob('*'))+list((R/'04_参考资料').rglob('*'))+[R/'03_运行资料/docs/小说项目初始化.md',R/'03_运行资料/AGENTS.md',R/'03_运行资料/模型创作路径删除报告.md']
for p in ps:
 if not p.is_file():continue
 b=p.read_bytes();s=b.decode('utf-8-sig',errors='replace');ls=s.splitlines(); rp=p.relative_to(R).as_posix();summary.append({'path':rp,'bytes':len(b),'nul':b.count(b'\0'),'lines':len(ls)})
 if b.count(b'\0'):blocks.append(f'## {rp}:1\n\n文件字节 {len(b)}，NUL字节 {b.count(bytes([0]))}；无法从该文件核实创作内容，不把文件名视为已完成设计。\n\n');continue
 if p.suffix=='.jsonl':
  records=[json.loads(l) for l in ls if l.strip()];from collections import Counter
  blocks.append(f'## {rp}:1-{len(ls)}\n\nJSONL记录数 {len(records)}；record_type分布 {dict(Counter(str(x.get(chr(114)+chr(101)+chr(99)+chr(111)+chr(114)+chr(100)+chr(95)+chr(116)+chr(121)+chr(112)+chr(101))) for x in records))}；授权属于声明，不能据此宣称正文已消费。\n\n');continue
 if p.suffix=='.json':
  try:d=json.loads(s)
  except:continue
  def walk(v,path=''):
   if isinstance(v,dict):
    for k,x in v.items():yield from walk(x,path+'.'+k if path else k)
   elif isinstance(v,list):
    if not v:yield path,v
    for i,x in enumerate(v):yield from walk(x,f'{path}[{i}]')
   else:yield path,v
  rows=[]
  for k,v in walk(d):
   val=json.dumps(v,ensure_ascii=False); token=k.rsplit('.',1)[-1].split('[')[0];hits=[i+1 for i,l in enumerate(ls) if '"'+token+'"' in l]
   # 字段同名时列出所有出现行，避免伪称精确值位置
   rows.append(f'- `{k}`；字段候选行 {",".join(map(str,hits)) or "参照父数组"}；值：`{val[:370]}`'+('（值过长，仅示例）' if len(val)>370 else '')+'\n')
  blocks.append(f'## {rp}:1-{len(ls)}\n\n字段路径提供消歧；重复键行号均列出；值为现存数据，不等于运行已消费。\n\n'+''.join(rows)+'\n')
 else:
  blocks.append(f'## {rp}:1-{len(ls)}\n\n'+''.join(f'源片段（连续，起始字符{i}）：\n\n```text\n{s[i:i+380]}\n```\n\n' for i in range(0,len(s),380)))
chunkwrite('06A_创作配置字段与完整性',blocks)
(O/'tmp/pipeline_design_metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))


