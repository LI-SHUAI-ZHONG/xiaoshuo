"""受众标签在当前步骤使用的《类型系统》原文。"""

MATERIAL = r"""#### 类型总表的受众标签
【类型系统原文位置】类型本体\类型总表.json 第3095行
【各条共用原文值】type_kind="AUDIENCE_TAG" | parent_id=null | level=1 | scope="读者体验"
【逐条原文值】type_id原文行 | type_id | canonical_name及display_name | definition | 本步用法
20381 | AUDIENCE_MALE | 男性向 | 以男性读者为主要目标 | 核对作者明确指定的男性目标读者范围。
20404 | AUDIENCE_FEMALE | 女性向 | 以女性读者为主要目标 | 核对作者明确指定的女性目标读者范围。
20427 | AUDIENCE_YOUTH | 青少年 | 以青少年读者为目标 | 核对作者明确的青少年受众及项目适龄范围。
20450 | AUDIENCE_ADULT | 成人 | 以成人读者为目标 | 核对作者明确的成人受众与项目内容边界。
20473 | AUDIENCE_ALL | 全年龄 | 适合所有年龄段读者 | 核对作者给定的全年龄定位与已知内容边界。
20496 | AUDIENCE_MAINSTREAM | 大众 | 面向大众读者 | 记录作者明确给出的大众读者定位。
20519 | AUDIENCE_NICHE | 小众 | 面向特定小众读者 | 记录作者指定的具体小众读者群及需求。
【本步使用条件】
按作者明确选定的目标读者和项目既有边界，使用实际选择的类型作 type_refs，在 adaptations 的 parameters、limits 或 boundaries 中记录已有受众要求。读者年龄、内容边界与文学效果依据作者和项目证据确认。"""
