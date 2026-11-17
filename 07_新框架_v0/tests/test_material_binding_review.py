from copy import deepcopy
import pytest

from nw.materials.semantic_application import validate_semantic_applications
from test_material_semantic_clauses import fixture


def test_profile_and_nonempty_paths_cannot_substitute_for_original_workflow_binding_review():
    source,contract,before,value,context=fixture()
    context.update(binding_policy='workflow-source-binding-v1',binding_reviews={})
    with pytest.raises(ValueError,match='BINDING|binding'):
        validate_semantic_applications('action_design',value,before,[source],context)


def test_a_model_cannot_add_its_own_route_approval_to_the_criteria():
    source,contract,before,value,context=fixture()
    context.update(binding_policy='workflow-source-binding-v1',binding_reviews={})
    value['_criteria'][0]['binding_review']={'approved':True,'stage':'action_design'}
    with pytest.raises(ValueError,match='binding|criteria'):
        validate_semantic_applications('action_design',value,before,[source],context)


def test_exact_reviewed_use_is_admitted_but_other_step_or_production_fixture_is_not():
    from fake_binding_reviews import review_fixture
    from nw.materials.binding_reviews import validate_execution_binding
    source,contract,before,value,context=fixture();review=review_fixture(source,['action_design'])
    context.update(binding_policy='workflow-source-binding-v1',binding_test_mode=True,binding_reviews={'method':review})
    validate_semantic_applications('action_design',value,before,[source],context)
    with pytest.raises(ValueError,match='binding'):
        validate_execution_binding('plot_design',source,context)
    context['binding_test_mode']=False
    with pytest.raises(ValueError,match='fixture'):validate_execution_binding('action_design',source,context)


def test_original_change_cannot_reuse_a_route_review():
    from fake_binding_reviews import review_fixture
    from nw.materials.binding_reviews import validate_review
    source,*_=fixture();review=review_fixture(source,['action_design'])
    source['original_text']+='\n【指令】未审核的新规则'
    with pytest.raises(ValueError,match='text changed'):validate_review(source,review,test_mode=True)


@pytest.mark.parametrize('misclassified_navigation',[False,True])
def test_required_unreviewed_source_stops_before_the_first_generation_call(tmp_path,monkeypatch,misclassified_navigation):
    from nw.materials.catalog import build_catalog
    from nw.materials.unit_catalog import index_units
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import drive_phases
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.call_budget import create_budget
    from nw.task_models import Budget
    from test_material_catalog import _manifest
    from test_material_phase_flow import PhaseModel
    from test_novel_flow import config
    from story_fixture import baseline
    data='### 1.1_候选方法\n【定义】人物必须有实际动机。\n【指令】当前动作要有真实后果。'.encode('utf-8')
    manifest=_manifest(tmp_path/'sources',tmp_path,[('library.txt','library',data)])
    build_catalog(tmp_path,tmp_path/'sources',manifest);index_units(tmp_path,None)
    from nw.materials.adjudication import build_adjudications
    build_adjudications(tmp_path)
    source=next(s for r in SourceDesk(tmp_path).rows if (s:=SourceDesk(tmp_path).read(r['id']))['use_mode']=='project_method')
    if misclassified_navigation:
        original=SourceDesk.read
        monkeypatch.setattr(SourceDesk,'read',lambda desk,ident:{**original(desk,ident),'use_mode':'navigation_only'})
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('隔离未核用途');store.add_brief('调查封条');adopt_story(store,baseline(),{})
        provider=PhaseModel();budget=create_budget(store,'unreviewed',Budget(32,90000,4000))
        request,package=prepare_plan_task(store,1,'book',provider,config(store),budget,'review-required')
        package['materials']=[{'source':source['source'],'request':{'disposition':'required'}}]
        with pytest.raises(ValueError,match='required source workflow binding needs_review'):
            drive_phases(store,request,package,provider,config(store))
        assert not provider.calls


