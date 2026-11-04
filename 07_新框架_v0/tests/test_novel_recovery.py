
import threading

import pytest

from nw.novel_flow import cancel_job, resume_job, show_job
from nw.store import Store
from test_novel_flow import Model, config, job, setup_story


def test_parallel_resume_claims_one_call(tmp_path):
    ready, release = threading.Event(), threading.Event()
    class Slow(Model):
        def generate(self, messages, **params):
            ready.set()
            assert release.wait(10)
            return super().generate(messages, **params)
    with Store(tmp_path, create=True, test_mode=True) as store:
        scenes = setup_story(store, 1)
        ident = job(store, scenes)
    provider = Slow()
    results = []
    def run():
        with Store(tmp_path, test_mode=True) as store:
            results.append(resume_job(store, ident, provider, config(store)))
    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert ready.wait(10)
        with Store(tmp_path, test_mode=True) as store:
            assert resume_job(store, ident, provider, config(store)).status == 'RUNNING'
    finally:
        release.set()
        worker.join(10)
    assert results[0].status == 'WAITING' and len(provider.calls) == 4


def test_cancel_prevents_next_request(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1))
        class Cancel(Model):
            def generate(self, messages, **params):
                with Store(tmp_path, test_mode=True) as other:
                    cancel_job(other, ident)
                return super().generate(messages, **params)
        provider = Cancel()
        result = resume_job(store, ident, provider, config(store))
        assert result.status == 'CANCELLED'
        assert len(provider.calls) == 1 and len(store.list('draft')) == 1


def test_unknown_call_retry_keeps_old_attempt(tmp_path, monkeypatch):
    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1))
        class Interrupted(Model):
            def generate(self, messages, **params):
                raise KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            resume_job(store, ident, Interrupted(), config(store))
        first = store.list('run')[0]
        provider = Model()
        result = resume_job(store, ident, provider, config(store))
        assert result.status == 'BLOCKED' and 'UNKNOWN' in result.reason and not provider.calls
        import nw.novel_scene as scene_module
        monkeypatch.setattr(scene_module, 'WRITE_PROMPT', 'new prompt ignored by frozen retry')
        done = resume_job(store, ident, provider, config(store), retry_failed=True)
        assert done.status == 'WAITING'
        runs = store.list('run')
        assert runs[0] == first and len(runs) == 3
        assert provider.calls[0][0]['content'] != scene_module.WRITE_PROMPT
        attempts = [row for row in show_job(store, ident).outputs['steps'] if row['step_key'].endswith(':write')]
        assert [row['attempt'] for row in attempts] == [1, 2]


def test_resume_does_not_change_prompt_version(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1), calls=1)
        provider = Model()
        assert resume_job(store, ident, provider, config(store)).status == 'BLOCKED'
        different = config(store)
        different.model = 'other'
        result = resume_job(store, ident, provider, different, max_calls=9)
        assert result.status == 'BLOCKED' and 'CONFIG_CHANGED' in result.reason
        assert len(provider.calls) == 1


@pytest.mark.parametrize('boundary', ['events', 'pointer', 'checkpoint', 'commit'])
def test_accept_and_job_checkpoint_commit_together(tmp_path, boundary):
    import json
    import sqlite3

    from nw.acceptance import accept_batch
    from nw.story_models import AcceptanceRequest, StateHead
    from nw.story_state import current_head
    from test_novel_flow import author

    with Store(tmp_path, create=True, test_mode=True) as store:
        scenes = setup_story(store, 1)
        ident = job(store, scenes)
        provider = Model()
        assert resume_job(store, ident, provider, config(store)).status == 'WAITING'
        condition = {
            'events': 'BEFORE INSERT ON story_events',
            'pointer': 'BEFORE INSERT ON accepted',
            'checkpoint': "BEFORE UPDATE ON novel_steps WHEN NEW.step_key='batch:accept' AND NEW.status='DONE'",
            'commit': "AFTER UPDATE ON novel_jobs WHEN NEW.status='DONE'",
        }[boundary]
        if boundary == 'commit':
            store.connection.execute("""
                CREATE TABLE commit_fault(
                    unknown_project TEXT REFERENCES projects(id) DEFERRABLE INITIALLY DEFERRED)
            """)
            body = "INSERT INTO commit_fault VALUES ('missing');"
        else:
            body = "SELECT RAISE(ABORT,'injected failure');"
        store.connection.execute(f'CREATE TRIGGER acceptance_fault {condition} BEGIN {body} END')
        with pytest.raises(sqlite3.IntegrityError):
            resume_job(store, ident, provider, config(store), author())
        assert current_head(store).revision == 0 and not store.list('accepted')
        assert store.connection.execute('SELECT count(*) FROM story_events').fetchone()[0] == 0
        raw = store.connection.execute("SELECT input_json,status FROM novel_steps WHERE step_key='batch:accept'").fetchone()
        assert raw['status'] == 'STARTED'
        expected = json.loads(raw['input_json'])
        requests = [AcceptanceRequest(**item) for item in expected['requests']]
        for checkpoint in [(ident, 'batch:accept', 2), (ident, 'batch:confirm', 1), ('other', 'batch:accept', 1)]:
            with pytest.raises(ValueError, match='checkpoint'):
                accept_batch(store, requests, StateHead(**expected['head']), expected['commit_id'], checkpoint)
        store.connection.execute('DROP TRIGGER acceptance_fault')
        assert resume_job(store, ident, provider, config(store)).status == 'DONE'
        assert len(provider.calls) == 4
        assert len(store.list('accepted')) == 1 and current_head(store).revision == 1
        assert accept_batch(store, requests, StateHead(**expected['head']), expected['commit_id'],
                            (ident, 'batch:accept', 1)).revision == 1


