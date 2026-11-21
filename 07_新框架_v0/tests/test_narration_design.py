import json
from copy import deepcopy

import pytest

from nw.materials.narration import POLICY, scene_bases, validate_beat
from nw.materials.phase_contract import validate_phase
from nw.materials.phase_projection import method_checks
from nw.materials.phase_schema import schema
from nw.task_models import content_sha256
from test_material_phase_projection import chain


def case():
    session = chain()
    records = {r['stage']: r for r in session['stages']}
    scene = records['scene_design']['products']
    body = scene['members'][0]['body']
    body['characters'] = ['yan', 'lin']
    scene['chapters'][0]['scenes'][0]['story_order'] = 5
    character = records['character_design']['products']['members'][0]['body']
    character['background'] = '曾经查错封条，被撤职三月'
    for record in records.values():
        record['sha256'] = content_sha256(record['products'])
    context = {'scope': 'chapter', 'narration_policy': POLICY, 'approved_cards': [
        {'card_id': 'archive', 'kind': 'world', 'body': {'rule': '涨潮方可开库门', 'history': '两年前旧库因屋梁烧断封闭', 'visibility': 'public'}},
        {'card_id': 'secret', 'kind': 'world', 'body': {'rule': '前任故意纵火', 'visibility': 'author_only'}},
        {'card_id': 'lin', 'kind': 'character', 'body': {'background': '曾私藏引火物', 'visibility': 'public'}}],
        'accepted_state': [{'holder': holder, 'claim': claim, 'story_order': story, 'disclosure_order': disclosure,
                            'value': '已封存的旧信'}
                           for holder, claim, story, disclosure in [('yan','fact',1,[0,0,0]),
                               ('READER','fact',1,[0,0,0]), ('lin','fact',1,[0,0,0]),
                               ('yan','belief',1,[0,0,0]), ('yan','fact',11,[0,0,0]),
                               ('READER','fact',1,[99,1,1])]]}
    return session, records, body, context


def guide(time, mode, owner, ref, quote, effect):
    return {'scene': 'scene', 'observable': effect, 'check': '从实际原句辨别说话或推断的归属和随后变化',
            'narration': {'time': time, 'mode': mode, 'owner': owner, 'basis_ref': ref,
                          'basis_quote': quote, 'effect': effect}}


def test_public_history_remains_reader_only_in_order_then_character_reacts():
    session, records, body, context = case()
    guides = [guide('past','summary',None,'card:archive:history','旧库因屋梁烧断封闭','先说封库结果，随后讲明封库缘由'),
              guide('current','speech','lin','scene:scene:goal',body['goal'],'林出声要求核对封条'),
              guide('past','reenactment','yan','card:yan:background','查错封条','口令令沈砚想起失手的旧事'),
              guide('current','thought','yan','fact:0','旧信','他只确认眼前字迹，暂停原来的判断')]
    product = {'_uses': [], 'guidance': guides}
    validate_phase({'stage': 'expression_design', 'products': product}, 'expression_design', records, [], context)
    records['expression_design']['products'] = product
    session['context'] = context
    checks = [r for r in method_checks(session, 'scene', {'yan': 'real-yan','lin': 'real-lin'})
              if r['id'].startswith('work:narration:')]
    assert [r['narration_order'] for r in checks] == [1, 2, 3, 4]
    segments = [json.loads(r['binding']['observable']) for r in checks]
    assert [r['owner'] for r in segments] == [None, 'real-lin', 'real-yan', 'real-yan']
    assert segments[0]['audience'] == 'reader_only' and segments[0]['basis_quote'] == '旧库因屋梁烧断封闭'
    assert [r['basis_claim'] for r in segments] == ['history','scene','history','fact']


