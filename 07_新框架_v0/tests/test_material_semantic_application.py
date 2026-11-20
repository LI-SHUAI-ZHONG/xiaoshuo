from copy import deepcopy
from pathlib import Path
import json

import pytest

from nw.materials.phase_contract import validate_phase
from nw.task_models import content_sha256
from test_material_phase_projection import chain


def source(key):
    data=json.loads((Path(__file__).parents[1]/'fixtures/material_semantics/source_samples.json').read_text(encoding='utf-8'))
    return deepcopy(next(row for row in data['samples'] if row['source']['key']==key))


def at(stage):
    records=chain()['stages'];index=next(i for i,r in enumerate(records) if r['stage']==stage)
    return {r['stage']:r for r in records[:index]},deepcopy(records[index]['products'])


def used(value,item,ref):
    value['_uses']=[{'source_id':item['source']['id'],'operation':'[FAKE] 按来源原义安排当前项目实际设计及检验',
                     'output_refs':[ref]}]


@pytest.mark.parametrize(('defect', 'message'), [
    ('excluded', 'candidate source IDs differ'),
    ('missing', 'candidate source IDs differ'),
    ('different_candidate', 'clauses and use record reference different candidates'),
])
def test_action_sources_agree_with_adoption_and_the_applied_clause_outputs(defect: str, message: str) -> None:
    from nw.materials.scene_source_bindings import POLICY
    from nw.materials.source_semantics import compile_semantics
    from test_material_semantic_clauses import criterion, source as action_source

    item = action_source()
    products, value = at('action_design')
    action = value['candidates'][0]
    action['source_ids'] = ['method']
    alternate = deepcopy(action)
    alternate.update(id='alternate', source_ids=[])
    value['candidates'].append(alternate)
    used(value, item, 'action:' + action['id'])
    value['_criteria'] = [criterion(compile_semantics(item))]
    context = {'scope': 'chapter', 'scene_source_binding_policy': POLICY, 'require_semantics': True,
               'brief': {'text': '[FAKE] 调查铜丝下的封条'}}
    raw = {'stage': 'action_design', 'products': value}
    validate_phase(raw, 'action_design', products, [item], context)

    if defect == 'excluded':
        value['_uses'] = value['_criteria'] = []
        value['_excluded'] = [{'source_id': 'method', 'reason': '[FAKE] 本场不采用该动作方法'}]
    elif defect == 'missing':
        action['source_ids'] = []
    else:
        for clause in value['_criteria'][0]['clauses']:
            clause['output_refs'] = ['/candidates/1/steps/0/action']
    with pytest.raises(ValueError, match=message):
        validate_phase(raw, 'action_design', products, [item], context)


def test_reader_wave_cannot_be_an_arbitrary_nonempty_string():
    item=source('板块64 读者情感#读者情绪波形设计')
    products,value=at('plot_design');value['reader_plan']=['全部场景情绪保持同一水平']
    used(value,item,'reader_plan')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[item],{'scope':'chapter'})


def test_real_foreshadow_subitem_cannot_omit_its_promise_plan():
    item=source('板块45 伏笔与反转#伏笔埋设')
    products,value=at('plot_design');value['promise_plan']=[]
    used(value,item,'direction:0')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[item],{'scope':'chapter'})


def test_native_dynamic_edge_cannot_apply_without_its_adopted_static_relation():
    item=source('C00001')
    products,value=at('state_transition');used(value,item,'scene:scene')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'state_transition','products':value},'state_transition',products,[item],{'scope':'chapter'})


def test_anchor_needs_an_actual_selected_action_and_trigger_basis():
    item=source('A1.1')
    products,value=at('anchor_design');value['beats'][0]['action']='全速冲刺'
    for field in ('action_ref','step_index','timing','trigger_basis'):value['beats'][0].pop(field,None)
    used(value,item,'scene:scene')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'anchor_design','products':value},'anchor_design',products,[item],{'scope':'chapter'})
    # Historical v3 output remains inspectable under its own recorded contract.
    validate_phase({'stage':'anchor_design','products':value},'anchor_design',products,[item],
                   {'scope':'chapter','legacy_replay':True})


