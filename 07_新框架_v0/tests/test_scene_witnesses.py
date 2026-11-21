import json

import pytest

from nw.materials import narration, narration_review
from nw.materials.phase_projection import method_checks
from nw.materials.phase_contract import validate_phase
from nw.materials.phase_schema import schema
from nw.materials.action_review import review_result
from nw.scene_messages import draft_messages
from test_material_action_review import draft, review_run, span
from test_narration_design import case, guide


def exchange():
    session, records, body, context = case()
    context['narration_policy'] = narration.ACCESS_POLICY
    prior = records['character_design']['products']['members'].pop(0)
    context['approved_cards'].append({'kind':'character','card_id':prior['key'], 'body':prior['body']})
    body.update(narrative_person='first', characters=['yan', 'lin', 'xu'])
    context['accepted_state'][2]['value'] = '旧库存有一封信，真正的寄信人一直使用化名。'
    context['accepted_state'][2]['claim'] = 'suspicion'
    spoken = guide('current', 'speech', 'lin', 'fact:2', context['accepted_state'][2]['value'],
                   '林凑近我说，旧库可能还留着一封信。')
    spoken['narration']['witnesses'] = ['yan']
    decision = guide('current', 'inference', 'yan', 'beat:1', spoken['observable'], '我先改去旧库查实，信在不在还说不准。')
    records['expression_design']['products'] = {'guidance': [spoken, decision], '_uses': []}
    from nw.task_models import content_sha256
    records['scene_design']['sha256'] = content_sha256(records['scene_design']['products'])
    records['character_design']['sha256'] = content_sha256(records['character_design']['products'])
    session['context'] = context
    return session, records, body, context, spoken


def test_speaker_can_disclose_part_of_her_own_knowledge_without_granting_it_to_the_room(draft):
    session, records, _, context, _ = exchange()
    product = records['expression_design']['products']
    validate_phase({'stage':'expression_design','products':product}, 'expression_design', records, [], context)
    checks = [c for c in method_checks(session, 'scene', {'yan': 'actual-1', 'lin': 'actual-2', 'xu': 'actual-3'})
              if c['id'].startswith(narration_review.PREFIX)]
    public = json.loads(checks[0]['binding']['observable'])
    assert public['witnesses'] == ['actual-1'] and public['owner'] == 'actual-2'
    assert public['narrative_person'] == 'first' and public['basis_claim'] == 'suspicion'
    assert 'basis_quote' not in public and '寄信人' not in json.dumps(public, ensure_ascii=False)
    assert checks[0]['method_artifact']['narration']['basis_ref'] == 'fact:2'
    split = draft.text.index('。') + 1
    heard, thought = span(draft, 0, split), span(draft, split, len(draft.text))
    rows = [dict(id=c['id'], status='pass', evidence=[s]) for c, s in zip(checks, [heard, thought])]
    ranges = narration_review.reader_spans(checks, rows, draft)
    for holder in ('actual-1', 'actual-2'):
        narration_review.check_state_audience([{'holder': holder, 'evidence': [heard]}], ranges)
    for holder, evidence in [('actual-3', heard), ('actual-2', thought), ('WORLD', thought)]:
        with pytest.raises(ValueError, match='MATERIAL_EVIDENCE'):
            narration_review.check_state_audience([{'holder':holder, 'evidence':[evidence]}], ranges)


def test_witness_relay_changes_who_can_react_and_requires_a_real_information_channel():
    _, records, body, context, spoken = exchange()
    bases = narration.scene_bases(records, context)['scene']
    narration.register_beat(bases, 1, spoken)
    response = guide('current', 'action', 'xu', 'beat:1', spoken['observable'], '许某听后动身')['narration']
    response['witnesses'] = ['yan']
    with pytest.raises(ValueError, match='没有见证'):
        narration.validate_beat(response, body, bases, access=True)
    relay = guide('current','speech','yan','beat:1',spoken['observable'],'我转告许某，林怀疑旧库有信。')
    relay['narration']['witnesses'] = ['xu']
    narration.validate_beat(relay['narration'], body, bases, access=True)
    narration.register_beat(bases, 2, relay)
    narration.validate_beat({**response, 'basis_ref':'beat:2','basis_quote':relay['observable']}, body, bases, access=True)
    for listeners in (None, [], ['xu'], ['yan','absent'], ['yan','yan'], ['lin','yan']):
        with pytest.raises(ValueError, match='叙述节拍'):
            narration.validate_beat({**spoken['narration'], 'witnesses':listeners}, body, bases, access=True)
    with pytest.raises(ValueError, match='公共前史'):
        narration.validate_beat({**spoken['narration'],'basis_ref':'card:archive:history','basis_quote':'屋梁烧断'},
                                body,bases,access=True)
    with pytest.raises(ValueError, match='场尾结果'):
        narration.validate_beat(dict(time='current',mode='thought',owner='yan',basis_ref='scene:scene:planned_result',
                                     basis_quote=body['planned_result'], effect='因此猜想'),body,bases,access=True)


