"""人物设计中的实体类型适配的《类型系统》原文。"""

MATERIAL = r"""#### 人物设计中的实体类型适配
【类型系统原文位置】类型表达适配总表.json 第20889行
【各条共用原文值】{"priority":0,"weight":0,"source_refs":[],"evidence_type":"template","confidence":999,"status":"active","schema_version":"TYPE_B-1.0.0"}
【本步使用条件】
本步核对原 target_id 为 CHARACTER 的对象，结合已有人物和世界要求记录允许保留的字段和缺口。原表出现物品用途及归属语义，沿用本轮的待核身份；人物已定身份、动机与能力沿用项目依据。
原始 confidence=999 按原值保留。design_ready 条目沿用现有资格及有效字段，按作者实际需要选用。blocked 条目用于核对待核字段及影响，项目参数沿用已确认的依据。GENRE_MORI 依项目已确认的原 ID 核对。
【逐条原文值】adaptation_id 原文行 | 现有资料裁定 | adaptation_id | type_id | target_kind | target_id | target_scope | adaptation_kind | 本步原字段 | 本步用法
22100 | blocked | ADAPT_B_00022 | GENRE_XIANXIA | entity_type | CHARACTER | null | expression_preference | {"parameters":{"appearance_preference":["仙气飘渺","灵光环绕","古朴典雅"],"function_emphasis":["修炼辅助","品级压制","认主绑定"],"ownership_emphasis":"宗门/个人","social_meaning":["身份象征","实力标志"],"description_density":"medium","visibility_emphasis":"normal"},"not_guaranteed":["宝物必然被抢夺","物品必然有灵性"]} | 按项目已定的仙侠依据核对实际角色，原文物品语义留待核对。
22158 | blocked | ADAPT_B_00023 | GENRE_DUSHI | entity_type | CHARACTER | null | expression_preference | {"parameters":{"appearance_preference":["现代风格","品牌","实用"],"function_emphasis":["效率","金钱价值","社会身份"],"ownership_emphasis":"个人购买","social_meaning":["经济地位","品味"],"description_density":"medium","visibility_emphasis":"normal"},"not_guaranteed":["物品必然是品牌货","物品必然展现贫富差距"]} | 按项目已定的都市依据核对实际角色，原文物品语义留待核对。
22216 | blocked | ADAPT_B_00024 | GENRE_MORI | entity_type | CHARACTER | null | expression_preference | {"parameters":{"appearance_preference":["破旧","实用","稀缺"],"function_emphasis":["生存必需","耐久性","便携性"],"ownership_emphasis":"临时占有","social_meaning":["生存筹码","交换媒介"],"description_density":"medium","visibility_emphasis":"normal"},"not_guaranteed":["物品必然被争夺","物品必然导致冲突"]} | 按项目明确采用的原末日类型范围核对实际角色，原文物品语义留待核对。
22274 | blocked | ADAPT_B_00025 | GENRE_KEHUAN | entity_type | CHARACTER | null | expression_preference | {"parameters":{"appearance_preference":["高科技外观","极简","流线型"],"function_emphasis":["多功能","智能化","科技层级"],"ownership_emphasis":"技术获得","social_meaning":["技术水平","文明等级"],"description_density":"medium","visibility_emphasis":"normal"},"not_guaranteed":["科技物品必然失控","科技物品必然是武器"]} | 按项目已定的科幻依据核对实际角色，原文物品语义留待核对。

【《类型系统》类型多样性策略的维度｜人物设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

32963｜reference｜{"id":"identity","name":"身份维度","weight":0.05}
【本步用法】用已确认人物身份及其权限、经历分析可呈现的差异，沿用原身份和公开范围。

【《类型系统》类型多样性策略的边界｜人物设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】在现有步骤核对候选的适用边界，并对照作者已确认的设定和前置产物。

33038｜"违反人物身份"
【本步用法】比较人物变体时以已确认身份、权限和可公开内容为边界。

33039｜"违反人物性格"
【本步用法】用已建立性格和可回查的行为依据核对备选人物表现。

【《类型系统》类型适配冲突规则｜人物设计】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38273｜reference｜{"conflict_rule_id":"CONFLICT_B_004","rule_name":"类型和人物身份之间不合理覆盖","category":"type_identity_conflict","description":"当类型适配试图覆盖人物既有的身份设置时检测","input_fields":["type_id","character_id","identity_fields"],"warning_condition":"类型适配试图修改人物已有身份属性","fail_condition":"类型适配成功覆盖人物身份","severity":"fail","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】对照已确认的人物身份、职责与知情范围，报告适配涉及的原身份字段及实际覆盖证据。
"""
