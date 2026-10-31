import json,re,collections
from pathlib import Path
O=Path('D:/诊断报告_20261101');e=json.loads((O/'tmp/library_entries.json').read_text(encoding='utf8')); inv=json.loads((O/'tmp/inventory.json').read_text(encoding='utf8'))
print('heading variants:',[(x['id'],x['section']) for x in e if not re.match(r'\d+\.\d+',x['id'])][:60]);print('defined',sum('定义'in x['fields'] for x in e))
p=Path('D:/搭建/02_原版资料/原始资料/资料库.txt'); ls=p.read_text(encoding='utf8').splitlines();h=[(i+1,l)for i,l in enumerate(ls)if re.match(r'^#{1,6} ',l)];print('headings tail',h[-90:]);print('inventory groups',collections.Counter('/'.join(x['path'].split('/')[:2])for x in inv['files']).most_common(20))
