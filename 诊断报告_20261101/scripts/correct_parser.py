p='D:/诊断报告_20261101/scripts/library_parse.py'
s=open(p,encoding='utf8').read();s=s.replace("fields={m[1]:m[2].strip() for m in re.finditer(r'【([^】]+)】\\s*([\\s\\S]*?)(?=【[^】]+】|\\Z)',base)}", "normalized=re.sub(r'【([^\\n】》)）\\]」]+)[】》)）\\]」]',r'【\\1】',base); normalized=re.sub(r'^\\*\\*([^*\\n]+)\\*\\*[：:]',r'【\\1】',normalized,flags=re.M); fields={m[1]:m[2].strip() for m in re.finditer(r'【([^】\\n]+)】\\s*([\\s\\S]*?)(?=【[^】\\n]+】|\\Z)',normalized)}")
s=s.replace("if not fields:continue", "if not fields and not (re.match(r'^\\d+[._]',r['id']) or re.match(r'^\\d+\\.\\d+',r['id'])):continue")
s=s.replace("print((O/'tmp/library_review.txt').read_text(encoding='utf8')[:26000])", "print('SAMPLE_COMPACT');\nfor x in sample: print(x['line'],x['id'], json.dumps({k:v[:700] for k,v in x['fields'].items() if k in ['定义','指令','判定标准','写作指令']},ensure_ascii=False))")
open(p,'w',encoding='utf8').write(s)
