"""Apply author-reviewed prose and state in one SQLite transaction."""
from dataclasses import asdict
import json
from uuid import uuid4

from nw.call_control import execution_lock
from nw.store import Store, now
from nw.story_delta import check_delta, draft_ref, manifest_refs, prepare_delta, read_delta
from nw.story_dependencies import add_dependency
from nw.story_models import AcceptanceRequest, StateDelta, StateHead
from nw.story_state import (baseline_for, branch_row, current_head, existing_commit, replay,
                            revision_state, selected_operations, text, write_revision)
from nw.task_models import Ref, canonical, content_sha256
from nw.tasks import read_input_manifest

__all__ = ['accept_batch', 'check_delta', 'prepare_delta', 'promote_branch', 'record_story_decision']


def record_story_decision(store: Store, action: str, targets: dict, reason: str) -> str:
    if action not in ('accept', 'promote', 'abandon') or not isinstance(targets, dict) or not text(reason):
        raise ValueError('A story decision requires an action, exact target and reason')
    ident = uuid4().hex
    if action == 'abandon':
        if len(targets) != 1 or not (set(targets) <= {'scene_id', 'run_id'} and all(map(text, targets.values()))):
            raise ValueError('Abandonment requires one legacy scene or run ID')
        key, value = next(iter(targets.items()))
        store.get(key[:-3], value)
        lock = f'run:{value}' if key == 'run_id' else f'flow:{value}:N5'
        with execution_lock(store, lock) as acquired:
            if not acquired:
                raise ValueError('Legacy operation is still running')
            _write_decision(store, ident, action, targets, reason)
    else:
        _write_decision(store, ident, action, targets, reason)
    return ident


def _write_decision(store: Store, ident: str, action: str, targets: dict, reason: str) -> None:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        if action == 'abandon' and store.managed_story():
            raise ValueError('Abandon legacy work before adopting the story')
        store.connection.execute('INSERT INTO story_decisions VALUES (?,?,?,?,?)',
                                 (ident, action, canonical(targets), reason, now()))


def _require_decision(store: Store, ident: str, action: str, targets: dict) -> None:
    row = store.connection.execute('SELECT action,targets_json FROM story_decisions WHERE id=?', (ident,)).fetchone()
    if row is None or row['action'] != action or row['targets_json'] != canonical(targets):
        raise ValueError('Author decision does not match these exact versions')


def _checked_deltas(store: Store, requests: list[AcceptanceRequest], expected_head: StateHead) -> dict[str, StateDelta]:
    deltas = {}
    for request in requests:
        if request.scene_id in deltas or request.branch_id != expected_head.branch_id:
            raise ValueError('Batch must contain distinct scenes on the expected branch')
        draft = store._check_acceptable(request.draft_id)
        if draft.scene_id != request.scene_id:
            raise ValueError('Draft belongs to a different scene')
        delta = read_delta(store, request.delta_id)
        if ((delta.branch_id, delta.base_revision) != (expected_head.branch_id, expected_head.revision) or
                (delta.draft_id, delta.manifest_id) != (draft.id, request.manifest_id)):
            raise ValueError('Delta, manifest, draft and batch base must match')
        targets = {k: v for k, v in asdict(request).items() if k != 'decision_id'}
        _require_decision(store, request.decision_id, 'accept', targets)
        blockers = [item.explanation for item in check_delta(store, delta, project=False)
                    if item.severity == 'hard']
        if blockers:
            raise ValueError('Unresolved state review: ' + '; '.join(blockers))
        deltas[request.scene_id] = delta
    return deltas


def _snapshot_dependencies(store: Store, snapshot: dict) -> dict[str, set[str]]:
    slots = snapshot['slots']
    edges = {scene_id: set() for scene_id in slots}
    for scene_id, slot in slots.items():
        if slot['delta_id'] is None:
            continue
        delta = read_delta(store, slot['delta_id'])
        manifest, _ = read_input_manifest(store, delta.manifest_id)
        for ref in manifest_refs(store, manifest, scene_id, current=False):
            if ref.kind == 'draft':
                source = store.get('draft', ref.id)
                other = slots.get(source.scene_id)
                matches = other is not None and other['draft_id'] == source.id
            elif ref.kind == 'delta':
                source = store.get('draft', read_delta(store, ref.id).draft_id)
                other = slots.get(source.scene_id)
                matches = other is not None and other['delta_id'] == ref.id
            else:
                continue
            if not matches:
                raise ValueError(f'Stale or missing scene dependency for {scene_id}')
            edges[scene_id].add(source.scene_id)
    return edges


