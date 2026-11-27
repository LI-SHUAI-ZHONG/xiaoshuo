"""Recommend and freeze production methods during project setup."""
import json

from nw.materials.phase_routes import phase_order
from nw.materials.planning_hierarchy import incompatible_method
from nw.materials.story_policies import current as current_story_policies
from nw.production_methods.inputs import binding
from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.production_methods.sources import MethodReader, enabled_outputs, matching_methods, stage_tasks
from nw.studio.catalog import SLOT_LABELS, type_map
from nw.studio.method_catalog import INPUTS, SCOPES, STAGES, TASKS, conditional_outputs
from nw.studio.corpus_story_observations import STORY_TASKS


SLOT_TASKS = {
    'genre': {'type_choice', 'type_adaptation'},
    'world': {'world_rules'},
    'character': {'character_arc', 'relationships', 'state_change', 'state_propagation'},
    'structure': {'main_plot', 'subplot', 'volume_outline', 'chapter_outline', 'event_chain',
                  'action_chain', 'scene_composition', 'pacing', 'method_binding'},
    'hook': {'hook', 'foreshadow', 'information'},
    'narration': {'narration', 'expression', 'scene_composition', 'information'},
    'tone': {'expression', 'pacing', 'anchors'},
    'style': {'expression', 'anchors'},
}


SLOT_OBSERVATION={'character':'cast_entry','structure':'chapter_progress'}
SLOT_OBSERVATIONS={'character':('cast_entry','cast_roster'),'structure':('chapter_progress',)}

AUTO_BASE_TASKS = {
    'world': SLOT_TASKS['world'],
    'character': SLOT_TASKS['character'],
    'structure': SLOT_TASKS['structure'] - {'pacing', 'method_binding'},
    'hook': {'hook', 'foreshadow'},
    'narration': {'narration'},
    'tone': {'pacing'},
    'style': {'expression'},
}
AUTO_SLOT_TASKS = {
    slot: tasks.union(*(STORY_TASKS.get(domain, ()) for domain in SLOT_OBSERVATIONS.get(slot, ())))
    for slot, tasks in AUTO_BASE_TASKS.items()
}
# Old jobs may already have frozen a binding-only method. Only new launches use AUTO_BASE_TASKS.
AUTO_SLOT_TASKS['structure'].add('method_binding')
MethodVersion = tuple[str, int]
StageRoute = tuple[str, str]
RouteCandidates = dict[MethodVersion, frozenset[str]]
Assignments = tuple[tuple[StageRoute, frozenset[str], tuple[MethodVersion, ...]], ...]


def same_reference_type(types: list[str], method_types: list[str], source_types: list[str]) -> bool:
    return bool(method_types and source_types and any(
        type_match([ident], method_types) and type_match([ident], source_types) for ident in types))


def freeze_automatic_policy(reader: MethodReader, types: list[str], settings: dict, *,
                            candidate_titles: dict[str, str] | None = None,
                            planning_hierarchy: bool = False) -> dict:
    from nw.production_methods.policy import normalize

    policy = normalize({**settings, 'world_selection': 'ai', 'recommendation_mode': 'auto',
                        'tasks': ['world_rules']}, types=types)
    maximum = min(3, policy['max_methods'])
    routes = automatic_requirements(reader, types, max_methods=maximum, candidate_titles=candidate_titles,
                                    planning_hierarchy=planning_hierarchy)
    return normalize({**policy, 'max_methods': maximum, 'recommended_slots': routes}, types=types)


