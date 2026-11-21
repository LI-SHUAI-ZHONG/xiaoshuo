"""Scene advancement must have an eligible cause and a distinct, traceable change."""
from copy import deepcopy
import json

import pytest

from nw.materials import chapter_progress as progress
from nw.materials.phase_scene_checks import selected_checks
from nw.materials.phase_schema import schema
from nw.story_models import Fact
from nw.task_models import content_sha256


def designs():
    nodes = [{'id': key, 'actors': [key], 'setting': setting, 'goal': '查验水情', 'obstacle': '雨幕',
              'completion_condition': '找到水尺'} for key, setting in [('patrol', '巡河人正在涨水的河边值守'), ('gong', '村民在等锣声')]]
    first = {'pov': 'yan', 'entering_state': '只听说有人要开闸', 'planned_result': '发现水尺移过位置'}
    second = {'pov': 'lin', 'entering_state': '在等撤离名单', 'planned_result': '同意暂缓敲锣'}
    bodies = [{'key': 'river', 'body': first}, {'key': 'bank', 'body': second}]
    places = [{'card': s['key'], 'index': i, 'story_order': i + 5} for i, s in enumerate(bodies, 1)]
    plan = {'members': bodies, 'chapters': [{'index': 2, 'card': 'chapter_2', 'scenes': places}],
        'selected_events': [{'scene': s['key'], 'event': node['id']} for s, node in zip(bodies, nodes, strict=True)],
        'selected_actions': [],
        'scene_progress': [{'scene': s['key'], 'origin': 'discovery', 'stimulus': s['body']['planned_result'],
            'basis_ref': 'event:' + node['id'], 'basis_quote': node['setting'], 'connection': 'unresolved',
            'change': 'knowledge', 'next_pressure': '后续计划仍有待查证'} for s, node in zip(bodies, nodes, strict=True)]}
    records = {'plot_design': {'products': {'event_nodes': nodes}}, 'scene_design': {'products': plan}}
    change = {'entity_id': 'gate', 'predicate': 'time', 'holder': 'yan', 'claim': 'suspicion',
              'story_order': 2, 'disclosure_order': [1, 1, 0], 'new_value': '起疑昨夜开过闸'}
    context = {'chapter_progress_policy': progress.POLICY,
               'chapter_changes': progress.chapter_changes({'character_changes': [change]})}
    return plan, records, context


def test_new_cast_member_cannot_take_over_a_previous_holders_progress_by_reusing_their_local_key():
    plan, records, context = designs()
    plan['scene_progress'][0].update(basis_ref='prior:0', basis_quote='起疑昨夜开过闸', origin='reflection')
    records['character_design'] = {'products':{'members':[{'kind':'character','key':'yan'}]}}
    with pytest.raises(ValueError, match='不能继承'):
        progress.validate(plan, records, context)


def test_review_and_writer_only_receive_the_current_scenes_approved_progress():
    plan, records, context = designs()
    plan['scene_progress'][0].update(basis_ref='prior:0', basis_quote='起疑昨夜开过闸', origin='reflection')
    progress.validate(plan, records, context)
    records['state_transition'] = {'products': {'patches': [
        {'scene': 'river', 'planned_result': '水尺底下露出刚削过的木榫'}]}}
    [first] = selected_checks(records, 'river', context=context)
    [last] = selected_checks(records, 'bank', context=context)
    body = json.loads(first['binding']['observable'])
    assert body['candidate_result'] == '水尺底下露出刚削过的木榫'
    assert body['personal_basis']['claim'] == 'suspicion' and body['connection'] == 'unresolved'
    assert '章首问题' in first['binding']['check'] and '章末解决' not in first['binding']['check']
    assert '章末解决' in last['binding']['check'] and '章首问题' not in last['binding']['check']
    assert '起疑昨夜' not in last['binding']['observable']
    assert '后续计划仍有待查证' not in str(first['binding'])
    assert not selected_checks(records, 'river', context={})
    assert 'scene_progress' in schema('scene_design', [], allow_requests=False, chapter_progress=True)['properties']['products']['required']
    assert 'scene_progress' not in schema('scene_design', [], allow_requests=False)['properties']['products']['properties']


