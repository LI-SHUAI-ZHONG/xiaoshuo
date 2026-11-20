"""Scene capacity is checked for downstream consumers before the paid prose call."""
from dataclasses import replace

import pytest

from nw.acceptance import accept_batch
from nw.call_budget import raise_context_limits, read_budget
from nw.context.story import build_story_context, scene_scope
from nw.llm.base import GenResult
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.novel_store import Journal
from nw.store import Store
from nw.story_state import current_head
from nw.task_models import Budget, canonical
from story_fixture import draft_for, proposal
from test_novel_flow import Model, config, setup_story


@pytest.mark.parametrize('revisions,margin,stage', [(0, 300, '审稿'), (1, 2100, '修订')])
def test_downstream_overflow_pauses_before_writing(tmp_path, revisions, margin, stage):
    with Store(tmp_path, create=True, test_mode=True) as store:
        scene, = setup_story(store, count=1)
        store.add_brief('长篇背景' * 15000, '保留本场硬约束')
        scope = scene_scope(store, scene)
        full = build_story_context(store, scene, scope, 160000)
        write_chars = len(full.prompt) + len(canonical(full.package))
        budget = Budget(10, write_chars + margin, 1600, revisions)
        ident = start_job(store, JobRequest('write', 'main', [scene], None, budget)).id
        model = Model()
        result = resume_job(store, ident, model, config(store))
        assert result.status == 'BLOCKED'
        assert 'CONTEXT_TOO_LARGE' in result.reason and stage in result.reason
        assert not model.calls and not store.drafts(scene)
        assert read_budget(store, ident).used_calls == 0


