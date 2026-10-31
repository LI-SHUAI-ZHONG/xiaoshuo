from pathlib import Path
import json,re,collections,csv,ast
R=Path(r'D:\搭建');O=Path(r'D:\诊断报告_20261101');T=O/'tmp'
def read(p):return p.read_text(encoding='utf-8-sig',errors='replace')
logs=json.loads(read(T/'history_cline_structure.json'));samples=json.loads(read(T/'history_reviewed_samples.json'));runs=json.loads(read(T/'history_runs.json'))
reviews=sum(len(z['text']) for x in samples for z in x['samples']);total=sum(x['chars'] for x in logs)
issues={
'044640':'开场同义复述；跨场套用固定收束', '064251':'第5/6行开头长段重复，长度不能当进展', '004729':'仅短段，无法证明整章完成','031712':'规则ID直接泄漏正文；跨场模板重复','fallback':'目录明确fallback；只是短模板片段','063112':'开场泛化环境描写；整章质量未核实','064113':'表情及紧张套语；整章质量未核实','071305':'直接追问第七息，信息推进边界需复核','072701':'正文与模板段混合；动作选择生硬','073859':'相邻段重复收手/挪步/倾听','074543':'相邻段重复推石/侧身/抚纹','082059':'与模板开场一致；缺独立质量证据','132304':'对话直接解释第七息，潜台词薄弱'}
base={}
for x in runs:
 if x['sha256'] not in base:base[x['sha256']]=x['id']
notes=[
'资料板块补全；助手称补入101–119，但仍有78–80缺项。结论是目录/编号治理，不能等同正文采用。',
'重分配索引assigned_to_module并保留load_order。字段归属修复只证明路由意图，尚不证明消费。',
'复制核心资料的任务因type_commitment.json缺失停下；没有完成复制的证据。',
'定位新版11模块管道，并提出execute_09改造；新版识别依时间/模块清单，仍需核对实际调用。',
'补模块10编辑检查与来源字段；检查规则数量增加不能替代自然叙事评审。',
'全资料审计与运行链追查；末尾明确可准备受控草稿、不能证明成品运用，早期全量完成口径须分层。',
'区分资料级改进与项目级采用；缺项目/类型确认时禁止虚构绑定。本段只有用户指令，无助手完成证据。',
'合并升级资料、生成classified-upgrade-transfer路径；用户追问先升级资料，显示任务焦点曾漂移。',
'Ollama请求停滞、run证据目录分裂、修订分支修复；模型服务可连接不意味着调用完成。',
'从卡住诊断转为正常返回但质量拒绝；长短和required_action门应与运行故障分开。末尾补丁超时，不能宣称已修复。',
'要求确定性锚点补全，却落在无目标代码工作区；此段失败是定位/交接问题，不是模型文笔证据。',
'继续收敛生成与审计；末尾仅确认收到任务，未给实现或运行完成凭据。',
'先要求资料包驱动，随后删除模型专属路径；末尾仍有共享脚本引用被删配置的说明。删除不等于完成新生成器。',
'步骤八半成品恢复后，要求不写入却调用会写注册表的初始化，发生约束冲突；改用隔离验证才可解释。',
'保留能力审计而去掉启动raise；末尾助手为空文本，只有用户授权，结果需下一段印证。',
'助手报告隔离副本完成01–08初始化与验证；明确没有运行09–11，不能借此声称正文链成功。',
'由全量加载转向步骤六传递、步骤八场景绑定、步骤九消费；用户明确指出运行层没有真正参与创作。',
'角色可用性升级；用户指出角色资料仍不全，助手承认把方法节点、评估指标和人物事实混淆。',
'规划、采用与验收链审查；末尾修正草稿/模块资料/正式正文三层落盘，说明产物身份曾混乱。',
'用户要求可发布的生动作品；末尾转为导出完整窗口原始历史，不构成小说商业质量验收。',
'只有“小说”及澄清答复，无实质运行或代码改动。',
'资料删除事件追查与恢复讨论；不把助手硬盘建议当删除机制证据，终端未捕获退出也不等于执行成功。',
'聊天导出由旧tasks占位转读messages.json；末尾仍是准备执行/核对，不应伪称全部原始工具历史已包含。']
report=['# 07 运行历史与失败归因\n','## 口径与结论\n','本轮只读源资料，未执行源项目、测试或模型。运行目录存在23份章节产物，不代表全部历史运行次数：Cline还提及没有正文落盘的失败run。文件名日期取UTC时间戳，不把会话起始日期当所有消息日期。模型名无法从这些正文文件逐一证明；不能把8月19日会话中的qwen2.5:7b推到所有产物。\n',f'全量扫描23份Cline导出，解析{sum(x["messages"] for x in logs)}个消息标题、{total}字符；每条消息角色/时间/起始行/长度存于tmp/history_cline_structure.json。各文件头L7说明不含工具调用、输出和系统压缩摘要。人工阅读固定首用户/末用户/末助手各最多300字符，共{sum(len(x["samples"]) for x in samples)}个去重消息片段、{reviews}字符，占{reviews/total:.3%}，其余{1-reviews/total:.3%}未按此抽样逐字审读；另定向阅读关键片段，不将其计入保守覆盖率。结构全扫不等于全文语义审读。\n','## 23份留存正文产物\n','长度=去空白Unicode字符，含标题与标点，不是模型token或纯汉字。哈希以UTF-8解码文本统一换行后计算；同哈希是文本一致。源均为03_运行资料/正文/运行/<run_id>/章节_CH01.md。\n','|run_id（含UTC日期）|类型/模型|长度|主要观察及证据|\n|---|---|---:|---|']
for x in runs:
 original=base[x['sha256']];key=next((k for k in issues if k in original),'044640');issue=issues[key]
 if original!=x['id']:issue='与'+original+'全文哈希一致；'+issue
 typ='fallback标记/模型未核实' if 'fallback' in x['id'] else ('smoke/模型未核实' if 'smoke' in x['id'] else '一般run/模型未核实')
 report.append(f'|{x["id"]}|{typ}|{x["nonspace"]}|{issue}（L5起）|')
