"""事件设计中的候选权重的《类型系统》原文。"""

MATERIAL = """#### 事件设计中的候选权重
【类型系统原文位置】类型表达适配总表.json 第20889行
【各条共用原文值】{"priority":0,"weight":0,"source_refs":[],"evidence_type":"template","confidence":999,"status":"active","schema_version":"TYPE_B-1.0.0"}
【本步使用条件】
依据已定人物、世界和上游事件节点细化候选。候选必须沿用前事件的真实完成条件；原权重及其顺序当前供待核对照，采用的权重单位、取舍和基准须有项目已确认的依据。
原始 confidence=999 按原值保留。design_ready 条目沿用现有资格及有效字段，按作者实际需要选用。blocked 条目用于核对待核字段及影响，项目参数沿用已确认的依据。GENRE_MORI 依项目已确认的原 ID 核对。
【逐条原文值】adaptation_id 原文行 | 现有资料裁定 | adaptation_id | type_id | target_kind | target_id | target_scope | adaptation_kind | 本步原字段 | 本步用法
23492 | blocked | ADAPT_B_00046 | GENRE_XIANXIA | event_type | null | all_events | expression_weight | {"parameters":{"scene_frequency_weight":0.5,"pacing_weight":0.5,"reveal_weight":0.5,"conflict_weight":0.7,"social_weight":0.5,"resource_weight":0.5,"identity_weight":0.6,"consequence_weight":0.5,"foreshadowing_weight":0.5},"not_guaranteed":["权重参数不等于事件必然发生","事件权重不等于质量"]} | 核对候选事件中的冲突和身份作用，参照已定上游完成条件。
23542 | blocked | ADAPT_B_00047 | GENRE_DUSHI | event_type | null | all_events | expression_weight | {"parameters":{"scene_frequency_weight":0.5,"pacing_weight":0.5,"reveal_weight":0.5,"conflict_weight":0.5,"social_weight":0.7,"resource_weight":0.6,"identity_weight":0.5,"consequence_weight":0.5,"foreshadowing_weight":0.5},"not_guaranteed":["权重参数不等于事件必然发生","事件权重不等于质量"]} | 核对候选事件的社会和资源作用，依实际人物和条件处理。
23592 | blocked | ADAPT_B_00048 | GENRE_MORI | event_type | null | all_events | expression_weight | {"parameters":{"scene_frequency_weight":0.5,"pacing_weight":0.5,"reveal_weight":0.5,"conflict_weight":0.8,"social_weight":0.5,"resource_weight":0.9,"identity_weight":0.5,"consequence_weight":0.8,"foreshadowing_weight":0.5},"not_guaranteed":["权重参数不等于事件必然发生","事件权重不等于质量"]} | 核对已有资源压力、冲突和后果，按真实事件前置安排。
23642 | blocked | ADAPT_B_00049 | GENRE_KEHUAN | event_type | null | all_events | expression_weight | {"parameters":{"scene_frequency_weight":0.5,"pacing_weight":0.5,"reveal_weight":0.7,"conflict_weight":0.5,"social_weight":0.5,"resource_weight":0.5,"identity_weight":0.5,"consequence_weight":0.6,"foreshadowing_weight":0.5},"not_guaranteed":["权重参数不等于事件必然发生","事件权重不等于质量"]} | 核对既定科技背景下已设的揭示与后果，使用实际上游条件。
23692 | blocked | ADAPT_B_00050 | GENRE_XUANYI | event_type | null | all_events | expression_weight | {"parameters":{"scene_frequency_weight":0.5,"pacing_weight":0.5,"reveal_weight":0.9,"conflict_weight":0.6,"social_weight":0.5,"resource_weight":0.5,"identity_weight":0.5,"consequence_weight":0.5,"foreshadowing_weight":0.8},"not_guaranteed":["权重参数不等于事件必然发生","事件权重不等于质量"]} | 核对既定悬疑事件的揭示和铺垫，依前事件完成条件安排。"""
