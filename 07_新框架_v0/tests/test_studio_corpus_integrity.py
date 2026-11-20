"""Source drift, atomic derivation and Git-managed complete data restoration."""
from copy import deepcopy

import pytest

from nw.studio.library import LibraryService
from nw.studio.corpus_methods import manual_method,prepare_method
from nw.studio.corpus_merge import resolve_fragment
from nw.studio.repository_data import snapshot,restore
from corpus_fixture import make_book,start_analysis,wait_job,CorpusModel,SOURCE


@pytest.fixture
def library(tmp_path):return LibraryService(tmp_path/'[FAKE]-integrity')


def approve(library,monkeypatch):
    book,job,provider=start_analysis(library,monkeypatch)
    assert job['status']=='completed',job['error']
    library.review_corpus(book['id'],{'version':1,'decision':'approve','note':'[FAKE] 结构核对'})
    return book,provider


def test_source_file_change_invalidates_structure_and_prevents_paid_resume(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=2
    book,job,_=start_analysis(library,monkeypatch,provider)
    raw=library._staging_row(book['id'])
    from pathlib import Path
    path=Path(raw['file_path'])
    if not path.is_absolute():path=library.root/path
    path.write_text(SOURCE+'[FAKE] 外部修改',encoding='utf-8')
    provider.fail_at=None
    with pytest.raises(ValueError,match='(校验|改变|完整性|原文)'):
        library.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True})
    assert len(provider.calls)==2


def test_withdrawn_source_cannot_publish_or_remain_available(library,monkeypatch):
    book,_=approve(library,monkeypatch)
    method=manual_method(library,book['id'],{'version':1,'thread_ids':['T_hook']})
    with library.connect() as conn:conn.execute("UPDATE staging_books SET status='rejected' WHERE id=?",(book['id'],))
    assert not library.get_corpus(book['id'])['available']
    method=library.get_method(method['id'])
    assert not method['available'] and any(i['field']=='origin' for i in method['source_issues'])
    with pytest.raises(ValueError,match='来源有效'):
        manual_method(library,book['id'],{'version':1,'thread_ids':['T_hook']})


def test_method_job_does_not_publish_a_partial_candidate_batch(library,monkeypatch):
    book,provider=approve(library,monkeypatch);provider.invalid_at=len(provider.calls)+2
    before=len(provider.calls)
    with pytest.raises(ValueError,match='请选择1–20'):
        library.start_corpus_job(book['id'],{'kind':'methods','options':{}})
    assert len(provider.calls)==before
    started=library.start_corpus_job(book['id'],{'kind':'methods','options':{'thread_ids':['T_hook','T_pacing']}})
    failed=wait_job(library,book['id'],started['id'])
    assert failed['status']=='failed' and failed['progress']['method_cursor']==1
    assert library.list_methods()['total']==0
    assert library.get_corpus(book['id'])['available']


def test_method_revisions_keep_origin_and_cannot_borrow_other_threads(library,monkeypatch):
    book,provider=approve(library,monkeypatch)
    started=library.start_corpus_job(book['id'],{'kind':'methods','options':{'thread_ids':['T_hook']}})
    completed=wait_job(library,book['id'],started['id']);assert completed['status']=='completed'
    method=library.list_methods()['methods'][0];body=deepcopy(method['body']);body['title']+='[FAKE] 修订'
    revised=library.save_method({'body':body,'expected_version':1},method['id'])
    assert revised['version']==2 and revised['structure_origin']['basis']==method['structure_origin']['basis']
    assert revised['structure_origin']['structure_version']==1
    candidate=deepcopy({'body':body,'basis':method['structure_origin']['basis']})
    structure=library.get_corpus(book['id'])
    candidate['basis']['link_ids']=[next(l['id'] for l in structure['body']['links'] if l['thread_id']=='T_pacing')]
    with pytest.raises(ValueError,match='对应所选线索'):
        prepare_method(library,structure,candidate)


