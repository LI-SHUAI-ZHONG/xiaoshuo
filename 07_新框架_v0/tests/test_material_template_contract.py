"""Pure project-design contracts preserve the five templates' distinct meanings."""
from copy import deepcopy
from importlib import import_module
from typing import Callable

import pytest


def api(name: str) -> Callable:
    try:
        module = import_module('nw.materials.template_contract')
    except ModuleNotFoundError:
        pytest.fail('template contract validators are not implemented')
    return getattr(module, name)


def sources() -> list[dict]:
    return [{'source': {'id': f't{i}', 'key': f'TDR_TEMPLATE_00{i}',
                        'profile': 'type_transition'}} for i in (1, 2, 3, 4, 5)]


def design() -> dict:
    return {
        'type_selection': {'selection': [{'id': 'mystery', 'label': '制度谜团', 'basis': '项目选择调查方向'}],
            'concepts': [{'id': 'doubt', 'label': '异常印章', 'type_refs': ['mystery'],
                          'activation_basis': '本项目选中调查类型，并以印章不符激活疑问'}], 'boundaries': []},
        'type_adaptation': {'adaptations': [{'id': 'adapt', 'type_refs': ['mystery'],
            'parameters': {'investigation': '封条调查'}, 'limits': ['证据先于推断']}],
            'focuses': [{'id': 'focus', 'concept': 'doubt', 'from_focus': '门禁是否可靠',
                        'to_focus': '谁更换过封条', 'application': '以两代印痕差异引导调查'}], 'boundaries': []},
        'world_design': {'members': [{'key': 'seal', 'kind': 'world', 'body': {'title': '封条'}}]},
        'character_design': {'members': [{'key': 'yan', 'kind': 'character', 'body': {'name': '沈砚'}},
                                         {'key': 'keeper', 'kind': 'character', 'body': {'name': '守门人'}}],
            'capabilities': [{'entity': 'yan', 'can_act': True, 'abilities': ['辨认印痕', '移动木片'],
                              'basis': '当前项目人设能力提案：曾在印坊学徒', 'limits': ['不能徒手拆除封条']},
                             {'entity': 'keeper', 'can_act': False, 'abilities': [],
                              'basis': '当前项目人设提案：仍在昏迷', 'limits': ['醒来前不能行动']}]},
        'static_relations': {'requirements': [{'id': 'rule', 'source_id': 't2', 'target_stage': 'scene_design',
            'constraint': '先呈现印痕差异，再允许推断替换者',
            'project_refs': ['member:seal', 'type:mystery', 'brief']}]},
        'plot_design': {'event_nodes': [{'id': 'inspect', 'actors': ['yan'], 'goal': '查明封条是否被换',
            'setting': '旧库门口', 'obstacle': '铜丝藏在边缘', 'completion_condition': '看清封条边缘旧印',
            'status': 'planned'}]},
        'event_design': {'candidates': [{'id': 'question', 'source_ids': ['t4'], 'predecessor': 'inspect',
            'event': '带着旧印拓片向印坊核查换印日期', 'actors': ['yan'],
            'completion_gate': '看清封条边缘旧印', 'status': 'conditional_candidate'}]},
        'action_design': {'candidates': [{'id': 'lift', 'source_ids': ['t5'], 'event': 'inspect',
            'actor': 'yan', 'action': '用木片托起封条边缘观察旧印',
            'steps': [{'object': '封条边缘', 'action': '以木片抬起纸角', 'obstacle': '边缘铜丝收紧',
                       'response': '压低木片避开铜丝', 'result': '露出旧印的半枚字形'}],
            'requires': ['辨认印痕', '移动木片'], 'cost': '纸角破损会暴露调查痕迹',
            'limits': ['木片折断即停止'], 'status': 'candidate'}], 'waiting': []},
        'scene_design': {'members': [{'key': 'scene', 'kind': 'scene',
            'body': {'pov': 'yan', 'characters': ['yan']}}],
            'selected_events': [{'scene': 'scene', 'event': 'inspect'}],
            'selected_actions': [{'scene': 'scene', 'action': 'lift'}]},
        'state_transition': {'transitions': [{'scene': 'scene', 'entity': 'yan', 'event': 'cut',
            'before_state': {'hand': '完好'}, 'after_state': {'hand': '划伤'},
            'action': '以手试探后改用木片'}]},
        'state_propagation': {'candidates': [{'id': 'notice', 'source_ids': ['t1'],
            'root_kind': 'planned_change', 'root_id': 'cut', 'source_entity': 'yan',
            'target_entity': 'keeper', 'external_action': '沈砚主动把带血木片留在门侧',
            'proposed_effect': {'suspicion': '守门人醒来后可能发现有人接近封条'},
            'continuity': '手伤和带血木片来自同一次试探', 'scene': 'scene',
            'status': 'conditional_candidate',
            'gates':{'require_root_confirmation':True,'require_external_action_selection':True,'require_continuity_validation':True},
            'activation_condition': '仅在根状态划伤被确认，且沈砚选择留下木片后，才考虑守门人是否发现'}], 'waiting': []},
        'anchor_design': {'selected_propagations': [{'scene': 'scene', 'propagation': 'notice'}]},
    }


