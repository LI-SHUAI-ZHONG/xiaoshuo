import json
from pathlib import Path

from nw.store import Store
from nw.task_models import content_sha256
from story_fixture import baseline, draft_for, operation, seed_book
from test_cli import invoke


def test_managed_cli_adoption_and_legacy_guards(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True) as store:
        [scene] = seed_book(store, 1)
        draft = draft_for(store, scene.id)
    base = baseline()
    path = tmp_path / 'baseline.json'
    path.write_text(json.dumps({'baseline': base, 'expected_accepted': {}, 'baseline_sha256': content_sha256(base)}),
                    encoding='utf-8')
    args = ('--config', str(tmp_path / 'missing.toml'), '--project', 'book')
    adopted = invoke(tmp_path, *args, 'story', 'adopt', '--baseline', str(path))
    assert adopted.returncode == 0, adopted.stderr
    assert json.loads(adopted.stdout) == {'branch_id': 'main', 'revision': 0}
    assert invoke(tmp_path, *args, 'show', 'draft', draft.id).returncode == 0
    rejected = invoke(tmp_path, *args, 'accept', '--draft', draft.id)
    assert rejected.returncode == 1 and 'DELTA_REQUIRED' in rejected.stderr
    blocked = invoke(tmp_path, *args, 'write', '--scene', scene.id)
    assert blocked.returncode == 1 and 'CONTEXT_PROVIDER_REQUIRED' in blocked.stderr
    legacy = invoke(tmp_path, *args, 'flow', 'resume', '--scene', scene.id, '--yes')
    assert legacy.returncode == 1 and 'MANAGED_STORY' in legacy.stderr
    shown = invoke(tmp_path, *args, 'story', 'show', '--branch', 'main', '--revision', '0', '--time', '0', '--holder', 'WORLD')
    assert shown.returncode == 0 and json.loads(shown.stdout)['facts'] == []

    def call(*command: str) -> dict:
        result = invoke(tmp_path, *args, *command)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    delta_file = tmp_path / 'delta.json'
    delta_file.write_text(json.dumps({'id': 'delta', 'draft_id': draft.id,
        'scope': {'id': 'frozen', 'branch_id': 'main', 'base_revision': 0, 'story_order': 1},
        'operations': [operation(draft)]}), encoding='utf-8')
    delta = call('story', 'delta', '--file', str(delta_file))
    assert call('story', 'check', '--delta', 'delta')['findings'] == []
    fields = {'branch_id': 'main', 'scene_id': scene.id, 'draft_id': draft.id,
              'delta_id': delta['id'], 'manifest_id': delta['manifest_id']}
    decision = tmp_path / 'decision.json'
    decision.write_text(json.dumps({'action': 'accept', 'targets': fields, 'reason': '核对证据'}), encoding='utf-8')
    ident = call('story', 'decide', '--file', str(decision))['decision_id']
    batch = tmp_path / 'batch.json'
    batch.write_text(json.dumps([{**fields, 'decision_id': ident}]), encoding='utf-8')
    assert call('accept', '--batch', str(batch), '--expected-head', '0', '--commit-id', 'cli')['revision'] == 1
    visible = call('story', 'show', '--branch', 'main', '--revision', '1', '--time', '1', '--holder', 'WORLD')
    assert visible['facts'][0]['value'] == '陆昭'


def test_adoption_requires_legacy_flow_completion_or_abandonment(tmp_path: Path) -> None:
    import pytest
    from nw.acceptance import record_story_decision
    from nw.flow.engine import FlowEngine
    from nw.llm.fake import FakeProvider
    from nw.story_state import adopt_story

    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = seed_book(store, 1)
        store.add_brief('需求')
        flow = FlowEngine(store, FakeProvider(), 'model', {})
        flow.run(scene.id, lambda *args: 'pause', notes=[{'kind':'fact','text':'未核对'}])
        with pytest.raises(ValueError, match='active legacy flow'):
            adopt_story(store, baseline(), {})
        record_story_decision(store, 'abandon', {'scene_id': scene.id}, '转入托管')
        assert adopt_story(store, baseline(), {}).revision == 0
