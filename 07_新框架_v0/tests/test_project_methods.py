"""Approved source methods create actual project designs and downstream work."""
from copy import deepcopy
import json

import pytest

from nw.cards import decide_card,read_card
from nw.novel_store import JobRequest,show_job,start_job
from nw.novel_flow import resume_job
from nw.store import Store
from nw.story_models import CardRef
from nw.story_state import adopt_story
from nw.task_models import Budget
from nw.tasks import read_input_manifest
from nw.production_methods.policy import normalize
from nw.production_methods.sources import MethodReader
from nw.materials.evidence import scene_checks,scene_materials
from story_fixture import baseline
from project_methods_fixture import seed_method,template_catalog,ProjectModel,approve_method_gate,config


@pytest.fixture
def project(tmp_path,monkeypatch):
    template_catalog(tmp_path);library,method=seed_method(tmp_path,monkeypatch)
    with Store(tmp_path/'[FAKE]-project',create=True,test_mode=True) as store:
        store.init_project('[FAKE] 本项目调查');store.add_brief('[FAKE] 查出封条更换的证据与登记者，并承担调查代价。')
        adopt_story(store,baseline(),{})
        yield store,library,method,ProjectModel()


def start(store,model,scope='book',parent=None,policy=None):
    policy=policy or normalize({'tasks':['hook']},types=['GENRE_XUANYI'])
    job=start_job(store,JobRequest('design',design_scope=scope,parent_id=parent,budget=Budget(80,180000,6000),production_method_policy=policy))
    return job,resume_job(store,job.id,model,config(store))


def approve_direction(store,job,model,result):
    while result.status=='WAITING' and result.outputs['gate'].get('kind')=='production_method_selection':
        result=resume_job(store,job.id,model,config(store),approve_method_gate)
    assert result.status=='WAITING',result.reason
    gate=result.outputs['gate'];root=gate['candidates'][0]['root']['card_id']
    return resume_job(store,job.id,model,config(store),lambda *_:{'action':'approve','reason':'[FAKE] 审核具体卡片与前置一致','root':root})


def test_real_method_reader_is_read_only_and_pins_approved_structure(project):
    store,library,method,_=project;reader=MethodReader(store.directory.parent)
    row=reader.approved()[0];pin=reader.snapshot(row);reader.verify(pin)
    assert row['id']==method['id'] and pin['instance']['events']
    assert len(pin['body']['evidence'])>=2 and pin['structure_origin']['structure_version']==1
    forged=deepcopy(pin);forged['instance']['events'][0]['summary']='[FAKE] 篡改'
    with pytest.raises(ValueError,match='快照已被改写'):reader.verify(forged)


def test_book_methods_wait_for_author_input_approval_and_keep_concrete_cards(project):
    store,library,method,model=project;job,result=start(store,model)
    assert result.status=='WAITING' and result.outputs['gate']['kind']=='production_method_selection',result.reason
    gate=result.outputs['gate'];assert gate['stage']=='plot_design'
    assert gate['candidates'][0]['inputs']['i1']['kind']=='brief'
    assert not any(json.loads(m[-1]['content']).get('stage')=='plot_design' for m in model.calls)
    finished=approve_direction(store,job,model,result)
    assert finished.status=='DONE',finished.reason
    application=finished.outputs['application'];members=application['approvals']
    assert any(read_card(store,CardRef(ref['card_id'],ref['version']))['kind']=='character' for ref in members)
    session=application['material_design']['work_session']
    plot=next(r for r in session['stages'] if r['stage']=='plot_design')
    assert plot['products']['_method_applications'][0]['method_id']==method['id']
    assert '[FAKE] 先以本案旧印' in plot['products']['directions'][0]['choice']
    assert plot['production_methods']['decision']['choice']['method_ids']==[method['id']]
    assert len(plot['production_methods']['target']['candidates'][0]['method']['instance']['events'])>=2


def test_missing_matching_type_method_stops_before_any_paid_design_call(project):
    store,library,method,model=project
    policy=normalize({'tasks':['hook']},types=['GENRE_QIHUAN'])
    job,result=start(store,model,policy=policy)
    assert result.status=='BLOCKED' and 'METHOD_DESIGN_REQUIRED' in result.reason
    assert not model.calls and not store.list('draft')


