"""场景设计步骤的《类型系统》层级、报告或条件原文。"""
FORESHADOWING_DISCLOSURE_USE = r"""本场承接已采用《类型伏笔适配》的项目伏笔时，使用以下原句。
【《类型系统》类型伏笔适配的补充约束｜场景设计】
【原文位置】来源块第 33,297 行。每项前缀为对应字段的物理原件行。
【本步用法】按原句核对已有伏笔来源、信息传播路径或角色实际所知，用现有章场产物记录。

33535｜"信息仍然需要传播路径"
【本步用法】从本场已选行动和此前掌握者核对同一信息的传递渠道、接收者和获得时点。

33536｜"角色仍然可能误解、怀疑或拒绝相信"
【本步用法】按各角色实际所知区分听到的信息、对它的理解和是否相信，保留剧情已定的误解、疑虑及不接受的可能。

"""


MATERIAL = r"""#### 场景设计核对的类型动态冲突
【类型系统原文位置】类型动态冲突规则.json 第26990行
【各条共用原文值】{"detection":"report_only","auto_resolve":false,"severity":"error","schema_version":"TYPE_D-1.0.0"}
【本步用法】在实际项目产物上核对以下报告项，记录具体对象、时点、所涉字段及依据。原件规定 report_only，auto_resolve=false。报告按现有产物和待核说明保存。
【逐条原文值】conflict_id 原文行 | conflict_id | description | 本步核对
27027 | TDC_005 | 同一信息同时公开和隐藏 | 按同一信息、知情者和故事时点对照本场披露及隐藏安排，明确冲突所及范围。

#### 场景设计核对的动态触发条件
【类型系统原文位置】类型动态触发条件.json 第27171行
【各条共用原文值】{"expected_value":null,"source_id":null,"required":true,"negatable":true,"failure_behavior":"report_and_skip","status":"active"}
【本步用法】逐条保留 reference 身份，只有项目实际采用所属 rule_id 时才从已具备的前置核对。依该父规则内 evaluation_order 检查实际对象与原条件。比较值或证据缺失时记录待核，原 failure_behavior 为 report_and_skip，已成立的候选仍沿用本步现有验证和选择条件。
【逐条原文值】condition_id 原文行 | condition_id | rule_id | condition_kind | field | operator | evaluation_order | source_refs | evidence_type | confidence | 本步核对
27478 | TDC_0017 | TDR_005 | information_known | info_id | exists | 0 | [] | inferred | 0.65 | 核对本场信息的实际持有者、接收者、观察者及已知边界。
27640 | TDC_0026 | TDR_014 | continuity_state | event_in_progress | exists | 0 | [] | template | 0.5 | 按所选事件、动作与时序核对事件仍在进行，以及可能中断的位置。
27693 | TDC_0029 | TDR_017 | continuity_state | pacing_need | exists | 0 | [] | template | 0.5 | 核对已定节点、场景节拍及项目实际需要怎样调节速度。
27780 | TDC_0034 | TDR_022 | information_unknown | info_id | exists | 0 | [] | template | 0.55 | 对照实际人物所知和拟披露信息，写清当前尚未知的范围。

【《类型系统》类型动态规则总表｜场景设计】
【原文位置】来源块第 28,706 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】按本步的实际前置、条目触发和外部选择条件判断用途。原条所列空值、候选范围和现行裁定随条保留。

29532｜design_ready｜{"rule_id":"TDR_005","rule_scope":"信息在类型环境中的传播候选","rule_kind":"TYPE_INFORMATION_CHANGE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":["秘密","发现","知识"],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["信息被至少一个实体掌握","接收实体存在"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_005_E01","effect_kind":"information_exposure","description":"信息可能向特定接收者传播"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"inferred","confidence":0.65,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】信息已有实际持有者且接收者存在时，沿本场所选事件与行动核对传递渠道、接收方及当场允许披露的内容。

29797｜design_ready｜{"rule_id":"TDR_008","rule_scope":"身份在类型环境中的变化候选","rule_kind":"TYPE_IDENTITY_CHANGE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["身份概念","社会地位"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["身份暴露或伪装有条件变化"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_008_E01","effect_kind":"identity_pressure","description":"身份变化压力"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"once","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["类型表达适配总表.json"],"evidence_type":"inferred","confidence":0.65,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已选情节涉及暴露或掩藏既有身份时，核对哪些角色已知真相、当前线索和可披露事实，保留候选压力。

31022｜design_ready｜{"rule_id":"TDR_022","rule_scope":"揭示压力适配","rule_kind":"TYPE_REVEAL_PRESSURE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":["秘密","真相"],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["信息存在且部分条件满足"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_022_E01","effect_kind":"information_exposure","description":"秘密可能被揭示"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"once","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已知秘密或真相且揭示条件只部分满足时，按选定事件与人物所知安排当前能看到的线索和允许确认的内容。

【《类型系统》类型动态候选效果｜场景设计】
【原文位置】来源块第 31,428 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】各候选效果随相应父规则核对本步状态或行动。原件的目标、字段和值均留空，现行裁定为 reference。用已具备的项目产物确定具体作用及可验证证据。

31730｜reference｜{"effect_id":"TDR_005_E01","rule_id":"TDR_005","effect_kind":"information_exposure","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"inferred","confidence":0.65,"status":"active"}
【本步用法】核对稿面将向哪位既有接收者呈现哪段信息，以及既定渠道、视角可知边界与采用结果。

31823｜reference｜{"effect_id":"TDR_008_E01","rule_id":"TDR_008","effect_kind":"identity_pressure","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["类型表达适配总表.json"],"evidence_type":"inferred","confidence":0.65,"status":"active"}
【本步用法】按已有处境定位身份的可见线索与知情者。采用前核对场景中供辨认的信息和既定披露边界。

32270｜reference｜{"effect_id":"TDR_022_E01","rule_id":"TDR_022","effect_kind":"information_exposure","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active"}
【本步用法】根据当前信息、人物视角与披露条件核对可能揭出的那部分内容，保留尚未满足的条件。

【《类型系统》类型动态筛选规则 TDF_001｜场景设计】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】按当前步骤的实际前置和已有产物落实适用的筛选动作，并保留原步骤编号及其现行裁定。

32471｜reference｜{"step":5,"action":"读取当前场景目标"}
【本步用法】本步从上游事件和动作候选中确定本场安排后，按本场目标核对资料与场景完成条件的关系。

32487｜reference｜{"step":9,"action":"读取当前信息和资源"}
【本步用法】按已选事件读取参与者实际掌握的信息和本场能用的资源，保留视角、来源及披露限制。

【《类型系统》类型动态筛选规则每场上限 TDF_001｜场景设计】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】用已有场景或候选实际对应的实体、字段、时点和范围核对原上限。证据不足或计数所需产物未形成时，在本步已有说明中标明待核。

32541｜{"max_information_candidates":5}
【本步用法】在已选事件和明确的信息持有人、接收者范围内，核对本场确有的信息候选项。

【《类型系统》类型动态验证规则｜场景设计】
【原文位置】来源块第 32,597 行。条目前缀是原件中的字段行。
【本步用法】按实际项目对象、已用资料和本步产物核对下列验证项，并将问题定位到已有产物和证据。原件规定 report_only=true、auto_fix_allowed=false。

32674｜reference｜{"validation_id":"TDV_009","check_description":"信息是否被相关人物掌握","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按前场及当前视角核对信息实际持有者、取得时点和披露限度，说明哪个角色尚不具备所用信息。

32701｜reference｜{"validation_id":"TDV_012","check_description":"身份是否允许","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按实际角色的已确认身份、权限及在场者所知核对所选行动或披露，标明违反边界的部分。

32710｜reference｜{"validation_id":"TDV_013","check_description":"关系是否允许","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】对照参与者之间真实成立的关系和职责，定位关系限制所影响的具体场景行动。

32719｜reference｜{"validation_id":"TDV_014","check_description":"时间是否允许","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】用已知时序、事件完成窗口和在场人物所需时间，核对所选事件和行动是否赶得上。

32728｜reference｜{"validation_id":"TDV_015","check_description":"空间是否允许","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】用实际场所、人物位置和既有空间限制核对该场采取的动作，标出无法成立的移动或接触。

【《类型系统》类型多样性策略的维度｜场景设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

32973｜reference｜{"id":"information","name":"信息维度","weight":0.05}
【本步用法】按实际持有人、证据及允许披露部分，辨明同一目标下可以采用的不同信息释放顺序。

32978｜reference｜{"id":"scene","name":"场景维度","weight":0.05}
【本步用法】在当前目标、上游事件和已选动作范围内核对场景进入状态、阻碍及结果的具体差异。

【《类型系统》类型多样性策略的边界｜场景设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】在现有步骤核对候选的适用边界，并对照作者已确认的设定和前置产物。

33043｜"违反时间线"
【本步用法】对照已知故事顺序及场景在场时点，核对变化的成立时间。

33044｜"违反空间位置"
【本步用法】沿用实际场所、距离、人物及道具所在位置核对场内动作或信息能否到达。

""" + FORESHADOWING_DISCLOSURE_USE + r"""【《类型系统》类型适配冲突规则｜场景设计】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38292｜reference｜{"conflict_rule_id":"CONFLICT_B_005","rule_name":"类型和场景条件冲突","category":"type_scene_conflict","description":"当类型表达偏好与当前场景实际条件冲突时检测","input_fields":["type_id","scene_id","scene_conditions"],"warning_condition":"类型的场景偏好与当前场景条件不兼容","fail_condition":"忽略场景条件强行应用类型适配","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】把拟用类型的场景偏好与本场已选事件、动作及人物实际处境对照，指出不兼容条件和所涉产物。

38368｜reference｜{"conflict_rule_id":"CONFLICT_B_009","rule_name":"类型和当前信息持有关系冲突","category":"type_information_conflict","description":"当类型信息揭示偏好与角色当前信息持有不匹配时检测","input_fields":["type_id","character_id","information_state"],"warning_condition":"类型偏好高度信息不对称但角色当前信息状态不支持","fail_condition":"强行改变信息持有状态","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】核对实际掌握信息的角色、获知时点和可披露范围，定位类型偏好与本场所知之间的冲突或拟改动。

"""

