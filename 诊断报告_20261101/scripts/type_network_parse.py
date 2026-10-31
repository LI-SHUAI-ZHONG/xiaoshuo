import os,json,re,collections,random,hashlib
from pathlib import Path
ROOT=Path(r'D:\搭建'); OUT=Path(r'D:\诊断报告_20261101'); BASE=ROOT/'02_原版资料/原始资料'
texts={n:(BASE/(n+'.txt')).read_text(encoding='utf-8-sig') for n in ['类型系统','类型连接','静态网络','动态网络','锚点网络']}
def clean(x):
 if isinstance(x,dict): return {k:clean(v) for k,v in x.items() if k!='运行层升级'}
 if isinstance(x,list): return [clean(v) for v in x]
 return x
def blocks(n):
 t=texts[n]; ms=list(re.finditer(r'^SOURCE: (.+)$',t,re.M)); out=[]
 for i,m in enumerate(ms):
  s=t[m.end():ms[i+1].start() if i+1<len(ms) else len(t)]; s=re.sub(r'^\s*=+\s*','',s)
  try: obj,end=json.JSONDecoder().raw_decode(s); err=None
  except Exception as e: obj=None;err=str(e)
  out.append(dict(name=m[1],line=t.count('\n',0,m.start())+1,data=clean(obj),error=err))
 return out
b={n:blocks(n) for n in ['类型系统','类型连接']}
net={n:json.loads(texts[n]) for n in ['静态网络','动态网络']}
a=[]
for i,l in enumerate(texts['锚点网络'].splitlines(),1):
 cols=[x.strip() for x in l.strip('|').split('|')]
 if re.match(r'^\|\s*[A-Z]+\d+(?:\.\d+)+\s*\|',l): a.append({'line':i,'id':cols[0],'name':cols[1],'content':cols[2],'condition':cols[3],'category':cols[4] if len(cols)>4 else ''})
(OUT/'tmp/type_network_parsed.json').write_text(json.dumps({'blocks':b,'net':net,'anchors':a},ensure_ascii=False),encoding='utf-8')
for n,bs in b.items():
 print(n,'blocks',len(bs))
 for z in bs:
  d=z['data']; print(z['line'],z['name'],z['error'], ('list '+str(len(d))) if isinstance(d,list) else {k:len(v) if isinstance(v,(dict,list,str)) else v for k,v in (d if isinstance(d,dict) else {}).items()})
for n,d in net.items(): print(n,{k:len(v) if isinstance(v,(dict,list)) else v for k,v in d.items()})
print('anchors',len(a),collections.Counter(x['category'] for x in a))
f=(BASE/'融合清单.json').read_bytes(); print('fusion',len(f),'nul',f.count(b'\0'),'sha256',hashlib.sha256(f).hexdigest())

