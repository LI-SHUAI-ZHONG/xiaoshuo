"""类型适配步骤中的第 951–1005 条组合原文及用法。"""

MATERIAL = """【《类型系统》类型组合总表｜类型适配｜第 951–1005 条】
【原文位置】第 56 个来源块始于第 42,967 行。本段为正文表顺序第 951–1005 条，前缀指组合 ID 字段的物理原件行。
【本步用法】按作者采用的类型、项目已有前置及当前需求核对组合的作用和实际使用条件。现行裁定为 blocked 的条目用于查原值、用途和待核项。原文中的子类型及风格空值照录，项目具体选择以作者确认的设定为据。
【各条共用原文值】{"primary_type_id":"GENRE_XUANYI","type_ids":["GENRE_XUANYI"],"subtype_ids":[],"hybrid_ids":[],"style_ids":[],"tone_ids":[],"audience_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"foreshadowing_type_ids":[],"selection_status":"candidate","source_refs":["type_combination_template"],"evidence_type":"inferred","status":"candidate","schema_version":"2.0"}
【逐条精简值】每条由共用值与本行有效组成字段合并而成，已剔除合成随机评分与跨类型污染外键。

139774｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANYI_0952","combination_kind":"CONFLICT_COMBINATION","combination_name":"悬疑×生存压力 冲突搭配","description":"悬疑中生存压力引发的冲突维度组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002205","TSC_002206","TSC_002207"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】以已有生存压力、积累路径和倒叙时点为据，核对曾经的资源限制如何引出对立，以及当时可见的行动。

139871｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANYI_0953","combination_kind":"INFORMATION_COMBINATION","combination_name":"悬疑×权力博弈 信息搭配","description":"悬疑类型下权力博弈的信息控制搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000532","TSC_000533","TSC_000534"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00051","ADAPT_B_00052","ADAPT_B_00053"]}
【本步用法】从项目已有权力格局和信息差出发，核对谁掌握哪类权限信息、披露先后及影响的选择。

139968｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANYI_0954","combination_kind":"RESOURCE_COMBINATION","combination_name":"悬疑×身份伪装 资源搭配","description":"悬疑×身份伪装的资源争夺组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001145","TSC_001146","TSC_001147"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00001","ADAPT_B_00002","ADAPT_B_00003"]}
【本步用法】把各线既定伪装身份、资源门槛和人物所知对照，核对身份与知情差怎样改变可取资源。

140065｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANYI_0955","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"悬疑×知识垄断 关系搭配","description":"悬疑叙事中知识垄断的关系张力组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002375","TSC_002376","TSC_002377"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00048","ADAPT_B_00049","ADAPT_B_00050"]}
【本步用法】沿既有知识持有者和接触限制核对人物依赖，查倒叙能说明哪次接触及当时各方所知。

140162｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANYI_0956","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"悬疑×情感纽带 伏笔搭配","description":"基于悬疑的情感纽带伏笔标记搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002426","TSC_002427","TSC_002428"],"dynamic_rule_ids":["TDR_001","TDR_002"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】依已经成立的情感纽带和后续验证点，核对能先出现的关系标记、当时看见的人及回收条件。

140261｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANYI_0957","combination_kind":"STYLE_COMBINATION","combination_name":"悬疑×命运轨迹 风格搭配","description":"悬疑风格体系中命运轨迹的美学组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000377","TSC_000378","TSC_000379"],"dynamic_rule_ids":["TDR_001","TDR_003"],"adaptation_ids":["ADAPT_B_00013","ADAPT_B_00014","ADAPT_B_00015"]}
【本步用法】把既定命运节点和成长阶段对照，核对作者所定写法能显出的轨迹变化及其既有前因。

140360｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANYI_0958","combination_kind":"PROJECT_COMBINATION","combination_name":"悬疑×禁忌领域 项目组合","description":"悬疑类型禁忌领域的项目结构搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000429","TSC_000430","TSC_000431"],"dynamic_rule_ids":["TDR_001","TDR_004"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】依据已有禁忌范围和线性成长安排，核对项目各阶段涉及禁忌的行为、前置条件和可见后果。

140459｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANYI_0959","combination_kind":"STATIC_COMBINATION","combination_name":"悬疑×传承体系 静态搭配","description":"基于悬疑的类型兼容传承体系搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001141","TSC_001142","TSC_001143"],"dynamic_rule_ids":["TDR_001","TDR_005"],"adaptation_ids":["ADAPT_B_00023","ADAPT_B_00024","ADAPT_B_00025"]}
【本步用法】从已确认的传承资格与既定关系出发，核对稳定的授受联系、相关对象和需要回查的依据。

140558｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANYI_0960","combination_kind":"DYNAMIC_COMBINATION","combination_name":"悬疑×背叛成本 动态搭配","description":"悬疑×背叛成本的动态传播搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000416","TSC_000417","TSC_000418"],"dynamic_rule_ids":["TDR_001","TDR_006"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】沿已经成立的背叛与代价核对变化经谁或何物传播、触发的后继行动及可确认的结果。

140657｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANYI_0961","combination_kind":"EXPRESSION_COMBINATION","combination_name":"悬疑×觉醒机制 表达配合","description":"适配悬疑的觉醒机制表达参数组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002171","TSC_002172","TSC_002173"],"dynamic_rule_ids":["TDR_001","TDR_007"],"adaptation_ids":["ADAPT_B_00013","ADAPT_B_00014","ADAPT_B_00015"]}
【本步用法】按既定觉醒条件和可见变化，核对作者所选表达能呈现哪些区别、人物能在何处察觉。

140756｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANYI_0962","combination_kind":"SCENE_COMBINATION","combination_name":"悬疑×世界观 场景搭配","description":"悬疑中世界观的场景构建组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001219","TSC_001220","TSC_001221"],"dynamic_rule_ids":["TDR_001","TDR_008"],"adaptation_ids":["ADAPT_B_00036","ADAPT_B_00037","ADAPT_B_00038"]}
【本步用法】以已有世界规则和场景目标为据，核对在场人、对象及能够展示规则作用的具体行动。

140855｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANYI_0963","combination_kind":"CONFLICT_COMBINATION","combination_name":"悬疑×力量体系 冲突搭配","description":"悬疑类型力量体系的对立冲突搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001741","TSC_001742","TSC_001743"],"dynamic_rule_ids":["TDR_001","TDR_009"],"adaptation_ids":["ADAPT_B_00115","ADAPT_B_00116","ADAPT_B_00117"]}
【本步用法】从前置力量边界及角色目标出发，核对能力使用在哪项条件下引起对立及其可见后果。

140954｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANYI_0964","combination_kind":"INFORMATION_COMBINATION","combination_name":"悬疑×身份设定 信息搭配","description":"悬疑×身份设定的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002995","TSC_002996","TSC_002997"],"dynamic_rule_ids":["TDR_001","TDR_010"],"adaptation_ids":["ADAPT_B_00018","ADAPT_B_00019","ADAPT_B_00020"]}
【本步用法】依已设真实身份与公开身份核对各方所知，查何时可以披露哪项身份信息及对后继行动的作用。

141053｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANYI_0965","combination_kind":"RESOURCE_COMBINATION","combination_name":"悬疑×社交网络 资源搭配","description":"悬疑世界中社交网络的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002434","TSC_002435","TSC_002436"],"dynamic_rule_ids":["TDR_001","TDR_011"],"adaptation_ids":["ADAPT_B_00042","ADAPT_B_00043","ADAPT_B_00044"]}
【本步用法】沿已有社交网络和资源需要核对提供者、取得路径及依赖的关系条件。

141152｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANYI_0966","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"悬疑×资源流通 关系搭配","description":"基于悬疑的资源流通关系演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002341","TSC_002342","TSC_002343"],"dynamic_rule_ids":["TDR_001","TDR_012"],"adaptation_ids":["ADAPT_B_00001","ADAPT_B_00002","ADAPT_B_00003"]}
【本步用法】从已确认的资源流向、持有方和交换条件出发，核对流转将怎样改变人物间的依赖与关系。

141251｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANYI_0967","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"悬疑×信息控制 伏笔搭配","description":"悬疑伏笔线索中信息控制的预置组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001292","TSC_001293","TSC_001294"],"dynamic_rule_ids":["TDR_001","TDR_013"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】按既定信息控制与后续揭示需求，核对前文可留下的事实线索、知情人和后来验证的位置。

141350｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANYI_0968","combination_kind":"STYLE_COMBINATION","combination_name":"悬疑×时间线 风格搭配","description":"悬疑类型下时间线的风格变奏搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001583","TSC_001584","TSC_001585"],"dynamic_rule_ids":["TDR_001","TDR_014"],"adaptation_ids":["ADAPT_B_00036","ADAPT_B_00037","ADAPT_B_00038"]}
【本步用法】对照已确定的时序、时间标记与作者选定风格，核对叙述能明确哪些节点和先后关系。

141449｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANYI_0969","combination_kind":"PROJECT_COMBINATION","combination_name":"悬疑×空间布局 项目组合","description":"悬疑×空间布局的项目配置组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000209","TSC_000210","TSC_000211"],"dynamic_rule_ids":["TDR_001","TDR_015"],"adaptation_ids":["ADAPT_B_00014","ADAPT_B_00015","ADAPT_B_00016"]}
【本步用法】把现有地点布局和成长目标纳入项目安排，核对各阶段通行条件、可达范围和需提前建立的空间依据。

141548｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANYI_0970","combination_kind":"STATIC_COMBINATION","combination_name":"悬疑×因果链条 静态搭配","description":"悬疑×因果链条的静态连接搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000138","TSC_000139","TSC_000140"],"dynamic_rule_ids":["TDR_001","TDR_016"],"adaptation_ids":["ADAPT_B_00111","ADAPT_B_00112","ADAPT_B_00113"]}
【本步用法】按已成立的事件因果核对相对稳定的前因、结果与相关对象，查哪些条件支撑后继变化。

141647｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANYI_0971","combination_kind":"DYNAMIC_COMBINATION","combination_name":"悬疑×道德困境 动态搭配","description":"悬疑中基于道德困境的动态行为组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001564","TSC_001565","TSC_001566"],"dynamic_rule_ids":["TDR_001","TDR_017"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】依据已有道德界线及选择核对触发的行动、代价和能够从后来事件观察的状态变化。

141746｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANYI_0972","combination_kind":"EXPRESSION_COMBINATION","combination_name":"悬疑×生存压力 表达配合","description":"悬疑中生存压力的语言表达适配组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000706","TSC_000707","TSC_000708"],"dynamic_rule_ids":["TDR_001","TDR_018"],"adaptation_ids":["ADAPT_B_00017","ADAPT_B_00018","ADAPT_B_00019"]}
【本步用法】从已知生存缺口和人物行动出发，核对作者采用的表达能显示哪些压力、限制及反应。

141845｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANYI_0973","combination_kind":"SCENE_COMBINATION","combination_name":"悬疑×权力博弈 场景搭配","description":"悬疑类型下权力博弈的场景布局搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000863","TSC_000864","TSC_000865"],"dynamic_rule_ids":["TDR_001","TDR_019"],"adaptation_ids":["ADAPT_B_00005","ADAPT_B_00006","ADAPT_B_00007"]}
【本步用法】以现有权力分布、在场人物和本场目的核对场景安排，查行动或站位可体现的权限条件。

141944｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANYI_0974","combination_kind":"CONFLICT_COMBINATION","combination_name":"悬疑×身份伪装 冲突搭配","description":"悬疑×身份伪装的冲突机制组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002262","TSC_002263","TSC_002264"],"dynamic_rule_ids":["TDR_001","TDR_020"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】把实际伪装、人物目标及身份质疑对照，核对冲突起点、对立对象与各方可选择的行动。

142043｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANYI_0975","combination_kind":"INFORMATION_COMBINATION","combination_name":"悬疑×知识垄断 信息搭配","description":"悬疑叙事中知识垄断的信息披露节奏组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001505","TSC_001506","TSC_001507"],"dynamic_rule_ids":["TDR_001","TDR_021"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】沿已有知识垄断、可知者和前置限制，核对哪项知识可披露、传播受谁控制以及影响。

142142｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANYI_0976","combination_kind":"RESOURCE_COMBINATION","combination_name":"悬疑×情感纽带 资源搭配","description":"基于悬疑的情感纽带资源转换搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001092","TSC_001093","TSC_001094"],"dynamic_rule_ids":["TDR_001","TDR_022"],"adaptation_ids":["ADAPT_B_00103","ADAPT_B_00104","ADAPT_B_00105"]}
【本步用法】依据已有情感纽带和资源条件，核对实际可提供的支持、转换范围和人物支付的代价。

142241｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANYI_0977","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"悬疑×命运轨迹 关系搭配","description":"悬疑中命运轨迹的人际关系组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001348","TSC_001349","TSC_001350"],"dynamic_rule_ids":["TDR_001","TDR_023"],"adaptation_ids":["ADAPT_B_00009","ADAPT_B_00010","ADAPT_B_00011"]}
【本步用法】根据既定命运节点与人物关系，核对关系在何种前置下形成或改变及可追查的依据。

142340｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANYI_0978","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"悬疑×禁忌领域 伏笔搭配","description":"悬疑类型下禁忌领域的伏笔铺设搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000221","TSC_000222","TSC_000223"],"dynamic_rule_ids":["TDR_001","TDR_024"],"adaptation_ids":["ADAPT_B_00052","ADAPT_B_00053","ADAPT_B_00057"]}
【本步用法】把已明确的禁忌边界与后文揭示对照，核对可以较早出现的行为线索、观察者及回收所需条件。

142439｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANYI_0979","combination_kind":"STYLE_COMBINATION","combination_name":"悬疑×传承体系 风格搭配","description":"悬疑×传承体系的叙述风格组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000364","TSC_000365","TSC_000366"],"dynamic_rule_ids":["TDR_001","TDR_025"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】用已成立的传承条件与作者所选风格核对表现，查哪些授受资格、行为细节或变动可被看见。

142538｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANYI_0980","combination_kind":"PROJECT_COMBINATION","combination_name":"悬疑×背叛成本 项目组合","description":"悬疑写作中背叛成本的项目规划组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002020","TSC_002021","TSC_002022"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】从已有背叛成本和成长阶段出发，核对项目各阶段发生的代价、前置关系与之后可查的后果。

142635｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANYI_0981","combination_kind":"STATIC_COMBINATION","combination_name":"悬疑×觉醒机制 静态搭配","description":"悬疑世界中觉醒机制的静态结构组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000262","TSC_000263","TSC_000264"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00105","ADAPT_B_00106","ADAPT_B_00107"]}
【本步用法】将各线既定觉醒条件与稳定规则对照，核对觉醒所依赖的对象、限制及各线可见依据。

142732｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANYI_0982","combination_kind":"DYNAMIC_COMBINATION","combination_name":"悬疑×世界观 动态搭配","description":"悬疑动态规则触发下的世界观变化","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000829","TSC_000830","TSC_000831"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00023","ADAPT_B_00024","ADAPT_B_00025"]}
【本步用法】以已定世界状态与实际触发事件为据，核对动态变化影响的规则或对象及倒叙可查的前因。

142829｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANYI_0983","combination_kind":"EXPRESSION_COMBINATION","combination_name":"悬疑×力量体系 表达配合","description":"悬疑类型力量体系的语气风格表达搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001845","TSC_001846","TSC_001847"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00067","ADAPT_B_00103","ADAPT_B_00104"]}
【本步用法】沿前置能力体系与资源积累过程，核对拟采用的表达能清楚呈现的积累、使用成本和力量变化。

142926｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANYI_0984","combination_kind":"SCENE_COMBINATION","combination_name":"悬疑×身份设定 场景搭配","description":"悬疑×身份设定场景元素组合方案","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002308","TSC_002309","TSC_002310"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00046","ADAPT_B_00047","ADAPT_B_00048"]}
【本步用法】按各线身份、转移对象及场景目标核对可见的识别线索、行动和身份在资源积累中的作用。

143023｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANYI_0985","combination_kind":"CONFLICT_COMBINATION","combination_name":"悬疑×社交网络 冲突搭配","description":"悬疑叙事中社交网络的冲突层次组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001074","TSC_001075","TSC_001076"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】把既定社交网络、资源争议和倒叙时点对照，核对关系冲突因何发生及可回查的行动证据。

143120｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANYI_0986","combination_kind":"INFORMATION_COMBINATION","combination_name":"悬疑×资源流通 信息搭配","description":"基于悬疑的资源流通信息博弈搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003075","TSC_003076","TSC_003077"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00007","ADAPT_B_00008","ADAPT_B_00009"]}
【本步用法】从已有资源流转和知情差核对谁知道归属、交易或转移的哪一环，以及信息对现有选择的作用。

143217｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANYI_0987","combination_kind":"RESOURCE_COMBINATION","combination_name":"悬疑×信息控制 资源搭配","description":"悬疑资源体系中信息控制的稀缺约束组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001287","TSC_001288","TSC_001289"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】沿各线既定信息权限和资源条件，核对信息取得所需的对象、稀缺限制以及给各线带来的影响。

143314｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANYI_0988","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"悬疑×时间线 关系搭配","description":"悬疑类型下时间线的社会纽带搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002179","TSC_002180","TSC_002181"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00008","ADAPT_B_00009","ADAPT_B_00010"]}
【本步用法】依据已定时间线、倒叙位置和人物知情差，核对关系成立时点、认知差及变化的可追溯依据。

143411｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANYI_0989","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"悬疑×空间布局 伏笔搭配","description":"悬疑×空间布局的伏笔回收组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002350","TSC_002351","TSC_002352"],"dynamic_rule_ids":["TDR_002","TDR_003"],"adaptation_ids":["ADAPT_B_00113","ADAPT_B_00114","ADAPT_B_00115"]}
【本步用法】把前文已出现的空间细节同既定地点关系对照，核对后文能回查的路线、方位或物件位置。

143510｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANYI_0990","combination_kind":"STYLE_COMBINATION","combination_name":"悬疑×因果链条 风格搭配","description":"悬疑语境中因果链条的风格基调组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002237","TSC_002238","TSC_002239"],"dynamic_rule_ids":["TDR_002","TDR_004"],"adaptation_ids":["ADAPT_B_00040","ADAPT_B_00041","ADAPT_B_00042"]}
【本步用法】从项目已有因果与成长节点出发，核对作者所选基调怎样表现前因、行动与具体后果。

143609｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANYI_0991","combination_kind":"PROJECT_COMBINATION","combination_name":"悬疑×道德困境 项目组合","description":"基于悬疑的道德困境项目骨架搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001023","TSC_001024","TSC_001025"],"dynamic_rule_ids":["TDR_002","TDR_005"],"adaptation_ids":["ADAPT_B_00064","ADAPT_B_00065","ADAPT_B_00066"]}
【本步用法】将已确认的道德困境和线性成长安排对应到项目骨架，核对各次选择的前置及可观察代价。

143708｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANYI_0992","combination_kind":"STATIC_COMBINATION","combination_name":"悬疑×生存压力 静态搭配","description":"悬疑与稳定关系生存压力的静态搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_003028","TSC_003029","TSC_003030"],"dynamic_rule_ids":["TDR_002","TDR_006"],"adaptation_ids":["ADAPT_B_00038","ADAPT_B_00039","ADAPT_B_00040"]}
【本步用法】依已有生存压力、供给范围和稳定人物关系，核对哪些条件持续影响人物行动和成长。

143807｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANYI_0993","combination_kind":"DYNAMIC_COMBINATION","combination_name":"悬疑×权力博弈 动态搭配","description":"悬疑类型权力博弈动态演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002462","TSC_002463","TSC_002464"],"dynamic_rule_ids":["TDR_002","TDR_007"],"adaptation_ids":["ADAPT_B_00108","ADAPT_B_00109","ADAPT_B_00110"]}
【本步用法】根据既有权力关系与触发行动，核对权限变化、受影响角色和接下来可确认的行动。

143906｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANYI_0994","combination_kind":"EXPRESSION_COMBINATION","combination_name":"悬疑×身份伪装 表达配合","description":"悬疑×身份伪装的修辞表达组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002589","TSC_002590","TSC_002591"],"dynamic_rule_ids":["TDR_002","TDR_008"],"adaptation_ids":["ADAPT_B_00057","ADAPT_B_00058","ADAPT_B_00059"]}
【本步用法】用现有伪装身份、真实身份与人物知情范围核对语言或动作能展示的差别，以及暂时保留的线索。

144005｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANYI_0995","combination_kind":"SCENE_COMBINATION","combination_name":"悬疑×知识垄断 场景搭配","description":"悬疑世界观中知识垄断的场景呈现组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000773","TSC_000774","TSC_000775"],"dynamic_rule_ids":["TDR_002","TDR_009"],"adaptation_ids":["ADAPT_B_00061","ADAPT_B_00062","ADAPT_B_00063"]}
【本步用法】从已设知识门槛和本场目标出发，核对角色可见的获取条件、接触对象和实际行动。

144104｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANYI_0996","combination_kind":"CONFLICT_COMBINATION","combination_name":"悬疑×情感纽带 冲突搭配","description":"基于悬疑的情感纽带冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001530","TSC_001531","TSC_001532"],"dynamic_rule_ids":["TDR_002","TDR_010"],"adaptation_ids":["ADAPT_B_00009","ADAPT_B_00010","ADAPT_B_00011"]}
【本步用法】沿已有情感纽带和人物目标核对需求相抵的原因、相关选择及关系变化的可见表现。

144203｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANYI_0997","combination_kind":"INFORMATION_COMBINATION","combination_name":"悬疑×命运轨迹 信息搭配","description":"悬疑信息流中命运轨迹的信息差组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000872","TSC_000873","TSC_000874"],"dynamic_rule_ids":["TDR_002","TDR_011"],"adaptation_ids":["ADAPT_B_00027","ADAPT_B_00028","ADAPT_B_00029"]}
【本步用法】把各既定命运节点与人物所知对照，核对信息何时出现、由谁获知及影响的决定。

144302｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANYI_0998","combination_kind":"RESOURCE_COMBINATION","combination_name":"悬疑×禁忌领域 资源搭配","description":"悬疑类型下禁忌领域的资源分配搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002752","TSC_002753","TSC_002754"],"dynamic_rule_ids":["TDR_002","TDR_012"],"adaptation_ids":["ADAPT_B_00048","ADAPT_B_00049","ADAPT_B_00050"]}
【本步用法】依据已确认的禁忌范围与资源分配条件，核对对象、可取资格和使资源受限的具体边界。

144401｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANYI_0999","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"悬疑×传承体系 关系搭配","description":"悬疑×传承体系的关系网络组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000567","TSC_000568","TSC_000569"],"dynamic_rule_ids":["TDR_002","TDR_013"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】从已有传承资格与人物关系出发，核对授受双方的联系、影响成长的前置和关系变化。

144500｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANYI_1000","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"悬疑×背叛成本 伏笔搭配","description":"悬疑叙事中背叛成本的伏笔密度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002120","TSC_002121","TSC_002122"],"dynamic_rule_ids":["TDR_002","TDR_014"],"adaptation_ids":["ADAPT_B_00104","ADAPT_B_00105","ADAPT_B_00106"]}
【本步用法】以已定背叛代价和后续节点为据，核对起初可见的代价线索与能够证实它的具体结果。

144599｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANYI_1001","combination_kind":"STYLE_COMBINATION","combination_name":"悬疑×觉醒机制 风格搭配","description":"基于悬疑的觉醒机制风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002688","TSC_002689","TSC_002690"],"dynamic_rule_ids":["TDR_002","TDR_015"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】按已有觉醒条件、人物实际变化及作者所定风格，核对该写法能表现的成长差别和观察点。

144698｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANYI_1002","combination_kind":"PROJECT_COMBINATION","combination_name":"悬疑×世界观 项目组合","description":"悬疑项目模板下世界观的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001600","TSC_001601","TSC_001602"],"dynamic_rule_ids":["TDR_002","TDR_016"],"adaptation_ids":["ADAPT_B_00053","ADAPT_B_00057","ADAPT_B_00058"]}
【本步用法】结合既定世界规则、角色所处阶段和成长目标，核对项目安排分别依赖哪些可查的世界事实。

144797｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANYI_1003","combination_kind":"STATIC_COMBINATION","combination_name":"悬疑×力量体系 静态搭配","description":"悬疑类型下的力量体系静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001289","TSC_001290","TSC_001291"],"dynamic_rule_ids":["TDR_002","TDR_017"],"adaptation_ids":["ADAPT_B_00028","ADAPT_B_00029","ADAPT_B_00030"]}
【本步用法】按已确立的力量来源和稳定限制，核对已有对象、使用条件及支持成长变化的依据。

144896｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANYI_1004","combination_kind":"DYNAMIC_COMBINATION","combination_name":"悬疑×身份设定 动态搭配","description":"悬疑中身份设定的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002200","TSC_002201","TSC_002202"],"dynamic_rule_ids":["TDR_002","TDR_018"],"adaptation_ids":["ADAPT_B_00058","ADAPT_B_00059","ADAPT_B_00060"]}
【本步用法】由项目已有身份与实际触发事件出发，核对身份前后变化、谁能见证以及它带来的后续行动。

144995｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANYI_1005","combination_kind":"EXPRESSION_COMBINATION","combination_name":"悬疑×社交网络 表达配合","description":"悬疑语境下社交网络的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000104","TSC_000105","TSC_000106"],"dynamic_rule_ids":["TDR_002","TDR_019"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】沿已有社交网络和人物位置核对叙述可以呈现的交往、所见关系与相应行为依据。

145094｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANYI_1006","combination_kind":"SCENE_COMBINATION","combination_name":"悬疑×资源流通 场景搭配","description":"基于悬疑的资源流通场景调度搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002201","TSC_002202","TSC_002203"],"dynamic_rule_ids":["TDR_002","TDR_020"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】按已确定的资源流向与当场目标核对持有方、交付动作、相关对象及转移后的实际状态。"""
