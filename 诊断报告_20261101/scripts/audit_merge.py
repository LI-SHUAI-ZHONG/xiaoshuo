from pathlib import Path
import json,collections,re
O=Path('D:/诊断报告_20261101');rows=[json.loads(l)for l in(O/'tmp/library_samples.jsonl').read_text(encoding='utf8').splitlines()if l];other=[json.loads(l)for l in(O/'tmp/type_network_samples.jsonl').read_text(encoding='utf8').splitlines()if l]
for x in other:rows.append({'material':x['资料'],'id':x['id'],'source':x['出处'],'seed':x['seed'],'excerpt':x['原文'][:400],'score':x['评分'],'reason':x['理由'],'unit':x['抽样单位']})
assert len(rows)==120 and all(x['score'] in [0,1,2]and len(x['excerpt'])<=400 for x in rows)
parts=[];cur=''
for x in rows:
 line=json.dumps(x,ensure_ascii=False)+'\n'
 if len((cur+line).encode())>58000:parts.append(cur);cur=''
 cur+=line
parts.append(cur)
for i,s in enumerate(parts):(O/('09_抽样数据.jsonl'if i==0 else f'09{chr(97+i)}_抽样数据.jsonl')).write_text(s,encoding='utf8')
g=collections.defaultdict(list)
for x in rows:g[x['material']].append(x)
counts={k:dict(collections.Counter(x['score']for x in v))for k,v in g.items()};(O/'tmp/audit_counts.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2),encoding='utf8')
s=['# 09 抽样审计','固定随机种子20261101。先抽取并保存样本，再由模型审读评分；未调用写作模型。分数0=空壳/填充，1=有信息但难直接写场景，2=具备可执行做法。评分是本轮单一评审判断，不是作者盲测或商业质量验收。','资料库分层：1–44、45–77、81–100、101–127、128–162五组，每组随机选四个实际板块，每板块再随机一条出现记录。各板块抽中概率不相同，重复版本保留，因此整体未加权均值不能估计全库真实可用率。类型系统在710本体、类型连接在3135静态连接、三网在各自核心表抽20；没有对每份资料所有子表均匀抽样。类型系统适配和动态规则可能比本体更有用，不能从本体样本推断整个文件无价值。','原文摘录每条不超过400字。个别资料库运行补全条目评分阅读了其语义字段，摘录只是证据窗口。样本在09_抽样数据.jsonl及续片，每文件小于60KB。','## 汇总','可用率严格定义为评分2占样本比例；“有信息率”为评分至少1占比。两者均只是抽中样本描述，不是实测场景提升率。','|资料|样本|0|1|2|可用率|有信息率|','|---|---:|---:|---:|---:|---:|---:|']
for k,v in g.items():
 c=collections.Counter(x['score']for x in v);n=len(v);s.append(f'|{k}|{n}|{c[0]}|{c[1]}|{c[2]}|{c[2]/n:.0%}|{(c[1]+c[2])/n:.0%}|')
s+=['\n## 逐条评分','|资料|ID/条目|分数|理由|出处|','|---|---|---:|---|---|']
for x in rows:s.append(f'|{x["material"]}|{x["id"]}|{x["score"]}|{x["reason"]}|{x["source"]}'+(':'+str(x['line'])if'line'in x else'')+'|')
s+=['\n## 局限','样本小、评分者相同、规则适用性强依赖场景。本轮没有写同场景前后对照，故“照着能改善”仍是可执行性判断。建议由作者复评分歧条目，再用固定基础上下文做场景消融；先验证收益再将候选升级为确认。样本的0分不能作为删除原资料的依据。']
(O/'09_抽样审计.md').write_text('\n'.join(s),encoding='utf8')
print(counts)