@pytest.mark.parametrize('source', ['background', 'independent_goal'])
def test_private_character_card_drives_only_owners_actual_public_beat(source):
    session, records, body, context, spoken = exchange()
    card = next(c['body'] for c in context['approved_cards'] if c['card_id'] == 'lin')
    card[source] = '要追回藏在四号柜的原信'
    ref = 'card:lin:' + source
    assert ref not in narration.scene_bases(records, context)['scene']
    context['narration_policy'] = narration.EVIDENCE_POLICY
    spoken['narration'].update(basis_ref=ref, basis_quote=card[source], effect='担心四号柜里的原信不保')
    spoken['check'] = '四号柜这段经历让林的措辞有所保留'
    product = records['expression_design']['products']
    validate_phase({'stage':'expression_design','products':product}, 'expression_design', records, [], context)
    check = next(c for c in method_checks(session, 'scene') if c['id'].startswith(narration_review.PREFIX))
    assert '四号柜' not in json.dumps(check['binding'], ensure_ascii=False)
    assert spoken['observable'] in check['binding']['observable']
    assert '四号柜' in check['method_artifact']['narration']['basis_quote']
    bases = narration.scene_bases(records, context)['scene']
    for override in ({'owner':'yan','witnesses':['lin']}, {'time':'past'}, {'mode':'thought'}):
        with pytest.raises(ValueError, match='叙述节拍'):
            narration.validate_beat({**spoken['narration'], **override}, body, bases, access=True)


def test_rumor_cannot_become_world_reader_or_listener_fact_without_accessible_corroboration(draft):
    session, records, _, context, _ = exchange()
    split = draft.text.index('。') + 1
    heard, thought = span(draft, 0, split), span(draft, split, len(draft.text))
    for policy in (narration.ACCESS_POLICY, narration.EVIDENCE_POLICY):
        context['narration_policy'] = policy
        checks = [c for c in method_checks(session, 'scene') if c['id'].startswith(narration_review.PREFIX)]
        rows = [dict(id=c['id'], status='pass', evidence=[s]) for c, s in zip(checks, [heard, thought])]
        ranges = narration_review.reader_spans(checks, rows, draft)
        if policy == narration.ACCESS_POLICY:
            assert all('reported_only' not in r for r in ranges)
            continue
        assert all(r['reported_only'] for r in ranges)
        for holder in ('WORLD', 'READER', 'yan', 'lin'):
            op = {'holder':holder, 'claim':'fact', 'evidence':[heard]}
            with pytest.raises(ValueError, match='独立凭据'):
                narration_review.check_state_audience([op], ranges)
            narration_review.check_state_audience([{**op, 'claim':'utterance'}], ranges)
        testimony = {'holder':'yan','claim':'fact','evidence':[heard, thought]}
        observation = {**ranges[1], 'mode':'perception', 'holders':['xu']}
        observation.pop('reported_only')
        with pytest.raises(ValueError, match='独立凭据'):
            narration_review.check_state_audience([testimony], [ranges[0], observation])
        narration_review.check_state_audience([testimony], [ranges[0], {**observation, 'holders':['yan']}])
        identity = {**testimony, 'entity_id':'lin', 'predicate':'identity_status:渡口'}
        other_person = {**ranges[0], 'reported_only':False, 'mode':'perception', 'cast_subject':'xu',
                        'cast_basis':'cast_reveal'}
        unseen = {**observation, 'reported_only':False, 'cast_subject':'lin', 'cast_basis':'cast_reveal'}
        with pytest.raises(ValueError, match='独立凭据'):
            narration_review.check_state_audience([identity], [other_person, unseen])
        narration_review.check_state_audience([identity], [other_person, {**unseen, 'holders':['yan']}])


def test_current_transport_requires_scene_person_and_legacy_schema_does_not():
    for policy in narration.POLICIES:
        props = schema('scene_design', [], allow_requests=False, narration=policy)['properties']['products']['properties']
        card = props['members']['items']['anyOf'][0]['properties']['body']
        assert ('narrative_person' in card['required']) == (policy in narration.ACCESS_POLICIES)
        shape = schema('expression_design', [], allow_requests=False, narration=policy)
        beat = shape['properties']['products']['properties']['guidance']['items']['properties']['narration']
        assert ('witnesses' in beat['properties']) == (policy in narration.ACCESS_POLICIES)


