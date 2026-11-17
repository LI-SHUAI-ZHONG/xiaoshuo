
"""Dispatch only the model inputs frozen by the current job attempt."""
from dataclasses import asdict, replace
import json
from typing import Callable
from uuid import NAMESPACE_URL, uuid5

from nw.call_budget import BudgetExceeded, reservation
from nw.config import Config
from nw.generation import call_model
from nw.llm.base import LLMProvider
from nw.models import Draft, Run
from nw.novel_store import JobPaused, Journal
from nw.task_models import InputManifest, TaskRequest, TaskResult
from nw.tasks import run_task


def call_id(job: str, key: str, attempt: int) -> str:
    return uuid5(NAMESPACE_URL, f'nw:novel:{job}:{key}:{attempt}').hex


class JobCalls:
    def __init__(self, journal: Journal, provider: LLMProvider, config: Config, retry_failed: bool) -> None:
        self.journal, self.provider, self.config = journal, provider, config
        self.retry_failed = retry_failed

    def _blocked(self, key: str, reason: str, **outputs: str) -> JobPaused:
        return JobPaused('BLOCKED', key, reason, **outputs)

    def run(self, key: str, scene_id: str, prepare: Callable[[], dict],
            validate: Callable[[Run], dict] | None = None, *,
            verify: Callable[[], None] | None = None) -> tuple[Run, Draft | None, dict]:
        j = self.journal
        step = j.latest(key)
        if step is None:
            step = j.reserve(key, prepare())
        if step['status'] == 'FAILED':
            if not self.retry_failed:
                raise self._blocked(key, step['output']['reason'], run_id=step['output']['run_id'])
            step = j.reserve(key, step['input'], attempt=step['attempt'] + 1)
        frozen = step['input']
        ident = call_id(j.id, key, step['attempt'])
        manifest = replace(InputManifest(**frozen['manifest']), id=f'run:{ident}')
        if manifest.selection is not None:
            manifest = replace(manifest, selection={**manifest.selection, 'manifest_id': manifest.id})
        try:
            run, draft = call_model(j.store, scene_id, self.provider, self.config.model, self.config.params,
                                    manifest.purpose, frozen['messages'], frozen['package'], ident,
                                    budget_id=j.id, story_manifest=manifest,
                                    before_reserve=verify or (lambda: j.check_active(key)))
        except BudgetExceeded as exc:
            raise self._blocked(key, str(exc)) from exc
        if step['status'] == 'DONE':
            return run, draft, step['output']
        hold = reservation(j.store, 'run', ident)
        outcome = ('UNKNOWN' if not run.ended_at or hold and hold['status'] == 'UNKNOWN' and
                   run.finish_reason != 'complete' else run.finish_reason)
        if outcome != 'complete':
            reason = f'{manifest.purpose} {outcome}'
            j.result(key, 'FAILED', {'run_id': ident, 'reason': reason})
            raise self._blocked(key, reason, run_id=ident)
        try:
            structured = validate(run) if validate else {}
        except (ValueError, RecursionError) as exc:
            reason = f'INVALID_REVIEW: {exc}'
            j.result(key, 'FAILED', {'run_id': ident, 'reason': reason})
            raise self._blocked(key, reason, run_id=ident) from exc
        if manifest.purpose in ('write', 'revise') and draft is None:
            raise self._blocked(key, 'Complete run did not produce a draft', run_id=ident)
        result = {'run_id': ident, 'draft_id': draft.id if draft else None, 'manifest_id': manifest.id, **structured}
        j.result(key, 'DONE', result)
        return run, draft, result

    def task(self, key: str, prepare: Callable[[], TaskRequest],
             validate: Callable[[dict], None], *, verify: Callable[[], None] | None = None) -> TaskResult:
        j = self.journal
        step = j.latest(key)
        if step is None:
            request = prepare()
            step = j.reserve(key, {'request': asdict(request)})
        if step['status'] == 'FAILED':
            if not self.retry_failed:
                raise self._blocked(key, step['output']['reason'], task_id=step['output']['task_id'])
            previous = TaskRequest(**step['input']['request'])
            request = replace(previous, id=call_id(j.id, key, step['attempt'] + 1),
                              retry_of=previous.id, attempt=previous.attempt + 1)
            step = j.reserve(key, {'request': asdict(request)}, attempt=step['attempt'] + 1)
        request = TaskRequest(**step['input']['request'])
        result = run_task(j.store, request, self.provider, self.config, validate=validate,
                          before_reserve=verify or (lambda: j.check_active(key)))
        if result.validation == 'VALID':
            if step['status'] != 'DONE':
                j.result(key, 'DONE', {'task_id': result.id, 'manifest_id': request.manifest_id})
            return result
        if result.status in ('RUNNING', 'BUDGET_EXCEEDED'):
            raise self._blocked(key, result.reason or result.status, task_id=result.id)
        reason = (result.reason if result.reason and result.reason.startswith(
            ('MATERIAL_DESIGN:','MATERIAL_WORK:','MATERIAL_STAGE:','MATERIAL_WAITING_INPUTS:'))
                  else f'{request.kind} {result.status}/{result.validation}')
        j.result(key, 'FAILED', {'task_id': result.id, 'reason': reason})
        raise self._blocked(key, reason, task_id=result.id)
