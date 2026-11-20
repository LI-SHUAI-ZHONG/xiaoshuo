"""Validate source-required project structures without scoring literary effects."""
import json
import re

from nw.materials.scene_actions import MULTI_ACTION_POLICY, selected_action_ids
from nw.task_models import _text,canonical


def require(ok: bool,reason: str) -> None:
    if not ok:raise ValueError('MATERIAL_SEMANTICS: '+reason)


def original(source: dict) -> object:
    raw=source.get('original_text','')
    try:return json.loads(raw)
    except (ValueError,TypeError):return raw


def source_text(source: dict) -> str:
    value=original(source)
    return value if isinstance(value,str) else canonical(value)


def domains(source: dict) -> set[str]:
    """These select artifact containers, never establish a semantic pass."""
    text=source_text(source);result=set()
    if any(word in text for word in ('读者情绪','读者情感')):result.add('reader')
    if '伏笔' in text and any(word in text for word in ('埋设','回收','揭示')):result.add('promise')
    return result


def _rows(value: object,fields: set[str],label: str) -> list[dict]:
    require(isinstance(value,list) and bool(value),label+' needs actual project rows')
    for row in value:
        require(isinstance(row,dict) and set(row)==fields,label+' has incomplete or invented fields')
    return value


def _reader(value: dict,sources: list[dict]) -> None:
    fields={'id','event','order','information','before_emotion','after_emotion','trigger','intended_effect','check'}
    rows=_rows(value['reader_plan'],fields,'reader plan')
    events={r['id'] for r in value['event_nodes']};seen=set();orders=set()
    for row in rows:
        require(all(_text(row[k]) for k in fields-{'order'}) and row['id'] not in seen
                and row['event'] in events and type(row['order']) is int and row['order']>0
                and row['order'] not in orders,'reader design needs actual information order, event and emotional trigger')
        seen.add(row['id']);orders.add(row['order'])
    require(orders==set(range(1,len(rows)+1)),'reader information order has gaps')
    wave=any(any(term in source_text(s) for term in ('不能是一条直线','必须有起有伏')) for s in sources)
    if wave:
        require(any(r['before_emotion']!=r['after_emotion'] for r in rows),
                'source requires an emotional change; a constant plan is not an instance')


def _promise_window(sources: list[dict]) -> tuple[int,int] | None:
    windows=[]
    for source in sources:
        text=source_text(source).replace('\\','')
        match=re.search(r'(?:首次引入|首次埋设).{0,12}?后[的\s]*(\d+)\s*[-–—~至到]\s*(\d+)\s*章',text)
        if match:windows.append((int(match[1]),int(match[2])))
    if not windows:return None
    require(len(set(windows))==1,'conflicting source payoff windows need an explicit ruling')
    return windows[0]


def _promise(value: dict,sources: list[dict],context: dict) -> None:
    fields={'id','promise','plant_event','payoff_event','plant_chapter','payoff_chapter','payoff_window',
            'setup','expected_meaning','payoff','check'}
    rows=_rows(value['promise_plan'],fields,'foreshadow plan')
    events={r['id'] for r in value['event_nodes']}
    promises={r['key']:r['body'] for r in value['members'] if r['kind']=='promise'}
    promises.update({r['card_id']:r['body'] for r in context.get('approved_cards',[]) if r['kind']=='promise'})
    seen=set();window=_promise_window(sources)
    for row in rows:
        require(all(_text(row[k]) for k in ('id','promise','plant_event','setup','expected_meaning','payoff','check'))
                and row['id'] not in seen and row['promise'] in promises and row['plant_event'] in events
                and (row['payoff_event'] is None or row['payoff_event'] in events)
                and type(row['plant_chapter']) is int and row['plant_chapter']>0,
                'foreshadow needs a real promise, plant event, meaning and return arrangement')
        seen.add(row['id'])
        require(all(canonical(row[k])==canonical(promises[row['promise']][k]) for k in ('setup','payoff')),
                'foreshadow plan differs from its actual promise artifact')
        limits=row['payoff_window']
        require(limits is None or isinstance(limits,dict) and set(limits)=={'min_offset','max_offset'}
                and all(type(v) is int and v>=0 for v in limits.values())
                and limits['min_offset']<=limits['max_offset'],'payoff window must be explicit or unknown')
        if window:
            require(limits=={'min_offset':window[0],'max_offset':window[1]},
                    'payoff window does not preserve the actual source interval')
        if row['payoff_chapter'] is not None:
            require(type(row['payoff_chapter']) is int and row['payoff_chapter']>=row['plant_chapter'],
                    'payoff chapter precedes the plant')
            if limits:
                require(limits['min_offset']<=row['payoff_chapter']-row['plant_chapter']<=limits['max_offset'],
                        'payoff chapter is outside the source/project window')


