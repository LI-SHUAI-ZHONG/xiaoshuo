"""类型选择步骤使用的《类型系统》名称、层级、身份和字段原文。"""

RELATED_MECHANISMS = {
    '穿越': 'PLOT_MECHANISM_TRANSMIGRATION',
    '重生': 'PLOT_MECHANISM_REBIRTH',
    '系统': 'PLOT_MECHANISM_SYSTEM',
    '复仇': 'PLOT_MECHANISM_REVENGE',
    '无限流': 'PLOT_MECHANISM_INFINITE',
    '快穿': 'PLOT_MECHANISM_FAST_TRANSMIGRATION',
    '阵法': 'PLOT_MECHANISM_ARRAY',
    '废柴逆袭': 'PLOT_MECHANISM_UNDERDOG',
    '无敌': 'PLOT_MECHANISM_INVINCIBLE',
    '探案': 'PLOT_MECHANISM_INVESTIGATION',
    '权谋': 'PLOT_MECHANISM_POLITICAL',
    '战争': 'PLOT_MECHANISM_WAR',
    '经营': 'PLOT_MECHANISM_MANAGEMENT',
    '种田': 'PLOT_MECHANISM_FARMING',
    '商业': 'PLOT_MECHANISM_TRADE',
    '游戏': 'PLOT_MECHANISM_GAME',
    '时间旅行': 'PLOT_MECHANISM_TIME_TRAVEL',
    '平行世界': 'PLOT_MECHANISM_PARALLEL',
    '虚拟现实': 'PLOT_MECHANISM_VR',
    '人工智能': 'PLOT_MECHANISM_AI',
    '机器人': 'PLOT_MECHANISM_ROBOT',
    '机甲': 'PLOT_MECHANISM_MECHA',
    '外星文明': 'PLOT_MECHANISM_ALIEN',
    '文明演化': 'PLOT_MECHANISM_CIVILIZATION',
    '末世': 'PLOT_MECHANISM_APOCALYPSE',
    '生化': 'PLOT_MECHANISM_BIOCHEMICAL',
    '基因': 'PLOT_MECHANISM_GENE',
    '赛博朋克': 'PLOT_MECHANISM_CYBERPUNK',
    '乌托邦': 'PLOT_MECHANISM_UTOPIA',
    '反乌托邦': 'PLOT_MECHANISM_DYSTOPIA',
    '多元宇宙': 'PLOT_MECHANISM_MULTIVERSE',
    '主神空间': 'PLOT_MECHANISM_MAIN_GOD',
    '轮回': 'PLOT_MECHANISM_REINCARNATION',
    '游戏化世界': 'PLOT_MECHANISM_GAMIFIED',
    '规则任务': 'PLOT_MECHANISM_RULE_TASK',
    '多世界穿梭': 'PLOT_MECHANISM_MULTI_WORLD',
}

NAME_EVIDENCE_USE = (
    '按 type_name_evidence 逐个核对类型本体总表的原名、原别名、各自类型种类和父项。'
    '别名只提供它明写的目标。原件同名主类型、子类型、题材标签各自保留 ID。'
    'related_name_only 标记近名机制的独立定义，需要项目明确选择之后才进入对应适配。'
    '在 selection.basis 依据作者实际需求说明选型，在 concepts.activation_basis 说明标签对应题材。'
    'TYPE_A 分表的实际选型照其本身定义核对。涉及古代言情时，保留总表与第2962行的层级冲突。'
    '同名而作者未说明层级或用途时，在已有 boundaries 记待核。涉及写法时按实际创作需求另查原资料。'
)

