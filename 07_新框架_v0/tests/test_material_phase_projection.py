from copy import deepcopy
import pytest

from nw.materials.phase_projection import compile_candidates,expand_output,verify_chain
from nw.task_models import content_sha256
from test_material_phase_contract import record
from test_planning import Planner
from fake_phase_work import TEST_STAGES,project_products


def chain() -> dict:
    candidates=Planner('chapter').output['candidate_cards']
    from nw.materials.phase_routes import REQUIRES
    records=[];products={}
    for stage in TEST_STAGES:
        value=project_products(stage,candidates,products,[],'chapter',native=True)
        if stage=='anchor_design':
            value['beats'][0]['observable']='看到封条裂口后收手'
            value['selected_propagations']=[{'scene':'scene','propagation':'trace_1'}]
        elif stage=='expression_design':value['guidance'][0]['observable']='先借灯看清封条再接触'
        value['_uses']=[];item=record(stage,value)
        required=list(products) if stage=='bind_scope' else REQUIRES[stage]
        item['inputs']=[{'stage':name,'task_id':products[name]['task_id'],'sha256':products[name]['sha256']} for name in required]
        item['source_ids']=[];records.append(item);products[stage]=item
    return {'policy':'artifact-stage-binding-v3','id':'session','scope':'chapter','stages':records,'sources':[],
            'context':{'scope':'chapter','approved_cards':[]}}


def test_compiler_uses_actual_upstream_cards_and_dynamic_patch_without_designing_new_content() -> None:
    session=chain();verify_chain(session)
    candidates=compile_candidates(session)
    scene=next(row for row in candidates[0]['members'] if row['kind']=='scene')
    records={row['stage']:row['products'] for row in session['stages']}
    action=records['action_design']['candidates'][0]['action']
    patch=records['state_transition']['patches'][0]['choice']
    assert action in scene['body']['choice'] and patch in scene['body']['choice']
    session['candidates']=candidates
    ref=content_sha256(candidates[0])
    raw={'scope':'chapter','candidate_cards':[{'kind':'plot','body':{'assembly_ref':ref}}]}
    assert expand_output(raw,{'material_work':session})['candidate_cards']==candidates
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):
        expand_output({'scope':'chapter','candidate_cards':[{'kind':'plot','body':{'assembly_ref':'invented'}}]}, {'material_work':session})


def test_replacing_or_removing_an_upstream_product_invalidates_the_stage_chain() -> None:
    session=chain()
    next(row for row in session['stages'] if row['stage']=='character_design')['products']['members'][0]['body']['want']='改为离开'
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):verify_chain(session)


def test_historical_v3_direct_dependencies_remain_readable_without_v4_semantic_promotion():
    session=chain();records={r['stage']:r for r in session['stages']}
    previous={'state_transition':('character_design','static_relations','scene_design'),
        'state_propagation':('world_design','character_design','static_relations','scene_design','state_transition')}
    for stage,names in previous.items():
        records[stage]['inputs']=[{'stage':name,'task_id':records[name]['task_id'],
                                  'sha256':records[name]['sha256']} for name in names]
    verify_chain(session)
    session['policy']='artifact-stage-binding-v4'
    with pytest.raises(ValueError,match='MATERIAL_STAGE:'):verify_chain(session)


def test_actual_anchor_and_expression_products_reach_writer_and_review_checks() -> None:
    from nw.materials.phase_projection import method_checks
    session=chain()
    checks=method_checks(session,'scene')
    assert any(c['binding']['observable']=='看到封条裂口后收手' for c in checks)
    assert any(c['binding']['observable']=='先借灯看清封条再接触' for c in checks)


def state_chain() -> dict:
    from nw.materials.phase_routes import REQUIRES
    session=chain();records={r['stage']:r for r in session['stages']}
    records['scene_design']['products']['events']=[{'id':'e','scene':'scene','entity':'yan',
        'trigger':'触碰铜丝受伤','before_state':{'hand':'完好'}}]
    records['state_transition']['products']['transitions']=[{'scene':'scene','entity':'yan','event':'e',
        'before_state':{'hand':'完好'},'action':'伸手试探后收手，改用木片','after_state':{'hand':'划伤'},
        'cost':'手背流血','failure':'无法抬起时停止','continuity':'后续保留手伤'}]
    records['state_propagation']['products']['candidates'][0]['root_id']='e'
    products={}
    for record in session['stages']:
        record['sha256']=content_sha256(record['products'])
        deps=list(products) if record['stage']=='bind_scope' else REQUIRES[record['stage']]
        record['inputs']=[{'stage':name,'task_id':products[name]['task_id'],'sha256':products[name]['sha256']} for name in deps]
        products[record['stage']]=record
    return session


