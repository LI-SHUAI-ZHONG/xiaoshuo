"""类型适配中的概念条件和非保证边界的《类型系统》原文。"""

MATERIAL = r"""#### 类型适配中的概念条件和非保证边界
【类型系统原文位置】类型表达适配总表.json 第20889行
【各条共用原文值】{"priority":0,"weight":0,"source_refs":[],"evidence_type":"template","confidence":999,"status":"active","schema_version":"TYPE_B-1.0.0"}
【本步使用条件】
本步沿用已选类型、已激活的项目概念及作者实际需求。原表 type_id 和 target_id 用于核对来源对象。用 adaptations 记录实际适配参数、limits 或 boundaries 记录非保证边界。已确认需要改变关注重点且有实际激活概念时，沿用现有 focuses。表达数值缺少量尺，采用范围依作者确认。
原始 confidence=999 按原值保留。design_ready 条目沿用现有资格及有效字段，按作者实际需要选用。blocked 条目用于核对待核字段及影响，项目参数沿用已确认的依据。GENRE_MORI 依项目已确认的原 ID 核对。
【逐条原文值】adaptation_id 原文行 | 现有资料裁定 | adaptation_id | type_id | target_kind | target_id | target_scope | adaptation_kind | 本步原字段 | 本步用法
20897 | design_ready | ADAPT_B_00001 | GENRE_XIANXIA | concept | NEED_FOOD | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["角色必然吃灵食","食物必然与修炼绑定"]} | 把已经明确的食物需求落到修炼用度或宗门供给这一关注点。
20960 | design_ready | ADAPT_B_00002 | GENRE_XIANXIA | concept | FATIGUE | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["疲惫必然导致闭关","疲惫必然是灵力枯竭"]} | 按已知疲惫原因核对要强调的问题和现有恢复途径。
21019 | design_ready | ADAPT_B_00003 | GENRE_XIANXIA | concept | FEAR | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["恐惧必然导致逃跑","恐惧必然导致突破"]} | 根据已定威胁区分本场关注的惧怕和可感的危险。
21077 | design_ready | ADAPT_B_00004 | GENRE_XIANXIA | concept | ANGER | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["愤怒必然导致战斗","愤怒必然导致杀人"]} | 用既有冲突核对愤怒所针对的对象和变化。
21135 | design_ready | ADAPT_B_00005 | GENRE_XIANXIA | concept | JOY | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["快乐必然导致突破"]} | 在已有进展中核对喜悦所来自的结果。
21190 | design_ready | ADAPT_B_00006 | GENRE_XIANXIA | concept | DESIRE | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["欲望必然导致堕落","欲望必然导致入魔"]} | 沿已确认的人物目标核对其欲望和取舍。
21247 | design_ready | ADAPT_B_00007 | GENRE_XIANXIA | concept | IDENTITY_HIDDEN | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["隐藏身份必然被揭穿","隐藏身份必然成为反转"]} | 按已确认的隐匿目标与可见身份核对所需关注。
21300 | design_ready | ADAPT_B_00008 | GENRE_DUSHI | concept | NEED_FOOD | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["角色必然点外卖","食物短缺必然导致剧情"]} | 按当前食物需要核对现实场合、获取方式或钱款的实际作用。
21364 | design_ready | ADAPT_B_00009 | GENRE_DUSHI | concept | FATIGUE | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["疲惫必然是加班造成"]} | 按实际疲惫来源和手头可用条件记录当前关注。
21423 | design_ready | ADAPT_B_00010 | GENRE_DUSHI | concept | FEAR | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["恐惧必然导致报警","恐惧必然导致逃跑"]} | 核对现实威胁和人物担心的后果，记录尚待弄清的信息。
21485 | design_ready | ADAPT_B_00011 | GENRE_DUSHI | concept | ANGER | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["愤怒必然导致暴力","愤怒必然导致决裂"]} | 沿已经明确的利害或关系核对愤怒的触发。
21543 | design_ready | ADAPT_B_00012 | GENRE_DUSHI | concept | JOY | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["快乐必然持续","快乐必然是简单获得"]} | 核对已发生或本场已设计的结果与人物喜悦。
21599 | design_ready | ADAPT_B_00013 | GENRE_DUSHI | concept | IDENTITY_HIDDEN | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["隐藏身份必然被揭露","隐藏身份必然是坏人"]} | 核对已有公开身份、隐匿身份及本场披露边界。
21652 | design_ready | ADAPT_B_00014 | GENRE_MORI | concept | NEED_FOOD | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["食物短缺必然导致死亡","搜寻必然找到食物"]} | 依已经确定的食物不足、地点和物资核对当前求取目标。
21719 | design_ready | ADAPT_B_00015 | GENRE_MORI | concept | FATIGUE | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["疲惫必然导致死亡","疲惫必然导致被袭击"]} | 按已定伤病、警戒或休息情况核对疲惫原因与约束。
21776 | design_ready | ADAPT_B_00016 | GENRE_MORI | concept | FEAR | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["恐惧必然导致逃跑","恐惧必然导致背叛"]} | 按已定危险情势核对人物为何恐惧及知道哪些信息。
21833 | design_ready | ADAPT_B_00017 | GENRE_MORI | concept | ANGER | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["愤怒必然导致暴力","愤怒必然导致杀人"]} | 核对已有争夺、背叛或秩序压力与人物愤怒的因果。
21887 | design_ready | ADAPT_B_00018 | GENRE_KEHUAN | concept | NEED_FOOD | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["食物必然是合成品"]} | 核对世界已设定的食物来源与本场需要。
21941 | design_ready | ADAPT_B_00019 | GENRE_KEHUAN | concept | FATIGUE | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["疲劳必然是科技副作用"]} | 确认本场疲惫与已有科技或环境条件的关系。
21993 | blocked | ADAPT_B_00020 | GENRE_XUANYI | concept | FEAR | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["恐惧必然源于凶手","恐惧是真实威胁"]} | 核对原文关联的恐惧与威胁信息，登记来源受阻及真实性待核。
22050 | design_ready | ADAPT_B_00021 | GENRE_XUANYI | concept | JOY | null | expression_preference | {"parameters":{"expression_weight":0.5},"not_guaranteed":["快乐必然是结局"]} | 核对已经确定的揭示、解除危险或结果与人物喜悦。
"""
