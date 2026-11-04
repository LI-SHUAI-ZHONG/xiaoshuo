"""Story adoption, inspection, decisions and evidence-backed acceptance commands."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from nw.acceptance import accept_batch, promote_branch, promotion_impacts, record_story_decision
from nw.call_control import model_settings
from nw.cards import decide_card, decision_history, read_card, read_decision, read_links
from nw.sources import import_seed_cards
from nw.store import Store
from nw.story_delta import (candidate_projection_digest, candidate_snapshot, check_delta, draft_digest, draft_ref, prepare_delta,
                            read_delta, save_delta)
from nw.story_models import AcceptanceRequest, CardRef, StateHead
from nw.story_state import (adopt_story, apply_settings, baseline_for, current_head, fork_story, position,
                            replay, revision_state, selected_operations, state_at)
from nw.task_models import Budget, InputManifest, content_sha256
from nw.tasks import freeze_manifest


def _position(value: str) -> tuple[int, int, int]:
    try:
        return position([int(part) for part in value.split(',')])
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use CH,SCENE,SPAN disclosure coordinates') from exc


def register_commands(subparsers: Any) -> None:
    stories = subparsers.add_parser('story', help='manage evidence-backed story state').add_subparsers(dest='action', required=True)
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


def _freeze(store: Store, draft_id: str, scope: dict, settings: dict) -> str:
    required = {'id', 'branch_id', 'base_revision', 'story_order'}
    if not isinstance(scope, dict) or not required <= scope.keys() or scope.keys() - required - {
            'candidate_delta_refs', 'predecessor_drafts', 'brief_ref', 'dependency_refs'}:
        raise ValueError('Invalid delta manifest fields')
    for field in ('candidate_delta_refs', 'predecessor_drafts', 'dependency_refs'):
        if not isinstance(scope.get(field, []), list):
            raise ValueError(f'{field} must be a list')
    if any(not isinstance(raw, dict) or not isinstance(raw.get('id'), str)
           for raw in scope.get('predecessor_drafts', [])):
        raise ValueError('Invalid predecessor draft reference')
    head = StateHead(scope['branch_id'], scope['base_revision'])
    draft = store.get('draft', draft_id)
    scene = store.get('scene', draft.scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    disclosure = (chapter.index, scene.index, 0)
    view = state_at(store, head.branch_id, head.revision, scope['story_order'], 'AUTHOR', disclosure)
    deps = scope.get('candidate_delta_refs', [])
    digest = candidate_projection_digest(store, head, deps, scene.id) if deps else None
    snapshot = candidate_snapshot(store, head, deps, scene.id)
    facts = replay(baseline_for(store, head.branch_id), selected_operations(store, snapshot),
                   story_order=scope['story_order'], disclosure=disclosure)
    changed_ids = {ident for ident, _ in deps}
    predecessors = {raw['id']: raw for raw in scope.get('predecessor_drafts', [])}
    for slot in snapshot['slots'].values():
        if slot['delta_id'] not in changed_ids:
            ref = draft_ref(store.get('draft', slot['draft_id']))
            predecessors.setdefault(ref.id, asdict(ref))
    package = {'draft_id': draft.id, 'draft_sha256': draft_digest(draft),
               'facts': [asdict(fact) for fact in facts], 'settings': view.settings}
    return freeze_manifest(store, InputManifest(
        scope['id'], 'state_extract', settings, content_sha256(package),
        brief_ref=scope.get('brief_ref'),
        card_refs=tuple({'card_id': card['card_id'], 'version': card['version']} for card in view.settings),
        branch_id=head.branch_id, state_revision=head.revision, story_order=scope['story_order'],
        disclosure_order=disclosure, predecessor_drafts=tuple(predecessors.values()),
        candidate_delta_refs=tuple(deps), candidate_projection_sha256=digest,
        dependency_refs=tuple(scope.get('dependency_refs', []))), package)


def dispatch(store: Store, args: argparse.Namespace) -> Any:
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
        ident = _freeze(store, data['draft_id'], data['scope'], settings)
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
    ident = _freeze(store, args.draft, scope, settings)
    return prepare_delta(store, args.draft, ident, args.provider_instance, args.settings, budget)
