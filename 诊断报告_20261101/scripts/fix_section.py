from pathlib import Path
p=Path('D:/诊断报告_20261101/scripts/library_parse.py');s=p.read_text(encoding='utf8');s=s.replace("r.update(fields=fields", "\n if re.match(r'^\\d+_',r['id']):\n  sn=int(r['id'].split('_')[0]);r['section']=(sn,r['id'].split('_',1)[1])\n r.update(fields=fields")
p.write_text(s,encoding='utf8')
