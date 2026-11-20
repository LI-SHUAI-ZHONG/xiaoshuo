"""Follow actual model-plan materialization, branch snapshots and draft acceptance."""
from copy import deepcopy
import json

import pytest

from nw.acceptance import accept_batch
from nw.config import Config
from nw.context.story import build_story_context, scene_scope
from nw.length_plan import (approved_book_plan, approved_length_budgets, design_context, draft_feedback,
                            frozen_scene_budget, manuscript_scene_ids, scene_length_feedback, validate_candidate)
from nw.planning import plan_input, propose_plan
from nw.story_state import adopt_story, current_head, revision_state
from nw.store import Store
from nw.task_models import Budget
from story_fixture import baseline, draft_for, proposal
from test_planning import Planner, apply


def budget(target, minimum, maximum, reason):
    return {'min_words': minimum, 'target_words': target, 'max_words': maximum, 'reason': reason}


def plan(scope, total=100):
    model = Planner(scope)
    for candidate in model.output['candidate_cards']:
        candidate['body']['length_plan'] = {'target_words': total, 'chapter_count': 1, 'reason': '一章内揭晓证据'}
        if scope == 'book':
            continue
        chapter = next(row for row in candidate['members'] if row['kind'] == 'chapter')
        chapter['body']['word_budget'] = budget(100, 95, 105, '章末才揭晓秘密')
        first = next(row for row in candidate['members'] if row['kind'] == 'scene')
        first['body']['word_budget'] = budget(40, 30, 50, '发现钥匙')
        second = deepcopy(first)
        second['key'] = 'second'
        second['body']['word_budget'] = budget(60, 50, 70, '校验证物')
        candidate['members'].append(second)
        candidate['chapters'][0]['scenes'].append({'index': 2, 'card': 'second', 'story_order': 2})
    return model


def setup_plans(store):
    store.init_project('[FAKE] 篇幅与证据')
    store.add_brief('查证\n\n立项参数：\n{"target_words":900}', '不得越过人物所知')
    adopt_story(store, baseline(), {})
    config = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
    inputs = {'plot_design': {'length_policy': {'target_words': 100}, 'length_auto': True}}
    direction = propose_plan(store, 1, 'book', plan('book'), config, Budget(1, 60000, 4000), governance_inputs=inputs)
    assert not approved_book_plan(store, revision_state(store, current_head(store, 'main')))
    apply(store, direction)
    chapter = propose_plan(store, 1, 'chapter', plan('chapter'), config, Budget(1, 60000, 4000),
                           parent_id=direction.id, governance_inputs=inputs)
    apply(store, chapter)
    return direction, chapter


