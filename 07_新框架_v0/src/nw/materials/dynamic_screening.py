"""Bind TDF_001 screening to current stage inputs and scene-level candidate evidence."""
from collections import defaultdict
import json
from pathlib import Path
import re

from nw.materials.catalog import show_fragment
from nw.materials.semantic_application import pointer_tokens
from nw.materials.source_set import selection_status
from nw.materials.template_support import product


FILTER_REF = {
    'id': '70c670b31970a4ee8eeaf6c95ebedf438c617c4829dac171c8a0b036049cc970',
    'sha256': '64c4491fb6bbb4dd7642e7773ffef68355dcd65daf951a4a35a32d239e4f88ed',
    'source_id': '6cd30d00d42a5b3410bed51599a705463517ef6316fbfc6c4319c45fc0a3cba5',
    'file_sha256': 'aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582',
    'path': '02_原版资料/原始资料/类型系统.txt',
    'line_start': 32450,
}
_LIMITS = {'type_dynamic': 'max_type_dynamic_rules', 'original_dynamic': 'max_original_dynamic_rules'}
_IDS = {'type_dynamic': re.compile(r'TDR_(?:TEMPLATE_)?\d{3}'), 'original_dynamic': re.compile(r'C\d{5}')}
_CANDIDATE_REFS = {'event_design': 'event_candidate', 'action_design': 'action',
                   'state_propagation': 'propagation'}
_SCENE_OUTPUTS = {
    'scene_design': {'members': 'key', 'events': 'scene', 'selected_events': 'scene', 'selected_actions': 'scene'},
    'state_transition': {'transitions': 'scene', 'patches': 'scene'},
    'anchor_design': {'beats': 'scene', 'selected_propagations': 'scene'},
    'expression_design': {'guidance': 'scene'},
    'bind_scope': {'method_guidance': 'scene'},
}


def load_dynamic_screening(workspace: Path) -> dict | None:
    selected = selection_status(workspace)
    if selected is None:
        return None
    files = {ref['family']: ref for ref in selected['sources']}
    original = files['types']
    if (original['id'], original['file_sha256'], original['path']) != (
            FILTER_REF['source_id'], FILTER_REF['file_sha256'], FILTER_REF['path']):
        raise ValueError('MATERIAL_GOVERNANCE: TDF_001 source version needs review')
    frozen = show_fragment(workspace, FILTER_REF['id'])
    if any(frozen[key] != FILTER_REF[key] for key in ('source_id', 'sha256', 'line_start')):
        raise ValueError('MATERIAL_GOVERNANCE: TDF_001 original location changed')
    raw = json.loads(frozen['text'])
    limits = {key: raw['per_scene_limits'][key] for key in _LIMITS.values()}
    if raw['filter_id'] != 'TDF_001' or any(type(value) is not int or value != 5 for value in limits.values()):
        raise ValueError('MATERIAL_GOVERNANCE: TDF_001 limits need review')
    return {'filter_id': raw['filter_id'], 'source_ref': dict(FILTER_REF), 'limits': limits,
            'sources': {kind: {key: files[family][key] for key in ('path', 'file_sha256')}
                        for kind, family in (('type_dynamic', 'types'), ('original_dynamic', 'dynamic'))}}


def _kind(ref: dict, contract: dict) -> str | None:
    for kind, source in contract['sources'].items():
        if all(ref.get(key) == value for key, value in source.items()) and _IDS[kind].fullmatch(ref.get('key') or ''):
            return kind
    return None


def _addressed_rows(body: dict, field: str, tail: list[str]) -> list[dict]:
    rows = body.get(field, [])
    if not tail:
        return rows
    index = int(tail[0])
    return rows[index:index + 1]


