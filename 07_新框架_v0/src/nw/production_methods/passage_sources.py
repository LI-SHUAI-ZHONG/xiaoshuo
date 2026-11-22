"""Resolve optional narration techniques from approved, genre-matched passages."""
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.production_methods.sources import MethodReader
from nw.selection import _keywords
from nw.studio.corpus_catalog import SCHEMA_VERSION
from nw.task_models import canonical


def _eligible(library, types: list[str], *, method_id: str | None = None) -> Iterator[dict]:
    # Narrow by task and approval before opening whole reference books for evidence checks.
    sql = """
        SELECT m.*, json_extract(mv.body_json,'$.type_tags') AS type_tags, b.confirmed_types_json, b.title, b.filename,
               review.created_at AS reviewed_at
        FROM production_methods m
        JOIN production_method_versions mv ON mv.method_id=m.id AND mv.version=m.approved_version
        JOIN production_method_reviews review ON review.method_id=m.id AND review.version=mv.version
        JOIN corpus_method_origins o ON o.method_id=m.id AND o.method_version=mv.version
        JOIN corpus_structures h ON h.book_id=o.book_id AND h.approved_version=o.structure_version
        JOIN corpus_structure_versions v ON v.book_id=h.book_id AND v.version=h.approved_version
        JOIN staging_books b ON b.id=v.book_id
        LEFT JOIN corpus_jobs j ON j.id=v.job_id
        WHERE review.decision='approve' AND b.status!='rejected'
          AND json_extract(v.body_json,'$.schema_version')=?
          AND coalesce(json_extract(j.runtime_json,'$.provider'),'') NOT IN ('fake','test-only')
          AND EXISTS (SELECT 1 FROM json_each(mv.body_json,'$.tasks') WHERE value='narration')
          AND json_array_length(o.basis_json,'$.thread_ids')=1
          AND EXISTS (SELECT 1 FROM json_each(v.body_json,'$.threads') t
                      WHERE json_type(t.value,'$.details.passage_sequence')='object'
                      AND json_extract(t.value,'$.id') IN (SELECT value FROM json_each(o.basis_json,'$.thread_ids')))
    """
    params = [SCHEMA_VERSION]
    if method_id is not None:
        sql += ' AND m.id=?'
        params.append(method_id)
    with library.connect() as conn:
        matches = []
        for head in conn.execute(sql + ' ORDER BY reviewed_at DESC, m.id', params):
            if any(head[k].strip().startswith('[FAKE]') for k in ('title','filename')):
                continue
            match = type_match(types, json.loads(head['type_tags']))
            book_match = type_match(types, json.loads(head['confirmed_types_json']))
            if (not match or not book_match or match['level'] == 'cross_type'
                    or book_match['level'] == 'cross_type'):
                continue
            matches.append((TYPE_PRIORITY[match['level']], head))
        for _, head in sorted(matches, key=lambda pair: pair[0]):
            books = {}
            row = library._method_row(dict(head), head['approved_version'], conn, books)
            if not row['current_for_production']:
                continue
            origin = row['structure_origin']
            body = row['body']
            outputs = {out['key'] for out in body['outputs']
                       if out['stage'] == 'expression_design' and out['field'] == 'guidance'}
            operations = [op for op in body['operations'] if outputs.intersection(op['output_keys'])]
            inputs = {key for op in operations for key in op['input_keys']}
            for sequence in origin.get('passage_sequences', []):
                if books[origin['book_id']][1].lstrip().startswith('[FAKE]'):
                    continue
                yield {
                    'ref': f"{row['id']}@{row['version']}#{sequence['thread_id']}",
                    'method_id': row['id'], 'version': row['version'], 'book_id': origin['book_id'],
                    'structure_version': origin['structure_version'], 'thread_id': sequence['thread_id'],
                    'body_sha256': row['body_sha256'], 'type_ids': list(types),
                    'scopes': sorted(set(row['body']['scopes']) & {'chapter', 'scene'}),
                    'kind': sequence['kind'], 'condition': sequence['condition'], 'boundary': sequence['boundary'],
                    'applicability': body['applicability'], 'non_applicability': body['non_applicability'],
                    'prerequisites': [p['requirement'] for p in body['prerequisites'] if p['key'] in inputs],
                    'operations': [op['instruction'] for op in operations],
                    'roles': [beat['role'] for beat in sequence['beats']],
                }


def recommendations(library, types: list[str]) -> list[dict]:
    """Keep the eligible pool until the project has actual events to rank it against."""
    return list(_eligible(library, types)) if types else []


def scene_candidates(references: list[dict], events: dict, actions: list[dict]) -> list[dict]:
    if not references:
        return []
    by_kind = defaultdict(list)
    for ref in references:
        words = _keywords([ref['condition'], *ref.get('applicability', []),
                           *ref.get('prerequisites', []), *ref.get('operations', [])])
        by_kind[ref['kind']].append((ref, words))
    actions_by_event = defaultdict(list)
    for action in actions:
        actions_by_event[action['event']].append(action)
    result = {}
    for ident, event in events.items():
        needs = _keywords([canonical(event), canonical(actions_by_event[ident])])
        for group in by_kind.values():
            ranked = sorted(group, key=lambda pair: len(needs & pair[1]), reverse=True)
            for ref, _ in ranked[:2]:
                if ref['ref'] not in result:
                    result[ref['ref']] = {key:ref[key] for key in (
                        'ref','kind','condition','boundary','roles','applicability','non_applicability','prerequisites')
                        if key in ref} | {'events': []}
                result[ref['ref']]['events'].append(ident)
    return list(result.values())


def verify_choices(workspace: Path, references: list[dict], choices: list[dict]) -> None:
    selected = {row['source_ref'] for row in choices if row.get('source_ref')}
    if not selected:
        return
    reader = MethodReader(workspace)
    frozen = {r['ref']: r for r in references}
    for ref in selected:
        pin = frozen.get(ref)
        if not pin or not reader.db_path.is_file() or not any(
                actual == pin for actual in _eligible(reader, pin['type_ids'], method_id=pin['method_id'])):
            raise ValueError('STALE_PROJECT_METHOD: 本场选用的段落方法、适用类型或原作依据已变化，请重新设计本场')
