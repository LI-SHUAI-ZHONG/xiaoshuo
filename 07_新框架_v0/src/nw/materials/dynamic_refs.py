"""Resolve reused dynamic edge IDs against a version and the original relationship."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from nw.materials.adjudication import read_adjudication
from nw.materials.catalog import _connect, show_fragment
from nw.materials.identity_catalog import POLICY, _EDGE_FIELDS, _migrations, _network, _read_contract
from nw.materials.route_catalog import _FRAGMENTS

LEGACY_RESTORE_IDS = frozenset(f'C{number:05}' for number in range(484, 495))
_PIN_FIELDS = ('id', 'source_id', 'path', 'file_sha256', 'sha256', 'locator')


def _active_rule(workspace: Path, ident: str) -> dict | None:
    with closing(_connect(workspace, write=False)) as db:
        rows = db.execute(_FRAGMENTS + """ WHERE s.family='dynamic' AND s.layer='baseline'
                          AND f.kind='network_edge' AND f.key=?""", (ident,)).fetchall()
    if len(rows) != 1:
        return None
    row = dict(rows[0])
    frozen = show_fragment(workspace, row['id'])
    if frozen['sha256'] != row['sha256'] or sha256(frozen['text'].encode('utf-8')).hexdigest() != row['sha256']:
        raise ValueError('DYNAMIC_REFERENCE: original edge changed')
    edge = json.loads(frozen['text'])
    if edge.get('id') != ident or not all(isinstance(edge.get(key), str) and edge[key] for key in _EDGE_FIELDS):
        raise ValueError('DYNAMIC_REFERENCE: incomplete original relationship')
    review = read_adjudication(workspace, row)
    return {'rule_id': ident, 'source_type': 'original_dynamic',
            'source_ref': {**{k: row[k] for k in ('id', 'source_id', 'path', 'file_sha256', 'sha256')},
                           'locator': f"line:{row['line_start']}"},
            **{key: edge[key] for key in _EDGE_FIELDS},
            'source_qualification': review['state'] if review else 'not_adjudicated'}


def dynamic_reference(workspace: Path, ident: str, legacy_map: Path | None = None) -> dict:
    """Return an original source pin, optionally tracing an explicit historical map."""
    if legacy_map is None:
        result = _active_rule(workspace, ident)
        if result is None:
            raise ValueError('DYNAMIC_REFERENCE: current ID is missing or ambiguous')
        return result

    document, map_ref = _read_contract(legacy_map)
    audit = workspace / 'materials/F2_网络身份对账.json'
    recorded = json.loads(audit.read_text(encoding='utf-8-sig')) if audit.is_file() else {}
    if (recorded.get('policy') != POLICY
            or recorded.get('legacy_migration_file', {}).get('sha256') != map_ref['sha256']):
        raise ValueError('DYNAMIC_REFERENCE: legacy map differs from the recorded migration source')
    with closing(_connect(workspace, write=False)) as db:
        _, edges = _network(db)
    mappings = [row for row in _migrations(document, edges) if row['old_id'] == ident]
    if len(mappings) != 1 or mappings[0]['status'] != 'target_verified':
        raise ValueError('DYNAMIC_REFERENCE: legacy ID has no unique verified target in this map')
    row = mappings[0]
    result = _active_rule(workspace, row['new_id'])
    if (result is None or result['source_ref']['id'] != row['current_targets'][0]['fragment_id']
            or result['source_ref']['sha256'] != row['current_targets'][0]['sha256']
            or any(result[key] != row[key] for key in _EDGE_FIELDS)):
        raise ValueError('DYNAMIC_REFERENCE: mapped original changed during verification')
    return {**result, 'legacy_mapping': {'source_ref': {**map_ref, 'locator': row['legacy_locator']},
            'old_id': ident, 'old_id_reused': row['old_id_reused']}}


def matches_current_rule(entry: object, proof: dict) -> bool:
    source_ref = proof.get('source_ref')
    if (not isinstance(entry, dict) or entry.get('status') != 'approved'
            or entry.get('source_type') != 'original_dynamic' or not isinstance(entry.get('source_ref'), dict)
            or not isinstance(source_ref, dict) or proof.get('source_qualification') != 'design_ready'):
        return False
    return (all(k in source_ref and entry['source_ref'].get(k) == source_ref[k] for k in _PIN_FIELDS)
            and all(k in proof and entry.get(k) == proof[k] for k in _EDGE_FIELDS))


def current_rule_proofs(workspace: Path, inputs: dict) -> dict[str, dict]:
    """Read only the explicitly registered, version-pinned collision candidates."""
    registries = inputs.get('registries') if isinstance(inputs, dict) else None
    supplied = registries.get('dynamic_rules') if isinstance(registries, dict) else None
    if not isinstance(supplied, dict):
        return {}
    verified = {}
    for ident in sorted(LEGACY_RESTORE_IDS.intersection(supplied)):
        entry = supplied[ident]
        if not isinstance(entry, dict) or entry.get('status') != 'approved' or entry.get('source_type') != 'original_dynamic':
            continue
        pin = entry.get('source_ref')
        if not isinstance(pin, dict) or not all(isinstance(pin.get(k), str) and pin[k] for k in _PIN_FIELDS):
            continue
        current = _active_rule(workspace, ident)
        if current is not None and matches_current_rule(entry, current):
            verified[ident] = current
    return verified
