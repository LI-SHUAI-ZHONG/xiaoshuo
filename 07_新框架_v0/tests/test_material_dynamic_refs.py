"""Versioned dynamic edges qualify only with their actual source and relationship."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from nw.materials.adjudication import build_adjudications
from nw.materials.catalog import build_catalog
from nw.materials.dynamic_refs import current_rule_proofs, dynamic_reference
from nw.materials.governance_checks import evaluate_governance
from nw.materials.governance_contracts import fingerprint
from nw.materials.identity_catalog import audit_identities
from nw.materials.unit_catalog import index_units
from test_material_catalog import _manifest
from test_material_governance_execution import compile_docs, inputs


@pytest.fixture
def dynamic_catalog(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / 'workspace'
    root = tmp_path / 'sources'
    library = '### 5.1_天气\n【定义】天气的变化。\n### 5.2_路况\n【定义】可以通行的路线。\n'
    edges = [
        {'id': 'C00214', 'source': '5.2_路况', 'target': '5.1_天气', 'type': '约束'},
        {'id': 'C00484', 'source': '5.1_天气', 'target': '5.2_路况', 'type': '触发'},
        {'id': 'C00494', 'source': '5.1_天气', 'target': '5.3_缺失项', 'type': '触发'},
    ]
    network = {'connections': [{**edge, 'condition': '降雨时核对通行情况', 'effect': '记录受影响的路线'}
                               for edge in edges]}
    manifest = _manifest(root, tmp_path, [('library.txt', 'library', library.encode('utf-8')),
                                         ('dynamic.json', 'dynamic', json.dumps(network, ensure_ascii=False).encode('utf-8'))])
    build_catalog(workspace, root, manifest)
    aliases = tmp_path / 'aliases.json'
    aliases.write_text('{}', encoding='utf-8')
    mapping = tmp_path / 'migration.json'
    mapping.write_text(json.dumps({'migrations': [{'old_id': 'C00214', 'new_id': 'C00484',
                                                   'source': '5.1_天气', 'target': '5.2_路况', 'type': '触发'}]},
                                  ensure_ascii=False), encoding='utf-8')
    audit = audit_identities(workspace, aliases, mapping)
    (workspace / 'materials/F2_网络身份对账.json').write_text(json.dumps(audit), encoding='utf-8')
    index_units(workspace, None)
    build_adjudications(workspace)
    return workspace, mapping


def _decisions(report: dict) -> dict:
    return {row['rule_id']: row['status'] for row in report['checks']}


def test_collision_requires_current_source_and_exact_relationship(dynamic_catalog: tuple[Path, Path]) -> None:
    workspace, mapping = dynamic_catalog
    current = dynamic_reference(workspace, 'C00484')
    assert current['source_qualification'] == 'design_ready'
    old = dynamic_reference(workspace, 'C00214', mapping)
    assert old['rule_id'] == 'C00484' and old['legacy_mapping']['old_id_reused']
    assert old['source_ref'] == current['source_ref']
    assert dynamic_reference(workspace, 'C00214')['source'] != old['source']
    with pytest.raises(ValueError, match='legacy ID has no unique verified target'):
        dynamic_reference(workspace, 'C00484', mapping)
    altered = mapping.with_name('altered-migration.json')
    altered.write_text(mapping.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='differs from the recorded migration source'):
        dynamic_reference(workspace, 'C00214', altered)

    data = inputs()
    data['subjects']['dynamic_patterns'][0]['dynamic_rule_ids'] = ['C00484']
    data['subjects']['static_patterns'][0]['source_rule_ids'] = ['C00484']
    data['subjects']['combinations'][0]['dynamic_rule_ids'] = ['C00484']
    rule_ids = ('DP-09', 'SP-10', 'COM-07', 'COM-10')
    contract = compile_docs()
    assert all(_decisions(evaluate_governance(contract, data))[rule] == 'failed' for rule in rule_ids)

    registry = data['registries']['dynamic_rules']
    registry['C00484'] = {**current, 'status': 'approved',
                         'subject_sha256s': [fingerprint(data['subjects'][kind][0])
                                             for kind in ('dynamic_patterns', 'static_patterns', 'combinations')]}
    proof = current_rule_proofs(workspace, data)
    assert proof == {'C00484': current}
    result = evaluate_governance(contract, data, current_rules=proof)
    assert all(_decisions(result)[rule] == 'pass' for rule in rule_ids)
    assert _decisions(result)['DP-10'] == 'waiting'
    assert result['dynamic_rule_evidence'] == proof
    changed_subject = deepcopy(data)
    changed_subject['subjects']['dynamic_patterns'][0]['dynamic_pattern_id'] = 'unapproved'
    assert _decisions(evaluate_governance(contract, changed_subject, current_rules=proof))['DP-09'] == 'failed'
    for field, invalid_value in (
            ('source_refs', [{'id': 'C00484', 'source_type': 'pending_restore'}]),
            ('dynamic_rule_ids', ['C00484', {'id': 'C00494', 'source_type': 'pending_restore'}])):
        conflicting = deepcopy(data)
        subject = conflicting['subjects']['dynamic_patterns'][0]
        subject[field] = invalid_value
        conflicting['registries']['dynamic_rules']['C00484']['subject_sha256s'] = [fingerprint(subject)]
        assert _decisions(evaluate_governance(contract, conflicting, current_rules=proof))['DP-09'] == 'failed'

    for field in ('source', 'target', 'type', 'source_type'):
        invalid = deepcopy(data)
        invalid['registries']['dynamic_rules']['C00484'][field] = '不匹配'
        assert not current_rule_proofs(workspace, invalid)
        assert _decisions(evaluate_governance(contract, invalid, current_rules=proof))['DP-09'] == 'failed'
    for field in ('file_sha256', 'sha256', 'locator'):
        invalid = deepcopy(data)
        invalid['registries']['dynamic_rules']['C00484']['source_ref'][field] = '不匹配'
        assert not current_rule_proofs(workspace, invalid)
    blocked = dynamic_reference(workspace, 'C00494')
    assert blocked['source_qualification'] == 'blocked'
    registry['C00494'] = {**blocked, 'status': 'approved'}
    assert current_rule_proofs(workspace, data) == proof


def test_planning_governance_rechecks_the_frozen_dynamic_pin(dynamic_catalog: tuple[Path, Path],
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    from nw.call_budget import create_budget
    from nw.materials import governance_runtime as governance
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from nw.tasks import read_input_manifest
    from story_fixture import baseline
    from test_material_governance_runtime import runtime
    from test_novel_flow import Model, config

    workspace, _ = dynamic_catalog
    current = dynamic_reference(workspace, 'C00484')
    stage = 'type_adaptation'
    combination = {'combination_id': 'combo', 'combination_kind': '动态', 'dynamic_rule_ids': ['C00484'],
                   'status': 'active', 'schema_version': 'H0D-1.0.0', 'evidence_type': 'normalized'}
    approved = {**current, 'status': 'approved', 'subject_sha256s': [fingerprint(combination)]}
    settings = {stage: {'registries': {'dynamic_rules': {'C00484': approved}}}}
    with Store(workspace / 'story', create=True, test_mode=True) as store:
        store.init_project('天气与路况')
        store.add_brief('雨天调查')
        adopt_story(store, baseline(), {})
        budget = create_budget(store, 'governance', Budget(12, 45000, 3000))
        request, package = prepare_plan_task(store, 1, 'book', Model(), config(store), budget, 'governance-test',
                                             governance_inputs=settings)
        assert read_input_manifest(store, request.manifest_id)[1]['governance_inputs'] == settings
        assert 'governance_inputs' not in json.loads(request.payload['messages'][-1]['content'])

    context = {'governance_inputs': package['governance_inputs'],
               'verified_dynamic_rules': governance.verify_dynamic_registries(workspace, settings)}
    source = {'source': {'id': 'combo'}, 'original_text': json.dumps(combination)}
    products = {'_uses': [{'source_id': 'combo'}]}
    checked = runtime()
    monkeypatch.setattr(governance, 'load_governance', lambda _: checked)
    report = governance.check_stage_governance(checked, stage, products, {}, [source], context)
    assert _decisions(report)['COM-07'] == 'pass'
    assert report['status'] == 'waiting'
    session = {'sources': [source], 'context': context, 'governance': checked,
               'stages': [{'stage': stage, 'source_ids': ['combo'], 'products': products,
                           'governance': governance.freeze_report(report)}]}
    governance.verify_session_governance(session, workspace)
    entry = context['governance_inputs'][stage]['registries']['dynamic_rules']['C00484']
    parameters = {'dynamic_rule_ids': ['C00484']}
    entry['subject_sha256s'].append(fingerprint(parameters))
    context['dynamic_reference_checks'] = True
    actual = {'_uses': [], 'adaptations': [{'id': 'book-rules', 'parameters': {'rules': parameters}}]}
    actual_report = governance.check_stage_governance(checked, stage, actual, {}, [], context)
    assert _decisions(actual_report)['TDV_020'] == 'pass'
    report_subject = next(r for r in actual_report['checks'] if r['rule_id']=='TDV_020')['checked_input']['subject']
    assert report_subject['path'] == '/adaptations/0/parameters/rules'
    assert report_subject['sha256'] == fingerprint(parameters)
    entry['source_ref'] = {**entry['source_ref'], 'locator': 'line:99999'}
    assert entry['source_ref'] != current['source_ref']
    with pytest.raises(ValueError, match='pinned dynamic rule evidence changed'):
        governance.verify_session_governance(session, workspace)
