"""Recommend and freeze the methods the author selected during project setup."""
from nw.materials.phase_routes import phase_order
import json

from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.production_methods.sources import MethodReader, matching_methods, stage_tasks
from nw.studio.catalog import SLOT_LABELS, type_map
from nw.studio.method_catalog import SCOPES, STAGES, TASKS
from nw.studio.corpus_story_observations import STORY_TASKS


SLOT_TASKS = {
    'genre': {'type_choice', 'type_adaptation'},
    'tone': {'expression', 'pacing', 'anchors'},
    'style': {'expression', 'anchors'},
    'narration': {'narration', 'expression', 'scene_composition', 'information'},
    'world': {'world_rules'},
    'character': {'character_arc', 'relationships', 'state_change', 'state_propagation'},
    'structure': {'main_plot', 'subplot', 'volume_outline', 'chapter_outline', 'event_chain',
                  'action_chain', 'scene_composition', 'pacing', 'method_binding'},
    'hook': {'hook', 'foreshadow', 'information'},
}


SLOT_OBSERVATION={'character':'cast_entry','structure':'chapter_progress'}

AUTO_SLOT_TASKS = {
    'tone': {'pacing'},
    'style': {'expression'},
    'narration': {'narration'},
    'world': SLOT_TASKS['world'],
    'character': SLOT_TASKS['character'].union(STORY_TASKS['cast_entry']),
    'structure': SLOT_TASKS['structure'].union(STORY_TASKS['chapter_progress']) - {'pacing'},
    'hook': {'hook', 'foreshadow'},
}


def same_reference_type(types: list[str], method_types: list[str], source_types: list[str]) -> bool:
    return bool(method_types and source_types and any(
        type_match([ident], method_types) and type_match([ident], source_types) for ident in types))


def automatic_requirements(reader: MethodReader, types: list[str]) -> dict:
    """Route each required recommendation to a step that can actually produce its output."""
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

    routes = [('book', stage) for stage in phase_order('book')]
    routes.extend(('chapter', stage) for stage in phase_order('chapter'))
    result = {}
    for slot, tasks in AUTO_SLOT_TASKS.items():
        eligible = matches
        slot_routes = routes
        if slot == 'world':
            slot_routes = [('book', 'world_design')]
            eligible = [row for row in matches if 'world_rules' in stage_tasks(row['body'], 'world_design', 'book')
                        and reader.world_source(row, types) is not None]
        for scope, stage in slot_routes:
            offered = [row for row in eligible if stage_tasks(row['body'], stage, scope) & tasks][:3]
            if offered:
                result[slot] = {'scope': scope, 'stage': stage,
                                'versions': {row['id']: row['version'] for row in offered}}
                break
    missing = [SLOT_LABELS[slot] for slot in AUTO_SLOT_TASKS if slot not in result]
    if missing:
        names = '、'.join(type_map()[key]['name'] for key in types)
        raise ValueError(f'AUTO_RECOMMENDATIONS_MISSING: 「{names}」缺少已批准的同类型推荐：'
                         f'{"、".join(missing)}。请在类型资料库补齐对应参考小说的拆解方法。')
    return result


def uses(body: dict, slot: str, origin: dict | None = None) -> list[dict]:
    allowed=SLOT_TASKS[slot]
    domain=SLOT_OBSERVATION.get(slot)
    if domain in (origin or {}).get('observation_domains',[]):
        allowed=allowed.union(STORY_TASKS[domain])
    return [{'scope': scope, 'scope_name': SCOPES[scope], 'stage': stage, 'stage_name': STAGES[stage],
             'tasks': [TASKS[task]['name'] for task in sorted(tasks)]}
            for scope in body['scopes'] for stage in phase_order(scope)
            if (tasks := stage_tasks(body, stage, scope) & allowed)]


def recommendations(reader: MethodReader, slot: str, types: list[str], selected: list[str]) -> dict:
    if slot not in SLOT_TASKS and slot != 'all':
        raise ValueError('未知的立项方法推荐板块')
    if len(selected) > 24:
        raise ValueError('立项最多查询 24 条已选方法')
    matches = matching_methods(reader, types) if types else []
    if slot == 'all':
        groups = []
        for board in SLOT_TASKS:
            rows = _ranked(reader, board, types, matches)
            groups.append({'slot': board, 'recommendations': [
                {key: row[key] for key in ('id', 'version', 'title', 'type_match', 'applicability')} for row in rows]})
        return {'slots': groups}
    current_versions = {row['id']: row['version'] for row, _ in matches if row['id'] in selected}
    result = {'slot': slot, 'recommendations': _ranked(reader, slot, types, matches),
              'current_versions': current_versions}
    if slot == 'world':
        result['book_world_available'] = any(
            stage_tasks(row['body'], 'world_design', 'book') & SLOT_TASKS['world']
            and match['level'] != 'cross_type' and reader.world_source(row, types) is not None
            for row, match in matches)
    return result


def _ranked(reader: MethodReader, slot: str, types: list[str], matches: list) -> list[dict]:
    if slot == 'narration':
        matches = sorted(matches, key=lambda item: (TYPE_PRIORITY[item[1]['level']],
                                       'narration' not in item[0]['body']['tasks']))
    if slot in SLOT_OBSERVATION:
        domain=SLOT_OBSERVATION[slot]
        matches = sorted(matches, key=lambda item:(TYPE_PRIORITY[item[1]['level']],
            domain not in (item[0].get('structure_origin') or {}).get('observation_domains',[])))
    result = []
    for row, match in matches:
        body = row['body']
        placements = uses(body, slot, row['structure_origin'])
        if not placements or (slot == 'world' and (match['level'] == 'cross_type' or reader.world_source(row, types) is None)):
            continue
        result.append({'id': row['id'], 'version': row['version'], 'title': body['title'], 'type_match': match,
                       'uses': placements, 'applicability': body['applicability'],
                       'non_applicability': body['non_applicability'], 'prerequisites': body['prerequisites'],
                       'evidence': body['evidence'], 'evidence_locations': row['evidence_locations'],
                       'structure_origin': row['structure_origin']})
        if len(result) == 3:
            break
    return result


def freeze_preferences(reader: MethodReader, requested: object, types: list[str]) -> list[dict]:
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
        if method is None or method[0]['version'] != version or not uses(method[0]['body'], slot, method[0]['structure_origin']):
            raise ValueError('所选方法的批准版本或适用类型已变化，请刷新方法推荐后重新选择')
        row, match = method
        if slot == 'world' and (match['level'] == 'cross_type' or reader.world_source(row, types) is None):
            raise ValueError('所选世界方法缺少对应类型参考小说中的世界规则和受影响事件，请刷新方法推荐')
        pin = reader.snapshot(row)
        reader.verify(pin)
        frozen.append({**item, 'title': row['body']['title'], 'type_match': match,
                       'body_sha256': pin['body_sha256'], 'snapshot_sha256': pin['snapshot_sha256'],
                       'structure_origin': pin['structure_origin'], 'source_sha256': pin['instance']['source_sha256'],
                       'evidence': pin['body']['evidence'], 'evidence_locations': pin['evidence_locations']})
        seen.add(ident)
    return frozen