@pytest.mark.parametrize('time,mode,owner,ref,quote', [
    ('current','thought','lin','scene:scene:goal','调查'),
    ('current','inference','lin','scene:scene:goal','调查'),
    ('current','speech','absent','scene:scene:goal','调查'),
    ('past','summary',None,'scene:scene:planned_result','发现旧封条'),
    ('past','summary',None,'card:secret:rule','纵火'),
    ('past','summary',None,'fact:0','旧信'),
    ('past','summary','yan','fact:1','旧信'),
    ('past','summary','yan','fact:2','旧信'),
    ('past','summary','yan','fact:3','旧信'),
    ('past','summary','yan','fact:4','旧信'),
    ('past','summary',None,'fact:5','旧信'),
    ('current','thought','yan','card:archive:history','屋梁烧断'),
    ('past','summary',None,'card:archive:rule','涨潮方可开库门'),
    ('past','summary','yan','card:archive:history','司机醉酒'),
])
def test_reject_unauthorized_thought_future_or_false_history(time,mode,owner,ref,quote):
    _, records, body, context = case()
    beat = guide(time, mode, owner, ref, quote, '讲明线索')['narration']
    with pytest.raises(ValueError, match='叙述节拍'):
        validate_beat(beat, body, scene_bases(records, context)['scene'])


def test_two_scenes_keep_private_recollections_separate_and_schema_replays_old_settings():
    _, records, body, context = case()
    scene = records['scene_design']['products']
    scene['members'].append({'key': 'other', 'kind': 'scene', 'body': {**body, 'pov': 'lin'}})
    scene['chapters'][0]['scenes'].append({'card': 'other', 'story_order': 6, 'index': 2})
    records['scene_design']['sha256'] = content_sha256(scene)
    bases = scene_bases(records, context)
    assert 'fact:2' not in bases['scene'] and 'fact:2' in bases['other']
    assert 'card:lin:background' not in bases['scene'] and 'card:lin:background' in bases['other']
    assert 'fact:0' not in bases['other'] and 'card:yan:background' not in bases['other']
    assert 'card:secret:rule' not in bases['other']
    for flag in (False, True):
        shape = schema('expression_design', [], allow_requests=False, narration=flag)
        item = shape['properties']['products']['properties']['guidance']['items']
        assert ('narration' in item['required']) == flag
        world = schema('world_design', [], allow_requests=False, narration=flag)
        member = world['properties']['products']['properties']['members']['items']['anyOf'][0]
        assert ('history' in member['properties']['body']['properties']) == flag
    legacy = deepcopy(records['expression_design']['products'])
    with pytest.raises(ValueError, match='叙述节拍'):
        validate_phase({'stage':'expression_design','products':legacy},'expression_design',records,[],context)


def test_a_spoken_line_can_change_the_viewpoint_decision_but_a_narrator_aside_cannot():
    session, records, body, context = case()
    history = guide('past', 'summary', None, 'card:archive:history', '屋梁烧断', '库房封闭源于旧日火灾')
    spoken = guide('current', 'speech', 'lin', 'card:archive:history', '屋梁烧断', '林说那时屋梁烧断')
    reply = guide('current', 'inference', 'yan', 'beat:2', '林说那时屋梁烧断', '他听完改问库门何时换过')
    product = {'_uses': [], 'guidance': [history, spoken, reply]}
    validate_phase({'stage':'expression_design','products':product},'expression_design',records,[],context)
    session['context'] = context
    records['expression_design']['products'] = product
    checks = [r for r in method_checks(session, 'scene') if r['id'].startswith('work:narration:')]
    assert json.loads(checks[2]['binding']['observable'])['basis_claim'] == 'speech'
    for ref, quote in [('beat:1', history['observable']), ('beat:3', reply['observable'])]:
        reply['narration'].update(basis_ref=ref,basis_quote=quote)
        with pytest.raises(ValueError, match='叙述节拍'):
            validate_phase({'stage':'expression_design','products':product},'expression_design',records,[],context)


