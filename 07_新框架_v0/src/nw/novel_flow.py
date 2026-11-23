
"""Persistent design and writing workflow over the M5–M8 services."""
from dataclasses import asdict
import json
from typing import Callable

from nw.acceptance import accept_batch
from nw.call_budget import extend_budget
from nw.call_control import check_test_provider, execution_lock, model_settings
from nw.cards import decide_card, eligible_rule_refs, read_card
from nw.config import Config
from nw.llm.base import LLMProvider
from nw.materials.binding import verify_materials
from nw.materials.scoped import precheck_scope, review_scope
from nw.novel_calls import JobCalls, call_id
from nw.novel_scene import scene_delta
from nw.novel_store import (JobPaused, JobRef, JobRequest, JobResult, Journal, cancel_job, checkpoint_input,
                            job_row, show_job, start_job)
from nw.plan_contract import validate_plan
from nw.planning import _known_cards, apply_plan, prepare_plan_task, show_plan
from nw.store import Store, now
from nw.story_dependencies import outline_ref
from nw.story_models import AcceptanceRequest, CardRef, StateDelta, StateHead
from nw.task_models import Ref, canonical
from nw.tasks import read_input_manifest

__all__ = ['JobRef', 'JobRequest', 'JobResult', 'cancel_job', 'resume_job', 'show_job', 'start_job']

Decision = Callable[[str, dict], dict | None]
TERMINAL = frozenset({'DONE', 'CANCELLED', 'REJECTED', 'STALE'})


def _routing_identity(settings: dict, config: Config) -> dict:
    """Window declarations guide local checks; only route/sampling changes break a frozen job."""
    base = {key: getattr(config, key) for key in ('provider', 'base_url', 'model', 'api_key_env', 'timeout', 'params')}
    stages = {}
    for stage, spec in settings.get('stage_models', {}).items():
        if not isinstance(spec, dict):
            stages[stage] = spec
            continue
        route = {key: value for key, value in spec.items() if key != 'context_window_tokens'}
        if route != base:
            stages[stage] = route
    return {**{key: value for key, value in settings.items() if key not in ('stage_models', 'context_window_tokens')},
            'stage_models': stages}


def _freeze_model(journal: Journal, settings: dict, config: Config) -> None:
    with journal.store.connection:
        journal.store.connection.execute('BEGIN IMMEDIATE')
        journal.check_active('model', check_head=False)
        row = job_row(journal.store, journal.id)
        frozen = canonical(settings)
        if row['model_json'] is None:
            journal.store.connection.execute('UPDATE novel_jobs SET model_json=? WHERE id=?', (frozen, journal.id))
        elif (row['model_json'] != frozen and
              _routing_identity(json.loads(row['model_json']), config) != _routing_identity(settings, config)):
            raise JobPaused('BLOCKED', row['step_key'], 'CONFIG_CHANGED: restore the original model settings')


def resume_job(store: Store, job_id: str, provider: LLMProvider, config: Config,
               decision: Decision | None = None, retry_failed: bool = False, *,
               max_calls: int | None = None, max_cost: str | None = None) -> JobResult:
    initial = show_job(store, job_id)
    if initial.status in TERMINAL:
        return initial
    check_test_provider(store, provider)
    if provider.name != config.provider:
        raise ValueError('Model provider must match the job configuration')
    with execution_lock(store, f'novel:{job_id}') as acquired:
        if not acquired:
            return JobResult(job_id, 'RUNNING', initial.step, reason='Another process holds the job')
        if job_row(store, job_id)['status'] in TERMINAL:
            return show_job(store, job_id)
        journal = Journal(store, job_id)
        calls = JobCalls(journal, provider, config, retry_failed)
        used_choice = False

        def decide(key: str, payload: dict) -> dict | None:
            nonlocal used_choice
            if decision is None or used_choice:
                return None
            choice = decision(key, payload)
            used_choice = choice is not None
            return choice

        try:
            frozen_model = model_settings(provider, config.model, config.params, 'novel-job-v1')
            if config.stage_models:
                frozen_model = {**frozen_model, 'stage_models': config.stage_models}
            _freeze_model(journal, frozen_model, config)
            extend_budget(store, job_id, max_calls, max_cost)
            journal.move('RUNNING', initial.step)
            if journal.request['mode'] == 'design':
                return _design(calls, decide)
            return _write_batch(calls, decide)
        except JobPaused as stop:
            return journal.move(stop.status, stop.step, str(stop), **stop.outputs)
        except ValueError as exc:
            reason = str(exc)
            status = 'STALE' if reason.startswith('STALE_') else 'BLOCKED'
            return journal.move(status, journal.current_step or initial.step, reason)


def _design(calls: JobCalls, decide: Decision) -> JobResult:
    journal = calls.journal
    if journal.request['design_scope'] == 'book':
        proposal, application = _plan_stage(calls, 'book', None, decide)
        return journal.move('DONE', 'plan:book:apply', proposal_id=proposal, application=application)
    parent = journal.request['parent_id']
    if parent is None:
        parent, _ = _plan_stage(calls, 'book', None, decide)
    proposal, application = _plan_stage(calls, journal.request['design_scope'], parent, decide)
    return journal.move('DONE', f"plan:{journal.request['design_scope']}:apply",
                        proposal_id=proposal, application=application)


