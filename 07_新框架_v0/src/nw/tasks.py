"""Project-scoped model calls: freeze, reserve, send, record, and validate."""
from dataclasses import asdict, is_dataclass
import json
import math
import sqlite3
from urllib.parse import urlsplit
from typing import Callable

from nw.call_budget import (BudgetExceeded, _reserve, _settle, create_budget, finish_reservation,
                            prepare_call, read_budget, reservation, reserve_call)
from nw.call_control import check_test_provider, execution_lock, model_settings, outcome_for, send_model
from nw.config import Config
from nw.llm.base import LLMProvider
from nw.store import Store, now
from nw.task_models import (TASK_KINDS, InputManifest, TaskRequest, TaskResult, _sha256, canonical,
                            content_sha256, response_json, validate_task_output)

__all__ = [
    'BudgetExceeded', 'create_budget', 'execution_lock', 'finish_reservation', 'freeze_manifest',
    'model_settings', 'read_budget', 'read_input_manifest', 'read_task', 'reserve_call',
    'run_task', 'validate_task_output',
]


def _check_settings(settings: dict) -> None:
    keys = {'provider', 'model', 'params', 'prompt_version', 'base_url', 'timeout', 'stream'}
    if (not isinstance(settings, dict) or set(settings) != keys or settings['stream'] is not False or
            any(not isinstance(settings[k], str) or not settings[k].strip()
                for k in ('provider', 'model', 'prompt_version')) or
            not isinstance(settings['params'], dict) or
            any(not isinstance(key, str) or key.lower() in {'api_key', 'authorization', 'headers', 'token'}
                for key in settings['params'])):
        raise ValueError('Invalid manifest model settings')
    timeout, base_url = settings['timeout'], settings['base_url']
    if timeout is not None and (type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('Invalid manifest model settings timeout')
    if base_url is not None:
        if not isinstance(base_url, str):
            raise ValueError('Invalid manifest model settings endpoint')
        url = urlsplit(base_url)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username is not None
                or url.password is not None or url.query or url.fragment):
            raise ValueError('Invalid manifest model settings endpoint')


def _disclosure_position(value: object) -> bool:
    return (type(value) is int or isinstance(value, (tuple, list)) and len(value) == 3
            and all(type(part) is int and part >= 0 for part in value))


def _insert_manifest(store: Store, inputs: InputManifest, package: dict, *, legacy: bool = False) -> str:
    if (not inputs.id or inputs.schema_version != 1 or
            inputs.purpose not in TASK_KINDS | {'write', 'review', 'revise'} or not isinstance(package, dict)):
        raise ValueError('Invalid input manifest')
    _check_settings(inputs.settings)
    scoped = (inputs.branch_id, inputs.state_revision, inputs.story_order, inputs.disclosure_order)
    if (any(v is not None for v in scoped) or
            (not legacy and inputs.purpose not in ('plan', 'rule_extract', 'material_work'))):
        if (not isinstance(inputs.branch_id, str) or not inputs.branch_id or
                type(inputs.state_revision) is not int or inputs.state_revision < 0 or
                type(inputs.story_order) is not int or not _disclosure_position(inputs.disclosure_order)):
            raise ValueError('Input manifest requires complete story scope: branch, revision and both orders')
    if inputs.context_sha256 != content_sha256(package):
        raise ValueError('Input manifest context hash mismatch')
    if inputs.material_design_sha256 is not None and not _sha256(inputs.material_design_sha256):
        raise ValueError('Invalid material design hash')
    payload = asdict(inputs)
    for optional in ('selection', 'novel_job_id', 'material_design_sha256'):
        if payload[optional] is None:
            payload.pop(optional)
    frozen = canonical(payload), canonical(package), inputs.context_sha256
    row = store.connection.execute(
        'SELECT payload_json,package_json,sha256 FROM input_manifests WHERE id=?', (inputs.id,)).fetchone()
    if row:
        if tuple(row) != frozen:
            raise ValueError('Input manifest ID already freezes different inputs')
    else:
        store.connection.execute('INSERT INTO input_manifests VALUES (?,?,?,?)', (inputs.id, *frozen))
    return inputs.id


