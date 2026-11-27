"""Genre-targeted material taxonomy, step boundaries, and coverage for 08–11 execution stages.

Covers the mid-workflow causal execution chain directly aligned with:
  - 08 action_design (`action_design*.py`)
  - 09 scene_design (`scene_design*.py`)
  - 10 state_transition (`state_transition*.py`)
  - 11 state_propagation (`state_propagation*.py`)

Design goals:
  1. Classify original workflow materials for 08–11 into 12 bounded, non-overlapping
     sub-categories explicitly bound to their owning stage and exact output fields.
  2. Enforce strict genre boundaries across all 35 main genres so realistic, mystery,
     historical, romance, workplace, or family novels automatically isolate supernatural
     energy/alchemy/array/breakthrough rules and sci-fi mecha/AI/containment rules,
     while xianxia/xuanhuan or sci-fi/cyberpunk activate only what belongs to them.
  3. Enforce strict inter-step handoff boundaries along 07 → 08 → 09 → 10 → 11 → 12:
     - 08 builds concrete action candidates (object/action/obstacle/response/result +
       requires + cost) without writing scene POV cards (09) or final after_state (10).
     - 09 binds upstream event + action into POV-bounded scene cards and before_state
       snapshots without mutating after_state (10) or drafting prose (15).
     - 10 verifies before_state verbatim, requires an external action trigger for every
       after_state delta, keeps costs persistent, and never auto-broadcasts off-scene
       knowledge (11).
     - 11 emits gated `conditional_candidate` propagations with explicit carriers
       (witness/message/rumor/trace) and all 3 gates enabled, never writing WORLD facts
       directly or letting unwitnessing actors become telepathically omniscient.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.studio.catalog import canonical_types, type_map


ACTION_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'action_design',
    'step_name': '08. 行动博弈与试错代价',
    'responsibility': (
        '仅在卷/章/场细化运行：承接 04 人物能力与限制、06/07 事件节点及已冻结 accepted_state，'
        '为可行动人物（can_act=true）设计具备完整步骤链（object/action/obstacle/response/result）、'
        '最低能力门槛（requires）、真实代价（cost）与限制（limits）的行动候选（candidates）及缺前置待核项（waiting）。'
    ),
    'upstream_steps': [
        {'step_id': 'world_design', 'supplies': '外部规则限制、道具边界与世界硬代价'},
        {'step_id': 'character_design', 'supplies': '人物 capabilities（can_act/abilities/limits）与初始状态'},
        {'step_id': 'static_relations', 'supplies': '权力/信息不对称、立场对立与关系约束'},
        {'step_id': 'plot_design', 'supplies': 'event_nodes 冲突与阻碍'},
        {'step_id': 'event_design', 'supplies': '条件后继事件候选（candidates）'},
    ],
    'produces': [
        'candidates（含 id/source_ids/event/actor/action/steps/requires/cost/limits/status=candidate）',
        'waiting（缺失能力、对象或前态前置时的明确待核记录）',
    ],
    'downstream_steps': [
        {'step_id': 'scene_design', 'consumes': '显式选用行动候选（selected_actions），原样写入 choice'},
        {'step_id': 'state_transition', 'consumes': '承接具体外部行动、应对与代价核对状态变化'},
        {'step_id': 'anchor_design', 'consumes': '按 action_ref 与 step_index（before/during/after）落点具象节拍'},
    ],
    'out_of_scope': [
        '禁止为 can_act=false 的受限人物安排行动，或使用 04 capabilities 中不存在的能力（不得临时编造外挂能力）。',
        '禁止省略障碍/应对/结果或写出无代价的空洞行动口号；每个动作须落实具体 steps 与 cost。',
        '禁止越界生成 09 场景卡（POV、出场名单、场景空间/时间线）或提前落盘 10 最终状态变化（after_state）。',
        '非超自然题材严禁引入炼丹/炼器/阵法/召唤/御兽/能量公式，非科幻异常题材严禁引入机甲/AI/机器人/异常收容机制。',
    ],
}


SCENE_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'scene_design',
    'step_name': '09. 场景结构与POV边界',
    'responsibility': (
        '仅在卷/章/场细化运行：承接上游事件（06/07）与行动候选（08），为每场显式绑定事件（selected_events）与行动（selected_actions），'
        '建立严格受限的 POV 视角、在场人员与目标、空间方位动线、可披露信息边界（allowed_disclosure）、'
        '章场推进（scene_progress/cast_payoffs）以及交接给 10 步的 events.before_state 快照。'
    ),
    'upstream_steps': [
        {'step_id': 'plot_design', 'supplies': '章纲目标、event_nodes、reader_plan 信息顺序与 promise_plan 伏笔窗口'},
        {'step_id': 'event_design', 'supplies': '后继事件候选供本场显式挑选'},
        {'step_id': 'action_design', 'supplies': '行动候选（steps/cost）供 selected_actions 选用'},
        {'step_id': 'character_design', 'supplies': '人物入场边界、暗身份隔离与配角阵容职责'},
    ],
    'produces': [
        'members（kind=scene 场景卡：title/goal/pov/characters/character_goals/entering_state/conflict/choice/planned_result/allowed_disclosure）',
        'chapters（章场编号与 story_order 排列）',
        'events（交付 10 步的 entity/trigger/before_state 快照）',
        'selected_events / selected_actions（及启用时的 scene_progress / cast_payoffs / passage_choices）',
    ],
    'downstream_steps': [
        {'step_id': 'state_transition', 'consumes': '原样核对 events.before_state 并回填 choice/planned_result 补丁'},
        {'step_id': 'anchor_design', 'consumes': '按本场 POV 与空间锚点设计可见节拍'},
        {'step_id': 'expression_design', 'consumes': '承接本场 allowed_disclosure、情绪温度与空间开篇要求'},
        {'step_id': 'writer', 'consumes': '以场景卡作为受限视角写作边界'},
    ],
    'out_of_scope': [
        '禁止跳过 selected_events 或 selected_actions 自行编造未承接上游的事件/行动，choice 须忠实采用所选 action 原文。',
        '禁止在场景中途无依据切换 POV，禁止把未在场/未目击信息或 author_only 暗身份偷跑进 allowed_disclosure。',
        '禁止把条件事件/行动候选直接宣称为既成 WORLD 事实，或越界提前改写 10 步 after_state。',
        '禁止直接撰写 15 步正文散文段落；非超自然题材严禁引入能量盲区/突破临界点/固化态场景规则。',
    ],
}


STATE_TRANSITION_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'state_transition',
    'step_name': '10. 状态变化与外部因果',
    'responsibility': (
        '仅在卷/章/场细化运行：逐条核对 09 场景交付的 events.before_state，严格依据本场具体的外部行动与应对选择，'
        '落盘至少有一项实质差值的 after_state、不可凭空消失的代价（cost）、失败情形（failure）、'
        '后场延续机制（continuity）以及回写场景卡的 patches（choice/planned_result）。'
    ),
    'upstream_steps': [
        {'step_id': 'scene_design', 'supplies': 'events（entity/before_state）与本场冲突、选择、披露范围'},
        {'step_id': 'action_design', 'supplies': '具体外部行动步骤、阻碍应对与成本限制'},
        {'step_id': 'world_design', 'supplies': '资源守恒、属性不可突变与道具状态连续性规则'},
        {'step_id': 'character_design', 'supplies': '人物心智模型、核心属性与初始状态基线'},
    ],
    'produces': [
        'patches（scene/choice/planned_result 与本场限制保持一致）',
        'transitions（scene/entity/event/before_state/action/after_state/cost/failure/continuity）',
    ],
    'downstream_steps': [
        {'step_id': 'state_propagation', 'consumes': '以 transition.event 作为 planned_change 根变化设计传播候选'},
        {'step_id': 'anchor_design', 'consumes': '把状态/情绪/代价变化转为可见身体与物件节拍'},
        {'step_id': 'acceptance', 'consumes': '对照正文实际引文核验状态增量与连续性'},
    ],
    'out_of_scope': [
        '禁止篡改 before_state（必须与 09 events.before_state 完全一致），禁止输出无任何属性变化的空壳 transition。',
        '禁止绕过具体外部行动让角色凭空顿悟、属性突变或无故回血/消除旧代价（代价可以转化或缓释，但不可凭空清零）。',
        '禁止在本步直接让场外未目击人物或势力自动得知变化（跨实体知情传播必须交给 11 state_propagation）。',
        '非超自然题材严禁引入能量储备/纯度跃迁或生命构造强化/退化反哺规则。',
    ],
}


STATE_PROPAGATION_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'state_propagation',
    'step_name': '11. 状态传播与连锁感知',
    'responsibility': (
        '仅在卷/章/场细化运行：以 10 步 planned_change 或已接受 WORLD 事实（accepted_fact）为根变化，'
        '通过明确的物理/社会传播载体（目击、传信、流言、留痕、资源流变），生成受三门条件保护的'
        '跨实体传播候选（candidates，status=conditional_candidate）与缺前置待核项（waiting）。'
    ),
    'upstream_steps': [
        {'step_id': 'state_transition', 'supplies': '本场 planned_change 根变化与连续性后果'},
        {'step_id': 'static_relations', 'supplies': '实体间联系通道、信息不对称与势力结构'},
        {'step_id': 'world_design', 'supplies': '资源供需、稀缺传导与通信/社会流转规则'},
    ],
    'produces': [
        'candidates（root_kind/root_id/source_entity/target_entity/external_action/proposed_effect/continuity/scene/status=conditional_candidate/gates/activation_condition）',
        'waiting（缺少根变化、行动者或传播路径时的待核记录）',
    ],
    'downstream_steps': [
        {'step_id': 'anchor_design', 'consumes': '显式决定本场是否采用某条传播候选（selected_propagations），未选则保留为后续预案'},
        {'step_id': 'plot_design', 'consumes': '下章/下卷承接延迟抵达的传闻、稀缺冲击或势力连锁反应'},
    ],
    'out_of_scope': [
        '禁止“全员瞬间全知”：必须写明具体可行动的 source_entity 与可观测的 external_action 传播载体，未收到消息者保持不知情。',
        '禁止绕过三门守卫（require_root_confirmation / require_external_action_selection / require_continuity_validation 必须全为 true）。',
        '禁止在本步把条件传播候选直接写入 WORLD 客观事实，或擅自替 12 anchor_design 强制在本场立刻触发所有连锁反应。',
    ],
}


# 12 bounded, non-overlapping material sub-categories across 08–11 directly grounded in src/nw/materials/steps/*.py
EXECUTION_CATEGORIES: tuple[dict[str, Any], ...] = (
    # ---- 08 action_design (4 categories) ----
    {
        'id': 'action_chain_tactics',
        'target_stage': 'action_design',
        'target_stage_label': '08 行动设计',
        'name': '完整行动链、决策风格与多维博弈交互',
        'short_name': '行动链与交互博弈',
        'description': '覆盖完整动作序列（蓄力→动作→观察-判断-调整→结果，2.3/159.2）、事前计划与事后复盘（159.1/159.3）、果断/犹豫等决策风格（板块67/72）、语言博弈目的（试探/隐瞒/施压/示弱，板块56）、环境/资源/信息/社会交互（板块83–86）与对抗回合（板块46–47）。',
        'usage_mode': '08 行动设计核心通用域：把抽象事件拆成带具体对象、阻碍、临场调整与结果的完整行动步骤（steps）。',
        'source_files': [
            'action_design.py (§2.3, §159.2, §3.5–3.6, §7.3)',
            'action_design_decisions.py (§159.1/159.3, 板块67/72)',
            'action_design_dialogue.py (板块56)',
            'action_design_interaction.py (板块83–86)',
            'action_design_plot.py (板块46–47)',
        ],
        'keywords': (
            '行动链', '动作序列', '观察判断', '临场调整', '决策', '试探', '隐瞒', '施压', '示弱',
            '语言博弈', '对话博弈', '环境交互', '资源交互', '信息交互', '社会交互', '对抗回合', '行动候选', '蓄力',
        ),
    },
    {
        'id': 'action_cost_dilemma',
        'target_stage': 'action_design',
        'target_stage_label': '08 行动设计',
        'name': '能力门槛、试错失败、错位应对与代价两难',
        'short_name': '能力门槛与试错代价',
        'description': '覆盖人物最低能力核验（requires）、身心状态限制（8.1/8.2）、岔路回撤与试错失败（42.6/42.8）、代价追溯与成长（4.4/118.5/118.6）、遗漏信息代价（116.9）、认知/预期/身份/立场错位应对（117.1–117.6）、资源投入产出优先级（125.*）、道德两难（板块76）及求生/规则受限博弈（SURVIVAL/RULE）。',
        'usage_mode': '08 行动设计硬核守门域：杜绝无门槛、无试错、无代价的“爽文直通车”，确保每次选择都付出现实或情绪代价。',
        'source_files': [
            'action_design.py (§4.4, §8.1–8.2, §9.2)',
            'action_design_costs.py (§118.5–118.6)',
            'action_design_ethics.py (板块76)',
            'action_design_information.py (§116.9)',
            'action_design_misalignment.py (§117.1–117.6)',
            'action_design_resources.py (§125.*)',
            'action_design_plot.py (§42.6/42.8)',
            'action_design_plot_mechanisms.py (SURVIVAL/RULE)',
        ],
        'keywords': (
            '能力门槛', '试错', '失败', '回撤', '代价', '成本', '道德困境', '两难', '伦理', '遗漏信息',
            '认知错位', '预期错位', '身份错位', '立场错位', '资源投入', '求生机制', '规则机制', '身心限制',
        ),
    },
    {
        'id': 'action_supernatural_craft',
        'target_stage': 'action_design',
        'target_stage_label': '08 行动设计',
        'name': '超凡能量运用与召唤/御兽/炼丹/炼器/阵法动作',
        'short_name': '超凡术法与炼制动作',
        'description': '覆盖超凡能量总量/纯度/技巧/公式/转化路径（action_design.py §10–§18）、超凡工艺制造（30.3/30.4/40.1/40.2）及 5 类超自然人物行动机制（召唤、御兽、炼丹、炼器、阵法）。',
        'usage_mode': '08 行动设计严格按题材边界启用：仅用于玄幻/仙侠/奇幻/游戏/诸天/二次元/轻小说等题材，现实/悬疑/历史/都市/职场等自动隔离。',
        'source_files': [
            'action_design.py (§10–§18 能量规则)',
            'action_design_crafting.py (§30.3–30.4, §40.1–40.2)',
            'action_design_plot_mechanisms.py (SUMMON/BEAST_TAMING/ALCHEMY/ARTIFACT/ARRAY)',
        ],
        'keywords': (
            '能量公式', '能量转化', '灵力', '魔力', '召唤机制', '御兽机制', '炼丹机制', '炼器机制', '阵法机制',
            '斗法', '法宝', '丹药', '阵法', '灵兽', '超凡施法', '功法运转',
        ),
    },
    {
        'id': 'action_tech_containment',
        'target_stage': 'action_design',
        'target_stage_label': '08 行动设计',
        'name': '机甲/AI/机器人操控与异常收容行动机制',
        'short_name': '科技载具与异常收容',
        'description': '覆盖人工智能互动对抗（PLOT_MECHANISM_AI）、机器人操控（PLOT_MECHANISM_ROBOT）、机甲驾驶战斗（PLOT_MECHANISM_MECHA）与异常物品/生物收容边界（PLOT_MECHANISM_CONTAINMENT）。',
        'usage_mode': '08 行动设计严格按题材边界启用：仅用于科幻/赛博/未来/灵异/末世/游戏/诸天等题材，古代/现实/纯言情/武侠自动隔离。',
        'source_files': [
            'action_design_plot_mechanisms.py (CONTAINMENT/AI/ROBOT/MECHA)',
        ],
        'keywords': (
            '机甲', '人工智能', 'AI对抗', '机器人', '义体', '黑客入侵', '异常收容', '收容机制', '收容边界', '载具操控',
        ),
    },
    # ---- 09 scene_design (3 categories) ----
    {
        'id': 'scene_pov_disclosure',
        'target_stage': 'scene_design',
        'target_stage_label': '09 场景设计',
        'name': '受限 POV 视角边界、知情差披露与在场/缺席控制',
        'short_name': 'POV边界与披露控制',
        'description': '覆盖第一/二/三人称有限与全知视角规则（scene_design_viewpoint.py 板块58、scene_design_narrator.py 109.*）、角色未知性与可披露边界（116.1/3/4/6、板块140）、伏笔休眠与延迟解码（板块45）、次要配角/背景≤3人/缺席者处理（1.3–1.5）及多视角配置（板块48/59）。',
        'usage_mode': '09 场景设计视角守门域：锁死单场 pov、characters 与 allowed_disclosure，杜绝中途切视角与场外知情偷跑。',
        'source_files': [
            'scene_design.py (§1.3–1.5, §31.2/33.1/35.3)',
            'scene_design_viewpoint.py (板块58)',
            'scene_design_narrator.py (§109.1/6/8/9)',
            'scene_design_disclosure.py (§116.1/3/4/6, 板块45/140)',
            'scene_design_multi_viewpoint.py',
        ],
        'keywords': (
            'POV', '视角边界', '限知', '知识边界', '可披露', 'allowed_disclosure', '知情差', '信息披露',
            '延迟解码', '缺席者', '在场人物', '视角切换', '配角视角', '半透明展示',
        ),
    },
    {
        'id': 'scene_structure_density',
        'target_stage': 'scene_design',
        'target_stage_label': '09 场景设计',
        'name': '场景结构、空间动线、事件动作绑定与情感密度',
        'short_name': '场景结构与空间节奏',
        'description': '覆盖场景内建立→升级→高潮→余波（板块46）、场景空间布局/距离/动线/密室与空间转换（115.1/2/4/8、S1.*）、“谁在哪、为什么去”三步铺垫（155.2）、重/中/轻/空情感密度（7.1/7.9/155.3）、章场过渡与尾钩（板块47–48/138/154）、配角职责落实（121.*、cast_payoffs）及交付 10 步的 before_state 快照。',
        'usage_mode': '09 场景设计组织核心域：每场显式绑定 1 个上游事件与 1+ 个上游动作，建立前 2–3 句空间结构并落实单场不可逆推进。',
        'source_files': [
            'scene_design.py (§7.1/7.9/155.3, §28.2–30.5)',
            'scene_design_structure.py (板块46–48/138/154, §43.*)',
            'scene_design_space.py (§115.1/2/4/8, §155.2, S1.*)',
            'scene_design_pacing.py',
            'scene_design_opening_timeline.py',
            'scene_design_supporting.py (§121.*, 板块144)',
        ],
        'keywords': (
            '场景结构', '空间布局', '动线', '空间转换', '三步铺垫', '情感密度', '场景节奏', '场景过渡',
            '场景尾钩', '场景目标', '场景卡', '进入状态', 'before_state', '出场职责', 'scene_progress', 'cast_payoffs',
        ),
    },
    {
        'id': 'scene_supernatural_breakthrough',
        'target_stage': 'scene_design',
        'target_stage_label': '09 场景设计',
        'name': '超凡固化态、能量干扰盲区与突破临界点场景规则',
        'short_name': '超凡临界与能量干扰场',
        'description': '覆盖超凡体系中的固化态转化（11.3）、能量干扰形成感知盲区（12.9）、突破临界点场域压力（15.2）与能量源衰竭危局（18.3）。',
        'usage_mode': '09 场景设计严格按题材边界启用：仅用于玄幻/仙侠/奇幻/科幻超能/末世/诸天等具备超凡能量体系的作品，现实题材自动隔离。',
        'source_files': [
            'scene_design.py (§11.3, §12.9, §15.2, §18.3)',
        ],
        'keywords': (
            '固化态', '能量干扰', '感知盲区', '突破临界点', '能量衰竭', '灵气枯竭', '渡劫场域', '结界盲区',
        ),
    },
    # ---- 10 state_transition (3 categories) ----
    {
        'id': 'state_causal_cost',
        'target_stage': 'state_transition',
        'target_stage_label': '10 状态变化',
        'name': '外部行动因果变更、连续性守恒与代价累积',
        'short_name': '因果变更与代价延续',
        'description': '覆盖角色状态更新（2.6）、维度互锁（4.2）、成长代价延续（4.4）、核心属性不能突变（102.1）、道具状态一致（107.3）、代价不消失/叠加/缓释（118.1–118.4）、资源归属/位置/流动追踪（125.5–125.12）及爽点与代价同步（42.5/42.8/44.3）。',
        'usage_mode': '10 状态变化铁律域：原样承接 09 before_state，必须由本场外部行动触发实质差值，写清 failure 与 continuity。',
        'source_files': [
            'state_transition.py (§2.6, §4.2, §4.4)',
            'state_transition_costs.py (§118.1–118.4)',
            'state_transition_continuity.py (§102.1, §107.3)',
            'state_transition_resources.py (§125.5–125.12)',
            'state_transition_plot.py (§42.5/42.8/44.3)',
            'state_transition_ethics.py (板块76)',
        ],
        'keywords': (
            '状态变化', 'before_state', 'after_state', '外部行动', '代价不消失', '代价累积', '代价叠加',
            '核心属性不突变', '道具状态', '资源归属', '连续性', '失败后果', '不可逆变更', '状态迁移',
        ),
    },
    {
        'id': 'state_cognition_relation',
        'target_stage': 'state_transition',
        'target_stage_label': '10 状态变化',
        'name': '心智模型重塑、关系权力反转与活跃状态过载',
        'short_name': '心智关系与状态过载',
        'description': '覆盖心智模型更新/破裂/重塑与信念崩溃（板块69）、权力反转视觉化/信任易崩难建/近距离暴露/立场固化（5.6/5.9/5.10/5.11）、不可逆情感释放与弧光追踪（7.6/7.8）、≤5 活跃身心状态过载与自然恢复/突变稳定（8.2–9.5）及配角欠账与还账（121.7/121.27）。',
        'usage_mode': '10 状态变化人物深度域：追踪人物心理、信任、权力位次与多重负面状态叠加后的真实崩塌或转型。',
        'source_files': [
            'state_transition.py (§5.6/5.9–5.11, §7.6/7.8, §8.2–9.5)',
            'state_transition_cognition.py (板块69)',
            'state_transition_supporting.py (§121.7/121.27)',
        ],
        'keywords': (
            '心智模型', '信念崩溃', '认知更新', '权力反转', '信任崩塌', '立场固化', '情感释放',
            '活跃状态', '状态过载', '状态化解', '自然恢复', '配角欠账', '还账', '心理转变',
        ),
    },
    {
        'id': 'state_energy_construct',
        'target_stage': 'state_transition',
        'target_stage_label': '10 状态变化',
        'name': '超凡能量储备/纯度跃迁与生命构造反哺退化',
        'short_name': '能量储备与构造演化',
        'description': '覆盖超凡能量储备耗尽/恢复、纯度提炼、境界突破后态（state_transition.py §10–§18）及生命构造改善/退化与能力反哺构造（state_transition_world.py §32.6/35.4/37.5–38.1）。',
        'usage_mode': '10 状态变化严格按题材边界启用：仅用于具备修炼/魔力/基因异能/义体进化等体系的题材，现实题材自动隔离。',
        'source_files': [
            'state_transition.py (§10–§18 能量状态)',
            'state_transition_world.py (§32.6, §35.4, §37.5–38.1)',
        ],
        'keywords': (
            '能量储备', '能量纯度', '境界突破', '灵力耗尽', '构造退化', '构造改善', '能力反哺', '修为跌落', '基因异化',
        ),
    },
    # ---- 11 state_propagation (2 categories) ----
    {
        'id': 'propagation_information_social',
        'target_stage': 'state_propagation',
        'target_stage_label': '11 状态传播',
        'name': '非全知信息载体、三门条件候选与人际/势力连锁感知',
        'short_name': '信息载体与连锁感知',
        'description': '覆盖根变化确认（planned_change/accepted_fact）、经由目击/传信/流言/留痕/社会记忆传导至场外实体（state_propagation_social_material/memory/meaning/deliberation）、三门激活守卫（gates）与未目击者不知情边界。',
        'usage_mode': '11 状态传播核心域：杜绝“全员瞬间全知”，所有跨实体连锁感知必须标明传播载体、知情延迟与激活条件。',
        'source_files': [
            'state_propagation_social_material.py',
            'state_propagation_memory.py',
            'state_propagation_meaning.py',
            'state_propagation_deliberation.py',
            'state_propagation_type_rules.py',
        ],
        'keywords': (
            '状态传播', '传播候选', '信息传播', '流言', '传信', '目击', '留痕', '知情延迟', '非全知',
            '连锁感知', '三门', 'activation_condition', 'conditional_candidate', '社会记忆', '势力反应',
        ),
    },
    {
        'id': 'propagation_resource_ecology',
        'target_stage': 'state_propagation',
        'target_stage_label': '11 状态传播',
        'name': '资源盈余→赤字转向、稀缺恐慌与组织生态波及',
        'short_name': '资源赤字与生态波及',
        'description': '覆盖资源从盈余转为赤字的系统性拐点（20.4）、稀缺引发恐慌与权力膨胀（27.3）、工艺/供应链中断及组织/地域生态连锁波及（state_propagation_crafting.py）。',
        'usage_mode': '11 状态传播宏观波及域：将单场局部损耗或事件后果按真实传导链扩散为市场动荡、势力扩张或群像恐慌。',
        'source_files': [
            'state_propagation.py (§20.4, §27.3)',
            'state_propagation_crafting.py',
        ],
        'keywords': (
            '资源盈余', '赤字', '稀缺恐慌', '权力膨胀', '供应链', '生态波及', '市场动荡', '物资紧缺', '势力扩张', '群体恐慌',
        ),
    },
)

EXECUTION_CATEGORY_MAP: dict[str, dict[str, Any]] = {c['id']: c for c in EXECUTION_CATEGORIES}
EXECUTION_CATEGORY_ORDER: dict[str, int] = {c['id']: i for i, c in enumerate(EXECUTION_CATEGORIES)}

RELEVANCE_RANK = {'primary': 0, 'optional': 1, 'out_of_scope': 2}
RELEVANCE_LABELS = {
    'primary': '本类型核心',
    'optional': '按需扩展',
    'out_of_scope': '非本类型常规项',
}

_CORE_GENERAL = (
    'action_chain_tactics',
    'action_cost_dilemma',
    'scene_pov_disclosure',
    'scene_structure_density',
    'state_causal_cost',
    'state_cognition_relation',
    'propagation_information_social',
)
_SUPERNATURAL_CATS = (
    'action_supernatural_craft',
    'scene_supernatural_breakthrough',
    'state_energy_construct',
)


def _eprofile(
    primary: tuple[str, ...],
    optional: tuple[str, ...],
    *,
    action_style: str,
    scene_pov_focus: str,
    state_cost_focus: str,
    propagation_focus: str,
    decomposition_focus: str,
) -> dict[str, Any]:
    return {
        'primary': primary,
        'optional': optional,
        'execution_profile': {
            'action_style': action_style,
            'scene_pov_focus': scene_pov_focus,
            'state_cost_focus': state_cost_focus,
            'propagation_focus': propagation_focus,
        },
        'decomposition_focus': decomposition_focus,
    }


DEFAULT_EXECUTION_PROFILE = _eprofile(
    primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
    optional=(*_SUPERNATURAL_CATS, 'action_tech_containment'),
    action_style='围绕真实能力门槛、障碍试错、语言与环境交互博弈展开，每条行动明示成本与失败回撤。',
    scene_pov_focus='单场显式绑定上游事件与动作，守住受限 POV 披露边界，开头建立空间方位并控制重中轻空情感密度。',
    state_cost_focus='严格承接 before_state，仅由外部行动引发 after_state 差值，保持代价持续与心智/关系连续性。',
    propagation_focus='通过目击、传信、流言或资源流变逐步传导，严禁场外人物瞬间全知。',
    decomposition_focus='重点拆解“尝试→受阻→调整→代价”的完整行动链、受限视角信息差控场、可核查前后状态差值及跨章信息传播路径。',
)


# Covers ALL 35 main genres from nw.studio.catalog.genres().
GENRE_EXECUTION_PROFILES: dict[str, dict[str, Any]] = {
    'GENRE_XUANHUAN': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS, 'propagation_resource_ecology'),
        optional=(),
        action_style='斗法对抗回合 + 灵力/法宝/阵法/炼丹等超凡工艺组合博弈，严格校验境界能力门槛与底牌耗损。',
        scene_pov_focus='兼顾战斗空间动线与能量干扰/突破临界点场域压迫，按重中轻空密度调控爆发与筹备场。',
        state_cost_focus='同步追踪灵力储备、伤势/反噬代价累积、境界突破后态与宗门资源得失，防战力凭空回满。',
        propagation_focus='战绩、秘宝现世与灵脉枯竭经目击者、宗门飞讯与黑市流言逐级扩散，引发强敌与势力连锁反应。',
        decomposition_focus='重点拆解越级/同阶斗法的战术试错步骤、突破临界场域铺垫、反噬代价延续及名声/宝物外泄的传播延迟。',
    ),
    'GENRE_QIHUAN': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS, 'propagation_resource_ecology'),
        optional=(),
        action_style='魔法/仪式/召唤/团队协作对抗，强调施法材料门槛、规则反噬与跨种族协作摩擦。',
        scene_pov_focus='多视角轮换时严守各 POV 独立知情与地理空间距离，重场写遗迹/战场空间边界。',
        state_cost_focus='记录魔力/生命构造耗损、誓约代价、同伴信任裂痕与装备损耗，不轻易清零远征成本。',
        propagation_focus='古史异动、战报与魔法灾变按真实信使/哨站/商路延迟传向王庭与各阵营。',
        decomposition_focus='重点拆解小队多角色配合行动链、多 POV 知情隔断、远征资源消耗演化与跨地域情报传递。',
    ),
    'GENRE_XIANXIA': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS, 'propagation_resource_ecology'),
        optional=(),
        action_style='谋定后动、炼丹/炼器/阵法筹备与精准斗法试探，重信息差博弈、底牌保留与因果代价核算。',
        scene_pov_focus='严守神识探查范围与阵法/能量盲区边界，精准区分人物口头客套与真实杀意披露。',
        state_cost_focus='重点追踪修为纯度、心魔/道心震荡、寿元/灵石消耗与人情因果欠账，杜绝无代价突破。',
        propagation_focus='散修传闻、宗门玉简与坊市灵材紧缺逐步改变各方对主角的估价与布局。',
        decomposition_focus='重点拆解以弱胜强的事前布局与临场应变、神识盲区控场、寿元/灵材代价追踪及宗门情报慢传导。',
    ),
    'GENRE_WUXIA': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=('action_supernatural_craft', 'state_energy_construct'),
        action_style='见招拆招的武学回合、环境地形借力与江湖暗语试探，突出内力/体力极限与道义两难。',
        scene_pov_focus='客栈/山道/厅堂空间站位与兵器距离须在前 2–3 句确立，严守耳目视线边界。',
        state_cost_focus='内伤、毒素、兵器损毁、江湖名声受损与恩怨欠账须持续影响后续出招与人际信任。',
        propagation_focus='江湖流言、茶楼说书与门派飞鸽制造真实的信息失真、误判与复仇连锁。',
        decomposition_focus='重点拆解有限内力/招式破绽下的实战拆招、客栈/密室空间张力、内伤与道义代价延续及江湖谣言失真传播。',
    ),
    'GENRE_DUSHI': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=('action_tech_containment',),
        action_style='商业谈判、话术施压、人脉调度与法律/资金边界博弈；严禁玄幻术法或炼丹阵法混入。',
        scene_pov_focus='写字楼/酒局/审讯/家庭场内紧盯身份权限、谁在场听见与潜台词信息披露。',
        state_cost_focus='现金流、信用、人情债、职级权限与舆论风险须随每次现实行动真实增减，不可突变。',
        propagation_focus='行业圈子口风、社媒热搜、资本尽调与熟人转述引发多米诺式现实连锁反应。',
        decomposition_focus='重点拆解酒局/谈判中的对话试探与筹码交换、现实资源约束与代价延续、以及圈内消息/舆情扩散路径。',
    ),
    'GENRE_LISHI': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='朝堂奏对、兵法调度、财政筹粮与礼法规则博弈；严格受时代技术、交通与官制权限约束。',
        scene_pov_focus='大殿/军帐/驿站空间等级分明，严守古代视角认知与信息不可跨时空透支边界。',
        state_cost_focus='军粮、民心、皇权猜忌、派系信任与士卒伤亡须严格守恒并持续反噬后续政令。',
        propagation_focus='八百里加急、邸报、密折与地方流言决定真实时间延迟与战局/朝局错位误判。',
        decomposition_focus='重点拆解古代权责边界下的博弈招式、信息延迟造成的战略误判、粮草/民心赤字转向与政令传导链。',
    ),
    'GENRE_JUNSHI': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=('action_tech_containment',),
        action_style='硬核战术协同、火力/弹药/地形约束、临场 OODA 观察-判断-调整循环与严酷战场代价。',
        scene_pov_focus='战壕/巷战/指挥所精确标定射界、掩体、盲区与通信中断时的受限 POV 信息差。',
        state_cost_focus='弹药油料消耗、减员伤亡、装备战损、士气波动与战区控制权严格按行动因果结算。',
        propagation_focus='无线电静默、侦察回传、战报延迟与补给线中断触发上级/友军/敌方连锁调度。',
        decomposition_focus='重点拆解突发敌情下的战术变招、通信盲区引发的战场迷雾、补给赤字传导与战损连续性。',
    ),
    'GENRE_KEHUAN': _eprofile(
        primary=(*_CORE_GENERAL, 'action_tech_containment', 'propagation_resource_ecology'),
        optional=('scene_supernatural_breakthrough', 'state_energy_construct'),
        action_style='科学实验验证、AI/机器人/机甲操控、工程应急抢修与硬物理/逻辑规则下的极限求生博弈。',
        scene_pov_focus='飞船舱室/空间站/行星基地强调封闭结构、传感器盲区与光速通信延迟造成的视角边界。',
        state_cost_focus='能源/氧气/算力损耗、设备不可逆故障、物理时间膨胀与文明伦理代价严格守恒。',
        propagation_focus='信号延迟、探测数据回传、技术外泄与资源枯竭在星系/组织尺度触发滞后连锁危机。',
        decomposition_focus='重点拆解硬核规则限制下的技术破局步骤、密闭空间与传感器盲区设计、资源耗尽曲线及信号延迟传播。',
    ),
    'GENRE_XUANYI': _eprofile(
        primary=_CORE_GENERAL,
        optional=('propagation_resource_ecology',),
        action_style='勘查取证、讯问心理施压、反侦查试探与信息缺口下的高危决策；严禁任何超自然与机甲外挂。',
        scene_pov_focus='极致收紧 POV 感知与 allowed_disclosure，利用空间隔断、时间差与证词矛盾制造悬疑。',
        state_cost_focus='证物损毁/污染、暴露行踪、心理防线动摇与信任破裂均须不可逆留痕并持续施压。',
        propagation_focus='线索泄露、证人串供、警方通告或匿名举报经由明确人物/媒介传递，制造紧迫时间差。',
        decomposition_focus='重点拆解问询话术博弈与证物试错、受限视角如何隐藏真相又保持公平线索、以及消息外泄后的多方应变。',
    ),
    'GENRE_TUILI': _eprofile(
        primary=_CORE_GENERAL,
        optional=(),
        action_style='现场勘验、时间线核对、实验排伪与逻辑质询对抗；所有推理行动须立足在场物理证据，严禁超自然。',
        scene_pov_focus='密室/走廊/楼层空间结构（S1.*）与视听阻断精确到人，读者与侦探同步掌握公平线索。',
        state_cost_focus='聚焦心智模型推翻（假说破产）、不在场证明瓦解、嫌疑人心理暴露与新案发改变局势。',
        propagation_focus='证言转述、二次误读与警方/嫌疑人得知部分线索后的反制行动须有明确传话人。',
        decomposition_focus='重点拆解假说提出→取证证伪→重组推理的完整循环、密室空间动线描写及证词信息差传播。',
    ),
    'GENRE_LINGYI': _eprofile(
        primary=(*_CORE_GENERAL, 'action_tech_containment', 'scene_supernatural_breakthrough'),
        optional=('action_supernatural_craft', 'state_energy_construct', 'propagation_resource_ecology'),
        action_style='规则怪谈试错、禁忌规避、异常收容与保命逃生；每次试探规则都伴随污染或生存代价。',
        scene_pov_focus='昏暗封闭空间、异常缺席与感知干扰盲区拉满受限 POV 压迫感，严格隔离幸存者各自所知。',
        state_cost_focus='追踪理智/污染值、违规标记、生存道具耗损与≤5活跃负面状态过载，杜绝轻松脱身。',
        propagation_focus='怪谈规则蔓延、异常传染、遗言纸条与幸存者口口相传（含致命误传）引发次生危机。',
        decomposition_focus='重点拆解拿命试探规则边界的动作链、异常盲区场景氛围、污染代价累积与错误传言的致命传播。',
    ),
    'GENRE_KONGBU': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=('action_tech_containment', 'scene_supernatural_breakthrough'),
        action_style='极限逃生、环境封堵、残酷道德抉择与猜忌对抗；强调能力匮乏与安全空间步步萎缩。',
        scene_pov_focus='死角/密室/单线走廊与视听隔断锁死受限 POV，用缺席者与痕迹信息放大未知恐惧。',
        state_cost_focus='体能透支、伤残流血、精神崩溃、物资递减与队伍信任瓦解持续叠加不可逆转。',
        propagation_focus='恐慌情绪传染、失联惨叫、血迹留痕与资源见底迅速诱发群体内讧。',
        decomposition_focus='重点拆解退路被逐一封死的试错行动、密闭空间视听阻断、多重身心负面状态过载与恐慌传播链。',
    ),
    'GENRE_YOUXI': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS, 'action_tech_containment', 'propagation_resource_ecology'),
        optional=(),
        action_style='副本机制拆解、技能冷却/蓝量/装备门槛博弈、召唤/阵法/机甲等数值与机制配合。',
        scene_pov_focus='战场仇恨范围、地形卡位、队友分工与系统提示披露边界清晰，兼顾现实与游戏视角。',
        state_cost_focus='技能 CD、耐久损耗、掉落归属、公会声望与副本首通资格随行动实时准确变更。',
        propagation_focus='全服公告、攻略论坛、拍卖行物价波动与公会间谍情报迅速改变版本竞争格局。',
        decomposition_focus='重点拆解开荒试错到机制破局的动作回合、资源/装备损耗追踪及全服消息引发的市场与势力连锁。',
    ),
    'GENRE_DIANJING': _eprofile(
        primary=_CORE_GENERAL,
        optional=('propagation_resource_ecology',),
        action_style='BP 战术博弈、团战微操对抗、临场指挥调整与心态抗压；严禁超自然与科幻机甲机制。',
        scene_pov_focus='精确区分选手战争迷雾（受限视野）与解说/观众视角，避免场内选手凭空得知敌方动向。',
        state_cost_focus='经济差、技能/视野资源、选手手伤/体能疲劳、队内信任与赛点心理压力实时演化。',
        propagation_focus='赛后采访、社区舆论风暴、转会流言与对手研究录像形成跨赛程连锁影响。',
        decomposition_focus='重点拆解关键局战术试探与反制回合、战争迷雾下的视野信息差、心态崩盘/重塑及舆论连锁效应。',
    ),
    'GENRE_TIYU': _eprofile(
        primary=_CORE_GENERAL,
        optional=('propagation_resource_ecology',),
        action_style='真实体能分配、技术动作对抗、临场战术变阵与伤病边缘抉择；严守人体物理极限，禁超自然。',
        scene_pov_focus='赛场空间距离、呼吸节奏、教练席与场上队员受限沟通构成高张力现场视角。',
        state_cost_focus='体能槽衰减、乳酸堆积、旧伤复发风险、犯规次数与比分心理压迫须持续影响后半程。',
        propagation_focus='战术被对手摸透、裁判尺度信号、媒体质疑与团队士气传导改变后续对阵策略。',
        decomposition_focus='重点拆解体能极限下的动作变招与试错、临场比分压力的心理迁移及对手针对性情报传导。',
    ),
    'GENRE_YANQING': _eprofile(
        primary=_CORE_GENERAL,
        optional=('propagation_resource_ecology',),
        action_style='试探推拉、潜台词对话博弈、护短/妥协/拒绝等情感抉择；严禁超自然术法或机甲机制。',
        scene_pov_focus='精准拿捏单方 POV 的心理猜度与未说出口的真相，通过近距离细节与空间界限放大暧昧与张力。',
        state_cost_focus='重点追踪信任度易崩难建、情感债务、心防裂痕、立场让步与不可逆表白/决裂后果。',
        propagation_focus='流言蜚语、亲友撮合或阻挠、第三方无意泄露秘密推动情感误解或真相水落石出。',
        decomposition_focus='重点拆解对话试探中的信息隐瞒与情感流露、POV 心理误读、信任与情感债变化及第三方消息传递。',
    ),
    'GENRE_XIANDAI_YANQING': _eprofile(
        primary=_CORE_GENERAL,
        optional=('propagation_resource_ecology',),
        action_style='都市日常互动、职场/家庭两难抉择与细腻言语攻防；严禁超自然与科幻战斗机制。',
        scene_pov_focus='公寓/咖啡馆/职场等现代私密与半公开空间切换，严守各自聊天记录与知情边界。',
        state_cost_focus='追踪亲密边界试探、旧伤触动、现实事业让步代价与双方信任修复进度。',
        propagation_focus='朋友圈动态、同事八卦、家庭聚会传话与媒体曝光自然引发关系涟漪。',
        decomposition_focus='重点拆解日常对话里的潜台词博弈、误会形成的真实信息差、情感代价累积与现代社交传播链。',
    ),
    'GENRE_GUDAI_YANQING': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='深宅礼制借力、言语机锋试探、账簿/信物查证与家族利益博弈；严禁超自然术法与科技机制。',
        scene_pov_focus='内宅院落、屏风隔断、主仆听闻权限构成天然空间与知情边界，重在半透明礼法展示。',
        state_cost_focus='闺誉、管家权、家族荫庇、恩情欠账与夫妻/主仆信任须随每次交锋真实变更。',
        propagation_focus='丫鬟婆子传话、帖子往来、京城茶楼风声与宫中赏赐流向引发深宅与朝堂联动。',
        decomposition_focus='重点拆解宅斗礼法借力打力、屏风/仆役造成的偷听与信息差、管家权/名声代价及内宅风声传播。',
    ),
    'GENRE_XIANSHI': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='生计奔波、人情周旋、现实制度磨合与两难取舍；严守现实物理与社会约束，禁止超自然。',
        scene_pov_focus='车间/菜场/家庭饭桌等真实生活空间自然入场，兼顾轻空章留白与克制披露。',
        state_cost_focus='家庭存款、健康劳损、人情亏欠、代际信任与信念妥协须如实沉淀，不轻易奇迹翻盘。',
        propagation_focus='邻里闲话、单位风声、政策通知与市场物价波动缓慢而深刻地改写普通人处境。',
        decomposition_focus='重点拆解小人物在现实约束下的艰难试错、生活成本累积、代际认知碰撞与基层社会消息传导。',
    ),
    'GENRE_QINGCHUN': _eprofile(
        primary=_CORE_GENERAL,
        optional=(),
        action_style='校园学业/竞赛努力、青涩试探表白、友情摩擦与自我突破；禁超自然及成人硬核权谋。',
        scene_pov_focus='教室/操场/天台/走廊空间动线鲜活，紧扣少年敏感自尊下的受限 POV 误读与成长。',
        state_cost_focus='成绩起伏、友情裂痕、错失机会的遗憾与自我认同重塑须真切留痕。',
        propagation_focus='班级小纸条、校园贴吧/广播、同学起哄与家长会通知自然串联校园群像反应。',
        decomposition_focus='重点拆解青春期沟通错位与试错、校园空间情绪氛围、自我认知蜕变及同学间消息扩散。',
    ),
    'GENRE_ERCIYUAN': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS),
        optional=('action_tech_containment', 'propagation_resource_ecology'),
        action_style='高概念异能/召唤/机甲战术智斗、伙伴羁绊协同与信念碰撞，保留爽利回合与真实限制代价。',
        scene_pov_focus='鲜明角色站位与情感密度切换（日常轻喜剧→高燃信念重场），守住能力情报信息差。',
        state_cost_focus='异能透支代价、羁绊信任升华或决裂、角色信念重塑与阵营立场变动清晰可核。',
        propagation_focus='学院/组织通告、宿敌目击与伙伴传讯引发阵营连锁集结与态度逆转。',
        decomposition_focus='重点拆解能力规则智斗回合、日常轻场与高燃重场的密度切换、羁绊状态迁移与阵营情报传播。',
    ),
    'GENRE_QINGXIAOSHUO': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS),
        optional=('action_tech_containment', 'propagation_resource_ecology'),
        action_style='高概念规则巧用、机智吐槽对话博弈与反套路试错破局，重视设定边界下的以小博大。',
        scene_pov_focus='强主体性第一/三限知 POV，以精准信息差和反差认知驱动趣味与反转。',
        state_cost_focus='聚焦角色心防松动、秘密暴露风险、特殊规则代价及日常关系微妙位移。',
        propagation_focus='校园/小圈子误解传闻、秘密外泄与异常事件余波推动下一卷风波。',
        decomposition_focus='重点拆解高概念规则下的巧妙行动设计、强个人 POV 信息差控场、微妙关系迁移与误解传播链。',
    ),
    'GENRE_TONGREN': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS),
        optional=('action_tech_containment', 'propagation_resource_ecology'),
        action_style='遵循原典力量/规则体系边界下的蝴蝶效应干预行动，避免无理由破坏原典角色能力逻辑。',
        scene_pov_focus='精准区隔主角“先知记忆”与原典角色当下受限知情，杜绝原典人物无理由降智。',
        state_cost_focus='追踪偏离原典剧情后的蝴蝶效应代价、原典角色好感/警惕度变化与新失衡风险。',
        propagation_focus='主角一次微小干预经原典人物间的既有关系网逐层放大为全局剧情偏移。',
        decomposition_focus='重点拆解利用先知信息差设计的干预动作、原典角色受限认知反应及蝴蝶效应的逐级传播链。',
    ),
    'GENRE_ZHUTIAN': _eprofile(
        primary=(*_CORE_GENERAL, *_SUPERNATURAL_CATS, 'action_tech_containment', 'propagation_resource_ecology'),
        optional=(),
        action_style='跨世界能力/道具/规则混搭破局，严核不同副本世界规则兼容限制与任务失败惩罚代价。',
        scene_pov_focus='兼顾副本土著视角局限与轮回者/穿越者信息差，每换新世界快速重立空间与规则边界。',
        state_cost_focus='跨界收获、任务评分/惩罚、身体/能量异化代价与世界线变动在回归结算时清晰落账。',
        propagation_focus='副本内影响经土著势力扩散，跨界影响经主神空间/同行竞争者情报网传播。',
        decomposition_focus='重点拆解跨体系规则限制下的破局步骤、多方信息差控场、跨世界收益与惩罚结算及同行情报传导。',
    ),
    'GENRE_MOSHI': _eprofile(
        primary=(*_CORE_GENERAL, 'action_tech_containment', 'propagation_resource_ecology'),
        optional=('action_supernatural_craft', 'scene_supernatural_breakthrough', 'state_energy_construct'),
        action_style='物资搜寻、避难所防卫、异变对抗与残酷资源取舍；每次外出行动须核算弹药/油料/伤亡成本。',
        scene_pov_focus='废墟/公路/安全屋强调视野死角、入口防御与撤退动线，精准控制危机压迫密度。',
        state_cost_focus='食物净水医药库存、人员伤亡、感染/异化风险与幸存者道德底线退化持续累积。',
        propagation_focus='资源盈余转赤字引发避难所恐慌、权力膨胀、电台求救暴露坐标与掠夺者连锁围攻。',
        decomposition_focus='重点拆解资源约束下的高危搜刮与防卫步骤、废墟空间动线、物资赤字引发的秩序崩塌与电台情报传播。',
    ),
    'GENRE_SAIBO': _eprofile(
        primary=(*_CORE_GENERAL, 'action_tech_containment', 'propagation_resource_ecology'),
        optional=('state_energy_construct',),
        action_style='黑客网域入侵、义体战术火并、情报掮客交易与巨企规则夹缝求生；禁古代修仙术法。',
        scene_pov_focus='赛博暗巷/企业塔/神经接入界面双层空间切换，严守监控覆盖盲区与加密信息披露。',
        state_cost_focus='义体赛博精神病风险、信用点负债、身份暴露通缉度、背叛创伤与身体不可逆改造持续累加。',
        propagation_focus='黑市赏金单、巨企清道夫追踪、暗网数据泄露与帮派火并消息迅速封锁主角退路。',
        decomposition_focus='重点拆解潜行+黑客+义体多维协同行动、物理与网络双空间视角、改造代价累积与暗网悬赏传播。',
    ),
    'GENRE_WEILAI': _eprofile(
        primary=(*_CORE_GENERAL, 'action_tech_containment', 'propagation_resource_ecology'),
        optional=('scene_supernatural_breakthrough', 'state_energy_construct'),
        action_style='算法治理博弈、未来科技工具运用、制度合规与越界试错，强调技术系统的边界代价。',
        scene_pov_focus='生态穹顶/数据中枢/分级城区突出阶层空间隔断与监控信息不对称。',
        state_cost_focus='社会信用/权限降级、能源配额削减、技术依赖反噬与制度信念裂变持续生效。',
        propagation_focus='算法风控扩散、公共舆情操控、供应链失衡与群体觉察引发宏观制度波动。',
        decomposition_focus='重点拆解未来制度与技术规则下的破局试错、监控空间与信息不对称、权限/配额迁移及系统性波及。',
    ),
    'GENRE_TONGHUA': _eprofile(
        primary=_CORE_GENERAL,
        optional=('action_supernatural_craft', 'scene_supernatural_breakthrough'),
        action_style='诺言践行、三次递进试炼与纯真智慧破局；动作简洁富象征性，严禁血腥硬核科技机制。',
        scene_pov_focus='森林/城堡/奇境空间意象鲜明，视角纯净克制，情感密度疏密有致。',
        state_cost_focus='诺言违背代价、奇物消耗、勇气/善意成长与象征物状态改变清晰可辨。',
        propagation_focus='约定回响、自然生灵传信与王国传闻形成温暖或警世的寓言连锁。',
        decomposition_focus='重点拆解寓言式三次试错行动链、象征空间场景构造、诺言代价转化与故事内消息回响。',
    ),
    'GENRE_ERTONG': _eprofile(
        primary=_CORE_GENERAL,
        optional=(),
        action_style='伙伴合作探索、动手解谜与善意试错；行动清晰安全有正向反馈，杜绝暗黑与超凡血斗。',
        scene_pov_focus='贴近儿童视角的空间探索与好奇观察，信息披露循序渐进、清晰易懂。',
        state_cost_focus='小挫折后的情绪调整、友情互信加深、好习惯/新本领养成真实可见。',
        propagation_focus='小伙伴口耳相传、老师家长了解经过并给予回应，形成温暖成长反馈。',
        decomposition_focus='重点拆解清晰可读的探索解谜步骤、儿童受限视角趣味、正向成长状态迁移与同伴反馈链。',
    ),
    'GENRE_JISHI': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='严格忠实真实行动、调查走访、机构决策与客观物理/制度限制；严禁任何虚构超自然或科幻机制。',
        scene_pov_focus='交叉受访者与档案视角须标明信息出处，严禁替真实人物编造无据内心或超前知情。',
        state_cost_focus='事实损害、制度后果、个人命运转折与社会成本全部依据可核查事件顺序落账。',
        propagation_focus='新闻报道、公文流转、亲历者口述与社会舆论真实还原事件波及链。',
        decomposition_focus='重点拆解真实决策在制度约束下的得失、多方视角交叉举证、客观代价演化及媒体/公文传播路径。',
    ),
    'GENRE_ZHIYE': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='专业技术/业务流程排障、合规红线博弈、向上管理与跨部门谈判；严禁超自然与科幻外挂。',
        scene_pov_focus='手术室/法庭/工地/会议室专业空间动线清晰，准确区分专业内行与外行信息差。',
        state_cost_focus='KPI/预算消耗、职业声誉、合规风险、团队信任与专业能力实证提升严格按案结算。',
        propagation_focus='内部邮件、绩效评议、客户口碑、行业通报与监管问询触发职场连锁反应。',
        decomposition_focus='重点拆解专业难题从排查失败到硬核破局的行动步骤、专业场景空间控制、预算/声誉代价及职场消息传导。',
    ),
    'GENRE_NVXING': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='清醒边界捍卫、事业/经济主动破局、女性互助协作与情感/现实两难抉择；禁超自然机制。',
        scene_pov_focus='深入刻画主体视角在职场与家庭双重场域下的感知边界与隐性不公披露。',
        state_cost_focus='经济独立度、话语权位次反转、情绪耗损恢复、自我认知重塑与人际边界重构持续可核。',
        propagation_focus='家庭群话术、职场人脉互助、社会评价流向与舆论声援触发真实境遇转变。',
        decomposition_focus='重点拆解主角如何以具体行动打破被动处境、权力反转状态落账、女性互助支线传播与认知觉醒。',
    ),
    'GENRE_JIATING': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='家庭协商、隐忍爆发、金钱/照护分工博弈与亲情两难取舍；严禁超自然与科幻机制。',
        scene_pov_focus='客厅/餐桌/病房封闭家庭空间张力十足，精准刻画各代际成员视角盲区与情绪温度。',
        state_cost_focus='家庭储蓄、健康负担、积年心结爆发、偏心旧账清算与亲情信任重塑持续延续。',
        propagation_focus='亲戚串门传话、家族微信群发酵与旧秘密意外捅破引发全家连锁摊牌。',
        decomposition_focus='重点拆解饭桌/家庭会议中的潜台词交锋、多成员视角信息差、家庭经济与情感债迁移及亲属传话链。',
    ),
    'GENRE_GONGTING': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='连环计设局、借刀杀人、言语试探圣意与规矩礼法反制；严禁超自然术法与科幻机制。',
        scene_pov_focus='宫禁殿宇/御前奏对/密室商议严控耳目隔断、站位尊卑与“谁能听见哪一句”的披露生死线。',
        state_cost_focus='圣眷盛衰、党羽损耗、把柄留存、信任崩塌与立场不可逆固化须步步留账。',
        propagation_focus='宫中眼线、密奏折子、外朝流言与人事任免风声按严密层级和延迟触发朝堂大地震。',
        decomposition_focus='重点拆解多步借势与试探回合、严密空间与耳目披露控制、权力位次不可逆反转及宫禁情报传导网。',
    ),
    'GENRE_SHEHUI': _eprofile(
        primary=(*_CORE_GENERAL, 'propagation_resource_ecology'),
        optional=(),
        action_style='艰难调查取证、程序正义与良知两难、弱势者周旋对抗庞大利益链；严禁任何超自然机制。',
        scene_pov_focus='交叉执法者、受害者与利益相关方多 POV 拼图，严格维持各自受限知情与社会阶层空间反差。',
        state_cost_focus='证人安全代价、职业前途风险、涉案人物信念崩塌、社会关系破裂与真相逐步逼近持续沉淀。',
        propagation_focus='媒体曝光、利益集团封口、证人连环反应与公共舆论转向驱动层层升级的社会连锁效应。',
        decomposition_focus='重点拆解程序限制下的调查试错、多阶层空间对比与知情拼图、良知代价延续及真相外泄后的多方反制。',
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
    if cat_id == 'action_supernatural_craft':
        return f'当前类型（{joined}）以现实或非超凡行动博弈为主，召唤、御兽、炼丹、炼器、阵法与超凡能量公式属于跨题材机制，避免违背题材边界。'
    if cat_id == 'action_tech_containment':
        return f'当前类型（{joined}）不以科幻载具或异常收容为核心，机甲、AI/机器人对抗与异常收容机制默认隔离。'
    if cat_id == 'scene_supernatural_breakthrough':
        return f'当前类型（{joined}）无超凡能量体系，固化态转化、能量干扰盲区与突破临界点场景规则默认隔离。'
    if cat_id == 'state_energy_construct':
        return f'当前类型（{joined}）不适用超凡能量储备/纯度跃迁与生命构造演化规则，避免破坏现实连续性。'
    return f'此分类在 {joined} 中属于跨类型扩展项，仅在作品明确需要时按需启用。'


def execution_profile_for_types(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Build genre-targeted 08–11 execution profile with strict category relevance and boundaries."""
    normalized, mains = _resolve_main_genres(types)
    mapping = type_map()
    type_objs = [{'id': tid, 'name': mapping[tid]['name'], 'parent_id': mapping[tid].get('parent_id')}
                 for tid in normalized if tid in mapping]
    main_names = [mapping[mid]['name'] for mid in mains if mid in mapping]

    profiles = [GENRE_EXECUTION_PROFILES.get(mid, DEFAULT_EXECUTION_PROFILE) for mid in mains] if mains else [DEFAULT_EXECUTION_PROFILE]

    relevance_by_cat: dict[str, str] = {}
    for cat in EXECUTION_CATEGORIES:
        cid = cat['id']
        best = 'out_of_scope'
        for prof in profiles:
            if cid in prof['primary']:
                best = 'primary'
                break
            if cid in prof['optional'] and best != 'primary':
                best = 'optional'
        relevance_by_cat[cid] = best

    action_styles: list[str] = []
    scene_focuses: list[str] = []
    state_focuses: list[str] = []
    prop_focuses: list[str] = []
    decomp_focuses: list[str] = []
    for prof in profiles:
        ep = prof['execution_profile']
        if ep['action_style'] not in action_styles:
            action_styles.append(ep['action_style'])
        if ep['scene_pov_focus'] not in scene_focuses:
            scene_focuses.append(ep['scene_pov_focus'])
        if ep['state_cost_focus'] not in state_focuses:
            state_focuses.append(ep['state_cost_focus'])
        if ep['propagation_focus'] not in prop_focuses:
            prop_focuses.append(ep['propagation_focus'])
        if prof['decomposition_focus'] not in decomp_focuses:
            decomp_focuses.append(prof['decomposition_focus'])

    categories: list[dict[str, Any]] = []
    for cat in EXECUTION_CATEGORIES:
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
            'relevance': rel,
            'relevance_label': RELEVANCE_LABELS[rel],
            'boundary_note': _out_of_scope_note(cid, main_names) if rel == 'out_of_scope' else cat['usage_mode'],
        })

    categories.sort(key=lambda r: (RELEVANCE_RANK[r['relevance']], EXECUTION_CATEGORY_ORDER[r['id']]))
    return {
        'types': type_objs,
        'main_types': [{'id': mid, 'name': mapping[mid]['name']} for mid in mains if mid in mapping],
        'has_genre_binding': bool(mains),
        'primary_categories': [c['id'] for c in categories if c['relevance'] == 'primary'],
        'optional_categories': [c['id'] for c in categories if c['relevance'] == 'optional'],
        'out_of_scope_categories': [c['id'] for c in categories if c['relevance'] == 'out_of_scope'],
        'categories': categories,
        'action_categories': [c for c in categories if c['target_stage'] == 'action_design'],
        'scene_categories': [c for c in categories if c['target_stage'] == 'scene_design'],
        'transition_categories': [c for c in categories if c['target_stage'] == 'state_transition'],
        'propagation_categories': [c for c in categories if c['target_stage'] == 'state_propagation'],
        'execution_profile': {
            'action_style': '；'.join(action_styles),
            'scene_pov_focus': '；'.join(scene_focuses),
            'state_cost_focus': '；'.join(state_focuses),
            'propagation_focus': '；'.join(prop_focuses),
        },
        'decomposition_focus': '；'.join(decomp_focuses),
        'step_boundaries': {
            'action_design': deepcopy(ACTION_STEP_BOUNDARY),
            'scene_design': deepcopy(SCENE_STEP_BOUNDARY),
            'state_transition': deepcopy(STATE_TRANSITION_STEP_BOUNDARY),
            'state_propagation': deepcopy(STATE_PROPAGATION_STEP_BOUNDARY),
        },
    }


