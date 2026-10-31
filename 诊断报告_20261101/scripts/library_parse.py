from pathlib import Path
import re,json,collections,statistics,random,hashlib
O=Path('D:/诊断报告_20261101'); p=Path('D:/搭建/02_原版资料/原始资料/资料库.txt');ls=p.read_text(encoding='utf-8-sig').splitlines(); rows=[];block=None;item=None
# Boundaries include markdown headings and bold numbered subitems; every occurrence retained.
for i,l in enumerate(ls):
 bm=re.match(r'^#{2,3}\s*板块(\d+)\s*(.*)',l); hm=re.match(r'^#{1,6}\s+(.+)',l); nm=re.match(r'^\*\*(\d+\.\d+[^*]*)\*\*',l)
 if bm: block=(int(bm[1]),bm[2])
 if hm or nm:
  if item: item['end']=i;rows.append(item)
  title=hm[1] if hm else nm[1];item={'id':title,'line':i+1,'start':i+1,'section':block}
if item:item['end']=len(ls);rows.append(item)
entries=[]
for r in rows:
 raw='\n'.join(ls[r['start']:r['end']]);base=raw.split('【运行层升级】')[0];normalized=re.sub(r'【([^\n】》)）\]」]+)[】》)）\]」]',r'【\1】',base); normalized=re.sub(r'^\*\*([^*\n]+)\*\*[：:]',r'【\1】',normalized,flags=re.M); fields={m[1]:m[2].strip() for m in re.finditer(r'【([^】\n]+)】\s*([\s\S]*?)(?=【[^】\n]+】|\Z)',normalized)}
 if not fields and not (re.match(r'^\d+[._]',r['id']) or re.match(r'^\d+\.\d+',r['id'])):continue
 if r['id'].startswith('板块') and '定义' not in fields:continue
 
 if re.search(r'\*\*板块\*\*[：:]\s*(\d+)\.',base):
  sn=int(re.search(r'\*\*板块\*\*[：:]\s*(\d+)\.',base)[1]);r['section']=(sn,'由条目板块元数据识别')
 if re.match(r'^\d+_',r['id']):
  sn=int(r['id'].split('_')[0]);r['section']=(sn,r['id'].split('_',1)[1])
 r.update(fields=fields,base=base.strip(),base_length=len(re.sub(r'\s','',base)),raw_length=len(raw),runtime=[])
 for m in re.finditer(r'```json\s*([\s\S]*?)```',raw):
  try:r['runtime'].append(json.loads(m[1]))
  except Exception:pass
 entries.append(r)
(O/'tmp/library_entries_v2.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf8')
blocks=collections.defaultdict(list)
for e in entries:
 if e['section']:blocks[e['section'][0]].append(e)
rng=random.Random(20261101); strata=[list(range(1,45)),list(range(45,78)),list(range(81,101)),list(range(101,128)),list(range(128,163))];sample=[]
for st in strata:
 available=[b for b in st if b in blocks]
 for b in rng.sample(available,4):sample.append(rng.choice(blocks[b]))
(O/'tmp/library_random.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf8')
# representative: three per source compilation bucket; plus substantive and weak examples
represent=[]
for lo,hi in [(1,44),(45,77),(81,100),(101,127),(128,154),(155,162)]:
 a=[x for x in entries if x['section'] and lo<=x['section'][0]<=hi];a.sort(key=lambda x:x['base_length']);represent.extend([a[0],a[len(a)//2],a[-1]])
seen={};review=sample+represent
for x in review:seen[x['line']]=x
(O/'tmp/library_review.txt').write_text('\n\n'.join(f"ID={x['id']} 行{x['line']} 板块={x['section']}\n{x['base'][:5000]}"for x in seen.values()),encoding='utf8')
print(json.dumps({'entries':len(entries),'blocks':len(blocks),'definition_markers':sum(l.strip()=='【定义】'for l in ls),'missing_block_numbers':[x for x in range(1,163) if x not in blocks],'review':len(seen),'fields':collections.Counter(k for x in entries for k in x['fields'])},ensure_ascii=False))
print('SAMPLE_COMPACT');
for x in sample: print(x['line'],x['id'], json.dumps({k:v[:700] for k,v in x['fields'].items() if k in ['定义','指令','判定标准','写作指令']},ensure_ascii=False))
