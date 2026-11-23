"""Real HTTP method setup, approval gates, usage receipts and frozen-job compatibility."""
from copy import deepcopy
import http.client
import json
import threading
import time

import pytest

from nw.studio.api import STAGE_LABELS, StudioService
from nw.studio.server import create_studio_server
from nw.config import Config
from nw.studio.corpus_methods import publish_methods
from nw.studio.repository_data import restore, snapshot
from nw.studio.production_store import ProductionStore
from project_methods_fixture import seed_method,template_catalog,ProjectModel


@pytest.fixture
def client(tmp_path,monkeypatch):
    workspace=tmp_path/'[FAKE]-http';workspace.mkdir();template_catalog(workspace)
    _,method=seed_method(workspace,monkeypatch)
    # The small test source catalog has no original governance documents.
    # Keep this HTTP fixture focused on method execution; governance has its own suite.
    monkeypatch.setattr('nw.studio.production.governance',lambda _: {})
    service=StudioService(workspace,config_path=tmp_path/'missing.toml');server=create_studio_server(service,port=0)
    model=ProjectModel();server.production.test_mode=True
    config=Config('fake','http://localhost','[FAKE] project-methods','',5,{},workspace,source_driven=False)
    server.production.runtime_factory=lambda:(config,model)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def request(verb,path,body=None,origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        conn.request(verb,path,json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None,headers)
        response=conn.getresponse();raw=response.read().decode('utf-8');status=response.status;conn.close()
        return status,json.loads(raw) if path.startswith('/api/') else raw
    def settled(ident):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            task=server.production._workers.get(ident)
            if task:task.join(timeout=.05)
            if not task or not task.is_alive():return request('GET',f'/api/novels/{ident}/progress')[1]
        raise AssertionError('isolated production worker did not settle')
    try:yield request,settled,server,method
    finally:server.shutdown();server.server_close();worker.join(timeout=5)


def make(request,enabled=True):
    payload={'title':'[FAKE] HTTP方法制作','idea':'[FAKE] 核对封条旧印以追查登记者的代价','genre_ids':['GENRE_XUANYI'],
             'budget':{'max_calls':80,'context_char_limit':200000,'output_limit':6000,'max_revisions':0}}
    if enabled:payload['production_methods']={'tasks':['hook']}
    status,result=request('POST','/api/novels',payload);assert status==201,result
    return result['novel']['id']


def test_http_selects_a_real_method_then_reports_actual_project_placements(client):
    request,settled,server,method=client;ident=make(request);progress=settled(ident)
    assert progress['status']=='WAITING'
    gate=progress['gates'][0];assert gate['target']['kind']=='production_method_selection'
    root=f'/api/novels/{ident}'
    status,result=request('POST',root+'/gates/'+gate['id'],{'token':gate['token'],'action':'approve',
        'reason':'[FAKE] 已核对实际前置和类型适用性','method_ids':[method['id']]})
    assert status==200,result
    progress=settled(ident);gate=progress['gates'][0]
    assert gate['target']['candidates']
    root_id=gate['target']['candidates'][0]['root']['card_id']
    assert request('POST',root+'/gates/'+gate['id'],{'token':gate['token'],'action':'approve','root':root_id,'reason':'[FAKE] 具体设计可执行'})[0]==200
    assert settled(ident)['status']=='DONE'
    status,uses=request('GET',root+'/methods')
    assert status==200 and uses['policy']['tasks']==['hook']
    selected=[r for r in uses['uses'] if r.get('method_id')==method['id']]
    assert len(selected)==1 and selected[0]['validation']=='VALID' and selected[0]['application']['outputs'][0]['placements']
    assert uses['review_checks']==[]  # design execution is separate from prose evidence


def test_blocked_book_reports_the_actual_stage_and_reuses_its_job_with_the_new_budget(client, monkeypatch):
    from ai_world_method_fixture import WorldModel

    request,settled,server,_=client
    production=server.production
    runtime,_=production._runtime()
    model=WorldModel()
    monkeypatch.setattr(production,'runtime_factory',lambda:(runtime,model))
    budget=production.budget
    with monkeypatch.context() as old:
        old.setattr(production,'budget',lambda raw=None:budget({'context_char_limit':4000,**(raw or {})}))
        status,created=request('POST','/api/novels',{'title':'[FAKE] 容量和选材断点',
            'idea':'[FAKE] 记录员调查潮刻为何变动','genre_ids':['GENRE_XUANYI'],'design_mode':'auto'})
        assert status==201,created
        ident=created['novel']['id']
        blocked=settled(ident)
    assert blocked['status']=='BLOCKED' and blocked['current_step']==STAGE_LABELS['type_selection']['zh'],blocked['reason']
    assert blocked['tree'][0]['children'][0]['status']=='blocked'
    assert '4,000 字符' in blocked['reason'] and not model.calls
    root=f'/api/novels/{ident}'
    assert request('GET','/api/kb/method-recommendations?slot=world&types=GENRE_XUANYI')[1]['book_world_available'] is False
    assert request('POST',root+'/retry',{'use_saved_context_budget':True})[0]==200
    retried=settled(ident)
    assert retried['job']['id']==blocked['job']['id']
    assert retried['job']['outputs']['budget']['context_char_limit']==150000
    assert retried['status']=='BLOCKED' and 'METHOD_DESIGN_REQUIRED' in retried['reason'],retried['reason']
    assert retried['job']['outputs']['blocked_design'] == {'scope':'book','stage':'world_design'}
    assert [json.loads(messages[-1]['content'])['stage'] for messages in model.calls]==['type_selection','type_adaptation']


def test_configuration_changes_only_new_jobs_and_requires_a_reason(client):
    request,settled,server,_=client;ident=make(request,enabled=False);settled(ident);root=f'/api/novels/{ident}/methods'
    assert request('POST',root,{'policy':{'tasks':['hook']},'reason':''})[0]==400
    status,configured=request('POST',root,{'policy':{'tasks':['hook']},'reason':'[FAKE] 后续按真实方法制作'})
    assert status==200 and configured['policy']['tasks']==['hook'] and configured['current_job_policy']=={}
    with server.production.open_store(server.production.db.get(ident)) as store:
        original=json.loads(store.connection.execute('SELECT request_json FROM novel_jobs LIMIT 1').fetchone()[0])
        assert not original['production_method_policy']
    assert request('POST',root,{'policy':None,'reason':'[FAKE] 关闭后续方法调度'})[1]['policy']=={}
    assert request('POST',root,{'reason':'[FAKE] 缺policy'})[0]==400


def test_http_rejects_wrong_method_selection_and_untrusted_mutation(client):
    request,settled,_,_=client;ident=make(request);progress=settled(ident);gate=progress['gates'][0]
    root=f'/api/novels/{ident}'
    status,result=request('POST',root+'/gates/'+gate['id'],{'token':gate['token'],'action':'approve','reason':'[FAKE] 不存在的方法','method_ids':['missing']})
    assert status==400 and '有效' in result['error']
    progress=settled(ident);assert progress['status']=='WAITING'
    assert request('POST',root+'/methods',{'policy':None,'reason':'[FAKE] 外站'},'https://untrusted.example')[0]==403
    assert request('GET','/api/novels/missing/methods')[0]==404


def test_ui_modules_expose_method_gates_wizard_and_usage_panel(client):
    request,_,_,_=client
    for name,needle in [('project-methods','methodGate'),('studio-decisions','bindMethodGate'),('wizard','design_mode:mode'),('studio','openProjectMethods')]:
        status,code=request('GET',f'/js/pages/{name}.js');assert status==200 and needle in code


def test_wizard_and_stage_share_approved_type_matches_and_save_evidence(client, tmp_path):
    request, settled, server, generic = client
    library = server.production.library
    origin = generic['structure_origin']

    def add_method(title, types):
        body = {**generic['body'], 'title': title, 'type_tags': types}
        with library.connect() as conn:
            method = publish_methods(library, conn, origin['book_id'], origin['structure_version'],
                                     [{'body': body, 'basis': origin['basis']}])[0]
        return method

    exact = add_method('[FAKE] 密室指定方法', ['SUB_XUANYI_02'])
    sibling = add_method('[FAKE] 心理悬疑指定方法', ['SUB_XUANYI_01'])
    cross = add_method('[FAKE] 跨类型方法', [])
    rec_path = '/api/kb/method-recommendations?slot=hook&types=GENRE_XUANYI'
    child_path = rec_path + ',SUB_XUANYI_02'
    status, genres = request('GET','/api/genres')
    assert status == 200
    genre = next(row for row in genres['genres'] if row['id']=='GENRE_XUANYI')
    assert genre['book_count'] == 1 and genre['coverage_total'] == len(genres['analysis_domains'])
    assert 'hook' in genres['approved_books'][0]['observed_domains']
    assert genres['approved_books'][0]['version']==generic['structure_origin']['structure_version']
    status, groups = request('GET',child_path.replace('slot=hook','slot=all'))
    assert status == 200
    from_atlas = next(group['recommendations'] for group in groups['slots'] if group['slot']=='hook')
    from_wizard = request('GET',child_path)[1]['recommendations']
    assert from_atlas == [{key:row[key] for key in from_atlas[0]} for row in from_wizard]
    assert [row['id'] for row in request('GET', child_path)[1]['recommendations']] == [generic['id']]
    for method in (exact, sibling, cross):
        status, result = request('POST', f"/api/kb/methods/{method['id']}/review",
                                 {'version': 1, 'decision': 'approve', 'note': '[FAKE] 核对方法与实际原文'})
        assert status == 200 and result['available'], result

    ranked = request('GET', child_path)[1]['recommendations']
    assert [(row['id'], row['type_match']['level']) for row in ranked] == [
        (exact['id'], 'subgenre'), (generic['id'], 'main'), (cross['id'], 'cross_type')]
    assert [row['id'] for row in request('GET', rec_path)[1]['recommendations']] == [generic['id'], cross['id']]
    chosen = {'id': exact['id'], 'version': 1, 'slot': 'hook'}
    novel = {'title': '[FAKE] 密室测试', 'idea': '[FAKE] 追查印记与登记者',
             'genre_ids': ['GENRE_XUANYI', 'SUB_XUANYI_02'], 'production_methods': {'tasks': ['hook']},
             'method_preferences': [chosen]}
    assert request('POST', '/api/novels', {**novel, 'method_preferences': [{**chosen, 'id': sibling['id']}]})[0] == 400
    assert request('POST', '/api/novels', {**novel, 'method_preferences': [{**chosen, 'slot': 'world'}]})[0] == 400
    status, result = request('POST', '/api/novels', novel)
    assert status == 201, result
    ident = result['novel']['id']
    references = result['novel']['wizard']['method_references']
    assert references[0]['evidence'] == ranked[0]['evidence']
    assert references[0]['evidence_locations'] == ranked[0]['evidence_locations']
    assert references[0]['snapshot_sha256'] and references[0]['structure_origin']['structure_version'] == 1
    assert result['novel']['wizard']['production_methods']['preferred_methods'] == {exact['id']: 1}
    progress = settled(ident)
    assert progress['status'] == 'WAITING', progress['reason']
    gate = progress['gates'][0]
    assert [(row['method']['id'], row['preferred']) for row in gate['target']['candidates']] == [
        (exact['id'], True), (generic['id'], False), (cross['id'], False)]

    folder, restored = tmp_path / 'tracked-runtime', tmp_path / 'restored-workspace'
    restored.mkdir()
    snapshot(library.workspace, folder)
    restore(folder, restored)
    assert ProductionStore(restored).get(ident)['wizard']['method_references'] == references


def test_pending_gate_refresh_rebinds_latest_version_without_model_calls(client):
    request, settled, server, method = client
    ident = make(request)
    progress = settled(ident)
    assert progress['status'] == 'WAITING'
    original = progress['gates'][0]
    root = f'/api/novels/{ident}'
    gate_path = f"{root}/gates/{original['id']}"
    model = server.production._runtime()[1]
    prior_calls = len(model.calls)
    assert 'world_design' not in [value['kind'] for value in original['target']['candidates'][0]['inputs'].values()]
    assert request('POST', gate_path + '/refresh', {}) == (200, {'gate': original, 'changed': False})

    library = server.production.library
    body = deepcopy(method['body'])
    body['title'] += ' [FAKE] 更新世界规则前置'
    body['prerequisites'][0]['input_kind'] = 'world_design'
    library.save_method({'body': body, 'expected_version': 2}, method['id'])
    rec_path = f"/api/kb/method-recommendations?slot=hook&types=GENRE_XUANYI&selected={method['id']}"
    assert request('GET', rec_path)[1]['current_versions'] == {method['id']: 2}
    library.review_method(method['id'], {'version': 3, 'decision': 'approve', 'note': '[FAKE] 核对更新的前置'})
    assert request('GET', rec_path)[1]['current_versions'] == {method['id']: 3}
    stale = {'title': '[FAKE] 过期立项选择', 'idea': '[FAKE] 查验印记', 'genre_ids': ['GENRE_XUANYI'],
             'method_preferences': [{'id': method['id'], 'slot': 'hook', 'version': 2}]}
    assert request('POST', '/api/novels', stale)[0] == 400

    choice = {'action': 'approve', 'token': original['token'], 'method_ids': [method['id']], 'reason': '[FAKE] 核对前置'}
    assert request('POST', gate_path, choice)[0] == 400
    assert settled(ident)['status'] == 'WAITING'
    status, result = request('POST', gate_path + '/refresh', {})
    assert status == 200 and result['changed'], result
    updated = result['gate']
    version = updated['target']['candidates'][0]
    assert version['method']['version'] == 3 and version['inputs']['i1']['kind'] == 'world_design'
    assert version['inputs']['i1']['ref']['task_id']
    assert updated['token'] != original['token'] and updated['job_id'] == original['job_id']
    assert len(model.calls) == prior_calls
    assert request('POST', gate_path, choice)[0] == 400
    refreshed_path = f"{root}/gates/{updated['id']}"
    assert request('POST', refreshed_path + '/refresh', {}) == (200, {'gate': updated, 'changed': False})
    assert request('POST', refreshed_path, {**choice, 'token': updated['token']})[0] == 200
    progress = settled(ident)
    assert progress['status'] == 'WAITING' and progress['gates'][0]['id'] != updated['id']
    assert request('POST', refreshed_path + '/refresh', {})[0] == 400
    with server.production.open_store(server.production.db.get(ident)) as store:
        rows = store.connection.execute('SELECT status,input_json FROM novel_steps WHERE job_id=? AND step_key=? '
                                        'ORDER BY attempt', (updated['job_id'], updated['step'])).fetchall()
        assert [row['status'] for row in rows] == ['STALE', 'DONE']
        assert [json.loads(row['input_json'])['candidates'][0]['method']['version'] for row in rows] == [2, 3]
    usage = request('GET', root + '/methods')[1]['uses']
    assert any(row.get('method_version') == 3 and row.get('application') for row in usage)
