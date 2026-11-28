"""Model calls with persisted input/output and optional flow recovery IDs."""
from dataclasses import asdict, replace
import json
from typing import Any, Callable
from uuid import uuid4

from nw.call_budget import _reserve, _settle, create_budget, finish_reservation, prepare_call, reservation
from nw.call_control import check_test_provider, execution_lock, model_settings, outcome_for, send_model
from nw.cards import eligible_rule_refs
from nw.context.registry import build_context
from nw.context.story import StoryScope, build_story_context, scene_scope
from nw.materials.stage_input import step_material_prompt
from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
from nw.story_delta import draft_ref, story_write_manifest
from nw.story_dependencies import add_dependency, check_inputs_current
from nw.story_state import current_head
from nw.story_models import CardRef, StateHead
from nw.llm.base import LLMProvider
from nw.models import Draft, Run
from nw.store import Store, now
from nw.task_models import Budget, InputManifest, Ref, canonical, content_sha256
from nw.tasks import _insert_manifest, read_input_manifest


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def review_draft(store: Store, draft_id: str, provider: LLMProvider,
                 model: str, params: dict, *, budget: Budget | None = None) -> Run:
    draft = store.get('draft', draft_id)
    original = store.get('run', draft.run_id)
    context = json.loads(original.context_package_json)
    frozen = None
    if budget is not None and not store.managed_story():
        raise ValueError('Story budget requires story adoption')
    if store.managed_story():
        ident = json.loads(original.input_snapshot_json).get('manifest_id')
        if not ident:
            raise ValueError('CONTEXT_PROVIDER_REQUIRED: review requires a frozen story draft')
        frozen = story_write_manifest(store, draft)
        if frozen is None:
            raise ValueError('CONTEXT_PROVIDER_REQUIRED: review requires a frozen story draft')
    prompt = '审查草稿与需求、设定和场景卡的一致性，列出具体修订意见；不要输出替代正文。'
    if frozen is not None:
        # This entry reviews the already frozen scene context. Formal material
        # checks with dedicated source contracts are handled in the novel job.
        prompt = step_material_prompt(prompt, REVIEW_MATERIAL, ())
    messages = [{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': encode({'context': context, 'draft': asdict(draft)})}]
    budget_id, manifest = None, None
    if frozen is not None:
        if budget is None:
            raise ValueError('BUDGET_REQUIRED: managed review needs an explicit budget')
        budget_id = create_budget(store, uuid4().hex, budget)
        effective, _ = prepare_call(store, budget_id, provider.name, params, messages)
        manifest = replace(InputManifest(**frozen), id=uuid4().hex, purpose='review',
                           dependency_refs=(*frozen['dependency_refs'], draft_ref(draft)),
                           settings=model_settings(provider, model, effective, 'story-review-v1'))
    run, _ = call_model(store, draft.scene_id, provider, model, params, 'review', messages, context,
                        budget_id=budget_id, story_manifest=manifest)
    return run


def write_scene(store: Store, scene_id: str, provider: LLMProvider,
                model: str, params: dict, *, context_name: str | None = None,
                story_scope: StoryScope | None = None, budget: Budget | None = None,
                branch: str = 'main') -> tuple[Run, Draft | None]:
    check_test_provider(store, provider)
    if store.managed_story():
        if context_name not in (None, 'story'):
            raise ValueError('CONTEXT_PROVIDER_REQUIRED: managed writing requires story context')
        scope = story_scope or scene_scope(store, scene_id, branch)
        if budget is None:
            raise ValueError('BUDGET_REQUIRED: managed writing needs an explicit budget')
        work = build_story_context(store, scene_id, scope, budget.context_char_limit)
        messages = [{'role': 'system', 'content': work.prompt},
                    {'role': 'user', 'content': canonical(work.package)}]
        budget_id = create_budget(store, uuid4().hex, budget)
        effective, _ = prepare_call(store, budget_id, provider.name, params, messages)
        manifest_id = uuid4().hex
        manifest = InputManifest(
            manifest_id, 'write', model_settings(provider, model, effective, 'story-write-v1'),
            content_sha256(work.package), brief_ref=work.brief_ref, card_refs=work.card_refs,
            source_refs=work.source_refs, branch_id=scope.branch_id, state_revision=scope.revision,
            story_order=scope.story_order, disclosure_order=work.disclosure,
            predecessor_drafts=work.predecessor_drafts, dependency_refs=work.dependency_refs,
            selection={**work.selection, 'manifest_id': manifest_id}, material_design_sha256=work.material_design_sha256)
        return call_model(store, scene_id, provider, model, params, 'write', messages, work.package,
                          budget_id=budget_id, story_manifest=manifest)
    if story_scope is not None or budget is not None or branch != 'main':
        raise ValueError('Story scope and budget require story adoption')
    context = build_context(store, scene_id, context_name or 'minimal')
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
               manifest_id: str | None = None,
               story_manifest: InputManifest | None = None, context_window_tokens: int | None = None,
               before_reserve: Callable[[], None] | None = None) -> tuple[Run, Draft | None]:
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
                        run_id, budget_id, manifest_id, story_manifest, before_reserve, context_window_tokens)


