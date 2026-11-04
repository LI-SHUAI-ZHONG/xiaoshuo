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


def test_story_ab_cli_preserves_blind_choice(tmp_path, server):
    from test_novel_flow import setup_story
    from test_selection import method

    url, state = server
    settings = tmp_path / 'model.toml'
    settings.write_text(f'[model]\nprovider="ollama"\nbase_url="{url}"\nmodel="test"\n', encoding='utf-8')
    budget = tmp_path / 'budget.json'
    budget.write_text('{"max_calls":2,"context_char_limit":45000,"output_limit":1000}', encoding='utf-8')
    with Store(tmp_path / 'book', create=True) as store:
        [scene] = setup_story(store, 1)
        method(store, 'investigate')
    requests = []

    def respond(body):
        requests.append(body)
        return {'message': {'content': f'[FAKE] {len(requests)}'}, 'done': True, 'done_reason': 'stop'}

    state['respond'] = respond

    def cli(*args):
        result = invoke(tmp_path, '--config', str(settings), '--project', 'book', 'ab', *args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    started = cli('start', '--scene', scene, '--budget', str(budget), '--seed', '42')
    ident = started['experiment_id']
    assert cli('show', '--experiment', ident) == started
    assert cli('choose', '2', '--experiment', ident, '--reason', '人物选择更清楚')['choice'] == 2
    revealed = cli('reveal', '--experiment', ident)
    assert revealed['choice_reason'] == '人物选择更清楚'
    assert revealed['comparison']['method_refs'][0]['card_id'] == 'investigate'
    assert revealed['seal'] == started['seal']
    assert len(requests) == 2 and requests[0]['options'] == requests[1]['options']
    with Store(tmp_path / 'book') as store:
        assert len(store.drafts(scene)) == 2 and store.accepted(scene) is None
