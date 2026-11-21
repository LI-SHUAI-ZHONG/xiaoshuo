from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from nw.materials import action_review, cast_fulfillment as cast
from nw.materials.cast_demands import POLICY
from nw.materials.phase_schema import schema
from nw.story_delta import draft_ref
from test_material_action_review import draft, review_run, span


def case():
    duty = {'id': 'permit', 'event': '确认丢失的登记', 'obstacle': '记录散在两本账上',
            'action': '把两份封存单平铺核对编号', 'result': '找出少了一页的登记册'}
    body = {'title': '查档', 'pov': 'visitor', 'characters': ['clerk', 'bystander']}
    node = {'id': 'lookup', 'goal': duty['event'], 'obstacle': duty['obstacle'],
            'actors': ['clerk', 'visitor'], 'completion_condition': '找到账簿缺页的原因'}
    plot = {'event_nodes': [node], 'cast_events': [{'demand': 'permit', 'event': 'lookup'}]}
    candidate = {'id': 'check', 'actor': 'clerk', 'event': 'follow',
                 'steps': [{'action': duty['action'], 'result': duty['result']}]}
    scene = {'members': [{'key': 'desk', 'body': body}], 'selected_actions': [{'scene': 'desk', 'action': 'check'}],
             'selected_events': [{'scene': 'desk', 'event': 'follow'}],
             'cast_payoffs': [{'demand': 'permit', 'scene': 'desk', 'action': 'check', 'step_index': 0}]}
    products = {'world_design': {'cast_demands': [duty]}, 'character_design': {'members': [],
                'cast_assignments': [{'demand': 'permit', 'actor': 'clerk'}]}, 'plot_design': plot,
                'event_design': {'candidates': [{'id': 'follow', 'predecessor': 'lookup'}]},
                'action_design': {'candidates': [candidate]}, 'scene_design': scene}
    context = {'cast_demand_policy': POLICY, 'approved_cards': [{'card_id': 'clerk', 'kind': 'character',
               'body': {'name': '陆昭', 'scene_function': '前章提供钥匙', 'background': '曾代看档库'}}]}
    return {stage: {'products': value} for stage, value in products.items()}, context


def test_new_duty_uses_existing_actor_and_selected_successor_without_rewriting_card():
    records, context = case()
    original = deepcopy(context['approved_cards'])
    for stage in cast.SCHEMAS:
        cast.validate(stage, records[stage]['products'], records, context)
        field = 'cast_events' if stage == 'plot_design' else 'cast_payoffs'
        assert field in schema(stage, [], allow_requests=False, cast_demand=True)['properties']['products']['required']
        assert field not in schema(stage, [], allow_requests=False)['properties']['products']['properties']
    check, = cast.scene_checks(records, 'desk', context)
    assert check['method_artifact']['action_ref'] == 'check'
    assert check['method_artifact']['event'] == 'follow'
    actual = records['action_design']['products']['candidates'][0]
    selected = {'id': check['action_check'], 'method_artifact': actual,
                'binding': {'observable': json.dumps({'actor': 'card_9', 'steps': actual['steps']})}}
    role = cast.performance(check, [check, selected])
    assert (role['actor'], role['action'], role['candidate_result']) == (
        'card_9', '把两份封存单平铺核对编号', '找出少了一页的登记册')
    assert context['approved_cards'] == original
    assert cast.scene_checks(records, 'absent', context) == []


@pytest.mark.parametrize('change', ['actor', 'event', 'quote', 'missing'])
def test_plot_rejects_appearance_or_unrelated_work(change):
    records, context = case()
    plot = records['plot_design']['products']
    node = plot['event_nodes'][0]
    if change == 'actor':
        node['actors'] = ['visitor']
    if change == 'event':
        plot['cast_events'][0]['event'] = 'another'
    if change == 'quote':
        node.update(goal='向行人推销糕点', obstacle='顾客赶路')
    if change == 'missing':
        plot['cast_events'] = []
    with pytest.raises(ValueError):
        cast.validate('plot_design', plot, records, context)


@pytest.mark.parametrize('change', ['wrong_actor', 'wrong_predecessor', 'wrong_step', 'wrong_action',
                                    'wrong_result', 'other_scene', 'unselected', 'blanket', 'omission'])
