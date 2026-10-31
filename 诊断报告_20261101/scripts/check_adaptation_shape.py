from pathlib import Path
import json
O=Path('D:/诊断报告_20261101');d=json.loads((O/'tmp/type_network_parsed.json').read_text(encoding='utf8'))
for b in d['blocks']['类型系统']:
 if b['name'].split('\\')[-1]=='类型表达适配总表.json':print(type(b['data']).__name__, list(b['data'])[:8])
