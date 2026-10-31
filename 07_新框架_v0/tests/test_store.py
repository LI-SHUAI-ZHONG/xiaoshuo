from dataclasses import FrozenInstanceError
from pathlib import Path
import sqlite3

import pytest

from nw import models
from nw.store import Store


def seed(store: Store) -> str:
    store.init_project('测试项目')
    chapter = store.add_chapter(1, '测试章')
    return store.add_scene(chapter.id, 1, '{"目的":"测试"}').id


def run_for(scene: str, number: int, text: str, reason: str = 'complete') -> models.Run:
    return models.Run(str(number), scene, 'write', 'fake', 'test', '{}',
                      '{"messages":[{"role":"user","content":"测试输入"}]}',
                      '{"items":[]}', text, reason, '{}', 'start', 'end')


def test_roundtrip_versions_acceptance_and_export(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        brief1 = store.add_brief('需求一', '限制')
        brief2 = store.add_brief('需求二', '限制')
        bible1 = store.add_bible('character', '人物', '设定一')
        bible2 = store.add_bible('character', '人物', '设定二')
        drafts = []
        for i in range(1, 4):
            text = f'[FAKE] 测试版本 {i}\n第二行。\n'
            store.add_run(run_for(scene, i, text))
            drafts.append(store.add_draft(scene, text, 'complete', str(i)))
        assert [d.version for d in drafts] == [1, 2, 3]
        with pytest.raises(FrozenInstanceError):
            drafts[0].text = '覆盖'
        for sql in ('UPDATE drafts SET text="覆盖" WHERE id=?',
                    'DELETE FROM drafts WHERE id=?'):
            with pytest.raises(sqlite3.IntegrityError):
                with store.connection:
                    store.connection.execute(sql, (drafts[0].id,))
        store.accept(drafts[0].id)
        store.accept(drafts[2].id)
        store.add_note(scene, 'fact', '测试事实')
        assert brief1.version == bible1.version == 1
        assert brief2.version == bible2.version == 2
    with Store(tmp_path / 'book', test_mode=True) as store:
        assert store.project().name == '测试项目'
        assert [d.text for d in store.drafts(scene)] == [d.text for d in drafts]
        assert store.accepted(scene).draft_id == drafts[2].id
        assert store.briefs() == [brief1, brief2]
        assert store.bible() == [bible1, bible2]
        assert store.notes(scene)[0].text == '测试事实'
        assert store.get('run', '1').input_snapshot_json == run_for(scene, 1, '').input_snapshot_json
        assert store.get('scene', scene).card_json == '{"目的":"测试"}'
        assert (tmp_path / 'book/正文/ch01_s01.md').read_text(encoding='utf-8') == drafts[2].text


@pytest.mark.parametrize('status', ['partial', 'truncated', 'error'])
def test_reject_incomplete_acceptance(tmp_path: Path, status: str) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        store.add_run(run_for(scene, 1, '[FAKE] incomplete', 'truncated'))
        draft = store.add_draft(scene, '[FAKE] incomplete', status, '1')
        with pytest.raises(ValueError, match='complete'):
            store.accept(draft.id)
        with pytest.raises(sqlite3.IntegrityError):
            with store.connection:
                store.connection.execute('INSERT INTO accepted VALUES (?, ?, ?)', (scene, draft.id, 'now'))
        assert store.accepted(scene) is None
        assert not (tmp_path / 'book/正文/ch01_s01.md').exists()


def test_wrong_scene_run_and_acceptance_rejected(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        other = store.add_scene(store.get('scene', scene).chapter_id, 2, '{}').id
        store.add_run(run_for(scene, 1, '[FAKE] x'))
        with pytest.raises(sqlite3.IntegrityError):
            store.add_draft(other, '[FAKE] x', 'complete', '1')
        draft = store.add_draft(scene, '[FAKE] x', 'complete', '1')
        with pytest.raises(sqlite3.IntegrityError):
            with store.connection:
                store.connection.execute('INSERT INTO accepted VALUES (?, ?, ?)', (other, draft.id, 'now'))
        assert store.drafts(other) == []


def test_export_failure_rolls_back_pointer(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        store.add_run(run_for(scene, 1, '[FAKE] x'))
        draft = store.add_draft(scene, '[FAKE] x', 'complete', '1')
        (tmp_path / 'book/正文').write_text('阻止创建目录', encoding='utf-8')
        with pytest.raises(OSError):
            store.accept(draft.id)
        assert store.accepted(scene) is None


def test_reopen_repairs_export_from_accepted(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        store.add_run(run_for(scene, 1, '[FAKE] original'))
        draft = store.add_draft(scene, '[FAKE] original', 'complete', '1')
        store.accept(draft.id)
    path = tmp_path / 'book/正文/ch01_s01.md'
    path.write_text('模拟异常中断后的不一致导出', encoding='utf-8')
    with Store(tmp_path / 'book', test_mode=True):
        assert path.read_text(encoding='utf-8') == '[FAKE] original'


def test_open_missing_and_future_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Store(tmp_path / 'missing')
    assert not (tmp_path / 'missing').exists()
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        store.init_project('测试')
        with store.connection:
            store.connection.execute('PRAGMA user_version=999')
    with pytest.raises(ValueError, match='version'):
        Store(tmp_path / 'book', test_mode=True)


def test_failed_commit_does_not_publish_unaccepted_text(tmp_path: Path) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        store.add_run(run_for(scene, 1, '[FAKE] x'))
        draft = store.add_draft(scene, '[FAKE] x', 'complete', '1')

        def deny_commit(action: int, arg1: str | None, arg2: str | None,
                        database: str | None, trigger: str | None) -> int:
            if action == sqlite3.SQLITE_TRANSACTION and arg1 == 'COMMIT':
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        store.connection.set_authorizer(deny_commit)
        with pytest.raises(sqlite3.DatabaseError):
            store.accept(draft.id)
        store.connection.set_authorizer(None)
        assert store.accepted(scene) is None
        assert not (tmp_path / 'book/正文/ch01_s01.md').exists()


def test_export_error_after_commit_is_recoverable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with Store(tmp_path / 'book', create=True, test_mode=True) as store:
        scene = seed(store)
        store.add_run(run_for(scene, 1, '[FAKE] recover'))
        draft = store.add_draft(scene, '[FAKE] recover', 'complete', '1')

        def fail_write(self: Path, *args: object, **kwargs: object) -> int:
            raise OSError('simulated disk write failure')

        with monkeypatch.context() as patch:
            patch.setattr(Path, 'write_text', fail_write)
            with pytest.raises(OSError, match='recorded'):
                store.accept(draft.id)
        assert store.accepted(scene).draft_id == draft.id
    with Store(tmp_path / 'book', test_mode=True) as store:
        assert (tmp_path / 'book/正文/ch01_s01.md').read_text(encoding='utf-8') == '[FAKE] recover'
