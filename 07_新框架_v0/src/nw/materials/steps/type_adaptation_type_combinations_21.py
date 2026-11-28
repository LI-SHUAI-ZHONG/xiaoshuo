"""类型适配步骤中的第 1161–1215 条组合原文及用法。"""

MATERIAL = """【《类型系统》类型组合总表｜类型适配｜第 1161–1215 条】
【原文位置】第 56 个来源块始于第 42,967 行。本段为正文表顺序第 1161–1215 条，前缀指组合 ID 字段的物理原件行。
【本步用法】按作者采用的类型、项目已有前置与当前设计用途核对各组合的作用和条件。现行裁定为 blocked 的条目供查原值、用途和待核项。原文留空的子类型与风格字段照录，项目具体选择以作者确认的设定为据。
【各条共用原文值】{"primary_type_id":"GENRE_YANQING","type_ids":["GENRE_YANQING"],"subtype_ids":[],"hybrid_ids":[],"style_ids":[],"tone_ids":[],"audience_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"foreshadowing_type_ids":[],"selection_status":"candidate","source_refs":["type_combination_template"],"evidence_type":"inferred","status":"candidate","schema_version":"2.0"}
【逐条精简值】每条由共用值与本行有效组成字段合并而成，已剔除合成随机评分与跨类型污染外键。

161102｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YANQING_1162","combination_kind":"INFORMATION_COMBINATION","combination_name":"言情×世界观 信息搭配","description":"言情信息流中世界观的信息差组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001735","TSC_001736","TSC_001737"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00019","ADAPT_B_00020","ADAPT_B_00021"]}
【本步用法】依已有世界规则、资源积累与回溯范围，核对倒叙可交代的规则信息、人物所知及相关资源状态。

161199｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YANQING_1163","combination_kind":"RESOURCE_COMBINATION","combination_name":"言情×力量体系 资源搭配","description":"言情类型下力量体系的资源分配搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001063","TSC_001064","TSC_001065"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00010","ADAPT_B_00011","ADAPT_B_00012"]}
【本步用法】从既定力量条件与人物知情差出发，核对谁能接触何种资源、所需前置及实际分配依据。

161296｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YANQING_1164","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"言情×身份设定 关系搭配","description":"言情×身份设定的关系网络组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002164","TSC_002165","TSC_002166"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00019","ADAPT_B_00020","ADAPT_B_00021"]}
【本步用法】沿各线既有身份关系和信息差，核对哪些人知道哪层身份，以及获知后会如何影响原有联系。

161393｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YANQING_1165","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"言情×社交网络 伏笔搭配","description":"言情叙事中社交网络的伏笔密度组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002513","TSC_002514","TSC_002515"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】根据已建立的社交网络和倒叙时点，核对可较早显示的关系线索、当时的可见范围及后续确认条件。

161490｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YANQING_1166","combination_kind":"STYLE_COMBINATION","combination_name":"言情×资源流通 风格搭配","description":"基于言情的资源流通风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002486","TSC_002487","TSC_002488"],"dynamic_rule_ids":["TDR_001","TDR_002"],"adaptation_ids":["ADAPT_B_00106","ADAPT_B_00107","ADAPT_B_00108"]}
【本步用法】按现有资源转移、归属和角色成长核对所选风格，查哪些叙述细节能让流向及其实际变化可见。

161589｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YANQING_1167","combination_kind":"PROJECT_COMBINATION","combination_name":"言情×信息控制 项目组合","description":"言情项目模板下信息控制的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001573","TSC_001574","TSC_001575"],"dynamic_rule_ids":["TDR_001","TDR_003"],"adaptation_ids":["ADAPT_B_00013","ADAPT_B_00014","ADAPT_B_00015"]}
【本步用法】把已有信息权限、披露时点与成长安排纳入项目骨架，核对各阶段的知情者及披露所依赖的事实。

161688｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YANQING_1168","combination_kind":"STATIC_COMBINATION","combination_name":"言情×时间线 静态搭配","description":"言情类型下的时间线静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000686","TSC_000687","TSC_000688"],"dynamic_rule_ids":["TDR_001","TDR_004"],"adaptation_ids":["ADAPT_B_00036","ADAPT_B_00037","ADAPT_B_00038"]}
【本步用法】从已确定的时间标记及事件顺序出发，核对线性进程中稳定的时序关联及依据。

161787｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YANQING_1169","combination_kind":"DYNAMIC_COMBINATION","combination_name":"言情×空间布局 动态搭配","description":"言情中空间布局的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002894","TSC_002895","TSC_002896"],"dynamic_rule_ids":["TDR_001","TDR_005"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】依已有地点、通路与触发事件，核对空间怎样变化、影响哪些人物及可追查的结果。

161886｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YANQING_1170","combination_kind":"EXPRESSION_COMBINATION","combination_name":"言情×因果链条 表达配合","description":"言情语境下因果链条的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000325","TSC_000326","TSC_000327"],"dynamic_rule_ids":["TDR_001","TDR_006"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】沿已经成立的因果链与成长节点，核对表达可以呈现的前因、行动及能够证实的后果。

161985｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YANQING_1171","combination_kind":"SCENE_COMBINATION","combination_name":"言情×道德困境 场景搭配","description":"基于言情的道德困境场景调度搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000435","TSC_000436","TSC_000437"],"dynamic_rule_ids":["TDR_001","TDR_007"],"adaptation_ids":["ADAPT_B_00045","ADAPT_B_00046","ADAPT_B_00047"]}
【本步用法】以既定道德界线和场景目的为据，核对在场人有何选择、哪些行动显示两难以及实际代价。

162084｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YANQING_1172","combination_kind":"CONFLICT_COMBINATION","combination_name":"言情×生存压力 冲突搭配","description":"言情中生存压力引发的冲突维度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002863","TSC_002864","TSC_002865"],"dynamic_rule_ids":["TDR_001","TDR_008"],"adaptation_ids":["ADAPT_B_00058","ADAPT_B_00059","ADAPT_B_00060"]}
【本步用法】从已有生存压力和人物目标出发，核对何种限制引起对立、各方如何行动与对应的结果。

162183｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YANQING_1173","combination_kind":"INFORMATION_COMBINATION","combination_name":"言情×权力博弈 信息搭配","description":"言情类型下权力博弈的信息控制搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002143","TSC_002144","TSC_002145"],"dynamic_rule_ids":["TDR_001","TDR_009"],"adaptation_ids":["ADAPT_B_00114","ADAPT_B_00115","ADAPT_B_00116"]}
【本步用法】依据已定权力配置及人物知情范围，核对哪类权限信息能在何时披露、会改变哪个决定。

162282｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YANQING_1174","combination_kind":"RESOURCE_COMBINATION","combination_name":"言情×身份伪装 资源搭配","description":"言情×身份伪装的资源争夺组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000095","TSC_000096","TSC_000097"],"dynamic_rule_ids":["TDR_001","TDR_010"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】沿已确认的伪装身份和资源准入，核对获取资格、争夺对象及后续可查的资源归属。

162381｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YANQING_1175","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"言情×知识垄断 关系搭配","description":"言情叙事中知识垄断的关系张力组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001101","TSC_001102","TSC_001103"],"dynamic_rule_ids":["TDR_001","TDR_011"],"adaptation_ids":["ADAPT_B_00009","ADAPT_B_00010","ADAPT_B_00011"]}
【本步用法】根据现有知识持有与准入条件，核对由知识控制引起的人物依赖、疏离或摩擦及可见表现。

162480｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YANQING_1176","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"言情×情感纽带 伏笔搭配","description":"基于言情的情感纽带伏笔标记搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002934","TSC_002935","TSC_002936"],"dynamic_rule_ids":["TDR_001","TDR_012"],"adaptation_ids":["ADAPT_B_00009","ADAPT_B_00010","ADAPT_B_00011"]}
【本步用法】把已有情感纽带和后来的关系变化对照，核对前文可留下的行为标记及兑现所需的证据。

162579｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YANQING_1177","combination_kind":"STYLE_COMBINATION","combination_name":"言情×命运轨迹 风格搭配","description":"言情风格体系中命运轨迹的美学组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003069","TSC_003070","TSC_003071"],"dynamic_rule_ids":["TDR_001","TDR_013"],"adaptation_ids":["ADAPT_B_00027","ADAPT_B_00028","ADAPT_B_00029"]}
【本步用法】依已定命运节点及作者所选风格核对表现，查哪些可观察细节能反映轨迹变化与成长。

162678｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YANQING_1178","combination_kind":"PROJECT_COMBINATION","combination_name":"言情×禁忌领域 项目组合","description":"言情类型禁忌领域的项目结构搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002456","TSC_002457","TSC_002458"],"dynamic_rule_ids":["TDR_001","TDR_014"],"adaptation_ids":["ADAPT_B_00012","ADAPT_B_00013","ADAPT_B_00014"]}
【本步用法】按既有禁忌范围和线性阶段目标核对项目计划，查何时接触禁忌、需先具备哪些条件。

162777｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YANQING_1179","combination_kind":"STATIC_COMBINATION","combination_name":"言情×传承体系 静态搭配","description":"基于言情的类型兼容传承体系搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002779","TSC_002780","TSC_002781"],"dynamic_rule_ids":["TDR_001","TDR_015"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】沿已定传承规则、稳定关系与相关对象，核对授受资格和可以反复成立的条件。

162876｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YANQING_1180","combination_kind":"DYNAMIC_COMBINATION","combination_name":"言情×背叛成本 动态搭配","description":"言情×背叛成本的动态传播搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002045","TSC_002046","TSC_002047"],"dynamic_rule_ids":["TDR_001","TDR_016"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】从已知背叛代价出发核对传播的触发、涉及的人或资源，以及之后的行为和状态变化。

162975｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YANQING_1181","combination_kind":"EXPRESSION_COMBINATION","combination_name":"言情×觉醒机制 表达配合","description":"适配言情的觉醒机制表达参数组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002429","TSC_002430","TSC_002431"],"dynamic_rule_ids":["TDR_001","TDR_017"],"adaptation_ids":["ADAPT_B_00024","ADAPT_B_00025","ADAPT_B_00026"]}
【本步用法】对照已有觉醒机制和可验证的结果，核对项目措辞或可见细节怎样表现觉醒的实际作用。

163074｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YANQING_1182","combination_kind":"SCENE_COMBINATION","combination_name":"言情×世界观 场景搭配","description":"言情中世界观的场景构建组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002864","TSC_002865","TSC_002866"],"dynamic_rule_ids":["TDR_001","TDR_018"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】以项目已有世界规则和本场用途为据，核对哪些现场对象、动作与限制能让规则可被观察。

163173｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YANQING_1183","combination_kind":"CONFLICT_COMBINATION","combination_name":"言情×力量体系 冲突搭配","description":"言情类型力量体系的对立冲突搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001208","TSC_001209","TSC_001210"],"dynamic_rule_ids":["TDR_001","TDR_019"],"adaptation_ids":["ADAPT_B_00115","ADAPT_B_00116","ADAPT_B_00117"]}
【本步用法】沿既定力量边界及人物目标核对冲突，查各方的可用能力、对立条件与可观察后果。

163272｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YANQING_1184","combination_kind":"INFORMATION_COMBINATION","combination_name":"言情×身份设定 信息搭配","description":"言情×身份设定的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001263","TSC_001264","TSC_001265"],"dynamic_rule_ids":["TDR_001","TDR_020"],"adaptation_ids":["ADAPT_B_00041","ADAPT_B_00042","ADAPT_B_00043"]}
【本步用法】用已确认的身份资料、公开信息及人物所知核对披露顺序，查哪项身份信息会影响当前选择。

163371｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YANQING_1185","combination_kind":"RESOURCE_COMBINATION","combination_name":"言情×社交网络 资源搭配","description":"言情世界中社交网络的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000472","TSC_000473","TSC_000474"],"dynamic_rule_ids":["TDR_001","TDR_021"],"adaptation_ids":["ADAPT_B_00107","ADAPT_B_00108","ADAPT_B_00109"]}
【本步用法】从已有社交网络和资源需要出发，核对提供者、接触条件与实际可用的取得路径。

163470｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YANQING_1186","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"言情×资源流通 关系搭配","description":"基于言情的资源流通关系演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000611","TSC_000612","TSC_000613"],"dynamic_rule_ids":["TDR_001","TDR_022"],"adaptation_ids":["ADAPT_B_00052","ADAPT_B_00053","ADAPT_B_00057"]}
【本步用法】按已经成立的资源流向与人物交换关系，核对资源得失如何改变依赖以及可回查的依据。

163569｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YANQING_1187","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"言情×信息控制 伏笔搭配","description":"言情伏笔线索中信息控制的预置组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002161","TSC_002162","TSC_002163"],"dynamic_rule_ids":["TDR_001","TDR_023"],"adaptation_ids":["ADAPT_B_00016","ADAPT_B_00017","ADAPT_B_00018"]}
【本步用法】依已设信息控制和后续验证点，核对前文可留下的具体线索、人物可知范围及证实位置。

163668｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YANQING_1188","combination_kind":"STYLE_COMBINATION","combination_name":"言情×时间线 风格搭配","description":"言情类型下时间线的风格变奏搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000712","TSC_000713","TSC_000714"],"dynamic_rule_ids":["TDR_001","TDR_024"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】把各已定时点和作者选用的写法对照，核对读者如何从具体标记明白前后事件关系。

163767｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YANQING_1189","combination_kind":"PROJECT_COMBINATION","combination_name":"言情×空间布局 项目组合","description":"言情×空间布局的项目配置组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001404","TSC_001405","TSC_001406"],"dynamic_rule_ids":["TDR_001","TDR_025"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】沿已有空间安排、通行路径与成长目标核对项目，查各节点实际可达的位置和前置。

163866｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YANQING_1190","combination_kind":"STATIC_COMBINATION","combination_name":"言情×因果链条 静态搭配","description":"言情×因果链条的静态连接搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003131","TSC_003132","TSC_003133"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】从已成立的因果关系出发，核对相对稳定的前提、结果对象与能为后继变化提供的依据。

163963｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YANQING_1191","combination_kind":"DYNAMIC_COMBINATION","combination_name":"言情×道德困境 动态搭配","description":"言情中基于道德困境的动态行为组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002662","TSC_002663","TSC_002664"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】按各线既有道德界线和具体取舍，核对哪项选择触发状态或关系变化及可观察代价。

164060｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YANQING_1192","combination_kind":"EXPRESSION_COMBINATION","combination_name":"言情×生存压力 表达配合","description":"言情中生存压力的语言表达适配组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001565","TSC_001566","TSC_001567"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00005","ADAPT_B_00006","ADAPT_B_00007"]}
【本步用法】依据已有生存压力、事件先后和回溯范围，核对表达能呈现的短缺前因与后来可见影响。

164157｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YANQING_1193","combination_kind":"SCENE_COMBINATION","combination_name":"言情×权力博弈 场景搭配","description":"言情类型下权力博弈的场景布局搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002134","TSC_002135","TSC_002136"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00002","ADAPT_B_00003","ADAPT_B_00004"]}
【本步用法】把既定权力位置、资源积累和本场任务对照，核对在场角色的行动权限及可展示的对象。

164254｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YANQING_1194","combination_kind":"CONFLICT_COMBINATION","combination_name":"言情×身份伪装 冲突搭配","description":"言情×身份伪装的冲突机制组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000487","TSC_000488","TSC_000489"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00019","ADAPT_B_00020","ADAPT_B_00021"]}
【本步用法】沿多线既有伪装、资源归属和积累条件，核对因身份变化或争议而产生对立的前置和后果。

164351｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YANQING_1195","combination_kind":"INFORMATION_COMBINATION","combination_name":"言情×知识垄断 信息搭配","description":"言情叙事中知识垄断的信息披露节奏组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001416","TSC_001417","TSC_001418"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00115","ADAPT_B_00116","ADAPT_B_00117"]}
【本步用法】从已有知识垄断、资源积累和倒叙时点出发，核对知识何时可披露及与资源取得的关系。

164448｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YANQING_1196","combination_kind":"RESOURCE_COMBINATION","combination_name":"言情×情感纽带 资源搭配","description":"基于言情的情感纽带资源转换搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000454","TSC_000455","TSC_000456"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00115","ADAPT_B_00116","ADAPT_B_00117"]}
【本步用法】按已建立的情感纽带与各方所知核对可提供的资源，查哪次获知会影响支持、转换及其代价。

164545｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YANQING_1197","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"言情×命运轨迹 关系搭配","description":"言情中命运轨迹的人际关系组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000511","TSC_000512","TSC_000513"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00107","ADAPT_B_00108","ADAPT_B_00109"]}
【本步用法】把各线既定命运节点、人物关系和知情差对照，核对一项关系因何成立或改变以及谁能确认。

164642｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YANQING_1198","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"言情×禁忌领域 伏笔搭配","description":"言情类型下禁忌领域的伏笔铺设搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000270","TSC_000271","TSC_000272"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00113","ADAPT_B_00114","ADAPT_B_00115"]}
【本步用法】以已有禁忌规则、回溯位置和人物所知为据，核对早先可出现的线索及后文能验证的边界。

164739｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YANQING_1199","combination_kind":"STYLE_COMBINATION","combination_name":"言情×传承体系 风格搭配","description":"言情×传承体系的叙述风格组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000142","TSC_000143","TSC_000144"],"dynamic_rule_ids":["TDR_002","TDR_003"],"adaptation_ids":["ADAPT_B_00025","ADAPT_B_00026","ADAPT_B_00027"]}
【本步用法】结合已有传承规则和作者确认的风格，核对叙述怎样表现授受条件、具体关系和可查的行为。

164838｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YANQING_1200","combination_kind":"PROJECT_COMBINATION","combination_name":"言情×背叛成本 项目组合","description":"言情写作中背叛成本的项目规划组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002517","TSC_002518","TSC_002519"],"dynamic_rule_ids":["TDR_002","TDR_004"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】沿已知背叛成本和成长阶段核对项目节点，查代价发生的前因、涉及对象与后续证据。

164937｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YANQING_1201","combination_kind":"STATIC_COMBINATION","combination_name":"言情×觉醒机制 静态搭配","description":"言情世界中觉醒机制的静态结构组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002663","TSC_002664","TSC_002665"],"dynamic_rule_ids":["TDR_002","TDR_005"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】从已确立的觉醒条件与稳定规则出发，核对所需对象、相对稳定的限制和支撑成长的依据。

165036｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YANQING_1202","combination_kind":"DYNAMIC_COMBINATION","combination_name":"言情×世界观 动态搭配","description":"言情动态规则触发下的世界观变化","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002905","TSC_002906","TSC_002907"],"dynamic_rule_ids":["TDR_002","TDR_006"],"adaptation_ids":["ADAPT_B_00019","ADAPT_B_00020","ADAPT_B_00021"]}
【本步用法】由前置世界状态与实际事件出发，核对动态规则触发后哪些既有条件改变及可见结果。

165135｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YANQING_1203","combination_kind":"EXPRESSION_COMBINATION","combination_name":"言情×力量体系 表达配合","description":"言情类型力量体系的语气风格表达搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000715","TSC_000716","TSC_000717"],"dynamic_rule_ids":["TDR_002","TDR_007"],"adaptation_ids":["ADAPT_B_00103","ADAPT_B_00104","ADAPT_B_00105"]}
【本步用法】按既有力量体系与可见表现，核对项目选用的语言或动作可以呈现的能力差异和限制。

165234｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YANQING_1204","combination_kind":"SCENE_COMBINATION","combination_name":"言情×身份设定 场景搭配","description":"言情×身份设定场景元素组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002974","TSC_002975","TSC_002976"],"dynamic_rule_ids":["TDR_002","TDR_008"],"adaptation_ids":["ADAPT_B_00010","ADAPT_B_00011","ADAPT_B_00012"]}
【本步用法】依项目已有身份、识别标记及在场条件，核对场景能够展示的线索、观察者与证据。

165333｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YANQING_1205","combination_kind":"CONFLICT_COMBINATION","combination_name":"言情×社交网络 冲突搭配","description":"言情叙事中社交网络的冲突层次组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000683","TSC_000684","TSC_000685"],"dynamic_rule_ids":["TDR_002","TDR_009"],"adaptation_ids":["ADAPT_B_00033","ADAPT_B_00034","ADAPT_B_00035"]}
【本步用法】沿已有社交网络核对人物需求和冲突层次，查哪个联系或限制实际推动当前对立。

165432｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YANQING_1206","combination_kind":"INFORMATION_COMBINATION","combination_name":"言情×资源流通 信息搭配","description":"基于言情的资源流通信息博弈搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002802","TSC_002803","TSC_002804"],"dynamic_rule_ids":["TDR_002","TDR_010"],"adaptation_ids":["ADAPT_B_00046","ADAPT_B_00047","ADAPT_B_00048"]}
【本步用法】结合已有资源流向与各方所知，核对转移信息何时可以给出及对相应取用或交易的作用。

165531｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YANQING_1207","combination_kind":"RESOURCE_COMBINATION","combination_name":"言情×信息控制 资源搭配","description":"言情资源体系中信息控制的稀缺约束组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000567","TSC_000568","TSC_000569"],"dynamic_rule_ids":["TDR_002","TDR_011"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】从已确认的信息权限和资源稀缺需求出发，核对取得信息所需资源与影响实际获取的限制。

165630｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YANQING_1208","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"言情×时间线 关系搭配","description":"言情类型下时间线的社会纽带搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001895","TSC_001896","TSC_001897"],"dynamic_rule_ids":["TDR_002","TDR_012"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】按既定时序核对人物关系的成立、持续和变化，定位前文或后文能查证的事件。

165729｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YANQING_1209","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"言情×空间布局 伏笔搭配","description":"言情×空间布局的伏笔回收组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001274","TSC_001275","TSC_001276"],"dynamic_rule_ids":["TDR_002","TDR_013"],"adaptation_ids":["ADAPT_B_00039","ADAPT_B_00040","ADAPT_B_00041"]}
【本步用法】把已经出现的地点或路径线索同既有布局对照，核对回收时能证明的位置关系和显示条件。

165828｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YANQING_1210","combination_kind":"STYLE_COMBINATION","combination_name":"言情×因果链条 风格搭配","description":"言情语境中因果链条的风格基调组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001884","TSC_001885","TSC_001886"],"dynamic_rule_ids":["TDR_002","TDR_014"],"adaptation_ids":["ADAPT_B_00012","ADAPT_B_00013","ADAPT_B_00014"]}
【本步用法】以既有因果链和成长节点为据，核对作者确定的基调怎样呈现事件变化与可查结果。

165927｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YANQING_1211","combination_kind":"PROJECT_COMBINATION","combination_name":"言情×道德困境 项目组合","description":"基于言情的道德困境项目骨架搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000425","TSC_000426","TSC_000427"],"dynamic_rule_ids":["TDR_002","TDR_015"],"adaptation_ids":["ADAPT_B_00048","ADAPT_B_00049","ADAPT_B_00050"]}
【本步用法】把已定道德困境、人物选择与成长阶段对应到项目安排，核对各决策的前置及代价。

166026｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YANQING_1212","combination_kind":"STATIC_COMBINATION","combination_name":"言情×生存压力 静态搭配","description":"言情与稳定关系生存压力的静态搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002030","TSC_002031","TSC_002032"],"dynamic_rule_ids":["TDR_002","TDR_016"],"adaptation_ids":["ADAPT_B_00015","ADAPT_B_00016","ADAPT_B_00017"]}
【本步用法】用已有生存条件、资源约束与稳定依赖关系核对压力来源，确认这些条件如何支撑后续安排。

166125｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YANQING_1213","combination_kind":"DYNAMIC_COMBINATION","combination_name":"言情×权力博弈 动态搭配","description":"言情类型权力博弈动态演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001029","TSC_001030","TSC_001031"],"dynamic_rule_ids":["TDR_002","TDR_017"],"adaptation_ids":["ADAPT_B_00002","ADAPT_B_00003","ADAPT_B_00004"]}
【本步用法】沿既有权力关系和触发事件，核对谁的权限改变、实际影响到谁及随后可观察的状态或行动。

166224｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YANQING_1214","combination_kind":"EXPRESSION_COMBINATION","combination_name":"言情×身份伪装 表达配合","description":"言情×身份伪装的修辞表达组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002854","TSC_002855","TSC_002856"],"dynamic_rule_ids":["TDR_002","TDR_018"],"adaptation_ids":["ADAPT_B_00007","ADAPT_B_00008","ADAPT_B_00009"]}
【本步用法】从已设伪装与人物所知出发，核对采用的表达能显出哪些身份线索、哪些信息留待后续。

166323｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YANQING_1215","combination_kind":"SCENE_COMBINATION","combination_name":"言情×知识垄断 场景搭配","description":"言情世界观中知识垄断的场景呈现组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001493","TSC_001494","TSC_001495"],"dynamic_rule_ids":["TDR_002","TDR_019"],"adaptation_ids":["ADAPT_B_00024","ADAPT_B_00025","ADAPT_B_00026"]}
【本步用法】按前置的知识门槛、在场者及场景任务，核对可观察的取得条件、限制与对应行动。

166422｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YANQING_1216","combination_kind":"CONFLICT_COMBINATION","combination_name":"言情×情感纽带 冲突搭配","description":"基于言情的情感纽带冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000160","TSC_000161","TSC_000162"],"dynamic_rule_ids":["TDR_002","TDR_020"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】依已有情感纽带和人物动机核对对立缘由、可行的选择及关系受到的实际影响。"""