def validate_plot_products(value: dict,sources: list[dict],context: dict) -> None:
    used={r['source_id'] for r in value.get('_uses',[])}
    reader=[s for s in sources if s['source']['id'] in used and 'reader' in domains(s)]
    promise=[s for s in sources if s['source']['id'] in used and 'promise' in domains(s)]
    if reader:_reader(value,reader)
    if promise:_promise(value,promise,context)


def _product(products: dict,stage: str) -> dict:
    return products.get(stage,{}).get('products',{})


def _relation_uses(products: dict,source_id: str) -> list[dict]:
    result=[]
    for stage,field in (('static_relations','relations'),('plot_design','static_bindings')):
        product=_product(products,stage)
        refs={ref for use in product.get('_uses',[]) if use['source_id']==source_id for ref in use['output_refs']}
        result.extend(r for r in product.get(field,[]) if r.get('source_id')==source_id or 'relation:'+r['id'] in refs)
    return result


def validate_static_bindings(value: dict,products: dict,sources: list[dict],context: dict) -> None:
    rows=value.get('static_bindings',[])
    require(isinstance(rows,list),'plot static bindings must be an explicit list')
    pool={s['source']['id']:s for s in [*context.get('method_sources',[]),*sources]}
    endpoints={r['card_id'] for r in context.get('approved_cards',[])}
    for stage in ('world_design','character_design'):
        endpoints.update(r['key'] for r in _product(products,stage).get('members',[]))
    endpoints.update(r['key'] for r in value.get('members',[]))
    used={r['source_id'] for r in value.get('_uses',[])};seen=set()
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'id','source_id','source','target','relation','condition'}
                and all(_text(v) for v in row.values()) and row['id'] not in seen
                and row['source'] in endpoints and row['target'] in endpoints,
                'post-plot relationship needs existing project endpoints and a unique identity')
        seen.add(row['id']);item=pool.get(row['source_id'])
        raw=original(item) if item else None
        require(row['source_id'] in used and isinstance(raw,dict)
                and all(raw.get(k) for k in ('source','target','type'))
                and not raw.get('generated_from_static') and not raw.get('effect'),
                'post-plot relationship must instantiate a read static method at this step')


def adopted_relation(source: dict,products: dict,context: dict) -> list[dict]:
    raw=original(source)
    if not isinstance(raw,dict) or not raw.get('generated_from_static'):return []
    signature=tuple(raw.get(k) for k in ('source','target','type'))
    sources={s['source']['id']:s for s in context.get('method_sources',[])}
    matches=[]
    for ident,item in sources.items():
        candidate=original(item)
        if isinstance(candidate,dict) and not candidate.get('generated_from_static') and not candidate.get('effect'):
            if tuple(candidate.get(k) for k in ('source','target','type'))==signature:
                matches.extend(_relation_uses(products,ident))
    return matches


def _network_relation_inputs(source: dict, raw: dict, products: dict, context: dict) -> dict[str, dict]:
    from nw.materials.network_workflow import STATIC_PROFILES, bound_relations

    related = source.get('related_sources', [])
    if len(related) > 1:
        return {}
    candidates = set()
    for item in context.get('method_sources', []):
        ref = item['source']
        if ref['profile'] not in STATIC_PROFILES or (related and ref['id'] != related[0]):
            continue
        if not related and source['source']['profile'] != 'dynamic_binding':
            continue
        basis = original(item)
        if (isinstance(basis, dict) and not basis.get('generated_from_static') and not basis.get('effect')
                and all(_text(raw.get(k)) and basis.get(k) == raw[k] for k in ('source', 'target', 'type'))):
            candidates.add(ref['id'])
    if len(candidates) != 1:
        return {}
    [ident] = candidates
    return {ref: row for ref, row in bound_relations(products).get(ident, {}).items()
            if row['relation'] == raw['type']}


