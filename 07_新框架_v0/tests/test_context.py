import json
from dataclasses import asdict
from pathlib import Path

import pytest
from nw.context.registry import build_context, register, get_provider
from nw.context.base import ContextPackage, ContextItem
from nw.generation import write_scene
from nw.llm.fake import FakeProvider
from nw.store import Store


def test_registry() -> None:
    class Custom:
        name = 'custom'
        def build(self, project: dict, scene: dict) -> ContextPackage:
            return ContextPackage([ContextItem('custom', '内容', '测试')], 2)
    register(Custom())
    assert get_provider('custom').build({}, {}).items[0].text == '内容'
    with pytest.raises(ValueError):
        get_provider('missing')


def test_context_selection_previous_rules_and_snapshots(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('测试')
        store.add_brief('旧需求'); store.add_brief('新需求')
        store.add_bible('character', '沈砚', '旧设定')
        store.add_bible('character', '沈砚', '新设定')
        store.add_bible('character', '无关人物', '不应入选')
        store.add_bible('style', '文风', '克制')
        chapter = store.add_chapter(1, '章')
        previous = store.add_scene(chapter.id, 1, '{}')
        _, draft = write_scene(store, previous.id, FakeProvider(), 'm', {})
        store.accept(draft.id)
        scene = store.add_scene(chapter.id, 2, json.dumps({'pov': '沈砚', 'tags': ['动作', '感官']}))
        minimal = build_context(store, scene.id, 'minimal')
        rules = build_context(store, scene.id, 'rules_pack')
        assert rules['items'][:len(minimal['items'])] == minimal['items']
        text = json.dumps(minimal, ensure_ascii=False)
        assert all(x in text for x in ['新需求', '新设定', '克制', '[FAKE]'])
        assert all(x not in text for x in ['旧需求', '旧设定', '不应入选'])
        selected = [x for x in rules['items'] if x['source'].startswith('rule:')]
        assert len(selected) == 2 and all('标签' in x['reason'] for x in selected)
        assert rules['token_estimate'] > minimal['token_estimate'] > 0
        provider = FakeProvider()
        run, _ = write_scene(store, scene.id, provider, 'm', {}, context_name='rules_pack')
        assert json.loads(run.context_package_json) == rules
        assert json.loads(run.input_snapshot_json)['messages'] == provider.calls[0]


def test_example_fixture(tmp_path: Path) -> None:
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / 'fixtures/create_example.py'),
                             '--workspace', str(tmp_path), '--project', 'example'],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    with Store(tmp_path / 'example') as store:
        assert store.project().name == '潮痕入骨'
        scene = store.list('scene')[0]
        package = build_context(store, scene.id, 'rules_pack')
        assert len([i for i in package['items'] if i['source'].startswith('rule:')]) == 6
        assert store.list('run') == []
        assert '沈砚' in json.dumps(package, ensure_ascii=False)


def test_flow_rules_context_frozen_after_n4(tmp_path: Path) -> None:
    from nw.flow.engine import FlowEngine
    from test_flow import yes, NOTES
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('测试'); store.add_brief('需求')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{"tags":["动作"]}')
        def stop(node: str) -> None:
            if node == 'N4':
                raise KeyboardInterrupt()
        engine = FlowEngine(store, FakeProvider(), 'm', {}, 'rules_pack')
        with pytest.raises(KeyboardInterrupt):
            engine.run(scene.id, yes, notes=NOTES, after_node=stop)
        frozen = engine.nodes(scene.id)[3]['output']
        assert any(i['source'].startswith('rule:') for i in frozen['items'])
        store.add_brief('后来的需求')
        with pytest.raises(ValueError):
            FlowEngine(store, FakeProvider(), 'm', {}).run(scene.id, yes, resume=True)
        assert engine.run(scene.id, yes, resume=True)['status'] == 'DONE'
        for run in store.list('run'):
            assert json.loads(run.context_package_json) == frozen
