"""Use applied plans and exact branch approvals to resolve immediate ancestry."""
import pytest

from nw.cards import decide_card
from nw.config import Config
from nw.planning import propose_plan
from nw.store import Store
from nw.story_models import CardRef
from nw.story_state import adopt_story, apply_settings, current_head, fork_story
from nw.task_models import Budget
from story_fixture import baseline
from test_planning import Planner, apply, propose


@pytest.fixture
def book(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('[FAKE] 全书卷章层级')
        store.add_brief('[FAKE] 调查暗井记录', '保持已明示的线索。')
        adopt_story(store, baseline(), {})
        yield store


def volume(store, parent, index=1, *, ending=None):
    model = Planner('volume', chapter=index)
    body = {'title': '[FAKE] 证据交接卷', 'goal': '追回登记', 'turn': '回执丢失'}
    if ending:
        body['ending_direction'] = ending
    for item in model.output['candidate_cards']:
        item['members'].append({'key': 'vol', 'kind': 'volume', 'body': body.copy()})
    cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
    result = propose_plan(store, 1, 'volume', model, cfg, Budget(1, 45000, 2000), parent_id=parent)
    apply(store, result)
    return result


def test_applied_immediate_parent_chain_retains_versions_and_approval(book):
    from nw.plan_hierarchy import approved_parent, parent_chain

    top = propose(book)
    assert approved_parent(book, 'volume') is None
    apply(book, top)
    middle = volume(book, top.id)
    chapter = propose(book, 'chapter', parent=middle.id, chapter=2)
    apply(book, chapter)
    start_count = book.connection.total_changes
    assert approved_parent(book, 'volume') == top.id
    assert approved_parent(book, 'chapter') == middle.id
    assert approved_parent(book, 'scene') == chapter.id
    captures = parent_chain(book, 'scene', chapter.id)
    assert [(item['scope'], item['proposal_id']) for item in captures] == [
        ('book', top.id), ('volume', middle.id), ('chapter', chapter.id)]
    assert captures[1]['title'] == '[FAKE] 证据交接卷'
    artifact = captures[1]['artifact']
    assert artifact['kind'] == 'volume' and artifact['body'] == {
        'title': '[FAKE] 证据交接卷', 'goal': '追回登记', 'turn': '回执丢失'}
    assert artifact['ref']['card_id'] == middle.materialization[0]['members']['vol']['card_id']
    assert len(artifact['ref']['sha256']) == 64
    for proof in captures:
        assert proof['root']['version'] == 1 and len(proof['root']['sha256']) == 64
        row = book.connection.execute(
            'SELECT decision_id FROM plan_applications WHERE proposal_id=?', (proof['proposal_id'],)).fetchone()
        assert proof['decision_id'] == row['decision_id']
    assert book.connection.total_changes == start_count


def test_strict_handoff_rejects_wrong_scope_and_missing_ancestor(book):
    from nw.plan_hierarchy import approved_parent, parent_chain

    top = propose(book)
    apply(book, top)
    with pytest.raises(ValueError, match='PLAN_PARENT_REQUIRED.*卷'):
        approved_parent(book, 'chapter', proposal_id=top.id)
    direct = propose(book, 'chapter', parent=top.id)
    apply(book, direct)
    assert approved_parent(book, 'scene') is None
    with pytest.raises(ValueError, match='PLAN_PARENT_REQUIRED.*卷'):
        parent_chain(book, 'scene', direct.id)


def test_only_active_branch_and_approved_ancestor_are_eligible(book):
    from nw.plan_hierarchy import approved_parent, parent_chain

    top = propose(book)
    apply(book, top)
    fork_story(book, current_head(book), 'alternate')
    middle = volume(book, top.id)
    assert approved_parent(book, 'chapter', 'alternate') is None
    with pytest.raises(ValueError, match='STALE_PLAN_PARENT'):
        parent_chain(book, 'chapter', middle.id, branch='alternate')
    decide_card(book, top.candidate_cards[0], 'disabled', '[FAKE] 已撤销全书方向')
    assert approved_parent(book, 'chapter') is None
    with pytest.raises(ValueError, match='STALE_PLAN_PARENT'):
        parent_chain(book, 'chapter', middle.id)


def test_automatic_routing_uses_the_latest_active_book_and_its_descendants(book):
    from nw.plan_hierarchy import approved_parent, parent_chain

    first = propose(book)
    apply(book, first)
    old_volume = volume(book, first.id)
    assert approved_parent(book, 'chapter') == old_volume.id
    current = propose(book)
    apply(book, current)
    assert approved_parent(book, 'volume') == current.id
    assert approved_parent(book, 'chapter') is None
    new_volume = volume(book, current.id, index=2, ending='从旧回执接出查印章的任务。')
    assert approved_parent(book, 'chapter') == new_volume.id
    assert parent_chain(book, 'chapter', new_volume.id)[-1]['artifact']['body']['ending_direction'] == (
        '从旧回执接出查印章的任务。')


def test_volume_member_and_exact_application_approval_remain_active(book):
    from nw.plan_hierarchy import approved_parent, parent_chain

    top = propose(book)
    apply(book, top)
    middle = volume(book, top.id)
    refreshed = decide_card(book, middle.candidate_cards[0], 'approved', '[FAKE] 换用另一条批准记录')
    apply_settings(book, current_head(book), [refreshed.id], 'volume-reapproved')
    assert approved_parent(book, 'chapter') is None
    with pytest.raises(ValueError, match='STALE_PLAN_PARENT'):
        parent_chain(book, 'chapter', middle.id)

    active = volume(book, top.id, index=2)
    assert approved_parent(book, 'chapter') == active.id
    plan = active.materialization[0]['members']['vol']
    decide_card(book, CardRef(**plan), 'disabled', '[FAKE] 已撤销卷计划产物')
    assert approved_parent(book, 'chapter') is None
    with pytest.raises(ValueError, match='STALE_PLAN_PARENT.*卷'):
        parent_chain(book, 'chapter', active.id)
