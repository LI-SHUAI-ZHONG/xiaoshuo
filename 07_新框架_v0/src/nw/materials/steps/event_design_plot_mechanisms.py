"""事件设计步骤直接使用的《类型系统》剧情机制原文。"""

MATERIAL = r"""#### 事件设计使用的触发与后继事件机制
【类型系统原文位置】类型本体\类型总表.json 第3095行
【各条共用原文值】type_kind="PLOT_MECHANISM" | parent_id=null | level=1 | scope="剧情机制"
【逐条原文值】type_id原文行 | type_id | canonical_name及display_name | definition | 本步用法
18679 | PLOT_MECHANISM_DUNGEON | 副本机制 | 主角挑战副本获得奖励 | 沿已有副本目标与前事件，细化挑战候选及满足任务条件后的候选奖励。
18725 | PLOT_MECHANISM_CONTAMINATION | 污染机制 | 主角面对污染和异变 | 根据作品已有异常设定写人物遇到污染或异变的条件事件与可见后果。
18909 | PLOT_MECHANISM_ALIEN | 外星文明机制 | 主角与外星文明接触 | 用作品已定的外星文明和前序剧情细化接触的参加者、条件及候选后果。
18978 | PLOT_MECHANISM_DISASTER | 灾难机制 | 主角面对灾难事件 | 用项目已定的灾难条件写候选遭遇，说明受影响的人物和可能后果。
19001 | PLOT_MECHANISM_BIOCHEMICAL | 生化机制 | 主角面对生化危机 | 沿用作品已定的虚构危机条件，细化人物如何遭遇危机及可观察的情节后果。
19231 | PLOT_MECHANISM_MAIN_GOD | 主神空间机制 | 主角在主神空间中完成任务 | 以已定主神空间和上游任务目标细化任务候选与可观察的完成条件。
19300 | PLOT_MECHANISM_RULE_TASK | 规则任务机制 | 主角在规则限制下完成任务 | 按已有规则和前置事件细化下一项任务候选及可判断的完成条件。
【本步使用条件】
依据已有剧情节点、人物、世界规则和作者采用的机制细化后继事件。candidates 保留实际上游节点及原 completion_condition，把本事件的参加者、触发与可能后果写清楚。事件保持条件候选。"""
