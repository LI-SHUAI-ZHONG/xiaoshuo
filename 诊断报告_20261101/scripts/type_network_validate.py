exec(open(r'D:\诊断报告_20261101\scripts\type_network_stats.py',encoding='utf-8-sig').read().split('stat={}')[0])
for name,ls,idkey in [('静态总表',get('类型连接','类型静态连接总表.json'),'connection_id'),('静态搭配',get('类型连接','类型静态搭配库.json')['原始条目'],'static_combination_id'),('动态搭配',get('类型连接','类型动态搭配库.json')['原始条目'],'dynamic_combination_id')]:
 print(name,len(ls),'ID',len({x[idkey] for x in ls}),'内容去自身id',len({json.dumps({k:v for k,v in x.items() if k!=idkey},sort_keys=True,ensure_ascii=False) for x in ls}),'sig empty',sum(not x.get('similarity_signature') for x in ls))
 print('fields',','.join(ls[0]))
print('conn triples',len({(x['source_id'],x['target_id'],x['connection_type']) for x in get('类型连接','类型静态连接总表.json')}))
rules=get('类型系统','类型动态规则总表.json')['原始条目'];rids={x['rule_id'] for x in rules};refs={v for x in c for v in x['dynamic_rule_ids']};print('rule ids',sorted(rids),'combo missing rules',sorted(refs-rids));print('rules status',collections.Counter(x['status'] for x in rules))
for n,ls in [('静态',st),('动态',dy)]:print(n,'nodes',len({x[k] for x in ls for k in ['source','target']}),'keys',len({(x['source'],x['target'],x['type']) for x in ls}))
print('derived effect',len({x['effect'] for x in dy if x.get('generated_from_static')}))
print('pure deriv matched',sum((x['source'],x['target'],x['type']) in {(y['source'],y['target'],y['type']) for y in st} for x in dy if x.get('generated_from_static')))