def test_budget_handoff_preserves_original_brief_and_follows_approved_branch(tmp_path):
    with Store(tmp_path / 'work', create=True, test_mode=True) as store:
        _, chapter = setup_plans(store)
        frozen = plan_input(store, chapter.id)[1]
        assert frozen['length_context']['parent_plan']['chapter_count'] == 1
        assert frozen['length_override'] == {'target_words': 100}
        assert '900' in store.briefs()[0].text and '900' not in frozen['brief']['text']
        assert not frozen['governance_inputs']
        head = current_head(store, 'main')
        state = revision_state(store, head)
        assert approved_book_plan(store, state)['target_words'] == 100
        first, second = sorted(store.list('scene'), key=lambda s: s.index)
        package = build_story_context(store, first.id, scene_scope(store, first.id), 10000).package
        assert frozen_scene_budget(package)['target_words'] == 40
        assert '章末才揭晓秘密' not in json.dumps(package, ensure_ascii=False)
        assert json.loads(package['items'][0]['text'])['text'].endswith('{"chapter_count":1,"target_words":100}')
        budgets = approved_length_budgets(store, state)
        assert budgets['chapters'][first.chapter_id]['target_words'] == 100
        manifest = {'branch_id': 'main', 'state_revision': head.revision, 'candidate_delta_refs': []}
        assert scene_length_feedback(store, first.id, manifest, '甲 ' * 40) == []
        assert '本场' in scene_length_feedback(store, first.id, manifest, '甲')[0]

        tight = deepcopy(budgets)
        tight['scenes'][second.id] = budget(55, 50, 55, '有限的收束场景')
        assert '整章达标' in draft_feedback(store, first.id, state, '甲' * 30, tight)[0]
        assert not draft_feedback(store, first.id, state, '甲' * 40, tight)

        # A completed chapter is evaluated using accepted versions and this batch's candidate.
        first_text = draft_for(store, first.id, '甲' * 30)
        request = proposal(store, head, first_text, [])
        next_head = accept_batch(store, [request], head, 'first')
        state = revision_state(store, next_head)
        second_package = build_story_context(store, second.id, scene_scope(store, second.id), 10000).package
        chapter_projection = next(json.loads(item['text']) for item in second_package['items']
                                  if item['source'] == 'chapter:length')
        assert (chapter_projection['accepted_other_words'], chapter_projection['chapter_min_words'],
                chapter_projection['feasible_min_words'], chapter_projection['suggested_scene_words']) == (30, 95, 65, 65)
        assert chapter_projection['feasible_max_words'] <= frozen_scene_budget(second_package)['max_words']
        assert '章末才揭晓秘密' not in json.dumps(second_package, ensure_ascii=False)
        problems = draft_feedback(store, second.id, state, '乙 ' * 50, budgets)
        assert len(problems) == 1 and '整章实际 80' in problems[0] and '秘密' not in problems[0]
        assert not draft_feedback(store, second.id, state, '乙 ' * 65, budgets)
        wrong = draft_for(store, second.id, '乙' * 50)
        wrong_request = proposal(store, next_head, wrong, [])
        with pytest.raises(ValueError, match='整章实际 80'):
            accept_batch(store, [wrong_request], next_head, 'reject-short-complete-chapter')
        revised = draft_for(store, second.id, '乙' * 65)
        good_request = proposal(store, next_head, revised, [])
        final = accept_batch(store, [good_request], next_head, 'second')
        latest = revision_state(store, final)
        progress = design_context(store, frozen['brief'], latest, None)
        assert (progress['accepted_words'], progress['remaining_words'], progress['pending_planned_words']) == (95, 5, 0)
        retired = {**latest, 'stale_plan_scenes': [first.id]}
        assert design_context(store, frozen['brief'], retired, None)['accepted_words'] == 65


def test_invalid_or_unbalanced_model_budgets_require_redesign():
    context = {'policy': {'target_words': 100}, 'parent_plan': {}, 'accepted_words': 0,
               'pending_planned_words': 0, 'existing_chapters': {}}
    item = plan('chapter').output['candidate_cards'][0]
    validate_candidate(item, 'chapter', context)
    wrong = deepcopy(item)
    wrong['body']['length_plan']['target_words'] = 99
    with pytest.raises(ValueError, match='全书目标'):
        validate_candidate(wrong, 'chapter', context)
    wrong = deepcopy(item)
    del wrong['members'][-1]['body']['word_budget']
    with pytest.raises(ValueError, match='三个正整数'):
        validate_candidate(wrong, 'chapter', context)
    wrong = deepcopy(item)
    wrong['members'][-1]['body']['word_budget']['target_words'] = 55
    with pytest.raises(ValueError, match='之和'):
        validate_candidate(wrong, 'chapter', context)


def test_authored_chapter_and_scene_references_allow_distinct_function_based_allocations():
    context = {'policy': {'chapter_target_words': 90, 'scene_target_words': 50}, 'parent_plan': {},
               'accepted_words': 0, 'pending_planned_words': 0, 'existing_chapters': {}}
    item = plan('chapter').output['candidate_cards'][0]
    for row in item['members']:
        if row['kind'] in ('chapter', 'scene'):
            row['body']['word_budget']['reference_words'] = 90 if row['kind'] == 'chapter' else 50
    validate_candidate(item, 'chapter', context)
    item['members'][-1]['body']['word_budget']['reference_words'] = 45
    with pytest.raises(ValueError, match='reference_words'):
        validate_candidate(item, 'chapter', context)


def test_last_chapter_can_reach_target_with_allowed_stretch():
    # The chapter's target is 100, but its approved range can reach the book's 104.
    context = {'policy': {'target_words': 104}, 'parent_plan': {}, 'accepted_words': 0,
               'pending_planned_words': 0, 'existing_chapters': {}}
    validate_candidate(plan('chapter', 104).output['candidate_cards'][0], 'chapter', context)
    context['policy']['target_words'] = 120
    with pytest.raises(ValueError, match='不足全书目标'):
        validate_candidate(plan('chapter', 120).output['candidate_cards'][0], 'chapter', context)


