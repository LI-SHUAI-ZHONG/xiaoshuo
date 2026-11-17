"""类型适配及跨章审稿使用的作品参考规则。"""

ADAPTATION_GUIDANCE = r"""
【作品参考的相似度、选取与重复核对】
以项目实际采用或明确拟采用且来源可回查的抽象参考为依据。按作者已确定的类型和本步实际用途选择相关规则，引用实际比较或使用记录。空内容和未提供的历史均记录为缺项。写法取舍依实际剧情、人物、场景需要及作者决定。
"""

SCOPE_REVIEW_GUIDANCE = r"""
【已采用作品参考的原创性审稿】
在实际稿件和项目引用确有覆盖时核对下列规则。连续使用按已覆盖章场逐项查记录。审稿在现有结果中报告风险、相关稿件位置和来源，对无法核对的内容说明证据缺口。
"""

ORIGINALITY_RULES = r"""
【《类型系统》作品知识库\相似度\原创性风险规则.json｜SOURCE[377]｜原文第 642,915 行】
【原文规则字段】{"schema_name":"原创性风险规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"OR-01","description":"完全相同签名：拒绝"},{"rule_id":"OR-02","description":"高度相似：降权并人工复核"},{"rule_id":"OR-03","description":"中度相似：保留并施加惩罚"},{"rule_id":"OR-04","description":"低度相似：正常保留"},{"rule_id":"OR-05","description":"高原创性风险不得自动进入正式项目"}]}
【本条用法】在项目有可比较的案例提案和来源记录时，按 OR-01 至 OR-05 核对重复与原创性风险。完全相同签名针对重复候选，高风险交人工核对其正式采用资格。审稿按第 70 块从实际稿件报告风险和出处。
"""

REUSE_RULES = r"""
【《类型系统》作品资料库\案例重复惩罚规则.json｜SOURCE[395]｜原文第 647,395 行】
【原文规则字段】{"schema_name":"案例重复惩罚规则","schema_version":"TYPE_F-1.0.0","rules":[{"condition":"同一案例重复使用","penalty":0.8,"max_consecutive":2},{"condition":"同一作品连续使用","penalty":0.6,"max_consecutive":3},{"condition":"同一场景重复案例","penalty":1,"action":"reject"},{"condition":"多个案例组合高度接近单一作品结构","risk":"high","action":"report"}]}
【本条用法】按当前项目、章场顺序和实际使用记录依次核对原四条规则。同一案例与同一作品的连续次数从实际采用记录计算。重复候选的处理和已成稿的风险报告分别沿用各自步骤的判据。
"""

CASE_SIMILARITY = r"""
【《类型系统》作品知识库\相似度\案例相似度特征.json｜SOURCE[375]｜原文第 642,739 行】
【原文规则字段】{"schema_name":"案例相似度特征","schema_version":"H0D-1.0.0","dimensions":["类型","子类型","机制","结构","风格","主题","剧情阶段","人物功能","人物关系","身份模式","世界元素","物品功能","信息模式","资源模式","钩子","冲突","爽点","伏笔","节奏","场景","失败路径","后果类型"],"items":[],"count":0,"evidence_type":"template","status":"active"}
【本条用法】已有项目可用案例及可比较对象时，按原列 22 个维度核对公开的抽象用途与彼此差异。items 为空时，比较材料只取本次实际提供的案例记录。记录差异对应的事实与用途。
"""

CASE_DUPLICATION = r"""
【《类型系统》作品知识库\相似度\案例重复惩罚规则.json｜SOURCE[376]｜原文第 642,820 行】
【原文规则字段】{"schema_name":"案例重复惩罚规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"P-01","description":"完全相同签名：拒绝"},{"rule_id":"P-02","description":"高度相似：降权并人工复核"},{"rule_id":"P-03","description":"中度相似：保留并施加惩罚"},{"rule_id":"P-04","description":"低度相似：正常保留"},{"rule_id":"P-05","description":"同类型不等于重复"},{"rule_id":"P-06","description":"同概念不等于重复"},{"rule_id":"P-07","description":"同风格不等于重复"},{"rule_id":"P-08","description":"相似度不能证明质量"},{"rule_id":"P-09","description":"相似度不能直接生成剧情"},{"rule_id":"P-10","description":"高原创性风险不得自动进入正式项目"}]}
【本条用法】按项目所用案例的实际比较，在适配结果说明选择、降权、拒绝或提交复核的理由。P-05 至 P-07 逐项确认是否仅同一种类、概念或风格。P-08 至 P-10 用于核对评价依据、取用边界与正式采用资格。相似分档缺少口径时，记录依据和待核项。
"""

COMBINATION_SIMILARITY = r"""
【《类型系统》作品知识库\相似度\组合相似度特征.json｜SOURCE[378]｜原文第 642,990 行】
【原文规则字段】{"schema_name":"组合相似度特征","schema_version":"H0D-1.0.0","dimensions":["类型","子类型","机制","结构","风格","主题","剧情阶段","人物功能","人物关系","身份模式","世界元素","物品功能","信息模式","资源模式","钩子","冲突","爽点","伏笔","节奏","场景","失败路径","后果类型"],"items":[],"count":0,"evidence_type":"template","status":"active"}
【本条用法】仅对当前有用且可回查的抽象组合，按原列 22 个维度对照前置、适用范围和实际差异。此表的 items 为空，组合签名若来自第 77 块则采用其原字段定义，比较记录明确所用维度。
"""