def records(values: dict) -> dict:
    return {stage: {'products': deepcopy(value)} for stage, value in values.items()}


def check(stage: str, value: dict | None = None, products: dict | None = None,
          context: dict | None = None) -> None:
    api('validate_extra')(stage, deepcopy(design()[stage] if value is None else value),
                          records(design()) if products is None else products, sources(), context or {})


@pytest.mark.parametrize('stage', list(design()))
def test_real_conditional_project_design_is_valid_without_completed_prerequisites(stage: str) -> None:
    check(stage)


@pytest.mark.parametrize('stage,key,defect', [
    ('type_selection', 'selection', {'id': 'mystery', 'label': '制度谜团'}),
    ('type_selection', 'concepts', {'id': 'doubt', 'label': '异常', 'type_refs': ['absent'], 'activation_basis': '项目提案'}),
    ('type_adaptation', 'adaptations', {'id': 'adapt', 'type_refs': ['absent'], 'parameters': {'x': 1}, 'limits': []}),
    ('type_adaptation', 'adaptations', {'id': 'adapt', 'type_refs': ['mystery'], 'parameters': {}, 'limits': []}),
    ('type_adaptation', 'focuses', {'id': 'focus', 'concept': 'absent', 'from_focus': '门禁', 'to_focus': '换印', 'application': '排查换印'}),
    ('character_design', 'capabilities', {'entity': 'invented', 'can_act': True, 'abilities': ['行动'], 'basis': '人设提案', 'limits': []}),
    ('static_relations', 'requirements', {'id': 'rule', 'source_id': 't2', 'target_stage': 'type_selection', 'constraint': '证据先于推断', 'project_refs': ['brief']}),
    ('static_relations', 'requirements', {'id': 'rule', 'source_id': 't2', 'target_stage': 'scene_design', 'constraint': '证据先于推断', 'project_refs': ['member:reader']}),
    ('plot_design', 'event_nodes', {'id': 'inspect', 'actors': ['yan'], 'goal': '调查', 'setting': '旧库', 'obstacle': '封条', 'completion_condition': '看清旧印', 'status': 'completed'}),
    ('event_design', 'candidates', {'id': 'question', 'source_ids': ['t4'], 'predecessor': 'absent', 'event': '向印坊核查日期', 'actors': ['yan'], 'completion_gate': '看清旧印', 'status': 'conditional_candidate'}),
])
def test_invented_refs_missing_content_and_completed_plans_are_rejected(stage: str, key: str, defect: dict) -> None:
    value = deepcopy(design()[stage]); value[key] = [defect]
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check(stage, value)


@pytest.mark.parametrize('stage,key', [
    ('type_selection', 'selection'), ('type_selection', 'concepts'),
    ('type_adaptation', 'adaptations'), ('type_adaptation', 'focuses'),
    ('static_relations', 'requirements'), ('plot_design', 'event_nodes'),
    ('event_design', 'candidates'), ('action_design', 'candidates'), ('state_propagation', 'candidates')])