def test_setup_may_close_quietly_but_a_whole_chapter_needs_some_advance():
    plan, records, context = designs()
    context['scope'] = 'chapter'
    plan['scene_progress'][1]['change'] = 'setup'
    plan['members'][1]['body']['planned_result'] = plan['members'][1]['body']['entering_state']
    progress.validate(plan, records, context)
    plan['scene_progress'][0]['change'] = 'setup'
    with pytest.raises(ValueError, match='完整章'):
        progress.validate(plan, records, context)
    context['scope'] = 'scene'
    progress.validate(plan, records, context)


def test_an_open_question_can_be_selected_for_a_specific_event_with_its_prior_review():
    plan, records, context = designs()
    review = {'draft_ref': {'id': 'accepted'}, 'delta_id': 'approved-delta', 'review_run_id': 'accepted-review',
              'disclosure_order': [1, 1, 0], 'possible_next_pressure': '仍须查清水尺是谁动过',
              'evidence': [{'quote': '木头还在滴水。'}]}
    options = progress.chapter_openings({'reviewed_progress': [dict(review, evidence=[]), review]})
    assert list(options) == ['open:1']
    link = {'ref': 'open:1', 'event': 'patrol', 'reason': '水尺异常使村民误判水情',
            'target_quote': '查验水情'}
    plot = records['plot_design']['products']
    context['chapter_openings'] = options
    plot['continuations'] = [link]
    progress.validate_continuations(plot, options)
    [proof] = progress.scene_check(records, 'river', context)['continuations']
    assert proof['prior']['evidence'] == review['evidence']
    assert '仍须查清' not in str(progress.scene_check(records, 'river', context)['binding'])
    assert 'continuations' not in progress.scene_check(records, 'bank', context)
    checks = [progress.scene_check(records, 'river', context)]
    progress.verify_current(checks, [], {'s': {'draft_id': 'accepted', 'delta_id': 'approved-delta'}})
    with pytest.raises(ValueError, match='已接受稿已经改变'):
        progress.verify_current(checks, [], {'s': {'draft_id': 'replaced'}})
    with pytest.raises(ValueError, match='已接受稿已经改变'):
        progress.verify_current(checks, [], {'s': {'draft_id': 'accepted', 'delta_id': 'revised-delta'}})
    progress.validate(plan, records, context)
    original = deepcopy(plan['selected_events'])
    plan['selected_events'][0]['event'] = 'gong'
    plan['scene_progress'][0].update(basis_ref='event:gong', basis_quote='村民在等锣声')
    with pytest.raises(ValueError, match='实际选中'):
        progress.validate(plan, records, context)
    plan['selected_events'] = original
    plan['scene_progress'][0].update(basis_ref='event:patrol', basis_quote='巡河人正在涨水的河边值守')
    options['open:1']['disclosure_order'] = [2, 2, 0]
    with pytest.raises(ValueError, match='前章问题出现之前'):
        progress.validate(plan, records, context)
    plot['continuations'] = [dict(link, target_quote='不是所选节点')]
    with pytest.raises(ValueError, match='新事件'):
        progress.validate_continuations(plot, options)
    plot['continuations'] = []
    progress.validate_continuations(plot, options)


