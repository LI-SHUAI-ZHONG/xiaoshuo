from pathlib import Path
p=Path('D:/诊断报告_20261101/scripts/library_parse.py');s=p.read_text(encoding='utf8');s=s.replace("if re.match(r'^\\d+_',r['id']):", "if re.search(r'\\*\\*板块\\*\\*[：:]\\s*(\\d+)\\.',base):\n  sn=int(re.search(r'\\*\\*板块\\*\\*[：:]\\s*(\\d+)\\.',base)[1]);r['section']=(sn,'由条目板块元数据识别')\n if re.match(r'^\\d+_',r['id']):")
p.write_text(s,encoding='utf8')