def automatic_requirements(reader: MethodReader, types: list[str], *, max_methods: int = 3,
                           candidate_titles: dict[str, str] | None = None, planning_hierarchy: bool = False) -> dict:
    """Freeze actionable seven-board coverage and keep every step within its method budget."""
    sources: dict[str, list[str]] = {}
    matches = []
    if reader.db_path.is_file():
        for row, match in matching_methods(reader, types):
            if match['level'] == 'cross_type':
                continue
            book_id = row['structure_origin']['book_id']
            if book_id not in sources:
                sources[book_id] = json.loads(reader._staging_row(book_id)['confirmed_types_json'])
            if same_reference_type(types, row['body']['type_tags'], sources[book_id]):
                matches.append(row)

    blocked: dict[str, dict[str, None]] = {}
    candidates = _launch_candidates(reader, types, matches, blocked, planning_hierarchy=planning_hierarchy)
    capacity = min(3, max_methods)
    eligible = set().union(*(slots for stage in candidates.values() for slots in stage.values()))
    missing = AUTO_SLOT_TASKS.keys() - eligible
    if missing:
        _missing_automatic(types, missing, blocked)

    covered, assignments = _schedule(candidates, capacity)
    if len(covered) != len(AUTO_SLOT_TASKS):
        _missing_automatic(types, AUTO_SLOT_TASKS.keys() - covered, {}, capacity=capacity)

    result = {}
    for (scope, stage), slots, selected in assignments:
        offers = candidates[(scope, stage)]
        pins = set(selected)
        for pin, boards in offers.items():
            if len(pins) == capacity:
                break
            if slots & boards:
                pins.add(pin)
        for slot in slots:
            result[slot] = {'scope': scope, 'stage': stage, 'versions': {
                ident: version for ident, version in offers if (ident, version) in pins and slot in offers[(ident, version)]}}
    if candidate_titles is not None:
        offered_ids = {ident for route in result.values() for ident in route['versions']}
        candidate_titles.update({row['id']: row['body']['title'] for row in matches if row['id'] in offered_ids})
    return {slot: result[slot] for slot in AUTO_SLOT_TASKS}


def _launch_candidates(reader: MethodReader, types: list[str], matches: list[dict],
                       blocked: dict[str, dict[str, None]], *, planning_hierarchy: bool) -> dict[StageRoute, RouteCandidates]:
    candidates = {}
    policies = current_story_policies() if (reader.workspace / 'materials/catalog.db').is_file() else {}
    scopes = ('book', 'volume', 'chapter') if planning_hierarchy else ('book', 'chapter')
    for scope in scopes:
        scope_policy = {**policies, 'scope': scope, 'planning_hierarchy': planning_hierarchy}
        for stage in phase_order(scope, planning_hierarchy=planning_hierarchy):
            available = _anticipated_inputs(scope, stage, planning_hierarchy=planning_hierarchy)
            offers = {}
            for row in matches:
                body = row['body']
                tasks = stage_tasks(body, stage, scope)
                observed = set(row['structure_origin'].get('observation_domains', ()))
                boards = frozenset(slot for slot, allowed in AUTO_BASE_TASKS.items() if (
                    (slot != 'world' or (scope, stage) == ('book', 'world_design'))
                    and (tasks & allowed or any(domain in observed and tasks.intersection(STORY_TASKS[domain])
                                                 for domain in SLOT_OBSERVATIONS.get(slot, ())))))
                if not boards:
                    continue
                reason = _unavailable_reason(reader, row, types, stage, available, scope_policy, boards)
                if reason:
                    for slot in boards:
                        blocked.setdefault(slot, {})[f'{SCOPES[scope]}·{STAGES[stage]}{reason}'] = None
                    continue
                offers[(row['id'], row['version'])] = boards
            if offers:
                candidates[(scope, stage)] = offers
    return candidates


def _anticipated_inputs(scope: str, stage: str, *, planning_hierarchy: bool = False) -> dict:
    order = phase_order(scope, planning_hierarchy=planning_hierarchy)
    kinds = ['brief', 'accepted_state', *order[:order.index(stage)]]
    if scope != 'book':
        # In the launch route the first chapter inherits the approved parent products.
        parent_scope = 'volume' if scope == 'chapter' and planning_hierarchy else ('chapter' if scope == 'scene' else 'book')
        kinds.extend(('parent_outline', *phase_order(parent_scope, planning_hierarchy=planning_hierarchy)))
    return {kind: {'kind': kind} for kind in kinds}


def _unavailable_reason(reader: MethodReader, row: dict, types: list[str], stage: str,
                        available: dict, policies: dict, boards: frozenset[str]) -> str:
    body = row['body']
    if incompatible_method(body, stage, policies):
        return '要求建立超出本级规划职责的卡片'
    if not enabled_outputs(body, stage, policies):
        if any(out['stage'] == stage and out['field'] == 'continuations' for out in body['outputs']):
            return '需要前章已核验的遗留事项'
        return '需要启用对应产物的分步制作规则'
    if 'world' in boards and reader.world_source(row, types) is None:
        return '缺少世界规则与其影响事件的原文依据'
    missing = binding(row, stage, available)['missing']
    if missing:
        labels = dict.fromkeys(INPUTS[item['input_kind']] for item in missing)
        return '缺少启动时可取得的前置「' + '、'.join(labels) + '」'
    return ''


