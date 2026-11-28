"""Step-driven material requirements and decomposition bindings across all workflow stages.

Reads the real workflow stages, default stage-material keys, queries, method tasks,
and corpus domains so decomposition, method derivation, and client views share one
authoritative map from each production step's actual material needs back to how a
reference novel should be read, retrieved, judged (functional vs. methodological),
and bound to the right downstream stage.
"""
from __future__ import annotations

from copy import deepcopy
from functools import cache
from typing import Any

from nw.materials.phase_routes import EXTERNAL_REQUIRES, ORDER, REQUIRES, ROUTES, phase_order
from nw.studio.corpus_catalog import DOMAINS
from nw.studio.corpus_passages import CRAFT_KINDS, KINDS
from nw.studio.method_catalog import (
    CONSUMERS,
    METHOD_FIELDS,
    OUTPUT_LABELS,
    SCOPES,
    STAGES,
    TASKS,
    output_artifacts,
)


MATERIAL_NATURES: dict[str, dict[str, Any]] = {
    'rule_constraint': {
        'id': 'rule_constraint',
        'name': '规则与约束类',
        'description': '决定故事中什么可以发生、什么被禁止、触发门槛、资源成本与例外边界。',
        'primary_steps': ['world_design', 'static_relations', 'state_transition', 'state_propagation'],
    },
    'functional_role': {
        'id': 'functional_role',
        'name': '功能与作用类',
        'description': '说明人物、配角、事件、支线或章场在推进故事、制造阻力、形成交汇中承担的实际作用。',
        'primary_steps': ['character_design', 'plot_design', 'event_design', 'scene_design'],
    },
    'method_technique': {
        'id': 'method_technique',
        'name': '方式与技法类',
        'description': '说明作者具体用什么行动博弈、叙述时序、视角权限、信息披露次序或段落技法实现叙事效果。',
        'primary_steps': ['action_design', 'scene_design', 'expression_design', 'writer'],
    },
    'structural_causal': {
        'id': 'structural_causal',
        'name': '结构与因果链类',
        'description': '定义类型承诺、组合适配、全书主线、钩子接力、伏笔埋收与跨章承接的宏观组织逻辑。',
        'primary_steps': ['type_selection', 'type_adaptation', 'plot_design', 'event_design'],
    },
    'observable_anchor': {
        'id': 'observable_anchor',
        'name': '表现锚点与感官节拍类',
        'description': '把抽象情绪、状态变化、身份线索与空间氛围落实为当前视角可感知的具象动作、物件、外貌与嗓音细节。',
        'primary_steps': ['anchor_design', 'expression_design', 'writer'],
    },
    'verification_gate': {
        'id': 'verification_gate',
        'name': '核验与收口判据类',
        'description': '把已采用的规则、技法与状态变化转为可独立核查的正文证据口径与连续性收口条件。',
        'primary_steps': ['bind_scope', 'review', 'acceptance'],
    },
}


DECOMPOSITION_METHODOLOGY: list[dict[str, str]] = [
    {
        'step': 'read',
        'order': '1',
        'name': '读取（原文与范围定位）',
        'summary': '通读映射 + 章场细拆，保留精确 Unicode 原文引文、章节范围、故事时间与文本顺序差异，区隔非正文章节（前言/感言）。',
    },
    {
        'step': 'retrieve',
        'order': '2',
        'name': '检索（按步骤资料需求定向回查）',
        'summary': '按 14 个设计步骤与写作/审稿实际消费的资料需求分类，在原文事件、人物、关系和段落中定向检索可证实实例并跨章关联。',
    },
    {
        'step': 'judge_function',
        'order': '3',
        'name': '判定作用性（功能与效果）',
        'summary': '判定该处原文承担的实际功能：改变了谁的目标、认知、关系或局面？引发了什么读者预期、情绪转向或跨章承接？删去会损失什么？',
    },
    {
        'step': 'judge_method',
        'order': '4',
        'name': '判定方式性（可迁移做法与绑定步骤）',
        'summary': '剥离原作人名与情节，归纳达成该作用的具体操作方式、所需前置、适用条件与不适用边界，并按资料性质精准绑定到唯一匹配的下游步骤与产物字段。',
    },
]