def _scope_governance_inputs(raw_gov: dict | None, scope: str) -> dict | None:
    if not raw_gov:
        return None
    from nw.materials.phase_routes import phase_order
    allowed = set(phase_order(scope))
    if scope in raw_gov and isinstance(raw_gov[scope], dict):
        scoped = {k: v for k, v in raw_gov[scope].items() if k in allowed and isinstance(v, dict)}
        return scoped or None
    if 'detail' in raw_gov and scope != 'book' and isinstance(raw_gov['detail'], dict):
        scoped = {k: v for k, v in raw_gov['detail'].items() if k in allowed and isinstance(v, dict)}
        return scoped or None
    scoped = {k: v for k, v in raw_gov.items() if k in allowed and isinstance(v, dict)}
    return scoped or None


def _plan_stage(calls: JobCalls, scope: str, parent: str | None, decide: Decision) -> tuple[str, dict]:
    j = calls.journal
    propose = f'plan:{scope}:propose'
    confirm = f'plan:{scope}:confirm'
    apply = f'plan:{scope}:apply'
    applied = j.latest(apply)
    if applied and applied['status'] == 'DONE':
        output = applied['output']
        j.head = StateHead(**output['application']['branch_head'])
        return output['proposal_id'], output['application']
    plan_calls = calls.for_stage('plan')
    approved_direction = None
    if scope == 'book' and j.request.get('direction_review'):
        from nw.book_direction_flow import choose_direction

        approved_direction = choose_direction(plan_calls, decide)
    j.current_step = propose

    def prepare():
        j.check_active(propose)
        gov_for_scope = _scope_governance_inputs(j.request.get('governance_inputs'), scope)
        request, _ = prepare_plan_task(j.store, Ref(**j.request['brief_ref']), scope, plan_calls.provider, plan_calls.config,
                                       j.id, call_id(j.id, propose, 1), parent_id=parent, branch=j.head.branch_id,
                                       materials=j.request.get('materials', ()),
                                       material_deferrals=j.request.get('material_deferrals'),
                                       governance_inputs=gov_for_scope,
                                       production_method_policy=j.request.get('production_method_policy'),
                                       approved_direction=approved_direction)
        from nw.materials.work_session import drive_plan
        from nw.production_methods.selection import method_step
        _,package=read_input_manifest(j.store,request.manifest_id)
        def choose_method(stage: str,target: dict,validate_choice: Callable) -> dict:
            key=method_step(scope, stage, cast_revision=bool(target.get('cast_revision')))
            choice=j.gate(key,target,decide,{'approve':'novel_confirm','reject':'novel_reject'},validate_choice)
            return {'choice':choice,'decision_id':f'{j.id}:{key}'}
        request,_=drive_plan(j.store,request,package,plan_calls.provider,plan_calls.config,retry_failed=calls.retry_failed,
                            verify=lambda:j.check_active(propose),method_decision=choose_method)
        return request

    def validate(output: dict) -> None:
        step = j.latest(propose)
        _, package = read_input_manifest(j.store, step['input']['request']['manifest_id'])
        from nw.materials.phase_projection import expand_output
        validate_plan(expand_output(output,package), scope, _known_cards(package), package.get('materials', ()),
                      package.get('material_deferrals'),package.get('material_work'),package.get('length_context'),
                      approved_direction=package.get('approved_direction'))

    def verify_plan() -> None:
        j.check_active(j.current_step or propose)
        step = j.latest(propose)
        manifest, frozen = read_input_manifest(j.store, step['input']['request']['manifest_id'])
        if frozen.get('approved_direction') != approved_direction:
            raise JobPaused('STALE', propose, 'STALE_BOOK_DIRECTION: 全书设计所用的确认方向已变化')
        verify_materials(j.store.directory.parent, frozen.get('materials', ()))
        if frozen.get('material_work'):
            from nw.materials.work_catalog import SourceDesk
            SourceDesk(j.store.directory.parent).verify(frozen['material_work']['sources'])
            from nw.production_methods.selection import verify_sources
            verify_sources(j.store,frozen['material_work'])
        if asdict(outline_ref(j.store)) != manifest['dependency_refs'][0]:
            raise JobPaused('STALE', propose, 'STALE_OUTLINE')
        selected = {CardRef(card['card_id'], card['version']) for card in frozen['method_cards']}
        if not selected <= set(eligible_rule_refs(j.store)):
            raise JobPaused('STALE', propose, 'STALE_METHOD_VERSION')

    result = plan_calls.task(propose, prepare, validate, verify=verify_plan)
    proposal = show_plan(j.store, result.id)
    if proposal.application is None:
        verify_plan()
    candidates = [
        {'root': read_card(j.store, CardRef(**item['root'])),
         'members': [read_card(j.store, CardRef(**ref)) for _, ref in sorted(item['members'].items())],
         **({'material_design': item['material_design']} if 'material_design' in item else {})}
        for item in proposal.materialization
    ]
    # Decision targets describe immutable versions; the approval changes only the separate decision log.
    for candidate in candidates:
        for card in [candidate['root'], *candidate['members']]:
            card.pop('status')
    roots = {ref.card_id: ref for ref in proposal.candidate_cards}

    def check_choice(choice: dict) -> None:
        root = choice.get('root')
        if choice['action'] == 'approve' and (not isinstance(root, str) or root not in roots):
            raise ValueError('Choose a root card from the current proposal')

    target = {'proposal_id': proposal.id, 'candidates': candidates, 'findings': proposal.findings}
    if approved_direction is not None:
        target['approved_direction'] = approved_direction
    choice = j.gate(confirm, target,
                    decide, {'approve': 'novel_confirm', 'reject': 'novel_reject'}, check_choice)
    if choice['action'] == 'reject':
        raise JobPaused('REJECTED', confirm, 'PLAN_REJECTED')
    approval_id = call_id(j.id, confirm, 1)
    if applied is None:
        j.reserve(apply, {'proposal_id': proposal.id, 'decision_id': approval_id})
    if proposal.application is None:
        j.check_active(apply)
        decide_card(j.store, roots[choice['root']], 'approved', choice['reason'], decision_id=approval_id)
    apply_plan(j.store, proposal.id, approval_id, before_apply=verify_plan)
    application = show_plan(j.store, proposal.id).application
    j.result(apply, 'DONE', {'proposal_id': proposal.id, 'application': application})
    j.head = StateHead(**application['branch_head'])
    return proposal.id, application


