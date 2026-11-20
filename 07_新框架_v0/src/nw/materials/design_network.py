"""Apply a source method only after independent project fields exist, then follow its actual placements."""
import re

from nw.materials.design_network_catalog import OWNERS, POLICY, audit
from nw.materials.network_workflow import type_matches
from nw.materials.phase_routes import product_ref
from nw.materials.semantic_application import concrete, input_value, output_value, pointer_tokens, require
from nw.task_models import canonical, content_sha256


def guidance(stage: str, demand: str, products: dict, context: dict) -> list[dict]:
    if stage not in OWNERS:
        return []
    # Inspect actual design content. Source descriptions and earlier method instructions cannot create a need.
    upstream = [products[s]['products'].get(field, []) for s, field in (
        ('type_adaptation', 'adaptations'), ('world_design', 'members')) if s in products]
    text = demand + ' ' + canonical(upstream)
    return [row for row in audit(stage, context) if row['status'] == 'conditional'
            and OWNERS[stage].relevant(row['key'], text)]


def _signature(row: dict) -> str:
    # A reissued card may have a different task, position or version. All substantive evidence must still match.
    def field(ref: str) -> tuple:
        family, producer, path = ref.split(':', 2)
        parts = pointer_tokens(path)
        if family == 'approved':
            stage = 'world_design' if parts in (['body', 'rule'], ['body', 'limits']) else row['owner']
            return (stage, *parts)
        if parts[0] == 'members':
            return (producer, *parts[2:])
        return (producer, *(p for p in parts if not p.isdecimal()))

    fields = sorted(canonical([field(e['ref']), e['value']]) for e in row['evidence'])
    return content_sha256([row['key'], row['member'], row['source'], row['static'],
                           [row.get(k) for k in ('actor', 'event', 'ability')], fields])


def _placements(record):
    by_id = {c['id']: c for c in record.get('network_design_candidates', [])}
    for use in record.get('products', {}).get('_network_design_uses', []):
        row = by_id[use['id']]
        for path in use['output_refs']:
            yield row, path, output_value(path, record['products'])


def inherited(parent: dict, members: dict | None = None, cards=()) -> list[dict]:
    from nw.cards import _body
    direction = parent.get('selected_direction')
    plot = next((r for r in parent.get('stages', []) if r['stage'] == 'plot_design'), None)
    if not direction or not plot:
        return []
    result = []
    for row, path, value in _placements(plot):
        index = int(pointer_tokens(path)[1])
        if canonical(_body('plot', plot['products']['directions'][index])) == canonical(_body('plot', direction)):
            pin = (members or {}).get(row['member'])
            if pin is None:
                pin = next(({k: c[k] for k in ('card_id', 'version')} for c in cards if c['card_id'] == row['member']), None)
            result.append({'signature': _signature(row), 'producer': product_ref(plot), 'path': path, 'value': value,
                           'row': {k: v for k, v in row.items() if k not in ('id', 'deliveries', 'required')}, 'card': pin})
    return result


