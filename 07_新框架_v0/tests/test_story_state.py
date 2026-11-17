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



def test_identity_changes_keep_world_permissions_separate_from_disclosure(tmp_path: Path) -> None:
    from hashlib import sha256

    from nw.acceptance import accept_batch
    from nw.chapter_state import chapter_state
    from nw.story_state import adopt_story, state_at

    predicate = 'identity_status:港务巡查'
    old = {'identity': '见习巡查', 'permissions': ['只能查水路名册'], 'social_expectations': ['值班随行']}
    current = {'identity': '正式巡查', 'permissions': ['可独自查封泊位'], 'social_expectations': ['报告异常并承担责任']}
    known = {'identity': '正式巡查'}
    appointment = '执事盖印，正式任命沈砚。新章程准他独自查封泊位，异常由他报告并担责。'
    disclosure = '陆昭看到任命书的职衔，才知道沈砚已正式任职。'
    with Store(tmp_path, create=True) as store:
        [scene] = seed_book(store, 1)
        fact = {'entity_id': '沈砚', 'predicate': predicate, 'value': old, 'holder': 'WORLD',
                'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0]}
        head = adopt_story(store, baseline(facts=[fact]), {})
        draft = draft_for(store, scene.id, appointment + '\n\n' + disclosure)
        world = operation(draft, predicate=predicate, old=old, new=current, entity='沈砚')
        world['evidence'][0]['end'] = len(appointment)
        reveal = operation(draft, predicate=predicate, new=known, entity='沈砚',
                           holder='陆昭', order=(1, 1, 1))
        reveal['evidence'][0]['start'] = len(appointment) + 2
        reader = {**reveal, 'holder': 'READER'}
        req = proposal(store, head, draft, [world, reveal, reader])
        head = accept_batch(store, [req], head, 'identity-appointment')

    with Store(tmp_path) as store:
        projection = chapter_state(store, head, 1)
        change, = projection['changes']
        assert change['expected_old'] == old and change['new_value'] == current
        evidence, = change['paragraph_evidence']
        assert evidence['prose_location'] == f'{scene.id}#paragraphs[0]'
        assert evidence['paragraph_sha256'] == sha256(appointment.encode()).hexdigest()
        assert {item['holder'] for item in projection['identity_disclosures']} == {'陆昭', 'READER'}
        revealed = projection['identity_disclosures'][0]['paragraph_evidence'][0]
        assert revealed['prose_location'] == f'{scene.id}#paragraphs[1]'
        assert revealed['paragraph_sha256'] == sha256(disclosure.encode()).hexdigest()
        assert state_at(store, 'main', head.revision, 0, 'WORLD').facts[0].value == old
        assert state_at(store, 'main', head.revision, 1, 'WORLD').facts[0].value == current
        assert state_at(store, 'main', head.revision, 1, '陆昭').facts[0].value == known
        assert not state_at(store, 'main', head.revision, 1, 'READER', (1, 1, 0)).facts
        assert state_at(store, 'main', head.revision, 1, 'READER', (1, 1, 1)).facts[0].value == known


def test_identity_schema_rejects_a_world_record_used_as_someones_knowledge(tmp_path: Path) -> None:
    from nw.story_state import adopt_story

    with Store(tmp_path, create=True) as store:
        [scene] = seed_book(store, 1)
        head = adopt_story(store, baseline(), {})
        draft = draft_for(store, scene.id)
        partial = {'identity': '学徒'}
        complete = {**partial, 'permissions': ['可入内查看'], 'social_expectations': ['须由师傅带领']}
        predicate = 'identity_status:行会职位'
        for holder, value in [('WORLD', partial), ('READER', complete), ('陆昭', complete)]:
            # World state must carry both kinds of consequences; a disclosure
            # only carries the identity actually learned by this holder.
            with pytest.raises(ValueError, match='IDENTITY_STATUS'):
                proposal(store, head, draft, [operation(
                    draft, entity='沈砚', predicate=predicate, holder=holder, new=value)])
        with pytest.raises(ValueError, match='world changes need a distinct resulting status'):
            proposal(store, head, draft, [operation(
                draft, entity='沈砚', predicate=predicate, old=complete, new=complete)])