def freeze_manifest(store: Store, inputs: InputManifest, package: dict) -> str:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        return _insert_manifest(store, inputs, asdict(package) if is_dataclass(package) else package)


def read_input_manifest(store: Store, manifest_id: str) -> tuple[dict, dict]:
    row = store.connection.execute('SELECT * FROM input_manifests WHERE id=?', (manifest_id,)).fetchone()
    if row is None:
        raise ValueError(f'Input manifest not found: {manifest_id}')
    payload, package = json.loads(row['payload_json']), json.loads(row['package_json'])
    if payload['context_sha256'] != row['sha256'] or content_sha256(package) != row['sha256']:
        raise ValueError('Input manifest context hash mismatch')
    return payload, package


def _task(store: Store, task_id: str) -> sqlite3.Row | None:
    return store.connection.execute('SELECT * FROM task_calls WHERE id=?', (task_id,)).fetchone()


def _result(row: sqlite3.Row, *, running: bool = False) -> TaskResult:
    return TaskResult(row['id'], 'RUNNING' if running else row['status'], row['finish_reason'],
                      row['validation'], json.loads(row['result_json']), json.loads(row['output_text_json']),
                      json.loads(row['raw_json']), json.loads(row['request_id_json']), json.loads(row['usage_json']),
                      row['reason'])


def _recover_task(store: Store, row: sqlite3.Row) -> TaskResult:
    """Only call while holding the root lock: a remaining STARTED row is orphaned."""
    if row['status'] == 'STARTED':
        with store.connection:
            store.connection.execute('BEGIN IMMEDIATE')
            store.connection.execute(
                "UPDATE task_calls SET status='UNKNOWN',reason='INTERRUPTED' WHERE id=?", (row['id'],))
            hold = reservation(store, 'task', row['id'])
            _settle(store, hold['id'], {}, 'UNKNOWN')
        row = _task(store, row['id'])
    return _result(row)


def read_task(store: Store, task_id: str) -> TaskResult:
    row = _task(store, task_id)
    if row is None:
        raise ValueError(f'Task not found: {task_id}')
    if row['status'] != 'STARTED':
        return _result(row)
    with execution_lock(store, f"task:{row['root_id']}") as acquired:
        return _recover_task(store, _task(store, task_id)) if acquired else _result(row, running=True)


def _check_retry(store: Store, request: TaskRequest, parent: sqlite3.Row) -> None:
    # Both the entire input and the selected provider settings must remain frozen.
    original = json.loads(parent['request_json'])
    original.update(id=request.id, attempt=request.attempt, retry_of=request.retry_of)
    if (request.attempt != parent['attempt'] + 1 or canonical(original) != canonical(asdict(request)) or
            store.connection.execute('SELECT 1 FROM task_calls WHERE retry_of=?', (parent['id'],)).fetchone()):
        raise ValueError('Invalid retry: use the latest failed attempt and its frozen inputs')
    previous = _recover_task(store, parent)
    if previous.validation == 'VALID':
        raise ValueError('Cannot retry a valid task result')


def _check_request(store: Store, request: TaskRequest) -> None:
    if (not request.id or request.kind not in TASK_KINDS or request.project_id != store.project().id or
            type(request.attempt) is not int or request.attempt < 1 or
            (request.attempt == 1) != (request.retry_of is None)):
        raise ValueError('Invalid project task request')


def run_task(store: Store, request: TaskRequest, provider: LLMProvider, config: Config, *,
             validate: Callable[[dict], None] | None = None,
             before_reserve: Callable[[], None] | None = None) -> TaskResult:
    _check_request(store, request)
    check_test_provider(store, provider)
    parent = _task(store, request.retry_of) if request.retry_of is not None else None
    if request.retry_of is not None and parent is None:
        raise ValueError('Cannot retry a missing task')
    root = parent['root_id'] if parent else request.id
    request_json = canonical(asdict(request))
    with execution_lock(store, f'task:{root}') as acquired:
        row = _task(store, request.id)
        if row is not None:
            if row['request_json'] != request_json:
                raise ValueError('Task ID already freezes different inputs')
            if acquired:
                return _recover_task(store, row)
            return _result(row, running=row['status'] == 'STARTED')
        if not acquired:
            return TaskResult(request.id, 'RUNNING')
        if parent is not None:
            _check_retry(store, request, _task(store, parent['id']))
        return _start_task(store, request, request_json, root, provider, config, validate, before_reserve)


