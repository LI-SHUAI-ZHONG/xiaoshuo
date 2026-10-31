from pathlib import Path
import json,zipfile,os,hashlib
O=Path('D:/诊断报告_20261101');R=Path('D:/搭建');d=json.loads((O/'tmp/type_network_parsed.json').read_text(encoding='utf8'));per=[]
def collect(x,a):
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='not_guaranteed':a.extend(z for z in(v if isinstance(v,list)else[v])if isinstance(z,str))
   else:collect(v,a)
 elif isinstance(x,list):
  for v in x:collect(v,a)
for b in d['blocks']['类型连接']:
 a=[];collect(b['data'],a)
 if a:per.append((b['name'],b['line'],len(a),len(set(a))))
with(O/'03a_规则与组合追踪.md').open('a',encoding='utf8')as h:
 h.write('\n\n## 按SOURCE复算不能保证字段\n\n|SOURCE|行|出现|精确去重|\n|---|---:|---:|---:|\n')
 for n,l,t,u in per:h.write(f'|{n}|{l}|{t}|{u}|\n')
reports=sorted(p for p in O.iterdir()if p.is_file()and p.name not in ['进度.md','交付清单.md']);assert all(p.stat().st_size<=60000 for p in reports)
rows=[json.loads(l)for l in(O/'09_抽样数据.jsonl').read_text(encoding='utf8').splitlines()];assert len(rows)==120
assert all(len(x['excerpt'])<=400 for x in rows)
inv=json.loads((O/'tmp/core_inventory.json').read_text(encoding='utf8'));changed=[x['path']for x in inv if x['path']!='00_资料说明.md'and hashlib.sha256((R/x['path']).read_bytes()).hexdigest()!=x['sha256']];assert not changed
(O/'交付清单.md').write_text('# 交付文件与大小\n\n|文件|字节|\n|---|---:|\n'+'\n'.join(f'|{p.name}|{p.stat().st_size}|'for p in reports)+'\n\n报告43片；进度与本清单另计。scripts为脚本；tmp为本地复核中间文件，不受上传分片上限约束。\n',encoding='utf8')
z=Path(os.environ['USERPROFILE'])/'Desktop/诊断报告_20261101.zip'
# This archive was newly created by this task; refresh it to match final reports.
with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as zz:
 for p in O.rglob('*'):
  if p.is_file():zz.write(p,arcname='诊断报告_20261101/'+p.relative_to(O).as_posix())
with zipfile.ZipFile(z)as zz:assert zz.testzip()is None
print(json.dumps({'report_count':len(reports),'zip_bytes':z.stat().st_size,'rows':len(rows),'source_changes':changed,'max_report_bytes':max(p.stat().st_size for p in reports),'overview_bytes':(O/'00_总览.md').stat().st_size},ensure_ascii=False))
