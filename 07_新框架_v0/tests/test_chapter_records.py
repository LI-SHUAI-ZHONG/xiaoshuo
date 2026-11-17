"""Chapter editorial records follow the actual accepted branch and draft versions."""
import json
from pathlib import Path

import pytest

from nw.acceptance import accept_batch
from nw.cards import decide_card, save_card
from nw.chapter_records import chapter_index, chapter_review, chapter_summary
from nw.config import Config
from nw.planning import propose_plan
from nw.store import Store
from nw.story_state import adopt_story, current_head, fork_story
from nw.task_models import Budget
from story_fixture import baseline, draft_for, operation, proposal
from test_chapter_state import prepare_story
from test_cli import invoke
from test_planning import Planner, apply, propose


def test_summary_compares_the_approved_preview_and_reads_the_matching_accepted_version(tmp_path: Path) -> None:
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        _, (first, last) = prepare_story(store)
        head = current_head(store)
        draft = draft_for(store, first, '[FAKE] 沈砚发现账册已被搬走。')
        partial = accept_batch(store, [proposal(store, head, draft, [])], head, 'part')
        assert chapter_summary(store, partial, 1)['status'] == 'drafts_pending'
        with pytest.raises(ValueError, match='CHAPTER_SCOPE_INCOMPLETE'):
            chapter_summary(store, partial, 1, {'summary': '井中的账册不见了。', 'input_sha256': 'early'})
        ending = draft_for(store, last, '[FAKE] 他决定回到井口追查。')
        head = accept_batch(store, [proposal(store, partial, ending, [])], partial, 'end')
        packet = chapter_summary(store, head, 1)
        assert packet['status'] == 'ready'
        assert packet['inputs']['preview']['body']['title']
        assert [row['draft_ref']['id'] for row in packet['inputs']['drafts']] == [draft.id, ending.id]
        with pytest.raises(ValueError, match='100 characters'):
            chapter_summary(store, head, 1, {'input_sha256': packet['input_sha256'], 'summary': '字' * 101})
        with pytest.raises(ValueError, match='CHAPTER_RECORD_STALE'):
            chapter_summary(store, head, 1, {'input_sha256': 'different', 'summary': '另一个版本。'})
        submission = {'input_sha256': packet['input_sha256'], 'summary': '井中账册被搬走，沈砚返回井口追查。',
                      'comparison': '原章纲侧重查看井室，成稿以追查失物结束。'}

    file = tmp_path / 'summary.json'
    file.write_text(json.dumps(submission, ensure_ascii=False), encoding='utf-8')
    result = invoke(tmp_path, '--project', 'story', 'story', 'chapter-summary', '--chapter', '1', '--file', str(file))
    assert result.returncode == 0, result.stderr
    saved = json.loads(result.stdout)['record']
    assert saved['author_record']['comparison'] == submission['comparison']
    with Store(tmp_path / 'story', test_mode=True) as store:
        assert chapter_summary(store, head, 1, submission)['record']['id'] == saved['id']
        assert submission['summary'] in chapter_index(store, head)['markdown']
        assert chapter_index(store, partial)['chapters'][0]['summary'] is None
        fork = fork_story(store, head, 'alternate')
        assert chapter_summary(store, fork, 1)['status'] == 'ready'
        with pytest.raises(ValueError, match='CHAPTER_RECORD_STALE'):
            chapter_summary(store, fork, 1, submission)
        alternate = draft_for(store, last, '[FAKE] 他留在原地守候。')
        renewed = accept_batch(store, [proposal(store, head, alternate, [])], head, 'replace')
        assert chapter_summary(store, renewed, 1)['status'] == 'ready'
        assert chapter_summary(store, head, 1)['record']['id'] == saved['id']


def test_periodic_reviews_use_complete_accepted_windows_and_the_author_ending(tmp_path: Path) -> None:
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('井下账册')
        store.add_brief('按已有证据安排调查、资源与后序')
        promise = save_card(store, {'card_id': 'ledger', 'kind': 'promise', 'origin': 'author',
                                   'body': {'title': '井下账册', 'setup': '首章发现记号', 'payoff': '查明记号所指'}}, None)
        decision = decide_card(store, promise, 'approved', '保留井下账册的伏笔')
        adopt_story(store, baseline(facts=[{'entity_id': 'purse', 'predicate': 'coins', 'holder': 'WORLD',
                                           'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0],
                                           'value': 10}], card_refs=[{'card_id': promise.card_id, 'version': promise.version,
                                                                    'decision_id': decision.id}]), {})
        parent = propose(store)
        apply(store, parent)
        config = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
        for index in range(1, 11):
            model = Planner('chapter', chapter=index)
            for candidate in model.output['candidate_cards']:
                candidate['chapters'][0]['scenes'][0]['story_order'] = index
            apply(store, propose_plan(store, 1, 'chapter', model, config, Budget(1, 45000, 2000), parent_id=parent.id))
        chapters = {row.id: row.index for row in store.list('chapter')}
        scene_ids = {chapters[row.chapter_id]: row.id for row in store.list('scene')}
        head = current_head(store)
        assert chapter_review(store, head, 2, 'cost')['status'] == 'not_due'
        with pytest.raises(ValueError, match='last approved chapter'):
            chapter_review(store, head, 3, 'commitment-ending')
        for index in range(1, 11):
            if index == 3:
                assert chapter_review(store, head, 3, 'cost')['missing_chapters'] == [3]
            draft = draft_for(store, scene_ids[index], '[FAKE] 沈砚继续核对账册与井里的证据。')
            changes = ([operation(draft, entity='purse', predicate='coins', old=10, new=4,
                                  time=1, order=(1, 1, 0))] if index == 1 else [])
            if index in (1, 4):
                changes.append(operation(draft, entity=promise.card_id, predicate='promise_stage', time=index,
                                         order=(index, 1, 0), old=None if index == 1 else 'planted',
                                         new='planted' if index == 1 else 'paid'))
            head = accept_batch(store, [proposal(store, head, draft, changes)], head, f'chapter-{index}')
            if index == 3:
                report = chapter_review(store, head, 3, 'cost')
                assert [row['chapter']['index'] for row in report['inputs']['chapters']] == [1, 2, 3]
                assert report['inputs']['chapters'][0]['changes'][0]['new_value'] == 4
                submitted = chapter_review(store, head, 3, 'cost', {'input_sha256': report['input_sha256'],
                                                                     'finding': '第1章的资源支付仍有状态记录。'})
                assert submitted['status'] == 'recorded'
                assert chapter_review(store, head, 3, 'character')['inputs']['initial_character_cards']
                assert len(chapter_review(store, head, 3, 'commitment')['inputs']['chapters']) == 3
                assert len(chapter_review(store, head, 3, 'resource-inventory')['inputs']['chapters']) == 3
        assert len(chapter_review(store, head, 10, 'resource-update')['inputs']['chapters']) == 1
        assert len(chapter_review(store, head, 10, 'resource-settlement')['inputs']['chapters']) == 10
        prior = chapter_review(store, head, 3, 'commitment')['inputs']
        assert [op['new_value'] for op in prior['promise_evidence']] == ['planted']
        ending = chapter_review(store, head, 10, 'commitment-ending')['inputs']
        assert len(ending['chapters']) == 10
        assert [op['new_value'] for op in ending['promise_evidence']] == ['planted', 'paid']

    with Store(tmp_path / 'story') as store:
        assert chapter_review(store, head, 3, 'cost')['record']['author_record']['finding'].startswith('第1章')
