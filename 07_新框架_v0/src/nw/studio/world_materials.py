"""Genre-targeted world material taxonomy, step boundaries, and coverage audit for 03 world_design.

Organizes every original workflow world material source (`world_design*.py`) into 9 bounded,
non-overlapping sub-categories, maps all 35 main genres (and their subgenres) to primary /
optional / out-of-scope world material scopes and typical resource profiles, and connects
upstream corpus decomposition (`world_rules`) and `01-02` type selection/adaptation cleanly
into `03 world_design` and downstream `04-09` steps without cross-step leakage.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.studio.catalog import canonical_types, type_map


WORLD_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'world_design',
    'order': 3,
    'name': '03. 世界设定与限制',
    'responsibility': (
        '建立故事世界可运行且可核查的外部规则底座：世界形态与底层前提、社会制度与权力执行、'
        '影响当下的历史遗留、核心资源与交易市场、道具边界与代价、生态张力与空间演化，'
        '以及仅在适配题材下启用的种族构造、力量能量与特殊世界机制。'
    ),
    'upstream_steps': [
        {'step_id': 'type_selection', 'name': '01. 类型判定与承诺', 'provides': '主/子/副类型编号、核心读者承诺与题材边界'},
        {'step_id': 'type_adaptation', 'name': '02. 类型组合与适配', 'provides': '多类型调和规则、世界观关注重点与原创防雷同约束'},
        {'step_id': 'corpus:world_rules', 'name': '参考拆解 · 世界规则', 'provides': '同类型原作经验证的“规则→限制→受影响选择→后果”可迁移方法'},
    ],
    'downstream_steps': [
        {'step_id': 'character_design', 'name': '04. 人物动机与弧线', 'consumes': '社会位置、职业权限、能力上限与阵容需求（cast_demands）'},
        {'step_id': 'static_relations', 'name': '05. 静态关系与张力', 'consumes': '阶层差异、势力阵营、制度从属与种族/资源张力'},
        {'step_id': 'plot_design', 'name': '06. 剧情因果与伏笔', 'consumes': '世界核心矛盾、自动运转事件、历史暗流与资源稀缺冲突'},
        {'step_id': 'action_design', 'name': '08. 行动博弈与试错代价', 'consumes': '规则门槛、资源消耗速率、道具功能边界与违规代价'},
        {'step_id': 'scene_design', 'name': '09. 场景结构与POV边界', 'consumes': '地理空间框架、可见性（visibility）与未写明史实边界'},
        {'step_id': 'state_transition', 'name': '10. 状态变化与外部因果', 'consumes': '资源增减/转化效率、损耗不可逆性与世界不变量'},
        {'step_id': 'review', 'name': '16. 独立审稿与证据核验', 'consumes': '世界硬限制、命名术语一致性与规则代价核验依据'},
    ],
    'allowed_outputs': [
        {'field': 'members', 'kind': 'world', 'description': '世界卡（title、rule、limits、visibility），按规则域拆分，不混写人物个人弧光'},
        {'field': 'limitations', 'kind': 'list[str]', 'description': '全书不可随意绕过的世界硬限制与代价清单'},
        {'field': 'unknowns', 'kind': 'list[str]', 'description': '尚未确定或刻意留白的世界边界，交给作者确认或后续揭示'},
        {'field': 'cast_demands', 'kind': 'list[object]', 'description': '（启用阵容需求策略时）由世界与剧情前置推导出的本轮人物职责需求，交接给 04 人物设计'},
    ],
    'in_scope': [
        '世界形态、地理空间、命名术语与不可改写的底层前提/不变量',
        '社会阶层、权力结构、执行机构、职业分工与晋升路径',
        '仍对当前故事起作用的历史分期、旧秩序创伤与未写明史实边界',
        '符合所选类型的资源库、计量/稀缺度、货币汇率与交易流通规则',
        '关键道具/物证/武器的功能边界、使用代价、反功能与制造门槛',
        '无主角时仍在运转的生态层级、势力张力与空间衰败/生长演化',
        '（仅适配题材）种族差异、生命构造限制、能量/力量体系公式与突破代价',
        '（仅适配或显式启用）系统/平行世界/VR/赛博/乌托邦/多元/游戏化运行机制',
    ],
    'out_of_scope': [
        '不得代替 01/02 步骤修改已选主副类型或推翻类型承诺',
        '不得提前编写单个角色的具体执念、性格习惯或成长弧光（归 04 人物设计）',
        '不得提前编写具体人物之间的私人恩怨、信任度或亲密关系网（归 05 静态关系）',
        '不得提前规划分卷/分章情节顺序、具体事件结果或大结局走向（归 06 剧情 / 07 事件）',
        '不得规定具体行文辞藻、叙事人称、对话语气或段落文风（归 13 表达设计）',
        '现实/都市日常/纯悬疑推理/纯言情/历史写实等非超自然题材，未经作者显式叠加超自然副类型不得套用修炼灵气或奇幻种族规则',
    ],
    'workflow_network_policies': [
        {'id': 'world_network_policy', 'name': '力量与物理算式静网前置'},
        {'id': 'world_advancement_policy', 'name': '进阶门槛与突破条件前置'},
        {'id': 'world_conversion_policy', 'name': '能量/资源转化效率与守恒前置'},
        {'id': 'world_resource_policy', 'name': '六大资源库与稀缺流转前置'},
        {'id': 'world_market_policy', 'name': '货币汇率与交易市场规则前置'},
        {'id': 'world_history_policy', 'name': '时代分期与历史后果前置'},
    ],
}


WORLD_CATEGORIES: tuple[dict[str, Any], ...] = (
    {
        'id': 'foundation',
        'name': '世界基础、形态与底层前提',
        'short_name': '基础与前提',
        'description': '确立世界形态（现实/架空/平行/异世界/反乌托邦）、地理空间框架、核心矛盾、世界基调、先验预设、不变量与 70%/30% 新奇度。',
        'usage_mode': '全题材底座：写明哪些规则不可被普通事件改写，以及哪些背景信息对读者保持半透明。',
        'source_files': ['world_design_setting.py (§31, §34, §35, §123.19)', 'world_design_resources.py (§124.9)'],
        'catalog_group_key': 'world.group.foundation',
        'network_policies': [],
        'keywords': ('世界观', '世界形态', '地理', '前提', '不变量', '半透明', '基调', '核心矛盾', '新奇度', '现实世界', '架空', '命名'),
    },
    {
        'id': 'institution',
        'name': '社会阶层、权力、职业与制度',
        'short_name': '制度与职业',
        'description': '规定社会分层、晋升通道、决策权力结构、执行机构（规则/委托/强制执行）及职业权限与合法资源获取路径。',
        'usage_mode': '约束角色能做什么、谁有权执行惩罚、违规有何制度后果，交接给人物位置与剧情阻力。',
        'source_files': ['world_design_setting.py (§33, §39)'],
        'catalog_group_key': 'world.group.institution',
        'network_policies': [],
        'keywords': ('制度', '阶层', '权力', '律法', '规则执行', '职业', '晋升', '执法', '官府', '宗门', '公司', '机构', '程序', '禁令', '合规', '朝廷', '宫规', '权限'),
    },
    {
        'id': 'history',
        'name': '时代分期、历史演化与未写明史实',
        'short_name': '历史与时代',
        'description': '记录创始/扩张/动荡/固化/暗流/裂变六阶段及未写明史实碎片，只保留对当下局势仍有真实约束的历史遗产。',
        'usage_mode': '把“暗流期”表面秩序与历史遗留矛盾写入世界卡，对接 world_history 网络前置，不写无关编年史。',
        'source_files': ['world_design_setting.py (§32)'],
        'catalog_group_key': 'world.group.history',
        'network_policies': ['world_history_policy'],
        'keywords': ('历史', '纪年', '时代', '朝代', '创始', '动荡', '固化', '暗流', '裂变', '旧案', '遗产', '传说', '灾变', '战争史', '史实'),
    },
    {
        'id': 'resource_market',
        'name': '资源库、货币汇率与交易市场',
        'short_name': '资源与市场',
        'description': '覆盖物质/能量/信息/关系/时间/机会六大资源库、价值分层、稀缺分级、消耗速率、转化损耗、再生机制与货币汇率交易规则。',
        'usage_mode': '按所选类型选定真实核心资源与计价单位，写清获取门槛与损耗上限，对接 world_resources / world_market 前置。',
        'source_files': ['world_design_resources.py (§125)', 'world_design_ecology.py (§24–§27)'],
        'catalog_group_key': 'world.group.resource_market',
        'network_policies': ['world_resource_policy', 'world_market_policy'],
        'keywords': ('资源', '货币', '汇率', '交易', '市场', '黑市', '稀缺', '消耗', '补给', '成本', '金钱', '灵石', '粮食', '资金', '预算', '算力', '人脉', '情报', '信用', '供给'),
    },
    {
        'id': 'items_props',
        'name': '道具功能边界、代价与制造工艺',
        'short_name': '道具与工艺',
        'description': '限定关键道具、武器、装备、载具或物证的功能边界、使用代价、成瘾/反功能、环境交互、维护升级与制造/技能树条件。',
        'usage_mode': '避免“万能道具”破坏冲突：明确物品能做什么、不能做什么及损坏/反噬条件，供 08 行动设计核验。',
        'source_files': ['world_design_ecology.py (§28–§30)', 'world_design_setting.py (§40)'],
        'catalog_group_key': 'world.group.items_props',
        'network_policies': [],
        'keywords': ('道具', '法宝', '武器', '装备', '物证', '器械', '工具', '载具', '制造', '炼器', '炼丹', '工艺', '技能树', '媒介', '代价', '反功能', '禁忌物'),
    },
    {
        'id': 'ecology_space',
        'name': '生态格局、势力张力与空间时间性',
        'short_name': '生态与空间',
        'description': '刻画生态系统层级、自动运转事件、均衡与熵增、势力自动互动与隐蔽暗线循环，以及空间随时间的衰败、生长与改造。',
        'usage_mode': '让世界在主角不在场时也持续运转，为多线剧情和长篇阶段升级提供外部环境变化依据。',
        'source_files': ['world_design_ecology.py (§20–§23)', 'world_design_space.py (§115.6)'],
        'catalog_group_key': 'world.group.ecology_space',
        'network_policies': [],
        'keywords': ('生态', '势力', '派系', '阵营', '自动运转', '均衡', '熵增', '暗线', '空间', '衰败', '区域', '环境', '地缘', '据点', '领地', '地形'),
    },
    {
        'id': 'race_construct',
        'name': '种族差异与生命构造边界',
        'short_name': '种族与构造',
        'description': '规定多种族属性、先天限制、社会嵌入与种族张力，以及身体/能量/精神三维度构造如何决定能力上限、承受力与退化。',
        'usage_mode': '严格按题材边界启用：仅用于存在非人种族、异化体质或超凡生理构造的世界，避免现实题材无端泛化。',
        'source_files': ['world_design_setting.py (§36–§38)'],
        'catalog_group_key': 'world.group.race_construct',
        'network_policies': [],
        'keywords': ('种族', '血脉', '灵根', '体质', '构造', '变异', '改造人', '义体', '非人', '妖', '魔', '精灵', '外星', '先天限制', '承受力', '能力上限'),
    },
    {
        'id': 'power_energy',
        'name': '力量体系、能量三态转化与突破代价',
        'short_name': '力量与能量',
        'description': '规定力量公式、状态叠加、能量总量/纯度/技巧、游离态/凝聚态转化、潮汐波动、物理引擎限制及等阶突破门槛与代价。',
        'usage_mode': '严格按题材边界启用：仅用于修炼/超凡/魔法/异能/武学/硬能源体系，对接 world_network / advancement / conversion 前置。',
        'source_files': ['world_design.py (§9–§19)'],
        'catalog_group_key': 'world.group.power_energy',
        'network_policies': ['world_network_policy', 'world_advancement_policy', 'world_conversion_policy'],
        'keywords': ('力量体系', '境界', '突破', '能量', '灵气', '灵力', '魔力', '魔法', '内力', '真气', '异能', '修炼', '功法', '咒术', '物理引擎', '守恒', '公式', '潮汐', '晋阶'),
    },
    {
        'id': 'special_mechanism',
        'name': '特殊世界运行机制',
        'short_name': '特殊机制',
        'description': '覆盖系统机制、平行世界、虚拟现实（VR）、赛博朋克、乌托邦、多元宇宙与游戏化世界等特殊顶层运行框架。',
        'usage_mode': '仅当作品显式采用特殊世界规则框架时启用，必须在世界卡写明现实与机制之间的边界与例外。',
        'source_files': ['world_design_plot_mechanisms.py (PLOT_MECHANISM_*)'],
        'catalog_group_key': 'world.group.special_mechanism',
        'network_policies': [],
        'keywords': ('系统机制', '面板', '任务奖励', '平行世界', '虚拟现实', 'VR', '全息', '赛博', '乌托邦', '反乌托邦', '多元宇宙', '无限流', '副本', '游戏化', '规则怪谈'),
    },
)

WORLD_CATEGORY_MAP: dict[str, dict[str, Any]] = {cat['id']: cat for cat in WORLD_CATEGORIES}
WORLD_CATEGORY_ORDER: dict[str, int] = {cat['id']: idx for idx, cat in enumerate(WORLD_CATEGORIES)}

RELEVANCE_RANK = {'primary': 0, 'optional': 1, 'out_of_scope': 2}
RELEVANCE_LABELS = {
    'primary': '本类型核心',
    'optional': '按需扩展',
    'out_of_scope': '非本类型常规项',
}


def _profile(
    primary: tuple[str, ...],
    optional: tuple[str, ...],
    *,
    preferred_resources: tuple[str, ...],
    exchange_media: tuple[str, ...],
    long_term_constraints: tuple[str, ...],
    item_emphasis: tuple[str, ...],
    decomposition_focus: str,
    adaptation_refs: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        'primary': primary,
        'optional': optional,
        'resource_profile': {
            'preferred_resources': list(preferred_resources),
            'exchange_media': list(exchange_media),
            'long_term_constraints': list(long_term_constraints),
            'item_emphasis': list(item_emphasis),
            'type_adaptation_refs': list(adaptation_refs),
        },
        'decomposition_focus': decomposition_focus,
    }


DEFAULT_WORLD_PROFILE = _profile(
    primary=('foundation', 'institution', 'resource_market'),
    optional=('history', 'items_props', 'ecology_space', 'race_construct', 'power_energy', 'special_mechanism'),
    preferred_resources=('资金/物质资源', '信息/情报', '人脉/信任', '时间/机会'),
    exchange_media=('通用货币', '利益/人情交换'),
    long_term_constraints=('制度权限', '资源稀缺度', '信息边界'),
    item_emphasis=('功能边界', '获取门槛', '使用代价'),
    decomposition_focus='优先核对决定事件能否发生的外部制度、核心资源与限制边界；只提取原文证实生效的规则。',
)


# Covers all 35 main genres from nw.studio.catalog.genres().
# Subgenres inherit from their parent_id; multi-genre selections merge via max relevance.
GENRE_WORLD_PROFILES: dict[str, dict[str, Any]] = {
    'GENRE_XUANHUAN': _profile(
        primary=('foundation', 'power_energy', 'resource_market', 'institution', 'ecology_space', 'race_construct', 'items_props'),
        optional=('history', 'special_mechanism'),
        preferred_resources=('修炼能源/晶石', '丹药/灵材', '功法/秘术', '神器/法宝', '领地/矿脉'),
        exchange_media=('高纯度能量币/灵石', '稀有材料以物易物'),
        long_term_constraints=('血脉/体质上限', '等阶压制', '资源枯竭与宗门垄断'),
        item_emphasis=('境界适配', '品级压制', '使用反噬与消耗'),
        decomposition_focus='重点拆解力量进阶门槛、能量转化损耗、宗门/帝国制度压制与核心资源垄断如何逼迫角色做选择。',
    ),
    'GENRE_QIHUAN': _profile(
        primary=('foundation', 'power_energy', 'race_construct', 'history', 'institution', 'ecology_space', 'items_props'),
        optional=('resource_market', 'special_mechanism'),
        preferred_resources=('魔力/秘银/素材', '古代遗物', '领地税收', '契约/信仰', '知识典籍'),
        exchange_media=('金币/帝国通货', '魔法素材', '契约凭证'),
        long_term_constraints=('施法代价/反噬', '种族先天边界', '教会与王权制衡'),
        item_emphasis=('附魔条件', '禁忌代价', '古物来历与归属'),
        decomposition_focus='重点拆解魔法/神术代价、多种族社会嵌入、历史遗留裂痕与教会/王国制度如何约束人物行动。',
    ),
    'GENRE_XIANXIA': _profile(
        primary=('foundation', 'power_energy', 'resource_market', 'institution', 'items_props', 'ecology_space', 'history'),
        optional=('race_construct', 'special_mechanism'),
        preferred_resources=('灵石', '丹药', '法宝', '功法', '灵脉'),
        exchange_media=('灵石', '丹药'),
        long_term_constraints=('灵根', '悟性', '机缘', '寿元与天劫代价'),
        item_emphasis=('修炼辅助', '品级压制', '认主绑定', '宗门/个人归属'),
        decomposition_focus='重点拆解灵脉/灵石/丹药供给、境界突破代价、宗门规矩与法宝认主/消耗规则，区分口头传说与真实天道限制。',
        adaptation_refs=('ADAPT_B_00026', 'ADAPT_B_00030', 'ADAPT_B_00061'),
    ),
    'GENRE_WUXIA': _profile(
        primary=('foundation', 'institution', 'history', 'power_energy', 'items_props', 'ecology_space'),
        optional=('resource_market', 'race_construct'),
        preferred_resources=('武学秘籍', '内力修为', '声望/侠名', '银两/盘缠', '门派人脉'),
        exchange_media=('白银/铜钱', '江湖人情/令牌'),
        long_term_constraints=('内力上限与经脉损伤', '江湖道义/门规', '朝廷缉捕边界'),
        item_emphasis=('神兵利器特性', '毒药/解药制约', '信物身份象征'),
        decomposition_focus='重点拆解江湖规矩与朝廷律法冲突、武学修为代价与破绽、门派势力格局与旧案恩怨。',
    ),
    'GENRE_DUSHI': _profile(
        primary=('foundation', 'institution', 'resource_market'),
        optional=('items_props', 'ecology_space', 'history', 'special_mechanism'),
        preferred_resources=('金钱', '人脉', '信息', '房产', '股份'),
        exchange_media=('金钱', '商业股权/合同权益'),
        long_term_constraints=('学历', '关系网', '信用记录', '法律法规与时间精力'),
        item_emphasis=('效率', '金钱价值', '社会身份', '个人购买归属'),
        decomposition_focus='重点拆解现实商业/行业/法律规则、金钱与人脉门槛、信息不对称与时间成本；若无超自然副类型，切勿套用能量公式或种族规则。',
        adaptation_refs=('ADAPT_B_00008', 'ADAPT_B_00009', 'ADAPT_B_00027', 'ADAPT_B_00062'),
    ),
    'GENRE_LISHI': _profile(
        primary=('foundation', 'history', 'institution', 'resource_market', 'ecology_space'),
        optional=('items_props',),
        preferred_resources=('粮草/土地', '钱币/盐铁', '官职/兵权', '宗族/士林声望', '情报驿路'),
        exchange_media=('铜钱/白银/布帛/粮食', '官凭勘合'),
        long_term_constraints=('生产力与交通通信延迟', '礼法宗法', '兵役赋税极限'),
        item_emphasis=('时代工艺上限', '身份礼制标志', '供给损耗'),
        decomposition_focus='重点拆解时代生产力上限、交通通信时延、官制礼法与财政粮草约束，防止现代制度或超自然规则穿帮。',
    ),
    'GENRE_JUNSHI': _profile(
        primary=('foundation', 'institution', 'resource_market', 'items_props', 'ecology_space', 'history'),
        optional=(),
        preferred_resources=('弹药/油料/粮秣', '兵力编制', '情报侦察', '制空/制海/地形节点', '指挥权限'),
        exchange_media=('军需配给', '战功/军令权限'),
        long_term_constraints=('后勤补给线', '武器射程与故障率', '军纪指挥链与战场迷雾'),
        item_emphasis=('战术性能边界', '维护弹药消耗', '地形/气候限制'),
        decomposition_focus='重点拆解编制指挥链、后勤补给极限、装备真实性能边界与战场情报延迟如何决定胜负与伤亡代价。',
    ),
    'GENRE_KEHUAN': _profile(
        primary=('foundation', 'power_energy', 'items_props', 'institution', 'resource_market', 'ecology_space', 'special_mechanism'),
        optional=('history', 'race_construct'),
        preferred_resources=('能源/核燃料', '算力/数据', '宇航载具/工业产能', '技术专利', '宜居空间'),
        exchange_media=('信用点', '能源配额', '技术/数据授权'),
        long_term_constraints=('光速/热力学物理底线', '技术层级代差', '资源与生态承载极限'),
        item_emphasis=('多功能', '智能化', '科技层级', '技术获得归属'),
        decomposition_focus='重点拆解核心科技/物理公理及其反噬边界、能源算力成本、科技层级带来的社会制度分化。',
        adaptation_refs=('ADAPT_B_00029', 'ADAPT_B_00033', 'ADAPT_B_00041'),
    ),
    'GENRE_XUANYI': _profile(
        primary=('foundation', 'institution', 'items_props', 'resource_market'),
        optional=('history', 'ecology_space', 'special_mechanism'),
        preferred_resources=('关键物证/档案', '调查权限', '时间窗口', '线人/目击证言', '资金与掩护'),
        exchange_media=('情报置换', '合法程序权限', '金钱'),
        long_term_constraints=('取证程序与时效', '物理时空封闭性', '目击者知情边界'),
        item_emphasis=('留痕与伪造边界', '物理可用性', '证据链唯一性'),
        decomposition_focus='重点拆解封闭/半封闭环境规则、调查权限限制、时间线物理硬约束与关键物证的不可伪造性；纯悬疑不得凭空引入超自然力量。',
    ),
    'GENRE_TUILI': _profile(
        primary=('foundation', 'institution', 'items_props'),
        optional=('resource_market', 'history'),
        preferred_resources=('物证/痕检数据', '时间线记录', '不在场证明', '空间结构图'),
        exchange_media=('司法/委托权限', '信息核验'),
        long_term_constraints=('公平线索原则', '物理与医学常识底线', '严格时空可达性'),
        item_emphasis=('机关物理原理', '痕检可追溯性', '唯一性限制'),
        decomposition_focus='重点拆解案件物理/空间/时间硬约束、刑侦或委托规则边界与道具机关的可证伪条件；严格屏蔽超自然力量与特殊系统。',
    ),
    'GENRE_LINGYI': _profile(
        primary=('foundation', 'power_energy', 'items_props', 'history', 'ecology_space'),
        optional=('institution', 'race_construct', 'resource_market', 'special_mechanism'),
        preferred_resources=('镇物/符箓/媒介', '禁忌情报', '阳寿/理智值', '安全屋/结界'),
        exchange_media=('以命换命/因果代价', '禁忌情报'),
        long_term_constraints=('触发禁忌规则', '理智/寿命折损', '灵异规律不可正面硬抗'),
        item_emphasis=('克制条件', '反噬代价', '触发限制'),
        decomposition_focus='重点拆解诡异/灵异触发铁律、生路条件、道具反噬代价与历史旧怨留下的空间禁忌。',
    ),
    'GENRE_KONGBU': _profile(
        primary=('foundation', 'items_props', 'ecology_space'),
        optional=('history', 'power_energy', 'institution', 'resource_market', 'special_mechanism'),
        preferred_resources=('照明/医疗/防身物资', '逃生路线信息', '体能与理智', '临时安全区'),
        exchange_media=('生存物资', '保命情报'),
        long_term_constraints=('环境孤立与通信断绝', '未知威胁规则', '感官与体能极限'),
        item_emphasis=('一次性消耗', '噪音/暴露副作用', '可靠性缺陷'),
        decomposition_focus='重点拆解封闭环境隔离条件、威胁行为规律与不可知边界（34.2）、资源耗尽如何压缩角色生路。',
    ),
    'GENRE_YOUXI': _profile(
        primary=('foundation', 'special_mechanism', 'power_energy', 'resource_market', 'items_props', 'institution'),
        optional=('ecology_space', 'race_construct', 'history'),
        preferred_resources=('经验值/等级', '金币/积分', '装备/道具', '技能书/副本情报', '公会资源'),
        exchange_media=('游戏金币/积分', '拍卖行/交易行契约'),
        long_term_constraints=('数值公式与冷却时间', '死亡惩罚', '版本机制与副本进入门槛'),
        item_emphasis=('属性数值边界', '耐久/冷却/绑定', '合成与掉落规则'),
        decomposition_focus='重点拆解游戏核心数值/副本/冷却/死亡惩罚规则、经济拍卖机制与现实-游戏双向影响边界。',
    ),
    'GENRE_DIANJING': _profile(
        primary=('foundation', 'institution', 'resource_market', 'special_mechanism'),
        optional=('items_props', 'ecology_space'),
        preferred_resources=('版本战术理解', '训练时长与体能', '俱乐部预算/转会名额', '赛事积分'),
        exchange_media=('转会费/赞助资金', '赛事席位与合同条款'),
        long_term_constraints=('官方赛制与版本平衡', '职业年龄与手伤极限', '团队配合与经济发育规则'),
        item_emphasis=('局内装备/英雄机制', '版本数值边界'),
        decomposition_focus='重点拆解比赛项目核心局内规则、职业联赛制度、转会合同边界与版本更迭约束。',
    ),
    'GENRE_TIYU': _profile(
        primary=('foundation', 'institution', 'resource_market'),
        optional=('items_props', 'history'),
        preferred_resources=('体能与恢复周期', '科学训练条件', '参赛资格/积分排名', '赞助与医疗团队'),
        exchange_media=('赛事奖金/转会费', '积分排名'),
        long_term_constraints=('赛规判罚底线', '人体生理与伤病恢复极限', '赛季赛程周期'),
        item_emphasis=('合规器材标准', '场地与气候影响'),
        decomposition_focus='重点拆解项目竞赛规则、晋级选拔制度与人体生理/伤病硬限制；不得引入超自然能力。',
    ),
    'GENRE_YANQING': _profile(
        primary=('foundation', 'institution', 'resource_market'),
        optional=('history', 'items_props', 'ecology_space', 'special_mechanism'),
        preferred_resources=('社交地位/名声', '时间与共处机会', '家庭/家族资源', '关键信物与隐私信息'),
        exchange_media=('情感信任/名分承诺', '现实经济与家族利益'),
        long_term_constraints=('阶层与门第阻力', '礼教/舆论/职场规范', '不可逾越的外部责任'),
        item_emphasis=('情感记忆载体', '象征化意义', '身份凭证'),
        decomposition_focus='重点拆解阻隔或促成关系推进的社会规范、阶层/家庭制度、现实成本与信物承载规则。',
    ),
    'GENRE_XIANDAI_YANQING': _profile(
        primary=('foundation', 'institution', 'resource_market'),
        optional=('items_props', 'ecology_space'),
        preferred_resources=('经济独立度', '职场/家庭时间', '人脉与舆论声誉', '隐私信息'),
        exchange_media=('金钱', '合作/人情契约'),
        long_term_constraints=('现代职场与法律规范', '原生家庭与社会舆论', '异地/时间成本'),
        item_emphasis=('记忆载体', '日常消费与身份符号'),
        decomposition_focus='重点拆解现代都市职场、家庭、法律与社交舆论如何对情感选择施加现实阻力。',
    ),
    'GENRE_GUDAI_YANQING': _profile(
        primary=('foundation', 'institution', 'history', 'resource_market'),
        optional=('items_props', 'ecology_space'),
        preferred_resources=('门第爵位', '嫁妆/田产银钱', '宗族声誉', '内宅/朝堂情报'),
        exchange_media=('银两/地契', '联姻与宗族人情'),
        long_term_constraints=('古代礼法与婚嫁制度', '宗族家长权', '阶层与律法压制'),
        item_emphasis=('信物凭证', '礼制服饰规制'),
        decomposition_focus='重点拆解古代宗法礼教、婚嫁财产制度、内宅权限与阶层规矩如何形成真实外部阻力。',
    ),
    'GENRE_XIANSHI': _profile(
        primary=('foundation', 'institution', 'resource_market', 'ecology_space'),
        optional=('history', 'items_props'),
        preferred_resources=('生计收入', '公共服务/社保/教育资格', '人情网络', '时间精力'),
        exchange_media=('货币', '政策名额/人情互助'),
        long_term_constraints=('经济周期与地域差异', '政策法规与户籍/行业门槛', '生老病死现实约束'),
        item_emphasis=('生活成本载体', '时代变迁印记'),
        decomposition_focus='重点拆解现实社会结构、政策制度、生计成本与时代变迁压力；严格禁止超自然力量与系统机制。',
    ),
    'GENRE_QINGCHUN': _profile(
        primary=('foundation', 'institution'),
        optional=('resource_market', 'items_props', 'ecology_space'),
        preferred_resources=('升学成绩/名额', '课余时间', '零花钱/家庭支持', '同侪口碑'),
        exchange_media=('学习互助/社交认同', '有限零花钱'),
        long_term_constraints=('校规与升学考试周期', '家庭监护边界', '校园小社会舆论'),
        item_emphasis=('青春记忆载体', '日常学习/社团物品'),
        decomposition_focus='重点拆解校园制度、升学时间表、家庭约束与同龄社交规则；避免套用成人权力模型或超自然规则。',
    ),
    'GENRE_ERCIYUAN': _profile(
        primary=('foundation', 'power_energy', 'special_mechanism', 'institution', 'items_props', 'race_construct'),
        optional=('resource_market', 'ecology_space', 'history'),
        preferred_resources=('特色能力/契约', '学院/组织积分', '专属武装/道具', '羁绊与情报'),
        exchange_media=('组织积分/点数', '契约条件'),
        long_term_constraints=('能力发动条件与反噬', '学院/世界秩序规则', '立场阵营对立'),
        item_emphasis=('专属设定标识', '能力增幅与限制', '象征化'),
        decomposition_focus='重点拆解高概念世界前提（70%日常熟悉+30%核心异能/规则）、能力发动条件与组织秩序边界。',
    ),
    'GENRE_QINGXIAOSHUO': _profile(
        primary=('foundation', 'special_mechanism', 'power_energy', 'institution', 'items_props'),
        optional=('race_construct', 'resource_market', 'ecology_space', 'history'),
        preferred_resources=('技能/天赋点', '日常/冒险经费', '特化道具', '社团/公会权限'),
        exchange_media=('通用货币/点数', '委托报酬'),
        long_term_constraints=('核心异常设定的硬约束', '日常伪装与暴露风险', '能力冷却/代价'),
        item_emphasis=('高辨识度功能', '反差代价', '日常与非日常桥梁'),
        decomposition_focus='重点拆解“核心奇点规则”如何与日常秩序碰撞，保持前3章可快速理解且后续不自相矛盾。',
    ),
    'GENRE_TONGREN': _profile(
        primary=('foundation', 'power_energy', 'institution', 'history', 'items_props', 'special_mechanism'),
        optional=('race_construct', 'resource_market', 'ecology_space'),
        preferred_resources=('原典世界核心资源', '先知情报窗口', '组织权限', '关键道具'),
        exchange_media=('原典通用交换媒介', '情报/战力互换'),
        long_term_constraints=('原典既有世界硬规则', '蝴蝶效应与时间线惯性', '不可越界的力量上限'),
        item_emphasis=('原典既定功能边界', '归属与获取节点'),
        decomposition_focus='重点拆解既有世界硬规则、时间线节点约束与改动世界后触发的连锁反作用边界。',
    ),
    'GENRE_ZHUTIAN': _profile(
        primary=('foundation', 'special_mechanism', 'power_energy', 'resource_market', 'items_props', 'ecology_space', 'history'),
        optional=('institution', 'race_construct'),
        preferred_resources=('穿梭能源/主神积分', '跨世界功法与科技', '任务权限', '时间流速差'),
        exchange_media=('跨界积分/本源点', '稀有跨界物资'),
        long_term_constraints=('跨界兼容/压制规则', '停留时限与回归代价', '高维规则惩罚'),
        item_emphasis=('跨世界兼容性', '能量补给边界', '带出限制'),
        decomposition_focus='重点拆解穿梭触发条件、跨世界力量/物资产出兼容与削弱规则、积分兑换率及回归惩罚边界。',
    ),
    'GENRE_MOSHI': _profile(
        primary=('foundation', 'resource_market', 'ecology_space', 'items_props', 'institution', 'history'),
        optional=('power_energy', 'race_construct', 'special_mechanism'),
        preferred_resources=('食物', '水', '药品', '弹药', '燃料'),
        exchange_media=('食物', '弹药', '药品'),
        long_term_constraints=('安全据点', '生存技能', '可靠伙伴', '污染/灾变环境与物资腐败'),
        item_emphasis=('生存必需', '耐久性', '便携性', '临时占有归属'),
        decomposition_focus='重点拆解灾变后物理环境恶化、基础生存物资消耗速率、据点防御制度与异变/污染规则（若有异能再启用力量域）。',
        adaptation_refs=('ADAPT_B_00014', 'ADAPT_B_00015', 'ADAPT_B_00028', 'ADAPT_B_00032', 'ADAPT_B_00063'),
    ),
    'GENRE_SAIBO': _profile(
        primary=('foundation', 'special_mechanism', 'institution', 'resource_market', 'items_props', 'ecology_space', 'race_construct'),
        optional=('power_energy', 'history'),
        preferred_resources=('信用点/黑市加密币', '义体/芯片/算力', '企业权限与身份码', '黑市情报', '抑制剂药物'),
        exchange_media=('加密信用点', '黑市情报与硬件'),
        long_term_constraints=('巨企垄断与阶层隔离', '义体排异/赛博精神病代价', '全天候监控网络'),
        item_emphasis=('义体兼容与损耗', '网络攻防边界', '追踪与反追踪代价'),
        decomposition_focus='重点拆解“高科技低生活”下的巨企垄断制度、网络监控规则、义体改造排异代价与黑市流通链。',
    ),
    'GENRE_WEILAI': _profile(
        primary=('foundation', 'special_mechanism', 'institution', 'ecology_space', 'resource_market', 'items_props', 'history'),
        optional=('power_energy', 'race_construct'),
        preferred_resources=('清洁能源/生态配额', '高阶技术/AI算力', '公民信用等级', '星际/地下居住权'),
        exchange_media=('数字配额/信用点', '技术许可'),
        long_term_constraints=('技术伦理与社会治理边界', '资源与环境再生周期', '系统故障代价'),
        item_emphasis=('智能化程度', '维护依赖', '阶层准入限制'),
        decomposition_focus='重点拆解未来社会制度演化、核心技术带来的新稀缺性、空间形态变化与乌托邦/反乌托邦张力。',
    ),
    'GENRE_TONGHUA': _profile(
        primary=('foundation', 'items_props', 'ecology_space'),
        optional=('race_construct', 'power_energy', 'institution', 'history'),
        preferred_resources=('契约/诺言', '象征性魔法物件', '勇气/善意代价', '秘密路径'),
        exchange_media=('承诺与交换代价', '象征信物'),
        long_term_constraints=('寓言式铁律（违约必受罚）', '魔法时限（如午夜失效）', '纯真/贪欲边界'),
        item_emphasis=('象征意义', '明确使用条件与失效时限'),
        decomposition_focus='重点拆解简洁而不可违背的寓言式规则、契约代价与魔法物件的触发/失效条件。',
    ),
    'GENRE_ERTONG': _profile(
        primary=('foundation', 'items_props'),
        optional=('institution', 'ecology_space', 'race_construct', 'power_energy'),
        preferred_resources=('日常探索工具', '伙伴互助', '时间与零花钱', '好奇心线索'),
        exchange_media=('分享与约定', '小物件互换'),
        long_term_constraints=('安全与适龄边界', '家庭/学校生活规律', '简单清晰的可理解规则'),
        item_emphasis=('趣味功能', '易懂边界', '成长象征'),
        decomposition_focus='重点拆解清晰易懂的生活或幻想规则边界，保持规则直观且前后一致。',
    ),
    'GENRE_JISHI': _profile(
        primary=('foundation', 'history', 'institution', 'resource_market'),
        optional=('ecology_space', 'items_props'),
        preferred_resources=('真实史料/档案', '预算与实地条件', '制度许可', '时间周期'),
        exchange_media=('现实经济与公共资源', '事实依据'),
        long_term_constraints=('客观史实与时间线不可篡改', '真实地理与法律制度', '可核查来源边界'),
        item_emphasis=('真实时代器物', '物证档案价值'),
        decomposition_focus='重点拆解真实时代背景、机构运作程序与物质条件限制；严禁引入虚构力量或超自然机制。',
    ),
    'GENRE_ZHIYE': _profile(
        primary=('foundation', 'institution', 'resource_market', 'items_props'),
        optional=('ecology_space', 'history'),
        preferred_resources=('专业资质/职级', '项目预算与资源配额', '行业人脉与口碑', '核心技能/案例数据'),
        exchange_media=('薪酬/绩效/股权', '行业信誉与项目机会'),
        long_term_constraints=('行业法规与SOP流程', 'KPI/晋升通道瓶颈', '专业技术与时间极限'),
        item_emphasis=('专业工具/设备标准', '合规与失误成本'),
        decomposition_focus='重点拆解真实行业规则、专业流程SOP、职级晋升门槛与资源审批链如何构成阻力与爽点。',
    ),
    'GENRE_NVXING': _profile(
        primary=('foundation', 'institution', 'resource_market'),
        optional=('ecology_space', 'history', 'items_props'),
        preferred_resources=('经济自主权', '职业/教育机会', '社会支持网络', '话语权与时间'),
        exchange_media=('金钱', '平等合作与互助信誉'),
        long_term_constraints=('职场/家庭隐性规则', '社会评价标准', '法律与经济现实压力'),
        item_emphasis=('独立生活载体', '职业工具与象征物'),
        decomposition_focus='重点拆解现实社会分工、职场/家庭制度期待与经济独立门槛如何制约并倒逼角色成长。',
    ),
    'GENRE_JIATING': _profile(
        primary=('foundation', 'institution', 'resource_market'),
        optional=('history', 'items_props'),
        preferred_resources=('家庭财产/房产/存款', '照护精力与时间', '亲属舆论与话语权', '继承/监护资格'),
        exchange_media=('金钱/产权', '亲情付出与责任分担'),
        long_term_constraints=('婚姻继承法与伦理规范', '代际经济依赖', '居住空间与生活开支'),
        item_emphasis=('房产契约/家产物件', '家族记忆载体'),
        decomposition_focus='重点拆解家庭经济结构、代际责任分工、法律产权与伦理规范如何持续制造两难处境。',
    ),
    'GENRE_GONGTING': _profile(
        primary=('foundation', 'institution', 'history', 'resource_market', 'ecology_space'),
        optional=('items_props',),
        preferred_resources=('皇权恩宠/圣旨', '官职爵位与兵权', '朝堂派系/外戚人脉', '密探情报', '府库钱粮'),
        exchange_media=('官爵利益', '派系站队筹码', '银钱密档'),
        long_term_constraints=('祖制礼法与宫规', '君臣猜忌制衡', '宗室/士族/宦官多方牵制'),
        item_emphasis=('印信虎符/密诏', '礼制僭越红线', '毒物/证物痕检'),
        decomposition_focus='重点拆解朝堂/后宫权力制衡机制、祖制礼法红线、信息传递与密探代价及派系利益循环。',
    ),
    'GENRE_SHEHUI': _profile(
        primary=('foundation', 'institution', 'resource_market', 'ecology_space', 'items_props'),
        optional=('history',),
        preferred_resources=('司法/媒体调查渠道', '涉案资金流与档案', '利益链关系网', '证人保护与舆论窗口'),
        exchange_media=('利益输送', '沉默筹码', '公开舆论压力'),
        long_term_constraints=('制度盲区与程序壁垒', '阶层权力不对等', '取证时效与物理事实'),
        item_emphasis=('财务/电子/物理证物', '程序合规与销毁痕迹'),
        decomposition_focus='重点拆解案件背后的社会制度漏洞、利益链运转逻辑、取证阻力与现实阶层压迫；严禁引入超自然设定。',
    ),
}


def _resolve_main_genres(types: list[str] | tuple[str, ...] | None) -> tuple[list[str], list[str]]:
    if not types:
        return [], []
    normalized = canonical_types(list(types))
    mapping = type_map()
    mains: list[str] = []
    for tid in normalized:
        parent = mapping.get(tid, {}).get('parent_id')
        main_id = parent or tid
        if main_id not in mains:
            mains.append(main_id)
    return normalized, mains


def _out_of_scope_note(cat_id: str, type_names: list[str]) -> str:
    joined = ' / '.join(type_names) if type_names else '当前所选类型'
    if cat_id == 'power_energy':
        return f'当前类型（{joined}）通常不包含超自然力量或能量修炼公式；仅在明确叠加超自然副类型或硬核科技能源设定时按需展开。'
    if cat_id == 'race_construct':
        return f'当前类型（{joined}）以常规人类社会为主，非人种族与超凡生理构造属于跨类型扩展项，避免无故跨题材污染。'
    if cat_id == 'special_mechanism':
        return f'当前类型（{joined}）默认不依赖系统/平行世界/VR/游戏化框架；除非立项明确引入特殊顶层机制，否则无需展开。'
    return f'此分类在 {joined} 中属于跨类型扩展项，仅在作品明确需要时按需启用。'


def world_profile_for_types(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Build the genre-targeted world material profile with strict step boundaries."""
    normalized, mains = _resolve_main_genres(types)
    mapping = type_map()
    type_objs = [{'id': tid, 'name': mapping[tid]['name'], 'parent_id': mapping[tid].get('parent_id')}
                 for tid in normalized if tid in mapping]
    main_names = [mapping[mid]['name'] for mid in mains if mid in mapping]

    if not mains:
        profiles = [DEFAULT_WORLD_PROFILE]
    else:
        profiles = [GENRE_WORLD_PROFILES.get(mid, DEFAULT_WORLD_PROFILE) for mid in mains]

    # Merge relevance across multi-genre selection: primary > optional > out_of_scope.
    relevance_by_cat: dict[str, str] = {}
    for cat in WORLD_CATEGORIES:
        cid = cat['id']
        best = 'out_of_scope'
        for prof in profiles:
            if cid in prof['primary']:
                best = 'primary'
                break
            if cid in prof['optional'] and best != 'primary':
                best = 'optional'
        relevance_by_cat[cid] = best

    # Merge resource profile preserving primary genre order first.
    merged_resource: dict[str, list[str]] = {
        'preferred_resources': [],
        'exchange_media': [],
        'long_term_constraints': [],
        'item_emphasis': [],
        'type_adaptation_refs': [],
    }
    focuses: list[str] = []
    for prof in profiles:
        rp = prof['resource_profile']
        for field in merged_resource:
            for item in rp.get(field, ()):
                if item not in merged_resource[field]:
                    merged_resource[field].append(item)
        if prof['decomposition_focus'] not in focuses:
            focuses.append(prof['decomposition_focus'])

    categories: list[dict[str, Any]] = []
    for cat in WORLD_CATEGORIES:
        cid = cat['id']
        rel = relevance_by_cat[cid]
        entry = {
            'id': cid,
            'name': cat['name'],
            'short_name': cat['short_name'],
            'description': cat['description'],
            'usage_mode': cat['usage_mode'],
            'source_files': list(cat['source_files']),
            'catalog_group_key': cat['catalog_group_key'],
            'network_policies': list(cat['network_policies']),
            'relevance': rel,
            'relevance_label': RELEVANCE_LABELS[rel],
            'boundary_note': _out_of_scope_note(cid, main_names) if rel == 'out_of_scope' else cat['usage_mode'],
        }
        categories.append(entry)

    categories.sort(key=lambda row: (RELEVANCE_RANK[row['relevance']], WORLD_CATEGORY_ORDER[row['id']]))
    return {
        'types': type_objs,
        'main_types': [{'id': mid, 'name': mapping[mid]['name']} for mid in mains if mid in mapping],
        'has_genre_binding': bool(mains),
        'primary_categories': [c['id'] for c in categories if c['relevance'] == 'primary'],
        'optional_categories': [c['id'] for c in categories if c['relevance'] == 'optional'],
        'out_of_scope_categories': [c['id'] for c in categories if c['relevance'] == 'out_of_scope'],
        'categories': categories,
        'resource_profile': merged_resource,
        'decomposition_focus': '；'.join(focuses),
        'step_boundary': deepcopy(WORLD_STEP_BOUNDARY),
    }


