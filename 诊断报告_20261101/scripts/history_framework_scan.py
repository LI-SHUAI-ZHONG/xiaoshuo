from pathlib import Path
import json,re,ast,collections
R=Path(r'D:\搭建');O=Path(r'D:\诊断报告_20261101');T=O/'tmp'; A=R/'01_搭建框架_ACCOS'
def read(p):return p.read_text(encoding='utf-8-sig',errors='replace')
def dump(n,x):(T/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
data=[]
for name,ranges in [('创作搭建.txt',[(1,40),(12811,12921),(53881,54051)]),('改进资料.txt',[(1,40),(11321,11481)])]:
 p=A/name;s=read(p);ls=s.splitlines();heads=[{'line':i,'text':l[:180]} for i,l in enumerate(ls,1) if re.match(r'^(?:#{1,6}\s|第[一二三四五六七八九十百0-9]+[步骤阶段层]|[一二三四五六七八九十]+[、．]|\d+[.、]\s)',l)]
 chars=sum(len('\n'.join(ls[a-1:b])) for a,b in ranges);data.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,chars=len(s),lines=len(ls),headings=heads,reviewed_ranges=ranges,reviewed_chars=chars,unread_ratio=1-chars/len(s)))
dump('history_source_docs_structure.json',data)
prog=json.loads(read(A/'后续执行/进度.json'));steps=[]
for p in sorted((A/'执行').glob('*.md')):
 n=int(p.name[:2]);
 if n:steps.append(dict(step=n,title=p.stem[3:],status='历史PASS' if n<23 else '历史PARTIAL',path=str(p.relative_to(R))))
for x in prog['steps']:steps.append(dict(step=x['step'],title=x['title'],status=x['status'],path='01_搭建框架_ACCOS/后续执行/'+x['file']))
workflow=read(A/'后续执行/06_完整小说创作工作流.md');nodes=[dict(line=i,text=l) for i,l in enumerate(workflow.splitlines(),1) if re.match(r'\| N\d\d ',l)]
new=R/'07_新框架_v0';schema=read(new/'src/nw/schema.py');tables=re.findall(r'CREATE TABLE (\w+)',schema);tests=[]
for p in sorted((new/'tests').glob('*.py')):
 tree=ast.parse(read(p));tests.append(dict(path=str(p.relative_to(R)),tests=[dict(name=n.name,line=n.lineno) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')]))
dump('history_framework_counts.json',dict(steps=steps,status_counts=dict(collections.Counter(x['status'] for x in steps)),nodes=nodes,tables=tables,test_files=len(tests),test_functions=sum(len(x['tests']) for x in tests),tests=tests))
print([(x['path'],x['lines'],x['chars'],x['reviewed_chars'],x['unread_ratio']) for x in data]);print(len(steps),len(nodes),len(tables),len(tests),sum(len(x['tests']) for x in tests))
