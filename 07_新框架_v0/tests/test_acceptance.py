from pathlib import Path
import sqlite3

import pytest

from nw.store import Store
from story_fixture import baseline, draft_for, operation, proposal, seed_book


def test_batch_topology_idempotence_and_replaced_events(tmp_path: Path) -> None:
    from nw.acceptance import accept_batch
    from nw.story_delta import read_delta
    from nw.story_state import adopt_story, project_candidate_state, state_at

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        head = adopt_story(store, baseline(), {})
        ra = proposal(store, head, da, [operation(da)])
        prior = read_delta(store, ra.delta_id)
        rb = proposal(store, head, db, [operation(db, order=(1, 2, 0), time=2, old='陆昭', new='沈砚')],
                      dependencies=[(prior.id, prior.sha256)])
        view = state_at(store, 'main', head.revision, 2, 'AUTHOR')
        second = read_delta(store, rb.delta_id)
        with pytest.raises(ValueError, match='dependency'):
            project_candidate_state(view, [second])
        assert project_candidate_state(view, [prior, second]).facts[0].value == '沈砚'
        with pytest.raises(ValueError, match='dependency'):
            accept_batch(store, [rb], head, 'missing')
        next_head = accept_batch(store, [rb, ra], head, 'batch')
        assert next_head == accept_batch(store, [ra, rb], head, 'batch')
        with pytest.raises(ValueError, match='commit ID'):
            accept_batch(store, [ra], head, 'batch')
        with pytest.raises(ValueError, match='STALE_HEAD'):
            accept_batch(store, [ra], head, 'other')
        assert state_at(store, 'main', next_head.revision, 2, 'WORLD').facts[0].value == '沈砚'
        same_draft = proposal(store, next_head, da, [operation(da)])
        assert same_draft.delta_id != ra.delta_id
        with pytest.raises(ValueError, match='dependency'):
            accept_batch(store, [same_draft], next_head, 'same-prose-new-delta')
        replacement = draft_for(store, a.id, '陆昭没有接钥匙。')
        new = proposal(store, next_head, replacement, [])
        with pytest.raises(ValueError, match='dependency'):
            accept_batch(store, [new], next_head, 'break')
        rb_new = proposal(store, next_head, db, [operation(db, order=(1, 2, 0), time=2, new='许照微')],
                          dependencies=[(new.delta_id, read_delta(store, new.delta_id).sha256)])
        final = accept_batch(store, [new, rb_new], next_head, 'repair')
        assert not state_at(store, 'main', final.revision, 1, 'WORLD').facts
        assert state_at(store, 'main', next_head.revision, 1, 'WORLD').facts[0].value == '陆昭'


def test_event_failure_rolls_back_batch_and_export_failure_keeps_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from nw.acceptance import accept_batch
    from nw.story_state import adopt_story, current_head

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        head = adopt_story(store, baseline(), {})
        ra = proposal(store, head, da, [operation(da)])
        rb = proposal(store, head, db, [operation(db, time=2, order=(1, 2, 0), entity='second')])
        with store.connection:
            store.connection.execute(f"""CREATE TRIGGER fail_event BEFORE INSERT ON story_events
                WHEN NEW.scene_id='{b.id}' BEGIN SELECT RAISE(ABORT,'injected'); END""")
        with pytest.raises(sqlite3.IntegrityError, match='injected'):
            accept_batch(store, [ra, rb], head, 'batch')
        assert store.list('accepted') == [] and current_head(store) == head
        assert not store.connection.execute('SELECT * FROM story_events').fetchall()
        with store.connection:
            store.connection.execute('DROP TRIGGER fail_event')
        def fail(draft) -> None:
            raise OSError('disk failure')
        with monkeypatch.context() as patch:
            patch.setattr(store, '_export', fail)
            with pytest.raises(OSError, match='committed'):
                accept_batch(store, [ra, rb], head, 'batch')
        assert store.accepted(a.id).draft_id == da.id and current_head(store).revision == head.revision + 1
    with Store(tmp_path) as store:
        assert store._export_path(db).read_text(encoding='utf-8') == db.text


def test_early_replacement_without_explicit_edges_requires_later_review(tmp_path: Path) -> None:
    from nw.acceptance import accept_batch
    from nw.story_state import adopt_story

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        root = adopt_story(store, baseline(), {})
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        first = accept_batch(store, [proposal(store, root, da, []), proposal(store, root, db, [])], root, 'initial')
        change = draft_for(store, a.id, '新版本')
        with pytest.raises(ValueError, match='revalidation'):
            accept_batch(store, [proposal(store, first, change, [])], first, 'change')
        assert store.accepted(a.id).draft_id == da.id and store.accepted(b.id).draft_id == db.id


def test_promotion_cannot_restore_unreviewed_inherited_prose(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.acceptance import accept_batch, promote_branch, record_story_decision
    from nw.story_state import adopt_story, fork_story

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        root = adopt_story(store, baseline(), {})
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        old = accept_batch(store, [proposal(store, root, da, []), proposal(store, root, db, [])], root, 'initial')
        new_b = draft_for(store, b.id, '主线第二场已经修订。')
        main = accept_batch(store, [proposal(store, old, new_b, [])], old, 'update-b')
        branch = fork_story(store, old, 'branch')
        new_a = draft_for(store, a.id, '候选第一场已修订。')
        candidate = accept_batch(store, [proposal(store, branch, new_a, [])], branch, 'update-a')
        decision = record_story_decision(store, 'promote', {'candidate': asdict(candidate), 'expected_main': asdict(main)}, '确认')
        with pytest.raises(ValueError, match='revalidated'):
            promote_branch(store, 'branch', main, decision, 'promote')
        assert store.accepted(b.id).draft_id == new_b.id


def test_branch_promotion_requires_author_and_dependency_closure(tmp_path: Path) -> None:
    from dataclasses import asdict
    from nw.acceptance import accept_batch, promote_branch, record_story_decision
    from nw.story_state import adopt_story, fork_story

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        root = adopt_story(store, baseline(), {})
        ma = accept_batch(store, [proposal(store, root, da, [])], root, 'main-a')
        mb = accept_batch(store, [proposal(store, ma, db, [])], ma, 'main-b')
        branch = fork_story(store, ma, 'candidate')
        changed = draft_for(store, a.id, '改版后陆昭离开。')
        first = accept_batch(store, [proposal(store, branch, changed, [])], branch, 'branch-a')
        assert store.accepted(a.id).draft_id == da.id
        def approve(head):
            return record_story_decision(store, 'promote',
                                         {'candidate': asdict(head), 'expected_main': asdict(mb)}, '审查后采用')
        with pytest.raises(ValueError, match='revalidated'):
            promote_branch(store, first.branch_id, mb, approve(first), 'promote')
        ready = accept_batch(store, [proposal(store, first, db, [])], first, 'branch-b')
        with pytest.raises(ValueError, match='decision'):
            promote_branch(store, ready.branch_id, mb, approve(first), 'promote')
        promoted = promote_branch(store, ready.branch_id, mb, approve(ready), 'promote')
        assert promoted.revision == mb.revision + 1 and store.accepted(a.id).draft_id == changed.id
