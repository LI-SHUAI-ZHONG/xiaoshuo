"""Model calls with persisted input/output and optional flow recovery IDs."""
from dataclasses import asdict
import json
from typing import Any
from uuid import uuid4

from nw.context.registry import build_context
from nw.llm.base import GenResult, LLMProvider
from nw.models import Draft, Run
from nw.store import Store, now


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
    if provider.name == 'fake' and not store.test_mode:
        raise ValueError('fake is allowed only in isolated test stores')
    context = build_context(store, scene_id, context_name)
    messages = [{'role': 'system', 'content': '根据作者需求、设定和场景卡创作本场景正文。只输出正文，不输出资料标签或解释。'},
                {'role': 'user', 'content': encode(context)}]
    return call_model(store, scene_id, provider, model, params, 'write', messages, context)


def call_model(store: Store, scene_id: str, provider: LLMProvider, model: str,
               params: dict, kind: str, messages: list[dict], context: dict,
               run_id: str | None = None) -> tuple[Run, Draft | None]:
    """Persist before calling; deterministic flow IDs reuse completed calls on resume."""
    if provider.name == 'fake' and not store.test_mode:
        raise ValueError('fake is allowed only in isolated test stores')
    if run_id:
        row = store.connection.execute('SELECT id FROM runs WHERE id=?', (run_id,)).fetchone()
        if row:
            run = store.get('run', run_id)
            drafts = [d for d in store.drafts(scene_id) if d.run_id == run_id]
            return run, drafts[0] if drafts else None
    snapshot = {'messages': messages, 'model': model, 'params': params,
                'provider': provider.name, 'base_url': getattr(provider, 'base_url', None),
                'stream': False, 'timeout': getattr(provider, 'timeout', None)}
    run = Run(run_id or uuid4().hex, scene_id, kind, provider.name, model, encode(params),
              encode(snapshot), encode(context), '', 'error', '{}', now(), '')
    store.add_run(run)  # Persist before contacting the model; ended_at='' means interrupted/in progress.
    try:
        result = provider.generate(messages, model=model, **params)
    except Exception as exc:
        result = GenResult('', 'error', {}, None, {'error_type': type(exc).__name__})
    return store.finish_run(run.id, result)
