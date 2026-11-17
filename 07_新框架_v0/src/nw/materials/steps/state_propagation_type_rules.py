"""状态传播步骤的《类型系统》层级、报告或条件原文。"""

DYNAMIC_FILTER_INPUTS = (
    'TDF_001 第1–3步用 inputs.type_selection 的已选身份和分类，以及 inputs.type_adaptation 的实际适配、限制与作者要求。'
    '未指定的结构、风格或语气留待作者决定。第4–5步用 inputs.plot_design 中的当前章任务以及 '
    'inputs.scene_design 中本场的目标、已选事件和行动。第6–7步对照人物能力、世界规则、批准卡片、'
    '本场前状态和 accepted_state。第8步使用实际已激活的概念及关注重点。第9步沿本场知情、资源持有和设定证据，'
    '第10步查实际事件节点和已有伏笔。核对冻结分支版本、场景时点和披露位置，采用的前置缺失时写入 waiting。'
    '候选规则按适用条件及实际作用取用。规划收口按真正落到本场的规则引用各核类型动态与原始动态两类上限。'
)

MATERIAL = r"""#### 状态传播核对的类型动态冲突
【类型系统原文位置】类型动态冲突规则.json 第26990行
【各条共用原文值】{"detection":"report_only","auto_resolve":false,"severity":"error","schema_version":"TYPE_D-1.0.0"}
【本步用法】在实际项目产物上核对以下报告项，记录具体对象、时点、所涉字段及依据。原件规定 report_only，auto_resolve=false。报告按现有产物和待核说明保存。
【逐条原文值】conflict_id 原文行 | conflict_id | description | 本步核对
27091 | TDC_013 | 类型规则导致无限传播 | 按实际变化根、已检查的层级及连续性查看循环或无终点的传播预案。
27115 | TDC_016 | 类型规则把静态连接当作动态触发 | 依据实际变化根、外部选择和连续性核对触发，记录仅有静态连接的情况。

#### 状态传播核对的动态触发条件
【类型系统原文位置】类型动态触发条件.json 第27171行
【各条共用原文值】{"expected_value":null,"source_id":null,"required":true,"negatable":true,"failure_behavior":"report_and_skip","status":"active"}
【本步用法】逐条保留 reference 身份，只有项目实际采用所属 rule_id 时才从已具备的前置核对。依该父规则内 evaluation_order 检查实际对象与原条件。比较值或证据缺失时记录待核，原 failure_behavior 为 report_and_skip，已成立的候选仍沿用本步现有验证和选择条件。
【逐条原文值】condition_id 原文行 | condition_id | rule_id | condition_kind | field | operator | evaluation_order | source_refs | evidence_type | confidence | 本步核对
27176 | TDC_0001 | TDR_TEMPLATE_001 | type_selected | type_id | equals | 0 | ["动态网络连接.txt"] | template | 0 | 核对模板涉及的实际已选类型，现有输入缺少选型证据时保留待核。
27195 | TDC_0002 | TDR_TEMPLATE_001 | entity_present | entity_id | exists | 1 | ["动态网络连接.txt"] | template | 0 | 核对变化根涉及的真实实体、当前可行动性与实体证据。
27344 | TDC_0010 | TDR_001 | type_selected | type_id | equals | 0 | ["动态网络连接.txt C00001-C00006"] | inferred | 0.8 | 核对饥饿等实际变化根所涉及的已选类型，原比较值为空时按项目证据核对。
27363 | TDC_0011 | TDR_001 | entity_present | entity_id | exists | 1 | ["动态网络连接.txt C00001-C00006"] | inferred | 0.8 | 核对变化根的实体在本项目存在且可行动，沿已有门槛保留传播候选。
27657 | TDC_0027 | TDR_015 | time_state | delay_elapsed | greater_than | 0 | [] | template | 0.5 | 核对实际变化根、已定后果及延迟依据，记明比较值待核处。
27854 | TDC_0038 | TDR_025 | type_selected | type_id | equals | 0 | ["类型表达适配总表.json"] | template | 0.55 | 从实际已选类型及既有社会结构核对影响范围，缺明确选型证据时保留待核。
27873 | TDC_0039 | TDR_025 | entity_present | entity_id | exists | 1 | ["类型表达适配总表.json"] | template | 0.55 | 核对实际人物或群体、社会结构和后续根变化依据，保留有条件候选。

#### 状态传播的全局限制
【类型系统原文位置】类型动态传播限制.json 第27940行
【本步用法】按现有传播候选的实际根、层级、链条范围与来源资格核对原始默认值。现有激活条件仍需根变化确认、实际外部行动选择和连续性验证。
【逐条原文值】原文行 | global_defaults 字段 | 原值 | 本步核对
27944 | max_activated_rules_per_scene | 5 | 核对同一场实际激活规则的数量及所用口径。
27945 | max_propagation_depth | 3 | 核对当前传播候选从根到后继的层级及停止位置。
27946 | max_state_updates_per_scene | 12 | 核对同一场实际状态更新的数量与对象，项目计数口径沿现有依据。
27947 | max_main_plot_chains | 1 | 对照实际相关传播链，核对主线链条的作用和数量。
27948 | max_character_sub_chains | 2 | 对照本场已有的角色支线，核对实际影响范围与链条数量。
27949 | max_background_foreshadowing_chains | 3 | 用已有伏笔与关联场景核对背景伏笔链条的数量。
27950 | max_candidate_effects_per_rule | 5 | 核对同一已采用规则实际提出的候选效果数量。
27951 | max_candidate_actions_per_character | 5 | 核对同一人物在已采用规则下的候选行动数量。
27952 | unverified_candidates_blocked | true | 沿用现有候选核验和采用状态，核对待核候选的资格。
27953 | pending_fixture_blocked | true | 核对相关记录有无 fixture 身份及当前可用性。
27954 | restore_pending_blocked | true | 核对实际依赖是否仍待恢复，保留原来源标记。
27955 | repeat_policy_enforcement | true | 按规则已具备的重复限制核对当前链条，缺原口径时保留待核。

#### 传播记录的原始模板
【类型系统原文位置】类型动态传播限制.json 第27940行
【各条共用原文值】{"root_rule_id":null,"current_rule_id":null,"depth":0,"parent_propagation_id":null,"activated_by":null,"activated_at":null,"affected_ids":[],"affected_state_types":[],"candidate_effect_ids":[],"blocked_effect_ids":[],"block_reasons":[],"validation_status":"pending","source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】这些原记录的核验状态为 pending，深度初值为 0，归属及输入为空。按当前已确认的根、实体及实际选择形成现有的传播候选，沿用本步的状态和证据。
【逐条原文值】propagation_id 原文行 | propagation_id
27959 | TDP_001
27977 | TDP_002
27995 | TDP_003
28013 | TDP_004
28031 | TDP_005
28049 | TDP_006
28067 | TDP_007
28085 | TDP_008
28103 | TDP_009
28121 | TDP_010

【《类型系统》类型动态规则总表｜状态传播】
【原文位置】来源块第 28,706 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】按本步的实际前置、条目触发和外部选择条件判断用途。原条所列空值、候选范围和现行裁定随条保留。

28711｜reference｜{"rule_id":"TDR_TEMPLATE_001","rule_scope":"状态传播模板","rule_kind":"TYPE_STATE_PROPAGATION","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["身体状态","精神状态"],"trigger_entities":["人物"],"trigger_event_types":["状态变化"],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["实体存在且可行动","状态变化已确认"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_T001_E01","effect_kind":"state_change","description":"相关状态可能被传播影响"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"unknown","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["动态网络连接.txt"],"evidence_type":"template","confidence":0,"status":"template","schema_version":"TYPE_D-1.0.0"}
【本步用法】从实际已确认的身体或精神状态变化出发，依可行动实体、现有传递条件和原上限提议传播，再按行动选择和连续性核对。

29164｜design_ready｜{"rule_id":"TDR_001","rule_scope":"身体状态在类型世界中的传播","rule_kind":"TYPE_STATE_PROPAGATION","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["身体状态","精神状态"],"trigger_entities":["人物"],"trigger_event_types":["状态变化"],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["实体存在且可行动","身体状态变化已确认"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_001_E01","effect_kind":"state_change","description":"饥饿在特定类型中触发不同优先级的冲动行为"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["动态网络连接.txt C00001-C00006"],"evidence_type":"inferred","confidence":0.8,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】饥饿等身体状态已有明确变化时，按确认的根变化、可行动者及既有场景限制保留可能提高冲动优先级的条件预案。

31288｜design_ready｜{"rule_id":"TDR_025","rule_scope":"社会压力在类型环境中的传播","rule_kind":"TYPE_STATE_PROPAGATION","type_ids":[],"subtype_ids":[],"hybrid_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"trigger_concepts":["社会","声誉","地位"],"trigger_entities":["人物","群体"],"trigger_event_types":[],"trigger_information_types":[],"trigger_resource_types":[],"trigger_relationship_types":[],"trigger_foreshadowing_types":[],"preconditions":["社会结构存在"],"required_context":[],"required_information":[],"required_resources":[],"required_capabilities":[],"required_relationships":[],"required_identity_conditions":[],"required_moral_conditions":[],"candidate_effects":[{"effect_id":"TDR_025_E01","effect_kind":"goal_pressure","description":"社会压力影响目标优先级"}],"candidate_actions":[],"candidate_reactions":[],"state_changes":[],"relationship_changes":[],"resource_changes":[],"information_changes":[],"identity_changes":[],"item_changes":[],"location_changes":[],"foreshadowing_changes":[],"delayed_effects":[],"alternative_branches":[],"failure_branches":[],"interruption_conditions":[],"selection_constraints":["必须经过外部行动选择","不能自动生成completed事件","需要连续性验证"],"propagation_limits":{"max_depth":3,"max_activated_rules":5,"max_state_updates":12},"priority":0,"weight":0,"cooldown":null,"repeat_policy":"repeatable","conflicts_with":[],"requires_rules":[],"excludes_rules":[],"forbidden_assumptions":["类型不能决定确定行为","类型不能代替行动选择","类型不能覆盖人物性格","类型不能跳过连续性验证"],"not_guaranteed":["候选效果不一定被选中","状态变化需要事件证据","传播需要验证每一层"],"validation_rules":[],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有社会结构及可核的根变化时，按人物或群体的现有关系、实际行动和连续性提出声誉或地位影响目标先后的条件预案。

【《类型系统》类型动态候选效果｜状态传播】
【原文位置】来源块第 31,428 行。每项前为条目 ID 字段的原件行和现行裁定。
【本步用法】各候选效果随相应父规则核对本步状态或行动。原件的目标、字段和值均留空，现行裁定为 reference。用已具备的项目产物确定具体作用及可验证证据。

31433｜reference｜{"effect_id":"TDR_T001_E01","rule_id":"TDR_TEMPLATE_001","effect_kind":"state_change","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["动态网络连接.txt"],"evidence_type":"template","confidence":0,"status":"active"}
【本步用法】候选对象和字段由已确认的传播起点、目标及实际行动确定。缺依据时保留相关状态可能受影响的参考。

31597｜reference｜{"effect_id":"TDR_001_E01","rule_id":"TDR_001","effect_kind":"state_change","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["动态网络连接.txt C00001-C00006"],"evidence_type":"inferred","confidence":0.8,"status":"active"}
【本步用法】根据真实饥饿状态、所选行动和传递对象核对冲动的候选影响，人物的最终行动由场景选择确认。

32367｜reference｜{"effect_id":"TDR_025_E01","rule_id":"TDR_025","effect_kind":"goal_pressure","target_id":null,"target_type":"entity","change_field":null,"change_operation":"candidate","candidate_value":null,"magnitude":null,"duration":null,"probability":null,"priority":0,"requires_selection":true,"requires_validation":true,"possible_side_effects":[],"possible_failures":[],"possible_interruptions":[],"continuity_requirements":["必须通过连续性验证","不能跳过事件证据"],"not_guaranteed":["此效果不是必然结果","需要外部行动选择和验证"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active"}
【本步用法】当前目标的候选排序依据来自已确认社会条件和具体作用者，采用时保留外部选择与复核门槛。

【《类型系统》类型动态筛选规则 TDF_001｜状态传播】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】按当前步骤的实际前置和已有产物落实适用的筛选动作，并保留原步骤编号及其现行裁定。

32507｜reference｜{"step":14,"action":"排除已超出传播层数的规则"}
【本步用法】按现有根变化到候选后继的已知链路核对层数和停止位置，记录超限候选及其实际路径。

32523｜reference｜{"step":18,"action":"生成候选效果"}
【本步用法】当前根变化及真实作用对象具备时，按实际条件形成拟影响字段、值或延续条件的候选效果。

32527｜reference｜{"step":19,"action":"等待行动选择和连续性验证"}
【本步用法】按上游实际行动选择及连续性证据核对传播候选，明确待确认的根变化和采纳条件。

【《类型系统》类型动态筛选规则每场上限 TDF_001｜状态传播】
【原文位置】来源块第 32,448 行。条目前缀是原件中的字段行。
【本步用法】用已有场景或候选实际对应的实体、字段、时点和范围核对原上限。证据不足或计数所需产物未形成时，在本步已有说明中标明待核。

32545｜{"max_propagation_depth":3}
【本步用法】用现有传播链和已确定的深度起算方式核对三层上限。计数口径缺依据时记录待核。

【《类型系统》类型动态验证规则｜状态传播】
【原文位置】来源块第 32,597 行。条目前缀是原件中的字段行。
【本步用法】按实际项目对象、已用资料和本步产物核对下列验证项，并将问题定位到已有产物和证据。原件规定 report_only=true、auto_fix_allowed=false。

32764｜reference｜{"validation_id":"TDV_019","check_description":"动态传播是否超过3层","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按实际根变化和后继节点核对传播路径深度，报告超过原文 3 层的那一段。

32809｜reference｜{"validation_id":"TDV_024","check_description":"是否跳过行动选择","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】对每个条件传播核对所需的外部行动及实际选择记录，标出缺少该记录的后继预案。

32818｜reference｜{"validation_id":"TDV_025","check_description":"是否跳过连续性验证","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】按本场和前文实际线索核对连续性依据，指出缺少验证的传播起点或结果。

32854｜reference｜{"validation_id":"TDV_029","check_description":"是否存在循环触发","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】沿已记录的触发链核对是否返回同一触发起点、规则和对象，报告可定位的循环。

32863｜reference｜{"validation_id":"TDV_030","check_description":"是否存在无法终止的重复传播","report_only":true,"auto_fix_allowed":false,"severity":"error","status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】核对现有重复触发链的停止条件、上限和实际推进依据，标出无法确认会停止的路径。

【《类型系统》类型关系传播规则｜状态传播】
【原文位置】来源块第 34,847 行。每项前缀为对应字段的物理原件行。
【本步用法】以已确认关系、真实互动实体、可回查事件和已有行动选择为依据核对候选。原条的双方、触发、代价空值及现行参考裁定随条保留。

34852｜reference｜{"propagation_id":"TRP_001","relation_type":"友好","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"友好","candidate_new_relation":["友好变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有事件确认双方友好且具备实际互动时，沿现有根变化和本场行动记录友好关系可能发生的变化，后值待选择和证据核对。

34890｜reference｜{"propagation_id":"TRP_002","relation_type":"敌对","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"敌对","candidate_new_relation":["敌对变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】既有事件确认双方敌对时，以能回查的行动和相互影响为依据考虑敌对程度或处境的后续变化，保留作用边界。

34928｜reference｜{"propagation_id":"TRP_003","relation_type":"中立","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"中立","candidate_new_relation":["中立变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已经确认双方处于中立时，按实际接触和后继行动核对可能维持或改变该关系的条件，保留真实触发和待确认结果。

34966｜reference｜{"propagation_id":"TRP_004","relation_type":"合作","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"合作","candidate_new_relation":["合作变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】合作关系已有事件依据时，核对实际合作内容、双方履行情况及会影响其延续的后继行动。

35004｜reference｜{"propagation_id":"TRP_005","relation_type":"竞争","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"竞争","candidate_new_relation":["竞争变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】有已确认的竞争对象与共同竞争范围时，按实际事件及双方行动核对改变竞争关系所需的条件和代价。

35042｜reference｜{"propagation_id":"TRP_006","relation_type":"师生","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"师生","candidate_new_relation":["师生变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】师生关系已经成立时，按真实授业、职责或互动事件核对可能受影响的关系范围及后续承接。

35080｜reference｜{"propagation_id":"TRP_007","relation_type":"家人","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"家人","candidate_new_relation":["家人变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】家人关系的前值已有依据时，依据双方已选行动、实际义务和事件结果核对关系是否变化及持续条件。

35118｜reference｜{"propagation_id":"TRP_008","relation_type":"爱慕","source_entity_id":null,"target_entity_id":null,"trigger_event":null,"current_relation":"爱慕","candidate_new_relation":["爱慕变化候选"],"required_evidence":["当前关系已通过事件确认","双方实体存在且可互动"],"social_cost":null,"moral_cost":null,"risk":"中","reversibility":"取决于具体event","delayed_effect":false,"validation_rule":["关系变化必须有事件依据","不能将关系冲突等同于攻击","不能将关系改善等同于信任","变化需要外部选择和验证"],"not_guaranteed":["候选关系变化不一定发生","关系冲突不必然导致攻击","关系改善不必然导致信任"],"source_refs":["类型表达适配总表.json"],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】项目确认相应爱慕及其持有者时，以真实互动和各方实际所知核对候选关系变化，保留尚待确认的方向。

【《类型系统》类型信息传播规则｜状态传播】
【原文位置】来源块第 38,510 行。条目前缀指原件字段行。
【本步用法】沿用本场已选行动、原持有者、真实接收者和已知传播条件核对拟传播效果，按原条参考裁定记录。

38515｜reference｜{"propagation_id":"TIP_001","information_type":"秘密","information_id":null,"source_id":null,"receiver_id":null,"propagation_path":"候选传播","information_state":"候选传播","reliability_change":null,"belief_change_candidate":null,"concealment_candidate":true,"verification_requirement":["信息源必须可追溯","接收者是否有能力理解信息","传播路径是否被阻断"],"delayed_effect":false,"validation_rule":["信息被说出不等同于所有人知道","信息被说出不等同于接收者相信","需要验证信息来源和接收者","传播需要外部选择和验证"],"not_guaranteed":["信息传播不保证到达","信息接收不保证相信","信息知道不保证行动"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】本场已有秘密和实际掌握者时，依所选行动核对传递渠道、可达接收者及披露边界，记录具体待证效果。

38549｜reference｜{"propagation_id":"TIP_002","information_type":"知识","information_id":null,"source_id":null,"receiver_id":null,"propagation_path":"候选传播","information_state":"候选传播","reliability_change":null,"belief_change_candidate":null,"concealment_candidate":true,"verification_requirement":["信息源必须可追溯","接收者是否有能力理解信息","传播路径是否被阻断"],"delayed_effect":false,"validation_rule":["信息被说出不等同于所有人知道","信息被说出不等同于接收者相信","需要验证信息来源和接收者","传播需要外部选择和验证"],"not_guaranteed":["信息传播不保证到达","信息接收不保证相信","信息知道不保证行动"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有可回查的知识来源且接收者具备理解条件时，沿实际行动核对哪些内容已传达、哪些仍待理解或确认。

38583｜reference｜{"propagation_id":"TIP_003","information_type":"谣言","information_id":null,"source_id":null,"receiver_id":null,"propagation_path":"候选传播","information_state":"候选传播","reliability_change":null,"belief_change_candidate":null,"concealment_candidate":true,"verification_requirement":["信息源必须可追溯","接收者是否有能力理解信息","传播路径是否被阻断"],"delayed_effect":false,"validation_rule":["信息被说出不等同于所有人知道","信息被说出不等同于接收者相信","需要验证信息来源和接收者","传播需要外部选择和验证"],"not_guaranteed":["信息传播不保证到达","信息接收不保证相信","信息知道不保证行动"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有谣言的说出者和接收者时，沿真实渠道及所见证据核对到达、相信和仍待查证的范围。

38617｜reference｜{"propagation_id":"TIP_004","information_type":"发现","information_id":null,"source_id":null,"receiver_id":null,"propagation_path":"候选传播","information_state":"候选传播","reliability_change":null,"belief_change_candidate":null,"concealment_candidate":true,"verification_requirement":["信息源必须可追溯","接收者是否有能力理解信息","传播路径是否被阻断"],"delayed_effect":false,"validation_rule":["信息被说出不等同于所有人知道","信息被说出不等同于接收者相信","需要验证信息来源和接收者","传播需要外部选择和验证"],"not_guaranteed":["信息传播不保证到达","信息接收不保证相信","信息知道不保证行动"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已选事件有实际发现者、可见线索及交接行动时，依证据确定候选传播的具体内容和接收者。

38651｜reference｜{"propagation_id":"TIP_005","information_type":"命令","information_id":null,"source_id":null,"receiver_id":null,"propagation_path":"候选传播","information_state":"候选传播","reliability_change":null,"belief_change_candidate":null,"concealment_candidate":true,"verification_requirement":["信息源必须可追溯","接收者是否有能力理解信息","传播路径是否被阻断"],"delayed_effect":false,"validation_rule":["信息被说出不等同于所有人知道","信息被说出不等同于接收者相信","需要验证信息来源和接收者","传播需要外部选择和验证"],"not_guaranteed":["信息传播不保证到达","信息接收不保证相信","信息知道不保证行动"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有可追溯的命令来源、渠道和可能接收者时，明确能获知的内容、理解条件及接收后尚待选择的行动。

【《类型系统》类型资源传播规则｜状态传播】
【原文位置】来源块第 41,918 行。条目前缀为 ID 字段的物理原件行。
【本步用法】用实际已知的资源、来源控制权、本场已选行动、可能接收者和当前项目条件核对原候选，按既有参考裁定保留原空值。

41923｜reference｜{"propagation_id":"TRS_001","resource_type":"金钱","source_owner":null,"receiver":null,"transfer_method":"候选转移","required_conditions":["资源存在","来源拥有资源或控制权","转移路径合法"],"amount_or_state_change":null,"cost":null,"risk":"中","reversibility":"取决于转移方式","side_effects":[],"validation_rule":["资源被提出不等同于交易成功","资源不足不能自动等同于抢夺","转移需要事件依据和双方确认"],"not_guaranteed":["资源转移不保证成功","资源不足不必然导致抢夺","资源转移需要双方能力验证"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】本场实际有货币及其控制者时，按现有转移条件和双方行动核对拟转移对象、金额及支持证据。

41955｜reference｜{"propagation_id":"TRS_002","resource_type":"物品","source_owner":null,"receiver":null,"transfer_method":"候选转移","required_conditions":["资源存在","来源拥有资源或控制权","转移路径合法"],"amount_or_state_change":null,"cost":null,"risk":"中","reversibility":"取决于转移方式","side_effects":[],"validation_rule":["资源被提出不等同于交易成功","资源不足不能自动等同于抢夺","转移需要事件依据和双方确认"],"not_guaranteed":["资源转移不保证成功","资源不足不必然导致抢夺","资源转移需要双方能力验证"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】现有物品具有真实持有者和拟接收者时，按已选交接动作与物品状态核对可成立的范围。

41987｜reference｜{"propagation_id":"TRS_003","resource_type":"能力","source_owner":null,"receiver":null,"transfer_method":"候选转移","required_conditions":["资源存在","来源拥有资源或控制权","转移路径合法"],"amount_or_state_change":null,"cost":null,"risk":"中","reversibility":"取决于转移方式","side_effects":[],"validation_rule":["资源被提出不等同于交易成功","资源不足不能自动等同于抢夺","转移需要事件依据和双方确认"],"not_guaranteed":["资源转移不保证成功","资源不足不必然导致抢夺","资源转移需要双方能力验证"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】项目已定义能力传递及相应控制权时，依实际来源、接收者能力与所选行动核对转移条件和变化证据。

42019｜reference｜{"propagation_id":"TRS_004","resource_type":"信息","source_owner":null,"receiver":null,"transfer_method":"候选转移","required_conditions":["资源存在","来源拥有资源或控制权","转移路径合法"],"amount_or_state_change":null,"cost":null,"risk":"中","reversibility":"取决于转移方式","side_effects":[],"validation_rule":["资源被提出不等同于交易成功","资源不足不能自动等同于抢夺","转移需要事件依据和双方确认"],"not_guaranteed":["资源转移不保证成功","资源不足不必然导致抢夺","资源转移需要双方能力验证"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有信息和其掌握方时，沿当前许可的渠道与双方行动记录接收范围，待证内容按现有知情和信念边界核对。

42051｜reference｜{"propagation_id":"TRS_005","resource_type":"地位","source_owner":null,"receiver":null,"transfer_method":"候选转移","required_conditions":["资源存在","来源拥有资源或控制权","转移路径合法"],"amount_or_state_change":null,"cost":null,"risk":"中","reversibility":"取决于转移方式","side_effects":[],"validation_rule":["资源被提出不等同于交易成功","资源不足不能自动等同于抢夺","转移需要事件依据和双方确认"],"not_guaranteed":["资源转移不保证成功","资源不足不必然导致抢夺","资源转移需要双方能力验证"],"source_refs":[],"evidence_type":"template","confidence":0.55,"status":"active","schema_version":"TYPE_D-1.0.0"}
【本步用法】已有持位者、制度依据及可被授权者时，核对项目允许的实际授予或变化条件、证据和后续影响。
"""
