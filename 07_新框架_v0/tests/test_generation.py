import json
from pathlib import Path

import pytest

from nw.config import ConfigRequired, load_config, make_provider
from nw.generation import write_scene
from nw.llm.fake import FakeProvider
from nw.store import Store


@pytest.mark.parametrize('reason,status', [('complete', 'complete'), ('truncated', 'truncated'),
                                         ('error', None), ('refused', None)])
def test_write_records_result_and_snapshot(tmp_path: Path, reason: str, status: str | None) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('测试')
        store.add_brief('需求旧')
        store.add_brief('需求新')
        chapter = store.add_chapter(1, '章')
        scene = store.add_scene(chapter.id, 1, '{"目的":"调查"}')
        provider = FakeProvider(reason=reason)
        run, draft = write_scene(store, scene.id, provider, 'test-model', {'temperature': 0.2})
        assert run.finish_reason == reason
        snapshot = json.loads(run.input_snapshot_json)
        assert snapshot['messages'] == provider.calls[0]
        assert snapshot['model'] == 'test-model'
        assert snapshot['params'] == {'temperature': 0.2}
        assert '需求新' in snapshot['messages'][1]['content']
        assert '需求旧' not in snapshot['messages'][1]['content']
        assert len(store.list('run')) == 1
        if status:
            assert draft.status == status
            assert draft.text.startswith('[FAKE]')
            if status == 'truncated':
                with pytest.raises(ValueError):
                    store.accept(draft.id)
        else:
            assert draft is None and store.drafts(scene.id) == []
        assert not (tmp_path / 'book/正文').exists()
    with Store(tmp_path / 'book', test_mode=True) as store:
        assert store.get('run', run.id) == run
        assert store.run_output(run.id)['request_id'] == 'fake-request'


def test_fake_cannot_write_production(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True) as store:
        store.init_project('测试')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
        with pytest.raises(ValueError, match='test'):
            write_scene(store, scene.id, FakeProvider(), 'test', {})
        assert store.list('run') == []


def test_missing_configuration_and_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigRequired):
        load_config(tmp_path / 'missing.toml')
    path = tmp_path / 'config.toml'
    path.write_text('[model]\nprovider="openai_compat"\nbase_url="http://localhost:9000/v1"\nmodel="test"\napi_key_env="NW_TEST_KEY"', encoding='utf-8')
    monkeypatch.delenv('NW_TEST_KEY', raising=False)
    with pytest.raises(ConfigRequired, match='NW_TEST_KEY'):
        make_provider(load_config(path))
    monkeypatch.setenv('NW_TEST_KEY', 'test-secret')
    provider = make_provider(load_config(path))
    assert provider.name == 'openai_compat'
    assert 'test-secret' not in repr(load_config(path))


def test_input_is_durable_before_call_and_exception_is_recorded(tmp_path: Path) -> None:
    class FailingProvider(FakeProvider):
        def generate(self, messages: list[dict], **params: object) -> object:
            with Store(tmp_path / 'book', test_mode=True) as reader:
                pending = reader.list('run')[0]
                assert json.loads(pending.input_snapshot_json)['messages'] == messages
                assert pending.ended_at == ''
            raise TimeoutError('sensitive transport details')

    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('测试')
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
        run, draft = write_scene(store, scene.id, FailingProvider(), 'm', {})
        assert run.finish_reason == 'error' and run.ended_at
        assert draft is None
        assert store.run_output(run.id)['raw'] == {'error_type': 'TimeoutError'}


def test_version_one_database_migrates_without_losing_data(tmp_path: Path) -> None:
    import sqlite3
    from nw.schema import SCHEMA

    directory = tmp_path / 'legacy'
    directory.mkdir()
    connection = sqlite3.connect(directory / 'nw.db')
    connection.executescript(SCHEMA)
    with connection:
        connection.execute('INSERT INTO projects VALUES (?,?,?)', ('old', '旧项目', 'before'))
    connection.close()
    with Store(directory) as store:
        assert store.project().name == '旧项目'
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 4


def test_test_mode_cannot_target_projects(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='production'):
        Store(tmp_path / 'projects' / 'book', create=True, test_mode=True)
