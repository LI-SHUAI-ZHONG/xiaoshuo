"""Read scoped type definitions and their source mappings from the current catalog."""
from collections import defaultdict
from collections.abc import Mapping, Sequence
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re

from nw.materials.catalog import _connect
from nw.materials.route_catalog import _FRAGMENTS, _UNITS
from nw.materials.type_adjudication import TYPE_TABLE, _JSONObject, _original, _ref

MAIN_TYPES = '主类型.json'
SUBTYPES = '子类型.json'
MAPPING_TABLE = '类型来源映射.json'
_TYPE_A_TARGETS = {
    'genre_standard': (MAIN_TYPES, 'type_id', 'GENRE'),
    'subgenre_standard': (SUBTYPES, 'type_id', 'SUBGENRE'),
    'hybrid_standard': ('混合类型.json', 'hybrid_id', 'HYBRID_GENRE'),
    'mechanism_standard': ('爽文机制.json', 'mechanism_id', 'TROPE_MECHANISM'),
    'structure_standard': ('特殊叙事结构.json', 'structure_id', 'NARRATIVE_STRUCTURE'),
}


def original_type_records(workspace: Path, blocks: tuple[str, ...]) -> dict[str, list[tuple[dict, dict, list[str]]]]:
    requested = ','.join('?' for _ in blocks)
    records = {}
    with closing(_connect(workspace, write=False)) as db:
        db.execute('BEGIN')
        tables = db.execute(_FRAGMENTS + " WHERE f.kind='source_block' AND s.family='types'"
                            + f" AND s.layer='baseline' AND f.key IN ({requested})", blocks)
        for table in tables:
            name = table['key']
            if name in records:
                raise ValueError(f'TYPE_SOURCE_SCOPE: multiple original blocks for {name}')
            rows = []
            records[name] = rows
            payload = db.execute('SELECT payload FROM fragments WHERE id=?', (table['id'],)).fetchone()[0]
            if sha256(payload).hexdigest() != table['sha256']:
                raise ValueError(f'TYPE_SOURCE_SCOPE: original block hash mismatch for {name}')
            for raw in db.execute(_UNITS + """ WHERE f.id=? AND u.kind='record'
                                  AND u.origin IN ('source','mixed') ORDER BY u.byte_start""", (table['id'],)):
                row = dict(raw)
                chunk = payload[row['byte_start'] - table['byte_start']:row['byte_end'] - table['byte_start']]
                if sha256(chunk).hexdigest() != row['sha256']:
                    raise ValueError(f'TYPE_SOURCE_SCOPE: original record hash mismatch for {name}')
                duplicates: list[str] = []
                original = _original(json.loads(chunk, object_pairs_hook=_JSONObject), duplicates)
                if isinstance(original, dict):
                    rows.append((row, original, duplicates))
    return records


def matches_source(current: dict, stored: dict) -> bool:
    return all(current.get(key) == stored[key] for key in ('id', 'path', 'file_sha256', 'sha256'))


def mapping_evidence(workspace: Path, source_refs: list[dict], qualifications: dict[str, dict]) -> list[dict]:
    """Show TYPE_A mappings only beside their exact original target definitions."""
    if not source_refs:
        return []
    refs = {ref['id']: ref for ref in source_refs}
    blocks = (MAPPING_TABLE, *(value[0] for value in _TYPE_A_TARGETS.values()))
    records = original_type_records(workspace, blocks)
    targets = defaultdict(list)
    for block, id_field, _ in _TYPE_A_TARGETS.values():
        for row, original, duplicates in records.get(block, ()):
            if isinstance(ident := original.get(id_field), str):
                targets[block, ident].append((row, original, duplicates))
    evidence = []
    for row, original, duplicates in records.get(MAPPING_TABLE, ()):
        role = qualifications.get(row['id'], {})
        if (duplicates or role.get('state') != 'reference'
                or any(role.get(key) != row[key] for key in ('sha256', 'file_sha256'))):
            continue
        scope = _TYPE_A_TARGETS.get(original.get('source_type'))
        if scope is None or not isinstance(original.get('target_id'), str):
            continue
        block, _, kind = scope
        matches = targets[block, original['target_id']]
        if len(matches) != 1:
            continue
        target, definition, issues = matches[0]
        if (issues or target['source_id'] != row['source_id'] or definition.get('schema_version') != 'TYPE_A-1.0.0'
                or not matches_source(refs.get(target['id'], {}), target)):
            continue
        evidence.append({'source_ref': _ref(row), 'qualification': role['state'], 'original': original,
                         'target': {'source_ref': _ref(target), 'schema_version': definition.get('schema_version'),
                                    'kind_from_table': kind}})
    return evidence


