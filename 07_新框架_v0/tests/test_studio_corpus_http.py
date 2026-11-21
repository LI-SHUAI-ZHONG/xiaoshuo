"""Real HTTP exercises the full source-structure-method chain in isolation."""
from copy import deepcopy
import http.client
import json
import threading

import pytest

from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from corpus_fixture import CorpusModel,make_book,runtime,wait_job


@pytest.fixture
def client(tmp_path):
    studio=StudioService(tmp_path/'[FAKE]-corpus-http',config_path=tmp_path/'missing.toml')
    server=create_studio_server(studio,port=0)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def request(method,path,body=None,origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        conn.request(method,path,json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None,headers)
        response=conn.getresponse();status=response.status;raw=response.read().decode('utf-8');conn.close()
        return status,json.loads(raw) if path.startswith('/api/') else raw
    try:yield request,server.library
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)


def test_http_pipeline_review_methods_and_immutable_input_output(client,monkeypatch):
    request,library=client;provider=CorpusModel()
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider))
    book=make_book(library);root=f'/api/staging/{book["id"]}/corpus'
    status,catalog=request('GET','/api/corpus/catalog')
    assert status==200 and len(catalog['domains'])==12
    old=request('GET','/api/corpus/catalog?version=4')[1]
    assert len(old['domains'])==11 and 'cast_roster_options' not in old
    assert request('GET','/api/corpus/catalog?version=99')[0]==400
    status,empty=request('GET',root)
    assert status==200 and not empty['initialized']
    status,estimate=request('POST',root+'/estimate',{'chunk_chars':6000})
    assert status==200 and estimate['minimum_structure_calls']==18
    status,job=request('POST',root+'/jobs',{'options':{'extent':'complete','note':'[FAKE] HTTP完整性声明'}})
    assert status==200
    completed=wait_job(library,book['id'],job['id'])
    assert completed['status']=='completed',completed['error']
    queue='/api/kb/review-queue'
    assert [r['id'] for r in request('GET',queue)[1]['structures']]==[book['id']]
    assert request('GET',root+'/jobs')[1]['jobs'][0]['id']==job['id']
    status,call=request('GET',root+f'/jobs/{job["id"]}/calls/1')
    assert status==200 and call['input']['messages'] and call['output']['text']
    assert request('GET',root+f'/jobs/{job["id"]}')[1]['calls_used']==18
    legacy=root.removesuffix('/corpus')
    assert request('GET',legacy)[1]['status']=='pending_verify'
    for body in ({},{'approve_all':True}):
        assert request('POST',legacy+'/verify',body)[0]==400
    assert request('POST',legacy+'/decompose',{'items':[]})[0]==400
    assert request('GET',legacy)[1]['status']=='pending_verify'
    assert request('POST',root+'/review',{'version':1,'decision':'approve','note':'[FAKE] 逐项核对'})[1]['available']
    status,method=request('POST',root+'/methods',{'version':1,'thread_ids':['T_hook']})
    assert status==200 and method['status']=='draft' and method['issues']
    pending=request('GET',queue)[1]
    assert pending['structures']==[] and [r['id'] for r in pending['methods']]==[method['id']]
    assert method['structure_origin']['basis']['thread_ids']==['T_hook']
    old=request('GET',root+'?version=1')[1]
    obsolete=deepcopy(old['body'])
    obsolete['schema_version']=1
    status,problem=request('POST',root+'/save',{'expected_version':1,'body':obsolete})
    assert status==400 and '当前拆解结构版本' in str(problem)
    assert request('GET',root)[1]['latest_version']==1
    overview=deepcopy(old['body']['overview']);overview['mainline']+='[FAKE] HTTP修订'
    revised=request('POST',root+'/record',{'expected_version':1,'section':'overview','row':overview})
    assert revised[0]==200 and revised[1]['version']==2
    assert request('GET',queue)[1]['structures']==[{'id':book['id'],'title':book['title'],'version':2}]
    assert request('GET',root+'?version=1')[1]['body_sha256']==old['body_sha256']
    assert request('POST',root+'/record',{'expected_version':1,'section':'overview','row':overview})[0]==400


