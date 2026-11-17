"""Join the F0 file denominator, supplemental recoveries, and the live catalog."""
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import file_digest
import json
from pathlib import Path

from nw.materials.catalog import _connect
from nw.task_models import _sha256, _text

_USES = {
    'version_review': 'version_comparison',
    'reference_only': 'reference_archive',
    'audit_only': 'audit_archive',
    'needs_review': 'placement_pending',
    'quarantined': 'source_quarantined',
    'alias': 'same_bytes_reference',
    'parse_compare': 'version_comparison',
    'parse_current': 'primary_material',
    'reconcile_edges': 'network_reconciliation',
    'parse_contract': 'execution_contract_review',
}
_REVIEW_PLACEMENTS = {'historical_source_comparison', 'historical_design_evidence', 'historical_run_evidence'}


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if (not isinstance(data, dict) or data.get('schema_version') != 1
            or not isinstance(data.get('file_registry'), list)
            or not isinstance(data.get('recovery_candidates', []), list)):
        raise ValueError('Unsupported material placement manifest')
    return data


def _relative(raw: object) -> Path:
    if not _text(raw):
        raise ValueError('Missing registered material path')
    path = Path(raw)
    if path.is_absolute() or path.drive or path.root or '..' in path.parts or path.as_posix() != raw:
        raise ValueError(f'Invalid material placement path: {raw}')
    return path


def _live(root: Path, row: dict) -> str:
    path = _relative(row['path'])
    try:
        actual = (root / path).resolve()
        if not actual.is_relative_to(root):
            return 'outside_root'
        if not actual.is_file():
            return 'missing'
        if actual.stat().st_size != row['bytes']:
            return 'version_changed'
        with actual.open('rb') as stream:
            return 'verified' if file_digest(stream, 'sha256').hexdigest() == row['sha256'] else 'version_changed'
    except OSError:
        return 'unavailable'


def audit_placement(workspace: Path, manifest: Path, *, supplement: Path | None = None,
                    source_root: Path | None = None, path: str | None = None, details: bool = False) -> dict:
    base = _read(manifest)
    extra = _read(supplement) if supplement is not None else {}
    registry = {}
    for name, data in [('F0', base), ('supplement', extra)]:
        for row in data.get('file_registry', []):
            if not isinstance(row, dict):
                raise ValueError('Invalid material registry row')
            key = _relative(row.get('path')).as_posix()
            if (key in registry or not _sha256(row.get('sha256')) or not _text(row.get('physical_status'))
                    or not _text(row.get('role')) or type(row.get('bytes')) is not int or row['bytes'] < 0
                    or not isinstance(row.get('usage'), str) or row['usage'] not in _USES):
                raise ValueError(f'Invalid or duplicate material registry row: {key}')
            registry[key] = (row, name)
    recoveries = defaultdict(list)
    recovered_paths = set()
    for data in (base, extra):
        for item in data.get('recovery_candidates', []):
            damaged, candidate = item['damaged'], item['candidate']
            if (damaged not in registry or candidate not in registry
                    or registry[damaged][0]['sha256'] != item['damaged_sha256']
                    or registry[candidate][0]['sha256'] != item['candidate_sha256']):
                raise ValueError(f'Recovery references an unregistered file version: {damaged}')
            recoveries[damaged].append(item)
            recovered_paths.add(candidate)
    decisions = {}
    for decision in extra.get('placement_decisions', []):
        if not isinstance(decision, dict) or set(decision) != {'path', 'sha256', 'placement', 'reason'}:
            raise ValueError('Invalid supplemental placement decision')
        key = _relative(decision['path']).as_posix()
        if (key in decisions or key not in registry or registry[key][0]['usage'] != 'needs_review'
                or registry[key][0]['sha256'] != decision['sha256']
                or decision['placement'] not in _REVIEW_PLACEMENTS or not _text(decision['reason'])):
            raise ValueError(f'Supplemental placement requires the exact pending file version: {key}')
        decisions[key] = decision
    sources = defaultdict(list)
    by_hash = defaultdict(list)
    with closing(_connect(workspace, write=False)) as db:
        db.execute('BEGIN')
        for source in db.execute("""
            SELECT s.id AS source_id,s.path,s.file_sha256,s.family,s.layer,s.status,
                   count(f.id) AS fragments
            FROM sources s LEFT JOIN fragments f ON f.source_id=s.id
            GROUP BY s.id ORDER BY s.path,s.id
        """):
            data = dict(source)
            sources[data['path'], data['file_sha256']].append(data)
            by_hash[data['file_sha256']].append(data)
    if path is not None and path not in registry:
        raise ValueError(f'Material file is not registered: {path}')
    root = source_root.resolve(strict=True) if source_root is not None else None
    rows = []
    for key, (row, origin) in sorted(registry.items()):
        if path is not None and key != path:
            continue
        versions = sources.get((key, row['sha256']), [])
        use = _USES[row['usage']]
        if key in decisions:
            use = decisions[key]['placement']
        if key in recovered_paths:
            use = 'recovery_source' if any(v['status'] == 'INDEXED' for v in versions) else 'recovery_source_pending'
        if row['usage'] in ('parse_current', 'parse_compare', 'reconcile_edges', 'parse_contract') and not versions:
            use = 'index_pending'
        links = [{k: item[k] for k in ('candidate','candidate_sha256','decision')}
                 for item in recoveries[key]]
        rows.append({**{k: row[k] for k in ('path','sha256','bytes','physical_status','role','usage')},
                     'registry': origin, 'placement': use, 'live_status': _live(root, row) if root else 'unchecked',
                     'placement_reason': decisions[key]['reason'] if key in decisions else None,
                     'catalog': versions, 'same_bytes_indexed': [item['source_id'] for item in by_hash[row['sha256']]
                                                                 if item['path'] != key],
                     'recovery_links': links})
    summary = {
        'registered_paths': len(rows), 'unique_content_hashes': len({row['sha256'] for row in rows}),
        'by_registry': dict(Counter(row['registry'] for row in rows)),
        'by_physical_status': dict(Counter(row['physical_status'] for row in rows)),
        'by_placement': dict(Counter(row['placement'] for row in rows)),
        'by_live_status': dict(Counter(row['live_status'] for row in rows)),
        'cataloged_paths': sum(bool(row['catalog']) for row in rows),
        'recovery_source_paths': sum(row['placement'] == 'recovery_source' for row in rows),
        'recovery_target_paths': sum(bool(row['recovery_links']) for row in rows),
        'historical_references': dict(Counter(item['status'] for item in base.get('references', []))),
    }
    return {'summary': summary, **({'files': rows} if details or path is not None else {})}