def candidates(stage: str, products: dict, context: dict) -> list[dict]:
    if context.get('design_network_policy') != POLICY or stage not in _PATHS:
        return []
    prior = {}
    if stage == 'plot_design' or stage == 'scene_design':
        for entry in context.get('parent_design_network', []):
            prior.setdefault(entry['signature'], []).append(entry)
            if card := entry['card']:
                current_signature = _signature({**entry['row'], 'member': card['card_id']})
                if current_signature != entry['signature']:
                    prior.setdefault(current_signature, []).append(entry)
    if stage == 'plot_design' and 'static_relations' in products:
        relations = products['static_relations']
        for row, path, value in _placements(relations):
            prior.setdefault(_signature(row), []).append({'producer': product_ref(relations), 'path': path, 'value': value})
    if stage == 'scene_design' and context.get('scope') != 'book':
        # Event and action deliveries become obligations only in scenes which actually select them.
        for upstream, selector in (('event_design', 'selected_events'), ('action_design', 'selected_actions')):
            for row, path, value in _placements(products[upstream]):
                chosen = products[upstream]['products']['candidates'][int(pointer_tokens(path)[1])]['id']
                prior.setdefault(_signature(row), []).append({'producer': product_ref(products[upstream]), 'path': path,
                    'value': value, 'selector': selector, 'candidate': chosen})
        # Detailed scopes have a single plot direction.
        plot = products['plot_design']
        for row, path, value in _placements(plot):
            prior.setdefault(_signature(row), []).append({'producer': product_ref(plot), 'path': path, 'value': value})
    result = []
    for key, pins in sorted(context.get('design_network_catalog', {}).items()):
        owner = pins['owner']
        methods = OWNERS[owner]
        spec = methods.SPECS[key]
        if (owner not in products or spec['status'] != 'conditional'
                or not type_matches(pins['valid_types'], context.get('network_type_scope', {}))
                or stage not in spec['consumers'] and not (stage == 'scene_design' and prior)):
            continue
        if pins['basis_stage'] == 'action_design' and stage not in ('action_design', 'scene_design'):
            continue
        producer = products[owner]
        for match in methods.matches(key, producer['products'], products=products, context=context):
            refs = [*(f'input:{owner}:{p}' for p in match['paths']), *match.get('upstream_refs', [])]
            # Additional pinned fields are explicitly delivered in this packet, including the original genre decision.
            evidence = [{'ref': ref, 'value': input_value(ref, stage, products, {**context, 'allowed_input_stages': None})}
                        for ref in dict.fromkeys(refs)]
            if not evidence:
                continue
            origins = {ref.split(':', 2)[1] for ref in refs if ref.startswith('input:')}
            approvals = {ref.split(':', 2)[1] for ref in refs if ref.startswith('approved:')}
            row = {'key': key, 'owner': owner, 'member': match['member'], 'origin': product_ref(producer),
                   'evidence': evidence, 'source': pins['source'], 'static': pins['static'],
                   'upstream': [product_ref(products[name]) for name in sorted(origins)],
                   'approved': [{k: card[k] for k in ('card_id', 'version')} for card in context.get('approved_cards', [])
                                if card['card_id'] in approvals],
                   'operation': spec['operation'], 'check': spec['check'],
                   'excerpts': [match[k] for k in ('rule_excerpt', 'limits_excerpt') if k in match]}
            if pins['basis_stage'] == 'action_design':
                cap = next(ref for ref in refs if ref.startswith('input:character_design:/capabilities/'))
                event = next(ref for ref in refs if ref.startswith(('input:plot_design:/event_nodes/', 'input:event_design:/candidates/')))
                row['ability'] = input_value(cap, stage, products, {**context, 'allowed_input_stages': None})
                row['actor'] = products['character_design']['products']['capabilities'][int(cap.split('/')[2])]['entity']
                event_stage, event_path = event.split(':')[1:]
                field, pos = pointer_tokens(event_path)[:2]
                row['event'] = products[event_stage]['products'][field][int(pos)]['id']
            carried = prior.get(_signature(row), [])
            if stage not in spec['consumers'] and not carried:
                continue
            row['id'] = 'design:' + content_sha256([stage, row])[:32]
            row.update(required=bool(carried), deliveries=[{k: v for k, v in item.items() if k not in ('row', 'card')}
                                                       for item in carried])
            result.append(row)
    if stage in ('plot_design', 'scene_design'):
        # A detailed plan can retain an approved actor or world without creating another member for it.
        for entry in context.get('parent_design_network', []):
            old, card = entry['row'], entry.get('card')
            if old['owner'] != 'world_design' or not card or any(r['key'] == old['key'] and r['member'] in (old['member'], card['card_id']) for r in result):
                continue
            pins = context['design_network_catalog'].get(old['key'])
            if not pins or pins['source'] != old['source'] or pins['static'] != old['static'] or not type_matches(
                    pins['valid_types'], context.get('network_type_scope', {})):
                continue
            if not any(c['card_id'] == card['card_id'] and c['version'] == card['version'] for c in context.get('approved_cards', [])):
                continue
            if any(m['key'] in (old['member'], card['card_id']) for m in products[old['owner']]['products']['members']):
                continue
            if any(e['ref'].startswith('input:type_selection:') and e['value'] not in {
                    choice['label'] for choice in products['type_selection']['products']['selection']} for e in old['evidence']):
                continue
            restored = {**old, 'member': card['card_id'], 'required': True,
                        'deliveries': [{k: v for k, v in entry.items() if k not in ('row', 'card')}]}
            restored['id'] = 'design:' + content_sha256([stage, old, card])[:32]
            if restored['id'] not in {r['id'] for r in result}:
                result.append(restored)
    return result