def test_reviewed_use_is_not_lost_due_to_an_old_navigation_classification(tmp_path):
    import json
    from nw.materials.catalog import build_catalog
    from nw.materials.unit_catalog import index_units
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import _sources
    from nw.materials.binding_reviews import POLICY
    from fake_binding_reviews import review_fixture
    from test_material_catalog import _manifest
    data=('SOURCE: 方法.json\n=====\n'+json.dumps([{'rule_id':'ACTUAL_METHOD',
        'writing_steps':['先按具体人物的能力与阻碍设计行动，再交场景选择']}],ensure_ascii=False)).encode('utf-8')
    manifest=_manifest(tmp_path/'sources',tmp_path,[('methods.txt','types',data)])
    build_catalog(tmp_path,tmp_path/'sources',manifest);index_units(tmp_path,None)
    desk=SourceDesk(tmp_path)
    source=next(desk.read(r['id']) for r in desk.rows if r['key']=='ACTUAL_METHOD')
    assert source['use_mode']=='navigation_only'
    path=tmp_path/'materials/workflow_binding_reviews.json'
    path.write_text(json.dumps({'policy':POLICY,'reviews':[review_fixture(source,['action_design'])]},
        ensure_ascii=False),encoding='utf-8')
    desk=SourceDesk(tmp_path,test_mode=True)
    package={'scope':'chapter','brief':{'text':'设计调查动作','constraints':''},
        'materials':[{'source':source['source'],'profile':source['source']['profile'],
            'request':{'disposition':'required'}}]}
    assert source in _sources(desk,'action_design',package,{},reviewed_only=True)


def test_discovery_finds_unreviewed_sources_without_admitting_them_as_execution(tmp_path):
    from nw.materials.catalog import build_catalog
    from nw.materials.unit_catalog import index_units
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import _sources
    from test_material_catalog import _manifest
    data='### 1.1_人物方法\n【定义】人物目标促成选择并承担代价。\n【指令】先核对当前人物目标。'.encode('utf-8')
    manifest=_manifest(tmp_path/'sources',tmp_path,[('library.txt','library',data)])
    build_catalog(tmp_path,tmp_path/'sources',manifest);index_units(tmp_path,None)
    desk=SourceDesk(tmp_path);assert desk.search('人物')['items']
    deferred=[]
    result=_sources(desk,'character_design',{'scope':'chapter','brief':{'text':'人物目标','constraints':''},'materials':[]},
        {},reviewed_only=True,deferrals=deferred)
    assert result==[] and deferred and all(r['status']=='needs_review' for r in deferred)


def test_original_1284_controls_retrieval_and_is_not_a_late_novel_design_use(tmp_path):
    import json
    from pathlib import Path
    from nw.materials.binding_reviews import load_reviews,reviewed_source
    samples=json.loads((Path(__file__).parents[1]/'fixtures/material_semantics/source_samples.json').read_text(encoding='utf-8'))['samples']
    source=next(s for s in samples if s['source']['key'].startswith('128.4_'))
    reviews=load_reviews(tmp_path)
    assert reviewed_source(source,reviews,stage='retrieval') is not None
    assert reviewed_source(source,reviews,stage='bind_scope') is None


def test_known_source_number_cannot_be_applied_as_a_novel_design_or_prose_instruction():
    from fake_binding_reviews import review_fixture
    from nw.materials.source_semantics import compile_semantics
    from nw.task_models import content_sha256
    from test_material_semantic_clauses import source as make_source,criterion
    source,_,before,value,context=fixture()
    source=make_source(original='{"rule_id":"R1","rule":"先核对人物能力再安排具体动作"}')
    contract=compile_semantics(source);review=review_fixture(source,['action_design'])
    numeric=next(c for c in contract['obligations'] if c['locator']=='/rule_id')
    next(c for c in review['clause_reviews'] if c['text_start']==numeric['source_ref']['text_start'])['status']='not_project_instruction'
    review['sha256']=content_sha256({k:v for k,v in review.items() if k!='sha256'})
    value['_criteria']=[criterion(contract)]
    context.update(semantic_contracts=[contract],binding_policy='workflow-source-binding-v1',
                   binding_test_mode=True,binding_reviews={'method':review})
    with pytest.raises(ValueError,match='metadata is not a project instruction'):
        validate_semantic_applications('action_design',value,before,[source],context)