def dynamic_rejection(source: dict, products: dict, context: dict) -> str:
    from nw.materials.network_workflow import DYNAMIC_PROFILES, POLICY, type_matches

    if context.get('network_prerequisite_policy') != POLICY or source['source']['profile'] not in DYNAMIC_PROFILES:
        return ''
    raw = original(source)
    if isinstance(raw, dict):
        if not type_matches(raw.get('valid_types'), context.get('network_type_scope', {})):
            return '已选类型不在原条适用范围，或缺少可核对的类型依据'
        if raw.get('generated_from_static') and not _network_relation_inputs(source, raw, products, context):
            return '缺少本项目已落实的对应静态关系'
    return ''


def _cites_relation(ref: str, cited: set[str]) -> bool:
    return ref in cited or any(f'{ref}/{field}' in cited for field in ('source', 'target', 'relation', 'condition'))


def _validate_action_relation(value: dict, ident: str, inputs: dict, products: dict, context: dict) -> None:
    people = {row['key'] for row in _product(products, 'character_design').get('members', [])}
    people.update(row['card_id'] for row in context.get('approved_cards', []) if row['kind'] == 'character')
    criteria = next((row for row in value.get('_criteria', []) if row['source_id'] == ident), {})
    for index, candidate in enumerate(value['candidates']):
        if ident not in candidate['source_ids']:
            continue
        target = f'/candidates/{index}'
        cited = {path.replace(':/products/', ':/', 1) for clause in criteria.get('clauses', [])
                 if clause['applicability'] == 'applies' and any(
                     output in ('/candidates', target) or output.startswith(target + '/')
                     for output in clause['output_refs']) for path in clause['input_refs']}
        require(any(_cites_relation(ref, cited) and
                    (not {row['source'], row['target']} <= people or candidate['actor'] in (row['source'], row['target']))
                    for ref, row in inputs.items()), 'dynamic action must cite its actual adopted static relationship')


def _static_endpoint(reference: str, products: dict, context: dict) -> str | None:
    from nw.materials.semantic_application import has_content, input_value, pointer_tokens

    match = re.fullmatch(r'(input|approved):(.+):(/.*)', reference)
    if match is None:
        return None
    kind, key, pointer = match.groups()
    tokens = pointer_tokens(pointer)
    if kind == 'approved' and tokens[0] == 'body':
        if any(card['card_id'] == key and card['kind'] in ('world', 'character', 'promise')
               for card in context.get('approved_cards', [])):
            return key if has_content(input_value(reference, 'static_relations', products, context)) else None
        return None
    if kind != 'input' or key not in ('world_design', 'character_design'):
        return None
    if tokens[0] == 'products':
        tokens = tokens[1:]
    if len(tokens) < 3 or tokens[0] != 'members' or not tokens[1].isdigit() or tokens[2] != 'body':
        return None
    resolved = input_value(reference, 'static_relations', products, context)
    return _product(products, key)['members'][int(tokens[1])]['key'] if has_content(resolved) else None


def validate_early_static(value: dict, products: dict, sources: list[dict], context: dict) -> None:
    """Require both real ends and the original relation type before handing off an early edge."""
    from nw.materials.network_workflow import EARLY_POLICY, prepared_static_source
    from nw.materials.semantic_application import concrete

    if context.get('early_network_policy') != EARLY_POLICY:
        return
    uses = {item['source_id']: set(item['output_refs']) for item in value['_uses']}
    clauses = {row['source_id']: [c for c in row['clauses'] if c['applicability'] == 'applies']
               for row in value.get('_criteria', [])}
    rows = {'relation:' + row['id']: (index, row) for index, row in enumerate(value['relations'])}
    for item in sources:
        ident = item['source']['id']
        if ident not in uses or not prepared_static_source(item, 'static_relations', context):
            continue
        edge = original(item)
        require(isinstance(edge, dict) and all(_text(edge.get(key)) for key in ('source', 'target', 'type'))
                and not edge.get('generated_from_static') and not edge.get('effect')
                and bool(uses[ident]) and uses[ident] <= rows.keys(),
                'early static source needs an original static edge and actual relation rows')
        paths = {f'/relations/{rows[ref][0]}' for ref in uses[ident]}
        applied = clauses.get(ident, [])
        require(all(any(output == path or output.startswith(path + '/') for path in paths)
                    for clause in applied for output in clause['output_refs']
                    if output == '/relations' or output.startswith('/relations/')),
                'early static clauses must name the exact relation row')
        for ref in sorted(uses[ident]):
            index, row = rows[ref]
            require(row['relation'] == edge['type'], 'early static relation differs from the original edge type')
            require(row['source'] != row['target'], 'early static relation needs two distinct project endpoints')
            require(concrete(row['condition']) and not row['condition'].strip().startswith(('待定', '待确认', '待补')),
                    'early static relation needs a concrete condition')
            path = f'/relations/{index}'
            matching = [clause for clause in applied if any(
                output == path or output.startswith(path + '/') for output in clause['output_refs'])]
            require(bool(matching), 'early static clauses must name the exact relation row')
            inputs = {reference for clause in matching for reference in clause['input_refs']}
            endpoints = {_static_endpoint(reference, products, context) for reference in inputs}
            require({row['source'], row['target']} <= endpoints,
                    'early static relation needs substantive card fields for both actual endpoints')


