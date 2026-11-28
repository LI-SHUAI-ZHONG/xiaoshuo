"""剧情设计中作者选用的创作路径参数原文。"""

MATERIAL = r"""#### 商业爆款路径的创作与节奏参数
【类型系统原文位置】创作路径\商业爆款路径.json 第297行
【原文字段】第303–304行
  "path_id": "PATH_B",
  "path_name": "商业爆款生产路径",
【原文字段】第307–405行
  "creation_goals": [
    "开篇抓力",
    "首章目标",
    "首章冲突",
    "首章信息差",
    "首章异常",
    "首章承诺",
    "章节末钩子",
    "事件密度",
    "冲突频率",
    "目标清晰度",
    "角色欲望强度",
    "读者期待",
    "延迟满足",
    "阶段性爽点",
    "反差",
    "身份揭示",
    "能力展示",
    "资源逆转",
    "关系逆转",
    "证据揭露",
    "伏笔回收",
    "cliffhanger",
    "留存风险",
    "市场定位",
    "批量生产可复用结构",
    "相似度惩罚",
    "原创性风险"
  ],
  "retrieval_weights": {
    "opening_hook_weight": 0.9,
    "chapter_hook_weight": 0.9,
    "event_density_weight": 0.85,
    "conflict_frequency_weight": 0.85,
    "satisfaction_frequency_weight": 0.85,
    "reader_retention_weight": 0.9,
    "market_fit_weight": 0.85,
    "production_speed_weight": 0.8,
    "character_depth_weight": 0.4
  },
  "rhythm_parameters": {
    "event_density": 0.85,
    "conflict_frequency": 0.85,
    "information_reveal_frequency": 0.8,
    "satisfaction_frequency": 0.85,
    "contrast_frequency": 0.8,
    "identity_reveal_frequency": 0.75,
    "cliffhanger_frequency": 0.85,
    "scene_state_update_limit": 12
  },
  "opening_parameters": {
    "opening_hook_weight": 0.9,
    "first_scene_conflict_weight": 0.9,
    "first_chapter_promise_weight": 0.9,
    "first_chapter_information_gap_weight": 0.85,
    "first_chapter_anomaly_weight": 0.85,
    "first_chapter_goal_weight": 0.85
  },
  "hook_parameters": {
    "chapter_hook_weight": 0.9,
    "chapter_end_hook_weight": 0.9,
    "cliffhanger_frequency": 0.85,
    "first_three_chapters_progression_weight": 0.85,
    "first_ten_chapters_hook_weight": 0.85
  },
  "conflict_parameters": {
    "first_scene_conflict_weight": 0.9,
    "conflict_frequency": 0.85,
    "conflict_escalation_weight": 0.85,
    "antagonist_pressure_weight": 0.8,
    "goal_clarity_weight": 0.85,
    "character_desire_intensity_weight": 0.85
  },
  "satisfaction_parameters": {
    "short_term_payoff_weight": 0.85,
    "long_term_payoff_weight": 0.7,
    "satisfaction_frequency": 0.85,
    "delayed_gratification_weight": 0.7,
    "stage_satisfaction_weight": 0.85,
    "contrast_frequency": 0.8,
    "identity_reveal_frequency": 0.75,
    "ability_display_frequency": 0.8,
    "resource_reversal_weight": 0.8,
    "relationship_reversal_weight": 0.8,
    "evidence_reveal_frequency": 0.75
  },
  "character_depth_parameters": {
    "character_depth_minimum": 0.4,
    "character_desire_intensity_weight": 0.85,
    "character_goal_clarity_weight": 0.85,
    "character_flatness_penalty": 0.8
  },
  "commercial_risk_parameters": {
    "reader_retention_weight": 0.9,
    "market_fit_weight": 0.85,
    "production_speed_weight": 0.8,
    "commercial_risk_limit": 0.7,
    "retention_risk_weight": 0.85
  },
【原文字段】第415–439行
  "parameters": {
    "opening_hook_weight": 0.9,
    "first_scene_conflict_weight": 0.9,
    "first_chapter_promise_weight": 0.9,
    "chapter_hook_weight": 0.9,
    "event_density": 0.85,
    "conflict_frequency": 0.85,
    "information_reveal_frequency": 0.8,
    "satisfaction_frequency": 0.85,
    "contrast_frequency": 0.8,
    "identity_reveal_frequency": 0.75,
    "resource_reversal_weight": 0.8,
    "relationship_reversal_weight": 0.8,
    "cliffhanger_frequency": 0.85,
    "short_term_payoff_weight": 0.85,
    "long_term_payoff_weight": 0.7,
    "character_depth_minimum": 0.4,
    "worldbuilding_minimum": 0.4,
    "originality_weight": 0.7,
    "similarity_penalty": 0.85,
    "production_speed_weight": 0.8,
    "repetition_penalty": 0.85,
    "reader_retention_weight": 0.9,
    "commercial_risk_limit": 0.7
  },
【本步用法】
作者已明确采用此路径时，在实际开篇、章任务、事件及承诺中选用有直接作用的指标。数值作为原配置参数供核对，实际取材、状态更新、篇幅和读者验收依现有流程与作者范围。

#### 原创深度路径的创作与节奏参数
【类型系统原文位置】创作路径\原创深度路径.json 第540行
【原文字段】第546–547行
  "path_id": "PATH_A",
  "path_name": "原创深度创作路径",
【原文字段】第550–626行
  "creation_goals": [
    "人物复杂性",
    "长期成长",
    "世界观深度",
    "道德和价值冲突",
    "关系变化",
    "信息层次",
    "伏笔回收",
    "主题表达",
    "长期读者留存",
    "原创性",
    "情绪余波",
    "多线因果",
    "角色选择和代价"
  ],
  "retrieval_weights": {
    "character_depth_weight": 0.9,
    "worldbuilding_weight": 0.8,
    "theme_weight": 0.85,
    "moral_conflict_weight": 0.8,
    "relationship_depth_weight": 0.85,
    "plot_complexity_weight": 0.8,
    "foreshadowing_weight": 0.85,
    "novelty_weight": 0.9,
    "commercial_pressure_weight": 0.2
  },
  "rhythm_parameters": {
    "slow_burn_allowed": true,
    "delayed_payoff_weight": 0.85,
    "action_density": 0.3,
    "dialogue_density": 0.5,
    "psychological_density": 0.8,
    "scene_state_update_limit": 12
  },
  "opening_parameters": {
    "opening_hook_weight": 0.6,
    "opening_character_intro_weight": 0.8,
    "opening_world_intro_weight": 0.7,
    "opening_theme_intro_weight": 0.7,
    "opening_promise_weight": 0.6
  },
  "hook_parameters": {
    "chapter_hook_weight": 0.5,
    "long_arc_hook_weight": 0.85,
    "foreshadowing_hook_weight": 0.85,
    "character_mystery_hook_weight": 0.8,
    "world_mystery_hook_weight": 0.75
  },
  "conflict_parameters": {
    "moral_conflict_weight": 0.85,
    "value_conflict_weight": 0.85,
    "relationship_conflict_weight": 0.8,
    "internal_conflict_weight": 0.8,
    "external_conflict_weight": 0.5,
    "conflict_escalation_weight": 0.7
  },
  "satisfaction_parameters": {
    "delayed_payoff_weight": 0.85,
    "emotional_aftermath_weight": 0.85,
    "character_growth_payoff_weight": 0.85,
    "theme_payoff_weight": 0.8,
    "short_term_satisfaction_weight": 0.3
  },
  "character_depth_parameters": {
    "character_complexity_weight": 0.9,
    "character_growth_weight": 0.9,
    "character_choice_weight": 0.9,
    "character_cost_weight": 0.85,
    "character_relationship_change_weight": 0.85,
    "character_moral_ambiguity_weight": 0.8
  },
  "commercial_risk_parameters": {
    "commercial_pressure_weight": 0.2,
    "reader_retention_weight": 0.5,
    "market_fit_weight": 0.3,
    "production_speed_weight": 0.2
  },
【原文字段】第635–654行
  "parameters": {
    "opening_hook_weight": 0.6,
    "character_depth_weight": 0.9,
    "worldbuilding_weight": 0.8,
    "theme_weight": 0.85,
    "moral_conflict_weight": 0.85,
    "relationship_depth_weight": 0.85,
    "plot_complexity_weight": 0.8,
    "slow_burn_allowed": true,
    "delayed_payoff_weight": 0.85,
    "foreshadowing_weight": 0.85,
    "action_density": 0.3,
    "dialogue_density": 0.5,
    "psychological_density": 0.8,
    "novelty_weight": 0.9,
    "repetition_penalty": 0.85,
    "originality_weight": 0.9,
    "commercial_pressure_weight": 0.2,
    "scene_state_update_limit": 12
  },
【本步用法】
作者已明确采用此路径时，以人物变化、主题、世界与多线因果确定实际章场和伏笔任务。原文权重和密度只在所用参数及其口径已明确时使用。"""
