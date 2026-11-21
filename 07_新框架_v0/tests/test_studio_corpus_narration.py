"""Trace two differently sourced passages through the real corpus job and method review."""
from copy import deepcopy
import json

import pytest

from corpus_fixture import CorpusModel, make_book, runtime, thread, wait_job
from nw.studio.corpus_catalog import corpus_catalog
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_contract import normalize_document
from nw.studio.corpus_methods import prepare_method
from nw.studio.library import LibraryService


PAST='昨夜西闸已破。'
NOW='门房心想，难道东闸也破了？“拿船来！”小棠听见喊声，抱起绳圈。'
TEXT=f'[FAKE] {PAST}今晨又传来锣声。{NOW}'


class PassageModel(CorpusModel):
    def generate(self,messages,**params):
        result=super().generate(messages,**params)
        payload=self.calls[-1]
        phase=payload['phase']
        raw=json.loads(result.text)
        if phase=='survey':
            keeper=raw['characters'][0]
            keeper['name']='门房'
            raw['characters'].append({**keeper,'id':keeper['id']+'_second','name':'小棠'})
        elif phase=='detail':
            self.detail_observations(raw,payload)
        elif phase=='relations' and payload['domain']=='narration':
            assert len(payload['narration_observations'])==2
            raw={'domains':raw['domains']}
        elif phase=='methods':
            body=raw['methods'][0]['body']
            body.update(title='先报已知，再呈现他人的疑问与回应',tasks=['narration'])
            body['outputs'][0].update(stage='expression_design',field='guidance',description='当下人物如何听见、回应')
            body['downstream']=[{'output_key':'o1','consumer':c,'usage':'按当场信息来源写出或核对他人的行动'}
                                for c in ('writer','review')]
        result.text=json.dumps(raw,ensure_ascii=False)
        return result

    @staticmethod
    def detail_observations(raw,payload):
        prefix=payload['prefix']
        prototype=raw['events'][0]
        known=[p['id'] for p in payload['known_characters']]
        raw.update(events=[],threads=[],evidence=[])
        for number,quote in enumerate((PAST,NOW)):
            eid=f'{prefix}_q{number}'
            event={**prototype,'id':f'{prefix}_event{number}','characters':known if number else [],
                   'evidence_ids':[eid],'summary':'门房怀疑、小棠听见催船' if number else '西闸昨夜已破'}
            raw['events'].append(event)
            raw['evidence'].append({'id':eid,'quote':quote,'explanation':'对应的原句'})
            observation=thread('narration',[event],None,[eid])
            observation.update(id=f'{prefix}_voice{number}',characters=event['characters'])
            observation['details']={
                'time_order':'今晨，接在昨夜背景之后' if number else '先交代昨夜已经发生的事',
                'presentation':'门房的内心疑问转入喊话和回应' if number else '叙述者一句压缩往事',
                'voice_access':'门房私下怀疑，小棠只听到喊话' if number else '叙述者告知读者',
                'claim_status':'attributed' if number else 'stated',
                'causal_basis':'喊话引出小棠拿绳' if number else '',
                'character_response':'小棠拿绳；东闸是否真破仍未知' if number else '',
                'reader_effect':'读者知道门房在猜，尚未知道东闸情况' if number else '读者得知西闸已破'}
            raw['threads'].append(observation)


def test_excerpt_observations_reach_method_and_remain_bound_to_their_passage(tmp_path,monkeypatch):
    library=LibraryService(tmp_path/'isolated-narration')
    model=PassageModel()
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    book=make_book(library,TEXT)['id']
    task=library.start_corpus_job(book,{'options':{'extent':'excerpt','note':'仅供测试的片段'}})
    job=wait_job(library,book,task['id'])
    assert job['status']=='completed',job['error']
    detail_call=next(c for c in job['calls'] if c['phase']=='detail')
    saved=library.corpus_call_record(book,job['id'],detail_call['seq'])
    assert '谁在讲、看、说或想' in saved['input']['messages'][0]['content']
    structure=library.review_corpus(book,{'version':1,'decision':'approve','note':'[FAKE] 核对两段原文','accept_limitations':True})
    reopened=LibraryService(library.workspace).get_corpus(book)
    observed=[t for t in reopened['body']['threads'] if t['domain']=='narration']
    assert [(t['details']['claim_status'],t['details']['voice_access']) for t in observed]==[
        ('stated','叙述者告知读者'),('attributed','门房私下怀疑，小棠只听到喊话')]
    task=library.start_corpus_job(book,{'kind':'methods','options':{'thread_ids':[observed[1]['id']]}})
    job=wait_job(library,book,task['id'])
    assert job['status']=='completed',job['error']
    assert model.calls[-1]['thread']['details']==observed[1]['details']
    method=library.list_methods()['methods'][0]
    assert method['body']['tasks']==['narration'] and [e['quote'] for e in method['body']['evidence']]==[NOW]
    assert library.review_method(method['id'],{'version':1,'decision':'approve','note':'[FAKE] 独立核对叙述方法'})['available']
    body=deepcopy(method['body'])
    body['evidence'].append({'book_id':book,'start':TEXT.index(PAST),'end':TEXT.index(PAST)+len(PAST),
                             'quote':PAST,'explanation':'试图从另一段借证据'})
    revised=library.save_method({'body':body,'expected_version':1},method['id'])
    assert any('以外的引文' in issue['message'] for issue in revised['source_issues'])
    bad=deepcopy(structure['body'])
    past,now=[t for t in bad['threads'] if t['domain']=='narration']
    now['evidence_ids']=past['evidence_ids']
    assert any(i['severity']=='error' and '每个所引事件' in i['message'] for i in graph_issues(bad,len(TEXT)))
    bad=deepcopy(structure['body'])
    next(t for t in bad['threads'] if t['domain']=='narration')['details']['claim_status']='人物猜测也作事实'
    with pytest.raises(ValueError,match='叙述观察须区分'):
        normalize_document(bad,TEXT)
    with pytest.raises(ValueError,match='已确认类型'):
        prepare_method(library,structure,{'basis':method['structure_origin']['basis'],
                                         'body':{**method['body'],'type_tags':['GENRE_QIHUAN']}})


def test_version_two_analysis_keeps_eight_domains_and_its_paused_job_budget(tmp_path,monkeypatch):
    from nw.studio import corpus_jobs

    library=LibraryService(tmp_path/'isolated-v2')
    model=CorpusModel()
    model.fail_at=2
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    current=corpus_jobs.empty_document
    monkeypatch.setattr(corpus_jobs,'empty_document',lambda *args:{**current(*args),'schema_version':2})
    book=make_book(library)['id']
    task=library.start_corpus_job(book,{'options':{'extent':'complete','max_calls':14,'note':'[FAKE] 旧版本任务'}})
    job=wait_job(library,book,task['id'])
    assert job['status']=='paused' and job['structure_schema_version']==2
    model.fail_at=None
    monkeypatch.setattr(corpus_jobs,'empty_document',current)
    library.control_corpus_job(book,job['id'],{'action':'resume','retry_failed':True})
    job=wait_job(library,book,task['id'])
    assert job['status']=='completed' and job['calls_used']==14
    body=library.get_corpus(book)['body']
    assert set(d['domain'] for d in body['domains'])==set(corpus_catalog(2)['domains'])
    assert body['schema_version']==2 and 'narration' not in corpus_catalog(2)['domains']
    with pytest.raises(ValueError, match='历史拆解规格'):
        library.review_corpus(book,{'version':1,'decision':'approve','note':'[FAKE] 原版职责完整'})
    assert library.get_corpus(book)['approved_version'] is None
