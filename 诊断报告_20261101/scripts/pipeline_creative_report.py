from pathlib import Path
import json
R=Path(r'D:\搭建');O=Path(r'D:\诊断报告_20261101');C=R/'03_运行资料/配置'
def load(n):return json.loads((C/n).read_text(encoding='utf-8-sig'))
c=load('project_config.json');b=load('项目创作圣经.json');tp=load('类型配置模板.json');brief=load('首章场景创作简报.json');sc=[s for ch in c['chapter_plan'] for s in ch['scenes']];beats=[x for s in sc for x in s.get('action_chain',[])]
nums={'chapters':len(c['chapter_plan']),'scenes':len(sc),'beats':len(beats),'authored_prose':sum(bool(x.get('prose')) for x in beats),'volumes':len(b['series_arc']),'characters':len(b['characters']),'types':len(tp['types']),'combinations':len(tp['combinations'])};(O/'tmp/pipeline_creative_counts.json').write_text(json.dumps(nums,ensure_ascii=False,indent=2),encoding='utf-8')
s=f'''# 06 创作设计资料：已有故事、实际消费与缺口

## 现状结论

当前不是空白项目：配置已保存《潮痕入骨》的世界、主角、主冲突与谜团，并有首章设计；但不能认定为完整小说生产系统。project_config只规划 {nums['chapters']} 章、{nums['scenes']} 场、{nums['beats']} 个行动节点，现存节点正文prose字段非空数为 {nums['authored_prose']}，目标总字数为 {c['target_words']}。圣经有 {nums['volumes']} 卷的简要弧线与 {nums['characters']} 个具名角色；类型模板有 {nums['types']} 种类型、{nums['combinations']} 项组合。数字由 `scripts/pipeline_creative_report.py` 计算，保存 `tmp/pipeline_creative_counts.json`；源：`03_运行资料/配置/project_config.json:27–181`、`项目创作圣经.json:31–97`、`类型配置模板.json:12–1654`（后三处同配置目录）。

“有卷弧线”不等于“有全书逐章大纲”。此外 `03_运行资料/文档/创作设计/` 下候选创作圣经、卷章蓝图、第一章场景卡、第一章最小资料包与授权申请、BATCH质量量规与审校状态机的现存文件全为NUL字节，不能解析；不可按文件名给它们评为已完成。逐文件字节/行证据见06A与 `tmp/pipeline_design_metrics.json`；损坏文件只有字节证据，虚拟行定位为:1，无法给出有意义的内容行。

## 资料各自的职责

| 资料 | 字段与例子 | 实际使用与边界 |
|---|---|---|
| project_config.json | project_id、creation_mode、类型、目标规模、protagonist、chapter_plan | 主事实与场景输入，模块01、04、05、06、08、09、10均读取；管道:1662–1704、1831–2202、2211–3336 |
| 项目创作圣经.json | authorial_draft；世界、阵营、具名人物、series_arc | BIBLE列入输入清单并做哈希；现存管道未把其characters/series_arc解码进入写手上下文，见管道:52、88、191、3465、3481；因此“声明输入”与“语义消费”有缺口 |
| 首章场景创作简报.json | creative_need、stage、required_source_kinds、retrieval_terms、activation_evidence | 模块06读取并决定场景动态链需求，模块08按创作需求激活；管道:2119–2145、2211–2630 |
| 类型配置模板.json | core_elements、style_constraints、source_ref、组合 | 初始化复制已选类型资料；世界设定把核心元素/风格约束作为筛边关键词；初始化:123–134，管道:1848–1868 |
| 项目创作生产政策.json | creation_modes、来源分类、required_strategy_fields、hard_boundaries | 模式约束与策略字段验证；脚本`项目创作生产政策.py:10–63`，不是小说设计内容 |
| 资源注册表（运行生成） | status、relative_path、sha256、bytes、item_or_line_count、source_quality | `资料注册与完整性.py:110–194`；解析与来源等级检查，不等于文学采用 |
| 启动绑定合同（运行生成） | project_id、author_input、genre_selection、source_registration、blocking_reasons | 管道:1348–1395；确认身份与资源类别齐备，未证明所有来源转成正文 |

本表脚本均相对于 `03_运行资料/脚本/`。06A按字段路径列出现存配置值和候选源行号，重复键靠完整JSON路径消歧。字段样例保持原值；没有把 authorial_draft、draft_only、not_confirmed改写为已确认。配置中的story_core_confirmation仍pending，formal_release_allowed为false（`03_运行资料/配置/project_config.json:19–37`）。

## 故事和人物实际承担什么

圣经的中心冲突是秩序以隐秘牺牲维持多数人稳定，能力代价是追听回声损失至亲记忆。它提供了价值选择和可持续冲突，而不只提供“升级变强”；但当前主流程主要消费project_config中的摘录，未发现完整圣经角色/分卷内容进入写手的调用链（`03_运行资料/配置/项目创作圣经.json:5–17`；管道:2035–2087、2647–2667）。

| 人物 | 剧情作用与内在矛盾 | 证据 |
|---|---|---|
| 沈砚 | 视角与调查发动者；晋升换遗物的现实目标与揭露阵法冲突，独自取证会牵连盟友 | 圣经:32–41；配置:41–64 |
| 陆昭 | 室友兼竞争者；为妹妹药额依赖制度，使“查真相”具有关系代价；首章遮挡视线但要求别牵连 | 圣经:42–48 |
| 许照微 | 档案线索入口与潜在盟友；兄长被抹去驱动越权，规则话术与暗助并存 | 圣经:49–55 |
| 闻执衡 | 知情守序者；以师父仍在阵中为理由维持封锁，承担反方伦理立场 | 圣经:56–61 |

此表“圣经”指 `03_运行资料/配置/项目创作圣经.json`，“配置”指同目录project_config.json。上表为已有作者草案的解释，不声称角色已在正文中充分实现。模块06只给主角配置专属欲望/执念，其余角色从资料库角色名生成并标unconfigured（管道:2053–2087）；因此具名配角圣经与运行角色表之间缺少显式映射。

## 大纲、细纲、场景卡与正文究竟由谁生成

初始化器接收类型、题材组合、字数和章节目标；把人物、书名、世界、冲突、谜团、chapter_plan留空（`03_运行资料/脚本/初始化小说项目.py:88–202`）。文档说后续project_planning应依据已选资料生成蓝图（`03_运行资料/docs/小说项目初始化.md:19`），这是工作流要求；现存 `项目规划.py:create` 实际接收外部draft JSON，检验章数/字数/来源后复制字段并写approved审批记录，没有模型生成调用（:78–122）。approved_by只是参数字符串，不能据此证明真人确已审读。

模块08依赖已写好的chapter_plan和场景行动链，进行来源筛选与装配；缺场景细纲直接报错（管道:2230–2241）。模块09又依赖beat.prose；缺文仅形成draft_request（:2794–2817）。所以当前缺的是“从选定资料与故事设计实际产出高质量草稿”的生成/作者输入环节，而不是再加一张状态表。人工或外部适配器必须提供草案与正文，但本次没有核实存在可调用的适配器。

## 创作能力：有、部分有、无可核实证据

| 能力 | 判定 | 实际证据和缺口 |
|---|---|---|
| 主线冲突与核心谜团 | 有草案 | project_config:39–40；圣经:5–17，事实确认未通过 |
| 全书方向 | 部分有 | 圣经series_arc:63–97提供各卷承诺、转折和终局选择；没有全书逐章计划 |
| 分卷设计 | 部分有 | 圣经:64–97有卷级摘要，不能核实卷章蓝图文件（全NUL） |
| 首章章纲/场景细纲 | 有草案 | project_config:66–181；简报:8–42明确创作需求；作者确认与发布分离 |
| 场景卡生成 | 有静态装配实现 | 管道:2211–2630把现有场景和来源形成卡片，不证明本次成功运行 |
| 伏笔 | 部分有 | 谜团/缺页/阵钥与后续卷转折见圣经:14–16、64–97；管道:2158只载入资料库伏笔规则，缺可核实全书埋设—误导—揭示—回收时间表 |
| 人物弧光 | 部分有 | 圣经:32–41含want/need/flaw，卷弧线有选择变化；无逐章角色状态演进验证，配角运行配置缺口见管道:2053–2087 |
| 字数控制 | 有数量约束，生成不足 | project_config:27–28、70；项目规划:89–95要求章数/预算总和匹配；管道:3148–3149检查落盘和目标下限，不负责扩写 |
| 文风 | 部分有 | 类型模板style_constraints；初始化:123–134；管道:1855把其作为检索关键词；无可核实样文驱动写作调用 |
| 章末钩子 | 部分有 | 场景hook/ending存在于project_config；管道:2603、2609读取chapter_end_hook但配置需检查是否提供该独立键；场景悬念不等于章节级承诺回收 |
| 正文自动生成 | 当前无可核实实现 | 管道:2799–2817仅消费外部prose；本配置非空prose计数见上 |
| 文学质量保证 | 部分规则，有明显不足 | 管道:3175、3192–3193、3211、3233–3239大量结构/关键词近似；来源合规不能替代文学判断 |

上表未带前缀的资料路径沿用前述配置目录或脚本目录；这是静态实现与现存数据判定，不是运行验收。

## 生产政策、绑定与来源层

政策区分generic_novel和project_bound。前者禁止project_fact/project_authorization/historical_artifact作为输入，后者允许项目事实与历史材料，但仍需来源层与职责检查（`03_运行资料/脚本/项目创作生产政策.py:16–63`）。所需策略字段为触发、可观察动作/结果、代价变化、语义锚点、证据位置和质量规则（:20–23）。这些字段适合强制“资料如何改变叙事”，不应当直接拼进正文。

政策JSON仍声明model_required_for_quality_candidate以及全量模型资料改进方案的契约/验证器路径（`03_运行资料/配置/项目创作生产政策.json:28–43`）；当前脚本目录没有对应模型生成入口，说明政策与实现能力存在脱节，不能用政策声明证明功能存在。授权是准入声明，消费需正文位置和结果；其边界在政策JSON:26及管道:273–326、2819以后都有静态实现。

## 参考资料现状与初始化落地

`04_参考资料/`现存只有README和文风样文README；前者说明设计对话仍保留在ACCOS目录供基线脚本使用，后者记录作者口味与未存仓库的参考开头（`04_参考资料/README.md:1–6`、`文风样文/README.md:1–7`）。这是历史说明，不是本报告已读取那些外部开头；不能据此复现文风。建议未来把“认可理由、适用类型、正反例的可公开摘要、句法/视角/节奏约束”变成版本化审校输入，仍须由作者确认。

初始化文档中的D盘旧位置只是示例（`03_运行资料/docs/小说项目初始化.md:5–12`），不能照抄作为当前部署路径。现存初始化脚本会创建配置/证据/正文目录、类型选择清单与灵感回执；仅对目标不存在或为空、类型存在和规模正数进行约束（`03_运行资料/脚本/初始化小说项目.py:69–118、197–202`）。它不是完整运行资料拷贝器；新项目还须有资源注册所需的原始资料、索引、采用规则和来源深度证据（`资料注册与完整性.py:113–131`）。

## 覆盖与尚未核实

已对配置JSON、授权JSONL、设计目录文件与参考目录全部做字节/解析/字段扫描，完整字段样例见06A；对初始化、规划、生产政策、注册与主管道作静态关联。没有运行初始化、绑定、授权、写手或审批脚本；未将现存历史正文当作本次生成结果；未核实NUL形成时间与原因，也未尝试恢复。尤其不能把配置中的runtime_baseline_ready或author_confirmed_for_draft_only当作当前全链已通过。
'''
assert len(s.encode())<60000
(O/'06_创作设计资料.md').write_text(s,encoding='utf-8')
with (O/'进度.md').open('a',encoding='utf-8') as f:
 f.write('\n- 已完成 `06_创作设计资料.md`。\n- 生成纠正：早期06A误把授权JSONL展开为大量分片，已仅清理本代理自产06A并重新生成字段/完整性摘要；旧06A完成条目作废，以当前实际文件为准，原始资料未改。\n')
print(len(s.encode()),nums)