def annotate_world_groups(groups: list[dict[str, Any]], types: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Annotate catalog world option groups with genre relevance and sort primary-first."""
    profile = world_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    annotated: list[dict[str, Any]] = []
    for group in groups:
        row = deepcopy(group)
        cat_id = row['key'].removeprefix('world.group.')
        meta = by_id.get(cat_id)
        if meta:
            row.update(
                world_category=cat_id,
                description=meta['description'],
                usage_mode=meta['usage_mode'],
                relevance=meta['relevance'],
                relevance_label=meta['relevance_label'],
                boundary_note=meta['boundary_note'],
                source_files=meta['source_files'],
            )
        annotated.append(row)
    annotated.sort(key=lambda r: (
        RELEVANCE_RANK.get(r.get('relevance', 'optional'), 1),
        WORLD_CATEGORY_ORDER.get(r.get('world_category', ''), 99),
    ))
    return annotated


def classify_world_method(body: dict[str, Any]) -> list[str]:
    """Deterministically classify a world_design method into matching world material categories."""
    if not isinstance(body, dict):
        return []
    tasks = set(body.get('tasks') or ())
    outputs = body.get('outputs') or ()
    targets_world = 'world_rules' in tasks or any(
        isinstance(o, dict) and o.get('stage') == 'world_design' for o in outputs
    )
    if not targets_world:
        return []
    parts = [
        str(body.get('title') or ''),
        ' '.join(str(x) for x in (body.get('applicability') or ())),
        ' '.join(str(o.get('instruction') or '') for o in (body.get('operations') or ()) if isinstance(o, dict)),
        ' '.join(str(o.get('description') or '') for o in outputs if isinstance(o, dict)),
    ]
    text = ' '.join(parts)
    scores: list[tuple[int, int, str]] = []
    for cat in WORLD_CATEGORIES:
        hits = sum(1 for kw in cat['keywords'] if kw in text)
        if hits:
            scores.append((-hits, WORLD_CATEGORY_ORDER[cat['id']], cat['id']))
    if not scores:
        return ['foundation']
    scores.sort()
    return [cid for _, _, cid in scores[:3]]


def world_decomposition_prompt(types: list[str] | tuple[str, ...] | None = None, *, phase: str = 'relations') -> str:
    """Concise genre-targeted guidance for decomposing/deriving world_rules without cross-step leakage."""
    profile = world_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    primary_names = '、'.join(by_id[cid]['short_name'] for cid in profile['primary_categories'])
    oos_names = '、'.join(by_id[cid]['short_name'] for cid in profile['out_of_scope_categories'])
    rp = profile['resource_profile']
    type_label = ' / '.join(t['name'] for t in profile['main_types']) or '当前参考书'
    if phase == 'methods':
        text = (
            f'【03世界设计·分类型资料边界（{type_label}）】'
            f'本类型核心世界资料子域：{primary_names}；'
            f'典型资源口径：{"、".join(rp["preferred_resources"][:5])}。'
        )
        if oos_names:
            text += f'非本类型常规子域（{oos_names}）除非原作明确存在且有直接引文，否则不要强行套用。'
        text += (
            '严格守住 03 世界设计步骤边界：只提炼外部世界规则、限制、代价与未知边界，'
            '不把单个人物成长弧光（04）、私人恩怨（05）或章纲结局（06）混入世界卡。'
        )
        return text
    text = (
        f'【03世界设计·按本书类型（{type_label}）定向核对world_rules】'
        f'优先检索本类型核心世界规则域（{primary_names}）及关键资源/制约（{"、".join(rp["preferred_resources"][:5])}）：'
        f'{profile["decomposition_focus"]}'
    )
    if oos_names:
        text += f'非本类型常规项（{oos_names}）仅在原文确有直接证据时记录，切勿为凑项脑补。'
    text += '严格区分外部世界规则与角色个人性格/剧情结局：没有改变人物选择或造成真实后果的背景闲笔不强行归入世界规则。'
    return text


def world_stage_prompt_packet(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Compact deterministic packet frozen into planning manifests for stage == 'world_design'."""
    profile = world_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    return {
        'types': [{'id': t['id'], 'name': t['name']} for t in profile['types']],
        'primary_categories': [
            {'id': cid, 'name': by_id[cid]['name'], 'usage_mode': by_id[cid]['usage_mode']}
            for cid in profile['primary_categories']
        ],
        'optional_categories': [
            {'id': cid, 'name': by_id[cid]['name']}
            for cid in profile['optional_categories']
        ],
        'out_of_scope_categories': [
            {'id': cid, 'name': by_id[cid]['name'], 'boundary_note': by_id[cid]['boundary_note']}
            for cid in profile['out_of_scope_categories']
        ],
        'resource_profile': profile['resource_profile'],
        'step_boundary': {
            'responsibility': WORLD_STEP_BOUNDARY['responsibility'],
            'out_of_scope': list(WORLD_STEP_BOUNDARY['out_of_scope']),
            'downstream_steps': [d['step_id'] for d in WORLD_STEP_BOUNDARY['downstream_steps']],
        },
    }


def world_blueprint(library: Any, types: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Combine genre-targeted world material profile with live workspace world-method coverage."""
    from nw.studio.downstream_handoff import audit_downstream_handoff

    profile = world_profile_for_types(types)
    audit = audit_downstream_handoff(library, types=list(types), planning_hierarchy=True)
    world_methods = [
        m for m in audit.get('methods', ())
        if 'world_rules' in m.get('tasks', ()) or 'world_design' in m.get('output_stages', ())
    ]
    by_cat_receivable: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in WORLD_CATEGORIES}
    by_cat_draft: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in WORLD_CATEGORIES}
    by_cat_blocked: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in WORLD_CATEGORIES}

    for method in world_methods:
        cats = method.get('world_categories') or ['foundation']
        brief = {
            'id': method['id'],
            'version': method['version'],
            'title': method['title'],
            'status': method['status'],
            'scopes': method['scopes'],
            'book_title': method.get('book_title', ''),
            'block_reasons': method.get('block_reasons', [])[:2],
        }
        for cid in cats:
            if cid not in by_cat_receivable:
                continue
            if method['status'] in ('receivable', 'inactive_by_policy'):
                by_cat_receivable[cid].append(brief)
            elif method['status'] == 'draft':
                by_cat_draft[cid].append(brief)
            else:
                by_cat_blocked[cid].append(brief)

    categories_with_coverage: list[dict[str, Any]] = []
    covered_primary = 0
    for cat in profile['categories']:
        cid = cat['id']
        rec = by_cat_receivable[cid]
        drf = by_cat_draft[cid]
        blk = by_cat_blocked[cid]
        if cat['relevance'] == 'primary' and rec:
            covered_primary += 1
        categories_with_coverage.append({
            **cat,
            'receivable_methods': rec,
            'draft_methods': drf,
            'blocked_methods': blk,
            'receivable_count': len(rec),
            'draft_count': len(drf),
            'blocked_count': len(blk),
        })

    return {
        **profile,
        'categories': categories_with_coverage,
        'coverage_summary': {
            'total_world_methods': len(world_methods),
            'receivable_world_methods': sum(1 for m in world_methods if m['status'] in ('receivable', 'inactive_by_policy')),
            'draft_world_methods': sum(1 for m in world_methods if m['status'] == 'draft'),
            'blocked_world_methods': sum(1 for m in world_methods if m['status'] == 'blocked'),
            'primary_category_count': len(profile['primary_categories']),
            'covered_primary_categories': covered_primary,
            'gap_primary_categories': [
                c['id'] for c in categories_with_coverage
                if c['relevance'] == 'primary' and c['receivable_count'] == 0
            ],
            'book_world_ready': audit['summary']['book_world_ready'],
            'cast_sample_ready': audit['summary']['cast_sample_ready'],
        },
        'cast_samples': audit['cast_samples'],
        'originality_audit': audit['originality_audit'],
    }
