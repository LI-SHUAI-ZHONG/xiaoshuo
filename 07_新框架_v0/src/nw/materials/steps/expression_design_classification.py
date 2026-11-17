"""表达设计中的风格基调与叙事速度原文。"""

MATERIAL = r"""【按当前已选风格和章场任务确定文字表现】
使用实际视角、事件和作者已定的表达边界，给本场具体的 observable 与 check。

### 124.5_按风格与基调分类
【原文位置】板块124.5 原件夹入条目 第138453行
**定义**：故事的情感质地。\*\*正剧\*\*：严肃、有深度、有社会意义。
\*\*喜剧\*\*：幽默、轻松、结局好。
\*\*悲剧\*\*：沉重、结局不好、让人思考。
\*\*悲喜剧\*\*：悲喜交织。
\*\*黑色幽默\*\*：在悲剧中带着荒诞的幽默。
\*\*荒诞\*\*：不合逻辑但有
【本步用法】
根据本场承担的风格或基调表现动作、措辞和情绪。荒诞项的尾句不全。

### 124.11_按叙事速度分类
【原文位置】板块124.11 原件夹入条目 第138623行
**定义**：故事的节奏形态。\*\*史诗型小说\*\*：跨度大，速度慢。
\*\*日常型小说\*\*：节奏平缓，生活化。
\*\*紧凑型小说\*\*：节奏快，事件密集。
\*\*舒缓型小说\*\*：节奏慢，注重氛围。
\*\*节奏交替型小说\*\*：快慢交替。
【本步用法】
用实际事件密度和已定篇幅表达快慢及转接。已采用的章级策略沿用本项目实际安排。

#### STYLE_LANGUAGE 语言风格
【类型系统原文位置】风格.json 第1127行
【原文字段】第1134–1146行
      "style_id": "STYLE_LANGUAGE",
      "canonical_name": "语言风格",
      "definition": "控制句式倾向和语言精度的风格维度",
      "tendency_dimensions": [
        "句式长短倾向",
        "词汇丰富度",
        "修辞频率"
      ],
      "not_overrides": [
        "通用概念",
        "角色性格",
        "世界观规则"
      ],
【本步用法】
按作者明确采用的语言风格，用当前场景和叙述者安排实际句式、词汇与修辞，并保留已定人物和世界规则。

#### 风格适配的可选维度与共同约束
【类型系统原文位置】风格表达适配.json 第1414行
【原文字段】第1419–1454行
  "description": "风格维度的表达适配参数",
  "total": 11,
  "style_dimensions": [
    "language_complexity",
    "sentence_length",
    "dialogue_ratio",
    "description_ratio",
    "internal_monologue_ratio",
    "action_detail_density",
    "sensory_detail_density",
    "psychological_detail_density",
    "environment_detail_density",
    "humor_density",
    "metaphor_density",
    "realism_level",
    "darkness_level",
    "emotional_directness",
    "emotional_suppression",
    "visual_focus",
    "sound_focus",
    "rhythm_speed",
    "paragraph_density",
    "cliffhanger_density",
    "information_density",
    "foreshadowing_density",
    "violence_consequence_density"
  ],
  "constraints": {
    "must_not": [
      "风格不得强制人物说某种话",
      "风格不得强制人物做某种动作",
      "风格不得强制人物拥有某种性格",
      "风格不得强制情绪表现为某种身体动作",
      "风格不得强制剧情按照某种结果发展"
    ]
  },
【本步用法】
从本场已确定的目标与作者独立选择的风格取相关维度，使用实际表达与判据。原文共同约束以人物、情绪、行为和情节的已定依据为准。

#### ADAPT_B_00068 语言风格
【类型系统原文位置】风格表达适配.json 第1414行
【类型系统同值原文位置】类型表达适配总表.json 第20889行，条目第24651行。
【原文字段】第1457–1471行
      "adaptation_id": "ADAPT_B_00068",
      "type_id": "STYLE_LANGUAGE",
      "target_kind": "style_dimension",
      "target_id": "STYLE_LANGUAGE",
      "target_scope": null,
      "adaptation_kind": "expression_preference",
      "priority": 0,
      "weight": 0,
      "parameters": {
        "language_complexity": "medium",
        "sentence_length": "medium",
        "dialogue_ratio": "medium",
        "description_ratio": "medium",
        "emotional_directness": "medium"
      },
【原文字段】第1491–1494行
      "not_guaranteed": [
        "风格不强制人物说某种话",
        "风格不强制人物做某种动作"
      ],
【原文字段】第1496行
      "source_refs": [],
【原文字段】第1498行
      "confidence": 999,
【本步用法】
原配置的置信度999和空来源待核，参数保留备查。按作者已明确的具体表达设置核对，未指定的设置留空。按作者明确采用的语言风格，用当前场景和叙述者安排实际句式、词汇与修辞，并保留已定人物和世界规则。
"""
