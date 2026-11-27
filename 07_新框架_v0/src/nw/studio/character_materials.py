"""Genre-targeted character & static-relations material taxonomy, step boundaries, and coverage audit.

Organizes the original workflow's 04 `character_design` and 05 `static_relations` materials
(`character_design*.py` and `static_relations*.py`) into 10 bounded, non-overlapping sub-categories
with explicit stage ownership (`character_design` vs `static_relations`), maps all 35 main genres
(and subgenres) to primary / optional / out-of-scope categories and cast/relation profiles, and
connects upstream corpus decomposition (`character_arc`, `cast_entry`, `cast_roster`) and
`03 world_design` (`cast_demands`, social/world rules) straight into `04`, `05`, and `06-09`.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.studio.catalog import canonical_types, type_map


CHARACTER_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'character_design',
    'order': 4,
    'name': '04. 人物动机与弧线',
    'responsibility': (
        '承接 01–03 的类型承诺、世界规则与剧情用人需求（cast_demands），坚持复用已有角色优先，'
        '为确需出场的人物确立公开身份、隐藏层与揭晓凭据、独立目标、剧情职责、认知与伦理立场、'
        '人格外化与声线、能力边界及初始状态。'
    ),
    'upstream_steps': [
        {'step_id': 'type_selection', 'name': '01. 类型判定与承诺', 'provides': '题材对主角/反派/配角定位的读者期待'},
        {'step_id': 'type_adaptation', 'name': '02. 类型组合与适配', 'provides': '人物身份防覆盖规则（CONFLICT_B_004）与适配重点'},
        {'step_id': 'world_design', 'name': '03. 世界设定与限制', 'provides': '社会阶层、职业权限、能力/资源上限与冻结的 cast_demands'},
        {'step_id': 'corpus:character_cast', 'name': '参考拆解 · 人物/出场/阵容', 'provides': '同类型人物弧光、配角复用方法与实见人物数量分布样本'},
    ],
    'downstream_steps': [
        {'step_id': 'static_relations', 'name': '05. 静态关系与张力', 'consumes': '已确立的人物实体 key、身份立场、利益诉求与知情边界'},
        {'step_id': 'plot_design', 'name': '06. 剧情因果与伏笔', 'consumes': '主角核心欲望/执念、反派阻力逻辑、配角独立目标与 cast_assignments'},
        {'step_id': 'action_design', 'name': '08. 行动博弈与试错代价', 'consumes': 'capabilities 能力门槛、限制代价与心理/认知盲点'},
        {'step_id': 'scene_design', 'name': '09. 场景结构与POV边界', 'consumes': 'casting 入场方式、暗身份线索/触发凭据与人物知情边界'},
        {'step_id': 'expression_design', 'name': '13. 叙述距离与表达设计', 'consumes': 'voice 嗓音口吻、三层人格外化锚点与首出场描写依据'},
        {'step_id': 'review', 'name': '16. 独立审稿与证据核验', 'consumes': '角色声线一致性、暗身份防偷跑与能力上限核验'},
    ],
    'allowed_outputs': [
        {'field': 'members', 'kind': 'character', 'description': '人物卡（name/role/want/visibility/casting/independent_goal/behavior/voice/boundaries 等）'},
        {'field': 'states', 'kind': 'list[object]', 'description': '人物初始候选状态（身体/精神/立场/持有物等前值）'},
        {'field': 'capabilities', 'kind': 'list[object]', 'description': '人物可行动性与能力清单、依据及硬限制'},
        {'field': 'cast_assignments', 'kind': 'list[object]', 'description': '（启用阵容需求策略时）逐项分派已冻结 cast_demands 到复用或新建人物'},
    ],
    'in_scope': [
        '主角、反派、重要/次要/功能/背景/缺席角色分层，坚持复用优先、禁止按配额硬造人',
        '人物外貌/嗓音/性格/三层人格外化（表层社交面具、中层习惯流露、深层压力暴露）',
        '欲望层级、执念、独立目标（须与剧情职责 scene_function 区分）、变化条件与弧光方向',
        '背景身份三层结构（表层/隐藏/被动）、职业身份、初始状态与能力上限/代价',
        '认知偏差、心智模型盲点、意志品质与道德判断/立场',
        '入场方式（opening/self/other/visible/withheld），暗身份 secret/trigger 严格隔离',
        '（仅适配题材）命运态度、血脉/天赋/基因/无敌机制与超凡能量/种族构造上限',
    ],
    'out_of_scope': [
        '不得推翻 01–03 的类型边界或世界硬规则，不得以类型适配覆盖已有角色身份（CONFLICT_B_004）',
        '不得脱离 cast_demands 或仅为了凑同类型样本人数配额而凭空造工具人',
        '不得把暗身份 secret/trigger 泄露进人物公开字段（name/role/clue/public_identity）',
        '不得在单人卡中替代 05 静态关系编写复杂的多人关系网、派系张力或跨实体约束',
        '不得提前写死具体分章情节结果与大结局（归 06 剧情）或代替 13 表达设计规定具体文风句式',
        '现实/都市日常/纯悬疑推理/纯言情/历史/职场/家庭等非超自然题材，不得引入血脉/基因/灵气等超凡能力机制',
    ],
}


STATIC_RELATIONS_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'static_relations',
    'order': 5,
    'name': '05. 静态关系与张力',
    'responsibility': (
        '仅使用 03 世界实体与 04 已确立的人物实体作为关系两端，构建亲缘/社会/情感关系网、'
        '配角间独立互动连接（全书至少 2 条不经过主角）、权力与信息不对称、情感债务、'
        '信任/亲密光谱、情感错位、结构性对立与势力/阶层张力，并将关系约束整理为下游 requirements。'
    ),
    'upstream_steps': [
        {'step_id': 'world_design', 'name': '03. 世界设定与限制', 'provides': '社会阶层、权力结构、资源流、势力格局与空间制度'},
        {'step_id': 'character_design', 'name': '04. 人物动机与弧线', 'provides': '已确立的人物实体、独立目标、背景身份、立场与知情边界'},
        {'step_id': 'corpus:relations', 'name': '参考拆解 · 人物/出场/支线', 'provides': '关系网构造、配角独立互动与不对称张力的可迁移方法'},
    ],
    'downstream_steps': [
        {'step_id': 'plot_design', 'name': '06. 剧情因果与伏笔', 'consumes': '结构性对立、情感债务、配角独立互动支线与升级触发条件'},
        {'step_id': 'event_design', 'name': '07. 事件链与候选分支', 'consumes': '势力自动互动与多方立场碰撞产生的候选事件条件'},
        {'step_id': 'action_design', 'name': '08. 行动博弈与试错代价', 'consumes': '权力/信息不对称、合作/竞争/同盟门槛与施压筹码'},
        {'step_id': 'scene_design', 'name': '09. 场景结构与POV边界', 'consumes': '同场双方当前信任度、亲密距离、情感错位与可披露差值'},
        {'step_id': 'state_transition', 'name': '10. 状态变化与外部因果', 'consumes': '关系初始基调与光谱基线（供后续背叛/和解前后对照）'},
        {'step_id': 'state_propagation', 'name': '11. 状态传播与连锁感知', 'consumes': '关系网络拓扑与势力/社交信息传导路径'},
    ],
    'allowed_outputs': [
        {'field': 'relations', 'kind': 'list[object]', 'description': '静态关系条（id, source, target, relation, condition），端点须为真实已建实体'},
        {'field': 'requirements', 'kind': 'list[object]', 'description': '面向下游步骤的关系设计约束（target_stage, constraint, project_refs），不虚构读者实体'},
    ],
    'in_scope': [
        '角色关系网拓扑：核心人物连接数与至少 2 条不经过主角的配角间独立互动关系',
        '亲缘、社会（竞争/旁观/合作/同盟）、情感关系与主配角 8 类关系定位',
        '权力不对称、信息不对称、情感债务、信任-怀疑光谱、距离-亲密光谱与立场位置',
        '情感错位（A 与 B 投入不对等）及高质量多维对立关系设计（利益/立场/价值观/情感/存在）',
        '势力自动互动、势力间持续张力、资源流依赖、阶层隶属与空间权力关系',
        '（仅适配题材）多种族社会嵌入与种族间结构性张力',
    ],
    'out_of_scope': [
        '不得凭空新建 04 人物设计尚未建立的人物实体，不得篡改人物卡已有核心目标与能力',
        '不得把尚未在剧情中发生的背叛、决裂、和解写成既成事实（仅记录当前基线、张力与触发条件，实际改变归 06 剧情 / 10 状态变化）',
        '不得虚构“读者”作为书内 relations 实体（涉及读者情绪/期待的关系规则须转成 requirements 交给下游）',
        '现实/都市/纯悬疑推理/历史/言情等单一常规人类社会题材，不得引入非人种族嵌入与种族张力',
    ],
}


CHARACTER_CATEGORIES: tuple[dict[str, Any], ...] = (
    {
        'id': 'core_drive',
        'target_stage': 'character_design',
        'target_stage_label': '04 人物设计',
        'name': '核心定位、属性、欲望执念与弧光',
        'short_name': '定位与欲望弧光',
        'description': '确立主角/反派/配角定位、外貌嗓音性格、欲望层级、执念、野心、责任、冲动、情绪管控与弧光演变方向。',
        'usage_mode': '04 人物设计全题材底座：写明“他想要什么、为什么非做不可、什么条件会逼他改变”。',
        'source_files': ['character_design.py (§1–§4)'],
        'catalog_group_key': 'character.group.core_drive',
        'keywords': ('主角', '反派', '动机', '欲望', '执念', '野心', '弧光', '性格', '外貌', '嗓音', '成长', '信念', '缺陷', '创伤'),
    },
    {
        'id': 'supporting_cast',
        'target_stage': 'character_design',
        'target_stage_label': '04 人物设计',
        'name': '配角层级、反派逻辑、人格外化与背景身份',
        'short_name': '配角与身份外化',
        'description': '涵盖配角功能分类、镜像/不可替代性、防工具化、五级出场分类、爆款反派逻辑、三层人格外化（表/中/深）、三层背景身份及团队机制。',
        'usage_mode': '04 人物设计核心：配合 cast_demands 与同类型人数样本，确保每个重要配角具备独立目标、不可替代性与标志性外化锚点。',
        'source_files': ['character_design_supporting.py (§121, §123.20, 板块144/146/151)', 'character_design_plot_mechanisms.py (TEAM)'],
        'catalog_group_key': 'character.group.supporting_cast',
        'keywords': ('配角', '工具化', '不可替代', '镜像', '反派', '出场', '阵容', '复用', '外化', '背景身份', '伪装', '暗身份', '伏笔身份', '团队', '辨识度'),
    },
    {
        'id': 'cognition_ethics',
        'target_stage': 'character_design',
        'target_stage_label': '04 人物设计',
        'name': '认知偏差、心智模型、意志与道德立场',
        'short_name': '认知与道德立场',
        'description': '覆盖 9 类认知偏差（确认偏误/沉没成本/认知失调等）、心智模型固化与盲点、9 项意志品质以及是非/善恶/正义/利己/利他/功利/义务道德取舍。',
        'usage_mode': '04 人物设计进阶：解释人物为何会在高压下做出有缺陷却合情理的判断，直接赋能 08 行动博弈与人物立体感。',
        'source_files': ['character_design_cognition.py (板块68–70)', 'character_design_ethics.py (板块74–75)'],
        'catalog_group_key': 'character.group.cognition_ethics',
        'keywords': ('认知', '偏误', '盲点', '心智模型', '自我欺骗', '意志', '胆量', '道德', '伦理', '是非', '正义', '利己', '利他', '功利', '底线', '原则', '抉择'),
    },
    {
        'id': 'status_profession',
        'target_stage': 'character_design',
        'target_stage_label': '04 人物设计',
        'name': '初始状态、职业定位与技能边界',
        'short_name': '状态与职业能力',
        'description': '定义人物开场身体/精神/正负初始状态、职业与身份/能力/社会位置/价值积累的绑定，以及现实或世界允许的技能边界。',
        'usage_mode': '04 人物设计承接 03 世界制度：把职业权限与开场状态落到 capabilities 与 states，避免人物无依据“开挂”。',
        'source_files': ['character_design.py (§8, §39, §40.5)'],
        'catalog_group_key': 'character.group.status_profession',
        'keywords': ('状态', '伤势', '精神状态', '职业', '技能', '权限', '专长', '身份关系', '能力边界', '初始状态', '行为依据'),
    },
    {
        'id': 'fate_attitude',
        'target_stage': 'character_design',
        'target_stage_label': '04 人物设计',
        'name': '命运态度（抗争/接受/逃避/利用/超越）',
        'short_name': '命运态度',
        'description': '规定角色面对预言、宿命、天劫或时代洪流时的根本态度（抗争/接受/逃避/利用/超越）及其对核心选择的持续驱动。',
        'usage_mode': '04 人物设计按题材启用：适用于存在宿命/天命/历史大势或预言设定的作品。',
        'source_files': ['character_design_fate.py (板块81)'],
        'catalog_group_key': 'character.group.fate_attitude',
        'keywords': ('命运', '宿命', '预言', '天命', '认命', '抗争', '逆天', '大势'),
    },
    {
        'id': 'supernatural_ability',
        'target_stage': 'character_design',
        'target_stage_label': '04 人物设计',
        'name': '超凡能量、种族构造与血脉/天赋/基因机制',
        'short_name': '超凡能力与血脉',
        'description': '覆盖能量总量/纯度/技巧/感知/等级吸收转化瓶颈、种族与三维度构造上限，以及血脉/天赋/无敌/基因改造机制。',
        'usage_mode': '04 人物设计严格按题材边界启用：仅在世界存在修炼/超凡/异能/基因改造/多种族时开启，写明代价与突破门槛。',
        'source_files': ['character_design.py (§10, §12, §13, §36–§38)', 'character_design_plot_mechanisms.py (BLOODLINE/TALENT/INVINCIBLE/GENE)'],
        'catalog_group_key': 'character.group.supernatural_ability',
        'keywords': ('血脉', '天赋', '无敌', '基因', '灵力', '灵根', '境界', '修为', '能量', '异能', '魔法', '种族', '体质', '构造', '觉醒', '功法'),
    },
    {
        'id': 'relation_network',
        'target_stage': 'static_relations',
        'target_stage_label': '05 静态关系',
        'name': '亲缘/社会/情感关系网与配角独立互动',
        'short_name': '关系网与独立互动',
        'description': '构建全书角色关系图（核心角色≥3连接、至少2条不经过主角的配角独立互动）、亲缘/社会/情感关系、主配角8类关系定位及合作/竞争/同盟。',
        'usage_mode': '05 静态关系全题材底座：让配角之间有独立于主角的真实往来与利益连接，支撑多线交汇。',
        'source_files': ['static_relations.py (§1.7, §5.1–§5.3, §8.4, 板块86)', 'static_relations_supporting.py (§121.5–§121.19)'],
        'catalog_group_key': 'character.group.relation_network',
        'keywords': ('关系网', '亲缘', '家族', '师徒', '盟友', '同盟', '合作', '竞争', '旁观', '配角互动', '独立关系', '社会关系', '情感关系'),
    },
    {
        'id': 'relation_tension',
        'target_stage': 'static_relations',
        'target_stage_label': '05 静态关系',
        'name': '不对称权力/信息、情感债务、光谱与对立错位',
        'short_name': '张力错位与对立',
        'description': '刻画权力不对称、信息不对称、情感债务、信任-怀疑光谱、距离-亲密光谱、立场位置、情感错位（117.4）与多维结构性对立（板块153）。',
        'usage_mode': '05 静态关系核心引擎：用可核查的不对称与多维对立制造“随时可能升级”的张力，交付 06 剧情与 09 场景。',
        'source_files': ['static_relations.py (§5.6–§5.11)', 'static_relations_misalignment.py (§117.4)', 'static_relations_supporting.py (板块153)'],
        'catalog_group_key': 'character.group.relation_tension',
        'keywords': ('不对称', '信息差', '权力差', '情感债务', '亏欠', '信任', '怀疑', '亲密', '疏远', '立场', '错位', '情感错位', '对立', '背叛', '制衡', '张力'),
    },
    {
        'id': 'faction_hierarchy',
        'target_stage': 'static_relations',
        'target_stage_label': '05 静态关系',
        'name': '势力互动、阶层权力、资源依赖与空间权限',
        'short_name': '势力与阶层关系',
        'description': '记录势力自动互动、势力间张力、资源流动与稀缺依赖、阶层隶属、权力决策执行链、职业接触边界与空间权力关系（115.7）。',
        'usage_mode': '05 静态关系承接 03 世界格局：把宏观世界制度与势力映射为具体实体之间的隶属、依存与压制关系。',
        'source_files': ['static_relations.py (§20.3, §22.1–§22.2, §27.3, §33.1/§33.3, §39.4)', 'static_relations_space.py (§115.7)'],
        'catalog_group_key': 'character.group.faction_hierarchy',
        'keywords': ('势力', '派系', '阵营', '阶层', '上下级', '隶属', '资源依赖', '垄断', '空间权力', '领地', '朝堂', '宗门派系', '公司架构'),
    },
    {
        'id': 'racial_relation',
        'target_stage': 'static_relations',
        'target_stage_label': '05 静态关系',
        'name': '种族社会嵌入与种族间结构性张力',
        'short_name': '种族关系张力',
        'description': '界定不同种族在社会结构中的相对位置、通婚/隔离/从属边界以及种族间长期结构性冲突。',
        'usage_mode': '05 静态关系严格按题材边界启用：仅在 03 世界与 04 人物明确存在多种族或异化群体时启用。',
        'source_files': ['static_relations.py (§36.4, §36.6)'],
        'catalog_group_key': 'character.group.racial_relation',
        'keywords': ('种族关系', '种族嵌入', '种族张力', '异族', '人妖', '外星群体', '改造人阶层'),
    },
)

CHARACTER_CATEGORY_MAP: dict[str, dict[str, Any]] = {cat['id']: cat for cat in CHARACTER_CATEGORIES}
CHARACTER_CATEGORY_ORDER: dict[str, int] = {cat['id']: idx for idx, cat in enumerate(CHARACTER_CATEGORIES)}

RELEVANCE_RANK = {'primary': 0, 'optional': 1, 'out_of_scope': 2}
RELEVANCE_LABELS = {
    'primary': '本类型核心',
    'optional': '按需扩展',
    'out_of_scope': '非本类型常规项',
}


def _cprofile(
    primary: tuple[str, ...],
    optional: tuple[str, ...],
    *,
    archetype_focus: str,
    relation_focus: str,
    antagonist_pattern: str,
    decomposition_focus: str,
    adaptation_refs: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        'primary': primary,
        'optional': optional,
        'cast_profile': {
            'archetype_focus': archetype_focus,
            'relation_focus': relation_focus,
            'antagonist_pattern': antagonist_pattern,
            'type_adaptation_refs': list(adaptation_refs),
        },
        'decomposition_focus': decomposition_focus,
    }


DEFAULT_CHARACTER_PROFILE = _cprofile(
    primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
    optional=('faction_hierarchy', 'fate_attitude', 'supernatural_ability', 'racial_relation'),
    archetype_focus='明确主角执念、配角独立目标与不可替代性，按剧情需求复用既有角色，不按人数凑角。',
    relation_focus='建立核心人物至少 3 条连接与 ≥2 条不经过主角的独立配角关系，以信息/权力不对称制造张力。',
    antagonist_pattern='反派须有独立行动逻辑、可理解动机及至少一项维度优势，避免扁平工具人。',
    decomposition_focus='重点拆解人物核心欲望与底线变化、配角入场职责与复用方式、人物间不对称张力及各章实际出场人数分布。',
)


# Covers all 35 main genres from nw.studio.catalog.genres().
GENRE_CHARACTER_PROFILES: dict[str, dict[str, Any]] = {
    'GENRE_XUANHUAN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'supernatural_ability', 'status_profession', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy', 'racial_relation'),
        optional=('cognition_ethics',),
        archetype_focus='主角高阶成长执念 + 体质/血脉/天赋优势与对应代价，配角按宗门/敌对/镜像定位分层。',
        relation_focus='宗门师徒/同门竞争、多势力制衡与种族阶层压迫构成长线张力网。',
        antagonist_pattern='高阶压制型或同代天骄镜像型反派，具备独立修炼资源诉求与宗门背景。',
        decomposition_focus='重点拆解主角成长代价、配角在不同大地图阶段如何退场或复用、宗门与势力关系如何驱动冲突升级。',
    ),
    'GENRE_QIHUAN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'supernatural_ability', 'cognition_ethics', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy', 'racial_relation'),
        optional=('status_profession',),
        archetype_focus='多元种族身份与三层背景负担、魔法/契约代价与信念冲突，强调同伴团队各司其职。',
        relation_focus='种族社会嵌入、教会/王国阵营对立、团队内信任光谱与价值分歧。',
        antagonist_pattern='理念/存在型对立反派，与主角共享世界危机却选择截然相反的代价路径。',
        decomposition_focus='重点拆解小队角色不可替代分工、多种族身份张力、信念分歧如何引发内部与外部冲突。',
    ),
    'GENRE_XIANXIA': _cprofile(
        primary=('core_drive', 'supporting_cast', 'supernatural_ability', 'fate_attitude', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('cognition_ethics', 'racial_relation'),
        archetype_focus='道心执念、灵根/寿元/境界限制、三层背景身份（散修/宗门/隐秘传承）与古朴外化锚点。',
        relation_focus='师承因果、宗门派系倾轧、同道资源竞争与道侣/挚友的情感错位或债务。',
        antagonist_pattern='争夺有限灵脉/机缘或道统对立的理性对手，在修为、资源或算计上占优。',
        decomposition_focus='重点拆解角色在长寿与资源争夺下的隐忍抉择、因果债务与师门关系如何跨越多个阶段回收。',
        adaptation_refs=('ADAPT_B_00022', 'CONFLICT_B_004'),
    ),
    'GENRE_WUXIA': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'supernatural_ability', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('fate_attitude',),
        archetype_focus='侠义底线与道德两难（义/利/恩/仇）、武学流派专长与身体伤病代价、鲜明外化口吻。',
        relation_focus='师门情义、江湖恩怨债务、正邪/朝堂立场对立与知己对手的镜像张力。',
        antagonist_pattern='与主角共享江湖规矩却走向极端执念的宿敌或权贵势力首脑。',
        decomposition_focus='重点拆解人物在恩怨与道义间的价值抉择、武学特点如何呼应性格、以及不经过主角的江湖门派互动。',
    ),
    'GENRE_DUSHI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('fate_attitude',),
        archetype_focus='现实职业与社会身份坐标、金钱/人脉/体面焦虑、表层社交面具与深层压力反差。',
        relation_focus='职场上下级权力不对称、家庭与社交人情债、利益同盟与暗中竞争。',
        antagonist_pattern='占据资本、职权、信息或社会话语权优势的现实既得利益者或同行竞品。',
        decomposition_focus='重点拆解都市角色的社会位置与现实顾虑、职场/人情权力不对等如何约束选择；纯都市勿强套血脉/种族规则。',
        adaptation_refs=('ADAPT_B_00023', 'CONFLICT_B_004'),
    ),
    'GENRE_LISHI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='时代出身与士农工商/官阶坐标、忠孝礼法与现实功利碰撞、历史大势下的命运态度。',
        relation_focus='君臣/宗族/门生故吏依附网、朝堂派系自动博弈与世家资源流关系。',
        antagonist_pattern='代表既有时代秩序或敌国/政敌派系利益的精明政治人物，无超自然能力。',
        decomposition_focus='重点拆解符合时代认知的动机边界、宗族/官场关系网及人物在历史洪流中的不可逆选择。',
    ),
    'GENRE_JUNSHI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('fate_attitude',),
        archetype_focus='军衔编制与专业兵种能力边界、战场胆量与创伤应激、团队各岗位不可替代协作。',
        relation_focus='上下级指挥服从与信任光谱、战友生死托付债务、派系/敌我情报不对称。',
        antagonist_pattern='战术素养极高、受自身后勤与战略目标约束的敌军指挥官或内部掣肘者。',
        decomposition_focus='重点拆解团队分工协作、高压下的服从与违令道德困境、指挥链与战场信息差。',
    ),
    'GENRE_KEHUAN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'supernatural_ability', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('fate_attitude', 'racial_relation'),
        archetype_focus='科研/工程/宇航专业能力与技术伦理立场、基因/义体/AI边界带来的自我认同危机。',
        relation_focus='科研共同体/巨企/文明阵营的权力与信息不对称、技术垄断依存与价值观对立。',
        antagonist_pattern='奉行极端功利主义的科学家、资本财团、失控制度或异质文明代表。',
        decomposition_focus='重点拆解技术伦理两难、专业能力边界如何限制解局方式、以及跨组织/跨文明的立场冲突。',
        adaptation_refs=('ADAPT_B_00025', 'CONFLICT_B_004'),
    ),
    'GENRE_XUANYI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('faction_hierarchy', 'fate_attitude'),
        archetype_focus='三层身份（表层/隐藏/被动）与知情边界（boundaries）、确认偏误/盲点与压力下微表情外化。',
        relation_focus='高密度信息不对称、信任-怀疑光谱剧烈摆动、秘密共同体与情感错位。',
        antagonist_pattern='拥有不在场布局、信息优势或制度掩护的高智商局中人，动机须经得起事后回看。',
        decomposition_focus='重点拆解人物隐藏身份的线索与揭晓凭据、谁在何时知道什么、认知偏差如何导致误判；严禁超自然能力混入纯悬疑。',
    ),
    'GENRE_TUILI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('faction_hierarchy',),
        archetype_focus='侦探与嫌疑人清晰的职业/专长/动因、严密时间线行为逻辑与不可欺骗读者的知情边界。',
        relation_focus='封闭嫌疑人群体内的隐秘利害纠葛、旧怨债务、伪证同盟与信息不对称。',
        antagonist_pattern='具备充分作案动机、物理可行手段与心理盲点的理性凶手，绝无超自然设定。',
        decomposition_focus='重点拆解嫌疑人阵容规模控制、人物动机与关系网如何公平埋设线索与误导。',
    ),
    'GENRE_LINGYI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'supernatural_ability', 'fate_attitude', 'relation_network', 'relation_tension'),
        optional=('status_profession', 'faction_hierarchy', 'racial_relation'),
        archetype_focus='直面不可知威胁时的理智/胆量阈值、命格或禁忌媒介代价、隐藏经历与执念弱点。',
        relation_focus='求生临时同盟的脆弱信任光谱、信息隐瞒与牺牲抉择、历史旧怨牵连。',
        antagonist_pattern='受死板禁忌规则约束的诡异存在或利用禁忌谋私的冷酷人祸推手。',
        decomposition_focus='重点拆解人物在恐惧高压下的性格暴露、临时同盟因信息差与自保本能产生的裂痕。',
    ),
    'GENRE_KONGBU': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('fate_attitude', 'supernatural_ability'),
        archetype_focus='极端压力下的深层人格暴露、体能/理智状态损耗、不同维度的胆量与求生本能冲突。',
        relation_focus='孤立环境中的怀疑传染、资源分配不公引发的迅速对立、亲疏关系反转。',
        antagonist_pattern='难以彻底消灭的环境/未知威胁 + 内部因恐慌失控的极端利己者。',
        decomposition_focus='重点拆解高压密闭空间内角色崩坏节奏、人物精简克制与互相猜忌张力。',
    ),
    'GENRE_YOUXI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'status_profession', 'supernatural_ability', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('cognition_ethics', 'fate_attitude', 'racial_relation'),
        archetype_focus='职业/技能树定位、现实身份与游戏马甲双层反差、团队副本分工与数值能力边界。',
        relation_focus='公会派系竞争、固定队合作信任、交易/拍卖利益链与现实-游戏关系交叉。',
        antagonist_pattern='顶级公会会长、版本垄断团队或掌握系统漏洞的高玩宿敌。',
        decomposition_focus='重点拆解角色职业定位差异、小队不可替代分工、公会势力博弈与马甲身份揭晓。',
    ),
    'GENRE_DIANJING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='选手操作风格/版本适配度/心理抗压与手伤年龄边界、战队五人互补性格与声线。',
        relation_focus='队友磨合与信任危机、俱乐部管理层权力不对称、宿敌战队镜像竞争。',
        antagonist_pattern='风格克制、战术纪律严明的冠军强敌或短视功利的俱乐部资本方。',
        decomposition_focus='重点拆解团队成员鲜明辨识度与独立目标、队内摩擦到信任建立的关系演变。',
    ),
    'GENRE_TIYU': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('faction_hierarchy',),
        archetype_focus='身体天赋与伤病极限、训练意志品质（坚韧/忍耐/动摇）、清晰技战术特长与心理短板。',
        relation_focus='师徒传承信任、队内首发名额公平竞争、镜像宿敌互相成就的张力。',
        antagonist_pattern='技术特点互补或资源条件更优的强劲赛场对手，遵守赛规与人体生理底线。',
        decomposition_focus='重点拆解角色克服瓶颈的心理与体能代价、师徒/队友/宿敌三种核心关系张力。',
    ),
    'GENRE_YANQING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'relation_network', 'relation_tension'),
        optional=('status_profession', 'faction_hierarchy', 'fate_attitude'),
        archetype_focus='情感创伤与核心需求、自我保护面具与心软反差、鲜明语言习惯与不可替代情感锚点。',
        relation_focus='距离-亲密光谱推拉、情感错位（117.4）、情感债务、信任裂痕与第三者/家庭外部阻力。',
        antagonist_pattern='制造现实阻隔的家族/阶层利益方或放大双方心结的镜像竞争者。',
        decomposition_focus='重点拆解双主角独立目标与情感防线、情感错位和误解如何在互动中逐步转化而非机械虐恋。',
    ),
    'GENRE_XIANDAI_YANQING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('faction_hierarchy',),
        archetype_focus='现代职业独立性、原生家庭与亲密关系心智模型盲点、日常细节与对话潜台词。',
        relation_focus='都市男女的平等与权力微差、情感错位、社交圈/职场交集与亲密光谱递进。',
        antagonist_pattern='价值观根本分歧的旧爱/职场利益竞争者/施压长辈，保持现实逻辑。',
        decomposition_focus='重点拆解现代职业处境如何牵动感情节奏、双方知情差与情感债务的真实拉扯。',
    ),
    'GENRE_GUDAI_YANQING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='门第出身与三层身份束缚、礼教下的隐忍与破局智慧、鲜明言谈气度与信物锚点。',
        relation_focus='宗族婚嫁利益绑定、主仆/妯娌/朝堂外戚多方关系网、情感错位与立场对立。',
        antagonist_pattern='依托宗法权势或朝堂利益的家族掌权者与政敌。',
        decomposition_focus='重点拆解门第身份对人物行为许可的限制、内宅与朝堂多配角独立互动网。',
    ),
    'GENRE_XIANSHI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('fate_attitude',),
        archetype_focus='扎根真实地域/阶层/职业的普通人复杂性、体面与生计的道德拉扯、沉没成本与盲点。',
        relation_focus='家庭代际债、邻里/单位人情权责网、阶层不对称与时代变迁下的关系离散。',
        antagonist_pattern='结构性生活困境与各有苦衷的现实利益冲突方，绝无脸谱化反派或超自然能力。',
        decomposition_focus='重点拆解人物日常职业行为细节、现实关系人情约束及配角独立生活轨迹。',
    ),
    'GENRE_QINGCHUN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'relation_network', 'relation_tension'),
        optional=('status_profession', 'fate_attitude'),
        archetype_focus='成长敏感度、自卑与骄傲的青春期面具、鲜活群体外貌/口头禅锚点与自我认同探索。',
        relation_focus='同桌/社团/寝室小群体的亲疏波动、暗恋情感错位、师生/亲子期待义务张力。',
        antagonist_pattern='升学竞争压力、同侪误解排挤或过度控制的家庭期待。',
        decomposition_focus='重点拆解校园群像辨识度、青涩情感错位及成长节点上心智模型的松动。',
    ),
    'GENRE_ERCIYUAN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'supernatural_ability', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('cognition_ethics', 'status_profession', 'racial_relation'),
        archetype_focus='高辨识度表层标签与深层反差萌/执念、专属能力发动条件与羁绊代价。',
        relation_focus='小队/学院羁绊网、宿敌镜像对照、阵营立场对立与情感错位。',
        antagonist_pattern='拥有华丽理念执念与鲜明能力反差的魅力型对立者。',
        decomposition_focus='重点拆解高辨识度角色标志特征如何自然复现、人物反差弧光与群体化学反应。',
    ),
    'GENRE_QINGXIAOSHUO': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'supernatural_ability', 'relation_network', 'relation_tension'),
        optional=('status_profession', 'fate_attitude', 'faction_hierarchy', 'racial_relation'),
        archetype_focus='高概念异常处境下的日常反差性格、强烈声线吐槽/潜台词与精准小阵容定位。',
        relation_focus='核心小圈子密集日常互动、隐藏身份信息差、暧昧情感错位与互助同盟。',
        antagonist_pattern='打破主角珍视日常秩序的对立理念者或异常规则代言人。',
        decomposition_focus='重点拆解精炼核心阵容的互动张力、表层日常身份与隐藏秘密之间的摩擦。',
    ),
    'GENRE_TONGREN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'supernatural_ability', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('status_profession', 'racial_relation'),
        archetype_focus='尊重原典人物性格与能力边界（防 OOC），明晰原创/穿越主角的先知盲点与身份限制。',
        relation_focus='原典既有关系拓扑的真实承接、蝴蝶效应引发的立场偏移与信任重建。',
        antagonist_pattern='原典核心反派及因主角介入而提前觉醒的新对立势力。',
        decomposition_focus='重点拆解如何用精准性格/声线锚点守住角色一致性，以及关系介入的合理条件。',
    ),
    'GENRE_ZHUTIAN': _cprofile(
        primary=('core_drive', 'supporting_cast', 'supernatural_ability', 'status_profession', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('cognition_ethics', 'racial_relation'),
        archetype_focus='跨世界携带能力兼容与代价、主角核心不变的执念锚点、各副本临时队友与常驻班底分层。',
        relation_focus='跨界组织/主神空间利益同盟、高信息不对称博弈与阶段性配角退场回收。',
        antagonist_pattern='同级竞争轮回者/跨界猎手或高维规则操纵者。',
        decomposition_focus='重点拆解跨副本阵容控制（常驻少而精、副本配角功能清晰）与主角长期核心弧光连续性。',
    ),
    'GENRE_MOSHI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('supernatural_ability', 'fate_attitude', 'racial_relation'),
        archetype_focus='灾变前职业技能在末世的实用转化、生存实用外观、资源匮乏下的道德底线拷问。',
        relation_focus='据点权力结构、物资分配公平冲突、求生小队脆弱信任与随时反转的同盟对立。',
        antagonist_pattern='奉行丛林法则的据点军阀/掠夺者或极端危机下背叛的同行者。',
        decomposition_focus='重点拆解极度稀缺环境如何逼出人物深层性格、团队分工与资源权力关系变化。',
        adaptation_refs=('ADAPT_B_00024', 'CONFLICT_B_004'),
    ),
    'GENRE_SAIBO': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'supernatural_ability', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('fate_attitude', 'racial_relation'),
        archetype_focus='义体改造代价与人性残存边界、街头/黑客/雇佣兵职业专长、极端不信任下的生存法则。',
        relation_focus='中间人/雇主/黑帮/巨企多层利益契约、严重权力与信息不对等、随时变质的同盟。',
        antagonist_pattern='冷酷非人格化的巨企高管、黑墙/AI代理或陷入赛博失控的昔日同行。',
        decomposition_focus='重点拆解人物在异化代价与尊严之间的挣扎、灰产契约关系网与背叛张力。',
    ),
    'GENRE_WEILAI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=('supernatural_ability', 'fate_attitude', 'racial_relation'),
        archetype_focus='未来公民等级/职业坐标、面对算法或制度治理的心智模型固化与觉醒过程。',
        relation_focus='阶层空间隔离关系、监控体系下的隐秘互助同盟与价值观根本对立。',
        antagonist_pattern='坚信秩序优先的制度维护者或垄断未来资源的精英群体。',
        decomposition_focus='重点拆解未来制度如何塑造角色认知盲点、以及人物间跨越阶层隔离的信任建立。',
    ),
    'GENRE_TONGHUA': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'fate_attitude', 'relation_network', 'relation_tension'),
        optional=('supernatural_ability', 'racial_relation'),
        archetype_focus='凝练鲜明的象征性格与单一核心渴望、直白可辨的标志性动作或物件特征。',
        relation_focus='契约/诺言绑定关系、善良与贪婪的镜像对比、简洁清晰的情感与立场对照。',
        antagonist_pattern='代表人性弱点或违背誓言代价的象征性对手或女巫/暴君。',
        decomposition_focus='重点拆解精简角色阵容的象征对照与诺言关系的闭环兑现。',
    ),
    'GENRE_ERTONG': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'relation_network'),
        optional=('relation_tension', 'status_profession', 'supernatural_ability'),
        archetype_focus='符合儿童视角的好奇心、小缺点与勇气成长，外貌与口头禅生动易记。',
        relation_focus='伙伴互助友谊、家庭陪伴与良性竞争，避免成人式阴暗权谋。',
        antagonist_pattern='顽皮竞争伙伴、误解大人的约束或适龄冒险挑战。',
        decomposition_focus='重点拆解鲜明童趣角色锚点与温暖真实的伙伴/亲子关系互动。',
    ),
    'GENRE_JISHI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='忠实可核查的真实身份、专业背景、时代局限与言行依据，严禁虚构超自然能力。',
        relation_focus='真实机构/家庭/社会脉络与历史利益制约，严格区分客观事实与当事人主观回忆。',
        antagonist_pattern='真实存在的制度壁垒、时代困局或立场相左的现实群体。',
        decomposition_focus='重点拆解真实人物言行引证口径与社会关系脉络，杜绝夸大臆测。',
    ),
    'GENRE_ZHIYE': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='硬核专业技能树与职级瓶颈、行业伦理底线、职场表层客套与压力下真实决断反差。',
        relation_focus='跨部门利益博弈、师徒/上下级权责不对等、甲方乙方契约与同行镜像竞争。',
        antagonist_pattern='专业能力强但价值导向不同（如重短期KPI轻安全底线）的行业对手或上司。',
        decomposition_focus='重点拆解专业行为如何同时体现职业素养与性格底色、以及职场权力与信任博弈。',
    ),
    'GENRE_NVXING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('faction_hierarchy', 'fate_attitude'),
        archetype_focus='自我主体意识觉醒、从被动社会身份到主动选择的弧光、女性群像各自独立目标。',
        relation_focus='女性互助与镜像对比、家庭/职场隐性权力不对称、情感债务清理与边界重塑。',
        antagonist_pattern='将主角工具化的隐性规训制度、既得利益亲属或职场压迫者。',
        decomposition_focus='重点拆解角色心智模型破冰与边界确立的过程、以及不围绕男性展开的独立配角互动网。',
    ),
    'GENRE_JIATING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension'),
        optional=('faction_hierarchy',),
        archetype_focus='代际观念差异、隐忍付出与沉没成本心理、每个家庭成员各有自洽却相撞的立场。',
        relation_focus='血缘不可选约束、长期情感债务与偏心错位、产权/照护权责不对称。',
        antagonist_pattern='没有绝对恶人，冲突来自代际控制欲、资源分配失衡与长期未沟通的旧账。',
        decomposition_focus='重点拆解多代同堂关系网中的情感债务积累、偏误误解与各自独立诉求。',
    ),
    'GENRE_GONGTING': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'fate_attitude', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='深沉城府与三层人格外化（表层顺从/中层试探/深层杀伐）、隐秘出身负担与政治抱负。',
        relation_focus='君臣猜忌、后宫/外戚/士族多极派系自动博弈、高烈度权力与信息不对称及多维对立。',
        antagonist_pattern='位高权重、耳目众多、拥有完整政治哲学与派系羽翼的顶级政敌。',
        decomposition_focus='重点拆解多派系不经过主角的暗线博弈、身份伪装/揭晓及权力与信息差对决策的制约。',
    ),
    'GENRE_SHEHUI': _cprofile(
        primary=('core_drive', 'supporting_cast', 'cognition_ethics', 'status_profession', 'relation_network', 'relation_tension', 'faction_hierarchy'),
        optional=(),
        archetype_focus='案件背后普通人与既得利益者的阶层身份坐标、道德灰色地带与自我欺骗机制。',
        relation_focus='官商/机构/家庭隐秘利益链、阶层权力不对等、证人沉默筹码与制度性对立。',
        antagonist_pattern='被利益链与制度盲区共同包裹的合谋群体，绝无超自然开脱。',
        decomposition_focus='重点拆解人物社会坐标如何决定知情与沉默动机、以及跨阶层关系网如何遮蔽真相。',
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
    if cat_id == 'supernatural_ability':
        return f'当前类型（{joined}）以常规人类能力与现实/时代技能为主，超凡能量、血脉、无敌与基因改造属于跨类型扩展项，避免违背题材底线。'
    if cat_id == 'racial_relation':
        return f'当前类型（{joined}）不存在非人多种族社会结构，种族嵌入与种族张力属于跨类型扩展项。'
    if cat_id == 'fate_attitude':
        return f'当前类型（{joined}）偏重现实因果或专业竞技，宿命/预言态度非常规核心项，可按需展开。'
    return f'此分类在 {joined} 中属于跨类型扩展项，仅在作品明确引入相关要素时按需启用。'


def character_profile_for_types(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Build genre-targeted 04 character_design + 05 static_relations profile with strict boundaries."""
    normalized, mains = _resolve_main_genres(types)
    mapping = type_map()
    type_objs = [{'id': tid, 'name': mapping[tid]['name'], 'parent_id': mapping[tid].get('parent_id')}
                 for tid in normalized if tid in mapping]
    main_names = [mapping[mid]['name'] for mid in mains if mid in mapping]

    profiles = [GENRE_CHARACTER_PROFILES.get(mid, DEFAULT_CHARACTER_PROFILE) for mid in mains] if mains else [DEFAULT_CHARACTER_PROFILE]

    relevance_by_cat: dict[str, str] = {}
    for cat in CHARACTER_CATEGORIES:
        cid = cat['id']
        best = 'out_of_scope'
        for prof in profiles:
            if cid in prof['primary']:
                best = 'primary'
                break
            if cid in prof['optional'] and best != 'primary':
                best = 'optional'
        relevance_by_cat[cid] = best

    archetype_focuses: list[str] = []
    relation_focuses: list[str] = []
    antagonist_patterns: list[str] = []
    adaptation_refs: list[str] = []
    decomp_focuses: list[str] = []
    for prof in profiles:
        cp = prof['cast_profile']
        if cp['archetype_focus'] not in archetype_focuses:
            archetype_focuses.append(cp['archetype_focus'])
        if cp['relation_focus'] not in relation_focuses:
            relation_focuses.append(cp['relation_focus'])
        if cp['antagonist_pattern'] not in antagonist_patterns:
            antagonist_patterns.append(cp['antagonist_pattern'])
        for ref in cp.get('type_adaptation_refs', ()):
            if ref not in adaptation_refs:
                adaptation_refs.append(ref)
        if prof['decomposition_focus'] not in decomp_focuses:
            decomp_focuses.append(prof['decomposition_focus'])

    categories: list[dict[str, Any]] = []
    for cat in CHARACTER_CATEGORIES:
        cid = cat['id']
        rel = relevance_by_cat[cid]
        categories.append({
            'id': cid,
            'target_stage': cat['target_stage'],
            'target_stage_label': cat['target_stage_label'],
            'name': cat['name'],
            'short_name': cat['short_name'],
            'description': cat['description'],
            'usage_mode': cat['usage_mode'],
            'source_files': list(cat['source_files']),
            'catalog_group_key': cat['catalog_group_key'],
            'relevance': rel,
            'relevance_label': RELEVANCE_LABELS[rel],
            'boundary_note': _out_of_scope_note(cid, main_names) if rel == 'out_of_scope' else cat['usage_mode'],
        })

    categories.sort(key=lambda r: (RELEVANCE_RANK[r['relevance']], CHARACTER_CATEGORY_ORDER[r['id']]))
    return {
        'types': type_objs,
        'main_types': [{'id': mid, 'name': mapping[mid]['name']} for mid in mains if mid in mapping],
        'has_genre_binding': bool(mains),
        'primary_categories': [c['id'] for c in categories if c['relevance'] == 'primary'],
        'optional_categories': [c['id'] for c in categories if c['relevance'] == 'optional'],
        'out_of_scope_categories': [c['id'] for c in categories if c['relevance'] == 'out_of_scope'],
        'categories': categories,
        'character_categories': [c for c in categories if c['target_stage'] == 'character_design'],
        'relation_categories': [c for c in categories if c['target_stage'] == 'static_relations'],
        'cast_profile': {
            'archetype_focus': '；'.join(archetype_focuses),
            'relation_focus': '；'.join(relation_focuses),
            'antagonist_pattern': '；'.join(antagonist_patterns),
            'type_adaptation_refs': adaptation_refs,
        },
        'decomposition_focus': '；'.join(decomp_focuses),
        'step_boundaries': {
            'character_design': deepcopy(CHARACTER_STEP_BOUNDARY),
            'static_relations': deepcopy(STATIC_RELATIONS_STEP_BOUNDARY),
        },
    }