def classify_execution_method(body: dict[str, Any]) -> list[str]:
    """Deterministically classify a method targeting 08–11 into matching execution categories."""
    if not isinstance(body, dict):
        return []
    tasks = set(body.get('tasks') or ())
    outputs = body.get('outputs') or ()
    output_stages = {o.get('stage') for o in outputs if isinstance(o, dict)}
    allowed_stages: set[str] = set()
    if 'action_chain' in tasks or 'action_design' in output_stages:
        allowed_stages.add('action_design')
    if 'scene_composition' in tasks or 'scene_design' in output_stages:
        allowed_stages.add('scene_design')
    if 'state_change' in tasks or 'state_transition' in output_stages:
        allowed_stages.add('state_transition')
    if 'state_propagation' in tasks or 'state_propagation' in output_stages:
        allowed_stages.add('state_propagation')
    if not allowed_stages:
        return []

    text = ' '.join([
        str(body.get('title') or ''),
        ' '.join(str(x) for x in (body.get('applicability') or ())),
        ' '.join(str(o.get('instruction') or '') for o in (body.get('operations') or ()) if isinstance(o, dict)),
        ' '.join(str(o.get('description') or '') for o in outputs if isinstance(o, dict)),
    ])
    scores: list[tuple[int, int, str]] = []
    for cat in EXECUTION_CATEGORIES:
        if cat['target_stage'] not in allowed_stages:
            continue
        hits = sum(1 for kw in cat['keywords'] if kw in text)
        if hits:
            scores.append((-hits, EXECUTION_CATEGORY_ORDER[cat['id']], cat['id']))
    if not scores:
        fallback: list[str] = []
        if 'action_design' in allowed_stages:
            fallback.append('action_chain_tactics')
        if 'scene_design' in allowed_stages:
            fallback.append('scene_structure_density')
        if 'state_transition' in allowed_stages:
            fallback.append('state_causal_cost')
        if 'state_propagation' in allowed_stages:
            fallback.append('propagation_information_social')
        return fallback
    scores.sort()
    return [cid for _, _, cid in scores[:4]]