def _start_task(store: Store, request: TaskRequest, request_json: str, root: str,
                provider: LLMProvider, config: Config, validate: Callable[[dict], None] | None,
                before_reserve: Callable[[], None] | None) -> TaskResult:
    manifest, _ = read_input_manifest(store, request.manifest_id)
    messages = json.loads(request_json)['payload'].get('messages')
    if (not isinstance(messages, list) or not messages or
            any(not isinstance(msg, dict) or set(msg) != {'role', 'content'} or
                msg['role'] not in ('system', 'user', 'assistant') or not isinstance(msg['content'], str)
                for msg in messages)):
        raise ValueError('Task payload requires role/content messages')
    try:
        params, estimate = prepare_call(store, request.budget_id, provider.name, config.params, messages,
                                        context_window_tokens=getattr(config, 'context_window_tokens', None),
                                        frozen_params=manifest['settings']['params'])
        settings = model_settings(provider, config.model, params, manifest['settings']['prompt_version'])
        if (provider.name != config.provider or manifest['purpose'] != request.kind or
                canonical(settings) != canonical(manifest['settings'])):
            raise ValueError('Provider, settings and task purpose must match the frozen input manifest')
        with store.connection:
            store.connection.execute('BEGIN IMMEDIATE')
            if before_reserve:
                before_reserve()
            hold = _reserve(store, request.budget_id, 'task', request.id, estimate)
            if hold is None:
                raise ValueError('Task call is already reserved')
            store.connection.execute(
                """INSERT INTO task_calls(id,project_id,kind,manifest_id,manifest_json,request_json,messages_json,
                   budget_id,root_id,attempt,retry_of,status,started_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,'STARTED',?)""",
                (request.id, request.project_id, request.kind, request.manifest_id, canonical(manifest),
                 request_json, canonical(messages), request.budget_id, root, request.attempt, request.retry_of, now()))
    except BudgetExceeded as exc:
        return TaskResult(request.id, 'BUDGET_EXCEEDED', reason=str(exc))

    result = send_model(provider, messages, config.model, params)
    validation, parsed, reason = 'UNREVIEWED', None, None
    status = outcome_for(result)
    if result.finish_reason == 'complete':
        try:
            parsed = validate_task_output(request.kind, result.text)
            if validate is not None:
                validate(parsed)
            validation = 'VALID'
        except (ValueError, RecursionError) as exc:
            parsed = None
            validation, reason = 'INVALID', 'INVALID_STRUCTURED_OUTPUT'
            if request.kind in ('plan','material_work') and str(exc).startswith(
                    ('MATERIAL_DESIGN:','MATERIAL_WORK:','MATERIAL_STAGE:','MATERIAL_WAITING_INPUTS:',
                     'MATERIAL_GOVERNANCE:','PROJECT_METHOD:','METHOD_DESIGN_REQUIRED:','STALE_PROJECT_METHOD:')):
                reason = str(exc)
    elif status == 'UNKNOWN':
        reason = 'PROVIDER_OUTCOME_UNKNOWN'
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            """UPDATE task_calls SET status=?,output_text_json=?,raw_json=?,finish_reason=?,validation=?,
               result_json=?,request_id_json=?,usage_json=?,reason=?,ended_at=? WHERE id=?""",
            (status, response_json(result.text), response_json(result.raw), result.finish_reason, validation,
             canonical(parsed), response_json(result.request_id), response_json(result.usage), reason, now(), request.id))
        _settle(store, hold, result.usage, status)
    return _result(_task(store, request.id))
