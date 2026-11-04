"""Story adoption, inspection, decisions and evidence-backed acceptance commands."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from nw.acceptance import accept_batch, promote_branch, promotion_impacts, record_story_decision
from nw.call_control import model_settings
from nw.context.story import StoryScope, build_story_context, scene_scope
from nw.novel_flow import JobRequest, cancel_job, resume_job, show_job, start_job
from nw.planning import SCOPES, apply_plan, plan_input, propose_plan, retry_plan, show_plan
from nw.cards import decide_card, decision_history, read_card, read_decision, read_links
from nw.sources import import_seed_cards
from nw.store import Store
from nw.story_extract import freeze_delta_input
from nw.story_delta import check_delta, prepare_delta, read_delta, save_delta
from nw.story_models import AcceptanceRequest, CardRef, StateHead
from nw.story_state import adopt_story, apply_settings, current_head, fork_story, position, revision_state, state_at
from nw.task_models import Budget, content_sha256
from nw.tasks import read_task


def _position(value: str) -> tuple[int, int, int]:
    try:
        return position([int(part) for part in value.split(',')])
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use CH,SCENE,SPAN disclosure coordinates') from exc


def register_commands(subparsers: Any) -> None:
    jobs = subparsers.add_parser('novel', help='coordinate persistent multi-scene creative work').add_subparsers(
        dest='action', required=True)
    jobs.add_parser('start').add_argument('--request', type=Path, required=True)
    for action in ('show', 'resume', 'cancel'):
        command = jobs.add_parser(action)
        command.add_argument('--job', required=True)
        if action == 'resume':
            command.add_argument('--retry-failed', action='store_true')
            command.add_argument('--decision', type=Path, help='UTF-8 JSON containing step, token, action and reason')
            command.add_argument('--max-calls', type=int, help='raise the total call ceiling for this job')
            command.add_argument('--max-cost', help='raise the existing cost ceiling for this job')
            command.add_argument('--provider', choices=['ollama', 'openai_compat'])
    stories = subparsers.add_parser('story', help='manage evidence-backed story state').add_subparsers(dest='action', required=True)
    context = stories.add_parser('context', help='inspect a POV work package without a model call')
    context.add_argument('--scene', required=True)
    context.add_argument('--branch', default='main')
    context.add_argument('--story-input', type=Path)
    context.add_argument('--context-char-limit', type=int, required=True)
    plans = subparsers.add_parser('plan', help='propose, inspect and apply story designs').add_subparsers(dest='action', required=True)
    propose = plans.add_parser('propose')
    propose.add_argument('--scope', choices=SCOPES, required=True)
    propose.add_argument('--brief-version', type=int, required=True)
    propose.add_argument('--parent', help='ID of an applied direction or design')
    propose.add_argument('--branch', default='main')
    propose.add_argument('--budget', type=Path, required=True)
    propose.add_argument('--provider', choices=['ollama', 'openai_compat'])
    retry = plans.add_parser('retry', help='explicitly retry a failed call with its original budget and inputs')
    retry.add_argument('--id', required=True)
    retry.add_argument('--provider', choices=['ollama', 'openai_compat'])
    plans.add_parser('show').add_argument('--id', required=True)
    apply = plans.add_parser('apply')
    apply.add_argument('--id', required=True)
    apply.add_argument('--decision', required=True)
    stories.add_parser('adopt').add_argument('--baseline', type=Path, required=True)
    show = stories.add_parser('show')
    fork = stories.add_parser('fork')
    for command in (show, fork):
        command.add_argument('--branch', required=True)
        command.add_argument('--revision', type=int, required=True)
    show.add_argument('--time', type=int, required=True)
    show.add_argument('--holder', required=True)
    show.add_argument('--disclosure', type=_position)
    fork.add_argument('--name', required=True)
    promote = stories.add_parser('promote')
    promote.add_argument('--branch', required=True)
    promote.add_argument('--expected-main', type=int, required=True)
    promote.add_argument('--decision', required=True)
    promote.add_argument('--commit-id')
    stories.add_parser('impacts').add_argument('--branch', required=True)
    stories.add_parser('decide').add_argument('--file', type=Path, required=True)
    stories.add_parser('settings').add_argument('--file', type=Path, required=True)
    stories.add_parser('delta').add_argument('--file', type=Path, required=True)
    stories.add_parser('check').add_argument('--delta', required=True)
    extract = stories.add_parser('extract')
    extract.add_argument('--draft', required=True)
    extract.add_argument('--manifest', type=Path, required=True, help='UTF-8 JSON scene scope and frozen dependencies')
    extract.add_argument('--budget', type=Path, required=True)
    extract.add_argument('--provider', choices=['ollama', 'openai_compat'])
    cards = subparsers.add_parser('cards', help='import and review candidate cards').add_subparsers(dest='action', required=True)
    importer = cards.add_parser('import')
    importer.add_argument('--file', type=Path, required=True)
    importer.add_argument('--root', type=Path)
    for name in ('show', 'decide'):
        card = cards.add_parser(name)
        card.add_argument('--id', required=True)
        card.add_argument('--version', type=int, required=True)
        if name == 'decide':
            card.add_argument('--decision', choices=['trial', 'approved', 'disabled'], required=True)
            card.add_argument('--reason', required=True)


def _load(path: Path, expected: type) -> Any:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, expected):
        raise ValueError(f'Expected {expected.__name__} in {path.name}')
    return value


def _shape(factory: Any, payload: dict) -> Any:
    try:
        return factory(**payload)
    except TypeError as exc:
        raise ValueError(f'Invalid {factory.__name__} fields: {exc}') from exc


def read_budget_file(path: Path | None) -> Budget | None:
    return _shape(Budget, _load(path, dict)) if path is not None else None


def read_scope_file(path: Path | None) -> StoryScope | None:
    return _shape(StoryScope, _load(path, dict)) if path is not None else None


def _plan(store: Store, args: argparse.Namespace) -> Any:
    if args.action == 'propose':
        return propose_plan(store, args.brief_version, args.scope, args.provider_instance, args.settings,
                            read_budget_file(args.budget), parent_id=args.parent, branch=args.branch)
    if args.action == 'retry':
        return retry_plan(store, args.id, args.provider_instance, args.settings)
    if args.action == 'apply':
        apply_plan(store, args.id, args.decision)
        return show_plan(store, args.id).application
    manifest, _ = plan_input(store, args.id)
    task = read_task(store, args.id)
    if task.validation != 'VALID':
        return {'task': asdict(task), 'manifest': manifest}
    proposal = show_plan(store, args.id)
    candidates = [
        {'root': read_card(store, CardRef(**candidate['root'])),
         'members': [read_card(store, CardRef(**ref)) for ref in candidate['members'].values()]}
        for candidate in proposal.materialization]
    return {'proposal': asdict(proposal), 'candidates': candidates, 'manifest': manifest}



def _novel(store: Store, args: argparse.Namespace) -> Any:
    if args.action == 'start':
        raw = _load(args.request, dict)
        if not isinstance(raw.get('budget'), dict):
            raise ValueError('Novel request requires a budget object')
        raw['budget'] = _shape(Budget, raw['budget'])
        return start_job(store, _shape(JobRequest, raw))
    if args.action == 'show':
        return show_job(store, args.job)
    if args.action == 'cancel':
        return cancel_job(store, args.job)
    choice = _load(args.decision, dict) if args.decision else None

    def decide(step: str, gate: dict) -> dict | None:
        if choice is None:
            return None
        if choice.get('step') != step or choice.get('token') != gate['token']:
            raise ValueError('Decision step and token must match the current author gate')
        return {key: value for key, value in choice.items() if key not in ('step', 'token')}

    return resume_job(store, args.job, args.provider_instance, args.settings, decide, args.retry_failed,
                      max_calls=args.max_calls, max_cost=args.max_cost)


def dispatch(store: Store, args: argparse.Namespace) -> Any:
    if args.command == 'novel':
        return _novel(store, args)
    if args.command == 'plan':
        return _plan(store, args)
    if args.command == 'accept':
        if args.expected_head is None or not args.commit_id:
            raise ValueError('Batch acceptance requires --expected-head and --commit-id')
        batch = [_shape(AcceptanceRequest, item) for item in _load(args.batch, list)]
        return accept_batch(store, batch, StateHead(args.branch, args.expected_head), args.commit_id)
    if args.command == 'cards':
        if args.action == 'import':
            return import_seed_cards(store, args.file, root=args.root)
        ref = CardRef(args.id, args.version)
        if args.action == 'decide':
            return decide_card(store, ref, args.decision, args.reason)
        card = read_card(store, ref)
        card['decisions'] = [asdict(read_decision(store, item.id)) for item in decision_history(store, ref)]
        card['links'] = [asdict(item) for item in read_links(store, ref)]
        return card
    return _story(store, args)


def _story(store: Store, args: argparse.Namespace) -> Any:
    if args.action == 'context':
        scope = read_scope_file(args.story_input) or scene_scope(store, args.scene, args.branch)
        return build_story_context(store, args.scene, scope, args.context_char_limit)
    if args.action == 'adopt':
        data = _load(args.baseline, dict)
        if (set(data) != {'baseline', 'baseline_sha256', 'expected_accepted'} or
                content_sha256(data['baseline']) != data['baseline_sha256']):
            raise ValueError('Adoption baseline hash or envelope mismatch')
        return adopt_story(store, data['baseline'], data['expected_accepted'])
    if args.action == 'show':
        return state_at(store, args.branch, args.revision, args.time, args.holder, args.disclosure)
    if args.action == 'fork':
        return fork_story(store, StateHead(args.branch, args.revision), args.name)
    if args.action == 'promote':
        return promote_branch(store, args.branch, StateHead('main', args.expected_main), args.decision,
                              args.commit_id or f'promote:{args.decision}')
    if args.action == 'impacts':
        main, candidate = current_head(store), current_head(store, args.branch)
        return {'stale_scenes': promotion_impacts(store, revision_state(store, main), revision_state(store, candidate))}
    if args.action == 'decide':
        data = _load(args.file, dict)
        if set(data) != {'action', 'targets', 'reason'}:
            raise ValueError('Story decision requires action, targets and reason')
        return {'decision_id': record_story_decision(store, **data)}
    if args.action == 'settings':
        data = _load(args.file, dict)
        if set(data) != {'head', 'approvals', 'commit_id'}:
            raise ValueError('Setting changes require head, approvals and commit_id')
        return apply_settings(store, _shape(StateHead, data['head']), data['approvals'], data['commit_id'])
    if args.action == 'check':
        delta = read_delta(store, args.delta)
        return {'delta': asdict(delta), 'findings': [asdict(f) for f in check_delta(store, delta)]}
    if args.action == 'delta':
        data = _load(args.file, dict)
        if set(data) != {'id', 'draft_id', 'scope', 'operations'}:
            raise ValueError('Manual delta requires id, draft_id, scope and operations')
        settings = {'provider': 'author', 'model': 'manual', 'params': {}, 'prompt_version': 'manual-state-v1',
                    'base_url': None, 'timeout': None, 'stream': False}
        ident = freeze_delta_input(store, data['draft_id'], data['scope'], settings)
        return save_delta(store, data['id'], data['draft_id'], ident, data['operations'])
    budget = _shape(Budget, _load(args.budget, dict))
    scope = _load(args.manifest, dict)
    params = dict(args.settings.params)
    limit_keys = {'max_tokens', 'max_completion_tokens', 'num_predict'} & params.keys()
    if len(limit_keys) > 1:
        raise ValueError('Conflicting provider output limits')
    key = next(iter(limit_keys), 'num_predict' if args.provider_instance.name == 'ollama' else 'max_tokens')
    if type(params.get(key, budget.output_limit)) is not int or type(budget.output_limit) is not int:
        raise ValueError('Budget output limit must be a positive integer')
    params[key] = min(params.get(key, budget.output_limit), budget.output_limit)
    settings = model_settings(args.provider_instance, args.settings.model, params, 'state-extract-v1')
    ident = freeze_delta_input(store, args.draft, scope, settings)
    return prepare_delta(store, args.draft, ident, args.provider_instance, args.settings, budget)
