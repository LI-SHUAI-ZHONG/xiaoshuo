exec(open(r'D:\诊断报告_20261101\scripts\type_network_stats.py',encoding='utf-8-sig').read().split('stat={}')[0])
for z in b['类型系统']:
 if z['error']:print(z['line'],z['name'],z['error'])
for n,s in [('类型连接','类型静态连接总表.json'),('类型连接','类型动态搭配库.json')]:
 d=get(n,s);ls=d if isinstance(d,list) else d['原始条目'];print(s,'fields',list(ls[0]),'empty',{k:sum(not x.get(k) for x in ls) for k in ls[0]});print('dedup',len(ls),len(set(json.dumps({k:v for k,v in x.items() if not k.endswith('_id') and k not in ['运行层升级']},sort_keys=True,ensure_ascii=False) for x in ls)))
print('xuanhuan children',sum(x['parent_id']=='GENRE_XUANHUAN' for x in t))
print('def taut',sum('的子类型' in x['definition'] for x in t))
