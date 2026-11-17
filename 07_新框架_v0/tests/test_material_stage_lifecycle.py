from copy import deepcopy

import pytest

from nw.materials.phase_routes import REQUIRES,phase_order,route_method


@pytest.mark.parametrize('number,stage',[(1,'state_propagation'),(2,'type_adaptation'),
    (3,'state_transition'),(4,'event_design'),(5,'action_design')])
def test_each_original_template_has_its_own_method_stage(number,stage):
    route=route_method({'source':{'key':f'TDR_TEMPLATE_00{number}','profile':'type_transition'}})
    assert route['stages']==[stage]
    assert route['requires_by_stage'][stage]==list(REQUIRES[stage])


def test_type_adaptation_runs_after_choice_and_before_project_world_design():
    order=phase_order('book')
    assert order==['type_selection','type_adaptation','world_design','character_design',
                   'static_relations','plot_design','bind_scope']
    assert 'type_adaptation' in REQUIRES['world_design']


def test_unselected_design_candidates_are_not_required_current_prose_sources():
    from nw.materials.phase_lifecycle import writing_sources
    products={
        'event_design':{'products':{'_uses':[{'source_id':'e','output_refs':['event_candidate:later']}] }},
        'action_design':{'products':{'_uses':[{'source_id':'a','output_refs':['action:chosen']}] }},
        'state_propagation':{'products':{'_uses':[{'source_id':'p','output_refs':['propagation:later']}] }},
        'character_design':{'products':{'_uses':[{'source_id':'person','output_refs':['member:yan']}] }},
        'scene_design':{'products':{'selected_events':[{'scene':'s','event':'base'}],
                                  'selected_actions':[{'scene':'s','action':'chosen'}],'_uses':[]}},
        'anchor_design':{'products':{'selected_propagations':[],'_uses':[]}},
    }
    assert writing_sources(products,[])=={'a','person'}
    products['anchor_design']['products']['selected_propagations']=[{'scene':'s','propagation':'later'}]
    assert writing_sources(products,[])=={'a','p','person'}


def test_directed_method_requirements_need_actual_downstream_application():
    from nw.materials.phase_lifecycle import validate_requirements
    products={'static_relations':{'products':{'requirements':[{'id':'reader-order',
        'source_id':'method','target_stage':'plot_design','constraint':'先见异常再揭解释','project_refs':['brief']}]}}}
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_requirements('plot_design',{'_requirements':[]},products,{'reader_plan'})
    value={'_requirements':[{'id':'reader-order','operation':'安排先见封条裂口后查验旧印的认知顺序',
                            'output_refs':['reader_plan']}]}
    validate_requirements('plot_design',value,products,{'reader_plan'})
    bad=deepcopy(value);bad['_requirements'][0]['output_refs']=['member:invented']
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_requirements('plot_design',bad,products,{'reader_plan'})


def test_selected_checks_resolve_real_character_and_target_ids():
    from test_material_phase_projection import chain
    from nw.materials.phase_projection import method_checks
    checks=method_checks(chain(),'scene',{'yan':'actual-yan','seal':'actual-seal'})
    selected=[r for r in checks if r['id'].startswith('work:selected:')]
    assert any('actual-yan' in r['binding']['observable'] for r in selected)
    assert any('actual-seal' in r['binding']['observable'] for r in selected)


def test_a_static_fact_cannot_substitute_for_a_confirmed_state_change():
    from test_material_template_contract import design,records,sources
    from nw.materials.template_contract import validate_extra
    values=design();value=values['state_propagation']
    value['candidates'][0].update(root_kind='accepted_fact',root_id='fact:0')
    context={'accepted_state':[{'entity_id':'yan','predicate':'name','value':'沈砚','holder':'WORLD',
        'claim':'fact','story_order':1,'evidence':[{'draft_id':'d','quote':'他名叫沈砚'}]}]}
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_extra('state_propagation',value,records(values),sources(),context)


def test_requirement_cannot_be_satisfied_only_by_an_unselected_action():
    from nw.materials.phase_lifecycle import validate_selected_requirements
    products={'static_relations':{'products':{'requirements':[{'id':'wood','source_id':'s',
        'target_stage':'action_design','constraint':'不能明火，只用木片','project_refs':['brief']}] }},
        'action_design':{'products':{'candidates':[{'id':'wood','actor':'yan'},{'id':'fire','actor':'yan'}],
            '_requirements':[{'id':'wood','operation':'按木片约束设计可执行调查动作','output_refs':['action:wood']}]}}}
    value={'selected_actions':[{'scene':'s','action':'fire'}],'selected_events':[]}
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_selected_requirements('scene_design',value,products)
    value['selected_actions'][0]['action']='wood'
    validate_selected_requirements('scene_design',value,products)


