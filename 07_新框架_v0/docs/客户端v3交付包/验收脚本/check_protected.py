from pathlib import Path
import hashlib
import json
import sys

PROJECT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT/'src'))
from nw.materials.adjudication import _code_hash

before=json.loads((Path(__file__).parent.parent/'protected-baseline.json').read_text(encoding='utf-8'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
after={'adjudication':_code_hash(),'phase_routes':sha(PROJECT/'src/nw/materials/phase_routes.py'),
       'originals':{name:sha(PROJECT.parent/name) for name in before['originals']}}
assert before==after,'Protected source files changed'
print(json.dumps({'unchanged':True,'original_files':len(after['originals']),'core_files':21}))
