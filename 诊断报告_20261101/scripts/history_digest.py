exec(open(r'D:\诊断报告_20261101\scripts\history_scan.py',encoding='utf-8-sig').read().split('logs=[]')[0])
for p in sorted((R/'05_Cline聊天记录').rglob('*.md')):
 s=read(p); ms=list(re.finditer(r'^## (\d+)\. (用户|Cline) · (.+)$',s,re.M));arr=[]
 for i,m in enumerate(ms):
  b=s[m.end():ms[i+1].start() if i+1<len(ms) else len(s)];b=re.sub(r'<[^>]+>','',b);b=re.sub(r'\s+',' ',b).strip();arr.append((m[2],s.count('\n',0,m.start())+1,b))
 u=[x for x in arr if x[0]=='用户'];a=[x for x in arr if x[0]=='Cline'];print('\n'+p.name)
 for x in (u[:1]+u[-2:]+a[-1:]):print(x[0],x[1],x[2][:580])
