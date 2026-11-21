import pytest

from corpus_fixture import CorpusModel, runtime, start_analysis, wait_job
from nw.studio import corpus_jobs
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_roster import canonical_person
from nw.studio.library import LibraryService


def test_roster_windows_and_original_citations_follow_each_chapter_and_person(tmp_path, monkeypatch):
    lib=LibraryService(tmp_path)
    book,job,model=start_analysis(lib,monkeypatch)
    assert job['status']=='completed',job['error']
    windows=[c for c in model.calls if c.get('domain')=='cast_roster']
    assert len(windows)==2
    record=lib.get_corpus(book['id'])
    body=record['body']
    rows=[r for r in body['threads'] if r['domain']=='cast_roster']
    assert [r['node_ids'][0] for r in rows]==[w['events'][0]['id'] for w in windows]
    subject=rows[0]['characters'][0]
    alias={**body['characters'][0],'id':'OtherName','name':'[FAKE] 另一个称呼','canonical_id':subject}
    body['characters'].append(alias)
    rows[1]['characters']=[alias['id']]
    people={p['id']:p for p in body['characters']}
    assert {canonical_person(r['characters'][0],people) for r in rows}=={subject}
    assert graph_issues(body,len(lib.get_staging(book['id'])['text']),record['coverage'])==[]
    citation=rows[1]['details']['appearance_evidence']
    rows[1]['details']['appearance_evidence']=rows[0]['details']['appearance_evidence']
    assert any('共同引用的原句' in e['message'] for e in graph_issues(body,body['units'][0]['end']))
    rows[1]['details']['appearance_evidence']=citation
    rows[1]['characters']=['OtherName']
    alias['canonical_id']=None
    rows[1]['details']['presence']='mentioned'
    assert any('仅提及也须' in e['message'] for e in graph_issues(body,body['units'][0]['end']))
    # Distinct alias in the passage and an independently sourced personal quote can each identify the subject.
    alias['name']='甲'
    assert not any('仅提及也须' in e['message'] for e in graph_issues(body,body['units'][0]['end']))
    alias['name']='另一个称呼'
    alias['evidence_ids'].append(citation)
    assert not any('仅提及也须' in e['message'] for e in graph_issues(body,body['units'][0]['end']))
    rows[1]['details']['presence']='onstage'
    assert any('实际出场须指向' in e['message'] for e in graph_issues(body,body['units'][0]['end']))
    body['threads'].remove(rows[1])
    assert any('尚未逐项核对阵容' in e['message'] for e in graph_issues(body,body['units'][0]['end'],record['coverage']))


def test_paused_v4_replays_without_cast_roster_or_using_new_budget(tmp_path,monkeypatch):
    lib=LibraryService(tmp_path)
    model=CorpusModel()
    model.fail_at=2
    current=corpus_jobs.empty_document
    with monkeypatch.context() as old:
        old.setattr(corpus_jobs,'empty_document',lambda *a:{**current(*a),'schema_version':4})
        book,job,_=start_analysis(lib,old,model,max_calls=17)
    assert job['status']=='paused'
    model.fail_at=None
    monkeypatch.setattr(lib,'_corpus_runtime',lambda:(runtime(),model))
    lib.control_corpus_job(book['id'],job['id'],{'action':'resume','retry_failed':True})
    done=wait_job(lib,book['id'],job['id'])
    assert done['status']=='completed',done['error']
    assert done['calls_used']==17 and done['structure_schema_version']==4
    assert 'cast_roster' not in {c.get('domain') for c in model.calls}
    with pytest.raises(ValueError,match='历史拆解规格'):
        lib.review_corpus(book['id'],{'version':1,'decision':'approve','note':'[FAKE] 旧版不能刷新为现行'})