def test_export_recovery_does_not_repeat_acceptance(tmp_path, monkeypatch):
    from test_novel_flow import author

    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1))
        provider = Model()
        assert resume_job(store, ident, provider, config(store)).status == 'WAITING'
        def fail(_):
            raise OSError('disk')
        monkeypatch.setattr(store, '_export', fail)
        with pytest.raises(OSError, match='committed'):
            resume_job(store, ident, provider, config(store), author())
        assert show_job(store, ident).status == 'DONE'
        assert len(store.list('accepted')) == 1
    with Store(tmp_path, test_mode=True) as reopened:
        assert resume_job(reopened, ident, provider, config(reopened)).status == 'DONE'
        assert (tmp_path / '正文' / 'ch01_s01.md').is_file()
        assert len(provider.calls) == 4


def test_stale_head_blocks_a_waiting_acceptance(tmp_path):
    from nw.story_state import apply_settings, current_head
    from nw.cards import decide_card, save_card
    from test_novel_flow import author

    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1))
        provider = Model()
        assert resume_job(store, ident, provider, config(store)).status == 'WAITING'
        style = save_card(store, {'card_id': 'style', 'kind': 'style', 'origin': 'author',
                          'body': {'title': '文风', 'guidance': '精确', 'check': '句子清楚'}}, None)
        approval = decide_card(store, style, 'approved', '更新')
        apply_settings(store, current_head(store), [approval.id], 'updated-settings')
        stopped = resume_job(store, ident, provider, config(store), author())
        assert stopped.status == 'STALE' and stopped.reason == 'STALE_HEAD'
        assert not store.list('accepted') and len(provider.calls) == 4


def test_invalid_unicode_review_is_retryable(tmp_path):
    from nw.llm.base import GenResult

    class BadReview(Model):
        def generate(self, messages, **params):
            if '{"recommendation"' in messages[0]['content']:
                return GenResult(r'{"recommendation":"pass","notes":"\ud800","core_changes":[]}',
                                 'complete', {}, 'bad-review', {})
            return super().generate(messages, **params)

    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1))
        bad = resume_job(store, ident, BadReview(), config(store))
        assert bad.status == 'BLOCKED' and 'INVALID_REVIEW' in bad.reason
        provider = Model()
        result = resume_job(store, ident, provider, config(store), retry_failed=True)
        assert result.step == 'batch:confirm' and len(provider.calls) == 3


def test_waiting_design_does_not_spend_budget_on_an_outdated_outline(tmp_path):
    from nw.story_state import adopt_story
    from story_fixture import baseline

    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('追查封条')
        adopt_story(store, baseline(), {})
        ident = job(store, [], calls=1, mode='design')
        provider = Model()
        def choose(step, data):
            return {'action': 'approve', 'root': data['candidates'][0]['root']['card_id'], 'reason': '采用'}
        assert resume_job(store, ident, provider, config(store)).step == 'plan:book:confirm'
        paused = resume_job(store, ident, provider, config(store), choose)
        assert paused.status == 'BLOCKED' and 'CALL_LIMIT' in paused.reason
        store.add_chapter(1, '作者新增的章节')
        stale = resume_job(store, ident, provider, config(store), max_calls=2)
        assert stale.status == 'STALE' and stale.reason == 'STALE_OUTLINE'
        assert len(provider.calls) == 1