def _validate_plot_relation(value: dict, ident: str, inputs: dict) -> None:
    upstream = [ref for ref in inputs if ref.startswith('input:static_relations:/relations/')]
    _validate_relation_citations(value, ident, upstream,
                                 'dynamic plot clause must cite its actual upstream static relationship')


def _validate_relation_citations(value: dict, ident: str, upstream: list[str], message: str) -> None:
    criteria = next((row for row in value.get('_criteria', []) if row['source_id'] == ident), {})
    inputs_by_clause = [{path.replace(':/products/', ':/', 1) for path in clause['input_refs']}
                        for clause in criteria.get('clauses', []) if clause['applicability'] == 'applies']
    require(bool(inputs_by_clause) and all(any(_cites_relation(ref, cited) for ref in upstream)
        for cited in inputs_by_clause), message)


def validate_prepared_static(value: dict, sources: list[dict], context: dict) -> None:
    from nw.materials.network_workflow import prepared_plot_source

    uses = {item['source_id']: set(item['output_refs']) for item in value['_uses']}
    criteria = {row['source_id']: {path for clause in row['clauses'] if clause['applicability'] == 'applies'
                                   for path in clause['output_refs']} for row in value.get('_criteria', [])}
    for item in sources:
        ident = item['source']['id']
        if ident not in uses or not prepared_plot_source(item, context):
            continue
        edge = original(item)
        actual = {}
        for index, row in enumerate(value.get('static_bindings', [])):
            if row['source_id'] == ident and isinstance(edge, dict) and row['relation'] == edge.get('type'):
                actual['relation:' + row['id']] = f'/static_bindings/{index}'
        require(uses[ident] <= actual.keys(), 'prepared static source needs its own exact plot relationship')
        paths = criteria.get(ident, set())
        proved = {ref for ref, pointer in actual.items() if any(
            path in ('/static_bindings', pointer) or path.startswith(pointer + '/') for path in paths)}
        require(uses[ident] == proved, 'prepared static clauses must establish the cited plot relationship')


def validate_dynamic_dependencies(stage: str,value: dict,products: dict,sources: list[dict],context: dict) -> None:
    from nw.materials.network_followup import BASIS_STAGE, POLICY as FOLLOWUP_POLICY, STAGE as FOLLOWUP_STAGE
    from nw.materials.network_workflow import DYNAMIC_PROFILES, EARLY_POLICY, POLICY

    strict = context.get('network_prerequisite_policy') == POLICY
    used={r['source_id'] for r in value.get('_uses',[])}
    for item in sources:
        ident = item['source']['id']
        if ident not in used:
            continue
        if strict:
            reason = dynamic_rejection(item, products, context)
            require(not reason, item['source']['key'] + '：' + reason)
        raw=original(item)
        if not isinstance(raw,dict) or not raw.get('generated_from_static'):continue
        if strict and item['source']['profile'] in DYNAMIC_PROFILES:
            inputs = _network_relation_inputs(item, raw, products, context)
            relations = list(inputs.values())
            if stage == 'action_design':
                _validate_action_relation(value, ident, inputs, products, context)
            if stage == 'plot_design' and context.get('early_network_policy') == EARLY_POLICY:
                _validate_plot_relation(value, ident, inputs)
            if stage == FOLLOWUP_STAGE and context.get('same_stage_network_policy') == FOLLOWUP_POLICY:
                frozen = [ref for ref in inputs if ref.startswith(f'input:{BASIS_STAGE}:/relations/')]
                _validate_relation_citations(value, ident, frozen,
                                             'dynamic static clause must cite its independently frozen static relationship')
        else:
            relations=adopted_relation(item,products,context)
        require(bool(relations),'dynamic source has no actual adopted static relationship')
        if stage=='state_propagation':
            own=[r for r in value['candidates'] if item['source']['id'] in r['source_ids']]
            require(bool(own) and all(any(r['source_entity']==s['source'] and r['target_entity']==s['target']
                    for s in relations) for r in own),'dynamic candidate differs from adopted static project endpoints')


