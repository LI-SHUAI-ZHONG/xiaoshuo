"""Cross-step anti-forgetting ledger, joint-material coordination, and consistency guards."""
from typing import Any

from nw.task_models import canonical


PRIORITY_HIERARCHY = (
    'accepted_state(已接受正文事实) > brief(作者需求与硬约束) > '
    'upstream_products(前置步骤已冻结产物) > design_ready(合格方法原义) > '
    'reference_template(候选模板，须结合项目输入实例化，禁自动升为已完成事实)'
)

_DRIVER_PROFILES = frozenset({
    'type_identity', 'type_combination', 'type_link', 'plot', 'opening',
    'character', 'scene', 'dynamic_relation', 'dynamic_binding', 'type_transition',
})
_BOUNDARY_PROFILES = frozenset({
    'world', 'static_relation', 'static_binding', 'knowledge', 'pov_process',
    'timeline_process', 'promise_process', 'preflight_process', 'usage_process',
    'material_selection', 'material_conversion', 'preflight', 'continuity',
})
_ANCHOR_PROFILES = frozenset({
    'anchor', 'expression', 'type_expression', 'prose_review', 'scope_review',
    'editor', 'character_editor',
})


def _clip(text: Any, limit: int = 96) -> str:
    value = str(text or '').strip()
    return value if len(value) <= limit else value[:limit - 1] + '…'


def build_continuity_ledger(stage: str, products: dict, deps: list[str], context: dict) -> dict | None:
    """Supply compact cross-step constraints omitted from direct REQUIRES so no step forgets prior bounds."""
    if stage == 'type_selection':
        return None
    ledger: dict[str, Any] = {}
    dep_set = set(deps)

    # 1. Preserve type & adaptation boundaries across mid/late steps that don't directly depend on type stages
    if ('type_selection' not in dep_set or 'type_adaptation' not in dep_set) and (
        'type_selection' in products or 'type_adaptation' in products
    ):
        ts = products.get('type_selection', {}).get('products', {})
        ta = products.get('type_adaptation', {}).get('products', {})
        bounds = [
            *(_clip(b) for b in ts.get('boundaries', ())[:4]),
            *(_clip(b) for b in ta.get('boundaries', ())[:4]),
            *(_clip(lim) for ad in ta.get('adaptations', ())[:3] for lim in ad.get('limits', ())[:2]),
        ]
        selected_ids = [row.get('id') for row in ts.get('selection', ())[:4] if isinstance(row, dict) and row.get('id')]
        if selected_ids or bounds:
            ledger['type_guard'] = {'selected': selected_ids, 'boundaries': list(dict.fromkeys(bounds))[:8]}

    # 2. Preserve world rules & limitations in steps like state_transition / anchor_design where world_design is absent
    if 'world_design' not in dep_set:
        wd = products.get('world_design', {}).get('products', {})
        world_cards = [
            {'key': m['key'], 'rule': _clip(m['body'].get('rule')), 'limits': _clip(m['body'].get('limits'))}
            for m in wd.get('members', ())[:4] if isinstance(m, dict) and isinstance(m.get('body'), dict)
        ]
        if not world_cards:
            world_cards = [
                {'key': c['card_id'], 'rule': _clip(c['body'].get('rule')), 'limits': _clip(c['body'].get('limits'))}
                for c in context.get('approved_cards', ())[:4]
                if isinstance(c, dict) and c.get('kind') == 'world' and isinstance(c.get('body'), dict)
            ]
        lims = [_clip(x) for x in wd.get('limitations', ())[:5]]
        unknowns = [_clip(x) for x in wd.get('unknowns', ())[:4]]
        if world_cards or lims or unknowns:
            ledger['world_guard'] = {'rules': world_cards, 'limitations': lims, 'open_unknowns': unknowns}

    # 3. Preserve plot promises & reader emotion targets in steps like anchor_design where plot_design is absent
    if 'plot_design' not in dep_set and 'plot_design' in products:
        pd = products['plot_design'].get('products', {})
        promises = [
            {
                'promise': p.get('promise'),
                'plant_event': p.get('plant_event'),
                'payoff_event': p.get('payoff_event'),
                'setup': _clip(p.get('setup'), 64),
            }
            for p in pd.get('promise_plan', ())[:4] if isinstance(p, dict)
        ]
        emotions = [
            {
                'event': r.get('event'),
                'shift': f"{r.get('before_emotion', '')}->{r.get('after_emotion', '')}",
                'trigger': _clip(r.get('trigger'), 64),
            }
            for r in pd.get('reader_plan', ())[:4] if isinstance(r, dict)
        ]
        if promises or emotions:
            ledger['plot_guard'] = {'promises': promises, 'reader_emotions': emotions}

    # 4. Compact visibility & capability reminder when characters exist
    if 'character_design' in products and stage in ('event_design', 'scene_design', 'state_transition', 'anchor_design', 'expression_design'):
        cd = products['character_design'].get('products', {})
        private_entities = [
            m['key'] for m in cd.get('members', ())
            if isinstance(m, dict) and isinstance(m.get('body'), dict) and m['body'].get('visibility') != 'public'
        ]
        non_actors = [
            c['entity'] for c in cd.get('capabilities', ())
            if isinstance(c, dict) and c.get('can_act') is False
        ]
        if private_entities or non_actors:
            ledger['entity_guard'] = {'non_public_entities': private_entities, 'cannot_act': non_actors}

    return ledger or None


