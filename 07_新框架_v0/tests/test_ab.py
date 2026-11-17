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
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 10
        assert store.connection.execute("SELECT output_json FROM flow_nodes").fetchone()[0] == '{"old":true}'
        assert store.connection.execute('SELECT COUNT(*) FROM ab_experiments').fetchone()[0] == 0


def test_ab_diff_is_only_rule_condition(tmp_path: Path) -> None:
    from nw.task_models import Budget, content_sha256
    from nw.tasks import read_input_manifest
    from test_novel_flow import setup_story
    from test_selection import method

    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = setup_story(store, 1)
        rule = method(store, 'investigate')
        provider = FakeProvider()
        result = Experiment(store).start_story(scene, provider, 'm', {'seed': 123},
                                               budget=Budget(2, 45000, 1000), seed=42)
        assert result['status'] == 'READY' and 'comparison' not in result
        assert 'investigate' not in json.dumps(result, ensure_ascii=False)
        with pytest.raises(ValueError, match='reason'):
            Experiment(store).choose(1, result['experiment_id'])
        Experiment(store).choose(1, result['experiment_id'], reason='行动线索更清楚')
        revealed = Experiment(store).reveal(result['experiment_id'])
        by_arm = {arm['provider']: store.get('run', arm['run_id']) for arm in revealed['mapping'].values()}
        plain, methods = by_arm['no_methods'], by_arm['selected_methods']
        plain_input, selected_input = [json.loads(run.input_snapshot_json) for run in (plain, methods)]
        assert plain_input['messages'][0] == selected_input['messages'][0]
        assert json.loads(plain.params_json) == json.loads(methods.params_json)
        base, with_methods = [json.loads(item['messages'][1]['content']) for item in (plain_input, selected_input)]
        assert base['items'] == [row for row in with_methods['items'] if not row['source'].startswith('rule:')]
        assert [row['source'] for row in with_methods['items'] if row['source'].startswith('rule:')] == ['rule:investigate']
        a, _ = read_input_manifest(store, plain_input['manifest_id'])
        b, _ = read_input_manifest(store, selected_input['manifest_id'])
        assert all(a[field] == b[field] for field in ('brief_ref', 'branch_id', 'state_revision', 'story_order',
                                                     'disclosure_order', 'predecessor_drafts', 'settings'))
        assert revealed['comparison']['base_sha256'] == content_sha256(base)
        assert revealed['comparison']['method_refs'] == [{'card_id': rule.card_id, 'version': rule.version}]
        assert revealed['choice_reason'] == '行动线索更清楚'
        assert not store.list('accepted')
    with Store(tmp_path, test_mode=True) as store:
        assert Experiment(store).reveal(result['experiment_id']) == revealed


def test_managed_ab_refuses_empty_or_unfunded_comparison(tmp_path: Path) -> None:
    from nw.task_models import Budget
    from test_novel_flow import setup_story
    from test_selection import method

    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = setup_story(store, 1)
        provider = FakeProvider()
        ab = Experiment(store)
        with pytest.raises(ValueError, match='eligible method'):
            ab.start_story(scene, provider, 'm', {}, budget=Budget(2, 45000, 1000))
        method(store, 'investigate')
        with pytest.raises(ValueError, match='two calls'):
            ab.start_story(scene, provider, 'm', {}, budget=Budget(1, 45000, 1000))
        assert not provider.calls and not store.list('run')


def test_story_ab_interrupted_pair_recovers_without_new_calls(tmp_path: Path) -> None:
    from nw.call_budget import read_budget
    from nw.task_models import Budget
    from test_novel_flow import setup_story
    from test_selection import method

    class Interrupted(FakeProvider):
        def generate(self, messages, **params):
            if self.calls:
                raise KeyboardInterrupt()
            return super().generate(messages, **params)

    provider = Interrupted()
    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = setup_story(store, 1)
        method(store, 'investigate')
        ab = Experiment(store)
        with pytest.raises(KeyboardInterrupt):
            ab.start_story(scene, provider, 'm', {}, budget=Budget(2, 45000, 1000), seed=12)
        assert ab.record()['status'] == 'IN_PROGRESS'
    with Store(tmp_path, test_mode=True) as store:
        ab = Experiment(store)
        assert ab.view()['status'] == 'BLOCKED'
        assert ab.view()['status'] == 'BLOCKED'
        assert len(provider.calls) == 1 and len(store.list('run')) == 2
        budget = read_budget(store, ab.record()['comparison']['budget_id'])
        assert budget.used_calls == budget.reserved_calls == 1
        with pytest.raises(ValueError, match='complete'):
            ab.choose(1, reason='不足以比较')


def test_story_ab_draft_retains_story_time_and_is_not_an_automatic_revision_source(tmp_path: Path) -> None:
    from nw.story_extract import freeze_delta_input
    from nw.task_models import Budget
    from test_novel_flow import job, setup_story
    from test_selection import method

    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = setup_story(store, 1)
        method(store, 'investigate')
        Experiment(store).start_story(scene, FakeProvider(), 'm', {}, budget=Budget(2, 45000, 1000))
        with pytest.raises(ValueError, match='complete source draft'):
            job(store, [scene], mode='revise')
        draft = store.drafts(scene)[0]
        settings = {'provider': 'author', 'model': 'manual', 'params': {}, 'prompt_version': 'manual-state-v1',
                    'base_url': None, 'timeout': None, 'stream': False}
        with pytest.raises(ValueError, match='story time'):
            freeze_delta_input(store, draft.id, {'id': 'wrong', 'branch_id': 'main', 'base_revision': 0,
                                                'story_order': 99}, settings)
