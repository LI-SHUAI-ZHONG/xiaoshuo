"""New world observations require source evidence without invalidating seven-domain books."""
from copy import deepcopy
import pytest

from corpus_fixture import CorpusModel, runtime, start_analysis, wait_job
from nw.studio import corpus_jobs
from nw.studio.corpus_catalog import corpus_catalog
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_methods import manual_method, prepare_method
from nw.studio.library import LibraryService


@pytest.fixture
def analysis(tmp_path, monkeypatch):
    library=LibraryService(tmp_path / 'isolated-world-corpus')
    book, job, provider=start_analysis(library,monkeypatch)
    assert job['status']=='completed',job['error']
    return library, book['id'], provider


def approve(library, book, version):
    return library.review_corpus(book,{'version':version,'decision':'approve','note':'[FAKE] 核对隔离结构。'})


def derive(library, book, thread):
    job=library.start_corpus_job(book,{'kind':'methods','options':{'thread_ids':[thread]}})
    return wait_job(library,book,job['id'])


def test_verified_rule_requires_an_effect_and_can_be_absent(analysis):
    library, book, provider=analysis
    saved=library.get_corpus(book)
    assert saved['body']['schema_version']==5
    assert saved['statistics']['thread_counts']['world_rules']==1
    assert [x['domain'] for x in provider.calls if x['phase']=='relations'].count('world_rules')==1
    body=deepcopy(saved['body'])
    next(t for t in body['threads'] if t['domain']=='world_rules')['details']['decision_effect']=''
    assert any(i['severity']=='error' and '实际后果' in i['message'] for i in graph_issues(body,body['units'][0]['end']))
    body['threads']=[t for t in body['threads'] if t['domain']!='world_rules']
    body['links']=[link for link in body['links'] if link['thread_id']!='T_world_rules']
    next(d for d in body['domains'] if d['domain']=='world_rules').update(
        status='not_observed',explanation='[FAKE] 当前证据没有呈现可判断的规则。')
    absent=library.save_corpus(book,{'expected_version':1,'body':body})
    assert approve(library,book,absent['version'])['available']
    with pytest.raises(ValueError,match='已批准结构中的线索'):
        derive(library,book,'T_world_rules')


def test_world_evidence_and_design_handoff_survive_method_revisions(analysis):
    library, book, _=analysis
    structure=approve(library,book,1)
    manual=manual_method(library,book,{'version':1,'thread_ids':['T_world_rules']})
    assert manual['body']['tasks']==['world_rules'] and not manual['available']
    assert derive(library,book,'T_hook')['status']=='completed'
    hook=next(r for r in library.list_methods()['methods'] if r['body']['tasks']==['hook'])
    body=deepcopy(hook['body'])
    body['tasks']=['world_rules']
    body['prerequisites'][0]['input_kind']='type_adaptation'
    body['outputs'][0].update(stage='world_design',field='members',artifact_kind='world')
    body['evidence']=manual['body']['evidence']
    candidate={'basis':manual['structure_origin']['basis'],'body':body}
    assert prepare_method(library,structure,candidate)['body']['outputs'][0]['artifact_kind']=='world'
    for field,value,reason in (
        ('type_tags',['GENRE_QIHUAN'],'已确认类型'),
        ('evidence',body['evidence'][:1],'两端证据'),
        ('downstream',[{**body['downstream'][0],'consumer':'review'}],'下游|步骤如何使用')):
        broken=deepcopy(candidate)
        broken['body'][field]=value
        with pytest.raises(ValueError,match=reason):
            prepare_method(library,structure,broken)
    with pytest.raises(ValueError,match='已核实的世界规则线索'):
        prepare_method(library,structure,{'body':body,'basis':hook['structure_origin']['basis']})
    revised=library.save_method({'body':body,'expected_version':1},manual['id'])
    assert not revised['issues'] and not revised['source_issues']
    body['evidence']=body['evidence'][:1]
    bad=library.save_method({'body':body,'expected_version':2},manual['id'])
    assert any('两端证据' in row['message'] for row in bad['source_issues'])
    with pytest.raises(ValueError,match='尚不能批准'):
        library.review_method(manual['id'],{'version':3,'decision':'approve','note':'[FAKE] 缺少原文依据。'})


