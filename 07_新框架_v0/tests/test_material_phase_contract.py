from copy import deepcopy

import pytest

from nw.materials.phase_contract import validate_phase
from nw.task_models import content_sha256


def record(stage,products):
    return {'stage':stage,'task_id':'call-'+stage,'products':products,'sha256':content_sha256(products)}


def prefix(records,stage):
    index=next(i for i,r in enumerate(records) if r['stage']==stage)
    return {r['stage']:r for r in records[:index]}


def before():
    return {'character_design':record('character_design',{'members':[{'key':'yan','kind':'character',
                'body':{'name':'沈砚','role':'主角','want':'调查'}}],'states':[],'_uses':[]}),
            'static_relations':record('static_relations',{'relations':[],'_uses':[]}),
            'plot_design':record('plot_design',{'members':[],'_uses':[]}),
            'action_design':record('action_design',{'candidates':[],'_uses':[]}),
            'scene_design':record('scene_design',{'members':[{'key':'s','kind':'scene','body':{'title':'封条','pov':'yan','goal':'查看'}}],
                'chapters':[],'events':[{'id':'e','scene':'s','entity':'yan','trigger':'封条下露出铜丝',
                                       'before_state':{'hand':'完好'}}],'_uses':[]})}


def transition():
    return {'stage':'state_transition','products':{'patches':[{'scene':'s','choice':'收手改用木片托起封条','planned_result':'手背受伤并看清旧印'}],
        'transitions':[{'scene':'s','entity':'yan','event':'e','before_state':{'hand':'完好'},
                        'action':'先伸手试探，受伤后改用木片','after_state':{'hand':'划伤'},
                        'cost':'手背流血且留下接近封条的痕迹','failure':'若木片折断就停止检查',
                        'continuity':'伤势来自触碰铜丝，后场继续保留手伤'}],
        '_uses':[{'source_id':'method','operation':'依据事件与前状态安排人物选择和受伤后果',
                  'output_refs':['scene:s']}]}}


def test_state_method_consumes_existing_entity_event_and_exact_before_state():
    source={'source':{'id':'method','key':'TDR_TEMPLATE_003','profile':'type_transition'}}
    validate_phase(transition(),'state_transition',before(),[source],{})
    for defect in ('entity','event','before_state'):
        raw=deepcopy(transition());item=raw['products']['transitions'][0]
        item[defect]={'hand':'早已划伤'} if defect=='before_state' else 'invented'
        with pytest.raises(ValueError,match='MATERIAL_STAGE'):
            validate_phase(raw,'state_transition',before(),[source],{})


def test_no_prerequisite_products_means_no_state_method_execution():
    with pytest.raises(ValueError,match='WAITING_INPUTS'):
        validate_phase(transition(),'state_transition',{},[],{})


def test_source_cannot_be_used_at_the_wrong_step_or_claim_an_absent_output():
    source={'source':{'id':'method','key':'10.1_世界规则','profile':'world'}}
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase(transition(),'state_transition',before(),[source],{})
    source['source'].update(key='TDR_TEMPLATE_003',profile='type_transition')
    raw=transition();raw['products']['_uses'][0]['output_refs']=['scene:absent']
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase(raw,'state_transition',before(),[source],{})


def test_used_methods_cannot_disappear_from_the_writable_scene_guidance():
    from test_material_phase_projection import chain
    products={r['stage']:r for r in chain()['stages'][:-1]}
    products['character_design']['products']['_uses']=[{'source_id':'method',
        'operation':'按来源设计人物实际调查目标与行动限制','output_refs':['member:yan']}]
    products['character_design']['sha256']=content_sha256(products['character_design']['products'])
    raw={'stage':'bind_scope','products':{'material_bindings':{},'process_bindings':{},'method_guidance':[],'_uses':[]}}
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase(raw,'bind_scope',products,[],{'scope':'chapter'})