def test_actual_design_ids_cannot_be_duplicated(stage: str, key: str) -> None:
    value = deepcopy(design()[stage]); value[key].append(deepcopy(value[key][0]))
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check(stage, value)


def test_conditional_successor_gate_must_name_the_real_predecessor_completion() -> None:
    value = deepcopy(design()['event_design']); value['candidates'][0]['completion_gate'] = '前驱已经完成'
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('event_design', value)


@pytest.mark.parametrize('field,bad', [('requires', ['飞行']), ('actor', 'keeper'),
    ('event', 'absent'), ('status', 'completed'), ('source_ids', ['absent']),
    ('steps', [{'object': '对象', 'action': '行动', 'obstacle': '障碍', 'response': '应对', 'result': '结果'}])])
def test_action_candidate_requires_actual_actor_event_capability_and_designed_steps(field: str, bad: object) -> None:
    value = deepcopy(design()['action_design']); value['candidates'][0][field] = bad
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('action_design', value)


def test_waiting_is_honest_but_never_counts_as_actual_template_application() -> None:
    value = {'candidates': [], 'waiting': [{'source_id': 't5', 'missing': ['人物最低能力'],
                                          'reason': '当前人物还没有足以完成行动的能力设计'}],
             '_uses': [{'source_id': 't5', 'operation': '以最低能力设计人物行动', 'output_refs': ['action:lift']}]}
    check('action_design', value)
    assert api('extra_refs')('action_design', value) == set()
    with pytest.raises(ValueError, match='MATERIAL_WAITING_INPUTS:'):
        api('validate_template_uses')('action_design', value, records(design()), sources(), {})


@pytest.mark.parametrize('field,bad', [('root_id', 'absent'), ('source_entity', 'keeper'),
    ('target_entity', 'reader'), ('scene', 'absent'), ('status', 'completed'),
    ('activation_condition', ''), ('proposed_effect', {})])
def test_propagation_needs_a_real_root_entities_scene_and_explicit_conditional_status(field: str, bad: object) -> None:
    value = deepcopy(design()['state_propagation']); value['candidates'][0][field] = bad
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('state_propagation', value)


def test_accepted_fact_root_requires_fact_evidence_and_the_corresponding_entity() -> None:
    value = deepcopy(design()['state_propagation']); value['candidates'][0].update(root_kind='accepted_fact', root_id='fact:0')
    fact={'entity_id':'yan','predicate':'hand','value':'划伤','holder':'WORLD','story_order':1,
          'claim':'fact','evidence':[{'draft_id':'d','quote':'手背渗血'}]}
    context = {'accepted_state':[fact],'accepted_changes':[{**fact,'expected_old':'完好','new_value':'划伤'}]}
    check('state_propagation', value, context=context)
    for defect in ({'claim': 'belief'}, {'evidence': []}, {'entity_id': 'keeper'}):
        bad = deepcopy(context); bad['accepted_state'][0].update(defect)
        with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
            check('state_propagation', value, context=bad)


@pytest.mark.parametrize('condition', ['自动传播并立刻生效', '根状态一出现就传到守门人',
    '选中候选后马上让守门人知道一切', '根状态已确认，无须再作任何外部选择'])
def test_propagation_gate_cannot_skip_confirming_the_root_and_external_choice(condition: str) -> None:
    value = deepcopy(design()['state_propagation']); value['candidates'][0]['activation_condition'] = condition
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('state_propagation', value)


def test_propagation_gate_accepts_an_explicit_english_conditional_plan() -> None:
    value = deepcopy(design()['state_propagation'])
    value['candidates'][0]['activation_condition'] = 'Only after the root change is confirmed and Yan chooses to leave the bloody splinter'
    check('state_propagation', value)


def test_project_owned_candidates_need_no_source_but_cannot_claim_a_template_use() -> None:
    value = deepcopy(design()['action_design']); value['candidates'][0]['source_ids'] = []
    api('validate_extra')('action_design', value, records(design()), [], {})
    value['_uses'] = [{'source_id': 't5', 'operation': '依据人物最低能力设计真实行动候选', 'output_refs': ['action:lift']}]
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        api('validate_template_uses')('action_design', value, records(design()), sources(), {})


