"""Type/scope admission, immutable versions, truthful placements and recovery."""
from copy import deepcopy
import json

import pytest

from nw.production_methods.policy import normalize
from nw.production_methods.sources import MethodReader,relevant
from nw.production_methods.contracts import placements,validate
from nw.production_methods.selection import verify_sources
from nw.materials.phase_projection import compile_candidates
from nw.studio.repository_data import snapshot,restore
from nw.store import Store
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest,start_job
from nw.task_models import Budget
from nw.task_models import content_sha256
from project_methods_fixture import config,approve_method_gate
from test_project_methods import project,start,approve_direction,chapter_design


def test_type_scope_filter_does_not_promote_an_excerpt_or_incomplete_method(project):
    store,library,method,_=project;reader=MethodReader(store.directory.parent)
    policy=normalize({'tasks':['hook']},types=['GENRE_XUANYI'])
    assert relevant(reader,policy,'plot_design','book',['GENRE_XUANYI'])
    assert relevant(reader,policy,'plot_design','chapter',['GENRE_XUANYI'])
    assert not relevant(reader,policy,'plot_design','volume',['GENRE_XUANYI'])
    assert not relevant(reader,policy,'plot_design','book',['GENRE_QIHUAN'])
    assert not relevant(reader,policy,'character_design','book',['GENRE_XUANYI'])
    draft=deepcopy(method['body']);draft['title']+='[FAKE] 未审新草稿'
    library.save_method({'body':draft,'expected_version':2},method['id'])
    assert reader.approved()[0]['version']==2  # existing approved version remains usable


def test_approving_new_method_version_invalidates_a_waiting_frozen_selection(project):
    store,library,method,model=project;job,result=start(store,model);before=len(model.calls)
    changed=deepcopy(method['body']);changed['title']+='[FAKE] 已批准新版本'
    library.save_method({'body':changed,'expected_version':2},method['id'])
    library.review_method(method['id'],{'version':3,'decision':'approve','note':'[FAKE] 审核版本变更'})
    result=resume_job(store,job.id,model,config(store),approve_method_gate)
    assert result.status=='STALE' and 'STALE_PROJECT_METHOD' in result.reason,result.reason
    assert len(model.calls)==before


def test_approved_parent_keeps_its_version_when_new_chapter_chooses_latest(project):
    store, library, method, model = project
    job, waiting = start(store, model)
    book = approve_direction(store, job, model, waiting)
    assert book.status == 'DONE', book.reason
    revised = {**method['body'], 'title': '[FAKE] 更新下一步的问题接力方法'}
    library.save_method({'body': revised, 'expected_version': 2}, method['id'])
    library.review_method(method['id'], {'version': 3, 'decision': 'approve', 'note': '[FAKE] 核对修订版'})

    chapter, waiting = start(store, model, 'chapter', book.outputs['proposal_id'])
    assert waiting.status == 'WAITING', waiting.reason
    assert waiting.outputs['gate']['candidates'][0]['method']['version'] == 3
    finished = approve_direction(store, chapter, model, waiting)
    assert finished.status == 'DONE', finished.reason
    session = finished.outputs['application']['material_design']['work_session']
    assert {row['method']['version'] for row in session['production_method_parents']} == {2}
    plot = next(row for row in session['stages'] if row['stage'] == 'plot_design')
    assert plot['production_methods']['selected'][0]['method']['version'] == 3


@pytest.mark.parametrize('place',[
    {'path':['_method_applications'],'value':'[FAKE] 标签'},
    {'path':['members',999,'body','goal'],'value':'[FAKE] 越界'},
    {'path':['members',0,'body','goal'],'value':'[FAKE] 假值'},
])
def test_method_placements_cannot_point_to_labels_missing_fields_or_fabricated_values(place):
    product={'members':[{'key':'s','kind':'scene','body':{'goal':'[FAKE] 实际目标'}}]}
    with pytest.raises(ValueError,match='PROJECT_METHOD'):placements([place],product,'scene_design')


def test_assembly_cannot_overwrite_a_method_generated_scene_field(project):
    done=chapter_design(project);session=deepcopy(done.outputs['application']['material_design']['work_session'])
    record=next(r for r in session['stages'] if r['stage']=='scene_design')
    receipt=record['products']['_method_receipts'][0]
    receipt['placements']=[{'path':['members',0,'body','choice'],'value':record['products']['members'][0]['body']['choice']}]
    record['sha256']=content_sha256(record['products'])
    # Compile alone verifies the precise final field after state-transition assembly.
    with pytest.raises(ValueError,match='组装修改了方法落点'):compile_candidates(session)


def test_git_snapshot_preserves_project_methods_inputs_decisions_and_placements(project,tmp_path):
    store,library,method,model=project;job,result=start(store,model);done=approve_direction(store,job,model,result)
    session=done.outputs['application']['material_design']['work_session'];verify_sources(store,session)
    folder=tmp_path/'[FAKE]-git';snapshot(store.directory.parent,folder)
    destination=tmp_path/'[FAKE]-clone';destination.mkdir();restore(folder,destination)
    with Store(destination/store.directory.name,test_mode=True) as restored:
        saved=json.loads(restored.connection.execute('SELECT mapping_json FROM plan_applications').fetchone()[0])
        assert saved['material_design']['work_session']==session
        verify_sources(restored,saved['material_design']['work_session'])
        assert restored.connection.execute("SELECT COUNT(*) FROM story_decisions WHERE action='novel_confirm'").fetchone()[0]>=2


def test_original_method_source_changed_during_a_call_stops_before_the_next_call(project):
    store,library,method,model=project;job,result=start(store,model)
    def change(payload):
        if payload.get('stage')=='plot_design':
            with library.connect() as conn:conn.execute("UPDATE staging_books SET status='rejected' WHERE id=?",(method['structure_origin']['book_id'],))
    model.on_payload=change;before=len(model.calls)
    result=resume_job(store,job.id,model,config(store),approve_method_gate)
    assert result.status=='STALE',result.reason
    assert len(model.calls)==before+1


def test_disabling_new_selection_keeps_approved_parent_method_handoffs(project):
    store,library,method,model=project;job,result=start(store,model);book=approve_direction(store,job,model,result)
    child=start_job(store,JobRequest('design',design_scope='chapter',parent_id=book.outputs['proposal_id'],
        budget=Budget(80,200000,6000)))
    result=resume_job(store,child.id,model,config(store));done=approve_direction(store,child,model,result)
    assert done.status=='DONE',done.reason
    session=done.outputs['application']['material_design']['work_session']
    assert session['production_method_policy']['tasks']==[] and session['production_method_parents']
    assert not any(r['products']['_method_applications'] for r in session['stages'])
    assert any(r['products']['_method_receipts'] for r in session['stages'])


@pytest.mark.parametrize('raw',[{'tasks':[]},{'tasks':['missing']},{'max_methods':0},{'policy':'invented'}])
def test_invalid_policy_never_enters_a_job(raw):
    with pytest.raises(ValueError):normalize(raw,types=['GENRE_XUANYI'])
