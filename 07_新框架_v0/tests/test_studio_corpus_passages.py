"""Exercise continuous-passage provenance through real library jobs and independent review."""
from copy import deepcopy
import json

import pytest

from corpus_fixture import CorpusModel, runtime, thread, wait_job
from nw.studio.corpus_catalog import corpus_catalog
from nw.studio.corpus_checks import graph_issues
from nw.studio.corpus_contract import normalize_document
from nw.studio.corpus_methods import prepare_method
from nw.studio.corpus_prompts import messages
from nw.studio.library import LibraryService


SAMPLES={
    'procedure_branch':[
        ('排头的小贺交还旧牌，领走新牌。','前一人先完整办理。','旧牌换为新牌。','读者看清常规办理的结果。'),
        ('十来个人照样办完，队尾终于往前挪了。','以队列移动略过同一办理。','队列推进。','重复的过程已经交代。'),
        ('轮到阿琴，她把牌揣回袖口：“我报失。”','相同柜台给新来者同一选择机会。','她改选报失。','读者知道这次不同。'),
        ('柜员没递新牌，把报失簿推过来。','另一种选择落到另一件物品。','报失簿交到台前。','能否补领仍未知。')],
    'focus_relay':[
        ('夜班候车厅的长椅上坐满了人。','候车厅和人群定位现场。','','读者知道这是一处仍在使用的公共空间。'),
        ('门响了一声，椅上几个人同时回头。','声音转移候车人的注意。','几个人回头。','读者随人群看向门口。'),
        ('值班员的视线越过旅客，停在门边的男孩脸上。','接住人群动作，追随值班员的视线。','值班员注意到门边男孩。','男孩成为当前焦点。'),
        ('他手里攥着半张车票，另一半会在哪儿？','以手上的细节接住刚出现的男孩。','','原文留下疑问，另一半车票的位置未知。')],
}


class SequenceModel(CorpusModel):
    def __init__(self,kind):
        super().__init__()
        self.kind=kind

    def generate(self,messages,**params):
        result=super().generate(messages,**params)
        payload=self.calls[-1]
        raw=json.loads(result.text)
        phase=payload['phase']
        if phase=='detail':
            assert 'passage_sequence' in messages[0]['content']
            event=raw['events'][0]
            quotes=[]
            kind=corpus_catalog()['passage_sequences'][self.kind]
            roles=(kind['required_roles'] if len(SAMPLES[self.kind])==len(kind['required_roles']) else kind['role_order'])
            beats=[]
            for index,(role,(line,bridge,change,reader)) in enumerate(zip(roles,SAMPLES[self.kind])):
                eid=f"{payload['prefix']}_q{index}"
                quotes.append({'id':eid,'quote':line,'explanation':reader})
                claim='unknown' if self.kind=='focus_relay' and index==3 else 'stated'
                beats.append(dict(role=role,event_id=event['id'],evidence_id=eid,bridge=bridge,story_change=change,
                                  reader_change=reader,claim_status=claim))
            raw['evidence']=quotes
            event['evidence_ids']=[q['id'] for q in quotes]
            observation=thread('narration',[event],None,event['evidence_ids'])
            observation['id']=payload['prefix']+'_sequence'
            observation['details'].update(claim_status='stated',passage_sequence={
                'kind':self.kind,
                'condition':'本场已有常规办理和另一个选择' if self.kind=='procedure_branch' else '已知现场与引出新人物的关注路径',
                'boundary':'没有重复事务与另一分支' if self.kind=='procedure_branch' else '同处一景但无人能看见该对象',
                'beats':beats})
            raw['threads']=[observation]
        elif phase=='relations' and payload['domain']=='narration':
            assert len(payload['narration_observations'])==1
            raw={'domains':raw['domains']}
        elif phase=='methods':
            assert 'passage_sequence' in messages[0]['content']
            body=raw['methods'][0]['body']
            body.update(title='按已知事件和注意线索安排连续段落',tasks=['narration'])
            body['outputs'][0].update(stage='expression_design',field='guidance',description='用本项目实际事件和场景推进各拍')
            body['downstream']=[{'output_key':'o1','consumer':c,'usage':'写出或核验前后两段怎样衔接'} for c in ('writer','review')]
        result.text=json.dumps(raw,ensure_ascii=False)
        return result