INFORMATION_REVEAL_USE = r"""本场采用《类型信息揭示适配》时，执行下列原约束。
该分表的 ADAPT_B_00064–ADAPT_B_00067 原条均为伏笔偏好，伏笔计划交由剧情设计核对。本场的信息披露根据已选事件、行动、信源和允许披露的范围安排。
【《类型系统》类型信息揭示适配的补充约束｜场景设计】
【原文位置】来源块第 38,733 行。条目前缀指原件字段行。
【本步用法】依据上游实际揭示条件、角色所知及当前场景产物核对原约束。

38968｜"类型不得跳过连续性验证"
【本步用法】本场已选信息揭示沿用前文真实线索、接收者所知与已定披露时序，核对信息出现的位置及连续性依据。

38969｜"信息仍然需要传播路径"
【本步用法】在本场揭示产物中沿已选事件和行动核对信息从实际持有人经什么渠道传到哪个接收者、何时可得，并遵守已定披露边界。

38970｜"角色可能误解、怀疑或拒绝相信"
【本步用法】在本场揭示产物中分别记录接收者获得的消息及其理解、信任状态。用已有角色与剧情依据保留误解、怀疑或拒信，取得消息本身不能证明已理解或相信。
"""

MATERIAL += INFORMATION_REVEAL_USE