def _new_run(store: Store, scene_id: str, provider: LLMProvider, model: str, params: dict,
             kind: str, messages: list[dict], context: dict, run_id: str, budget_id: str | None,
             manifest_id: str | None, story_manifest: InputManifest | None,
             before_reserve: Callable[[], None] | None, context_window_tokens: int | None) -> tuple[Run, Draft | None]:
    saved = read_input_manifest(store, manifest_id) if manifest_id is not None and story_manifest is None else None
    frozen_params = saved[0]['settings']['params'] if saved else None
    if story_manifest is not None:
        frozen_params = story_manifest.settings['params']
    params, estimate = prepare_call(store, budget_id, provider.name, params, messages,
                                    context_window_tokens=context_window_tokens, frozen_params=frozen_params)
    legacy = manifest_id is None and story_manifest is None
    if story_manifest is not None:
        settings = model_settings(provider, model, params, story_manifest.settings['prompt_version'])
        if manifest_id is not None or settings != story_manifest.settings or story_manifest.purpose != kind:
            raise ValueError('Story run inputs must match the frozen input manifest')
        manifest_id = story_manifest.id
    elif saved:
        manifest, package = saved
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
        if before_reserve:
            before_reserve()
        if store.managed_story() != (story_manifest is not None):
            raise ValueError('CONTEXT_PROVIDER_REQUIRED: managed writing and review need story context')
        if story_manifest is not None:
            refs = _story_run_refs(story_manifest)
            if kind == 'write':
                if current_head(store, story_manifest.branch_id) != StateHead(story_manifest.branch_id, story_manifest.state_revision):
                    raise ValueError('STALE_HEAD')
                check_inputs_current(store, refs)
                selected = {CardRef(**ref) for ref in (story_manifest.selection or {}).get('selected_refs', [])}
                if selected and not selected <= set(eligible_rule_refs(store)):
                    raise ValueError('STALE_INPUT: selected method version changed before the call')
            _insert_manifest(store, story_manifest, context)
            consumer = Ref('run', run.id, 1, content_sha256(asdict(story_manifest)))
            for producer in refs:
                add_dependency(store, consumer, producer)
        hold = _reserve(store, budget_id, 'run', run_id, estimate)
        if hold is None:
            raise ValueError('Run call is already reserved')
        if legacy:
            _insert_manifest(store, InputManifest(manifest_id, kind, settings, content_sha256(context)), context, legacy=True)
        store._insert('run', run)
    live_provider = provider.name != 'fake'
    result = send_model(
        provider, messages, model, params,
        allow_continuation=(live_provider and kind in ('write', 'revise')),
        max_empty_retries=(2 if live_provider else 0),
    )
    return store.finish_run(run.id, result, settle=lambda: _settle(store, hold, result.usage, outcome_for(result)))


def _story_run_refs(manifest: InputManifest) -> list[Ref]:
    refs = [*manifest.dependency_refs, *manifest.predecessor_drafts,
            *(Ref('delta', ident, 1, digest) for ident, digest in manifest.candidate_delta_refs)]
    if manifest.brief_ref:
        refs.append(manifest.brief_ref)
    return [Ref(**ref) if isinstance(ref, dict) else ref for ref in refs]