def _multi_anchor_scene() -> tuple[dict, dict]:
    products, value = at('anchor_design')
    actions = products['action_design']['products']['candidates']
    second = deepcopy(actions[0])
    second.update(id='compare_marks', action='[FAKE] 换照角度比对封条两枚印痕')
    second['steps'].extend([{**second['steps'][0], 'object': '[FAKE] 暗处的第二枚印痕',
                             'action': '[FAKE] 将灯光移向第二枚印痕'}])
    actions.append(second)
    products['scene_design']['products']['selected_actions'].append({'scene': 'scene', 'action': second['id']})
    for stage in ('scene_design', 'action_design'):
        products[stage]['sha256'] = content_sha256(products[stage]['products'])
    value['beats'].append({**value['beats'][0], 'action_ref': second['id'], 'step_index': 1, 'timing': 'during',
                           'observable': '[FAKE] 第二枚印痕浮在灯光斜影下'})
    return products, value


@pytest.mark.parametrize(('defect', 'message'), [
    ('missing', 'each selected action'),
    ('unselected', 'actual selected upstream action'),
    ('step', 'actual action beat'),
    ('order', 'follow the actual action and step order'),
])
def test_multi_action_scene_anchors_cover_each_selected_action_in_order(defect: str, message: str) -> None:
    from nw.materials.scene_actions import MULTI_ACTION_POLICY

    products, value = _multi_anchor_scene()
    raw = {'stage': 'anchor_design', 'products': value}
    context = {'scope': 'chapter', 'multi_action_policy': MULTI_ACTION_POLICY}
    validate_phase(raw, 'anchor_design', products, [], context)
    if defect == 'missing':
        value['beats'].pop()
    elif defect == 'unselected':
        stage = products['action_design']
        candidates = stage['products']['candidates']
        candidates.append({**candidates[0], 'id': 'reserved'})
        stage['sha256'] = content_sha256(stage['products'])
        value['beats'][1]['action_ref'] = 'reserved'
    elif defect == 'step':
        value['beats'][1]['step_index'] = 2
    else:
        value['beats'].reverse()
    with pytest.raises(ValueError, match=message):
        validate_phase(raw, 'anchor_design', products, [], context)


@pytest.mark.parametrize(('defect', 'message'), [
    ('broad', 'needs a concrete beat output'),
    ('wrong_action', 'must cite the action and step'),
    ('wrong_step', 'must cite the action and step'),
    ('wrong_scene', 'outside its scene use'),
])
def test_anchor_source_clause_cites_its_exact_action_in_a_multi_action_scene(defect: str, message: str) -> None:
    from nw.materials.scene_actions import MULTI_ACTION_POLICY
    from nw.materials.source_semantics import compile_semantics
    from test_material_semantic_clauses import criterion, source as draft_source

    products, value = _multi_anchor_scene()
    anchor = draft_source('anchor', original='【指令】从实际查看物证的动作中选择一个能被在场人物看见的具体变化')
    anchor['source'].update(profile='anchor', key='A1.1')
    value['_criteria'] = [criterion(compile_semantics(anchor), '/beats/1/observable')]
    for clause in value['_criteria'][0]['clauses']:
        clause.update(input_refs=['input:action_design:/candidates/1/steps/1/action'], consumer='review')
    used(value, anchor, 'scene:scene')
    context = {'scope': 'chapter', 'multi_action_policy': MULTI_ACTION_POLICY}
    raw = {'stage': 'anchor_design', 'products': value}
    validate_phase(raw, 'anchor_design', products, [anchor], context)
    for clause in value['_criteria'][0]['clauses']:
        if defect == 'broad':
            clause['output_refs'] = ['/beats']
        elif defect == 'wrong_action':
            clause['input_refs'] = ['input:action_design:/candidates/0/steps/0/action']
        elif defect == 'wrong_step':
            clause['input_refs'] = ['input:action_design:/candidates/1/steps/0/action']
    if defect == 'wrong_scene':
        stage = products['scene_design']
        members = stage['products']['members']
        members.append({**members[0], 'key': 'different_scene'})
        stage['products']['selected_actions'].append({'scene': 'different_scene', 'action': 'lift_1'})
        stage['sha256'] = content_sha256(stage['products'])
        value['beats'].append({**value['beats'][0], 'scene': 'different_scene'})
        value['_uses'][0]['output_refs'] = ['scene:different_scene']
    with pytest.raises(ValueError, match=message):
        validate_phase(raw, 'anchor_design', products, [anchor], context)