def test_optional_tail_dropped_for_review_keeps_scene_and_brief_and_logs_why(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        first, second = setup_story(store, count=2)
        head = current_head(store)
        prior = draft_for(store, first, '[FAKE] ' + '上文可选段落' * 210)
        delta = proposal(store, head, prior, [])
        accept_batch(store, [delta], head, 'prior')
        full = build_story_context(store, second, scene_scope(store, second), 64000)
        assert any(i['source'].startswith('previous:') for i in full.package['items'])
        write_chars = len(full.prompt) + len(canonical(full.package))
        budget = Budget(10, write_chars + 300, 600, 0)
        ident = start_job(store, JobRequest('write', 'main', [second], None, budget)).id
        model = Model()
        resume_job(store, ident, model, config(store))
        row = Journal(store, ident).latest(f'scene:{second}:select')
        assert row is not None
        sources = {item['source'] for item in row['input']['package']['items']}
        assert 'brief' in sources and 'scene:card2' in sources and 'pov:yan' in sources
        assert not any(s.startswith('previous:') for s in sources)
        report = row['input']['capacity_preflight']
        assert report['optional_context_limited_by'] == ['review']
        assert 'previous' in report['omitted_optional_groups']
        assert report['stages']['review']['input_chars'] <= budget.context_char_limit
        assert model.calls


def test_review_models_own_window_can_be_raised_on_same_job_without_changing_route(tmp_path):
    class OfflineTransport(Model):
        # Exercise the production stage resolver with local responses in a test Store.
        name = 'openai_compat'

    with Store(tmp_path, create=True, test_mode=True) as store:
        _, scene = setup_story(store, count=2)
        cfg = replace(config(store), provider='openai_compat', context_window_tokens=65000)
        model = OfflineTransport()
        review = {key: getattr(cfg, key) for key in ('provider', 'base_url', 'api_key_env', 'timeout', 'params')}
        review.update(model='small-reviewer', context_window_tokens=300)
        ident = start_job(store, JobRequest('write', 'main', [scene], None, Budget(10, 64000, 128))).id
        result = resume_job(store, ident, model, replace(cfg, stage_models={'review': review}))
        assert result.status == 'BLOCKED' and 'MODEL_CONTEXT_WINDOW' in result.reason
        assert 'small-reviewer' in result.reason and '估算' in result.reason and not model.calls
        resumed = resume_job(store, ident, model, replace(cfg, stage_models={
            'review': {**review, 'context_window_tokens': 48000}}))
        assert resumed.status == 'WAITING', resumed.reason
        assert {run.kind: run.model for run in store.list('run')} == {'write': cfg.model, 'review': 'small-reviewer'}


def test_partial_output_never_goes_to_review(tmp_path):
    class Truncated(Model):
        def generate(self, messages, **kwargs):
            self.calls.append(messages)
            return GenResult('[FAKE] 残稿', 'truncated', {}, 'fake', {})
    with Store(tmp_path, create=True, test_mode=True) as store:
        scene, = setup_story(store, count=1)
        ident = start_job(store, JobRequest('write', 'main', [scene], None, Budget(10, 64000, 1200))).id
        model = Truncated()
        result = resume_job(store, ident, model, config(store))
        assert result.status == 'BLOCKED' and 'truncated' in result.reason
        assert len(model.calls) == 1 and not store.list('accepted')


def test_actual_long_draft_rechecked_before_review_and_retained_for_replanning(tmp_path):
    class LongDraft(Model):
        def generate(self, messages, **kwargs):
            import json
            payload = json.loads(messages[-1]['content'])
            if 'items' in payload:
                self.calls.append(messages)
                return GenResult('[FAKE] ' + '正文' * 3200, 'complete', {}, 'fake', {})
            return super().generate(messages, **kwargs)

    with Store(tmp_path, create=True, test_mode=True) as store:
        _, scene = setup_story(store, count=2)
        ident = start_job(store, JobRequest('write', 'main', [scene], None, Budget(10, 5000, 200, 0))).id
        model = LongDraft()
        result = resume_job(store, ident, model, config(store))
        assert result.status == 'BLOCKED' and '审稿实际输入' in result.reason and '5000' in result.reason
        assert len(model.calls) == 1 and len(store.drafts(scene)) == 1 and not store.list('accepted')
        initial = store.list('run')[0]
        assert read_budget(store, ident).used_calls == 1
        request = Journal(store, ident).request
        change = raise_context_limits(store, ident, context_char_limit=32000, output_limit=600)
        assert change == {'before': {'context_char_limit': 5000, 'output_limit': 200},
                          'after': {'context_char_limit': 32000, 'output_limit': 600}}
        resumed = resume_job(store, ident, model, config(store))
        assert resumed.status == 'WAITING', resumed.reason
        assert len(store.drafts(scene)) == 1 and store.get('run', initial.id) == initial
        assert Journal(store, ident).request == request
        assert any(r.kind == 'review' and '"max_tokens":600' in r.params_json.replace(' ', '') for r in store.list('run'))
        with pytest.raises(ValueError, match='提高或保持'):
            raise_context_limits(store, ident, context_char_limit=31000, output_limit=650)
        assert read_budget(store, ident).output_limit == 600


def test_pending_frozen_prose_uses_original_output_limit_after_raise(tmp_path):
    import json
    from nw.novel_calls import JobCalls
    from nw.novel_scene import _inputs
    with Store(tmp_path, create=True, test_mode=True) as store:
        _, scene = setup_story(store, count=2)
        ident = start_job(store, JobRequest('write', 'main', [scene], None, Budget(10, 16000, 200, 0))).id
        model, cfg = Model(), config(store)
        frozen = _inputs(JobCalls(Journal(store, ident), model, cfg, False), scene, ())
        assert frozen['manifest']['settings']['params']['max_tokens'] == 200
        raise_context_limits(store, ident, context_char_limit=32000, output_limit=500)
        result = resume_job(store, ident, model, cfg)
        assert result.status == 'WAITING', result.reason
        used = {r.kind: json.loads(r.params_json)['max_tokens'] for r in store.list('run')}
        assert used == {'write': 200, 'review': 500}
        assert Journal(store, ident).latest(f'scene:{scene}:select')['input'] == frozen


def test_window_only_route_override_can_resume_old_job_but_changed_endpoint_cannot(tmp_path):
    from nw.call_control import model_settings
    from nw.novel_flow import _freeze_model
    from nw.novel_store import JobPaused
    with Store(tmp_path, create=True, test_mode=True) as store:
        scene, = setup_story(store, count=1)
        ident = start_job(store, JobRequest('write', 'main', [scene], None, Budget(10, 16000, 200))).id
        model, cfg = Model(), config(store)
        journal = Journal(store, ident)
        before = model_settings(model, cfg.model, cfg.params, 'novel-job-v1')
        _freeze_model(journal, before, cfg)
        route = {key: getattr(cfg, key) for key in ('provider', 'model', 'base_url', 'api_key_env', 'timeout', 'params')}
        _freeze_model(journal, {**before, 'stage_models': {'review': {**route, 'context_window_tokens': 32768}}}, cfg)
        for changed in ({'base_url': 'https://changed.example'}, {'model': 'changed'}, {'params': {'temperature': .6}}):
            with pytest.raises(JobPaused, match='CONFIG_CHANGED'):
                _freeze_model(journal, {**before, 'stage_models': {'review': {**route, **changed}}}, cfg)


def test_preflight_uses_the_effective_approved_chapter_and_scene_ceiling(tmp_path):
    from test_length_plan import setup_plans
    from nw.novel_calls import JobCalls
    from nw.scene_capacity import SceneCapacity
    with Store(tmp_path, create=True, test_mode=True) as store:
        setup_plans(store)
        first, second = sorted(store.list('scene'), key=lambda scene: scene.index)
        head = current_head(store)
        draft = draft_for(store, first.id, '甲' * 50)
        accept_batch(store, [proposal(store, head, draft, [])], head, 'accept-first')
        work = build_story_context(store, second.id, scene_scope(store, second.id), 64000)
        request = JobRequest('write', 'main', [second.id], None, Budget(10, 64000, 1600))
        journal = Journal(store, start_job(store, request).id)
        cap = SceneCapacity(JobCalls(journal, Model(), config(store), retry_failed=False), second.id, ())
        measured = cap.check(work.prompt, work.package, set(work.writing_source_keys))
        # The original scene allows 70, but 50 accepted characters leave at most 55 in this chapter.
        assert measured['reserved_draft_chars'] == 55
        assert measured['draft_estimate_basis'] == 'feasible_chapter_scene_max_words'
