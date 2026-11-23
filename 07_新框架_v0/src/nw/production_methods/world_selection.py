"""Select reference-world methods from the project's frozen, actual design requirements."""
from collections import Counter
from copy import deepcopy
import re

from nw.production_methods.handoff import inherited
from nw.production_methods.inputs import binding, registry
from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.production_methods.runtime import missing_recommendation_slots, recommendation_error, recommendation_slots
from nw.production_methods.sources import matching_methods, stage_tasks
from nw.studio.catalog import canonical_types, type_map
from nw.task_models import canonical


def is_ai_world(policy: dict, stage: str) -> bool:
    return stage == 'world_design' and policy.get('world_selection') == 'ai' and 'world_rules' in policy['tasks']


def terms(value: object) -> set[str]:
    if isinstance(value, dict):
        return set().union(*(terms(v) for k, v in value.items() if not k.startswith('_') and k not in
                             ('type_refs', 'id', 'project_id', 'key', 'version', 'input_keys', 'output_keys')))
    if isinstance(value, list):
        return set().union(*(terms(v) for v in value))
    result = set()
    for word in re.findall(r'[\u3400-\u9fff]+|[a-z0-9]+', str(value).lower()):
        if word.isascii() or len(word) < 2:
            result.add(word)
        else:
            result.update(word[i:i + 2] for i in range(len(word) - 1))
    return result


def has_value(value: object) -> bool:
    if isinstance(value, dict):
        return any(has_value(v) for v in value.values())
    if isinstance(value, list):
        return any(has_value(v) for v in value)
    return isinstance(value, str) and bool(value.strip()) or type(value) in (int, float, bool)


def actual_demand(package: dict, products: dict) -> dict:
    inputs = registry(package, products, ai_world=True)
    if not {'type_selection', 'type_adaptation'} <= products.keys():
        raise ValueError('METHOD_DESIGN_REQUIRED: 世界设计需要本次类型选择与类型适配的实际产物')
    taxonomy = type_map()
    demand = {'brief': deepcopy(package['brief']),
              **{key: {k: deepcopy(v) for k, v in inputs[key]['value'].items() if not k.startswith('_')}
                 for key in ('type_selection', 'type_adaptation')}}
    selection = demand['type_selection'].get('selection', [])
    chosen = [r['id'] for r in selection if isinstance(r, dict) and isinstance(r.get('id'), str)
              and r['id'].removeprefix('genre.') in taxonomy and isinstance(r.get('basis'), str) and r['basis'].strip()]
    if not chosen:
        raise ValueError('METHOD_DESIGN_REQUIRED: 本次类型选择缺少可与拆解小说对照的真实类型编号及选择依据')
    types = list(dict.fromkeys(t for tag in chosen for t in canonical_types([tag])))
    adaptations = demand['type_adaptation'].get('adaptations', [])
    indices = [i for i, row in enumerate(adaptations) if isinstance(row, dict)
               and isinstance(row.get('type_refs'), list) and set(chosen).intersection(row['type_refs'])
               and (isinstance(row.get('parameters'), dict) and has_value(row['parameters'])
                    or isinstance(row.get('limits'), list) and has_value(row['limits']))]
    if not indices:
        raise ValueError('METHOD_DESIGN_REQUIRED: 缺少对应所选小说类型的适配参数与限制，请补前置类型适配设计')

    return {'type_ids': types, 'demand': demand, 'adaptation_indices': indices,
            'upstream_refs': {k: inputs[k]['ref'] for k in demand}}


def needs(demand: dict, types: list, indices: list) -> dict:
    """The creative requirements that made an approved rule applicable in the first place."""
    return {'brief': {k: demand['brief'].get(k) for k in ('text', 'constraints')}, 'type_ids': sorted(types),
            'selection': demand['type_selection'].get('selection'), 'concepts': demand['type_selection'].get('concepts'),
            'type_boundaries': demand['type_selection'].get('boundaries'),
            'adaptations': [demand['type_adaptation']['adaptations'][i] for i in indices],
            'focuses': demand['type_adaptation'].get('focuses'), 'boundaries': demand['type_adaptation'].get('boundaries')}


