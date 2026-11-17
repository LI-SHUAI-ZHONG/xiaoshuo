"""行动设计步骤的《类型系统》层级、报告或条件原文。"""

MATERIAL = r"""#### 行动设计核对的类型动态冲突
【类型系统原文位置】类型动态冲突规则.json 第26990行
【各条共用原文值】{"detection":"report_only","auto_resolve":false,"severity":"error","schema_version":"TYPE_D-1.0.0"}
【本步用法】在实际项目产物上核对以下报告项，记录具体对象、时点、所涉字段及依据。原件规定 report_only，auto_resolve=false。报告按现有产物和待核说明保存。
【逐条原文值】conflict_id 原文行 | conflict_id | description | 本步核对
27067 | TDC_010 | 类型规则绕过能力限制 | 按当步人物现有能力与候选最低要求，报告能力边界被绕过的具体行动。
27075 | TDC_011 | 类型规则绕过道德和关系限制 | 核对已有关系、人物道德边界和本场作用对象，报告候选触及的限制。
27083 | TDC_012 | 类型规则强制固定行为 | 核对动作候选是否还需外部选择，报告仅靠类型条件强制行为的条目。

#### 行动设计核对的动态触发条件
【类型系统原文位置】类型动态触发条件.json 第27171行
【各条共用原文值】{"expected_value":null,"source_id":null,"required":true,"negatable":true,"failure_behavior":"report_and_skip","status":"active"}
【本步用法】逐条保留 reference 身份，只有项目实际采用所属 rule_id 时才从已具备的前置核对。依该父规则内 evaluation_order 检查实际对象与原条件。比较值或证据缺失时记录待核，原 failure_behavior 为 report_and_skip，已成立的候选仍沿用本步现有验证和选择条件。
【逐条原文值】condition_id 原文行 | condition_id | rule_id | condition_kind | field | operator | evaluation_order | source_refs | evidence_type | confidence | 本步核对
27310 | TDC_0008 | TDR_TEMPLATE_005 | entity_present | entity_id | exists | 0 | [] | template | 0 | 核对事件参与的真实人物以及可行动身份。
27327 | TDC_0009 | TDR_TEMPLATE_005 | capability_state | capability | greater_or_equal | 1 | [] | template | 0 | 对照上游能力和事件所需最低要求，保留原 expected_value 的空值。
27495 | TDC_0018 | TDR_006 | resource_available | resource_id | exists | 0 | [] | inferred | 0.6 | 核对行动涉及的资源是否可用，以及已定的取得或转移约束。
27729 | TDC_0031 | TDR_019 | resource_available | item_id | exists | 0 | [] | template | 0.5 | 用已定物品和人物的可用条件核对候选消耗及代价。
27763 | TDC_0033 | TDR_021 | location_state | entity_location | within | 0 | [] | template | 0.5 | 按实际地点、角色位置及项目规定范围核对行动受限处。

#### 传播限制中同一人物的行动候选
【类型系统原文位置】类型动态传播限制.json 第27940行
【逐条原文值】原文行 | global_defaults 字段 | 原值 | 本步核对
27951 | max_candidate_actions_per_character | 5 | 核对同一人物在已采用规则下的候选行动数量。
【本步用法】当上游已采用相关规则时按实际人物核对候选上限，并核对其事件、能力和对象。

【《类型系统》类型动态规则总表｜行动设计】
【原文位置】来源块第 28,706 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】按本步的实际前置、条目触发和外部选择条件判断用途。原条所列空值、候选范围和现行裁定随条保留。

29078｜reference｜{"rule_id":"TDR_TEMPLATE_005","rule_scope":"行动候选模板","rule_kind":"TYPE_ACTION_CANDIDATE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":["人物"],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["实体存在且可行动","能力满足最低要求"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_T005_E01","effect_kind":"candidate_action","description":"候选行动供外部选择"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"unknown","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0,"status":"template","schema_version":"TYPE_D-1.0.0"}
【本步用法】事件涉及已存在且可行动的人物时，对照上游能力与最低要求给出实际的行动候选及其成立条件。

29620｜design_ready｜{"rule_id":"TDR_006","rule_scope":"资源在类型环境中的变化候选","rule_kind":"TYPE_RESOURCE_CHANGE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":["金钱","物品","能力"],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["资源存在","转移路径合法"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_006_E01","effect_kind":"resource_consumption","description":"资源可能被消耗或转移"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"inferred","confidence":0.6,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】实际资源和作品已允许的转移路径都成立时，设计能实施的取得、消耗或转移一步，标明来源、目的地及成本。

30066｜design_ready｜{"rule_id":"TDR_011","rule_scope":"冲突降级候选路径","rule_kind":"TYPE_DEESCALATION","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["冲突","谈判","妥协"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["冲突存在","至少一方有意愿降级"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_011_E01","effect_kind":"risk_decrease","description":"冲突可降级但不可强制"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["类型适配冲突规则.json"],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】一方有明确降级意愿且原冲突尚在时，按实际人物和可行条件写出能付诸实施的缓和选择及接受或落空的代价。

30156｜design_ready｜{"rule_id":"TDR_012","rule_scope":"类型场景中的替代路径候选","rule_kind":"TYPE_ALTERNATIVE_PATH","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["选择","分支"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["存在多个可能的方向"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_012_E01","effect_kind":"alternative_path","description":"替代路径候选"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】项目已经有多个可行方向时，依据同一个既有事件分别列出可执行的一步、各自前置条件及承担的后果。

30242｜design_ready｜{"rule_id":"TDR_013","rule_scope":"失败分支候选","rule_kind":"TYPE_FAILURE_BRANCH","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["失败","风险"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["行动有失败可能"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_013_E01","effect_kind":"failure_path","description":"可能失败但不必然"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已定行动存在可说明的失败条件时，沿动作顺序指出在哪一步可能失败、受影响对象及已有应对。

30328｜design_ready｜{"rule_id":"TDR_014","rule_scope":"事件中断候选","rule_kind":"TYPE_INTERRUPTION","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["中断","突发事件"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["有正在进行的事件"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_014_E01","effect_kind":"interruption_path","description":"事件可能被中断"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有正在进行的事件时，按既定中断条件写明原行动会在何处停下、能够采取的下一步及哪些原计划仍可延续。

30676｜design_ready｜{"rule_id":"TDR_018","rule_scope":"反应候选","rule_kind":"TYPE_REACTION_CANDIDATE","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":["人物"],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["实体受到刺激或事件影响"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_018_E01","effect_kind":"candidate_reaction","description":"多种反应候选"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.6,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】人物受到具体事件或刺激时，按上游人设和已有能力提供其可选反应及后果，供场景选定。

30763｜design_ready｜{"rule_id":"TDR_019","rule_scope":"物品消耗候选","rule_kind":"TYPE_ITEM_CONSUMPTION","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":[],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":["消耗品","道具"],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["物品存在且可使用"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_019_E01","effect_kind":"resource_consumption","description":"物品可能被消耗"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】实际道具或消耗品存在且可用时，确定候选用途、可使用条件和准备承担的耗用成本。

30936｜design_ready｜{"rule_id":"TDR_021","rule_scope":"地点约束适配","rule_kind":"TYPE_LOCATION_CONSTRAINT","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["地点","空间"],"trigger_entities":[],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["地点有约束条件"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_021_E01","effect_kind":"location_constraint","description":"地点可能限制行动"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】现有场所确有可适用的行动限制时，按项目已定空间条件和人物能力说明影响哪步行动与可行选择。

【《类型系统》类型动态候选效果｜行动设计】
【原文位置】来源块第 31,428 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】各候选效果随相应父规则核对本步状态或行动。原件的目标、字段和值均留空，现行裁定为 reference。用已具备的项目产物确定具体作用及可验证证据。

31566｜reference｜{"effect_id":"TDR_T005_E01","rule_id":"TDR_TEMPLATE_005","effect_kind":"candidate_action","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0,"status":"active"}
【本步用法】随本场已有事件和可行动人物保存动作选择，能力门槛和代价均由既有产物支持。

31761｜reference｜{"effect_id":"TDR_006_E01","rule_id":"TDR_006","effect_kind":"resource_consumption","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"inferred","confidence":0.6,"status":"active"}
【本步用法】随已选的资源行动核对实际资源、方向和可能消耗，原文空数量由已定证据核实。

31923｜reference｜{"effect_id":"TDR_011_E01","rule_id":"TDR_011","effect_kind":"risk_decrease","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["类型适配冲突规则.json"],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】从已知的意愿、动作条件和另一方可能回应核对实际缓和空间，保留条件候选。

31956｜reference｜{"effect_id":"TDR_012_E01","rule_id":"TDR_012","effect_kind":"alternative_path","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】对应现有目的和可行动角色，保存替代路线的前置与效果供本场选择及验证。

31987｜reference｜{"effect_id":"TDR_013_E01","rule_id":"TDR_013","effect_kind":"failure_path","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】根据该行动实际的风险和限制保留失败路径，按后续稿件或所选结果核对是否发生。

32018｜reference｜{"effect_id":"TDR_014_E01","rule_id":"TDR_014","effect_kind":"interruption_path","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】随进行中的实际事件确定触发时间、被打断的动作和可采取的替代应对。

32144｜reference｜{"effect_id":"TDR_018_E01","rule_id":"TDR_018","effect_kind":"candidate_reaction","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.6,"status":"active"}
【本步用法】候选反应与实际刺激、角色能力和目标对应，选定后按本场行为核对。

32177｜reference｜{"effect_id":"TDR_019_E01","rule_id":"TDR_019","effect_kind":"resource_consumption","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】以当前已有物品和行动步骤核对可能耗用及依据，后续依据选用和可见结果确认。

32239｜reference｜{"effect_id":"TDR_021_E01","rule_id":"TDR_021","effect_kind":"location_constraint","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":[],"evidence_type":"template","confidence":0.5,"status":"active"}
【本步用法】记录当前地点的实际约束和受影响的一步，按选定的应对核对能否绕开既定限制。

【《类型系统》类型动态筛选规则 TDF_001｜行动设计】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】按当前步骤的实际前置和已有产物落实适用的筛选动作，并保留原步骤编号及其现行裁定。

32475｜reference｜{"step":6,"action":"读取人物状态"}
【本步用法】用上游人物卡、已知状态和既有能力核对该人物当前可执行的动作及其限制。

32479｜reference｜{"step":7,"action":"读取实体、物品和地点状态"}
【本步用法】对照作品已定的实体、物品和地点前态，确定当前动作可用的对象、用途与空间条件。

【《类型系统》类型动态筛选规则每场上限 TDF_001｜行动设计】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】用已有场景或候选实际对应的实体、字段、时点和范围核对原上限。证据不足或计数所需产物未形成时，在本步已有说明中标明待核。

32539｜{"max_candidate_actions_per_character":5}
【本步用法】依同场和实际可行动角色分组，核对每个角色列出的实际行动候选数。

32540｜{"max_candidate_reactions":10}
【本步用法】在同场实际候选中核对归属于具体刺激或事件的角色反应数，使用本场口径。

32542｜{"max_resource_candidates":5}
【本步用法】按本场既有资源实体和行动方案核对实际取得、转移或消耗的候选数。

【《类型系统》类型动态验证规则｜行动设计】
【原文位置】来源块第 32,597 行。条目前缀是原件中的字段行。
【本步用法】按实际项目对象、已用资料和本步产物核对下列验证项，并将问题定位到已有产物和证据。原件规定 report_only=true、auto_fix_allowed=false。

32647｜reference｜{"validation_id":"TDV_006","check_description":"人物是否存在","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按本场所涉候选实际引用的人物 key 与上游人物资料核对角色是否存在。

32683｜reference｜{"validation_id":"TDV_010","check_description":"资源是否足够","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】核对实际可用资源和所选目标所需的消耗，记录不足的资源、数量或使用条件。

32692｜reference｜{"validation_id":"TDV_011","check_description":"能力是否满足","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】逐个对照行动所需的能力与人物上游已有能力及限制，报告不满足的条件和具体动作。

32737｜reference｜{"validation_id":"TDV_016","check_description":"伤势是否影响行动","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按上游已证伤势和人物可行动状态核对会受影响的实际步骤和范围。

32746｜reference｜{"validation_id":"TDV_017","check_description":"物品状态是否允许使用","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】核对具体物品的持有、完损、可用状态及调用条件，指出与计划使用不符的地方。

32791｜reference｜{"validation_id":"TDV_022","check_description":"是否产生固定行为","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】核对动作候选的意图、能力及理由源自哪些已有条件，指出仅根据类型便固定了角色行动的那项选择。

【《类型系统》类型多样性策略的维度｜行动设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

32968｜reference｜{"id":"resource","name":"资源维度","weight":0.05}
【本步用法】对照已具备资源和已知取得或转移条件，比较候选行动采用的具体资源及其代价。

32993｜reference｜{"id":"moral_conflict","name":"道德冲突维度","weight":0.04}
【本步用法】依据人物已经建立的价值边界及现有冲突比较可执行的取舍，并核对各自代价。

32998｜reference｜{"id":"social_strategy","name":"社交策略维度","weight":0.04}
【本步用法】用真实关系、人物目标及当场约束比较其可采取的合作、拒绝或交涉行动。

33003｜reference｜{"id":"failure","name":"行动失败维度","weight":0.04}
【本步用法】把不同失败候选落到真实动作步骤与失败条件，核对各自影响范围及可选应对。

【《类型系统》类型多样性策略的边界｜行动设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】在现有步骤核对候选的适用边界，并对照作者已确认的设定和前置产物。

33040｜"违反人物能力"
【本步用法】逐项用人物已有能力和可行动状态核对备选动作的最低条件。

33042｜"违反资源状态"
【本步用法】按已知资源持有者、可用量和实际用途核对备选行动能否成立。

【《类型系统》类型适配冲突规则｜行动设计】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38311｜reference｜{"conflict_rule_id":"CONFLICT_B_006","rule_name":"类型和资源状态冲突","category":"type_resource_conflict","description":"当类型资源呈现偏好与角色当前资源状态冲突时检测","input_fields":["type_id","character_id","resource_states"],"warning_condition":"类型要求呈现资源充足但角色实际资源匮乏","fail_condition":"忽略资源限制呈现不实资源状态","severity":"warning","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】按真实持有者、当前资源值与人物实际可用条件核对类型所提资源表现，并定位拟用动作与现有资源的差异。

38330｜reference｜{"conflict_rule_id":"CONFLICT_B_007","rule_name":"类型和道德边界冲突","category":"type_moral_conflict","description":"当类型适配试图影响人物道德边界时检测","input_fields":["type_id","character_id","moral_boundary"],"warning_condition":"类型适配暗示道德松弛或越界","fail_condition":"类型适配覆盖人物已有道德设置","severity":"fail","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】将拟选动作的取舍与人物已确定的道德边界相核对，报告存在冲突的实际行动与设定字段。

38424｜reference｜{"conflict_rule_id":"CONFLICT_B_012","rule_name":"类型适配试图生成固定动作","category":"type_fixed_action","description":"当类型适配指定了具体固定动作时检测","input_fields":["type_id","candidate_actions","not_guaranteed"],"warning_condition":"candidate_actions仅含一个元素且缺少not_guaranteed","fail_condition":"类型适配生成了固定动作选择","severity":"fail","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】依原件警告条件核对单一候选及其非保证字段。以项目当前可行选择和产物证据判断是否出现固定动作。

【《类型系统》类型验证规则｜行动设计】
【原文位置】来源块第 40,879 行。条目前缀为 ID 字段的物理原件行。
【本步用法】按本步实际对象及证据核对适用的原验收项。涉及旧阶段 A、备份、文件清单或原测试的条目，按相应阶段和资料维护范围核对已有记录。

40981｜reference｜{"test_id":"TA20","test":"类型不会强制推出固定人物行为","check":"no_forced_character_behavior"}
【本步用法】依据上游事件、人物目标、能力和实际选择核对动作候选的来源。
"""
