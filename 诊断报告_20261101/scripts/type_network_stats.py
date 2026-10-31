import json,collections,random,re
from pathlib import Path
O=Path(r'D:\诊断报告_20261101'); p=json.loads((O/'tmp/type_network_parsed.json').read_text(encoding='utf-8'));b=p['blocks']
def get(n,s):return next(z['data'] for z in b[n] if z['name']==s)
t=get('类型系统','类型本体\\类型总表.json')['types'];a=get('类型系统','类型表达适配总表.json')['adaptations'];c=get('类型系统','类型组合总表.json')['原始条目']; st=p['net']['静态网络']['connections'];dy=p['net']['动态网络']['动态网络连接_完整版']['连接列表']
stat={}
for k in ['type_kind','level','evidence_type']:stat[k]=dict(collections.Counter(str(x.get(k)) for x in t))
stat['type_empty']={k:sum(not x.get(k) for x in t) for k in t[0]};stat['invalid_parent']=[x['type_id'] for x in t if x['parent_id'] and x['parent_id'] not in {y['type_id'] for y in t}];stat['xuanhuan']={k:sum(k in json.dumps(x,ensure_ascii=False) for x in t) for k in ['玄幻','GENRE_XUANHUAN']}
stat['adapt_empty']={k:sum(not x.get(k) for x in a) for k in a[0]};stat['adapt_confidence']=dict(collections.Counter(str(x.get('confidence')) for x in a));stat['adapt_type']=dict(collections.Counter(str(x.get('type_id')) for x in a))
fields=['primary_type_id','type_ids','subtype_ids','mechanism_ids','structure_ids','style_ids','tone_ids','concept_ids','entity_type_ids','event_type_ids','dynamic_rule_ids','static_connection_ids'];sig=lambda x:json.dumps({k:x.get(k) for k in fields},sort_keys=True,ensure_ascii=False)
stat['combination_unique_signature']=len(set(map(sig,c)));stat['combination_unique_id']=len({x.get('combination_id') for x in c});stat['combination_generation']=dict(collections.Counter(x.get('generation_method') for x in c))
stat['static_types']=dict(collections.Counter(x['type'] for x in st));stat['dynamic_n']=len(dy);stat['dynamic_generated']=sum(bool(x.get('generated_from_static')) for x in dy);stat['dynamic_effect_unique']=len({x.get('effect') for x in dy});stat['dynamic_conditions_unique']=len({x.get('condition') for x in dy});stat['dynamic_type']=dict(collections.Counter(x.get('type') for x in dy));stat['dynamic_fields']={k:dict(collections.Counter(str(x.get(k)) for x in dy)) for k in ['source_layer','target_layer','direction','strength','validation_status']}
stat['anchor_unique_id']=len({x['id'] for x in p['anchors']});stat['anchor_unique_content']=len({x['content'] for x in p['anchors']});stat['anchor_unique_condition']=len({x['condition'] for x in p['anchors']});stat['anchors_category']=dict(collections.Counter(x['category'] for x in p['anchors']))
(O/'tmp/type_network_stats.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(stat,ensure_ascii=False,indent=2))
# Each source independently seeded. Sampling units: types / static connection total table / edges / anchor rows.
pools={'类型系统':t,'类型连接':get('类型连接','类型静态连接总表.json'),'静态网络':st,'动态网络':dy,'锚点网络':p['anchors']};samples=[]
for n,ls in pools.items():
 for i in random.Random(20261101).sample(range(len(ls)),20):
  x=ls[i]; ident=next((x[k] for k in ['type_id','connection_id','id'] if k in x),str(i+1)); excerpt=json.dumps(x,ensure_ascii=False)
  if n=='类型系统':excerpt=x['canonical_name']+'：'+x['definition']
  elif n=='类型连接':excerpt=json.dumps({k:v for k,v in x.items() if k not in ['运行层升级']},ensure_ascii=False)[:380]
  elif n in ['静态网络','动态网络']:excerpt='；'.join(str(x.get(k,'')) for k in ['source','target','type','condition','effect'])
  elif n=='锚点网络':excerpt='；'.join(x[k] for k in ['name','content','condition'])
  row={'资料':n,'抽样单位':'类型条目' if n=='类型系统' else '静态连接总表条目' if n=='类型连接' else '连接边' if n in ['静态网络','动态网络'] else '状态锚点','序号':i+1,'id':ident,'出处':f'02_原版资料/原始资料/{n}.txt / '+('line '+str(x['line']) if n=='锚点网络' else str(ident)),'原文':excerpt[:380]};samples.append(row)
(O/'tmp/type_network_sample_raw.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
for j,x in enumerate(samples):print(j,x['资料'],x['id'],x['原文'])