def test_single_action_anchor_use_keeps_its_scope_in_a_mixed_chapter() -> None:
    from nw.materials.scene_actions import MULTI_ACTION_POLICY
    from nw.materials.source_semantics import compile_semantics
    from test_material_semantic_clauses import criterion, source as draft_source

    products, value = _multi_anchor_scene()
    stage = products['scene_design']
    scene = stage['products']['members'][0]
    stage['products']['members'].append({**scene, 'key': 'single_scene'})
    stage['products']['selected_actions'].append({'scene': 'single_scene', 'action': 'lift_1'})
    stage['sha256'] = content_sha256(stage['products'])
    value['beats'].append({**value['beats'][0], 'scene': 'single_scene'})
    anchor = draft_source('anchor', original='【指令】从实际查看物证的动作中选择一个能被在场人物看见的具体变化')
    anchor['source'].update(profile='anchor', key='A1.1')
    value['_criteria'] = [criterion(compile_semantics(anchor), '/beats')]
    for clause in value['_criteria'][0]['clauses']:
        clause.update(input_refs=['input:action_design:/candidates/0/steps/0/action'], consumer='review')
    used(value, anchor, 'scene:single_scene')

    validate_phase({'stage': 'anchor_design', 'products': value}, 'anchor_design', products, [anchor],
                   {'scope': 'chapter', 'multi_action_policy': MULTI_ACTION_POLICY})


def test_writer_and_reviewer_receive_ordered_actions_and_exact_anchor_steps() -> None:
    from nw.materials.phase_projection import method_checks
    from nw.materials.scene_actions import MULTI_ACTION_POLICY

    products, value = _multi_anchor_scene()
    session = chain()
    session['context']['multi_action_policy'] = MULTI_ACTION_POLICY
    for record in session['stages']:
        stage = record['stage']
        if stage in products:
            record.update(products[stage])
        if stage == 'anchor_design':
            record.update(products=value, sha256=content_sha256(value))

    checks = method_checks(session, 'scene', {'yan': 'real-pov'})
    actions = [check for check in checks if check['id'].startswith('work:selected:action:')]
    assert [(check['id'], check['action_order']) for check in actions] == [
        ('work:selected:action:scene:lift_1', 1), ('work:selected:action:scene:compare_marks', 2)]
    assert [json.loads(check['binding']['observable'])['action_order'] for check in actions] == [1, 2]
    anchors = [json.loads(check['binding']['observable']) for check in checks
               if check['id'].startswith('work:stage:anchor_design:')]
    assert [(entry['action_ref'], entry['action_order'], entry['step_index']) for entry in anchors] == [
        ('lift_1', 1, 0), ('compare_marks', 2, 1)]
    assert anchors[1]['action_step']['object'] == '[FAKE] 暗处的第二枚印痕'
    assert anchors[1]['observer'] == 'real-pov'


def test_real_reader_and_foreshadow_methods_accept_actual_plans_and_keep_unknown_future():
    products,value=at('plot_design')
    for key,ref in (('板块64 读者情感#读者情绪波形设计','reader_plan'),
                    ('板块45 伏笔与反转#伏笔埋设','promise_plan')):
        item=source(key);used(value,item,ref)
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[item],{'scope':'chapter'})
    assert value['promise_plan'][0]['payoff_chapter'] is None


def test_static_relationship_waits_for_real_plot_endpoint_then_dynamic_uses_it():
    from nw.materials.semantic_products import validate_dynamic_dependencies
    from nw.materials.template_candidates import validate_propagations
    static=source('1.1_主角 / 130_核心悬念 / 绑定');dynamic=source('C00001')
    products,value=at('plot_design');used(value,static,'relation:core')
    promise=next(r['key'] for r in value['members'] if r['kind']=='promise')
    value['static_bindings']=[{'id':'core','source_id':static['source']['id'],
        'source':'yan','target':promise,'relation':'绑定','condition':'[FAKE] 人物采用调查旧印的主线悬念'}]
    validate_phase({'stage':'plot_design','products':value},'plot_design',products,[static],{'scope':'chapter'})
    later,propagation=at('state_propagation')
    later['plot_design']['products']=value;later['plot_design']['sha256']=content_sha256(value)
    row=propagation['candidates'][0];row['source_ids']=[dynamic['source']['id']];row['target_entity']=promise
    used(propagation,dynamic,'propagation:'+row['id'])
    context={'scope':'chapter','method_sources':[static,dynamic]}
    validate_dynamic_dependencies('state_propagation',propagation,later,[dynamic],context)
    validate_propagations(propagation,later,[dynamic],context)
    value['static_bindings'][0]['target']='not-created'
    with pytest.raises(ValueError,match='endpoints'):
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[static],context)