def start_passage_method(library,monkeypatch,kind='procedure_branch'):
    model=SequenceModel(kind)
    config=runtime()
    config.provider='openai'
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(config,model))
    title={'procedure_branch':'柜前换牌','focus_relay':'候车厅的半张票'}[kind]
    book=library.import_book({'filename':title+'.txt','title':title,'text':'\n'.join(s[0] for s in SAMPLES[kind])})
    if book['status']=='pending_review':
        book=library.review_book(book['id'],{'types':['GENRE_XUANYI'],'decompose':False})
    book=book['id']
    task=library.start_corpus_job(book,{'options':{'extent':'excerpt','note':'[FAKE] 隔离测试片段'}})
    job=wait_job(library,book,task['id'])
    assert job['status']=='completed',job['error']
    review={'version':1,'decision':'approve','note':'[FAKE] 核实相邻原文','accept_limitations':True}
    structure=library.review_corpus(book,review)
    tid=next(t['id'] for t in structure['body']['threads'] if 'passage_sequence' in t['details'])
    task=library.start_corpus_job(book,{'kind':'methods','options':{'thread_ids':[tid]}})
    job=wait_job(library,book,task['id'])
    assert job['status']=='completed',job['error']
    method_id=library.get_corpus(book)['derived_methods'][0]['method_id']
    library.review_method(method_id,{'version':1,'decision':'approve','note':'[FAKE] 核实方法迁移及边界'})
    return book,structure,library.get_method(method_id)


@pytest.mark.parametrize('kind',list(SAMPLES))
def test_verified_sequences_survive_reopen_and_require_all_adjacent_evidence(tmp_path,monkeypatch,kind):
    service=LibraryService(tmp_path)
    book,structure,method=start_passage_method(service,monkeypatch,kind)
    reread=LibraryService(tmp_path).get_method(method['id'])
    assert reread['available']
    sequence,=reread['structure_origin']['passage_sequences']
    assert sequence['kind']==kind
    assert [b['role'] for b in sequence['beats']]==corpus_catalog()['passage_sequences'][kind]['role_order']
    assert all('evidence_id' not in b and 'event_id' not in b for b in sequence['beats'])
    source='\n'.join(s[0] for s in SAMPLES[kind])
    doc=structure['body']
    row=next(t for t in doc['threads'] if t['id']==sequence['thread_id'])
    beats=row['details']['passage_sequence']['beats']
    revised=deepcopy(method['body'])
    revised['evidence'].pop(1)
    with pytest.raises(ValueError,match='每个落点'):
        prepare_method(service,structure,{'body':revised,'basis':method['structure_origin']['basis']})
    beats[1].update(claim_status='inferred',story_change='')
    with pytest.raises(ValueError,match='关键承接只凭推测'):
        prepare_method(service,structure,{'body':method['body'],'basis':method['structure_origin']['basis']})
    beats[1]['claim_status']='stated'
    beats[0]['evidence_id'],beats[3]['evidence_id']=beats[3]['evidence_id'],beats[0]['evidence_id']
    assert any('原文实际位置递进' in issue['message'] for issue in graph_issues(doc,len(source),content=source))
    beats[0]['evidence_id'],beats[3]['evidence_id']=beats[3]['evidence_id'],beats[0]['evidence_id']
    beats[0]['claim_status']='attributed'
    beats[0]['story_change']='未经确认已领取'
    with pytest.raises(ValueError,match='人物说法'):
        normalize_document(doc,source)
    beats[0]['claim_status']='stated'
    beats[2]['role']=beats[0]['role']
    with pytest.raises(ValueError,match='依次'):
        normalize_document(doc,source)


