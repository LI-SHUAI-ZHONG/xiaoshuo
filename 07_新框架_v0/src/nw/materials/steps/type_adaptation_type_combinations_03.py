"""类型适配步骤中的第 111–165 条组合原文及用法。"""

MATERIAL = """【《类型系统》类型组合总表｜类型适配｜第 111–165 条】
【原文位置】第 56 个来源块始于第 42,967 行。本批为正文表顺序第 111–165 条，前缀指组合 ID 字段的物理原件行。
【本步用法】按作者采用的类型、项目已有前置和当前设计需要核对机制、结构、组成及对应条件。本批 blocked 条目供查原值、用途和现行待核项。子类型、风格等空值沿用原文，项目采用的子类型与风格以作者确认的内容为据。
【各条共用原文值】{"primary_type_id":"GENRE_XIANXIA","type_ids":["GENRE_XIANXIA"],"subtype_ids":[],"hybrid_ids":[],"style_ids":[],"tone_ids":[],"audience_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"foreshadowing_type_ids":[],"selection_status":"candidate","source_refs":["type_combination_template"],"evidence_type":"inferred","status":"candidate","schema_version":"2.0"}
【逐条精简值】每条由共用值与本行有效组成字段合并而成，已剔除合成随机评分与跨类型污染外键。

54462｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XIANXIA_0112","combination_kind":"STATIC_COMBINATION","combination_name":"仙侠×生存压力 静态搭配","description":"仙侠与稳定关系生存压力的静态搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001698","TSC_001699","TSC_001700"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】以已有生存压力、可取得资源和相对稳定的关系为据，核对倒叙中哪些物件与供应条件能说明积累起点。

54559｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XIANXIA_0113","combination_kind":"DYNAMIC_COMBINATION","combination_name":"仙侠×权力博弈 动态搭配","description":"仙侠类型权力博弈动态演化搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002135","TSC_002136","TSC_002137"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00058","ADAPT_B_00059","ADAPT_B_00060"]}
【本步用法】在既定权力关系中查各方掌握的信息，以及信息改变后实际能触发的权力变化与后续行动。

54656｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XIANXIA_0114","combination_kind":"EXPRESSION_COMBINATION","combination_name":"仙侠×身份伪装 表达配合","description":"仙侠×身份伪装的修辞表达组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001103","TSC_001104","TSC_001105"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00066","ADAPT_B_00067","ADAPT_B_00103"]}
【本步用法】按已确认的真实身份、公开身份及各线的知情范围，核对措辞能呈现的伪装线索和披露边界。

54753｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XIANXIA_0115","combination_kind":"SCENE_COMBINATION","combination_name":"仙侠×知识垄断 场景搭配","description":"仙侠世界观中知识垄断的场景呈现组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002539","TSC_002540","TSC_002541"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00107","ADAPT_B_00108","ADAPT_B_00109"]}
【本步用法】对照知识持有者、受限者和当场目标，核对倒叙场景中可观察的知识壁垒及其原有依据。

54850｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XIANXIA_0116","combination_kind":"CONFLICT_COMBINATION","combination_name":"仙侠×情感纽带 冲突搭配","description":"基于仙侠的情感纽带冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002533","TSC_002534","TSC_002535"],"dynamic_rule_ids":["TDR_001","TDR_002"],"adaptation_ids":["ADAPT_B_00050","ADAPT_B_00051","ADAPT_B_00052"]}
【本步用法】沿前置已经建立的情感纽带查各方需求与临场选择，核对哪个关系矛盾会推动现有成长阶段。

54949｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XIANXIA_0117","combination_kind":"INFORMATION_COMBINATION","combination_name":"仙侠×命运轨迹 信息搭配","description":"仙侠信息流中命运轨迹的信息差组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002260","TSC_002261","TSC_002262"],"dynamic_rule_ids":["TDR_001","TDR_003"],"adaptation_ids":["ADAPT_B_00037","ADAPT_B_00038","ADAPT_B_00039"]}
【本步用法】把已确定的命运节点同人物所知及披露顺序对照，核对已有信息差在哪个成长节点起作用。

55048｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XIANXIA_0118","combination_kind":"RESOURCE_COMBINATION","combination_name":"仙侠×禁忌领域 资源搭配","description":"仙侠类型下禁忌领域的资源分配搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002994","TSC_002995","TSC_002996"],"dynamic_rule_ids":["TDR_001","TDR_004"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】以现有禁忌范围和资源需求为据，核对获取资格、支配范围以及会被禁忌限制的分配活动。

55147｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XIANXIA_0119","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"仙侠×传承体系 关系搭配","description":"仙侠×传承体系的关系网络组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000338","TSC_000339","TSC_000340"],"dynamic_rule_ids":["TDR_001","TDR_005"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】从既定传承资格和人物关系出发，核对已有的授受、继承与竞争关系如何支撑成长过程。

55246｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XIANXIA_0120","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"仙侠×背叛成本 伏笔搭配","description":"仙侠叙事中背叛成本的伏笔密度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002930","TSC_002931","TSC_002932"],"dynamic_rule_ids":["TDR_001","TDR_006"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】在已确定背叛及其代价后，核对可早先出现的代价线索、分布位置和后续可查的回收点。

55345｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XIANXIA_0121","combination_kind":"STYLE_COMBINATION","combination_name":"仙侠×觉醒机制 风格搭配","description":"基于仙侠的觉醒机制风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000732","TSC_000733","TSC_000734"],"dynamic_rule_ids":["TDR_001","TDR_007"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】以已知觉醒条件和可观察效果核对项目所选风格能否呈现其变化，具体写法使用作者确认的设定。

55444｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XIANXIA_0122","combination_kind":"PROJECT_COMBINATION","combination_name":"仙侠×世界观 项目组合","description":"仙侠项目模板下世界观的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002008","TSC_002009","TSC_002010"],"dynamic_rule_ids":["TDR_001","TDR_008"],"adaptation_ids":["ADAPT_B_00006","ADAPT_B_00007","ADAPT_B_00008"]}
【本步用法】将已经确认的世界规则、可用对象和成长阶段放在同一项目方案中核对，查各阶段依赖的世界条件。

55543｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XIANXIA_0123","combination_kind":"STATIC_COMBINATION","combination_name":"仙侠×力量体系 静态搭配","description":"仙侠类型下的力量体系静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000494","TSC_000495","TSC_000496"],"dynamic_rule_ids":["TDR_001","TDR_009"],"adaptation_ids":["ADAPT_B_00013","ADAPT_B_00014","ADAPT_B_00015"]}
【本步用法】以实际力量来源和稳定使用条件为据，核对持有对象与角色成长需要的支撑关系。

55642｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XIANXIA_0124","combination_kind":"DYNAMIC_COMBINATION","combination_name":"仙侠×身份设定 动态搭配","description":"仙侠中身份设定的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002024","TSC_002025","TSC_002026"],"dynamic_rule_ids":["TDR_001","TDR_010"],"adaptation_ids":["ADAPT_B_00112","ADAPT_B_00113","ADAPT_B_00114"]}
【本步用法】以已有身份和触发事件为起点，核对身份变化的成立条件、见证者和后继行动依据。

55741｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XIANXIA_0125","combination_kind":"EXPRESSION_COMBINATION","combination_name":"仙侠×社交网络 表达配合","description":"仙侠语境下社交网络的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_003111","TSC_003112","TSC_003113"],"dynamic_rule_ids":["TDR_001","TDR_011"],"adaptation_ids":["ADAPT_B_00059","ADAPT_B_00060","ADAPT_B_00061"]}
【本步用法】从已经建立的社交关系及角色地位出发，核对哪些关系可经具体叙述呈现，哪些仍需前置证据。

55840｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XIANXIA_0126","combination_kind":"SCENE_COMBINATION","combination_name":"仙侠×资源流通 场景搭配","description":"基于仙侠的资源流通场景调度搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002159","TSC_002160","TSC_002161"],"dynamic_rule_ids":["TDR_001","TDR_012"],"adaptation_ids":["ADAPT_B_00040","ADAPT_B_00041","ADAPT_B_00042"]}
【本步用法】按已确定的交易或转移需求核对场景中的对象、持有方、交付动作和交付后的资源位置。

55939｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XIANXIA_0127","combination_kind":"CONFLICT_COMBINATION","combination_name":"仙侠×信息控制 冲突搭配","description":"仙侠中信息控制引发的冲突维度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000776","TSC_000777","TSC_000778"],"dynamic_rule_ids":["TDR_001","TDR_013"],"adaptation_ids":["ADAPT_B_00035","ADAPT_B_00036","ADAPT_B_00037"]}
【本步用法】以项目已建立的信息控制关系为据，核对信息受限会引发哪一方的冲突选择以及现有的反应条件。

56038｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XIANXIA_0128","combination_kind":"INFORMATION_COMBINATION","combination_name":"仙侠×时间线 信息搭配","description":"仙侠类型下时间线的信息控制搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000851","TSC_000852","TSC_000853"],"dynamic_rule_ids":["TDR_001","TDR_014"],"adaptation_ids":["ADAPT_B_00019","ADAPT_B_00020","ADAPT_B_00021"]}
【本步用法】从已确定的事件时序出发，核对哪项时间信息由谁掌握、在哪个节点可以披露并影响后续成长。

56137｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XIANXIA_0129","combination_kind":"RESOURCE_COMBINATION","combination_name":"仙侠×空间布局 资源搭配","description":"仙侠×空间布局的资源争夺组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002948","TSC_002949","TSC_002950"],"dynamic_rule_ids":["TDR_001","TDR_015"],"adaptation_ids":["ADAPT_B_00113","ADAPT_B_00114","ADAPT_B_00115"]}
【本步用法】沿既有空间布局核对资源位置、占有方与可达条件，判断空间约束在实际争夺中的作用。

56236｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XIANXIA_0130","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"仙侠×因果链条 关系搭配","description":"仙侠叙事中因果链条的关系张力组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001431","TSC_001432","TSC_001433"],"dynamic_rule_ids":["TDR_001","TDR_016"],"adaptation_ids":["ADAPT_B_00014","ADAPT_B_00015","ADAPT_B_00016"]}
【本步用法】按已经成立的因果链核对人物关系受哪一件事影响，以及关系张力可从哪个行动或后果回查。

56335｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XIANXIA_0131","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"仙侠×道德困境 伏笔搭配","description":"基于仙侠的道德困境伏笔标记搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002522","TSC_002523","TSC_002524"],"dynamic_rule_ids":["TDR_001","TDR_017"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】以已确定的道德界线与后续困境为据，检查哪项早期选择可以成为后来两难的伏笔标记。

56434｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XIANXIA_0132","combination_kind":"STYLE_COMBINATION","combination_name":"仙侠×生存压力 风格搭配","description":"仙侠风格体系中生存压力的美学组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000888","TSC_000889","TSC_000890"],"dynamic_rule_ids":["TDR_001","TDR_018"],"adaptation_ids":["ADAPT_B_00107","ADAPT_B_00108","ADAPT_B_00109"]}
【本步用法】结合已建立的生存压力核对作者所选写法如何体现资源紧张与持续代价，并定位可观察的落点。

56533｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XIANXIA_0133","combination_kind":"PROJECT_COMBINATION","combination_name":"仙侠×权力博弈 项目组合","description":"仙侠类型权力博弈的项目结构搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001742","TSC_001743","TSC_001744"],"dynamic_rule_ids":["TDR_001","TDR_019"],"adaptation_ids":["ADAPT_B_00013","ADAPT_B_00014","ADAPT_B_00015"]}
【本步用法】对照已经存在的权力关系和线性进程，核对各阶段的立场、可行动条件和权力变化依据。

56632｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XIANXIA_0134","combination_kind":"STATIC_COMBINATION","combination_name":"仙侠×身份伪装 静态搭配","description":"基于仙侠的类型兼容身份伪装搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001027","TSC_001028","TSC_001029"],"dynamic_rule_ids":["TDR_001","TDR_020"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】据既有真实身份和对外伪装核对稳定关系、相关对象和可认出的身份条件。

56731｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XIANXIA_0135","combination_kind":"DYNAMIC_COMBINATION","combination_name":"仙侠×知识垄断 动态搭配","description":"仙侠×知识垄断的动态传播搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001179","TSC_001180","TSC_001181"],"dynamic_rule_ids":["TDR_001","TDR_021"],"adaptation_ids":["ADAPT_B_00048","ADAPT_B_00049","ADAPT_B_00050"]}
【本步用法】以现有的垄断关系和权利边界为据，核对接触到知识或传播受阻后会触发哪项实际变化。

56830｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XIANXIA_0136","combination_kind":"EXPRESSION_COMBINATION","combination_name":"仙侠×情感纽带 表达配合","description":"适配仙侠的情感纽带表达参数组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001310","TSC_001311","TSC_001312"],"dynamic_rule_ids":["TDR_001","TDR_022"],"adaptation_ids":["ADAPT_B_00010","ADAPT_B_00011","ADAPT_B_00012"]}
【本步用法】根据真实情感纽带和已经发生的选择核对叙述里的可见表现，查看关系变化是否有据可查。

56929｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XIANXIA_0137","combination_kind":"SCENE_COMBINATION","combination_name":"仙侠×命运轨迹 场景搭配","description":"仙侠中命运轨迹的场景构建组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002855","TSC_002856","TSC_002857"],"dynamic_rule_ids":["TDR_001","TDR_023"],"adaptation_ids":["ADAPT_B_00008","ADAPT_B_00009","ADAPT_B_00010"]}
【本步用法】按现有命运节点与场景功能核对当场人物、物件和动作能否支持该阶段实际发生的变化。

57028｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XIANXIA_0138","combination_kind":"CONFLICT_COMBINATION","combination_name":"仙侠×禁忌领域 冲突搭配","description":"仙侠类型禁忌领域的对立冲突搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000520","TSC_000521","TSC_000522"],"dynamic_rule_ids":["TDR_001","TDR_024"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】依据项目已划定的禁忌和人物目标，核对对立双方如何因具体边界、行动及后果形成冲突。

57127｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XIANXIA_0139","combination_kind":"INFORMATION_COMBINATION","combination_name":"仙侠×传承体系 信息搭配","description":"仙侠×传承体系的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000902","TSC_000903","TSC_000904"],"dynamic_rule_ids":["TDR_001","TDR_025"],"adaptation_ids":["ADAPT_B_00044","ADAPT_B_00045","ADAPT_B_00046"]}
【本步用法】沿已有传承条件查知情者、接收传承者和其他相关人物的知情范围，核对信息差如何影响实际继承进程。

57226｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XIANXIA_0140","combination_kind":"RESOURCE_COMBINATION","combination_name":"仙侠×背叛成本 资源搭配","description":"仙侠世界中背叛成本的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000904","TSC_000905","TSC_000906"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00007","ADAPT_B_00008","ADAPT_B_00009"]}
【本步用法】从已确认的背叛后果回查旧的资源获取路径，核对哪些关系仍可调动资源及其实际代价。

57323｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XIANXIA_0141","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"仙侠×觉醒机制 关系搭配","description":"基于仙侠的觉醒机制关系演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000769","TSC_000770","TSC_000771"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00041","ADAPT_B_00042","ADAPT_B_00043"]}
【本步用法】从既定觉醒机制与多线关系出发，核对哪项变化会传到哪条线，关系改变如何从前置回查。

57420｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XIANXIA_0142","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"仙侠×世界观 伏笔搭配","description":"仙侠伏笔线索中世界观的预置组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000612","TSC_000613","TSC_000614"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00053","ADAPT_B_00057","ADAPT_B_00058"]}
【本步用法】根据已定世界规则和倒叙安排核对较早能埋下的设定线索，以及后文显出该规则所需的条件。

57517｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XIANXIA_0143","combination_kind":"STYLE_COMBINATION","combination_name":"仙侠×力量体系 风格搭配","description":"仙侠类型下力量体系的风格变奏搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000126","TSC_000127","TSC_000128"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】把已有力量体系的资源积累阶段与项目所选笔法对照，检查各阶段的差别能否通过现有细节表现。

57614｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XIANXIA_0144","combination_kind":"PROJECT_COMBINATION","combination_name":"仙侠×身份设定 项目组合","description":"仙侠×身份设定的项目配置组合方案","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001385","TSC_001386","TSC_001387"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00062","ADAPT_B_00063","ADAPT_B_00064"]}
【本步用法】沿项目已经确定的多线身份与资源积累需求，核对各线可动用的资源与身份变化约束。

57711｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XIANXIA_0145","combination_kind":"STATIC_COMBINATION","combination_name":"仙侠×社交网络 静态搭配","description":"仙侠×社交网络的静态连接搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000307","TSC_000308","TSC_000309"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】从已经建立的社交网络查稳定连接，核对倒叙交代的关系起点及该关系能否影响资源积累。

57808｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XIANXIA_0146","combination_kind":"DYNAMIC_COMBINATION","combination_name":"仙侠×资源流通 动态搭配","description":"仙侠中基于资源流通的动态行为组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002227","TSC_002228","TSC_002229"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】以项目已有资源流向和各方所知为据，查信息差如何改变已有交易机会、行动和后果。

57905｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XIANXIA_0147","combination_kind":"EXPRESSION_COMBINATION","combination_name":"仙侠×信息控制 表达配合","description":"仙侠中信息控制的语言表达适配组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_003125","TSC_003126","TSC_003127"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】按多线各方真实知情范围核对措辞能透露的内容、被保留的信息及其后续检验点。

58002｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XIANXIA_0148","combination_kind":"SCENE_COMBINATION","combination_name":"仙侠×时间线 场景搭配","description":"仙侠类型下时间线的场景布局搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002970","TSC_002971","TSC_002972"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00032","ADAPT_B_00033","ADAPT_B_00034"]}
【本步用法】用已确立的时间锚和信息披露顺序核对倒叙场景的位置，确认人物和读者当场能辨认的时间信息。

58099｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XIANXIA_0149","combination_kind":"CONFLICT_COMBINATION","combination_name":"仙侠×空间布局 冲突搭配","description":"仙侠×空间布局的冲突机制组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000151","TSC_000152","TSC_000153"],"dynamic_rule_ids":["TDR_002","TDR_003"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】按既有地点、可达路径和冲突目的，核对空间限制如何成为人物当场选择及冲突升级的条件。

58198｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XIANXIA_0150","combination_kind":"INFORMATION_COMBINATION","combination_name":"仙侠×因果链条 信息搭配","description":"仙侠叙事中因果链条的信息披露节奏组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002741","TSC_002742","TSC_002743"],"dynamic_rule_ids":["TDR_002","TDR_004"],"adaptation_ids":["ADAPT_B_00011","ADAPT_B_00012","ADAPT_B_00013"]}
【本步用法】对照已确定的原因、结果和各方知情时间，核对哪些因果信息可以按线性进程先后披露。

58297｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XIANXIA_0151","combination_kind":"RESOURCE_COMBINATION","combination_name":"仙侠×道德困境 资源搭配","description":"基于仙侠的道德困境资源转换搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002696","TSC_002697","TSC_002698"],"dynamic_rule_ids":["TDR_002","TDR_005"],"adaptation_ids":["ADAPT_B_00060","ADAPT_B_00061","ADAPT_B_00062"]}
【本步用法】按已确认的道德边界和已有资源核对一次转换或交换的可行条件，以及参与者承担的代价。

58396｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XIANXIA_0152","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"仙侠×生存压力 关系搭配","description":"仙侠中生存压力的人际关系组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000626","TSC_000627","TSC_000628"],"dynamic_rule_ids":["TDR_002","TDR_006"],"adaptation_ids":["ADAPT_B_00002","ADAPT_B_00003","ADAPT_B_00004"]}
【本步用法】从实际生存压力与人物依赖关系出发，查哪些关系因共同需求发生变化以及对应的行为依据。

58495｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XIANXIA_0153","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"仙侠×权力博弈 伏笔搭配","description":"仙侠类型下权力博弈的伏笔铺设搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002871","TSC_002872","TSC_002873"],"dynamic_rule_ids":["TDR_002","TDR_007"],"adaptation_ids":["ADAPT_B_00066","ADAPT_B_00067","ADAPT_B_00103"]}
【本步用法】以实际权力关系及延后的揭示节点为据，核对可提前出现的地位、权限或行为线索。

58594｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XIANXIA_0154","combination_kind":"STYLE_COMBINATION","combination_name":"仙侠×身份伪装 风格搭配","description":"仙侠×身份伪装的叙述风格组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002826","TSC_002827","TSC_002828"],"dynamic_rule_ids":["TDR_002","TDR_008"],"adaptation_ids":["ADAPT_B_00044","ADAPT_B_00045","ADAPT_B_00046"]}
【本步用法】依据既定伪装与知情边界，核对作者所选叙述风格能显出的伪装痕迹及其可见范围。

58693｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XIANXIA_0155","combination_kind":"PROJECT_COMBINATION","combination_name":"仙侠×知识垄断 项目组合","description":"仙侠写作中知识垄断的项目规划组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001619","TSC_001620","TSC_001621"],"dynamic_rule_ids":["TDR_002","TDR_009"],"adaptation_ids":["ADAPT_B_00062","ADAPT_B_00063","ADAPT_B_00064"]}
【本步用法】从已确认的知识掌控与成长目标出发，核对项目各阶段需要获取的信息、渠道和受限原因。

58792｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_XIANXIA_0156","combination_kind":"STATIC_COMBINATION","combination_name":"仙侠×情感纽带 静态搭配","description":"仙侠世界中情感纽带的静态结构组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002580","TSC_002581","TSC_002582"],"dynamic_rule_ids":["TDR_002","TDR_010"],"adaptation_ids":["ADAPT_B_00109","ADAPT_B_00110","ADAPT_B_00111"]}
【本步用法】对照已建立的情感纽带和更改前的状态，核对成长阶段依赖的稳定关系与可查的表现。

58891｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_XIANXIA_0157","combination_kind":"DYNAMIC_COMBINATION","combination_name":"仙侠×命运轨迹 动态搭配","description":"仙侠动态规则触发下的命运轨迹变化","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002444","TSC_002445","TSC_002446"],"dynamic_rule_ids":["TDR_002","TDR_011"],"adaptation_ids":["ADAPT_B_00116","ADAPT_B_00117","ADAPT_B_00118"]}
【本步用法】在已有命运节点及动态触发下，核对行动如何造成后续变化、影响哪项前置状态。

58990｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_XIANXIA_0158","combination_kind":"EXPRESSION_COMBINATION","combination_name":"仙侠×禁忌领域 表达配合","description":"仙侠类型禁忌领域的语气风格表达搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000175","TSC_000176","TSC_000177"],"dynamic_rule_ids":["TDR_002","TDR_012"],"adaptation_ids":["ADAPT_B_00109","ADAPT_B_00110","ADAPT_B_00111"]}
【本步用法】以实际禁忌边界和人物所知为据，核对项目设定的语气如何在可透露范围内表现禁忌。

59089｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_XIANXIA_0159","combination_kind":"SCENE_COMBINATION","combination_name":"仙侠×传承体系 场景搭配","description":"仙侠×传承体系场景元素组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001939","TSC_001940","TSC_001941"],"dynamic_rule_ids":["TDR_002","TDR_013"],"adaptation_ids":["ADAPT_B_00105","ADAPT_B_00106","ADAPT_B_00107"]}
【本步用法】从已确定的传承事件和场景目的出发，核对在场人物、传承载体与交接条件是否有前置依据。

59188｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_XIANXIA_0160","combination_kind":"CONFLICT_COMBINATION","combination_name":"仙侠×背叛成本 冲突搭配","description":"仙侠叙事中背叛成本的冲突层次组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001812","TSC_001813","TSC_001814"],"dynamic_rule_ids":["TDR_002","TDR_014"],"adaptation_ids":["ADAPT_B_00108","ADAPT_B_00109","ADAPT_B_00110"]}
【本步用法】沿实际背叛、受影响者和已知代价核对冲突层次，查各层的行动对象及逐步产生的后果。

59287｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_XIANXIA_0161","combination_kind":"INFORMATION_COMBINATION","combination_name":"仙侠×觉醒机制 信息搭配","description":"基于仙侠的觉醒机制信息博弈搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000274","TSC_000275","TSC_000276"],"dynamic_rule_ids":["TDR_002","TDR_015"],"adaptation_ids":["ADAPT_B_00014","ADAPT_B_00015","ADAPT_B_00016"]}
【本步用法】把真实觉醒条件、见证者和保密需求对照，核对各方得知信息的先后及对现有行动的影响。

59386｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_XIANXIA_0162","combination_kind":"RESOURCE_COMBINATION","combination_name":"仙侠×世界观 资源搭配","description":"仙侠资源体系中世界观的稀缺约束组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000938","TSC_000939","TSC_000940"],"dynamic_rule_ids":["TDR_002","TDR_016"],"adaptation_ids":["ADAPT_B_00057","ADAPT_B_00058","ADAPT_B_00059"]}
【本步用法】依据世界观已确认的资源边界和稀缺条件，核对成长阶段所需资源、可获得范围及受限原因。

59485｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_XIANXIA_0163","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"仙侠×力量体系 关系搭配","description":"仙侠类型下力量体系的社会纽带搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000768","TSC_000769","TSC_000770"],"dynamic_rule_ids":["TDR_002","TDR_017"],"adaptation_ids":["ADAPT_B_00104","ADAPT_B_00105","ADAPT_B_00106"]}
【本步用法】按既有力量分布、参与人物和社会纽带，核对可追溯的关系条件以及力量变化会触及的关系。

59584｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_XIANXIA_0164","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"仙侠×身份设定 伏笔搭配","description":"仙侠×身份设定的伏笔回收组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001320","TSC_001321","TSC_001322"],"dynamic_rule_ids":["TDR_002","TDR_018"],"adaptation_ids":["ADAPT_B_00110","ADAPT_B_00111","ADAPT_B_00112"]}
【本步用法】对照早先已经留下的身份线索与后续揭示条件，核对同一线索能否从前文回查并在此回收。

59683｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_XIANXIA_0165","combination_kind":"STYLE_COMBINATION","combination_name":"仙侠×社交网络 风格搭配","description":"仙侠语境中社交网络的风格基调组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001581","TSC_001582","TSC_001583"],"dynamic_rule_ids":["TDR_002","TDR_019"],"adaptation_ids":["ADAPT_B_00111","ADAPT_B_00112","ADAPT_B_00113"]}
【本步用法】以实际社交关系和互动差异核对作者所选基调能否显出网络层次，定位可落实的叙述表现。

59782｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_XIANXIA_0166","combination_kind":"PROJECT_COMBINATION","combination_name":"仙侠×资源流通 项目组合","description":"基于仙侠的资源流通项目骨架搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_002144","TSC_002145","TSC_002146"],"dynamic_rule_ids":["TDR_002","TDR_020"],"adaptation_ids":["ADAPT_B_00012","ADAPT_B_00013","ADAPT_B_00014"]}
【本步用法】沿既定的资源流向与阶段目标核对项目骨架中的供给、归属、交易节点及其对成长的支撑。"""
