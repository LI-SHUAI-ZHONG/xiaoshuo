from copy import deepcopy

import pytest

from nw.materials.governance_contracts import compile_governance
from test_material_governance_execution import DOCUMENTS


def runtime():
    return {'contract':compile_governance(deepcopy(DOCUMENTS)),
            'status':'ready','pins':[],'dependency_checks':[]}


def test_runtime_checks_the_actual_selected_configuration_not_a_default_empty_set():
    from nw.materials.governance_runtime import check_stage_governance
    value={'selection':[{'id':str(i)} for i in range(4)],'_uses':[],
           '_governance':{'project_config':{'genre_ids':[str(i) for i in range(4)],
               'mechanism_ids':[],'structure_ids':[],'style_ids':[],'tone_ids':[]}}}
    result=check_stage_governance(runtime(),'type_selection',value,{},[],{})
    assert result['status']=='failed'
    assert next(c for c in result['checks'] if c['rule_id']=='CONFIG-max_genre_combination')['status']=='failed'


def test_missing_configuration_and_partial_mapping_remain_visible_and_cannot_accept():
    from nw.materials.governance_runtime import check_stage_governance, require_governance_clear
    value={'selection':[{'id':'chosen'}],'_uses':[]}
    result=check_stage_governance(runtime(),'type_selection',value,{},[],{})
    assert result['status']=='waiting'
    with pytest.raises(ValueError,match='GOVERNANCE'):
        require_governance_clear(result)
    value['_governance']={'project_config':{k:[] for k in
        ('genre_ids','mechanism_ids','structure_ids','style_ids','tone_ids')}}
    result=check_stage_governance(runtime(),'type_selection',value,{},[],{})
    assert result['status']=='failed'
    assert 'configuration_binding' in str(result)


def test_only_actual_used_objects_are_subjects_and_their_source_is_preserved():
    from nw.materials.governance_runtime import check_stage_governance
    import json
    source={'source':{'id':'read-rule'},'original_text':json.dumps({'static_pattern_id':'SP',
        'source_work_ids':[],'not_guaranteed':[],'similarity_features':[],
        'originality_risk':'unknown','evidence_type':'fixture','status':'fixture'})}
    value={'_uses':[]}
    report=check_stage_governance(runtime(),'static_relations',value,{},[source],{})
    assert report['status']=='not_applicable'
    value['_uses']=[{'source_id':'read-rule'}]
    report=check_stage_governance(runtime(),'static_relations',value,{},[source],{})
    assert report['status'] in ('failed','waiting')
    assert report['input_snapshot']['source_bindings'][0]['source_id']=='read-rule'
    assert next(c for c in report['checks'] if c['rule_id']=='SP-09')['status']!='pass'


def test_replay_recomputes_rules_instead_of_trusting_saved_pass():
    from nw.materials.governance_runtime import verify_stage_governance
    with pytest.raises(ValueError,match='GOVERNANCE'):
        verify_stage_governance(runtime(),{'status':'pass','input_snapshot':{}},
            'type_selection',{'selection':[],'_uses':[]},{},[],{})


@pytest.mark.parametrize('metadata',[None,[],{'project_config':{'genre_ids':None}}])
def test_malformed_configuration_is_reported_without_a_runtime_crash(metadata):
    from nw.materials.governance_runtime import check_stage_governance
    report=check_stage_governance(runtime(),'type_selection',
        {'selection':[{'id':'chosen'}],'_uses':[],'_governance':metadata},{},[],{})
    assert report['status'] in ('waiting','failed')


def test_changed_governance_source_is_not_silently_treated_as_an_absent_test_catalog(tmp_path):
    from nw.materials.catalog import build_catalog
    from nw.materials.governance_runtime import load_governance
    from test_material_catalog import _manifest
    data='SOURCE: 类型组合约束.json\n=====\n{"schema_version":"UNREVIEWED-9"}'.encode('utf-8')
    manifest=_manifest(tmp_path/'source',tmp_path,[('changed.txt','type_links',data)])
    build_catalog(tmp_path,tmp_path/'source',manifest)
    with pytest.raises(ValueError,match='unreviewed source version'):load_governance(tmp_path)


