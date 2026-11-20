"""A derived static-stage method can consume only the already saved relationship."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from nw.materials.network_followup import BASIS_STAGE, POLICY, basis_inputs, merge_followup, verify_followup
from nw.materials.network_workflow import POLICY as NETWORK_POLICY
from nw.materials.phase_routes import product_ref
from nw.materials.semantic_application import input_value
from nw.task_models import content_sha256
from test_material_semantic_application import at, used
from test_material_semantic_clauses import record, source


def example() -> tuple[dict, dict, list[dict], list[dict], dict, dict]:
    upstream, value = at('static_relations')
    edge = {'source': '1.2_重要配角', 'target': '5.1_亲缘关系', 'type': '嵌套', 'condition': '关系连接'}
    original = source('base-source', json.dumps(edge, ensure_ascii=False))
    original['source'].update(key='1.2_重要配角 / 5.1_亲缘关系 / 嵌套', profile='static_binding')
    derived = source('derived-source', json.dumps({**edge, 'generated_from_static': True,
                                                    'valid_types': ['悬疑'], 'effect': '确认亲缘约束'}, ensure_ascii=False))
    derived['source'].update(key='C00006', profile='dynamic_relation')
    derived['related_sources'] = ['base-source']
    value['relations'] = [{'id': 'kin', 'source': 'yan', 'target': 'partner', 'relation': '嵌套',
                           'condition': '[FAKE] 对方已经出示可查证的家谱和同一旧籍编号'},
                          {'id': 'other', 'source': 'yan', 'target': 'visitor', 'relation': '嵌套',
                           'condition': '[FAKE] 两人合作处理另一本案卷上的封条'}]
    value['requirements'] = [{'id': 'known', 'source_id': 'base-source', 'target_stage': 'plot_design',
                               'constraint': '[FAKE] 在调查目标中保留县档保存的实际线索', 'project_refs': ['member:yan']}]
    used(value, original, 'relation:kin')
    basis = record('static_relations', value)
    basis.update(inputs=[product_ref(row) for row in upstream.values()], source_ids=['base-source'])
    delta = {'requirements': [{'id': 'kin-reaction', 'source_id': 'derived-source', 'target_stage': 'plot_design',
                               'constraint': '[FAKE] 确认亲缘后才改变双方的合作条件',
                               'project_refs': ['member:yan', 'member:partner']}],
             '_uses': [], '_excluded': [], '_criteria': [{'source_id': 'derived-source', 'clauses': [
                 {'applicability': 'applies', 'input_refs': [f'input:{BASIS_STAGE}:/relations/0/condition'],
                  'output_refs': ['/requirements/1/constraint'], 'consumer': 'plot_design'}]}]}
    used(delta, derived, 'requirement:kin-reaction')
    context = {'scope': 'book', 'same_stage_network_policy': POLICY, 'network_prerequisite_policy': NETWORK_POLICY,
               'network_type_scope': {'GENRE_XUANYI': ['悬疑']}, 'method_sources': [original, derived],
               'approved_cards': [{'card_id': key, 'kind': 'character'} for key in ['partner', 'visitor']]}
    return basis, delta, [original], [derived], upstream, context


def test_same_stage_followup_appends_frozen_requirements() -> None:
    basis, delta, _, sources, upstream, context = example()
    saved = deepcopy(basis)
    merged = merge_followup(basis, delta, sources, upstream, context)
    assert merged['relations'] == basis['products']['relations']
    assert merged['requirements'] == basis['products']['requirements'] + delta['requirements']
    assert merged['_uses'] == basis['products']['_uses'] + delta['_uses']
    assert basis == saved
    assert BASIS_STAGE not in upstream


@pytest.mark.parametrize(('defect', 'message'), [
    ('relation_rewrite', 'only append requirements'),
    ('same_marker_removed', 'policy is not active'),
    ('basis_not_adopted', '缺少本项目已落实'),
    ('wrong_genre', '已选类型'),
    ('same_stage_target', 'later stage in scope'),
    ('out_of_scope_target', 'later stage in scope'),
    ('old_row_output', 'own new requirement row'),
    ('wrong_endpoints', 'frozen relation of its requirement endpoints'),
    ('wrong_relation', 'frozen relation of its requirement endpoints'),
    ('other_relation_too', 'frozen relation of its requirement endpoints'),
    ('missing_relation', 'frozen relation of its requirement endpoints'),
    ('unoffered_input', 'only the delivered brief and frozen relation'),
    ('wrong_consumer', 'consumer must match'),
    ('source_not_decided', 'one decision per source'),
    ('requirement_already_present', 'new concrete requirement'),
])
def test_same_stage_followup_refuses_unsupported_execution(defect: str, message: str) -> None:
    basis, delta, _, sources, upstream, context = example()
    requirement = delta['requirements'][0]
    clause = delta['_criteria'][0]['clauses'][0]
    if defect == 'relation_rewrite':
        delta['relations'] = []
    elif defect == 'same_marker_removed':
        context.pop('same_stage_network_policy')
    elif defect == 'basis_not_adopted':
        basis['products']['_uses'] = []
        basis['sha256'] = content_sha256(basis['products'])
    elif defect == 'wrong_genre':
        context['network_type_scope'] = {'other': ['科幻']}
    elif defect == 'same_stage_target':
        requirement['target_stage'] = 'static_relations'
    elif defect == 'out_of_scope_target':
        requirement['target_stage'] = 'action_design'
    elif defect == 'old_row_output':
        clause['output_refs'] = ['/requirements/0/constraint']
    elif defect == 'wrong_endpoints':
        requirement['project_refs'] = ['member:yan', 'member:visitor']
    elif defect == 'wrong_relation':
        clause['input_refs'] = [f'input:{BASIS_STAGE}:/relations/1/condition']
    elif defect == 'other_relation_too':
        clause['input_refs'].append(f'input:{BASIS_STAGE}:/relations/1/condition')
    elif defect == 'missing_relation':
        clause['input_refs'] = ['brief:/text']
    elif defect == 'unoffered_input':
        clause['input_refs'].append('input:world_design:/members/0/body/rule')
    elif defect == 'wrong_consumer':
        clause['consumer'] = 'writer'
    elif defect == 'source_not_decided':
        delta['_uses'] = delta['_criteria'] = []
    else:
        requirement['id'] = 'known'
    with pytest.raises(ValueError, match=message):
        merge_followup(basis, delta, sources, upstream, context)


@pytest.mark.parametrize(('defect', 'message'), [
    ('ordinary_stage', 'only available to its own'),
    ('no_policy', 'only available to its own'),
    ('not_sent', 'input stage was not sent'),
    ('whole_list', 'one exact relation'),
    ('id_only', 'one exact relation'),
    ('own_output', 'input stage is not upstream'),
    ('changed_hash', 'upstream product hash mismatch'),
])
def test_only_same_stage_frozen_relationships_are_readable(defect: str, message: str) -> None:
    basis, _, _, _, upstream, context = example()
    frozen = basis_inputs(upstream, basis)
    actual = f'input:{BASIS_STAGE}:/relations/0/condition'
    context['allowed_input_stages'] = [*upstream, BASIS_STAGE]
    assert input_value(actual, 'static_relations', frozen, context) == basis['products']['relations'][0]['condition']
    stage, identifier = 'static_relations', actual
    if defect == 'ordinary_stage':
        stage = 'plot_design'
    elif defect == 'no_policy':
        context.pop('same_stage_network_policy')
    elif defect == 'not_sent':
        context['allowed_input_stages'].remove(BASIS_STAGE)
    elif defect == 'whole_list':
        identifier = f'input:{BASIS_STAGE}:/relations'
    elif defect == 'id_only':
        identifier = f'input:{BASIS_STAGE}:/relations/0/id'
    elif defect == 'own_output':
        identifier = 'input:static_relations:/relations/0/condition'
        frozen['static_relations'] = basis
        context['allowed_input_stages'].append('static_relations')
    else:
        frozen[BASIS_STAGE]['products']['relations'][0]['condition'] = '[FAKE] 已变更未冻结的成立条件'
    with pytest.raises(ValueError, match=message):
        input_value(identifier, stage, frozen, context)


@pytest.mark.parametrize(('defect', 'message'), [
    ('missing_basis', 'invalid frozen static follow-up record'),
    ('missing_followup', 'invalid frozen static follow-up record'),
    ('missing_both_but_offered', 'requires its frozen static follow-up'),
    ('changed_delta', 'invalid frozen static follow-up record'),
    ('changed_basis', 'upstream product hash mismatch'),
    ('missing_call', 'original call records in order'),
    ('wrong_order', 'original call records in order'),
    ('changed_combined', 'cannot rewrite'),
    ('changed_sources', 'changed its independent inputs'),
])
def test_replay_checks_both_passes_before_accepting_the_combined_stage(defect: str, message: str) -> None:
    basis, delta, original, derived, upstream, context = example()
    merged = merge_followup(basis, delta, derived, upstream, context)
    final = record('static_relations', merged)
    final.update(task_id='follow-up-task', inputs=basis['inputs'], source_ids=['base-source', 'derived-source'],
                 static_relations_basis=basis,
                 static_relations_followup={'products': delta, 'sha256': content_sha256(delta),
                                            'source_ids': ['derived-source'], 'task_id': 'follow-up-task',
                                            'manifest_id': 'second-contract-input'})
    calls = [{'task_id': basis['task_id'], 'manifest_id': 'first-contract-input'},
             {'task_id': 'follow-up-task', 'manifest_id': 'second-contract-input'}]
    sources = {item['source']['id']: item for item in [*original, *derived]}
    assert BASIS_STAGE in verify_followup(final, upstream, sources, context, calls)
    if defect == 'missing_basis':
        final.pop('static_relations_basis')
    elif defect == 'missing_followup':
        final.pop('static_relations_followup')
    elif defect == 'missing_both_but_offered':
        final.pop('static_relations_basis')
        final.pop('static_relations_followup')
        final['products'] = basis['products']
        final['sha256'] = basis['sha256']
    elif defect == 'changed_delta':
        delta['requirements'][0]['constraint'] = '[FAKE] 冒充之前模型产出的关系结果'
    elif defect == 'changed_basis':
        basis['products']['relations'][0]['condition'] = '[FAKE] 改写先验事实以绕过前置核验'
    elif defect == 'missing_call':
        calls.pop()
    elif defect == 'wrong_order':
        calls.reverse()
    elif defect == 'changed_combined':
        final['products']['relations'] = []
        final['sha256'] = content_sha256(final['products'])
    else:
        final['source_ids'] = ['derived-source']
    with pytest.raises(ValueError, match=message):
        verify_followup(final, upstream, sources, context, calls)


def test_old_stage_records_retain_their_original_inputs() -> None:
    basis, _, static, _, upstream, _ = example()
    assert verify_followup(basis, upstream, {'base-source': static[0]}, {}, []) is upstream


def test_current_dynamic_runtime_layer_binds_exact_followup_fields_and_review() -> None:
    from fake_semantic_clauses import criteria_for
    from nw.materials.network_layers import POLICY as LAYER_POLICY
    from nw.materials.semantic_application import validate_semantic_applications
    from nw.materials.semantic_checks import make_semantic_checks
    from nw.materials.source_semantics import compile_semantics

    basis, delta, originals, derived, upstream, context = example()
    [static], [dynamic] = originals, derived
    dynamic['source']['path'] = '原始资料/动态网络.txt'
    rejected = '这里是需要隔离的旧口径统一要求和早期模板'
    text = json.dumps({'unsafe': rejected}, ensure_ascii=False)
    dynamic['application_layers'] = [{'source_ref': {'id': 'old-layer', 'sha256': sha256(text.encode()).hexdigest()},
                                      'text': text, 'aligned_fields': [],
                                      'rejected_fields': [{'field': 'unsafe', 'reason': '旧统一执行语义和原文关系不符'}]}]
    static_contract, dynamic_contract = compile_semantics(static), compile_semantics(dynamic)
    [base] = criteria_for({'source_contracts': [static_contract]}, basis['products'])
    for clause in base['clauses']:
        if clause['applicability'] == 'applies':
            clause['output_refs'] = ['/relations/0/condition']
    basis['products']['_criteria'] = [base]
    basis['sha256'] = content_sha256(basis['products'])
    [followup] = criteria_for({'source_contracts': [dynamic_contract]}, delta)
    followup['layer_application'] = {'bindings': []}
    trigger = f'input:{BASIS_STAGE}:/relations/0/condition'
    result = '/requirements/1/constraint'
    for clause in followup['clauses']:
        if clause['applicability'] == 'applies':
            clause.update(input_refs=[trigger], output_refs=[result], consumer='plot_design')
            followup['layer_application']['bindings'].append({'clause_id': clause['id'], 'trigger_ref': trigger,
                                                               'result_ref': result})
    assert followup['layer_application']['bindings']
    delta['_criteria'] = [followup]
    context.update(network_layer_policy=LAYER_POLICY, require_semantics=True,
                   allowed_input_stages=[*upstream, BASIS_STAGE], semantic_contracts=[static_contract, dynamic_contract],
                   brief={'text': '[FAKE] 家谱线索来源的真实性先由双方确认'})
    merged = merge_followup(basis, delta, derived, upstream, context)
    snapshot = basis_inputs(upstream, basis)
    validate_semantic_applications('static_relations', merged, snapshot, [static, dynamic], context)

    final = record('static_relations', merged)
    final.update(inputs=basis['inputs'], static_relations_basis=basis, source_ids=['base-source', 'derived-source'])
    binder = record('bind_scope', {'method_guidance': [{'scene': 'scene', 'source_ids': ['derived-source']}], '_uses': []})
    session = {'id': 'isolated-same-stage-layer', 'stages': [*upstream.values(), final, binder],
               'sources': [static, dynamic], 'context': context}
    checks = make_semantic_checks(session, 'scene')
    proof = next(check['layer_contract']['layer_application'] for check in checks if check['id'].startswith('work:layer:'))
    assert proof['trigger'] == {'path': trigger, 'value': basis['products']['relations'][0]['condition']}
    assert proof['result'] == {'path': result, 'value': delta['requirements'][0]['constraint']}
    assert all(rejected not in check['binding']['observable'] for check in checks)

    merged['requirements'][1]['constraint'] = rejected
    with pytest.raises(ValueError, match='rejected runtime field'):
        validate_semantic_applications('static_relations', merged, snapshot, [static, dynamic], context)