def _topological(edges: dict[str, set[str]]) -> list[str]:
    pending = {scene_id: parents.copy() for scene_id, parents in edges.items()}
    result = []
    while pending:
        ready = sorted(scene_id for scene_id, parents in pending.items() if not parents)
        if not ready:
            raise ValueError('Cyclic scene dependencies')
        result.extend(ready)
        for scene_id in ready:
            del pending[scene_id]
        for parents in pending.values():
            parents.difference_update(ready)
    return result


def _write_events(store: Store, commit_id: str, scene_id: str, delta: StateDelta) -> None:
    for index, operation in enumerate(delta.operations):
        store.connection.execute('INSERT INTO story_events VALUES (?,?,?,?,?)',
                                 (f'{commit_id}:{scene_id}:{index}', commit_id, scene_id, delta.draft_id,
                                  canonical({'delta_id': delta.id, 'operation': operation})))


def _check_settings_for_delta(store: Store, snapshot: dict, delta: StateDelta) -> None:
    draft = store.get('draft', delta.draft_id)
    if draft.scene_id in snapshot.get('stale_plan_scenes', []):
        raise ValueError('STALE_PLAN: retired design cannot be accepted on this branch')
    manifest, _ = read_input_manifest(store, delta.manifest_id)
    settings = {(card['card_id'], card['version']) for card in snapshot['settings']}
    baseline = revision_state(store, StateHead(delta.branch_id, delta.base_revision))
    if settings != {(card['card_id'], card['version']) for card in baseline['settings']}:
        raise ValueError('Scene must be revalidated against the changed branch settings')
    for ref in manifest['card_refs']:
        if not isinstance(ref, dict) or (ref.get('card_id'), ref.get('version')) not in settings:
            raise ValueError('Frozen setting card is not pinned on this branch')


def _accept_in_transaction(store: Store, requests: list[AcceptanceRequest], head: StateHead,
                           commit_id: str, digest: str) -> tuple[StateHead, list[str]]:
    deltas = _checked_deltas(store, requests, head)
    before = revision_state(store, head)
    snapshot = {**before, 'slots': before['slots'].copy()}
    for scene_id, delta in deltas.items():
        _check_settings_for_delta(store, snapshot, delta)
        snapshot['slots'][scene_id] = {'draft_id': delta.draft_id, 'delta_id': delta.id}
    order = _topological(_snapshot_dependencies(store, snapshot))
    if head.branch_id == 'main':
        affected = promotion_impacts(store, before, snapshot)
        if affected:
            raise ValueError(f"Earlier changes require downstream dependency revalidation: {', '.join(affected)}")
        for scene_id, delta in deltas.items():
            if scene_id not in before['slots']:
                continue
            manifest, _ = read_input_manifest(store, delta.manifest_id)
            checked = {ident for ident, _ in manifest['candidate_delta_refs']}
            for earlier_id, earlier in deltas.items():
                if (_scene_position(store, earlier_id) < _scene_position(store, scene_id) and
                        earlier.id not in checked):
                    raise ValueError('Downstream dependency review must freeze the replacement delta')
    replay(baseline_for(store, head.branch_id), selected_operations(store, snapshot))
    result = StateHead(head.branch_id, head.revision + 1)
    write_revision(store, result, head.revision, commit_id, digest, snapshot)
    updated = [scene_id for scene_id in order if scene_id in deltas]
    for scene_id in updated:
        delta = deltas[scene_id]
        _write_events(store, commit_id, scene_id, delta)
        consumer = Ref('story_commit', commit_id, result.revision, digest)
        add_dependency(store, consumer, Ref('delta', delta.id, 1, delta.sha256))
        if head.branch_id == 'main':
            store._accept_in_transaction(delta.draft_id)
    return result, updated if head.branch_id == 'main' else []


def accept_batch(store: Store, requests: list[AcceptanceRequest], expected_head: StateHead,
                 commit_id: str, checkpoint: tuple[str, str, int] | None = None) -> StateHead:
    if not requests or not text(commit_id):
        raise ValueError('A nonempty batch and commit ID are required')
    if checkpoint is not None:
        raise ValueError('Workflow checkpoints require the M9 scheduler')
    records = sorted((asdict(r) for r in requests), key=canonical)
    digest = content_sha256({'action': 'accept', 'head': asdict(expected_head), 'requests': records})
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        existing = existing_commit(store, commit_id, digest)
        if existing:
            return existing
        if current_head(store, expected_head.branch_id) != expected_head:
            raise ValueError('STALE_HEAD')
        result, export = _accept_in_transaction(store, requests, expected_head, commit_id, digest)
    store._export_accepted(export)
    return result


