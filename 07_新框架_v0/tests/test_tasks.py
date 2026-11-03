"""Task execution against real SQLite; only the remote model is replaced."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
from threading import Event

import pytest

from nw.config import Config
from nw.generation import call_model
from nw.llm.base import GenResult
from nw.store import Store

MESSAGES = [{'role': 'user', 'content': '设计一个关于代价的故事'}]
PLAN = '{"scope":"book","candidate_cards":[{"kind":"plot","body":{"premise":"海岸"}}]}'


class Model:
    name = 'fake'

    def __init__(self, text: str = PLAN) -> None:
        self.text = text
        self.calls = []

    def generate(self, messages: list[dict], **params: object) -> GenResult:
        self.calls.append((messages, params))
        return GenResult(self.text, 'complete', {'prompt_tokens': 9, 'completion_tokens': 2},
                         'request-1', {'answer': self.text})


def setup_task(store: Store, *, max_calls: int = 3, max_cost: str | None = None):
    from nw.tasks import create_budget, freeze_manifest, model_settings
    from nw.task_models import Budget, InputManifest, TaskRequest, content_sha256

    project = store.init_project('隔离测试')
    config = Config('fake', '', 'test-model', '', 3, {}, store.directory)
    package = {'brief': '设计一个关于代价的故事'}
    freeze_manifest(store, InputManifest(
        id='frozen', purpose='plan', settings=model_settings(Model(), config.model, {'max_tokens': 64}, 'plan-v1'),
        context_sha256=content_sha256(package)), package)
    create_budget(store, 'budget', Budget(max_calls, context_char_limit=4000, output_limit=64,
                  max_cost=max_cost, price_snapshot={'input_per_token': '0.001', 'output_per_token': '0.002',
                                                     'currency': 'USD'} if max_cost else None))
    return TaskRequest('first', project.id, 'plan', 'frozen', {'messages': MESSAGES}, 'budget'), config


def test_project_plan_has_no_scene_or_draft(tmp_path: Path) -> None:
    from nw.tasks import read_input_manifest, read_task, run_task

    provider = Model()
    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store)
        result = run_task(store, request, provider, config)
        assert result.status == 'FINISHED' and result.validation == 'VALID'
        assert result.parsed['scope'] == 'book'
        assert store.list('run') == store.list('scene') == store.list('draft') == []
    with Store(tmp_path, test_mode=True) as store:
        assert read_task(store, request.id).raw == {'answer': PLAN}
        assert read_input_manifest(store, 'frozen')[1] == {'brief': '设计一个关于代价的故事'}
        row = store.connection.execute('SELECT messages_json,manifest_json FROM task_calls').fetchone()
        assert json.loads(row[0]) == MESSAGES
        assert json.loads(row[1])['id'] == 'frozen'
        assert run_task(store, request, provider, config) == result
        assert provider.calls == [(MESSAGES, {'model': 'test-model', 'max_tokens': 64})]


@pytest.mark.parametrize('bad', [
    '不是 JSON', '{"scope":"book","scope":"scene","candidate_cards":[]}',
    '{"scope":"book","candidate_cards":[{"kind":"plot","body":{"x":NaN}}]}',
    '{"scope":"book","candidate_cards":[{"kind":"plot","body":false}]}',
])
def test_complete_invalid_json_is_not_valid_plan(tmp_path: Path, bad: str) -> None:
    from nw.tasks import run_task

    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store)
        result = run_task(store, request, Model(bad), config)
        assert result.finish_reason == 'complete'
        assert result.validation == 'INVALID' and result.parsed is None
        assert result.raw == {'answer': bad}


def test_unknown_call_needs_explicit_retry(tmp_path: Path) -> None:
    from nw.tasks import run_task

    class Interrupted(Model):
        def generate(self, messages: list[dict], **params: object) -> GenResult:
            raise KeyboardInterrupt()

    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store, max_calls=2)
        with pytest.raises(KeyboardInterrupt):
            run_task(store, request, Interrupted(), config)
    provider = Model()
    with Store(tmp_path, test_mode=True) as store:
        assert run_task(store, request, provider, config).status == 'UNKNOWN'
        assert provider.calls == []
        counts = store.connection.execute('SELECT used_calls,reserved_calls FROM budgets').fetchone()
        assert tuple(counts) == (0, 1)
        retry = replace(request, id='retry', attempt=2, retry_of=request.id)
        with pytest.raises(ValueError):
            run_task(store, replace(retry, payload={'messages': [{'role': 'user', 'content': '换题'}]}),
                     provider, config)
        assert run_task(store, retry, provider, config).validation == 'VALID'
        assert len(provider.calls) == 1
        with pytest.raises(ValueError, match='retry'):
            run_task(store, replace(retry, id='second-retry'), provider, config)
        assert len(provider.calls) == 1


def test_parallel_claim_calls_provider_once(tmp_path: Path) -> None:
    from nw.tasks import run_task

    entered, release = Event(), Event()

    class Waiting(Model):
        def generate(self, messages: list[dict], **params: object) -> GenResult:
            entered.set()
            assert release.wait(10)
            return super().generate(messages, **params)

    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store)

    def execute(task, provider: Model):
        with Store(tmp_path, test_mode=True) as store:
            return run_task(store, task, provider, config)

    first, second = Waiting(), Model()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(execute, request, first)
        try:
            assert entered.wait(5)
            assert execute(request, second).status == 'RUNNING'
            retry = replace(request, id='retry', attempt=2, retry_of=request.id)
            assert execute(retry, second).status == 'RUNNING'
            assert second.calls == []
        finally:
            release.set()
        assert future.result(timeout=5).validation == 'VALID'
    assert len(first.calls) == 1


def test_budget_reserved_before_send_and_shared_with_scene(tmp_path: Path) -> None:
    from nw.tasks import BudgetExceeded, run_task

    class CheckReservation(Model):
        def generate(self, messages: list[dict], **params: object) -> GenResult:
            # A second connection can see the committed preflight record.
            with Store(tmp_path, test_mode=True) as other:
                row = other.connection.execute('SELECT used_calls,reserved_calls FROM budgets').fetchone()
                assert tuple(row) == (0, 1)
            return super().generate(messages, **params)

    provider = CheckReservation()
    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store, max_calls=1)
        assert run_task(store, request, provider, config).validation == 'VALID'
        assert run_task(store, replace(request, id='denied'), provider, config).status == 'BUDGET_EXCEEDED'
        scene = store.add_scene(store.add_chapter(1, '章').id, 1, '{}')
        with pytest.raises(BudgetExceeded):
            call_model(store, scene.id, provider, config.model, {}, 'write', MESSAGES, {}, budget_id='budget')
        assert len(provider.calls) == 1 and store.list('run') == []


def test_cost_limit_refuses_send_and_settles_reported_usage(tmp_path: Path) -> None:
    from nw.tasks import run_task

    with Store(tmp_path / 'denied', create=True, test_mode=True) as store:
        request, config = setup_task(store, max_cost='0.001')
        provider = Model()
        assert run_task(store, request, provider, config).status == 'BUDGET_EXCEEDED'
        assert provider.calls == []
    with Store(tmp_path / 'allowed', create=True, test_mode=True) as store:
        request, config = setup_task(store, max_cost='1.00')
        assert run_task(store, request, Model(), config).validation == 'VALID'
        budget = store.connection.execute('SELECT reserved_cost,spent_cost FROM budgets').fetchone()
        assert tuple(budget) == ('0', '0.013')


@pytest.mark.parametrize(('kind', 'output'), [
    ('rule_extract', '{"rules":[{"original_meaning":"线索","source_refs":[{}]}]}'),
    ('state_extract', '{"operations":[{"op":"invent","evidence":{"x":1}}]}'),
    ('fact_review', '{"findings":[{"code":"x","severity":"hard","target_ref":{},"evidence":[],'
                    '"explanation":"证据不足","suggested_action":"核对","status":"OPEN"}]}'),
])
def test_invalid_nested_refs_and_evidence(kind: str, output: str) -> None:
    from nw.tasks import validate_task_output

    with pytest.raises(ValueError):
        validate_task_output(kind, output)


def test_complete_invalid_unicode_is_preserved(tmp_path: Path) -> None:
    from nw.tasks import read_task, run_task

    broken = chr(0xd800)
    with Store(tmp_path, create=True, test_mode=True) as store:
        request, config = setup_task(store)
        run_task(store, request, Model(broken), config)
    with Store(tmp_path, test_mode=True) as store:
        result = read_task(store, request.id)
        assert (result.status, result.finish_reason, result.validation) == ('FINISHED', 'complete', 'INVALID')
        assert result.output_text == broken and result.raw == {'answer': broken}


def test_manifest_rejects_incomplete_scope_and_model_settings(tmp_path: Path) -> None:
    from nw.task_models import InputManifest, content_sha256
    from nw.tasks import freeze_manifest, model_settings

    package = {'scene': 'one'}
    with Store(tmp_path, create=True, test_mode=True) as store:
        settings = model_settings(Model(), 'test-model', {'max_tokens': 64}, 'write-v1')
        manifest = InputManifest('managed', 'write', settings, content_sha256(package))
        with pytest.raises(ValueError, match='scope'):
            freeze_manifest(store, manifest, package)
        scoped = replace(manifest, branch_id='main', state_revision=0, story_order=1, disclosure_order=1)
        with pytest.raises(ValueError, match='settings'):
            freeze_manifest(store, replace(scoped, settings={'prompt_version': 'write-v1'}), package)
        assert freeze_manifest(store, scoped, package) == 'managed'