def _schedule(candidates: dict[StageRoute, RouteCandidates], capacity: int) -> tuple[frozenset[str], Assignments]:
    """Try each distinct board coverage (at most 128) within a stage, then combine stages."""
    plans: dict[frozenset[str], Assignments] = {frozenset(): ()}
    for route, offers in candidates.items():
        stage_covers = {frozenset(): ()}
        seen = set()
        for pin, boards in offers.items():
            if boards in seen:
                continue  # Equal coverage has the same placement, so keep the highest ranked version.
            seen.add(boards)
            for covered, selected in tuple(stage_covers.items()):
                combined = covered | boards
                if combined == covered or len(selected) >= capacity:
                    continue
                if combined not in stage_covers or len(selected) + 1 < len(stage_covers[combined]):
                    stage_covers[combined] = (*selected, pin)
        for covered, earlier in sorted(plans.items(), key=lambda item: -len(item[0])):
            for local, selected in stage_covers.items():
                additional = local - covered
                if additional:
                    plans.setdefault(covered | additional, (*earlier, (route, additional, selected)))
        fullest = max(plans, key=len)
        if len(fullest) == len(AUTO_SLOT_TASKS):
            return fullest, plans[fullest]
    fullest = max(plans, key=len)
    return fullest, plans[fullest]


def _missing_automatic(types: list[str], missing: set[str], blocked: dict[str, dict[str, None]],
                       *, capacity: int | None = None) -> None:
    names = '、'.join(type_map()[key]['name'] for key in types)
    labels = '、'.join(SLOT_LABELS[slot] for slot in AUTO_SLOT_TASKS if slot in missing)
    details = '；'.join(f'{SLOT_LABELS[slot]}（{"；".join(list(blocked[slot])[:3])}）'
                       for slot in AUTO_SLOT_TASKS if slot in missing and slot in blocked)
    reason = f'。现有候选在每步最多采用 {capacity} 条方法的范围内无法覆盖全部板块' if capacity is not None else ''
    if details:
        reason = '。' + details
    raise ValueError(f'AUTO_RECOMMENDATIONS_MISSING: 「{names}」缺少可执行的已批准同类型推荐：'
                     f'{labels}{reason}。请在类型资料库补齐对应参考小说的拆解方法，核对前置和产物后批准。')


def uses(body: dict, slot: str, origin: dict | None = None, *, planning_hierarchy: bool = False) -> list[dict]:
    allowed = SLOT_TASKS[slot]
    domains = SLOT_OBSERVATIONS.get(slot, ())
    observed = set((origin or {}).get('observation_domains', []))
    for domain in domains:
        if domain in observed:
            allowed = allowed.union(STORY_TASKS[domain])
    routes = []
    for scope in body['scopes']:
        for stage in phase_order(scope, planning_hierarchy=planning_hierarchy):
            if planning_hierarchy and incompatible_method(body, stage, {'scope': scope, 'planning_hierarchy': True}):
                continue
            tasks = stage_tasks(body, stage, scope) & allowed
            if not tasks or binding({'body': body}, stage, _anticipated_inputs(scope, stage, planning_hierarchy=planning_hierarchy))['missing']:
                continue
            conditional = conditional_outputs(stage)
            conditions = list(dict.fromkeys(conditional[out['field']] for out in body['outputs']
                                             if out['stage'] == stage and out['field'] in conditional))
            routes.append({'scope': scope, 'scope_name': SCOPES[scope], 'stage': stage, 'stage_name': STAGES[stage],
                           'tasks': [TASKS[task]['name'] for task in sorted(tasks)],
                           **({'conditions': conditions} if conditions else {})})
    return routes


