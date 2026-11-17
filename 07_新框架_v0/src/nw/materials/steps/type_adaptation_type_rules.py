"""类型适配步骤的《类型系统》层级、报告或条件原文。"""

NAME_EVIDENCE_USE = (
    '按 type_name_evidence 回查前步采用的类型和题材身份。按照各来源自身模式解释。'
    'adaptations.type_refs 引用实际已选类型，parameters 只填写本项目确有的适配参数。'
    '近名机制的原义供核对。仅有类型或题材选择时先在 boundaries 保留机制待确认。'
    '项目明确采用机制后，依据该机制的确切原定义和当前人物、剧情或设定条件使用。'
)

MATERIAL = r"""#### 类型适配核对的类型动态冲突
【类型系统原文位置】类型动态冲突规则.json 第26990行
【各条共用原文值】{"detection":"report_only","auto_resolve":false,"severity":"error","schema_version":"TYPE_D-1.0.0"}
【本步用法】在实际项目产物上核对以下报告项，记录具体对象、时点、所涉字段及依据。原件规定 report_only，auto_resolve=false。报告按现有产物和待核说明保存。
【逐条原文值】conflict_id 原文行 | conflict_id | description | 本步核对
27051 | TDC_008 | 类型规则触发条件缺少类型选择 | 对照已经选择的类型与实际概念，报告动态适配缺失的选型依据。

#### 类型适配核对的动态触发条件
【类型系统原文位置】类型动态触发条件.json 第27171行
【各条共用原文值】{"expected_value":null,"source_id":null,"required":true,"negatable":true,"failure_behavior":"report_and_skip","status":"active"}
【本步用法】逐条保留 reference 身份，只有项目实际采用所属 rule_id 时才从已具备的前置核对。依该父规则内 evaluation_order 检查实际对象与原条件。比较值或证据缺失时记录待核，原 failure_behavior 为 report_and_skip，已成立的候选仍沿用本步现有验证和选择条件。
【逐条原文值】condition_id 原文行 | condition_id | rule_id | condition_kind | field | operator | evaluation_order | source_refs | evidence_type | confidence | 本步核对
27214 | TDC_0003 | TDR_TEMPLATE_002 | type_selected | type_id | equals | 0 | ["类型表达适配总表.json"] | template | 0 | 与类型选择步骤的实际 selection 核对模板所需的类型。
27233 | TDC_0004 | TDR_TEMPLATE_002 | concept_active | concept_id | exists | 1 | ["类型表达适配总表.json"] | template | 0 | 与上游 concepts 核对概念已在项目内激活及其依据。
27382 | TDC_0012 | TDR_002 | type_selected | type_id | equals | 0 | ["类型表达适配总表.json"] | inferred | 0.75 | 确认项目实际选择的类型及适配采用依据。
27401 | TDC_0013 | TDR_002 | concept_active | concept_id | exists | 1 | ["类型表达适配总表.json"] | inferred | 0.75 | 根据已激活的具体概念和 type_refs 核对关注重点。

【《类型系统》类型动态规则适配原始规则｜类型适配】
【原文位置】来源块第 28,192 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】适配原表全部为 pending_review，现行裁定均为 reference。先核对现有项目的已选类型、实际关注事项、原规则版本及两端源位。排序、范围及选择调整沿用原字段值。

28197｜reference｜{"adaptation_id":"TDA_001","type_rule_id":"TDR_001","original_rule_id":"C00001","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00001 是主角和核心悬念的绑定。核对其确切源位与本条身体状态传播所需的旧边，登记差异后确认选用范围。

28232｜reference｜{"adaptation_id":"TDA_002","type_rule_id":"TDR_002","original_rule_id":"C00002","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00002 涉及主角欲望。确认概念已激活及被调整的关注项，再核对原注是否所指同一条规则。

28267｜reference｜{"adaptation_id":"TDA_003","type_rule_id":"TDR_003","original_rule_id":"C00003","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00003 涉及主角执念。核对该适配所需实体状态与原边端点和条件是否对应，原排序调整保留零值。

28302｜reference｜{"adaptation_id":"TDA_004","type_rule_id":"TDR_004","original_rule_id":"C00004","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00004 涉及主角弧光。对照实际采用的前一事件及完成条件，核对本组旧编号是否指提供后继事件依据的规则。

28337｜reference｜{"adaptation_id":"TDA_005","type_rule_id":"TDR_005","original_rule_id":"C00005","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00005 涉及共鸣点。依据实际信息持有者及披露任务核对是否确有支持信息传播的原条，保留参考资格。

28372｜reference｜{"adaptation_id":"TDA_006","type_rule_id":"TDR_006","original_rule_id":"C00006","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00006 涉及重要配角亲缘。核对资源实体、已知转移路径与旧边正文是否一致，再确认检索适用范围。

28407｜reference｜{"adaptation_id":"TDA_007","type_rule_id":"TDR_007","original_rule_id":"C00007","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00007 涉及重要配角关系演变。复核双方、关系前值和源行，按本条原零值保留候选排序记录。

28442｜reference｜{"adaptation_id":"TDA_008","type_rule_id":"TDR_008","original_rule_id":"C00008","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00008 涉及重要配角的他人视角。用实际身份和知情边界核对原边条件是否能支持该适配，同时保留原空适用范围。

28477｜reference｜{"adaptation_id":"TDA_009","type_rule_id":"TDR_009","original_rule_id":"C00009","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00009 涉及次要配角的信息承载。按已发生的风险、升级条件和源条内容核对是否是所指历史规则。

28512｜reference｜{"adaptation_id":"TDA_010","type_rule_id":"TDR_010","original_rule_id":"C00010","adaptation_kind":"retrieval_priority_adjustment","allowed_modifications":["检索优先级","适用类型范围","候选效果排序","表达方式","场景相关性","资源或信息关注重点","规则是否需要人工确认"],"forbidden_modifications":["原始规则ID","原始规则正文","原始触发条件","原始效果","原始传播限制","原始来源","原始状态"],"priority_adjustment":0,"selection_adjustment":null,"scope_restriction":[],"source_refs":["动态网络连接.txt","类型动态规则总表.json"],"evidence_type":"inferred","confidence":0.6,"status":"pending_review","schema_version":"TYPE_D-1.0.0"}
【本步用法】当前同号 C00010 涉及次要配角的合作。核对本作冲突参与者、既有关系和两端原文，在证据能对应时登记适用范围。

【《类型系统》类型动态规则总表｜类型适配】
【原文位置】来源块第 28,706 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】按本步的实际前置、条目触发和外部选择条件判断用途。原条所列空值、候选范围和现行裁定随条保留。

28804｜reference｜{"rule_id":"TDR_TEMPLATE_002","rule_scope":"概念触发模板","rule_kind":"TYPE_CONCEPT_TRIGGER","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["身份概念","道德概念","关系概念"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["类型已选中","概念已激活"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_T002_E01","effect_kind":"attention_shift","description":"概念激活影响关注重点"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"unknown","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0,"status":"template","schema_version":"TYPE_D-1.0.0"}
【本步用法】项目已选类型且激活身份、道德或关系概念时，核对该概念所影响的实际关注重点，记录对应适配参数。

29257｜design_ready｜{"rule_id":"TDR_002","rule_scope":"类型概念触发动态规则适配","rule_kind":"TYPE_CONCEPT_TRIGGER","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["身份概念","关系概念","道德概念"],"trigger_entities":["人物","群体"],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["类型已选中","概念已被该类型环境激活"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_002_E01","effect_kind":"attention_shift","description":"概念激活重新分配关注优先级"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["类型表达适配总表.json"],"evidence_type":"inferred","confidence":0.75,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】用已选项目类型和实际激活的身份、关系或道德概念说明关注重点从哪里转向哪里，以及这种关注如何用于后续设计。

【《类型系统》类型动态候选效果｜类型适配】
【原文位置】来源块第 31,428 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】各候选效果随相应父规则核对本步状态或行动。原件的目标、字段和值均留空，现行裁定为 reference。用已具备的项目产物确定具体作用及可验证证据。

31466｜reference｜{"effect_id":"TDR_T002_E01","rule_id":"TDR_TEMPLATE_002","effect_kind":"attention_shift","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0,"status":"active"}
【本步用法】随已激活的概念对照当前关注变化，候选落点是实际关注对象和优先项。

31630｜reference｜{"effect_id":"TDR_002_E01","rule_id":"TDR_002","effect_kind":"attention_shift","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["类型表达适配总表.json"],"evidence_type":"inferred","confidence":0.75,"status":"active"}
【本步用法】以项目内已激活的具体概念为对象核对关注变化，保留它所影响的实际观察或取舍。

【《类型系统》类型动态筛选规则 TDF_001｜类型适配】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】按当前步骤的实际前置和已有产物落实适用的筛选动作，并保留原步骤编号及其现行裁定。

32455｜reference｜{"step":1,"action":"读取项目类型"}
【本步用法】只使用上游实际选定的项目类型和来源依据，核对与本步适配有关的条件。

32459｜reference｜{"step":2,"action":"读取子类型、混合类型和机制"}
【本步用法】沿用已选子类型、混合类型和机制的具体身份。以所涉项目目标和实际原义核对适用的候选。

32463｜reference｜{"step":3,"action":"读取叙事结构、风格和语气"}
【本步用法】读取作者已经明确的结构、风格和语气，按当前项目实际具备的写法要求核对本步适用条件。

32483｜reference｜{"step":8,"action":"读取当前概念"}
【本步用法】核对上游实际激活的概念、来源及其对应条件，写入本步有依据的关注变化。

【《类型系统》类型多样性策略的维度｜类型适配】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

32938｜reference｜{"id":"mechanism","name":"机制维度","weight":0.06}
【本步用法】对已有机制及其绑定目的核对作用方式可否变化，优先保留作者确认的条件和边界。

32943｜reference｜{"id":"structure","name":"结构维度","weight":0.06}
【本步用法】针对当前已采纳的结构和作者明确的目标比较可使用的结构特点及预期效果。

32948｜reference｜{"id":"style","name":"风格维度","weight":0.06}
【本步用法】依据当前写作任务和作者提供的风格条件比较可用的表达取向。作者尚未指定时保留可选择空间。

32953｜reference｜{"id":"concept","name":"概念维度","weight":0.06}
【本步用法】比较本次实际激活的概念及其影响的关注点，保留各候选的适用条件和具体作用。

【《类型系统》类型多样性策略的边界｜类型适配】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】在现有步骤核对候选的适用边界，并对照作者已确认的设定和前置产物。

33046｜"违反类型组合合法性"
【本步用法】按实际已选类型及本体中的组合限制核对变体所涉及的类型身份和适用范围。

【《类型系统》类型来源映射｜类型适配】
【原文位置】来源块第 35,204 行。每项前为对应条目的原件字段行。
【本步用法】本表的来源、目标编码和现行 reference 裁定随条保留。使用本场或本项目实际采用的类型、结构、机制与原定义核对映射，沿用作者确认的项目选择。

35785｜reference｜{"mapping_id":"MAP_0042","source_name":"修仙言情","source_type":"hybrid_standard","target_id":"HYBRID_XIANXIA_YANQING","mapping_type":"component","reason":"组合类型：['GENRE_XIANXIA', 'GENRE_YANQING']","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「混合类型.json」第 2,404 行。按作者实际采用的组合和分表所列 GENRE_XIANXIA、GENRE_YANQING 核对组件。把具体组件与组合来源写入现有适配依据。

35799｜reference｜{"mapping_id":"MAP_0043","source_name":"科幻悬疑","source_type":"hybrid_standard","target_id":"HYBRID_KEHUAN_XUANYI","mapping_type":"component","reason":"组合类型：['GENRE_KEHUAN', 'GENRE_XUANYI']","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「混合类型.json」第 2,447 行。按作者实际采用的组合和分表所列 GENRE_KEHUAN、GENRE_XUANYI 核对组件。总表同 ID 的名称为「科幻背景中的悬疑」，依其原义确认本次使用的组合。

35813｜reference｜{"mapping_id":"MAP_0044","source_name":"都市悬疑","source_type":"hybrid_standard","target_id":"HYBRID_DUSHI_XUANYI","mapping_type":"component","reason":"组合类型：['GENRE_DUSHI', 'GENRE_XUANYI']","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「混合类型.json」第 2,490 行。按作者实际采用的组合和分表所列 GENRE_DUSHI、GENRE_XUANYI 核对组件。总表同 ID 的名称为「都市背景中的悬疑」，依其原义确认本次使用的组合。

35827｜reference｜{"mapping_id":"MAP_0045","source_name":"穿越历史","source_type":"hybrid_standard","target_id":"HYBRID_CHUANYUE_LISHI","mapping_type":"component","reason":"组合类型：['GENRE_CHUANYUE', 'GENRE_LISHI']","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「混合类型.json」第 2,532 行。此处的「穿越历史」是混合型，原组件为 GENRE_CHUANYUE 和 GENRE_LISHI。另有 MAP_0032 的同名子类型，核对作者所采用的结构与组件依据。

35841｜reference｜{"mapping_id":"MAP_0046","source_name":"玄幻末世","source_type":"hybrid_standard","target_id":"HYBRID_XUANHUAN_MORI","mapping_type":"component","reason":"组合类型：['GENRE_XUANHUAN', 'GENRE_MORI']","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.85,"status":"active"}
【本步用法】原目标见《类型系统》内「混合类型.json」第 2,576 行。组件原记录含 GENRE_MORI，现行总表采用 GENRE_MOSHI 标识末世。依各自原件定义与已选组件核对组合。

35855｜reference｜{"mapping_id":"MAP_0047","source_name":"成长机制","source_type":"mechanism_standard","target_id":"MECHANISM_GROWTH","mapping_type":"normalized","reason":"标准化机制：成长机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,139 行。「成长机制」用于识别本步实际采用的机制名称。比较项目已确认的能力提升、累积过程及阶段成长条件。总表同名编码 PLOT_MECHANISM_GROWTH 依确切原义分别回查。

35869｜reference｜{"mapping_id":"MAP_0048","source_name":"资源积累机制","source_type":"mechanism_standard","target_id":"MECHANISM_RESOURCE_ACCUMULATION","mapping_type":"normalized","reason":"标准化机制：资源积累机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,174 行。「资源积累机制」用于识别本步实际采用的机制名称。根据项目已有资源取得和消耗途径核对积累成立的条件。

35883｜reference｜{"mapping_id":"MAP_0049","source_name":"信息差机制","source_type":"mechanism_standard","target_id":"MECHANISM_INFORMATION_GAP","mapping_type":"normalized","reason":"标准化机制：信息差机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,207 行。「信息差机制」用于识别本步实际采用的机制名称。按作品已定信息持有者和可知范围核对实际信息差用途。

35897｜reference｜{"mapping_id":"MAP_0050","source_name":"身份反转机制","source_type":"mechanism_standard","target_id":"MECHANISM_IDENTITY_REVERSAL","mapping_type":"normalized","reason":"标准化机制：身份反转机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,241 行。「身份反转机制」用于识别本步实际采用的机制名称。按已设身份及揭示边界辨明此处设计是否采用身份反转。

35911｜reference｜{"mapping_id":"MAP_0051","source_name":"复仇机制","source_type":"mechanism_standard","target_id":"MECHANISM_REVENGE","mapping_type":"normalized","reason":"标准化机制：复仇机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,276 行。「复仇机制」用于识别本步实际采用的机制名称。依已设动机和事件目标核对当前选用的复仇机制。总表同名编码 PLOT_MECHANISM_REVENGE 依确切原义分别回查。

35925｜reference｜{"mapping_id":"MAP_0052","source_name":"逆袭机制","source_type":"mechanism_standard","target_id":"MECHANISM_COUNTERATTACK","mapping_type":"normalized","reason":"标准化机制：逆袭机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,310 行。「逆袭机制」用于识别本步实际采用的机制名称。核对现有起点、原阻碍及作者拟呈现的地位或能力变化。

35939｜reference｜{"mapping_id":"MAP_0053","source_name":"竞争机制","source_type":"mechanism_standard","target_id":"MECHANISM_COMPETITION","mapping_type":"normalized","reason":"标准化机制：竞争机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,343 行。「竞争机制」用于识别本步实际采用的机制名称。依据既有竞争对象、共同争夺目标及项目规则核对本次采用。

35953｜reference｜{"mapping_id":"MAP_0054","source_name":"收集机制","source_type":"mechanism_standard","target_id":"MECHANISM_COLLECTION","mapping_type":"normalized","reason":"标准化机制：收集机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,375 行。「收集机制」用于识别本步实际采用的机制名称。从已定目标对象和可回查的取得条件确认采用的收集机制。

35967｜reference｜{"mapping_id":"MAP_0055","source_name":"任务机制","source_type":"mechanism_standard","target_id":"MECHANISM_QUEST","mapping_type":"normalized","reason":"标准化机制：任务机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,407 行。「任务机制」用于识别本步实际采用的机制名称。依项目已有任务、触发及完成可核依据确认筛选用途。

35981｜reference｜{"mapping_id":"MAP_0056","source_name":"奖励机制","source_type":"mechanism_standard","target_id":"MECHANISM_REWARD","mapping_type":"normalized","reason":"标准化机制：奖励机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,438 行。「奖励机制」用于识别本步实际采用的机制名称。按原有兑现条件和已知后果核对实际所需的奖励机制。

35995｜reference｜{"mapping_id":"MAP_0057","source_name":"危机升级机制","source_type":"mechanism_standard","target_id":"MECHANISM_CRISIS_ESCALATION","mapping_type":"normalized","reason":"标准化机制：危机升级机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,470 行。「危机升级机制」用于识别本步实际采用的机制名称。用当前已存在危机、原触发及可回查的升级条件确认用途。

36009｜reference｜{"mapping_id":"MAP_0058","source_name":"误会和澄清机制","source_type":"mechanism_standard","target_id":"MECHANISM_MISUNDERSTANDING","mapping_type":"normalized","reason":"标准化机制：误会和澄清机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,502 行。「误会和澄清机制」用于识别本步实际采用的机制名称。在既有信息差及实际澄清渠道存在时核对所选机制。

36023｜reference｜{"mapping_id":"MAP_0059","source_name":"关系推进机制","source_type":"mechanism_standard","target_id":"MECHANISM_RELATIONSHIP","mapping_type":"normalized","reason":"标准化机制：关系推进机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,536 行。「关系推进机制」用于识别本步实际采用的机制名称。按真实关系双方及已设互动事件核对推进方式是否对应此原义。

36037｜reference｜{"mapping_id":"MAP_0060","source_name":"谜团揭示机制","source_type":"mechanism_standard","target_id":"MECHANISM_MYSTERY","mapping_type":"normalized","reason":"标准化机制：谜团揭示机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,568 行。「谜团揭示机制」用于识别本步实际采用的机制名称。依据现有谜团与已立证据核对实际揭示需求。

36051｜reference｜{"mapping_id":"MAP_0061","source_name":"伏笔回收机制","source_type":"mechanism_standard","target_id":"MECHANISM_FORESHADOW_RECOVERY","mapping_type":"normalized","reason":"标准化机制：伏笔回收机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,600 行。「伏笔回收机制」用于识别本步实际采用的机制名称。根据已有伏笔及可回查埋设、回收节点确认该机制的作用。

36065｜reference｜{"mapping_id":"MAP_0062","source_name":"阶段目标机制","source_type":"mechanism_standard","target_id":"MECHANISM_STAGE_GOAL","mapping_type":"normalized","reason":"标准化机制：阶段目标机制","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「爽文机制.json」第 469,632 行。「阶段目标机制」用于识别本步实际采用的机制名称。在作者确认的阶段任务、达成条件与后续承接上核对本项。

36079｜reference｜{"mapping_id":"MAP_0063","source_name":"线性推进","source_type":"structure_standard","target_id":"STRUCTURE_LINEAR","mapping_type":"normalized","reason":"标准化叙事结构：线性推进","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,719 行。「线性推进」按作者已确认的写法或本步原定结构使用。比较当前选定剧情是否按实际时间顺序向前承接。

36093｜reference｜{"mapping_id":"MAP_0064","source_name":"多线并行","source_type":"structure_standard","target_id":"STRUCTURE_MULTILINE","mapping_type":"normalized","reason":"标准化叙事结构：多线并行","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,742 行。「多线并行」按作者已确认的写法或本步原定结构使用。按已设多个线索或主支线的前后关系核对各线并行条件。

36107｜reference｜{"mapping_id":"MAP_0065","source_name":"倒叙","source_type":"structure_standard","target_id":"STRUCTURE_FLASHBACK","mapping_type":"normalized","reason":"标准化叙事结构：倒叙","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,767 行。「倒叙」按作者已确认的写法或本步原定结构使用。已有先呈现的结果或关键场景及回溯范围时核对实际采用的结构。

36121｜reference｜{"mapping_id":"MAP_0066","source_name":"插叙","source_type":"structure_standard","target_id":"STRUCTURE_INTERSPERSED","mapping_type":"normalized","reason":"标准化叙事结构：插叙","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,789 行。「插叙」按作者已确认的写法或本步原定结构使用。依已定主叙事时序与插入事件的作用核对该项的适用性。

36135｜reference｜{"mapping_id":"MAP_0067","source_name":"视角轮换","source_type":"structure_standard","target_id":"STRUCTURE_VIEWPOINT_ROTATION","mapping_type":"normalized","reason":"标准化叙事结构：视角轮换","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,811 行。「视角轮换」按作者已确认的写法或本步原定结构使用。按实际轮换的视角及已确定的披露范围核对采用依据。

36149｜reference｜{"mapping_id":"MAP_0068","source_name":"限制视角","source_type":"structure_standard","target_id":"STRUCTURE_LIMITED_POV","mapping_type":"normalized","reason":"标准化叙事结构：限制视角","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,836 行。「限制视角」按作者已确认的写法或本步原定结构使用。以当前人物的所知及允许表达边界来确认限制视角的采用。

36163｜reference｜{"mapping_id":"MAP_0069","source_name":"多视角拼图","source_type":"structure_standard","target_id":"STRUCTURE_MOSAIC","mapping_type":"normalized","reason":"标准化叙事结构：多视角拼图","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,859 行。「多视角拼图」按作者已确认的写法或本步原定结构使用。明确多个视角分别持有的实际信息及需要拼合的已定内容。

36177｜reference｜{"mapping_id":"MAP_0070","source_name":"非可靠叙述","source_type":"structure_standard","target_id":"STRUCTURE_UNRELIABLE","mapping_type":"normalized","reason":"标准化叙事结构：非可靠叙述","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,882 行。「非可靠叙述」按作者已确认的写法或本步原定结构使用。按项目已设叙述者与能够核对的信息差或失实范围确认适用。

36191｜reference｜{"mapping_id":"MAP_0071","source_name":"时间循环","source_type":"structure_standard","target_id":"STRUCTURE_TIME_LOOP","mapping_type":"normalized","reason":"标准化叙事结构：时间循环","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,906 行。「时间循环」按作者已确认的写法或本步原定结构使用。以实际已设循环条件、起点及出口核对是否采用这一叙事结构。

36205｜reference｜{"mapping_id":"MAP_0072","source_name":"框架叙事","source_type":"structure_standard","target_id":"STRUCTURE_FRAME","mapping_type":"normalized","reason":"标准化叙事结构：框架叙事","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,930 行。「框架叙事」按作者已确认的写法或本步原定结构使用。依据已经成立的外层叙事及内层事件范围核对本项目结构。

36219｜reference｜{"mapping_id":"MAP_0073","source_name":"单元剧结构","source_type":"structure_standard","target_id":"STRUCTURE_EPISODIC","mapping_type":"normalized","reason":"标准化叙事结构：单元剧结构","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,952 行。「单元剧结构」按作者已确认的写法或本步原定结构使用。按现有单元目标及其与整部作品承接关系核对适用。

36233｜reference｜{"mapping_id":"MAP_0074","source_name":"任务链结构","source_type":"structure_standard","target_id":"STRUCTURE_QUEST_CHAIN","mapping_type":"normalized","reason":"标准化叙事结构：任务链结构","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,976 行。「任务链结构」按作者已确认的写法或本步原定结构使用。用已设任务序列和完成后接续关系核对是否采用任务链。

36247｜reference｜{"mapping_id":"MAP_0075","source_name":"调查揭谜结构","source_type":"structure_standard","target_id":"STRUCTURE_INVESTIGATION","mapping_type":"normalized","reason":"标准化叙事结构：调查揭谜结构","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 469,998 行。「调查揭谜结构」按作者已确认的写法或本步原定结构使用。根据已定问题、调查顺序及可回查线索范围核对已选结构。

36261｜reference｜{"mapping_id":"MAP_0076","source_name":"群像结构","source_type":"structure_standard","target_id":"STRUCTURE_ENSEMBLE","mapping_type":"normalized","reason":"标准化叙事结构：群像结构","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 470,022 行。「群像结构」按作者已确认的写法或本步原定结构使用。按已建立的多个人物中心、行动线索及相互依存关系核对采用。

36275｜reference｜{"mapping_id":"MAP_0077","source_name":"章节反转结构","source_type":"structure_standard","target_id":"STRUCTURE_CHAPTER_TWIST","mapping_type":"normalized","reason":"标准化叙事结构：章节反转结构","source_refs":["web_novel_taxonomy_standard"],"evidence_type":"template","confidence":0.9,"status":"active"}
【本步用法】原目标见《类型系统》内「特殊叙事结构.json」第 470,046 行。「章节反转结构」按作者已确认的写法或本步原定结构使用。依据现有章目标、此前证据与计划中转折的具体作用核对。

【《类型系统》类型枚举的类型身份｜类型适配】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【本步用法】以下名称及前缀来自 TYPE_A-1.0.0，对照当前条目所属原件核对。项目使用的 ID、类别和层级沿用各自已确认的本体定义。

36355｜{"TROPE_MECHANISM":{"description":"爽文/叙事机制","id_prefix":"MECHANISM_"}}
【本步用法】识别当前已采用的叙事机制及来源模式，记录名称、ID 和作用范围。

36359｜{"NARRATIVE_STRUCTURE":{"description":"特殊叙事结构","id_prefix":"STRUCTURE_"}}
【本步用法】依已确认结构和其所属原表识别 ID、叙事用途与规定范围。

36363｜{"STYLE":{"description":"写作风格","id_prefix":"STYLE_"}}
【本步用法】作者已指定风格时，核对其写法类别、来源与实际适用范围。

36367｜{"TONE":{"description":"情绪/语气基调","id_prefix":"TONE_"}}
【本步用法】对照实际指定的语气或基调及应体现的范围，保留对应原身份。

【《类型系统》类型枚举的映射类型｜类型适配】
【原文位置】来源块第 36,337 行。每项前为对应条目的原件字段行。
【本步用法】以实际名称、规则、原件和项目产物为据记录所用映射的身份、条件与边界。

36392｜"component"
【本步用法】在已选组合上逐个回查组成成员、原定义及其作用。

36393｜"inferred"
【本步用法】按已确认项目范围说明推断映射的依据和仍待核的实际条件。

【《类型系统》类型适配冲突规则｜类型适配】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38216｜reference｜{"conflict_rule_id":"CONFLICT_B_001","rule_name":"类型间表达权重冲突","category":"type_expression_conflict","description":"当多个被选类型对同一概念给出冲突的表达权重时，检测并报告","input_fields":["type_ids","concept_id","expression_weights"],"warning_condition":"两个以上类型对同一概念的表达权重差异超过0.4","fail_condition":"权重冲突且无法通过优先级解决","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】对同一已激活概念上的实际权重逐项核对差值和优先级依据，按原件的 0.4 阈值及失败条件记录具体冲突。

38387｜reference｜{"conflict_rule_id":"CONFLICT_B_010","rule_name":"类型适配试图覆盖通用概念底层逻辑","category":"type_concept_override","description":"当类型适配试图修改通用概念的底层定义时检测","input_fields":["type_id","concept_id","concept_definition"],"warning_condition":"类型适配包含概念定义修改","fail_condition":"概念底层逻辑被修改","severity":"fail","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】回查已采用的通用概念定义及此次的适配参数，指出修改底层定义所涉及的具体字段和实际依据。

【《类型系统》类型验证规则｜类型适配】
【原文位置】来源块第 40,879 行。条目前缀为 ID 字段的物理原件行。
【本步用法】按本步实际对象及证据核对适用的原验收项。涉及旧阶段 A、备份、文件清单或原测试的条目，按相应阶段和资料维护范围核对已有记录。

40916｜reference｜{"test_id":"TA07","test":"混合类型组件引用存在","check":"hybrid_components_valid"}
【本步用法】回查实际采用混合类型的各成员及其原定义、ID 和对当前项目的作用。

40971｜reference｜{"test_id":"TA18","test":"叙事结构不会当成爽文机制","check":"structure_not_mechanism"}
【本步用法】依据项目所用原定义及类别字段核对已采用叙事结构、机制各自的用途。

40976｜reference｜{"test_id":"TA19","test":"类型对象包含not_guaranteed字段","check":"has_not_guaranteed"}
【本步用法】回查本步实际采用类型对象中的 not_guaranteed 及其与拟用参数的关系。

【《类型系统》类型字段说明｜类型适配】
【原文位置】来源块第 42,359 行。条目前缀为对应字段的原件行。
【本步用法】使用本表说明核对采用 TYPE_A-1.0.0 的字段。按该条所属的原模式和现有项目产物确认使用方式。

42452｜{"not_guaranteed":{"type":"array","description":"不能由此类型强制推出的内容","required":true}}
【本步用法】把原非保证边界随本次已采用的适配参数记录，候选用途依当前写作需要和前置产物确定。

【《类型系统》类型总表｜类型适配】
【原文位置】来源块第 42,543 行。条目前缀为对应字段的原件行。
【本步用法】核对 TYPE_A-1.0.0 原总表以及当前采用条目的名单、层级和计数范围。原件 all_type_ids 起于第 42,563 行，其 103 个 ID 与各层级的成员及顺序一致。

42734｜{"level_4_mechanism":{"description":"爽文机制层：TROPE_MECHANISM","items":["MECHANISM_GROWTH","MECHANISM_RESOURCE_ACCUMULATION","MECHANISM_INFORMATION_GAP","MECHANISM_IDENTITY_REVERSAL","MECHANISM_REVENGE","MECHANISM_COUNTERATTACK","MECHANISM_COMPETITION","MECHANISM_COLLECTION","MECHANISM_QUEST","MECHANISM_REWARD","MECHANISM_CRISIS_ESCALATION","MECHANISM_MISUNDERSTANDING","MECHANISM_RELATIONSHIP","MECHANISM_MYSTERY","MECHANISM_FORESHADOW_RECOVERY","MECHANISM_STAGE_GOAL"]}}
【本步用法】按已有选型目标和项目实际采用的机制身份核对对应原成员及用法。

42755｜{"level_5_structure":{"description":"特殊叙事结构层：NARRATIVE_STRUCTURE","items":["STRUCTURE_LINEAR","STRUCTURE_MULTILINE","STRUCTURE_FLASHBACK","STRUCTURE_INTERSPERSED","STRUCTURE_VIEWPOINT_ROTATION","STRUCTURE_LIMITED_POV","STRUCTURE_MOSAIC","STRUCTURE_UNRELIABLE","STRUCTURE_TIME_LOOP","STRUCTURE_FRAME","STRUCTURE_EPISODIC","STRUCTURE_QUEST_CHAIN","STRUCTURE_INVESTIGATION","STRUCTURE_ENSEMBLE","STRUCTURE_CHAPTER_TWIST"]}}
【本步用法】对照本表列明的叙事结构原 ID、已采用的结构及其真实叙事用途。

42775｜{"level_6_style_tone":{"description":"风格和语气层：STYLE / TONE","styles":["STYLE_LANGUAGE","STYLE_VISUAL","STYLE_PACING","STYLE_DIALOGUE","STYLE_PSYCHOLOGICAL","STYLE_HUMOR","STYLE_REALISM","STYLE_DARKNESS","STYLE_EMOTION","STYLE_DESCRIPTION","STYLE_ACTION"],"tones":["TONE_TENSE","TONE_COLD","TONE_WARM","TONE_HUMOROUS","TONE_SAD","TONE_EPIC","TONE_MYSTERIOUS","TONE_RELAXED","TONE_OPPRESSIVE"]}}
【本步用法】在作者已经给出风格或语气选择时，按对应列表、原定义和采用理由核对适配范围。

【《类型系统》类型组合约束｜类型适配】
【原文位置】来源块第 42,867 行。条目前缀为对应字段的原件行。
【原文属性】{"schema_version":"TYPE_A-1.0.0","updated_at":"2026-07-31T09:42:37.831980"}
【本步用法】按当前选型、适配产物和正式来源证据核对原组合约束。原严重程度及现行参考裁定随条保留。

42874｜reference｜{"constraint_id":"CC01","constraint":"一个项目可以有1个或多个主类型，但必须记录权重","severity":"warning"}
【本步用法】项目实际采用多个主类型时，核对作者已确认的权重和采用依据，在现有适配参数或说明中保存。原件无具体权重时保留待核。

42884｜reference｜{"constraint_id":"CC03","constraint":"混合类型必须引用至少2个类型组件","severity":"error"}
【本步用法】核对已采用的混合类型成员、各自来源及原件要求的最低组件数量。
"""