COMBINATION_DUPLICATION = r"""
【《类型系统》作品知识库\相似度\组合重复惩罚规则.json｜SOURCE[379]｜原文第 643,071 行】
【原文规则字段】{"schema_name":"组合重复惩罚规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"P-01","description":"完全相同签名：拒绝"},{"rule_id":"P-02","description":"高度相似：降权并人工复核"},{"rule_id":"P-03","description":"中度相似：保留并施加惩罚"},{"rule_id":"P-04","description":"低度相似：正常保留"},{"rule_id":"P-05","description":"同类型不等于重复"},{"rule_id":"P-06","description":"同概念不等于重复"},{"rule_id":"P-07","description":"同风格不等于重复"},{"rule_id":"P-08","description":"相似度不能证明质量"},{"rule_id":"P-09","description":"相似度不能直接生成剧情"},{"rule_id":"P-10","description":"高原创性风险不得自动进入正式项目"}]}
【本条用法】对抽象组合的候选依 P-01 至 P-10 核对重复和原创性条件。以本次真实签名与比较记录处理排序。已选类型只用来确定查找范围，具体用途及与已有材料的差异由本步核对。
"""

WORK_SIMILARITY = r"""
【《类型系统》作品知识库\相似度\作品相似度特征.json｜SOURCE[380]｜原文第 643,166 行】
【原文规则字段】{"schema_name":"作品相似度特征","schema_version":"H0D-1.0.0","dimensions":["类型","子类型","机制","结构","风格","主题","剧情阶段","人物功能","人物关系","身份模式","世界元素","物品功能","信息模式","资源模式","钩子","冲突","爽点","伏笔","节奏","场景","失败路径","后果类型"],"items":[],"count":0,"evidence_type":"template","status":"active"}
【本条用法】项目已确认使用作品的抽象参考时，按原列维度对照所采用的机制、结构和风格等有证据的内容。空表只给出了比较维度，实际参考来自本次已采用资料。
"""

WORK_DUPLICATION = r"""
【《类型系统》作品知识库\相似度\作品重复惩罚规则.json｜SOURCE[381]｜原文第 643,247 行】
【原文规则字段】{"schema_name":"作品重复惩罚规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"P-01","description":"完全相同签名：拒绝"},{"rule_id":"P-02","description":"高度相似：降权并人工复核"},{"rule_id":"P-03","description":"中度相似：保留并施加惩罚"},{"rule_id":"P-04","description":"低度相似：正常保留"},{"rule_id":"P-05","description":"同类型不等于重复"},{"rule_id":"P-06","description":"同概念不等于重复"},{"rule_id":"P-07","description":"同风格不等于重复"},{"rule_id":"P-08","description":"相似度不能证明质量"},{"rule_id":"P-09","description":"相似度不能直接生成剧情"},{"rule_id":"P-10","description":"高原创性风险不得自动进入正式项目"}]}
【本条用法】按可查的实际来源比较作品参考的重复使用，记录有据的相似分档及采用理由。P-05 至 P-07 依实际证据区分共享单一维度与整体重复，风险项按现有项目审稿规则报告。
"""

CASE_COMPARISON = r"""
【《类型系统》作品资料库\案例相似度特征.json｜SOURCE[394]｜原文第 647,323 行】
【原文规则字段】{"schema_name":"案例相似度特征","schema_version":"TYPE_F-1.0.0","description":"案例间相似度比较维度","comparison_dimensions":["主类型","子类型","机制","叙事结构","风格","概念焦点","人物关系","身份模式","资源模式","信息模式","事件模式","伏笔模式","节奏模式","场景模式","失败路径","后果类型"]}
【本条用法】本次使用的是作品资料库里的实际案例时，按原列 16 个维度检查案例服务的具体剧情、关系、伏笔、场景和失败路径。用可核的项目目标和案例字段说明采用理由。
"""

WORK_COMPARISON = r"""
【《类型系统》作品资料库\作品相似度特征.json｜SOURCE[448]｜原文第 653,910 行】
【原文规则字段】{"schema_name":"作品相似度特征","schema_version":"TYPE_F-1.0.0","comparison_dimensions":["主类型","子类型","机制","叙事结构","风格","概念焦点","人物关系","身份模式","资源模式","信息模式","事件模式","伏笔模式","节奏模式","场景模式","失败路径","后果类型"],"usage_rules":["相似度只用于检索、排序和多样性控制","不得以相似度证明作品质量","不得以相似度直接生成剧情","不得因为相似度高就删除来源作品","不得因为相似度低就认定作品类型不同"]}
【本条用法】项目采用已确认的抽象参考时，按原列 16 个维度比较检索与多样性需要，记录可核证据和使用理由。相似度规则按原文约束实际排序与创作。
"""

MATERIAL = '\n'.join((
    ADAPTATION_GUIDANCE,
    CASE_SIMILARITY,
    CASE_DUPLICATION,
    ORIGINALITY_RULES,
    COMBINATION_SIMILARITY,
    COMBINATION_DUPLICATION,
    WORK_SIMILARITY,
    WORK_DUPLICATION,
    CASE_COMPARISON,
    REUSE_RULES,
    WORK_COMPARISON,
))

SCOPE_REVIEW_MATERIAL = '\n'.join((SCOPE_REVIEW_GUIDANCE, ORIGINALITY_RULES, REUSE_RULES))
