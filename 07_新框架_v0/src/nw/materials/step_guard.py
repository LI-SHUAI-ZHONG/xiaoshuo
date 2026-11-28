"""Cross-step anti-forgetting ledger, joint-material coordination, multi-character ensemble guards, and consistency checks."""
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

_BAD_PLACEHOLDERS = frozenset({
    'todo', 'tbd', '待定', '待补充', '未知变化', '<填写>', '【待补】', '【待填写】', '【待补正文】',
})
_PERSONALITY_ATTRS = frozenset({
    'personality', 'core_personality', 'behavior', 'stance', 'loyalty', 'value_priority',
    '性格', '核心性格', '立场', '信念', '价值观',
})
_UNMOTIVATED_MARKERS = frozenset({
    'none', 'null', '无', '无事件', '无故', '自然变化', '自然转变', '突然改变', '突然暴怒', '无故动摇',
})
_TIME_TRANSITION_CUES = (
    '时间跳跃', '跳时', '数日后', '次日', '翌日', '隔日', '三天后', '三日后', '数月后', '多年后',
    '年后', '月后', '日后', '数小时后', '半日后', '天亮后', '入夜后', '倒叙', '回忆', '前夜',
    '此前', '往事', 'flashback', 'time_jump', 'later', 'earlier',
)


def _clip(text: Any, limit: int = 96) -> str:
    value = str(text or '').strip()
    return value if len(value) <= limit else value[:limit - 1] + '…'


