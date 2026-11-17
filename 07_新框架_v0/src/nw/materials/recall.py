"""Recall qualified, version-pinned functional sources for normal planning."""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from nw.materials.adjudication import adjudication_status
from nw.materials.binding import BOOK, PROCESS, _type_id, resolve_materials
from nw.materials.catalog import _connect, show_fragment
from nw.selection import _keywords

POLICY = 'catalog-functional-recall-v1'
_CORE = ('128.4_', '127.5_')
_SPECIAL_PROCESS_CUES=('对话','动作','环境','复盘','修正','篇幅','节奏','信息释放','异常','例外',
                       '角色类型','章节类型','场景功能','读者体验')


def recall_materials(workspace: Path, terms: str, *, scope: str = 'book',
                     existing: list[dict] = ()) -> tuple[list[dict], dict]:
    report = {'policy': POLICY, 'scope': scope, 'status': 'catalog_missing', 'selected': [],
              'candidates': [], 'excluded': [], 'literary_effects_verified': False}
    if not (workspace / 'materials' / 'catalog.db').is_file():
        return [], report
    status = adjudication_status(workspace)
    if status['status'] != 'current':
        raise ValueError('STALE_MATERIAL: automatic selection requires current materials adjudicate')
    report.update(status='recalled', ledger=status.get('fingerprint', {}))
    with closing(_connect(workspace, write=False)) as catalog:
        families = {r['path']: r['family'] for r in catalog.execute('SELECT path,family FROM sources')}
    path = workspace / 'materials' / 'adjudication.db'
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(r) for r in db.execute('''SELECT p.id,p.sha256,p.file_sha256,p.key,p.profile,p.path,
            coalesce(json_extract(c.payload_json,'$.contract.identity.canonical_name'),p.key) AS title,
            coalesce(json_extract(c.payload_json,'$.contract.scoped_id.original_id'),p.key) AS logical_id,
            json_extract(c.payload_json,'$.contract.effective_constituent_fields.primary_type_id') AS primary_type,
            json_extract(c.payload_json,'$.contract.source_id') AS type_source,
            json_extract(c.payload_json,'$.contract.target_id') AS type_target,
            json_extract(c.payload_json,'$.meaning') AS meaning
            FROM positions p JOIN contracts c ON c.owner_id=p.owner_id
            WHERE p.id=p.owner_id AND p.state='design_ready' ORDER BY p.path,p.key,p.id''')]
        counts = dict(db.execute('SELECT state,count(*) FROM positions WHERE id=owner_id GROUP BY state'))
    report['qualified_owners'] = len(rows)
    report['owner_states'] = counts
    for row in rows:
        if row['profile']=='type_identity' and row['title']==row['key']:
            original=json.loads(show_fragment(workspace,row['id'])['text'])
            if isinstance(original,dict) and isinstance(original.get('canonical_name'),str):
                row['title']=original['canonical_name']
                row['logical_id']=_type_id(original) or row['logical_id']
    known = {r['source']['id']: r for r in existing}
    selected_types = {r.get('original', {}).get('canonical_name') for r in existing
                      if r['profile'] == 'type_identity' and isinstance(r.get('original'), dict)}
    logical_types = {r['original'].get('type_id') or r['original'].get('hybrid_id') for r in existing
                     if r['profile']=='type_identity' and isinstance(r.get('original'),dict)}
    book_choices = Counter(r['profile'] for r in existing if r['profile'] in {'type_combination','type_link'})
    process_choices = Counter(r['profile'] for r in existing if r['profile'] in {'material_selection','material_conversion'}
                              and not any(r['source']['key'].startswith(key) for key in _CORE))
    excluded, chosen, scored = Counter(), [], []
    keywords = _keywords([terms])
    for row in rows:
        if row['id'] in known:
            continue
        title = row['title'] or ''
        hits = sorted(keywords & _keywords([title]))
        semantic = keywords & _keywords([row['meaning'] or ''])
        core = any((row['key'] or '').startswith(key) for key in _CORE)
        if row['profile'] in {'material_selection','material_conversion'} and not core:
            if process_choices[row['profile']]>=1 or not any(cue in (row['key'] or '') and cue in terms
                                                            for cue in _SPECIAL_PROCESS_CUES):
                excluded['PROCESS_FUNCTION_ALREADY_COVERED_OR_NOT_TRIGGERED']+=1
                continue
        if row['profile'] in BOOK:
            if row['profile'] == 'type_identity' and (not title or title not in terms):
                excluded['TYPE_REQUIRES_EXPLICIT_FIT'] += 1
                continue
        if not core and not hits and len(semantic) < 2 and row['profile']!='type_link':
            excluded['NO_FUNCTION_MATCH'] += 1
            continue
        scored.append(((-1000 if core else -len(hits)*10-len(semantic)*3), row,
                       '阶段流程：' + row['key'] if core else '当前任务匹配具体来源功能：' + '、'.join(sorted(set(hits)|semantic))))
    scored.sort(key=lambda item: (item[0], item[1]['id']))
    signatures = {(r['profile'], r['source']['key']) for r in existing}
    optional = sum(r['profile'] not in PROCESS | BOOK for r in existing)
    used_families = Counter(r['source']['family'] for r in existing if r['profile'] not in PROCESS)
    # Diversify recall; exact dependencies are added atomically with their child.
    def rank(item):
        return (0 if item[0] <= -1000 else 1 if item[1]['profile']=='type_identity'
                else 2 if item[1]['profile'] in BOOK else 3,
                used_families[families.get(item[1]['path'], '')], item[0], item[1]['id'])
    scored.sort(key=rank)
    while scored:
        _, row, reason = scored.pop(0)
        report['candidates'].append({'id': row['id'], 'key': row['key'], 'profile': row['profile'], 'reason': reason})
        signature = row['profile'], row['title'] if row['profile'] == 'type_identity' else row['key']
        if signature in signatures or row['profile'] == 'type_identity' and row['title'] in selected_types:
            excluded['SAME_FUNCTION_VERSION_ALREADY_CHOSEN'] += 1
            continue
        if row['profile']=='type_identity' and row['logical_id'] in logical_types:
            excluded['EXACT_TYPE_ID_VERSION_ALREADY_CHOSEN'] += 1
            continue
        if row['profile'] in {'type_combination','type_link'}:
            if book_choices[row['profile']] >= 1 or (row['profile']=='type_combination' and row['primary_type'] not in logical_types
                    or row['profile']=='type_link' and not {row['type_source'],row['type_target']} <= logical_types):
                excluded['TYPE_COMPOSITION_CONTEXT_OR_BUDGET'] += 1
                continue
        core = any((row['key'] or '').startswith(key) for key in _CORE)
        if not core and row['profile'] not in BOOK | PROCESS and optional >= 5:
            excluded['OPTIONAL_METHOD_BUDGET'] += 1
            continue
        if not core and row['profile'] in {'material_selection','material_conversion'} and process_choices[row['profile']]>=1:
            excluded['PROCESS_FUNCTION_ALREADY_COVERED_OR_NOT_TRIGGERED']+=1
            continue
        pin = {key: row[key] for key in ('id', 'file_sha256', 'sha256')}
        record = resolve_materials(workspace, [{**pin, 'disposition': 'required', 'reason': reason}])[0]
        contract = record['review'].get('contract', {})
        if row['profile']=='type_combination':
            selected_roots = {r['source']['id'] for r in [*existing,*chosen] if r['profile']=='type_identity'}
            groups = [g['root_ids'] for g in contract.get('constituents',[]) if g['original_id'] in logical_types]
            if not groups or any(not selected_roots.intersection(ids) for ids in groups):
                excluded['TYPE_COMBINATION_REQUIRES_EXACT_SELECTED_SOURCE_VERSIONS'] += 1
                continue
        if row['profile']=='type_link':
            selected_roots = {r['source']['id'] for r in [*existing,*chosen] if r['profile']=='type_identity'}
            groups = [g['root_ids'] for g in contract.get('constituents',[]) if g['field'] in {'source_id','target_id'}]
            if len(groups)!=2 or any(not selected_roots.intersection(ids) for ids in groups):
                excluded['TYPE_LINK_REQUIRES_EXACT_SELECTED_SOURCE_VERSIONS'] += 1
                continue
        valid_types = contract.get('valid_types', [])
        if valid_types and not selected_types.intersection(valid_types):
            excluded['TYPE_PRECONDITION_NOT_ADOPTED'] += 1
            continue
        dependency_ids = record['review'].get('related', []) if record['profile'] in {'dynamic_binding', 'dynamic_relation'} else []
        dependencies = []
        if contract.get('generated_from_static') or record['profile'] == 'dynamic_binding':
            allowed = [r for r in rows if r['id'] in dependency_ids and r['profile'] in {'static_binding', 'static_relation'}]
            if not allowed:
                excluded['EXACT_STATIC_DEPENDENCY_UNAVAILABLE'] += 1
                continue
            upstream = allowed[0]
            if upstream['id'] not in known and upstream['id'] not in {r['source']['id'] for r in chosen}:
                dependency = {key: upstream[key] for key in ('id', 'file_sha256', 'sha256')}
                dependencies = resolve_materials(workspace, [{**dependency, 'disposition': 'required',
                    'reason': '采用动态边之前必须绑定其确切静态依赖：' + row['key']}])
        if not core and row['profile'] not in BOOK | PROCESS and optional + 1 + len(dependencies) > 5:
            excluded['DEPENDENCY_BUNDLE_EXCEEDS_METHOD_BUDGET'] += 1
            continue
        for value in [*dependencies, record]:
            if value['source']['id'] in {r['source']['id'] for r in chosen}:
                continue
            chosen.append(value)
            if value['profile'] not in PROCESS:
                used_families[value['source']['family']] += 1
            signatures.add((value['profile'], value['source']['key']))
            report['selected'].append({'id': value['source']['id'], 'key': value['source']['key'],
                'profile': value['profile'], 'reason': value['request']['reason']})
        if row['profile'] == 'type_identity':
            selected_types.add(row['title'])
            logical_types.add(row['logical_id'])
        elif row['profile'] in {'type_combination','type_link'}:
            book_choices[row['profile']]+=1
        elif row['profile'] in {'material_selection','material_conversion'} and not core:
            process_choices[row['profile']]+=1
        elif not core and row['profile'] not in PROCESS:
            optional += 1 + len(dependencies)
        scored.sort(key=rank)
    report['excluded_counts'] = dict(excluded)
    report['candidates'] = report['candidates'][:40]
    report['adoption'] = 'candidate_until_author_approves_plan_and_independent_evidence_passes'
    return chosen, report