report += [f'\n23份产物只有{len(base)}种文本哈希。重复组、字节/汉字/总字符/行数见tmp/history_runs.json。不能将相同输出的多次保存当作独立试验，也不能仅凭哈希认定没有调用模型。全部23份做长度/哈希/标题扫描；人工按13种独立文本抽看开头非标题行，8月29日样本额外读完整章，其他未全篇审读。\n','## 8月29日：可见失败形态\n','源：run-20260829T102146Z-e38534f6/章节_CH01.md。L5开头重复表达走入检测场/观察；L13把检测器套到档案廊；L13–14将规则标签当故事事实。L7、L15和L23复用同一心理解释；L8、L16、L24用同一代价总结，造成三个场景节奏与声音趋同。真正需要保留的是各场独有的证据、关系代价、不可逆选择；不应靠加规则名字证明使用。下列自产正文引文合计不足400字：\n','> 观察_识别_场景_机会在栖云宗外门检测场中改变了沈砚对线索的判断。（L5）\n> 嫉妒_重度在栖云宗藏卷阁档案廊中改变了沈砚对线索的判断。（L14）\n> 对方若答得太快，便是在替谁守门；若答得太慢，也一样。（L7，另见L15/L23）\n','## Cline逐段时间线：改动—问题—可成立结论\n','以下“称/报告”均为历史文字证词，未用缺失的工具输出补造验证。每段首用户短引文保留直接需求证据；报告中的路径是当前导出路径，正文内旧D盘路径不代表今天仍存在。\n']
for i,(l,s,n) in enumerate(zip(logs,samples,notes),1):
 report.append(f'### {i:03d} {Path(l["path"]).name}\n\n源：`{l["path"]}`。全量结构：{l["messages"]}消息（用户{l["users"]}、Cline {l["cline"]}），{l["lines"]}行。\n\n{n}\n')
 for z in s['samples']:
  quote=re.sub('<[^>]*>','',re.sub(r'\s+',' ',z['text'])).strip()[:90].replace('|','／')
  report.append(f'- {z["role"]} #{z["id"]} L{z["line"]}：{quote}…')