def execution_decomposition_prompt(
    types: list[str] | tuple[str, ...] | None = None,
    domain: str = 'chapter_progress',
    *,
    phase: str = 'methods',
) -> str:
    """Concise genre-targeted 08–11 boundary reminder for method derivation prompts."""
    profile = execution_profile_for_types(types)
    by_id = {c['id']: c for c in profile['categories']}
    type_label = ' / '.join(t['name'] for t in profile['main_types']) or '当前参考书'
    oos_names = '、'.join(by_id[cid]['short_name'] for cid in profile['out_of_scope_categories'])
    ep = profile['execution_profile']

    if phase == 'methods':
        domain_focus = {
            'chapter_progress': f'行动博弈（{ep["action_style"]}）、场景控场（{ep["scene_pov_focus"]}）与状态迁移（{ep["state_cost_focus"]}）',
            'information': f'场景 POV 披露边界（{ep["scene_pov_focus"]}）与非全知传播链（{ep["propagation_focus"]}）',
            'character_arc': f'带能力门槛的行动抉择（{ep["action_style"]}）与心智/代价状态变化（{ep["state_cost_focus"]}）',
            'world_rules': f'外部规则限制下的行动代价（{ep["action_style"]}）与资源/生态状态传播（{ep["propagation_focus"]}）',
        }.get(domain, profile['decomposition_focus'])
        text = (
            f'【08行动–11状态传播·分类型边界（{type_label}）】'
            f'若本条方法服务 08–11 细化步骤，请对照本类型重点：{domain_focus}。'
        )
        if oos_names:
            text += f'非本类型常规子域（{oos_names}）除非原作确有直接原文证据，否则不要套用。'
        text += (
            '严守四步边界：带能力门槛与代价的行动步骤落入 action_design.candidates；'
            '受限 POV 场景卡与 before_state 落入 scene_design；'
            '外部行动触发的 before_state→after_state 实质差值落入 state_transition.transitions；'
            '经目击/传信/流言等载体的条件扩散落入 state_propagation.candidates（禁止全员瞬间全知）。'
        )
        return text
    return f'【08–11 执行链核对（{type_label}）】{profile["decomposition_focus"]}'


