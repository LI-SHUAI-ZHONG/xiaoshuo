"""Verify that competing preferences have explicit placements or reasons to defer."""
import re


def validate_selected_types(value: dict, context: dict) -> None:
    plan = (context.get('governance_inputs') or {}).get('type_selection', {}).get('creation_plan', {})
    if not (selected := [row['id'] for row in plan.get('types', [])]):
        return
    from nw.studio.catalog import type_map

    known = type_map()
    actual = [row['id'] for row in value['selection'] if row['id'] in known or row['id'] in selected]
    if actual != selected:
        raise ValueError('本步须按顺序保留立项所选类型及其主次关系')


def resolution_keys(packet: dict) -> list[str]:
    return sorted({key for row in packet.get('preference_interactions', []) for key in row['keys']})


def add_resolution_schema(shape: dict, keys: list[str]) -> None:
    from nw.materials.phase_schema import TEXT, array, obj

    row = obj({'key': {'enum': keys}, 'reason': TEXT, 'output_ref': {'type': 'string'},
               'status': {'enum': ['applied', 'deferred']}})
    for alternative in shape.get('anyOf', [shape]):
        if products := alternative.get('properties', {}).get('products'):
            products['properties']['preference_resolutions'] = {**array(row, len(keys)), 'maxItems': len(keys)}
            products['required'].append('preference_resolutions')


def validate_resolutions(stage: str, value: dict, context: dict) -> None:
    packet = (context.get('governance_inputs') or {}).get(stage, {}).get('creation_plan', {})
    keys = resolution_keys(packet)
    if not keys:
        if 'preference_resolutions' in value:
            raise ValueError('本步无须提交立项偏好安排')
        return
    rows = value.get('preference_resolutions')
    if not isinstance(rows, list) or len(rows) != len(keys):
        raise ValueError('每个需协调的立项偏好都须说明应用位置或延后条件')
    placed: dict[str, str] = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'key', 'status', 'reason', 'output_ref'}
                or row['key'] not in keys or row['key'] in placed or not isinstance(row['reason'], str)
                or not row['reason'].strip() or len(row['reason']) > 300):
            raise ValueError('立项偏好安排须逐项填写理由，不能重复')
        ref = row['output_ref']
        if row['status'] == 'applied':
            if not isinstance(ref, str) or not re.fullmatch(r'/guidance/(?:0|[1-9]\d{0,4})/observable', ref):
                raise ValueError('已采用的立项偏好须指向本步场景指导中的具体表达')
            from nw.materials.semantic_application import output_value

            try:
                output_value(ref, value)
            except ValueError as exc:
                raise ValueError('立项偏好指定的场景指导不存在或为空') from exc
        elif row['status'] != 'deferred' or ref != '':
            raise ValueError('暂缓的立项偏好须填写适用条件并留空应用位置')
        placed[row['key']] = ref
    for interaction in packet['preference_interactions']:
        targets = [placed[key] for key in interaction['keys'] if placed[key]]
        if len(targets) != len(set(targets)):
            raise ValueError('需协调的立项偏好应分别对应各自的场景指导或叙述节拍')
