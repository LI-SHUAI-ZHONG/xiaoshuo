"""类型适配步骤中的第 1841–1890 条组合原文及用法。"""

MATERIAL = """【《类型系统》类型组合总表｜类型适配｜第 1841–1890 条】
【原文位置】第 56 个来源块始于第 42,967 行。本段为正文表顺序第 1841–1890 条，前缀指组合 ID 字段的物理原件行。
【本步用法】按作者采用的类型、项目已有前置与当前设计需求核对各条组合的作用及成立条件。现行裁定为 blocked 的组合供查原值、用途和待核项。子类型、风格的空值按原文保留，项目具体采用以作者已确认的设定为据。
【各条共用原文值】{"primary_type_id":"GENRE_YOUXI","type_ids":["GENRE_YOUXI"],"subtype_ids":[],"hybrid_ids":[],"style_ids":[],"tone_ids":[],"audience_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"foreshadowing_type_ids":[],"selection_status":"candidate","source_refs":["type_combination_template"],"evidence_type":"inferred","status":"candidate","schema_version":"2.0"}
【逐条精简值】每条由共用值与本行有效组成字段合并而成，已剔除合成随机评分与跨类型污染外键。

229800｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YOUXI_1842","combination_kind":"SCENE_COMBINATION","combination_name":"游戏×世界观 场景搭配","description":"游戏中世界观的场景构建组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002322","TSC_002323","TSC_002324"],"dynamic_rule_ids":["TDR_002","TDR_016"],"adaptation_ids":["ADAPT_B_00034","ADAPT_B_00035","ADAPT_B_00036"]}
【本步用法】依据已确认的世界规则和成长阶段，核对现有场景借通行、使用物件或受到限制展示哪条规则，并确认相关伏笔当前具备的证据。

229899｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YOUXI_1843","combination_kind":"CONFLICT_COMBINATION","combination_name":"游戏×力量体系 冲突搭配","description":"游戏类型力量体系的对立冲突搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001317","TSC_001318","TSC_001319"],"dynamic_rule_ids":["TDR_002","TDR_017"],"adaptation_ids":["ADAPT_B_00043","ADAPT_B_00044","ADAPT_B_00045"]}
【本步用法】对照既定力量上限及各方已知的能力，核查差距具体阻断了什么目标，各次对抗是否与已确认的升级节点相合。

229998｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YOUXI_1844","combination_kind":"INFORMATION_COMBINATION","combination_name":"游戏×身份设定 信息搭配","description":"游戏×身份设定的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_003102","TSC_003103","TSC_003104"],"dynamic_rule_ids":["TDR_002","TDR_018"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】按既定身份与当前知情范围，核对旁人看见哪些凭证、如何理解异常，以及已有反应足以支持哪一项身份推断。

230097｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YOUXI_1845","combination_kind":"RESOURCE_COMBINATION","combination_name":"游戏×社交网络 资源搭配","description":"游戏世界中社交网络的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002614","TSC_002615","TSC_002616"],"dynamic_rule_ids":["TDR_002","TDR_019"],"adaptation_ids":["ADAPT_B_00014","ADAPT_B_00015","ADAPT_B_00016"]}
【本步用法】顺既定社交关系核对资源经谁引介、交换或消耗，查请求条件、实际交付和剩余状态能否支撑已定的获得结果。

230196｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YOUXI_1846","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"游戏×资源流通 关系搭配","description":"基于游戏的资源流通关系演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002894","TSC_002895","TSC_002896"],"dynamic_rule_ids":["TDR_002","TDR_020"],"adaptation_ids":["ADAPT_B_00111","ADAPT_B_00112","ADAPT_B_00113"]}
【本步用法】依据既有流通权限和人物联系，核查一次交付、缺损或中止会触及谁的承诺，并对照已发生的资源变化定位关系转折。

230295｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YOUXI_1847","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"游戏×信息控制 伏笔搭配","description":"游戏伏笔线索中信息控制的预置组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000968","TSC_000969","TSC_000970"],"dynamic_rule_ids":["TDR_002","TDR_021"],"adaptation_ids":["ADAPT_B_00045","ADAPT_B_00046","ADAPT_B_00047"]}
【本步用法】由已定披露点前查谁从何处取得或受到限制，标出可先出现的准入痕迹和见证者，核查它与后续证据指向的信息。

230394｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YOUXI_1848","combination_kind":"STYLE_COMBINATION","combination_name":"游戏×时间线 风格搭配","description":"游戏类型下时间线的风格变奏搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000941","TSC_000942","TSC_000943"],"dynamic_rule_ids":["TDR_002","TDR_022"],"adaptation_ids":["ADAPT_B_00005","ADAPT_B_00006","ADAPT_B_00007"]}
【本步用法】按既定事件次序和已确认的风格，核查时间标记、延宕与揭示所占篇幅，确认转场留下的人物所知与当时状态连续。

230493｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YOUXI_1849","combination_kind":"PROJECT_COMBINATION","combination_name":"游戏×空间布局 项目组合","description":"游戏×空间布局的项目配置组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001139","TSC_001140","TSC_001141"],"dynamic_rule_ids":["TDR_002","TDR_023"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】按项目现有成长阶段整理常用地点、交通路径和关键物件分布，核查地点可达性对各阶段行动的支持，回查已有伤势对路线的影响。

230592｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YOUXI_1850","combination_kind":"STATIC_COMBINATION","combination_name":"游戏×因果链条 静态搭配","description":"游戏×因果链条的静态连接搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001112","TSC_001113","TSC_001114"],"dynamic_rule_ids":["TDR_002","TDR_024"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】依据既定因果关系核查哪些前提在不同事件间持续有效，包括稳定约束、人物底线和所需物件的可用状态。

230691｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YOUXI_1851","combination_kind":"DYNAMIC_COMBINATION","combination_name":"游戏×道德困境 动态搭配","description":"游戏中基于道德困境的动态行为组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002079","TSC_002080","TSC_002081"],"dynamic_rule_ids":["TDR_002","TDR_025"],"adaptation_ids":["ADAPT_B_00012","ADAPT_B_00013","ADAPT_B_00014"]}
【本步用法】以已确定的伦理选择为起点，核查行为发生前后的资源和关系证据，查既有社会压力会由哪些已成立联系传向有关人物。

230790｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YOUXI_1852","combination_kind":"EXPRESSION_COMBINATION","combination_name":"游戏×生存压力 表达配合","description":"游戏中生存压力的语言表达适配组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001202","TSC_001203","TSC_001204"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00006","ADAPT_B_00007","ADAPT_B_00008"]}
【本步用法】按已定补给和实体状态核对描写的用词，从可见体力、装备与行动限制呈现生存压力，并与人物当时的判断分开记录。

230887｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YOUXI_1853","combination_kind":"SCENE_COMBINATION","combination_name":"游戏×权力博弈 场景搭配","description":"游戏类型下权力博弈的场景布局搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001219","TSC_001220","TSC_001221"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00036","ADAPT_B_00037","ADAPT_B_00038"]}
【本步用法】对照多线已定权属与冲突位置，核查各场景能展示哪项权限的行使、质疑或失效，保持参与者和可用物件在各线间衔接。

230984｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YOUXI_1854","combination_kind":"CONFLICT_COMBINATION","combination_name":"游戏×身份伪装 冲突搭配","description":"游戏×身份伪装的冲突机制组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001484","TSC_001485","TSC_001486"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00041","ADAPT_B_00042","ADAPT_B_00043"]}
【本步用法】把当前身份冲突与倒叙中已发生的身份事件对照，核查谁在何时目睹破绽，及认定、质疑或对抗能获得哪项前置依据。

231081｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YOUXI_1855","combination_kind":"INFORMATION_COMBINATION","combination_name":"游戏×知识垄断 信息搭配","description":"游戏叙事中知识垄断的信息披露节奏组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002674","TSC_002675","TSC_002676"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】沿已定积累顺序核查知识载体从被控制到可接触的各个阶段，定位各人实际掌握的信息量与可验证的披露时点。

231178｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YOUXI_1856","combination_kind":"RESOURCE_COMBINATION","combination_name":"游戏×情感纽带 资源搭配","description":"基于游戏的情感纽带资源转换搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002024","TSC_002025","TSC_002026"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】对照各线已有的互助和资源记录，核查承诺转成支持、交付或耗用的前提，并确认不同视角所见指向同一次流转。

231275｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YOUXI_1857","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"游戏×命运轨迹 关系搭配","description":"游戏中命运轨迹的人际关系组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000245","TSC_000246","TSC_000247"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】以已确定的命运转折回查倒叙中的协助、债务和物资积累，核对此前的关系凭何成立，以及它怎样影响当前人物的选择范围。

231372｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YOUXI_1858","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"游戏×禁忌领域 伏笔搭配","description":"游戏类型下禁忌领域的伏笔铺设搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002150","TSC_002151","TSC_002152"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00018","ADAPT_B_00019","ADAPT_B_00020"]}
【本步用法】从禁区已有规则和知情差中核查早期能看见的边界或物件状态，区分首次观察的含义与后来验证出的限制。

231469｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YOUXI_1859","combination_kind":"STYLE_COMBINATION","combination_name":"游戏×传承体系 风格搭配","description":"游戏×传承体系的叙述风格组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000977","TSC_000978","TSC_000979"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00028","ADAPT_B_00029","ADAPT_B_00030"]}
【本步用法】依据多线既定传承及各方所知，按作者确认的风格核查各线的称谓、详略和视角距离，并对照同一传承事实的不同可见切面。

231566｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YOUXI_1860","combination_kind":"PROJECT_COMBINATION","combination_name":"游戏×背叛成本 项目组合","description":"游戏写作中背叛成本的项目规划组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001614","TSC_001615","TSC_001616"],"dynamic_rule_ids":["TDR_003"],"adaptation_ids":["ADAPT_B_00002","ADAPT_B_00003","ADAPT_B_00004"]}
【本步用法】把已定背叛的实际代价、各方所知和倒叙位置分列，核查项目在哪一节点揭示真正的损失及早期依据。

231663｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YOUXI_1861","combination_kind":"STATIC_COMBINATION","combination_name":"游戏×觉醒机制 静态搭配","description":"游戏世界中觉醒机制的静态结构组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002178","TSC_002179","TSC_002180"],"dynamic_rule_ids":["TDR_003","TDR_004"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】以已确认的觉醒资格及其对象为据，核查长期有效的触发条件、能力门槛和持有物要求，标明前一事件完成后才具备的条件。

231762｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YOUXI_1862","combination_kind":"DYNAMIC_COMBINATION","combination_name":"游戏×世界观 动态搭配","description":"游戏动态规则触发下的世界观变化","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002495","TSC_002496","TSC_002497"],"dynamic_rule_ids":["TDR_003","TDR_005"],"adaptation_ids":["ADAPT_B_00012","ADAPT_B_00013","ADAPT_B_00014"]}
【本步用法】按照已有事件和信息传播核查实际变化的对象、范围和生效条件，区分世界状态发生变化与人物后来获知规则。

231861｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YOUXI_1863","combination_kind":"EXPRESSION_COMBINATION","combination_name":"游戏×力量体系 表达配合","description":"游戏类型力量体系的语气风格表达搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001564","TSC_001565","TSC_001566"],"dynamic_rule_ids":["TDR_003","TDR_006"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】对照已有力量阶段、资源转移与能力耗用，核查对话或叙述如何称述程度、限制及代价，并与作者确认的语气相合。

231960｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YOUXI_1864","combination_kind":"SCENE_COMBINATION","combination_name":"游戏×身份设定 场景搭配","description":"游戏×身份设定场景元素组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000198","TSC_000199","TSC_000200"],"dynamic_rule_ids":["TDR_003","TDR_007"],"adaptation_ids":["ADAPT_B_00042","ADAPT_B_00043","ADAPT_B_00044"]}
【本步用法】按既定成长节点与关系核查场景可让哪些人物见到身份凭证、认出什么事实，以及当时在场的其他人能知道多少。

232059｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YOUXI_1865","combination_kind":"CONFLICT_COMBINATION","combination_name":"游戏×社交网络 冲突搭配","description":"游戏叙事中社交网络的冲突层次组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001221","TSC_001222","TSC_001223"],"dynamic_rule_ids":["TDR_003","TDR_008"],"adaptation_ids":["ADAPT_B_00067","ADAPT_B_00103","ADAPT_B_00104"]}
【本步用法】从已有社交纽带和知情范围核对冲突双方的支持、义务与身份暴露条件，定位哪项事实成立后会使争端进入下一层。

232158｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YOUXI_1866","combination_kind":"INFORMATION_COMBINATION","combination_name":"游戏×资源流通 信息搭配","description":"基于游戏的资源流通信息博弈搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001634","TSC_001635","TSC_001636"],"dynamic_rule_ids":["TDR_003","TDR_009"],"adaptation_ids":["ADAPT_B_00009","ADAPT_B_00010","ADAPT_B_00011"]}
【本步用法】沿已定流通路径核查实际持有量与各方所知的差别，查资源风险的已知证据、尚未验证的判断及可澄清它们的交付节点。

232257｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YOUXI_1867","combination_kind":"RESOURCE_COMBINATION","combination_name":"游戏×信息控制 资源搭配","description":"游戏资源体系中信息控制的稀缺约束组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000363","TSC_000364","TSC_000365"],"dynamic_rule_ids":["TDR_003","TDR_010"],"adaptation_ids":["ADAPT_B_00115","ADAPT_B_00116","ADAPT_B_00117"]}
【本步用法】把既有信息载体、接触权限和争夺对象一并核查，定位稀缺来自取得、保存还是传播条件，并对照已发生冲突的压力。

232356｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YOUXI_1868","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"游戏×时间线 关系搭配","description":"游戏类型下时间线的社会纽带搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000950","TSC_000951","TSC_000952"],"dynamic_rule_ids":["TDR_003","TDR_011"],"adaptation_ids":["ADAPT_B_00104","ADAPT_B_00105","ADAPT_B_00106"]}
【本步用法】按既定时间线与成长节点核查在某时有效的承诺、同行或救助关系，并用可回溯的接触事件核对关系缓和或延续的条件。

232455｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YOUXI_1869","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"游戏×空间布局 伏笔搭配","description":"游戏×空间布局的伏笔回收组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002316","TSC_002317","TSC_002318"],"dynamic_rule_ids":["TDR_003","TDR_012"],"adaptation_ids":["ADAPT_B_00057","ADAPT_B_00058","ADAPT_B_00059"]}
【本步用法】从已定空间揭示回查较早可见的通道、位置标记与物件状态，核查后续改道或重访时能否凭同一证据确认布局。

232554｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YOUXI_1870","combination_kind":"STYLE_COMBINATION","combination_name":"游戏×因果链条 风格搭配","description":"游戏语境中因果链条的风格基调组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000694","TSC_000695","TSC_000696"],"dynamic_rule_ids":["TDR_003","TDR_013"],"adaptation_ids":["ADAPT_B_00044","ADAPT_B_00045","ADAPT_B_00046"]}
【本步用法】按已定原因、可能失败的行动和实际结果，核查叙述节奏及用词是否能让读者分辨尝试与兑现，并与作者确认的风格核对。

232653｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YOUXI_1871","combination_kind":"PROJECT_COMBINATION","combination_name":"游戏×道德困境 项目组合","description":"基于游戏的道德困境项目骨架搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001176","TSC_001177","TSC_001178"],"dynamic_rule_ids":["TDR_003","TDR_014"],"adaptation_ids":["ADAPT_B_00109","ADAPT_B_00110","ADAPT_B_00111"]}
【本步用法】以已明确的伦理边界、实际目标与成长顺序核查项目各阶段的选择，确定已出现的中断怎样改变尚可承担的后果。

232752｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YOUXI_1872","combination_kind":"STATIC_COMBINATION","combination_name":"游戏×生存压力 静态搭配","description":"游戏与稳定关系生存压力的静态搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002171","TSC_002172","TSC_002173"],"dynamic_rule_ids":["TDR_003","TDR_015"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】根据已定物资来源、维持生存的支出和补给依赖，核查持续存在的压力条件，并把已发生事件的延迟后果放到相应时点。

232851｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YOUXI_1873","combination_kind":"DYNAMIC_COMBINATION","combination_name":"游戏×权力博弈 动态搭配","description":"游戏类型权力博弈动态演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002956","TSC_002957","TSC_002958"],"dynamic_rule_ids":["TDR_003","TDR_016"],"adaptation_ids":["ADAPT_B_00108","ADAPT_B_00109","ADAPT_B_00110"]}
【本步用法】沿既有权力变化核对触发事件和前后权限，查控制对象、实际执行者及其依据，关联到已写伏笔时核对兑现事件。

232950｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YOUXI_1874","combination_kind":"EXPRESSION_COMBINATION","combination_name":"游戏×身份伪装 表达配合","description":"游戏×身份伪装的修辞表达组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000101","TSC_000102","TSC_000103"],"dynamic_rule_ids":["TDR_003","TDR_017"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】按既定伪装内容及观察距离核查称谓、描述和答复各能透露何种事实，在披露节点前后分别对照人物证据范围。

233049｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YOUXI_1875","combination_kind":"SCENE_COMBINATION","combination_name":"游戏×知识垄断 场景搭配","description":"游戏世界观中知识垄断的场景呈现组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003083","TSC_003084","TSC_003085"],"dynamic_rule_ids":["TDR_003","TDR_018"],"adaptation_ids":["ADAPT_B_00041","ADAPT_B_00042","ADAPT_B_00043"]}
【本步用法】对照既有知识垄断和访问安排，核查场景中可见的载体、准入动作和被拒后的反应，并确认各方当时具备的访问权。

233148｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YOUXI_1876","combination_kind":"CONFLICT_COMBINATION","combination_name":"游戏×情感纽带 冲突搭配","description":"基于游戏的情感纽带冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002162","TSC_002163","TSC_002164"],"dynamic_rule_ids":["TDR_003","TDR_019"],"adaptation_ids":["ADAPT_B_00107","ADAPT_B_00108","ADAPT_B_00109"]}
【本步用法】按既定情感关系与成长目标核对双方投入、消耗和实际受损的支持条件，定位由哪次相处或取舍推动对立。

233247｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YOUXI_1877","combination_kind":"INFORMATION_COMBINATION","combination_name":"游戏×命运轨迹 信息搭配","description":"游戏信息流中命运轨迹的信息差组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000438","TSC_000439","TSC_000440"],"dynamic_rule_ids":["TDR_003","TDR_020"],"adaptation_ids":["ADAPT_B_00009","ADAPT_B_00010","ADAPT_B_00011"]}
【本步用法】沿已定命运节点对照角色知道的承诺、消息和物件状态，核查转折前谁可能察觉、转折后哪些变化已得到证实。

233346｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YOUXI_1878","combination_kind":"RESOURCE_COMBINATION","combination_name":"游戏×禁忌领域 资源搭配","description":"游戏类型下禁忌领域的资源分配搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000408","TSC_000409","TSC_000410"],"dynamic_rule_ids":["TDR_003","TDR_021"],"adaptation_ids":["ADAPT_B_00031","ADAPT_B_00032","ADAPT_B_00033"]}
【本步用法】对照已设禁区边界和资源准入条件，核查何人能在何处取得、动用或带出资源，以及相关地点限制从何时生效。

233445｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YOUXI_1879","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"游戏×传承体系 关系搭配","description":"游戏×传承体系的关系网络组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002115","TSC_002116","TSC_002117"],"dynamic_rule_ids":["TDR_003","TDR_022"],"adaptation_ids":["ADAPT_B_00048","ADAPT_B_00049","ADAPT_B_00050"]}
【本步用法】按已有传承资格、承载物和披露计划核查授予、见证及支持关系，确定资格变化或信息公开会触及哪些已成立联系。

233544｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YOUXI_1880","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"游戏×背叛成本 伏笔搭配","description":"游戏叙事中背叛成本的伏笔密度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001252","TSC_001253","TSC_001254"],"dynamic_rule_ids":["TDR_003","TDR_023"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】依据已确认的背叛损失与后续验证，核对较早的物件状态、使用权限或伤势痕迹，按原定节奏检查各条线索出现密度。

233643｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_YOUXI_1881","combination_kind":"STYLE_COMBINATION","combination_name":"游戏×觉醒机制 风格搭配","description":"基于游戏的觉醒机制风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002589","TSC_002590","TSC_002591"],"dynamic_rule_ids":["TDR_003","TDR_024"],"adaptation_ids":["ADAPT_B_00041","ADAPT_B_00042","ADAPT_B_00043"]}
【本步用法】按作者已定风格和人物既有选择边界，核查觉醒前后征兆的称述与显隐程度，确认同一能力阶段的表达能互相对应。

233742｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_YOUXI_1882","combination_kind":"PROJECT_COMBINATION","combination_name":"游戏×世界观 项目组合","description":"游戏项目模板下世界观的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002630","TSC_002631","TSC_002632"],"dynamic_rule_ids":["TDR_003","TDR_025"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】将既定世界规则、成长阶段及资源周转放回项目各节点，核查社会条件如何影响人物的实际行动范围以及可回查的支持证据。

233841｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_YOUXI_1883","combination_kind":"STATIC_COMBINATION","combination_name":"游戏×力量体系 静态搭配","description":"游戏类型下的力量体系静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002676","TSC_002677","TSC_002678"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】核查已确定的力量阶段、稳定上限和人与资源的依赖，注明后续能力变化须依赖的已完成事件及可使用物件。

233938｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_YOUXI_1884","combination_kind":"DYNAMIC_COMBINATION","combination_name":"游戏×身份设定 动态搭配","description":"游戏中身份设定的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002735","TSC_002736","TSC_002737"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】对照各线已有身份事件，核对一个事件完成后可考虑的身份变化、已经成立的身份状态，以及各线何时能够观察到它。

234035｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_YOUXI_1885","combination_kind":"EXPRESSION_COMBINATION","combination_name":"游戏×社交网络 表达配合","description":"游戏语境下社交网络的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002766","TSC_002767","TSC_002768"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】根据已定社交关系与当前所知，核查倒叙中的称呼、交付和合作细节，确认这些表达支持的是哪一时点的关系及既有前置。

234132｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_YOUXI_1886","combination_kind":"SCENE_COMBINATION","combination_name":"游戏×资源流通 场景搭配","description":"基于游戏的资源流通场景调度搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001783","TSC_001784","TSC_001785"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00015","ADAPT_B_00016","ADAPT_B_00017"]}
【本步用法】沿已定积累次序核查现有场景的取得、携带、交付与库存显示，使同一资源在前后场的状态和数量能够对照。

234229｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_YOUXI_1887","combination_kind":"CONFLICT_COMBINATION","combination_name":"游戏×信息控制 冲突搭配","description":"游戏中信息控制引发的冲突维度组合","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000379","TSC_000380","TSC_000381"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00028","ADAPT_B_00029","ADAPT_B_00030"]}
【本步用法】逐线核查已定消息控制和资源积累，定位双方在何时掌握哪些材料、据此争夺什么，并回查使冲突启动的已完成事件。

234326｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_YOUXI_1888","combination_kind":"INFORMATION_COMBINATION","combination_name":"游戏×时间线 信息搭配","description":"游戏类型下时间线的信息控制搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000020","TSC_000021","TSC_000022"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00033","ADAPT_B_00034","ADAPT_B_00035"]}
【本步用法】把已定资源记录按真实时间与披露时点对照，核实倒叙能补足的是存量、交接还是耗用信息，以及人物当时对这些记录所知。

234423｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_YOUXI_1889","combination_kind":"RESOURCE_COMBINATION","combination_name":"游戏×空间布局 资源搭配","description":"游戏×空间布局的资源争夺组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002175","TSC_002176","TSC_002177"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00043","ADAPT_B_00044","ADAPT_B_00045"]}
【本步用法】以已定空间布局与知情差为据，核对争夺双方可到达的资源点、取用权限和各自可获的位置证据。

234520｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_YOUXI_1890","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"游戏×因果链条 关系搭配","description":"游戏叙事中因果链条的关系张力组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003051","TSC_003052","TSC_003053"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00064","ADAPT_B_00065","ADAPT_B_00066"]}
【本步用法】把各关系线已有的因与果及各方知道它们的时点分列，核实信赖、追索或指责能追溯至哪项行动，及证据怎样跨线到达。

234617｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_YOUXI_1891","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"游戏×道德困境 伏笔搭配","description":"基于游戏的道德困境伏笔标记搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000323","TSC_000324","TSC_000325"],"dynamic_rule_ids":["TDR_004"],"adaptation_ids":["ADAPT_B_00037","ADAPT_B_00038","ADAPT_B_00039"]}
【本步用法】从已定伦理取舍及其代价回查倒叙中的物资状态、当事人所知与前一事件结果，标出较早可埋设且后续能够验证的线索。"""
