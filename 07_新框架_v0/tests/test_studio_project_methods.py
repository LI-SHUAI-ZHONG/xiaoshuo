"""Real HTTP method setup, approval gates, usage receipts and frozen-job compatibility."""
import http.client
import json
import threading
import time

import pytest

from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from nw.config import Config
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
    for name,needle in [('project-methods','methodGate'),('studio-decisions','bindMethodGate'),('wizard','production_methods'),('studio','openProjectMethods')]:
        status,code=request('GET',f'/js/pages/{name}.js');assert status==200 and needle in code
