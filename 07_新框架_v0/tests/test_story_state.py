from pathlib import Path

import pytest

from nw.store import Store
from story_fixture import baseline, draft_for, operation, proposal, seed_book


def test_adoption_checks_accepted_and_keeps_legacy_notes_unverified(tmp_path: Path) -> None:
    from nw.story_state import adopt_story, state_at

    with Store(tmp_path, create=True) as store:
        [scene] = seed_book(store, 1)
        draft = draft_for(store, scene.id)
        store.accept(draft.id)
        store.add_note(scene.id, 'fact', '尚未核验')
        with pytest.raises(ValueError, match='accepted'):
            adopt_story(store, baseline(), {})
        head = adopt_story(store, baseline(), {scene.id: draft.id})
        assert state_at(store, 'main', head.revision, 0, 'WORLD').facts == []
        assert state_at(store, 'main', head.revision, 0, 'AUTHOR').legacy_notes[0]['status'] == 'legacy_unverified'


def test_story_time_and_disclosure_cutoffs_are_independent(tmp_path: Path) -> None:
    from nw.acceptance import accept_batch
    from nw.story_state import adopt_story, state_at

    with Store(tmp_path, create=True) as store:
        [scene] = seed_book(store, 1)
        head = adopt_story(store, baseline(), {})
        draft = draft_for(store, scene.id)
        req = proposal(store, head, draft, [
            operation(draft, time=9),
            operation(draft, time=9, order=(1, 1, 1), holder='READER', new='陆昭'),
            operation(draft, time=9, order=(1, 1, 2), holder='沈砚', claim='belief', new='许照微'),
        ])
        head = accept_batch(store, [req], head, 'first')
        assert not state_at(store, 'main', head.revision, 5, 'WORLD').facts
        assert state_at(store, 'main', head.revision, 9, 'WORLD').facts[0].value == '陆昭'
        assert not state_at(store, 'main', head.revision, 9, '陆昭').facts
        assert state_at(store, 'main', head.revision, 9, '沈砚').facts[0].value == '许照微'
        with pytest.raises(ValueError, match='disclosure'):
            state_at(store, 'main', head.revision, 5, 'READER')
        assert not state_at(store, 'main', head.revision, 5, 'READER', (1, 1, 0)).facts
        assert state_at(store, 'main', head.revision, 5, 'READER', (1, 1, 1)).facts[0].value == '陆昭'


def test_reader_state_is_replayed_in_disclosure_order_even_for_author(tmp_path: Path) -> None:
    from nw.acceptance import accept_batch
    from nw.story_state import adopt_story, state_at

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        head = adopt_story(store, baseline(), {})
        ra = proposal(store, head, da, [operation(da, time=9, holder='READER')])
        rb = proposal(store, head, db, [operation(db, time=3, holder='READER', order=(1, 2, 0),
                                                  old='陆昭', new='沈砚')])
        result = accept_batch(store, [ra, rb], head, 'flash')
        assert state_at(store, 'main', result.revision, 3, 'AUTHOR').facts[0].value == '沈砚'


def test_branch_setting_decision_and_history_anchor(tmp_path: Path) -> None:
    from nw.cards import decide_card, save_card
    from nw.story_state import adopt_story, apply_settings, fork_story, state_at

    card = {'card_id': 'secret', 'kind': 'world', 'origin': 'author',
            'body': {'title': '秘密', 'rule': '潮灾真因', 'limits': '作者掌握'}}
    with Store(tmp_path, create=True) as store:
        seed_book(store, 1)
        head = adopt_story(store, baseline(as_of_story_order=10), {})
        with pytest.raises(ValueError, match='HISTORY_INCOMPLETE'):
            state_at(store, 'main', head.revision, 9, 'WORLD')
        ref = save_card(store, card, None)
        approval = decide_card(store, ref, 'approved', '确认')
        branch = apply_settings(store, fork_story(store, head, 'b'), [approval.id], 'settings')
        assert state_at(store, 'b', branch.revision, 10, 'AUTHOR').settings[0]['card_id'] == ref.card_id
        assert not state_at(store, 'b', branch.revision, 10, '沈砚').settings
        assert not state_at(store, 'main', head.revision, 10, 'AUTHOR').settings
