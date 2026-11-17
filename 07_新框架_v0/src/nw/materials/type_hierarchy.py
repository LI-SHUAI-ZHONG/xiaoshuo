"""Read the parent and subtype relationships recorded in the active ontology table."""
from collections import defaultdict
import json
from pathlib import Path

from nw.materials.type_adjudication import TYPE_TABLE, _ref
from nw.materials.type_sources import MAIN_TYPES, SUBTYPES, matches_source, original_type_records


def _hierarchy(workspace: Path, blocks: tuple[str, ...]) -> dict[str, dict]:
    records = defaultdict(list)
    for rows in original_type_records(workspace, blocks).values():
        for row, original, duplicates in rows:
            if isinstance(ident := original.get('type_id'), str) and ident:
                records[ident].append((row, original, duplicates))
    parents = {}
    schemas = {}
    for ident, entries in records.items():
        row, original, duplicates = entries[0]
        if (len(entries) == 1 and not duplicates and original.get('type_kind') == 'GENRE'
                and original.get('parent_id') is None and original.get('level') == 1
                and original.get('ancestor_ids') == []):
            parents[ident] = {'type_id': ident, 'canonical_name': original.get('canonical_name'),
                              'source_ref': _ref(row), 'declared_child_ids': original.get('child_ids'),
                              'subtypes': [], 'issues': []}
            schemas[ident] = original.get('schema_version')
    for ident, entries in records.items():
        for row, original, duplicates in entries:
            parent_id = original.get('parent_id')
            if (original.get('type_kind') != 'SUBGENRE' or not isinstance(parent_id, str)
                    or parent_id not in parents):
                continue
            parent = parents[parent_id]
            if (row['source_id'] != parent['source_ref']['source_id']
                    or original.get('schema_version') != schemas[parent_id]):
                parent['issues'].append({'type_id': ident, 'source_ref': _ref(row),
                                         'reason': '子项与父项的原件或模式不同'})
                continue
            if (len(entries) != 1 or duplicates or original.get('ancestor_ids') != [parent_id]
                    or original.get('level') != 2):
                parent['issues'].append({'type_id': ident, 'source_ref': _ref(row),
                                         'reason': '子类型 ID、字段或父级证据存在冲突'})
                continue
            parent['subtypes'].append({'type_id': ident, 'canonical_name': original.get('canonical_name'),
                                       'parent_id': parent_id, 'ancestor_ids': original['ancestor_ids'],
                                       'level': original['level'], 'source_ref': _ref(row)})
    for parent in parents.values():
        declared = parent['declared_child_ids']
        confirmed = [row['type_id'] for row in parent['subtypes']]
        if declared not in (None, []) and (not isinstance(declared, list)
                or not all(isinstance(key, str) for key in declared) or sorted(declared) != sorted(confirmed)):
            parent['issues'].append({'source_ref': parent['source_ref'],
                                     'reason': '父项的 child_ids 与子项明确声明的父级未能对齐'})
    return parents


def read_type_hierarchy(workspace: Path) -> dict[str, dict]:
    return _hierarchy(workspace, (TYPE_TABLE,))


def type_children(workspace: Path, parent: str) -> dict:
    result = read_type_hierarchy(workspace).get(parent)
    if result is None:
        raise ValueError('TYPE_HIERARCHY: parent is missing or ambiguous in the active ontology table')
    return result


def selection_hierarchy(workspace: Path, sources: list[dict], *, exact_sources: bool = True) -> list[dict]:
    """Summarize relevant parent links for the current type-selection input."""
    relevant = []
    for source in sources:
        if source['source']['profile'] != 'type_identity':
            continue
        try:
            original = json.loads(source['original_text'])
        except ValueError:
            continue
        if isinstance(original, dict) and original.get('type_kind') in ('GENRE', 'SUBGENRE'):
            relevant.append((source['source'], original))
    if not relevant:
        return []
    groups = [read_type_hierarchy(workspace)]
    if exact_sources:
        groups.append(_hierarchy(workspace, (MAIN_TYPES, SUBTYPES)))
    result = {}
    for pin, original in relevant:
        ident = original.get('type_id')
        parent_id = ident if original['type_kind'] == 'GENRE' else original.get('parent_id')
        if not isinstance(ident, str) or not isinstance(parent_id, str):
            continue
        for parents in groups:
            if (parent := parents.get(parent_id)) is None:
                continue
            owner = parent if ident == parent_id else next(
                (row for row in parent['subtypes'] if row['type_id'] == ident), None)
            if owner is None:
                continue
            original_ref = owner['source_ref']
            if exact_sources and not matches_source(pin, original_ref):
                continue
            if pin['file_sha256'] != original_ref['file_sha256']:
                continue
            parent_source_id = parent['source_ref']['id']
            result[parent_source_id] = {'parent_id': parent_id, 'parent_source_id': parent_source_id,
                                        'subtype_ids': [row['type_id'] for row in parent['subtypes']],
                                        'open_source_issues': len(parent['issues'])}
    return list(result.values())
