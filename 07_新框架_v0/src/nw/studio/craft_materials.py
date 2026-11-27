"""Genre-targeted material taxonomy, step boundaries, and coverage for 12–17 craft & closure stages.

Covers the final expression, binding, writing, review, and acceptance chain directly aligned with:
  - 12 anchor_design (`anchor_design*.py`)
  - 13 expression_design (`expression_design*.py`, including Wizard `narration`/`tone`/`style` slots)
  - 14 bind_scope (`bind_scope*.py`)
  - 15 writer (`writing*.py`)
  - 16 review (`review*.py`)
  - 17 acceptance (`state_extract.py`)

Design goals:
  1. Classify 12–17 original workflow materials into 12 bounded, non-overlapping sub-categories
     explicitly bound to their owning stage and Wizard craft slots (`narration`, `tone`, `style`).
  2. Provide item-level genre relevance ranking & cross-genre isolation for all 10 `TONE_*`
     and 20 `STYLE_*` items across all 35 main genres without altering any canonical ID or
     `source_ref.original_line`, keeping `creation_plan` and `creation_preferences` 100% intact.
  3. Enforce strict inter-step handoff boundaries along 12 → 13 → 14 → 15 → 16 → 17 so
     anchors bind real upstream actions/propagations, expression resolves competing preferences
     without inventing plot facts, bind_scope consolidates scene guidance cleanly, writer obeys
     POV/disclosure contracts, review checks independent prose quotes, and acceptance isolates
     subjective character claims from verified WORLD facts.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.studio.catalog import canonical_types, type_map


ANCHOR_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'anchor_design',
    'step_name': '12. 具象锚点与身体节拍',
    'responsibility': (
        '仅在卷/章/场细化运行：承接 08 行动步骤、09 场景 POV 与空间、10 状态/代价变化及 11 条件传播候选，'
        '将抽象情绪、状态位移与身份线索落为当前 POV 观察者可感知的具象身体微反应、物件交互、镜头节拍与氛围锚点（beats），'
        '并显式决定本场是否启用某条上游传播候选（selected_propagations）。'
    ),
    'upstream_steps': [
        {'step_id': 'action_design', 'supplies': '行动候选 steps（供 action_ref / step_index / timing 精准挂载）'},
        {'step_id': 'scene_design', 'supplies': '本场 POV 观察者、在场对象、空间方位与 selected_actions'},
        {'step_id': 'state_transition', 'supplies': '本场状态变化、不可逆代价与情绪波动'},
        {'step_id': 'state_propagation', 'supplies': '带三门守卫的条件传播候选供本场决定是否选用'},
    ],
    'produces': [
        'beats（scene/observer/object/action/observable/check，锚点资料另含 action_ref/step_index/timing/trigger_basis）',
        'selected_propagations（本场确实采纳的上游传播候选 ID；未选者自动保留为后续预案）',
    ],
    'downstream_steps': [
        {'step_id': 'expression_design', 'consumes': '承接可见节拍与选定传播，组织叙述时序、距离、对白潜台词与文风'},
        {'step_id': 'bind_scope', 'consumes': '汇总已用锚点方法与本场可验证表现'},
        {'step_id': 'writer', 'consumes': '按 before/during/after 节拍把抽象情绪写成具象动作与感官细节'},
    ],
    'out_of_scope': [
        '禁止使用非本场 POV 人物作为 observer，禁止把未在场或超出感知范围的细节冒充可见锚点。',
        '禁止只贴抽象锚点标签或绑定无关动作（须准确对应本场 selected_actions 的 action_ref 与 step_index）。',
        '禁止强行在本场触发全部 11 步传播候选，也禁止在本步直接撰写 15 步正文段落或新增未立项剧情事实。',
    ],
}


EXPRESSION_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'expression_design',
    'step_name': '13. 叙述距离与表达设计',
    'responsibility': (
        '仅在卷/章/场细化运行：承接 09 场景披露边界、12 具象节拍、作者选定的写法/语气/文风偏好及段落技法，'
        '为每场输出可落笔、可核验的表达指导（guidance：observable + check），协调互相竞争的语气/文风偏好'
        '（preference_resolutions），并按需编排 passage_sequences 与 craft_applications。'
    ),
    'upstream_steps': [
        {'step_id': 'scene_design', 'supplies': 'POV 权限、allowed_disclosure、情绪密度与选定段落技法'},
        {'step_id': 'anchor_design', 'supplies': '具象动作/感官/物件节拍（beats）与本场采纳的传播'},
        {'step_id': 'character_design', 'supplies': '各角色专属声线、说话风格与三层外化习惯'},
    ],
    'produces': [
        'guidance（scene/observable/check，写清动作、情绪、对白、叙述距离与信息披露落点）',
        'preference_resolutions（互相竞争的语气/文风立项偏好须分别落至不重叠的 /guidance/序号/observable 或明确延后）',
        'passage_sequences / situated_beats / people_design / effects_plan / craft_applications（启用段落技法时）',
    ],
    'downstream_steps': [
        {'step_id': 'bind_scope', 'consumes': '校验方法落场并与写作指导对齐'},
        {'step_id': 'writer', 'consumes': '作为单场正文落笔的语体、距离、节奏与对话潜台词蓝图'},
        {'step_id': 'review', 'consumes': '逐条对照 guidance.check 核验正文表现是否真实达标'},
    ],
    'out_of_scope': [
        '禁止违背 09 allowed_disclosure 泄露未披露信息，禁止替 10 步篡改前后状态或替 06/07 步发明新剧情事实。',
        '禁止把互斥或竞争的语气/文风偏好叠写到同一条 /guidance/序号/observable 而不加协调说明。',
        '禁止在本步直接输出完整 15 步正文散文，也禁止将“风格标签口号”充当具体 observable 表现。',
    ],
}


BIND_SCOPE_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'bind_scope',
    'step_name': '14. 范围绑定与检验收口',
    'responsibility': (
        '全书收口（第 7 步）与细化收口（第 14 步）运行：按三层精准筛选与数据传递完整性规则，'
        '汇总本范围所有已采用资料与拆解方法的实际绑定（material_bindings / process_bindings），'
        '在章/场细化阶段为每项落场方法生成供 15 写手与 16 审稿核对的 method_guidance（observable + check）。'
    ),
    'upstream_steps': [
        {'step_id': 'world_design', 'supplies': '已启用世界卡与规则限制绑定目标'},
        {'step_id': 'character_design', 'supplies': '已确立人物卡与阵容职责分派'},
        {'step_id': 'plot_design', 'supplies': '已定剧情/伏笔卡与事件节点'},
        {'step_id': 'expression_design', 'supplies': '各场景可写表达指导与段落技法应用'},
    ],
    'produces': [
        'material_bindings（按 binding_contract 绑定实际项目成员）',
        'process_bindings（按 binding_contract 绑定实际设计过程）',
        'method_guidance（章/场细化：每场已用 source_ids 的 POV 可见表现 observable 与原义审稿判据 check；全书/卷纲必须为空数组）',
    ],
    'downstream_steps': [
        {'step_id': 'writer', 'consumes': '按 method_guidance 在对应场景写出可核查正文表现'},
        {'step_id': 'review', 'consumes': '逐条核对 method_guidance.check 是否在正文中有精确引文支撑'},
        {'step_id': 'acceptance', 'consumes': '按绑定范围校验状态提交与未采纳候选的排除记录'},
    ],
    'out_of_scope': [
        '禁止在本步改写上游 01–13 已确认的世界规则、人物设定、事件因果或场景设计。',
        '全书（book）与卷纲（volume）范围没有实际场景，method_guidance 必须为空数组，严禁越界伪造场景绑定。',
        '禁止把未读或已排除资料强行塞入 method_guidance，也禁止给仅绑定特定场景的资料随意扩散到无关场景。',
    ],
}


WRITER_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'writer',
    'step_name': '15. 正文写作与修订',
    'responsibility': (
        '严格承接 09 场景卡、12 具象节拍、13 表达指导与 14 method_guidance，在冻结的已接受事实与受限 POV 边界内撰写或修订场景正文：'
        '控制句长比例与精确动词，禁用无因/巧合套词，首出场落实外貌剪影与嗓音特征，将代价、冲突与情绪通过感官与动作具象落文。'
    ),
    'upstream_steps': [
        {'step_id': 'scene_design', 'supplies': '受限 POV、在场人员、空间方位与 allowed_disclosure 边界'},
        {'step_id': 'anchor_design', 'supplies': 'before/during/after 具象身体与物件节拍'},
        {'step_id': 'expression_design', 'supplies': '语体距离、对话潜台词、节奏密度与段落技法'},
        {'step_id': 'bind_scope', 'supplies': '本场必查 method_guidance.observable 清单'},
    ],
    'produces': [
        '场景草稿（scene_draft，带完整 story_write_manifest 溯源与版本留痕）',
        '面向审稿退回意见的定向修订稿（revise_draft）',
    ],
    'downstream_steps': [
        {'step_id': 'review', 'consumes': '独立逐段核查正文引文、视角一致性、方法落实与语体连续性'},
        {'step_id': 'acceptance', 'consumes': '仅从审稿通过的正文精确区间提取状态增量'},
    ],
    'out_of_scope': [
        '禁止泄露 allowed_disclosure 以外的暗身份或未目击信息，禁止在场内中途无依据切视角。',
        '禁止用抽象总结词（如“他心想”“他意识到”“突然巧合”）替代具象动作与因果铺垫。',
        '禁止擅自改写已接受 WORLD 事实、跳过未触发的事件完成门或把下章情节提前写完。',
    ],
}


REVIEW_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'review',
    'step_name': '16. 独立审稿与证据核验',
    'responsibility': (
        '独立于写手身份执行多维核验：逐条对照 14 method_guidance.check 与正文精确引文，检查场景因果与不可逆性、'
        '视角一致性、语言禁词（如“他心想/意识到”）、对话潜台词、跨章语体统一、世界/时间线/伏笔一致性与原创性防雷同。'
    ),
    'upstream_steps': [
        {'step_id': 'writer', 'supplies': '待审场景正文草稿'},
        {'step_id': 'bind_scope', 'supplies': '逐条方法审稿判据（check）与绑定范围'},
        {'step_id': 'expression_design', 'supplies': '场景表达效果判据与偏好协调记录'},
    ],
    'produces': [
        '独立审稿结论（pass / revise）及定位到正文具体段落的问题证据清单',
        '方法/资料验收核验记录（material_review / method_review）',
    ],
    'downstream_steps': [
        {'step_id': 'writer', 'consumes': '未通过时按审稿定位缺陷定向修订正文'},
        {'step_id': 'acceptance', 'consumes': '审稿与材料核验均通过后方允许进入批次状态接受'},
    ],
    'out_of_scope': [
        '禁止用“计划书里写了”或关键词命中代替正文实际可引用段落的独立验证。',
        '禁止放行视角越界、信息偷跑、未目击人物改判或无代价跳过阻碍的草稿。',
        '禁止绕过独立审稿直接批准手写/生成草稿入库，也禁止替写手直接改写原稿覆盖版本历史。',
    ],
}


ACCEPTANCE_STEP_BOUNDARY: dict[str, Any] = {
    'step_id': 'acceptance',
    'step_name': '17. 状态提取、事实复核与批次接受',
    'responsibility': (
        '以审稿通过的正文精确字符区间为唯一事实依据，提取真实发生的状态增量（state_delta），'
        '严格隔离“叙述确证事实（WORLD）”与“人物主观说法/推测（attributed/inferred）”，'
        '追踪道具状态一致与代价累积不消失，经事实复核后执行批次原子接受并推进主线/分支版本。'
    ),
    'upstream_steps': [
        {'step_id': 'writer', 'supplies': '审稿通过的最终场景正文'},
        {'step_id': 'review', 'supplies': '独立审稿与材料核验通过凭据'},
        {'step_id': 'state_transition', 'supplies': '计划内状态迁移、代价延续与失败预案对照基线'},
    ],
    'produces': [
        '带正文精确偏移引文的 state_delta 与独立 fact_review 复核结论',
        '原子批次提交后的最新 accepted_state（作为下一章/下一卷的冻结事实起点）',
    ],
    'downstream_steps': [
        {'step_id': 'plot_design', 'consumes': '下一章承接本场已接受状态、未决遗留问题（continuations）与伏笔进度'},
        {'step_id': 'action_design', 'consumes': '以更新后的 accepted_state 核验下轮资源、伤势与可用能力'},
        {'step_id': 'state_propagation', 'consumes': '以新沉淀的 accepted_fact 作为后续跨实体传播根变化'},
    ],
    'out_of_scope': [
        '禁止录入没有正文精确引文支撑的脑补事实，禁止将人物口头谎言/推测直接写为 WORLD 客观事实。',
        '禁止在缺少审稿或材料核验的情况下强行放行批次接受，或静默清零历史累积代价。',
        '禁止在批次提交时跨分支混用或覆盖未选分支的已接受修订链。',
    ],
}


# 12 bounded, non-overlapping craft & closure sub-categories across 12–17.
CRAFT_CATEGORIES: tuple[dict[str, Any], ...] = (
    # ---- 12 anchor_design (2 categories) ----
    {
        'id': 'anchor_body_camera',
        'slot': 'narration',
        'target_stage': 'anchor_design',
        'target_stage_label': '12 锚点设计',
        'name': '身体微反应、镜头聚焦、氛围与脉搏/呼吸锚点',
        'short_name': '身体镜头与氛围锚点',
        'description': '覆盖身体情绪微反应（B2/B3）、视觉/听觉/近景/特写/主观/定格镜头（板块52/60）、他人视角人格锚点（板块147）、氛围映射与突变（110.2/4/8）、场景脉搏/呼吸点（板块46/148）、时间锚点（113.5）及切视角前置锚点（120.20）。',
        'usage_mode': '12 锚点设计核心表现域：把抽象情绪与节奏停顿落到 POV 观察者当场可见的动作、感官与镜头节拍。',
        'source_files': [
            'anchor_design_body_emotion.py (B2/B3 47 项)',
            'anchor_design_viewpoint.py (板块52/60/147)',
            'anchor_design_atmosphere.py (§110.2/4/8)',
            'anchor_design_scene.py (板块46/148)',
            'anchor_design_timeline.py (§113.5)',
            'anchor_design_multi_viewpoint.py (§120.20)',
        ],
        'catalog_group_keys': ('narration.group.anchor_beats',),
        'keywords': (
            '锚点', '身体反应', '微表情', '特写镜头', '近景镜头', '主观镜头', '定格', '脉搏点', '呼吸点',
            '时间锚点', '氛围映射', '氛围突变', '人格锚点', '可见节拍', 'beats', '感官锚点',
        ),
    },
    {
        'id': 'anchor_prop_propagation',
        'slot': None,
        'target_stage': 'anchor_design',
        'target_stage_label': '12 锚点设计',
        'name': '道具交互、能力边界观测与传播候选落场',
        'short_name': '道具动作锚点与传播落场',
        'description': '覆盖道具与角色交互可见节拍（29.1）、能力边界外显观测（38.3）、动作步骤 before/during/after 绑定（action_ref/step_index）及显式选用 11 步状态传播候选（selected_propagations）。',
        'usage_mode': '12 锚点设计因果接力域：确保每条动作与采纳传播都在本场有可观察物证或动作节拍，未选传播保留预案。',
        'source_files': [
            'anchor_design.py (§29.1, §38.3)',
            'anchor_design_anchor_network*.py',
        ],
        'catalog_group_keys': (),
        'keywords': (
            '道具交互', '能力边界', 'action_ref', 'step_index', 'selected_propagations', '传播落场',
            '蓄力节拍', '触发依据', '物件锚点', '可观察依据',
        ),
    },
    # ---- 13 expression_design (6 categories, directly wired to narration / tone / style slots) ----
    {
        'id': 'expr_narrator_voice',
        'slot': 'narration',
        'target_stage': 'expression_design',
        'target_stage_label': '09/13 叙述声音',
        'name': '叙述者可信度、声音距离与干预程度',
        'short_name': '叙述声音与距离',
        'description': '覆盖叙述者可信度（109.2）、叙述者与读者距离（109.3）、叙述者声音质感（109.5）与叙述干预程度（109.7）。',
        'usage_mode': '13 表达设计叙述主控域（同步作用于 09 视角边界）：决定叙述声音贴近人物还是冷峻克制，以及读者能否完全轻信叙述者。',
        'source_files': ['expression_design_narrator.py (§109.2/3/5/7)'],
        'catalog_group_keys': ('narration.group.expression_design_narrator',),
        'keywords': (
            '叙述者可信度', '不可靠叙述', '叙述距离', '叙述者声音', '叙述干预', '声音质感', '零度叙述',
        ),
    },
    {
        'id': 'expr_viewpoint_boundary',
        'slot': 'narration',
        'target_stage': 'expression_design',
        'target_stage_label': '09/13 视角边界',
        'name': '叙述者形态、知识边界与主角关系',
        'short_name': '视角形态与知识边界',
        'description': '覆盖第一/二/三人称有限与全知叙述者类型（109.1）、叙述者知识边界（109.6）、叙述者演变（109.8）及叙述者与主角关系（109.9）。',
        'usage_mode': '09 场景与 13 表达共用边界域：严格限定每场“谁在讲、能知道多少、何时扩展边界”，防止全知串味。',
        'source_files': ['scene_design_narrator.py (§109.1/6/8/9)'],
        'catalog_group_keys': ('narration.group.scene_design_narrator',),
        'keywords': (
            '第一人称', '第三人称有限', '全知叙述', '知识边界', '限知', '叙述者变化', '叙述者与主角关系',
        ),
    },
    {
        'id': 'expr_timeline_disclosure',
        'slot': 'narration',
        'target_stage': 'expression_design',
        'target_stage_label': '09/13 时序与披露',
        'name': '叙述时序、速度、回忆插叙与信息释放方式',
        'short_name': '叙述时序与信息释放',
        'description': '覆盖顺叙/插叙/倒叙/先果后因与回落当下（expression_design_timeline.py）、时间压缩与展开以及信息释放的具体呈现方式（116.7）。',
        'usage_mode': '13 表达设计节奏编排域：区分故事发生顺序与文本讲述顺序，安排读者在具体哪一句更新判断。',
        'source_files': [
            'expression_design_timeline.py',
            'expression_design_disclosure.py (§116.7)',
        ],
        'catalog_group_keys': (
            'narration.group.expression_design_timeline',
            'narration.group.expression_design_disclosure',
        ),
        'keywords': (
            '叙述时序', '顺叙', '插叙', '倒叙', '先果后因', '回忆', '时间压缩', '信息释放方式', '讲述顺序', '段落技法',
        ),
    },
    {
        'id': 'expr_dialogue_sensory',
        'slot': 'narration',
        'target_stage': 'expression_design',
        'target_stage_label': '13 对白感官与氛围',
        'name': '潜台词对白技术、五感距离、语言质感与氛围语体统一',
        'short_name': '对白潜台词与感官氛围',
        'description': '覆盖潜台词/非直接回答/非台词元素/对话速度与口吻一致（板块56–57）、五感描写/近中远叙述距离/快中慢语言质感与音律陌生化（板块52–55）、场景氛围渐变与主题连接（110.*）及全篇语体一致性（106.1–106.3）。',
        'usage_mode': '13 表达设计核心落笔指导域：把角色交锋、空间氛围与段落长短句节奏转化为可直接供 15 写手执行的 guidance。',
        'source_files': [
            'expression_design_dialogue.py (板块56–57)',
            'expression_design_sensory.py (板块52–55)',
            'expression_design_atmosphere.py (§110.1–110.7, §161.1)',
            'expression_design_continuity.py (§106.1–106.3)',
            'expression_design_application.py (§127.8–127.17)',
        ],
        'catalog_group_keys': (
            'narration.group.dialogue_subtext',
            'narration.group.sensory_atmosphere',
        ),
        'keywords': (
            '潜台词', '非直接回答', '非台词元素', '对话技术', '说话风格', '五感', '近距离叙述', '远距离叙述',
            '快节奏场景语言', '慢节奏场景语言', '语言陌生化', '音律', '场景氛围', '语言风格统一', 'guidance', '表达指导',
        ),
    },
    {
        'id': 'expr_tone_matrix',
        'slot': 'tone',
        'target_stage': 'expression_design',
        'target_stage_label': '13 语气基调',
        'name': '语气基调适配（10 类标准语气）',
        'short_name': '语气基调适配',
        'description': '覆盖严肃、轻松、幽默、黑暗、温暖、冷峻、讽刺、史诗、亲密、疏离 10 类标准语气；按所选小说主副类型自动排序核心项并隔离跨题材语气。',
        'usage_mode': '13 表达设计语气标尺：按当前说话人与场景落点措辞，多种竞争语气须经 preference_resolutions 分配至不同节拍。',
        'source_files': ['expression_design_type_tones.py (10 类 TONE_*)'],
        'catalog_group_keys': ('tone.group.types',),
        'keywords': (
            '严肃语气', '轻松语气', '幽默语气', '黑暗语气', '温暖语气', '冷峻语气', '讽刺语气', '史诗语气', '亲密语气', '疏离语气', '语气基调',
        ),
    },
    {
        'id': 'expr_style_matrix',
        'slot': 'style',
        'target_stage': 'expression_design',
        'target_stage_label': '13 文风质感',
        'name': '文风与语言质感适配（20 类标准风格）',
        'short_name': '文风与语言质感',
        'description': '覆盖现实主义、幻想、史诗、黑暗、轻松、幽默、严肃、写实、诗意、动作、悬疑、恐怖、浪漫、成长、群像、谋略、温暖、冷峻、快节奏、慢节奏 20 类标准风格；按所选主副类型自动分层隔离。',
        'usage_mode': '13 表达设计文风标尺：落实为具体句式、感官与节奏指导；竞争风格（如轻松 vs 写实）须在 preference_resolutions 明确各自落场。',
        'source_files': ['expression_design_type_styles.py (20 类 STYLE_*)'],
        'catalog_group_keys': ('style.group.types',),
        'keywords': (
            '现实主义风格', '幻想风格', '史诗风格', '写实风格', '诗意风格', '动作风格', '悬疑风格', '恐怖风格',
            '浪漫风格', '谋略风格', '冷峻风格', '快节奏风格', '慢节奏风格', '文风', '语言质感',
        ),
    },
    # ---- 14 bind_scope (1 category) ----
    {
        'id': 'bind_scope_contract',
        'slot': None,
        'target_stage': 'bind_scope',
        'target_stage_label': '14 绑定汇总',
        'name': '三层精准筛选、来源标签与方法落场收口',
        'short_name': '绑定收口与写审交接',
        'description': '覆盖规划师自检与三阶段数据传递完整性（板块87/90）、三层精准筛选与调用量控制（126.*/128.*）、设计转应用三步法（127.1–127.7）、5 类来源标签（SOURCE_*）及 scene 级 method_guidance 汇总。',
        'usage_mode': '14 绑定汇总收口域：确保每条启用方法都有明确落场 observable 与审稿 check，且绝不改写上游设计。',
        'source_files': [
            'bind_scope_workflow.py (板块87/90)',
            'bind_scope_selection.py (§126.*/§128.*)',
            'bind_scope_application.py (§127.1–127.7)',
            'bind_scope_source_tags.py (SOURCE_*)',
        ],
        'catalog_group_keys': (),
        'keywords': (
            '绑定汇总', 'method_guidance', 'material_bindings', 'process_bindings', '三层筛选', '精准调用',
            '规划师→写手', '数据传递完整性', '来源标签', '范围收口', '验收交接',
        ),
    },
    # ---- 15 writer (1 category) ----
    {
        'id': 'writer_craft_execution',
        'slot': None,
        'target_stage': 'writer',
        'target_stage_label': '15 正文写作',
        'name': '受限 POV 落笔、句式精确动词、首尾句与代价可视化正文执行',
        'short_name': '正文落笔与修订执行',
        'description': '覆盖写手输入输出自查（板块88/108.1–108.2）、句长比例/短句时机/精确动词/禁用无因巧合词（板块49–51）、受限视角与配角 POV 前 500 字规则（板块58–59/120.*）、首句/尾句与结尾余波（112.*）及代价可视化（118.7/118.9）。',
        'usage_mode': '15 正文写作执行域：把 09–14 冻结设计与锚点节拍落成真实连贯的文学段落，严守受限视角与已接受事实边界。',
        'source_files': [
            'writing_workflow.py (板块88/90, §108.1–108.2)',
            'writing_language.py (板块49–51)',
            'writing_viewpoint.py & writing_multi_viewpoint.py (板块58–59, §120.*)',
            'writing_opening_ending.py (§112.*)',
            'writing_disclosure_costs.py (§118.7/118.9)',
            'writing_sensory.py & writing_perception_anchors.py',
        ],
        'catalog_group_keys': (),
        'keywords': (
            '正文写作', '精确动词', '句长比例', '短句', '禁用无因词', '第一句话', '最后一句话', '结尾余波',
            '配角POV前500字', '代价可视化', '写手自查', '段落承接', '人物首出场描写',
        ),
    },
    # ---- 16 review (1 category) ----
    {
        'id': 'review_independent_evidence',
        'slot': None,
        'target_stage': 'review',
        'target_stage_label': '16 独立审稿',
        'name': '独立编辑核验、语言视角红线与跨章一致性复核',
        'short_name': '独立审稿与引文核验',
        'description': '覆盖编辑核查与最小修改原则（板块89/90）、禁止“他心想/他意识到”与潜台词检查（板块94–95）、场景节奏/因果/结局不可逆/视角一致（板块91–92）、角色/世界/时间线/伏笔一致性（板块93/97/98、103.*/104.*）及原创性防雷同检查。',
        'usage_mode': '16 独立审稿红线域：以正文精确引文为唯一凭据，逐条验证方法 check 与红线守卫，杜绝口头宣称过关。',
        'source_files': [
            'review_workflow.py (板块89/90)',
            'review_language_checks.py (板块94–95)',
            'review_scene_checks.py (板块91–92)',
            'review_scope_continuity_checks.py (板块93/97/98)',
            'review_scope_rules.py (§103.*/§104.*)',
            'review_type_originality.py',
        ],
        'catalog_group_keys': (),
        'keywords': (
            '独立审稿', '禁止他心想', '禁止他意识到', '场景结局不可逆', '视角一致性', '时间线一致性',
            '伏笔一致性', '世界观一致性', '编辑模式', '正文引文核验', '原创性检查', '方法验收',
        ),
    },
    # ---- 17 acceptance (1 category) ----
    {
        'id': 'acceptance_state_evidence',
        'slot': None,
        'target_stage': 'acceptance',
        'target_stage_label': '17 状态验收',
        'name': '正文偏移状态增量提取、主客观事实隔离与批次原子验收',
        'short_name': '状态提取与批次验收',
        'description': '覆盖写作后检查（108.3）、状态追踪表（9.5）、道具状态一致（107.3）、代价累积不消失（118.1–118.2）、背景身份核验（板块151）、正文偏移引文支撑的 state_delta 与 WORLD/人物说法隔离。',
        'usage_mode': '17 状态验收闭环域：仅将有审稿通过与正文精确区间佐证的变化写入 WORLD 事实，保障跨章与分支连续演进。',
        'source_files': [
            'state_extract.py (板块151, §9.5, §107.3, §108.3, §118.1–118.2)',
        ],
        'catalog_group_keys': (),
        'keywords': (
            '状态提取', 'state_delta', '事实复核', 'fact_review', '批次接受', '状态追踪表', '客观事实',
            '人物说法隔离', 'stated', 'attributed', 'inferred', '写作后检查', '分支提升',
        ),
    },
)

CRAFT_CATEGORY_MAP: dict[str, dict[str, Any]] = {c['id']: c for c in CRAFT_CATEGORIES}
CRAFT_CATEGORY_ORDER: dict[str, int] = {c['id']: i for i, c in enumerate(CRAFT_CATEGORIES)}

RELEVANCE_RANK = {'primary': 0, 'optional': 1, 'out_of_scope': 2}
RELEVANCE_LABELS = {
    'primary': '本类型核心',
    'optional': '按需扩展',
    'out_of_scope': '非本类型常规项',
}

ALL_CRAFT_CAT_IDS = tuple(c['id'] for c in CRAFT_CATEGORIES)


def _cprofile(
    *,
    preferred_tones: tuple[str, ...],
    optional_tones: tuple[str, ...],
    preferred_styles: tuple[str, ...],
    optional_styles: tuple[str, ...],
    anchor_focus: str,
    expression_focus: str,
    writer_review_focus: str,
    acceptance_focus: str,
    decomposition_focus: str,
) -> dict[str, Any]:
    return {
        'primary': ALL_CRAFT_CAT_IDS,
        'optional': (),
        'preferred_tones': preferred_tones,
        'optional_tones': optional_tones,
        'preferred_styles': preferred_styles,
        'optional_styles': optional_styles,
        'craft_profile': {
            'anchor_focus': anchor_focus,
            'expression_focus': expression_focus,
            'writer_review_focus': writer_review_focus,
            'acceptance_focus': acceptance_focus,
        },
        'decomposition_focus': decomposition_focus,
    }


DEFAULT_CRAFT_PROFILE = _cprofile(
    preferred_tones=('TONE_SERIOUS', 'TONE_WARM', 'TONE_COLD', 'TONE_LIGHT'),
    optional_tones=('TONE_HUMOROUS', 'TONE_DARK', 'TONE_SATIRICAL', 'TONE_EPIC', 'TONE_INTIMATE', 'TONE_DISTANT'),
    preferred_styles=('STYLE_REALISTIC', 'STYLE_GROWTH', 'STYLE_FAST', 'STYLE_SUSPENSE'),
    optional_styles=('STYLE_GRITTY', 'STYLE_WARM', 'STYLE_COLD', 'STYLE_STRATEGIC', 'STYLE_ACTION', 'STYLE_LIGHT', 'STYLE_SERIOUS', 'STYLE_SLOW', 'STYLE_GROUP'),
    anchor_focus='以 POV 观察者可感知的动作细节、物件变化、身体微反应与脉搏/呼吸点落实上游事件与代价。',
    expression_focus='统一叙述距离、对话潜台词与快中慢语言质感，确保互相竞争的风格/语气落到各自独立场景节拍。',
    writer_review_focus='正文严守受限视角、精准动词与首尾句控制；独立审稿逐条核对 method_guidance 判据与正文引文。',
    acceptance_focus='仅凭审稿通过的正文精确区间提取状态增量，隔离人物说法与客观 WORLD 事实并保持代价累积。',
    decomposition_focus='重点拆解段落连续承接（narration/passage_sequence）、感官与空间具象锚点、对话潜台词及正文前后事实证据口径。',
)


# Covers ALL 35 main genres from nw.studio.catalog.genres().
GENRE_CRAFT_PROFILES: dict[str, dict[str, Any]] = {
    'GENRE_XUANHUAN': _cprofile(
        preferred_tones=('TONE_EPIC', 'TONE_SERIOUS', 'TONE_COLD', 'TONE_LIGHT'),
        optional_tones=('TONE_DARK', 'TONE_HUMOROUS', 'TONE_WARM'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_ACTION', 'STYLE_EPIC', 'STYLE_FAST', 'STYLE_GROWTH'),
        optional_styles=('STYLE_STRATEGIC', 'STYLE_DARK', 'STYLE_COLD', 'STYLE_GROUP', 'STYLE_HUMOROUS'),
        anchor_focus='强化斗法蓄力/出招/反噬的身体与兵刃物件特写、灵压氛围突变及突破时刻的脉搏点。',
        expression_focus='战斗段用高密度短句与精确动词加速，筹备与战后盘点放缓呼吸，兼顾热血爽感与代价可视化。',
        writer_review_focus='严查打斗招式因果、灵力/伤势代价是否落入正文，防止空喊口号或跳过受阻回合直出胜果。',
        acceptance_focus='精准提取境界、灵宝归属、伤势反噬与宗门立场变化，区分旁观者惊叹推测与真实战力事实。',
        decomposition_focus='重点拆解高燃战斗段落的短句加速、蓄力→爆发→旁观震慑三拍节拍与战利品/代价落笔方式。',
    ),
    'GENRE_QIHUAN': _cprofile(
        preferred_tones=('TONE_EPIC', 'TONE_SERIOUS', 'TONE_DARK', 'TONE_WARM'),
        optional_tones=('TONE_COLD', 'TONE_DISTANT', 'TONE_LIGHT', 'TONE_HUMOROUS'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_EPIC', 'STYLE_GROUP', 'STYLE_ACTION', 'STYLE_GROWTH'),
        optional_styles=('STYLE_DARK', 'STYLE_POETIC', 'STYLE_STRATEGIC', 'STYLE_SLOW', 'STYLE_GRITTY'),
        anchor_focus='突出宏大异域空间五感、魔法/遗迹异常物件锚点与多 POV 切换前的声音/意象交接锚点。',
        expression_focus='平衡史诗远景与近距离角色感受，不同种族与阶层须保持鲜明对话声线与语体辨识度。',
        writer_review_focus='重点核查多视角切换时的信息补偿与读者重置成本，确保异界设定半透明融入动作而非堆砌说明文。',
        acceptance_focus='同步追踪远征物资、同盟誓约、多线时间坐标与古史真相揭示（区分传说说法与已证实史实）。',
        decomposition_focus='重点拆解多视角切换锚点、异域环境五感建构、史诗对话质感与长线世界观半透明渗透写法。',
    ),
    'GENRE_XIANXIA': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_COLD', 'TONE_EPIC', 'TONE_DISTANT'),
        optional_tones=('TONE_WARM', 'TONE_DARK', 'TONE_LIGHT'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_POETIC', 'STYLE_EPIC', 'STYLE_STRATEGIC', 'STYLE_GROWTH'),
        optional_styles=('STYLE_ACTION', 'STYLE_COLD', 'STYLE_SLOW', 'STYLE_SERIOUS', 'STYLE_SUSPENSE'),
        anchor_focus='善用古典意象、神识探查边界的微小异动、丹器法阵细节与情绪克制下的身体微反应锚点。',
        expression_focus='雅致凝练不晦涩，重对白潜台词与礼数机锋，斗法写清虚实算计，静修段留足空隙与余韵。',
        writer_review_focus='严查文白夹杂是否统一、角色口吻是否符合辈分身份，禁止用现代网梗破坏仙侠整体语体一致性。',
        acceptance_focus='严格记录寿元、修为瓶颈、灵材耗损、心魔与人情因果账，隔离传闻秘辛与亲历证实事实。',
        decomposition_focus='重点拆解古典意境营造、表面客套下的杀机潜台词、长线修炼节奏留白与斗法算计落笔。',
    ),
    'GENRE_WUXIA': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_COLD', 'TONE_WARM', 'TONE_EPIC'),
        optional_tones=('TONE_DARK', 'TONE_HUMOROUS', 'TONE_SATIRICAL'),
        preferred_styles=('STYLE_ACTION', 'STYLE_POETIC', 'STYLE_GRITTY', 'STYLE_SERIOUS', 'STYLE_GROWTH'),
        optional_styles=('STYLE_STRATEGIC', 'STYLE_SUSPENSE', 'STYLE_COLD', 'STYLE_GROUP', 'STYLE_ROMANTIC'),
        anchor_focus='紧扣兵器锋芒、酒馆山道风声光影、出招前身法重心微动与侠义克制时的脉搏停顿。',
        expression_focus='行文利落有骨力，招式描写重意境与破绽因果而非冗长说明书，对话重江湖切口与言外之意。',
        writer_review_focus='核查招式空间距离与内伤限制是否一贯，防止语言浮夸堆砌形容词而缺乏精确动词。',
        acceptance_focus='准确沉淀内伤毒素、兵器损毁、江湖名声与恩怨诺言变化，严分江湖流言与当场目击事实。',
        decomposition_focus='重点拆解江湖氛围速写、静极而动的比武节拍、侠客对白留白与道义抉择时的情绪张力。',
    ),
    'GENRE_DUSHI': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_SERIOUS', 'TONE_HUMOROUS', 'TONE_WARM'),
        optional_tones=('TONE_COLD', 'TONE_SATIRICAL', 'TONE_INTIMATE'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_FAST', 'STYLE_GROWTH', 'STYLE_STRATEGIC', 'STYLE_LIGHT'),
        optional_styles=('STYLE_HUMOROUS', 'STYLE_WARM', 'STYLE_GRITTY', 'STYLE_SUSPENSE', 'STYLE_ROMANTIC'),
        anchor_focus='捕捉现实生活细节（手机通知、合同条款、酒局眼神、衣着物件反差）作为阶层与情绪锚点。',
        expression_focus='明快流畅、贴近当代口语却不失精炼，酒局/商业博弈对话重潜台词与筹码亮底节奏。',
        writer_review_focus='核查现实行业/常识细节与人物说话身份一致性，避免“他心想”直白说教和强行降智打脸。',
        acceptance_focus='落账资金、合同权属、职级人脉与舆论风向变化，严格区分圈内传言与实签实证事实。',
        decomposition_focus='重点拆解现代生活质感细节、快节奏打脸/谈判对话回合与章末现实利益钩子的落笔方式。',
    ),
    'GENRE_LISHI': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_EPIC', 'TONE_COLD', 'TONE_SATIRICAL'),
        optional_tones=('TONE_DARK', 'TONE_DISTANT', 'TONE_HUMOROUS'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_EPIC', 'STYLE_STRATEGIC', 'STYLE_SERIOUS', 'STYLE_GROUP'),
        optional_styles=('STYLE_GRITTY', 'STYLE_COLD', 'STYLE_ACTION', 'STYLE_SLOW', 'STYLE_POETIC'),
        anchor_focus='立足时代器物、官服礼仪、地图军报与朝堂站位细节，把权力暗流具象为举止礼数锚点。',
        expression_focus='沉稳典雅而通俗易懂，朝堂奏对重委婉试探与政治潜台词，战阵段重调度全景与底层体感切换。',
        writer_review_focus='严查时代语言/器物穿帮、古人视角认知越界，确保多派系群像各自口吻与立场分明。',
        acceptance_focus='严守纪年时间线、军粮财政数字、官职任免与战局实控变化，严分密报传闻与实证结果。',
        decomposition_focus='重点拆解朝堂博弈潜台词对白、历史时代感器物细节与宏观战局/个体视角的距离切换。',
    ),
    'GENRE_JUNSHI': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_COLD', 'TONE_DARK'),
        optional_tones=('TONE_EPIC', 'TONE_DISTANT', 'TONE_WARM'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_GRITTY', 'STYLE_ACTION', 'STYLE_FAST', 'STYLE_SERIOUS'),
        optional_styles=('STYLE_STRATEGIC', 'STYLE_COLD', 'STYLE_EPIC', 'STYLE_GROUP', 'STYLE_SUSPENSE'),
        anchor_focus='精确落实枪械装备操作、弹道声响、地形掩体距离、通信杂音与战时生理应激锚点。',
        expression_focus='硬朗克制、高强度短句精准推进，战术指令简洁专业，休整期通过细微互动沉淀战友情谊。',
        writer_review_focus='严查战术距离、弹药损耗、通信盲区视角一致性，禁用脱离战场的抒情腔破坏临场感。',
        acceptance_focus='逐场核账弹药油料、人员伤亡、阵地控制与敌我态势，严分侦察研判与确证敌情。',
        decomposition_focus='重点拆解战场高压短句节奏、五感噪音/硝烟沉浸描写及通信中断时的受限视角张力。',
    ),
    'GENRE_KEHUAN': _cprofile(
        preferred_tones=('TONE_COLD', 'TONE_SERIOUS', 'TONE_EPIC', 'TONE_DISTANT'),
        optional_tones=('TONE_DARK', 'TONE_SATIRICAL', 'TONE_WARM'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_EPIC', 'STYLE_COLD', 'STYLE_SUSPENSE', 'STYLE_SERIOUS'),
        optional_styles=('STYLE_FANTASY', 'STYLE_GRITTY', 'STYLE_STRATEGIC', 'STYLE_ACTION', 'STYLE_POETIC'),
        anchor_focus='用仪表读数、物理异常现象、舱室失重/光照细节与时间膨胀信号作为硬核奇观与危机锚点。',
        expression_focus='理性克制中蕴含宏大敬畏感，科学原理通过行动与故障自然呈现，杜绝大段百科式设定灌输。',
        writer_review_focus='严核物理/逻辑前后一致、技术术语与叙述清晰度平衡，防止用“黑科技巧合”跳过因果。',
        acceptance_focus='精确追踪能源氧气库存、设备损伤、实验观测数据与时间坐标，严分科学假说与实测事实。',
        decomposition_focus='重点拆解科幻奇观的感官具象化、硬核概念的自然融入手法与冷静疏离语体的情绪爆点。',
    ),
    'GENRE_XUANYI': _cprofile(
        preferred_tones=('TONE_COLD', 'TONE_SERIOUS', 'TONE_DARK', 'TONE_DISTANT'),
        optional_tones=('TONE_SATIRICAL', 'TONE_INTIMATE'),
        preferred_styles=('STYLE_SUSPENSE', 'STYLE_GRITTY', 'STYLE_COLD', 'STYLE_REALISTIC', 'STYLE_STRATEGIC'),
        optional_styles=('STYLE_DARK', 'STYLE_SERIOUS', 'STYLE_FAST', 'STYLE_SLOW'),
        anchor_focus='高度依赖微表情破绽、现场异常缺席物件、时间印记与环境压迫感锚点，每处细节皆可回溯。',
        expression_focus='紧控叙述距离与信息释放层级，问询与对峙对白充满试探、回避与非直接回答，杜绝提前剧透。',
        writer_review_focus='重点审查 POV 知识边界、禁止“他意识到真相”式直给，核对所有伏笔与反转均在正文留有公平线索。',
        acceptance_focus='严守“证人供词/侦探推测（attributed/inferred）”与“物证确证事实（WORLD）”的绝对隔离。',
        decomposition_focus='重点拆解信息差控制、延迟解码伏笔的句子掩体、讯问潜台词博弈与章末悬念收束。',
    ),
    'GENRE_TUILI': _cprofile(
        preferred_tones=('TONE_COLD', 'TONE_SERIOUS', 'TONE_DISTANT'),
        optional_tones=('TONE_LIGHT', 'TONE_HUMOROUS', 'TONE_DARK'),
        preferred_styles=('STYLE_SUSPENSE', 'STYLE_REALISTIC', 'STYLE_COLD', 'STYLE_STRATEGIC', 'STYLE_SERIOUS'),
        optional_styles=('STYLE_SLOW', 'STYLE_GRITTY', 'STYLE_LIGHT'),
        anchor_focus='精确锁定密室门锁、钟表刻度、物证位置与证人细微口误等可公允核对的物理/言语锚点。',
        expression_focus='清晰冷静、叙述极度准确无歧义，区分客观现场描写与侦探主观假说推演，解谜段层层剥笋。',
        writer_review_focus='严审公平线索原则与时间线严密性，禁止在叙述中隐瞒 POV 亲眼所见的关键物证欺骗读者。',
        acceptance_focus='逐条建档物理物证、时间点与不在场证明状态，将伪解答假说与真解答实证严格分层。',
        decomposition_focus='重点拆解公平线索的精准植入句法、伪解答误导叙述技巧与终局推理的逻辑递进节奏。',
    ),
    'GENRE_LINGYI': _cprofile(
        preferred_tones=('TONE_DARK', 'TONE_COLD', 'TONE_SERIOUS', 'TONE_DISTANT'),
        optional_tones=('TONE_HUMOROUS', 'TONE_SATIRICAL'),
        preferred_styles=('STYLE_HORROR', 'STYLE_SUSPENSE', 'STYLE_DARK', 'STYLE_COLD', 'STYLE_FANTASY'),
        optional_styles=('STYLE_GRITTY', 'STYLE_STRATEGIC', 'STYLE_FAST', 'STYLE_SLOW'),
        anchor_focus='善用“正常里的微小违和”、视觉死角、异常声响/温度骤降、规则纸条字句与生理寒意锚点。',
        expression_focus='克制留白胜过直白嘶吼，善用静默时刻与短促停顿放大未知压迫，用冷静笔法衬托荒诞诡异。',
        writer_review_focus='严审感知边界与规则一致性，避免廉价形容词堆砌“很恐怖”，须以具体反常细节让读者自行发毛。',
        acceptance_focus='追踪污染/理智状态、触发禁忌记录与规则试错结论，严分“幸存者猜测的假规则”与“实测真规则”。',
        decomposition_focus='重点拆解反常细节的留白渲染、规则怪谈的文本信息差、静默蓄压与骤然异变的节奏对比。',
    ),
    'GENRE_KONGBU': _cprofile(
        preferred_tones=('TONE_DARK', 'TONE_COLD', 'TONE_SERIOUS'),
        optional_tones=('TONE_DISTANT',),
        preferred_styles=('STYLE_HORROR', 'STYLE_DARK', 'STYLE_GRITTY', 'STYLE_SUSPENSE', 'STYLE_FAST'),
        optional_styles=('STYLE_COLD', 'STYLE_SLOW', 'STYLE_REALISTIC', 'STYLE_ACTION'),
        anchor_focus='极端贴近感官压迫（呼吸急促、心跳、黑暗触觉、门缝异响、血迹/缺席者痕迹）建立窒息节拍。',
        expression_focus='静默长句蓄压与濒死短句骤然爆发强烈交替，近距离主观视角让读者同步体验绝境失控感。',
        writer_review_focus='严查恐惧疲劳与节奏波形，确保每场险境都有真实物理封锁与代价，杜绝廉价梦境/巧合解围。',
        acceptance_focus='如实沉淀伤残流血、物资减少、空间封锁与幸存者生死/崩溃状态，绝不凭空恢复安全感。',
        decomposition_focus='重点拆解幽闭空间感官描写、静默蓄压→骤然惊吓→余悸喘息的段落节奏与主观视角压迫感。',
    ),
    'GENRE_YOUXI': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_HUMOROUS', 'TONE_SERIOUS', 'TONE_EPIC'),
        optional_tones=('TONE_WARM', 'TONE_COLD'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_ACTION', 'STYLE_FAST', 'STYLE_LIGHT', 'STYLE_GROWTH'),
        optional_styles=('STYLE_HUMOROUS', 'STYLE_STRATEGIC', 'STYLE_GROUP', 'STYLE_EPIC'),
        anchor_focus='兼顾技能光效/Boss 动作前摇/血条阈值具象锚点与玩家团队语音互动细节，避免纯报冰冷数据。',
        expression_focus='爽利流畅、操作感强，把机制拆解与团队配合写成可读性高的动态画面，善用轻快吐槽调节高强度副本。',
        writer_review_focus='严查数值/冷却/装备前后一致，防止把小说写成流水账战报或属性面板复制粘贴。',
        acceptance_focus='精确追踪装备掉落、技能冷却/解锁、副本首通记录、声望与现实/游戏双线状态同步。',
        decomposition_focus='重点拆解将游戏机制转化为生动画面与操作爽感的写法、团队语音节奏及收益正反馈落笔。',
    ),
    'GENRE_DIANJING': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_SERIOUS', 'TONE_HUMOROUS', 'TONE_WARM'),
        optional_tones=('TONE_COLD', 'TONE_EPIC'),
        preferred_styles=('STYLE_FAST', 'STYLE_ACTION', 'STYLE_GROWTH', 'STYLE_GROUP', 'STYLE_STRATEGIC'),
        optional_styles=('STYLE_LIGHT', 'STYLE_HUMOROUS', 'STYLE_WARM', 'STYLE_REALISTIC'),
        anchor_focus='抓准键鼠微操、队内语音指令节奏、选手手部/眼神细节、大屏画面与观众席山呼海啸的声场锚点。',
        expression_focus='团战段极短句高频切换配合战术解说视角，赛外日常轻快鲜活，突出少年热忱与逆风抗压张力。',
        writer_review_focus='严查非玩家读者可读性（战术须直观易懂）与比赛战争迷雾视角一致性，禁止强行神化操作。',
        acceptance_focus='落账赛程比分、BP 战术暴露、选手伤病心态与舆论风向变化，确保多轮系列赛状态连贯。',
        decomposition_focus='重点拆解团战多线同步的清晰叙事、解说与选手视角无缝切换及逆风翻盘的情绪递进写法。',
    ),
    'GENRE_TIYU': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_WARM', 'TONE_EPIC', 'TONE_LIGHT'),
        optional_tones=('TONE_COLD', 'TONE_HUMOROUS'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_ACTION', 'STYLE_GROWTH', 'STYLE_FAST', 'STYLE_SERIOUS'),
        optional_styles=('STYLE_GRITTY', 'STYLE_WARM', 'STYLE_GROUP', 'STYLE_STRATEGIC'),
        anchor_focus='高度聚焦真实生理体感（肺部灼烧、汗水视线、肌肉痉挛、脚步节奏、记分牌倒计时与哨声定格）。',
        expression_focus='把毫秒级技术动作与心理博弈适度放慢特写，配合全场节奏加速，让读者亲历体能极限与意志碰撞。',
        writer_review_focus='严查人体机能极限与项目规则真实性，防止无依据超人爆发或重复空洞的呐喊描写。',
        acceptance_focus='追踪体能消耗、伤病隐患、技术弱点暴露、比分与赛季晋级状态，保持跨场连贯。',
        decomposition_focus='重点拆解竞技决胜瞬间的慢镜头特写、体能极限的感官落笔与胜负代价的余波描写。',
    ),
    'GENRE_YANQING': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_INTIMATE', 'TONE_LIGHT', 'TONE_SERIOUS'),
        optional_tones=('TONE_HUMOROUS', 'TONE_COLD', 'TONE_DARK'),
        preferred_styles=('STYLE_ROMANTIC', 'STYLE_WARM', 'STYLE_POETIC', 'STYLE_SLOW', 'STYLE_LIGHT'),
        optional_styles=('STYLE_REALISTIC', 'STYLE_GROWTH', 'STYLE_HUMOROUS', 'STYLE_SERIOUS', 'STYLE_SUSPENSE'),
        anchor_focus='极致打磨指尖触碰、眼神躲闪、呼吸停顿、信物细节与私密空间距离拉近的微反应锚点。',
        expression_focus='细腻克制、善用潜台词对话与欲言又止的停顿，贴近人物主观情绪距离，把心动与委屈藏进具体举动。',
        writer_review_focus='严查“他心里爱极了”式直白抒情，须以可感知动作/对白落实情感变化，严防无逻辑降智误会。',
        acceptance_focus='细腻追踪信任度、情感债务、亲密边界与未揭开秘密状态，严分“单方臆测”与“对方真实表态”。',
        decomposition_focus='重点拆解推拉暧昧对话的潜台词结构、心动瞬间的微表情/距离特写与甜虐情绪波形控制。',
    ),
    'GENRE_XIANDAI_YANQING': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_INTIMATE', 'TONE_LIGHT', 'TONE_HUMOROUS'),
        optional_tones=('TONE_SERIOUS', 'TONE_COLD', 'TONE_SATIRICAL'),
        preferred_styles=('STYLE_ROMANTIC', 'STYLE_REALISTIC', 'STYLE_WARM', 'STYLE_LIGHT', 'STYLE_SLOW'),
        optional_styles=('STYLE_HUMOROUS', 'STYLE_GROWTH', 'STYLE_POETIC', 'STYLE_SERIOUS'),
        anchor_focus='紧扣当代亲密日常细节（微信输入中停顿、晚归灯光、雨伞倾斜、咖啡温度与生活习惯磨合）。',
        expression_focus='自然松弛、对话富有现代机锋与生活烟火气，在轻甜日常与现实分歧之间精准调节情绪温度。',
        writer_review_focus='核查人物职业/生活细节真实度与双人声线差异，避免悬浮霸总套话或空洞心理独白。',
        acceptance_focus='落账感情进展、现实分歧筹码、旧伤揭露与双方真实承诺，严格区分猜测与已沟通共识。',
        decomposition_focus='重点拆解现代生活细节传递爱意/隔阂的写法、自然灵动的对话节奏与现实痛点的克制落笔。',
    ),
    'GENRE_GUDAI_YANQING': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_INTIMATE', 'TONE_SERIOUS', 'TONE_COLD'),
        optional_tones=('TONE_LIGHT', 'TONE_SATIRICAL', 'TONE_EPIC'),
        preferred_styles=('STYLE_ROMANTIC', 'STYLE_POETIC', 'STYLE_STRATEGIC', 'STYLE_WARM', 'STYLE_SLOW'),
        optional_styles=('STYLE_SERIOUS', 'STYLE_SUSPENSE', 'STYLE_LIGHT', 'STYLE_REALISTIC', 'STYLE_GROUP'),
        anchor_focus='善用古典器物衣饰、庭院四时风物、礼法行礼深浅与屏风帘幕隔断作为情感与权谋双重锚点。',
        expression_focus='温润雅致、暗藏机锋，深宅对话重礼数分寸与话里有话，亲密处含蓄隽永、动静相宜。',
        writer_review_focus='严查礼制称谓与语体一致性，杜绝现代网络用语穿帮，核对每场宅斗/朝堂交锋的因果证据。',
        acceptance_focus='追踪闺誉、管家权、家族位次、信物线索与感情信任变化，严分府内风声与确证事实。',
        decomposition_focus='重点拆解含蓄深情的古风意象表达、宅斗礼法借力对话技巧与情义/权谋双线交织写法。',
    ),
    'GENRE_XIANSHI': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_WARM', 'TONE_COLD', 'TONE_SATIRICAL'),
        optional_tones=('TONE_DISTANT', 'TONE_DARK', 'TONE_LIGHT', 'TONE_INTIMATE'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_GRITTY', 'STYLE_SERIOUS', 'STYLE_SLOW', 'STYLE_WARM'),
        optional_styles=('STYLE_GROUP', 'STYLE_POETIC', 'STYLE_GROWTH', 'STYLE_COLD'),
        anchor_focus='扎根真实烟火气物件（账本、老旧家具、双手茧痕、餐桌饭菜、时代街景声响）承载命运重量。',
        expression_focus='克制平实、白描见深情，不煽情拔高，靠扎实生活细节、地方口吻质感与留白空隙引发深层共鸣。',
        writer_review_focus='严查是否悬浮说教或廉价煽情，核对人物阶层语言、物价/政策时代细节与因果现实合理性。',
        acceptance_focus='如实记录家庭经济、健康劳损、人情亏欠、社会关系与时代处境变动，杜绝脱离现实的奇迹反转。',
        decomposition_focus='重点拆解现实主义白描细节、克制留白的悲欢落笔、群像声线差异与时代变迁的具象折射。',
    ),
    'GENRE_QINGCHUN': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_LIGHT', 'TONE_INTIMATE', 'TONE_HUMOROUS'),
        optional_tones=('TONE_SERIOUS', 'TONE_DISTANT'),
        preferred_styles=('STYLE_GROWTH', 'STYLE_WARM', 'STYLE_LIGHT', 'STYLE_POETIC', 'STYLE_REALISTIC'),
        optional_styles=('STYLE_ROMANTIC', 'STYLE_HUMOROUS', 'STYLE_SLOW', 'STYLE_GROUP'),
        anchor_focus='捕捉校园光影（粉笔灰、晚风操场、草稿纸涂鸦、考场钟声、自行车铃）与少年局促微反应。',
        expression_focus='清澈鲜活、灵动细腻，善用近距离主观视角还原青涩心事，结尾讲究成长告别后的温柔余韵。',
        writer_review_focus='避免成人油腻说教腔或矫揉造作，核查校园日常推进与人物心智变化的真实可见依据。',
        acceptance_focus='记录学业节点、友情/暗恋关系位移与自我认同变化，区分少年主观敏感脑补与客观事实。',
        decomposition_focus='重点拆解青春光影氛围营造、少年口语与敏感心理的具象化写法及首尾呼应的成长收束。',
    ),
    'GENRE_ERCIYUAN': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_HUMOROUS', 'TONE_WARM', 'TONE_EPIC'),
        optional_tones=('TONE_SERIOUS', 'TONE_DARK', 'TONE_INTIMATE'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_LIGHT', 'STYLE_HUMOROUS', 'STYLE_ACTION', 'STYLE_GROWTH'),
        optional_styles=('STYLE_GROUP', 'STYLE_FAST', 'STYLE_WARM', 'STYLE_ROMANTIC', 'STYLE_EPIC'),
        anchor_focus='突出高辨识度角色招牌动作/口癖、夸张鲜明的轻喜剧反应与高燃信念爆发时的定格特写镜头。',
        expression_focus='画面感与镜头切换感极强，日常对话轻快有梗，转入信念对决时骤然收紧节奏拉满情感张力。',
        writer_review_focus='严查角色招牌人设一致性与燃点铺垫是否充分，避免无铺垫尬燃或角色声线同质化。',
        acceptance_focus='追踪能力规则底牌、伙伴羁绊跃迁、阵营立场与隐藏身份揭露进度。',
        decomposition_focus='重点拆解强画面镜头语言、日常吐槽与高燃决战的语体切换技巧及角色萌点/燃点塑造。',
    ),
    'GENRE_QINGXIAOSHUO': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_HUMOROUS', 'TONE_INTIMATE', 'TONE_WARM'),
        optional_tones=('TONE_SERIOUS', 'TONE_SATIRICAL', 'TONE_DARK'),
        preferred_styles=('STYLE_LIGHT', 'STYLE_HUMOROUS', 'STYLE_FANTASY', 'STYLE_FAST', 'STYLE_ROMANTIC'),
        optional_styles=('STYLE_SUSPENSE', 'STYLE_GROWTH', 'STYLE_WARM', 'STYLE_ACTION', 'STYLE_POETIC'),
        anchor_focus='抓准第一/近三视角下的微妙反差动作、日常物件错位细节与高速对话中的停顿反转节拍。',
        expression_focus='灵动轻快、节奏明晰、第一人称吐槽或对话机锋密集，擅长用日常轻松表层包裹核心反转与真情。',
        writer_review_focus='核查吐槽密度不冲淡核心冲突、信息差与反转线索公平可见、各角色对话辨识度清晰。',
        acceptance_focus='追踪高概念规则限制、角色秘密知情范围与单卷伏笔回收状态，区分误会臆测与事实真相。',
        decomposition_focus='重点拆解轻小说标志性对话节奏、反差误会叙述技巧及卷末高潮的情感/反转收束。',
    ),
    'GENRE_TONGREN': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_SERIOUS', 'TONE_HUMOROUS', 'TONE_WARM'),
        optional_tones=('TONE_EPIC', 'TONE_COLD', 'TONE_DARK'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_GROWTH', 'STYLE_ACTION', 'STYLE_STRATEGIC', 'STYLE_FAST'),
        optional_styles=('STYLE_LIGHT', 'STYLE_HUMOROUS', 'STYLE_GROUP', 'STYLE_WARM', 'STYLE_ROMANTIC'),
        anchor_focus='还原原典角色标志性习惯、器物细节与名场面氛围锚点，同时突出主角介入带来的微妙偏差信号。',
        expression_focus='贴合原典世界语体风味而不生硬模仿，通过对比“原典预期”与“蝴蝶效应现实”制造新鲜读感。',
        writer_review_focus='严查原典角色 OOC（口吻/性格/战力崩坏）与先知信息边界，确保原典人物按自身认知自然反应。',
        acceptance_focus='精准追踪已偏离的原典时间线节点、原典人物对主角的新认知及蝴蝶效应连锁状态。',
        decomposition_focus='重点拆解不 OOC 的人物声线还原技巧、原典节点改写的情感张力与先知信息差写法。',
    ),
    'GENRE_ZHUTIAN': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_LIGHT', 'TONE_EPIC', 'TONE_COLD'),
        optional_tones=('TONE_HUMOROUS', 'TONE_DARK', 'TONE_SATIRICAL'),
        preferred_styles=('STYLE_FANTASY', 'STYLE_FAST', 'STYLE_ACTION', 'STYLE_STRATEGIC', 'STYLE_GROWTH'),
        optional_styles=('STYLE_EPIC', 'STYLE_LIGHT', 'STYLE_DARK', 'STYLE_SUSPENSE'),
        anchor_focus='每次切入新副本世界迅速用 2–3 个标志性风物/规则锚点定调，回归空间突出跨界战利品与实力跃迁感。',
        expression_focus='随副本世界题材微调表层风味而保持主角核心叙事声音统一，副本破局快节奏、结算段爽感清晰。',
        writer_review_focus='严查跨世界语体割裂与能力体系规则冲突，确保每次副本收获都在后续世界有实际表现与限制。',
        acceptance_focus='分世界清晰建账跨界道具、主神/系统任务评分、身体演化代价及主世界主线推进状态。',
        decomposition_focus='重点拆解新副本世界的快速入戏写法、跨体系能力碰撞表达与回归结算的节奏控制。',
    ),
    'GENRE_MOSHI': _cprofile(
        preferred_tones=('TONE_DARK', 'TONE_COLD', 'TONE_SERIOUS'),
        optional_tones=('TONE_WARM', 'TONE_DISTANT'),
        preferred_styles=('STYLE_GRITTY', 'STYLE_DARK', 'STYLE_REALISTIC', 'STYLE_ACTION', 'STYLE_FAST'),
        optional_styles=('STYLE_HORROR', 'STYLE_SUSPENSE', 'STYLE_COLD', 'STYLE_STRATEGIC', 'STYLE_GROUP'),
        anchor_focus='突出废墟焦土气味、干渴饥饿体感、弹药/净水余量、警戒动静与荒野微弱暖意的强烈对比锚点。',
        expression_focus='冷硬粗粝、惜字如金，危机段节奏凌厉紧绷，在残酷求生缝隙中用极克制的细节写人性微光。',
        writer_review_focus='严查物资/体力/伤势连续性与环境危险感，防止末世变成无消耗旅游或廉价爽文。',
        acceptance_focus='严格核算食物水药弹药库存、据点防御状态、成员伤亡感染及幸存者信任/秩序变化。',
        decomposition_focus='重点拆解末世荒芜感官建构、极限资源压力下的行动紧迫感写法与粗粝克制的情感刻画。',
    ),
    'GENRE_SAIBO': _cprofile(
        preferred_tones=('TONE_COLD', 'TONE_DARK', 'TONE_SATIRICAL', 'TONE_DISTANT'),
        optional_tones=('TONE_SERIOUS', 'TONE_HUMOROUS'),
        preferred_styles=('STYLE_DARK', 'STYLE_GRITTY', 'STYLE_COLD', 'STYLE_SUSPENSE', 'STYLE_ACTION'),
        optional_styles=('STYLE_FAST', 'STYLE_STRATEGIC', 'STYLE_REALISTIC', 'STYLE_HORROR'),
        anchor_focus='捕捉酸雨霓虹反光、义体机械杂音/过热痛觉、神经接口眩晕与巨企冰冷标语的高反差感官锚点。',
        expression_focus='黑色电影式冷峻讽刺语体，街区俚语与企业公关官腔形成尖锐对比，信息战与潜行火并节奏利落。',
        writer_review_focus='核查义体代价与监控盲区一致性，避免空洞堆砌赛博名词而缺乏人物在系统碾压下的真实痛感。',
        acceptance_focus='精准沉淀义体损耗/精神阈值、债务信用点、通缉暴露度、数据芯片归属与多方背叛账目。',
        decomposition_focus='重点拆解霓虹与底层破败的感官对比、黑色电影冷峻对白风格与物理/网络双线切换表达。',
    ),
    'GENRE_WEILAI': _cprofile(
        preferred_tones=('TONE_COLD', 'TONE_SERIOUS', 'TONE_DISTANT', 'TONE_SATIRICAL'),
        optional_tones=('TONE_EPIC', 'TONE_DARK', 'TONE_WARM'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_COLD', 'STYLE_SERIOUS', 'STYLE_SUSPENSE', 'STYLE_EPIC'),
        optional_styles=('STYLE_STRATEGIC', 'STYLE_SLOW', 'STYLE_GROUP', 'STYLE_POETIC', 'STYLE_GRITTY'),
        anchor_focus='以未来日常交互细节（算法评分提示、环境穹顶光照、配额终端）映照庞大制度对个体的无形塑造。',
        expression_focus='冷静精密、富有思辨质感，通过具体生活不便与异常裂缝自然揭示未来秩序本质，避免空泛说教。',
        writer_review_focus='严查未来设定生活化落地与逻辑闭环，确保观念冲突落实到真实人物抉择而非辩论演讲。',
        acceptance_focus='追踪权限/信用等级、技术系统异常证据、配额变动与群体意识觉醒节点。',
        decomposition_focus='重点拆解未来日常细节的陌生化写法、反乌托邦/新秩序的冷静讽刺语体与思辨落笔。',
    ),
    'GENRE_TONGHUA': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_LIGHT', 'TONE_INTIMATE'),
        optional_tones=('TONE_HUMOROUS', 'TONE_SERIOUS', 'TONE_EPIC'),
        preferred_styles=('STYLE_POETIC', 'STYLE_FANTASY', 'STYLE_WARM', 'STYLE_LIGHT', 'STYLE_SLOW'),
        optional_styles=('STYLE_GROWTH', 'STYLE_ROMANTIC', 'STYLE_HUMOROUS'),
        anchor_focus='凝练运用反复回响的色彩、自然生灵声音、奇幻信物与充满诗意的空间意象作为主题锚点。',
        expression_focus='纯净优美、音律舒朗、富于节奏感与隐喻余韵，用简洁透亮的句子传递深邃情感与寓言哲思。',
        writer_review_focus='严查语体纯净度与音律美感，避免生硬说教或成人市侩辞藻破坏童话氛围一致性。',
        acceptance_focus='清晰记录诺言履行/违背状态、象征信物变化与角色心灵成长兑现。',
        decomposition_focus='重点拆解童话诗意意象复现、三段递进音律节奏与留白隽永的寓言收束句法。',
    ),
    'GENRE_ERTONG': _cprofile(
        preferred_tones=('TONE_LIGHT', 'TONE_WARM', 'TONE_HUMOROUS'),
        optional_tones=('TONE_INTIMATE',),
        preferred_styles=('STYLE_LIGHT', 'STYLE_WARM', 'STYLE_HUMOROUS', 'STYLE_GROWTH', 'STYLE_FAST'),
        optional_styles=('STYLE_FANTASY', 'STYLE_REALISTIC', 'STYLE_POETIC'),
        anchor_focus='善用鲜明色彩、拟声词、有趣小道具与孩子好奇观察视角下的可爱动态细节。',
        expression_focus='明朗晓畅、句式简短有节奏、对话活泼贴合童心，在趣味冒险中自然融入友善与勇气。',
        writer_review_focus='严查用词适龄性、情节清晰度与正向价值，杜绝晦涩长难句、血腥恐怖或说教口吻。',
        acceptance_focus='准确记录冒险线索、小物件用途、伙伴互助关系与正向成长收获。',
        decomposition_focus='重点拆解适龄简明句式、趣味悬念节奏与贴近儿童视角的生动感官描写。',
    ),
    'GENRE_JISHI': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_DISTANT', 'TONE_COLD'),
        optional_tones=('TONE_WARM', 'TONE_SATIRICAL'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_SERIOUS', 'STYLE_GRITTY', 'STYLE_SLOW', 'STYLE_COLD'),
        optional_styles=('STYLE_GROUP', 'STYLE_SUSPENSE', 'STYLE_WARM'),
        anchor_focus='忠实依托真实档案时间、现场物证、环境原貌与受访者可证实的神态/原话，严禁虚构渲染。',
        expression_focus='克制客观、精准节制，通过事实并置、时间线剪辑与白描细节产生震撼力，杜绝主观抒情代判。',
        writer_review_focus='严审非虚构边界：禁止替人物编造无出处内心独白，每处时间/数字/引语须与已有事实一致。',
        acceptance_focus='逐条标注信息来源出处，严格区分受访者口述（attributed）与多方交叉确证事实（WORLD）。',
        decomposition_focus='重点拆解纪实文学的客观克制笔法、多源证言交叉剪辑与白描细节的叙事力量。',
    ),
    'GENRE_ZHIYE': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_LIGHT', 'TONE_COLD', 'TONE_WARM'),
        optional_tones=('TONE_HUMOROUS', 'TONE_SATIRICAL'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_FAST', 'STYLE_GROWTH', 'STYLE_STRATEGIC', 'STYLE_SERIOUS'),
        optional_styles=('STYLE_GRITTY', 'STYLE_WARM', 'STYLE_LIGHT', 'STYLE_GROUP', 'STYLE_SUSPENSE'),
        anchor_focus='落实真实行业动作、专业工具/文档/指标细节与职场微表情（汇报停顿、签字笔落点、会议座次）。',
        expression_focus='专业利落且外行可读，把行业术语转化为清晰风险与结果，职场交锋对话重分寸、甩锅与反制潜台词。',
        writer_review_focus='严查行业流程常识硬伤与外行理解门槛，防止堆砌术语或将职场剧写成脱离业务的悬浮恋爱。',
        acceptance_focus='精确落账项目进度、预算 KPI、合规风险、团队信任与专业资历实证变化。',
        decomposition_focus='重点拆解专业难题通俗化表达、高密度职场会议潜台词与专业破局爽感的落笔方式。',
    ),
    'GENRE_NVXING': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_SERIOUS', 'TONE_INTIMATE', 'TONE_COLD'),
        optional_tones=('TONE_LIGHT', 'TONE_SATIRICAL', 'TONE_HUMOROUS'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_GROWTH', 'STYLE_WARM', 'STYLE_SERIOUS', 'STYLE_STRATEGIC'),
        optional_styles=('STYLE_ROMANTIC', 'STYLE_GROUP', 'STYLE_POETIC', 'STYLE_FAST', 'STYLE_SLOW'),
        anchor_focus='敏锐捕捉主体视角下的细微不公、情绪边界确立瞬间、经济/事业实绩物证与女性互助的具象举动。',
        expression_focus='清醒有力且富有共情温度，对话鲜明有力不流于口号，通过克制反击与自我接纳展现成长弧光。',
        writer_review_focus='严查是否用空洞口号取代具体行动与现实代价，核对女性群像各自独立动机与声音辨识度。',
        acceptance_focus='追踪经济自主权、职场/家庭话语权反转、情感边界重构与互助关系沉淀。',
        decomposition_focus='重点拆解主体觉醒瞬间的克制落笔、现实反击对话张力与女性群像互助的细腻刻画。',
    ),
    'GENRE_JIATING': _cprofile(
        preferred_tones=('TONE_WARM', 'TONE_SERIOUS', 'TONE_INTIMATE', 'TONE_SATIRICAL'),
        optional_tones=('TONE_LIGHT', 'TONE_HUMOROUS', 'TONE_COLD'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_WARM', 'STYLE_SLOW', 'STYLE_GROUP', 'STYLE_SERIOUS'),
        optional_styles=('STYLE_GRITTY', 'STYLE_GROWTH', 'STYLE_LIGHT', 'STYLE_POETIC'),
        anchor_focus='聚焦饭桌碗筷声响、旧物件、医药单/房产证、门锁开关与亲人欲言又止的微动作锚点。',
        expression_focus='极具生活真实感与代际口吻差异，家常对话暗藏积年委屈、偏心与不善表达的牵挂，留足情绪消化余韵。',
        writer_review_focus='核查多代家庭成员语言习惯区分与情绪合理性，避免脸谱化“极品亲戚”或强行大团圆说教。',
        acceptance_focus='清晰记录家庭开支、照护分工、旧账摊牌结果、健康状况与亲情边界变化。',
        decomposition_focus='重点拆解饭桌群像多声部对话、生活琐事蓄积爆发的写法与不煽情却戳心的和解/边界落笔。',
    ),
    'GENRE_GONGTING': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_COLD', 'TONE_DARK', 'TONE_SATIRICAL'),
        optional_tones=('TONE_EPIC', 'TONE_DISTANT', 'TONE_INTIMATE'),
        preferred_styles=('STYLE_STRATEGIC', 'STYLE_SERIOUS', 'STYLE_COLD', 'STYLE_SUSPENSE', 'STYLE_POETIC'),
        optional_styles=('STYLE_DARK', 'STYLE_EPIC', 'STYLE_SLOW', 'STYLE_GROUP', 'STYLE_ROMANTIC'),
        anchor_focus='精雕细琢玉器茶盏、叩拜礼数、君王微表情、宫灯阴影与帘后耳目等高密度权力信号锚点。',
        expression_focus='含蓄深沉、字字机锋，一句表面谦恭暗藏杀机与试探，叙述克制疏离，于无声处见惊雷。',
        writer_review_focus='严查礼制称谓、宫禁空间权限、谁听见哪句话的披露边界及连环计因果闭环。',
        acceptance_focus='精确核账君心盛衰、派系消长、把柄证物、官爵贬升与立场不可逆固化，严分流言与密旨实证。',
        decomposition_focus='重点拆解宫廷权谋的弦外之音对话、微动作显露圣意/杀机的写法与高悬念节奏把控。',
    ),
    'GENRE_SHEHUI': _cprofile(
        preferred_tones=('TONE_SERIOUS', 'TONE_COLD', 'TONE_DARK', 'TONE_SATIRICAL'),
        optional_tones=('TONE_DISTANT', 'TONE_WARM'),
        preferred_styles=('STYLE_REALISTIC', 'STYLE_GRITTY', 'STYLE_SUSPENSE', 'STYLE_SERIOUS', 'STYLE_GROUP'),
        optional_styles=('STYLE_COLD', 'STYLE_DARK', 'STYLE_STRATEGIC', 'STYLE_SLOW'),
        anchor_focus='以阶层空间反差（豪华会所 vs 城中村）、关键账单/录音物证及小人物沉默眼神作为现实刺痛锚点。',
        expression_focus='冷峻写实而怀抱深沉悲悯，交叉群像声部各有阶层语言质感，揭露真相时克制有力、余味悠长。',
        writer_review_focus='严审现实程序逻辑、公平线索与多阶层视角可信度，防止空洞道德批判取代真实人性复杂性。',
        acceptance_focus='严守证据链、涉案利益关系网、证人处境与程序后果，严格隔离传言猜测与确证事实。',
        decomposition_focus='重点拆解社会派悬疑的群像交叉剪辑、阶层空间对比白描与冷峻悲悯语体的张力构造。',
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


def craft_profile_for_types(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Build genre-targeted 12–17 craft/closure profile with item-level tone & style ranking."""
    normalized, mains = _resolve_main_genres(types)
    mapping = type_map()
    type_objs = [{'id': tid, 'name': mapping[tid]['name'], 'parent_id': mapping[tid].get('parent_id')}
                 for tid in normalized if tid in mapping]
    profiles = [GENRE_CRAFT_PROFILES.get(mid, DEFAULT_CRAFT_PROFILE) for mid in mains] if mains else [DEFAULT_CRAFT_PROFILE]

    pref_tones: list[str] = []
    opt_tones: list[str] = []
    pref_styles: list[str] = []
    opt_styles: list[str] = []
    anchor_focuses: list[str] = []
    expr_focuses: list[str] = []
    wr_focuses: list[str] = []
    acc_focuses: list[str] = []
    decomp_focuses: list[str] = []

    for prof in profiles:
        for t in prof['preferred_tones']:
            if t not in pref_tones:
                pref_tones.append(t)
        for t in prof['optional_tones']:
            if t not in opt_tones and t not in pref_tones:
                opt_tones.append(t)
        for s in prof['preferred_styles']:
            if s not in pref_styles:
                pref_styles.append(s)
        for s in prof['optional_styles']:
            if s not in opt_styles and s not in pref_styles:
                opt_styles.append(s)
        cp = prof['craft_profile']
        if cp['anchor_focus'] not in anchor_focuses:
            anchor_focuses.append(cp['anchor_focus'])
        if cp['expression_focus'] not in expr_focuses:
            expr_focuses.append(cp['expression_focus'])
        if cp['writer_review_focus'] not in wr_focuses:
            wr_focuses.append(cp['writer_review_focus'])
        if cp['acceptance_focus'] not in acc_focuses:
            acc_focuses.append(cp['acceptance_focus'])
        if prof['decomposition_focus'] not in decomp_focuses:
            decomp_focuses.append(prof['decomposition_focus'])

    categories: list[dict[str, Any]] = []
    for cat in CRAFT_CATEGORIES:
        categories.append({
            'id': cat['id'],
            'slot': cat['slot'],
            'target_stage': cat['target_stage'],
            'target_stage_label': cat['target_stage_label'],
            'name': cat['name'],
            'short_name': cat['short_name'],
            'description': cat['description'],
            'usage_mode': cat['usage_mode'],
            'source_files': list(cat['source_files']),
            'catalog_group_keys': list(cat['catalog_group_keys']),
            'relevance': 'primary',
            'relevance_label': RELEVANCE_LABELS['primary'],
            'boundary_note': cat['usage_mode'],
        })

    return {
        'types': type_objs,
        'main_types': [{'id': mid, 'name': mapping[mid]['name']} for mid in mains if mid in mapping],
        'has_genre_binding': bool(mains),
        'primary_categories': [c['id'] for c in categories],
        'optional_categories': [],
        'out_of_scope_categories': [],
        'preferred_tones': pref_tones,
        'optional_tones': opt_tones,
        'preferred_styles': pref_styles,
        'optional_styles': opt_styles,
        'categories': categories,
        'narration_categories': [c for c in categories if c['slot'] == 'narration'],
        'anchor_categories': [c for c in categories if c['target_stage'] == 'anchor_design'],
        'expression_categories': [c for c in categories if c['target_stage'] == 'expression_design'],
        'bind_scope_categories': [c for c in categories if c['target_stage'] == 'bind_scope'],
        'writer_categories': [c for c in categories if c['target_stage'] == 'writer'],
        'review_categories': [c for c in categories if c['target_stage'] == 'review'],
        'acceptance_categories': [c for c in categories if c['target_stage'] == 'acceptance'],
        'craft_profile': {
            'anchor_focus': '；'.join(anchor_focuses),
            'expression_focus': '；'.join(expr_focuses),
            'writer_review_focus': '；'.join(wr_focuses),
            'acceptance_focus': '；'.join(acc_focuses),
        },
        'decomposition_focus': '；'.join(decomp_focuses),
        'step_boundaries': {
            'anchor_design': deepcopy(ANCHOR_STEP_BOUNDARY),
            'expression_design': deepcopy(EXPRESSION_STEP_BOUNDARY),
            'bind_scope': deepcopy(BIND_SCOPE_STEP_BOUNDARY),
            'writer': deepcopy(WRITER_STEP_BOUNDARY),
            'review': deepcopy(REVIEW_STEP_BOUNDARY),
            'acceptance': deepcopy(ACCEPTANCE_STEP_BOUNDARY),
        },
    }


