"""A source judgment stays qualified, and each approved operation keeps its own observation."""
from copy import deepcopy
import json

import pytest

from corpus_fixture import CorpusModel, runtime, wait_job
from nw.passage_catalog import OBSERVATIONS
from nw.production_methods.passage_sources import recommendations, verify_choices
from nw.studio.corpus_contract import normalize_sequence
from nw.studio.corpus_methods import manual_method
from nw.studio.corpus_passages import sequence_issue
from nw.studio.corpus_prompts import messages
from nw.studio.library import LibraryService
from test_studio_corpus_passages import SAMPLES, SequenceModel, start_passage_method


@pytest.mark.parametrize('kind,role,status,line', [
    ('qualified_claim', 'claim', 'unknown', '男孩手里攥着半张车票。另一半兴许还在窗台上？'),
    ('interpreted_motive', 'interpretation', 'attributed', '男孩转身时，值班员暗想，他大概是为取回另一半票才来的。'),
])
def test_source_judgments_cannot_be_approved_as_facts_and_operations_remain_separate(
        tmp_path, monkeypatch, kind, role, status, line):
    samples = list(SAMPLES['focus_relay'])
    samples[-1] = (line, '由男孩的动作留下一个未获证实的解释。', '', '读者只能作待证判断。')
    monkeypatch.setitem(SAMPLES, 'focus_relay', samples)
    service = LibraryService(tmp_path)
    book, structure, model_method = start_passage_method(service, monkeypatch, 'focus_relay')
    doc = deepcopy(structure['body'])
    relay = next(t for t in doc['threads'] if t['details'].get('passage_sequence'))
    observed = deepcopy(relay)
    observed.update(id='PartialJudgment', title='据所见产生待核判断')
    observed['details']['claim_status'] = status
    seq = observed['details']['passage_sequence']
    beat = dict(seq['beats'][-1], role=role, claim_status=status)
    seq.update(kind=kind, condition='现场可见线索不足以证实答案', boundary='答案已用独立证据确认', beats=[beat])
    doc['threads'].append(observed)

    def save():
        return service.save_corpus(book, {'body':doc,'expected_version':1,
            'reviewed_units':structure['coverage']['reviewed_units']})

    for change in ('把推测当作事实', ''):
        beat.update(claim_status='stated', story_change=change)
        with pytest.raises(ValueError, match='估计或对他人动机'):
            save()
    beat.update(claim_status=status, story_change='')
    observed['details']['claim_status'] = 'stated'
    with pytest.raises(ValueError, match='估计或对他人动机'):
        save()
    observed['details']['claim_status'] = status
    new = save()
    review = {'version':new['version'],'decision':'approve','note':'有原句支持的判断仍为未证实','accept_limitations':True}
    service.review_corpus(book, review)

    def make_method(ids, instructions):
        draft = manual_method(service, book, {'version':new['version'],'thread_ids':ids})
        body = deepcopy(model_method['body'])
        step = body['operations'][0]
        body['operations'] = [dict(step, key=f's{i}',instruction=instr) for i,instr in enumerate(instructions)]
        return service.save_method({'body':body,'expected_version':1}, draft['id'])

    use_relay = '以现场声音转移注意，然后让视线落到本场需要出现的人。'
    use_claim = '保留当下可见依据和判断中的限定，未受证实的另一种解释继续开放。'
    mixed = make_method([relay['id'], observed['id']], [use_relay, use_claim])
    with pytest.raises(ValueError, match='分别归属一项原文观察'):
        service.review_method(mixed['id'], review)
    for thread_id, operation in ((relay['id'],use_relay),(observed['id'],use_claim)):
        item = make_method([thread_id], [operation])
        service.review_method(item['id'], review)
    reopened = LibraryService(tmp_path)
    refs = recommendations(reopened, ['GENRE_XUANYI'])
    assert {r['kind']:r['operations'] for r in refs} == {'focus_relay':[use_relay],kind:[use_claim]}
    verify_choices(tmp_path, refs, [{'source_ref':r['ref']} for r in refs])

    # Simulate an old database where the combined method had passed review. The production
    # selector must still omit it when opening a project frozen under the earlier rules.
    with reopened.connect() as conn:
        conn.execute('INSERT INTO production_method_reviews VALUES(?,?,?,?,?)',
                     (mixed['id'], mixed['version'], 'approve', '此前批准的组合方法', '2020-01-01T00:00:00Z'))
        conn.execute('UPDATE production_methods SET approved_version=? WHERE id=?', (mixed['version'], mixed['id']))
    assert not reopened.get_method(mixed['id'])['current_for_production']
    assert {r['ref'] for r in recommendations(reopened,['GENRE_XUANYI'])} == {r['ref'] for r in refs}
    old_pin = dict(refs[0], method_id=mixed['id'], ref=f"{mixed['id']}@{mixed['version']}#{relay['id']}")
    with pytest.raises(ValueError, match='STALE_PROJECT_METHOD'):
        verify_choices(tmp_path, [old_pin], [{'source_ref':old_pin['ref']}])