def test_belief_is_projected_as_a_personal_inference_and_cannot_be_recast_as_public_history():
    session, records, body, context = case()
    row = guide('current','inference','yan','fact:3','旧信','他怀疑有人换过信，但尚未找到证据')
    validate_beat(row['narration'], body, scene_bases(records, context)['scene'])
    session['context'] = context
    records['expression_design']['products']['guidance'] = [row]
    [check] = [r for r in method_checks(session, 'scene') if r['id'].startswith('work:narration:')]
    assert json.loads(check['binding']['observable'])['basis_claim'] == 'belief'
    for claim in ('belief', 'suspicion'):
        context['accepted_state'][3]['claim'] = claim
        bases = scene_bases(records, context)['scene']
        for mode, time, owner in [('summary','past',None),('reenactment','past','yan'),('speech','current','lin')]:
            with pytest.raises(ValueError, match='叙述节拍'):
                validate_beat({**row['narration'],'mode':mode,'time':time,'owner':owner}, body, bases)


def test_subjective_chain_and_reported_speech_cannot_become_an_established_cause():
    from nw.materials.narration import register_beat

    _, records, body, context = case()
    bases = scene_bases(records, context)['scene']
    inferred = guide('current','inference','yan','fact:3','旧信','沈砚怀疑旧信是伪造的')
    register_beat(bases, 1, inferred)
    spoken = guide('current','speech','yan','beat:1',inferred['observable'],'沈砚说自己怀疑旧信是伪造的')
    validate_beat(spoken['narration'], body, bases)
    register_beat(bases, 2, spoken)
    for ref, original in [('beat:1',inferred['observable']),('beat:2',spoken['observable'])]:
        for quote in ('旧信是伪造的',original):
            aside = guide('current','summary',None,ref,quote,'叙述者证实来信确属伪造')
            with pytest.raises(ValueError, match='叙述节拍'):
                validate_beat(aside['narration'], body, bases)


def test_narrator_cannot_drop_the_hearsay_qualifier_from_a_mixed_history_record():
    _, records, body, context = case()
    context['approved_cards'][0]['body']['history'] = '县志载明旧库停用。传闻前任故意纵火。'
    row = guide('past','summary',None,'card:archive:history','前任故意纵火','公开纵火原因')
    with pytest.raises(ValueError, match='传言或未决'):
        validate_beat(row['narration'], body, scene_bases(records, context)['scene'])