def recommendations(reader: MethodReader, slot: str, types: list[str], selected: list[str], *,
                    planning_hierarchy: bool = False, limit: int = 3) -> dict:
    if slot not in SLOT_TASKS and slot != 'all':
        raise ValueError('未知的立项方法推荐板块')
    if len(selected) > 24:
        raise ValueError('立项最多查询 24 条已选方法')
    limit = max(1, min(24, int(limit)))
    matches = matching_methods(reader, types) if types else []
    if slot == 'all':
        groups = []
        for board in SLOT_TASKS:
            rows, _ = _ranked(reader, board, types, matches, planning_hierarchy=planning_hierarchy, limit=limit)
            groups.append({'slot': board, 'recommendations': [
                {key: row[key] for key in ('id', 'version', 'title', 'type_match', 'applicability')} for row in rows]})
        return {'slots': groups}
    current_versions = {row['id']: row['version'] for row, _ in matches if row['id'] in selected}
    ranked_rows, total_available = _ranked(reader, slot, types, matches, planning_hierarchy=planning_hierarchy, limit=limit)
    result = {'slot': slot, 'recommendations': ranked_rows, 'total_available': total_available,
              'current_versions': current_versions}
    if slot == 'world':
        result['book_world_available'] = any(
            match['level'] != 'cross_type'
            and any(route['scope'] == 'book' and route['stage'] == 'world_design'
                    for route in uses(row['body'], 'world', row['structure_origin'], planning_hierarchy=planning_hierarchy))
            and reader.world_source(row, types) is not None
            for row, match in matches)
    return result


def _ranked(reader: MethodReader, slot: str, types: list[str], matches: list, *,
            planning_hierarchy: bool = False, limit: int = 3) -> tuple[list[dict], int]:
    if slot == 'narration':
        matches = sorted(matches, key=lambda item: (TYPE_PRIORITY[item[1]['level']],
                                       'narration' not in item[0]['body']['tasks']))
    if slot in SLOT_OBSERVATIONS:
        domains = set(SLOT_OBSERVATIONS[slot])
        matches = sorted(matches, key=lambda item: (TYPE_PRIORITY[item[1]['level']],
            not domains.intersection((item[0].get('structure_origin') or {}).get('observation_domains', []))))
    result = []
    total_available = 0
    for row, match in matches:
        body = row['body']
        placements = uses(body, slot, row['structure_origin'], planning_hierarchy=planning_hierarchy)
        if not placements or (slot == 'world' and (match['level'] == 'cross_type' or reader.world_source(row, types) is None)):
            continue
        total_available += 1
        if len(result) < limit:
            result.append({'id': row['id'], 'version': row['version'], 'title': body['title'], 'type_match': match,
                           'uses': placements, 'applicability': body['applicability'],
                           'non_applicability': body['non_applicability'], 'prerequisites': body['prerequisites'],
                           'evidence': body['evidence'], 'evidence_locations': row['evidence_locations'],
                           'structure_origin': row['structure_origin']})
    return result, total_available


def freeze_preferences(reader: MethodReader, requested: object, types: list[str], *,
                       planning_hierarchy: bool = False) -> list[dict]:
    if not isinstance(requested, list) or len(requested) > 24:
        raise ValueError('立项最多保存 24 条方法偏好')
    if not requested:
        return []
    methods = {row['id']: (row, match) for row, match in matching_methods(reader, types)}
    frozen = []
    seen = set()
    for item in requested:
        if (not isinstance(item, dict) or set(item) != {'slot', 'id', 'version'}
                or not isinstance(item['slot'], str) or item['slot'] not in SLOT_TASKS
                or not isinstance(item['id'], str) or type(item['version']) is not int or item['id'] in seen):
            raise ValueError('无效或重复的立项方法选择')
        slot, ident, version = item['slot'], item['id'], item['version']
        method = methods.get(ident)
        if method is None or method[0]['version'] != version:
            raise ValueError('所选方法的批准版本或适用类型已变化，请刷新方法推荐后重新选择')
        row, match = method
        placements = uses(row['body'], slot, row['structure_origin'], planning_hierarchy=planning_hierarchy)
        if not placements:
            raise ValueError('所选方法缺少可用的制作步骤或前置，请刷新方法推荐后重新选择')
        if slot == 'world' and (match['level'] == 'cross_type' or reader.world_source(row, types) is None):
            raise ValueError('所选世界方法缺少对应类型参考小说中的世界规则和受影响事件，请刷新方法推荐')
        pin = reader.snapshot(row)
        reader.verify(pin)
        frozen.append({**item, 'title': row['body']['title'], 'type_match': match,
                       'body_sha256': pin['body_sha256'], 'snapshot_sha256': pin['snapshot_sha256'],
                       'structure_origin': pin['structure_origin'], 'source_sha256': pin['instance']['source_sha256'],
                       'evidence': pin['body']['evidence'], 'evidence_locations': pin['evidence_locations'],
                       'uses': placements})
        seen.add(ident)
    return frozen
