import json
from pathlib import Path
import pytest
from nw.experiments.ab import Experiment
from nw.llm.fake import FakeProvider
from nw.store import Store


def setup(store: Store) -> str:
    store.init_project('试验'); store.add_brief('需求')
    return store.add_scene(store.add_chapter(1, '章').id, 1, '{"tags":["动作"]}').id


def test_ab_persistence_seal_and_reproducibility(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = setup(store)
        provider = FakeProvider()
        ab = Experiment(store)
        first = ab.start(scene, provider, 'm', {}, seed=42)
        assert set(first) == {'experiment_id', 'status', 'seal', '一', '二'}
        assert first['status'] == 'READY'
        assert first['一'].startswith('[FAKE]')
        runs = store.list('run')
        assert len(runs) == 2
        for i, run in enumerate(runs):
            assert json.loads(run.input_snapshot_json)['messages'] == provider.calls[i]
            assert json.loads(run.context_package_json)['items']
        with pytest.raises(ValueError, match='choose'):
            ab.reveal(first['experiment_id'])
        ab.choose(1, first['experiment_id'])
        revealed = ab.reveal(first['experiment_id'])
        assert revealed['verified'] and revealed['choice'] == 1
        second = ab.start(scene, provider, 'm', {}, seed=42)
        ab.choose(2, second['experiment_id'])
        assert ab.reveal(second['experiment_id'])['providers'] == revealed['providers']
        assert len(store.drafts(scene)) == 4 and store.accepted(scene) is None
    with Store(tmp_path / 'book', test_mode=True) as store:
        assert Experiment(store).reveal(first['experiment_id']) == revealed
        with store.connection:
            store.connection.execute("UPDATE ab_experiments SET mapping_json='{}' WHERE id=?", (first['experiment_id'],))
        with pytest.raises(ValueError, match='seal'):
            Experiment(store).reveal(first['experiment_id'])


@pytest.mark.parametrize('reason', ['truncated', 'error', 'refused'])
def test_failed_ab_retains_runs_no_choice(tmp_path: Path, reason: str) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = setup(store)
        ab = Experiment(store)
        result = ab.start(scene, FakeProvider(reason=reason), 'm', {})
        assert result['status'] == 'BLOCKED'
        assert len(store.list('run')) == 2
        with pytest.raises(ValueError):
            ab.choose(1)
        assert store.accepted(scene) is None


def test_unknown_context_and_interrupted_experiment(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = setup(store)
        provider = FakeProvider()
        with pytest.raises(ValueError):
            Experiment(store).start(scene, provider, 'm', {}, b='unknown')
        assert not provider.calls and not store.list('run')
        class Interrupted(FakeProvider):
            def generate(self, messages: list[dict], **params: object) -> object:
                raise KeyboardInterrupt()
        with pytest.raises(KeyboardInterrupt):
            Experiment(store).start(scene, Interrupted(), 'm', {})
    with Store(tmp_path / 'book', test_mode=True) as store:
        assert Experiment(store).view()['status'] == 'IN_PROGRESS'
        assert len(store.list('run')) == 1 and not store.list('run')[0].ended_at
        with pytest.raises(ValueError):
            Experiment(store).choose(1)


def test_v3_migrates_without_losing_flow(tmp_path: Path) -> None:
    import sqlite3
    from nw.schema import SCHEMA, MIGRATE_V2, MIGRATE_V3
    directory = tmp_path / 'old'; directory.mkdir()
    connection = sqlite3.connect(directory / 'nw.db')
    connection.executescript(SCHEMA + MIGRATE_V2 + MIGRATE_V3)
    with connection:
        connection.execute('INSERT INTO projects VALUES (?,?,?)', ('p', '旧项目', 'before'))
        connection.execute('INSERT INTO chapters VALUES (?,?,?,?)', ('c', 'p', 1, '章'))
        connection.execute('INSERT INTO scenes VALUES (?,?,?,?)', ('s', 'c', 1, '{}'))
        connection.execute('INSERT INTO flow_meta VALUES (?,?,?)', ('s', '{}', '[]'))
        connection.execute('INSERT INTO flow_nodes VALUES (?,?,?,?,?)', ('s', 'N4', 'DONE', '{}', '{"old":true}'))
    connection.close()
    with Store(directory) as store:
        assert store.project().name == '旧项目'
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 4
        assert store.connection.execute("SELECT output_json FROM flow_nodes").fetchone()[0] == '{"old":true}'
        assert store.connection.execute('SELECT COUNT(*) FROM ab_experiments').fetchone()[0] == 0
