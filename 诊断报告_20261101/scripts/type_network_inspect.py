exec(open(r'D:\诊断报告_20261101\scripts\type_network_parse.py',encoding='utf-8-sig').read().split('for n,bs in b.items():')[0])
def get(n,s):return next(z['data'] for z in b[n] if z['name']==s)
types=get('类型系统','类型本体\\类型总表.json')['types']; adap=get('类型系统','类型表达适配总表.json')['adaptations']; combos=get('类型系统','类型组合总表.json')['原始条目']
for name,ls in [('types',types),('adap',adap),('combos',combos),('static',net['静态网络']['connections']),('dynamic',net['动态网络']['动态网络连接_完整版']['连接列表'])]:
 print('\n',name,'FIRST',json.dumps(clean(ls[0]),ensure_ascii=False)[:6500])
 if name=='types':
  print('fields',collections.Counter(k for x in ls for k in x));print('xuanhuan',[x for x in ls if x.get('type_id')=='GENRE_XUANHUAN'])
for s in ['类型本体\\类型层级规则.json','类型组合约束.json','类型动态筛选规则.json']:
 print(s,json.dumps(get('类型系统',s),ensure_ascii=False))
print('dynkeys',net['动态网络']['动态网络连接_完整版'].keys())
