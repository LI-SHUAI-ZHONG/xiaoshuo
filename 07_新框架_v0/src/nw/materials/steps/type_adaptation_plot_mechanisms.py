"""类型适配步骤直接使用的《类型系统》剧情机制原文。"""

MATERIAL = r"""#### 类型适配使用的项目时间与转生机制
【类型系统原文位置】类型本体\类型总表.json 第3095行
【各条共用原文值】type_kind="PLOT_MECHANISM" | parent_id=null | level=1 | scope="剧情机制"
【逐条原文值】type_id原文行 | type_id | canonical_name及display_name | definition | 本步用法
18058 | PLOT_MECHANISM_REBIRTH | 重生机制 | 主角重生回到过去，利用先知优势 | 记录已定的重生时点与人物保有的先知范围，供下游核对实际可用信息。
18081 | PLOT_MECHANISM_TRANSMIGRATION | 穿越机制 | 主角穿越到异世界或历史时期 | 记录作者确认的原环境与穿越去向，具体是异世界还是历史时期依项目设定。
18771 | PLOT_MECHANISM_TIME_TRAVEL | 时间旅行机制 | 主角穿越时间 | 按作者给定的时间起点和去向记录适配参数，未明确的前后关系留待确认。
19185 | PLOT_MECHANISM_LOOP | 循环机制 | 主角经历时间循环 | 记录作者已定的时间循环范围、起止条件及角色记忆的待核项。
19254 | PLOT_MECHANISM_REINCARNATION | 轮回机制 | 主角经历轮回转世 | 按作者明确的轮回转世范围记录前后身份及既有约束。
【本步使用条件】
按作者已经确认的机制和现有类型核对。用 adaptations.type_refs 引用实际选型，parameters 写项目确认的起点、终点或反复条件，limits 及 boundaries 写项目限制和待核事项。适配依据来自作者独立确认的机制。"""