def test_accepted_current_state_and_evidence_must_still_match_at_writing_time():
    plan, records, context = designs()
    plan['scene_progress'][0].update(basis_ref='prior:0', basis_quote='起疑昨夜开过闸')
    evidence = ({'draft_id': 'accepted-v1'},)
    source = context['chapter_changes']['prior:0']
    source['evidence_sha256'] = content_sha256(evidence)
    checks = selected_checks(records, 'river', context=context)
    def fact(value, holder='yan', spans=evidence):
        return Fact('gate', 'time', value, holder, 'suspicion', 2, (1, 1, 0), spans)
    progress.verify_current(checks, [fact(source['text'])], {})
    for facts in ([], [fact('已否定此想法')], [fact(source['text'], 'READER')],
                  [fact(source['text'], spans=({'draft_id': 'replaced-v2'},))]):
        with pytest.raises(ValueError, match='MATERIAL_PRECONDITION'):
            progress.verify_current(checks, facts, {})
    accepted = {**source, 'new_value': '只让读者得知', 'holder': 'READER'}
    assert not progress.chapter_changes({'identity_disclosures': [accepted]})


def test_world_event_can_change_the_situation_but_is_learned_by_a_current_character():
    plan, records, context = designs()
    context['chapter_changes']['prior:0'].update(holder='WORLD', claim='fact', text='闸门已经落下')
    row = plan['scene_progress'][0]
    row.update(basis_ref='prior:0', basis_quote='闸门已经落下', origin='incident', change='situation')
    progress.validate(plan, records, context)
    for origin in ('reflection', 'continuation', 'incident'):
        row.update(change='knowledge', origin=origin)
        with pytest.raises(ValueError, match='客观处境'):
            progress.validate(plan, records, context)
    row.update(origin='conversation', stimulus='听到巡河人喊落闸，转身去找水尺。')
    progress.validate(plan, records, context)
    assert 'personal_basis' not in json.loads(progress.scene_check(records, 'river', context)['binding']['observable'])


def test_a_scene_relying_on_a_living_witness_must_be_replanned_after_confirmed_death():
    plan, records, context = designs()
    history = {'entity_id': 'witness', 'predicate': 'alive', 'holder': 'WORLD', 'claim': 'fact',
               'new_value': True, 'story_order': 1, 'disclosure_order': [1, 1, 0]}
    context['chapter_changes'] = progress.chapter_changes({'changes': [history]})
    plan['scene_progress'][0].update(basis_ref='prior:0', basis_quote='true', change='knowledge',
                                     origin='conversation', stimulus='当面问巡河人昨夜的水位。')
    progress.validate(plan, records, context)
    checks = selected_checks(records, 'river', context=context)
    def witness(alive):
        return Fact('witness', 'alive', alive, 'WORLD', 'fact', 1, (1, 1, 0), ())
    progress.verify_current(checks, [witness(True)], {})
    with pytest.raises(ValueError, match='MATERIAL_PRECONDITION'):
        progress.verify_current(checks, [witness(False)], {})


@pytest.mark.parametrize('corruption', ['other_event', 'wrong_quote', 'private', 'future', 'retracted',
                                         'duplicate', 'missing', 'same_result'])
def test_advancement_rejects_borrowed_causes_and_missing_change(corruption):
    plan, records, context = designs()
    row = plan['scene_progress'][0]
    if corruption == 'other_event':
        row.update(basis_ref='event:gong', basis_quote='村民在等锣声')
    elif corruption == 'wrong_quote':
        row['basis_quote'] = '一件完全不同的事'
    elif corruption in ('private', 'future', 'retracted'):
        row.update(basis_ref='prior:0', basis_quote='起疑昨夜开过闸')
        old = context['chapter_changes']['prior:0']
        if corruption == 'private':
            old['holder'] = 'lin'
        elif corruption == 'future':
            old['disclosure_order'] = [2, 2, 0]
        else:
            context['chapter_changes']['prior:1'] = {**old, 'story_order': 4, 'text': None}
    elif corruption == 'duplicate':
        plan['scene_progress'][1] = deepcopy(row)
    elif corruption == 'missing':
        plan['scene_progress'].pop()
    else:
        body = plan['members'][0]['body']
        body['planned_result'] = body['entering_state']
    with pytest.raises(ValueError, match='MATERIAL_STAGE'):
        progress.validate(plan, records, context)