def test_accepted_unbound_scenes_count_in_design_and_chapter_review(tmp_path):
    with Store(tmp_path / 'work', create=True, test_mode=True) as store:
        store.init_project('[FAKE] legacy')
        chapter = store.add_chapter(1, '旧章')
        old = store.add_scene(chapter.id, 1, '{}')
        retired = store.add_scene(chapter.id, 2, '{}')
        off_branch = store.add_scene(chapter.id, 3, json.dumps({'story': {
            'scene_ref': {'card_id': 'inactive', 'version': 1}}}))
        new = store.add_scene(chapter.id, 4, json.dumps({'story': {
            'scene_ref': {'card_id': 'active', 'version': 1}}}))
        slots = {s.id: {'draft_id': draft_for(store, s.id, '乙 ' * size).id}
                 for s, size in [(old, 22), (retired, 10), (off_branch, 7)]}
        state = {'slots': slots, 'settings': [{'card_id': 'active', 'version': 1}],
                 'stale_plan_scenes': [retired.id]}
        assert manuscript_scene_ids(store, state) == {old.id, new.id}
        assert manuscript_scene_ids(store, None) == {old.id, retired.id, off_branch.id, new.id}
        brief = {'text': '卷首\n\n立项参数：\n{"target_words": 60}'}
        projection = design_context(store, brief, state, None)
        assert (projection['accepted_words'], projection['remaining_words']) == (22, 38)
        store.accept(slots[old.id]['draft_id'])
        assert design_context(store, brief, None, None)['accepted_words'] == 22
        budgets = {'scenes': {}, 'chapters': {chapter.id: budget(60, 58, 62, '兑现')}}
        assert not draft_feedback(store, new.id, state, '甲' * 38, budgets)
        assert '整章实际 52' in draft_feedback(store, new.id, state, '甲' * 30, budgets)[0]


def test_long_book_model_input_keeps_totals_and_only_relevant_chapter_rows():
    from nw.materials.stage_input import model_package
    existing = {str(i): {'allocated_words': 100, 'open_scenes': int(i > 100)} for i in range(1, 201)}
    existing['2']['word_budget'] = budget(100, 90, 110, '当前任务直接上游')
    context = {'existing_chapters': existing, 'accepted_words': 10000, 'parent_chapters': [2]}
    cards = [{'card_id': str(i), 'body': {'goal': '揭示身份', 'word_budget': budget(100, 90, 110, '已归档')}}
             for i in range(200)]
    original = {'length_context': context, 'approved_cards': cards}
    projected = model_package(original)
    short = projected['length_context']
    assert set(short['existing_chapters']) == {'2', '100', '101', '102', '103', '104', '199', '200'}
    assert short['existing_chapters']['2']['word_budget'] == existing['2']['word_budget']
    assert short['accepted_words'] == 10000 and short['other_chapter_count'] == 192
    assert all(card['body'] == {'goal': '揭示身份'} for card in projected['approved_cards'])
    assert len(original['length_context']['existing_chapters']) == 200
    assert 'word_budget' in original['approved_cards'][0]['body']


def test_final_volume_includes_only_available_space_in_an_existing_chapter():
    # Branch chapter numbers can have gaps after retiring a previous direction.
    context = {'policy': {'target_words': 90}, 'parent_plan': {}, 'accepted_words': 30,
               'pending_planned_words': 20, 'pending_max_words': 20,
               'existing_chapters': {'4': {'word_budget': budget(55, 45, 60, '追查'), 'allocated_words': 50,
                                           'accepted_words': 30, 'pending_max_words': 20}}}
    result = {'body': {'length_plan': {'chapter_count': 2, 'target_words': 90, 'reason': '两章兑现'}},
              'members': [{'key': key, 'kind': kind, 'body': {'word_budget': words}}
                          for key, kind, words in [('previous', 'scene', budget(5, 2, 30, '补充前证')),
                                                  ('final', 'chapter', budget(20, 15, 20, '兑现')),
                                                  ('ending', 'scene', budget(20, 15, 20, '揭晓'))]],
              'chapters': [{'index': 4, 'card': None, 'scenes': [{'card': 'previous'}]},
                           {'index': 7, 'card': 'final', 'scenes': [{'card': 'ending'}]}]}
    with pytest.raises(ValueError, match='不足全书目标'):
        validate_candidate(result, 'volume', context)
    result['body']['length_plan']['target_words'] = context['policy']['target_words'] = 80
    validate_candidate(result, 'volume', context)