def test_dynamic_products_reach_writer_and_evidence_hypotheses_with_actual_entity_ids() -> None:
    from nw.materials.evidence import scene_checks,writer_checks,state_hypotheses
    design={'materials':[],'bindings':{},'process_bindings':{},'material_key':'scene','work_session':state_chain(),
            'work_application':{},'process_ids':{'yan':'actual-character'}}
    checks=scene_checks(design)
    assert any('划伤' in c['observable'] and '木片' in c['observable'] for c in writer_checks(design))
    review=[{'id':c['id'],'evidence':[{'id':'draft','start':0,'end':30}]} for c in checks]
    hypotheses=state_hypotheses(design,review,'draft')
    assert any(t['entity_id']=='actual-character' and t['predicate']=='hand' and t.get('expected_old') is None
               and t['new_value']=='划伤' for h in hypotheses for t in h['transitions'])
    assert all(t['predicate']!='trace' for h in hypotheses for t in h['transitions'])


def test_writer_receives_actual_after_state_even_when_patch_does_not_repeat_it() -> None:
    from nw.materials.evidence import writer_checks
    session=state_chain()
    transition=next(r for r in session['stages'] if r['stage']=='state_transition')['products']['transitions'][0]
    transition['after_state']={'vision':'永久失明'}
    design={'materials':[],'bindings':{},'process_bindings':{},'material_key':'scene',
            'work_session':session,'work_application':{},'process_ids':{'yan':'actual'}}
    assert any('永久失明' in row['observable'] for row in writer_checks(design))


def test_native_hypothesis_does_not_use_latest_planning_fact_as_story_time_old_value() -> None:
    from nw.materials.phase_projection import method_checks
    session=state_chain();session['context']['accepted_state']=[{'entity_id':'actual','predicate':'hand',
        'holder':'WORLD','claim':'fact','value':'后来已愈合','story_order':99}]
    changes=[t for c in method_checks(session,'scene',{'yan':'actual'}) for t in c['binding'].get('state',[])]
    assert changes and all('expected_old' not in t for t in changes)


def test_current_before_state_is_checked_without_promoting_an_unknown_candidate_to_fact() -> None:
    from types import SimpleNamespace
    import nw.materials.phase_projection as projection
    check=getattr(projection,'verify_current_state',None)
    assert check is not None
    session=state_chain()
    check(session,'scene',{'yan':'actual'},[])
    fact=SimpleNamespace(entity_id='actual',predicate='hand',holder='WORLD',claim='fact',value='已经受伤')
    with pytest.raises(ValueError,match='MATERIAL_PRECONDITION'):
        check(session,'scene',{'yan':'actual'},[fact])
    session=chain();session['stages']=[r for r in session['stages'] if r['stage']!='scene_design']
    with pytest.raises(ValueError,match='MATERIAL_STAGE'):verify_chain(session)



def test_writer_leaves_private_identity_status_in_the_independent_review_contract() -> None:
    from nw.materials.evidence import scene_checks, state_hypotheses, writer_checks

    session = state_chain()
    transition = next(row for row in session['stages'] if row['stage'] == 'state_transition')['products']['transitions'][0]
    key = 'identity_status:暗查职务'
    private_status = {
        'identity': '未对外公开的暗查掌印',
        'permissions': ['可核未公开的卷宗'],
        'social_expectations': ['单独向案牍长回报'],
    }
    transition['after_state'][key] = private_status
    design = {'materials': [], 'bindings': {}, 'process_bindings': {}, 'material_key': 'scene',
              'work_session': session, 'work_application': {}, 'process_ids': {'yan': 'actual'}}
    visible = writer_checks(design)
    assert any('划伤' in check['observable'] for check in visible)
    assert all(private_status['identity'] not in check['observable'] and key not in check['observable'] for check in visible)
    evidence = [{'id': check['id'], 'evidence': [{'id': 'draft', 'start': 0, 'end': 20}]}
                for check in scene_checks(design)]
    hypotheses = state_hypotheses(design, evidence, 'draft')
    assert any(op['predicate'] == key and op['holder'] == 'WORLD' and op['entity_id'] == 'actual'
               and op['new_value'] == private_status for proof in hypotheses for op in proof['transitions'])
