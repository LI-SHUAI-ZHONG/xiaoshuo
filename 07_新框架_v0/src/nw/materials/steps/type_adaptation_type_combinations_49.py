"""类型适配步骤中的第 2631–2680 条组合原文及用法。"""

MATERIAL = """【《类型系统》类型组合总表｜类型适配｜第 2631–2680 条】
【原文位置】第 56 个来源块始于第 42,967 行。本段为正文表顺序第 2631–2680 条，前缀指组合 ID 字段的物理原件行。
【本步用法】按作者采用的类型、项目已有前置与当前设计需求核对各条组合的作用及成立条件。现行裁定为 blocked 的组合供查原值、用途和待核项。子类型、风格的空值按原文保留，项目具体采用以作者已确认的设定为据。
【各条共用原文值】{"primary_type_id":"GENRE_JUNSHI","type_ids":["GENRE_JUNSHI"],"subtype_ids":[],"hybrid_ids":[],"style_ids":[],"tone_ids":[],"audience_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"foreshadowing_type_ids":[],"selection_status":"candidate","source_refs":["type_combination_template"],"evidence_type":"inferred","status":"candidate","schema_version":"2.0"}
【逐条精简值】每条由共用值与本行有效组成字段合并而成，已剔除合成随机评分与跨类型污染外键。

310188｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_JUNSHI_2632","combination_kind":"DYNAMIC_COMBINATION","combination_name":"军事×生存压力 动态搭配","description":"军事动态规则触发下的生存压力变化","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002935","TSC_002936","TSC_002937"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】把资源积累、消耗和生存压力的变化对回真实时序，核查倒叙中可见的补给或体力状态怎样解释当下处境。

310285｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_JUNSHI_2633","combination_kind":"EXPRESSION_COMBINATION","combination_name":"军事×权力博弈 表达配合","description":"军事类型权力博弈的语气风格表达搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001969","TSC_001970","TSC_001971"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00032","ADAPT_B_00033","ADAPT_B_00034"]}
【本步用法】按既定权属与知情差核查命令、请示和拒绝的措辞，确认人物口气能对应自身实际知道的权限及处境。

310382｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_JUNSHI_2634","combination_kind":"SCENE_COMBINATION","combination_name":"军事×身份伪装 场景搭配","description":"军事×身份伪装场景元素组合方案","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000299","TSC_000300","TSC_000301"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00039","ADAPT_B_00040","ADAPT_B_00041"]}
【本步用法】按各线既定身份、知情差及在场人物核查场景可见的凭证、物件和反应，标明各视角何时足以认出同一身份。

310479｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_JUNSHI_2635","combination_kind":"CONFLICT_COMBINATION","combination_name":"军事×知识垄断 冲突搭配","description":"军事叙事中知识垄断的冲突层次组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001752","TSC_001753","TSC_001754"],"dynamic_rule_ids":["TDR_001"],"adaptation_ids":["ADAPT_B_00036","ADAPT_B_00037","ADAPT_B_00038"]}
【本步用法】从当下的知识争执回查倒叙可证的控制者、访问条件和知情差，确认哪次受阻或实际变化解释了后续对立。

310576｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_JUNSHI_2636","combination_kind":"INFORMATION_COMBINATION","combination_name":"军事×情感纽带 信息搭配","description":"基于军事的情感纽带信息博弈搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_003084","TSC_003085","TSC_003086"],"dynamic_rule_ids":["TDR_001","TDR_002"],"adaptation_ids":["ADAPT_B_00016","ADAPT_B_00017","ADAPT_B_00018"]}
【本步用法】依已设情感联系和成长次序核查谁知晓他人的负担、谁暂留消息，定位什么已见事实会改变对方对关系的判断。

310675｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_JUNSHI_2637","combination_kind":"RESOURCE_COMBINATION","combination_name":"军事×命运轨迹 资源搭配","description":"军事资源体系中命运轨迹的稀缺约束组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002224","TSC_002225","TSC_002226"],"dynamic_rule_ids":["TDR_001","TDR_003"],"adaptation_ids":["ADAPT_B_00104","ADAPT_B_00105","ADAPT_B_00106"]}
【本步用法】沿既定命运节点核查补给与体力构成的限制、物件实际可用度以及真实耗费，确认后续转折由哪项已有条件支持。

310774｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_JUNSHI_2638","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"军事×禁忌领域 关系搭配","description":"军事类型下禁忌领域的社会纽带搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001498","TSC_001499","TSC_001500"],"dynamic_rule_ids":["TDR_001","TDR_004"],"adaptation_ids":["ADAPT_B_00003","ADAPT_B_00004","ADAPT_B_00005"]}
【本步用法】依据既有禁区规则和已完成事件核查谁具备引介、接触或限制资格，定位已确认的身体和关系变化影响哪个交往条件。

310873｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_JUNSHI_2639","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"军事×传承体系 伏笔搭配","description":"军事×传承体系的伏笔回收组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_003047","TSC_003048","TSC_003049"],"dynamic_rule_ids":["TDR_001","TDR_005"],"adaptation_ids":["ADAPT_B_00044","ADAPT_B_00045","ADAPT_B_00046"]}
【本步用法】从已设传承验证回查早期的承载物、授予话语及消息传递，核实谁曾见到同一凭证、后来如何辨认和证实。

310972｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_JUNSHI_2640","combination_kind":"STYLE_COMBINATION","combination_name":"军事×背叛成本 风格搭配","description":"军事语境中背叛成本的风格基调组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000638","TSC_000639","TSC_000640"],"dynamic_rule_ids":["TDR_001","TDR_006"],"adaptation_ids":["ADAPT_B_00104","ADAPT_B_00105","ADAPT_B_00106"]}
【本步用法】依已定背叛事实、转移与损失按作者风格核查用词和叙述距离，确认物件或关系呈现的代价源于实际变化。

311071｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_JUNSHI_2641","combination_kind":"PROJECT_COMBINATION","combination_name":"军事×觉醒机制 项目组合","description":"基于军事的觉醒机制项目骨架搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000855","TSC_000856","TSC_000857"],"dynamic_rule_ids":["TDR_001","TDR_007"],"adaptation_ids":["ADAPT_B_00113","ADAPT_B_00114","ADAPT_B_00115"]}
【本步用法】把已定觉醒前提、成长阶段及所需关系支持放回项目骨架，核查可见状态与相关人物互动何时能证明变化。

311170｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_JUNSHI_2642","combination_kind":"STATIC_COMBINATION","combination_name":"军事×世界观 静态搭配","description":"军事与稳定关系世界观的静态搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001808","TSC_001809","TSC_001810"],"dynamic_rule_ids":["TDR_001","TDR_008"],"adaptation_ids":["ADAPT_B_00027","ADAPT_B_00028","ADAPT_B_00029"]}
【本步用法】沿既有世界规则核查持续有效的权属、准入和补给约束，确认涉及身份变化时哪些稳定条件仍可用。

311269｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_JUNSHI_2643","combination_kind":"DYNAMIC_COMBINATION","combination_name":"军事×力量体系 动态搭配","description":"军事类型力量体系动态演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000283","TSC_000284","TSC_000285"],"dynamic_rule_ids":["TDR_001","TDR_009"],"adaptation_ids":["ADAPT_B_00049","ADAPT_B_00050","ADAPT_B_00051"]}
【本步用法】从已定力量阶段与风险核查能力实际使用之前及之后的体力、物资和呈现，明确变化及影响行动的证据。

311368｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_JUNSHI_2644","combination_kind":"EXPRESSION_COMBINATION","combination_name":"军事×身份设定 表达配合","description":"军事×身份设定的修辞表达组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_000321","TSC_000322","TSC_000323"],"dynamic_rule_ids":["TDR_001","TDR_010"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】依既有身份和冲突核查人物用什么称呼、物件指代或自述相互辨认，确认措辞透露的内容符合当时权限。

311467｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_JUNSHI_2645","combination_kind":"SCENE_COMBINATION","combination_name":"军事×社交网络 场景搭配","description":"军事世界观中社交网络的场景呈现组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_003004","TSC_003005","TSC_003006"],"dynamic_rule_ids":["TDR_001","TDR_011"],"adaptation_ids":["ADAPT_B_00053","ADAPT_B_00057","ADAPT_B_00058"]}
【本步用法】根据既定社交网络和实际相处核查场景可展示的求助、退让或交付，确认其中哪项行动能体现关系缓和。

311566｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_JUNSHI_2646","combination_kind":"CONFLICT_COMBINATION","combination_name":"军事×资源流通 冲突搭配","description":"基于军事的资源流通冲突驱动搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002472","TSC_002473","TSC_002474"],"dynamic_rule_ids":["TDR_001","TDR_012"],"adaptation_ids":["ADAPT_B_00015","ADAPT_B_00016","ADAPT_B_00017"]}
【本步用法】依实际资源争执和流向核查各方可动用的条件、耗损和替代来源，定位已发生变化如何促成现有分歧。

311665｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_JUNSHI_2647","combination_kind":"INFORMATION_COMBINATION","combination_name":"军事×信息控制 信息搭配","description":"军事信息流中信息控制的信息差组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002127","TSC_002128","TSC_002129"],"dynamic_rule_ids":["TDR_001","TDR_013"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】据已有信息持有、接触和保密边界核查何人获准得知何事，确认传递受阻或失败在哪次事件中有所体现。

311764｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_JUNSHI_2648","combination_kind":"RESOURCE_COMBINATION","combination_name":"军事×时间线 资源搭配","description":"军事类型下时间线的资源分配搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001323","TSC_001324","TSC_001325"],"dynamic_rule_ids":["TDR_001","TDR_014"],"adaptation_ids":["ADAPT_B_00113","ADAPT_B_00114","ADAPT_B_00115"]}
【本步用法】把资源取得、耗用、中断和可调用时点放回实际次序，核查人物与物件在各成长节点怎样衔接。

311863｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_JUNSHI_2649","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"军事×空间布局 关系搭配","description":"军事×空间布局的关系网络组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002694","TSC_002695","TSC_002696"],"dynamic_rule_ids":["TDR_001","TDR_015"],"adaptation_ids":["ADAPT_B_00029","ADAPT_B_00030","ADAPT_B_00031"]}
【本步用法】依据既有活动范围和关系联系核查谁能在何处会面、互助或交付，定位迟来显现的空间或状态后果是否影响关系。

311962｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_JUNSHI_2650","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"军事×因果链条 伏笔搭配","description":"军事叙事中因果链条的伏笔密度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002433","TSC_002434","TSC_002435"],"dynamic_rule_ids":["TDR_001","TDR_016"],"adaptation_ids":["ADAPT_B_00015","ADAPT_B_00016","ADAPT_B_00017"]}
【本步用法】沿已定原因与结果回查早期能看到的消耗、移动和道具状态，核对伏笔分布和后文验证能否指回同一事件。

312061｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_JUNSHI_2651","combination_kind":"STYLE_COMBINATION","combination_name":"军事×道德困境 风格搭配","description":"基于军事的道德困境风格协调搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001166","TSC_001167","TSC_001168"],"dynamic_rule_ids":["TDR_001","TDR_017"],"adaptation_ids":["ADAPT_B_00022","ADAPT_B_00023","ADAPT_B_00024"]}
【本步用法】依已明确的伦理选择和作者风格核查压力、物件和人物反应的叙述详略，确保进度变化有现存选择与代价作依据。

312160｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_JUNSHI_2652","combination_kind":"PROJECT_COMBINATION","combination_name":"军事×生存压力 项目组合","description":"军事项目模板下生存压力的整体组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002636","TSC_002637","TSC_002638"],"dynamic_rule_ids":["TDR_001","TDR_018"],"adaptation_ids":["ADAPT_B_00065","ADAPT_B_00066","ADAPT_B_00067"]}
【本步用法】把已有生存需求、补给和成长节点纳入项目，核查短缺先如何被察觉、哪些实体条件已改变并引起真实反应。

312259｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_JUNSHI_2653","combination_kind":"STATIC_COMBINATION","combination_name":"军事×权力博弈 静态搭配","description":"军事类型下的权力博弈静态组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001273","TSC_001274","TSC_001275"],"dynamic_rule_ids":["TDR_001","TDR_019"],"adaptation_ids":["ADAPT_B_00025","ADAPT_B_00026","ADAPT_B_00027"]}
【本步用法】以既定权力和长期职责核查分配、领取和物品使用条件，确认各角色既有控制权怎样通过实际交付维持。

312358｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_JUNSHI_2654","combination_kind":"DYNAMIC_COMBINATION","combination_name":"军事×身份伪装 动态搭配","description":"军事中身份伪装的事件驱动动态组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002119","TSC_002120","TSC_002121"],"dynamic_rule_ids":["TDR_001","TDR_020"],"adaptation_ids":["ADAPT_B_00103","ADAPT_B_00104","ADAPT_B_00105"]}
【本步用法】沿已有伪装事件核查可见凭证、人物反应与身份认定怎样改变，物件已损坏时辨认线索应以实际状态为据。

312457｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_JUNSHI_2655","combination_kind":"EXPRESSION_COMBINATION","combination_name":"军事×知识垄断 表达配合","description":"军事语境下知识垄断的叙述表达组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002378","TSC_002379","TSC_002380"],"dynamic_rule_ids":["TDR_001","TDR_021"],"adaptation_ids":["ADAPT_B_00025","ADAPT_B_00026","ADAPT_B_00027"]}
【本步用法】按知识保管、位置限制与当事人所知核查叙述怎样表现限制，确认可用的称谓、动作或细节有观察依据。

312556｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_JUNSHI_2656","combination_kind":"SCENE_COMBINATION","combination_name":"军事×情感纽带 场景搭配","description":"基于军事的情感纽带场景调度搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_001656","TSC_001657","TSC_001658"],"dynamic_rule_ids":["TDR_001","TDR_022"],"adaptation_ids":["ADAPT_B_00044","ADAPT_B_00045","ADAPT_B_00046"]}
【本步用法】依既有情感关系和成长目标核查场景能显露的照顾、退让或承诺，标明人物最早何时察觉感情的变化。

312655｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_JUNSHI_2657","combination_kind":"CONFLICT_COMBINATION","combination_name":"军事×命运轨迹 冲突搭配","description":"军事中命运轨迹引发的冲突维度组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001162","TSC_001163","TSC_001164"],"dynamic_rule_ids":["TDR_001","TDR_023"],"adaptation_ids":["ADAPT_B_00005","ADAPT_B_00006","ADAPT_B_00007"]}
【本步用法】沿既定命运转折与已确认的伤势等后果核查冲突双方怎样遭遇阻力，定位可证的实际状态及认识差。

312754｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_JUNSHI_2658","combination_kind":"INFORMATION_COMBINATION","combination_name":"军事×禁忌领域 信息搭配","description":"军事类型下禁忌领域的信息控制搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000450","TSC_000451","TSC_000452"],"dynamic_rule_ids":["TDR_001","TDR_024"],"adaptation_ids":["ADAPT_B_00063","ADAPT_B_00064","ADAPT_B_00065"]}
【本步用法】根据已设禁区、人物伦理边界及其所知核查谁掌握限制、从何处知道，以及在何处可以证实。

312853｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_JUNSHI_2659","combination_kind":"RESOURCE_COMBINATION","combination_name":"军事×传承体系 资源搭配","description":"军事×传承体系的资源争夺组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_003102","TSC_003103","TSC_003104"],"dynamic_rule_ids":["TDR_001","TDR_025"],"adaptation_ids":["ADAPT_B_00008","ADAPT_B_00009","ADAPT_B_00010"]}
【本步用法】依已设传承资格和已有社会压力核查承载物被谁实际持有、如何交接与何时可用，确认争夺具有既有证据。

312952｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_JUNSHI_2660","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"军事×背叛成本 关系搭配","description":"军事叙事中背叛成本的关系张力组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000257","TSC_000258","TSC_000259"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00023","ADAPT_B_00024","ADAPT_B_00025"]}
【本步用法】从实际背叛代价与人物关系核查被削弱的支持、承诺或依赖，按已激活的概念定位最需核对的关系落点。

313049｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_JUNSHI_2661","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"军事×觉醒机制 伏笔搭配","description":"基于军事的觉醒机制伏笔标记搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001098","TSC_001099","TSC_001100"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00006","ADAPT_B_00007","ADAPT_B_00008"]}
【本步用法】由各线既定觉醒验证回查先前的身体迹象、人物反应或物资痕迹，核查跨线前置出现的时点及后文回收。

313146｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_JUNSHI_2662","combination_kind":"STYLE_COMBINATION","combination_name":"军事×世界观 风格搭配","description":"军事风格体系中世界观的美学组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000974","TSC_000975","TSC_000976"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00025","ADAPT_B_00026","ADAPT_B_00027"]}
【本步用法】按作者风格和已设世界规则核查倒叙、当下所呈现的物件和行动，确认两时段怎样支持同一条规则及其已见影响。

313243｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_JUNSHI_2663","combination_kind":"PROJECT_COMBINATION","combination_name":"军事×力量体系 项目组合","description":"军事类型力量体系的项目结构搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000368","TSC_000369","TSC_000370"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00004","ADAPT_B_00005","ADAPT_B_00006"]}
【本步用法】按线性积累把已定力量条件、所需持有物与阶段结果放回项目骨架，核对是否存在支持各阶段使用的实际证据。

313340｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_JUNSHI_2664","combination_kind":"STATIC_COMBINATION","combination_name":"军事×身份设定 静态搭配","description":"基于军事的类型兼容身份设定搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002836","TSC_002837","TSC_002838"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00015","ADAPT_B_00016","ADAPT_B_00017"]}
【本步用法】逐线查既有身份、持有与积累记录，定位长期成立的凭证或资格以及各场叙述可以依赖的事实。

313437｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_JUNSHI_2665","combination_kind":"DYNAMIC_COMBINATION","combination_name":"军事×社交网络 动态搭配","description":"军事×社交网络的动态传播搭配","mechanism_ids":["MECHANISM_RESOURCE_ACCUMULATION"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002730","TSC_002731","TSC_002732"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00026","ADAPT_B_00027","ADAPT_B_00028"]}
【本步用法】用倒叙中的已有关照、交付和转告回查当前社交网络怎样形成，核验关系和消息的变化先后及其累积依据。

313534｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_JUNSHI_2666","combination_kind":"EXPRESSION_COMBINATION","combination_name":"军事×资源流通 表达配合","description":"适配军事的资源流通表达参数组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000078","TSC_000079","TSC_000080"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00103","ADAPT_B_00104","ADAPT_B_00105"]}
【本步用法】沿已有流向和知情差核查资源转手的称呼、数量与公开程度，以物件和持有证据约束各角色的表达。

313631｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_JUNSHI_2667","combination_kind":"SCENE_COMBINATION","combination_name":"军事×信息控制 场景搭配","description":"军事中信息控制的场景构建组合","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_MULTILINE"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000166","TSC_000167","TSC_000168"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00113","ADAPT_B_00114","ADAPT_B_00115"]}
【本步用法】依多线已定观察范围和信息边界核查场景可呈现的接触、阻隔或见证，标出每条线上能读懂的内容。

313728｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_JUNSHI_2668","combination_kind":"CONFLICT_COMBINATION","combination_name":"军事×时间线 冲突搭配","description":"军事类型时间线的对立冲突搭配","mechanism_ids":["MECHANISM_INFORMATION_GAP"],"structure_ids":["STRUCTURE_FLASHBACK"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002160","TSC_002161","TSC_002162"],"dynamic_rule_ids":["TDR_002"],"adaptation_ids":["ADAPT_B_00015","ADAPT_B_00016","ADAPT_B_00017"]}
【本步用法】把倒叙与当前事件和知情时点并列，核查冲突来自实际时间差还是人物误判，定位已经发生的事能如何澄清。

313825｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_JUNSHI_2669","combination_kind":"INFORMATION_COMBINATION","combination_name":"军事×空间布局 信息搭配","description":"军事×空间布局的信息不对称组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["IDENTITY_HIDDEN","JOY","NEED_FOOD"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_002876","TSC_002877","TSC_002878"],"dynamic_rule_ids":["TDR_002","TDR_003"],"adaptation_ids":["ADAPT_B_00058","ADAPT_B_00059","ADAPT_B_00060"]}
【本步用法】依据既有空间布局、物件位置和人物可见范围，核查位置消息由谁掌握，以及实际状态何时可验证。

313924｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_JUNSHI_2670","combination_kind":"RESOURCE_COMBINATION","combination_name":"军事×因果链条 资源搭配","description":"军事世界中因果链条的资源获取路径组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000170","TSC_000171","TSC_000172"],"dynamic_rule_ids":["TDR_002","TDR_004"],"adaptation_ids":["ADAPT_B_00053","ADAPT_B_00057","ADAPT_B_00058"]}
【本步用法】沿已定因果核查资源在前一事件前后怎样取得、转手和耗用，确认后续行为确有已经完成的前置。

314023｜design_ready｜{"combination_id":"RELATION_COMBO_GENRE_JUNSHI_2671","combination_kind":"RELATIONSHIP_COMBINATION","combination_name":"军事×道德困境 关系搭配","description":"基于军事的道德困境关系演化搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001970","TSC_001971","TSC_001972"],"dynamic_rule_ids":["TDR_002","TDR_005"],"adaptation_ids":["ADAPT_B_00062","ADAPT_B_00063","ADAPT_B_00064"]}
【本步用法】从已作伦理取舍与关系范围查当事者了解的事实、资源代价和其后转达，定位究竟哪项选择改变信任。

314122｜design_ready｜{"combination_id":"FORESHADOW_COMBO_GENRE_JUNSHI_2672","combination_kind":"FORESHADOWING_COMBINATION","combination_name":"军事×生存压力 伏笔搭配","description":"军事伏笔线索中生存压力的预置组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_000696","TSC_000697","TSC_000698"],"dynamic_rule_ids":["TDR_002","TDR_006"],"adaptation_ids":["ADAPT_B_00033","ADAPT_B_00034","ADAPT_B_00035"]}
【本步用法】由后文确认的补给压力回查早期的领取、耗损及体力迹象，核对有关资源转手的线索何时可以回收。

314221｜design_ready｜{"combination_id":"STYLE_COMBO_GENRE_JUNSHI_2673","combination_kind":"STYLE_COMBINATION","combination_name":"军事×权力博弈 风格搭配","description":"军事类型下权力博弈的风格变奏搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_002686","TSC_002687","TSC_002688"],"dynamic_rule_ids":["TDR_002","TDR_007"],"adaptation_ids":["ADAPT_B_00021","ADAPT_B_00022","ADAPT_B_00023"]}
【本步用法】依已定权属、关系和作者风格核查表达的强弱与视角距离，说明各人物的权利主张由什么已发生事实支撑。

314320｜design_ready｜{"combination_id":"PROJECT_COMBO_GENRE_JUNSHI_2674","combination_kind":"PROJECT_COMBINATION","combination_name":"军事×身份伪装 项目组合","description":"军事×身份伪装的项目配置组合方案","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FATIGUE","FEAR","IDENTITY_HIDDEN"],"entity_type_ids":["ITEM","VEHICLE","WEAPON"],"static_connection_ids":["TSC_000059","TSC_000060","TSC_000061"],"dynamic_rule_ids":["TDR_002","TDR_008"],"adaptation_ids":["ADAPT_B_00046","ADAPT_B_00047","ADAPT_B_00048"]}
【本步用法】把已有伪装、凭证与可导致暴露的事件按成长顺序放进项目，核对身份认定所需证据在何时对谁可用。

314419｜design_ready｜{"combination_id":"STATIC_COMBO_GENRE_JUNSHI_2675","combination_kind":"STATIC_COMBINATION","combination_name":"军事×知识垄断 静态搭配","description":"军事×知识垄断的静态连接搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001267","TSC_001268","TSC_001269"],"dynamic_rule_ids":["TDR_002","TDR_009"],"adaptation_ids":["ADAPT_B_00109","ADAPT_B_00110","ADAPT_B_00111"]}
【本步用法】依既有知识持有与访问关系核查一直有效的限制和授权，定位相关风险上升时仍成立的条件。

314518｜design_ready｜{"combination_id":"DYNAMIC_COMBO_GENRE_JUNSHI_2676","combination_kind":"DYNAMIC_COMBINATION","combination_name":"军事×情感纽带 动态搭配","description":"军事中基于情感纽带的动态行为组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["DESIRE","FATIGUE","FEAR"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_000798","TSC_000799","TSC_000800"],"dynamic_rule_ids":["TDR_002","TDR_010"],"adaptation_ids":["ADAPT_B_00031","ADAPT_B_00032","ADAPT_B_00033"]}
【本步用法】据已定情感关系、实际消耗和已发生冲突核查行动是否改变了关照或信任，定位前后差异可回查的证据。

314617｜design_ready｜{"combination_id":"EXPRESSION_COMBO_GENRE_JUNSHI_2677","combination_kind":"EXPRESSION_COMBINATION","combination_name":"军事×命运轨迹 表达配合","description":"军事中命运轨迹的语言表达适配组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CHARACTER","CLOTHING","FOOD"],"static_connection_ids":["TSC_001028","TSC_001029","TSC_001030"],"dynamic_rule_ids":["TDR_002","TDR_011"],"adaptation_ids":["ADAPT_B_00001","ADAPT_B_00002","ADAPT_B_00003"]}
【本步用法】按命运节点和已发生的缓和核查叙述用词怎样呈现预期、转折及最终可知结果，保持与人物所知相合。

314716｜design_ready｜{"combination_id":"SCENE_COMBO_GENRE_JUNSHI_2678","combination_kind":"SCENE_COMBINATION","combination_name":"军事×禁忌领域 场景搭配","description":"军事类型下禁忌领域的场景布局搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001364","TSC_001365","TSC_001366"],"dynamic_rule_ids":["TDR_002","TDR_012"],"adaptation_ids":["ADAPT_B_00038","ADAPT_B_00039","ADAPT_B_00040"]}
【本步用法】依既有禁区边界及可行备选核查场景可呈现的进入、受阻和退让，确认在场者能直接观察到的依据。

314815｜design_ready｜{"combination_id":"CONFLICT_COMBO_GENRE_JUNSHI_2679","combination_kind":"CONFLICT_COMBINATION","combination_name":"军事×传承体系 冲突搭配","description":"军事×传承体系的冲突机制组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_002786","TSC_002787","TSC_002788"],"dynamic_rule_ids":["TDR_002","TDR_013"],"adaptation_ids":["ADAPT_B_00030","ADAPT_B_00031","ADAPT_B_00032"]}
【本步用法】从已有传承资格、载体和已设失败条件核查双方的争执，明确哪项既定事件使交接受阻或可被继续验证。

314914｜design_ready｜{"combination_id":"INFO_COMBO_GENRE_JUNSHI_2680","combination_kind":"INFORMATION_COMBINATION","combination_name":"军事×背叛成本 信息搭配","description":"军事叙事中背叛成本的信息披露节奏组合","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["ANGER","DESIRE","FATIGUE"],"entity_type_ids":["FOOD","ITEM","VEHICLE"],"static_connection_ids":["TSC_001906","TSC_001907","TSC_001908"],"dynamic_rule_ids":["TDR_002","TDR_014"],"adaptation_ids":["ADAPT_B_00047","ADAPT_B_00048","ADAPT_B_00049"]}
【本步用法】沿已确认背叛及中断事件核查各人先看见的损失、后来得到的报告与验证点，定位叙述披露的先后。

315013｜design_ready｜{"combination_id":"RESOURCE_COMBO_GENRE_JUNSHI_2681","combination_kind":"RESOURCE_COMBINATION","combination_name":"军事×觉醒机制 资源搭配","description":"基于军事的觉醒机制资源转换搭配","mechanism_ids":["MECHANISM_GROWTH"],"structure_ids":["STRUCTURE_LINEAR"],"concept_ids":["FEAR","IDENTITY_HIDDEN","JOY"],"entity_type_ids":["CLOTHING","FOOD","ITEM"],"static_connection_ids":["TSC_001800","TSC_001801","TSC_001802"],"dynamic_rule_ids":["TDR_002","TDR_015"],"adaptation_ids":["ADAPT_B_00006","ADAPT_B_00007","ADAPT_B_00008"]}
【本步用法】按已设觉醒前置与延迟后果核查资源取得、消耗和转化，确认何时能实际动用以及何时可以证实。"""
