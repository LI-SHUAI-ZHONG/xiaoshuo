"""Reconcile every runtime position with its source owner and execution route."""
from collections import Counter, defaultdict
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from nw.materials.adjudication import _fingerprint
from nw.materials.catalog import _connect
from nw.materials.layers import LayerCompiler
from nw.materials.governance import GovernanceRouter


def audit_layers(workspace: Path, *, details: bool = False) -> dict:
    target = workspace / 'materials' / 'adjudication.db'
    if not target.is_file():
        raise ValueError('MATERIAL_ADJUDICATION_STALE: run materials adjudicate first')
    with closing(_connect(workspace, write=False)) as catalog, closing(
            sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as saved:
        catalog.execute('BEGIN')
        meta = {key: json.loads(value) for key, value in saved.execute('SELECT * FROM metadata')}
        if any(meta.get(key) != value for key, value in _fingerprint(catalog, workspace).items()):
            raise ValueError('MATERIAL_ADJUDICATION_STALE: rebuild the original and runtime-layer ledger')
        units = {row['id']: dict(row) for row in catalog.execute("""
            SELECT u.id,u.fragment_id,u.key,u.kind,u.origin,u.sha256,u.locator,u.byte_start,u.byte_end,u.line_start,u.line_end,
                   f.source_id,s.path,s.file_sha256,s.family
            FROM material_units u JOIN fragments f ON f.id=u.fragment_id JOIN sources s ON s.id=f.source_id
            WHERE s.layer='baseline' AND (u.origin='upgrade' OR (u.origin='supplement' AND u.kind='type_profile'))
            ORDER BY s.path,u.byte_start,u.id""")}
        paired, routed, by_family, issues = defaultdict(list), Counter(), defaultdict(Counter), defaultdict(set)
        owners, repairs, needs, counts = [], [], [], Counter()
        for ident, payload in saved.execute('SELECT owner_id,payload_json FROM contracts ORDER BY owner_id'):
            review = json.loads(payload)
            counts[review['state']] += 1
            layer = review.get('layer_contract')
            if review.get('source_retranslation'):
                repairs.append({'owner_id': ident, **review['source_retranslation']})
            record = {'owner_id': ident, 'profile': review['profile'], 'state': review['state'],
                      'meaning': review['meaning'], 'source_refs': review['source_refs'],
                      'missing': review.get('missing', []), 'conflicts': review.get('conflicts', []),
                      'layer_contract': layer}
            if details:
                owners.append(record)
            if not layer:
                continue
            for issue in layer['issues']:
                issues[issue['source_ref']['id']].add(issue['kind'])
            for pair in layer['pairs']:
                if pair['id'] not in units:
                    raise ValueError('MATERIAL_LAYER_SOURCE: pairing points outside the frozen runtime positions')
                paired[pair['id']].append(ident)
                by_family[units[pair['id']]['family']]['owner_pairs'] += 1
            if layer['execution']:
                for stage in layer['execution']['stages']:
                    routed[review['state'], stage] += 1
                if review['state'] == 'design_ready':
                    counts['executable_owners_with_layers'] += 1
                else:
                    counts['owners_requiring_reconstruction'] += 1
                    needs.append({'owner_id': ident, 'profile': review['profile'], 'meaning': review['meaning'],
                                  'source_refs': review['source_refs'], 'pending': layer['pending']})
        unpaired, roles, governance_routes = [], Counter(), []
        compiler = LayerCompiler(catalog)
        governance = GovernanceRouter(catalog, compiler)
        for ident, unit in units.items():
            by_family[unit['family']]['runtime_positions' if unit['origin'] == 'upgrade' else 'supplement_profiles'] += 1
            if ident in paired:
                by_family[unit['family']]['paired_positions'] += 1
            else:
                by_family[unit['family']]['unpaired_positions'] += 1
                value, error = compiler._parse(unit)
                role = ('profile_governance_annotation' if unit['locator'].startswith('profiles/') else
                        'source_block_governance' if isinstance(value, dict) and value.get('补全运行层') else
                        'provenance_only' if isinstance(value, dict) and not value.get('runtime_calling_layer')
                        and value.get('tail_upgrade_evidence') else 'unresolved_translation')
                route = governance.route(unit) if role == 'unresolved_translation' else None
                if route:
                    role = route['role']
                    governance_routes.append(route)
                    by_family[unit['family']]['governance_routed_positions'] += 1
                roles[role] += 1
                unpaired.append({'source_ref': unit, 'role': role,
                                 **({'governance_route': route} if route else {}),
                                 'reasons': sorted(issues.get(ident, {error or 'no_exact_owner_pair'}))})
        runtime = {ident for ident, unit in units.items() if unit['origin'] == 'upgrade'}
        summary = {'policy': 'source-runtime-pairing-v1', 'layer_positions': len(units),
                   'runtime_positions': len(runtime), 'supplement_profiles': len(units)-len(runtime),
                   'paired_layer_positions': len(paired), 'unpaired_layer_positions': len(unpaired),
                   'paired_runtime_positions': len(runtime & paired.keys()),
                   'unpaired_runtime_positions': len(runtime - paired.keys()), 'unpaired_roles': dict(roles),
                   'unresolved_translation_positions': roles['unresolved_translation'],
                   'governance_routed_positions': len(governance_routes),
                   'governance_roles': dict(Counter(r['role'] for r in governance_routes)),
                   'governance_validation_statuses': dict(Counter(r['validation']['status'] for r in governance_routes)),
                   'governance_pending_consumers': sum(bool(r['pending']) for r in governance_routes),
                   'source_contract_states': {key: counts[key] for key in ('design_ready', 'reference', 'blocked')},
                   'executable_owners_with_layers': counts['executable_owners_with_layers'],
                   'owners_requiring_reconstruction': counts['owners_requiring_reconstruction'],
                   'explicit_source_retranslations': len(repairs),
                   'formal_novel_effects_verified': 0,
                   'by_family': {key: dict(value) for key, value in sorted(by_family.items())},
                   'stages': [{'state': state, 'stage': stage, 'owners': total}
                              for (state, stage), total in sorted(routed.items())]}
        return {'summary': summary, 'fingerprint': {key: value for key, value in meta.items() if key != 'summary'},
                'retranslations': repairs,
                **({'owners': owners, 'reconstruction_queue': needs, 'unpaired': unpaired,
                    'governance_routes': governance_routes} if details else {})}
