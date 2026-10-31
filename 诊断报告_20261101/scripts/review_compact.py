import json
from pathlib import Path
O=Path('D:/诊断报告_20261101');e=json.loads((O/'tmp/library_random.json').read_text(encoding='utf8'))
for x in e: print(x['line'],x['id'],' | '.join(k+'='+v[:900] for k,v in x['fields'].items() if k in ['定义','指令','设计指令','禁止清单','替代方式'])[:1700])
a=json.loads((O/'tmp/library_entries_v2.json').read_text(encoding='utf8'));print('EXTRA REPRESENTATIVES');
for lo,hi in [(1,44),(45,77),(81,100),(101,127),(128,154),(155,162)]:
 b=sorted([x for x in a if x['section'] and lo<=x['section'][0]<=hi],key=lambda x:x['base_length'])
 for x in [b[0],b[len(b)//2],b[-1]]:print(x['line'],x['id'],x['base'][:1100].replace('\n',' '))
