"""静态关系、状态变化和状态传播步骤使用的作品资料库原文。"""

STATIC_MATERIAL = r"""
【作品资料库的静态连接模式】
【原文共用字段】{"schema_version":"TYPE_F-1.0.0","created_at":"2026-07-31T12:08:30.700982","fields":{"static_pattern_id":{"type":"string","prefix":"STATIC_PATTERN_","required":true},"pattern_kind":{"type":"string","required":true},"source_work_ids":{"type":"array","prefix":"WORK_","required":true},"type_ids":{"type":"array","required":false},"source_node_kinds":{"type":"array","required":false},"target_node_kinds":{"type":"array","required":false},"relation_type":{"type":"string","required":true},"stable_relation_description":{"type":"string","required":true},"compatible_contexts":{"type":"array","required":false},"incompatible_contexts":{"type":"array","required":false},"candidate_uses":{"type":"array","required":false},"not_guaranteed":{"type":"array","required":true},"similarity_features":{"type":"object","required":false},"source_refs":{"type":"array","required":false},"evidence_type":{"type":"string","default":"inferred","required":true},"confidence":{"type":"float","min":0,"max":1,"required":true},"status":{"type":"string","required":true}},"patterns":[],"total_patterns":0,"rule":"静态模式只能描述稳定结构，不得写成触发规则"}
【共用字段用法】本项目确有已采用并可回查的抽象模式时，先查其对应的两端、关系和相容条件，依已有人物、世界与类型选择核对适用性。以原有 relations 或下游 requirements 格式落到实际对象。patterns 为空表示当前原表没有模式实例。

【《类型系统》作品资料库\连接模式\场景结构静态模式.json｜SOURCE[434]｜原文第 651,803 行】
【原文块字段】{"schema_name":"场景结构静态模式","pattern_kind":"scene_structure_static"}
【本条用法】上游已有明确的场景空间、参与对象或布置时，比较本项目两端能否形成稳定结构。在 relations 写明实际端点和适用条件，供场景设计沿用。

【《类型系统》作品资料库\连接模式\静态模式总表.json｜SOURCE[438]｜原文第 652,440 行】
【原文块字段】{"schema_name":"静态模式总表","pattern_kind":"static_overview"}
【本条用法】从本项目已有场景、人物、资源或规则核对两端及相容条件。在 relations 记录稳定关系本身及生效范围，为后续场景取用。

【《类型系统》作品资料库\连接模式\类型静态模式.json｜SOURCE[440]｜原文第 652,741 行】
【原文块字段】{"schema_name":"类型静态模式","pattern_kind":"genre_static"}
【本条用法】依本项目已选类型、实际所属实体和各端适用范围回查稳定关系。只把对本项目成立的关系和明确的用途写入本步产物。

【《类型系统》作品资料库\连接模式\人物关系静态模式.json｜SOURCE[441]｜原文第 652,874 行】
【原文块字段】{"schema_name":"人物关系静态模式","pattern_kind":"character_relation_static"}
【本条用法】从上游现有人物及可回查的关系依据出发，写明两端身份、相容条件和实际有约束的稳定关系。

【《类型系统》作品资料库\连接模式\身份立场静态模式.json｜SOURCE[442]｜原文第 653,007 行】
【原文块字段】{"schema_name":"身份立场静态模式","pattern_kind":"identity_stance_static"}
【本条用法】依据当前相关人物可回查的身份、所属和立场范围，写出稳定的角色或组织关系，明确会限制哪个下游动作或场景。

【《类型系统》作品资料库\连接模式\物品作用静态模式.json｜SOURCE[443]｜原文第 653,140 行】
【原文块字段】{"schema_name":"物品作用静态模式","pattern_kind":"item_role_static"}
【本条用法】已有实体、物品和用途时，核对物品与持有者、场景或用途的稳定关联。消耗、转移或失效由对应的状态步骤按实际事件处理。

【《类型系统》作品资料库\连接模式\资源分布静态模式.json｜SOURCE[447]｜原文第 653,777 行】
【原文块字段】{"schema_name":"资源分布静态模式","pattern_kind":"resource_distribution_static"}
【本条用法】从本项目已有资源与区域、组织或持有者出发，记录哪些稳定分布和取得条件能由现有设定支撑，为世界或场景设计提供实际边界。
"""