def execution_stage_prompt_packet(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Compact deterministic packet frozen into planning manifests for 08–11 stages."""
    profile = execution_profile_for_types(types)
    type_list = [{'id': t['id'], 'name': t['name']} for t in profile['types']]
    ep = profile['execution_profile']
    focus_key_by_stage = {
        'action_design': ('action_style', ep['action_style']),
        'scene_design': ('scene_pov_focus', ep['scene_pov_focus']),
        'state_transition': ('state_cost_focus', ep['state_cost_focus']),
        'state_propagation': ('propagation_focus', ep['propagation_focus']),
    }

    def _for_stage(stage: str) -> dict[str, Any]:
        cats = [c for c in profile['categories'] if c['target_stage'] == stage]
        boundary = profile['step_boundaries'][stage]
        focus_key, focus_val = focus_key_by_stage[stage]
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
            'stage_focus': {focus_key: focus_val},
            'step_boundary': {
                'responsibility': boundary['responsibility'],
                'out_of_scope': list(boundary['out_of_scope']),
                'downstream_steps': [d['step_id'] for d in boundary['downstream_steps']],
            },
        }

    return {
        'action_design': _for_stage('action_design'),
        'scene_design': _for_stage('scene_design'),
        'state_transition': _for_stage('state_transition'),
        'state_propagation': _for_stage('state_propagation'),
    }


def execution_blueprint(library: Any, types: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Combine genre-targeted 08–11 execution profile with live workspace method coverage."""
    from nw.studio.downstream_handoff import audit_downstream_handoff

    profile = execution_profile_for_types(types)
    audit = audit_downstream_handoff(library, types=list(types), planning_hierarchy=True)
    exec_tasks = {'action_chain', 'scene_composition', 'state_change', 'state_propagation'}
    exec_stages = {'action_design', 'scene_design', 'state_transition', 'state_propagation'}
    target_methods = [
        m for m in audit.get('methods', ())
        if bool(exec_tasks & set(m.get('tasks', ())))
        or bool(exec_stages & set(m.get('output_stages', ())))
    ]
    by_cat_rec: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in EXECUTION_CATEGORIES}
    by_cat_draft: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in EXECUTION_CATEGORIES}
    by_cat_blocked: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in EXECUTION_CATEGORIES}

    for method in target_methods:
        cats = method.get('execution_categories') or []
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
    return {
        **profile,
        'categories': categories_with_coverage,
        'action_categories': [c for c in categories_with_coverage if c['target_stage'] == 'action_design'],
        'scene_categories': [c for c in categories_with_coverage if c['target_stage'] == 'scene_design'],
        'transition_categories': [c for c in categories_with_coverage if c['target_stage'] == 'state_transition'],
        'propagation_categories': [c for c in categories_with_coverage if c['target_stage'] == 'state_propagation'],
        'coverage_summary': {
            'total_execution_methods': len(target_methods),
            'receivable_action_methods': step_by_id.get('action_design', {}).get('receivable_count', 0),
            'receivable_scene_methods': step_by_id.get('scene_design', {}).get('receivable_count', 0),
            'receivable_transition_methods': step_by_id.get('state_transition', {}).get('receivable_count', 0),
            'receivable_propagation_methods': step_by_id.get('state_propagation', {}).get('receivable_count', 0),
            'primary_category_count': len(profile['primary_categories']),
            'covered_primary_categories': covered_primary,
            'gap_primary_categories': [
                c['id'] for c in categories_with_coverage
                if c['relevance'] == 'primary' and c['receivable_count'] == 0
            ],
            'passage_reference_count': audit['summary']['passage_reference_count'],
        },
        'originality_audit': audit['originality_audit'],
    }