def test_one_detail_window_can_yield_separate_methods_for_multiple_kinds(tmp_path, monkeypatch):
    kinds = {'sensory_evidence','identity_slice','place_function'}
    samples = list(SAMPLES['focus_relay'])
    samples[0] = ('旅客们逐个抬起手腕，把车票递到值班员眼前。','排队验票。','','读者看见核验动作。')
    samples[-1] = ('男孩摊开半张票。身后，黄线沿着地砖一直延伸到验票口。','陈设印证了此处用途。','','读者认出了验票口。')
    monkeypatch.setitem(SAMPLES,'focus_relay',samples)
    old_hint = '只见单段技巧或中间隔了举证不了的完整段落，保留普通观察'
    for phase,payload in [('detail',{}),('relations',{'domain':'narration'})]:
        assert old_hint in messages(phase,payload,craft=False)[0]['content']
        current = messages(phase,payload,craft=True)[0]['content']
        assert old_hint not in current and '只需一处证据的手法可以只存一拍' in current
        for _, roles in OBSERVATIONS.values():
            assert all(role+'='+basis in current for role,basis in roles.items())

    class MultiObservationBook(SequenceModel):
        def generate(self, messages, **params):
            prompt = messages[0]['content']
            payload = json.loads(messages[-1]['content'])
            phase = payload['phase']
            if phase == 'relations' and payload['domain'] == 'narration':
                assert {t['details']['passage_sequence']['kind'] for t in payload['narration_observations']} == kinds
                result = CorpusModel.generate(self, messages, **params)
                result.text = json.dumps({'domains':json.loads(result.text)['domains']},ensure_ascii=False)
                return result
            result = super().generate(messages, **params)
            raw = json.loads(result.text)
            if phase == 'detail':
                assert old_hint not in prompt
                prototype, = raw['threads']
                raw['threads'] = []
                for kind, positions in [('sensory_evidence',[(1,'detail')]),('identity_slice',[(2,'entry')]),
                                        ('place_function',[(0,'activity'),(3,'setting')])]:
                    row = deepcopy(prototype)
                    row['id'] += '_'+kind
                    seq = row['details']['passage_sequence']
                    beats = [dict(seq['beats'][i],role=role,claim_status='stated') for i,role in positions]
                    seq.update(kind=kind,beats=beats)
                    row['evidence_ids'] = [b['evidence_id'] for b in beats]
                    raw['threads'].append(row)
            if phase == 'methods':
                row = payload['thread']
                kind = row['details']['passage_sequence']['kind']
                assert all(role+'='+basis in prompt for role,basis in OBSERVATIONS[kind][1].items())
                body = raw['methods'][0]['body']
                quotes = {e['quote'] for e in payload['evidence'] if e['id'] in row['evidence_ids']}
                body['evidence'] = [e for e in body['evidence'] if e['quote'] in quotes]
                body['operations'][0]['instruction'] = OBSERVATIONS[kind][0]
            result.text = json.dumps(raw,ensure_ascii=False)
            return result

    service = LibraryService(tmp_path)
    model = MultiObservationBook('focus_relay')
    config = runtime()
    config.provider = 'openai'
    monkeypatch.setattr(service,'_corpus_runtime',lambda:(config,model))
    book = service.import_book({'filename':'候车厅夜班.txt','title':'候车厅夜班',
                                'text':'\n'.join(r[0] for r in SAMPLES['focus_relay'])})
    if book['status']=='pending_review':
        service.review_book(book['id'],{'types':['GENRE_XUANYI'],'decompose':False})
    book = book['id']
    task = service.start_corpus_job(book,{'options':{'extent':'excerpt','note':'隔离测试摘录'}})
    structure_job = wait_job(service,book,task['id'])
    assert structure_job['status']=='completed',structure_job['error']
    review = {'version':1,'decision':'approve','note':'核对实际原句','accept_limitations':True}
    structure = service.review_corpus(book,review)
    observed = [t for t in structure['body']['threads'] if t['details'].get('passage_sequence')]
    assert {t['details']['passage_sequence']['kind'] for t in observed} == kinds
    task = service.start_corpus_job(book,{'kind':'methods','options':{'thread_ids':[t['id'] for t in observed]}})
    done = wait_job(service,book,task['id'])
    assert done['status']=='completed' and len(done['calls'])==len(kinds),done['error']
    for method in service.get_corpus(book)['derived_methods']:
        service.review_method(method['method_id'],review)
    refs = recommendations(LibraryService(tmp_path), ['GENRE_XUANYI'])
    assert {r['kind']:r['operations'] for r in refs} == {k:[OBSERVATIONS[k][0]] for k in kinds}
    assert next(r['roles'] for r in refs if r['kind']=='place_function') == ['activity','setting']


def test_place_evidence_preserves_source_order_and_event_across_a_paragraph():
    activity = '旅客抬手将票递了出去。'
    setting = '黄线尽头竖着一排验票闸。'
    source = activity+'\n中间的人往旁边站了站。\n'+setting
    quotes = {k:{'id':k,'start':source.index(q),'end':source.index(q)+len(q)} for k,q in [('a',activity),('s',setting)]}
    unit = {'ch':{'id':'ch','level':'chapter'}}
    event = {'id':'e','unit_id':'ch','granularity':'detail','evidence_ids':['a','s']}
    def beat(role, key):
        return {'role':role,'evidence_id':key,'event_id':'e','claim_status':'stated','story_change':'',
                'reader_change':'看出用途','bridge':'验票的位置确定了现场的用途'}
    seq = normalize_sequence({'kind':'place_function','condition':'需要交代此处用途','boundary':'人物看不见',
                              'beats':[beat('activity','a'),beat('setting','s')]})
    thread = {'details':{'passage_sequence':seq},'node_ids':['e','elsewhere'],'evidence_ids':['a','s']}
    def issue():
        return sequence_issue(thread,{'e':event,'elsewhere':dict(event,id='elsewhere')},quotes,unit,source)
    assert not issue()
    seq['beats'].reverse()
    assert '不能倒排' in issue()
    seq['beats'].reverse()
    seq['beats'][1]['event_id'] = 'elsewhere'
    assert '未举证的完整自然段' in issue()
    seq['beats'][1]['event_id'] = 'e'
    # A paragraph transition itself must occur across the cited boundary.
    seq['kind'] = 'paragraph_turn'
    seq['beats'][0]['role'],seq['beats'][1]['role'] = 'before','after'
    assert '未举证的完整自然段' in issue()
