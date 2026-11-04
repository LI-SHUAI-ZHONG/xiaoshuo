from dataclasses import asdict
import json
from pathlib import Path

import pytest

from nw.config import Config
from nw.llm.base import GenResult
from nw.store import Store
from story_fixture import baseline, draft_for, operation, proposal, seed_book


def test_delta_rejects_evidence_for_another_draft_and_world_utterance(tmp_path: Path) -> None:
    from nw.story_state import adopt_story

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        head = adopt_story(store, baseline(), {})
        with pytest.raises(ValueError, match='evidence'):
            proposal(store, head, da, [operation(db)])
        with pytest.raises(ValueError, match='WORLD'):
            proposal(store, head, da, [operation(da, claim='utterance')])


def test_resource_precondition_must_match(tmp_path: Path) -> None:
    from nw.acceptance import accept_batch
    from nw.story_state import adopt_story

    with Store(tmp_path, create=True) as store:
        [scene] = seed_book(store, 1)
        draft = draft_for(store, scene.id)
        head = adopt_story(store, baseline(), {})
        with pytest.raises(ValueError, match='precondition'):
            request = proposal(store, head, draft, [operation(draft, old='沈砚')])
            accept_batch(store, [request], head, 'wrong-owner')
        assert store.accepted(scene.id) is None


def test_reader_cannot_learn_ending_before_its_evidence(tmp_path: Path) -> None:
    from nw.story_state import adopt_story

    with Store(tmp_path, create=True) as store:
        [scene] = seed_book(store, 1)
        draft = draft_for(store, scene.id, '他走进档案廊。\n\n陆昭拿到了钥匙。')
        head = adopt_story(store, baseline(), {})
        op = operation(draft, holder='READER')
        op['evidence'][0]['start'] = draft.text.index('陆昭')
        with pytest.raises(ValueError, match='disclosure'):
            proposal(store, head, draft, [op])


def test_future_scene_and_unverified_or_stale_brief_are_rejected(tmp_path: Path) -> None:
    from dataclasses import replace
    from nw.acceptance import accept_batch
    from nw.story_delta import draft_ref, read_delta
    from nw.story_dependencies import legacy_ref
    from nw.story_state import adopt_story, find_impacts

    with Store(tmp_path, create=True) as store:
        a, b = seed_book(store)
        brief = store.add_brief('旧目标')
        ref = legacy_ref('brief', store.project().id, brief)
        head = adopt_story(store, baseline(), {})
        da, db = draft_for(store, a.id), draft_for(store, b.id)
        later = proposal(store, head, db, [])
        delta = read_delta(store, later.delta_id)
        with pytest.raises(ValueError, match='earlier scene'):
            proposal(store, head, da, [], dependencies=[(delta.id, delta.sha256)])
        with pytest.raises(ValueError, match='earlier scene'):
            proposal(store, head, da, [], predecessors=[draft_ref(db)])
        with pytest.raises(ValueError, match='version and hash'):
            proposal(store, head, da, [], brief_ref=replace(ref, sha256='0' * 64))
        original = proposal(store, head, da, [], brief_ref=ref)
        store.add_brief('改版目标')
        assert find_impacts(store, [ref])[0].id == original.delta_id
        with pytest.raises(ValueError, match='STALE_INPUT'):
            accept_batch(store, [original], head, 'stale')


class ReviewModel:
    name = 'fake'

    def __init__(self, operations: list[dict], findings: list[dict]) -> None:
        self.responses = [{'operations': operations}, {'findings': findings}]
        self.calls = []

    def generate(self, messages: list[dict], **params: object) -> GenResult:
        payload = self.responses[len(self.calls)]
        self.calls.append(messages)
        return GenResult(json.dumps(payload, ensure_ascii=False), 'complete', {}, None, payload)


@pytest.mark.parametrize('bad', [None, 'offset', 'hard', 'self_resolved'])
def test_model_extraction_and_independent_review_validate_same_draft(tmp_path: Path, bad: str | None) -> None:
    from nw.acceptance import accept_batch, record_story_decision
    from nw.call_control import model_settings
    from nw.story_delta import draft_ref, prepare_delta, save_delta
    from nw.story_models import AcceptanceRequest
    from nw.story_state import adopt_story
    from nw.task_models import Budget, InputManifest, content_sha256
    from nw.tasks import freeze_manifest, read_task

    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = seed_book(store, 1)
        draft = draft_for(store, scene.id)
        head = adopt_story(store, baseline(), {})
        op = operation(draft)
        if bad == 'offset':
            op['evidence'][0]['end'] += 20
        findings = []
        if bad in ('hard', 'self_resolved'):
            findings.append({'code': 'UNSUPPORTED', 'severity': 'hard', 'target_ref': asdict(draft_ref(draft)),
                             'evidence': op['evidence'], 'explanation': '正文缺少该事实',
                             'suggested_action': '检查后重新提取', 'status': 'OPEN' if bad == 'hard' else 'RESOLVED'})
        provider = ReviewModel([op], findings)
        config = Config('fake', '', 'test', '', 10, {}, tmp_path)
        budget = Budget(2, 20000, 500)
        package = {'draft_id': draft.id}
        manifest = InputManifest('m', 'state_extract', model_settings(provider, 'test', {'max_tokens': 500}, 'v1'),
                                 content_sha256(package), branch_id='main', state_revision=0, story_order=1,
                                 disclosure_order=(1, 1, 0))
        freeze_manifest(store, manifest, package)
        if bad is None:
            with pytest.raises(ValueError, match='independent fact review'):
                save_delta(store, 'forged', draft.id, 'm', [op])
            with pytest.raises(ValueError, match='task evidence'):
                save_delta(store, 'forged', draft.id, 'm', [op], extraction_task_id='x', review_task_id='y')
        if bad in ('offset', 'self_resolved'):
            with pytest.raises(ValueError, match='INVALID'):
                prepare_delta(store, draft.id, 'm', provider, config, budget)
            target = 'delta-extract:m' if bad == 'offset' else 'delta-review:m'
            assert read_task(store, target).validation == 'INVALID'
            assert read_task(store, target).raw is not None
            return
        delta = prepare_delta(store, draft.id, 'm', provider, config, budget)
        assert delta == prepare_delta(store, draft.id, 'm', provider, config, budget)
        assert len(provider.calls) == 2
        assert json.loads(provider.calls[1][1]['content'])['draft']['id'] == draft.id
        fields = {'branch_id': 'main', 'scene_id': scene.id, 'draft_id': draft.id, 'delta_id': delta.id,
                  'manifest_id': 'm'}
        ident = record_story_decision(store, 'accept', fields, '核对候选')
        req = AcceptanceRequest(**fields, decision_id=ident)
        if bad == 'hard':
            with pytest.raises(ValueError, match='Unresolved state review'):
                accept_batch(store, [req], head, 'accept')
        else:
            assert accept_batch(store, [req], head, 'accept').revision == 1