MATERIAL = r"""【核对作者已确认的类型身份与项目范围】
#### 类型本体的别名表
【类型系统原文位置】类型本体\类型别名表.json 第2666行
【原文字段】第2671–2812行
  "aliases": [
    {
      "alias": "玄幻",
      "canonical": "GENRE_XUANHUAN"
    },
    {
      "alias": "奇幻",
      "canonical": "GENRE_QIHUAN"
    },
    {
      "alias": "仙侠",
      "canonical": "GENRE_XIANXIA"
    },
    {
      "alias": "武侠",
      "canonical": "GENRE_WUXIA"
    },
    {
      "alias": "都市",
      "canonical": "GENRE_DUSHI"
    },
    {
      "alias": "历史",
      "canonical": "GENRE_LISHI"
    },
    {
      "alias": "军事",
      "canonical": "GENRE_JUNSHI"
    },
    {
      "alias": "科幻",
      "canonical": "GENRE_KEHUAN"
    },
    {
      "alias": "悬疑",
      "canonical": "GENRE_XUANYI"
    },
    {
      "alias": "推理",
      "canonical": "GENRE_TUILI"
    },
    {
      "alias": "灵异",
      "canonical": "GENRE_LINGYI"
    },
    {
      "alias": "恐怖",
      "canonical": "GENRE_KONGBU"
    },
    {
      "alias": "游戏",
      "canonical": "GENRE_YOUXI"
    },
    {
      "alias": "电竞",
      "canonical": "GENRE_DIANJING"
    },
    {
      "alias": "体育",
      "canonical": "GENRE_TIYU"
    },
    {
      "alias": "言情",
      "canonical": "GENRE_YANQING"
    },
    {
      "alias": "现代言情",
      "canonical": "GENRE_XIANDAI_YANQING"
    },
    {
      "alias": "古代言情",
      "canonical": "GENRE_GUDAI_YANQING"
    },
    {
      "alias": "现实",
      "canonical": "GENRE_XIANSHI"
    },
    {
      "alias": "校园",
      "canonical": "GENRE_QINGCHUN"
    },
    {
      "alias": "二次元",
      "canonical": "GENRE_ERCIYUAN"
    },
    {
      "alias": "轻小说",
      "canonical": "GENRE_QINGXIAOSHUO"
    },
    {
      "alias": "同人",
      "canonical": "GENRE_TONGREN"
    },
    {
      "alias": "无限流",
      "canonical": "GENRE_ZHUTIAN"
    },
    {
      "alias": "末世",
      "canonical": "GENRE_MOSHI"
    },
    {
      "alias": "赛博朋克",
      "canonical": "GENRE_SAIBO"
    },
    {
      "alias": "未来",
      "canonical": "GENRE_WEILAI"
    },
    {
      "alias": "童话",
      "canonical": "GENRE_TONGHUA"
    },
    {
      "alias": "儿童",
      "canonical": "GENRE_ERTONG"
    },
    {
      "alias": "纪实",
      "canonical": "GENRE_JISHI"
    },
    {
      "alias": "职业",
      "canonical": "GENRE_ZHIYE"
    },
    {
      "alias": "女性",
      "canonical": "GENRE_NVXING"
    },
    {
      "alias": "家庭",
      "canonical": "GENRE_JIATING"
    },
    {
      "alias": "宫廷",
      "canonical": "GENRE_GONGTING"
    },
    {
      "alias": "社会派",
      "canonical": "GENRE_SHEHUI"
    }
  ],
【本步用法】
以作者已明确的命名核对来源里的别名及相应ID。别名出现多个不同对象时，以现有类型记录及该作品的实际需求确认身份。

#### 类型本体的层级规则
【类型系统原文位置】类型本体\类型层级规则.json 第2861行
【原文字段】第2866–2885行
  "rules": [
    {
      "rule": "主类型是最高层级，parent_id为null"
    },
    {
      "rule": "子类型必须引用已存在的主类型作为parent_id"
    },
    {
      "rule": "混合类型必须引用已存在的主类型作为component_type_ids"
    },
    {
      "rule": "不允许循环父子关系"
    },
    {
      "rule": "题材标签、机制、结构、风格等不得作为主类型"
    },
    {
      "rule": "穿越、重生、系统等不得直接作为主类型"
    }
  ],
【本步用法】
在本步用已提供的原文和作者需求核对主、子、混合与标签的位置。父级、组成及适用范围以真实类型记录为准。

#### 类型本体的冲突规则
【类型系统原文位置】类型本体\类型冲突规则.json 第2934行
【原文字段】第2939–2964行
  "rules": [
    {
      "rule": "玄幻与仙侠必须区分，玄幻偏力量体系，仙侠偏修仙体系"
    },
    {
      "rule": "奇幻与玄幻必须区分，奇幻偏西方魔法，玄幻偏东方修炼"
    },
    {
      "rule": "武侠与仙侠必须区分，武侠偏武学江湖，仙侠偏修仙长生"
    },
    {
      "rule": "悬疑、推理、灵异、恐怖必须区分"
    },
    {
      "rule": "游戏、电竞、体育竞技必须区分"
    },
    {
      "rule": "穿越、重生、系统不得作为主类型"
    },
    {
      "rule": "现代言情是言情的一个子类型"
    },
    {
      "rule": "古代言情是言情的一个子类型"
    }
  ],
【本步用法】
按实际候选定义核对相近名称、同名对象和主子层级。作品风格、具体写法和兼容性另按作者已确认范围与后续步骤使用。

#### 类型本体的字段说明
【类型系统原文位置】类型本体\类型字段说明.json 第3013行
【原文字段】第3018–3046行
  "fields": {
    "type_id": "类型唯一标识",
    "type_kind": "类型对象种类（GENRE/SUBGENRE/HYBRID_GENRE/SUBJECT_TAG/ERA_TAG/WORLD_TAG/PLOT_MECHANISM/SATISFACTION_MECHANISM/NARRATIVE_STRUCTURE/VIEWPOINT_TAG/STYLE/TONE/AUDIENCE_TAG/MARKET_TAG/SOURCE_TAG）",
    "canonical_name": "规范名称",
    "display_name": "显示名称",
    "aliases": "别名列表",
    "parent_id": "父类型ID",
    "ancestor_ids": "祖先类型ID列表",
    "child_ids": "子类型ID列表",
    "level": "层级（1=主类型，2=子类型）",
    "definition": "定义",
    "scope": "适用范围",
    "inclusions": "包含项",
    "exclusions": "排除项",
    "distinguishing_features": "区分特征",
    "common_confusions": "常见混淆",
    "not_guaranteed": "不保证项",
    "source_refs": "来源引用",
    "evidence_type": "证据类型",
    "confidence": "置信度",
    "status": "状态",
    "schema_version": "Schema版本",
    "component_type_ids": "混合类型组件ID列表",
    "combination_reason": "混合原因",
    "compatible_mechanisms": "兼容机制",
    "compatible_structures": "兼容结构",
    "compatible_styles": "兼容风格",
    "possible_conflicts": "可能冲突"
  },
【本步用法】
读取实际类型来源时，依字段核对身份、定义、适用与排除范围，以及真实父子和组合关系。依据本步现有 selection、concepts 和 boundaries 保存项目已确认部分，空值沿用现有待核方式。
"""
