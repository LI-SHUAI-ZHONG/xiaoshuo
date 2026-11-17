"""类型适配时核对作品参考边界及组合的来源、比较和使用记录。"""

DYNAMIC_REFERENCE_USE = (
    '实际采用动态规则时，使用本步读到的原件位置和工作包的来源引用。保留原组合的 '
    'dynamic_rule_ids 或 source_rule_ids 时，按 TDV_020 核对所对应版本和关系。'
    '用途、触发条件、前置产物和未核问题依项目实际证据记录。'
)

MATERIAL = r"""
【《类型系统》热门作品相似度使用规则.json｜SOURCE[62]｜原文第 468,981 行】
【本步用法】只有项目已经确认采用有来源的作品参考时，才按各条规则核对相似内容。相似度在 type_adaptation 的 boundaries 中说明比较对象、类型特征或多样性用途，引用实际比较依据。未确认的旧候选作品和相似分不进入项目依据。
【原文规则字段】{"rule_id":"POPULAR_WORK_SIMILARITY_RULES_V1","version":"1.0","created_at":"2026-07-31 11:55:45","rules":["热门作品相似度只用于类型特征提取和多样性参考","不得将热门作品相似度当作剧情合理性证明","不得将热门作品拆解结果当作原创小说剧情","相似度只能用于排序和参考，不生成具体内容","热门作品模式是抽象参考，不是剧情模板"]}
【逐项用法】
1．只在作者已确认的作品参考中提取已有类型特征，说明和本次多样性比较的关系。
2．剧情合理性继续用项目里的前置条件、因果和人物选择核对。
3．用抽象参考核对类型，保留本项目独立设计的剧情来源。
4．只有已有可回查的相似比较数据时用于排序，写清采用或放弃的依据。
5．回查原对象中抽象模式的适用条件，具体行动及剧情沿当前项目设计步骤决定。

【《类型系统》组合评分规则.json｜SOURCE[73]｜原文第 474,180 行】
【本步用法】仅对已依据作者类型、实际用途和已核资料筛过的组合逐项核对。可引用已有可解释的分项和证据，缺项在 boundaries 留存。原表正向权重合计 0.90，负项权重为 null，完整计算口径待核。
【原文规则字段】{"rule_id":"SCORING_RULES_V1","version":"1.0","created_at":"2026-07-31 11:55:45","score_fields":{"compatibility_score":{"weight":0.15,"description":"类型兼容度评分","explainable":true},"source_support_score":{"weight":0.15,"description":"来源支持度评分","explainable":true},"hierarchy_validity_score":{"weight":0.1,"description":"层级合法性评分","explainable":true},"static_connection_score":{"weight":0.05,"description":"静态连接有效性评分","explainable":true},"dynamic_rule_validity_score":{"weight":0.05,"description":"动态规则有效性评分","explainable":true},"expression_completeness_score":{"weight":0.05,"description":"表达完整性评分","explainable":true},"scene_usefulness_score":{"weight":0.05,"description":"场景有用性评分","explainable":true},"information_diversity_score":{"weight":0.05,"description":"信息多样性评分","explainable":true},"resource_diversity_score":{"weight":0.05,"description":"资源多样性评分","explainable":true},"relationship_diversity_score":{"weight":0.05,"description":"关系多样性评分","explainable":true},"foreshadowing_diversity_score":{"weight":0.05,"description":"伏笔多样性评分","explainable":true},"continuity_safety_score":{"weight":0.05,"description":"连续性安全评分","explainable":true},"novelty_score":{"weight":0.05,"description":"新颖性评分","explainable":true},"history_penalty":{"weight":null,"description":"历史使用惩罚（负值）","explainable":true},"duplicate_penalty":{"weight":null,"description":"重复惩罚（负值）","explainable":true},"unsupported_fact_penalty":{"weight":null,"description":"无来源事实惩罚（负值）","explainable":true},"conflict_penalty":{"weight":null,"description":"冲突惩罚（负值）","explainable":true}},"forbidden":["使用不可解释的总分","用评分掩盖来源缺失","用高分覆盖严重冲突","用多样性分数替代因果验证","用新颖性分数替代类型合法性"]}
【逐项用法】
1．compatibility_score 核对候选双方当前采用的类型和具体兼容理由。
2．source_support_score 对照现行源页及来源资格，记录支持本次组合的证据。
3．hierarchy_validity_score 核对主类型、子类型或混合类型的层级及父级。
4．static_connection_score 核对实际采用的静态连接和两端当前对象。
5．dynamic_rule_validity_score 核对动态规则的当前资格、已有触发和限制。
6．expression_completeness_score 核对已有表达参数、适用条件和缺项。
7．scene_usefulness_score 已有场景时，核对场景目标所需和组合实际可提供的设计条件。
8．information_diversity_score 依据两组已知信息用途和披露方式比较差别。
9．resource_diversity_score 依据现有资源的用途、得失及限制比较差别。
10．relationship_diversity_score 依据已有角色、关系及变动边界比较差别。
11．foreshadowing_diversity_score 依据已有伏笔的埋设、回收及作用比较差别。
12．continuity_safety_score 对照已确认设定和前后状态，检查可保留的因果与连续性。
13．novelty_score 只有已有比较对象和证据时才说明本次差异。
14．history_penalty 依据独立的实际使用记录回查。
15．duplicate_penalty 依据已核对的相似签名及重复口径回查。
16．unsupported_fact_penalty 定位欠缺来源的具体字段，保留其资格处理。
17．conflict_penalty 定位与现行来源、上游设定和因果有冲突的具体字段。

【《类型系统》组合生成策略.json｜SOURCE[74]｜原文第 474,328 行】
【本步用法】用各层原义说明项目当前用途和已有候选的适用程度。合法性按现行来源核验，缺来源或引用待定时保持原资格。多样性和最小评分指标出自原组合构建策略；具体评分字段映射及缺项口径待核。可用于核对候选，项目事实与实际动作由相关步骤根据已成立前置产出。
【原文规则字段】{"strategy_id":"COMBO_GEN_STRATEGY_V1","strategy_name":"类型组合生成策略","version":"1.0","created_at":"2026-07-31 11:55:45","layers":{"layer_1_legality":{"name":"合法性筛选","rules":["类型ID必须存在于类型总表","父子层级关系合法","机制、结构、风格类型正确","组合对象间无明确冲突关系","不引用pending或fixture状态的内容","动态组合引用的动态规则必须为active状态","不引用C00484至C00494范围内的规则"],"failure_action":"reject"},"layer_2_semantic":{"name":"语义互补筛选","dimensions":["冲突维度","资源维度","信息维度","身份维度","关系维度","场景维度","节奏维度","伏笔维度","表达维度","人物选择维度"],"min_coverage_dimensions":3,"failure_action":"downgrade"},"layer_3_dedup":{"name":"重复筛选","detection_rules":["完全相同组合检测","组成部分相同但顺序不同检测","组成部分高度重叠（>80%）检测","概念焦点完全相同检测","动态规则集合完全相同检测","场景焦点完全相同检测","表达参数高度相似（余弦相似度>0.9）检测","资源和信息路径高度相似检测"],"failure_action":"reject_or_downgrade"},"layer_4_diversity":{"name":"多样性筛选","target_dimensions":["概念组合","人物关系","身份冲突","资源约束","信息差","场景类型","事件类型","伏笔类型","节奏","风格","叙事结构","道德困境","社交策略","失败路径","延迟后果"],"min_unique_dimensions_per_type":8,"failure_action":"downgrade"},"layer_5_quality":{"name":"质量筛选","score_components":["compatibility_score","source_support_score","structure_validity_score","diversity_score","novelty_score","continuity_safety_score","retrieval_usefulness_score","repetition_penalty","unsupported_fact_penalty","conflict_penalty"],"min_quality_score":0.3,"failure_action":"downgrade_or_reject"}},"generation_constraints":["不得生成具体人物事实","不得生成具体剧情事实","不得自动选择固定动作","不得复制原始动态规则正文","不得自动创建completed事件","组合候选不得覆盖原始三网络","相似度只用于排序和去重，不代表剧情合理性"]}
【逐项用法】
1．合法性筛选逐项核对原列 7 条，引用现行原文的类型 ID、层级、资格与禁用范围；模板或空表不能自证冲突已解决。
2．语义互补以本次确有依据的 10 类维度逐项识别覆盖，原门槛只用于本策略的候选构建。
3．重复筛选实查候选的组成、关注点、动态条件和资源信息路径；原重叠及余弦阈值有明确可复核的分值时使用。
4．多样性筛选记录本次具备的具体差异，用原列维度解释各候选能提供的不同用途。
5．质量筛选只报告已可复核的分项；与第73块不完全同名的字段待核，按来源核对门槛的实际依据。
6．七条 generation_constraints 逐项对应实际方法输出与下游边界，保留候选身份及原网络来源。

【《类型系统》组合使用记录说明.md｜SOURCE[75]｜原文第 474,477 行】
【本步用法】依据本项目的已选类型、已有章场目标及真实使用记录执行筛选说明。使用前后按现有步骤产物或已有使用记录记明选择、证据和偏差。原记录说明中的分数只核对已可复算的值。缺少章场、签名或历史记录时在 boundaries 指明缺什么。
【原文】
# 组合使用记录说明

## 状态标记

| 状态 | 含义 |
|------|------|
| planned | 计划调用但尚未使用 |
| used | 已实际使用 |
| replaced | 使用后被替换 |
| conflict | 发现冲突 |

## 记录规则

1. 不能删除历史记录
2. 不得把历史记录当作原始资料
3. 历史记录必须与正式项目数据隔离管理
4. 每次组合调用必须记录选择理由
5. 实际使用与计划有偏差必须记录

## 使用流程

1. 读取项目类型和当前场景目标
2. 筛选合法组合
3. 计算兼容度、相似度
4. 施加历史使用惩罚和重复惩罚
5. 返回候选并记录选择
6. 使用后记录实际效果
【逐项用法】
1．planned 对应实际选中的准备方案，先记本步选择理由与适用原条。
2．used 依据后续步骤或正文可回查的实际采用证据和效果确认。
3．replaced 保留旧采用出处、后来选取及替换理由。
4．conflict 记实质冲突及受影响的规则、对象或后续步骤。
5．兼容度、相似度和历史惩罚按已具备的候选、章场和记录核对。保留 planned 与 used 的偏差，用相应产物或已有历史记录举证。

【《类型系统》组合相似度规则.json｜SOURCE[76]｜原文第 474,508 行】
【本步用法】比较本项目已有候选的相似处时逐维说明两份资料实际共有的字段以及差别，参考原表方法与阈值。多个维度在相关签名表里无对应字段或无非空值，词组/参数向量、空集合及归一口径也待核。启用具体分值以项目已有可复核数据及核定口径为前提；相似度只服务于候选排序和去重。
【原文规则字段】{"rule_id":"SIMILARITY_RULES_V1","version":"1.0","created_at":"2026-07-31 11:55:45","dimensions":{"type_overlap":{"weight":0.15,"method":"jaccard"},"mechanism_overlap":{"weight":0.1,"method":"jaccard"},"structure_overlap":{"weight":0.1,"method":"jaccard"},"style_overlap":{"weight":0.1,"method":"jaccard"},"concept_overlap":{"weight":0.1,"method":"jaccard"},"event_overlap":{"weight":0.05,"method":"jaccard"},"resource_overlap":{"weight":0.05,"method":"jaccard"},"information_overlap":{"weight":0.05,"method":"jaccard"},"relationship_overlap":{"weight":0.05,"method":"jaccard"},"foreshadowing_overlap":{"weight":0.05,"method":"jaccard"},"scene_overlap":{"weight":0.05,"method":"jaccard"},"dynamic_rule_overlap":{"weight":0.05,"method":"jaccard"},"failure_branch_overlap":{"weight":0.05,"method":"jaccard"},"expression_overlap":{"weight":0.05,"method":"cosine"}},"thresholds":{"exact_duplicate":1,"high_similarity":0.8,"medium_similarity":0.5,"low_similarity":0.2,"distinct":"< 0.2"}}
【逐项用法】
1．type_overlap 比较两候选有据的类型集合。
2．mechanism_overlap 比较实际可用的机制集合。
3．structure_overlap 比较已记录的结构集合。
4．style_overlap 比较现有可核风格集合，作者未定风格时如实保留缺项。
5．concept_overlap 比较双方有实际用途的概念集合。
6．event_overlap 比较已有明确事件类型；空数组不证明相同事件。
7．resource_overlap 比较已有资源类型；空数组留空。
8．information_overlap 比较已有信息类型；空数组留空。
9．relationship_overlap 需要双方有据的关系类型集合，签名表无对应字段，核对实际已提供的记录。
10．foreshadowing_overlap 比较已有伏笔类型，空数组留空。
11．scene_overlap 需有双方实际可比的场景类型，签名表中没有该维。
12．dynamic_rule_overlap 比较双方引用的现行规则集合并核对适用资格。
13．failure_branch_overlap 需有双方实际有据的失败分支和一致口径，签名表中没有该维。
14．expression_overlap 需有同口径的可比较表达向量才能核对原表 cosine。

【《类型系统》组合相似度签名.json｜SOURCE[77]｜原文第 474,627 行】
【本步用法】逐行比对原签名表和已经写入本步的第56块组合表，4,200 个 combination_id 顺序及签名映射的 13 个原字段完全对应。按下列字段从双方实际选定的组合行读取签名，空数组保持为空；比较前先核对两条组合是否适用本项目。
【原文表头】{"signature_schema_version":"2.0","created_at":"2026-07-31 11:55:45","total_combinations":4200,"dimensions":["type_signature","subtype_signature","mechanism_signature","structure_signature","style_signature","concept_signature","event_signature","information_signature","resource_signature","foreshadowing_signature","dynamic_rule_signature"]}
【签名字段与本步已有第56块字段对应】{"type_signature":"type_ids","subtype_signature":"subtype_ids","mechanism_signature":"mechanism_ids","structure_signature":"structure_ids","style_signature":"style_ids","concept_signature":"concept_ids","event_signature":"event_type_ids","information_signature":"information_type_ids","resource_signature":"resource_type_ids","foreshadowing_signature":"foreshadowing_type_ids","dynamic_rule_signature":"dynamic_rule_ids","combination_kind":"combination_kind","primary_type_id":"primary_type_id"}
原表的 event_signature、information_signature、resource_signature、foreshadowing_signature 全为空；实际有说明的比较对象不足时，在 boundaries 指明。

【《类型系统》组合验证规则.json｜SOURCE[78]｜原文第 603,037 行】
【本步用法】在本步候选筛选中按原 V01–V20 顺序逐项核对本次具有适用条件的要求。组合或引用待核时保留资格和证据缺口。原规则只作组合候选的查验依据，后续设计及正文依各现有步骤执行。
【原文规则字段】{"rule_id":"VALIDATION_RULES_V1","version":"1.0","created_at":"2026-07-31 11:55:45","validations":[{"id":"V01","rule":"组合ID合法","field":"combination_id","check":"non_empty_unique"},{"id":"V02","rule":"组合组成部分存在","field":"type_ids/subtype_ids/etc","check":"ref_exists"},{"id":"V03","rule":"组合种类与ID前缀一致","field":"combination_kind vs combination_id","check":"prefix_match"},{"id":"V04","rule":"主类型存在","field":"primary_type_id","check":"ref_exists_in_type_table"},{"id":"V05","rule":"子类型父级存在","field":"subtype_ids","check":"parent_exists"},{"id":"V06","rule":"混合类型组件存在","field":"hybrid_ids","check":"ref_exists"},{"id":"V07","rule":"机制、结构和风格类型正确","field":"mechanism/structure/style_ids","check":"type_correct"},{"id":"V08","rule":"静态搭配不含动态触发条件","field":"static_combination","check":"no_dynamic_triggers"},{"id":"V09","rule":"动态搭配引用的规则存在","field":"dynamic_rule_ids","check":"ref_exists"},{"id":"V10","rule":"动态搭配不引用C00484-C00494","field":"dynamic_rule_ids","check":"not_in_forbidden_range"},{"id":"V11","rule":"动态搭配传播限制不超标","field":"propagation_profile","check":"within_limits"},{"id":"V12","rule":"组合不包含固定行为","field":"all","check":"no_fixed_behavior"},{"id":"V13","rule":"组合不包含固定剧情","field":"all","check":"no_fixed_plot"},{"id":"V14","rule":"组合不包含测试夹具","field":"all","check":"no_fixture_in_production"},{"id":"V15","rule":"组合可被片段读取","field":"all","check":"accessible_by_id"},{"id":"V16","rule":"组合调用数量不超限","field":"all","check":"within_call_limits"},{"id":"V17","rule":"组合不会直接写入状态","field":"all","check":"no_direct_state_write"},{"id":"V18","rule":"组合不会直接生成正文","field":"all","check":"no_direct_text_gen"},{"id":"V19","rule":"组合不会覆盖人物性格/身份/能力","field":"all","check":"no_char_override"},{"id":"V20","rule":"组合不会修改原始三网络","field":"all","check":"no_source_modification"}]}
【逐项用法】
1．按本步实际读取的组合记录核对 ID 唯一且非空。
2．核对组合列出的组成 ID 能追溯到现行资料。
3．核对原 combination_kind 对应原 ID 前缀。
4．在项目用的类型表中核对原列主类型。
5．核对每个采用子类型能定位到与项目相符的父级。
6．核对混合类型列出的组件均存在且有据。
7．分别核对机制、结构、风格的原文标类。
8．核对静态搭配本身是否含动态触发；已列动态规则引用须辨明用途。
9．对原列动态规则逐一核查现行出处。
10．引用落在旧隔离编号范围时，核对所用文件版本、条目位置及关系两端。沿明确的现用来源核对实际资格，旧待恢复项及出处不明的引用保留隔离。
11．以原传播限制同本次候选传播范围核查。
12．检查组合资料是否强制指定人物的实际行动。
13．检查组合资料是否预设实际项目情节。
14．检查原组合及引用的资格，隔离夹具。
15．用来源 ID 或组合 ID 确认可实际回查原条。
16．按已有数量上限核对本次调用；没有生效上限时标待核。
17．检查候选仅影响本步设计，实际状态仍依独立事实认定流程。
18．检查本步产物保持为类型适配设计，表达和正文依后续职责形成。
19．对照已有项目人物资料判明性格、身份与能力是否被覆盖。
20．核对这次类型适配只使用原网络的实际引用，保留其原记录。

【《类型系统》组合重复惩罚规则.json｜SOURCE[79]｜原文第 603,213 行】
【本步用法】先看两个组合实际可比较的范围，并核对是否只是同类型、同概念或同风格。只有相似分已有出处和可核依据时才按原值解释候选排序或拒绝的原因；已确认项目设定以实际决定为据。
【原文规则字段】{"rule_id":"DUPLICATE_PENALTY_RULES_V1","version":"1.0","created_at":"2026-07-31 11:55:45","penalty_levels":{"exact_duplicate":{"threshold":1,"action":"reject","description":"完全重复：直接拒绝"},"high_duplicate":{"threshold":0.8,"action":"heavy_downgrade","penalty":0.5,"description":"高度重复：大幅降权"},"medium_duplicate":{"threshold":0.5,"action":"downgrade","penalty":0.2,"description":"中度重复：保留但降低优先级"},"low_duplicate":{"threshold":0.2,"action":"keep_normal","penalty":0.05,"description":"低度重复：正常保留"},"only_type_same":{"threshold":"N/A","action":"not_duplicate","description":"仅类型相同但其他维度不同：不得判定为重复"},"only_concept_same":{"threshold":"N/A","action":"not_duplicate","description":"仅共享同一概念：不得判定为重复"},"only_style_same":{"threshold":"N/A","action":"not_duplicate","description":"仅共享同一风格：不得判定为重复"}}}
【逐项用法】
1．双方具有同口径且完全相同的组合签名时，按原拒绝规则处理该重复候选。
2．达到已有高相似判定时，按原 0.5 惩罚解释降序及其证据。
3．达到已有中相似判定时，记录原 0.2 惩罚，保留候选。
4．达到已有低相似判定时记录原 0.05 惩罚及正常保留。
5．仅同类型时，保留实际差别及该次比较理由。
6．仅同概念时，保留实际差别及该次比较理由。
7．仅同风格时，保留实际差别及该次比较理由。
"""
