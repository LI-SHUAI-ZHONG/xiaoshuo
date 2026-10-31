from pathlib import Path
import json,re,collections,statistics
O=Path('D:/诊断报告_20261101');R=Path('D:/搭建');E=json.loads((O/'tmp/library_entries_v2.json').read_text(encoding='utf8'));S=json.loads((O/'tmp/library_random.json').read_text(encoding='utf8'));text=(R/'02_原版资料/原始资料/资料库.txt').read_text(encoding='utf8');path='02_原版资料/原始资料/资料库.txt'
B=collections.defaultdict(list); names={int(m[1]):m[2].strip() for m in re.finditer(r'^#{2,3}\s*板块(\d+)\s*(.+)',text,re.M)}
for e in E:B[e['section'][0]].append(e)
# Conservative reproducible estimate, not linguistic information entropy or authorship detection.
meaning_fields=['定义','指令','设计指令','写作指令','判定标准','修正指南','禁止清单','替代方式']
def core(e):
 vals=[]
 for k in meaning_fields:
  v=e['fields'].get(k,'').strip()
  if not v or v=='无' or any(t in v for t in ['在设计阶段规划','在写作阶段按','如不合格，重新审视','作为角色决策的深层驱动']):continue
  if v not in vals: vals.append(v)
 return '\n'.join(vals)
