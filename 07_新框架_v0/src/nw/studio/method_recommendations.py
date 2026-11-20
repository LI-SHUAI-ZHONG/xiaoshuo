"""Recommend and freeze the methods the author selected during project setup."""
from nw.materials.phase_routes import phase_order
from nw.production_methods.sources import MethodReader, matching_methods, stage_tasks
from nw.studio.method_catalog import SCOPES, STAGES, TASKS


SLOT_TASKS = {
    'genre': {'type_choice', 'type_adaptation'},
    'tone': {'expression', 'pacing', 'anchors'},
    'style': {'expression', 'anchors'},
    'narration': {'expression', 'scene_composition', 'information'},
    'world': {'world_rules'},
    'character': {'character_arc', 'relationships', 'state_change', 'state_propagation'},
    'structure': {'main_plot', 'subplot', 'volume_outline', 'chapter_outline', 'event_chain',
                  'action_chain', 'scene_composition', 'pacing', 'method_binding'},
    'hook': {'hook', 'foreshadow', 'information'},
}


def uses(body: dict, slot: str) -> list[dict]:
    return [{'scope': scope, 'scope_name': SCOPES[scope], 'stage': stage, 'stage_name': STAGES[stage],
             'tasks': [TASKS[task]['name'] for task in sorted(tasks)]}
            for scope in body['scopes'] for stage in phase_order(scope)
            if (tasks := stage_tasks(body, stage, scope) & SLOT_TASKS[slot])]


def recommendations(reader: MethodReader, slot: str, types: list[str], selected: list[str]) -> dict:
    if slot not in SLOT_TASKS:
        raise ValueError('未知的立项方法推荐板块')
    if len(selected) > 24:
        raise ValueError('立项最多查询 24 条已选方法')
    matches = matching_methods(reader, types) if types else []
    current_versions = {row['id']: row['version'] for row, _ in matches if row['id'] in selected}
    result = []
    for row, match in matches:
        body = row['body']
        placements = uses(body, slot)
        if not placements:
            continue
        result.append({'id': row['id'], 'version': row['version'], 'title': body['title'], 'type_match': match,
                       'uses': placements, 'applicability': body['applicability'],
                       'non_applicability': body['non_applicability'], 'prerequisites': body['prerequisites'],
                       'evidence': body['evidence'], 'evidence_locations': row['evidence_locations'],
                       'structure_origin': row['structure_origin']})
        if len(result) == 3:
            break
    return {'slot': slot, 'recommendations': result, 'current_versions': current_versions}


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
        if method is None or method[0]['version'] != version or not uses(method[0]['body'], slot):
            raise ValueError('所选方法的批准版本或适用类型已变化，请刷新方法推荐后重新选择')
        row, match = method
        pin = reader.snapshot(row)
        reader.verify(pin)
        frozen.append({**item, 'title': row['body']['title'], 'type_match': match,
                       'body_sha256': pin['body_sha256'], 'snapshot_sha256': pin['snapshot_sha256'],
                       'structure_origin': pin['structure_origin'], 'source_sha256': pin['instance']['source_sha256'],
                       'evidence': pin['body']['evidence'], 'evidence_locations': pin['evidence_locations']})
        seen.add(ident)
    return frozen