def selection_source_refs(record: dict) -> list[dict]:
    products = record['products']
    used = {row['source_id'] for row in products['_uses'] if 'selection' in row['output_refs']}
    used.update(criterion['source_id'] for criterion in products.get('_criteria', ())
                if any(clause['applicability'] == 'applies'
                       and any(path == '/selection' or path.startswith('/selection/')
                               for path in clause['output_refs'])
                       for clause in criterion['clauses']))
    return [ref for ref in record.get('source_selection', {}).get('selected', ())
            if ref['id'] in used and ref['profile'] in ('type_identity', 'type_expression')]


_ONTOLOGY_ALIASES = r'类型本体\类型别名表.json'
_NAME_ROLES = {'GENRE', 'SUBGENRE', 'SUBJECT_TAG', 'PLOT_MECHANISM'}


def _identity_entry(row: dict, value: dict, records: dict, near_name: bool) -> dict:
    parent = None
    if target := records.get(value.get('parent_id')):
        parent_row, parent_value = target
        if (row['source_id'] == parent_row['source_id'] and value['type_kind'] == 'SUBGENRE'
                and parent_value['type_kind'] == 'GENRE' and value.get('ancestor_ids') == [value['parent_id']]
                and value.get('level') == 2 and parent_value.get('level') == 1):
            parent = {'type_id': parent_value['type_id'], 'name': parent_value['canonical_name'],
                      'source_ref': _ref(parent_row)}
    return {**{key: value.get(key) for key in ('type_id', 'canonical_name', 'type_kind', 'definition', 'level', 'parent_id')},
            'parent': parent, 'source_ref': _ref(row), 'related_name_only': near_name}


def ontology_name_evidence(workspace: Path, brief_text: str, *, selected_terms: Sequence[str] = (),
                           selected_sources: Sequence[dict] = (),
                           related_mechanisms: Mapping[str, str] | None = None) -> list[dict]:
    """Project literal ontology names and explicit aliases as read-only selection evidence."""
    if not (brief_text or selected_terms or selected_sources):
        return []
    blocks = original_type_records(workspace, (TYPE_TABLE, _ONTOLOGY_ALIASES))
    raw_records = defaultdict(list)
    for row, value, duplicates in blocks.get(TYPE_TABLE, ()):
        if isinstance(ident := value.get('type_id'), str):
            raw_records[ident].append((row, value, duplicates))
    records = {ident: (row, value) for ident, entries in raw_records.items() if len(entries) == 1
               for row, value, duplicates in entries if not duplicates and value.get('schema_version') == 'TYPE_H1A-1.0.0'
               and value.get('type_kind') in _NAME_ROLES and isinstance(value.get('canonical_name'), str)
               and value['canonical_name'].strip()}
    choices = defaultdict(dict)
    aliases = defaultdict(list)
    for ident, (_, value) in records.items():
        choices[value['canonical_name']][ident] = False
    for row, value, duplicates in blocks.get(_ONTOLOGY_ALIASES, ()):
        ident, label = value.get('canonical'), value.get('alias')
        if (duplicates or not isinstance(label, str) or not label or not isinstance(ident, str)
                or ident not in records or row['source_id'] != records[ident][0]['source_id']):
            continue
        choices[label][ident] = False
        aliases[label].append({'target_id': ident, 'source_ref': _ref(row)})
    for label, ident in (related_mechanisms or {}).items():
        if label not in choices or ident not in records:
            continue
        row, value = records[ident]
        if (value['type_kind'] == 'PLOT_MECHANISM' and value['canonical_name'] == label + '机制'
                and any(row['source_id'] == records[other][0]['source_id'] for other in choices[label])):
            choices[label].setdefault(ident, True)

    ref_ids = {ref['id']: ref for ref in selected_sources}
    requested = set(selected_terms) | set(re.findall(r'\b[A-Z][A-Z0-9_]+\b', brief_text))
    requested.update(ident for ident, (row, _) in records.items() if matches_source(ref_ids.get(row['id'], {}), row))
    evidence = []
    for label, variants in sorted(choices.items()):
        if len(variants) < 2 or not (label in brief_text or label in requested or requested.intersection(variants)):
            continue
        evidence.append({'term': label, 'alternatives': [
            _identity_entry(*records[ident], records, near) for ident, near in sorted(variants.items())
        ], 'aliases': aliases[label]})
    return evidence