def test_scene_requires_this_person_to_cause_the_promised_result(change):
    records, context = case()
    scene = records['scene_design']['products']
    row = scene['cast_payoffs'][0]
    act = records['action_design']['products']['candidates'][0]
    if change == 'wrong_actor':
        act['actor'] = 'visitor'
    if change == 'wrong_predecessor':
        records['event_design']['products']['candidates'][0]['predecessor'] = 'unrelated'
    if change == 'wrong_step':
        row['step_index'] = True
    if change == 'wrong_action':
        act['steps'][0]['action'] = '向客人报出糕点价钱'
    if change == 'wrong_result':
        act['steps'][0]['result'] = '客人买了三块糕'
    if change == 'other_scene':
        row['scene'] = 'elsewhere'
    if change == 'unselected':
        row['action'] = 'some_other_candidate'
    if change == 'blanket':
        scene['cast_payoffs'].append(dict(row))
    if change == 'omission':
        scene['cast_payoffs'].clear()
    with pytest.raises(ValueError):
        cast.validate('scene_design', scene, records, context)


def test_different_actions_can_serve_one_duty_but_may_not_conscript_unassigned_bystanders():
    records, context = case()
    scene = records['scene_design']['products']
    actions = records['action_design']['products']['candidates']
    actions.append(dict(actions[0], id='other'))
    scene['selected_actions'].append({'scene': 'desk', 'action': 'other'})
    cast.validate('scene_design', scene, records, context)
    actions[1]['actor'] = 'bystander'
    with pytest.raises(ValueError, match='独立行动'):
        cast.validate('scene_design', scene, records, context)


def test_action_design_returns_before_scene_selection_when_only_unrelated_steps_exist():
    records, context = case()
    design = records['action_design']['products']
    cast.validate('action_design', design, records, context)
    design['candidates'][0]['steps'][0]['action'] = '向来人推销点心'
    with pytest.raises(ValueError, match='可供选场'):
        cast.validate('action_design', design, records, context)


def test_independent_review_requires_this_actors_passage_and_can_identify_a_separate_result(draft):
    draft = replace(draft, text='陆昭把两张封存单平铺并核对编号。她循着缺号找出了少一页的登记册。')
    records, context = case()
    check, = cast.scene_checks(records, 'desk', context)
    action = {'id': check['action_check'], 'profile': 'method_work'}
    contract = {'draft': asdict(draft_ref(draft)), 'checks': [action, check]}
    split = draft.text.index('。') + 1
    performed, result = span(draft, 0, split), span(draft, split, len(draft.text))
    action_review_row = {'id': action['id'], 'status': 'pass', 'reason': '辨认编号的行动确已发生', 'evidence': [performed]}
    def checked(proof):
        review = {'id': check['id'], 'status': 'pass', 'reason': '两份单据的编号让陆昭找到缺页', 'evidence': proof}
        return action_review.review_result(review_run(draft, [review, action_review_row]), contract, draft, None)
    assert checked([performed, result])['recommendation'] == 'pass'
    assert checked([result])['recommendation'] == 'revise'
    assert checked([span(draft, split - 1, len(draft.text))])['recommendation'] == 'revise'


def test_reviewers_can_cite_the_same_specific_action_excerpt_inside_a_sentence(draft):
    draft = replace(draft, text='众人还没走远，风声里陆昭封好登记册。')
    excerpt = span(draft, draft.text.index('陆昭'), len(draft.text))
    assert cast._shares_passage(excerpt, excerpt, draft)


@pytest.mark.parametrize('brief_action', ['她签了字。', '“走！”'])
def test_two_meaningful_passages_can_share_only_a_short_action_or_line(draft, brief_action):
    text = '陆昭接过来人的通行文书。' + brief_action + '门房立即撤掉门口的锁链。'
    draft = replace(draft, text=text)
    start = text.index(brief_action)
    end = start + len(brief_action)
    records, context = case()
    duty = records['world_design']['products']['cast_demands'][0]
    duty.update(event='决定是否放行来人', obstacle='门房等待指示', action=brief_action, result='门房开锁放行')
    records['action_design']['products']['candidates'][0]['steps'] = [{'action': duty['action'], 'result': duty['result']}]
    check, = cast.scene_checks(records, 'desk', context)
    contract = {'draft': asdict(draft_ref(draft)), 'checks': [check, {'id': check['action_check'], 'profile': 'method_work'}]}
    reviews = [{'id': check['id'], 'status': 'pass', 'reason': '此举促使门房开门', 'evidence': [span(draft, start, len(text))]},
               {'id': check['action_check'], 'status': 'pass', 'reason': '已经有明确举动', 'evidence': [span(draft, 0, end)]}]
    assert action_review.review_result(review_run(draft, reviews), contract, draft, None)['recommendation'] == 'pass'
