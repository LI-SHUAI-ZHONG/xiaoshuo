import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Iterator
from pathlib import Path

import pytest

from nw.llm.ollama import OllamaProvider
from nw.llm.openai_compat import OpenAICompatProvider


@pytest.fixture
def server() -> Iterator[tuple[str, dict]]:
    state = {'body': {}, 'status': 200}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            state['path'] = self.path
            state['request'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['auth'] = self.headers.get('Authorization')
            self.send_response(state['status'])
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(state.get('raw_body', json.dumps(state['body'])).encode('utf-8'))

        def log_message(self, format: str, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}', state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


@pytest.mark.parametrize('finish,expected', [('stop', 'complete'), ('length', 'truncated'),
                                           ('content_filter', 'refused'), ('unknown', 'error')])
def test_compat_protocol(server: tuple[str, dict], finish: str, expected: str) -> None:
    url, state = server
    state['body'] = {'id': 'req1', 'choices': [{'message': {'content': '[FAKE] text'}, 'finish_reason': finish}], 'usage': {'total_tokens': 10}}
    result = OpenAICompatProvider(url + '/v1', 'secret').generate([{'role': 'user', 'content': '测试'}], model='m', temperature=0.1)
    assert result.finish_reason == expected
    assert result.text == '[FAKE] text'
    assert result.request_id == 'req1'
    assert state['path'] == '/v1/chat/completions'
    assert state['request']['stream'] is False
    assert state['auth'] == 'Bearer secret'


@pytest.mark.parametrize('done,reason,expected', [(True, 'stop', 'complete'), (True, 'length', 'truncated'), (False, '', 'truncated')])
def test_ollama_protocol(server: tuple[str, dict], done: bool, reason: str, expected: str) -> None:
    url, state = server
    state['body'] = {'message': {'content': '[FAKE] 文本'}, 'done': done, 'done_reason': reason, 'eval_count': 2}
    result = OllamaProvider(url).generate([{'role': 'user', 'content': '测试'}], model='m', temperature=0.1)
    assert result.finish_reason == expected
    assert state['path'] == '/api/chat'
    assert state['request']['options'] == {'temperature': 0.1}


def test_http_error_and_malformed_are_not_success(server: tuple[str, dict]) -> None:
    url, state = server
    provider = OpenAICompatProvider(url + '/v1', 'secret')
    state['status'] = 500
    assert provider.generate([], model='m').finish_reason == 'error'
    state['status'] = 200
    state['body'] = {'choices': []}
    assert provider.generate([], model='m').finish_reason == 'error'


def test_cli_write_inspection_accept_and_secret_redaction(server: tuple[str, dict], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from nw.store import Store
    from test_cli import invoke

    url, state = server
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('测试')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
    config = tmp_path / 'config.toml'
    config.write_text(f'[model]\nprovider="openai_compat"\nbase_url="{url}/v1"\nmodel="test"\napi_key_env="NW_TEST_KEY"', encoding='utf-8')
    monkeypatch.setenv('NW_TEST_KEY', 'secret-test-key')
    state['body'] = {'id': 'request-1', 'choices': [{'message': {'content': '[FAKE] 完整测试文本'}, 'finish_reason': 'stop'}], 'echo': 'secret-test-key'}
    result = invoke(tmp_path, '--project', 'book', '--config', str(config), 'write', '--scene', scene.id, '--provider', 'openai_compat')
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    run_id, draft_id = data['run']['id'], data['draft']['id']
    shown = invoke(tmp_path, '--project', 'book', 'show', 'run', run_id)
    assert shown.returncode == 0
    shown_data = json.loads(shown.stdout)
    assert json.loads(shown_data['input_snapshot_json'])['messages'] == state['request']['messages']
    assert shown_data['response']['raw']['echo'] == '[REDACTED]'
    assert 'secret-test-key' not in shown.stdout
    assert b'secret-test-key' not in (tmp_path / 'book/nw.db').read_bytes()
    assert len(json.loads(invoke(tmp_path, '--project', 'book', 'runs').stdout)) == 1
    accepted = invoke(tmp_path, '--project', 'book', 'accept', '--draft', draft_id)
    assert accepted.returncode == 0, accepted.stderr
    assert (tmp_path / 'book/正文/ch01_s01.md').read_text(encoding='utf-8') == '[FAKE] 完整测试文本'
    state['body']['choices'][0]['finish_reason'] = 'length'
    result = invoke(tmp_path, '--project', 'book', '--config', str(config), 'write', '--scene', scene.id)
    assert result.returncode == 1
    draft_id = json.loads(result.stdout)['draft']['id']
    assert invoke(tmp_path, '--project', 'book', 'accept', '--draft', draft_id).returncode == 1


def test_cli_requires_config_without_creating_project(tmp_path: Path) -> None:
    from test_cli import invoke

    result = invoke(tmp_path, '--project', 'missing', '--config', str(tmp_path / 'none.toml'), 'write', '--scene', 'scene')
    assert result.returncode == 2
    assert 'CONFIG_REQUIRED' in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_malformed_request_id_is_recorded_as_error(server: tuple[str, dict], tmp_path: Path) -> None:
    from nw.store import Store
    from nw.generation import write_scene

    url, state = server
    state['body'] = {'id': {'bad': 'object'}, 'choices': [{'message': {'content': '[FAKE] x'}, 'finish_reason': 'stop'}]}
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('测试')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
        run, draft = write_scene(store, scene.id, OpenAICompatProvider(url + '/v1', 'secret'), 'm', {})
        assert run.finish_reason == 'error' and run.ended_at
        assert draft is None
        assert store.run_output(run.id)['raw']['id'] == {'bad': 'object'}


@pytest.mark.parametrize('number', ['NaN', 'Infinity', '1e999'])
def test_invalid_json_number_still_finishes_run(server: tuple[str, dict], tmp_path: Path, number: str) -> None:
    from nw.store import Store
    from nw.generation import write_scene

    url, state = server
    state['raw_body'] = '{"usage":{"tokens":' + number + '}}'
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('测试')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
        run, draft = write_scene(store, scene.id, OpenAICompatProvider(url + '/v1', 'secret'), 'm', {})
        assert run.finish_reason == 'error' and run.ended_at
        assert draft is None
        assert number in store.run_output(run.id)['raw']['body']