def _scene_position(store: Store, scene_id: str) -> tuple[int, int]:
    scene = store.get('scene', scene_id)
    return store.get('chapter', scene.chapter_id).index, scene.index


def promotion_impacts(store: Store, main: dict, candidate: dict) -> list[str]:
    earlier = main['slots']
    later = candidate['slots']
    changed = [key for key in set(earlier) | set(later) if earlier.get(key) != later.get(key)]
    settings_changed = main['settings'] != candidate['settings']
    first = min((_scene_position(store, key) for key in changed), default=None)
    stale_plan = set(candidate.get('stale_plan_scenes', []))
    return [key for key in earlier if key in stale_plan or key not in later or (
        earlier[key] == later[key] and (settings_changed or first is not None and _scene_position(store, key) > first))]


def _require_promotion_reviews(store: Store, branch_id: str, main: dict, candidate: dict,
                               updates: list[str]) -> None:
    revisions = dict(store.connection.execute("""
        SELECT s.scene_id,c.revision FROM story_slots s JOIN story_commits c ON c.id=s.commit_id
        WHERE s.branch_id=?
    """, (branch_id,)))
    changed = {}
    for scene_id in updates:
        slot = candidate['slots'][scene_id]
        delta = read_delta(store, slot['delta_id']) if slot['delta_id'] else None
        if delta is None or delta.branch_id != branch_id:
            raise ValueError(f'Promotion needs revalidated state on this branch for {scene_id}')
        _check_settings_for_delta(store, candidate, delta)
        changed[scene_id] = delta
    for scene_id, delta in changed.items():
        if scene_id not in main['slots']:
            continue
        manifest, _ = read_input_manifest(store, delta.manifest_id)
        frozen = {ident for ident, _ in manifest['candidate_delta_refs']}
        for prior_id, earlier in changed.items():
            if _scene_position(store, prior_id) >= _scene_position(store, scene_id):
                continue
            if (delta.base_revision < revisions[prior_id] and
                    (revisions[prior_id] != revisions[scene_id] or earlier.id not in frozen)):
                raise ValueError(f'Promotion needs revalidated downstream scene {scene_id}')


def promote_branch(store: Store, branch_id: str, expected_main: StateHead,
                   decision_id: str, commit_id: str) -> StateHead:
    if expected_main.branch_id != 'main' or not text(commit_id):
        raise ValueError('Promotion requires the main head and a commit ID')
    # Decision contents are immutable, so a retry can reproduce the original promotion hash.
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        record = store.connection.execute('SELECT targets_json FROM story_decisions WHERE id=?', (decision_id,)).fetchone()
        if record is None:
            raise ValueError('Missing promotion decision')
        targets = json.loads(record[0])
        digest = content_sha256({'action': 'promote', 'branch': branch_id, 'main': asdict(expected_main),
                                 'decision': decision_id, 'targets': targets})
        previous = existing_commit(store, commit_id, digest)
        if previous:
            return previous
        candidate = current_head(store, branch_id)
        _require_decision(store, decision_id, 'promote',
                          {'candidate': asdict(candidate), 'expected_main': asdict(expected_main)})
        branch = branch_row(store, branch_id)
        if (current_head(store) != expected_main or branch['parent_branch_id'] != 'main' or
                branch['parent_at_fork'] != expected_main.revision):
            raise ValueError('STALE_HEAD: branch promotion requires the unchanged main head at fork')
        old, new = revision_state(store, expected_main), revision_state(store, candidate)
        impacts = promotion_impacts(store, old, new)
        if impacts:
            raise ValueError(f"Promotion needs revalidated scenes: {', '.join(impacts)}")
        _topological(_snapshot_dependencies(store, new))
        replay(baseline_for(store, branch_id), selected_operations(store, new))
        updates = [key for key, slot in new['slots'].items() if old['slots'].get(key) != slot]
        _require_promotion_reviews(store, branch_id, old, new, updates)
        for key in updates:
            slot = new['slots'][key]
            store._check_acceptable(slot['draft_id'])
        result = StateHead('main', expected_main.revision + 1)
        write_revision(store, result, expected_main.revision, commit_id, digest, new)
        for key in updates:
            slot = new['slots'][key]
            _write_events(store, commit_id, key, read_delta(store, slot['delta_id']))
            store._accept_in_transaction(slot['draft_id'])
    store._export_accepted(updates)
    return result
