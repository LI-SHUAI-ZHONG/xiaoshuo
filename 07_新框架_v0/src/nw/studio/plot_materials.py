"""Genre-targeted plot_design (06) & event_design (07) material taxonomy, boundaries, and coverage audit.

Organizes the original workflow's 06 `plot_design` and 07 `event_design` materials
(`plot_design*.py` and `event_design*.py`) into 12 bounded, non-overlapping sub-categories
across the `structure` (06) and `hook` (06-07) client boards, adds item-level genre
relevance for all 15 narrative structures and 30 plot/event mechanisms, maps all 35 main
genres (and subgenres), and connects upstream decomposition (`main_plot`, `subplot`, `hook`,
`foreshadow`, `information`, `chapter_progress`) and 01-05 outputs straight into 06, 07,
and downstream 08-13 steps without cross-step leakage.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.studio.catalog import canonical_types, type_map


PLOT_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'plot_design',
    'order': 6,
    'name': '06. 剧情因果与伏笔',
    'responsibility': (
        '承接 01–05 的类型承诺、世界硬规则、人物目标与静态关系张力（及已确认方向与篇幅计划），'
        '组织全书主线/分卷转折/单章目标（directions / members），拆出具备明确完成条件的事件节点'
        '（event_nodes），编排面向读者而非替代人物体验的信息与情绪序列（reader_plan），'
        '并维护可追踪埋设与回收窗口的伏笔承诺计划（promise_plan）。'
    ),
    'upstream_steps': [
        {'step_id': 'type_selection', 'name': '01. 类型判定与承诺', 'provides': '题材核心读者承诺、开篇/结局预期底线'},
        {'step_id': 'type_adaptation', 'name': '02. 类型组合与适配', 'provides': '篇幅/节奏适配参数与多题材主辅分工'},
        {'step_id': 'world_design', 'name': '03. 世界设定与限制', 'provides': '世界核心矛盾、资源稀缺冲突与自动运转背景事件'},
        {'step_id': 'character_design', 'name': '04. 人物动机与弧线', 'provides': '主角执念、反派阻力逻辑、配角独立目标与 cast_assignments'},
        {'step_id': 'static_relations', 'name': '05. 静态关系与张力', 'provides': '结构性对立、情感债务、配角独立互动与等待剧情端点的关系'},
        {'step_id': 'corpus:plot', 'name': '参考拆解 · 主线/支线/钩子/伏笔/信息/推进', 'provides': '同类型主支线、钩子接力、伏笔回收方法与篇幅统计样本'},
    ],
    'downstream_steps': [
        {'step_id': 'event_design', 'name': '07. 事件链与候选分支', 'consumes': 'event_nodes 及其 completion_condition（作为后继事件完成门）'},
        {'step_id': 'action_design', 'name': '08. 行动博弈与试错代价', 'consumes': '事件目标、障碍与人物冲突压力'},
        {'step_id': 'scene_design', 'name': '09. 场景结构与POV边界', 'consumes': '章卡、事件节点、reader_plan 披露顺序与 promise_plan 埋收安排'},
        {'step_id': 'state_transition', 'name': '10. 状态变化与外部因果', 'consumes': '事件预期结果、代价与伏笔承诺状态推进'},
        {'step_id': 'expression_design', 'name': '13. 叙述距离与表达设计', 'consumes': '章内情绪波形、节奏密度与钩子留白目标'},
        {'step_id': 'review', 'name': '16. 独立审稿与证据核验', 'consumes': '伏笔兑现窗口、反转前置线索可回溯性与章末追读钩子'},
    ],
    'allowed_outputs': [
        {'field': 'directions', 'kind': 'list[object]', 'description': '全书 2–3 个候选方向（或已选方向/卷章细化时的唯一深化方向）'},
        {'field': 'members', 'kind': 'plot/promise/chapter/volume', 'description': '按当前范围生成的剧情卡、伏笔承诺卡、卷卡或章卡'},
        {'field': 'event_nodes', 'kind': 'list[object]', 'description': '含 actors、goal、setting、obstacle、completion_condition 的计划事件节点'},
        {'field': 'reader_plan', 'kind': 'list[object]', 'description': '面向读者的信息披露次序与前后情绪变化（不以人物情绪替代读者体验）'},
        {'field': 'promise_plan', 'kind': 'list[object]', 'description': '伏笔埋设、预期含义、回收节点与窗口（远期未定时填 null，不编造）'},
        {'field': 'continuations', 'kind': 'list[object]', 'description': '（续写章节时）承接上一已接受章稿遗留问题的具体安排'},
    ],
    'in_scope': [
        '叙事结构骨架（线性/非线性/多视角/单元/篇章/升级/任务/群像/循环等）与三幕/起承转合/闭环安排',
        '开篇黄金三章承诺、引力中心、进度脉动、失败代价设计与终章不可逆收束',
        '推进动力、重/中/轻/空章节奏轮换、冲突类型轮换与篇幅字数档位配比',
        '配角发起转折（30%–40%）、配角支线与主线交汇、资源作为冲突与伏笔工具',
        '伏笔埋设、休眠期、延迟解码、80% 回收率、深层掩体、反转前奏/余响与可回溯合理性',
        '信息差设计、优先回应上章钩子、延迟信息释放与认知错位悬念',
    ],
    'out_of_scope': [
        '不得推翻已批准的上级全书方向或卷纲（另起方向须另建细化方案）',
        '不得把单个人物情绪直接冒充 reader_plan 的读者情绪轨迹',
        '不得凭空伪造远期尚未规划的伏笔回收章节号（未定时必须保留 null）',
        '不得越界在本步生成具体场景 POV 卡片（归 09 场景设计）或具体行动试错步骤（归 08 行动设计）',
        '不得直接规定具体句子辞藻或修辞文风（归 13 表达设计）',
        '非对应题材不得套用跨题材推进机制（如现实悬疑/宫廷/职场不可强套快穿/升级/星际战争）',
    ],
}


EVENT_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'event_design',
    'order': 7,
    'name': '07. 事件链与候选分支',
    'responsibility': (
        '仅在卷/章/场细化阶段运行：严格引用 06 剧情设计的 event_nodes 及其 completion_condition'
        ' 作为前驱完成门（TDR_TEMPLATE_004 / 104.1 事件顺序不能颠倒），结合世界自动运转事件、'
        '势力互动、决策连锁反应与适用的事件机制，设计多方条件后继候选事件（conditional_candidate）。'
    ),
    'upstream_steps': [
        {'step_id': 'world_design', 'name': '03. 世界设定与限制', 'provides': '自动运转事件表、生态失衡条件与制度执行机制'},
        {'step_id': 'static_relations', 'name': '05. 静态关系与张力', 'provides': '势力自动互动、多方立场与升级触发条件'},
        {'step_id': 'plot_design', 'name': '06. 剧情因果与伏笔', 'provides': 'event_nodes 及其精确 completion_condition 与反转/伏笔节点'},
        {'step_id': 'corpus:event', 'name': '参考拆解 · 章场推进/支线/钩子', 'provides': '前事件完成门触发后继事件、跨支线交汇与意外分支方法'},
    ],
    'downstream_steps': [
        {'step_id': 'action_design', 'name': '08. 行动博弈与试错代价', 'consumes': '被承接的候选事件、参与者与触发条件'},
        {'step_id': 'scene_design', 'name': '09. 场景结构与POV边界', 'consumes': '经 selected_events 显式选中的单场事件'},
        {'step_id': 'state_transition', 'name': '10. 状态变化与外部因果', 'consumes': '事件前后因果链路核验'},
    ],
    'allowed_outputs': [
        {'field': 'candidates', 'kind': 'list[object]', 'description': '条件后继事件候选（id, source_ids, predecessor, event, actors, completion_gate, status=conditional_candidate）'},
    ],
    'in_scope': [
        '严格引用 plot.event_nodes.id 作为 predecessor，原样沿用其 completion_condition 作为 completion_gate',
        '设计前事件完成后的多方后继事件候选、决策连锁反应、探索归来后继与配角独立行动交汇',
        '承接世界自动运转事件、生态扰动失衡/寻找新均衡、势力自动变化与暗线循环发现节点',
        '（仅适配题材）细化副本/污染/外星接触/灾难/生化/主神任务/规则任务的条件触发事件',
    ],
    'out_of_scope': [
        '绝不得在全书（book）层级提前生成细粒度候选事件（仅卷/章/场细化运行）',
        '绝不得颠倒事件因果顺序（104.1）或跳过/篡改前驱事件的 completion_condition',
        '绝不得把尚未满足前提的条件候选假称为已经发生的 WORLD 事实（status 须保持 conditional_candidate）',
        '绝不得在本步生成场景卡（归 09 场景设计）或拆解人物具体动作步骤与能力消耗（归 08 行动设计）',
        '现实/都市日常/纯悬疑推理/历史/宫廷/言情/职场/家庭等题材，不得引入副本/污染/外星/生化/主神等超自然危机机制',
    ],
}


PLOT_EVENT_CATEGORIES: tuple[dict[str, Any], ...] = (
    # --- Slot: structure (06 plot_design) ---
    {
        'id': 'narrative_structure',
        'slot': 'structure',
        'target_stage': 'plot_design',
        'target_stage_label': '06 剧情结构',
        'name': '叙事结构与视角框架（15 类标准结构）',
        'short_name': '叙事结构框架',
        'description': '选定全书宏观叙事结构：线性/非线性、单视角/多视角、单元剧/连续剧/篇章/升级/任务/史诗/群像/循环/框架/意识流/编年体。',
        'usage_mode': '06 剧情与 09 场景共用总骨架：决定事件如何排布、讲述顺序与视角组织方式（单视角与多视角互斥）。',
        'source_files': ['plot_design_narrative_structures.py (15 类 NARRATIVE_STRUCTURE_*)'],
        'catalog_group_key': 'structure.group.types',
        'keywords': ('线性', '非线性', '多视角', '单视角', '单元剧', '连续剧', '篇章', '升级式', '任务式', '史诗', '群像', '循环', '框架', '编年体', '叙事结构'),
    },
    {
        'id': 'arc_conflict',
        'slot': 'structure',
        'target_stage': 'plot_design',
        'target_stage_label': '06 剧情结构',
        'name': '三幕/起承转合骨架、主支线、冲突类型与高潮余波',
        'short_name': '骨架冲突与高潮',
        'description': '覆盖三幕/15节拍/起承转合/闭环/多线并行、引力中心、余波链、岔路回撤、配角转折、主角失败设计、8类核心冲突与高潮爽点叠加。',
        'usage_mode': '06 剧情全题材底座：确保主线有引力中心、重大转折有至少两波余波、主角失败带来不可逆代价。',
        'source_files': ['plot_design_structure.py (§41–§44, 板块154)'],
        'catalog_group_key': 'structure.group.plot_design_structure',
        'keywords': ('三幕', '起承转合', '主线', '支线', '引力中心', '余波', '岔路', '失败', '冲突', '高潮', '爽点', '道德困境', '信息博弈', '资源争夺', '时间压力'),
    },
    {
        'id': 'opening_ending',
        'slot': 'structure',
        'target_stage': 'plot_design',
        'target_stage_label': '06 剧情结构',
        'name': '开篇承诺、终章收束、首尾呼应与连续性底线',
        'short_name': '开篇承诺与收束',
        'description': '界定开篇承诺、类型读者预期兑现、终章设计、结尾类型、首尾呼应、结尾不可逆性及因果/时间线连续性核查。',
        'usage_mode': '06 全书/卷级定锚：把“开篇答应给读者什么”与“结局如何不可逆兑现”闭环锁死。',
        'source_files': ['plot_design_opening_ending.py (§112)', 'plot_design_type_expectations.py (§114, 板块132)', 'plot_design_continuity.py (§102–§107)'],
        'catalog_group_key': 'structure.group.opening_ending',
        'keywords': ('开篇承诺', '终章', '结尾', '首尾呼应', '不可逆', '读者预期', '类型承诺', '兑现', '闭环', '结局', '连续性'),
    },
    {
        'id': 'chapter_rhythm',
        'slot': 'structure',
        'target_stage': 'plot_design',
        'target_stage_label': '06 剧情结构',
        'name': '推进动力、重/中/轻/空章节奏轮换与章内结构',
        'short_name': '章节推进与节奏',
        'description': '覆盖章节推进动力/并行交错/速度切换、冲突类型轮换、重中轻空四类章节变奏、章内起承转合、情绪波形与章节预览摘要。',
        'usage_mode': '06 章纲与篇幅计划联动：防止连续章同质疲劳，将目标字数档位落实为有张有弛的章节节奏序列。',
        'source_files': ['plot_design_progression.py (§122)', 'plot_design_chapters.py (板块47/48/133)', 'plot_design_reader.py (板块61/62)'],
        'catalog_group_key': 'structure.group.chapter_rhythm',
        'keywords': ('推进', '章纲', '章节', '重章', '轻章', '中章', '空章', '节奏', '轮换', '情绪波形', '阅读速度', '篇幅', '卷纲', '承接', '变奏'),
    },
    {
        'id': 'subplot_resource',
        'slot': 'structure',
        'target_stage': 'plot_design',
        'target_stage_label': '06 剧情结构',
        'name': '配角支线交汇、退场弧光与资源剧情绑定',
        'short_name': '支线与资源驱动',
        'description': '规划配角登场/退场时机、配角行动与主线交汇、配角情感/成长支线，以及将资源稀缺与流转作为剧情推进与伏笔工具。',
        'usage_mode': '06 剧情承接 03 资源与 04–05 配角关系网：避免配角游离注水，让支线在关键节点反哺主线。',
        'source_files': ['plot_design_supporting.py (§121)', 'plot_design_resources.py (§125)'],
        'catalog_group_key': 'structure.group.subplot_resource',
        'keywords': ('配角支线', '支线交汇', '退场', '登场时机', '配角弧光', '资源冲突', '资源推进', '稀缺管理', '并行线'),
    },
    {
        'id': 'multi_viewpoint',
        'slot': 'structure',
        'target_stage': 'plot_design',
        'target_stage_label': '06 剧情/场景',
        'name': '多角色视角切换与交错编排',
        'short_name': '多视角切换编排',
        'description': '规定多视角作品的视角分配比例、切视角时机、信息不对称衔接与群像多线交汇规则。',
        'usage_mode': '仅在采用多视角/群像/双线交错结构时启用；单视角作品可忽略以保持聚焦。',
        'source_files': ['plot_design_multi_viewpoint.py (§120)'],
        'catalog_group_key': 'structure.group.multi_viewpoint',
        'keywords': ('多视角', '视角切换', 'POV切换', '双线视角', '群像视角', '交错视角'),
    },
    # --- Slot: hook (06 plot_design + 07 event_design) ---
    {
        'id': 'plot_mechanism',
        'slot': 'hook',
        'target_stage': 'plot_design',
        'target_stage_label': '06–07 推进机制',
        'name': '核心情节推进机制（23 类标准机制）',
        'short_name': '核心推进机制',
        'description': '覆盖升级/无限流/快穿/逆袭/解谜/探案/权谋/战争/经营/种田/商业/恋爱/复仇/成长/竞技/游戏/文明/末世/反乌托邦/太空/星际/星球/多世界机制。',
        'usage_mode': '06 剧情与 07 事件共享引擎：已按当前所选类型将最匹配机制排至顶部，跨题材机制标为非本类型常规项。',
        'source_files': ['plot_design_plot_mechanisms.py (23 类 PLOT_MECHANISM_*)'],
        'catalog_group_key': 'hook.group.types',
        'keywords': ('升级', '逆袭', '解谜', '探案', '权谋', '战争', '经营', '种田', '商业', '恋爱', '复仇', '成长', '竞技', '无限流', '快穿', '末世', '反乌托邦', '星际', '机制'),
    },
    {
        'id': 'reader_engagement',
        'slot': 'hook',
        'target_stage': 'plot_design',
        'target_stage_label': '06 卖点与追读',
        'name': '黄金三章、追读钩子、情绪波形与读者承诺',
        'short_name': '黄金三章与钩子',
        'description': '覆盖爆款核心公式、黄金三章吸引力、连续追读动力、连载节奏、情绪波形、社交传播点与读感爽点兑现。',
        'usage_mode': '06 剧情卖点核心：确保开篇前 3 章快速抛锚，章末留有真实可承接的新问题而非空喊悬念。',
        'source_files': ['plot_design_reader_engagement.py (§123)'],
        'catalog_group_key': 'hook.group.plot_design_reader_engagement',
        'keywords': ('黄金三章', '钩子', '追读', '爆款', '爽点', '连载', '卖点', '悬念钩', '章末', '期待感', '传播点'),
    },
    {
        'id': 'foreshadow_twist',
        'slot': 'hook',
        'target_stage': 'plot_design',
        'target_stage_label': '06 伏笔与反转',
        'name': '伏笔埋设、休眠延迟解码、回收率与反转联动',
        'short_name': '伏笔与反转联动',
        'description': '覆盖伏笔埋设（2–10章窗口）、休眠期、延迟解码、伏笔密度、≥80%回收率、伏笔网络、深层掩体、反转前奏/余响、合理性回溯与双伏笔联动反转。',
        'usage_mode': '06 剧情 promise_plan 核心：每条反转须有前文可回溯线索支撑，未定远期回收章保留 null 待续。',
        'source_files': ['plot_design_foreshadowing.py (板块45, §120.20)', 'plot_design_promise_workflow.py (§126.10)'],
        'catalog_group_key': 'hook.group.foreshadow_twist',
        'keywords': ('伏笔', '埋设', '回收', '休眠', '掩体', '延迟解码', '反转', '前奏', '余响', '承诺', 'promise', '伏笔网络'),
    },
    {
        'id': 'disclosure_suspense',
        'slot': 'hook',
        'target_stage': 'plot_design',
        'target_stage_label': '06 信息与悬念',
        'name': '信息差设计、延迟信息释放与认知错位悬念',
        'short_name': '信息差与悬念',
        'description': '规划必要/延迟/奖励三类信息释放节奏、读者与角色信息不对称（板块59）、认知错位悬念（§117.7–117.9）及核心象征物意象互锁。',
        'usage_mode': '06 剧情 reader_plan 核心：严格区分角色获知与读者获知时点，优先回应上章钩子信息。',
        'source_files': ['plot_design_disclosure.py (§116, 板块59/140/143)', 'plot_design_misalignment.py (§117.7–§117.9)', 'plot_design_symbolism.py (§111)'],
        'catalog_group_key': 'hook.group.disclosure_suspense',
        'keywords': ('信息差', '信息披露', '悬念', '误导', '延迟信息', '认知错位', '象征', '意象', '保密', '揭晓', 'reader_plan'),
    },
    {
        'id': 'event_chain_triggers',
        'slot': 'hook',
        'target_stage': 'event_design',
        'target_stage_label': '07 事件链触发',
        'name': '前驱完成门、因果顺序、决策连锁与自动运转事件',
        'short_name': '事件链与完成门',
        'description': '覆盖事件顺序不能颠倒（104.1）、前驱完成条件门、决策连锁反应（板块73）、探索归来后继（板块83）、生态失衡/势力自动变化与暗线循环触发。',
        'usage_mode': '07 事件设计专属底座：严格沿用 06 event_nodes 的 completion_condition 生成条件候选分支，不越界写场景卡。',
        'source_files': ['event_design.py (§20–§34, §104.1, 板块73/83)', 'event_design_progression.py (§122)', 'event_design_supporting.py (§121.9)'],
        'catalog_group_key': 'hook.group.event_chain_triggers',
        'keywords': ('事件链', '前驱', '完成条件', '完成门', '后继事件', '候选事件', '连锁反应', '自动运转事件', '事件顺序', '触发条件', '失衡', '暗线循环', '探索归来'),
    },
    {
        'id': 'event_crisis_mechanisms',
        'slot': 'hook',
        'target_stage': 'event_design',
        'target_stage_label': '07 危机事件机制',
        'name': '特殊事件危机机制（副本/污染/外星/灾难/生化/主神/规则任务）',
        'short_name': '特殊危机事件机制',
        'description': '覆盖副本挑战、污染异变、外星文明接触、灾难事件、生化危机、主神空间任务与规则任务等高概念事件触发机制。',
        'usage_mode': '07 事件设计严格按题材边界启用：仅用于科幻/末世/游戏/诸天/灵异/恐怖/赛博等题材，现实题材自动折叠隔离。',
        'source_files': ['event_design_plot_mechanisms.py (7 类危机 PLOT_MECHANISM_*)'],
        'catalog_group_key': 'hook.group.event_crisis_mechanisms',
        'keywords': ('副本', '污染', '异变', '外星', '灾难', '生化', '主神空间', '规则任务', '危机机制', '诡异事件'),
    },
)

PLOT_EVENT_CATEGORY_MAP: dict[str, dict[str, Any]] = {c['id']: c for c in PLOT_EVENT_CATEGORIES}
PLOT_EVENT_CATEGORY_ORDER: dict[str, int] = {c['id']: i for i, c in enumerate(PLOT_EVENT_CATEGORIES)}

RELEVANCE_RANK = {'primary': 0, 'optional': 1, 'out_of_scope': 2}
RELEVANCE_LABELS = {
    'primary': '本类型核心',
    'optional': '按需扩展',
    'out_of_scope': '非本类型常规项',
}

# Item-level genre affinities for the 23 plot mechanisms + 7 event crisis mechanisms.
# Mechanisms outside a genre's primary/optional sets are clearly marked out_of_scope (never forced).
_SCI_FI_MECHS = ('PLOT_MECHANISM_SPACE', 'PLOT_MECHANISM_STAR', 'PLOT_MECHANISM_PLANET', 'PLOT_MECHANISM_CIVILIZATION', 'PLOT_MECHANISM_DYSTOPIA')
_FANTASY_POWER_MECHS = ('PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_REVENGE')
_MULTIWORLD_MECHS = ('PLOT_MECHANISM_INFINITE', 'PLOT_MECHANISM_FAST_TRANSMIGRATION', 'PLOT_MECHANISM_MULTI_WORLD')
_CRISIS_MECHS = ('PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_CONTAMINATION', 'PLOT_MECHANISM_ALIEN',
                 'PLOT_MECHANISM_DISASTER', 'PLOT_MECHANISM_BIOCHEMICAL', 'PLOT_MECHANISM_MAIN_GOD', 'PLOT_MECHANISM_RULE_TASK')


def _pprofile(
    primary: tuple[str, ...],
    optional: tuple[str, ...],
    *,
    preferred_structures: tuple[str, ...],
    optional_structures: tuple[str, ...] = ('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_ARC'),
    preferred_mechanisms: tuple[str, ...],
    optional_mechanisms: tuple[str, ...] = ('PLOT_MECHANISM_GROWTH',),
    arc_pattern: str,
    pacing_profile: str,
    hook_foreshadow_pattern: str,
    event_trigger_pattern: str,
    decomposition_focus: str,
) -> dict[str, Any]:
    return {
        'primary': primary,
        'optional': optional,
        'preferred_structures': preferred_structures,
        'optional_structures': optional_structures,
        'preferred_mechanisms': preferred_mechanisms,
        'optional_mechanisms': optional_mechanisms,
        'plot_profile': {
            'arc_pattern': arc_pattern,
            'pacing_profile': pacing_profile,
            'hook_foreshadow_pattern': hook_foreshadow_pattern,
            'event_trigger_pattern': event_trigger_pattern,
        },
        'decomposition_focus': decomposition_focus,
    }


DEFAULT_PLOT_PROFILE = _pprofile(
    primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
             'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
    optional=('multi_viewpoint', 'event_crisis_mechanisms'),
    preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_SERIAL'),
    optional_structures=('NARRATIVE_STRUCTURE_SINGLE_POV', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_GROUP'),
    preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_REVENGE'),
    optional_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_COMPETITION'),
    arc_pattern='以清晰主线总问题为引力中心，每卷完成阶段性不可逆推进，配角支线在关键转折与主线交汇。',
    pacing_profile='重/中/轻/空章交替轮换，避免连续同质冲突；结合同类型篇幅档位稳定章均推进量。',
    hook_foreshadow_pattern='开篇 3 章抛出核心承诺，章末钩子留真实可承接问题，伏笔在 2–10 章及卷末分批回收。',
    event_trigger_pattern='严格承接 06 事件节点的完成条件生成后继候选，并穿插场外势力与决策连锁事件。',
    decomposition_focus='重点拆解全书主线因果链、支线交汇方式、钩子设问与兑现间隔、伏笔埋收窗口及前事件触发后继的完成条件。',
)


# Covers all 35 main genres from nw.studio.catalog.genres().
GENRE_PLOT_PROFILES: dict[str, dict[str, Any]] = {
    'GENRE_XUANHUAN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_LEVEL', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_EPIC'),
        preferred_mechanisms=('PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_WAR'),
        optional_mechanisms=('PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_RULE_TASK'),
        arc_pattern='大地图篇章递进 + 境界阶梯突破，每一大卷以换地图或破大境完成阶跃，旧怨与大世界危机交错。',
        pacing_profile='长篇高频爽点波峰 + 中轻章消化战利品与修炼筹备，开篇黄金三章必须确立压抑与破局预期。',
        hook_foreshadow_pattern='以秘境/宗门大比/强敌约战作中期钩子，血脉/古物身世作长线延迟解码伏笔。',
        event_trigger_pattern='以大比、秘境开启、资源争夺与宗门动荡作为条件后继事件，支持副本与试炼分支。',
        decomposition_focus='重点拆解地图切换与阶段目标衔接、蓄力→打脸/破境的节奏波形、以及长篇如何防战力与支线崩盘。',
    ),
    'GENRE_QIHUAN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=(),
        preferred_structures=('NARRATIVE_STRUCTURE_EPIC', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_UPGRADE'),
        optional_mechanisms=('PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_CIVILIZATION', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_DISASTER', 'PLOT_MECHANISM_CONTAMINATION'),
        arc_pattern='远征/使命任务主线 + 多势力多视角交汇，中段主角计划必经不可逆挫折后重整同盟。',
        pacing_profile='宏大世界探索与危机倒计时交替，重章承担战役/仪式高潮，轻章沉淀人物与世界观细节。',
        hook_foreshadow_pattern='预言/古史碎片与多线伏笔网络在卷末同步绽放，以世界秘密层层揭示拉动追读。',
        event_trigger_pattern='由远征探索归来、多方势力自动互动与灾变/污染失衡触发连锁候选事件。',
        decomposition_focus='重点拆解多线交汇时序、史诗卷纲的阶段转折点、预言伏笔的合理兑现及配角独立支线推进。',
    ),
    'GENRE_XIANXIA': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_LEVEL', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_EPIC'),
        preferred_mechanisms=('PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_MYSTERY'),
        optional_mechanisms=('PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_FARMING', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_CONTAMINATION'),
        arc_pattern='凡尘入道→宗门历练→大劫破境→飞升/问道的长周期阶梯，因果伏笔横跨数卷。',
        pacing_profile='修炼筹谋与机缘搏杀张弛交替，重章写斗法与渡劫，轻章写炼丹/悟道/人情往来。',
        hook_foreshadow_pattern='秘境机缘、宗门暗算与上古因果线作长伏笔，通过延迟解码与资源争夺维持强期待。',
        event_trigger_pattern='宗门试炼、灵脉枯竭、正魔势力变动与秘境探索归来触发多分支后继事件。',
        decomposition_focus='重点拆解漫长修炼周期中的阶段驱动力、资源争夺与剧情绑定、以及跨大章的伏笔休眠与回收。',
    ),
    'GENRE_WUXIA': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_COMPETITION'),
        optional_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_UNDERDOG'),
        arc_pattern='灭门/旧案悬念起手，江湖行旅串联门派恩怨与家国大义，最终在道义抉择中闭环。',
        pacing_profile='静处论剑与骤然生死交锋反差强烈，冲突在武学切磋、智谋拆招与道德困境间轮换。',
        hook_foreshadow_pattern='以“往年旧案真相/神秘高手身份”埋设双层伏笔，配合江湖流言制造信息差。',
        event_trigger_pattern='门派火并、朝廷缉捕与恩怨仇杀形成决策连锁，严禁超自然副本/外星危机混入。',
        decomposition_focus='重点拆解江湖旧案的多层反转、道义两难如何成为卷末高潮及配角恩怨如何驱动转折。',
    ),
    'GENRE_DUSHI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_SINGLE_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_REVENGE'),
        optional_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_MYSTERY'),
        arc_pattern='现实困境切入→阶段性事业/人生跃迁→更大阶层博弈，靠现实资源与信息差层层破局。',
        pacing_profile='节奏明快、黄金三章直给现实痛点与破局契机，每 5–10 章完成一次可见收益或反击兑现。',
        hook_foreshadow_pattern='用商业合同漏洞、隐秘人脉、竞争对手暗手制造贴近生活的追读钩子与反转。',
        event_trigger_pattern='资本变动、舆情爆发、行业监管与合作伙伴变卦触发连锁后继事件；严禁超自然危机机制。',
        decomposition_focus='重点拆解都市题材如何用现实困境制造高密度爽点/冲突轮换，以及资源积累与阶段升级的衔接。',
    ),
    'GENRE_LISHI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=(),
        preferred_structures=('NARRATIVE_STRUCTURE_CHRONICLE', 'NARRATIVE_STRUCTURE_EPIC', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_LINEAR'),
        preferred_mechanisms=('PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_FARMING', 'PLOT_MECHANISM_CIVILIZATION'),
        optional_mechanisms=('PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_REVENGE'),
        arc_pattern='立足真实历史大势节点，以小人物/关键谋士撬动财政、军事与朝局，因果环环相扣。',
        pacing_profile='庙堂谋划（中轻章）与战阵/政变决战（重章）交替，兼顾历史时间轴与戏剧压缩感。',
        hook_foreshadow_pattern='利用历史已知大危机（如灾荒/外患/党争）作倒计时压力与长线伏笔回收。',
        event_trigger_pattern='朝堂政令、粮草危机、边关军情与多方势力博弈自动触发后继事件；严禁科幻/超自然危机机制。',
        decomposition_focus='重点拆解历史大事件节点与虚构个人线的咬合、多方朝堂势力博弈的因果推进及信息时延悬念。',
    ),
    'GENRE_JUNSHI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('foreshadow_twist',),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_CHRONICLE', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_POLITICAL'),
        optional_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_REVENGE'),
        arc_pattern='任务简报→战前筹划→意外变数→硬核战术破局→战后代价与新战区升级。',
        pacing_profile='高密度时间压力与战场迷雾推进，重章打战术对抗回合，轻章做休整、补给与战损复盘。',
        hook_foreshadow_pattern='敌情不明、补给线受胁与内线情报差驱动强紧迫感，伏笔落于地形/装备细节。',
        event_trigger_pattern='前线战况变化、后勤断档与上级军令变更直接触发条件后继候选；严禁玄幻/超自然危机机制。',
        decomposition_focus='重点拆解战役阶段推进、意外突发状况如何打破原计划并迫使战术临机应变。',
    ),
    'GENRE_KEHUAN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=(),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_EPIC', 'NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_LOOP'),
        preferred_mechanisms=('PLOT_MECHANISM_SPACE', 'PLOT_MECHANISM_STAR', 'PLOT_MECHANISM_PLANET', 'PLOT_MECHANISM_CIVILIZATION', 'PLOT_MECHANISM_DYSTOPIA', 'PLOT_MECHANISM_MYSTERY'),
        optional_mechanisms=('PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_APOCALYPSE', 'PLOT_MECHANISM_ALIEN', 'PLOT_MECHANISM_DISASTER', 'PLOT_MECHANISM_BIOCHEMICAL'),
        arc_pattern='核心科技奇点/异常观测切入→实验验证与危机失控→跨尺度文明博弈与理念收束。',
        pacing_profile='科学悬疑推理与宏大危机倒计时交替，严守物理与逻辑因果连续性。',
        hook_foreshadow_pattern='早期微小异常数据作为深层掩体伏笔，后期翻转整个世界观认知（必然性错觉→揭示）。',
        event_trigger_pattern='外星接触、技术失控灾难、系统故障与星际文明博弈触发多级余波候选事件。',
        decomposition_focus='重点拆解“核心科学异常→推理揭示→世界级后果”的递进结构、硬逻辑伏笔与反转合理性。',
    ),
    'GENRE_XUANYI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint', 'subplot_resource'),
        preferred_structures=('NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_SINGLE_POV', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_FRAME', 'NARRATIVE_STRUCTURE_ARC'),
        preferred_mechanisms=('PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_REVENGE'),
        optional_mechanisms=('PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_GROWTH'),
        arc_pattern='核心异常/悬案抛出→多重假说与误导→关键证物撕裂旧判断→双伏笔联动终极反转。',
        pacing_profile='强时间压力与信息释放节奏控制，严格区分“决策前必要信息”与“回溯延迟信息”。',
        hook_foreshadow_pattern='核心在于深层伏笔掩体、延迟解码、反转前奏（1–2场）与反转余响（1–2场）及 80%+ 回收率。',
        event_trigger_pattern='调查发现新证物、证人失踪或翻供、密闭时间窗逼近触发连锁事件；严禁副本/外星/生化等跨题材危机。',
        decomposition_focus='重点拆解信息披露先后（reader_plan）、认知错位误导、双线索交汇反转及每条伏笔的跨章回收路径。',
    ),
    'GENRE_TUILI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_SINGLE_POV', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_FRAME'),
        preferred_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_MYSTERY'),
        optional_mechanisms=('PLOT_MECHANISM_REVENGE',),
        arc_pattern='发案与不在场困局→逐一取证排伪→伪解答破产→公平线索收拢至唯一真解答。',
        pacing_profile='勘查取证（中章）→突发二案/证词崩塌（重章）→收束推理（高潮重章）→余韵消化（轻章）。',
        hook_foreshadow_pattern='极致公平线索原则：所有用于终局推理的伏笔必须在前文对读者可见，严禁凭空掏证。',
        event_trigger_pattern='物理时间线节点、证言矛盾暴露与连续案发严格按因果顺序推进；严禁任何超自然事件机制。',
        decomposition_focus='重点拆解公平线索埋设、伪解答如何误导读者又合乎逻辑、以及线索在终局如何全部回收。',
    ),
    'GENRE_LINGYI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('subplot_resource', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_SINGLE_POV', 'NARRATIVE_STRUCTURE_LOOP'),
        preferred_mechanisms=('PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_APOCALYPSE', 'PLOT_MECHANISM_INFINITE'),
        optional_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_CONTAMINATION', 'PLOT_MECHANISM_RULE_TASK', 'PLOT_MECHANISM_DUNGEON'),
        arc_pattern='诡异事件/规则怪谈单元切入→试错摸清禁忌生路→串连背后庞大诡异源头主线。',
        pacing_profile='高危诡异压迫（重章）与安全屋线索拼图（轻中章）强烈交替，善用信息缺口制造寒意。',
        hook_foreshadow_pattern='用反常细节、规则纸条缺页与幸存者遗言埋设伏笔，通过发现暗线循环规律制造爽点。',
        event_trigger_pattern='违规触发禁忌、污染扩散与规则任务倒计时直接触发致命候选事件。',
        decomposition_focus='重点拆解规则探索试错链、单元事件如何向主线归拢、以及诡异规律被反利用的反转设计。',
    ),
    'GENRE_KONGBU': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_SINGLE_POV', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_LOOP'),
        preferred_mechanisms=('PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_APOCALYPSE'),
        optional_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_CONTAMINATION', 'PLOT_MECHANISM_DISASTER', 'PLOT_MECHANISM_BIOCHEMICAL', 'PLOT_MECHANISM_RULE_TASK'),
        arc_pattern='孤立陷阱封闭→生存空间步步收紧→防线瓦解与惨痛逃生→留白式余悸收束。',
        pacing_profile='静默蓄压→骤然惊吓→喘息错觉→更大危机，严控情绪波形防止读感麻木。',
        hook_foreshadow_pattern='用不可知阴影、逐渐减少的物资/幸存者倒数和前人留痕拉满持续恐慌悬念。',
        event_trigger_pattern='环境封锁、污染/生化扩散与内部猜忌背叛触发高压求生候选事件。',
        decomposition_focus='重点拆解压力步步升级曲线、虚假安全感如何被打破以及高压下的残酷抉择链。',
    ),
    'GENRE_YOUXI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_LEVEL', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR'),
        preferred_mechanisms=('PLOT_MECHANISM_GAME', 'PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_TRADE'),
        optional_mechanisms=('PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_RULE_TASK'),
        arc_pattern='新手村破局→首通副本/隐藏任务→公会争夺与版本大事件→现实与游戏双线汇流。',
        pacing_profile='任务接取→开荒受阻→机制破局→掉落盘点，节奏爽利且反馈清晰。',
        hook_foreshadow_pattern='隐藏任务链、版本更新剧透与稀有装备打造作为强追读钩子与中期兑现。',
        event_trigger_pattern='副本开启、世界 Boss 刷新、公会宣战与版本规则变动驱动候选事件链。',
        decomposition_focus='重点拆解副本机制破局节点、收益正反馈节奏以及线上线下双线如何互相牵动。',
    ),
    'GENRE_DIANJING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'event_chain_triggers'),
        optional=('foreshadow_twist', 'disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_MANAGEMENT'),
        optional_mechanisms=('PLOT_MECHANISM_GAME', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_ROMANCE'),
        arc_pattern='低谷/新队组建→常规赛磨合与版本阵痛→季后赛逆袭→世界赛巅峰决战。',
        pacing_profile='训练/转会/舆论（中轻章）与 BO3/BO5 关键局战术博弈（重章）交替，杜绝纯报流水账。',
        hook_foreshadow_pattern='藏招体系、版本大改与宿敌约战构成天然赛季钩子，每轮赛事均有明确胜负兑现。',
        event_trigger_pattern='赛程抽签、版本补丁、伤病/舆论风波与关键团战失利触发连锁事件；严禁超自然危机机制。',
        decomposition_focus='重点拆解赛场内外情绪双线交替、关键战败如何倒逼战术与心智成长。',
    ),
    'GENRE_TIYU': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'event_chain_triggers'),
        optional=('foreshadow_twist', 'disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_CHRONICLE', 'NARRATIVE_STRUCTURE_SINGLE_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_UNDERDOG'),
        optional_mechanisms=('PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_REVENGE'),
        arc_pattern='体能/技术瓶颈起点→系统苦练与选拔淘汰→重大失利或伤病考验→大赛逆转登顶。',
        pacing_profile='训练蓄力→资格赛试水→大赛高密度对抗→赛后复盘消化，真实体现体能极限。',
        hook_foreshadow_pattern='技术弱点针对、体能极限倒计时与强敌纪录构成清晰追读悬念。',
        event_trigger_pattern='赛程升级、伤病突袭、临场判罚与对手战术针对触发真实赛场候选；严禁超自然机制。',
        decomposition_focus='重点拆解训练细节如何精准伏笔到决胜局技术动作，以及失败代价的不可逆转化。',
    ),
    'GENRE_YANQING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_MULTI_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_REVENGE'),
        optional_mechanisms=('PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_FARMING'),
        arc_pattern='心动/利益错位相遇→试探推拉与情感升温→现实阻隔/信任裂痕考验→双向奔赴与圆满/余韵收束。',
        pacing_profile='甜虐张弛交替，重章写表白/决裂/守护高光，轻章写细腻日常与情绪消化。',
        hook_foreshadow_pattern='情感错位、未说出口的秘密与信物/往事伏笔驱动强共情追读。',
        event_trigger_pattern='外部现实压力、家族/职场变故与第三方介入推动情感关系质变；严禁科幻/生化危机机制。',
        decomposition_focus='重点拆解感情线与事业/外部主线的双线交织、情感推拉节拍与误解/真相的合理揭示时机。',
    ),
    'GENRE_XIANDAI_YANQING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_SINGLE_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_TRADE'),
        optional_mechanisms=('PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_MYSTERY'),
        arc_pattern='都市现实交集起势→事业与亲密关系磨合→现实分歧/旧伤爆发→平等成熟的和解与承诺。',
        pacing_profile='日常轻甜与职场/家庭现实危机轮换，注重对话潜台词与情绪余韵。',
        hook_foreshadow_pattern='往事心结、秘密身份或关键抉择截止期拉动追读，伏笔重在情感记忆载体。',
        event_trigger_pattern='职场项目节点、原生家庭冲突与现实抉择岔路触发后继事件；严禁超自然危机机制。',
        decomposition_focus='重点拆解现代生活事件如何自然倒逼情感升温或破裂，避免无逻辑强行误会。',
    ),
    'GENRE_GUDAI_YANQING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_MULTI_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_FARMING'),
        optional_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_WAR'),
        arc_pattern='内宅/婚约困局破冰→宅斗/朝堂利益交织→家国或身世危机考验→并肩破局与情义闭环。',
        pacing_profile='深宅机锋、情感试探与朝局骤变轮换，兼顾礼制氛围与节奏爽感。',
        hook_foreshadow_pattern='身世秘辛、旧日恩怨信物与政敌阴谋构成多层伏笔，注重延迟揭晓与反转打脸。',
        event_trigger_pattern='赐婚/贬谪/族中大事与朝堂风波触发连锁候选事件；严禁科幻/生化危机机制。',
        decomposition_focus='重点拆解宅斗/朝堂事件线与感情推进如何同频共振，以及多配角支线如何反哺主线。',
    ),
    'GENRE_XIANSHI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('foreshadow_twist',),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_CHRONICLE', 'NARRATIVE_STRUCTURE_GROUP', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_ARC'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_FARMING'),
        optional_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_INVESTIGATION'),
        arc_pattern='扎根时代变迁与普通人命运抉择，小人物选择与宏观社会浪潮互相映照，结局讲究真实余味。',
        pacing_profile='扎实生活流推进与关键命运转折点结合，保留空章/轻章让读者消化现实重量。',
        hook_foreshadow_pattern='以具体生计难题、时代政策节点和人物未竟心愿作核心牵引，善用日常意象象征互锁。',
        event_trigger_pattern='经济周期波动、家庭变故与政策变动触发真实生活连锁反应；严禁超自然与系统危机机制。',
        decomposition_focus='重点拆解日常细节如何蓄积为不可逆的命运转折，以及群像支线如何映射时代全貌。',
    ),
    'GENRE_QINGCHUN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('foreshadow_twist', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_CHRONICLE', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_SINGLE_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_COMPETITION'),
        optional_mechanisms=('PLOT_MECHANISM_MYSTERY',),
        arc_pattern='学期/学年自然时间轴串联考试、社团、友情与懵懂心动，在毕业或关键抉择完成告别与成长。',
        pacing_profile='轻松鲜活的校园日常与考试/比赛/情感波折交替，结尾重在成长余韵与首尾呼应。',
        hook_foreshadow_pattern='用暗恋心事、未寄出的信、竞赛目标与小秘密埋设温柔伏笔。',
        event_trigger_pattern='月考、运动会、艺术节、家庭变动与升学分流触发校园事件链；严禁超自然危机机制。',
        decomposition_focus='重点拆解青春日常事件如何承担人物心智成长节点，避免流水账堆砌。',
    ),
    'GENRE_ERCIYUAN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_GAME', 'PLOT_MECHANISM_MULTI_WORLD'),
        optional_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_INFINITE', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_RULE_TASK'),
        arc_pattern='单元/篇章式高燃展开，每个篇章围绕一位核心伙伴或阵营矛盾爆发羁绊与信念高潮。',
        pacing_profile='轻松互动吐槽（轻章）与燃系信念对决（重章）鲜明切换，高潮注重情绪与主题双层共振。',
        hook_foreshadow_pattern='隐藏身份、阵营黑幕与过往羁绊伏笔在关键战斗前夕集中引爆。',
        event_trigger_pattern='学院/组织任务、异变副本与宿敌登场触发热血连锁候选事件。',
        decomposition_focus='重点拆解篇章结构节奏、伙伴支线如何汇入主线高潮及热血反转的情绪铺垫。',
    ),
    'GENRE_QINGXIAOSHUO': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('subplot_resource', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_SINGLE_POV', 'NARRATIVE_STRUCTURE_LOOP'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_GAME', 'PLOT_MECHANISM_MULTI_WORLD'),
        optional_mechanisms=('PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_FAST_TRANSMIGRATION', 'PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_RULE_TASK'),
        arc_pattern='高概念核心奇点开局→卷级起承转合解决单卷核心事件→逐步触碰深层世界真相。',
        pacing_profile='对话机锋密集、卷内节奏紧凑，单卷结尾自带小高潮与下一卷引子。',
        hook_foreshadow_pattern='以反差日常误会与高概念规则漏洞做高能钩子，卷末反转兼具趣味与情感回响。',
        event_trigger_pattern='异常日常事件、规则限制任务与角色秘密险些暴露驱动后继候选。',
        decomposition_focus='重点拆解单卷结构闭环、日常轻喜剧与核心悬疑/燃点的节奏切换。',
    ),
    'GENRE_TONGREN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_CHRONICLE'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_MULTI_WORLD', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_REVENGE'),
        optional_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_MAIN_GOD'),
        arc_pattern='锚定原典关键时间节点→主角介入引发蝴蝶效应→走出原创分支高潮并圆回情感期待。',
        pacing_profile='借原典名场面建立读者预期，再以原创变量制造超预期爽点与转折。',
        hook_foreshadow_pattern='利用读者与原典角色之间的“先知信息差”制造强烈期待与蝴蝶效应悬念。',
        event_trigger_pattern='原典大事件节点与主角改变因果后的连锁偏离触发新分支候选事件。',
        decomposition_focus='重点拆解如何借原典节点省去冗长铺垫，同时制造有说服力的原创蝴蝶效应分支。',
    ),
    'GENRE_ZHUTIAN': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_LEVEL', 'NARRATIVE_STRUCTURE_EPISODIC'),
        preferred_mechanisms=('PLOT_MECHANISM_INFINITE', 'PLOT_MECHANISM_FAST_TRANSMIGRATION', 'PLOT_MECHANISM_MULTI_WORLD', 'PLOT_MECHANISM_UPGRADE', 'PLOT_MECHANISM_UNDERDOG'),
        optional_mechanisms=('PLOT_MECHANISM_GAME', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_DUNGEON', 'PLOT_MECHANISM_MAIN_GOD', 'PLOT_MECHANISM_RULE_TASK', 'PLOT_MECHANISM_BIOCHEMICAL'),
        arc_pattern='主世界/空间主线串联多个独立副本世界：每世界完整起承转合，带回收获反哺总主线。',
        pacing_profile='入世界建立规则与任务→高压破局拿奖励→回归结算强化→开启更高阶世界。',
        hook_foreshadow_pattern='主神/诸天背后真相作全书长伏笔，各副本隐藏任务与跨界道具联动制造高密度钩子。',
        event_trigger_pattern='主神任务发布、副本世界异变与跨界回归结算驱动强条件后继事件。',
        decomposition_focus='重点拆解副本世界如何保持独立新鲜感又不脱离全书主线，以及回归结算的节奏控制。',
    ),
    'GENRE_MOSHI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('disclosure_suspense', 'multi_viewpoint'),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_SERIAL'),
        preferred_mechanisms=('PLOT_MECHANISM_APOCALYPSE', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_UPGRADE'),
        optional_mechanisms=('PLOT_MECHANISM_FARMING', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_DISASTER', 'PLOT_MECHANISM_BIOCHEMICAL', 'PLOT_MECHANISM_CONTAMINATION'),
        arc_pattern='灾变爆发求生→小队建立与物资转移→据点经营与势力兼并→探明灾变根源与文明重建。',
        pacing_profile='极端物资/安全倒计时压迫与据点建设休整交替，时刻保持生存危机感。',
        hook_foreshadow_pattern='灾变源头真相、异变升级信号与稀缺补给线危机构成长短结合的追读钩子。',
        event_trigger_pattern='尸潮/极端天灾、生化污染扩散、补给耗尽与外部掠夺者逼近直接触发求生事件链。',
        decomposition_focus='重点拆解资源稀缺如何直接驱动每次行动与冲突，以及从个人求生到群体重建的格局升级。',
    ),
    'GENRE_SAIBO': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_SINGLE_POV'),
        preferred_mechanisms=('PLOT_MECHANISM_DYSTOPIA', 'PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_POLITICAL'),
        optional_mechanisms=('PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_CONTAMINATION', 'PLOT_MECHANISM_RULE_TASK'),
        arc_pattern='底层灰色委托切入→意外卷入巨企/黑墙核心机密→被多方追杀反击→付出沉重代价撕开秩序裂缝。',
        pacing_profile='冷峻霓虹潜行侦查与骤然义体火并交替，信息博弈与背叛反转密度极高。',
        hook_foreshadow_pattern='记忆篡改、芯片隐藏数据与委托人真实目的构成黑色电影式多层伏笔与反转。',
        event_trigger_pattern='委托失控、企业通缉升级、网络入侵反追踪与义体过载触发连锁危局。',
        decomposition_focus='重点拆解黑色委托链如何层层揭开巨企阴谋，以及每一次升级改造带来的不可逆代价。',
    ),
    'GENRE_WEILAI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers', 'event_crisis_mechanisms'),
        optional=(),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_EPIC', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_NONLINEAR'),
        preferred_mechanisms=('PLOT_MECHANISM_DYSTOPIA', 'PLOT_MECHANISM_CIVILIZATION', 'PLOT_MECHANISM_SPACE', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_MANAGEMENT'),
        optional_mechanisms=('PLOT_MECHANISM_PLANET', 'PLOT_MECHANISM_STAR', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_DISASTER', 'PLOT_MECHANISM_ALIEN', 'PLOT_MECHANISM_CONTAMINATION'),
        arc_pattern='未来社会表层稳定下的微小裂缝→体制/技术矛盾激化→文明抉择与新秩序诞生。',
        pacing_profile='社会探索与技术/制度危机推演交错，注重观念碰撞与宏观余波链。',
        hook_foreshadow_pattern='系统异常日志、被抹除的旧世界史料构成长线延迟解码伏笔。',
        event_trigger_pattern='生态临界、AI/算法治理失衡与跨星域事件触发多方条件候选。',
        decomposition_focus='重点拆解未来制度裂缝如何一步步演变为全局危机，以及个人选择对文明走向的撬动。',
    ),
    'GENRE_TONGHUA': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('subplot_resource',),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_QUEST', 'NARRATIVE_STRUCTURE_FRAME', 'NARRATIVE_STRUCTURE_EPISODIC'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MYSTERY'),
        optional_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_REVENGE'),
        arc_pattern='清晰出发使命→三次递进试炼/诺言考验→核心象征物兑现→闭环首尾呼应与寓言余味。',
        pacing_profile='节奏凝练明快、重复中有递进，重在象征意象与主题互锁。',
        hook_foreshadow_pattern='诺言代价、时限魔咒（如午夜）与反复出现的象征物承担伏笔与回收。',
        event_trigger_pattern='违约惩罚、试炼完成与奇遇触发清晰直线后继；严禁硬核生化/星际危机机制。',
        decomposition_focus='重点拆解寓言三段递进结构、象征物首尾呼应与诺言兑现闭环。',
    ),
    'GENRE_ERTONG': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm',
                 'plot_mechanism', 'reader_engagement', 'event_chain_triggers'),
        optional=('foreshadow_twist', 'disclosure_suspense', 'subplot_resource'),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_QUEST'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MYSTERY'),
        optional_mechanisms=('PLOT_MECHANISM_COMPETITION', 'PLOT_MECHANISM_GAME'),
        arc_pattern='好奇心触发小冒险→伙伴合作克服困难→收获成长与温暖回归。',
        pacing_profile='章短轻快、每章均有清晰小目标与有趣反馈，线索直白易懂。',
        hook_foreshadow_pattern='善用趣味谜题、神奇小物件与友善约定吸引小读者继续翻页。',
        event_trigger_pattern='发现新线索、伙伴求助与趣味挑战触发积极向上的后继事件；严禁血腥/暗黑危机机制。',
        decomposition_focus='重点拆解简洁清晰的单元冒险节奏与积极正向的成长兑现。',
    ),
    'GENRE_JISHI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('reader_engagement', 'foreshadow_twist'),
        preferred_structures=('NARRATIVE_STRUCTURE_CHRONICLE', 'NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_LINEAR'),
        preferred_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MANAGEMENT'),
        optional_mechanisms=('PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_TRADE'),
        arc_pattern='忠实重大真实事件脉络，通过交叉视角与时间线剪辑呈现事件背后的深层因果。',
        pacing_profile='客观纪实推进与关键历史转折点深度停顿结合，严守时间与事实顺序不可颠倒。',
        hook_foreshadow_pattern='以真实未解疑问、关键档案细节与命运交叉点维系阅读张力，杜绝杜撰反转。',
        event_trigger_pattern='真实因果事件与决策连锁自然推进；严禁任何虚构超自然或系统危机机制。',
        decomposition_focus='重点拆解非虚构叙事如何通过剪辑次序、多方交叉证言与关键节点聚焦建立戏剧张力。',
    ),
    'GENRE_ZHIYE': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_EPISODIC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_QUEST'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_COMPETITION'),
        optional_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_ROMANCE'),
        arc_pattern='专业案例/项目单元推进 + 职级晋升与行业变革总主线，专业难题即核心戏剧冲突。',
        pacing_profile='项目立项/接案→专业受阻与职场博弈→硬核专业破局→复盘晋升，节奏干脆利落。',
        hook_foreshadow_pattern='用行业黑幕、关键技术/业务隐患与职场派系暗线做长线伏笔，专业细节即反转依据。',
        event_trigger_pattern='甲方变卦、审计/监管检查、事故危机与核心人事调整触发职场连锁；严禁超自然危机机制。',
        decomposition_focus='重点拆解专业案例如何转化为普通读者也能看懂的冲突与爽点，以及单案与主线的结合。',
    ),
    'GENRE_NVXING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('multi_viewpoint',),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_ROMANCE'),
        optional_mechanisms=('PLOT_MECHANISM_UNDERDOG', 'PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_INVESTIGATION'),
        arc_pattern='突破外部规训/困局起势→建立经济与精神主体性→在事业/关系考验中完成自我实现闭环。',
        pacing_profile='现实阻力压迫与清醒反击爽感交替，重视人物自我认知跃迁的节奏留白。',
        hook_foreshadow_pattern='用职场/家庭隐蔽算计、自我觉醒契机与女性互助支线埋设情感与爽点双线钩子。',
        event_trigger_pattern='职场竞争、家庭/婚姻危机与合作破局触发连锁选择；严禁超自然危机机制。',
        decomposition_focus='重点拆解主角每一次主动选择如何扭转被动局面，以及女性群像支线如何互相映照。',
    ),
    'GENRE_JIATING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'disclosure_suspense', 'event_chain_triggers'),
        optional=('foreshadow_twist',),
        preferred_structures=('NARRATIVE_STRUCTURE_LINEAR', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_GROUP', 'NARRATIVE_STRUCTURE_CHRONICLE'),
        preferred_mechanisms=('PLOT_MECHANISM_GROWTH', 'PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_TRADE'),
        optional_mechanisms=('PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_REVENGE'),
        arc_pattern='突发家庭事件（遗产/照护/婚变/搬迁）撕开表层和平→积年旧账爆发→在代价与理解中重建边界。',
        pacing_profile='日常饭桌微摩擦（中轻章）与重大家庭变故摊牌（重章）交替，重在情感余波链。',
        hook_foreshadow_pattern='隐藏多年未说的家庭秘密、偏心旧账与财产安排构成强代入感悬念。',
        event_trigger_pattern='突发疾病、房产纠纷、子女教育与亲属借贷触发多米诺式家庭连锁事件；严禁超自然危机。',
        decomposition_focus='重点拆解日常细节如何积累为摊牌冲突，以及多视角展现各家庭成员苦衷的编排方式。',
    ),
    'GENRE_GONGTING': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=(),
        preferred_structures=('NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_SERIAL', 'NARRATIVE_STRUCTURE_CHRONICLE'),
        preferred_mechanisms=('PLOT_MECHANISM_POLITICAL', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_WAR', 'PLOT_MECHANISM_MYSTERY'),
        optional_mechanisms=('PLOT_MECHANISM_ROMANCE', 'PLOT_MECHANISM_MANAGEMENT', 'PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_UNDERDOG'),
        arc_pattern='潜伏布局→借势破局与连环反杀→多派系倾轧升级→夺权/定鼎与代价反思收束。',
        pacing_profile='暗流布局（中章）→朝堂/宫宴骤变翻盘（高密重章）→清洗余波（轻章），信息博弈贯穿始终。',
        hook_foreshadow_pattern='明修栈道暗度陈仓：善用深层伏笔掩体、一石二鸟与双伏笔联动朝堂反转。',
        event_trigger_pattern='圣意试探、弹劾风波、储位更迭与外敌军报触发牵一发而动全身的连锁事件；严禁超自然危机。',
        decomposition_focus='重点拆解多步连环计的前置铺垫、信息不对称下的借刀杀人及每次博弈后的权力格局重洗。',
    ),
    'GENRE_SHEHUI': _pprofile(
        primary=('narrative_structure', 'arc_conflict', 'opening_ending', 'chapter_rhythm', 'subplot_resource', 'multi_viewpoint',
                 'plot_mechanism', 'reader_engagement', 'foreshadow_twist', 'disclosure_suspense', 'event_chain_triggers'),
        optional=(),
        preferred_structures=('NARRATIVE_STRUCTURE_NONLINEAR', 'NARRATIVE_STRUCTURE_MULTI_POV', 'NARRATIVE_STRUCTURE_ARC', 'NARRATIVE_STRUCTURE_GROUP'),
        preferred_mechanisms=('PLOT_MECHANISM_INVESTIGATION', 'PLOT_MECHANISM_MYSTERY', 'PLOT_MECHANISM_REVENGE', 'PLOT_MECHANISM_POLITICAL'),
        optional_mechanisms=('PLOT_MECHANISM_TRADE', 'PLOT_MECHANISM_GROWTH'),
        arc_pattern='表层案件切入→顺藤摸瓜牵出庞大利益链与制度盲区→在程序/良知困境中揭开结构性真相。',
        pacing_profile='调查取证线与涉案群像命运线双轨交错，真相揭晓兼顾逻辑震撼与社会刺痛。',
        hook_foreshadow_pattern='以证人反常沉默、资金流断层与旧年未结案构成深层伏笔，反转直指社会动因。',
        event_trigger_pattern='关键证据被销毁、舆论反转、涉案者灭口或自首触发紧迫连锁事件；严禁任何超自然机制。',
        decomposition_focus='重点拆解案件线如何自然牵引出社会结构纵深、群像视角如何拼接真相全貌。',
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
    if cat_id == 'event_crisis_mechanisms':
        return f'当前类型（{joined}）以常规因果与现实/时代事件为主，副本、污染、外星、生化、主神与规则任务属于跨类型危机机制，避免违背题材边界。'
    if cat_id == 'multi_viewpoint':
        return f'当前类型（{joined}）默认更适合聚焦核心视角，多视角群像编排可按需展开。'
    return f'此分类在 {joined} 中属于跨类型扩展项，仅在作品明确需要时按需启用。'


def plot_profile_for_types(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Build genre-targeted 06 plot_design + 07 event_design profile with item-level mechanism guidance."""
    normalized, mains = _resolve_main_genres(types)
    mapping = type_map()
    type_objs = [{'id': tid, 'name': mapping[tid]['name'], 'parent_id': mapping[tid].get('parent_id')}
                 for tid in normalized if tid in mapping]
    main_names = [mapping[mid]['name'] for mid in mains if mid in mapping]

    profiles = [GENRE_PLOT_PROFILES.get(mid, DEFAULT_PLOT_PROFILE) for mid in mains] if mains else [DEFAULT_PLOT_PROFILE]

    relevance_by_cat: dict[str, str] = {}
    for cat in PLOT_EVENT_CATEGORIES:
        cid = cat['id']
        best = 'out_of_scope'
        for prof in profiles:
            if cid in prof['primary']:
                best = 'primary'
                break
            if cid in prof['optional'] and best != 'primary':
                best = 'optional'
        relevance_by_cat[cid] = best

    pref_structs: list[str] = []
    opt_structs: list[str] = []
    pref_mechs: list[str] = []
    opt_mechs: list[str] = []
    arc_patterns: list[str] = []
    pacing_profiles: list[str] = []
    hook_patterns: list[str] = []
    event_patterns: list[str] = []
    decomp_focuses: list[str] = []
    for prof in profiles:
        for s in prof['preferred_structures']:
            if s not in pref_structs:
                pref_structs.append(s)
        for s in prof['optional_structures']:
            if s not in opt_structs and s not in pref_structs:
                opt_structs.append(s)
        for m in prof['preferred_mechanisms']:
            if m not in pref_mechs:
                pref_mechs.append(m)
        for m in prof['optional_mechanisms']:
            if m not in opt_mechs and m not in pref_mechs:
                opt_mechs.append(m)
        pp = prof['plot_profile']
        if pp['arc_pattern'] not in arc_patterns:
            arc_patterns.append(pp['arc_pattern'])
        if pp['pacing_profile'] not in pacing_profiles:
            pacing_profiles.append(pp['pacing_profile'])
        if pp['hook_foreshadow_pattern'] not in hook_patterns:
            hook_patterns.append(pp['hook_foreshadow_pattern'])
        if pp['event_trigger_pattern'] not in event_patterns:
            event_patterns.append(pp['event_trigger_pattern'])
        if prof['decomposition_focus'] not in decomp_focuses:
            decomp_focuses.append(prof['decomposition_focus'])

    categories: list[dict[str, Any]] = []
    for cat in PLOT_EVENT_CATEGORIES:
        cid = cat['id']
        rel = relevance_by_cat[cid]
        categories.append({
            'id': cid,
            'slot': cat['slot'],
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

    categories.sort(key=lambda r: (RELEVANCE_RANK[r['relevance']], PLOT_EVENT_CATEGORY_ORDER[r['id']]))
    return {
        'types': type_objs,
        'main_types': [{'id': mid, 'name': mapping[mid]['name']} for mid in mains if mid in mapping],
        'has_genre_binding': bool(mains),
        'primary_categories': [c['id'] for c in categories if c['relevance'] == 'primary'],
        'optional_categories': [c['id'] for c in categories if c['relevance'] == 'optional'],
        'out_of_scope_categories': [c['id'] for c in categories if c['relevance'] == 'out_of_scope'],
        'preferred_structures': pref_structs,
        'optional_structures': opt_structs,
        'preferred_mechanisms': pref_mechs,
        'optional_mechanisms': opt_mechs,
        'categories': categories,
        'structure_categories': [c for c in categories if c['slot'] == 'structure'],
        'hook_categories': [c for c in categories if c['slot'] == 'hook'],
        'plot_categories': [c for c in categories if c['target_stage'] == 'plot_design'],
        'event_categories': [c for c in categories if c['target_stage'] == 'event_design'],
        'plot_profile': {
            'arc_pattern': '；'.join(arc_patterns),
            'pacing_profile': '；'.join(pacing_profiles),
            'hook_foreshadow_pattern': '；'.join(hook_patterns),
            'event_trigger_pattern': '；'.join(event_patterns),
        },
        'decomposition_focus': '；'.join(decomp_focuses),
        'step_boundaries': {
            'plot_design': deepcopy(PLOT_STEP_BOUNDARY),
            'event_design': deepcopy(EVENT_STEP_BOUNDARY),
        },
    }


def _annotate_typed_children(children: list[dict[str, Any]], primary_ids: list[str], optional_ids: list[str],
                             *, has_genre: bool) -> list[dict[str, Any]]:
    if not has_genre:
        return children
    primary_set = set(primary_ids)
    optional_set = set(optional_ids)
    annotated = []
    for idx, child in enumerate(children):
        item = deepcopy(child)
        ident = item.get('id', '')
        rel = 'primary' if ident in primary_set else 'optional' if ident in optional_set else 'out_of_scope'
        item.update(relevance=rel, relevance_label=RELEVANCE_LABELS[rel], _orig_idx=idx)
        annotated.append(item)
    annotated.sort(key=lambda r: (RELEVANCE_RANK[r['relevance']], r['_orig_idx']))
    for item in annotated:
        item.pop('_orig_idx', None)
    return annotated


def annotate_plot_groups(slot: str, groups: list[dict[str, Any]],
                         types: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Annotate structure (06) or hook (06-07) option groups & typed children with genre relevance."""
    profile = plot_profile_for_types(types)
    by_group_key = {c['catalog_group_key']: c for c in profile['categories'] if c['slot'] == slot}
    annotated: list[dict[str, Any]] = []
    for group in groups:
        row = deepcopy(group)
        meta = by_group_key.get(row['key'])
        if meta:
            row.update(
                plot_category=meta['id'],
                target_stage=meta['target_stage'],
                target_stage_label=meta['target_stage_label'],
                description=meta['description'],
                usage_mode=meta['usage_mode'],
                relevance=meta['relevance'],
                relevance_label=meta['relevance_label'],
                boundary_note=meta['boundary_note'],
                source_files=meta['source_files'],
            )
            if meta['id'] == 'narrative_structure' and row.get('children'):
                row['children'] = _annotate_typed_children(
                    row['children'], profile['preferred_structures'], profile['optional_structures'],
                    has_genre=profile['has_genre_binding'],
                )
            elif meta['id'] in ('plot_mechanism', 'event_crisis_mechanisms') and row.get('children'):
                row['children'] = _annotate_typed_children(
                    row['children'], profile['preferred_mechanisms'], profile['optional_mechanisms'],
                    has_genre=profile['has_genre_binding'],
                )
        annotated.append(row)
    annotated.sort(key=lambda r: (
        RELEVANCE_RANK.get(r.get('relevance', 'optional'), 1),
        PLOT_EVENT_CATEGORY_ORDER.get(r.get('plot_category', ''), 99),
    ))
    return annotated


def annotate_plot_children(slot: str, parent_key: str, children: list[dict[str, Any]],
                           types: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Annotate children when fetching a single parent group via /api/options?slot=...&parent=...&types=..."""
    profile = plot_profile_for_types(types)
    if slot == 'structure' and parent_key == 'structure.group.types':
        return _annotate_typed_children(
            children, profile['preferred_structures'], profile['optional_structures'],
            has_genre=profile['has_genre_binding'],
        )
    if slot == 'hook' and parent_key in ('hook.group.types', 'hook.group.event_crisis_mechanisms'):
        return _annotate_typed_children(
            children, profile['preferred_mechanisms'], profile['optional_mechanisms'],
            has_genre=profile['has_genre_binding'],
        )
    return deepcopy(children)


def classify_plot_event_method(body: dict[str, Any]) -> list[str]:
    """Deterministically classify a plot_design (06) or event_design (07) method into matching categories."""
    if not isinstance(body, dict):
        return []
    tasks = set(body.get('tasks') or ())
    outputs = body.get('outputs') or ()
    output_stages = {o.get('stage') for o in outputs if isinstance(o, dict)}
    plot_tasks = {'main_plot', 'subplot', 'volume_outline', 'chapter_outline', 'hook', 'foreshadow', 'information', 'pacing'}
    targets_plot = bool(tasks & plot_tasks) or 'plot_design' in output_stages
    targets_event = 'event_chain' in tasks or 'event_design' in output_stages
    if not (targets_plot or targets_event):
        return []
    text = ' '.join([
        str(body.get('title') or ''),
        ' '.join(str(x) for x in (body.get('applicability') or ())),
        ' '.join(str(o.get('instruction') or '') for o in (body.get('operations') or ()) if isinstance(o, dict)),
        ' '.join(str(o.get('description') or '') for o in outputs if isinstance(o, dict)),
    ])
    allowed_stages = set()
    if targets_plot:
        allowed_stages.add('plot_design')
    if targets_event:
        allowed_stages.add('event_design')
    scores: list[tuple[int, int, str]] = []
    for cat in PLOT_EVENT_CATEGORIES:
        if cat['target_stage'] not in allowed_stages:
            continue
        hits = sum(1 for kw in cat['keywords'] if kw in text)
        if hits:
            scores.append((-hits, PLOT_EVENT_CATEGORY_ORDER[cat['id']], cat['id']))
    if not scores:
        fallback = []
        if targets_plot:
            if 'foreshadow' in tasks:
                fallback.append('foreshadow_twist')
            elif 'hook' in tasks:
                fallback.append('reader_engagement')
            elif 'information' in tasks:
                fallback.append('disclosure_suspense')
            elif 'subplot' in tasks:
                fallback.append('subplot_resource')
            elif 'chapter_outline' in tasks or 'pacing' in tasks:
                fallback.append('chapter_rhythm')
            else:
                fallback.append('arc_conflict')
        if targets_event:
            fallback.append('event_chain_triggers')
        return fallback
    scores.sort()
    return [cid for _, _, cid in scores[:3]]


def plot_event_decomposition_prompt(
    types: list[str] | tuple[str, ...] | None = None,
    domain: str = 'main_plot',
    *,
    phase: str = 'relations',
) -> str:
    """Concise genre-targeted guidance for decomposing/deriving 06 plot_design & 07 event_design domains."""
    profile = plot_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    type_label = ' / '.join(t['name'] for t in profile['main_types']) or '当前参考书'
    primary_plot = '、'.join(by_id[cid]['short_name'] for cid in profile['primary_categories'] if by_id[cid]['target_stage'] == 'plot_design')
    oos_names = '、'.join(by_id[cid]['short_name'] for cid in profile['out_of_scope_categories'])

    if phase == 'methods':
        text = (
            f'【06剧情与07事件·分类型资料边界（{type_label}）】'
            f'06剧情核心子域：{primary_plot or "骨架冲突与伏笔钩子"}；'
            f'主线结构特点：{profile["plot_profile"]["arc_pattern"]}；'
            f'事件链触发特点：{profile["plot_profile"]["event_trigger_pattern"]}。'
        )
        if oos_names:
            text += f'非本类型常规子域（{oos_names}）除非原作确有直接原文证据，否则不要强行套用。'
        text += (
            '严格守住 06 与 07 分工：主线/支线/卷章目标/伏笔窗口/读者信息序落入 plot_design'
            '（directions/members/event_nodes/reader_plan/promise_plan/continuations）；'
            '前事件完成门触发的条件后继分支落入 event_design（candidates），不提前造场景卡或把候选当作既成事实。'
        )
        return text

    domain_note = {
        'main_plot': '聚焦全书总问题、主线不可逆抉择、阶段转折与结局承诺兑现，区分全书主线（06）与单场动作细节（08）。',
        'subplot': '聚焦支线独立目标、与主线交汇节点及交汇后对主线的实际改写，识别配角引发的后继事件条件（07）。',
        'hook': '聚焦章末/场末设问、读者期待与后续章节实际回应或升级，未回应时保留未决。',
        'foreshadow': '聚焦埋设载体、伪装掩体、休眠间隔与跨章回收窗口，必须核对埋设与回收两端不同原文。',
        'information': '严格区分角色知情与读者知情先后、误导来源及纠正证据，服务 06 reader_plan 与 09 披露边界。',
        'chapter_progress': '逐章核对进入前提、核心转折、留下的直接压力（next_pressure）及下章如何顺势承接（06 continuations / 07 后继事件）。',
    }.get(domain, '')
    text = (
        f'【06剧情与07事件·按本书类型（{type_label}）定向核对{domain}】'
        f'{domain_note}{profile["decomposition_focus"]}'
    )
    if oos_names:
        text += f'非本类型常规项（{oos_names}）仅在原文确有直接依据时记录，切勿脑补。'
    return text


def plot_event_stage_prompt_packet(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Compact deterministic packet frozen into planning manifests for 06 plot_design & 07 event_design."""
    profile = plot_profile_for_types(types)
    type_list = [{'id': t['id'], 'name': t['name']} for t in profile['types']]

    def _for_stage(stage: str) -> dict[str, Any]:
        cats = [c for c in profile['categories'] if c['target_stage'] == stage]
        boundary = profile['step_boundaries'][stage]
        packet: dict[str, Any] = {
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
            'plot_profile': profile['plot_profile'],
            'step_boundary': {
                'responsibility': boundary['responsibility'],
                'out_of_scope': list(boundary['out_of_scope']),
                'downstream_steps': [d['step_id'] for d in boundary['downstream_steps']],
            },
        }
        if stage == 'plot_design':
            packet['preferred_structures'] = list(profile['preferred_structures'])
            packet['preferred_mechanisms'] = [m for m in profile['preferred_mechanisms'] if m not in _CRISIS_MECHS]
        else:
            packet['preferred_event_mechanisms'] = [m for m in (*profile['preferred_mechanisms'], *profile['optional_mechanisms']) if m in _CRISIS_MECHS]
        return packet

    return {
        'plot_design': _for_stage('plot_design'),
        'event_design': _for_stage('event_design'),
    }


def plot_blueprint(library: Any, types: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Combine genre-targeted 06/07 profile with live workspace coverage and length recommendation."""
    from nw.studio.downstream_handoff import audit_downstream_handoff

    profile = plot_profile_for_types(types)
    audit = audit_downstream_handoff(library, types=list(types), planning_hierarchy=True)
    plot_tasks = {'main_plot', 'subplot', 'volume_outline', 'chapter_outline', 'hook', 'foreshadow', 'information', 'pacing', 'event_chain'}
    target_methods = [
        m for m in audit.get('methods', ())
        if bool(plot_tasks & set(m.get('tasks', ())))
        or bool({'plot_design', 'event_design'} & set(m.get('output_stages', ())))
    ]
    by_cat_rec: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in PLOT_EVENT_CATEGORIES}
    by_cat_draft: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in PLOT_EVENT_CATEGORIES}
    by_cat_blocked: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in PLOT_EVENT_CATEGORIES}

    for method in target_methods:
        cats = method.get('plot_categories') or []
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
    plot_step = step_by_id.get('plot_design', {})
    event_step = step_by_id.get('event_design', {})
    return {
        **profile,
        'categories': categories_with_coverage,
        'structure_categories': [c for c in categories_with_coverage if c['slot'] == 'structure'],
        'hook_categories': [c for c in categories_with_coverage if c['slot'] == 'hook'],
        'plot_categories': [c for c in categories_with_coverage if c['target_stage'] == 'plot_design'],
        'event_categories': [c for c in categories_with_coverage if c['target_stage'] == 'event_design'],
        'coverage_summary': {
            'total_plot_event_methods': len(target_methods),
            'receivable_plot_methods': plot_step.get('receivable_count', 0),
            'receivable_event_methods': event_step.get('receivable_count', 0),
            'primary_category_count': len(profile['primary_categories']),
            'covered_primary_categories': covered_primary,
            'gap_primary_categories': [
                c['id'] for c in categories_with_coverage
                if c['relevance'] == 'primary' and c['receivable_count'] == 0
            ],
            'length_recommendation_ready': audit['length_recommendation']['ready'],
        },
        'length_recommendation': audit['length_recommendation'],
        'originality_audit': audit['originality_audit'],
    }
