
from dataclasses import asdict
import json

import pytest

from nw.cards import decide_card, read_card
from nw.config import Config
from nw.context.story import build_story_context, scene_scope
from nw.llm.base import GenResult
from nw.llm.fake import FakeProvider
from nw.planning import apply_plan, propose_plan, show_plan
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline


class Planner(FakeProvider):
    def __init__(self, scope, *, chapter=1, open_rule=False):
        super().__init__()
        self.output = {'scope': scope, 'candidate_cards': []}
        for i, choice in enumerate(('追查封条', '结盟换证'), start=1):
            self.output['candidate_cards'].append({
                'kind': 'plot', 'body': {
                    'title': choice, 'reader_promise': '制度谜团', 'protagonist_want': '查明暗井真相',
                    'conflict': '守井人阻挠', 'resistance': '禁止接近井底', 'choice': choice,
                    'cost': f'放弃一份证据{i}', 'consequence': f'卷入调查{i}', 'ending_direction': '查明真相',
                },
                'members': [
                    {'key': 'yan', 'kind': 'character', 'body': {
                        'name': '沈砚', 'role': '主角', 'want': '查封条', 'visibility': 'public'}},
                    {'key': 'ch', 'kind': 'chapter', 'body': {'title': choice, 'goal': '入井', 'consequence': '受阻'}},
                    {'key': 'scene', 'kind': 'scene', 'body': {
                        'title': '暗井', 'goal': '调查证物', 'pov': 'yan', 'characters': ['yan'],
                        'conflict': '封条限制进出', 'choice': choice, 'planned_result': '发现旧封条',
                        'entering_state': '沈砚独自入井', 'allowed_disclosure': '可展示封条',
                        'character_goals': {'yan': '查封条'}}},
                ] if scope != 'book' else [],
                'chapters': [{'index': chapter, 'card': 'ch', 'scenes': [
                    {'index': 1, 'card': 'scene', 'story_order': 1}]}] if scope != 'book' else [],
                'open_world_rules': ['封条开启的代价未定'] if open_rule else [],
            })

    def generate(self, messages, **kwargs):
        self.calls.append(messages)
        return GenResult(json.dumps(self.output, ensure_ascii=False), 'complete', {}, 'test-plan', {'isolated_test': True})


@pytest.fixture
def book(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('制度谜团，主角调查暗井', '受限第三人称')
        adopt_story(store, baseline(), {})
        yield store


def propose(store, scope='book', parent=None, chapter=1, open_rule=False, branch='main'):
    provider = Planner(scope, chapter=chapter, open_rule=open_rule)
    config = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory,source_driven=False)
    return propose_plan(store, 1, scope, provider, config, Budget(1, 45000, 2000),
                        parent_id=parent, branch=branch)


def apply(store, proposal):
    ref = proposal.candidate_cards[0]
    decision = decide_card(store, ref, 'approved', '选第一案')
    return apply_plan(store, proposal.id, decision.id)


def test_brief_generates_distinct_proposals_without_scene_input(book):
    proposal = propose(book)
    assert len(proposal.candidate_cards) == 2
    roots = [read_card(book, ref)['body'] for ref in proposal.candidate_cards]
    assert len({body['choice'] for body in roots}) == 2
    assert show_plan(book, proposal.id) == proposal


def test_proposal_does_not_mutate_canon(book):
    from nw.story_state import current_head
    before = current_head(book)
    proposal = propose(book)
    assert current_head(book) == before
    assert not book.list('chapter') and not book.list('scene')
    assert all(read_card(book, ref)['status'] == 'proposal' for ref in proposal.candidate_cards)


def test_plan_has_choice_cost_and_consequences(book):
    proposal = propose(book)
    for ref in proposal.candidate_cards:
        root = read_card(book, ref)['body']
        assert root['choice'] and root['cost'] and root['consequence']


def test_apply_requires_matching_author_decision(book):
    a, b = propose(book), propose(book)
    decision = decide_card(book, a.candidate_cards[0], 'approved', '仅选 A')
    with pytest.raises(ValueError, match='decision'):
        apply_plan(book, b.id, decision.id)


def test_apply_twice_reuses_chapter_scene_ids(book):
    direction = propose(book)
    apply(book, direction)
    chapter = propose(book, 'chapter', parent=direction.id)
    ref = chapter.candidate_cards[0]
    decision = decide_card(book, ref, 'approved', '采用')
    first = apply_plan(book, chapter.id, decision.id)
    assert first == apply_plan(book, chapter.id, decision.id)
    assert len(book.list('chapter')) == len(book.list('scene')) == 1
    [scene] = book.list('scene')
    assert build_story_context(book, scene.id, scene_scope(book, scene.id), 10000).card_refs