_PATHS = {
    'static_relations': r'/relations/(\d+)/condition',
    'plot_design': r'/directions/(\d+)/(?:choice|consequence|conflict|cost|resistance|ending_direction)',
    'event_design': r'/candidates/(\d+)/(?:event|completion_gate)',
    'action_design': r'/candidates/(\d+)/(?:action|cost|limits/\d+|steps/\d+/(?:object|action|obstacle|response|result))',
    'scene_design': r'/members/(\d+)/body/(?:goal|conflict|allowed_disclosure)',
}


def _supports(text: str, values: list) -> bool:
    # Ignore formatting, test markers and stock descriptions. Require a shared phrase from project evidence.
    def words(value):
        return set(re.findall(r'[a-z0-9][a-z0-9_-]{3,}', value.lower())) | {
            run[i:i+4] for run in re.findall(r'[\u3400-\u9fff]+', value) for i in range(len(run)-3)}
    scrub = lambda s: re.sub(r'\[FAKE[^\]]*\]|按照要求|根据设定|当前项目|本项目中|具体设计|相关条件|适用范围|按照规则|在本场景|方法已经采用', '', s)
    chunks = words(scrub(text))
    return any(chunks & words(scrub(v)) for v in values if isinstance(v, str))


def _participants(stage: str, value: dict, index: int) -> set | None:
    if stage == 'scene_design':
        body = value['members'][index]['body']
        return {body['pov'], *body['characters']}
    if stage == 'static_relations':
        relation = value['relations'][index]
        return {relation['source'], relation['target']}
    if stage == 'event_design':
        return set(value['candidates'][index]['actors'])
    if stage == 'action_design':
        return {value['candidates'][index]['actor']}
    return None