def test_approved_characters_and_items_are_valid_without_fabricating_project_members() -> None:
    products = records(design())
    people = products['character_design']['products'].pop('members')
    item = products['world_design']['products'].pop('members')[0]
    context = {'approved_cards': [{'card_id': row['key'], 'kind': row['kind'], 'body': row['body']}
                                   for row in [*people, item]]}
    check('action_design', products=products, context=context)
    check('state_propagation', products=products, context=context)


def test_candidate_event_ids_cannot_shadow_a_planned_node() -> None:
    value = deepcopy(design()['event_design']); value['candidates'][0]['id'] = 'inspect'
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('event_design', value)


def test_propagation_can_target_an_item_but_only_a_person_can_initiate_it() -> None:
    value = deepcopy(design()['state_propagation']); value['candidates'][0]['target_entity'] = 'seal'
    check('state_propagation', value)
    products = records(design())
    products['character_design']['products']['capabilities'].append({'entity': 'seal', 'can_act': True, 'abilities': ['移动']})
    products['state_transition']['products']['transitions'][0]['entity'] = 'seal'
    value['candidates'][0]['source_entity'] = 'seal'
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('state_propagation', value, products=products)


def test_scene_selects_one_existing_event_and_action_with_its_actual_actor() -> None:
    for key, field, bad in [('selected_events', 'event', 'absent'), ('selected_actions', 'action', 'absent'),
                            ('selected_actions', 'scene', 'absent')]:
        value = deepcopy(design()['scene_design']); value[key][0][field] = bad
        with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
            check('scene_design', value)
    value = deepcopy(design()['scene_design']); value['members'][0]['body'].update(pov='keeper', characters=['keeper'])
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('scene_design', value)
    value = deepcopy(design()['scene_design']); value['selected_actions'] = []
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('scene_design', value)


def test_multi_action_scene_accepts_two_present_event_actors_and_rejects_invalid_rows() -> None:
    from nw.materials.scene_actions import MULTI_ACTION_POLICY

    data = design()
    scene = data['scene_design']
    scene['members'][0]['body']['characters'].append('keeper')
    data['plot_design']['event_nodes'][0]['actors'].append('keeper')
    data['character_design']['capabilities'][1].update(can_act=True, abilities=['辨认印痕'])
    action = deepcopy(data['action_design']['candidates'][0])
    action.update(id='read', actor='keeper', action='判读拓片的印痕', requires=['辨认印痕'])
    data['action_design']['candidates'].append(action)
    scene['selected_actions'].append({'scene': 'scene', 'action': 'read'})
    context = {'multi_action_policy': MULTI_ACTION_POLICY}
    check('action_design', data['action_design'], records(data))
    check('scene_design', scene, records(data), context)
    with pytest.raises(ValueError, match='one action per scene'):
        check('scene_design', scene, records(data))

    repeated = deepcopy(scene)
    repeated['selected_actions'].append({'scene': 'scene', 'action': 'lift'})
    with pytest.raises(ValueError, match='repeats the same action'):
        check('scene_design', repeated, records(data), context)

    absent_actor = deepcopy(scene)
    absent_actor['members'][0]['body']['characters'].remove('keeper')
    with pytest.raises(ValueError, match='actor or event'):
        check('scene_design', absent_actor, records(data), context)

    action['event'] = 'question'
    with pytest.raises(ValueError, match='actor or event'):
        check('scene_design', scene, records(data), context)


