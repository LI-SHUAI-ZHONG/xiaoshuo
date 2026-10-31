import json
from pathlib import Path
O=Path('D:/诊断报告_20261101');e=json.loads((O/'tmp/library_random.json').read_text(encoding='utf8'))[-1];print(json.dumps(e['runtime'],ensure_ascii=False)[:7000])
