"""Build and inspect source-specific adjudications for every candidate position."""
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from nw.materials.catalog import _connect
from nw.materials.network_adjudication import NetworkAdjudicator
from nw.materials.layers import LayerCompiler
from nw.materials.retranslations import retranslate
from nw.materials.functional_rebuild import rebuild_function
from nw.materials.reviews import source_review
from nw.materials.routing import disposition
from nw.task_models import canonical

POLICY = 'material-adjudication-v1'
_STATES = {'design_ready', 'reference', 'blocked', 'context'}
_SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE contracts (owner_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL);
CREATE TABLE positions (
    id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, file_sha256 TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES contracts(owner_id), state TEXT NOT NULL, profile TEXT NOT NULL,
    key TEXT, path TEXT NOT NULL
);
CREATE INDEX positions_owner ON positions(owner_id);
"""


def _code_hash() -> str:
    folder = Path(__file__).parent
    names = ('adjudication.py', 'type_adjudication.py', 'type_auxiliary.py', 'type_source_repairs.py', 'library_adjudication.py',
             'network_adjudication.py', 'routing.py', 'reviews.py', 'units.py', 'unit_catalog.py',
             'binding.py', 'evidence.py', 'scoped.py', 'layers.py', 'layer_workflow.py', 'process_workflow.py', 'retranslations.py',
             'functional_rebuild.py', 'stage_workflow.py', 'stage_effects.py', 'recall.py')
    return sha256(b''.join(name.encode() + (folder / name).read_bytes() for name in names)).hexdigest()


def _fingerprint(db: sqlite3.Connection, workspace: Path) -> dict:
    sources = [tuple(row) for row in db.execute('SELECT id,file_sha256 FROM sources ORDER BY id')]
    identity = workspace / 'materials' / 'F2_网络身份对账.json'
    return {'policy': POLICY, 'code_sha256': _code_hash(),
            'source_set_sha256': sha256(canonical(sources).encode()).hexdigest(),
            'unit_count': db.execute('SELECT count(*) FROM material_units').fetchone()[0],
            'identity_sha256': sha256(identity.read_bytes()).hexdigest() if identity.is_file() else ''}


def _review_group(family: str) -> str:
    if family in {'types', 'type_links'}:
        return 'types'
    if family in {'library', 'anchors'}:
        return 'library'
    return 'network'


def _save_contract(db: sqlite3.Connection, review: dict, roots: Counter) -> None:
    owner = review['owner_id']
    payload = canonical(review)
    record = db.execute('INSERT OR IGNORE INTO contracts VALUES (?,?)', (owner, payload))
    if record.rowcount:
        roots[review['state']] += 1
    elif db.execute('SELECT payload_json FROM contracts WHERE owner_id=?', (owner,)).fetchone()[0] != payload:
        raise ValueError(f'Conflicting full adjudications for {owner}')


class Adjudicator:
    def __init__(self, db: sqlite3.Connection, workspace: Path) -> None:
        self.db, self.workspace = db, workspace
        self.reviewers = {}
        self.functional_cache = {}
        self.obligation_cache = {}
        self.layers = LayerCompiler(db)

    def review(self, row: dict) -> dict:
        profile, _, _ = disposition(row)
        manual = source_review(row, profile)
        if manual and manual.can_offer_for_design:
            result = {'state': 'design_ready', 'can_offer_for_design': True, 'profile': profile,
                    'meaning': manual.meaning, 'boundary': manual.boundary,
                    'evidence_required': manual.evidence_required, 'related': list(manual.related),
                    'source_refs': [], 'conditions': [], 'missing': [], 'conflicts': [],
                    'owner_id': row['id'], 'contract': {'manually_reviewed': True}, 'manual_reviewed': True}
            return self._with_layers(row, result)
        family = row['family']
        group = _review_group(family)
        if group not in self.reviewers:
            if group == 'types':
                from nw.materials.type_adjudication import TypeAdjudicator
                reviewer = TypeAdjudicator(self.db)
            elif group == 'library':
                from nw.materials.library_adjudication import LibraryAdjudicator
                reviewer = LibraryAdjudicator(self.db)
            else:
                reviewer = NetworkAdjudicator(self.db, self.workspace)
            self.reviewers[group] = reviewer
        result = self.reviewers[group].review(row)
        if result is None:
            result = {'state': 'blocked', 'can_offer_for_design': False, 'profile': profile,
                      'meaning': '当前来源位置尚无完成的逐类裁定。',
                      'boundary': '先核定完整原义及适用合同。',
                      'evidence_required': '完整原文、条件、边界、项目产物及可检验依据。',
                      'source_refs': [], 'conditions': [], 'missing': ['source_specific_adjudication'],
                      'conflicts': [], 'related': [], 'contract': {}}
        result = dict(result)
        if manual is not None and not manual.can_offer_for_design:
            result.update(state='blocked', can_offer_for_design=False, manual_reviewed=True,
                          manual_review={'meaning': manual.meaning, 'boundary': manual.boundary,
                                         'evidence_required': manual.evidence_required})
            result['missing'] = [*result.get('missing', []), '已核读但未通过原义与执行资格核定，不能把核读记录当作采用资格']
        result.setdefault('owner_id', row['id'])
        result.setdefault('related', [])
        result.setdefault('contract', {})
        result.setdefault('manual_reviewed', False)
        result = retranslate(self.db, row, result)
        result = rebuild_function(self.db, row, result, self.functional_cache, engine=self.reviewers.get('types'))
        if result['state'] == 'design_ready' and not result['manual_reviewed']:
            result = self._with_obligations(row, result)
        if result['state'] not in _STATES or result['can_offer_for_design'] != (result['state'] == 'design_ready'):
            raise ValueError(f"Invalid adjudication state for {row['id']}")
        return self._with_layers(row, result)

    def _with_layers(self, row: dict, result: dict) -> dict:
        layers = self.layers.for_owner(row, result)
        return {**result, 'layer_contract': layers} if layers else result

    def _with_obligations(self, row: dict, result: dict) -> dict:
        owner = result['owner_id']
        if owner != row['id']:
            return result
        owners = [row]
        from nw.materials.route_catalog import _UNITS
        for dependency in result['contract'].get('dependency_contracts', []):
            if dependency.get('role') == 'exclusion_boundary':
                continue
            found = self.db.execute(_UNITS + ' WHERE u.id=?', (dependency['source_ref']['id'],)).fetchone()
            if found is None:
                raise ValueError('Material constituent source is missing')
            owners.append(dict(found))
        obligations = []
        seen = set()
        adopted = result.get('source_retranslation', {}).get('adopted_fields')
        library_fields = {item['ref']['id'] for items in result['contract'].values() if isinstance(items, list)
                          for item in items if isinstance(item, dict) and isinstance(item.get('ref'), dict)}
        for original in owners:
            if original['id'] not in self.obligation_cache:
                self.obligation_cache[original['id']] = self.db.execute("""SELECT u.id,u.kind,u.label,u.sha256,
                    substr(f.payload,u.byte_start-f.byte_start+1,u.byte_end-u.byte_start) AS payload
                    FROM material_units u JOIN fragments f ON f.id=u.fragment_id
            WHERE u.fragment_id=? AND u.origin='source' AND u.byte_start>=? AND u.byte_end<=?
              AND u.kind IN ('definition','instruction','condition','exception','constraint',
                           'prohibition','guarantee_boundary','check','effect','applicability')
            ORDER BY u.byte_start,u.byte_end,u.id""", (original['fragment_id'], original['byte_start'], original['byte_end'])).fetchall()
            fields = self.obligation_cache[original['id']]
            for field in fields:
                if row['family'] in {'library','anchors'} and field['id'] not in library_fields:
                    continue
                if adopted is not None and field['id'] not in adopted:
                    continue
                if field['id'] in seen:
                    continue
                seen.add(field['id'])
                data = field['payload']
                if sha256(data).hexdigest() != field['sha256']:
                    raise ValueError('Source obligation hash differs from the indexed field')
                text = data.decode('utf-8')
                excluded = False
                if row['family'] in {'types','type_links'}:
                    from nw.materials.type_adjudication import _original
                    value = json.loads(text)
                    effective = _original(value, [])
                    if effective != value:
                        if effective in ({}, []):
                            continue
                        text = canonical(effective)
                        excluded = True
                obligations.append({'id': field['id'], 'kind': field['kind'], 'label': field['label'],
                                    'owner_id': original['id'], 'sha256': field['sha256'], 'text': text,
                                    **({'nested_legacy_fields_excluded': True} if excluded else {})})
        return {**result, 'contract': {**result['contract'], 'obligations': obligations}}


def build_adjudications(workspace: Path) -> dict:
    from nw.materials.route_catalog import _FRAGMENTS, _UNITS, _check_complete

    folder = workspace / 'materials'
    target = folder / 'adjudication.db'
    pending = folder / f'adjudication-{uuid4().hex}.tmp'
    positions, roots = Counter(), Counter()
    by_family = defaultdict(Counter)
    manual = 0
    with closing(_connect(workspace, write=False)) as catalog, closing(sqlite3.connect(pending)) as saved:
        catalog.execute('BEGIN')
        _check_complete(catalog)
        fingerprint = _fingerprint(catalog, workspace)
        families_by_group = defaultdict(list)
        for (family,) in catalog.execute('SELECT DISTINCT family FROM sources ORDER BY family'):
            families_by_group[_review_group(family)].append(family)
        saved.executescript(_SCHEMA)
        try:
            with saved:
                for families in families_by_group.values():
                    engine = Adjudicator(catalog, workspace)
                    slots = ','.join('?' for _ in families)
                    for query in (_FRAGMENTS, _UNITS):
                        for raw in catalog.execute(query + f' WHERE s.family IN ({slots})', families):
                            row = dict(raw)
                            if disposition(row)[2] != 'candidate':
                                continue
                            review = engine.review(row)
                            owner = review['owner_id']
                            state = review['state']
                            if owner == row['id']:
                                _save_contract(saved, review, roots)
                            saved.execute('INSERT INTO positions VALUES (?,?,?,?,?,?,?,?)',
                                          (row['id'], row['sha256'], row['file_sha256'], owner, state,
                                           review['profile'], row['key'], row['path']))
                            positions[state] += 1
                            by_family[row['family']][state] += 1
                            manual += int(review['manual_reviewed'])
                    del engine
                absent = saved.execute("""SELECT DISTINCT owner_id FROM positions
                    WHERE owner_id NOT IN (SELECT owner_id FROM contracts)""").fetchall()
                previous_group = None
                for (owner,) in absent:
                    root = catalog.execute(_FRAGMENTS + ' WHERE f.id=?', (owner,)).fetchone()
                    if root is None:
                        root = catalog.execute(_UNITS + ' WHERE u.id=?', (owner,)).fetchone()
                    if root is None:
                        raise ValueError(f'Candidate context has no source owner: {owner}')
                    group = _review_group(root['family'])
                    if group != previous_group:
                        engine = Adjudicator(catalog, workspace)
                        previous_group = group
                    review = engine.review(dict(root))
                    if review['state'] == 'context' or review['owner_id'] != owner:
                        raise ValueError(f'Candidate context has an invalid owner: {owner}')
                    _save_contract(saved, review, roots)
                if _fingerprint(catalog, workspace) != fingerprint:
                    raise ValueError('Material adjudication inputs changed during the build; rerun the batch')
                summary = {'policy': POLICY, 'candidate_positions': sum(positions.values()),
                           'positions': dict(positions), 'source_contracts': sum(roots.values()), 'contracts': dict(roots),
                           'manual_reviewed_positions': manual,
                           'by_family': {key: dict(value) for key, value in sorted(by_family.items())}}
                saved.executemany('INSERT INTO metadata VALUES (?,?)',
                                  [(key, canonical(value)) for key, value in {**fingerprint, 'summary': summary}.items()])
            assert saved.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert saved.execute('PRAGMA foreign_key_check').fetchone() is None
        except BaseException:
            saved.close()
            pending.unlink(missing_ok=True)
            raise
    pending.replace(target)
    return summary


def read_adjudication(workspace: Path, row: dict) -> dict | None:
    target = workspace / 'materials' / 'adjudication.db'
    if not target.is_file():
        return None
    with closing(_connect(workspace, write=False)) as catalog, closing(
            sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as saved:
        saved.row_factory = sqlite3.Row
        meta = {item['key']: json.loads(item['value']) for item in saved.execute('SELECT * FROM metadata')}
        if any(meta.get(key) != value for key, value in _fingerprint(catalog, workspace).items()):
            return {'state': 'stale', 'can_offer_for_design': False, 'missing': ['rebuild_adjudications']}
        result = saved.execute("""SELECT p.*,c.payload_json FROM positions p JOIN contracts c ON p.owner_id=c.owner_id
                                  WHERE p.id=?""", (row['id'],)).fetchone()
        if result is None:
            return None
        if (result['sha256'], result['file_sha256']) != (row['sha256'], row['file_sha256']):
            raise ValueError('Adjudication source hash differs from the frozen location')
        review = json.loads(result['payload_json'])
        if result['state'] == 'context':
            review = {**review, 'state': 'context', 'owner_state': review['state'], 'can_offer_for_design': False}
        return review


def adjudication_status(workspace: Path) -> dict:
    target = workspace / 'materials' / 'adjudication.db'
    if not target.is_file():
        return {'status': 'missing', 'summary': None}
    with closing(_connect(workspace, write=False)) as catalog, closing(
            sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as saved:
        meta = {key: json.loads(value) for key, value in saved.execute('SELECT * FROM metadata')}
        current = all(meta.get(key) == value for key, value in _fingerprint(catalog, workspace).items())
    return {'status': 'current' if current else 'stale', 'summary': meta.get('summary')}


def inspect_adjudications(workspace: Path, *, state: str | None = None, profile: str | None = None,
                           key: str | None = None, roots_only: bool = False, limit: int = 50, offset: int = 0) -> dict:
    if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
        raise ValueError('Invalid adjudication page')
    target = workspace / 'materials' / 'adjudication.db'
    if not target.is_file():
        raise ValueError('Run materials adjudicate before inspecting the ledger')
    with closing(sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as db, closing(
            _connect(workspace, write=False)) as catalog:
        db.row_factory = sqlite3.Row
        meta = {row['key']: json.loads(row['value']) for row in db.execute('SELECT * FROM metadata')}
        if any(meta.get(name) != value for name, value in _fingerprint(catalog, workspace).items()):
            raise ValueError('MATERIAL_ADJUDICATION_STALE: rerun materials adjudicate')
        summary = json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
        filters, values = [], []
        for column, value in [('state', state), ('profile', profile)]:
            if value is not None:
                filters.append(f'{column}=?')
                values.append(value)
        if key is not None:
            filters.append("""(instr(COALESCE(key,''),?)>0 OR owner_id IN (
                SELECT owner_id FROM contracts
                WHERE instr(COALESCE(json_extract(payload_json,'$.contract.scoped_id.original_id'),''),?)>0
                   OR instr(COALESCE(json_extract(payload_json,'$.meaning'),''),?)>0))""")
            values.extend((key, key, key))
        if roots_only:
            filters.append('id=owner_id')
        clause = ' WHERE ' + ' AND '.join(filters) if filters else ''
        count = db.execute('SELECT count(*) FROM positions' + clause, values).fetchone()[0]
        rows = [dict(row) for row in db.execute('SELECT id,owner_id,state,profile,key,path FROM positions' + clause +
                                               ' ORDER BY id LIMIT ? OFFSET ?', (*values, limit, offset))]
    return {'summary': summary, 'matches': count, 'offset': offset, 'positions': rows}

