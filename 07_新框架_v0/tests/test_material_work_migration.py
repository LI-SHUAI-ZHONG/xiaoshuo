from pathlib import Path

from nw import migrations
from nw.schema import VERSION
from nw.store import Store
from nw.story_state import adopt_story
from story_fixture import baseline
from test_planning import propose,apply


def test_existing_v8_plan_calls_and_applications_survive_new_method_task_kind(tmp_path,monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(migrations,'VERSION',8)
        with Store(tmp_path,create=True,test_mode=True) as store:
            store.init_project('既有小说');store.add_brief('调查封条');adopt_story(store,baseline(),{})
            proposal=propose(store);apply(store,proposal)
            before=[tuple(row) for row in store.connection.execute('SELECT * FROM task_calls')]
            applications=[tuple(row) for row in store.connection.execute('SELECT * FROM plan_applications')]
    with Store(tmp_path,test_mode=True) as store:
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == VERSION
        assert [tuple(row) for row in store.connection.execute('SELECT * FROM task_calls')]==before
        assert [tuple(row) for row in store.connection.execute('SELECT * FROM plan_applications')]==applications
        assert not store.connection.execute('PRAGMA foreign_key_check').fetchall()
        assert 'material_work' in store.connection.execute("SELECT sql FROM sqlite_master WHERE name='task_calls'").fetchone()[0]
    assert list(tmp_path.glob('nw.v8.*.bak'))