@pytest.mark.parametrize('problem',['omit_application','wrong_value'])
def test_missing_or_fabricated_execution_cannot_publish_project_cards(project,problem):
    store,_,_,model=project;setattr(model,problem,True);job,result=start(store,model)
    result=resume_job(store,job.id,model,config(store),approve_method_gate)
    assert result.status=='BLOCKED' and 'PROJECT_METHOD' in result.reason,result.reason
    assert not store.connection.execute('SELECT 1 FROM plan_applications').fetchone()


def test_missing_semantic_prerequisite_returns_design_instead_of_guessing(tmp_path,monkeypatch):
    template_catalog(tmp_path);seed_method(tmp_path,monkeypatch,input_kind='parent_outline')
    with Store(tmp_path/'[FAKE]-missing',create=True,test_mode=True) as store:
        store.init_project('[FAKE] 无父纲');store.add_brief('[FAKE] 本项目需要完整调查');adopt_story(store,baseline(),{})
        model=ProjectModel();job,result=start(store,model)
        assert result.status=='BLOCKED' and 'METHOD_DESIGN_REQUIRED' in result.reason
        assert 'parent_outline' in result.reason and not store.list('draft')
        assert not any(json.loads(m[-1]['content']).get('stage')=='plot_design' for m in model.calls)


def test_completed_stage_calls_are_reused_when_author_chooses_method(project):
    store,_,_,model=project;job,result=start(store,model);before=len(model.calls)
    assert result.status=='WAITING'
    resume_job(store,job.id,model,config(store))
    assert len(model.calls)==before
    result=resume_job(store,job.id,model,config(store),approve_method_gate)
    assert result.status=='WAITING' and result.outputs['gate'].get('candidates')
    stages=[json.loads(m[-1]['content']).get('stage') for m in model.calls]
    assert stages.count('world_design')==1


def chapter_design(project):
    store,library,method,model=project;book,result=start(store,model)
    done=approve_direction(store,book,model,result);assert done.status=='DONE',done.reason
    job,result=start(store,model,'chapter',done.outputs['proposal_id'])
    done=approve_direction(store,job,model,result);assert done.status=='DONE',done.reason
    return done


def test_approved_book_method_reaches_chapter_scene_writer_review_and_acceptance(project):
    store,library,method,model=project;done=chapter_design(project)
    application=done.outputs['application'];scene=application['chapters'][0]['scenes'][0]['scene_id']
    session=application['material_design']['work_session']
    assert session['production_method_parents']
    scene_record=next(r for r in session['stages'] if r['stage']=='scene_design')
    assert len(scene_record['products']['_method_receipts'])>=2
    checks=[c for c in scene_checks(scene_materials(store,scene)) if c['id'].startswith('method:')]
    assert checks and all(c['production_method']['version']==2 for c in checks)
    job=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(20,200000,6000,0)))
    result=resume_job(store,job.id,model,config(store))
    assert result.status=='WAITING',result.reason
    reviews=[json.loads(m[-1]['content']) for m in model.calls if 'material_review' in json.loads(m[-1]['content'])]
    assert reviews and any(c['id'].startswith('method:') for c in reviews[-1]['material_review']['checks'])
    result=resume_job(store,job.id,model,config(store),lambda *_:{'action':'accept','reason':'[FAKE] 已核对方法实际呈现及独立引文证据'})
    assert result.status=='DONE',result.reason
    assert store.list('accepted')


def test_downstream_without_method_receipt_cannot_reach_writing(project):
    store,_,_,model=project;book,result=start(store,model);done=approve_direction(store,book,model,result)
    model.omit_receipt=True
    job,result=start(store,model,'chapter',done.outputs['proposal_id'])
    while result.status=='WAITING' and result.outputs['gate'].get('kind')=='production_method_selection':
        result=resume_job(store,job.id,model,config(store),approve_method_gate)
    assert result.status=='BLOCKED' and '下游必须逐项回执' in result.reason,result.reason
    assert not store.list('draft')


def test_withdrawn_method_source_blocks_before_new_prose_call(project):
    store,library,method,model=project;done=chapter_design(project)
    scene=done.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
    with library.connect() as conn:conn.execute("UPDATE staging_books SET status='rejected' WHERE id=?",(method['structure_origin']['book_id'],))
    before=len(model.calls)
    job=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(20,200000,6000)))
    result=resume_job(store,job.id,model,config(store))
    assert result.status=='STALE' and 'STALE_PROJECT_METHOD' in result.reason,result.reason
    assert len(model.calls)==before and not store.list('draft')
