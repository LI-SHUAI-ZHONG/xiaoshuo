"""场景设计中的出现位置及披露候选的《类型系统》原文。"""

MATERIAL = """#### 场景设计中的出现位置及披露候选
【类型系统原文位置】类型表达适配总表.json 第20889行
【各条共用原文值】{"priority":0,"weight":0,"source_refs":[],"evidence_type":"template","confidence":999,"status":"active","schema_version":"TYPE_B-1.0.0"}
【本步使用条件】
沿用上游剧情、事件、动作和已有关联对象。现有章场产物中核对地点、参与人物与 allowed_disclosure，按视角可见、人物已知及作者范围使用原字段。
原始 confidence=999 按原值保留。design_ready 条目沿用现有资格及有效字段，按作者实际需要选用。blocked 条目用于核对待核字段及影响，项目参数沿用已确认的依据。GENRE_MORI 依项目已确认的原 ID 核对。
【逐条原文值】adaptation_id 原文行 | 现有资料裁定 | adaptation_id | type_id | target_kind | target_id | target_scope | adaptation_kind | 本步原字段 | 本步用法
20897 | design_ready | ADAPT_B_00001 | GENRE_XIANXIA | concept | NEED_FOOD | null | expression_preference | {"candidate_scene_uses":["宗门膳堂","丹药阁","灵田"],"not_guaranteed":["角色必然吃灵食","食物必然与修炼绑定"]} | 在实际已有的膳堂、丹药阁或灵田中核对哪个场所符合场景目标。
21247 | design_ready | ADAPT_B_00007 | GENRE_XIANXIA | concept | IDENTITY_HIDDEN | null | expression_preference | {"candidate_information_patterns":["identity","capability"],"not_guaranteed":["隐藏身份必然被揭穿","隐藏身份必然成为反转"]} | 核对修为或身份能否被当前视角知晓，按已有披露安排处理。
21300 | design_ready | ADAPT_B_00008 | GENRE_DUSHI | concept | NEED_FOOD | null | expression_preference | {"candidate_scene_uses":["餐厅","便利店","办公室"],"not_guaranteed":["角色必然点外卖","食物短缺必然导致剧情"]} | 按事件发生地点和场景功能核对餐厅、便利店或办公室候选。
21423 | design_ready | ADAPT_B_00010 | GENRE_DUSHI | concept | FEAR | null | expression_preference | {"candidate_information_patterns":["threat","weakness"],"not_guaranteed":["恐惧必然导致报警","恐惧必然导致逃跑"]} | 依本场前态和视角区分角色实际知晓的威胁与弱点。
21485 | design_ready | ADAPT_B_00011 | GENRE_DUSHI | concept | ANGER | null | expression_preference | {"candidate_information_patterns":["relationship"],"not_guaranteed":["愤怒必然导致暴力","愤怒必然导致决裂"]} | 用已有利害和知情边界核对哪部分关系信息可以披露。
21599 | design_ready | ADAPT_B_00013 | GENRE_DUSHI | concept | IDENTITY_HIDDEN | null | expression_preference | {"candidate_information_patterns":["identity","secret"],"not_guaranteed":["隐藏身份必然被揭露","隐藏身份必然是坏人"]} | 按照已定公开身份与隐匿信息核对披露范围。
21652 | design_ready | ADAPT_B_00014 | GENRE_MORI | concept | NEED_FOOD | null | expression_preference | {"candidate_scene_uses":["废墟","避难所","补给站"],"not_guaranteed":["食物短缺必然导致死亡","搜寻必然找到食物"]} | 按已定路线与风险核对废墟、避难所或补给站的用途。
21776 | design_ready | ADAPT_B_00016 | GENRE_MORI | concept | FEAR | null | expression_preference | {"candidate_information_patterns":["danger","threat"],"not_guaranteed":["恐惧必然导致逃跑","恐惧必然导致背叛"]} | 用本场已设危险和预警来源核对视角知情。
21887 | design_ready | ADAPT_B_00018 | GENRE_KEHUAN | concept | NEED_FOOD | null | expression_preference | {"candidate_scene_uses":["太空站","实验室","合成车间"],"not_guaranteed":["食物必然是合成品"]} | 依既有空间与食物供给方式核对太空站、实验室或合成车间候选。
21993 | blocked | ADAPT_B_00020 | GENRE_XUANYI | concept | FEAR | null | expression_preference | {"candidate_information_patterns":["danger","false_information","secret"],"not_guaranteed":["恐惧必然源于凶手","恐惧是真实威胁"]} | 按原值核对危险、虚假信息及秘密的区别，来源仍受阻。
24060 | blocked | ADAPT_B_00057 | GENRE_XUANYI | information_type | null | all_information | information_reveal_preference | {"parameters":{"information_asymmetry":"high","viewpoint_restriction":"high"},"candidate_information_patterns":["clue","secret","false_information","motive","danger"],"not_guaranteed":["信息必然被揭示","信息必然是真实的"]} | 核对线索、秘密、虚假信息、动机和危险的拟披露边界，实际披露使用已定依据。
24109 | blocked | ADAPT_B_00058 | GENRE_DUSHI | information_type | null | all_information | information_reveal_preference | {"parameters":{"information_asymmetry":"medium","viewpoint_restriction":"low"},"candidate_information_patterns":["identity","resource","relationship","plan","opportunity"],"not_guaranteed":["信息必然被揭示","信息必然是真实的"]} | 核对身份、资源、关系、计划和机会在当前场景的已知范围。
24158 | blocked | ADAPT_B_00059 | GENRE_MORI | information_type | null | all_information | information_reveal_preference | {"parameters":{"information_asymmetry":"high","viewpoint_restriction":"high"},"candidate_information_patterns":["resource","danger","threat","location","weakness"],"not_guaranteed":["信息必然被揭示","信息必然是真实的"]} | 核对资源、危险、威胁、地点和弱点各自的实际持有者与可见范围。
24207 | blocked | ADAPT_B_00060 | GENRE_XIANXIA | information_type | null | all_information | information_reveal_preference | {"parameters":{"information_asymmetry":"high","viewpoint_restriction":"medium"},"candidate_information_patterns":["capability","secret","opportunity","history","rule"],"not_guaranteed":["信息必然被揭示","信息必然是真实的"]} | 核对能力、秘密、机会、历史和规则的已有披露前置。"""
