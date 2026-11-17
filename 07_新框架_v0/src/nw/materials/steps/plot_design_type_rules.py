"""剧情设计步骤的《类型系统》层级、报告或条件原文。"""
FORESHADOWING_USE = r"""本步采用《类型伏笔适配》时，依原句核对已有伏笔计划。
【《类型系统》类型伏笔适配的补充约束｜剧情设计】
【原文位置】来源块第 33,297 行。每项前缀为对应字段的物理原件行。
【本步用法】保留原字段 constraints.must_not。逐句区分禁止自动操作的边界与查验实际前置的要求。

33532｜"类型不得自动创建伏笔"
【本步用法】核对拟铺设伏笔的实际剧情节点与意图。类型倾向本身只供设计时判断。

33533｜"类型不得自动回收伏笔"
【本步用法】回查伏笔已安排的前文铺设、触发条件和本章回收证据。

33534｜"伏笔仍然需要建立事件或来源"
【本步用法】在现有伏笔计划上对应实际建立事件或信息来源，明确能回查的前文线索和预期。

"""


MATERIAL = r"""#### 剧情设计核对的动态触发条件
【类型系统原文位置】类型动态触发条件.json 第27171行
【各条共用原文值】{"expected_value":null,"source_id":null,"required":true,"negatable":true,"failure_behavior":"report_and_skip","status":"active"}
【本步用法】逐条保留 reference 身份，只有项目实际采用所属 rule_id 时才从已具备的前置核对。依该父规则内 evaluation_order 检查实际对象与原条件。比较值或证据缺失时记录待核，原 failure_behavior 为 report_and_skip，已成立的候选仍沿用本步现有验证和选择条件。
【逐条原文值】condition_id 原文行 | condition_id | rule_id | condition_kind | field | operator | evaluation_order | source_refs | evidence_type | confidence | 本步核对
27606 | TDC_0024 | TDR_012 | continuity_state | branch_available | exists | 0 | [] | template | 0.5 | 核对实际已有的分支或备选路径，使用当前作者选择及范围内的产物。
27674 | TDC_0028 | TDR_016 | foreshadowing_state | active | exists | 0 | ["因果验证规则.json"] | inferred | 0.55 | 沿已建立的伏笔及相关节点核对是否已生效，实际承接记录在 promise_plan。

【《类型系统》类型动态规则总表｜剧情设计】
【原文位置】来源块第 28,706 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】按本步的实际前置、条目触发和外部选择条件判断用途。原条所列空值、候选范围和现行裁定随条保留。

30501｜design_ready｜{"rule_id":"TDR_016","rule_scope":"伏笔状态变化适配","rule_kind":"TYPE_FORESHADOWING_CHANGE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":["设置伏笔","回收伏笔"],"preconditions":["伏笔存在","相关事件达成"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_016_E01","effect_kind":"foreshadowing_pressure","description":"伏笔提示但不自动回收"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"once","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["因果验证规则.json"],"evidence_type":"inferred","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有伏笔且对应事件已达成时，按实际伏笔、前置证据和可能回收的事件核对本次适合埋设、提醒或兑现的范围。

30590｜design_ready｜{"rule_id":"TDR_017","rule_scope":"节奏压力适配","rule_kind":"TYPE_PACING_PRESSURE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["节奏","进度"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["叙事进度可衡量"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_017_E01","effect_kind":"pacing_pressure","description":"节奏可加速或减速"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】本作已经有可检查的进度或节奏目标时，对照现有事件及信息顺序，确定该段确需加快或放缓的实际环节。

【《类型系统》类型动态候选效果｜剧情设计】
【原文位置】来源块第 31,428 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】各候选效果随相应父规则核对本步状态或行动。原件的目标、字段和值均留空，现行裁定为 reference。用已具备的项目产物确定具体作用及可验证证据。

32080｜reference｜{"effect_id":"TDR_016_E01","rule_id":"TDR_016","effect_kind":"foreshadowing_pressure","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["因果验证规则.json"],"evidence_type":"inferred","confidence":0.55,"status":"active"}
【本步用法】在现有伏笔计划中检查涉及哪项已立承诺和哪个候选揭示节点，证据补齐后再核对是否回收。

32113｜reference｜{"effect_id":"TDR_017_E01","rule_id":"TDR_017","effect_kind":"pacing_pressure","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】随具体事件进度、已有读者预期及节奏调整依据核对影响方向。

【《类型系统》类型动态筛选规则 TDF_001｜剧情设计】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】按当前步骤的实际前置和已有产物落实适用的筛选动作，并保留原步骤编号及其现行裁定。

32467｜reference｜{"step":4,"action":"读取当前章节目标"}
【本步用法】依据当前已立章目标与所选父方向核对本章真正要推进的事件或承诺。

32491｜reference｜{"step":10,"action":"读取已有事件和伏笔"}
【本步用法】回读已立事件节点和伏笔计划，定位本章目标可以承接的已有触发和兑现条件。

【《类型系统》类型动态筛选规则每场上限 TDF_001｜剧情设计】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】用已有场景或候选实际对应的实体、字段、时点和范围核对原上限。证据不足或计数所需产物未形成时，在本步已有说明中标明待核。

32544｜{"max_foreshadowing_candidates":5}
【本步用法】能定位到同一场景的已立伏笔候选按该场核对数量，引用实际设置或回收场。

【《类型系统》类型动态验证规则｜剧情设计】
【原文位置】来源块第 32,597 行。条目前缀是原件中的字段行。
【本步用法】按实际项目对象、已用资料和本步产物核对下列验证项，并将问题定位到已有产物和证据。原件规定 report_only=true、auto_fix_allowed=false。

32800｜reference｜{"validation_id":"TDV_023","check_description":"是否产生固定剧情结果","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】检查已选进展、角色选择和事件因果，指出仅依类型便固定剧情结果的候选及其失去的选择依据。

【《类型系统》类型多样性策略的维度｜剧情设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

32988｜reference｜{"id":"foreshadowing","name":"伏笔维度","weight":0.05}
【本步用法】用已立伏笔及承诺比较线索呈现、重复或回收节点的安排，保留其实际来源。

33023｜reference｜{"id":"pacing","name":"节奏维度","weight":0.03}
【本步用法】对照已有章目标、事件先后及释放时点，比较确有必要调整的叙事节奏。

""" + FORESHADOWING_USE + r"""【《类型系统》类型适配冲突规则｜剧情设计】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38235｜reference｜{"conflict_rule_id":"CONFLICT_B_002","rule_name":"类型和风格之间节奏冲突","category":"type_style_conflict","description":"当类型偏好与风格参数在节奏设置上冲突时检测","input_fields":["type_id","style_id","pacing_params"],"warning_condition":"类型要求的节奏与风格参数方向相反","fail_condition":"节奏冲突无法通过重新排序解决","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】对照项目已采用的类型偏好、作者指定风格及当前章场节奏，指出相反的方向和受影响的安排。

38349｜reference｜{"conflict_rule_id":"CONFLICT_B_008","rule_name":"类型和已有伏笔方向冲突","category":"type_foreshadowing_conflict","description":"当类型伏笔偏好与已有伏笔方向不一致时检测","input_fields":["type_id","foreshadowing_id","foreshadowing_direction"],"warning_condition":"类型偏好高密度伏笔但已有伏笔已饱和","fail_condition":"忽略已有伏笔强行添加新伏笔倾向","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】用已立伏笔、相关章场和回收计划核对适配提议的密度及方向，定位有证据的饱和或覆盖问题。

【《类型系统》类型验证规则｜剧情设计】
【原文位置】来源块第 40,879 行。条目前缀为 ID 字段的物理原件行。
【本步用法】按本步实际对象及证据核对适用的原验收项。涉及旧阶段 A、备份、文件清单或原测试的条目，按相应阶段和资料维护范围核对已有记录。

40991｜reference｜{"test_id":"TA22","test":"类型不会强制推出固定剧情结果","check":"no_forced_plot_outcome"}
【本步用法】以选定前因和人物决定核对已安排的结果，定位仅凭类型便确定结局的地方。
"""