def test_source_quotes_and_offsets_count_unicode_characters(library):
    text='# 第一章\n[FAKE] 🧪 原文证据\n';book=make_book(library,text)
    initialized=library.initialize_corpus(book['id'],{'extent':'excerpt','note':'[FAKE] Unicode测试'})
    quote='🧪 原文证据';start=text.index(quote)
    row=library.edit_corpus_record(book['id'],{'expected_version':initialized['version'],'section':'evidence',
        'row':{'id':'E_unicode','start':start,'end':start+len(quote),'quote':quote,'explanation':'[FAKE] 按字符定位'}})
    assert row['body']['evidence'][0]['end']==text.index('\n',start)


def test_git_snapshot_restores_structures_methods_reviews_and_full_call_files(library,monkeypatch,tmp_path):
    book,_=approve(library,monkeypatch)
    manual=manual_method(library,book['id'],{'version':1,'thread_ids':['T_hook']})
    before=library.get_corpus(book['id']);ident=before['jobs'][0]['id']
    original_call=library.corpus_call_record(book['id'],ident,1)
    folder=tmp_path/'[FAKE]-git-managed';manifest=snapshot(library.workspace,folder)
    assert any('/corpus_calls/' in e['path'] for e in manifest['entries'])
    target=tmp_path/'[FAKE]-other-client';target.mkdir()
    restore(folder,target);restored=LibraryService(target)
    actual=restored.get_corpus(book['id'])
    assert actual['available'] and actual['body_sha256']==before['body_sha256']
    assert actual['review']==before['review'] and actual['coverage']==before['coverage']
    assert restored.get_method(manual['id'])['structure_origin']==library.get_method(manual['id'])['structure_origin']
    call=restored.corpus_call_record(book['id'],ident,1)
    assert call['input']==original_call['input'] and call['output']==original_call['output']
    with restored.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM corpus_calls').fetchone()[0]==13


def test_resume_cannot_change_frozen_chunking_or_source_extent(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=1
    book,job,_=start_analysis(library,monkeypatch,provider)
    for options in ({'chunk_chars':1000},{'extent':'excerpt'}):
        with pytest.raises(ValueError,match='只可调整'):
            library.control_corpus_job(book['id'],job['id'],{'action':'resume','options':options})
    assert len(provider.calls)==1


@pytest.mark.parametrize('wrong_unit',[True,False])
def test_reading_fragment_cannot_reuse_another_range_as_current_observation(library,monkeypatch,wrong_unit):
    book,_=approve(library,monkeypatch);doc=library.get_corpus(book['id'])['body']
    chapters=[u for u in doc['units'] if u['level']=='chapter']
    event=deepcopy(next(e for e in doc['events'] if e['granularity']=='overview'))
    event['id']='BAD_Event';chapter=chapters[1] if wrong_unit else chapters[0]
    span={'unit_id':chapter['id'],'start':chapter['start']+(0 if wrong_unit else 3),'end':chapter['end']}
    message='属于当前读取' if wrong_unit else '当前原文片段'
    with pytest.raises(ValueError,match=message):
        resolve_fragment({'events':[event]},doc,SOURCE,span=span,prefix='BAD',phase='survey')


@pytest.mark.parametrize('action',['pause','cancel'])
def test_completed_publication_wins_over_a_stale_control_request(library,monkeypatch,action):
    book,job,_=start_analysis(library,monkeypatch);assert job['status']=='completed'
    original=library.get_corpus_job;old=original(book['id'],job['id']);old['status']='running'
    monkeypatch.setattr(library,'get_corpus_job',lambda *_:old)
    with pytest.raises(ValueError,match='结果和完成状态保留'):
        library.control_corpus_job(book['id'],job['id'],{'action':action})
    assert original(book['id'],job['id'])['status']=='completed'
    assert library.get_corpus(book['id'])['version']==1
