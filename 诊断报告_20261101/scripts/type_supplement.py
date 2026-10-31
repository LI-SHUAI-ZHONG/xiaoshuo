from pathlib import Path
import json,collections
O=Path('D:/诊断报告_20261101');d=json.loads((O/'tmp/type_network_parsed.json').read_text(encoding='utf8'))
def get(n,name):return next(x for x in d['blocks'][n]if x['name'].split('\\')[-1]==name)
s=['# 03a 动态规则、四子库与组合追踪补充','## 四子库口径纠正','03正文的“四类核心表”是审计用表分组；按作者指定的四子库，应为动态搭配库、作品资源流动模式库、静态连接总表、静态搭配库。类型组合总表属于类型系统，不能代替作品资源库。', '作品资源流动模式库（类型连接.txt:1144461）实际为items=[]、count=0、evidence_type=template、status=active、schema_version=H0D-1.0.0。它没有可抽取的真实作品流动案例；active不能证明有数据。其余三库字段、去重与用法见03。','## 动态规则全表','下列逐条列出原数据的scope、kind、触发、前提和候选结果。每字段摘录<=350字。规则是候选推理约束，不是已发生事件；生成方法的完整历史未核实，template/active仅为数据状态。','']
r=get('类型系统','类型动态规则总表.json')
for x in r['data']['原始条目']:
 s.append('### '+x['rule_id'])
 for k in ['rule_scope','rule_kind','type_ids','trigger_concepts','trigger_event_types','preconditions','candidate_effects','selection_constraints','evidence_type','status']:
  v=x.get(k)
  if v not in(None,[],{},''):s.append(f'- {k}：'+json.dumps(v,ensure_ascii=False)[:350])
s+=['## “不能保证什么”的复算','对类型连接所有SOURCE解码后的JSON递归访问not_guaranteed字段，统计其字符串叶子；已在解析时剥离运行层升级。相同内容跨子库会重复出现；这是字段语句重复率，不是全部知识去重率。']
v=[]
def walk(x):
 if isinstance(x,dict):
  for k,y in x.items():
   if k=='not_guaranteed':
    if isinstance(y,list):v.extend(z for z in y if isinstance(z,str))
    elif isinstance(y,str):v.append(y)
   else:walk(y)
 elif isinstance(x,list):
  for y in x:walk(y)
for b in d['blocks']['类型连接']:walk(b['data'])
c=collections.Counter(v);s.append(f'本轮该口径共{len(v)}次字符串、{len(c)}种精确值。旧索引“8400条/4种”若限定不同表，口径并不相同；不能照抄。')
(O/'tmp/not_guaranteed_counts.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8')
s.append('下列仅列频次最高20种；完整精确值计数见tmp/not_guaranteed_counts.json。')
for k,n in c.most_common(20):s.append(f'- {n}次：{k[:350]}')
s+=['## 类型组合从选定到约束：真实引用追踪','这是静态追踪示范，未执行管线、未确认成正式事实、未生成新小说正文。']
co=get('类型系统','类型组合总表.json')['data']['原始条目'][0]
s.append('选择：'+co['combination_id']+'（类型系统.txt:42967 SOURCE；条目ID定位）。其状态='+co['selection_status']+'，生成方法='+co['generation_method']+'，仍需作者/项目选择。')
for k in ['primary_type_id','subtype_ids','mechanism_ids','structure_ids','style_ids','static_connection_ids','dynamic_rule_ids','adaptation_ids']:s.append('- '+k+'：'+json.dumps(co[k],ensure_ascii=False))
s.append('下面展开该组合引用的动态规则与表达适配。字符串/编号指向不等于所有上下文前提满足；未能唯一找到的明确列缺口。')
def records(x):
 if isinstance(x,list):return x
 if isinstance(x,dict):return x.get('原始条目',x.get('adaptations',x.get('items',[])))
 return []
for field,table,idkey in [('dynamic_rule_ids','类型动态规则总表.json','rule_id'),('adaptation_ids','类型表达适配总表.json','adaptation_id')]:
 a=records(get('类型系统',table)['data'])
 for rid in co[field]:
  x=next((y for y in a if y.get(idkey)==rid),None);s.append('### '+rid)
  if x is None:s.append('当前指定表未匹配；不得补造。');continue
  for k,vv in x.items():
   if k in ['preconditions','candidate_effects','selection_constraints','preferred_expressions','forbidden_expressions','not_guaranteed','type_id','target_object_type','target_type','replacement_expressions'] and vv:s.append(k+'：'+json.dumps(vv,ensure_ascii=False)[:350])
s+=['可产出的约束应是：先确认仙侠/成长/线性结构是否符合作者题材；再只取与当前对象匹配的适配词，禁用词检查也按type_id和对象范围；动态候选必须满足前提、由人物行动选择后才进入状态。此组合若引用了与人物/场景不相关的食物、服装或隐藏身份资料，应排除，不能强制塞进正文。','这里未得到完整的项目承诺、章字数、具体人物选择与终局兑现规则，因此本组合本身不能独立产出合格场景。需项目圣经、场景卡和作者事实补足；不能把组合的quality_score=0.9称为文学质量得分。']
body='\n'.join(s);assert len(body.encode())<60000;(O/'03a_规则与组合追踪.md').write_text(body,encoding='utf8');print('supplement',len(body.encode()),'not_guaranteed',len(v),len(c))