# Memorized step material requirements aligned directly to src/nw/materials/steps/* and phase_flow.py.
_STEP_SPECS: list[dict[str, Any]] = [
    {
        'step_id': 'type_selection',
        'name': '前置契约 · 立项类型冻结（自动继承）',
        'phase_group': '全书与细化共用',
        'material_natures': ['structural_causal'],
        'need_categories': ['主/子/副类型本体定义', '核心读者承诺与预期边界', '题材禁止项与反例边界'],
        'corpus_domains': ['main_plot', 'hook'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '开篇核心卖点、全书总问题、主线推进方式与结局承诺兑现口径。',
            'retrieval_cues': '检索决定作品类型归属的标志性冲突、核心悬念与题材边界原句。',
            'functional_judgment': '判定该类型要素向读者建立了何种核心期待，以及违背何种边界会让读者出戏。',
            'method_judgment': '总结不同类型组合下确立读者承诺与类型边界的具体立项判断方式。',
        },
    },
    {
        'step_id': 'type_adaptation',
        'name': '前置契约 · 多类型融合（单类型自动冻结）',
        'phase_group': '全书与细化共用',
        'material_natures': ['structural_causal', 'rule_constraint'],
        'need_categories': ['多类型组合冲突与调和规则', '受众/篇幅/节奏适配参数', '概念激活与关注重点转移'],
        'corpus_domains': ['main_plot', 'subplot', 'pacing', 'world_rules'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '主副类型交汇处的取舍、核心设定的现实化或风格化约束参数。',
            'retrieval_cues': '检索参考书中双题材融合（如悬疑+奇幻、权谋+修仙）时相互制约的关键桥段。',
            'functional_judgment': '判定融合规则如何避免风格割裂并强化主线张力。',
            'method_judgment': '提取可复用的类型适配参数、冲突限制与关注重点调整方式。',
        },
    },
    {
        'step_id': 'world_design',
        'name': '世界规则与限制定稿（底层域 03）',
        'phase_group': '全书与细化共用',
        'material_natures': ['rule_constraint'],
        'need_categories': [
            '世界基础、形态（现实/架空/平行/异世界/反乌托邦）与不可改写底层前提',
            '社会阶层、权力结构、职业分工与执行制度',
            '影响当下的时代分期、历史暗流与未写明史实边界',
            '按所选类型分化的六大资源库、货币汇率、消耗速率与交易市场',
            '道具/武器/物证的功能边界、使用代价、反功能与制造工艺',
            '无主角时仍在运转的生态格局、势力张力与空间时间性',
            '（仅适配题材）种族差异、生命构造限制、力量/能量公式与突破代价',
            '（仅适配或显式启用）系统/平行/VR/赛博/乌托邦/多元/游戏化机制',
        ],
        'corpus_domains': ['world_rules'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '按参考书类型重点读取原文中实际生效的制度、资源门槛、道具边界、空间生态或力量代价（严格区分人物口头声称与真实生效规则）。',
            'retrieval_cues': '检索“必须/不得/代价/耗尽/例外/制度/权限/禁令”及受规则直接阻止或改写的决策事件，跳过与该类型无关的跨题材模板。',
            'functional_judgment': '判定该外部规则如何真实限制或改写人物选择，带来何种可验证的后果、损耗或代价，不把人物个人性格或剧情结局混作世界规则。',
            'method_judgment': '将原作机制抽离为“规则主体 + 成立条件 + 限制与代价 + 未知/可见性边界”的世界设计操作，精准落入 world_design.members / limitations。',
        },
    },
    {
        'step_id': 'character_design',
        'name': '核心人物与弧光起点（底层域 04）',
        'phase_group': '全书与细化共用',
        'material_natures': ['functional_role', 'rule_constraint'],
        'need_categories': [
            '主角/反派核心欲望执念、属性与弧光演变方向',
            '配角五级出场分类、不可替代性、防工具化、三层人格外化与三层背景身份',
            '认知偏差、心智模型盲点、意志品质与道德判断/立场',
            '承接 03 世界制度的初始状态、职业定位与技能边界',
            '入场方式（opening/self/other/visible/withheld）与暗身份隔离凭据',
            '（仅适配题材）命运态度、血脉/天赋/基因机制与超凡能力上限',
            '同类型人物数量与章段分布样本（cast_samples）及复用优先原则',
        ],
        'corpus_domains': ['character_arc', 'cast_entry', 'cast_roster'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '按参考书类型读取人物欲望、信念盲点、能力边界、外化习惯、入场披露方式与各章实际出场人数分布。',
            'retrieval_cues': '检索人物首次出场、面临伦理/利益抉择、能力受限时刻及同人别名归并证据，跳过跨题材超凡模板。',
            'functional_judgment': '判定人物在全书和单章承担何种剧情职责（推动/阻力/信息/镜像/见证），确认其独立目标与不可替代性。',
            'method_judgment': '归纳复用优先建卡、配角职责分派、三层外化与能力代价绑定的设计方式，精准落入 character_design。',
        },
    },
    {
        'step_id': 'static_relations',
        'name': '人物关系与势力张力（底层域 05）',
        'phase_group': '全书与细化共用',
        'material_natures': ['rule_constraint', 'functional_role'],
        'need_categories': [
            '全书角色关系网（核心人物≥3连接、至少2条不经过主角的配角独立互动）',
            '亲缘、社会（竞争/旁观/合作/同盟）、情感与主配角 8 类关系定位',
            '权力不对称、信息不对称、情感债务、信任/亲密光谱、情感错位与多维结构性对立',
            '势力自动互动、阶层权力结构、资源稀缺依赖与空间权力关系',
            '（仅适配题材）多种族社会嵌入与种族间结构性张力',
        ],
        'corpus_domains': ['character_arc', 'cast_entry', 'cast_roster', 'subplot'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '仅基于已有实体核对双方立场、权力/信息不对称、情感债务、情感错位及不经过主角的配角独立往来。',
            'retrieval_cues': '检索人物交集时的身份称谓、立场对峙、旧账/债务提及、不对称信息差与配角间独立对话。',
            'functional_judgment': '判定静态关系如何为后续剧情制造随时可升级的张力、阻力或支线交汇条件，不提前写死未发生结局。',
            'method_judgment': '提炼关系端点设定、多维对立构造、配角独立互动网与下游关系约束（relations / requirements）。',
        },
    },
    {
        'step_id': 'plot_design',
        'name': '故事大纲、开篇承诺与卷章切分（底层域 06）',
        'phase_group': '全书与细化共用',
        'material_natures': ['structural_causal', 'functional_role'],
        'need_categories': [
            '15 类标准叙事结构、三幕/起承转合骨架、主支线引力中心与主角失败代价',
            '开篇承诺、黄金三章、终章不可逆收束与首尾呼应',
            '推进动力、重/中/轻/空章节奏轮换、冲突轮换与同类型篇幅档位配比',
            '配角发起转折、支线与主线交汇及资源剧情绑定',
            '23 类核心情节推进机制（按所选类型精准排序隔离）',
            '伏笔埋设（2–10章窗口）、休眠延迟解码、≥80%回收率与双伏笔联动反转',
            '信息差设计、延迟信息释放、认知错位悬念与读者情绪序列（reader_plan）',
        ],
        'corpus_domains': ['main_plot', 'subplot', 'hook', 'foreshadow', 'information', 'pacing', 'chapter_progress'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '按参考书类型读取主线因果链、不可逆选择、支线交汇、钩子设问兑现、伏笔埋收窗口与读者信息差。',
            'retrieval_cues': '检索跨章 causes/enables/responds/escalates/foreshadows/pays_off/reveals 关系及两端不同原文证据，跳过跨题材推进机制。',
            'functional_judgment': '判定某事件/伏笔/钩子对全书总问题、单卷转折、单章推进和读者情绪起伏起了何种作用（区分读者体验与角色情绪）。',
            'method_judgment': '提炼结构推进、钩子接力、伏笔掩体、反转前奏/余响与前章遗留承接（continuations），精准落入 plot_design。',
        },
    },
    {
        'step_id': 'event_design',
        'name': '本章事件链与因果触发（底层域 07）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['structural_causal', 'functional_role'],
        'need_categories': [
            '严格引用 06 event_nodes 的前驱完成门（completion_condition）与逻辑因果顺序（104.1）',
            '决策连锁反应、探索归来后继与配角独立行动线触发的意外交汇',
            '世界自动运转事件、生态扰动失衡/寻找新均衡、势力自动变化与暗线循环发现',
            '（仅适配题材）副本/污染/外星/灾难/生化/主神/规则任务条件危机事件',
        ],
        'corpus_domains': ['chapter_progress', 'subplot', 'hook', 'cast_entry'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '相邻事件之间的前驱完成门、决策连锁压力（next_pressure）与场外势力/环境自动运转引发的新事件。',
            'retrieval_cues': '检索细拆事件中的进入前提、突发转折、前因完成标志与配角自主入场节点，非适配题材跳过超自然危机模板。',
            'functional_judgment': '判定上一事件的后果如何必然或合理地催生下一事件候选，而非靠巧合硬推或时间线倒置。',
            'method_judgment': '总结事件前驱门设置、多支线交汇触发与条件分支预案（conditional_candidate），精准落入 event_design.candidates。',
        },
    },
    {
        'step_id': 'action_design',
        'name': '人物行动博弈与试错代价（底层域 08）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['method_technique', 'rule_constraint'],
        'need_categories': [
            '完整行动链（蓄力→动作→观察-判断-调整→结果）、决策风格与语言/环境/资源/信息/社会多维博弈',
            '人物能力门槛校验（requires 取自 04 capabilities）、试错失败回撤、认知/立场错位与道德两难代价',
            '（仅适配题材）超凡能量运用与召唤/御兽/炼丹/炼器/阵法行动机制',
            '（仅适配题材）机甲/AI/机器人操控与异常收容行动机制',
        ],
        'corpus_domains': ['chapter_progress', 'character_arc', 'world_rules', 'cast_entry'],
        'passage_techniques': ['procedure_branch'],
        'decomposition_guide': {
            'reading_target': '人物在阻力面前的具体行动步骤、受限后的变通/试错、语言交锋与必须支付的真实代价（按题材跳过跨类型超凡或机甲模板）。',
            'retrieval_cues': '检索事件中的 goal/conflict/choice/cost/result 及“尝试→受阻→改变策略→付出代价”片段。',
            'functional_judgment': '判定行动如何暴露人物性格、验证世界规则与能力门槛限制并推动局势发生实质位移。',
            'method_judgment': '提炼带能力前置、障碍升级、试错失败分支与代价核算的行动链设计方式，精准落入 action_design.candidates。',
        },
    },
    {
        'step_id': 'scene_design',
        'name': '场景卡与 POV 边界排布（底层域 09）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['functional_role', 'method_technique'],
        'need_categories': [
            '受限 POV 视角边界、在场/缺席/背景≤3人控制、知情差与可披露边界（allowed_disclosure）',
            '每场显式绑定 1 个上游事件（selected_events）与 1+ 个上游动作（selected_actions）及交接 10 步的 before_state 快照',
            '场景空间方位动线（115.* / S1.*）、三步铺垫（155.2）、重/中/轻/空情感密度、配角职责落实（cast_payoffs）与章场推进（scene_progress）',
            '（仅适配题材）超凡固化态、能量干扰盲区与突破临界点场景规则',
        ],
        'corpus_domains': ['chapter_progress', 'cast_entry', 'cast_roster', 'information', 'pacing', 'narration'],
        'passage_techniques': ['procedure_branch', 'focus_relay', 'place_function'],
        'decomposition_guide': {
            'reading_target': '场景切入点与空间定位、在场人员与各自当下目标、POV 知情边界、场内信息释放与离场遗留压力。',
            'retrieval_cues': '检索场景边界（地点/时间/视角切换）、谁在场听见/看见、谁被蒙在鼓里及场末转向原句。',
            'functional_judgment': '判定本场在整章承担何种职责、完成了哪一格推进以及为下一场留下了什么压力，绝不越界预支 10 步 after_state。',
            'method_judgment': '提炼场景组织、受限 POV 信息差控场、同场多人物交集与场景转场方式，精准落入 scene_design。',
        },
    },
    {
        'step_id': 'state_transition',
        'name': '场内状态变化与代价（底层域 10）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['rule_constraint', 'functional_role'],
        'need_categories': [
            '原样承接 09 before_state，由本场具体外部行动触发至少一项实质差值的 after_state 与回写 patches',
            '核心属性不突变、道具/资源归属一致、代价不消失/叠加缓释与失败情形延续（failure/continuity）',
            '心智模型破裂重塑、权力视觉化反转、信任易崩难建、配角欠账还账与≤5 活跃状态过载',
            '（仅适配题材）超凡能量储备/纯度跃迁与生命构造改善/退化反哺',
        ],
        'corpus_domains': ['character_arc', 'chapter_progress', 'world_rules'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '事件前后人物心理/立场/关系/身体/资源的可核查前后差值，以及导致该变化的外部行动与不可消除代价。',
            'retrieval_cues': '检索 `initial_state -> final_state`、`information_before -> information_after` 及代价延续证据。',
            'functional_judgment': '判定状态变化是否由本场外部行动真实触发，且对后续章节构成不可忽视的约束（不越界代 11 步做场外全知传播）。',
            'method_judgment': '归纳“前态核对 → 行动触发 → 后态差值 → 代价/失败/连续性保障”的状态迁移写法，精准落入 state_transition。',
        },
    },
    {
        'step_id': 'state_propagation',
        'name': '状态连锁传播预案（底层域 11）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['rule_constraint', 'structural_causal'],
        'need_categories': [
            '非全知信息载体（目击/传信/流言/留痕/社会记忆）与未目击者不知情边界',
            '以 10 步 planned_change 或 accepted_fact 为根变化，全部开启三门守卫的 conditional_candidate',
            '资源盈余→赤字转向（20.4）、稀缺恐慌与权力膨胀（27.3）及组织/供应链宏观波及',
        ],
        'corpus_domains': ['information', 'chapter_progress', 'subplot', 'world_rules'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '某事件结果经由何种具体载体（目击/传信/流言/留痕/资源流变）传到场外人物或势力并引发后续连锁决策。',
            'retrieval_cues': '检索跨章 `reveals`/`causes` 关系及信息经第三方转述、误读、延迟抵达或资源短缺引发连锁反应的桥段。',
            'functional_judgment': '判定后果传播如何避免“全员瞬间全知”，制造真实的时间差、误判或连锁反应，保持条件候选交由 12 步挑选。',
            'method_judgment': '总结设定传播载体、三门确认条件与知情延迟的设计方式，精准落入 state_propagation.candidates。',
        },
    },
    {
        'step_id': 'anchor_design',
        'name': '具象动作锚点与感官节拍（底层域 12）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['observable_anchor'],
        'need_categories': [
            '身体微反应（B2/B3）、近景/特写/主观/定格镜头、氛围映射突变与脉搏/呼吸点（beats）',
            '时间锚点（113.5）、他人视角人格锚点（板块147）与视角切换前置锚点（120.20）',
            '道具交互与能力边界观测，严格绑定本场动作（action_ref/step_index/before|during|after）',
            '显式挑选本场采用的上游传播候选（selected_propagations），未选者保留后续预案',
        ],
        'corpus_domains': ['narration', 'pacing'],
        'passage_techniques': ['sensory_evidence', 'place_function', 'focus_relay'],
        'decomposition_guide': {
            'reading_target': '不靠抽象告知、而通过当前 POV 可感知的身体细节、物件交互、镜头聚焦与环境反常传递情绪或真相的段落。',
            'retrieval_cues': '检索动作动词、感官线索（视觉/听觉/触觉）、地点陈设反常缺席与微表情变化原句。',
            'functional_judgment': '判定该具象锚点替读者省去了什么直白说教，或精准传递了何种潜台词与情绪强度（严守本场 POV 观察者边界）。',
            'method_judgment': '归纳“触发时机（before/during/after）+ 观察者 POV + 物件/身体载体 + 可核效果”的锚点设计方式，精准落入 anchor_design.beats。',
        },
    },
    {
        'step_id': 'expression_design',
        'name': '叙述距离、对白与文风指导（底层域 13）',
        'phase_group': '卷/章/场细化专用',
        'material_natures': ['method_technique', 'observable_anchor'],
        'need_categories': [
            '叙述者可信度/声音距离/干预程度与视角知识边界（109.*）',
            '叙述时序（顺叙/插叙/倒叙/先果后因与回落当下）与信息释放方式（116.7）',
            '潜台词对白技术、非直接回答、五感叙述距离、快中慢语言质感轮换与全篇语体统一（106.*）',
            '按小说主副类型分层的 10 类语气（TONE_*）与 20 类文风（STYLE_*）适配及竞争偏好协调（preference_resolutions）',
        ],
        'corpus_domains': ['narration', 'pacing', 'information'],
        'passage_techniques': sorted(KINDS.keys() | CRAFT_KINDS.keys()),
        'decomposition_guide': {
            'reading_target': '作者在具体段落中如何安排讲述次序、切换视角权限、组织对白潜台词与长短句节奏、区分事实与人物主观推断。',
            'retrieval_cues': '检索 `narration` 观察中的 `time_order`/`presentation`/`voice_access`/`claim_status` 与各类段落技法原句。',
            'functional_judgment': '判定该表达安排如何让读者在特定句点形成新判断（reader_change）或引发角色当场反应，不越界改动上游剧情与披露边界。',
            'method_judgment': '把原作段落结构抽离为可复用的表达节拍指导（expression_design.guidance），明确适用语境、不适用边界与验收判据。',
        },
    },
    {
        'step_id': 'bind_scope',
        'name': '冻结可写场景工作包（底层域 14 · 卷纲自动收口）',
        'phase_group': '全书收口(第7步)/细化收口(第14步)',
        'material_natures': ['verification_gate'],
        'need_categories': [
            '规划师自检、三层精准筛选与三阶段数据传递完整性（板块87/90、126.*/128.*）',
            '本范围已采用资料与拆解方法的成员/过程绑定（material_bindings / process_bindings）与来源标签',
            '章/场细化逐场汇总正文可见表现（observable）与审稿判据（check）至 method_guidance（全书/卷纲为空）',
        ],
        'corpus_domains': ['main_plot', 'world_rules', 'narration', 'chapter_progress'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '对照已选方法的预期产物与实际场景，确认每项方法都有明确落场位置与独立验收口径。',
            'retrieval_cues': '核查方法 `outputs -> downstream -> acceptance` 是否闭环且指向真实步骤字段，不改写上游设计。',
            'functional_judgment': '确保上游拆解方法真正落到具体场景可执行条目，而非停留在口号标签或越界扩散到无关场景。',
            'method_judgment': '按 `method_binding` 规范汇总每场必查表现与审稿核验口径，精准落入 bind_scope。',
        },
    },
    {
        'step_id': 'writer',
        'name': '15. 正文写作与修订',
        'phase_group': '写作与验收',
        'material_natures': ['method_technique', 'observable_anchor'],
        'need_categories': [
            '严格执行受限 POV、配角 POV 前 500 字限制与场外信息隔离',
            '句长比例、高强度短句、精确动词、禁用无因/巧合词与人物首出场外貌嗓音落笔',
            '完整动作序列、感官锚点、首尾句设计与代价可视化落文（带 story_write_manifest 溯源）',
        ],
        'corpus_domains': ['narration', 'pacing', 'character_arc', 'cast_entry'],
        'passage_techniques': sorted(KINDS.keys() | CRAFT_KINDS.keys()),
        'decomposition_guide': {
            'reading_target': '正文中句子如何承接上一拍、人物如何用各自口吻说话、动作如何连贯收束、代价如何可见、章末如何自然停顿。',
            'retrieval_cues': '检索高质量正文片段中的段间过渡、精确动词、首出场剪影和对话潜台词。',
            'functional_judgment': '判定该段写法为何让读者产生身临其境的阅读体验而不显得抽象告知或视角出戏。',
            'method_judgment': '经由 `expression_design.guidance`、`anchor_design.beats` 与 `bind_scope.method_guidance` 交付给正文写作与修订。',
        },
    },
    {
        'step_id': 'review',
        'name': '16. 独立审稿与证据核验',
        'phase_group': '写作与验收',
        'material_natures': ['verification_gate'],
        'need_categories': [
            '逐条对照 method_guidance.check 与正文精确引文，杜绝以计划复述代替正文证据',
            '语言红线（禁“他心想/他意识到”）、潜台词、场景因果与结局不可逆检查',
            '视角越界/信息偷跑拦截、角色/世界/时间线/伏笔一致性与原创性防雷同复核',
        ],
        'corpus_domains': ['narration', 'information', 'world_rules'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '提炼方法时明确“正文出现何种可引用段落才算通过，仅写关键词或复述计划为何不算”。',
            'retrieval_cues': '核对每条方法的 `acceptance.check` 与 `acceptance.evidence_required` 是否可定位到正文段落。',
            'functional_judgment': '判定该验收口径能否独立分辨“真正写出了效果”与“口头宣称已使用”。',
            'method_judgment': '把拆解中验证过的原句证据模式转化为可独立复核的正文审稿标准。',
        },
    },
    {
        'step_id': 'acceptance',
        'name': '17. 状态提取、事实复核与批次接受',
        'phase_group': '写作与验收',
        'material_natures': ['verification_gate', 'rule_constraint'],
        'need_categories': [
            '以审稿通过正文精确字符区间为依据的状态增量提取（state_delta）与独立 fact_review',
            '严格隔离叙述确证事实（WORLD）与人物主观说法/推测（attributed/inferred）',
            '道具状态一致（107.3）、代价累积不消失（118.1–118.2）与批次原子提交/分支提升复核',
        ],
        'corpus_domains': ['chapter_progress', 'cast_entry', 'world_rules'],
        'passage_techniques': [],
        'decomposition_guide': {
            'reading_target': '区分原文中“叙述确证事实（stated）”与“人物说法/推测（attributed/inferred）”，核对道具与代价跨章留痕。',
            'retrieval_cues': '在拆解 `narration`/`cast_entry` 时严格标注 `claim_status`，防止把人物臆测当既成事实。',
            'functional_judgment': '确保事实库只沉淀有审稿通过与正文精确区间支撑的真实变化，支撑下一章持续推演。',
            'method_judgment': '将“可核查变化点与连续性追踪”设计进状态迁移与范围验收要求。',
        },
    },
]