DYNAMIC_COMMON = r"""
【作品资料库的动态连接模式】
【原文共用字段】{"schema_version":"TYPE_F-1.0.0","created_at":"2026-07-31T12:08:30.700982","fields":{"dynamic_pattern_id":{"type":"string","prefix":"DYNAMIC_PATTERN_","required":true},"pattern_kind":{"type":"string","required":true},"source_work_ids":{"type":"array","prefix":"WORK_","required":true},"type_ids":{"type":"array","required":false},"trigger_contexts":{"type":"array","required":false},"preconditions":{"type":"array","required":true},"candidate_changes":{"type":"array","required":false},"candidate_actions":{"type":"array","required":false},"candidate_reactions":{"type":"array","required":false},"information_effects":{"type":"array","required":false},"resource_effects":{"type":"array","required":false},"relationship_effects":{"type":"array","required":false},"identity_effects":{"type":"array","required":false},"foreshadowing_effects":{"type":"array","required":false},"failure_branches":{"type":"array","required":false},"alternative_branches":{"type":"array","required":false},"propagation_limits":{"type":"object","default":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12}},"not_guaranteed":{"type":"array","required":true},"source_refs":{"type":"array","required":false},"evidence_type":{"type":"string","default":"inferred","required":true},"confidence":{"type":"float","min":0,"max":1,"required":true},"status":{"type":"string","required":true}},"patterns":[],"total_patterns":0,"rules":["必须是抽象模式","不得复制作品原剧情","不得直接写入原始动态网络","不得覆盖类型系统D已有规则","不得引用待恢复[已移除规则引用]至[已移除规则引用]","不得自动生成固定行为","不得自动生成固定剧情结果","必须保留候选路径和失败路径","必须保留传播限制","必须经过类型系统D的验证规则"]}
【共用字段用法】只参考本项目已采用、来源和限制可核的抽象模式。根据当步实际事件、对象和条件选择可执行的候选、备用及失败路径。传播限制以本步的现行验证和项目已定范围为据，原表 3、5、12 的默认值可与现有类型动态传播限制核对。原禁引范围含移除标记，按现行适用资格与类型动态验证规则查实际来源。patterns 为空表示当前原表没有模式实例。
"""

TRANSITION_USES = r"""
【《类型系统》作品资料库\连接模式\关系变化动态模式.json｜SOURCE[437]｜原文第 652,272 行】
【原文块字段】{"schema_name":"关系变化动态模式","pattern_kind":"relationship_change_dynamic"}
【本条用法】在已有明确关系、人物选择和上游事件时，核对本场哪项关系属性会改变，写清前值、后值、行动原因、失败应对与后场延续。

【《类型系统》作品资料库\连接模式\状态变化动态模式.json｜SOURCE[445]｜原文第 653,441 行】
【原文块字段】{"schema_name":"状态变化动态模式","pattern_kind":"state_change_dynamic"}
【本条用法】沿上游事件、实体前状态和所选行动选择适用的状态变化候选。在 transitions 写明实际改变的属性、前后值、代价、失败路径和连续性。

【《类型系统》作品资料库\连接模式\资源变化动态模式.json｜SOURCE[446]｜原文第 653,609 行】
【原文块字段】{"schema_name":"资源变化动态模式","pattern_kind":"resource_change_dynamic"}
【本条用法】以项目已有资源、持有状态和实际事件为据，核对能否支撑获得、消耗或转移等变化。在 transitions 用原有前后值与因果格式体现本场影响。
"""

PROPAGATION_USES = r"""
【《类型系统》作品资料库\连接模式\动态模式总表.json｜SOURCE[435]｜原文第 651,936 行】
【原文块字段】{"schema_name":"动态模式总表","pattern_kind":"dynamic_overview"}
【本条用法】传播设计以已确认的根变化或带条件的上游变化方案为据，先核对可行动实体、触发上下文与所选外部行为，再决定是否保留真实可解释的传播候选。

【《类型系统》作品资料库\连接模式\伏笔传播动态模式.json｜SOURCE[436]｜原文第 652,104 行】
【原文块字段】{"schema_name":"伏笔传播动态模式","pattern_kind":"foreshadowing_propagation_dynamic"}
【本条用法】对当前伏笔已明确埋设或传递对象的场合，核对变化怎样影响后面可见的提示或回收条件，在候选里说明触达范围、未触达的分支与连续性。

【《类型系统》作品资料库\连接模式\类型动态模式.json｜SOURCE[439]｜原文第 652,573 行】
【原文块字段】{"schema_name":"类型动态模式","pattern_kind":"genre_dynamic"}
【本条用法】以实际选定的类型和项目中已成立的根变化为前置，比较该类型传播用法能否解决当前需求。在候选里记录行动者、目标和有条件的结果。

【《类型系统》作品资料库\连接模式\信息传播动态模式.json｜SOURCE[444]｜原文第 653,273 行】
【原文块字段】{"schema_name":"信息传播动态模式","pattern_kind":"information_propagation_dynamic"}
【本条用法】依人物已确认的所知和信息传递途径，核对哪个变化令消息可以传播、谁能触达以及候选失效条件。传播范围据实际行动与已有知情边界确定。
"""

TRANSITION_MATERIAL = '\n'.join((DYNAMIC_COMMON, TRANSITION_USES))
PROPAGATION_MATERIAL = '\n'.join((DYNAMIC_COMMON, PROPAGATION_USES))
