"""Require exact project references for adopted network runtime guidance."""
from copy import deepcopy
from hashlib import sha256

import pytest

from nw.materials.network_layers import POLICY
from nw.materials.phase_schema import schema
from nw.materials.semantic_application import validate_semantic_applications
from nw.materials.semantic_handoff import handoffs_for, validate_handoffs
from nw.materials.source_semantics import compile_semantics
from test_material_semantic_clauses import criterion, fixture, layer_application, record, validate


REJECTED = '触发身体信号作为所有叙事法的表现'


def network_case(filename: str = '动态网络.txt') -> list:
    source, _, upstream, value, context = fixture()
    source['source']['path'] = '原始资料/' + filename
    text = '{"unsafe":"' + REJECTED + '"}'
    source['application_layers'] = [{'source_ref': {'id': 'runtime', 'sha256': sha256(text.encode()).hexdigest()},
        'text': text, 'aligned_fields': [], 'rejected_fields': [{'field': 'unsafe', 'reason': '改变原义'}]}]
    contract = compile_semantics(source)
    context.update(semantic_contracts=[contract], network_layer_policy=POLICY)
    applied = criterion(contract)
    applied['layer_application'] = {'bindings': [
        {'clause_id': clause['id'], 'trigger_ref': clause['input_refs'][1], 'result_ref': clause['output_refs'][0]}
        for clause in applied['clauses']]}
    value['_criteria'] = [applied]
    return [source, contract, upstream, value, context]


@pytest.mark.parametrize('name', ['动态网络.txt', '静态网络.txt', '锚点网络.txt'])
def test_network_project_use_with_only_rejected_legacy_fields(name: str) -> None:
    data = network_case(name)
    assert not data[1]['application_guidance'][0]['aligned_fields']
    validate(data)


@pytest.mark.parametrize(('defect', 'message'), [
    ('legacy_summary', 'exact project field bindings'),
    ('omitted', 'every applied clause output'),
    ('duplicate', 'cover one applied clause output once'),
    ('other_trigger', 'frozen input of the same clause'),
    ('empty_trigger', 'substantive frozen value'),
    ('uncited_output', 'cover one applied clause output once'),
    ('wrong_candidate', 'different product than its recorded use'),
    ('unscoped_collection', 'identify a concrete product'),
    ('copied_operation', 'rejected runtime field'),
    ('copied_result', 'rejected runtime field'),
])
def test_network_layer_binding_rejects_wrong_or_unproven_references(defect: str, message: str) -> None:
    data = network_case()
    current = data[3]['_criteria'][0]
    clause, binding = current['clauses'][0], current['layer_application']['bindings'][0]
    if defect == 'legacy_summary':
        current['layer_application'] = layer_application()
    elif defect == 'omitted':
        current['layer_application']['bindings'].pop()
    elif defect == 'duplicate':
        current['layer_application']['bindings'].append(binding.copy())
    elif defect == 'other_trigger':
        binding['trigger_ref'] = 'brief:/constraints'
        data[4]['brief']['constraints'] = '[FAKE] 这一条件存在但该条款没有引用它'
    elif defect == 'empty_trigger':
        data[4]['brief']['text'] = ''
        binding['trigger_ref'] = 'brief:/text'
    elif defect == 'uncited_output':
        binding['result_ref'] = '/candidates/0/action'
    elif defect == 'wrong_candidate':
        data[3]['candidates'].append({**data[3]['candidates'][0], 'id': 'other-action'})
        binding['result_ref'] = '/candidates/1/action'
        clause['output_refs'] = [binding['result_ref']]
    elif defect == 'unscoped_collection':
        binding['result_ref'] = '/candidates'
        clause['output_refs'] = ['/candidates']
    elif defect == 'copied_operation':
        clause['operation'] = REJECTED
    else:
        data[3]['candidates'][0]['steps'][0]['action'] = REJECTED
    with pytest.raises(ValueError, match=message):
        validate(data)


@pytest.mark.parametrize('legacy', [True, False])
def test_existing_summary_remains_valid_for_older_runs_and_other_sources(legacy: bool) -> None:
    data = network_case('动态网络.txt' if legacy else '资料库.txt')
    if legacy:
        data[4].pop('network_layer_policy')
    data[3]['_criteria'][0]['layer_application'] = layer_application()
    validate(data)


@pytest.mark.parametrize(('other', 'message'), [
    ('/candidates/1/steps/0/action', 'its own action'),
    ('/candidates/0/steps/1/action', 'its own action step'),
])
def test_network_anchor_trigger_must_belong_to_its_own_beat(other: str, message: str) -> None:
    source, _, upstream, value, context = network_case('锚点网络.txt')
    anchor = {'scene': 'scene-a', 'action_ref': 'action-a', 'step_index': 0,
              'observable': '[FAKE] 纸角扬起露出压在下方的铜丝'}
    action = value['candidates'][0]
    action['steps'].append({'action': '[FAKE] 沿被照亮的字纹记下印记形状'})
    value['candidates'].append({**action, 'id': 'action-b'})
    upstream['action_design'] = record('action_design', {'candidates': deepcopy(value['candidates'])})
    context['allowed_input_stages'].append('action_design')
    applied = value['_criteria'][0]
    trigger = 'input:action_design:/candidates/0/steps/0/action'
    for clause, binding in zip(applied['clauses'], applied['layer_application']['bindings'], strict=True):
        clause.update(input_refs=[trigger, 'input:action_design:' + other],
                      output_refs=['/beats/0/observable'], consumer='writer')
        binding.update(trigger_ref=trigger, result_ref='/beats/0/observable')
    result = {'beats': [anchor], '_uses': [{**value['_uses'][0], 'output_refs': ['scene:scene-a']}],
              '_criteria': [applied]}
    validate_semantic_applications('anchor_design', result, upstream, [source], context)
    applied['layer_application']['bindings'][0]['trigger_ref'] = 'input:action_design:' + other
    with pytest.raises(ValueError, match=message):
        validate_semantic_applications('anchor_design', result, upstream, [source], context)


def test_network_field_shape_and_handoff_follow_the_specific_source() -> None:
    source, contract, upstream, value, _ = network_case()
    model_contract = {**contract, 'application_required': True, 'network_layer_fields': True}
    shape = schema('action_design', [source], allow_requests=False, contracts=[model_contract])
    layer = shape['properties']['products']['properties']['_criteria']['items']['anyOf'][0][
        'properties']['layer_application']
    assert layer['required'] == ['bindings']
    item = layer['properties']['bindings']['items']
    assert set(item['required']) == {'clause_id', 'result_ref', 'trigger_ref'}
    assert item['properties']['clause_id']['enum'] == [o['id'] for o in contract['obligations']]

    upstream['action_design'] = record('action_design', value)
    handoffs = handoffs_for('scene_design', upstream)
    bindings = value['_criteria'][0]['layer_application']['bindings']
    assert [row['network_layer_bindings'] for row in handoffs] == [[binding] for binding in bindings]
    for handoff, binding in zip(handoffs, bindings, strict=True):
        assert handoff['actual_inputs'] == [{'path': binding['result_ref'],
                                             'value': value['candidates'][0]['steps'][0]['action']}]
    with pytest.raises(ValueError, match='disappeared'):
        validate_handoffs('scene_design', {'_receipts': []}, upstream)