def screening_report(products: dict, contract: dict) -> dict:
    """Count distinct versioned rule references attached to actual scene designs."""
    scene_design = product(products, 'scene_design')
    scene_rules = {row['key']: {} for row in scene_design.get('members', ())}
    placements = {stage: defaultdict(set) for stage in _CANDIDATE_REFS}
    for stage, choices, field in (
            ('event_design', scene_design.get('selected_events', ()), 'event'),
            ('action_design', scene_design.get('selected_actions', ()), 'action'),
            ('state_propagation', product(products, 'anchor_design').get('selected_propagations', ()), 'propagation')):
        for row in choices:
            placements[stage][row[field]].add(row['scene'])

    unassigned = []

    def attach(stage: str, target: str, refs: list[dict], scenes: set[str]) -> None:
        rules = [{'source_ref': ref, 'source_type': kind}
                 for ref in refs if (kind := _kind(ref, contract))]
        if not scenes and rules:
            unassigned.append({'stage': stage, 'candidate': target, 'rules': rules})
        for scene in sorted(scenes):
            for rule in rules:
                ref = rule['source_ref']
                entry = scene_rules[scene].setdefault(ref['id'], {**rule, 'placements': []})
                placement = {'stage': stage, 'product': target}
                if placement not in entry['placements']:
                    entry['placements'].append(placement)

    for stage, record in products.items():
        selected = {ref['id']: ref for ref in record.get('source_selection', {}).get('selected', ())}
        if not selected:
            continue
        body = record['products']
        prefix = _CANDIDATE_REFS.get(stage)
        used_by_candidate = defaultdict(set)
        for use in body.get('_uses', ()):
            ident = use['source_id']
            if ident not in selected:
                continue
            for output in use.get('output_refs', ()):
                form, _, target = output.partition(':')
                direct = form == 'scene' or (form == 'member' and stage == 'scene_design')
                direct = direct or (form == 'guidance' and stage == 'bind_scope')
                if direct and target in scene_rules:
                    attach(stage, output, [selected[ident]], {target})
                if form == prefix:
                    used_by_candidate[target].add(ident)
        for criterion in body.get('_criteria', ()):
            ident = criterion['source_id']
            if ident not in selected or not _kind(selected[ident], contract):
                continue
            for clause in criterion['clauses']:
                if clause['applicability'] != 'applies':
                    continue
                for output in clause['output_refs']:
                    field, *tail = pointer_tokens(output)
                    if scene_field := _SCENE_OUTPUTS.get(stage, {}).get(field):
                        scenes = {row[scene_field] for row in _addressed_rows(body, field, tail)}
                        attach(stage, output, [selected[ident]], scenes & scene_rules.keys())
                    elif field == 'candidates' and prefix:
                        for row in _addressed_rows(body, field, tail):
                            used_by_candidate[row['id']].add(ident)
        if prefix is None:
            continue
        for candidate in body.get('candidates', ()):
            used = set(candidate['source_ids']) | used_by_candidate[candidate['id']]
            refs = [selected[ident] for ident in sorted(used & selected.keys())]
            scenes = placements[stage][candidate['id']]
            if stage == 'state_propagation' and candidate['scene']:
                scenes = {candidate['scene']}
            attach(stage, candidate['id'], refs, scenes)

    scenes = {}
    violations = []
    for scene, mapping in scene_rules.items():
        rules = list(mapping.values())
        counts = {kind: sum(rule['source_type'] == kind for rule in rules) for kind in _LIMITS}
        scenes[scene] = {'counts': counts, 'rules': rules}
        for kind, count in counts.items():
            cap = contract['limits'][_LIMITS[kind]]
            if count > cap:
                violations.append({'scene': scene, 'source_type': kind, 'count': count, 'limit': cap})
    return {'filter_id': contract['filter_id'], 'source_ref': contract['source_ref'],
            'scope': 'scene_candidate_references', 'scenes': scenes, 'unassigned': unassigned,
            'violations': violations}


def require_scene_limits(report: dict) -> None:
    if report['violations']:
        details = ', '.join(f"{item['scene']} {item['source_type']} {item['count']}/{item['limit']}"
                            for item in report['violations'])
        raise ValueError('MATERIAL_GOVERNANCE: TDF_001 scene candidate limit: ' + details)
