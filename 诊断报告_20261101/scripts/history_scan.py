from pathlib import Path
import re,json,hashlib,collections,ast
R=Path(r'D:\搭建'); O=Path(r'D:\诊断报告_20261101'); T=O/'tmp';T.mkdir(exist_ok=True)
def read(p):return p.read_text(encoding='utf-8-sig',errors='replace')
def out(n,x): (T/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
logs=[]; excerpts=[]
for p in sorted((R/'05_Cline聊天记录').rglob('*.md')):
 s=read(p);ls=s.splitlines();matches=list(re.finditer(r'^## (\d+)\. (用户|Cline) · (.+)$',s,re.M));msgs=[]
 for i,m in enumerate(matches):
  body=s[m.end():matches[i+1].start() if i+1<len(matches) else len(s)]
  msgs.append(dict(id=m[1],role=m[2],date=m[3],line=s.count('\n',0,m.start())+1,chars=len(body),text=body))
 users=[m for m in msgs if m['role']=='用户']; chosen=users[:1]+users[-2:]
 scored=sorted(users,key=lambda x:sum(x['text'].count(w) for w in ['问题','不满意','机械','模板','没有','失败','重复','质量']),reverse=True)[:2]
 chosen={m['id']:m for m in chosen+scored}.values()
 a=[m for m in msgs if m['role']=='Cline']; chosen=list(chosen)+(a[-1:] if a else [])
 excerpts.append('\n## '+p.name+'\n'+'\n'.join(f"L{m['line']} {m['role']} #{m['id']} {m['text'][:1800]}" for m in chosen))
 logs.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,chars=len(s),lines=len(ls),messages=len(msgs),users=len(users),cline=len(a),sample_ids=[m['id'] for m in chosen],sample_chars=sum(min(len(m['text']),1800) for m in chosen),structure=[{k:v for k,v in m.items() if k!='text'} for m in msgs]))
out('history_cline_structure.json',logs);(T/'history_cline_samples.txt').write_text('\n'.join(excerpts),encoding='utf8')
runs=[]
for p in sorted((R/'03_运行资料/正文/运行').rglob('*.md')):
 s=read(p);runs.append(dict(id=p.parent.name,path=str(p.relative_to(R)),bytes=p.stat().st_size,chars=len(s),nonspace=len(re.sub(r'\s','',s)),han=len(re.findall(r'[\u4e00-\u9fff]',s)),lines=len(s.splitlines()),sha256=hashlib.sha256(s.encode()).hexdigest(),heading=[(i,l) for i,l in enumerate(s.splitlines(),1) if l.startswith('#')],sample=[(i,l[:200]) for i,l in enumerate(s.splitlines(),1) if l.strip() and not l.startswith('#')][:2]))
out('history_runs.json',runs)
acc=R/'01_搭建框架_ACCOS';progress=json.loads(read(acc/'后续执行/进度.json'));out('history_progress.json',progress)
fw=[]
for p in sorted((R/'07_新框架_v0/src').rglob('*.py')):
 s=read(p);tree=ast.parse(s);fw.append(dict(path=str(p.relative_to(R)),lines=len(s.splitlines()),symbols=[dict(name=n.name,line=n.lineno,kind=type(n).__name__) for n in ast.walk(tree) if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]))
out('history_newframework.json',fw)
print('logs',len(logs),'messages',sum(x['messages'] for x in logs),'chars',sum(x['chars'] for x in logs),'sample chars',sum(x['sample_chars'] for x in logs));print('runs',len(runs),'unique',len(set(x['sha256'] for x in runs)));print('progress',collections.Counter(x['status'] for x in progress['steps']))
