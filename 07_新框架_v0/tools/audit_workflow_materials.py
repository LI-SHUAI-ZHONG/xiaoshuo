"""Read-only inventory of production stages and the Studio corpus interface.

Writes audit evidence only. Does not create novels, rebuild source data, call
models, or change the runtime implementation.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent
sys.path.insert(0, str(PROJECT / 'src'))

from nw import cards
from nw.materials import phase_flow
from nw.materials.adjudication import _code_hash, adjudication_status
from nw.materials.phase_contract import FIELDS
from nw.materials.phase_routes import EXTERNAL_REQUIRES, ORDER, REQUIRES, phase_order
from nw.materials.source_set import selection_status
from nw.materials.stage_input import extract_step_keys, step_material_prompt
from nw.materials.work_catalog import SourceDesk
from nw.studio import catalog
from nw.studio.production_inputs import STAGES as PREFERENCE_STAGES


def sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(REPOSITORY), *args], text=True, encoding='utf-8').strip()


def assigned(path: str, name: str) -> ast.AST:
    tree = ast.parse((PROJECT / path).read_text(encoding='utf-8'))
    return next(node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))


def literal(path: str, name: str) -> object:
    return ast.literal_eval(assigned(path, name))


def definitions(path: str) -> dict:
    tree = ast.parse((PROJECT / path).read_text(encoding='utf-8'))
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            result[node.name] = {'path': path, 'line': node.lineno}
    return result


def resources() -> dict:
    node = assigned('src/nw/materials/phase_flow.py', 'STAGE_MATERIALS')
    result = {}
    for key, value in zip(node.keys, node.values, strict=True):
        stage = ast.literal_eval(key)
        modules = sorted({part.value.id for part in ast.walk(value)
                          if isinstance(part, ast.Attribute) and part.attr == 'MATERIAL'
                          and isinstance(part.value, ast.Name)})
        rows = []
        for name in modules:
            module = getattr(phase_flow, name)
            path = Path(module.__file__).resolve()
            material = module.MATERIAL
            rows.append({'module': name, 'path': path.relative_to(PROJECT).as_posix(),
                         'file_sha256': sha(path), 'material_characters': len(material),
                         'headings': [line.strip('# ').strip() for line in material.splitlines()
                                      if line.startswith('### ')]})
        result[stage] = rows
    return result


def studio_catalog() -> dict:
    rows = {}
    for slot in catalog.SLOTS:
        options = [value for value in catalog.option_map(slot).values()
                   if value.get('selectable') is not False]
        rows[slot] = {
            'selectable_options': len(options),
            'source_files': sorted({value.get('source_ref', {}).get('file') for value in options
                                    if value.get('source_ref', {}).get('file')}),
            'decomposition_default_stages': list(catalog.SLOT_STAGES[slot]),
            'wizard_preference_stages': list(PREFERENCE_STAGES[slot]),
            'options': [{'key': value['key'], 'name': value['name'],
                         'source_ref': value.get('source_ref', {})} for value in options],
        }
    defaults = {stage for stages in catalog.SLOT_STAGES.values() for stage in stages}
    return {'slots': rows, 'default_stage_count': len(defaults),
            'stages_without_decomposition_default': [stage for stage in ORDER if stage not in defaults],
            'explicit_stage_override_supported': True,
            'mapping_differences': {slot: {
                'decomposition': list(catalog.SLOT_STAGES[slot]), 'preference': list(PREFERENCE_STAGES[slot])}
                for slot in catalog.SLOTS if catalog.SLOT_STAGES[slot] != PREFERENCE_STAGES[slot]},
            'limits': 'Default mappings are not semantic coverage; explicit stage tags may reach other stages.'}


def runtime() -> dict:
    workspace = PROJECT / 'workspace'
    result = {'workspace': str(workspace), 'database_access': 'SQLite URI mode=ro',
              'models_called': 0, 'novels_created': 0}
    path = workspace / 'library/library.db'
    if path.is_file():
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            db.execute('BEGIN')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            names = ('staging_books', 'decomp_items', 'type_kb', 'upgrade_candidates',
                     'upgrade_versions', 'reviewed_adoptions', 'novels')
            result['library_table_counts'] = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                                               for name in names if name in tables}
            result['library_table_columns'] = {name: [row[1] for row in db.execute('PRAGMA table_info(' + name + ')')]
                                                 for name in names if name in tables}
            result['decomposition_states'] = dict(db.execute('SELECT status,count(*) FROM decomp_items GROUP BY status'))
    if (workspace / 'materials/catalog.db').is_file():
        desk = SourceDesk(workspace)
        selected = selection_status(workspace)
        result['materials'] = {'rows': len(desk.rows), 'states': dict(Counter(row['state'] for row in desk.rows)),
                               'profiles': dict(Counter(row['profile'] for row in desk.rows)),
                               'selected_source_files': selected['active_file_sources'] if selected else None,
                               'adjudication_status': adjudication_status(workspace)['status'],
                               'explicit_binding_review_records': len(desk.binding_reviews),
                               'note': 'Review-record count excludes runtime-generated in-step uses; neither count proves semantic completion.'}
    return result


def protection() -> dict:
    path = PROJECT / 'docs/客户端v3交付包/protected-baseline.json'
    old = json.loads(path.read_text(encoding='utf-8'))
    current = {'adjudication': _code_hash(), 'phase_routes': sha(PROJECT / 'src/nw/materials/phase_routes.py'),
               'originals': {name: sha(REPOSITORY / name) for name in old['originals']}}
    return {'matches_pre_client_baseline': current == old, 'original_files': len(old['originals']),
            'core_files': 21, 'fingerprints': current}


def collect(audit_date: str) -> dict:
    material_resources = resources()
    studio = studio_catalog()
    stages = []
    for stage in ORDER:
        text = phase_flow.STAGE_MATERIALS[stage]
        keys = sorted(extract_step_keys(text))
        modules = material_resources[stage]
        exposed = {filename for slot in studio['slots'].values() for filename in slot['source_files']}
        stages.append({
            'stage': stage, 'in_book_scope': stage in phase_order('book'),
            'required_prior_stages': list(REQUIRES[stage]),
            'dynamic_inputs': 'Named semantic handoffs append their origin; bind_scope gathers all actual scope stages.',
            'required_product_fields': sorted(FIELDS[stage]),
            'direct_consumers': [name for name in ORDER if stage in REQUIRES[name]],
            'default_decomposition_slots': [slot for slot in catalog.SLOTS if stage in catalog.SLOT_STAGES[slot]],
            'static_material_characters': len(text), 'static_material_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'in_step_keys_count': len(keys),
            'sample_single_key': keys[0] if keys else None,
            'sample_single_key_instruction_characters': len(step_material_prompt('AUDIT', text, keys[:1])),
            'sample_is_real_call_measurement': False,
            'direct_resource_modules': modules,
            'direct_modules_exposed_in_any_studio_option': [row['module'] for row in modules if Path(row['path']).name in exposed],
            'note': 'Resources are supply inventory, not proof of correct per-source use. Final text also includes generated type-connection instructions.'})
    files = ('src/nw/materials/phase_flow.py', 'src/nw/materials/phase_contract.py',
             'src/nw/materials/phase_schema.py', 'src/nw/materials/stage_input.py',
             'src/nw/materials/work_session.py', 'src/nw/materials/semantic_handoff.py',
             'src/nw/studio/staging.py', 'src/nw/studio/staging_model.py', 'src/nw/studio/recommend.py',
             'src/nw/studio/catalog.py', 'src/nw/studio/production_inputs.py', 'src/nw/materials/author_references.py',
             'src/nw/planning.py', 'src/nw/plan_contract.py', 'src/nw/plan_application.py',
             'src/nw/novel_flow.py', 'src/nw/novel_scene.py', 'src/nw/novel_calls.py',
             'src/nw/acceptance.py', 'src/nw/story_extract.py', 'src/nw/chapter_records.py',
             'src/nw/cards.py', 'src/nw/call_budget.py', 'src/nw/materials/phase_routes.py',
             'src/nw/materials/semantic_products.py', 'src/nw/materials/step_guard.py',
             'src/nw/materials/stage_effects.py', 'src/nw/studio/production.py',
             'src/nw/studio/production_views.py', 'src/nw/studio/kb.py')
    now = datetime.now(timezone.utc)
    report = {'format_version': 1, 'audit_date': date.fromisoformat(audit_date).isoformat(),
              'generated_at_utc': now.isoformat(), 'client_timezone': 'America/New_York',
              'baseline_commit': git('rev-parse', 'HEAD'),
              'audited_src_tree': git('rev-parse', 'HEAD:' + PROJECT.relative_to(REPOSITORY).as_posix() + '/src'),
              'src_worktree_status': git('status', '--porcelain', '--', PROJECT.relative_to(REPOSITORY).as_posix() + '/src'),
              'scope': 'All 14 stage interfaces and direct material modules, corpus catalog and adapters, downstream source paths, focused semantic samples. Not a clause-by-clause semantic certification of all original material.',
              'book_stages': phase_order('book'), 'detail_stages': list(ORDER),
              'stages': stages, 'external_requires': {key: list(value) for key, value in EXTERNAL_REQUIRES.items()},
              'card_fields': {'required': cards._REQUIRED, 'optional': cards._OPTIONAL,
                              'lists': cards._LISTS, 'maps': cards._MAPS},
              'studio_catalog': studio, 'runtime': runtime(), 'protected_files': protection(),
              'evidence_symbols': {path: definitions(path) for path in files},
              'source_file_hashes': {path: sha(PROJECT / path) for path in files}}
    assert len(report['stages']) == 14 and set(FIELDS) == set(ORDER)
    assert report['protected_files']['matches_pre_client_baseline']
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit-date', required=True, help='Client-local date, YYYY-MM-DD; independent of host timezone')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(PROJECT / 'docs'):
        raise ValueError('Audit evidence must be saved under this project docs directory')
    report = collect(args.audit_date)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'stages': len(report['stages']),
                      'resource_references': sum(len(stage['direct_resource_modules']) for stage in report['stages']),
                      'decomposition_default_stages': report['studio_catalog']['default_stage_count'],
                      'library_counts': report['runtime'].get('library_table_counts', {}),
                      'protected_files_unchanged': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