def test_manual_records_read_confirmation_and_source_limits_are_explicit(client):
    request,library=client;book=make_book(library);root=f'/api/staging/{book["id"]}/corpus'
    status,initialized=request('POST',root+'/initialize',{'extent':'excerpt','note':'[FAKE] 仅导入片段'})
    assert status==200 and initialized['version']==1 and initialized['body']['events']==[]
    chapters=[u['id'] for u in initialized['body']['units'] if u['level']=='chapter']
    status,read=request('POST',root+'/record',{'expected_version':1,'section':'read_confirmation','row':chapters})
    assert status==200 and read['coverage']['reviewed_units']==chapters
    assert read['statistics']['manual_reviewed_units']==chapters
    assert read['body']['source_extent']['status']=='excerpt'
    assert request('POST',root+'/review',{'version':2,'decision':'approve','note':'[FAKE] 缺实际观察不得通过','accept_limitations':True})[0]==400
    assert request('POST',root+'/record',{'expected_version':2,'section':'read_confirmation','row':['invented']})[0]==400
    assert request('POST',root+'/record',{'expected_version':2,'section':'evidence','row':{
        'id':'E_bad','start':0,'end':3,'quote':'不存在','explanation':'[FAKE] 错误证据'}})[0]==400
    assert request('GET',root)[1]['version']==2


def test_no_config_or_invalid_requests_never_silently_start_a_job(client):
    request,library=client;book=make_book(library);root=f'/api/staging/{book["id"]}/corpus'
    status,missing=request('POST',root+'/jobs',{'options':{'extent':'complete','note':'[FAKE] 未配置'}})
    assert status==400 and 'CONFIG_REQUIRED' in json.dumps(missing)
    assert request('GET',root+'/jobs')[1]['jobs']==[]
    for query in ('?version=nan','?version=-1'):
        assert request('GET',root+query)[0]==400
    assert request('GET','/api/staging/missing/corpus')[0]==404
    assert request('POST',root+'/initialize',{},'https://untrusted.example')[0]==403
    assert request('POST',root+'/jobs/missing',{'action':'resume'})[0]==404


def test_legacy_requests_cannot_replace_an_active_job_or_archive_its_unreviewed_structure(client,monkeypatch):
    from corpus_fixture import SOURCE

    request,library=client
    book=library.import_book({'text':SOURCE,'filename':'[FAKE] 原有批注.md'})
    key=book['id']
    library.review_book(key,{'types':['GENRE_XUANYI']})
    short={'slot':'tone','option_key':'tone.TONE_COLD','usage_text':'[FAKE] 局部冷调',
           'stages':['expression_design'],'evidence':{'quote':'甲提出问题'}}
    library._insert_items(key,[short])
    endpoint=f'/api/staging/{key}'
    entered,release=threading.Event(),threading.Event()
    model=CorpusModel()
    def wait_for_first(_):
        entered.set()
        assert release.wait(20)
    model.on_call=wait_for_first
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    status,job=request('POST',endpoint+'/corpus/jobs',{'options':{'extent':'complete','note':'[FAKE] 两章全文'}})
    try:
        assert status==200 and entered.wait(3)
        assert request('POST',endpoint+'/verify',{'approve_all':True})[0]==400
        assert request('POST',endpoint+'/decompose',{'items':[short]})[0]==400
        assert request('GET',endpoint)[1]['status']=='decomposing'
    finally:
        release.set()
    assert wait_job(library,key,job['id'])['status']=='completed'
    assert request('GET',endpoint)[1]['status']=='pending_verify'
    assert request('POST',endpoint+'/verify',{'approve_all':True})[0]==400
    assert request('POST',endpoint+'/corpus/review',{'version':1,'decision':'approve','note':'[FAKE] 核对原文'})[0]==200
    archived=request('GET',endpoint)[1]
    assert archived['status']=='archived' and [i['status'] for i in archived['items']]==['draft']


def test_new_modules_are_served_by_the_existing_client(client):
    request,_=client
    for module in ('corpus','corpus_editor','corpus_jobs','corpus_view'):
        status,code=request('GET',f'/js/pages/{module}.js')
        assert status==200 and 'export ' in code
    status,code=request('GET','/js/pages/staging.js')
    assert status==200 and 'renderCorpus' in code and 'analysisCatalogHtml(catalog)' in code
    assert 'autoDecompose' not in code and 'manualDecompose' not in code