def _write_batch(calls: JobCalls, decide: Decision) -> JobResult:
    j = calls.journal
    scenes = j.request['scene_ids']
    precheck_scope(j.store, scenes, j.head)
    deltas = []
    chain = ()
    for scene in scenes:
        delta = scene_delta(calls, scene, chain, decide)
        deltas.append(delta)
        chain = (*chain, (delta.id, delta.sha256))
    scoped = review_scope(calls.for_stage('scope_review'), deltas)
    gate = 'batch:confirm'
    previews = [_preview(j, scene, delta) for scene, delta in zip(scenes, deltas, strict=True)]

    def check_choice(choice: dict) -> None:
        if 'scene_id' in choice and (choice['action'] != 'reject' or choice['scene_id'] not in scenes):
            raise ValueError('Reject a scene from this batch or reject the whole batch')

    choice = j.gate(gate, {'scenes': previews, 'head': asdict(j.head),
                         **({'material_scope_review': scoped} if scoped else {})}, decide,
                    {'accept': 'novel_confirm', 'reject': 'novel_reject'}, check_choice)
    if choice['action'] == 'reject':
        rejected = choice.get('scene_id')
        stale = scenes[scenes.index(rejected) + 1:] if rejected else scenes
        with j.store.connection:
            j.store.connection.execute('BEGIN IMMEDIATE')
            j.check_active(gate)
            for scene in stale:
                prefix = f'scene:{scene}:'
                j.store.connection.execute("""UPDATE novel_steps SET status='STALE'
                    WHERE job_id=? AND substr(step_key,1,length(?))=?""", (j.id, prefix, prefix))
            j.store.connection.execute(
                "UPDATE novel_jobs SET status='REJECTED',step_key=?,reason='BATCH_REJECTED',output_json=? WHERE id=?",
                (gate, canonical({'rejected_scene': rejected, 'stale_scenes': stale}), j.id))
        return show_job(j.store, j.id)
    requests = _acceptance_requests(j, scenes, deltas, choice['reason'])
    key = 'batch:accept'
    commit = f'novel:{j.id}'
    expected = checkpoint_input(requests, j.head, commit)
    row = j.latest(key)
    if row is None:
        row = j.reserve(key, expected)
    accept_batch(j.store, requests, j.head, commit, checkpoint=(j.id, key, row['attempt']))
    return show_job(j.store, j.id)


def _preview(j: Journal, scene: str, delta: StateDelta) -> dict:
    checks = j.latest(f'scene:{scene}:check')['output']
    return {'scene_id': scene, 'draft': asdict(j.store.get('draft', delta.draft_id)),
            'delta_id': delta.id, 'manifest_id': delta.manifest_id, 'delta_sha256': delta.sha256,
            'operations': delta.operations, **checks}


def _acceptance_requests(j: Journal, scenes: list[str], deltas: list[StateDelta],
                         reason: str) -> list[AcceptanceRequest]:
    requests = []
    with j.store.connection:
        j.store.connection.execute('BEGIN IMMEDIATE')
        j.check_active('batch:accept')
        for scene, delta in zip(scenes, deltas, strict=True):
            fields = {'branch_id': j.head.branch_id, 'scene_id': scene, 'draft_id': delta.draft_id,
                      'delta_id': delta.id, 'manifest_id': delta.manifest_id}
            ident = call_id(j.id, f'accept:{scene}', 1)
            j.store.connection.execute('INSERT INTO story_decisions VALUES (?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
                                       (ident, 'accept', canonical(fields), reason, now()))
            requests.append(AcceptanceRequest(**fields, decision_id=ident))
    return requests