report+=['\n## 四类原因及证据强度\n','|类别|可确认的现象|因果边界|\n|---|---|---|\n|资料本体|018 L1963用户指出角色资料仍不全；L1987助手承认方法/指标/事实混杂|只能定位资料语义风险；未证明完整资料库普遍无用|\n|管道与上下文|017 L18495用户指出运行层未参与；L18547补6→8→9绑定；019 L49650纠正落盘层次；8/29规则ID入正文|直接支持传递/消费表达存在问题；新增绑定字段本身仍不是正确采用证据|\n|模型与调用|009 L12提及qwen2.5:7b首次请求停滞；010 L4966说明另一次正常返回但质量拒绝|连接故障、短输出、模型能力是不同变量；没有固定提示/种子/模型对照，不能归咎7B模型本身|\n|评估与工程过程|013 L12要求停止单段长度与marker补丁；014 L380只读与写入初始化冲突；011 L269错误工作区|门禁可能把格式合规当创作质量；历史记录证明需求/交接摩擦，不证明全部故障同因|\n','四类失败贡献比例：**无法估计**。缺完整失败事件分母、模型原始请求/响应、每次代码版本、共同输入和独立盲评；四类原因还能共现。既不分配因果百分比，也不将关键词频率当责任占比。可确定优先级：先保证输入、生成、接受证据闭环；再以同一模型做资料消融；最后才判断模型升级收益。\n','## 10月29日盲测解释\n','源：03_运行资料/写作实验/2026-10-29_第七息回亮_盲测.md L3–13：同场景，一版最小简介，另一版增加六条规则，作者选版本一，文档自述并非严格对照。该结果只支持“这个场景、这次提示方式、这位读者更喜欢无规则版”。不支持“六大资料无价值”，也不支持“多规则一定更好”。文档没有足以复核每次调用的模型版本/采样参数/完整请求与时间戳，模型同一性属于记录声明。\n','建议下次固定场景、模型、参数、长度预算和基础提示，改变一个规则组，随机展示并保存原始输入输出；先由作者盲选再揭晓，记录因果推进、人物选择、潜台词、规则泄漏、重读意愿及修改时间。对多个场景重复；不以封存码代替独立重复。07新框架已提供相应记录工具，但尚未给出真实模型效果证据。\n','## 新框架v0：实际结构、命令、数据和验证边界\n','README L3称M0–M4已实现，本文静态解析src/nw全部Python源，未执行。模块职责如下。\n','|模块|源文件与入口|质量作用/边界|\n|---|---|---|\n|CLI|src/nw/cli.py L106–158|init、brief、bible add/list、outline chapter/scene、write、review、accept、runs、show、flow run/resume、ab start/show/choose/reveal；命令存在不等于真人认可|\n|存储|schema.py L6–76、store.py|SQLite版本/草稿/接受指针；阻止把失败输出当正式正文|\n|模型|llm/base.py、ollama.py、openai_compat.py、fake.py、transport.py|适配真实/本地与测试服务；fake不是文学能力测试|\n|生成|generation.py|记录输入与Run输出，失败/截断分流|\n|流程|flow/nodes.py L9–43、engine.py|N1需求、N2设定、N3场景、N4上下文、N5写审修、N6接受；有限修订与恢复|\n|上下文|context/minimal.py、rules_pack.py、registry.py|最小材料+按标签选六条规则；未等于六大资料检索|\n|实验|experiments/ab.py|持久化顺序、选择和揭晓；检验规则增益的工具，而非已有增益|\n','数据库建表全量提取：projects、briefs、bible_entries、chapters、scenes、runs、drafts、accepted、state_notes、run_outputs、flow_meta、flow_nodes、ab_experiments。schema版本迁移与不可变草稿机制在README L51–60有说明；DB与Markdown不是跨介质原子事务，SQLite是权威。该表清单来自schema.py静态扫描，不曾打开用户DB。\n','配置：config.example.toml L1–14的paths.workspace、model.provider/base_url/model/api_key_env/timeout、params.temperature。占位模型不能证明已经配置可用。密钥只从环境读取；本轮没有查看.env或个人密钥。运行命令示意：`python -m nw --project demo init --name 示例`、`python -m nw --project demo write --scene SCENE_ID --provider ollama`、`python -m nw --project demo ab start --scene SCENE_ID --a minimal --b rules_pack --seed 42`；仅记录，不执行。\n','测试情况：README L65起明确自动测试使用fake及本机模拟HTTP、未验证真实模型。tests目录有存储、生成、提供器、上下文、流程和A/B及CLI测试源；本轮只解析函数，不执行pytest、服务或模型。README“全部通过”是预期/历史声明，不能报告为本轮通过。StateNote仍由作者提供，未自动提取；多章记忆和六大资料检索留在后续范围。\n']
(O/'07_运行历史与失败归因.md').write_text('\n'.join(report),encoding='utf8')
with (O/'进度.md').open('a',encoding='utf8') as f:f.write('\n- 07完成：23正文全量结构/哈希、23 Cline全量消息结构及逐段抽样；覆盖率和未核实边界见07。未运行源项目。\n')
print('07 bytes',(O/'07_运行历史与失败归因.md').stat().st_size)
