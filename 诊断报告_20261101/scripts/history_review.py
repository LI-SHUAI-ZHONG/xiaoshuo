exec(open(r'D:\诊断报告_20261101\scripts\history_scan.py',encoding='utf-8-sig').read().split('logs=[]')[0])
a=[]
for p in sorted((R/'05_Cline聊天记录').rglob('*.md')):
 s=read(p);ms=list(re.finditer(r'^## (\d+)\. (用户|Cline) · (.+)$',s,re.M));arr=[]
 for i,m in enumerate(ms):
  b=s[m.end():ms[i+1].start() if i+1<len(ms) else len(s)];arr.append(dict(id=m[1],role=m[2],line=s.count('\n',0,m.start())+1,text=b))
 u=[x for x in arr if x['role']=='用户'];c=[x for x in arr if x['role']=='Cline'];sel={x['id']:x for x in u[:1]+u[-1:]+c[-1:]}.values()
 for x in sel:x['text']=x['text'][:300]
 a.append(dict(file=p.name,samples=list(sel)))
out('history_reviewed_samples.json',a)
for x in a:
 print(x['file']);
 for v in x['samples']:print(v['line'],v['role'],re.sub(r'\s+',' ',v['text']))