def _is_placeholder(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    stripped = val.strip()
    return stripped.casefold() in _BAD_PLACEHOLDERS or '<填写' in stripped or '【待补' in stripped


def _character_map(products: dict, context: dict) -> dict[str, dict]:
    """Collect character card bodies keyed by entity ID from character_design and approved_cards."""
    chars: dict[str, dict] = {}
    for card in context.get('approved_cards', ()):
        if isinstance(card, dict) and card.get('kind') == 'character' and isinstance(card.get('body'), dict):
            cid = card.get('card_id') or card.get('key', '')
            if cid:
                chars[str(cid)] = card['body']
    cd = products.get('character_design', {}).get('products', {})
    for m in cd.get('members', ()):
        if isinstance(m, dict) and m.get('kind', 'character') == 'character' and isinstance(m.get('body'), dict):
            cid = m.get('key') or m.get('card_id', '')
            if cid:
                chars[str(cid)] = m['body']
    return chars


def _capability_map(products: dict) -> dict[str, dict]:
    cd = products.get('character_design', {}).get('products', {})
    return {
        str(c['entity']): c
        for c in cd.get('capabilities', ())
        if isinstance(c, dict) and c.get('entity')
    }


def _non_actors(products: dict) -> set[str]:
    return {ent for ent, cap in _capability_map(products).items() if cap.get('can_act') is False}


def _restricted_cards(products: dict, context: dict) -> list[dict]:
    """Gather cards with non-public visibility (holders or explicit author_only on world/character/promise)."""
    items: list[dict] = []
    seen: set[str] = set()
    for card in context.get('approved_cards', ()):
        if not isinstance(card, dict) or not isinstance(card.get('body'), dict):
            continue
        cid = str(card.get('card_id') or card.get('key') or '')
        kind = card.get('kind', '')
        vis = card['body'].get('visibility', 'public')
        if cid and cid not in seen and vis in ('holders', 'author_only') and kind in ('world', 'character', 'promise', 'plot'):
            seen.add(cid)
            items.append({'id': cid, 'kind': kind, 'visibility': vis,
                          'holders': list(card['body'].get('holders', ())), 'body': card['body']})
    for stage_name in ('world_design', 'character_design', 'plot_design'):
        st_prod = products.get(stage_name, {}).get('products', {})
        for m in st_prod.get('members', ()):
            if not isinstance(m, dict) or not isinstance(m.get('body'), dict):
                continue
            cid = str(m.get('key') or m.get('card_id') or '')
            kind = m.get('kind', 'character' if stage_name == 'character_design' else 'world')
            vis = m['body'].get('visibility')
            if cid and cid not in seen and vis in ('holders', 'author_only') and kind in ('world', 'character', 'promise'):
                seen.add(cid)
                items.append({'id': cid, 'kind': kind, 'visibility': vis,
                              'holders': list(m['body'].get('holders', ())), 'body': m['body']})
    return items


def _build_character_voice_guard(products: dict, context: dict) -> dict | None:
    chars = _character_map(products, context)
    if not chars:
        return None
    profiles: list[dict[str, Any]] = []
    for cid, body in list(chars.items())[:8]:
        voice = _clip(body.get('voice') or body.get('voice_traits') or body.get('speech_pattern') or '', 80)
        personality = _clip(
            body.get('behavior') or body.get('core_personality') or body.get('personality') or body.get('flaw') or '',
            80,
        )
        boundaries = _clip(body.get('boundaries') or '', 80)
        change_cond = _clip(body.get('change_conditions') or '', 80)
        raw_kb = body.get('knowledge_boundary') or ''
        if raw_kb:
            kb = _clip(raw_kb, 80)
        elif body.get('visibility') == 'holders' and body.get('holders'):
            kb = _clip('仅限知情者:' + ','.join(str(h) for h in body['holders'][:4]), 80)
        elif body.get('unknowns'):
            kb = _clip('未知盲区:' + '；'.join(str(u) for u in body['unknowns'][:3]), 80)
        else:
            kb = ''
        if any((voice, personality, boundaries, change_cond, kb)):
            prof: dict[str, Any] = {
                'entity': cid,
                'voice_traits': voice,
                'core_personality': personality,
                'knowledge_boundary': kb,
            }
            if body.get('name'):
                prof['name'] = _clip(body['name'], 40)
            if boundaries:
                prof['value_boundaries'] = boundaries
            if change_cond:
                prof['change_conditions'] = change_cond
            profiles.append(prof)
    if not profiles:
        return None
    return {
        'profiles': profiles,
        'rule': (
            '同一角色的嗓音特征(voice)、核心性格基线(behavior/boundaries)和知情范围在跨场与跨步中必须保持一致；'
            '性格或立场转向必须满足change_conditions并有明确驱动事件；'
            '角色在心理、行动与对白中不得获知或调用其知情范围之外的信息。'
        ),
    }


def _build_foreshadow_reminder(stage: str, products: dict, context: dict) -> dict | None:
    pd = products.get('plot_design', {}).get('products', {})
    promises = list(pd.get('promise_plan', ())) or list(context.get('promise_plan', ()))
    if not promises:
        return None

    sd = products.get('scene_design', {}).get('products', {})
    current_scene = str(context.get('current_scene') or '').strip()
    selected_by_scene = {
        str(r['scene']): str(r['event'])
        for r in sd.get('selected_events', ())
        if isinstance(r, dict) and r.get('scene') and r.get('event')
    }
    active_events: set[str] = {str(e) for e in context.get('current_events', ()) if e}
    if context.get('current_event'):
        active_events.add(str(context['current_event']))
    if current_scene and current_scene in selected_by_scene:
        active_events.add(selected_by_scene[current_scene])
    elif not current_scene:
        active_events.update(selected_by_scene.values())

    current_chapter = context.get('current_chapter')
    if current_chapter is None:
        chapters = sd.get('chapters', ())
        if chapters and isinstance(chapters[0], dict) and type(chapters[0].get('index')) is int:
            current_chapter = chapters[0]['index']
    current_scene_idx = context.get('current_scene_index')
    overdue_limit = int(context.get('foreshadow_overdue_limit', 5))

    resolved_ids = {str(x) for x in context.get('resolved_promises', ())}
    hinted_ids = {str(x) for x in context.get('hinted_promises', ())}

    counts = {'planted': 0, 'hinted': 0, 'paid_off': 0}
    due_this_scene: list[dict[str, Any]] = []
    overdue_warnings: list[dict[str, Any]] = []
    still_open: list[str] = []

    for p in promises:
        if not isinstance(p, dict):
            continue
        pid = str(p.get('promise') or p.get('id') or '').strip()
        rid = str(p.get('id') or pid).strip()
        raw_status = str(p.get('status') or '').strip().lower()
        if raw_status in ('paid_off', 'resolved', 'completed') or pid in resolved_ids or rid in resolved_ids:
            status = 'paid_off'
        elif raw_status == 'hinted' or pid in hinted_ids or rid in hinted_ids:
            status = 'hinted'
        else:
            status = 'planted'
        counts[status] += 1
        if status == 'paid_off':
            continue

        payoff_scene = str(p.get('payoff_scene') or '').strip()
        payoff_event = str(p.get('payoff_event') or '').strip()
        payoff_chapter = p.get('payoff_chapter')
        plant_ref = str(p.get('plant_scene') or p.get('plant_event') or '')

        is_due = False
        if current_scene and (payoff_scene == current_scene or payoff_event == current_scene):
            is_due = True
        elif payoff_event and payoff_event in active_events:
            is_due = True
        elif type(current_chapter) is int and type(payoff_chapter) is int and current_chapter == payoff_chapter:
            is_due = True

        if is_due:
            due_item: dict[str, Any] = {
                'promise': _clip(pid, 80),
                'status': status,
                'plant_scene': plant_ref,
            }
            if p.get('setup'):
                due_item['setup'] = _clip(p['setup'], 64)
            if p.get('payoff'):
                due_item['payoff'] = _clip(p['payoff'], 64)
            due_this_scene.append(due_item)
        else:
            still_open.append(_clip(pid or p.get('setup', ''), 60))

        # Overdue detection by chapter window or scene span
        plant_ch = p.get('plant_chapter')
        window = p.get('payoff_window')
        overdue_reason = ''
        if type(current_chapter) is int and type(plant_ch) is int:
            elapsed_ch = current_chapter - plant_ch
            if isinstance(window, dict) and type(window.get('max_offset')) is int and elapsed_ch > window['max_offset']:
                overdue_reason = f'超出回收窗口上限({window["max_offset"]}章)，已滞后{elapsed_ch}章'
            elif type(payoff_chapter) is int and current_chapter > payoff_chapter:
                overdue_reason = f'超过预定回收章(第{payoff_chapter}章)，当前第{current_chapter}章'
            elif window is None and payoff_chapter is None and elapsed_ch > overdue_limit:
                overdue_reason = f'已连续{elapsed_ch}章未回收(预警阈值{overdue_limit}章)'
        if not overdue_reason and type(current_scene_idx) is int and type(p.get('plant_scene_index')) is int:
            elapsed_sc = current_scene_idx - p['plant_scene_index']
            if elapsed_sc > overdue_limit:
                overdue_reason = f'已连续{elapsed_sc}场未回收(预警阈值{overdue_limit}场)'
        if overdue_reason:
            overdue_warnings.append({
                'promise': _clip(pid, 80),
                'status': status,
                'reason': overdue_reason,
            })

    return {
        'lifecycle_counts': counts,
        'due_this_scene': due_this_scene,
        'overdue_warnings': overdue_warnings[:6],
        'still_open': still_open[:8],
        'rule': (
            '伏笔三态(planted已埋设/hinted已暗示/paid_off已回收)全链路追踪：'
            '本场标记为due_this_scene的待回收伏笔必须在正文中兑现或显式推迟；'
            '超期预警(overdue_warnings)伏笔须优先推进；已埋伏笔不得矛盾覆盖，新埋伏笔须记录plant_scene。'
        ),
    }


def build_multi_character_coordination(stage: str, products: dict, context: dict) -> dict | None:
    """
    Coordinate 2+ active characters in ensemble scenes/steps so dialogue voices,
    knowledge boundaries, action capabilities, and emotional reactions never cross-contaminate.
    """
    if stage in ('type_selection', 'type_adaptation', 'world_design', 'character_design', 'static_relations', 'plot_design'):
        return None

    chars = _character_map(products, context)
    cap_map = _capability_map(products)
    non_actors = sorted(_non_actors(products))
    current_scene = str(context.get('current_scene') or '').strip()

    sd = products.get('scene_design', {}).get('products', {})
    scene_ensembles: list[dict[str, Any]] = []
    active_set: list[str] = []

    def _add_active(cid: str) -> None:
        if cid and cid not in active_set and cid not in non_actors:
            active_set.append(cid)

    scene_cards = list(sd.get('members', ())) or list(context.get('scene_cards', ()))
    for sc in scene_cards:
        if not isinstance(sc, dict) or not isinstance(sc.get('body'), dict):
            continue
        sc_key = str(sc.get('key') or sc.get('card_id') or '')
        if current_scene and sc_key != current_scene:
            continue
        body = sc['body']
        pov = str(body.get('pov') or '')
        participants = list(dict.fromkeys([c for c in (pov, *(body.get('characters') or ())) if c]))
        if len(participants) >= 2:
            goals = {
                str(k): _clip(v, 60)
                for k, v in (body.get('character_goals') or {}).items()
                if k in participants
            }
            scene_ensembles.append({
                'scene': sc_key,
                'pov': pov,
                'participants': participants,
                'character_goals': goals,
            })
            for p in participants:
                _add_active(p)

    if not active_set:
        for cid in context.get('active_characters', ()):
            _add_active(str(cid))

    if len(active_set) < 2:
        ed_cands = products.get('event_design', {}).get('products', {}).get('candidates', ())
        pd_nodes = products.get('plot_design', {}).get('products', {}).get('event_nodes', ())
        for ev in (*ed_cands, *pd_nodes):
            if isinstance(ev, dict) and isinstance(ev.get('actors'), list) and len(ev['actors']) >= 2:
                for a in ev['actors']:
                    _add_active(str(a))

    if len(active_set) < 2 and stage in ('expression_design', 'writing') and not scene_cards:
        for cid, body in chars.items():
            if body.get('visibility', 'public') != 'author_only':
                _add_active(cid)

    if len(active_set) < 2:
        return None

    active_chars = active_set[:8]
    personas: list[dict[str, Any]] = []
    for cid in active_chars:
        body = chars.get(cid, {})
        cap = cap_map.get(cid, {})
        personas.append({
            'entity': cid,
            'name': _clip(body.get('name', cid), 32),
            'voice': _clip(body.get('voice') or body.get('voice_traits') or body.get('speech_pattern') or '', 72),
            'temperament': _clip(body.get('behavior') or body.get('core_personality') or body.get('personality') or '', 72),
            'change_conditions': _clip(body.get('change_conditions') or '', 72),
            'can_act': cap.get('can_act', True),
            'ability_limits': [_clip(lim, 48) for lim in cap.get('limits', ())[:3]],
        })

    # Extract inter-character static relations among active characters
    sr_rels = products.get('static_relations', {}).get('products', {}).get('relations', ())
    pb_rels = products.get('plot_design', {}).get('products', {}).get('static_bindings', ())
    inter_relations: list[dict[str, str]] = []
    for rel in (*sr_rels, *pb_rels):
        if not isinstance(rel, dict):
            continue
        src_e, tgt_e = str(rel.get('source') or ''), str(rel.get('target') or '')
        if src_e in active_chars and tgt_e in active_chars:
            inter_relations.append({
                'pair': f'{src_e}->{tgt_e}',
                'relation': _clip(rel.get('relation', ''), 48),
                'condition': _clip(rel.get('condition', ''), 64),
            })

    # Compute information asymmetry across active characters
    asymmetry: list[dict[str, Any]] = []
    for item in _restricted_cards(products, context):
        if item['visibility'] == 'holders':
            holders = set(str(h) for h in item['holders'])
            known_by = [c for c in active_chars if c in holders]
            hidden_from = [c for c in active_chars if c not in holders]
            if known_by and hidden_from:
                asymmetry.append({
                    'item': item['id'],
                    'known_by': known_by,
                    'hidden_from': hidden_from,
                    'guard': f"{','.join(known_by)}未在当场主动披露前，{','.join(hidden_from)}的对白与反应严禁预设知晓{item['id']}",
                })
        elif item['visibility'] == 'author_only':
            asymmetry.append({
                'item': item['id'],
                'known_by': [],
                'hidden_from': list(active_chars),
                'guard': f"{item['id']}为作者层未公开设定，所有在场角色对白均不得直接点破",
            })

    # Also check accepted_state holder-specific knowledge gaps among active characters
    holder_facts: dict[tuple[str, str], set[str]] = {}
    for fact in context.get('accepted_state', ()):
        if isinstance(fact, dict) and fact.get('holder') in active_chars:
            fkey = (str(fact.get('entity_id', '')), str(fact.get('predicate', '')))
            if fkey[0] and fkey[1]:
                holder_facts.setdefault(fkey, set()).add(str(fact['holder']))
    for (ent_id, pred), knowers in list(holder_facts.items())[:6]:
        unknowers = [c for c in active_chars if c not in knowers]
        if knowers and unknowers:
            asymmetry.append({
                'item': f'{ent_id}.{pred}',
                'known_by': sorted(knowers),
                'hidden_from': unknowers,
                'guard': f"{','.join(unknowers)}尚不知晓{ent_id}.{pred}，严禁在对话中超前接话",
            })

    result: dict[str, Any] = {
        'stage': stage,
        'active_characters': active_chars,
        'character_personas': personas,
        'information_asymmetry': asymmetry[:8],
        'rules': [
            '防对白张冠李戴：每句台词的语速、措辞、停顿必须严格对应说话人的voice与当场目标。',
            '防知情交叉污染：information_asymmetry中的受限信息仅known_by掌握，hidden_from角色严禁未卜先知或顺嘴泄露。',
            '防行动能力越界：non_acting_entities及超出ability_limits的动作严禁发生。',
            '防情绪无因突变：群戏中角色激烈情绪转向必须有当场可见触发事件并契合temperament与change_conditions。',
        ],
    }
    if scene_ensembles:
        result['scenes'] = scene_ensembles[:6]
    if inter_relations:
        result['inter_character_relations'] = inter_relations[:8]
    if non_actors:
        result['non_acting_entities'] = non_actors
    return result


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
    if 'character_design' in products and stage in (
        'event_design', 'scene_design', 'state_transition', 'anchor_design', 'expression_design', 'writing'
    ):
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

    # 5. Character voice, personality baseline, and knowledge boundary guard
    if stage in (
        'event_design', 'action_design', 'scene_design', 'state_transition',
        'anchor_design', 'expression_design', 'bind_scope', 'writing',
    ):
        voice_guard = _build_character_voice_guard(products, context)
        if voice_guard is not None:
            ledger['character_voice_guard'] = voice_guard

    # 6. Foreshadowing 3-state lifecycle & payoff/overdue reminder
    if 'promise_continuity' in context:
        if stage in ('plot_design', 'event_design', 'action_design', 'scene_design', 'state_transition',
                     'anchor_design', 'expression_design', 'bind_scope'):
            from nw.materials.promise_continuity import continuation_reminder

            if (foreshadow := continuation_reminder(products, context)) is not None:
                ledger['foreshadow_reminder'] = foreshadow
    elif stage in ('scene_design', 'anchor_design', 'expression_design', 'bind_scope', 'writing'):
        foreshadow = _build_foreshadow_reminder(stage, products, context)
        if foreshadow is not None:
            ledger['foreshadow_reminder'] = foreshadow

    # 7. Multi-character ensemble coordination when 2+ active characters interact
    if stage in (
        'event_design', 'action_design', 'scene_design', 'state_transition',
        'anchor_design', 'expression_design', 'bind_scope', 'writing',
    ):
        multi_coord = build_multi_character_coordination(stage, products, context)
        if multi_coord is not None:
            ledger['multi_char_guard'] = multi_coord

    return ledger or None


def _classify_material_role(stage: str, prof: str, key: str) -> str:
    """Stage-aware role assignment so materials act according to the current step's real responsibility."""
    if stage == 'type_selection':
        return 'drivers' if prof in ('type_identity', 'brief') else 'boundaries'
    if stage == 'type_adaptation':
        if prof in ('type_combination', 'type_link', 'type_expression', 'type_identity'):
            return 'drivers'
        return 'boundaries'
    if stage == 'world_design':
        if prof in ('world', 'type_link', 'type_combination'):
            return 'drivers'
        return 'boundaries'
    if stage == 'character_design':
        if prof in ('character', 'type_link', 'type_combination'):
            return 'drivers'
        return 'boundaries'
    if stage == 'static_relations':
        if prof in ('static_relation', 'static_binding', 'type_link'):
            return 'drivers'
        return 'boundaries'
    if stage in ('plot_design', 'event_design'):
        if prof in ('plot', 'opening', 'promise_process', 'dynamic_relation', 'dynamic_binding',
                    'type_transition', 'type_link', 'type_combination') or (stage == 'event_design' and prof == 'scene'):
            return 'drivers'
        if prof == 'type_expression' and any(tok in key for tok in ('结构', '机制', '伏笔', '悬念', '冲突', 'FORESHADOW', 'STRUCTURE', 'MECHANISM')):
            return 'drivers'
        return 'boundaries'
    if stage in ('action_design', 'state_transition', 'state_propagation'):
        if prof in ('dynamic_relation', 'dynamic_binding', 'type_transition', 'scene', 'character', 'plot'):
            return 'drivers'
        return 'boundaries'
    if stage == 'anchor_design':
        if prof == 'anchor':
            return 'drivers'
        if prof in ('expression', 'type_expression'):
            return 'anchors_and_expression'
        return 'boundaries'
    if stage == 'expression_design':
        if prof in ('expression', 'type_expression'):
            return 'drivers'
        if prof == 'anchor':
            return 'anchors_and_expression'
        return 'boundaries'
    if stage == 'bind_scope':
        if prof in ('material_selection', 'material_conversion', 'usage_process', 'preflight'):
            return 'drivers'
        if prof in ('anchor', 'expression', 'type_expression'):
            return 'anchors_and_expression'
        return 'boundaries'
    # Default / scene_design: preserve classic 3-tier role division.
    if prof in _DRIVER_PROFILES:
        return 'drivers'
    if prof in _BOUNDARY_PROFILES:
        return 'boundaries'
    if prof in _ANCHOR_PROFILES:
        return 'anchors_and_expression'
    return 'boundaries'


def format_writing_continuity_prompt(ledger: dict | None) -> str:
    """Render compact cross-step anti-forgetting guards for Step 15 prose writing."""
    if not ledger:
        return ''
    parts: list[str] = []
    if vg := ledger.get('character_voice_guard'):
        voices = [
            f"{p.get('name') or p['entity']}({p['voice_traits'] or p['core_personality']})"
            for p in vg.get('profiles', ())[:5]
            if p.get('voice_traits') or p.get('core_personality')
        ]
        if voices:
            parts.append('人物声线与基线：' + '；'.join(voices))
    if eg := ledger.get('entity_guard'):
        if eg.get('cannot_act'):
            parts.append('非行动实体禁发主动动作：' + '、'.join(str(x) for x in eg['cannot_act'][:6]))
    if fr := ledger.get('foreshadow_reminder'):
        due = [str(d.get('title') or d.get('promise') or '') for d in fr.get('due_this_scene', ())[:4] if d]
        overdue = [str(o.get('title') or o.get('promise') or '') for o in fr.get('overdue_warnings', ())[:4] if o]
        if due:
            parts.append('本场到期伏笔须自然落笔或交代推迟：' + '、'.join(due))
        if overdue:
            parts.append('超期未回收伏笔优先推进：' + '、'.join(overdue))
    if mc := ledger.get('multi_char_guard'):
        asym = [str(a.get('guard') or '') for a in mc.get('information_asymmetry', ())[:4] if a.get('guard')]
        if asym:
            parts.append('群戏知情隔离：' + '；'.join(asym))
    if not parts:
        return ''
    return '【15写作跨步连续性守卫】' + ' ｜ '.join(parts) + '。'


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
        role = _classify_material_role(stage, prof, str(label))
        if role == 'drivers':
            drivers.append(label)
        elif role == 'anchors_and_expression':
            anchors.append(label)
        else:
            boundaries.append(label)

    plan: dict[str, Any] = {
        'stage': stage,
        'total_sources': len(sources),
        'priority': PRIORITY_HIERARCHY,
        'rule': '多份资料联合使用时：驱动类决定本步核心产物与因果推进，边界类划定世界/知情/能力/步骤职责红线（严禁越步篡改上游目标），锚点表达类落地具象感知与语言质感；不适用项写入_excluded并说明本项目具体差异，局部缺义条款标source_unresolved，严禁硬凑冲突效果或伪造已完成事实。',
        'creative_autonomy_rule': '弹性与原创铁律（126.15）：资料与模板是启发因果与检验质量的脚手架，绝非束缚故事生命力的八股填空；当参考套路与本作人物真实动机/处境张力冲突时，优先服从已接受事实、作者意图与人物真实选择。',
    }
    if drivers:
        plan['drivers'] = drivers[:16]
    if boundaries:
        plan['boundaries'] = boundaries[:16]
    if anchors:
        plan['anchors_and_expression'] = anchors[:16]
    if templates_or_partial:
        plan['needs_instantiation_or_clause_guard'] = templates_or_partial[:16]
    return plan


def _validate_plot_quality(value: dict, products: dict, context: dict) -> None:
    non_actors = _non_actors(products)

    # 1. Direction causal closure & placeholder check
    for direction in value.get('directions', ()):
        if not isinstance(direction, dict):
            continue
        for k in ('conflict', 'choice', 'cost', 'consequence'):
            if _is_placeholder(direction.get(k)):
                raise ValueError(f'MATERIAL_STAGE: unfilled placeholder in plot_design direction.{k}')
        conflict = str(direction.get('conflict') or '').strip()
        choice = str(direction.get('choice') or '').strip()
        consequence = str(direction.get('consequence') or '').strip()
        if consequence and (consequence == conflict or consequence == choice):
            raise ValueError(
                'MATERIAL_STAGE: unclosed causal chain in plot_design direction (consequence repeats conflict/choice)'
            )

    # 2. Event nodes: capability check, causal closure, cycle check, and anti-loop deduplication
    node_order: dict[str, int] = {}
    predecessors: dict[str, str] = {}
    seen_signatures: set[tuple[Any, ...]] = set()
    prior_ids: set[str] = set()
    prior_sigs: set[tuple[Any, ...]] = set()
    for past in context.get('completed_events', ()):
        if isinstance(past, str):
            prior_ids.add(past)
        elif isinstance(past, dict):
            if past.get('id'):
                prior_ids.add(str(past['id']))
            psig = (
                tuple(sorted(str(a) for a in past.get('actors', ()))),
                str(past.get('goal') or '').strip(),
                str(past.get('setting') or '').strip(),
                str(past.get('obstacle') or '').strip(),
                str(past.get('completion_condition') or '').strip(),
            )
            if all(psig[1:]):
                prior_sigs.add(psig)

    for idx, node in enumerate(value.get('event_nodes', ())):
        if not isinstance(node, dict):
            continue
        nid = str(node.get('id') or '')
        if nid in prior_ids:
            raise ValueError(f'MATERIAL_STAGE: event_node {nid} repeats an already completed event (plot loop)')
        for actor in node.get('actors', ()):
            if str(actor) in non_actors:
                raise ValueError(f'MATERIAL_STAGE: non-acting entity {actor} cannot be an event actor in plot_design')
        for k in ('goal', 'obstacle', 'completion_condition'):
            if _is_placeholder(node.get(k)):
                raise ValueError(f'MATERIAL_STAGE: unfilled placeholder in event_node.{k}')
        goal = str(node.get('goal') or '').strip()
        setting = str(node.get('setting') or '').strip()
        obstacle = str(node.get('obstacle') or '').strip()
        comp = str(node.get('completion_condition') or '').strip()
        if goal and comp and goal == comp:
            raise ValueError(
                f'MATERIAL_STAGE: unclosed causal chain in event_node {nid} (completion_condition repeats goal)'
            )
        pred = str(node.get('predecessor') or node.get('cause_event') or '').strip()
        if pred:
            if pred == nid:
                raise ValueError(f'MATERIAL_STAGE: causal self-loop on event_node {nid}')
            predecessors[nid] = pred
        sig = (tuple(sorted(str(a) for a in node.get('actors', ()))), goal, setting, obstacle, comp)
        if all((goal, setting, obstacle, comp)):
            if sig in seen_signatures or sig in prior_sigs:
                raise ValueError(f'MATERIAL_STAGE: duplicate event_node {nid} causes plot loop')
            seen_signatures.add(sig)
        if nid:
            node_order[nid] = idx

    # Detect predecessor cycle or dangling predecessor if explicit predecessor links are present
    for nid, pred in predecessors.items():
        if node_order and pred not in node_order and pred not in prior_ids:
            raise ValueError(f'MATERIAL_STAGE: event_node {nid} references missing cause_event {pred}')
        visited = {nid}
        cur = pred
        while cur in predecessors:
            if cur in visited:
                raise ValueError(f'MATERIAL_STAGE: causal cycle detected involving event_node {nid}')
            visited.add(cur)
            cur = predecessors[cur]

    # 3. Promise plan contradiction & causal order check
    seen_promises: dict[str, tuple[str, str]] = {}
    for p in value.get('promise_plan', ()):
        if not isinstance(p, dict):
            continue
        pid = str(p.get('promise') or p.get('id') or '')
        setup_s = str(p.get('setup') or '').strip()
        payoff_s = str(p.get('payoff') or '').strip()
        if _is_placeholder(setup_s) or _is_placeholder(payoff_s):
            raise ValueError(f'MATERIAL_STAGE: unfilled placeholder in promise_plan {pid}')
        if pid and pid in seen_promises and seen_promises[pid] != (setup_s, payoff_s):
            raise ValueError(f'MATERIAL_STAGE: conflicting promise_plan definitions for {pid}')
        if pid:
            seen_promises[pid] = (setup_s, payoff_s)
        plant_ev = str(p.get('plant_event') or '').strip()
        payoff_ev = str(p.get('payoff_event') or '').strip()
        if plant_ev and payoff_ev:
            win = p.get('payoff_window')
            plant_ch, payoff_ch = p.get('plant_chapter'), p.get('payoff_chapter')
            if plant_ev == payoff_ev and (
                win is None
                or (isinstance(win, dict) and win.get('min_offset', 0) > 0)
                or (type(plant_ch) is int and type(payoff_ch) is int and payoff_ch > plant_ch)
            ):
                raise ValueError(
                    f'MATERIAL_STAGE: promise {pid} cannot plant and pay off in the same event {plant_ev}'
                )
            if plant_ev in node_order and payoff_ev in node_order and node_order[payoff_ev] < node_order[plant_ev]:
                raise ValueError(
                    f'MATERIAL_STAGE: promise {pid} payoff_event {payoff_ev} precedes plant_event {plant_ev}'
                )


def _validate_scene_quality(value: dict, products: dict, context: dict) -> None:
    chars = _character_map(products, context)
    char_ids = set(chars.keys())
    non_actors = _non_actors(products)
    restricted = {item['id']: item for item in _restricted_cards(products, context)}

    scene_bodies: dict[str, dict] = {}
    scene_participants: dict[str, set[str]] = {}
    for m in value.get('members', ()):
        if isinstance(m, dict) and m.get('key') and isinstance(m.get('body'), dict):
            sk = str(m['key'])
            body = m['body']
            scene_bodies[sk] = body
            pov = str(body.get('pov') or '')
            if pov in non_actors:
                raise ValueError(f'MATERIAL_STAGE: non-acting entity {pov} cannot serve as scene POV in {sk}')
            parts = {c for c in (pov, *(str(x) for x in (body.get('characters') or ()))) if c}
            scene_participants[sk] = parts
            # Check explicit secret disclosure violations on scene cards
            for disc_id in body.get('disclosed_items', ()):
                r_item = restricted.get(str(disc_id))
                if r_item and r_item['visibility'] == 'holders' and pov not in r_item['holders']:
                    raise ValueError(
                        f'MATERIAL_STAGE: scene {sk} POV {pov} cannot disclose restricted item {disc_id} outside knowledge boundary'
                    )

    # 1. Same-scene conflicting before_state + placeholder check + participant membership check
    seen_before: dict[tuple[str, str, str], str] = {}
    scene_before_by_entity: dict[tuple[str, str], dict[str, str]] = {}
    for event in value.get('events', ()):
        if not isinstance(event, dict):
            continue
        sc, ent = str(event.get('scene') or ''), str(event.get('entity') or '')
        if sc in scene_participants and ent in char_ids and ent not in scene_participants[sc]:
            raise ValueError(f'MATERIAL_STAGE: event character {ent} is not in scene {sc} participants')
        bstate = event.get('before_state', {})
        if isinstance(bstate, dict):
            ent_state = scene_before_by_entity.setdefault((sc, ent), {})
            for attr, val in bstate.items():
                if _is_placeholder(val):
                    raise ValueError(f'MATERIAL_STAGE: unfilled placeholder in scene_design before_state.{attr}')
                enc = canonical(val)
                key = (sc, ent, str(attr))
                if key in seen_before and seen_before[key] != enc:
                    raise ValueError(
                        f'MATERIAL_STAGE: conflicting before_state on ({sc}, {ent}, {attr}) within scene_design'
                    )
                seen_before[key] = enc
                ent_state[str(attr)] = enc

    # Verify selected_events actors belong to scene participants
    ev_actors_map: dict[str, list[str]] = {}
    for node in products.get('plot_design', {}).get('products', {}).get('event_nodes', ()):
        if isinstance(node, dict) and node.get('id') and isinstance(node.get('actors'), list):
            ev_actors_map[str(node['id'])] = [str(a) for a in node['actors']]
    for cand in products.get('event_design', {}).get('products', {}).get('candidates', ()):
        if isinstance(cand, dict) and cand.get('id') and isinstance(cand.get('actors'), list):
            ev_actors_map[str(cand['id'])] = [str(a) for a in cand['actors']]
    for sel in value.get('selected_events', ()):
        if isinstance(sel, dict) and sel.get('scene') in scene_participants and sel.get('event') in ev_actors_map:
            sc = str(sel['scene'])
            for actor in ev_actors_map[str(sel['event'])]:
                if actor in char_ids and actor not in scene_participants[sc]:
                    raise ValueError(
                        f'MATERIAL_STAGE: selected event actor {actor} is absent from scene {sc} participants'
                    )

    # 2. Cross-scene state/location handoff & timeline continuity checks
    prior_end_states: dict[str, dict[str, str]] = {}
    for ent, st in (context.get('prior_scene_states') or {}).items():
        if isinstance(st, dict):
            prior_end_states[str(ent)] = {str(k): canonical(v) for k, v in st.items()}

    simultaneous_locations: dict[tuple[int, str], str] = {}
    for ch in value.get('chapters', ()):
        if not isinstance(ch, dict):
            continue
        prev_coord: tuple[str, int] | None = None
        for sc_ref in ch.get('scenes', ()):
            if not isinstance(sc_ref, dict):
                continue
            sc_key = str(sc_ref.get('card') or '')
            s_order = sc_ref.get('story_order')
            s_body = scene_bodies.get(sc_key, {})

            # Check story_time vs story_order consistency when story_time is integer-formatted
            raw_time = s_body.get('story_time')
            if isinstance(raw_time, str) and raw_time.strip().lstrip('-').isdigit() and type(s_order) is int:
                if int(raw_time.strip()) != s_order:
                    raise ValueError(
                        f'MATERIAL_STAGE: scene {sc_key} story_time ({raw_time}) conflicts with story_order ({s_order})'
                    )

            # Check simultaneous conflicting locations for the same character at identical story_order
            loc = str(s_body.get('location') or '').strip()
            if loc and type(s_order) is int:
                for part in scene_participants.get(sc_key, ()):
                    loc_key = (s_order, part)
                    if loc_key in simultaneous_locations and simultaneous_locations[loc_key] != loc:
                        raise ValueError(
                            f'MATERIAL_STAGE: character {part} cannot occupy conflicting locations '
                            f'({simultaneous_locations[loc_key]} vs {loc}) at story_order {s_order}'
                        )
                    simultaneous_locations[loc_key] = loc

            # Check unexplained timeline jump within chapter
            has_time_cue = False
            if prev_coord is not None and type(s_order) is int:
                _, prev_order = prev_coord
                delta_order = s_order - prev_order
                cue_blob = ' '.join(
                    str(s_body.get(f) or '') for f in ('title', 'goal', 'entering_state', 'story_time')
                ) + ' ' + ' '.join(str(t) for t in (s_body.get('tags') or ()))
                has_time_cue = any(cue in cue_blob.casefold() for cue in _TIME_TRANSITION_CUES)
                if (delta_order > 1 or delta_order < 0) and not has_time_cue:
                    raise ValueError(
                        f'MATERIAL_STAGE: unexplained timeline jump from story_order {prev_order} '
                        f'to {s_order} in scene {sc_key}'
                    )

            # Check state handoff against prior_end_states when sequential without time jump
            if prior_end_states and not has_time_cue:
                for part in scene_participants.get(sc_key, set()) | set(prior_end_states.keys()):
                    cur_bstate = scene_before_by_entity.get((sc_key, part), {})
                    prev_astate = prior_end_states.get(part, {})
                    for attr, enc_val in cur_bstate.items():
                        if attr in prev_astate and prev_astate[attr] != enc_val:
                            raise ValueError(
                                f'MATERIAL_STAGE: scene {sc_key} before_state on ({part}, {attr}) '
                                f'conflicts with prior scene state without transition'
                            )

            # Advance prior_end_states if scene carries explicit expected_after_state
            if isinstance(s_body.get('expected_after_state'), dict):
                for ent, st in s_body['expected_after_state'].items():
                    if isinstance(st, dict):
                        prior_end_states.setdefault(str(ent), {}).update(
                            {str(k): canonical(v) for k, v in st.items()}
                        )

            if type(s_order) is int:
                prev_coord = (sc_key, s_order)


def _validate_dialogue_and_voice_consistency(stage: str, value: dict, products: dict, context: dict) -> None:
    non_actors = _non_actors(products)
    chars = _character_map(products, context)
    restricted = {item['id']: item for item in _restricted_cards(products, context)}

    sd = products.get('scene_design', {}).get('products', {})
    scene_participants: dict[str, set[str]] = {}
    for m in sd.get('members', ()):
        if isinstance(m, dict) and m.get('key') and isinstance(m.get('body'), dict):
            b = m['body']
            scene_participants[str(m['key'])] = {
                c for c in (str(b.get('pov') or ''), *(str(x) for x in (b.get('characters') or ()))) if c
            }

    transitions = products.get('state_transition', {}).get('products', {}).get('transitions', ())
    changed_entities = {str(t.get('entity')) for t in transitions if isinstance(t, dict) and t.get('entity')}

    for actor in value.get('actors', ()):
        if str(actor) in non_actors:
            raise ValueError(f'MATERIAL_STAGE: non-acting entity {actor} cannot act in {stage}')

    current_sc = str(value.get('scene') or context.get('current_scene') or '')
    for line in value.get('dialogues', ()):
        if not isinstance(line, dict):
            continue
        speaker = str(line.get('speaker') or '')
        sc = str(line.get('scene') or current_sc)
        if speaker in non_actors:
            raise ValueError(f'MATERIAL_STAGE: non-acting entity {speaker} cannot speak dialogue in {stage}')
        if sc and sc in scene_participants and speaker in chars and speaker not in scene_participants[sc]:
            raise ValueError(
                f'MATERIAL_STAGE: dialogue speaker {speaker} is not in scene {sc} participants'
            )
        # Knowledge boundary check on speaker
        for ref_id in line.get('references_restricted', ()) or (
            [line['discloses']] if line.get('discloses') else ()
        ):
            r_item = restricted.get(str(ref_id))
            if r_item:
                if r_item['visibility'] == 'author_only' or (
                    r_item['visibility'] == 'holders' and speaker not in r_item['holders']
                ):
                    raise ValueError(
                        f'MATERIAL_STAGE: speaker {speaker} violated knowledge boundary on {ref_id}'
                    )
        forbidden = context.get('forbidden_knowledge', {}).get(speaker, ())
        utterance = str(line.get('text') or '')
        for secret_tok in forbidden:
            if secret_tok and str(secret_tok) in utterance:
                raise ValueError(
                    f'MATERIAL_STAGE: speaker {speaker} uttered forbidden knowledge outside their boundary'
                )
        # Voice / emotional outburst drift without event trigger
        if speaker in chars:
            expected_voice = str(chars[speaker].get('voice') or chars[speaker].get('voice_traits') or '').strip()
            override_voice = str(line.get('voice_style') or '').strip()
            trigger_ev = str(line.get('trigger_event') or '').strip()
            if (
                expected_voice
                and override_voice
                and override_voice != expected_voice
                and (not trigger_ev or trigger_ev.casefold() in _UNMOTIVATED_MARKERS)
                and speaker not in changed_entities
            ):
                raise ValueError(
                    f'MATERIAL_STAGE: character {speaker} voice drifted from baseline without driving event'
                )
            if line.get('emotion_shift') and (
                not trigger_ev or trigger_ev.casefold() in _UNMOTIVATED_MARKERS
            ) and speaker not in changed_entities:
                raise ValueError(
                    f'MATERIAL_STAGE: character {speaker} emotional shift lacks driving event'
                )


def _validate_writing_consistency(value: dict, products: dict, context: dict) -> None:
    text = value.get('text')
    if isinstance(text, str) and _is_placeholder(text):
        raise ValueError('MATERIAL_STAGE: unfilled placeholder in writing text')

    _validate_dialogue_and_voice_consistency('writing', value, products, context)

    # Check author_only world/promise secrets leaking into POV-restricted prose when pov is known
    pov = str(value.get('pov') or context.get('pov') or '')
    if isinstance(text, str) and text and pov:
        for item in _restricted_cards(products, context):
            if item['visibility'] == 'holders' and pov not in item['holders']:
                secret_val = str(
                    item['body'].get('rule') or item['body'].get('payoff') or item['body'].get('secret') or ''
                ).strip()
                if len(secret_val) >= 6 and secret_val in text:
                    raise ValueError(
                        f'MATERIAL_STAGE: writing text leaks restricted card {item["id"]} to non-holder POV {pov}'
                    )

    pd = products.get('plot_design', {}).get('products', {})
    existing_promises = {
        str(p.get('promise') or p.get('id')): p
        for p in pd.get('promise_plan', ())
        if isinstance(p, dict) and (p.get('promise') or p.get('id'))
    }

    # Check newly planted promises in writing
    for planted in value.get('planted_promises', ()):
        if not isinstance(planted, dict):
            continue
        pid = str(planted.get('promise') or planted.get('id') or '').strip()
        plant_sc = str(planted.get('plant_scene') or planted.get('plant_event') or '').strip()
        if not pid or not plant_sc:
            raise ValueError('MATERIAL_STAGE: newly planted promise in writing requires promise ID and plant_scene')
        if pid in existing_promises:
            old_setup = str(existing_promises[pid].get('setup') or '').strip()
            new_setup = str(planted.get('setup') or '').strip()
            if old_setup and new_setup and old_setup != new_setup:
                raise ValueError(
                    f'MATERIAL_STAGE: writing planted_promises contradicts established setup of promise {pid}'
                )

    # Check due foreshadowing promises when resolved/deferred tracking is supplied
    if isinstance(value.get('resolved_promises'), list) or value.get('enforce_due_promises'):
        reminder = _build_foreshadow_reminder('writing', products, context)
        if reminder and reminder['due_this_scene']:
            resolved = {str(x) for x in (value.get('resolved_promises') or ())}
            deferred = {
                str(d.get('promise') if isinstance(d, dict) else d)
                for d in (value.get('deferred_promises') or ())
            }
            for due in reminder['due_this_scene']:
                due_id = due['promise']
                if due_id not in resolved and due_id not in deferred:
                    raise ValueError(
                        f'MATERIAL_STAGE: due foreshadowing promise {due_id} was neither resolved nor deferred in writing'
                    )


def validate_cross_step_consistency(stage: str, value: dict, products: dict, context: dict) -> None:
    """Reject cross-step state contradictions, character OOC drift, broken causal/foreshadow chains, and placeholders."""
    if context.get('legacy_replay'):
        return

    if stage == 'plot_design':
        _validate_plot_quality(value, products, context)

    elif stage == 'event_design':
        non_actors = _non_actors(products)
        seen_cands: set[tuple[str, str, tuple[str, ...]]] = set()
        for cand in value.get('candidates', ()):
            if not isinstance(cand, dict):
                continue
            for actor in cand.get('actors', ()):
                if str(actor) in non_actors:
                    raise ValueError(
                        f'MATERIAL_STAGE: non-acting entity {actor} cannot be an event actor in event_design'
                    )
            ev_text = str(cand.get('event') or '').strip()
            if _is_placeholder(ev_text):
                raise ValueError('MATERIAL_STAGE: unfilled placeholder in event_design candidate')
            sig = (
                str(cand.get('predecessor') or '').strip(),
                ev_text,
                tuple(sorted(str(a) for a in cand.get('actors', ()))),
            )
            if sig[0] and sig[1]:
                if sig in seen_cands:
                    raise ValueError(f"MATERIAL_STAGE: duplicate event candidate {cand.get('id')} causes plot loop")
                seen_cands.add(sig)

    elif stage == 'scene_design':
        _validate_scene_quality(value, products, context)

    elif stage == 'state_transition':
        chars = _character_map(products, context)
        seen_after: dict[tuple[str, str, str], str] = {}
        for tr in value.get('transitions', ()):
            if not isinstance(tr, dict):
                continue
            sc, ent = str(tr.get('scene') or ''), str(tr.get('entity') or '')
            action_s = str(tr.get('action') or '').strip()
            event_s = str(tr.get('event') or '').strip()
            bstate = tr.get('before_state', {}) if isinstance(tr.get('before_state'), dict) else {}
            astate = tr.get('after_state', {})
            if isinstance(astate, dict):
                for attr, val in astate.items():
                    if _is_placeholder(val):
                        raise ValueError(f'MATERIAL_STAGE: unfilled placeholder in after_state.{attr}')
                    enc = canonical(val)
                    key = (sc, ent, str(attr))
                    if key in seen_after and seen_after[key] != enc:
                        raise ValueError(
                            f'MATERIAL_STAGE: conflicting after_state on ({sc}, {ent}, {attr}) within state_transition'
                        )
                    seen_after[key] = enc

                    # Guard against unmotivated personality/stance drift on characters
                    if (
                        ent in chars
                        and str(attr) in _PERSONALITY_ATTRS
                        and canonical(bstate.get(attr)) != enc
                    ):
                        if (
                            not event_s
                            or not action_s
                            or event_s.casefold() in _UNMOTIVATED_MARKERS
                            or action_s.casefold() in _UNMOTIVATED_MARKERS
                        ):
                            raise ValueError(
                                f'MATERIAL_STAGE: character {ent} personality/stance change on {attr} '
                                f'requires a concrete driving event and action'
                            )

    elif stage == 'expression_design':
        _validate_dialogue_and_voice_consistency('expression_design', value, products, context)

    elif stage == 'writing':
        _validate_writing_consistency(value, products, context)
