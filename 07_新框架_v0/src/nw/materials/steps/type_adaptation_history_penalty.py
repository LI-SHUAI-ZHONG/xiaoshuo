"""类型适配步骤中的历史使用惩罚原文及用法。"""

MATERIAL = r"""
【《类型系统》历史使用惩罚规则.json｜SOURCE[57]｜原文第 468,532 行】
【原文规则字段】
{
  "rule_id": "HISTORY_PENALTY_RULES_V1",
  "version": "1.0",
  "created_at": "2026-07-31 11:55:45",
  "record_fields": [
    "project_id",
    "chapter_id",
    "scene_id",
    "used_combination_id",
    "used_type_ids",
    "used_concept_ids",
    "used_event_type_ids",
    "used_style_ids",
    "used_dynamic_rule_ids",
    "used_at",
    "usage_count",
    "last_used_at",
    "similarity_to_current",
    "penalty_score"
  ],
  "penalty_calculation": {
    "base_penalty": 0.05,
    "max_penalty": 0.5,
    "decay_factor": 0.1,
    "decay_period_days": 7,
    "method": "base_penalty * usage_count * exp(-decay_factor * days_since_last_use)"
  },
  "constraints": [
    "不能删除历史记录",
    "不能把历史记录当作原始资料",
    "历史记录必须与正式项目数据隔离",
    "历史惩罚只影响排序和选择，不删除组合",
    "同一项目内重复使用惩罚权重更高"
  ]
}
【本步用法】已有独立使用记录和可比较的类型组合时，按下列字段核对重复使用的证据。排序须先满足作者已确认的类型、机制和用途。当前裁定为 reference，原附运行层为空，计算式各待核处沿用台账。没有可核记录时，把依据缺口记入本步 boundaries，候选继续按已经成立的条件比较。
【记录字段用法】
project_id 核对记录所属项目，用于区分本项目和其他项目。
chapter_id 核对采用发生在哪一章，以实际引用作证。
scene_id 核对采用发生在哪一场，和章坐标一并检查。
used_combination_id 核对实际采用的组合 ID，预选和实际采用使用各自的记录。
used_type_ids 核对采用时留下的类型 ID，与当前作者已选类型分开看。
used_concept_ids 核对实际用到的概念 ID，明确哪个已用概念和本次用途可比较。
used_event_type_ids 仅用当时实际记录的事件类型核对重复情况。
used_style_ids 核对当时实际记录的写法，当前风格以作者此项目已确认的内容为据。
used_dynamic_rule_ids 核对实际采用的动态规则 ID，组合所列候选字段和独立的使用记录须各有依据。
used_at 核对一次采用的记录时间和对应章场。
usage_count 核对已留存的采用次数及其统计范围。
last_used_at 核对最近一次采用的时间来源，确认和次数属于同一统计范围。
similarity_to_current 有现成取值及其依据时用于查阅相似性记录，原计算式未定义其计分作用。
penalty_score 只核对在已有历史记录中已经可回查的分值和依据。
【计算字段用法】
base_penalty 对照原值 0.05 核查已有计分依据。
max_penalty 对照原值 0.5 核查已提供的封顶口径，原式未列封顶操作。
decay_factor 对照原值 0.1 核查已提供的衰减依据。
decay_period_days 保留原值 7 天，原式未写这个字段如何参与。
method 将已有计算记录与原式、实际次数和最近使用时间对照，天数口径、封顶和同项目权重待核时保留为缺项。
【约束用法】
保存独立历史记录及章场出处，供回查实际采用。
把使用历史当作排序证据，正式素材来源按原版和现行资格核对。
核对使用历史与正式项目产物各自的来源，按原文保存隔离要求。
重复情况只用于有依据的排序或选择说明，保留组合原值和资格。
同一项目内使用从项目 ID 和章场记录核对，原作者未给的权重数值留待确认。
""".strip()