def test_selected_action_source_must_reach_the_same_scene_in_writing_and_review() -> None:
    from nw.materials.evidence import scene_checks, writer_checks
    from nw.materials.phase_routes import POLICY as PHASE_POLICY
    from nw.materials.scene_source_bindings import POLICY
    from nw.materials.source_semantics import compile_semantics
    from test_material_phase_projection import chain
    from test_material_semantic_clauses import criterion, source

    session = chain()
    session['policy'] = PHASE_POLICY
    binding = session['stages'][-1]
    stages = prefix(session['stages'], 'bind_scope')
    action = stages['action_design']['products']
    selected = action['candidates'][0]
    selected['source_ids'] = ['method']
    action['_uses'] = [{'source_id': 'method', 'operation': '[FAKE] 依原义设计调查动作及应对顺序',
                       'output_refs': ['action:' + selected['id']]}]
    item = source()
    contract = compile_semantics(item)
    action['_criteria'] = [criterion(contract)]
    for clause in action['_criteria'][0]['clauses']:
        clause['consumer'] = 'review'
    stages['action_design']['sha256'] = content_sha256(action)
    stages['action_design']['source_ids'] = ['method']
    session['sources'] = [item]
    session['context']['brief'] = {'text': '[FAKE] 调查封条并核对观察与应对顺序'}
    first = stages['scene_design']['products']
    other = deepcopy(first['members'][0])
    other['key'] = 'scene-b'
    first['members'].append(other)
    first['chapters'][0]['scenes'].append({'index': 2, 'card': 'scene-b', 'story_order': 2})
    stages['scene_design']['sha256'] = content_sha256(first)

    value = binding['products']
    raw = {'stage': 'bind_scope', 'products': value}
    strict = {**session['context'], 'scene_source_binding_policy': POLICY}
    guide = {'source_ids': ['method'], 'observable': '[FAKE] 借灯先看清铜丝再伸入木片',
             'check': '[FAKE] 核对两项动作以及纸角破损证据'}
    value['method_guidance'] = [dict(guide, scene='scene-b')]
    validate_phase(raw, 'bind_scope', stages, [], session['context'])
    with pytest.raises(ValueError, match='lost its actual scene placement'):
        validate_phase(raw, 'bind_scope', stages, [], strict)
    value['method_guidance'].append(dict(guide, scene='scene'))
    with pytest.raises(ValueError, match='assigned to the wrong scene'):
        validate_phase(raw, 'bind_scope', stages, [], strict)
    value['method_guidance'].pop(0)
    validate_phase(raw, 'bind_scope', stages, [], strict)
    binding['sha256'] = content_sha256(value)

    design = {'materials': [], 'bindings': {}, 'work_session': session, 'work_application': {},
              'material_key': 'scene', 'process_ids': {'scene': 'actual-a', 'scene-b': 'actual-b'}}
    review = [row for row in scene_checks(design) if row['id'].startswith('work:semantic:')]
    assert {row['method_sources'][0]['original_quotes'][0] for row in review} == {
        row['value'] for row in contract['obligations']}
    assert {row['id'] for row in review} <= {row['id'] for row in writer_checks(design)}
    assert all(row['method_artifact']['current_outputs'][0]['value'] == selected['steps'][0]['action']
               for row in review)
    design['material_key'] = 'scene-b'
    assert not any(row['id'].startswith('work:semantic:') for row in scene_checks(design))
    assert not any(row['id'].startswith('work:semantic:') for row in writer_checks(design))


def test_scene_source_placement_follows_each_selection_and_preserves_unselected_alternatives() -> None:
    from nw.materials.phase_lifecycle import writing_sources
    from nw.materials.scene_source_bindings import scene_source_placements

    values = {
        'event_design': {'_uses': [
            {'source_id': 'shared', 'output_refs': ['event_candidate:adopted']},
            {'source_id': 'spare', 'output_refs': ['event_candidate:unselected']},
        ]},
        'scene_design': {'members': [{'key': 'a'}, {'key': 'b'}],
                         'selected_events': [{'event': 'adopted', 'scene': 'a'}]},
        'state_propagation': {'_uses': [{'source_id': 'shared', 'output_refs': ['propagation:trace']}]},
        'anchor_design': {'selected_propagations': [{'propagation': 'trace', 'scene': 'b'}]},
        'plot_design': {'_uses': [{'source_id': 'global', 'output_refs': ['reader_plan']}]},
    }
    stages = {stage: record(stage, value) for stage, value in values.items()}
    assert scene_source_placements(stages) == ({'shared': {'a', 'b'}}, {'global'})
    assert writing_sources(stages, []) == {'shared', 'global'}