def _validate_anchor_source_beats(value: dict, anchor_ids: set[str], multi_scenes: set[str],
                                  indices: dict[str, int]) -> None:
    """Require each anchor source applied in a multi-action scene to locate its own beat and action."""
    from nw.materials.semantic_application import pointer_tokens

    targets = {row['source_id']: {ref[6:] for ref in row['output_refs'] if ref.startswith('scene:')}
               for row in value.get('_uses', []) if row['source_id'] in anchor_ids}
    criteria = {row['source_id']: row['clauses'] for row in value.get('_criteria', [])}
    for ident, scenes in targets.items():
        scene_coverage = set()
        for clause in criteria.get(ident, []):
            if clause['applicability'] != 'applies':
                continue
            for output in clause['output_refs']:
                tokens = pointer_tokens(output)
                if tokens[0] != 'beats':
                    continue
                if len(tokens) == 1:
                    require(not (scenes & multi_scenes),
                            'anchor source needs a concrete beat output for each applicable action')
                    continue
                beat = value['beats'][int(tokens[1])]
                require(beat['scene'] in scenes, 'anchor source applies to a beat outside its scene use')
                if beat['scene'] not in multi_scenes:
                    continue
                target = f"input:action_design:/candidates/{indices[beat['action_ref']]}"
                step = f"{target}/steps/{beat['step_index']}"
                refs = [ref.replace(':/products/', ':/', 1) for ref in clause['input_refs']]
                require(any(ref == target or (ref.startswith(target + '/') and not ref.startswith(target + '/steps/'))
                            or ref == step or ref.startswith(step + '/') for ref in refs),
                        'anchor source must cite the action and step of its actual beat')
                scene_coverage.add(beat['scene'])
        require((scenes & multi_scenes) <= scene_coverage, 'anchor source use has no corresponding multi-action beat')


def validate_anchor_products(value: dict, products: dict, sources: list[dict], context: dict | None = None) -> None:
    used = {r['source_id'] for r in value.get('_uses', [])}
    anchor_ids = {s['source']['id'] for s in sources if s['source']['id'] in used and s['source'].get('profile') == 'anchor'}
    active = (context or {}).get('multi_action_policy') == MULTI_ACTION_POLICY
    if not active and not anchor_ids:
        return
    chosen = selected_action_ids(_product(products, 'scene_design'))
    if not active:
        chosen = {scene: ids[-1:] for scene, ids in chosen.items()}
    multi_scenes = {scene for scene, ids in chosen.items() if len(ids) > 1}
    orders = {scene: {ident: index for index, ident in enumerate(ids)} for scene, ids in chosen.items()}
    candidates = _product(products, 'action_design').get('candidates', [])
    actions = {r['id']: r for r in candidates}
    timing = {'before': 0, 'during': 1, 'after': 2}
    seen: dict[str, set[str]] = {scene: set() for scene in multi_scenes}
    last: dict[str, tuple[int, int, int]] = {}
    for row in value['beats']:
        scene, ref = row['scene'], row.get('action_ref')
        has_action_fields = active and any(k in row for k in ('action_ref', 'step_index', 'timing', 'trigger_basis'))
        if not anchor_ids and scene not in multi_scenes and not has_action_fields:
            continue
        require(_text(ref) and ref in orders.get(scene, {}) and ref in actions,
                'anchor has no actual selected upstream action in this scene')
        step = row.get('step_index')
        require(type(step) is int and 0 <= step < len(actions[ref]['steps'])
                and row.get('timing') in timing and _text(row.get('trigger_basis')),
                'anchor needs an actual action beat, timing and source-condition basis')
        if scene in multi_scenes:
            position = (orders[scene][ref], step, timing[row['timing']])
            require(scene not in last or position >= last[scene], 'anchors must follow the actual action and step order')
            last[scene] = position
            seen[scene].add(ref)
    for scene in multi_scenes:
        require(seen[scene] == orders[scene].keys(), 'each selected action needs a visible anchor beat in its scene')
    if multi_scenes and anchor_ids:
        _validate_anchor_source_beats(value, anchor_ids, multi_scenes, {r['id']: i for i, r in enumerate(candidates)})
