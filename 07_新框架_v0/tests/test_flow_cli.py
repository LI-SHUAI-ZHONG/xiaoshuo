import json
from pathlib import Path

import pytest

from test_cli import invoke
from test_providers import server
from nw.store import Store


def test_flow_cli_and_resume(server: tuple[str, dict], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url, state = server
    state['body'] = {'id': 'test', 'choices': [{'message': {'content': '[FAKE] 临时测试'}, 'finish_reason': 'stop'}]}
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('测试')
        store.add_brief('作者需求')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
    config = tmp_path / 'config.toml'
    config.write_text(f'[model]\nprovider="openai_compat"\nmodel="test"\nbase_url="{url}/v1"\napi_key_env="NW_TEST_KEY"', encoding='utf-8')
    monkeypatch.setenv('NW_TEST_KEY', 'test-secret')
    notes = tmp_path / 'notes.json'
    notes.write_text('[{"kind":"fact","text":"作者记录"}]', encoding='utf-8')
    args = ('--config', str(config), '--project', 'book')
    result = invoke(tmp_path, *args, 'flow', 'run', '--scene', scene.id, '--notes', str(notes), '--yes')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['status'] == 'DONE'
    result = invoke(tmp_path, *args, 'flow', 'resume', '--scene', scene.id, '--yes')
    assert result.returncode == 0, result.stderr
    with Store(tmp_path / 'book') as store:
        assert len(store.list('run')) == 2 and len(store.notes(scene.id)) == 1
        draft = store.drafts(scene.id)[0]
    result = invoke(tmp_path, *args, 'review', '--draft', draft.id)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['kind'] == 'review'
    with Store(tmp_path / 'book') as store:
        assert len(store.drafts(scene.id)) == 1