def test_state_template_cannot_claim_another_scene_as_its_real_product():
    from nw.materials.template_contract import validate_template_uses
    value={'transitions':[{'scene':'changed'}],
        '_uses':[{'source_id':'t3','operation':'设计本场铜丝划伤手背的行动与后果',
                  'output_refs':['scene:unrelated']}]}
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_template_uses('state_transition',value,{},[
            {'source':{'id':'t3','key':'TDR_TEMPLATE_003','profile':'type_transition'}}],{})


@pytest.mark.parametrize('condition',[
    '如果根变化未经确认，人物也没有作出任何外部选择，就立即自动传播',
    'When the root is not confirmed and no external action is selected, propagate immediately'])
def test_propagation_cannot_reverse_the_source_activation_gates(condition):
    from test_material_template_contract import design,records,sources
    from nw.materials.template_contract import validate_extra
    values=design();value=values['state_propagation'];value['candidates'][0]['activation_condition']=condition
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_extra('state_propagation',value,records(values),sources(),{})


def test_propagation_preserves_a_correct_waiting_branch():
    from test_material_template_contract import design,records,sources
    from nw.materials.template_contract import validate_extra
    values=design();value=values['state_propagation']
    value['candidates'][0]['activation_condition']='如果根变化未经确认则等待；只有根变化确认且人物选择留下木片后，才考虑传播'
    validate_extra('state_propagation',value,records(values),sources(),{})


def test_person_specific_requirement_stays_scoped_when_reusing_approved_people():
    from nw.materials.phase_lifecycle import validate_selected_requirements
    products={'character_design':{'products':{'members':[]}},
        'static_relations':{'products':{'requirements':[{'id':'wood','source_id':'s',
            'target_stage':'action_design','constraint':'沈砚不能明火，只用木片','project_refs':['member:approved-yan']}]}},
        'action_design':{'products':{'candidates':[{'id':'wood','actor':'approved-yan'},
            {'id':'walk','actor':'approved-keeper'}],
            '_requirements':[{'id':'wood','operation':'按木片约束设计沈砚调查动作','output_refs':['action:wood']}]}}}
    value={'selected_actions':[{'scene':'s','action':'walk'}],'selected_events':[]}
    context={'approved_cards':[{'card_id':'approved-yan','kind':'character'},
                               {'card_id':'approved-keeper','kind':'character'}]}
    validate_selected_requirements('scene_design',value,products,context)


@pytest.mark.parametrize('gate',['require_root_confirmation','require_external_action_selection','require_continuity_validation'])
def test_propagation_cannot_disable_a_mandatory_gate(gate):
    from test_material_template_contract import design,records,sources
    from nw.materials.template_contract import validate_extra
    values=design();value=values['state_propagation'];value['candidates'][0]['gates'][gate]=False
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_extra('state_propagation',value,records(values),sources(),{})


def test_metadata_readout_cannot_stand_in_for_applying_the_state_method():
    from test_material_phase_contract import before,transition
    from nw.materials.phase_contract import validate_phase
    value=transition();value['products']['_uses'][0]['operation']='readout_original_text'
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_phase(value,'state_transition',before(),[
            {'source':{'id':'method','key':'TDR_TEMPLATE_003','profile':'type_transition'}}],{})


def test_repeated_transition_of_the_same_event_is_not_a_second_design_product():
    from test_material_phase_contract import before,transition
    from nw.materials.phase_contract import validate_phase
    value=transition();value['products']['transitions']*=2
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_phase(value,'state_transition',before(),[
            {'source':{'id':'method','key':'TDR_TEMPLATE_003','profile':'type_transition'}}],{})


def test_transport_schema_cannot_invent_a_requirement_when_none_was_assigned():
    from nw.materials.phase_schema import schema
    shape=schema('state_transition',[],inputs={'static_relations':{'products':{'requirements':[]}}},allow_requests=False)
    assert shape['properties']['products']['properties']['_requirements']['maxItems']==0


@pytest.mark.parametrize('reason',['原始状态为template，不能作为已确认组成依据','模板身份尚未获得来源资格'])
def test_template_identity_alone_is_not_a_project_nonapplicability_reason(reason):
    from test_material_phase_projection import chain
    from nw.materials.phase_contract import validate_phase
    rows=chain()['stages'];products={'type_selection':rows[0]}
    value=deepcopy(next(r['products'] for r in rows if r['stage']=='type_adaptation'))
    value.update(_uses=[],_excluded=[{'source_id':'t2','reason':reason}])
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):
        validate_phase({'stage':'type_adaptation','products':value},'type_adaptation',products,[
            {'source':{'id':'t2','key':'TDR_TEMPLATE_002','profile':'type_transition'}}],{})