def build_joint_material_plan(stage: str, sources: list[dict]) -> dict | None:
    """Coordinate 2+ materials in the same step so they combine by role without deadlocking or clashing."""
    if len(sources) < 2:
        return None
    drivers: list[str] = []
    boundaries: list[str] = []
    anchors: list[str] = []
    templates_or_partial: list[str] = []

    for src in sources:
        meta = src.get('source', {})
        label = meta.get('key') or meta.get('id', '')
        prof = meta.get('profile', '')
        has_issues = any(src.get('source_issues', {}).values())
        is_ref = src.get('source_state') != 'design_ready'
        if is_ref or has_issues:
            templates_or_partial.append(label)
        if prof in _DRIVER_PROFILES:
            drivers.append(label)
        elif prof in _BOUNDARY_PROFILES:
            boundaries.append(label)
        elif prof in _ANCHOR_PROFILES:
            anchors.append(label)
        else:
            boundaries.append(label)

    plan: dict[str, Any] = {
        'stage': stage,
        'priority': PRIORITY_HIERARCHY,
        'rule': '多份资料联合使用时：驱动类决定目标与推进，边界类限定规则/知情/能力上限，锚点表达类落地可见细节；不适用项写入_excluded并说明本项目具体差异，局部缺义条款标source_unresolved，严禁硬凑冲突效果或伪造已完成事实。',
    }
    if drivers:
        plan['drivers'] = drivers[:8]
    if boundaries:
        plan['boundaries'] = boundaries[:8]
    if anchors:
        plan['anchors_and_expression'] = anchors[:8]
    if templates_or_partial:
        plan['needs_instantiation_or_clause_guard'] = templates_or_partial[:8]
    return plan


def validate_cross_step_consistency(stage: str, value: dict, products: dict, context: dict) -> None:
    """Reject cross-step state contradictions and placeholder hallucinations."""
    if context.get('legacy_replay'):
        return
    if stage == 'scene_design':
        # Ensure multiple change events on the same (scene, entity) do not claim contradictory before_state
        seen_before: dict[tuple[str, str, str], str] = {}
        for event in value.get('events', ()):
            if not isinstance(event, dict):
                continue
            sc, ent = event.get('scene', ''), event.get('entity', '')
            bstate = event.get('before_state', {})
            if isinstance(bstate, dict):
                for attr, val in bstate.items():
                    enc = canonical(val)
                    key = (sc, ent, str(attr))
                    if key in seen_before and seen_before[key] != enc:
                        raise ValueError(
                            f'MATERIAL_STAGE: conflicting before_state on ({sc}, {ent}, {attr}) within scene_design'
                        )
                    seen_before[key] = enc
    elif stage == 'state_transition':
        # Disallow placeholder tokens masquerading as after_state values and conflicting same-scene transitions
        bad_placeholders = {'todo', 'tbd', '待定', '待补充', '未知变化', '<填写>'}
        seen_after: dict[tuple[str, str, str], str] = {}
        for tr in value.get('transitions', ()):
            if not isinstance(tr, dict):
                continue
            sc, ent = tr.get('scene', ''), tr.get('entity', '')
            astate = tr.get('after_state', {})
            if isinstance(astate, dict):
                for attr, val in astate.items():
                    if isinstance(val, str) and val.strip().casefold() in bad_placeholders:
                        raise ValueError(f'MATERIAL_STAGE: unfilled placeholder in after_state.{attr}')
                    enc = canonical(val)
                    key = (sc, ent, str(attr))
                    if key in seen_after and seen_after[key] != enc:
                        raise ValueError(
                            f'MATERIAL_STAGE: conflicting after_state on ({sc}, {ent}, {attr}) within state_transition'
                        )
                    seen_after[key] = enc