def parent_design(context: dict, parents: list) -> dict:
    current = needs(context['demand'], context['type_ids'], context['adaptation_indices'])
    entries = [r for r in parents if r.get('approved_parent') and r.get('world_design_basis')]
    # A new or changed requirement requires a method for this scope. One matching parent
    # alone cannot justify ignoring a different approved rule with incompatible requirements.
    if not entries or any(r['world_design_basis'].get('needs') != current for r in entries):
        return {}
    cards = {}
    for entry in entries:
        for member in entry['world_design_basis'].get('members', []):
            key = member['key']
            if key in cards and cards[key] != member:
                return {}
            cards[key] = member
    if not cards:
        return {}
    return {'approved_world_members': list(cards.values()), 'parent_deliveries': [r['id'] for r in entries]}


def build_world_target(reader: object, package: dict, products: dict) -> dict:
    scope = package['scope']
    policy = package['production_method_policy']
    slots = recommendation_slots(policy, 'book', 'world_design')
    try:
        context = actual_demand(package, products)
    except ValueError as exc:
        if slots and str(exc).startswith('METHOD_DESIGN_REQUIRED: '):
            raise recommendation_error(list(slots), 'world_design', str(exc).removeprefix('METHOD_DESIGN_REQUIRED: ')) from exc
        raise
    types, demand, indices = (context[k] for k in ('type_ids', 'demand', 'adaptation_indices'))
    adaptations = demand['type_adaptation']['adaptations']
    base = {'kind': 'production_method_selection', 'stage': 'world_design', 'scope': scope,
            'max_methods': policy['max_methods'], **context}
    parent = parent_design(context, inherited(package)) if scope != 'book' else {}
    if parent:
        return {**base, **parent, 'selection_mode': 'inherit_world', 'candidates': [], 'candidate_total': 0,
                'required_tasks': [], 'missing_tasks': [],
                'instruction': '本步沿用父纲中已经采用的项目世界规则与限制，将它们交给剧情、行动与场景。'}
    if not policy['tasks']:
        raise ValueError('METHOD_DESIGN_REQUIRED: 本次需求与已批准父纲的世界设计不一致，须按当前范围补对应拆解方法')
    inputs = registry(package, products, ai_world=True)
    ready = []
    missing = []
    approved = matching_methods(reader, types) if reader.db_path.is_file() else []
    pins = {pair for versions in slots.values() for pair in versions.items()}
    for row, method_match in approved:
        if (slots and (row['id'], row['version']) not in pins
                or method_match['level'] == 'cross_type'
                or 'world_rules' not in stage_tasks(row['body'], 'world_design', scope)):
            continue
        source = reader.world_source(row, types)
        if source is None:
            continue
        pin, source_match = source
        applicable = {t for t in types if type_match([t], row['body']['type_tags'])
                      and type_match([t], source_match['source_type_ids'])}
        matching_indices = [i for i in indices if any(isinstance(t, str) and t.removeprefix('genre.') in applicable
                            for t in adaptations[i]['type_refs'])]
        if not matching_indices:
            continue
        candidate = binding(pin, 'world_design', inputs)
        if candidate['missing']:
            missing.extend(p['input_kind'] for p in candidate['missing'])
            continue
        candidate.update(status='eligible_for_ai_selection', type_match=method_match, source_type_match=source_match,
                         adaptation_indices=matching_indices,
                         preferred=policy.get('preferred_methods', {}).get(row['id']) == row['version'])
        if slots:
            candidate['recommended_for'] = ['world']
        body = row['body']
        features = terms([body['title'], body['applicability'], body['prerequisites'],
                          candidate['operations'], candidate['outputs']])
        ready.append((candidate, features))
    adaptation_terms = {i: terms(adaptations[i]) for i in indices}
    brief_terms = terms([demand['brief'], demand['type_selection']])
    frequency = Counter(word for _, features in ready for word in features)
    for candidate, features in ready:
        demand_terms = set().union(*(adaptation_terms[i] for i in candidate['adaptation_indices']))
        candidate['demand_score'] = round(sum(
            (3 * (word in demand_terms) + (word in brief_terms)) / frequency[word]
            for word in sorted(features & (demand_terms | brief_terms))), 6)
    ready.sort(key=lambda pair: (-pair[0]['demand_score'], TYPE_PRIORITY[pair[0]['source_type_match']['level']],
                                 TYPE_PRIORITY[pair[0]['type_match']['level']], not pair[0]['preferred'],
                                 pair[0]['method']['id']))
    maximum = policy['max_methods']
    # Freeze the whole ranked set so a rejected page can be followed by the next real offers.
    page_size = min(40, max(6, 2 * maximum))
    candidates = [candidate for candidate, _ in ready]
    return {**base, 'selection_mode': 'ai', 'required_tasks': ['world_rules'],
            'missing_tasks': [] if candidates else ['world_rules'], 'unavailable_inputs': sorted(set(missing)),
            'candidates': candidates, 'candidate_total': len(ready), 'page_size': page_size,
            **({'required_recommended_slots': slots} if slots else {}),
            'instruction': '先根据类型适配中的具体参数和限制，逐项判断原作方法的适用与不适用条件；把适用方法落实到本项目世界规则和边界。'}


