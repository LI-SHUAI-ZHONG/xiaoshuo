"""Explain every frozen source position and audit routing coverage."""
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from nw.materials.catalog import _connect
from nw.materials.identity_catalog import edge_identity
from nw.materials.reviews import source_review
from nw.materials.routing import POLICY, PROFILES, disposition
from nw.materials.adjudication import adjudication_status, read_adjudication


_FRAGMENT_COLUMNS = """
    f.id, 'fragment' AS level, f.id AS fragment_id, f.kind, f.key, NULL AS label, NULL AS locator,
    'source' AS origin, f.byte_start, f.byte_end, f.line_start, f.line_end, f.sha256
"""
_UNIT_COLUMNS = """
    u.id, 'unit' AS level, f.id AS fragment_id, u.kind, u.key, u.label, u.locator,
    u.origin, u.byte_start, u.byte_end, u.line_start, u.line_end, u.sha256
"""
_COMMON = """
    , f.key AS fragment_key, f.line_start AS fragment_line_start, f.line_end AS fragment_line_end,
      s.id AS source_id, s.path, s.family, s.layer, s.file_sha256, f.sha256 AS fragment_sha256
"""
_FRAGMENTS = f"""SELECT {_FRAGMENT_COLUMNS} {_COMMON}
                FROM fragments f JOIN sources s ON s.id=f.source_id"""
_UNITS = f"""SELECT {_UNIT_COLUMNS} {_COMMON}
            FROM material_units u JOIN fragments f ON f.id=u.fragment_id JOIN sources s ON s.id=f.source_id"""
_SUPPORT = {'condition','exception','alternative','prohibition','guarantee_boundary','dependency'}


def _check_complete(connection: sqlite3.Connection) -> None:
    tables = {r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE name IN ('unit_checkpoints','material_units')")}
    if len(tables) != 2 or connection.execute("""
        SELECT 1 FROM sources s LEFT JOIN unit_checkpoints u ON u.source_id=s.id
        WHERE u.source_id IS NULL LIMIT 1
    """).fetchone() is not None:
        raise ValueError('Run materials index-units for all sources before auditing routes')


def audit_routes(workspace: Path) -> dict:
    coverage: Counter = Counter()
    profiles: Counter = Counter()
    eligibility: Counter = Counter()
    interpretation: Counter = Counter()
    by_source: dict = defaultdict(Counter)
    reviewed: list[dict] = []
    with closing(_connect(workspace, write=False)) as connection:
        connection.execute('BEGIN')
        _check_complete(connection)
        sources = connection.execute('SELECT count(*) FROM sources').fetchone()[0]
        for query in (_FRAGMENTS, _UNITS):
            for raw in connection.execute(query):
                row = dict(raw)
                profile, state, permission = disposition(row)
                review = source_review(row, profile) if permission == 'candidate' else None
                if review is not None:
                    state = 'reviewed'
                coverage[row['level']] += 1
                profiles[profile] += 1
                eligibility[permission] += 1
                interpretation[state] += 1
                by_source[row['layer'],row['family']][permission] += 1
                if state == 'reviewed':
                    reviewed.append({'id':row['id'],'key':row['key'],'line_start':row['line_start'],
                                     'sha256':row['sha256'],'profile':profile,'path':row['path']})
    return {
        'policy':POLICY, 'sources':sources, 'coverage':dict(coverage), 'profiles':dict(profiles),
        'adjudication': adjudication_status(workspace),
        'eligibility':dict(eligibility), 'interpretation':dict(interpretation), 'execution_allowed':0,
        'by_layer_family':[{'layer':layer,'family':family,'eligibility':dict(counts)}
                           for (layer,family),counts in sorted(by_source.items())],
        'reviewed':sorted(reviewed,key=lambda item:item['line_start']),
    }


def _supporting_fields(connection: sqlite3.Connection, row: dict) -> list[dict]:
    if row['level'] == 'fragment' and row['kind'] not in {'library_entry','library_block','network_edge','anchor'}:
        return []
    if row['origin'] in {'upgrade','residual'}:
        return []
    locator = row['locator'] or ''
    if locator.startswith('/') or (row['kind']=='record' and row['family'] in {'types','type_links'}):
        pointer = locator if row['kind']=='record' else locator.rpartition('/')[0]
    else:
        pointer = None
    fields = []
    for item in connection.execute("""
        SELECT id,kind,label,locator,sha256,line_start FROM material_units
        WHERE fragment_id=? AND origin='source' AND id<>? ORDER BY byte_start, id
    """, (row['fragment_id'],row['id'])):
        if item['kind'] not in _SUPPORT:
            continue
        if pointer is not None and item['locator'].rpartition('/')[0] != pointer:
            continue
        fields.append(dict(item))
    return fields


def _issues(workspace: Path, row: dict) -> list[dict]:
    folder = workspace / 'materials'
    path = folder / 'F2_统一问题台账.jsonl'
    if not path.is_file():
        path = folder / 'F1_统一问题台账.jsonl'
    if not path.is_file():
        return []
    found = []
    with path.open(encoding='utf-8') as source:
        for line in source:
            if not line.strip():
                continue
            issue = json.loads(line)
            ref = issue['source_locator']
            matches_source = ref.get('path') == row['path'] and issue.get('source_hash') == row['file_sha256']
            if matches_source:
                related = issue.get('related_ids', [])
                if row['id'] in related or row['fragment_id'] in related:
                    matches_source = True
                elif ref.get('unit_id'):
                    matches_source = ref['unit_id'] == row['id']
                elif 'line' in ref:
                    matches_source = row['fragment_line_start'] <= ref['line'] <= row['fragment_line_end']
            if not matches_source and issue['kind']=='cross_version_identifier_collision':
                matches_source = any(x['fragment_id']==row['fragment_id'] and x['source_hash']==row['file_sha256']
                                     for x in issue['evidence']['现行编号'])
            if matches_source:
                found.append({'id':issue['issue_id'],'kind':issue['kind'],'status':issue['status']})
    return found


def route(workspace: Path, object_id: str) -> dict:
    with closing(_connect(workspace, write=False)) as connection:
        connection.execute('BEGIN')
        _check_complete(connection)
        raw = connection.execute(_FRAGMENTS + ' WHERE f.id=?',(object_id,)).fetchone()
        if raw is None:
            raw = connection.execute(_UNITS + ' WHERE u.id=?',(object_id,)).fetchone()
        if raw is None:
            raise ValueError('Material fragment or unit not found')
        row = dict(raw)
        profile, state, eligibility = disposition(row)
        review = source_review(row,profile) if eligibility == 'candidate' else None
        qualified = review is not None and review.can_offer_for_design
        adjudication = read_adjudication(workspace, row) if eligibility == 'candidate' else None
        if qualified:
            state = 'reviewed'
        elif adjudication is not None and adjudication['state'] == 'design_ready':
            state = 'adjudicated'
            profile = adjudication['profile']
        support = _supporting_fields(connection,row) if eligibility == 'candidate' else []
        review_data = asdict(review) if review is not None else None
        if qualified:
            # Preserve the frozen representation of previously qualified reviews.
            review_data.pop('can_offer_for_design')
    return {
        'policy':POLICY, 'profile':profile, **asdict(PROFILES[profile]), 'interpretation':state,
        'eligibility':eligibility, 'execution_allowed':False, 'source':row,
        'supporting_fields':support, 'issues':_issues(workspace,row),
        'source_review':review_data,
        'adjudication': adjudication,
        'network_identity':edge_identity(workspace,row),
    }
