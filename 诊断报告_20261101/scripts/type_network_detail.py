exec(open(r'D:\诊断报告_20261101\scripts\type_network_stats.py',encoding='utf-8-sig').read().split('stat={}')[0])
for n,s in [('类型系统','创作路径\\商业爆款路径.json'),('类型系统','风格.json'),('类型系统','类型动态规则总表.json'),('类型连接','类型静态搭配库.json'),('类型连接','类型静态连接总表.json')]:
 d=get(n,s); print(s,json.dumps(d if s.endswith('商业爆款路径.json') else (d.get('原始条目',d.get('styles',[]))[:1] if isinstance(d,dict) else d[:1]),ensure_ascii=False)[:7000])
print('errors',[(n,sum(z['error'] is not None for z in bs)) for n,bs in b.items()])
for n,bs in b.items():
 print('MENTIONS',n)
 for z in bs:
  if '作品' not in z['name'] and any(w in json.dumps(z['data'],ensure_ascii=False) for w in ['承诺','字数']):print(z['line'],z['name'])