def test_other_object_schema_cannot_inherit_current_governance_by_shared_field_name():
    import json
    from nw.materials.governance_runtime import check_stage_governance
    source={'source':{'id':'other-schema'},'original_text':json.dumps({
        'static_pattern_id':'SP','schema_version':'DIFFERENT-2'})}
    report=check_stage_governance(runtime(),'static_relations',{'_uses':[{'source_id':'other-schema'}]},
        {},[source],{})
    assert any(r['rule_id']=='source_schema_version' and r['status']=='waiting' for r in report['checks'])


def test_normal_stage_driver_freezes_governance_and_adoption_cannot_skip_pending_rules(tmp_path,monkeypatch):
    import json
    from nw.materials import governance_runtime
    from nw.materials.phase_flow import drive_phases
    from nw.materials.phase_projection import verify_chain
    from nw.materials.governance_runtime import verify_session_governance
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.call_budget import create_budget
    from nw.task_models import Budget
    from test_material_phase_flow import PhaseModel,template_catalog
    from test_novel_flow import config
    from story_fixture import baseline
    checked=runtime();monkeypatch.setattr(governance_runtime,'load_governance',lambda _:deepcopy(checked))
    class ConfigModel(PhaseModel):
        def generate(self,messages,**params):
            result=super().generate(messages,**params)
            payload=json.loads(messages[-1]['content'])
            if '[MATERIAL_STEP]' in messages[0]['content'] and payload['stage']=='type_selection':
                raw=json.loads(result.text);value=raw['products']
                value['_governance']={'project_config':{k:[] for k in
                    ('genre_ids','mechanism_ids','structure_ids','style_ids','tone_ids')}}
                value['_governance']['project_config']['genre_ids']=[r['id'] for r in value['selection']]
                result.text=json.dumps(raw,ensure_ascii=False)
            return result
    template_catalog(tmp_path)
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('隔离治理入口');store.add_brief('调查封条');adopt_story(store,baseline(),{})
        model=ConfigModel();budget=create_budget(store,'governance',Budget(32,90000,4000))
        request,package=prepare_plan_task(store,1,'book',model,config(store),budget,'gov-main')
        _,frozen=drive_phases(store,request,{**package,'scope':'chapter'},model,config(store))
        session=frozen['material_work'];verify_chain(session)
        assert all(r.get('governance') for r in session['stages'])
        assert session['stages'][0]['governance']['status']=='waiting'
        with pytest.raises(ValueError,match='MATERIAL_GOVERNANCE'):
            verify_session_governance(session,tmp_path,adopting=True)
        session['stages'][0]['governance']['status']='pass'
        with pytest.raises(ValueError,match='MATERIAL_GOVERNANCE'):verify_chain(session)


def test_normal_type_adaptation_checks_governance_on_actual_dynamic_reference(tmp_path, monkeypatch):
    import json
    from nw.call_budget import create_budget
    from nw.materials import governance_runtime
    from nw.materials.phase_flow import drive_phases
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_novel_flow import config

    monkeypatch.setattr(governance_runtime, 'load_governance', lambda _: runtime())
    template_catalog(tmp_path)

    class AdaptationModel(PhaseModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if payload.get('stage') == 'type_adaptation':
                assert '按 TDV_020 核对所对应版本和关系' in messages[0]['content']
                output = json.loads(result.text)
                output['products']['adaptations'][0]['parameters']['rules'] = {'dynamic_rule_ids': ['C00484']}
                result.text = json.dumps(output, ensure_ascii=False)
            return result

    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('类型适配的实际引用')
        store.add_brief('调查封条')
        adopt_story(store, baseline(), {})
        model = AdaptationModel()
        budget = create_budget(store, 'governance', Budget(16, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', model, config(store), budget, 'dynamic-actual')
        with pytest.raises(ValueError, match='TDV_020'):
            drive_phases(store, request, package, model, config(store))
