from pathlib import Path
import ast,json,hashlib,re,collections
R=Path(r'D:\搭建'); O=Path(r'D:\诊断报告_20261101'); S=R/'03_运行资料/脚本'
def rel(p):return p.relative_to(R).as_posix()
def read(p):return p.read_text(encoding='utf-8-sig')
def emit_parts(prefix,blocks):
 part=1;buf='# '+prefix+'\n\n静态扫描；未导入或运行被审计代码。行号按 Python splitlines 计算。\n\n'
 for block in blocks:
  if len((buf+block).encode())>56000:
   save(f'{prefix}_{part:02}.md',buf);part+=1;buf='# '+prefix+'（续）\n\n'
  buf+=block
 save(f'{prefix}_{part:02}.md',buf)
def save(name,text):
 assert len(text.encode())<60000
 (O/name).write_text(text,encoding='utf-8')
 with (O/'进度.md').open('a',encoding='utf-8') as f:f.write(f'\n- 已完成 `{name}`（只读静态取证）。\n')
rows=[];funcs=[];gates=[];cli=[];prompts=[];metrics=[]
for p in sorted(S.iterdir()):
 if not p.is_file():continue
 b=p.read_bytes();t=b.decode('utf-8-sig',errors='replace');ls=t.splitlines(); tree=None;err=''
 if p.suffix=='.py' or '.py.before' in p.name:
  try:tree=ast.parse(t)
  except Exception as e:err=str(e)
 kind='历史备份，不作当前执行入口' if '.before' in p.name else '测试，保留回归价值' if p.name.startswith('test_') or p.name.startswith('_step') else '治理/修复工具，迁移前隔离副作用' if any(x in p.name for x in ['升级','修复','重建','融合','补全','补齐','搬','回写','冻结']) else '运行/校验工具，保留契约并拆分职责'
 fs=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))] if tree else []
 metrics.append({'path':rel(p),'bytes':len(b),'lines':len(ls),'nul':b.count(b'\0'),'sha256':hashlib.sha256(b).hexdigest(),'functions':len(fs),'parse_error':err,'classification':kind})
 names=', '.join(f'{n.name}@{n.lineno}' for n in fs[:12])
 rows.append(f'| `{rel(p)}:1-{len(ls)}` | {len(b)} / {len(ls)} / {len(fs)} | {kind} | {err or names or "非Python/无函数"} |\n')
 for n in fs:
  calls=sorted({ast.unparse(c.func) for c in ast.walk(n) if isinstance(c,ast.Call)})
  sig=ast.unparse(n.args)
  funcs.append(f'## {rel(p)}:{n.lineno}-{n.end_lineno} `{n.name}`\n\n- 输入签名：`{sig}`\n- 返回类型：`{ast.unparse(n.returns) if n.returns else "未标注"}`\n- 直接调用（静态名，不代表运行成功）：'+', '.join('`'+x+'`' for x in calls)+'\n\n')
 if tree and p.suffix=='.py':
  for n in ast.walk(tree):
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument':
    cli.append(f'- `{rel(p)}:{n.lineno}-{n.end_lineno}`：`{ast.unparse(n).replace("|","/ ")}`\n')
   if isinstance(n,ast.Call) and ast.unparse(n.func)=='check':
    args=[ast.unparse(x) for x in n.args[:4]]
    gates.append(f'- `{rel(p)}:{n.lineno}-{n.end_lineno}`：'+ '；'.join(args)+'；'+', '.join(ast.unparse(k) for k in n.keywords)+'\n')
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and 'prompt' in n.name.lower():
    source=ast.get_source_segment(t,n)
    # 每段严格不超过380字符，保留完整源顺序；分段仅为引用长度约束
    chunks=[source[i:i+380] for i in range(0,len(source),380)]
    prompts.append(f'## `{rel(p)}:{n.lineno}-{n.end_lineno}`\n\n完整函数源，连续片段拼回即可恢复；不补造系统提示词。\n\n'+''.join(f'片段 {i+1}/{len(chunks)}\n\n```python\n{c}\n```\n\n' for i,c in enumerate(chunks)))
emit_parts('05A_脚本目录',['| 路径与范围 | 字节/行/函数 | 分类与处置建议 | 函数定位/异常 |\n|---|---:|---|---|\n']+rows)
emit_parts('05B_全量函数调用表',funcs)
emit_parts('05C_命令参数',cli)
emit_parts('05D_编辑门条件',gates)
emit_parts('05E_完整提示词',prompts)
(O/'tmp/pipeline_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(metrics),'python':sum(x['path'].endswith('.py') for x in metrics),'functions':sum(x['functions'] for x in metrics),'parse_errors':[x for x in metrics if x['parse_error']],'nul_files':[x for x in metrics if x['nul']],'generated':len(list(O.glob('05*.md')))},ensure_ascii=False))
