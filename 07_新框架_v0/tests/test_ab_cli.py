import json
from pathlib import Path
import pytest
from test_cli import invoke
from test_providers import server
from nw.store import Store


def test_ab_cli(server: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url, state = server
    state['body'] = {'id': 'test', 'choices': [{'message': {'content': '[FAKE] CLI测试'}, 'finish_reason': 'stop'}]}
    config = tmp_path / 'config.toml'
    config.write_text(f'[model]\nprovider="openai_compat"\nbase_url="{url}/v1"\nmodel="test"\napi_key_env="TEST_KEY"', encoding='utf-8')
    monkeypatch.setenv('TEST_KEY', 'secret')
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('测试'); store.add_brief('需求')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{"tags":["动作"]}')
    def call(*args: str) -> dict:
        result = invoke(tmp_path, '--config', str(config), '--project', 'book', *args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    result = call('ab', 'start', '--scene', scene.id, '--a', 'minimal', '--b', 'rules_pack', '--seed', '8')
    assert set(result) == {'experiment_id', 'status', 'seal', '一', '二'}
    assert 'minimal' not in json.dumps(result) and 'rules_pack' not in json.dumps(result)
    chosen = call('ab', 'choose', '1')
    assert chosen['choice'] == 1
    revealed = call('ab', 'reveal')
    assert revealed['verified'] and revealed['seal'] == result['seal']
    run = call('write', '--scene', scene.id, '--context', 'rules_pack')['run']
    assert any(i['source'].startswith('rule:') for i in json.loads(run['context_package_json'])['items'])
    with Store(tmp_path / 'book') as store:
        assert len(store.list('run')) == 3 and store.accepted(scene.id) is None


def test_ab_requires_real_config(tmp_path: Path) -> None:
    result = invoke(tmp_path, '--config', str(tmp_path / 'absent.toml'), '--project', 'book', 'ab', 'start', '--scene', 's')
    assert result.returncode == 2 and 'CONFIG_REQUIRED' in result.stderr