def test_each_scene_needs_actual_anchor_and_expression_products():
    from test_material_phase_projection import chain
    for stage in ('anchor_design','expression_design'):
        records=chain()['stages'];products={r['stage']:r for r in records[:next(i for i,r in enumerate(records) if r['stage']==stage)]}
        scenes=products['scene_design']['products'];other=deepcopy(scenes['members'][0]);other['key']='scene2'
        scenes['members'].append(other);scenes['chapters'][0]['scenes'].append({'index':2,'card':'scene2','story_order':2})
        products['scene_design']['sha256']=content_sha256(scenes)
        raw={'stage':stage,'products':next(r['products'] for r in records if r['stage']==stage)}
        with pytest.raises(ValueError,match='MATERIAL_STAGE'):
            validate_phase(raw,stage,products,[],{'scope':'chapter'})


def test_scene_stage_rejects_bad_chapter_coordinates_before_downstream_methods():
    from test_material_phase_projection import chain
    records=chain()['stages'];products=prefix(records,'scene_design')
    scene=deepcopy(next(r['products'] for r in records if r['stage']=='scene_design'));scene['chapters']=[{'title':'错误结构','index':1,'scenes':[{'index':1,'card':'scene','story_order':1}]}]
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase({'stage':'scene_design','products':scene},'scene_design',products,[],{'scope':'chapter'})


def test_scene_cannot_silently_bind_a_character_hidden_from_its_viewpoint():
    from test_material_phase_projection import chain
    records=chain()['stages'];products=prefix(records,'scene_design')
    products['character_design']['products']['members'][0]['body'].pop('visibility')
    products['character_design']['sha256']=content_sha256(products['character_design']['products'])
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase({'stage':'scene_design','products':next(r['products'] for r in records if r['stage']=='scene_design')},'scene_design',products,[],{'scope':'chapter'})


def test_state_method_cannot_copy_entering_state_or_instruction_labels_as_action_cost():
    for defect in ('static','label'):
        products=before();raw=transition()
        if defect=='static':
            products['scene_design']['products']['members'][0]['body']['entering_state']='站在封条前手背完好'
            raw['products']['transitions'][0]['action']='站在封条前手背完好'
            products['scene_design']['sha256']=content_sha256(products['scene_design']['products'])
        else:raw['products']['transitions'][0]['cost']='必须选择怎样处理手伤，写出实际代价'
        with pytest.raises(ValueError,match='MATERIAL_STAGE'):
            validate_phase(raw,'state_transition',products,[{'source':{'id':'method','key':'TDR_TEMPLATE_003','profile':'type_transition'}}],{})


def test_call_mode_is_not_an_actual_method_operation():
    raw=transition();raw['products']['_uses'][0]['operation']='read_or_execute'
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase(raw,'state_transition',before(),[{'source':{'id':'method','key':'TDR_TEMPLATE_003','profile':'type_transition'}}],{})


def test_empty_output_is_not_actual_source_application():
    products={'type_selection':record('type_selection',{'selection':[],'concepts':[],'boundaries':[],'_uses':[]}),
              'type_adaptation':record('type_adaptation',{'adaptations':[],'focuses':[],'boundaries':[],'_uses':[]})}
    raw={'stage':'world_design','products':{'members':[],'limitations':[],'unknowns':[],
        '_uses':[{'source_id':'world','operation':'依照世界规则设计实际可执行的行动边界','output_refs':['limitations']}]}}
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase(raw,'world_design',products,[{'source':{'id':'world','key':'10.1_世界规则','profile':'world'}}],{})


@pytest.mark.parametrize('key',['64.1_读者情绪','45.1_伏笔'])
def test_reader_and_foreshadow_methods_need_their_actual_design_products(key):
    from test_material_phase_projection import chain
    rows=chain()['stages'];products=prefix(rows,'plot_design')
    raw={'stage':'plot_design','products':deepcopy(next(r['products'] for r in rows if r['stage']=='plot_design'))}
    raw['products']['_uses']=[{'source_id':'method','operation':'依据所读方法把当前故事安排为实际因果链','output_refs':['direction:0']}]
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        validate_phase(raw,'plot_design',products,[{'source':{'id':'method','key':key,'profile':'plot'}}],{})