def test_legacy_method_replays_but_new_work_requires_a_current_review(tmp_path,monkeypatch):
    from nw.production_methods.sources import MethodReader, matching_methods
    from nw.studio import corpus_catalog as catalog

    library=LibraryService(tmp_path)
    current=corpus_jobs.empty_document
    with monkeypatch.context() as initial:
        initial.setattr(corpus_jobs,'empty_document',lambda *args:{**current(*args),'schema_version':1})
        book,job,provider=start_analysis(library,initial)
    assert job['status']=='completed',job['error']
    book=book['id']
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider))
    row=library.get_corpus(book)
    frozen=row['body_sha256']
    # Seed decisions and a frozen reference from when the seven-domain edition was current.
    reader=MethodReader(tmp_path)
    with monkeypatch.context() as earlier:
        earlier.setattr(catalog,'SCHEMA_VERSION',1)
        earlier.setattr(corpus_jobs,'empty_document',lambda *args:{**current(*args),'schema_version':1})
        old=approve(library,book,row['version'])
        assert old['available'] and len(old['statistics']['thread_counts'])==7
        task=derive(library,book,'T_hook')
        assert task['status']=='completed' and task['runtime']['pipeline_version']=='corpus-v1'
        approved_method=library.review_method(library.list_methods()['methods'][0]['id'],
            {'version':1,'decision':'approve','note':'[FAKE] 七职责版本的原方法。'})
        pin=reader.snapshot(approved_method)
    reader.verify(pin)
    assert library.get_method(approved_method['id'])['structure_schema_version']==1
    assert not library.get_method(approved_method['id'])['current_for_production']
    assert not matching_methods(reader,['GENRE_XUANYI'])
    with pytest.raises(ValueError,match='历史拆解规格'):
        derive(library,book,'T_hook')
    with pytest.raises(ValueError,match='历史拆解规格'):
        manual_method(library,book,{'version':row['version'],'thread_ids':['T_hook']})
    assert 'world_rules' not in corpus_catalog(1)['domains']
    manual=library.edit_corpus_record(book,{'expected_version':row['version'],'section':'overview',
                                           'row':row['body']['overview']})
    assert manual['body']['schema_version']==5 and manual['approved_version']==row['version']
    assert manual['coverage'].get('detail_ranges',[]) == [] and not manual['coverage']['reviewed_units']
    assert library.get_corpus(book,row['version'])['statistics']['detail']['complete_imported_text']
    with pytest.raises(ValueError,match='结构尚不能批准'):
        approve(library,book,manual['version'])
    assert library.get_method(approved_method['id'])['available']
    rerun=library.start_corpus_job(book,{'options':{'extent':'complete','note':'[FAKE] 从原文重新分析。'}})
    fresh=wait_job(library,book,rerun['id'])
    assert fresh['status']=='completed' and fresh['runtime']['pipeline_version']=='corpus-v5'
    assert library.get_corpus(book)['body']['schema_version']==5
    assert library.get_corpus(book,row['version'])['body_sha256']==frozen
    assert library.get_method(approved_method['id'])['available']
    approve(library,book,library.get_corpus(book)['version'])
    job=derive(library,book,'T_hook')
    assert job['status']=='completed',job['error']
    new_method=job['progress']['published_methods'][0]['id']
    library.review_method(new_method,{'version':1,'decision':'approve','note':'[FAKE] 已核对现行结构。'})
    assert [m['id'] for m,_ in matching_methods(reader,['GENRE_XUANYI'])]==[new_method]


@pytest.mark.parametrize('request_body', [{}, {'mode':'model'}])
def test_automatic_decompose_entry_runs_current_full_structure(tmp_path,monkeypatch,request_body):
    from corpus_fixture import make_book

    library=LibraryService(tmp_path)
    book=make_book(library)['id']
    model=CorpusModel()
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    job=library.decompose_book(book,request_body)
    completed=wait_job(library,book,job['id'])
    assert completed['status']=='completed',completed['error']
    assert completed['structure_schema_version']==5
    assert {c['domain'] for c in model.calls if c['phase']=='relations'}==set(corpus_catalog()['domains'])
    assert library.get_staging(book)['items']==[]


def test_resume_keeps_legacy_schema_and_its_original_call_budget(tmp_path,monkeypatch):
    library=LibraryService(tmp_path / 'isolated-legacy-checkpoint')
    provider=CorpusModel()
    provider.fail_at=2
    new_document=corpus_jobs.empty_document

    def legacy_document(*args):
        body=new_document(*args)
        body['schema_version']=1
        return body

    with monkeypatch.context() as initial:
        initial.setattr(corpus_jobs,'empty_document',legacy_document)
        book, job, _=start_analysis(library,initial,provider,max_calls=13)
    assert job['status']=='paused'
    first=library.corpus_call_record(book['id'],job['id'],1)['input']
    assert 'world_rules' not in first['messages'][0]['content']
    provider.fail_at=None
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider))
    library.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True})
    resumed=wait_job(library,book['id'],job['id'])
    assert resumed['status']=='completed',resumed['error']
    assert resumed['calls_used']==13 and resumed['runtime']['pipeline_version']=='corpus-v1'
    assert len(library.get_corpus(book['id'])['body']['domains'])==7
    assert library.corpus_call_record(book['id'],job['id'],1)['input']==first