def annotate_character_groups(groups: list[dict[str, Any]], types: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Annotate catalog character/relation option groups with stage ownership and genre relevance."""
    profile = character_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    annotated: list[dict[str, Any]] = []
    for group in groups:
        row = deepcopy(group)
        cat_id = row['key'].removeprefix('character.group.')
        meta = by_id.get(cat_id)
        if meta:
            row.update(
                character_category=cat_id,
                target_stage=meta['target_stage'],
                target_stage_label=meta['target_stage_label'],
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
        CHARACTER_CATEGORY_ORDER.get(r.get('character_category', ''), 99),
    ))
    return annotated


def classify_character_method(body: dict[str, Any]) -> list[str]:
    """Deterministically classify a character_design or static_relations method into matching categories."""
    if not isinstance(body, dict):
        return []
    tasks = set(body.get('tasks') or ())
    outputs = body.get('outputs') or ()
    output_stages = {o.get('stage') for o in outputs if isinstance(o, dict)}
    targets_char = 'character_arc' in tasks or 'character_design' in output_stages
    targets_rel = 'relationships' in tasks or 'static_relations' in output_stages
    if not (targets_char or targets_rel):
        return []
    text = ' '.join([
        str(body.get('title') or ''),
        ' '.join(str(x) for x in (body.get('applicability') or ())),
        ' '.join(str(o.get('instruction') or '') for o in (body.get('operations') or ()) if isinstance(o, dict)),
        ' '.join(str(o.get('description') or '') for o in outputs if isinstance(o, dict)),
    ])
    allowed_stages = set()
    if targets_char:
        allowed_stages.add('character_design')
    if targets_rel:
        allowed_stages.add('static_relations')
    scores: list[tuple[int, int, str]] = []
    for cat in CHARACTER_CATEGORIES:
        if cat['target_stage'] not in allowed_stages:
            continue
        hits = sum(1 for kw in cat['keywords'] if kw in text)
        if hits:
            scores.append((-hits, CHARACTER_CATEGORY_ORDER[cat['id']], cat['id']))
    if not scores:
        fallback = []
        if targets_char:
            fallback.append('core_drive')
        if targets_rel:
            fallback.append('relation_network')
        return fallback
    scores.sort()
    return [cid for _, _, cid in scores[:3]]


def character_decomposition_prompt(
    types: list[str] | tuple[str, ...] | None = None,
    domain: str = 'character_arc',
    *,
    phase: str = 'relations',
) -> str:
    """Concise genre-targeted guidance for decomposing/deriving character_arc, cast_entry, and cast_roster."""
    profile = character_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    type_label = ' / '.join(t['name'] for t in profile['main_types']) or '当前参考书'
    primary_char = '、'.join(by_id[cid]['short_name'] for cid in profile['primary_categories'] if by_id[cid]['target_stage'] == 'character_design')
    primary_rel = '、'.join(by_id[cid]['short_name'] for cid in profile['primary_categories'] if by_id[cid]['target_stage'] == 'static_relations')
    oos_names = '、'.join(by_id[cid]['short_name'] for cid in profile['out_of_scope_categories'])

    if phase == 'methods':
        text = (
            f'【04人物与05静态关系·分类型资料边界（{type_label}）】'
            f'04人物核心子域：{primary_char or "定位与欲望弧光"}；'
            f'05关系核心子域：{primary_rel or "关系网与张力"}。'
        )
        if oos_names:
            text += f'非本类型常规子域（{oos_names}）除非原作确有直接原文证据，否则不要强行套用。'
        text += (
            '严格守住步骤分工：单人动机/身份/外化/能力/分派落入 character_design（members/capabilities/states/cast_assignments），'
            '双方关系/不对称张力/配角独立互动落入 static_relations（relations/requirements），不把单人弧光与跨章结局混为一谈。'
        )
        return text

    domain_note = {
        'character_arc': '聚焦人物欲望执念、压力抉择、代价与心智/立场转变，区分单人弧光（04）与双边关系张力（05）。',
        'cast_entry': '聚焦人物为何在此时入场、独立目标、披露方式（自报/他介/暗身份）及后续揭晓，避免工具化误判。',
        'cast_roster': '逐章核实在场与提及人物、区分个体与群体、准确记录全书地位与单章职责，为同类型人物分布样本提供可靠统计。',
    }.get(domain, '')
    text = (
        f'【04人物与05静态关系·按本书类型（{type_label}）定向核对{domain}】'
        f'{domain_note}{profile["decomposition_focus"]}'
    )
    if oos_names:
        text += f'非本类型常规项（{oos_names}）仅在原文确有实证时记录，切勿脑补。'
    return text


def character_stage_prompt_packet(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Compact deterministic packet frozen into planning manifests for 04 character_design & 05 static_relations."""
    profile = character_profile_for_types(types)
    type_list = [{'id': t['id'], 'name': t['name']} for t in profile['types']]

    def _for_stage(stage: str) -> dict[str, Any]:
        cats = [c for c in profile['categories'] if c['target_stage'] == stage]
        boundary = profile['step_boundaries'][stage]
        return {
            'types': type_list,
            'stage': stage,
            'primary_categories': [
                {'id': c['id'], 'name': c['name'], 'usage_mode': c['usage_mode']}
                for c in cats if c['relevance'] == 'primary'
            ],
            'optional_categories': [
                {'id': c['id'], 'name': c['name']}
                for c in cats if c['relevance'] == 'optional'
            ],
            'out_of_scope_categories': [
                {'id': c['id'], 'name': c['name'], 'boundary_note': c['boundary_note']}
                for c in cats if c['relevance'] == 'out_of_scope'
            ],
            'cast_profile': profile['cast_profile'],
            'step_boundary': {
                'responsibility': boundary['responsibility'],
                'out_of_scope': list(boundary['out_of_scope']),
                'downstream_steps': [d['step_id'] for d in boundary['downstream_steps']],
            },
        }

    return {
        'character_design': _for_stage('character_design'),
        'static_relations': _for_stage('static_relations'),
    }


def character_blueprint(library: Any, types: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Combine genre-targeted 04/05 profile with live workspace coverage and cast samples."""
    from nw.studio.downstream_handoff import audit_downstream_handoff

    profile = character_profile_for_types(types)
    audit = audit_downstream_handoff(library, types=list(types), planning_hierarchy=True)
    target_methods = [
        m for m in audit.get('methods', ())
        if bool({'character_arc', 'relationships'} & set(m.get('tasks', ())))
        or bool({'character_design', 'static_relations'} & set(m.get('output_stages', ())))
    ]
    by_cat_rec: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in CHARACTER_CATEGORIES}
    by_cat_draft: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in CHARACTER_CATEGORIES}
    by_cat_blocked: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in CHARACTER_CATEGORIES}

    for method in target_methods:
        cats = method.get('character_categories') or []
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
            if cid not in by_cat_rec:
                continue
            if method['status'] in ('receivable', 'inactive_by_policy'):
                by_cat_rec[cid].append(brief)
            elif method['status'] == 'draft':
                by_cat_draft[cid].append(brief)
            else:
                by_cat_blocked[cid].append(brief)

    categories_with_coverage: list[dict[str, Any]] = []
    covered_primary = 0
    for cat in profile['categories']:
        cid = cat['id']
        rec = by_cat_rec[cid]
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

    step_by_id = {s['step_id']: s for s in audit.get('steps', ())}
    char_step = step_by_id.get('character_design', {})
    rel_step = step_by_id.get('static_relations', {})
    return {
        **profile,
        'categories': categories_with_coverage,
        'character_categories': [c for c in categories_with_coverage if c['target_stage'] == 'character_design'],
        'relation_categories': [c for c in categories_with_coverage if c['target_stage'] == 'static_relations'],
        'coverage_summary': {
            'total_character_relation_methods': len(target_methods),
            'receivable_character_methods': char_step.get('receivable_count', 0),
            'receivable_relation_methods': rel_step.get('receivable_count', 0),
            'primary_category_count': len(profile['primary_categories']),
            'covered_primary_categories': covered_primary,
            'gap_primary_categories': [
                c['id'] for c in categories_with_coverage
                if c['relevance'] == 'primary' and c['receivable_count'] == 0
            ],
            'cast_sample_ready': audit['summary']['cast_sample_ready'],
        },
        'cast_samples': audit['cast_samples'],
        'originality_audit': audit['originality_audit'],
    }
