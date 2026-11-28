"""Creative novel-writing workflow layer over durable material & state verification.

Turns the underlying 14-stage material governance graph into an author-facing,
working novel creation pipeline:
1. Programmatically compiles/inherits already-chosen genre & adaptation contracts
   (0 wasted LLM calls for volume/chapter type stages, book type_selection,
   single-genre book type_adaptation, and empty volume bind_scope).
2. Enforces concrete screenwriter/outlining deliverables:
   - book: opening_plan (开篇抢跑与黄金三章), character_arcs (逐人弧光变化链),
     story_segments (可拆分主线因果段).
   - volume: chapter_splits (逐章任务切分与交接表).
   - chapter: auto-injects volume chapter_splits mission + golden-three beats +
     character arc turns into chapter outline design.
3. Supplies scope-aware working step names and grouping for the Studio UI so
   authors and models work on actual novel-writing steps instead of repetitive
   type-classification headers.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.materials.phase_routes import product_ref
from nw.task_models import canonical, content_sha256

POLICY = 'creative-workflow-v1'

CREATIVE_DIRECTION_FIELDS: dict[str, tuple[str, int]] = {
    'opening_hook': ('开篇切入瞬间与黄金三章钩子', 240),
    'story_arcs': ('从开端到结局的阶段因果路线', 360),
    'protagonist_arc': ('主角核心弧光（起点盲点→触发选择→代价→蜕变）', 240),
    'design_needs': ('故事成立所需的世界规则与关键人物条件', 240),
}

# Scope-specific working step labels & creative workflow grouping.
SCOPE_STEP_META: dict[str, dict[str, dict[str, Any]]] = {
    'book': {
        'type_selection': {'label': '立项类型契约（自动冻结）', 'group': 'auto_contract', 'auto_collapsible': True},
        'type_adaptation': {'label': '多类型融合边界校核', 'group': 'auto_contract', 'auto_collapsible': True},
        'world_design': {'label': '世界规则与限制定稿', 'group': 'book_foundation', 'group_label': '一、全书设定与人物定稿'},
        'character_design': {'label': '核心人物与弧光起点', 'group': 'book_foundation', 'group_label': '一、全书设定与人物定稿'},
        'static_relations': {'label': '人物关系与势力张力', 'group': 'book_foundation', 'group_label': '一、全书设定与人物定稿'},
        'plot_design': {'label': '全书主线、开篇承诺与分卷大纲', 'group': 'book_outline', 'group_label': '二、全书故事大纲与收口'},
        'bind_scope': {'label': '全书规则核验与定稿收口', 'group': 'book_outline', 'group_label': '二、全书故事大纲与收口'},
    },
    'volume': {
        'type_selection': {'label': '继承全书类型契约（免重判）', 'group': 'auto_contract', 'auto_collapsible': True},
        'type_adaptation': {'label': '继承全书类型适配（免重判）', 'group': 'auto_contract', 'auto_collapsible': True},
        'world_design': {'label': '本卷新增世界规则补位', 'group': 'volume_prep', 'group_label': '一、本卷增量设定与人物'},
        'character_design': {'label': '本卷新增人物补位（复用优先）', 'group': 'volume_prep', 'group_label': '一、本卷增量设定与人物'},
        'static_relations': {'label': '本卷势力与关系变动', 'group': 'volume_prep', 'group_label': '一、本卷增量设定与人物'},
        'plot_design': {'label': '本卷剧情分段与逐章任务切分', 'group': 'volume_split', 'group_label': '二、卷纲剧情与逐章切分'},
        'bind_scope': {'label': '卷纲收口（自动完成）', 'group': 'auto_contract', 'auto_collapsible': True},
    },
    'chapter': {
        'type_selection': {'label': '继承全书类型契约（免重判）', 'group': 'auto_contract', 'auto_collapsible': True},
        'type_adaptation': {'label': '继承全书类型适配（免重判）', 'group': 'auto_contract', 'auto_collapsible': True},
        'world_design': {'label': '本章局部规则与出场需求', 'group': 'chapter_outline_prep', 'group_label': '一、本章承接与章纲确认'},
        'character_design': {'label': '本章出场人物核对（复用优先）', 'group': 'chapter_outline_prep', 'group_label': '一、本章承接与章纲确认'},
        'static_relations': {'label': '本章在场关系与信息差', 'group': 'chapter_outline_prep', 'group_label': '一、本章承接与章纲确认'},
        'plot_design': {'label': '本章剧情推进与章纲定稿', 'group': 'chapter_outline_prep', 'group_label': '一、本章承接与章纲确认'},
        'event_design': {'label': '本章事件链与因果触发', 'group': 'scene_beats', 'group_label': '二、场景节拍与行动状态'},
        'action_design': {'label': '人物行动博弈与试错代价', 'group': 'scene_beats', 'group_label': '二、场景节拍与行动状态'},
        'scene_design': {'label': '场景卡与 POV 边界排布', 'group': 'scene_beats', 'group_label': '二、场景节拍与行动状态'},
        'state_transition': {'label': '场内状态变化与代价', 'group': 'scene_beats', 'group_label': '二、场景节拍与行动状态'},
        'state_propagation': {'label': '状态连锁传播预案', 'group': 'scene_beats', 'group_label': '二、场景节拍与行动状态'},
        'anchor_design': {'label': '具象动作锚点与感官节拍', 'group': 'writing_pack', 'group_label': '三、写前表现与场景工作包'},
        'expression_design': {'label': '叙述距离、对白与文风指导', 'group': 'writing_pack', 'group_label': '三、写前表现与场景工作包'},
        'bind_scope': {'label': '冻结可写场景工作包', 'group': 'writing_pack', 'group_label': '三、写前表现与场景工作包'},
    },
}

CREATIVE_STAGE_DEFAULTS: dict[str, str] = {
    'type_selection': '立项类型契约（程序自动冻结）',
    'type_adaptation': '多类型融合适配（单类型自动冻结）',
    'world_design': '世界规则与限制定稿',
    'character_design': '核心人物与弧光起点',
    'static_relations': '人物关系与势力张力',
    'plot_design': '故事大纲、开篇承诺与卷章切分',
    'event_design': '本章事件链与因果触发',
    'action_design': '人物行动博弈与试错代价',
    'scene_design': '场景卡与 POV 边界排布',
    'state_transition': '场内状态变化与代价',
    'state_propagation': '状态连锁传播预案',
    'anchor_design': '具象动作锚点与感官节拍',
    'expression_design': '叙述距离、对白与文风指导',
    'bind_scope': '冻结可写场景工作包',
    'writer': '场景正文起草',
    'review': '事实与读者独立审稿',
    'acceptance': '状态提取、复核与作者接受',
}


def step_label(scope: str, stage: str, *, fallback: str = '') -> str:
    scoped = SCOPE_STEP_META.get(scope, {}).get(stage)
    if scoped:
        return scoped['label']
    return CREATIVE_STAGE_DEFAULTS.get(stage, fallback or stage)


def step_meta(scope: str, stage: str) -> dict[str, Any]:
    scoped = SCOPE_STEP_META.get(scope, {}).get(stage)
    if scoped:
        return dict(scoped)
    return {'label': CREATIVE_STAGE_DEFAULTS.get(stage, stage), 'group': 'other', 'auto_collapsible': False}


def workflow_overview() -> dict[str, Any]:
    """Author-facing overview of the actual novel creation workflow across all 4 tiers."""
    return {
        'policy': POLICY,
        'title': '实际创作工作流（立项契约自动继承 · 按真实写书步骤推进）',
        'summary': (
            '立项已选的类型、偏好、篇幅与拆解方法由程序自动冻结并逐级继承，不再在全书/卷纲/每章重复空转'
            '「类型判定 / 类型适配」；模型专注完成全书大纲、世界与人物定稿、卷纲逐章切分、章细纲与可写场景包、'
            '正文写作、独立审稿修订、状态提取接受与续章复盘。'
        ),
        'auto_contract': {
            'label': '立项类型与偏好契约（程序自动冻结 · 免重复判定）',
            'internal_stages': ['type_selection', 'type_adaptation'],
            'behavior': '全书立项自动编译类型契约（仅多主类型融合冲突时才做一次融合校核）；卷纲与章纲 0 调用自动继承。',
        },
        'tiers': [
            {
                'id': 'book',
                'order': 1,
                'title': '一、全书方向与故事大纲',
                'goal': '确立可推演的主线因果、开篇黄金三章承诺、关键人物弧光变化链，以及故事成立所需的世界与人物设计需求。',
                'steps': [
                    {'stage': 'book_direction', 'label': '全书方向与故事大纲（可选多案对比或直出）', 'deliverable': '开篇钩子、全书因果路线、主角弧光、世界/人物设计需求'},
                    {'stage': 'world_design', 'label': '世界规则与限制定稿', 'deliverable': '世界规则卡、硬限制、代价与待确认边界'},
                    {'stage': 'character_design', 'label': '核心人物与弧光起点', 'deliverable': '主角/反派/配角卡、能力上限、入场与知情边界'},
                    {'stage': 'static_relations', 'label': '人物关系与势力张力', 'deliverable': '真实实体关系网、权力/信息不对称、配角独立互动'},
                    {'stage': 'plot_design', 'label': '全书主线、开篇承诺与分卷大纲', 'deliverable': '主线方向、开篇与黄金三章、逐人弧光链、可拆分剧情段、伏笔总表'},
                ],
            },
            {
                'id': 'volume',
                'order': 2,
                'title': '二、当前卷纲与逐章切分',
                'goal': '承接全书大纲与前卷状态，补齐本卷新增设定与角色，把本卷剧情拆成明确的逐章任务清单。',
                'steps': [
                    {'stage': 'world_design', 'label': '本卷新增世界规则补位（按需增量）', 'deliverable': '本卷新地图/新制度/新代价（无新增直接沿用全书卡）'},
                    {'stage': 'character_design', 'label': '本卷新增人物与关系补位', 'deliverable': '复用全书角色优先，仅补本卷新势力与关系变动'},
                    {'stage': 'plot_design', 'label': '本卷剧情分段与逐章任务切分', 'deliverable': '卷卡目标/转折/卷末交接 + 逐章任务切分表（chapter_splits）+ 伏笔节奏分配'},
                ],
            },
            {
                'id': 'chapter',
                'order': 3,
                'title': '三、当前章细纲与可写场景包',
                'goal': '领取本卷切分给本章的任务与上章已接受后果，确认章纲后直接落地场景节拍、行动博弈、状态变化与写前表达包。',
                'steps': [
                    {'stage': 'plot_design', 'label': '本章前情承接、出场核对与章纲定稿', 'deliverable': '承接上章钩子/到期伏笔/人物所知 → 产出章卡与事件节点 → 作者确认章纲'},
                    {'stage': 'scene_design', 'label': '事件链、行动博弈与场景 POV 排布', 'deliverable': '每场时空/POV/在场人物/行动试错代价/前态快照'},
                    {'stage': 'state_transition', 'label': '场内状态变化与连锁传播预案', 'deliverable': '因果状态迁移、代价延续、非全知传播候选'},
                    {'stage': 'expression_design', 'label': '具象锚点、表达指导与场景包冻结', 'deliverable': 'POV可见节拍、叙述距离与对白指导、可写场景工作包'},
                ],
            },
            {
                'id': 'writing',
                'order': 4,
                'title': '四、正文写作、审稿修订与连载推进',
                'goal': '按受限 POV 场景包起草正文，经过事实+读者双审与限次修订，提取真实正文状态增量并接受入库，带着实际后果推进下一章。',
                'steps': [
                    {'stage': 'writer', 'label': '场景正文起草（15）', 'deliverable': '受限POV正文草稿（不可变版本）'},
                    {'stage': 'review', 'label': '事实与读者独立审稿及限次修订（16）', 'deliverable': '逐条引文核验、语言/逻辑红线检查、最多2轮修订'},
                    {'stage': 'acceptance', 'label': '状态提取、作者接受与续章复盘（17）', 'deliverable': '正文偏移状态增量、章节总结、7类周期复盘与伏笔清账'},
                ],
            },
        ],
    }


def _has_active_method_work(method_plan: dict | None, stage: str, context: dict) -> bool:
    if method_plan is None:
        return False
    target = method_plan.get('target') or {}
    if target.get('required_tasks') or target.get('required_recommended_slots'):
        return True
    if method_plan.get('selected'):
        return True
    if any(p.get('consumer') == stage for p in context.get('production_method_parents', ())):
        return True
    # Also check if any ready candidate was explicitly preferred by author for this stage.
    if any(c.get('preferred') and not c.get('missing') for c in target.get('candidates', ())):
        return True
    return False


def _has_type_network_work(stage: str, products: dict, context: dict) -> bool:
    """Keep LLM execution if type_network_policy actually has active dynamic rules."""
    if stage != 'type_adaptation':
        return False
    from nw.materials.type_network import POLICY as TYPE_NETWORK_POLICY
    if context.get('type_network_policy') != TYPE_NETWORK_POLICY:
        return False
    selection = products.get('type_selection', {}).get('products', {})
    return bool(selection.get('adaptation_inputs'))


def _book_chosen_genre_ids(package: dict, context: dict) -> list[str]:
    gov = (context.get('governance_inputs') or {}).get('type_selection', {})
    plan_types = [str(r.get('id', '')).strip() for r in (gov.get('creation_plan', {}).get('types') or []) if r.get('id')]
    if plan_types:
        return plan_types
    cfg = gov.get('project_config') or {}
    if cfg.get('genre_ids'):
        return [str(x).strip() for x in cfg['genre_ids'] if str(x).strip()]
    policy_types = (package.get('production_method_policy') or {}).get('type_ids') or []
    return [str(x).strip() for x in policy_types if str(x).strip()]


def can_auto_compile_stage(
    stage: str,
    package: dict,
    products: dict,
    context: dict,
    method_plan: dict | None,
) -> bool:
    """Return True when a stage can be compiled deterministically with 0 LLM calls."""
    if context.get('creative_workflow_policy') != POLICY:
        return False
    scope = package.get('scope', 'chapter')
    hierarchy = bool(package.get('planning_hierarchy'))
    if _has_active_method_work(method_plan, stage, context):
        return False

    # 1. Volume & chapter scopes: ALWAYS inherit frozen parent type_selection & type_adaptation.
    if stage in ('type_selection', 'type_adaptation') and hierarchy and scope != 'book':
        inherited_fields = context.get('hierarchy_inherited_types', {}).get(stage)
        parent_stage = next(
            (r for r in (package.get('parent_material_work') or {}).get('stages', []) if r.get('stage') == stage),
            None,
        )
        return bool(inherited_fields and parent_stage)

    # 2. Book scope: compile type_selection directly from frozen wizard genres / creation_plan.
    if stage == 'type_selection' and scope == 'book':
        if not _book_chosen_genre_ids(package, context):
            return False
        # Verify no required book-level material explicitly needs type_selection execution.
        if any(m.get('request', {}).get('disposition') == 'required'
               and m.get('profile') in ('type_identity', 'brief')
               for m in package.get('materials', ())):
            return False
        return True

    # 3. Book scope: compile type_adaptation automatically for single-genre paths.
    if stage == 'type_adaptation' and scope == 'book':
        if _has_type_network_work(stage, products, context):
            return False
        from nw.studio.catalog import single_genre_path
        gov_ts = (context.get('governance_inputs') or {}).get('type_selection', {})
        genre_ids = _book_chosen_genre_ids(package, context)
        if not (gov_ts.get('single_genre_selection') or single_genre_path(genre_ids)):
            # Multi-genre fusion (2+ main genres) runs focused reconciliation if needed.
            return False
        if any(m.get('request', {}).get('disposition') == 'required'
               and m.get('profile') in ('type_combination', 'type_link', 'type_expression')
               for m in package.get('materials', ())):
            return False
        return True

    # 4. Volume scope: bind_scope is strictly empty by contract (planning_hierarchy + volume).
    if stage == 'bind_scope' and hierarchy and scope == 'volume':
        if package.get('materials'):
            return False
        return True

    return False


def _build_book_type_selection(package: dict, context: dict) -> dict:
    from nw.studio.catalog import option_map, type_map

    gov = (context.get('governance_inputs') or {}).get('type_selection', {})
    plan = gov.get('creation_plan') or {}
    known_types = type_map()
    plan_types = plan.get('types') or [
        {'id': gid, 'name': (known_types.get(gid) or {}).get('name', gid)}
        for gid in _book_chosen_genre_ids(package, context)
    ]
    raw_project_config = gov.get('project_config')
    project_config = deepcopy(raw_project_config) if isinstance(raw_project_config, dict) else None
    brief = package.get('brief') or {}
    direction = (context.get('approved_direction') or {}).get('candidate') or {}
    brief_hint = (direction.get('premise') or brief.get('text') or '').strip()[:80]

    selection: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    concepts: list[dict[str, Any]] = []
    boundaries: list[str] = []

    # First emit chosen genres in exact wizard order (satisfies validate_selected_types).
    for idx, row in enumerate(plan_types):
        ident = str(row.get('id', '')).strip()
        if not ident or ident in seen_ids:
            continue
        seen_ids.add(ident)
        meta = known_types.get(ident) or {}
        label = str(row.get('name') or meta.get('name') or ident)
        role_hint = '主类型' if idx == 0 else ('子类型' if meta.get('parent_id') else '副类型')
        defn = str(meta.get('definition') or '').strip()[:100]
        basis = f"作者立项选定{role_hint}「{label}」" + (f"（{defn}）" if defn else '') + (
            f"，服务故事前提：{brief_hint}" if brief_hint else ''
        )
        selection.append({'id': ident, 'label': label, 'basis': basis})
        features = [str(f).strip() for f in (meta.get('features') or []) if str(f).strip()]
        concepts.append({
            'id': f'concept_{ident.lower()}',
            'label': f'{label}核心体验承诺',
            'type_refs': [ident],
            'activation_basis': (features[0] if features else f'按{label}核心冲突与读者期待组织全书主线')[:160],
        })
        for ex in (meta.get('excludes') or [])[:2]:
            ex_text = str(ex).strip()
            if ex_text and ex_text not in boundaries:
                boundaries.append(f'【{label}禁区】{ex_text}')

    # Next emit any typed non-genre IDs from project_config so configuration_binding matches 100%.
    if project_config is not None:
        slot_lookup = {
            'mechanism_ids': ('hook', '核心机制'),
            'structure_ids': ('structure', '结构模式'),
            'style_ids': ('style', '文风基调'),
            'tone_ids': ('tone', '叙事语气'),
        }
        pref_by_id = {str(p.get('id')): p for p in (plan.get('preferences') or []) if p.get('id')}
        for cfg_key, (slot, zh_kind) in slot_lookup.items():
            opt_by_id = {v['id']: v for v in option_map(slot).values() if isinstance(v, dict) and v.get('id')}
            for ident in project_config.get(cfg_key, ()):
                if ident in seen_ids:
                    continue
                seen_ids.add(ident)
                pref = pref_by_id.get(ident) or opt_by_id.get(ident) or {}
                label = str(pref.get('name') or ident)
                selection.append({
                    'id': ident,
                    'label': label,
                    'basis': f'作者立项选定{zh_kind}「{label}」，已冻结进入对应创作步骤。',
                })

    if brief.get('constraints'):
        boundaries.append(f"【作者硬约束】{str(brief['constraints']).strip()[:160]}")
    if not boundaries:
        boundaries.append('严守所选类型核心读者承诺，不违背立项设定与硬约束。')

    result: dict[str, Any] = {
        'selection': selection,
        'concepts': concepts,
        'boundaries': boundaries,
        '_uses': [],
        '_excluded': [],
        '_requirements': [],
        '_receipts': [],
        '_criteria': [],
    }
    if project_config is not None:
        result['_governance'] = {'project_config': project_config}
    return result


def _build_book_type_adaptation(package: dict, products: dict, context: dict) -> dict:
    ts = products['type_selection']['products']
    genre_ids = [
        r['id'] for r in ts.get('selection', [])
        if r['id'] in (ts.get('_governance', {}).get('project_config', {}).get('genre_ids') or [])
    ] or [r['id'] for r in ts.get('selection', [])[:2]]
    direction = (context.get('approved_direction') or {}).get('candidate') or {}
    length_ctx = package.get('length_context') or {}
    brief_text = str((package.get('brief') or {}).get('text') or '').strip()[:240]
    params: dict[str, Any] = {
        'mode': 'single_genre_path_frozen',
        'story_premise': direction.get('premise') or brief_text or '围绕立项构想推进故事',
        'primary_drive': direction.get('long_term_drive') or direction.get('conflict') or '围绕立项构想推进主线冲突与代价',
        'pacing_policy': str(length_ctx.get('tier_label') or length_ctx.get('length_mode') or 'rolling_outline'),
    }
    adaptations = [{
        'id': 'adapt_primary_contract',
        'type_refs': genre_ids,
        'parameters': params,
        'limits': [
            '单类型路径无跨题材规则冲突，后续世界、人物、卷章直接落实核心机制与代价',
            '所有设定须接受世界规则与人物动机约束，不得用机械降神化解冲突',
        ],
    }]
    focuses = []
    for idx, concept in enumerate(ts.get('concepts', [])[:3], start=1):
        focuses.append({
            'id': f'focus_{idx}',
            'concept': concept['id'],
            'from_focus': '立项静态类型标签',
            'to_focus': '可演进的剧情冲突、人物抉择与正文可感表现',
            'application': direction.get('type_fit') or concept['activation_basis'],
        })
    if not focuses:
        focuses.append({
            'id': 'focus_1',
            'concept': 'primary_promise',
            'from_focus': '立项概念',
            'to_focus': '剧情与人物因果',
            'application': '围绕核心矛盾与不可逆代价推进全书主线',
        })
    boundaries = [
        '立项类型与偏好为创作承诺而非机械套模板指令，须在具体世界与人物抉择中自然兑现',
    ]
    return {
        'adaptations': adaptations,
        'focuses': focuses,
        'boundaries': boundaries,
        '_uses': [],
        '_excluded': [],
        '_requirements': [],
        '_receipts': [],
        '_criteria': [],
    }


def _build_inherited_type_products(stage: str, package: dict, context: dict) -> dict:
    parent_stage = next(
        r for r in (package.get('parent_material_work') or {}).get('stages', []) if r.get('stage') == stage
    )
    parent_products = parent_stage['products']
    inherited = deepcopy(context['hierarchy_inherited_types'][stage])
    raw: dict[str, Any] = {
        **inherited,
        '_uses': [],
        '_excluded': [],
        '_requirements': [],
        '_receipts': [],
        '_criteria': [],
    }
    if stage == 'type_selection':
        if '_governance' in parent_products:
            raw['_governance'] = deepcopy(parent_products['_governance'])
        elif project_config := (context.get('governance_inputs') or {}).get('type_selection', {}).get('project_config'):
            raw['_governance'] = {'project_config': deepcopy(project_config)}
        if 'adaptation_inputs' in parent_products and context.get('type_network_policy'):
            raw['adaptation_inputs'] = deepcopy(parent_products['adaptation_inputs'])
    return raw


def _build_volume_bind_scope() -> dict:
    return {
        'material_bindings': {},
        'process_bindings': {},
        'method_guidance': [],
        '_uses': [],
        '_excluded': [],
        '_requirements': [],
        '_receipts': [],
        '_criteria': [],
    }


def compile_stage_record(
    stage: str,
    request: Any,
    package: dict,
    products: dict,
    context: dict,
    governance: dict | None,
    method_plan: dict | None,
) -> dict:
    """Deterministically compile a stage record without invoking any LLM."""
    from nw.materials.governance_runtime import check_stage_governance, freeze_report
    from nw.materials.phase_contract import validate_phase
    from nw.materials.semantic_handoff import input_stages
    from nw.production_methods import runtime as project_methods
    from nw.production_methods.selection import finalize

    scope = package['scope']
    hierarchy = bool(package.get('planning_hierarchy'))
    deps = input_stages(stage, products, dynamic_screening=bool(context.get('dynamic_screening')))

    if stage in ('type_selection', 'type_adaptation') and hierarchy and scope != 'book':
        stage_products = _build_inherited_type_products(stage, package, context)
        exec_mode = 'programmatic_inherited'
    elif stage == 'type_selection' and scope == 'book':
        stage_products = _build_book_type_selection(package, context)
        exec_mode = 'programmatic_compiled'
    elif stage == 'type_adaptation' and scope == 'book':
        stage_products = _build_book_type_adaptation(package, products, context)
        exec_mode = 'programmatic_compiled'
    elif stage == 'bind_scope' and hierarchy and scope == 'volume':
        stage_products = _build_volume_bind_scope()
        exec_mode = 'programmatic_finalized'
    else:
        raise ValueError(f'CREATIVE_WORKFLOW: stage {stage} cannot be programmatically compiled in scope {scope}')

    if method_plan is not None:
        stage_products['_method_applications'] = []
        stage_products['_method_receipts'] = []

    raw = {'stage': stage, 'products': stage_products}
    clean, _ = project_methods.split(raw)
    stage_context = {
        **context,
        'allowed_input_stages': deps,
        'require_semantics': True,
        'semantic_contracts': [],
    }
    validate_phase(clean, stage, products, [], stage_context)

    finalized_plan = None
    if method_plan is not None:
        finalized_plan = finalize(method_plan, stage_products)
        project_methods.validate_output(
            raw, stage, products, finalized_plan, context.get('production_method_parents', [])
        )

    gov_report = check_stage_governance(governance, stage, stage_products, products, [], context)
    if gov_report and gov_report['status'] == 'failed':
        bad = [r['rule_id'] for r in gov_report['checks'] if r['status'] == 'failed']
        raise ValueError('MATERIAL_GOVERNANCE: ' + ','.join(dict.fromkeys(bad)))

    upstream_refs = [product_ref(products[k]) for k in deps]
    selection = {
        'before_stage': stage,
        'upstream': upstream_refs,
        'offered': [],
        'selected': [],
        'control_review_sha256': context.get('retrieval_control', {}).get('review', {}).get('sha256'),
    }
    record: dict[str, Any] = {
        'stage': stage,
        'task_id': f'auto:{request.id}:{stage}',
        'execution_mode': exec_mode,
        'products': stage_products,
        'sha256': content_sha256(stage_products),
        'inputs': upstream_refs,
        'semantic_contracts': [],
        'binding_reviews': {},
        'deferred_sources': [],
        'source_selection': selection,
        'source_ids': [],
    }
    if direction := context.get('approved_direction'):
        if stage in ('type_selection', 'type_adaptation'):
            record['approved_direction_sha256'] = direction['sha256']
    if finalized_plan is not None:
        record['production_methods'] = finalized_plan
    if governance:
        record['governance'] = freeze_report(gov_report)
    return record


# ---------- Concrete Creative Workflow Deliverables on plot_design ----------

BOOK_PLOT_EXTRA_FIELDS = frozenset({'opening_plan', 'character_arcs', 'story_segments'})
VOLUME_PLOT_EXTRA_FIELDS = frozenset({'chapter_splits', 'character_arcs'})
CHAPTER_PLOT_EXTRA_FIELDS = frozenset({'character_arcs'})


def extra_plot_field_names(scope: str, context: dict) -> set[str]:
    if context.get('creative_workflow_policy') != POLICY:
        return set()
    if scope == 'book':
        return set(BOOK_PLOT_EXTRA_FIELDS)
    if scope == 'volume':
        return set(VOLUME_PLOT_EXTRA_FIELDS)
    if scope == 'chapter':
        return set(CHAPTER_PLOT_EXTRA_FIELDS)
    return set()


def plot_schema_fields(scope: str) -> dict[str, dict]:
    from nw.materials.phase_schema import TEXT, array, obj, strings

    arc_item = obj({
        **strings('character', 'start_state', 'trigger_event', 'choice', 'cost', 'new_state', 'target_span'),
    })
    if scope == 'book':
        return {
            'opening_plan': obj({
                **strings('hook_moment', 'first_chapter_promise', 'reader_expectation'),
                'golden_three_beats': array(TEXT, 1),
            }),
            'character_arcs': array(arc_item, 1),
            'story_segments': array(obj(strings(
                'id', 'title', 'entry_condition', 'core_events', 'turning_choice', 'ending_state', 'next_driver',
            )), 1),
        }
    if scope == 'volume':
        return {
            'chapter_splits': array(obj({
                'chapter_index': {'type': 'integer', 'minimum': 1},
                **strings('title', 'mission', 'entering_state', 'key_turn', 'ending_change',
                          'handoff_to_next', 'hook_or_foreshadow'),
            }), 1),
            'character_arcs': array(arc_item, 0),
        }
    if scope == 'chapter':
        return {
            'character_arcs': array(arc_item, 0),
        }
    return {}


def plot_output_contract_extras(scope: str) -> dict[str, Any]:
    if scope == 'book':
        return {
            'opening_plan': {
                'hook_moment': '<第一章开篇切入瞬间与冲突钩子>',
                'first_chapter_promise': '<第一章向读者立下的类型与核心悬念承诺>',
                'golden_three_beats': ['<第1章推进节拍>', '<第2章推进节拍>', '<第3章推进节拍>'],
                'reader_expectation': '<读完前三章读者最想追问的问题>',
            },
            'character_arcs': [{
                'character': '<实际人物key>',
                'start_state': '<原状态/信念盲点>',
                'trigger_event': '<触发事件>',
                'choice': '<人物自己作出的选择>',
                'cost': '<付出的具体代价>',
                'new_state': '<变化后的新状态>',
                'target_span': '<落在哪一卷或章节区间>',
            }],
            'story_segments': [{
                'id': 'seg_1',
                'title': '<剧情段标题>',
                'entry_condition': '<进入局面>',
                'core_events': '<核心事件链>',
                'turning_choice': '<关键转折抉择>',
                'ending_state': '<段末新局面>',
                'next_driver': '<为何必须引出下一段>',
            }],
        }
    if scope == 'volume':
        return {
            'chapter_splits': [{
                'chapter_index': 1,
                'title': '<章名>',
                'mission': '<本章承担的核心剧情推进任务>',
                'entering_state': '<承接的进入局面>',
                'key_turn': '<本章关键事件或抉择>',
                'ending_change': '<章末得到的具体结果或变化>',
                'handoff_to_next': '<留给下一章必须接续的问题/钩子>',
                'hook_or_foreshadow': '<本章推进/埋设/回收的钩子或伏笔>',
            }],
            'character_arcs': [],
        }
    if scope == 'chapter':
        return {'character_arcs': []}
    return {}


def plot_instructions(scope: str, handoff: dict | None = None) -> str:
    if scope == 'book':
        return (
            '\n[CREATIVE_WORKFLOW_BOOK] 全书大纲必须额外交付三项可向下级拆解的真实产物：\n'
            '1. opening_plan：明确开篇第一幕切入瞬间、第一章读者承诺、黄金三章节拍（golden_three_beats）与追更期待；\n'
            '2. character_arcs：至少为主角及关键角色建立「原状态→触发事件→自己作出的选择→代价→新状态→落点卷/章」变化链（character 须引用已建人物 key）；\n'
            '3. story_segments：把全书主线拆成可交给卷纲承接的因果剧情段（进入局面→核心事件→转折抉择→段末变化→下段动因）。'
        )
    if scope == 'volume':
        extra = ''
        if handoff and handoff.get('book_segments'):
            extra = '\ncreative_handoff.book_segments 与 book_character_arcs 给出了全书已批准的剧情段与人物弧，请明确本卷承接哪些段落与弧光转折。'
        return (
            '\n[CREATIVE_WORKFLOW_VOLUME] 卷纲必须交付 chapter_splits（逐章任务切分表）：\n'
            '按剧情推进切分本卷近期可写章节，每章写清 chapter_index、title、mission（本章负责哪件事）、'
            'entering_state、key_turn、ending_change（章末得到什么结果）、handoff_to_next（下一章凭什么接上）'
            '与 hook_or_foreshadow。绝不允许只交空泛卷简介。' + extra
        )
    if scope == 'chapter':
        extra = ''
        if handoff and handoff.get('assigned_chapter_split'):
            extra = (
                '\ncreative_handoff.assigned_chapter_split 是已批准卷纲切分给本章的明确任务，'
                '请直接围绕该任务、entering_state、ending_change 与 handoff_to_next 展开本章章卡与 event_nodes。'
            )
        if handoff and handoff.get('opening_plan'):
            extra += '\n当前处于开篇黄金三章区间，请同时核对 creative_handoff.opening_plan 的开篇承诺与节奏节拍。'
        return (
            '\n[CREATIVE_WORKFLOW_CHAPTER] 章纲聚焦「本章承接什么→通过哪些事件和选择走到结果→留下什么给下一章」，'
            '若本章触发关键人物弧光转折请在 character_arcs 记录对应变化。' + extra
        )
    return ''


def validate_plot_deliverables(value: dict, products: dict, context: dict) -> None:
    if context.get('creative_workflow_policy') != POLICY:
        return
    from nw.materials.phase_contract import require
    from nw.task_models import _text

    scope = context.get('scope', 'chapter')
    people = {r['key'] for r in products.get('character_design', {}).get('products', {}).get('members', [])}
    people |= {r['card_id'] for r in context.get('approved_cards', []) if r['kind'] == 'character'}

    def check_arcs(arcs: Any, *, required: bool) -> None:
        if required:
            require(isinstance(arcs, list) and bool(arcs), '全书大纲须至少交付一条关键人物弧光变化链（character_arcs）')
        elif arcs is None:
            return
        else:
            require(isinstance(arcs, list), 'character_arcs 须为列表')
        for arc in arcs:
            require(
                isinstance(arc, dict)
                and set(arc) == {'character', 'start_state', 'trigger_event', 'choice', 'cost', 'new_state', 'target_span'}
                and all(_text(arc[k]) for k in arc)
                and (not people or arc['character'] in people),
                '人物弧光须引用实际人物 key，并写清原状态→触发→选择→代价→新状态→落点',
            )

    if scope == 'book':
        opening = value.get('opening_plan')
        require(
            isinstance(opening, dict)
            and set(opening) == {'hook_moment', 'first_chapter_promise', 'golden_three_beats', 'reader_expectation'}
            and all(_text(opening[k]) for k in ('hook_moment', 'first_chapter_promise', 'reader_expectation'))
            and isinstance(opening['golden_three_beats'], list)
            and bool(opening['golden_three_beats'])
            and all(_text(b) for b in opening['golden_three_beats']),
            '全书大纲须交付开篇与黄金三章设计（opening_plan）',
        )
        check_arcs(value.get('character_arcs'), required=True)
        segments = value.get('story_segments')
        require(isinstance(segments, list) and bool(segments), '全书大纲须交付可拆分的因果剧情段（story_segments）')
        seen_seg: set[str] = set()
        for seg in segments:
            require(
                isinstance(seg, dict)
                and set(seg) == {'id', 'title', 'entry_condition', 'core_events', 'turning_choice', 'ending_state', 'next_driver'}
                and all(_text(seg[k]) for k in seg)
                and seg['id'] not in seen_seg,
                '剧情段须包含唯一 id、进入条件、核心事件、转折抉择、段末状态与下段动因',
            )
            seen_seg.add(seg['id'])

    elif scope == 'volume':
        splits = value.get('chapter_splits')
        require(isinstance(splits, list) and bool(splits), '卷纲须交付逐章任务切分表（chapter_splits）')
        seen_idx: set[int] = set()
        for item in splits:
            require(
                isinstance(item, dict)
                and set(item) == {
                    'chapter_index', 'title', 'mission', 'entering_state',
                    'key_turn', 'ending_change', 'handoff_to_next', 'hook_or_foreshadow',
                }
                and type(item['chapter_index']) is int
                and item['chapter_index'] >= 1
                and item['chapter_index'] not in seen_idx
                and all(_text(item[k]) for k in (
                    'title', 'mission', 'entering_state', 'key_turn',
                    'ending_change', 'handoff_to_next', 'hook_or_foreshadow',
                )),
                '卷纲逐章切分须为每章填写唯一正整数章号、核心任务、进入状态、关键转折、章末变化与下章交接',
            )
            seen_idx.add(item['chapter_index'])
        if 'character_arcs' in value:
            check_arcs(value.get('character_arcs'), required=False)

    elif scope == 'chapter':
        if 'character_arcs' in value:
            check_arcs(value.get('character_arcs'), required=False)


def extract_creative_handoff(package: dict) -> dict | None:
    """Extract creative outline deliverables (story_segments, character_arcs, chapter_splits, opening_plan) from parent."""
    if package.get('creative_workflow_policy') != POLICY:
        return None
    parent_stages = (package.get('parent_material_work') or {}).get('stages') or []
    parent_plot = next((r.get('products') for r in parent_stages if r.get('stage') == 'plot_design'), None)
    if not isinstance(parent_plot, dict):
        return None
    handoff: dict[str, Any] = {}
    scope = package.get('scope', 'chapter')
    if scope == 'volume':
        if parent_plot.get('story_segments'):
            handoff['book_segments'] = deepcopy(parent_plot['story_segments'])
        if parent_plot.get('character_arcs'):
            handoff['book_character_arcs'] = deepcopy(parent_plot['character_arcs'])
        if parent_plot.get('opening_plan'):
            handoff['opening_plan'] = deepcopy(parent_plot['opening_plan'])
    elif scope == 'chapter':
        target_index = package.get('chapter_target_index')
        splits = parent_plot.get('chapter_splits') or []
        if splits:
            handoff['volume_chapter_splits'] = deepcopy(splits)
            if isinstance(target_index, int):
                matched = next((row for row in splits if row.get('chapter_index') == target_index), None)
                if matched:
                    handoff['assigned_chapter_split'] = deepcopy(matched)
        if parent_plot.get('character_arcs'):
            handoff['parent_character_arcs'] = deepcopy(parent_plot['character_arcs'])
        if parent_plot.get('opening_plan') and (target_index is None or target_index <= 3):
            handoff['opening_plan'] = deepcopy(parent_plot['opening_plan'])
    return handoff or None