def verify_context(plan: dict | None, session: dict, previous: dict) -> None:
    policy = session.get('production_method_policy') or {}
    parents = session.get('production_method_parents', [])
    auto = is_ai_world(policy, 'world_design')
    inherit_only = not policy.get('tasks') and policy.get('world_selection') == 'ai' and any(
        r.get('approved_parent') and r.get('world_design_basis') for r in parents)
    if not (auto or inherit_only):
        if plan and plan['target'].get('selection_mode') in ('ai', 'inherit_world'):
            raise ValueError('STALE_PROJECT_METHOD: 本任务未启用世界方法自动设计')
        return
    if not plan:
        raise ValueError('STALE_PROJECT_METHOD: 世界设计的前置需求及方法记录缺失')
    target = plan['target']
    context = actual_demand({'brief': session['context']['brief']}, previous)
    if (target['stage'] != 'world_design' or target['scope'] != session['scope']
            or target['max_methods'] != policy['max_methods']
            or any(canonical(target.get(k)) != canonical(v) for k, v in context.items())):
        raise ValueError('STALE_PROJECT_METHOD: 世界方法与本次实际前置需求不一致')
    parent = parent_design(context, parents) if session['scope'] != 'book' else {}
    expected_mode = 'inherit_world' if parent else 'ai'
    expected_slots = {} if parent else recommendation_slots(policy, 'book', 'world_design')
    if (target.get('selection_mode') != expected_mode or inherit_only and not parent
            or target.get('required_recommended_slots', {}) != expected_slots
            or any(canonical(target.get(k)) != canonical(v) for k, v in parent.items())):
        raise ValueError('STALE_PROJECT_METHOD: 世界卡或方法来源与已批准父纲不一致')


def finalize(plan: dict | None, products: dict) -> dict | None:
    if plan is None:
        return plan
    if plan['target'].get('selection_mode') == 'inherit_world':
        expected = {r['key']: r for r in plan['target']['approved_world_members']}
        actual = [r for r in products.get('members', []) if isinstance(r, dict) and r.get('kind') == 'world']
        if (products.get('_method_applications') or plan['selected'] or plan['decision'] is not None
                or len(actual) != len(expected) or {r['key']: r for r in actual} != expected):
            raise ValueError('PROJECT_METHOD: 承接父纲时须保留已批准世界卡及其规则和限制，不得把新设定登记为父纲产物')
        return plan
    if plan['target'].get('selection_mode') != 'ai':
        return plan
    target = plan['target']
    applications = products.get('_method_applications')
    offered = {c['method']['id']: c for c in target['candidates'] if not c['missing']}
    if isinstance(applications, list) and (slots := target.get('required_recommended_slots')):
        adopted = [offered[app['method_id']] for app in applications if isinstance(app, dict)
                   and isinstance(app.get('method_id'), str) and app['method_id'] in offered]
        if missing := missing_recommendation_slots(slots, adopted):
            raise recommendation_error(missing, target['stage'], 'AI 未在本步产物中采用这些板块的冻结方法。')
    if not isinstance(applications, list) or not 1 <= len(applications) <= target['max_methods']:
        raise ValueError('PROJECT_METHOD: 世界设计须在实际产物中落实至少一种且不超过本步上限的拆解方法')
    ids = [app.get('method_id') if isinstance(app, dict) else None for app in applications]
    if any(not isinstance(ident, str) or ident not in offered for ident in ids) or len(set(ids)) != len(ids):
        raise ValueError('PROJECT_METHOD: 世界设计引用了候选外、未就绪或重复的方法')
    refs = target['upstream_refs']
    for ident in ids:
        candidate = offered[ident]
        if any(item['kind'] in refs and canonical(item['ref']) != canonical(refs[item['kind']])
               for item in candidate['inputs'].values()):
            raise ValueError('STALE_PROJECT_METHOD: 世界方法绑定的前置与本次实际设计不符')
    return {'target': target, 'selected': [offered[ident] for ident in ids],
            'decision': {'actor': 'ai', 'method_ids': ids}}