def test_client_design_freezes_public_history_and_personal_inference_for_reopened_writer(tmp_path):
    from dataclasses import asdict
    from nw.cards import decide_card, save_card
    from nw.context.story import build_story_context, scene_scope
    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.store import Store
    from nw.story_state import adopt_story, current_head, state_at
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_material_workflow import choose
    from test_novel_flow import config

    private_belief = '我怀疑封条被换，只有交班簿的柜号戊九能查证。'
    spoken = '[FAKE] 老许说：“我怀疑封条换过，得比一比旧印。”'
    orphan = '只有同名旧人记得的封条暗号'

    class Model(PhaseModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if payload.get('stage') == 'scene_design':
                raw = json.loads(result.text)
                body = raw['products']['members'][0]['body']
                body['characters'].append('informant')
                body['character_goals']['informant'] = '让查印的人先核对旧印，保住交班簿的柜号'
                body['entering_state'] = '沈砚举灯走近封条，老许正站在井口翻交班簿。'
                result.text = json.dumps(raw, ensure_ascii=False)
            elif payload.get('stage') == 'expression_design':
                from nw.materials.narration import EVIDENCE_POLICY
                assert payload['narration_policy'] == EVIDENCE_POLICY
                assert '人物可据自己的疑心发言或行动' in messages[0]['content']
                bases = payload['narration_bases']['scene']
                assert bases['card:archive:history']['public']
                [ref] = [k for k, v in bases.items() if v.get('claim') == 'belief']
                assert bases[ref]['audience'] == 'informant' and bases[ref]['speaker_private']
                assert bases[ref]['text'] == private_belief and orphan not in json.dumps(bases, ensure_ascii=False)
                raw = json.loads(result.text)
                entrances = [g for g in raw['products']['guidance'] if g['narration']['basis_ref'].startswith('cast:')]
                [scene] = payload['inputs']['scene_design']['products']['members']
                pov = scene['body']['pov']
                line = guide('current', 'speech', 'informant', ref, private_belief, spoken)
                line['narration']['witnesses'] = [pov]
                line['narration']['effect'] = '老许最担心的仍是戊九的柜号'
                line['check'] = '因没有公开戊九的柜号，沈砚只能先去查印'
                raw['products']['guidance'] = entrances + [
                    guide('past','summary',None,'card:archive:history','旧库因屋梁烧断封闭','[FAKE] 读者先得知封库始末'),
                    line, guide('current', 'inference', pov, f'beat:{len(entrances) + 2}', spoken,
                                '[FAKE] 听老许说完，他觉得新印值得比对，仍拿不准是否换过封条。')]
                result.text = json.dumps(raw, ensure_ascii=False)
            return result

    directory = tmp_path / 'story'
    template_catalog(tmp_path)
    with Store(directory, create=True, test_mode=True) as store:
        store.init_project('库门口的两种叙述')
        store.add_brief('先讲旧库封闭始末，回到门口写沈砚的疑心')
        ref = save_card(store, {'card_id':'archive','kind':'world','origin':'author',
            'body':{'title':'库史','rule':'涨潮方可开库门','history':'两年前旧库因屋梁烧断封闭','limits':'以县志为准','visibility':'public'}}, None)
        approved = decide_card(store, ref, 'approved', '批准库史')
        person = save_card(store, {'card_id': 'informant', 'kind': 'character', 'origin': 'author',
            'body': {'name': '老许', 'role': '井口守簿人', 'want': '当面查清可疑封条', 'visibility': 'public'}}, None)
        approval = decide_card(store, person, 'approved', '核对既有守簿人的身份')
        belief = {'entity_id':'archive','predicate':'cause','holder':'informant','value':private_belief,'claim':'belief',
                  'story_order':0,'disclosure_order':[0,0,0]}
        adopt_story(store, baseline(card_refs=[{**asdict(ref),'decision_id':approved.id},
                    {**asdict(person), 'decision_id': approval.id}],
                    facts=[belief, {**belief, 'holder': 'yan', 'value': orphan}]), {})
        provider = Model()
        job = start_job(store, JobRequest('design', budget=Budget(32, 90000, 4000))).id
        assert resume_job(store, job, provider, config(store)).step == 'plan:book:confirm'
        assert resume_job(store, job, provider, config(store), choose).step == 'plan:chapter:confirm'
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason
        scene = store.list('scene')[0].id
    with Store(directory, test_mode=True) as store:
        items = build_story_context(store, scene, scene_scope(store, scene), 90000).package['items']
        beats = [json.loads(json.loads(item['text'])['observable']) for item in items
                 if item['source'].startswith('material:work:narration:')]
        history, statement, response = [b for b in beats if b['basis_claim'] != 'cast_entry']
        assert (history['time'], history['audience'], history['basis_claim']) == ('past', 'reader_only', 'history')
        pov = response['owner']
        assert pov != 'yan' and (statement['owner'], statement['witnesses']) == ('informant', [pov])
        assert statement['basis_claim'] == 'belief' and 'basis_quote' not in statement and 'effect' not in statement
        assert (response['mode'], response['basis_claim'], response['basis_quote']) == ('inference', 'speech', spoken)
        package = json.dumps(items, ensure_ascii=False)
        assert private_belief not in package and orphan not in package and '戊九' not in package
        head = current_head(store)
        def beliefs(holder):
            view = state_at(store, head.branch_id, head.revision, 1, holder, (1, 1, 0), before_scene=scene)
            return [f.value for f in view.facts if f.claim == 'belief']
        assert beliefs('informant') == [private_belief] and beliefs(pov) == []
