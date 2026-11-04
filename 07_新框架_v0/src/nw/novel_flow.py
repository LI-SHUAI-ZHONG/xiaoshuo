
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


def _freeze_model(journal: Journal, settings: dict) -> None:
    with journal.store.connection:
        journal.store.connection.execute('BEGIN IMMEDIATE')
        journal.check_active('model', check_head=False)
        row = job_row(journal.store, journal.id)
        frozen = canonical(settings)
        if row['model_json'] is None:
            journal.store.connection.execute('UPDATE novel_jobs SET model_json=? WHERE id=?', (frozen, journal.id))
        elif row['model_json'] != frozen:
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
            _freeze_model(journal, model_settings(provider, config.model, config.params, 'novel-job-v1'))
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
    parent = journal.request['parent_id']
    if parent is None:
        parent, _ = _plan_stage(calls, 'book', None, decide)
    proposal, application = _plan_stage(calls, journal.request['design_scope'], parent, decide)
    return journal.move('DONE', f"plan:{journal.request['design_scope']}:apply",
                        proposal_id=proposal, application=application)


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
    j.current_step = propose

    def prepare():
        j.check_active(propose)
        request, _ = prepare_plan_task(j.store, Ref(**j.request['brief_ref']), scope, calls.provider, calls.config,
                                       j.id, call_id(j.id, propose, 1), parent_id=parent, branch=j.head.branch_id)
        return request

    def validate(output: dict) -> None:
        step = j.latest(propose)
        _, package = read_input_manifest(j.store, step['input']['request']['manifest_id'])
        validate_plan(output, scope, _known_cards(package))

    def verify_plan() -> None:
        j.check_active(j.current_step or propose)
        step = j.latest(propose)
        manifest, frozen = read_input_manifest(j.store, step['input']['request']['manifest_id'])
        if asdict(outline_ref(j.store)) != manifest['dependency_refs'][0]:
            raise JobPaused('STALE', propose, 'STALE_OUTLINE')
        selected = {CardRef(card['card_id'], card['version']) for card in frozen['method_cards']}
        if not selected <= set(eligible_rule_refs(j.store)):
            raise JobPaused('STALE', propose, 'STALE_METHOD_VERSION')

    result = calls.task(propose, prepare, validate, verify=verify_plan)
    proposal = show_plan(j.store, result.id)
    if proposal.application is None:
        verify_plan()
    candidates = [
        {'root': read_card(j.store, CardRef(**item['root'])),
         'members': [read_card(j.store, CardRef(**ref)) for _, ref in sorted(item['members'].items())]}
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

    choice = j.gate(confirm, {'proposal_id': proposal.id, 'candidates': candidates, 'findings': proposal.findings},
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
    deltas = []
    chain = ()
    for scene in scenes:
        delta = scene_delta(calls, scene, chain, decide)
        deltas.append(delta)
        chain = (*chain, (delta.id, delta.sha256))
    gate = 'batch:confirm'
    previews = [_preview(j, scene, delta) for scene, delta in zip(scenes, deltas, strict=True)]

    def check_choice(choice: dict) -> None:
        if 'scene_id' in choice and (choice['action'] != 'reject' or choice['scene_id'] not in scenes):
            raise ValueError('Reject a scene from this batch or reject the whole batch')

    choice = j.gate(gate, {'scenes': previews, 'head': asdict(j.head)}, decide,
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
    return {'scene_id': scene, 'draft': asdict(j.store.get('draft', delta.draft_id)),
            'delta_id': delta.id, 'manifest_id': delta.manifest_id, 'delta_sha256': delta.sha256,
            'operations': delta.operations, 'findings': j.latest(f'scene:{scene}:check')['output']['findings']}


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