C=[core(e)for e in E]; unique=list(dict.fromkeys(v for v in C if v));runtimechars=sum(e['raw_length']-len(e['base'])for e in E);rt=[v for e in E for v in e['runtime']];bad=[(i+1,l)for i,l in enumerate(text.splitlines())if re.match(r'^【',l) and not re.match(r'^【[^\n】]+】',l)]
rep=[]
for lo,hi in [(1,44),(45,77),(81,100),(101,127),(128,154),(155,162)]:
 a=sorted([e for e in E if lo<=e['section'][0]<=hi],key=lambda e:e['base_length']);rep.extend([a[0],a[len(a)//2],a[-1]])
review={e['line'] for e in S+rep}; reviewed_extra=[15,197405,197979,198847,195031,189728]
review.update(x for x in reviewed_extra if any(e['line']==x for e in E))
stats={'entries':len(E),'blocks':len(B),'reviewed':len(review),'unread_percent':round(100*(len(E)-len(review))/len(E),2),'bytes':(R/path).stat().st_size,'lines':len(text.splitlines()),'chars':len(text),'base_chars':sum(len(e['base'])for e in E),'heuristic_unique_chars':sum(len(v)for v in unique),'core_median':statistics.median(len(v)for v in C),'runtime_jsons':len(rt),'bad_markers':len(bad)}
(O/'tmp/library_final_stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8')
s=['# 02 资料库诊断','\n## 全量解析与人工审读口径',f'文件 {path}：{stats["bytes"]}字节、{stats["lines"]}行。全文件扫描标题、字段及运行层JSON；兼容【字段】、错括号和 **字段**：，同时识别粗体数字子项及条目自身板块元数据。解析得到{len(E)}个条目出现位置，{len(B)}个实际板块编号，{len(rt)}个可解析运行JSON。不是去重后的独立知识条数。',f'审读了{len(review)}个不同条目的核心字段/代表片段（包含固定随机20条），剩余{stats["unread_percent"]}%未逐条语义审读。对大条目并非读完所有JSON；JSON结构解析不等于内容验收。旧索引“754条含定义”不是本轮条目口径，本轮兼容多种格式并保留重复版本，不能直接比较。脚本：library_parse.py、library_report.py；早期试解析保存在tmp，最终以library_entries_v2.json与library_final_stats.json为准。','\n## 真正内容量：可复算的代理指标',f'剥离运行层后条目正文合计{stats["base_chars"]}字符；保留定义/指令/设计指令/写作指令/判定/修正/禁止/替代字段，剔除若干明确套话，再对条目整段精确去重，得到{stats["heuristic_unique_chars"]}字符；每条保留字符中位数{stats["core_median"]}。算法列在脚本中。这不是“人写字数”，不是知识价值，也没有消除所有语义重复。旧索引约十万字的算法未附，无法据本指标机械证实原数字。','资料覆盖面广且深度不均；绝非没有有效方法。身体状态通过行为体现、权力反转的可见时刻、视角控制、推进诊断、观察到行动的链条，都可以提炼。另一方面，三幕结构只说“故事最基本的骨架划分”，不能指导作者真正排出长篇。','\n## 条目结构与来源判断','|字段组|意义与实际问题|','|---|---|','|定义|概念/原则；有的短语即可概括，有的包含完整操作约束；需逐条辨别|','|调用条件/优先级/例外|意图控制何时使用；大量“无”或循环解释，不能自动当成检索策略|','|指令/设计/写作|理应给出可执行动作；很多为“按某规则执行”，也存在明确做法|','|分级/场景变体/判定/修正|理应支持审稿；“轻度简单、中度充分、重度深度”无法客观执行|','|示例/反例|很多只复述定义或给流程占位；不是可模仿的场景正反对照|','|关联板块/路径/标签|用于定位；必须核验编号与真实目录，不能当正文材料|','|运行层升级|绑定、激活、授权与消费证据合同，扩充了运行元数据而非等量写作知识|','不能从文风可靠判定“人工原作”与“模型生成”。本轮把运行层JSON与可见脚本模板判作程序派生证据；基础段落作者身份未核实。文件首部写有来源和生成时间（:1–9），也不足以证明逐条人写。','\n## 运行层字段含义','|字段|含义|','|---|---|','|fusion_mode / canonical_source_id / source_locator|融合方式与原条目标识；末尾补全常用precise_source_ref|','|binding_id/source_id/source_kind/source_ref|绑定ID、资料种类及定位；其中历史line_start不能直接当当前行号|','|translation_status/model_input_eligible/prose_write_allowed|程序状态及输入许可；true不证明内容正确或质量高|','|semantic_interpretation|原意、操作含义、语义词、原语义短摘、禁止元数据入正文|','|creation_binding|创作阶段、对象、动作、场景/正文策略、激活条件与作用范围|','|creative_strategy|触发、可观察行动、结果、代价、证据位置和质量要求|','|evidence_contract|设计、场景、正文应提交哪些字段及段落哈希|','|use_authorization|批量授权范围、时间、来源哈希；不是正式事实批准/发表许可|','|tail_upgrade_evidence|尾部升级追踪信息，仍需与真实源版本核对|','证据：资料库:93起第一份JSON；全量资料解释词转译与创作绑定.py:59–100读取定义/指令并截取语义锚，:141–185按source_kind插入固定触发/动作/代价句，:188起用关键词决定创作对象，:361起输出绑定文件。该脚本证明运行合同的模板来源；将所有合同嵌回txt的最后一次写回脚本与完整执行记录未核实。','同脚本:99的短摘会截断句子；资料库:201748的148运行补全段确有“不同人格角色观察到不同东西（”这类未闭合摘录。它携带原条目痕迹，不能说完全无信息，但长模板并未增加同等长度的新方法。','\n## 设想如何用、哪里自相矛盾','资料库:197405明确按场景做三层筛选并给出调用/不调用清单；:189728将参数转为叙述、对话、动作与证据；:197017要求已有故事设计时跳过核心驱动层。可见“精选+转化”原本就在资料里，H2不能只归因于资料没有此思想。','同时，:195362的调用表包含错位编号（例如五节点链条被指向146，而实际板块145在:197815）；固定比例和每章强制动作也可能互相抢占篇幅。检索应按用途筛选，不能逐条强制执行全库。','\n## 板块目录与长度','长度为剥离运行层后、去空白的原文字数，包含模板字段；同编号的多个出现版本合并计数。无定义数包含仅运行补全或纯映射条目，不一定是丢失。评级是自动筛查：A候选=保留核心长度中位数≥180，B待筛=≥60，C偏薄=<60；不是逐板块人工评分，不可据此批量停用。','|编号|名称|出现条目|平均长度|中位长度|无定义|初筛|首行|','|---:|---|---:|---:|---:|---:|---|---:|']
for n in range(1,163):
 a=B.get(n,[])
 if not a:s.append(f'|{n}|缺板块正文|0|—|—|—|缺失|—|');continue
 median=statistics.median(len(core(e)) for e in a);grade='A候选'if median>=180 else 'B待筛'if median>=60 else 'C偏薄';s.append(f'|{n}|{names.get(n,a[0]["section"][1])}|{len(a)}|{statistics.mean(e["base_length"]for e in a):.1f}|{statistics.median(e["base_length"]for e in a)}|{sum(not e["fields"].get("定义")for e in a)}|{grade}|{a[0]["line"]}|')
s+=['\n## 代表性真实示例','按人物世界、表达情节、检查执行、后期扩展、综合规则、补充美学分组，下面每组三个位置，包含薄条目与相对具体条目。引文只取资料规则，不引用第三方小说正文。']
for i,e in enumerate(rep):
 if i%3==0:s.append('\n### '+['人物与世界','情节与表达','执行与检查','一致性与推进','综合调用与扩展','补充节奏与审美'][i//3])
 excerpt=core(e)[:350] or '（基础正文为空，仅运行层合同；见原条目）';s.extend([f'**{e["id"]}**（{path}:{e["line"]}）', '> '+excerpt.replace('\n','\n> '),'判断：'+('缺少基础写法，宜回查原条目。'if not core(e) else '包含具体约束，但数字阈值与强制性需按项目验证。'if len(core(e))>180 else '主要是概念或简短原则，单独不足以生成场景。')])
s+=['\n## 重复、断裂、错误','- 板块128正文出现重叠版本（:195029、:197405）；末尾129–154运行补全不是新的基础知识（:199338起）。不能只凭标题去重删除。','- 106.1_全篇语言风格统一（:100815）被指令要求呈现为“角色状态”“身体信号”，对象错配；属于机器适配污染，不是文风本身无价值。','- 128.2（:195362）对145以后多处板块号错位；规划引用必须重建ID映射。','- 4.2（:7917）定义以冒号结尾而无列表；后续互锁规则仍有信息，因此不能把整条归零。',f'- 非标准字段开括号行检测到{len(bad)}处；清单见02a。只在解析副本兼容，原文件未修改。','- 未发现78–80板块标题正文，其他条目仍引用79（:197405）；缺失源正文无法凭推测补全。','- 以标题归一或字符串重复只能发现候选重复；完整的语义重复/错误清单未核实。','\n## 对长篇创作的覆盖','|主题|结论|可核对板块|','|---|---|','|设定与人物|覆盖广，有规则约束；具体项目的一致性账本仍需另建|1–40、101–108|','|大纲与剧情|有结构名、推进与冲突方法；从题材到全书大纲的可靠生成能力未由资料证明|41–48、122|','|对话、场景、感官、视角|有较多可提炼规则，混有比例硬约束及占位示例|46–60、120、156–159|','|悬念、爽点、钩子|主题存在；需要兑现时机和具体情境评估|44–45、48、65、130|','|文风|有一致性、句式、词汇、叙述距离；缺作者认可的成套文风样本验证|49–55、106、109|','|字数与节奏|有篇幅分配和重轻章规则，不是完全空白；缺经验证的类型×全书目标规模规划|61–62、127.12、155|','|长篇运营|写作作息与反馈有条目；预算、续写恢复、连载频率和商业质量控制需项目系统落实|134–137|','结论：适合整理成带适用条件的候选规则卡，不能把全库直接当强制规范。最值得优先试验的是可观察的角色选择与代价、视角一致性、对话潜台词、场景信息释放、推进诊断和章末未解决问题。固定配比保留原出处，状态先设候选，不包装成已验证规律。']
(O/'02_资料库.md').write_text('\n'.join(s),encoding='utf8')
# bounded error list and duplicate candidate list
A=['# 02a 格式与重复候选清单','\n字段错括号原行（截断到160字；仅列原格式，不自动修复）：']
A += [f'- {path}:{n} `{v[:160]}`'for n,v in bad]
D=collections.defaultdict(list)
for e in E:D[re.sub(r'^(?:板块)?\d+(?:\.\d+)?[_\s]*','',e['id'])].append(e)
A+=['\n同名候选（不是自动判为语义重复）：']
A += [f'- {k}：'+','.join(str(e['line'])for e in a)for k,a in D.items()if len(a)>1]
body='\n'.join(A)
# split at safe line boundaries
parts=[];b=''
for line in body.splitlines(True):
 if len((b+line).encode())>55000:parts.append(b);b='# 02 格式清单续\n'
 b+=line
parts.append(b)
for i,b in enumerate(parts):(O/f'02{chr(97+i)}_格式与重复清单.md').write_text(b,encoding='utf8')
scores=[2,2,2,2,1,1,1,2,1,1,1,2,2,1,2,1,2,2,2,1]
reasons=['用身体信号承载情感，可改进抽象告知；每章强制配额待验证','给出了走姿呼吸幅度等场景可见落点','让交易产生时间机会代价，可增加选择张力','虽定义断裂，维度互锁仍给出可执行的变化代价','仅解释静默概念，没有组织场景的方法','只解释回访意愿，没有形成回访动力的方法','距离配额可执行但固定频率缺少适用条件','短句与动词密度直接指导快速场景表达','给出欺骗概念与风险提示，缺信息差操作','同义重复和泛化执行要求较多','固定插配角POV可能破坏既定视角，不宜直接强制','给出信息时间代价逐章增压检查法','持续保留未解决问题可作审稿检查','定义可用但被转译为身体状态，需先修复','高低张力调节有操作方向，固定章数仅候选','提供板块组合索引，还需展开具体写法','区分未知和多可能，给出排除揭示转化方式','明确空间声音符号与文本独立性检查','观察者滤镜与反证互动能改善人物呈现','运行补全保留原意但短摘截断且模板多，应回读基础条目']
rows=[]
for e,score,reason in zip(S,scores,reasons):
 excerpt=(core(e) or json.dumps(e['runtime'][0]['runtime_calling_layer'][0]['semantic_interpretation'],ensure_ascii=False))[:380]
 rows.append({'material':'资料库','id':e['id'],'source':path,'line':e['line'],'section':e['section'][0],'seed':20261101,'excerpt':excerpt,'score':score,'reason':reason})
(O/'tmp/library_samples.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n'for x in rows),encoding='utf8')
with(O/'进度.md').open('a',encoding='utf8')as f:f.write('\n已完成：02资料库、格式与重复附录、固定分层随机20条审计；解析口径已校正多种字段格式。\n')
print(stats);print('report_bytes',(O/'02_资料库.md').stat().st_size)