def test_missing_critical_world_rule_stays_open(book):
    direction = propose(book)
    apply(book, direction)
    candidate = propose(book, 'chapter', parent=direction.id, open_rule=True)
    assert candidate.findings[0]['status'] == 'OPEN'
    assert candidate.findings[0]['severity'] == 'hard'
    apply(book, candidate)
    [scene] = book.list('scene')
    with pytest.raises(ValueError, match='OPEN_DESIGN_QUESTIONS'):
        build_story_context(book, scene.id, scene_scope(book, scene.id), 10000)


def test_replan_marks_affected_descendants(book):
    from nw.story_state import current_head, fork_story
    direction = propose(book)
    apply(book, direction)
    chapter = propose(book, 'chapter', parent=direction.id)
    apply(book, chapter)
    [old] = book.list('scene')
    fork_story(book, current_head(book), 'alternate')
    replacement = propose(book, 'replan', parent=direction.id, chapter=2, branch='alternate')
    apply(book, replacement)
    assert show_plan(book, replacement.id).application['stale_scenes'] == [old.id]
    with pytest.raises(ValueError, match='STALE_PLAN'):
        build_story_context(book, old.id, scene_scope(book, old.id, 'alternate'), 10000)
    assert build_story_context(book, old.id, scene_scope(book, old.id), 10000).package


def test_apply_rolls_back_member_decisions_on_scene_conflict(book):
    direction = propose(book)
    apply(book, direction)
    with book.connection:
        # Use an existing chapter and occupy the target scene number.
        existing = book.add_chapter(1, '既有章')
        book.add_scene(existing.id, 1, '{}')
    provider = Planner('scene')
    for candidate in provider.output['candidate_cards']:
        candidate['members'] = [row for row in candidate['members'] if row['kind'] != 'chapter']
        candidate['chapters'][0]['card'] = None
    config = Config('fake', 'http://localhost', 'test', '', 5, {}, book.directory,source_driven=False)
    candidate = propose_plan(book, 1, 'scene', provider, config, Budget(1, 45000, 2000),
                             parent_id=direction.id)
    decision = decide_card(book, candidate.candidate_cards[0], 'approved', '选定')
    with pytest.raises(ValueError, match='PLAN_COORDINATE_CONFLICT'):
        apply_plan(book, candidate.id, decision.id)
    assert len(book.list('scene')) == 1
    assert show_plan(book, candidate.id).application is None
    for raw in candidate.materialization[0]['members'].values():
        from nw.story_models import CardRef
        assert read_card(book, CardRef(**raw))['status'] == 'proposal'


def test_plan_retry_keeps_frozen_messages_and_charges_budget(book):
    from nw.call_budget import read_budget
    from nw.planning import plan_input, retry_plan
    from nw.tasks import read_task

    provider = Planner('book')
    original_choice = provider.output['candidate_cards'][1]['body']['choice']
    provider.output['candidate_cards'][1]['body']['choice'] = provider.output['candidate_cards'][0]['body']['choice']
    config = Config('fake', 'http://localhost', 'test', '', 5, {}, book.directory,source_driven=False)
    with pytest.raises(ValueError, match='INVALID') as failure:
        propose_plan(book, 1, 'book', provider, config, Budget(2, 45000, 2000))
    original = str(failure.value).rsplit(' ', 1)[-1]
    assert read_task(book, original).validation == 'INVALID'
    provider.output['candidate_cards'][1]['body']['choice'] = original_choice
    recovered = retry_plan(book, original, provider, config)
    assert provider.calls[0] == provider.calls[1]
    assert recovered.id != original
    assert plan_input(book, original) == plan_input(book, recovered.id)
    assert read_budget(book, f'plan:{original}').used_calls == 2


def test_child_design_preserves_unresolved_parent_rules(book):
    direction = propose(book, open_rule=True)
    apply(book, direction)
    chapter = propose(book, 'chapter', parent=direction.id)
    assert chapter.findings[0]['code'] == 'OPEN_WORLD_RULE'
    apply(book, chapter)
    [scene] = book.list('scene')
    with pytest.raises(ValueError, match='OPEN_DESIGN_QUESTIONS'):
        build_story_context(book, scene.id, scene_scope(book, scene.id), 10000)


def test_replan_cannot_retire_an_accepted_descendant(book):
    from nw.acceptance import accept_batch
    from nw.story_state import current_head, fork_story
    from story_fixture import draft_for, proposal

    direction = propose(book)
    apply(book, direction)
    chapter = propose(book, 'chapter', parent=direction.id)
    apply(book, chapter)
    [old] = book.list('scene')
    draft = draft_for(book, old.id)
    head = current_head(book)
    accepted = accept_batch(book, [proposal(book, head, draft, [])], head, 'accept-scene')
    fork = fork_story(book, accepted, 'alternate')
    replacement = propose(book, 'replan', parent=direction.id, chapter=2, branch='alternate')
    with pytest.raises(ValueError, match='REPLAN_ACCEPTED_DESCENDANTS'):
        apply(book, replacement)
    assert show_plan(book, replacement.id).application is None
    assert current_head(book, 'alternate') == fork
    assert book.list('scene') == [old]
