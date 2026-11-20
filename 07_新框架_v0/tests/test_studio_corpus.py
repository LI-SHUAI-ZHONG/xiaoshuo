"""Source boundaries, whole-book graph, immutable reviews and method provenance."""
from copy import deepcopy
import json

import pytest

from nw.studio.library import LibraryService
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_contract import normalize_document
from nw.studio.corpus_index import source_units,range_coverage
from nw.studio.corpus_methods import manual_method
from corpus_fixture import SOURCE,make_book,start_analysis,wait_job,runtime,CorpusModel


@pytest.fixture
def library(tmp_path):return LibraryService(tmp_path/'[FAKE]-corpus')


def test_literal_index_covers_preamble_volumes_and_chapters_without_gaps():
    text='[FAKE] 前置\n# 第一卷\n卷首\n## 第一章\n甲\n## 第二章\n乙\n# 第二卷\n## 第三章\n丙'
    units=source_units(text);chapters=[u for u in units if u['level']=='chapter']
    assert range_coverage(chapters,len(text))['complete_imported_text']
    assert len([u for u in units if u['level']=='volume'])==2
    assert any(u['boundary_basis']=='analyst_inference' for u in units)
    assert all(text[u['start']:u['end']] for u in units)


def test_getting_uninitialized_structure_never_creates_a_fake_analysis(library):
    book=make_book(library);row=library.get_corpus(book['id'])
    assert not row['initialized'] and not row['body']['events']
    with library.connect() as conn:assert conn.execute('SELECT COUNT(*) FROM corpus_structures').fetchone()[0]==0


def test_complete_staged_pipeline_uses_global_basis_before_detail_and_does_not_auto_approve(library,monkeypatch):
    book,job,provider=start_analysis(library,monkeypatch)
    assert job['status']=='completed',job['error']
    phases=[c['phase'] for c in provider.calls]
    assert phases==['survey','survey','overview','detail','detail']+['relations']*7
    details=[p for p in provider.calls if p['phase']=='detail']
    assert all(p['global_overview']['mainline'] and p['global_basis_sha256'] and p['overview_events'] for p in details)
    row=library.get_corpus(book['id'])
    assert row['status']=='draft' and not row['available'] and row['issues']==[]
    assert len(row['body']['threads'])==7 and len(row['body']['domains'])==7
    assert {e['granularity'] for e in row['body']['events']}=={'overview','detail'}
    assert range_coverage(row['coverage']['survey_ranges'],len(SOURCE))['complete_imported_text']
    assert range_coverage(row['coverage']['detail_ranges'],len(SOURCE))['complete_imported_text']
    assert all(c['status']=='completed' for c in job['calls'])
    call=library.corpus_call_record(book['id'],job['id'],1)
    assert SOURCE.startswith(call['input']['messages'][-1]['content']) is False
    assert json.loads(call['input']['messages'][-1]['content'])['source_text'] in SOURCE
    assert call['output']['finish_reason']=='complete'
    assert library.list_methods()['total']==0


def test_approved_structure_can_derive_independent_draft_methods_with_frozen_basis(library,monkeypatch):
    book,job,provider=start_analysis(library,monkeypatch)
    assert job['status']=='completed',job['error']
    approved=library.review_corpus(book['id'],{'version':1,'decision':'approve','note':'[FAKE] 核对完整结构'})
    assert approved['available']
    task=library.start_corpus_job(book['id'],{'kind':'methods','options':{'thread_ids':['T_hook']}})
    result=wait_job(library,book['id'],task['id'])
    assert result['status']=='completed',result['error']
    methods=library.list_methods()['methods'];assert len(methods)==1
    method=methods[0];assert method['status']=='draft' and method['structure_origin']['structure_version']==1
    assert method['structure_origin']['basis']['thread_ids']==['T_hook']
    approved_method=library.review_method(method['id'],{'version':1,'decision':'approve','note':'[FAKE] 独立方法审核'})
    assert approved_method['available']
    changed=deepcopy(approved['body']);changed['overview']['mainline']+='[FAKE] 修订'
    revised=library.save_corpus(book['id'],{'body':changed,'expected_version':1})
    assert library.get_method(method['id'])['available']  # pending structure revision keeps active approval
    library.review_corpus(book['id'],{'version':revised['version'],'decision':'approve','note':'[FAKE] 审核新结构'})
    old=library.get_method(method['id'])
    assert not old['available'] and old['status']=='source_unavailable'
    assert old['body_sha256']==method['body_sha256']


def test_partial_text_cannot_be_promoted_to_complete_book_methods(library,monkeypatch):
    book,job,_=start_analysis(library,monkeypatch,extent='excerpt')
    assert job['status']=='completed',job['error']
    with pytest.raises(ValueError,match='确认当前覆盖限制'):
        library.review_corpus(book['id'],{'version':1,'decision':'approve','note':'[FAKE] 仅摘录'})
    library.review_corpus(book['id'],{'version':1,'decision':'approve','note':'[FAKE] 仅当前摘录','accept_limitations':True})
    method=manual_method(library,book['id'],{'version':1,'thread_ids':['T_main_plot']})
    assert method['issues'] and not method['available']
    body=deepcopy(method['body']);body['scopes']=['book']
    saved=library.save_method({'body':body,'expected_version':1},method['id'])
    assert saved['structure_origin'] and any('不完整' in i['message'] for i in saved['source_issues'])


@pytest.mark.parametrize('change,message',[
    (lambda b:b['links'][0].update(source='fabricated'),'端点'),
    (lambda b:b['links'][0].update(evidence_ids=b['links'][0]['evidence_ids'][:1]),'各自证据'),
    (lambda b:b['threads'].append({**b['threads'][0]}),'标识重复'),
    (lambda b:b['events'][-1].update(parent_event_ids=[]),'总览节点'),
    (lambda b:b['characters'][0].update(canonical_id=b['characters'][0]['id']),'循环'),
])
def test_dangling_and_false_graph_relationships_are_not_approvable(library,monkeypatch,change,message):
    book,job,_=start_analysis(library,monkeypatch)
    assert job['status']=='completed',job['error']
    row=library.get_corpus(book['id']);body=deepcopy(row['body']);change(body)
    new=library.save_corpus(book['id'],{'body':body,'expected_version':1})
    assert any(message in issue['message'] for issue in new['issues'])
    with pytest.raises(ValueError,match='尚不能批准'):
        library.review_corpus(book['id'],{'version':2,'decision':'approve','note':'[FAKE] 不得通过'})


def test_false_quotation_is_rejected_before_any_version_is_written(library):
    book=make_book(library);body=library.get_corpus(book['id'])['body']
    body['evidence']=[{'id':'E1','start':0,'end':8,'quote':'[FAKE] 错误引文','explanation':'[FAKE] 必须失败'}]
    with pytest.raises(ValueError,match='证据'):
        library.save_corpus(book['id'],{'body':body,'expected_version':0})
    assert not library.get_corpus(book['id'])['initialized']


def test_manual_read_claim_is_explicit_and_versions_never_overwrite(library,monkeypatch):
    book,job,_=start_analysis(library,monkeypatch)
    assert job['status']=='completed',job['error']
    old=library.get_corpus(book['id']);body=deepcopy(old['body'])
    body['overview']['mainline']+='[FAKE] 人工修改'
    new=library.save_corpus(book['id'],{'body':body,'expected_version':1})
    assert new['version']==2 and library.get_corpus(book['id'],1)['body_sha256']==old['body_sha256']
    with pytest.raises(ValueError,match='已更新'):
        library.save_corpus(book['id'],{'body':body,'expected_version':1})
