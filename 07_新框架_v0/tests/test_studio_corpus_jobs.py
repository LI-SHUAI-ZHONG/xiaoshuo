"""Interrupted calls, budget stops, source changes and cancellation are explicit."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from nw.call_control import execution_lock
from nw.config import ConfigRequired
from nw.studio.library import LibraryService
from nw.studio.library_util import encode
from nw.studio.corpus_jobs import recover_corpus_jobs
from nw.studio.corpus_calls import artifact
from corpus_fixture import SOURCE,CorpusModel,make_book,runtime,start_analysis,wait_job


@pytest.fixture
def library(tmp_path):return LibraryService(tmp_path/'[FAKE]-jobs')


def test_missing_real_configuration_never_calls_a_fallback_model(library):
    book=make_book(library)
    with pytest.raises(ConfigRequired,match='CONFIG_REQUIRED'):
        library.start_corpus_job(book['id'],{'options':{'extent':'complete','note':'[FAKE] 完整性'}})
    assert library.list_corpus_jobs(book['id'])['jobs']==[]


def test_unknown_call_requires_explicit_retry_and_keeps_completed_work(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=2
    book,job,_=start_analysis(library,monkeypatch,provider)
    assert job['status']=='paused' and job['calls'][-1]['status']=='unknown'
    first=library.corpus_call_record(book['id'],job['id'],1)
    first_bytes=artifact(library,first['record']['input_path']).read_bytes()
    library.control_corpus_job(book['id'],job['id'],{'action':'resume'})
    stopped=wait_job(library,book['id'],job['id'])
    assert stopped['status']=='paused' and len(provider.calls)==2
    provider.fail_at=None
    library.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True})
    finished=wait_job(library,book['id'],job['id'])
    assert finished['status']=='completed',finished['error']
    assert len(provider.calls)==19 and len(finished['calls'])==19
    assert finished['calls'][1]['status']=='unknown' and finished['calls'][2]['call_key']=='survey:1'
    assert artifact(library,first['record']['input_path']).read_bytes()==first_bytes


def test_completed_output_file_is_recovered_without_another_request(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=2;initial={}
    def capture(payload):
        if len(provider.calls)==1:
            with library.connect() as conn:initial['state']=conn.execute('SELECT state_json FROM corpus_jobs').fetchone()[0]
    provider.on_call=capture
    book,job,_=start_analysis(library,monkeypatch,provider)
    assert job['status']=='paused'
    with library.connect() as conn:
        conn.execute('UPDATE corpus_jobs SET state_json=? WHERE id=?',(initial['state'],job['id']))
        conn.execute("UPDATE corpus_calls SET status='sending',result_json=NULL WHERE job_id=? AND seq=1",(job['id'],))
    library.control_corpus_job(book['id'],job['id'],{'action':'resume'})
    stopped=wait_job(library,book['id'],job['id'])
    assert stopped['status']=='paused' and len(provider.calls)==2
    assert stopped['calls'][0]['status']=='completed'
    assert stopped['progress']['survey_cursor']==1


def test_invalid_model_result_is_never_published_or_automatically_retried(library,monkeypatch):
    provider=CorpusModel();provider.invalid_at=1
    book,job,_=start_analysis(library,monkeypatch,provider)
    assert job['status']=='failed' and job['calls'][0]['status']=='invalid'
    assert not library.get_corpus(book['id'])['initialized']
    library.control_corpus_job(book['id'],job['id'],{'action':'resume'})
    assert wait_job(library,book['id'],job['id'])['status']=='paused' and len(provider.calls)==1


def test_input_budget_stops_before_http_and_can_be_increased(library,monkeypatch):
    provider=CorpusModel();monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider))
    book=make_book(library,'# 第一章\n[FAKE] '+('仅为预算测试。'*950))
    task=library.start_corpus_job(book['id'],{'options':{'extent':'excerpt','note':'[FAKE] 预算测试文本','max_input_chars':8000}})
    job=wait_job(library,book['id'],task['id'])
    assert job['status']=='paused' and 'CONTEXT_TOO_LARGE' in job['error']
    assert not provider.calls and not job['calls']
    assert list((library.root/'corpus_calls'/job['id']).glob('blocked_*.input.json'))
    library.control_corpus_job(book['id'],job['id'],{'action':'resume','options':{'max_input_chars':64000}})
    done=wait_job(library,book['id'],job['id'])
    assert done['status']=='completed',done['error']


def test_call_limit_below_known_minimum_never_starts(library,monkeypatch):
    provider=CorpusModel();monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider));book=make_book(library)
    with pytest.raises(ValueError,match='最低需求'):
        library.start_corpus_job(book['id'],{'options':{'extent':'complete','note':'[FAKE] 范围','max_calls':1}})
    assert not provider.calls and not library.list_corpus_jobs(book['id'])['jobs']


def test_pause_and_cancel_save_records_but_never_publish(library,monkeypatch):
    provider=CorpusModel();book=make_book(library)
    def pause(payload):
        if len(provider.calls)==1:
            job=library.list_corpus_jobs(book['id'])['jobs'][0]
            library.control_corpus_job(book['id'],job['id'],{'action':'pause'})
    provider.on_call=pause
    _,job,_=start_analysis(library,monkeypatch,provider)
    assert job['status']=='paused' and job['progress']['survey_cursor']==1
    library.control_corpus_job(book['id'],job['id'],{'action':'cancel'})
    assert library.get_corpus_job(book['id'],job['id'])['status']=='cancelled'
    assert not library.get_corpus(book['id'])['initialized']
    assert len(provider.calls)==1


def test_restart_recovers_abandoned_jobs_but_never_interrupts_live_lock(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=1
    book,job,_=start_analysis(library,monkeypatch,provider)
    with library.connect() as conn:conn.execute("UPDATE corpus_jobs SET status='running' WHERE id=?",(job['id'],))
    with execution_lock(SimpleNamespace(directory=library.root),f'decompose:{book["id"]}') as acquired:
        assert acquired
        recover_corpus_jobs(library)
        assert library.get_corpus_job(book['id'],job['id'])['status']=='running'
    reopened=LibraryService(library.workspace)
    assert reopened.get_corpus_job(book['id'],job['id'])['status']=='paused'


def test_source_change_and_stale_structure_block_resume(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=1
    book,job,_=start_analysis(library,monkeypatch,provider)
    original=library.get_corpus(book['id'])['body']
    library.save_corpus(book['id'],{'body':original,'expected_version':0})
    with pytest.raises(ValueError,match='结构已修改'):
        library.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True})
    assert len(provider.calls)==1


def test_runtime_change_cannot_mix_completed_results(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=1
    book,job,_=start_analysis(library,monkeypatch,provider)
    changed=runtime();changed.model='[FAKE] another-model'
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(changed,provider))
    with pytest.raises(ValueError,match='模型配置已改变'):
        library.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True})
    assert len(provider.calls)==1


def test_pending_window_keeps_its_exact_input_across_resume(library,monkeypatch):
    provider=CorpusModel();provider.fail_at=3
    book,job,_=start_analysis(library,monkeypatch,provider)
    assert job['phase']=='overview' and job['status']=='paused'
    before=library.corpus_call_record(book['id'],job['id'],3)['input']['messages']
    provider.fail_at=None
    library.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True,'options':{'max_input_chars':70000}})
    final=wait_job(library,book['id'],job['id'])
    assert final['status']=='completed',final['error']
    after=library.corpus_call_record(book['id'],job['id'],4)['input']['messages']
    assert before==after


def test_cancel_during_a_call_does_not_publish_the_late_result(library,monkeypatch):
    provider=CorpusModel();book=make_book(library)
    def cancel(payload):
        job=library.list_corpus_jobs(book['id'])['jobs'][0]
        library.control_corpus_job(book['id'],job['id'],{'action':'cancel'})
    provider.on_call=cancel
    _,job,_=start_analysis(library,monkeypatch,provider)
    assert job['status']=='cancelled' and len(job['calls'])==1
    assert job['calls'][0]['status']=='completed' and not library.get_corpus(book['id'])['initialized']


def test_long_global_and_relation_windows_keep_context_and_cover_every_range(library,monkeypatch):
    provider=CorpusModel();monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),provider))
    text=''.join(f'# 第{i}章\n[FAKE] 第{i}段不同观察，用于验证跨窗口整合。\n' for i in range(1,7))
    book=make_book(library,text)
    started=library.start_corpus_job(book['id'],{'options':{'extent':'complete','note':'[FAKE] 多窗口测试','max_input_chars':8500}})
    job=wait_job(library,book['id'],started['id'])
    assert job['status']=='paused' and 'CONTEXT_TOO_LARGE' in job['error']
    library.control_corpus_job(book['id'],job['id'],{'action':'resume','options':{'max_input_chars':64000}})
    job=wait_job(library,book['id'],job['id'])
    assert job['status']=='completed',job['error']
    global_calls=[c for c in provider.calls if c['phase']=='overview']
    assert len(global_calls)>1
    assert any(c['open_threads'] or c['closed_thread_index'] for c in global_calls[1:])
    structure=library.get_corpus(book['id'])
    assert structure['statistics']['survey']['complete_imported_text']
    assert structure['statistics']['detail']['complete_imported_text']
    assert len(structure['body']['domains'])==12
