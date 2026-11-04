"""Model calls with persisted input/output and optional flow recovery IDs."""
from dataclasses import asdict
import json
from typing import Any
from uuid import uuid4

from nw.call_budget import _reserve, _settle, finish_reservation, prepare_call, reservation
from nw.call_control import check_test_provider, execution_lock, model_settings, outcome_for, send_model
from nw.context.registry import build_context
from nw.llm.base import LLMProvider
from nw.models import Draft, Run
from nw.store import Store, now
from nw.task_models import InputManifest, canonical, content_sha256
from nw.tasks import _insert_manifest, read_input_manifest


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def review_draft(store: Store, draft_id: str, provider: LLMProvider,
                 model: str, params: dict) -> Run:
    draft = store.get('draft', draft_id)
    context = json.loads(store.get('run', draft.run_id).context_package_json)
    messages = [{'role': 'system', 'content': '审查草稿与需求、设定和场景卡的一致性，列出具体修订意见；不要输出替代正文。'},
                {'role': 'user', 'content': encode({'context': context, 'draft': asdict(draft)})}]
    run, _ = call_model(store, draft.scene_id, provider, model, params, 'review', messages, context)
    return run


def write_scene(store: Store, scene_id: str, provider: LLMProvider,
                model: str, params: dict, *, context_name: str = 'minimal') -> tuple[Run, Draft | None]:
    check_test_provider(store, provider)
    context = build_context(store, scene_id, context_name)
    messages = [{'role': 'system', 'content': '根据作者需求、设定和场景卡创作本场景正文。只输出正文，不输出资料标签或解释。'},
                {'role': 'user', 'content': encode(context)}]
    return call_model(store, scene_id, provider, model, params, 'write', messages, context)


class RunInProgress(ValueError):
    pass


def _existing_run(store: Store, run_id: str, scene_id: str, kind: str) -> tuple[Run, Draft | None] | None:
    if store.connection.execute('SELECT 1 FROM runs WHERE id=?', (run_id,)).fetchone() is None:
        return None
    run = store.get('run', run_id)
    if (run.scene_id, run.kind) != (scene_id, kind):
        raise ValueError('Run ID belongs to a different scene or operation')
    return run, next((d for d in store.drafts(scene_id) if d.run_id == run_id), None)


def _mark_orphaned_reservation(store: Store, run: Run) -> None:
    hold = reservation(store, 'run', run.id)
    if not run.ended_at and hold is not None and hold['status'] == 'STARTED':
        finish_reservation(store, hold['id'], {}, 'UNKNOWN')


def recover_run(store: Store, run_id: str) -> Run | None:
    """Return the saved run and reconcile its hold, or None while the sender owns it."""
    with execution_lock(store, f'run:{run_id}') as acquired:
        if not acquired:
            return None
        run = store.get('run', run_id)
        _mark_orphaned_reservation(store, run)
        return run


def call_model(store: Store, scene_id: str, provider: LLMProvider, model: str,
               params: dict, kind: str, messages: list[dict], context: dict,
               run_id: str | None = None, *, budget_id: str | None = None,
               manifest_id: str | None = None) -> tuple[Run, Draft | None]:
    """Persist the request before sending; a previous run ID never sends twice."""
    check_test_provider(store, provider)
    run_id = run_id or uuid4().hex
    with execution_lock(store, f'run:{run_id}') as acquired:
        existing = _existing_run(store, run_id, scene_id, kind)
        if existing is not None:
            if acquired:
                _mark_orphaned_reservation(store, existing[0])
            return existing
        if not acquired:
            raise RunInProgress(f'Run is being started: {run_id}')
        return _new_run(store, scene_id, provider, model, params, kind, messages, context,
                        run_id, budget_id, manifest_id)


def _new_run(store: Store, scene_id: str, provider: LLMProvider, model: str, params: dict,
             kind: str, messages: list[dict], context: dict, run_id: str, budget_id: str | None,
             manifest_id: str | None) -> tuple[Run, Draft | None]:
    params, estimate = prepare_call(store, budget_id, provider.name, params, messages)
    legacy = manifest_id is None
    if not legacy:
        manifest, package = read_input_manifest(store, manifest_id)
        settings = model_settings(provider, model, params, manifest['settings']['prompt_version'])
        if (manifest['purpose'] != kind or canonical(settings) != canonical(manifest['settings'])
                or canonical(package) != canonical(context)):
            raise ValueError('Run inputs must match the frozen input manifest')
    else:
        settings = model_settings(provider, model, params, 'v0-scene-v1')
        manifest_id = f'run:{run_id}'
    snapshot = {**settings, 'messages': messages, 'manifest_id': manifest_id}
    run = Run(run_id, scene_id, kind, provider.name, model, encode(params), encode(snapshot),
              encode(context), '', 'error', '{}', now(), '')
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        if store.managed_story():
            raise ValueError('CONTEXT_PROVIDER_REQUIRED: managed writing and review need story context')
        hold = _reserve(store, budget_id, 'run', run_id, estimate)
        if hold is None:
            raise ValueError('Run call is already reserved')
        if legacy:
            _insert_manifest(store, InputManifest(manifest_id, kind, settings, content_sha256(context)), context, legacy=True)
        store._insert('run', run)
    result = send_model(provider, messages, model, params)
    return store.finish_run(run.id, result, settle=lambda: _settle(store, hold, result.usage, outcome_for(result)))