def test_scene_phase_choice_preserves_all_selected_actions_in_order() -> None:
    from nw.materials.phase_contract import validate_phase
    from nw.materials.scene_actions import MULTI_ACTION_POLICY
    from nw.task_models import content_sha256
    from test_material_phase_projection import chain

    entries = chain()['stages']
    scene_index = next(index for index, row in enumerate(entries) if row['stage'] == 'scene_design')
    before = {row['stage']: row for row in entries[:scene_index]}
    scene = entries[scene_index]['products']
    actions = before['action_design']['products']['candidates']
    first, = actions
    second = dict(deepcopy(first), id='record-mark', action='把印痕的缺口记录到拓片上')
    actions.append(second)
    before['action_design']['sha256'] = content_sha256(before['action_design']['products'])
    output = {'stage': 'scene_design', 'products': scene}
    validate_phase(output, 'scene_design', before, [], {'scope': 'chapter'})

    scene['selected_actions'].append({'scene': scene['selected_actions'][0]['scene'], 'action': second['id']})
    body = scene['members'][0]['body']
    context = {'scope': 'chapter', 'multi_action_policy': MULTI_ACTION_POLICY}
    for choice in (first['action'], f"{second['action']}；{first['action']}"):
        body['choice'] = choice
        with pytest.raises(ValueError, match='selected action text in selection order'):
            validate_phase(output, 'scene_design', before, [], context)

    body['choice'] = f"{first['action']}；{second['action']}"
    validate_phase(output, 'scene_design', before, [], context)


def test_anchor_cannot_select_an_absent_propagation_or_other_scene_candidate() -> None:
    value = {'selected_propagations': [{'scene': 'scene', 'propagation': 'absent'}]}
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('anchor_design', value)
    products = records(design()); products['state_propagation']['products']['candidates'][0]['scene'] = 'other'
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        check('anchor_design', products=products)


@pytest.mark.parametrize('number,stage,prefix,key', [
    (1, 'state_propagation', 'propagation', 'candidates'),
    (2, 'type_adaptation', 'focus', 'focuses'),
    (4, 'event_design', 'event_candidate', 'candidates'),
    (5, 'action_design', 'action', 'candidates')])
def test_each_template_use_must_cite_its_own_kind_of_real_project_product(number: int, stage: str, prefix: str, key: str) -> None:
    value = deepcopy(design()[stage]); ident = value[key][0]['id']
    value['_uses'] = [{'source_id': f't{number}', 'operation': '据原文设计实际且有前置条件的项目候选',
                       'output_refs': [f'{prefix}:{ident}']}]
    api('validate_template_uses')(stage, value, records(design()), sources(), {})
    value['_uses'][0]['output_refs'] = ['scene:scene']
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        api('validate_template_uses')(stage, value, records(design()), sources(), {})
    value['_uses'][0]['output_refs'] = [f'{prefix}:{ident}']
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        api('validate_template_uses')('state_transition', value, records(design()), sources(), {})


def test_candidate_cannot_impersonate_another_source_actual_use() -> None:
    value = deepcopy(design()['event_design']); value['candidates'][0]['source_ids'] = ['t1']
    value['_uses'] = [{'source_id': 't4', 'operation': '按前驱完成条件产生实际后继事件候选', 'output_refs': ['event_candidate:question']}]
    with pytest.raises(ValueError, match='MATERIAL_STAGE:'):
        api('validate_template_uses')('event_design', value, records(design()), sources(), {})


def test_type_combination_link_and_expression_need_actual_adaptation_products() -> None:
    for profile in ('type_combination', 'type_link', 'type_expression'):
        method = [{'source': {'id': 'combine', 'key': '类型辅助方法', 'profile': profile}}]
        value = {'_uses': [{'source_id': 'combine', 'operation': '把选中类型适配成封条调查约束', 'output_refs': ['scene:scene']}]}
        api('validate_template_uses')('expression_design', value, records(design()), method, {})
        products = records(design()); products['type_adaptation']['products']['adaptations'] = []
        with pytest.raises(ValueError, match='MATERIAL_WAITING_INPUTS:'):
            api('validate_template_uses')('expression_design', value, products, method, {})


def test_extra_refs_names_actual_products_and_has_no_effect_on_inputs() -> None:
    cases = {'type_selection': {'concept:doubt'}, 'type_adaptation': {'adaptation:adapt', 'focus:focus'},
        'static_relations': {'requirement:rule'}, 'plot_design': {'event_node:inspect'},
        'event_design': {'event_candidate:question'}, 'action_design': {'action:lift'},
        'state_propagation': {'propagation:notice'}, 'character_design': set()}
    for stage, expected in cases.items():
        value = deepcopy(design()[stage]); before = deepcopy(value)
        assert api('extra_refs')(stage, value) == expected
        check(stage, value)
        assert value == before
