"""表达设计步骤的《类型系统》层级、报告或条件原文。"""

MATERIAL = r"""#### 表达设计核对的动态触发条件
【类型系统原文位置】类型动态触发条件.json 第27171行
【各条共用原文值】{"expected_value":null,"source_id":null,"required":true,"negatable":true,"failure_behavior":"report_and_skip","status":"active"}
【本步用法】逐条保留 reference 身份，只有项目实际采用所属 rule_id 时才从已具备的前置核对。依该父规则内 evaluation_order 检查实际对象与原条件。比较值或证据缺失时记录待核，原 failure_behavior 为 report_and_skip，已成立的候选仍沿用本步现有验证和选择条件。
【逐条原文值】condition_id 原文行 | condition_id | rule_id | condition_kind | field | operator | evaluation_order | source_refs | evidence_type | confidence | 本步核对
27710 | TDC_0030 | TDR_018 | entity_present | entity_id | exists | 0 | ["类型表达适配总表.json"] | template | 0.6 | 按本场真实在场人物、已定刺激及所选反应核对可见表现。

【《类型系统》类型多样性策略的维度｜表达设计】
【原文位置】来源块第 32,920 行。每项前缀为对应字段的物理原件行。
【本步用法】沿用作者已确认的条件，比较当前步骤实际已有的适用候选。权重保留原值，具体比较依据采用本次已明确的范围。

33013｜reference｜{"id":"expression","name":"语言表达维度","weight":0.04}
【本步用法】在场景目标和人物说话方式已定时，比较符合实际视角的措辞、对白或动作呈现。

33018｜reference｜{"id":"visual","name":"视觉呈现维度","weight":0.03}
【本步用法】围绕选定对象和动作比较读者能看到的细节、出现位置及视觉侧重。

【《类型系统》类型适配冲突规则｜表达设计】
【原文位置】来源块第 38,207 行。条目前缀指原件字段行。
【本步用法】按实际采用的项目条件和本步产物核对下列冲突。原记录为 report_only=true、auto_fix_allowed=false，按原警告及失败条件保留说明和可复核证据。

38254｜reference｜{"conflict_rule_id":"CONFLICT_B_003","rule_name":"风格和人物性格之间表达冲突","category":"style_character_conflict","description":"当风格表达参数与人物已有性格不一致时检测","input_fields":["style_id","character_id","personality_traits"],"warning_condition":"风格要求抑制情绪但人物性格偏向情绪外露","fail_condition":"风格覆盖人物性格","severity":"fail","auto_fix_allowed":false,"report_only":true,"source_refs":[],"evidence_type":"template","status":"active"}
【本步用法】用人物已形成的性格和本场表达证据核对风格参数对角色表现的影响，定位实际覆盖或相反的地方。

【《类型系统》类型验证规则｜表达设计】
【原文位置】来源块第 40,879 行。条目前缀为 ID 字段的物理原件行。
【本步用法】按本步实际对象及证据核对适用的原验收项。涉及旧阶段 A、备份、文件清单或原测试的条目，按相应阶段和资料维护范围核对已有记录。

40986｜reference｜{"test_id":"TA21","test":"类型不会强制推出固定情绪表达","check":"no_forced_emotion"}
【本步用法】依本场已确定的触发、角色状态和视角证据核对情绪表现是否有实际依据。
"""
