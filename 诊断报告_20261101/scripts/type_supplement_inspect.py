from pathlib import Path
import json,collections
O=Path('D:/诊断报告_20261101');d=json.loads((O/'tmp/type_network_parsed.json').read_text(encoding='utf8'))
for n in ['类型系统','类型连接']:
 for x in d['blocks'][n]:
  if any(z in x['name'] for z in ['类型动态规则总表.json','类型组合总表.json','作品资源流动模式库.json']):
   v=x['data']; print(n,x['name'],x['line'],type(v).__name__,list(v)[:8]if isinstance(v,dict)else'');
   if isinstance(v,dict):
    a=v.get('原始条目',[]);print(json.dumps(a[:1]if a else v,ensure_ascii=False)[:3500])