def validate(stage: str, value: dict, offered: list[dict], products: dict | None = None, context: dict | None = None) -> None:
    uses = value.get('_network_design_uses', [])
    require(isinstance(uses, list), '世界与人物设计采用记录须为列表')
    by_id = {row['id']: row for row in offered}
    seen = set()
    landed = {}
    for use in uses:
        require(isinstance(use, dict) and set(use) == {'id', 'operation', 'output_refs'}
                and isinstance(use['id'], str) and use['id'] in by_id and use['id'] not in seen
                and concrete(use['operation']), '采用记录须引用本步已交付的项目证据并说明具体操作')
        row = by_id[use['id']]
        seen.add(row['id'])
        paths = use['output_refs']
        require(isinstance(paths, list) and paths and all(isinstance(p, str) for p in paths)
                and len(set(paths)) == len(paths), '世界与人物方法须有互异的实际产物字段')
        evidence = row['excerpts'] or [e['value'] for e in row['evidence'] if not e['ref'].endswith('/body/name')
                                       and e['ref'].startswith(('input:' + row['owner'] + ':', 'approved:' + row['member'] + ':'))]
        if row['key'] == 'C00835':
            evidence = [e['value'] for e in row['evidence'] if '/abilities/' in e['ref']]
        for path in paths:
            match = re.fullmatch(_PATHS[stage], path)
            require(match is not None, '世界与人物方法须落实到本步允许的具体设计字段')
            text = output_value(path, value)
            exact_ability = row['key'] == 'C00835' and isinstance(text, str) and any(
                isinstance(v, str) and len(v.strip()) >= 2 and v.strip() in text for v in evidence)
            require(concrete(text) and (exact_ability or _supports(text, evidence)), '落点未保留冻结前置的可辨认项目细节')
            index = int(match[1])
            participants = _participants(stage, value, index)
            if stage == 'scene_design':
                scene = value['members'][index]['key']
                landed.setdefault(row['id'], set()).add(scene)
                limits = _delivery_scenes(row, value)
                require(limits is None or scene in limits, '采用的事件或行动与该场景的实际选择不一致')
            elif stage == 'plot_design' and row['owner'] == 'character_design' and products is not None:
                people = {p['key']: p['body'].get('name') for p in products['character_design']['products']['members']}
                people.update({p['card_id']: p['body'].get('name') for p in (context or {}).get('approved_cards', [])
                               if p['kind'] == 'character'})
                subject = people.get(row['member'])
                others = [n for k, n in people.items() if k != row['member'] and n and n != subject]
                require(not any(n in text for n in others) or subject and subject in text,
                        '剧情落点点名了另一人物，须写明实际运用这项方法的人物')
            elif stage == 'action_design' and row['key'] == 'C00835':
                skills = value['candidates'][index]['requires']
                require(any(skill in evidence and (skill in text or _supports(text, [skill])) for skill in skills),
                        '职业能力在本行动的实际所需能力与落点中不一致')
            elif stage == 'action_design' and 'actor' in row:
                action = value['candidates'][index]
                require(action['actor'] == row['actor'] and action['event'] == row['event'] and row['ability'] in action['requires'],
                        '动作的实际人物或事件未使用本条世界依据')
            if participants is not None and row['owner'] == 'character_design':
                require(row['member'] in participants, '人物资料被登记给本产物之外的人物')
    for row in offered:
        if not row['required']:
            continue
        if stage == 'scene_design':
            selections = _delivery_scenes(row, value, selected_only=True)
            require(selections <= landed.get(row['id'], set()), '已选事件或动作在对应场景缺少设计落点')
            if _delivery_scenes(row, value) == set():
                continue
        if row['id'] in seen:
            continue
        if stage == 'scene_design' and row['owner'] == 'character_design' and all(
                row['member'] not in _participants(stage, value, i) for i in range(len(value['members']))):
            continue
        require(False, '本范围已采用的剧情设计缺少实际承接字段 ' + row['key'])


def _delivery_scenes(row: dict, value: dict, *, selected_only: bool = False) -> set | None:
    selected = set()
    for item in row['deliveries']:
        if selector := item.get('selector'):
            name = 'action' if selector == 'selected_actions' else 'event'
            selected.update(s['scene'] for s in value[selector] if s[name] == item['candidate'])
    if selected_only or row['deliveries'] and all('selector' in item for item in row['deliveries']):
        return selected
    return None


def scene_checks(record: dict, scene: str) -> list[dict]:
    result = []
    for row, path, value in _placements(record):
        member = record['products']['members'][int(pointer_tokens(path)[1])]
        if member['key'] != scene:
            continue
        result.append({'id': 'work:design-network:' + content_sha256([row['id'], path, scene])[:32],
            'profile': 'method_work', 'network_design_key': row['key'],
            'binding': {'observable': value, 'check': row['check']},
            'method_artifact': {'source': row['source'], 'static': row['static'], 'origin': row['origin'],
                                **{k: row[k] for k in ('actor', 'event', 'ability') if k in row},
                                'upstream': row['upstream'], 'approved': row['approved'],
                                'prerequisites': row['evidence'], 'scene_ref': product_ref(record), 'path': path,
                                'application': next(u['operation'] for u in record['products']['_network_design_uses']
                                                    if u['id'] == row['id'])},
            'evidence_required': '对照本场实际文字核验该设计的可观察结果，并指出对应原句。'})
    return result


def add_schema(shape: dict, offered: list[dict]) -> None:
    for option in shape.get('anyOf', [shape]):
        products = option.get('properties', {}).get('products')
        if products:
            products['properties']['_network_design_uses'] = {'type': 'array', 'items': {'type': 'object',
                'properties': {'id': {'enum': [row['id'] for row in offered]}, 'operation': {'type': 'string'},
                    'output_refs': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}}},
                'required': ['id', 'operation', 'output_refs'], 'additionalProperties': False}}