@pytest.mark.parametrize('problem', ['person', 'witness'])
def test_reported_prose_defect_routes_to_revision_with_current_draft_positions(draft, problem):
    check = {'id':'work:narration:s:0', 'profile':'method_work', 'narration_order':1, 'narrative_person':'first'}
    contract = {'checks':[check]}
    read, _ = draft_messages({}, 'review', draft, None, contract, '', ())
    assert '人物台词中的“我”' in read[0]['content']
    evidence = span(draft, 0, draft.text.index('。') + 1)
    finding = {'id':check['id'], 'status':'failed', 'reason':f'[{problem}] 本稿没有落实当前视角。',
               'evidence':[evidence]}
    result = review_result(review_run(draft, [finding]), contract, draft, None)
    assert result['recommendation'] == 'revise'
    messages, _ = draft_messages({}, 'revise', draft, result, None, '', ())
    feedback, = json.loads(messages[-1]['content'])['review']['material_checks']
    assert feedback['fix'] == narration_review.FIXES[problem]
    assert feedback['draft_locations'] == [{'start':0, 'end':evidence['end']}]


@pytest.mark.parametrize('claim', ['utterance', 'plan'])
def test_prior_utterance_or_plan_can_motivate_current_action_without_becoming_a_completed_fact(claim):
    _, records, body, context, _ = exchange()
    context['accepted_state'][0].update(claim=claim, value='等收据拿到再查旧库')
    bases = narration.scene_bases(records, context)['scene']
    response = guide('current', 'action', 'yan', 'fact:0', '等收据拿到再查旧库', '我把查库的纸条压回桌底。')['narration']
    response['witnesses'] = []
    narration.validate_beat(response, body, bases, access=True)
    for bad in (dict(mode='summary', time='past'), dict(basis_quote='查旧库')):
        with pytest.raises(ValueError, match='叙述节拍'):
            narration.validate_beat({**response, **bad}, body, bases, access=True)


def test_hearing_a_self_introduction_is_not_independent_proof_of_identity():
    heard = {'start':0, 'end':12, 'cast_subject':'keeper', 'cast_basis':'cast_entry',
             'time':'current', 'mode':'speech', 'holders':['keeper','yan']}
    proof = {'start':20, 'end':34, 'cast_subject':'keeper', 'cast_basis':'cast_reveal',
             'time':'current', 'mode':'perception', 'holders':['yan']}
    op = {'holder':'yan','entity_id':'keeper','claim':'fact','predicate':'identity_status:巡官','evidence':[heard]}
    for holder in ('yan', 'WORLD', 'READER'):
        with pytest.raises(ValueError, match='不能单独证实'):
            narration_review.check_state_audience([{**op, 'holder':holder}], [heard, proof])
    narration_review.check_state_audience([{**op,'claim':'utterance'}], [heard, proof])
    narration_review.check_state_audience([{**op,'evidence':[proof]}], [heard, proof])
    with pytest.raises(ValueError, match='不能单独证实'):
        narration_review.check_state_audience([{**op, 'entity_id':'messenger','evidence':[proof]}], [heard, proof])


def test_review_keeps_each_distinct_upstream_receipt_in_the_same_message():
    from copy import deepcopy
    from nw.materials.phase_projection import _share_product_refs

    first = {'stage':'scene_design', 'task_id':'ab', 'sha256':'a' * 64}
    second = {**first, 'sha256':'b' * 64}
    checks = [{'id':'work:semantic:1', 'method_artifact':{'applications':[
        {'product_ref':first, 'application':'动作'}, {'product_ref':second, 'application':'时序'}]}},
        {'id':'work:semantic:2','method_artifact':{'product_ref':dict(first),'application':'视角'}}]
    original = deepcopy(checks)
    _share_product_refs(checks)
    table = checks[0].pop('stage_product_refs')
    assert len(table) == 1
    for row in checks:
        proof = row['method_artifact']
        for app in proof.get('applications', [proof]):
            if isinstance(app['product_ref'], str):
                app['product_ref'] = table[app['product_ref']]
    assert checks == original


def test_frozen_speaker_fact_checks_its_actual_holder_version_and_prose_evidence_again():
    from dataclasses import asdict, replace
    from nw.story_models import Fact

    session, records, body, context, spoken = exchange()
    fact = Fact('archive','sender','旧库存有一封信，真正的寄信人一直使用化名。','lin','suspicion',1,(0,0,0),
                ({'draft_id':'prior','start':0,'end':18},))
    context['accepted_state'][2] = asdict(fact)
    basis = narration.scene_bases(records, context)['scene']['fact:2']
    frozen = narration.scene_check(spoken, 0, 1, body['pov'], {}, basis, 'first')
    assert 'state_sha256' not in frozen['binding']['observable']
    required = {frozen['narration_state_sha256']}
    narration.verify_scene_facts(required, [fact])
    for change in [dict(holder='yan'),dict(claim='fact'),dict(evidence=()),dict(value='来信的确已经烧毁')]:
        with pytest.raises(ValueError, match='MATERIAL_PRECONDITION'):
            narration.verify_scene_facts(required, [replace(fact, **change)])
