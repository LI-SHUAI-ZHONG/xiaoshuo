"""类型适配步骤中的第 331–420 条组合原文及用法。"""

MATERIAL = """【《类型系统》类型组合总表｜类型适配｜第 331–420 条】
【原文位置】第 56 个来源块始于第 42,967 行。本批为正文表顺序第 331–420 条，前缀指组合 ID 字段的物理原件行。
【本步用法】按作者采用的类型、项目已有前置及当前设计需求核对各组合的实际用途和条件。blocked 条目供查原值、用途和待核项。本批子类型及风格字段均依原记录保留，对应的项目用法以作者确认的设定为据。
【各条共用原文值】{"primary_type_id":"GENRE_XUANHUAN","type_ids":["GENRE_XUANHUAN"],"subtype_ids":[],"hybrid_ids":[],"style_ids":[],"tone_ids":[],"audience_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"foreshadowing_type_ids":[],"selection_status":"candidate","source_refs":["type_combination_template"],"evidence_type":"inferred","status":"candidate","schema_version":"2.0"}
【逐条精简值】每条由共用值与本行有效组成字段合并而成，已剔除合成随机评分与跨类型污染外键。

76772｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0332","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×生存压力 静态搭配","description":"玄幻与稳定关系生存压力的静态搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000598","TSC_000599","TSC_000600"],"dynamic_rule_ids":["TDR_001","TDR_008"],"adaptation_ids":["ADAPT_B_00052","ADAPT_B_00053","ADAPT_B_00057"]}
【本步用法】按已有的生存压力、供给条件及依赖关系，核对成长阶段中哪些压力长期成立、通过什么对象表现。

76871｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0333","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×权力博弈 动态搭配","description":"玄幻类型权力博弈动态演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002483","TSC_002484","TSC_002485"],"dynamic_rule_ids":["TDR_001","TDR_009"],"adaptation_ids":["ADAPT_B_00052","ADAPT_B_00053","ADAPT_B_00057"]}
【本步用法】从已建立的权力关系和真实事件出发，核对权限转移的触发、所涉人物及对后续成长的影响。

76970｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0334","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×身份伪装 表达配合","description":"玄幻×身份伪装的修辞表达组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002364","TSC_002365","TSC_002366"],"dynamic_rule_ids":["TDR_001","TDR_010"],"adaptation_ids":["ADAPT_B_00066","ADAPT_B_00067","ADAPT_B_00103"]}
【本步用法】对照项目前置的真实身份、外显身份和他人所知，核对措辞能给出哪类伪装线索及其出现条件。

77069｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0335","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×知识垄断 场景搭配","description":"玄幻世界观中知识垄断的场景呈现组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000157","TSC_000158","TSC_000159"],"dynamic_rule_ids":["TDR_001","TDR_011"],"adaptation_ids":["ADAPT_B_00001","ADAPT_B_00002","ADAPT_B_00003"]}
【本步用法】以已设知识持有者、限制方式与本场需求为据，核对场景中角色可见的知识门槛和相应行动。

77168｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0336","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×情感纽带 冲突搭配","description":"基于玄幻的情感纽带冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000060","TSC_000061","TSC_000062"],"dynamic_rule_ids":["TDR_001","TDR_012"],"adaptation_ids":["ADAPT_B_00111","ADAPT_B_00112","ADAPT_B_00113"]}
【本步用法】沿已建立的情感纽带核对人物需求何处相抵，查冲突的选择及影响后续成长的可见结果。

77267｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0337","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×命运轨迹 信息搭配","description":"玄幻信息流中命运轨迹的信息差组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000609","TSC_000610","TSC_000611"],"dynamic_rule_ids":["TDR_001","TDR_013"],"adaptation_ids":["ADAPT_B_00066","ADAPT_B_00067","ADAPT_B_00103"]}
【本步用法】按既定命运节点和人物所知核对哪些信息较早出现、哪一方先得知及其对选择的影响。

77366｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0338","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×禁忌领域 资源搭配","description":"玄幻类型下禁忌领域的资源分配搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002440","TSC_002441","TSC_002442"],"dynamic_rule_ids":["TDR_001","TDR_014"],"adaptation_ids":["ADAPT_B_00064","ADAPT_B_00065","ADAPT_B_00066"]}
【本步用法】在已有禁忌范围和资源对象下，核对谁有取得或分配资格、哪些既定约束会限制该活动。

77465｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0339","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×传承体系 关系搭配","description":"玄幻×传承体系的关系网络组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000332","TSC_000333","TSC_000334"],"dynamic_rule_ids":["TDR_001","TDR_015"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】对照现有传承资格与人物关系，核对授受双方的稳定联系及成长进程中何时能回查。

77564｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0340","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×背叛成本 伏笔搭配","description":"玄幻叙事中背叛成本的伏笔密度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002333","TSC_002334","TSC_002335"],"dynamic_rule_ids":["TDR_001","TDR_016"],"adaptation_ids":["ADAPT_B_00109","ADAPT_B_00110","ADAPT_B_00111"]}
【本步用法】沿已确定的背叛代价核对前文能埋下的细节、各处线索的分布及结果得到确认的时点。

77663｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0341","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×觉醒机制 风格搭配","description":"基于玄幻的觉醒机制风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002334","TSC_002335","TSC_002336"],"dynamic_rule_ids":["TDR_001","TDR_017"],"adaptation_ids":["ADAPT_B_00020","ADAPT_B_00021","ADAPT_B_00022"]}
【本步用法】根据既有觉醒条件和可观察的变化，核对项目采用的写法能体现哪些觉醒阶段与效果。

77762｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0342","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×世界观 项目组合","description":"玄幻项目模板下世界观的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002733","TSC_002734","TSC_002735"],"dynamic_rule_ids":["TDR_001","TDR_018"],"adaptation_ids":["ADAPT_B_00058","ADAPT_B_00059","ADAPT_B_00060"]}
【本步用法】把已设世界规则、可用对象和成长阶段对应到项目整体安排，核对每个阶段依赖的具体世界条件。

77861｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0343","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×力量体系 静态搭配","description":"玄幻类型下的力量体系静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002544","TSC_002545","TSC_002546"],"dynamic_rule_ids":["TDR_001","TDR_019"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】按既有力量来源、稳定限制和角色持有对象，核对人物要实现成长变化需具备的支撑条件。

77960｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0344","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×身份设定 动态搭配","description":"玄幻中身份设定的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001382","TSC_001383","TSC_001384"],"dynamic_rule_ids":["TDR_001","TDR_020"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】从项目现有身份和实际触发事件出发，核对身份在事件前后的变化、见证者及后继行动条件。

78059｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0345","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×社交网络 表达配合","description":"玄幻语境下社交网络的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000446","TSC_000447","TSC_000448"],"dynamic_rule_ids":["TDR_001","TDR_021"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】沿已有社交网络和人物地位核对叙述可展示哪些交往关系及其作用，定位项目中支持这些表述的行动。

78158｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0346","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×资源流通 场景搭配","description":"基于玄幻的资源流通场景调度搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001590","TSC_001591","TSC_001592"],"dynamic_rule_ids":["TDR_001","TDR_022"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】以已经确认的流转事项和场景目标为据，核对交付双方、在场资源、转移动作和转移后的状态。

78257｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0347","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×信息控制 冲突搭配","description":"玄幻中信息控制引发的冲突维度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001733","TSC_001734","TSC_001735"],"dynamic_rule_ids":["TDR_001","TDR_023"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】从已存在的信息控制方式出发，核对信息受限如何触发实际对立、涉及哪些角色和回应。

78356｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0348","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×时间线 信息搭配","description":"玄幻类型下时间线的信息控制搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000841","TSC_000842","TSC_000843"],"dynamic_rule_ids":["TDR_001","TDR_024"],"adaptation_ids":["ADAPT_B_00112","ADAPT_B_00113","ADAPT_B_00114"]}
【本步用法】按已定时序核对何人掌握确切时间、哪件事尚未披露，以及这一差异会影响的后续成长节点。

78455｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0349","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×空间布局 资源搭配","description":"玄幻×空间布局的资源争夺组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000575","TSC_000576","TSC_000577"],"dynamic_rule_ids":["TDR_001","TDR_025"],"adaptation_ids":["ADAPT_B_00016","ADAPT_B_00017","ADAPT_B_00018"]}
【本步用法】对照既有地点、通路和物件位置，核对资源争夺中各方能抵达哪里、接近什么以及相应条件。

78554｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0350","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×因果链条 关系搭配","description":"玄幻叙事中因果链条的关系张力组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001538","TSC_001539","TSC_001540"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】沿已成立的因果事件核对哪一项后果引起人物关系变化，以及冲突或依赖能从何处追查。

78651｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0351","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×道德困境 伏笔搭配","description":"基于玄幻的道德困境伏笔标记搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002518","TSC_002519","TSC_002520"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00048","ADAPT_B_00049","ADAPT_B_00050"]}
【本步用法】从各线已知的道德界线和后来的选择出发，核对前文适合留下的行为标记及可验证的回收点。

78748｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0352","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×生存压力 风格搭配","description":"玄幻风格体系中生存压力的美学组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000526","TSC_000527","TSC_000528"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00006","ADAPT_B_00007","ADAPT_B_00008"]}
【本步用法】按已确立的生存压力和倒叙顺序，核对作者所选风格如何呈现前因、资源短缺及后来可见的代价。

78845｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0353","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×权力博弈 项目组合","description":"玄幻类型权力博弈的项目结构搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001358","TSC_001359","TSC_001360"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00109","ADAPT_B_00110","ADAPT_B_00111"]}
【本步用法】以既有权力配置与资源积累路径核对项目骨架，查各线性阶段的可用资源与权力变化依据。

78942｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0354","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×身份伪装 静态搭配","description":"基于玄幻的类型兼容身份伪装搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000566","TSC_000567","TSC_000568"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00046","ADAPT_B_00047","ADAPT_B_00048"]}
【本步用法】沿各线已有真实身份、外显身份和积累条件，核对支撑伪装的稳定关系、对象及使用范围。

79039｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0355","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×知识垄断 动态搭配","description":"玄幻×知识垄断的动态传播搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001235","TSC_001236","TSC_001237"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00039","ADAPT_B_00040","ADAPT_B_00041"]}
【本步用法】从已有知识垄断和积累条件核对知识传播的实际触发、受影响人物及倒叙可查的结果。

79136｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0356","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×情感纽带 表达配合","description":"适配玄幻的情感纽带表达参数组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002719","TSC_002720","TSC_002721"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00028","ADAPT_B_00029","ADAPT_B_00030"]}
【本步用法】用既定情感纽带和不同人物的知情差核对叙述表现，查哪些情感变化可由已有行为或措辞体现。

79233｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0357","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×命运轨迹 场景搭配","description":"玄幻中命运轨迹的场景构建组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002168","TSC_002169","TSC_002170"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】按多线已有命运节点和知情范围，核对场景中需要出现的人物、可见线索及其前置依据。

79330｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0358","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×禁忌领域 冲突搭配","description":"玄幻类型禁忌领域的对立冲突搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000309","TSC_000310","TSC_000311"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】把既定禁忌边界、倒叙顺序和各方所知对照，核对触发对立的具体行为及能回查的后果。

79427｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0359","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×传承体系 信息搭配","description":"玄幻×传承体系的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001585","TSC_001586","TSC_001587"],"dynamic_rule_ids":["TDR_002","TDR_003"],"adaptation_ids":["ADAPT_B_00038","ADAPT_B_00039","ADAPT_B_00040"]}
【本步用法】沿已确认的传承规则核对掌握条件的人、接收传承者和信息差，查实际披露对继承进程的作用。

79526｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0360","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×背叛成本 资源搭配","description":"玄幻世界中背叛成本的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002733","TSC_002734","TSC_002735"],"dynamic_rule_ids":["TDR_002","TDR_004"],"adaptation_ids":["ADAPT_B_00029","ADAPT_B_00030","ADAPT_B_00031"]}
【本步用法】从已有背叛代价、资源归属和取得路线出发，核对哪些原有渠道仍可用以及继续使用的代价。

79625｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0361","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×觉醒机制 关系搭配","description":"基于玄幻的觉醒机制关系演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001439","TSC_001440","TSC_001441"],"dynamic_rule_ids":["TDR_002","TDR_005"],"adaptation_ids":["ADAPT_B_00035","ADAPT_B_00036","ADAPT_B_00037"]}
【本步用法】按既定觉醒条件和人物关系核对觉醒会改变哪项纽带，以及变化怎样经项目已有行为看到。

79724｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0362","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×世界观 伏笔搭配","description":"玄幻伏笔线索中世界观的预置组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002163","TSC_002164","TSC_002165"],"dynamic_rule_ids":["TDR_002","TDR_006"],"adaptation_ids":["ADAPT_B_00005","ADAPT_B_00006","ADAPT_B_00007"]}
【本步用法】以已有世界设定和后续验证需要为据，核对可提前留下的规则线索和之后可观察的兑现位置。

79823｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0363","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×力量体系 风格搭配","description":"玄幻类型下力量体系的风格变奏搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000520","TSC_000521","TSC_000522"],"dynamic_rule_ids":["TDR_002","TDR_007"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】对照项目力量体系的阶段差别与作者已经采用的写法，核对表现中能见到哪些力量变化及限制。

79922｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0364","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×身份设定 项目组合","description":"玄幻×身份设定的项目配置组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003027","TSC_003028","TSC_003029"],"dynamic_rule_ids":["TDR_002","TDR_008"],"adaptation_ids":["ADAPT_B_00037","ADAPT_B_00038","ADAPT_B_00039"]}
【本步用法】把已确定的身份、人物所处阶段和成长目标放入项目初步安排，核对身份条件何时有效及影响范围。

80021｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0365","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×社交网络 静态搭配","description":"玄幻×社交网络的静态连接搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002331","TSC_002332","TSC_002333"],"dynamic_rule_ids":["TDR_002","TDR_009"],"adaptation_ids":["ADAPT_B_00043","ADAPT_B_00044","ADAPT_B_00045"]}
【本步用法】从前置的社交网络和相关角色出发，核对当前仍稳定的身份、依赖和交往关系及其适用范围。

80120｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0366","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×资源流通 动态搭配","description":"玄幻中基于资源流通的动态行为组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000259","TSC_000260","TSC_000261"],"dynamic_rule_ids":["TDR_002","TDR_010"],"adaptation_ids":["ADAPT_B_00025","ADAPT_B_00026","ADAPT_B_00027"]}
【本步用法】以实际资源流向和既定触发条件核对人物的一项行动、对象转移及其给后继事件造成的变化。

80219｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0367","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×信息控制 表达配合","description":"玄幻中信息控制的语言表达适配组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001078","TSC_001079","TSC_001080"],"dynamic_rule_ids":["TDR_002","TDR_011"],"adaptation_ids":["ADAPT_B_00038","ADAPT_B_00039","ADAPT_B_00040"]}
【本步用法】按已定信息权限与人物可知内容，核对语言表达可以显示哪些信息受控方式和实际边界。

80318｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0368","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×时间线 场景搭配","description":"玄幻类型下时间线的场景布局搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000737","TSC_000738","TSC_000739"],"dynamic_rule_ids":["TDR_002","TDR_012"],"adaptation_ids":["ADAPT_B_00064","ADAPT_B_00065","ADAPT_B_00066"]}
【本步用法】从既有时间锚和场景目标出发，核对当场能看出时点的事物、人物所知及与前后事件的衔接。

80417｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0369","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×空间布局 冲突搭配","description":"玄幻×空间布局的冲突机制组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001212","TSC_001213","TSC_001214"],"dynamic_rule_ids":["TDR_002","TDR_013"],"adaptation_ids":["ADAPT_B_00029","ADAPT_B_00030","ADAPT_B_00031"]}
【本步用法】依项目已设地点、通行条件与冲突目标，核对空间限制怎样实际改变人物行动或迫使各方选择。

80516｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0370","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×因果链条 信息搭配","description":"玄幻叙事中因果链条的信息披露节奏组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000101","TSC_000102","TSC_000103"],"dynamic_rule_ids":["TDR_002","TDR_014"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】沿已成立的原因与结果核对读者何时取得每项因果信息，各阶段披露需依赖哪些早先证据。

80615｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0371","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×道德困境 资源搭配","description":"基于玄幻的道德困境资源转换搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002965","TSC_002966","TSC_002967"],"dynamic_rule_ids":["TDR_002","TDR_015"],"adaptation_ids":["ADAPT_B_00053","ADAPT_B_00057","ADAPT_B_00058"]}
【本步用法】根据既定道德边界和资源状态，核对转换或交换所需的实际条件、人物选择和付出。

80714｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0372","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×生存压力 关系搭配","description":"玄幻中生存压力的人际关系组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001668","TSC_001669","TSC_001670"],"dynamic_rule_ids":["TDR_002","TDR_016"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】从现有生存压力与人物关系核对共同需求、依赖与摩擦怎样影响关系，以及相应行为如何查证。

80813｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0373","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×权力博弈 伏笔搭配","description":"玄幻类型下权力博弈的伏笔铺设搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000052","TSC_000053","TSC_000054"],"dynamic_rule_ids":["TDR_002","TDR_017"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】把已有权力归属和之后的对立节点对照，核对早期可见的权限线索、出现位置及后文验证点。

80912｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0374","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×身份伪装 风格搭配","description":"玄幻×身份伪装的叙述风格组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002930","TSC_002931","TSC_002932"],"dynamic_rule_ids":["TDR_002","TDR_018"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】按既定伪装、角色知情范围及作者选定风格，核对叙述可以呈现哪些身份细节和披露时点。

81011｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0375","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×知识垄断 项目组合","description":"玄幻写作中知识垄断的项目规划组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003076","TSC_003077","TSC_003078"],"dynamic_rule_ids":["TDR_002","TDR_019"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】对照已有知识门槛和阶段成长需求，核对项目安排中谁控制知识、何时能取得以及前提。

81110｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0376","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×情感纽带 静态搭配","description":"玄幻世界中情感纽带的静态结构组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001554","TSC_001555","TSC_001556"],"dynamic_rule_ids":["TDR_002","TDR_020"],"adaptation_ids":["ADAPT_B_00007","ADAPT_B_00008","ADAPT_B_00009"]}
【本步用法】从已建立的情感纽带和人物稳定关系出发，核对成长阶段所依赖的关系及可见支持。

81209｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0377","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×命运轨迹 动态搭配","description":"玄幻动态规则触发下的命运轨迹变化","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002815","TSC_002816","TSC_002817"],"dynamic_rule_ids":["TDR_002","TDR_021"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】在已有命运节点和动态规则条件下，核对具体触发、行动与项目中确可观察的轨迹变化。

81308｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0378","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×禁忌领域 表达配合","description":"玄幻类型禁忌领域的语气风格表达搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001748","TSC_001749","TSC_001750"],"dynamic_rule_ids":["TDR_002","TDR_022"],"adaptation_ids":["ADAPT_B_00045","ADAPT_B_00046","ADAPT_B_00047"]}
【本步用法】根据项目已确认的禁忌与人物所知，核对作者所选语气怎样表现限制、变动及可说范围。

81407｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0379","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×传承体系 场景搭配","description":"玄幻×传承体系场景元素组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001854","TSC_001855","TSC_001856"],"dynamic_rule_ids":["TDR_002","TDR_023"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】按确定的传承事件和本场所需功能核对参与者、传承对象、交接动作及早先已成立的条件。

81506｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0380","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×背叛成本 冲突搭配","description":"玄幻叙事中背叛成本的冲突层次组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000968","TSC_000969","TSC_000970"],"dynamic_rule_ids":["TDR_002","TDR_024"],"adaptation_ids":["ADAPT_B_00045","ADAPT_B_00046","ADAPT_B_00047"]}
【本步用法】由已有背叛、受影响者和代价核对冲突层次，确认各层引发的行动与确切后果。

81605｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0381","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×觉醒机制 信息搭配","description":"基于玄幻的觉醒机制信息博弈搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002270","TSC_002271","TSC_002272"],"dynamic_rule_ids":["TDR_002","TDR_025"],"adaptation_ids":["ADAPT_B_00034","ADAPT_B_00035","ADAPT_B_00036"]}
【本步用法】把既有觉醒触发、见证者和保密范围对照，核对各方得知的时序及实际影响其选择的信息。

81704｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0382","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×世界观 资源搭配","description":"玄幻资源体系中世界观的稀缺约束组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002079","TSC_002080","TSC_002081"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00051","ADAPT_B_00052","ADAPT_B_00053"]}
【本步用法】按项目世界观中的稀缺规则核对成长所需资源、可用来源和限制资源取得的具体前置。

81801｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0383","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×力量体系 关系搭配","description":"玄幻类型下力量体系的社会纽带搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002541","TSC_002542","TSC_002543"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00045","ADAPT_B_00046","ADAPT_B_00047"]}
【本步用法】从多线既有力量分布和人物关系核对角色间的依赖或对立及它们成立的力量条件。

81898｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0384","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×身份设定 伏笔搭配","description":"玄幻×身份设定的伏笔回收组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000617","TSC_000618","TSC_000619"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00019","ADAPT_B_00020","ADAPT_B_00021"]}
【本步用法】依据已有身份线索与倒叙安排，核对后文揭示时能回查的早期片段，以及该线索可证实的身份范围。

81995｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0385","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×社交网络 风格搭配","description":"玄幻语境中社交网络的风格基调组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000143","TSC_000144","TSC_000145"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】对照社交网络已有的角色位置和资源积累过程，核对作者选择的基调如何体现在真实互动中。

82092｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0386","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×资源流通 项目组合","description":"基于玄幻的资源流通项目骨架搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001879","TSC_001880","TSC_001881"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】沿多线资源流向和积累需求核对项目的归属、转移和阶段目标，查每一线可用的来源和先决条件。

82189｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0387","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×信息控制 静态搭配","description":"玄幻与稳定关系信息控制的静态搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002468","TSC_002469","TSC_002470"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】把既有信息访问和关系范围与倒叙顺序对照，核对限制信息流通的稳定条件及其对积累的影响。

82286｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0388","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×时间线 动态搭配","description":"玄幻类型时间线动态演化搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000272","TSC_000273","TSC_000274"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00051","ADAPT_B_00052","ADAPT_B_00053"]}
【本步用法】按已确认的事件时序、各方所知和触发条件，核对某项信息变化何时改变下一步行动及时间安排。

82383｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0389","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×空间布局 表达配合","description":"玄幻×空间布局的修辞表达组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001221","TSC_001222","TSC_001223"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00115","ADAPT_B_00116","ADAPT_B_00117"]}
【本步用法】用各线前置的空间布局和知情差核对表达内容，查描述能让读者确定哪些地点关系和可见物件。

82480｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0390","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×因果链条 场景搭配","description":"玄幻世界观中因果链条的场景呈现组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002980","TSC_002981","TSC_002982"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00029","ADAPT_B_00030","ADAPT_B_00031"]}
【本步用法】从已成立的原因、结果和角色所知出发，核对倒叙场景能展示的因果动作以及留下的信息差。

82577｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0391","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×道德困境 冲突搭配","description":"基于玄幻的道德困境冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001659","TSC_001660","TSC_001661"],"dynamic_rule_ids":["TDR_003","TDR_004"],"adaptation_ids":["ADAPT_B_00111","ADAPT_B_00112","ADAPT_B_00113"]}
【本步用法】按人物既定道德界线与成长目标核对两难如何转为冲突、各方实际可选的行动及其后果。

82676｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0392","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×生存压力 信息搭配","description":"玄幻信息流中生存压力的信息差组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000235","TSC_000236","TSC_000237"],"dynamic_rule_ids":["TDR_003","TDR_005"],"adaptation_ids":["ADAPT_B_00027","ADAPT_B_00028","ADAPT_B_00029"]}
【本步用法】对照既有生存压力中供给和出路的知情范围，核对信息差在哪个阶段影响人物实际选择。

82775｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0393","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×权力博弈 资源搭配","description":"玄幻类型下权力博弈的资源分配搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000912","TSC_000913","TSC_000914"],"dynamic_rule_ids":["TDR_003","TDR_006"],"adaptation_ids":["ADAPT_B_00041","ADAPT_B_00042","ADAPT_B_00043"]}
【本步用法】按已确立的权力关系和占有条件，核对谁能够分配何种资源、受益者及结果如何回查。

82874｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0394","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×身份伪装 关系搭配","description":"玄幻×身份伪装的关系网络组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002757","TSC_002758","TSC_002759"],"dynamic_rule_ids":["TDR_003","TDR_007"],"adaptation_ids":["ADAPT_B_00014","ADAPT_B_00015","ADAPT_B_00016"]}
【本步用法】把项目前置的伪装关系、真实身份和相关对象对照，核对每段关系能保持的条件与见证者。

82973｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0395","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×知识垄断 伏笔搭配","description":"玄幻叙事中知识垄断的伏笔密度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000790","TSC_000791","TSC_000792"],"dynamic_rule_ids":["TDR_003","TDR_008"],"adaptation_ids":["ADAPT_B_00010","ADAPT_B_00011","ADAPT_B_00012"]}
【本步用法】沿已有知识控制条件核对前文能留下的获取障碍或异常线索、分布位置及后文可验证的回收。

83072｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0396","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×情感纽带 风格搭配","description":"基于玄幻的情感纽带风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002341","TSC_002342","TSC_002343"],"dynamic_rule_ids":["TDR_003","TDR_009"],"adaptation_ids":["ADAPT_B_00040","ADAPT_B_00041","ADAPT_B_00042"]}
【本步用法】从已确认的情感纽带和关系变化出发，核对作者的表达基调如何在有依据的细节中显出变化。

83171｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0397","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×命运轨迹 项目组合","description":"玄幻项目模板下命运轨迹的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000440","TSC_000441","TSC_000442"],"dynamic_rule_ids":["TDR_003","TDR_010"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】按项目已有命运节点和线性成长安排核对先决事件、各阶段的选择及能观察到的结果。

83270｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0398","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×禁忌领域 静态搭配","description":"玄幻类型下的禁忌领域静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001661","TSC_001662","TSC_001663"],"dynamic_rule_ids":["TDR_003","TDR_011"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】把已设禁忌区域、稳定关系及接触条件对照，核对边界在成长阶段的适用对象和确定依据。

83369｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0399","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×传承体系 动态搭配","description":"玄幻中传承体系的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002553","TSC_002554","TSC_002555"],"dynamic_rule_ids":["TDR_003","TDR_012"],"adaptation_ids":["ADAPT_B_00108","ADAPT_B_00109","ADAPT_B_00110"]}
【本步用法】从已确认的传承事件出发，核对启动授受的条件、接受者状态变化及后续实际行动。

83468｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0400","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×背叛成本 表达配合","description":"玄幻语境下背叛成本的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002790","TSC_002791","TSC_002792"],"dynamic_rule_ids":["TDR_003","TDR_013"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】沿已有背叛及代价核对措辞和可见反应，查人物此时能够说出或观察到哪些代价。

83567｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0401","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×觉醒机制 场景搭配","description":"基于玄幻的觉醒机制场景调度搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000341","TSC_000342","TSC_000343"],"dynamic_rule_ids":["TDR_003","TDR_014"],"adaptation_ids":["ADAPT_B_00003","ADAPT_B_00004","ADAPT_B_00005"]}
【本步用法】按已定觉醒条件、人物和场景职责核对承接触发的元素、可见表现及动作所需的前置。

83666｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0402","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×世界观 冲突搭配","description":"玄幻中世界观引发的冲突维度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000966","TSC_000967","TSC_000968"],"dynamic_rule_ids":["TDR_003","TDR_015"],"adaptation_ids":["ADAPT_B_00017","ADAPT_B_00018","ADAPT_B_00019"]}
【本步用法】从已成立的世界规则核对哪种限制实际妨碍人物的成长目的，查行动如何引起对立及后果。

83765｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0403","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×力量体系 信息搭配","description":"玄幻类型下力量体系的信息控制搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001405","TSC_001406","TSC_001407"],"dynamic_rule_ids":["TDR_003","TDR_016"],"adaptation_ids":["ADAPT_B_00040","ADAPT_B_00041","ADAPT_B_00042"]}
【本步用法】对照已有力量体系和人物所知，核对其能披露的能力、使用边界及披露所改变的决定。

83864｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0404","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×身份设定 资源搭配","description":"玄幻×身份设定的资源争夺组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002715","TSC_002716","TSC_002717"],"dynamic_rule_ids":["TDR_003","TDR_017"],"adaptation_ids":["ADAPT_B_00037","ADAPT_B_00038","ADAPT_B_00039"]}
【本步用法】据现有身份和资源取得规则核对各方资格、可争夺的对象及身份变化影响的实际处置权。

83963｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0405","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×社交网络 关系搭配","description":"玄幻叙事中社交网络的关系张力组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001064","TSC_001065","TSC_001066"],"dynamic_rule_ids":["TDR_003","TDR_018"],"adaptation_ids":["ADAPT_B_00066","ADAPT_B_00067","ADAPT_B_00103"]}
【本步用法】沿已确立的社交网络核对角色之间的依赖与摩擦，定位哪些关系张力会推动已有行动。

84062｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0406","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×资源流通 伏笔搭配","description":"基于玄幻的资源流通伏笔标记搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002922","TSC_002923","TSC_002924"],"dynamic_rule_ids":["TDR_003","TDR_019"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】把前文已有的流通对象、归属变化和后继节点对照，核对可追踪的伏笔标记和证实位置。

84161｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0407","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×信息控制 风格搭配","description":"玄幻风格体系中信息控制的美学组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000661","TSC_000662","TSC_000663"],"dynamic_rule_ids":["TDR_003","TDR_020"],"adaptation_ids":["ADAPT_B_00066","ADAPT_B_00067","ADAPT_B_00103"]}
【本步用法】按项目前置的信息控制边界核对作者所选风格可呈现的内容、人物知情范围和延后披露的线索。

84260｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0408","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×时间线 项目组合","description":"玄幻类型时间线的项目结构搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000724","TSC_000725","TSC_000726"],"dynamic_rule_ids":["TDR_003","TDR_021"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】沿已定线性时间线核对各成长阶段的先后、相连事件和确认时点，查已有物件的时间标记是否可用。

84359｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0409","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×空间布局 静态搭配","description":"基于玄幻的类型兼容空间布局搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001476","TSC_001477","TSC_001478"],"dynamic_rule_ids":["TDR_003","TDR_022"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】根据已有地点、通路和对象位置核对稳定的空间关系，以及人物实际能怎样抵达或观察。

84458｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0410","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×因果链条 动态搭配","description":"玄幻×因果链条的动态传播搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000499","TSC_000500","TSC_000501"],"dynamic_rule_ids":["TDR_003","TDR_023"],"adaptation_ids":["ADAPT_B_00018","ADAPT_B_00019","ADAPT_B_00020"]}
【本步用法】以已成立的因果和状态变化为据，核对后果怎样传到相关角色或对象，以及可验证的后继行为。

84557｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XUANHUAN_0411","combination_kind":"EXPRESSION_COMBINATION","combination_name":"玄幻×道德困境 表达配合","description":"适配玄幻的道德困境表达参数组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002069","TSC_002070","TSC_002071"],"dynamic_rule_ids":["TDR_003","TDR_024"],"adaptation_ids":["ADAPT_B_00002","ADAPT_B_00003","ADAPT_B_00004"]}
【本步用法】按已定道德界线和确切选择核对表达参数，查措辞或可见行动能把哪项代价呈现出来。

84656｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XUANHUAN_0412","combination_kind":"SCENE_COMBINATION","combination_name":"玄幻×生存压力 场景搭配","description":"玄幻中生存压力的场景构建组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002153","TSC_002154","TSC_002155"],"dynamic_rule_ids":["TDR_003","TDR_025"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】把项目既有的资源缺口、角色需求和当场目标对照，核对场景中可观察的生存压力与对应反应。

84755｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XUANHUAN_0413","combination_kind":"CONFLICT_COMBINATION","combination_name":"玄幻×权力博弈 冲突搭配","description":"玄幻类型权力博弈的对立冲突搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002799","TSC_002800","TSC_002801"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】沿前置权力关系和各方行使权限的条件，核对触发对立的实际行为、可选回应和冲突的结果。

84852｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XUANHUAN_0414","combination_kind":"INFORMATION_COMBINATION","combination_name":"玄幻×身份伪装 信息搭配","description":"玄幻×身份伪装的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001243","TSC_001244","TSC_001245"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】以各线真实身份、伪装身份及知情范围为据，核对谁能够在何时获得对应信息及其实际作用。

84949｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XUANHUAN_0415","combination_kind":"RESOURCE_COMBINATION","combination_name":"玄幻×知识垄断 资源搭配","description":"玄幻世界中知识垄断的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002879","TSC_002880","TSC_002881"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00061","ADAPT_B_00062","ADAPT_B_00063"]}
【本步用法】从已有知识持有者和资源取得路径出发，核对掌握的知识如何影响资源获取、倒叙能交代哪些取得前提。

85046｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XUANHUAN_0416","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"玄幻×情感纽带 关系搭配","description":"基于玄幻的情感纽带关系演化搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000304","TSC_000305","TSC_000306"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00044","ADAPT_B_00045","ADAPT_B_00046"]}
【本步用法】对照既有情感关系和资源积累，核对能够改变关系的具体支持、资源转移与可观察的后果。

85143｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XUANHUAN_0417","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"玄幻×命运轨迹 伏笔搭配","description":"玄幻伏笔线索中命运轨迹的预置组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001240","TSC_001241","TSC_001242"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】按各线已定命运节点和资源变化核对可以先埋的实际线索及后续验证所需的前置。

85240｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XUANHUAN_0418","combination_kind":"STYLE_COMBINATION","combination_name":"玄幻×禁忌领域 风格搭配","description":"玄幻类型下禁忌领域的风格变奏搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001269","TSC_001270","TSC_001271"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】从已划定禁忌、资源积累和倒叙安排出发，核对作者选择的风格能呈现哪些早期边界及资源限制。

85337｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XUANHUAN_0419","combination_kind":"PROJECT_COMBINATION","combination_name":"玄幻×传承体系 项目组合","description":"玄幻×传承体系的项目配置组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001228","TSC_001229","TSC_001230"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00045","ADAPT_B_00046","ADAPT_B_00047"]}
【本步用法】把已确认的传承条件和各方知情差放入项目安排，核对线性进程里授受、披露与前置证据的时序。

85434｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XUANHUAN_0420","combination_kind":"STATIC_COMBINATION","combination_name":"玄幻×背叛成本 静态搭配","description":"玄幻×背叛成本的静态连接搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000939","TSC_000940","TSC_000941"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00042","ADAPT_B_00043","ADAPT_B_00044"]}
【本步用法】根据已有背叛代价和各线知情范围核对稳定关系、相关对象和后果得以成立的条件。

85531｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XUANHUAN_0421","combination_kind":"DYNAMIC_COMBINATION","combination_name":"玄幻×觉醒机制 动态搭配","description":"玄幻中基于觉醒机制的动态行为组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000098","TSC_000099","TSC_000100"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00046","ADAPT_B_00047","ADAPT_B_00048"]}
【本步用法】对照已定觉醒触发、人物所知及倒叙安排，核对觉醒后的实际行动与可回查的状态变化。"""