DOMAIN_STEP_BINDINGS: dict[str, dict[str, Any]] = {
    'main_plot': {
        'domain': 'main_plot',
        'name': DOMAINS['main_plot'],
        'material_natures': ['structural_causal'],
        'target_steps': ['type_selection', 'type_adaptation', 'plot_design'],
        'recommended_tasks': ['main_plot', 'volume_outline', 'type_choice'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'directions', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'members', 'artifact_kind': 'plot'},
            {'stage': 'plot_design', 'field': 'event_nodes', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['event_design', 'scene_design', 'writer', 'review'],
        'reading_focus': '提取全书总问题、主角核心目标、主要阻力、关键不可逆选择与结局兑现。',
        'retrieval_cues': '跨章追踪开篇设问、中段升级转折与终局兑现的因果事件链。',
        'functional_judgment': '判定主线冲突如何驱动全书长篇动力并兑现类型核心读者承诺。',
        'method_judgment': '抽离“总问题确立 → 阻力递进 → 代价抉择 → 结局兑现”的主线架构做法，绑定至全书/卷级剧情设计。',
    },
    'subplot': {
        'domain': 'subplot',
        'name': DOMAINS['subplot'],
        'material_natures': ['structural_causal', 'functional_role'],
        'target_steps': ['plot_design', 'event_design', 'static_relations'],
        'recommended_tasks': ['subplot', 'event_chain', 'relationships'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'event_nodes', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'members', 'artifact_kind': 'plot'},
            {'stage': 'event_design', 'field': 'candidates', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['event_design', 'scene_design', 'review'],
        'reading_focus': '提取支线的独立目标、与主线的交汇事件以及交汇后对主线的实际改写。',
        'retrieval_cues': '检索支线起势节点、`crosses` 交汇关系及主线随之改道的原文依据。',
        'functional_judgment': '判定支线是否真正为主线提供关键条件/阻力/情感映照，而非游离注水。',
        'method_judgment': '提炼支线并行推进与关键节点交汇主线的结构操作，绑定至剧情设计与事件设计。',
    },
    'character_arc': {
        'domain': 'character_arc',
        'name': DOMAINS['character_arc'],
        'material_natures': ['functional_role', 'rule_constraint'],
        'target_steps': ['character_design', 'static_relations', 'plot_design', 'action_design', 'state_transition'],
        'recommended_tasks': ['character_arc', 'relationships', 'action_chain', 'state_change'],
        'target_outputs': [
            {'stage': 'character_design', 'field': 'members', 'artifact_kind': 'character'},
            {'stage': 'character_design', 'field': 'capabilities', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'event_nodes', 'artifact_kind': 'stage_product'},
            {'stage': 'state_transition', 'field': 'transitions', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['plot_design', 'action_design', 'scene_design', 'writer', 'review'],
        'reading_focus': '提取人物欲望、初始信念/边界、承受的压力、关键抉择、真实代价及最终变化。',
        'retrieval_cues': '检索 `changes_character` 关系及人物在高压下坚持或打破原则的前后对照证据。',
        'functional_judgment': '判定人物选择如何既符合自身性格与能力边界，又推动剧情发生不可逆变化。',
        'method_judgment': '提炼“初始执念/边界 → 压力逼迫 → 付出代价的抉择 → 状态/信念转变”的人物弧光与状态变化设计方法。',
    },
    'hook': {
        'domain': 'hook',
        'name': DOMAINS['hook'],
        'material_natures': ['structural_causal', 'method_technique'],
        'target_steps': ['plot_design', 'event_design', 'scene_design', 'expression_design'],
        'recommended_tasks': ['hook', 'chapter_outline', 'scene_composition'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'reader_plan', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'promise_plan', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'members', 'artifact_kind': 'scene'},
            {'stage': 'expression_design', 'field': 'guidance', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['scene_design', 'expression_design', 'writer', 'review'],
        'reading_focus': '提取悬念/利益/危险的抛出点、读者期待、实际回应与后续升级链。',
        'retrieval_cues': '检索章末/场末设问及后续章节中的 `responds`、`escalates` 关系与多处原文。',
        'functional_judgment': '判定钩子如何拉动读者继续翻页，以及回应兑现是否满足并抬升了原有期待。',
        'method_judgment': '提炼设问抛出、延迟回应与新问题接力的结构与表达手法。',
    },
    'foreshadow': {
        'domain': 'foreshadow',
        'name': DOMAINS['foreshadow'],
        'material_natures': ['structural_causal'],
        'target_steps': ['plot_design', 'scene_design', 'expression_design'],
        'recommended_tasks': ['foreshadow', 'information'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'promise_plan', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'members', 'artifact_kind': 'promise'},
            {'stage': 'scene_design', 'field': 'members', 'artifact_kind': 'scene'},
            {'stage': 'expression_design', 'field': 'guidance', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['scene_design', 'expression_design', 'writer', 'review'],
        'reading_focus': '提取埋设伪装、表层预期含义、中途提示/误读、回收节点与跨章窗口依据。',
        'retrieval_cues': '检索 `foreshadows`、`hints`、`pays_off` 关系链，确认埋设与回收至少有两处不同章节原文。',
        'functional_judgment': '判定伏笔如何在不提前剧透的前提下埋下合理依据，并在回收时制造意料之外、情理之中的反转。',
        'method_judgment': '提炼伏笔掩体、中途二次提示与跨章回收窗口的编排方法。',
    },
    'information': {
        'domain': 'information',
        'name': DOMAINS['information'],
        'material_natures': ['method_technique', 'structural_causal'],
        'target_steps': ['plot_design', 'scene_design', 'state_propagation', 'expression_design'],
        'recommended_tasks': ['information', 'state_propagation', 'scene_composition'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'reader_plan', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'members', 'artifact_kind': 'scene'},
            {'stage': 'state_propagation', 'field': 'candidates', 'artifact_kind': 'stage_product'},
            {'stage': 'expression_design', 'field': 'guidance', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['scene_design', 'expression_design', 'writer', 'review'],
        'reading_focus': '对照读者与各人物事前/事后所知差值、披露次序、误读来源与纠正节点。',
        'retrieval_cues': '检索 `reveals` 关系及事件中 `information_before`/`information_after` 发生跃迁的原句。',
        'functional_judgment': '判定信息不对称如何制造悬念、误判冲突或延迟真相的戏剧张力。',
        'method_judgment': '提炼分批信息释放、知情权限隔离与信息传播条件控制的方法。',
    },
    'pacing': {
        'domain': 'pacing',
        'name': DOMAINS['pacing'],
        'material_natures': ['method_technique', 'observable_anchor'],
        'target_steps': ['plot_design', 'scene_design', 'anchor_design', 'expression_design', 'writer'],
        'recommended_tasks': ['pacing', 'expression', 'anchors'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'reader_plan', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'chapters', 'artifact_kind': 'stage_product'},
            {'stage': 'anchor_design', 'field': 'beats', 'artifact_kind': 'stage_product'},
            {'stage': 'expression_design', 'field': 'guidance', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['scene_design', 'expression_design', 'writer', 'review'],
        'reading_focus': '提取事件快慢序列、紧张与释放节拍、情绪触发点与章场转换方式。',
        'retrieval_cues': '检索 `emotional_shift` 关系与章内 `emotion_before -> emotion_after` 剧烈起伏段落。',
        'functional_judgment': '判定节奏张弛如何防止疲劳、在关键高潮处放大情绪释放感。',
        'method_judgment': '提炼场景内快慢交替、情绪铺垫与转场控速的可执行操作。',
    },
    'world_rules': {
        'domain': 'world_rules',
        'name': DOMAINS['world_rules'],
        'material_natures': ['rule_constraint'],
        'target_steps': ['world_design', 'plot_design', 'action_design', 'state_transition'],
        'recommended_tasks': ['world_rules'],
        'target_outputs': [
            {'stage': 'world_design', 'field': 'members', 'artifact_kind': 'world'},
            {'stage': 'world_design', 'field': 'limitations', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['character_design', 'plot_design', 'action_design', 'scene_design', 'review'],
        'reading_focus': '提取原文可核对的运行规律/制度/资源门槛、适用主体与条件、例外边界及受约束决策后果。',
        'retrieval_cues': '检索规则陈述与受规则影响的实际事件及 `causes`/`enables`/`opposes` 关系两端原文。',
        'functional_judgment': '判定世界规则如何真实限制人物选择或制造行动成本，而非沦为背景装饰。',
        'method_judgment': '把原作规则转化为可落入本项目世界卡（rule/limits）并约束下游剧情与行动的设计操作。',
    },
    'narration': {
        'domain': 'narration',
        'name': DOMAINS['narration'],
        'material_natures': ['method_technique', 'observable_anchor'],
        'target_steps': ['scene_design', 'anchor_design', 'expression_design', 'writer', 'review'],
        'recommended_tasks': ['narration', 'expression', 'anchors'],
        'target_outputs': [
            {'stage': 'expression_design', 'field': 'guidance', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'members', 'artifact_kind': 'scene'},
            {'stage': 'anchor_design', 'field': 'beats', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['expression_design', 'writer', 'review'],
        'reading_focus': '提取讲述时序、呈现模式、谁在看/说/想/听、证据性质（stated/attributed/inferred）及段落技法链。',
        'retrieval_cues': '定位连续段落承接、感官细节、空间功能、视角受限反应及读者认知更新的精确短引。',
        'functional_judgment': '判定该叙述安排对人物当场回应和读者认知变化（reader_change）产生了什么具体效果。',
        'method_judgment': '抽离可迁移的叙述节拍、表达文风或具象锚点操作，绑定到场景/锚点/表达设计并交付写审。',
    },
    'chapter_progress': {
        'domain': 'chapter_progress',
        'name': DOMAINS['chapter_progress'],
        'material_natures': ['functional_role', 'structural_causal'],
        'target_steps': ['plot_design', 'event_design', 'action_design', 'scene_design', 'state_transition', 'state_propagation'],
        'recommended_tasks': ['chapter_outline', 'event_chain', 'action_chain', 'scene_composition', 'state_change', 'state_propagation', 'information'],
        'target_outputs': [
            {'stage': 'plot_design', 'field': 'continuations', 'artifact_kind': 'stage_product'},
            {'stage': 'event_design', 'field': 'candidates', 'artifact_kind': 'stage_product'},
            {'stage': 'action_design', 'field': 'candidates', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'scene_progress', 'artifact_kind': 'stage_product'},
            {'stage': 'state_transition', 'field': 'transitions', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['event_design', 'action_design', 'scene_design', 'expression_design', 'writer', 'review'],
        'reading_focus': '提取章场进入条件、触发转向、认知/关系/局面变化、留下压力及后续跨章实际承接。',
        'retrieval_cues': '按章场定位前因、转折点与新压力原句，跨章核对 `later_use` 实际承接关系。',
        'functional_judgment': '判定每一场如何切实推进局面或改变知情，杜绝原地踏步的无效水文。',
        'method_judgment': '提炼单章推进、行动应对与前章遗留承接（continuations/scene_progress）的可复用设计方式。',
    },
    'cast_entry': {
        'domain': 'cast_entry',
        'name': DOMAINS['cast_entry'],
        'material_natures': ['functional_role', 'method_technique'],
        'target_steps': ['character_design', 'static_relations', 'plot_design', 'action_design', 'scene_design'],
        'recommended_tasks': ['character_arc', 'relationships', 'subplot', 'action_chain', 'scene_composition', 'information', 'foreshadow'],
        'target_outputs': [
            {'stage': 'character_design', 'field': 'cast_assignments', 'artifact_kind': 'stage_product'},
            {'stage': 'static_relations', 'field': 'relations', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'cast_events', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'cast_payoffs', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['static_relations', 'plot_design', 'scene_design', 'expression_design', 'writer', 'review'],
        'reading_focus': '提取人物为何在此时出场、自身独立目的、交集作用、身份披露途径与后续揭晓。',
        'retrieval_cues': '定位人物入场交集原句、谁自报/转述/听见及跨章 `reveals`/`pays_off` 身份揭晓证据。',
        'functional_judgment': '判定该角色在当前事件承担的真实剧情职责与自身动因，避免无理由工具人。',
        'method_judgment': '提炼人物自然入场、职责分派/复用与身份分层披露的操作方法。',
    },
    'cast_roster': {
        'domain': 'cast_roster',
        'name': DOMAINS['cast_roster'],
        'material_natures': ['functional_role', 'verification_gate'],
        'target_steps': ['character_design', 'static_relations', 'plot_design', 'scene_design'],
        'recommended_tasks': ['character_arc', 'relationships', 'chapter_outline', 'scene_composition'],
        'target_outputs': [
            {'stage': 'character_design', 'field': 'cast_assignments', 'artifact_kind': 'stage_product'},
            {'stage': 'plot_design', 'field': 'cast_events', 'artifact_kind': 'stage_product'},
            {'stage': 'scene_design', 'field': 'cast_payoffs', 'artifact_kind': 'stage_product'},
        ],
        'downstream_consumers': ['character_design', 'plot_design', 'scene_design', 'review'],
        'reading_focus': '逐章核实实际出场/仅提及人物、个人与群体区分、全书地位与单章剧情职责，并统计同类型人数分布。',
        'retrieval_cues': '对照每章全部细拆事件与人物别名归并，核对在场证据与全书地位依据。',
        'functional_judgment': '判定全书与各章段如何控制出场人数密度、避免人物膨胀或功能重叠。',
        'method_judgment': '提炼复用已有角色承担新职责、推迟引入新人与分阶段调控阵容密度的方法，并同步产出同类型人数样本。',
    },
}


@cache
def _workflow_stage_material_stats() -> dict[str, dict[str, Any]]:
    from nw.materials.phase_flow import DEFAULT_STAGE_MATERIALS, FUNCTION_QUERIES
    from nw.materials.stage_input import extract_step_keys

    profiles_by_stage: dict[str, list[str]] = {}
    for profile, stages in ROUTES.items():
        for stage in stages:
            profiles_by_stage.setdefault(stage, []).append(profile)

    stats: dict[str, dict[str, Any]] = {}
    for stage in ORDER:
        raw = DEFAULT_STAGE_MATERIALS.get(stage, '')
        stats[stage] = {
            'workflow_material_queries': list(FUNCTION_QUERIES.get(stage, ())),
            'workflow_material_key_count': len(extract_step_keys(raw)),
            'workflow_material_chars': len(raw),
            'workflow_material_profiles': sorted(profiles_by_stage.get(stage, ())),
        }
    from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
    from nw.materials.steps.state_extract import MATERIAL as STATE_EXTRACT_MATERIAL
    from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
    stats['writer'] = {
        'workflow_material_queries': ['受限视角 人物外貌嗓音 动作序列 感官锚点 节奏文风'],
        'workflow_material_key_count': len(extract_step_keys(WRITING_MATERIAL)),
        'workflow_material_chars': len(WRITING_MATERIAL),
        'workflow_material_profiles': sorted(profiles_by_stage.get('writer', ())),
    }
    stats['review'] = {
        'workflow_material_queries': ['独立审稿 正文引文证据 视角越界 跨章语体'],
        'workflow_material_key_count': len(extract_step_keys(REVIEW_MATERIAL)),
        'workflow_material_chars': len(REVIEW_MATERIAL),
        'workflow_material_profiles': sorted(profiles_by_stage.get('review', ())),
    }
    stats['acceptance'] = {
        'workflow_material_queries': ['状态增量提取 事实证据复核 客观事实与人物说法隔离'],
        'workflow_material_key_count': len(extract_step_keys(STATE_EXTRACT_MATERIAL)),
        'workflow_material_chars': len(STATE_EXTRACT_MATERIAL),
        'workflow_material_profiles': sorted(profiles_by_stage.get('acceptance', ())),
    }
    return stats


def domain_bindings(version: int | None = None) -> dict[str, dict[str, Any]]:
    from nw.studio.corpus_catalog import SCHEMA_VERSION, domains_for

    active = domains_for(SCHEMA_VERSION if version is None else version)
    step_names = {**STAGES, 'writer': '正文写作', 'review': '独立审稿', 'acceptance': '范围验收'}
    result: dict[str, dict[str, Any]] = {}
    for domain in active:
        spec = deepcopy(DOMAIN_STEP_BINDINGS[domain])
        spec['target_step_names'] = [step_names.get(step, step) for step in spec['target_steps']]
        spec['material_nature_names'] = [MATERIAL_NATURES[n]['name'] for n in spec['material_natures']]
        spec['recommended_task_names'] = [TASKS[t]['name'] for t in spec['recommended_tasks'] if t in TASKS]
        result[domain] = spec
    return result


def domain_prompt_guide(domain: str, *, craft: bool = True) -> str:
    """Concise step-demand + 4-step (read/retrieve/function/method) guide for relations phase."""
    spec = DOMAIN_STEP_BINDINGS.get(domain)
    if not spec:
        return ''
    step_names = {**STAGES, 'writer': '正文写作', 'review': '独立审稿', 'acceptance': '范围验收'}
    steps = '、'.join(step_names.get(s, s) for s in spec['target_steps'])
    natures = '、'.join(MATERIAL_NATURES[n]['name'] for n in spec['material_natures'])
    text = (
        f"【步骤资料需求绑定】本职责（{spec['name']}，性质：{natures}）直接服务后续步骤：{steps}。"
        f"拆解须按「读取→检索→判定作用性→判定方式性」核对："
        f"检索关注：{spec['retrieval_cues']}"
        f"作用性判定：{spec['functional_judgment']}"
        f"方式性判定：{spec['method_judgment']}"
    )
    if not craft:
        text = text.replace('sensory_evidence', '').replace('reader_address', '')
    return text


def method_derivation_guide(domain: str) -> dict[str, Any]:
    """Structured step-binding target packet injected into method derivation prompts."""
    spec = DOMAIN_STEP_BINDINGS.get(domain)
    if not spec:
        return {}
    step_names = {**STAGES, 'writer': '正文写作', 'review': '独立审稿', 'acceptance': '范围验收'}
    step_lookup = {row['step_id']: row for row in _STEP_SPECS}
    target_needs = [
        {
            'step': step,
            'step_name': step_names.get(step, step),
            'need_categories': step_lookup[step]['need_categories'],
        }
        for step in spec['target_steps']
        if step in step_lookup
    ]
    allowed_tasks = [
        {
            'id': tid,
            'name': TASKS[tid]['name'],
            'stages': list(TASKS[tid]['stages']),
            'scopes': list(TASKS[tid]['scopes']),
            'input_kinds': list(TASKS[tid]['input_kinds']),
        }
        for tid in spec['recommended_tasks']
        if tid in TASKS
    ]
    guide = {
        'source_domain': domain,
        'source_domain_name': spec['name'],
        'material_natures': [MATERIAL_NATURES[n]['name'] for n in spec['material_natures']],
        'target_steps': target_needs,
        'recommended_tasks': allowed_tasks,
        'recommended_outputs': deepcopy(spec['target_outputs']),
        'recommended_consumers': [
            {'id': cid, 'name': CONSUMERS.get(cid, cid)} for cid in spec['downstream_consumers']
        ],
        'functional_role_check': spec['functional_judgment'],
        'method_pattern_check': spec['method_judgment'],
    }
    if domain == 'world_rules':
        from nw.studio.world_materials import WORLD_CATEGORIES, WORLD_STEP_BOUNDARY
        guide['world_categories'] = [
            {'id': c['id'], 'name': c['name'], 'usage_mode': c['usage_mode']}
            for c in WORLD_CATEGORIES
        ]
        guide['step_boundary'] = {
            'responsibility': WORLD_STEP_BOUNDARY['responsibility'],
            'out_of_scope': list(WORLD_STEP_BOUNDARY['out_of_scope']),
        }
    elif domain in ('character_arc', 'cast_entry', 'cast_roster'):
        from nw.studio.character_materials import (
            CHARACTER_CATEGORIES,
            CHARACTER_STEP_BOUNDARY,
            STATIC_RELATIONS_STEP_BOUNDARY,
        )
        guide['character_categories'] = [
            {'id': c['id'], 'target_stage': c['target_stage'], 'name': c['name'], 'usage_mode': c['usage_mode']}
            for c in CHARACTER_CATEGORIES
        ]
        guide['step_boundaries'] = {
            'character_design': {
                'responsibility': CHARACTER_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(CHARACTER_STEP_BOUNDARY['out_of_scope']),
            },
            'static_relations': {
                'responsibility': STATIC_RELATIONS_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(STATIC_RELATIONS_STEP_BOUNDARY['out_of_scope']),
            },
        }
    elif domain in ('main_plot', 'subplot', 'hook', 'foreshadow', 'information', 'chapter_progress'):
        from nw.studio.plot_materials import (
            EVENT_STEP_BOUNDARY,
            PLOT_EVENT_CATEGORIES,
            PLOT_STEP_BOUNDARY,
        )
        guide['plot_event_categories'] = [
            {'id': c['id'], 'slot': c['slot'], 'target_stage': c['target_stage'], 'name': c['name'], 'usage_mode': c['usage_mode']}
            for c in PLOT_EVENT_CATEGORIES
        ]
        guide['step_boundaries'] = {
            'plot_design': {
                'responsibility': PLOT_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(PLOT_STEP_BOUNDARY['out_of_scope']),
            },
            'event_design': {
                'responsibility': EVENT_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(EVENT_STEP_BOUNDARY['out_of_scope']),
            },
        }
    if domain in ('chapter_progress', 'information', 'character_arc', 'world_rules'):
        from nw.studio.execution_materials import (
            ACTION_STEP_BOUNDARY,
            EXECUTION_CATEGORIES,
            SCENE_STEP_BOUNDARY,
            STATE_PROPAGATION_STEP_BOUNDARY,
            STATE_TRANSITION_STEP_BOUNDARY,
        )
        guide['execution_categories'] = [
            {'id': c['id'], 'target_stage': c['target_stage'], 'name': c['name'], 'usage_mode': c['usage_mode']}
            for c in EXECUTION_CATEGORIES
        ]
        guide['execution_step_boundaries'] = {
            'action_design': {
                'responsibility': ACTION_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(ACTION_STEP_BOUNDARY['out_of_scope']),
            },
            'scene_design': {
                'responsibility': SCENE_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(SCENE_STEP_BOUNDARY['out_of_scope']),
            },
            'state_transition': {
                'responsibility': STATE_TRANSITION_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(STATE_TRANSITION_STEP_BOUNDARY['out_of_scope']),
            },
            'state_propagation': {
                'responsibility': STATE_PROPAGATION_STEP_BOUNDARY['responsibility'],
                'out_of_scope': list(STATE_PROPAGATION_STEP_BOUNDARY['out_of_scope']),
            },
        }
    if domain in ('narration', 'pacing'):
        from nw.studio.craft_materials import (
            ACCEPTANCE_STEP_BOUNDARY,
            ANCHOR_STEP_BOUNDARY,
            BIND_SCOPE_STEP_BOUNDARY,
            CRAFT_CATEGORIES,
            EXPRESSION_STEP_BOUNDARY,
            REVIEW_STEP_BOUNDARY,
            WRITER_STEP_BOUNDARY,
        )
        guide['craft_categories'] = [
            {'id': c['id'], 'slot': c['slot'], 'target_stage': c['target_stage'], 'name': c['name'], 'usage_mode': c['usage_mode']}
            for c in CRAFT_CATEGORIES
        ]
        guide['craft_step_boundaries'] = {
            sid: {'responsibility': bnd['responsibility'], 'out_of_scope': list(bnd['out_of_scope'])}
            for sid, bnd in (
                ('anchor_design', ANCHOR_STEP_BOUNDARY),
                ('expression_design', EXPRESSION_STEP_BOUNDARY),
                ('bind_scope', BIND_SCOPE_STEP_BOUNDARY),
                ('writer', WRITER_STEP_BOUNDARY),
                ('review', REVIEW_STEP_BOUNDARY),
                ('acceptance', ACCEPTANCE_STEP_BOUNDARY),
            )
        }
    return guide


def _library_step_coverage(library: Any) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {
        step['step_id']: {'approved_method_count': 0, 'draft_method_count': 0, 'approved_method_ids': []}
        for step in _STEP_SPECS
    }
    if library is None:
        return counts
    rows: list[dict[str, Any]] = []
    offset = 0
    try:
        while True:
            listed = library.list_methods(limit=100, offset=offset)
            batch = listed.get('methods', ())
            rows.extend(batch)
            total = int(listed.get('total', len(rows)))
            if not batch or len(rows) >= total:
                break
            offset += len(batch)
    except Exception:
        return counts
    for row in rows:
        body = row.get('body') or {}
        stages = {out.get('stage') for out in body.get('outputs', ()) if out.get('stage')}
        consumers = {d.get('consumer') for d in body.get('downstream', ()) if d.get('consumer')}
        targets = stages | (consumers & {'writer', 'review', 'acceptance'})
        for step_id in targets:
            if step_id not in counts:
                continue
            if row.get('current_for_production'):
                counts[step_id]['approved_method_count'] += 1
                counts[step_id]['approved_method_ids'].append(row['id'])
            elif row.get('status') in ('draft', 'approved'):
                counts[step_id]['draft_method_count'] += 1
    return counts


def build_step_blueprint(library: Any = None) -> dict[str, Any]:
    """Build the complete 17-step material demand and decomposition blueprint."""
    stats = _workflow_stage_material_stats()
    coverage = _library_step_coverage(library)
    all_techniques = KINDS | CRAFT_KINDS

    steps: list[dict[str, Any]] = []
    for index, spec in enumerate(_STEP_SPECS, start=1):
        step_id = spec['step_id']
        is_design = step_id in ORDER
        matched_tasks = [
            {'id': t['id'], 'name': t['name'], 'purpose': t['purpose'], 'scopes': list(t['scopes'])}
            for t in TASKS.values()
            if step_id in t['stages']
        ]
        fields = sorted(METHOD_FIELDS[step_id]) if is_design else []
        artifacts = {
            field: list(output_artifacts(step_id, field))
            for field in fields
        }
        cov = coverage[step_id]
        cov_status = (
            'covered' if cov['approved_method_count'] > 0
            else 'draft_only' if cov['draft_method_count'] > 0
            else 'gap'
        )
        entry = {
            'order': index,
            'step_id': step_id,
            'name': spec['name'],
            'short_name': STAGES.get(step_id, CONSUMERS.get(step_id, step_id)),
            'phase_group': spec['phase_group'],
            'is_design_stage': is_design,
            'scopes': [s for s in SCOPES if step_id in phase_order(s)] if is_design else ['scene'],
            'hierarchical_scopes': [s for s in SCOPES if step_id in phase_order(s, planning_hierarchy=True)] if is_design else ['scene'],
            'required_prior_steps': list(REQUIRES[step_id]) if is_design else list(EXTERNAL_REQUIRES.get(step_id, ())),
            'material_natures': [
                {'id': nid, 'name': MATERIAL_NATURES[nid]['name']} for nid in spec['material_natures']
            ],
            'need_categories': list(spec['need_categories']),
            'output_fields': [{'id': f, 'label': OUTPUT_LABELS.get(f, f)} for f in fields],
            'output_artifacts': artifacts,
            'method_tasks': matched_tasks,
            'corpus_domains': [
                {'id': d, 'name': DOMAINS[d]} for d in spec['corpus_domains'] if d in DOMAINS
            ],
            'passage_techniques': [
                {'id': k, 'label': all_techniques[k]['label']} for k in spec['passage_techniques'] if k in all_techniques
            ],
            'decomposition_guide': deepcopy(spec['decomposition_guide']),
            'library_coverage': {**cov, 'status': cov_status},
            **stats[step_id],
        }
        if step_id == 'world_design':
            from nw.studio.world_materials import WORLD_CATEGORIES, WORLD_STEP_BOUNDARY
            entry['world_categories'] = deepcopy(list(WORLD_CATEGORIES))
            entry['step_boundary'] = deepcopy(WORLD_STEP_BOUNDARY)
        elif step_id == 'character_design':
            from nw.studio.character_materials import CHARACTER_CATEGORIES, CHARACTER_STEP_BOUNDARY
            entry['character_categories'] = deepcopy([c for c in CHARACTER_CATEGORIES if c['target_stage'] == 'character_design'])
            entry['step_boundary'] = deepcopy(CHARACTER_STEP_BOUNDARY)
        elif step_id == 'static_relations':
            from nw.studio.character_materials import CHARACTER_CATEGORIES, STATIC_RELATIONS_STEP_BOUNDARY
            entry['relation_categories'] = deepcopy([c for c in CHARACTER_CATEGORIES if c['target_stage'] == 'static_relations'])
            entry['step_boundary'] = deepcopy(STATIC_RELATIONS_STEP_BOUNDARY)
        elif step_id == 'plot_design':
            from nw.studio.plot_materials import PLOT_EVENT_CATEGORIES, PLOT_STEP_BOUNDARY
            entry['plot_categories'] = deepcopy([c for c in PLOT_EVENT_CATEGORIES if c['target_stage'] == 'plot_design'])
            entry['step_boundary'] = deepcopy(PLOT_STEP_BOUNDARY)
        elif step_id == 'event_design':
            from nw.studio.plot_materials import EVENT_STEP_BOUNDARY, PLOT_EVENT_CATEGORIES
            entry['event_categories'] = deepcopy([c for c in PLOT_EVENT_CATEGORIES if c['target_stage'] == 'event_design'])
            entry['step_boundary'] = deepcopy(EVENT_STEP_BOUNDARY)
        elif step_id == 'action_design':
            from nw.studio.execution_materials import ACTION_STEP_BOUNDARY, EXECUTION_CATEGORIES
            entry['action_categories'] = deepcopy([c for c in EXECUTION_CATEGORIES if c['target_stage'] == 'action_design'])
            entry['step_boundary'] = deepcopy(ACTION_STEP_BOUNDARY)
        elif step_id == 'scene_design':
            from nw.studio.execution_materials import EXECUTION_CATEGORIES, SCENE_STEP_BOUNDARY
            entry['scene_categories'] = deepcopy([c for c in EXECUTION_CATEGORIES if c['target_stage'] == 'scene_design'])
            entry['step_boundary'] = deepcopy(SCENE_STEP_BOUNDARY)
        elif step_id == 'state_transition':
            from nw.studio.execution_materials import EXECUTION_CATEGORIES, STATE_TRANSITION_STEP_BOUNDARY
            entry['transition_categories'] = deepcopy([c for c in EXECUTION_CATEGORIES if c['target_stage'] == 'state_transition'])
            entry['step_boundary'] = deepcopy(STATE_TRANSITION_STEP_BOUNDARY)
        elif step_id == 'state_propagation':
            from nw.studio.execution_materials import EXECUTION_CATEGORIES, STATE_PROPAGATION_STEP_BOUNDARY
            entry['propagation_categories'] = deepcopy([c for c in EXECUTION_CATEGORIES if c['target_stage'] == 'state_propagation'])
            entry['step_boundary'] = deepcopy(STATE_PROPAGATION_STEP_BOUNDARY)
        elif step_id in ('anchor_design', 'expression_design', 'bind_scope', 'writer', 'review', 'acceptance'):
            from nw.studio.craft_materials import (
                ACCEPTANCE_STEP_BOUNDARY,
                ANCHOR_STEP_BOUNDARY,
                BIND_SCOPE_STEP_BOUNDARY,
                CRAFT_CATEGORIES,
                EXPRESSION_STEP_BOUNDARY,
                REVIEW_STEP_BOUNDARY,
                WRITER_STEP_BOUNDARY,
            )
            craft_map = {
                'anchor_design': ('anchor_categories', ANCHOR_STEP_BOUNDARY),
                'expression_design': ('expression_categories', EXPRESSION_STEP_BOUNDARY),
                'bind_scope': ('bind_scope_categories', BIND_SCOPE_STEP_BOUNDARY),
                'writer': ('writer_categories', WRITER_STEP_BOUNDARY),
                'review': ('review_categories', REVIEW_STEP_BOUNDARY),
                'acceptance': ('acceptance_categories', ACCEPTANCE_STEP_BOUNDARY),
            }
            cat_key, bnd = craft_map[step_id]
            entry[cat_key] = deepcopy([c for c in CRAFT_CATEGORIES if c['target_stage'] == step_id])
            entry['step_boundary'] = deepcopy(bnd)
        steps.append(entry)

    from nw.materials.creative_workflow import workflow_overview
    return {
        'schema_version': 1,
        'creative_workflow': workflow_overview(),
        'methodology': deepcopy(DECOMPOSITION_METHODOLOGY),
        'material_natures': list(deepcopy(MATERIAL_NATURES).values()),
        'steps': steps,
        'domain_bindings': domain_bindings(),
        'summary': {
            'total_steps': len(steps),
            'design_steps': len(ORDER),
            'execution_steps': len(steps) - len(ORDER),
            'covered_steps': sum(1 for row in steps if row['library_coverage']['status'] == 'covered'),
            'gap_steps': [row['step_id'] for row in steps if row['library_coverage']['status'] == 'gap'],
        },
    }
