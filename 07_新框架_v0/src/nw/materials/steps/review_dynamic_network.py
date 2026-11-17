"""场景审稿步骤所用的《动态网络》原文与本步用法。"""

MATERIAL = r"""【动态网络原文 · 场景检查范围待核】
每条先列连接列表的原文行及作用字段，再列原始端点、规范端点与来源字段原值。根据作者已采用的项目关系和本步实际事件、人物及条件使用。valid_types 保留原件的适用范围。

33928｜{"id":"C00163","source":"123.3_无短板原则","target":"91_场景检查","type":"约束","condition":"无短板=各板块通过检查；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"source_layer":"未分类","target_layer":"未分类","generated_from_static":true,"needs_review":false,"validation_status":"derived_contract_validated","status":"derived"}
【追溯原值】{"derivation_contract":"NET-DYNAMIC-DERIVATION-CONTRACT-1.0","original_source":"123.3_无短板原则","original_target":"91_场景检查","normalized_source":"123.3_无短板原则","normalized_target":"91_场景检查","field_source":{"direction":"明确默认规则: direction=单向","strength":"明确默认规则: strength=中","valid_types":"NET-DYNAMIC-DERIVATION-CONTRACT-1.0 全类型适用策略","source_layer":"明确默认规则: 未分类","target_layer":"明确默认规则: 未分类","condition":"静态网络对应记录","priority":"静态网络对应记录","effect":"按静态关系类型派生的通用状态变化语义"},"source_refs":[{"artifact":"NET-STATIC-FULL","source":"静态网络.txt source_index","source_key":["123.3_无短板原则","91_场景检查","约束"]}],"review_reason":"已按 NET-DYNAMIC-DERIVATION-CONTRACT-1.0 校验；具体故事采用仍需绑定当前对象和情境"}
【本步用法】本条现行裁定为 blocked。原目标「91_场景检查」和板块91场景结构检查的对应范围待核，保留原约束供当前范围查缺。

【动态网络原文 · 稿段动作与精确动词的核对】

248026｜{"id":"C01183","source":"50.1_精确动词","target":"156.5_动作审美","type":"约束","condition":"精确动词支撑审美；且当前故事明确采用该静态关系","priority":1,"effect":"当起点成立时，限制终点可采取的状态或行为范围。","direction":"单向","strength":"中","valid_types":["玄幻","仙侠","科幻","游戏","军事","悬疑","都市","历史","言情","奇幻"],"source_layer":"未分类","target_layer":"未分类","generated_from_static":true,"needs_review":false,"validation_status":"derived_contract_validated","status":"derived"}
【追溯原值】{"derivation_contract":"NET-DYNAMIC-DERIVATION-CONTRACT-1.0","original_source":"50.1_精确动词","original_target":"156.5_动作审美","normalized_source":"50.1_精确动词","normalized_target":"156.5_动作审美","field_source":{"direction":"明确默认规则: direction=单向","strength":"明确默认规则: strength=中","valid_types":"NET-DYNAMIC-DERIVATION-CONTRACT-1.0 全类型适用策略","source_layer":"明确默认规则: 未分类","target_layer":"明确默认规则: 未分类","condition":"静态网络对应记录","priority":"静态网络对应记录","effect":"按静态关系类型派生的通用状态变化语义"},"source_refs":[{"artifact":"NET-STATIC-FULL","source":"静态网络.txt source_index","source_key":["50.1_精确动词","156.5_动作审美","约束"]}],"review_reason":"已按 NET-DYNAMIC-DERIVATION-CONTRACT-1.0 校验；具体故事采用仍需绑定当前对象和情境"}
【本步用法】在本次覆盖的稿段中，以实有动作、对象、先后和结果检查动词能否具体表现项目采用的动作审美，标明相应句子。
"""
