from pathlib import Path
import json

import pytest

from nw.flow.engine import FlowEngine
from nw.llm.fake import FakeProvider
from nw.store import Store


def seed(store: Store) -> str:
    store.init_project('测试')
    store.add_brief('作者需求')
    store.add_bible('world', '世界', '作者设定')
    return store.add_scene(store.add_chapter(1, '第一章').id, 1, '{"目的":"调查"}').id


def yes(node: str, payload: dict) -> str:
    return 'accept' if node == 'N5' else 'confirm'


NOTES = [{'kind': 'fact', 'text': '作者确认的状态记录'}]


def test_end_to_end_and_idempotent_resume(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        provider = FakeProvider()
        engine = FlowEngine(store, provider, 'test', {})
        result = engine.run(scene, yes, notes=NOTES)
        assert result['status'] == 'DONE'
        assert [r.kind for r in store.list('run')] == ['write', 'review']
        assert len(store.drafts(scene)) == 1  # review is not prose
        accepted = store.accepted(scene)
        assert (tmp_path / 'book/正文/ch01_s01.md').read_text(encoding='utf-8') == store.get('draft', accepted.draft_id).text
        assert store.notes(scene)[0].text == '作者确认的状态记录'
        assert [n['status'] for n in engine.nodes(scene)] == ['DONE'] * 6
        assert all(n['input'] and n['output'] for n in engine.nodes(scene))
    with Store(tmp_path / 'book', test_mode=True) as store:
        provider = FakeProvider()
        assert FlowEngine(store, provider, 'test', {}).run(scene, yes, resume=True)['status'] == 'DONE'
        assert provider.calls == [] and len(store.notes(scene)) == 1


def test_forced_stop_after_n3_resumes_frozen_inputs(tmp_path: Path) -> None:
    def stop(node: str) -> None:
        if node == 'N3':
            raise KeyboardInterrupt()

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        with pytest.raises(KeyboardInterrupt):
            FlowEngine(store, FakeProvider(), 'test', {}).run(scene, yes, notes=NOTES, after_node=stop)
        assert store.list('run') == []
        store.add_brief('中断后新增，不得悄悄替换已确认需求')
    with Store(tmp_path / 'book', test_mode=True) as store:
        confirmations = []
        def decide(node: str, payload: dict) -> str:
            confirmations.append(node)
            return yes(node, payload)
        provider = FakeProvider()
        engine = FlowEngine(store, provider, 'test', {})
        assert engine.run(scene, decide, resume=True)['status'] == 'DONE'
        assert confirmations == ['N5']
        assert len(store.briefs()) == 2 and len(store.list('chapter')) == 1
        assert '中断后新增' not in json.dumps(provider.calls, ensure_ascii=False)


def test_two_revision_limit_and_rejected_drafts_preserved(tmp_path: Path) -> None:
    def reject(node: str, payload: dict) -> str:
        return 'revise' if node == 'N5' else 'confirm'

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        provider = FakeProvider()
        engine = FlowEngine(store, provider, 'test', {})
        assert engine.run(scene, reject, notes=NOTES)['status'] == 'BLOCKED'
        assert [r.kind for r in store.list('run')] == ['write', 'review', 'revise', 'review', 'revise', 'review']
        assert [d.version for d in store.drafts(scene)] == [1, 2, 3]
        assert store.accepted(scene) is None and store.notes(scene) == []
        calls = len(provider.calls)
        assert engine.run(scene, yes, resume=True)['status'] == 'DONE'
        assert len(provider.calls) == calls
        assert len(store.drafts(scene)) == 3


@pytest.mark.parametrize('reason', ['truncated', 'error', 'refused'])
def test_generation_failure_does_not_accept_or_repeat(tmp_path: Path, reason: str) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        provider = FakeProvider(reason=reason)
        engine = FlowEngine(store, provider, 'test', {})
        assert engine.run(scene, yes, notes=NOTES)['status'] == 'BLOCKED'
        assert store.accepted(scene) is None and not store.notes(scene)
        assert engine.run(scene, yes, resume=True)['status'] == 'BLOCKED'
        assert len(provider.calls) == 1


def test_declined_gate_resumes_without_skipping_confirmation(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        engine = FlowEngine(store, FakeProvider(), 'test', {})
        assert engine.run(scene, lambda n, p: 'pause', notes=NOTES)['status'] == 'BLOCKED'
        assert engine.nodes(scene)[0]['status'] == 'BLOCKED'
        assert store.list('run') == []
        assert engine.run(scene, yes, resume=True)['status'] == 'DONE'


def test_interrupted_review_is_not_automatically_repeated(tmp_path: Path) -> None:
    class Interrupted(FakeProvider):
        def generate(self, messages: list[dict], **params: object) -> object:
            if len(self.calls) == 1:
                raise KeyboardInterrupt()
            return super().generate(messages, **params)

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        with pytest.raises(KeyboardInterrupt):
            FlowEngine(store, Interrupted(), 'test', {}).run(scene, yes, notes=NOTES)
    with Store(tmp_path / 'book', test_mode=True) as store:
        provider = FakeProvider()
        assert FlowEngine(store, provider, 'test', {}).run(scene, yes, resume=True)['status'] == 'BLOCKED'
        assert provider.calls == []
        assert len(store.list('run')) == 2 and len(store.drafts(scene)) == 1
        assert store.accepted(scene) is None
        assert FlowEngine(store, provider, 'test', {}).run(scene, yes, resume=True, retry_failed=True)['status'] == 'DONE'
        assert len(provider.calls) == 1
        assert [r.kind for r in store.list('run')] == ['write', 'review', 'review']
        assert len(store.drafts(scene)) == 1


def test_resume_after_accept_commit_before_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_write(self: Path, *args: object, **kwargs: object) -> int:
        raise OSError('simulated disk failure')

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'write_text', fail_write)
            with pytest.raises(OSError):
                FlowEngine(store, FakeProvider(), 'test', {}).run(scene, yes, notes=NOTES)
        assert store.accepted(scene) is not None
        assert store.notes(scene) == []
    with Store(tmp_path / 'book', test_mode=True) as store:
        provider = FakeProvider()
        engine = FlowEngine(store, provider, 'test', {})
        assert engine.run(scene, yes, resume=True)['status'] == 'DONE'
        assert provider.calls == [] and len(store.notes(scene)) == 1
        assert engine.run(scene, yes, resume=True)['status'] == 'DONE'
        assert len(store.notes(scene)) == 1


def test_resume_rejects_changed_model(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        FlowEngine(store, FakeProvider(), 'test', {}).run(scene, lambda n, p: 'pause', notes=NOTES)
        with pytest.raises(ValueError, match='original'):
            FlowEngine(store, FakeProvider(), 'other-model', {}).run(scene, yes, resume=True)


def test_explicit_retry_preserves_failure_and_completes(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        FlowEngine(store, FakeProvider(reason='error'), 'test', {}).run(scene, yes, notes=NOTES)
        old = store.list('run')[0]
        provider = FakeProvider()
        result = FlowEngine(store, provider, 'test', {}).run(scene, yes, resume=True, retry_failed=True)
        assert result['status'] == 'DONE'
        assert len(provider.calls) == 2
        assert store.get('run', old.id) == old
        assert [r.kind for r in store.list('run')] == ['write', 'write', 'review']


def test_unconfirmed_brief_can_be_corrected(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        engine = FlowEngine(store, FakeProvider(), 'test', {})
        engine.run(scene, lambda n, p: 'pause', notes=NOTES)
        store.add_brief('修正需求')
        observed = []
        def decide(node: str, payload: dict) -> str:
            if node == 'N1':
                observed.append(payload['brief']['text'])
            return yes(node, payload)
        assert engine.run(scene, decide, resume=True)['status'] == 'DONE'
        assert observed == ['修正需求']


def test_interleaved_resume_does_not_duplicate_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from nw.flow.nodes import NodeStore

    def stop(node: str) -> None:
        if node == 'N5':
            raise KeyboardInterrupt()

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        engine = FlowEngine(store, FakeProvider(), 'test', {})
        with pytest.raises(KeyboardInterrupt):
            engine.run(scene, yes, notes=NOTES, after_node=stop)
        original = NodeStore.get
        armed = [True]
        def interleave(self: NodeStore, node: str) -> dict:
            record = original(self, node)
            if node == 'N6' and armed[0]:
                armed[0] = False
                with Store(tmp_path / 'book', test_mode=True) as other:
                    FlowEngine(other, FakeProvider(), 'test', {}).run(scene, yes, resume=True)
            return record
        monkeypatch.setattr(NodeStore, 'get', interleave)
        assert engine.run(scene, yes, resume=True)['status'] == 'DONE'
        assert len(store.notes(scene)) == 1