def test_gap_between_cited_paragraphs_and_legacy_prompt_compatibility():
    from nw.studio.corpus_passages import sequence_issue
    content='拍一\n无据串入的另一个事件\n拍二'
    evidence={k:{'id':k,'start':content.index(q),'end':content.index(q)+len(q)} for k,q in [('q1','拍一'),('q2','拍二')]}
    event={'id':'e','unit_id':'c','granularity':'detail','evidence_ids':list(evidence)}
    thread_row={'evidence_ids':list(evidence),'node_ids':['e'],'details':{'passage_sequence':{
        'beats':[{'event_id':'e','evidence_id':k} for k in evidence]}}}
    assert '完整自然段' in sequence_issue(thread_row,{'e':event},evidence,{'c':{'id':'c','level':'chapter'}},content)
    heading={'c':{'id':'c','level':'chapter','start':0,'end':len(content),'boundary_basis':'source_heading'}}
    assert '章名只能定位章节' in sequence_issue(thread_row,{'e':event},evidence,heading,content)
    evidence['q1']['end']+=1
    assert '章名只能定位章节' in sequence_issue(thread_row,{'e':event},evidence,heading,content)
    assert 'passage_sequence' not in messages('detail',{},version=5,passages=False)[0]['content']
    assert 'passage_sequence' not in messages('detail',{},version=4)[0]['content']
    assert 'passage_sequence' in messages('detail',{},version=5)[0]['content']


@pytest.mark.parametrize('kind,indices',[('focus_relay',[0,1,2]),('procedure_branch',[0,2])])
def test_no_narrated_handoff_or_time_skip_is_required(tmp_path,monkeypatch,kind,indices):
    # The source actually ends at the focus or choice, without the sample's later sentence.
    model_rows=[SAMPLES[kind][i] for i in indices]
    required=corpus_catalog()['passage_sequences'][kind]['required_roles']
    assert len(model_rows)==len(required)
    monkeypatch.setitem(SAMPLES,kind,model_rows)
    service=LibraryService(tmp_path)
    _,_,method=start_passage_method(service,monkeypatch,kind)
    sequence,=method['structure_origin']['passage_sequences']
    assert [b['role'] for b in sequence['beats']]==required
    assert not any(b['role']=='handoff' for b in sequence['beats'])


@pytest.mark.parametrize('had_passages',[False,True],ids=['original-v5','v5-before-single-techniques'])
def test_pre_extension_v5_job_resumes_with_its_original_detail_request(tmp_path,monkeypatch,had_passages):
    service=LibraryService(tmp_path)
    model=CorpusModel()
    model.fail_at=3
    monkeypatch.setattr(service,'_corpus_runtime',lambda:(runtime(),model))
    launch=service._launch_corpus
    def simulate_saved_v5_state(book,job,*args):
        with service.connect() as conn:
            conn.execute("UPDATE corpus_jobs SET state_json=json_remove(state_json,'$.craft_observations') WHERE id=?",(job,))
            if not had_passages:
                conn.execute("UPDATE corpus_jobs SET state_json=json_remove(state_json,'$.passage_observations') WHERE id=?",(job,))
        launch(book,job,*args)
    monkeypatch.setattr(service,'_launch_corpus',simulate_saved_v5_state)
    from corpus_fixture import make_book
    book=make_book(service,'[FAKE] 旧版任务一章原文。')['id']
    task=service.start_corpus_job(book,{'options':{'extent':'excerpt','note':'[FAKE] 模拟旧版任务续跑'}})
    job=wait_job(service,book,task['id'])
    assert job['status']=='paused' and job['calls'][-1]['phase']=='detail'
    model.fail_at=None
    service=LibraryService(tmp_path)
    monkeypatch.setattr(service,'_corpus_runtime',lambda:(runtime(),model))
    service.control_corpus_job(book,task['id'],{'action':'resume','retry_failed':True})
    completed=wait_job(service,book,task['id'])
    assert completed['status']=='completed',completed['error']
    detail=[service.corpus_call_record(book,task['id'],c['seq'])['input']['messages']
            for c in completed['calls'] if c['phase']=='detail']
    assert len(detail)==2 and detail[0]==detail[1]
    expected=messages('detail',json.loads(detail[0][-1]['content']),version=5,passages=had_passages,craft=False)
    assert detail[0]==expected
    system=detail[0][0]['content']
    assert ('procedure_branch' in system and 'focus_relay' in system)==had_passages
    assert ('passage_sequence' in system)==had_passages
    for call in completed['calls']:
        logged=service.corpus_call_record(book,task['id'],call['seq'])['input']['messages']
        assert 'sensory_evidence' not in logged[0]['content'] and 'reader_address' not in logged[0]['content']