def _annotate_typed_children(children: list[dict[str, Any]], primary_ids: list[str], optional_ids: list[str],
                             *, has_genre: bool) -> list[dict[str, Any]]:
    if not has_genre:
        return deepcopy(children)
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


def annotate_craft_groups(slot: str, groups: list[dict[str, Any]],
                          types: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Annotate narration (09/12/13), tone (13), or style (13) option groups & typed items by genre."""
    profile = craft_profile_for_types(types)
    by_group_key: dict[str, dict[str, Any]] = {}
    for cat in profile['categories']:
        if cat['slot'] == slot:
            for gkey in cat['catalog_group_keys']:
                by_group_key[gkey] = cat

    annotated: list[dict[str, Any]] = []
    for group in groups:
        row = deepcopy(group)
        meta = by_group_key.get(row['key'])
        if meta:
            row.update(
                craft_category=meta['id'],
                target_stage=meta['target_stage'],
                target_stage_label=meta['target_stage_label'],
                description=row.get('description') or meta['description'],
                usage_mode=meta['usage_mode'],
                relevance=meta['relevance'],
                relevance_label=meta['relevance_label'],
                boundary_note=meta['boundary_note'],
                source_files=meta['source_files'],
            )
            if slot == 'tone' and row.get('children'):
                row['children'] = _annotate_typed_children(
                    row['children'], profile['preferred_tones'], profile['optional_tones'],
                    has_genre=profile['has_genre_binding'],
                )
            elif slot == 'style' and row.get('children'):
                row['children'] = _annotate_typed_children(
                    row['children'], profile['preferred_styles'], profile['optional_styles'],
                    has_genre=profile['has_genre_binding'],
                )
        annotated.append(row)
    return annotated


def annotate_craft_children(slot: str, parent_key: str, children: list[dict[str, Any]],
                            types: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Annotate children when fetching /api/options?slot=tone|style&parent=...&types=..."""
    profile = craft_profile_for_types(types)
    if slot == 'tone' and parent_key == 'tone.group.types':
        return _annotate_typed_children(
            children, profile['preferred_tones'], profile['optional_tones'],
            has_genre=profile['has_genre_binding'],
        )
    if slot == 'style' and parent_key == 'style.group.types':
        return _annotate_typed_children(
            children, profile['preferred_styles'], profile['optional_styles'],
            has_genre=profile['has_genre_binding'],
        )
    return deepcopy(children)


def classify_craft_method(body: dict[str, Any]) -> list[str]:
    """Deterministically classify a method targeting 12–17 into matching craft & closure categories."""
    if not isinstance(body, dict):
        return []
    tasks = set(body.get('tasks') or ())
    outputs = body.get('outputs') or ()
    downstream = body.get('downstream') or ()
    output_stages = {o.get('stage') for o in outputs if isinstance(o, dict)}
    exec_consumers = {d.get('consumer') for d in downstream if isinstance(d, dict)}

    allowed_stages: set[str] = set()
    if 'anchors' in tasks or 'anchor_design' in output_stages:
        allowed_stages.add('anchor_design')
    if bool({'narration', 'expression', 'pacing'} & tasks) or 'expression_design' in output_stages:
        allowed_stages.add('expression_design')
    if 'method_binding' in tasks or 'bind_scope' in output_stages:
        allowed_stages.add('bind_scope')
    for exec_st in ('writer', 'review', 'acceptance'):
        if exec_st in exec_consumers:
            allowed_stages.add(exec_st)
    if not allowed_stages:
        return []

    text = ' '.join([
        str(body.get('title') or ''),
        ' '.join(str(x) for x in (body.get('applicability') or ())),
        ' '.join(str(o.get('instruction') or '') for o in (body.get('operations') or ()) if isinstance(o, dict)),
        ' '.join(str(o.get('description') or '') for o in outputs if isinstance(o, dict)),
    ])
    scores: list[tuple[int, int, str]] = []
    for cat in CRAFT_CATEGORIES:
        if cat['target_stage'] not in allowed_stages:
            continue
        hits = sum(1 for kw in cat['keywords'] if kw in text)
        if hits:
            scores.append((-hits, CRAFT_CATEGORY_ORDER[cat['id']], cat['id']))
    if not scores:
        fallback: list[str] = []
        if 'anchor_design' in allowed_stages:
            fallback.append('anchor_body_camera')
        if 'expression_design' in allowed_stages:
            fallback.append('expr_dialogue_sensory' if 'expression' in tasks else 'expr_narrator_voice')
        if 'bind_scope' in allowed_stages:
            fallback.append('bind_scope_contract')
        if 'writer' in allowed_stages:
            fallback.append('writer_craft_execution')
        if 'review' in allowed_stages:
            fallback.append('review_independent_evidence')
        if 'acceptance' in allowed_stages:
            fallback.append('acceptance_state_evidence')
        return fallback
    scores.sort()
    return [cid for _, _, cid in scores[:4]]


def craft_decomposition_prompt(
    types: list[str] | tuple[str, ...] | None = None,
    domain: str = 'narration',
    *,
    phase: str = 'methods',
) -> str:
    """Concise genre-targeted 12–17 boundary guidance for narration/pacing decomposition & derivation.

    Note: deliberately excludes raw craft-only token identifiers so craft=False prompts remain spotless.
    """
    profile = craft_profile_for_types(types)
    type_label = ' / '.join(t['name'] for t in profile['main_types']) or '当前参考书'
    cp = profile['craft_profile']
    if phase == 'methods':
        return (
            f'【12锚点–17写审验收·分类型边界（{type_label}）】'
            f'12锚点重点：{cp["anchor_focus"]}；'
            f'13表达重点：{cp["expression_focus"]}；'
            f'写审验收重点：{cp["writer_review_focus"]}。'
            '严守收尾分工：观察者可见的动作/身体/物件节拍落入 anchor_design.beats（须对应真实动作与 POV）；'
            '叙述时序、距离、对白潜台词与文风落入 expression_design.guidance；'
            '每条方法必须给出可定位正文段落的独立验收 check 与 evidence_required，严禁以计划复述代替正文证据。'
        )
    return (
        f'【12–17 锚点与表达·按本书类型（{type_label}）定向核对{domain}】'
        f'{profile["decomposition_focus"]} 严格区分原文确证事实与人物主观说法/推测，保留可核查的段落承接依据。'
    )


def craft_stage_prompt_packet(types: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Compact deterministic packet frozen into planning manifests for 12–14 design stages."""
    profile = craft_profile_for_types(types)
    type_list = [{'id': t['id'], 'name': t['name']} for t in profile['types']]
    cp = profile['craft_profile']

    def _for_stage(stage: str) -> dict[str, Any]:
        cats = [c for c in profile['categories'] if c['target_stage'] == stage]
        boundary = profile['step_boundaries'][stage]
        packet: dict[str, Any] = {
            'types': type_list,
            'stage': stage,
            'primary_categories': [
                {'id': c['id'], 'name': c['name'], 'usage_mode': c['usage_mode']}
                for c in cats
            ],
            'step_boundary': {
                'responsibility': boundary['responsibility'],
                'out_of_scope': list(boundary['out_of_scope']),
                'downstream_steps': [d['step_id'] for d in boundary['downstream_steps']],
            },
        }
        if stage == 'anchor_design':
            packet['stage_focus'] = {'anchor_focus': cp['anchor_focus']}
        elif stage == 'expression_design':
            packet['stage_focus'] = {'expression_focus': cp['expression_focus']}
            packet['preferred_tones'] = list(profile['preferred_tones'])
            packet['preferred_styles'] = list(profile['preferred_styles'])
        else:
            packet['stage_focus'] = {
                'writer_review_focus': cp['writer_review_focus'],
                'acceptance_focus': cp['acceptance_focus'],
            }
        return packet

    return {
        'anchor_design': _for_stage('anchor_design'),
        'expression_design': _for_stage('expression_design'),
        'bind_scope': _for_stage('bind_scope'),
    }


def design_genre_ids(design: dict | None) -> list[str]:
    """Extract canonical GENRE_/SUB_ IDs from an approved scene's work_session if present."""
    if not isinstance(design, dict):
        return []
    session = design.get('work_session')
    if not isinstance(session, dict):
        return []
    raw: list[str] = []
    for st in session.get('stages', ()):
        if isinstance(st, dict) and st.get('stage') == 'type_selection':
            prods = st.get('products') or {}
            for item in prods.get('selection', ()):
                if isinstance(item, dict) and isinstance(item.get('id'), str):
                    raw.append(item['id'])
            break
    if not raw:
        ctx = session.get('context') or {}
        policy = ctx.get('production_method_policy') or session.get('production_method_policy') or {}
        if isinstance(policy.get('type_ids'), list):
            raw.extend(x for x in policy['type_ids'] if isinstance(x, str))
    if not raw:
        return []
    known = type_map()
    valid = [ident for ident in raw if ident in known]
    if not valid:
        return []
    try:
        return canonical_types(valid)
    except ValueError:
        return []


def writing_genre_guidance(types: list[str] | tuple[str, ...] | None) -> str:
    """Concise genre-targeted 15 writer / revise prompt guidance; empty if no types."""
    if not types:
        return ''
    try:
        profile = craft_profile_for_types(types)
    except ValueError:
        return ''
    if not profile['has_genre_binding']:
        return ''
    label = ' / '.join(t['name'] for t in profile['main_types'])
    cp = profile['craft_profile']
    return (
        f'【15正文写作·{label}约束】'
        f'表达与节奏：{cp["expression_focus"]}'
        f' 写审红线：{cp["writer_review_focus"]}'
        ' 严守受限POV与allowed_disclosure，用精确动词与具象动作感官代替抽象总结。'
    )


def review_genre_guidance(types: list[str] | tuple[str, ...] | None) -> str:
    """Concise genre-targeted 16 independent review prompt guidance; empty if no types."""
    if not types:
        return ''
    try:
        profile = craft_profile_for_types(types)
    except ValueError:
        return ''
    if not profile['has_genre_binding']:
        return ''
    label = ' / '.join(t['name'] for t in profile['main_types'])
    cp = profile['craft_profile']
    return (
        f'【16独立审稿·{label}红线】'
        f'{cp["writer_review_focus"]}'
        ' 以正文具体段落引文为准，严查视角越界、信息偷跑、“他心想/他意识到”直白总结与无代价跳过阻碍。'
    )


def acceptance_genre_guidance(types: list[str] | tuple[str, ...] | None) -> str:
    """Concise genre-targeted 17 state-extract & fact-review guidance; empty if no types."""
    if not types:
        return ''
    try:
        profile = craft_profile_for_types(types)
    except ValueError:
        return ''
    if not profile['has_genre_binding']:
        return ''
    label = ' / '.join(t['name'] for t in profile['main_types'])
    cp = profile['craft_profile']
    return (
        f'【17状态提取与事实复核·{label}口径】'
        f'{cp["acceptance_focus"]}'
        ' 严禁将无正文引文支撑的计划或人物口头说辞/推测写入WORLD客观事实，历史累积代价不可静默清零。'
    )


def craft_blueprint(library: Any, types: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Combine genre-targeted 12–17 craft/closure profile with live workspace coverage."""
    from nw.studio.downstream_handoff import audit_downstream_handoff

    profile = craft_profile_for_types(types)
    audit = audit_downstream_handoff(library, types=list(types), planning_hierarchy=True)
    craft_tasks = {'anchors', 'narration', 'expression', 'pacing', 'method_binding'}
    craft_stages = {'anchor_design', 'expression_design', 'bind_scope'}
    target_methods = [
        m for m in audit.get('methods', ())
        if bool(craft_tasks & set(m.get('tasks', ())))
        or bool(craft_stages & set(m.get('output_stages', ())))
        or bool(m.get('downstream_execution'))
    ]
    by_cat_rec: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in CRAFT_CATEGORIES}
    by_cat_draft: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in CRAFT_CATEGORIES}
    by_cat_blocked: dict[str, list[dict[str, Any]]] = {c['id']: [] for c in CRAFT_CATEGORIES}

    for method in target_methods:
        cats = method.get('craft_categories') or []
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
        if rec:
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
        'narration_categories': [c for c in categories_with_coverage if c['slot'] == 'narration'],
        'anchor_categories': [c for c in categories_with_coverage if c['target_stage'] == 'anchor_design'],
        'expression_categories': [c for c in categories_with_coverage if c['target_stage'] == 'expression_design'],
        'bind_scope_categories': [c for c in categories_with_coverage if c['target_stage'] == 'bind_scope'],
        'writer_categories': [c for c in categories_with_coverage if c['target_stage'] == 'writer'],
        'review_categories': [c for c in categories_with_coverage if c['target_stage'] == 'review'],
        'acceptance_categories': [c for c in categories_with_coverage if c['target_stage'] == 'acceptance'],
        'coverage_summary': {
            'total_craft_methods': len(target_methods),
            'receivable_anchor_methods': step_by_id.get('anchor_design', {}).get('receivable_count', 0),
            'receivable_expression_methods': step_by_id.get('expression_design', {}).get('receivable_count', 0),
            'receivable_bind_scope_methods': step_by_id.get('bind_scope', {}).get('receivable_count', 0),
            'receivable_writer_methods': step_by_id.get('writer', {}).get('receivable_count', 0),
            'receivable_review_methods': step_by_id.get('review', {}).get('receivable_count', 0),
            'receivable_acceptance_methods': step_by_id.get('acceptance', {}).get('receivable_count', 0),
            'primary_category_count': len(profile['primary_categories']),
            'covered_primary_categories': covered_primary,
            'passage_reference_count': audit['summary']['passage_reference_count'],
        },
        'originality_audit': audit['originality_audit'],
    }
