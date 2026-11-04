"""Revisioned story projections, independent of the legacy prose pointers."""
from dataclasses import asdict, replace
import json
import sqlite3
from uuid import uuid4

from nw.cards import read_card, read_decision
from nw.store import Store, now
from nw.story_dependencies import find_impacts
from nw.story_models import CardRef, Fact, StateDelta, StateHead, StateView
from nw.task_models import canonical, content_sha256

CLAIMS = ('fact', 'belief', 'suspicion', 'utterance', 'plan')
ACTIONS = ('set', 'unset', 'add_relation', 'remove_relation', 'introduce_promise', 'advance_promise')


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def position(value: object) -> tuple[int, int, int]:
    if (not isinstance(value, (list, tuple)) or len(value) != 3 or
            any(type(part) is not int or part < 0 for part in value)):
        raise ValueError('Invalid disclosure position; expected chapter,scene,span')
    return tuple(value)


def fact_key(fact: Fact) -> tuple[str, str, str, str]:
    group = fact.claim if fact.claim in ('utterance', 'plan') else 'knowledge'
    return fact.holder, fact.entity_id, fact.predicate, group


def parse_fact(value: dict, evidence: tuple[dict, ...]) -> Fact:
    if (not isinstance(value, dict) or not {'entity_id', 'predicate', 'holder', 'claim',
                                            'story_order', 'disclosure_order', 'value'} <= value.keys() or
            not all(text(value[k]) for k in ('entity_id', 'predicate', 'holder')) or
            value['claim'] not in CLAIMS or type(value['story_order']) is not int or
            value['holder'] == 'AUTHOR' or value['value'] is None):
        raise ValueError('Invalid story fact')
    if value['holder'] == 'WORLD' and value['claim'] != 'fact':
        raise ValueError('WORLD accepts only facts')
    if value['predicate'] == 'owner' and value['holder'] == 'WORLD' and not text(value['value']):
        raise ValueError('WORLD owner must be one stable holder ID')
    canonical(value['value'])
    return Fact(value['entity_id'], value['predicate'], value['value'], value['holder'], value['claim'],
                value['story_order'], position(value['disclosure_order']), evidence)


def branch_row(store: Store, branch_id: str) -> sqlite3.Row:
    row = store.connection.execute('SELECT * FROM story_branches WHERE id=? AND enabled=1', (branch_id,)).fetchone()
    if row is None:
        raise ValueError('Story branch not found')
    return row


def current_head(store: Store, branch_id: str = 'main') -> StateHead:
    return StateHead(branch_id, branch_row(store, branch_id)['head_revision'])


def revision_state(store: Store, head: StateHead) -> dict:
    if type(head.revision) is not int or head.revision < 0:
        raise ValueError('Invalid story revision')
    row = store.connection.execute('SELECT state_json FROM story_commits WHERE branch_id=? AND revision=?',
                                   (head.branch_id, head.revision)).fetchone()
    if row is None:
        raise ValueError('Story revision not found')
    return json.loads(row['state_json'])


def write_revision(store: Store, head: StateHead, parent_revision: int, ident: str,
                   digest: str, snapshot: dict) -> None:
    store.connection.execute('INSERT INTO story_commits VALUES (?,?,?,?,?,?,?)',
                             (ident, head.branch_id, head.revision, parent_revision, digest, canonical(snapshot), now()))
    for scene_id, slot in snapshot['slots'].items():
        store.connection.execute(
            '''INSERT INTO story_slots(branch_id,scene_id,draft_id,commit_id,delta_id) VALUES (?,?,?,?,?)
               ON CONFLICT(branch_id,scene_id) DO UPDATE SET draft_id=excluded.draft_id,
               commit_id=excluded.commit_id,delta_id=excluded.delta_id
               WHERE story_slots.draft_id<>excluded.draft_id OR story_slots.delta_id IS NOT excluded.delta_id''',
            (head.branch_id, scene_id, slot['draft_id'], ident, slot['delta_id']))
    store.connection.execute('UPDATE story_branches SET head_revision=? WHERE id=?',
                             (head.revision, head.branch_id))


def _approved_cards(store: Store, entries: list[dict]) -> list[dict]:
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'card_id', 'version', 'decision_id'}:
            raise ValueError('Setting requires a CardRef and explicit approval decision')
        ref = CardRef(entry['card_id'], entry['version'])
        decision = read_decision(store, entry['decision_id']).ref
        card = read_card(store, ref)
        if decision.card_ref != ref or decision.decision != 'approved' or card['status'] != 'approved':
            raise ValueError('Setting approval must match the selected card version')
        if card['kind'] == 'rule' or ref.card_id in result:
            raise ValueError('Invalid or duplicate story setting')
        result[ref.card_id] = entry
    return list(result.values())


def _baseline(store: Store, baseline: dict, decision_id: str) -> dict:
    required = {'as_of_story_order', 'disclosure_order', 'coverage', 'facts', 'card_refs'}
    if (not isinstance(baseline, dict) or set(baseline) != required or
            type(baseline['as_of_story_order']) is not int or not isinstance(baseline['facts'], list)
            or not isinstance(baseline['card_refs'], list)):
        raise ValueError('Invalid story baseline')
    order = position(baseline['disclosure_order'])
    coverage = baseline['coverage']
    if (not isinstance(coverage, dict) or set(coverage) != {'entities', 'predicates'} or
            any(not isinstance(v, list) or not all(text(item) for item in v) for v in coverage.values())):
        raise ValueError('Baseline coverage requires entity and predicate ID lists')
    facts: dict[tuple[str, str, str, str], Fact] = {}
    for raw in baseline['facts']:
        if not isinstance(raw, dict) or 'evidence' in raw:
            raise ValueError('Baseline fact evidence is the adoption decision')
        fact = parse_fact(raw, ({'decision_id': decision_id},))
        if fact.story_order > baseline['as_of_story_order'] or fact.disclosure_order > order:
            raise ValueError('Baseline fact lies beyond its snapshot anchor')
        key = fact_key(fact)
        if key in facts:
            raise ValueError('Duplicate baseline fact')
        facts[key] = fact
    return {**baseline, 'disclosure_order': order, 'facts': [asdict(f) for f in facts.values()],
            'card_refs': _approved_cards(store, baseline['card_refs'])}


def adopt_story(store: Store, baseline: dict, expected_accepted: dict[str, str]) -> StateHead:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        if store.managed_story():
            raise ValueError('Story is already managed')
        actual = {row.scene_id: row.draft_id for row in store.list('accepted')}
        if actual != expected_accepted:
            raise ValueError('Current accepted drafts do not match the baseline')
        active = store.connection.execute("""
            SELECT scene_id FROM flow_nodes WHERE status<>'DONE' AND scene_id NOT IN (
                SELECT json_extract(targets_json,'$.scene_id') FROM story_decisions WHERE action='abandon'
                AND json_type(targets_json,'$.scene_id')='text')
            LIMIT 1
        """).fetchone()
        pending_run = store.connection.execute("SELECT id FROM runs WHERE ended_at='' LIMIT 1").fetchone()
        if active or (pending_run and not _abandoned_pending_runs(store)):
            raise ValueError('Complete or explicitly abandon the active legacy flow or run before adoption')
        decision_id = uuid4().hex
        frozen = _baseline(store, baseline, decision_id)
        digest = content_sha256({'baseline': baseline, 'expected_accepted': expected_accepted})
        store.connection.execute('INSERT INTO story_decisions VALUES (?,?,?,?,?)',
                                 (decision_id, 'adopt', canonical({'sha256': digest}), 'Explicit story adoption', now()))
        store.connection.execute('INSERT INTO story_branches VALUES (?,NULL,0,0,0,1,?)',
                                 ('main', canonical(frozen)))
        head = StateHead('main', 0)
        snapshot = {'settings': frozen['card_refs'], 'slots': {
            scene_id: {'draft_id': draft_id, 'delta_id': None} for scene_id, draft_id in actual.items()}}
        write_revision(store, head, 0, f'adopt:{decision_id}', digest, snapshot)
        return head


def _abandoned_pending_runs(store: Store) -> bool:
    # An unfinished Run can be either orphaned or still sending. Only explicit run-ID
    # abandonment under its existing process lock is recorded by record_story_decision.
    return not store.connection.execute("""
        SELECT 1 FROM runs WHERE ended_at='' AND id NOT IN (
            SELECT json_extract(targets_json,'$.run_id') FROM story_decisions
            WHERE action='abandon' AND json_type(targets_json,'$.run_id')='text') LIMIT 1
    """).fetchone()


def fork_story(store: Store, from_head: StateHead, new_id: str) -> StateHead:
    if not text(new_id) or new_id == 'main':
        raise ValueError('Invalid candidate branch ID')
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        parent = branch_row(store, from_head.branch_id)
        snapshot = revision_state(store, from_head)
        if store.connection.execute('SELECT 1 FROM story_branches WHERE id=?', (new_id,)).fetchone():
            raise ValueError('Story branch ID already exists')
        store.connection.execute('INSERT INTO story_branches VALUES (?,?,?,?,0,1,?)',
                                 (new_id, from_head.branch_id, from_head.revision,
                                  parent['head_revision'], parent['baseline_json']))
        head = StateHead(new_id, 0)
        write_revision(store, head, 0, f'fork:{uuid4().hex}', content_sha256(snapshot), snapshot)
        return head


def apply_settings(store: Store, head: StateHead, approvals: list[str], commit_id: str) -> StateHead:
    if not text(commit_id) or not approvals:
        raise ValueError('Setting commit requires an ID and approvals')
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        digest = content_sha256({'head': asdict(head), 'approvals': approvals, 'action': 'settings'})
        previous = existing_commit(store, commit_id, digest)
        if previous:
            return previous
        if current_head(store, head.branch_id) != head:
            raise ValueError('STALE_HEAD')
        snapshot = revision_state(store, head)
        if head.branch_id == 'main' and snapshot['slots']:
            raise ValueError('Apply settings in a candidate branch and revalidate selected prose before promotion')
        refs = [{**asdict(read_decision(store, ident).ref.card_ref), 'decision_id': ident} for ident in approvals]
        merged = {entry['card_id']: entry for entry in snapshot['settings']}
        merged.update((entry['card_id'], entry) for entry in _approved_cards(store, refs))
        snapshot['settings'] = list(merged.values())
        result = StateHead(head.branch_id, head.revision + 1)
        write_revision(store, result, head.revision, commit_id, digest, snapshot)
        return result


def existing_commit(store: Store, ident: str, digest: str) -> StateHead | None:
    row = store.connection.execute('SELECT * FROM story_commits WHERE id=?', (ident,)).fetchone()
    if row is None:
        return None
    if row['payload_hash'] != digest:
        raise ValueError('Same commit ID used with different inputs')
    return StateHead(row['branch_id'], row['revision'])


def baseline_for(store: Store, branch_id: str) -> dict:
    return json.loads(branch_row(store, branch_id)['baseline_json'])


def selected_operations(store: Store, snapshot: dict) -> list[dict]:
    result = []
    for slot in snapshot['slots'].values():
        if slot['delta_id'] is not None:
            row = store.connection.execute('SELECT operations_json FROM state_deltas WHERE id=?',
                                           (slot['delta_id'],)).fetchone()
            result.extend(json.loads(row[0]))
    return result


def _operation_key(op: dict) -> tuple:
    disclosure = position(op['disclosure_order'])
    return (op['holder'], disclosure if op['holder'] == 'READER' else (op['story_order'], *disclosure))


def apply_operation(facts: dict[tuple[str, str, str, str], Fact], op: dict) -> None:
    removes = op['op'] in ('unset', 'remove_relation')
    candidate = parse_fact({**op, 'value': op['expected_old'] if removes else op['new_value']}, tuple(op['evidence']))
    key = fact_key(candidate)
    previous = facts.get(key)
    if canonical(previous.value if previous else None) != canonical(op['expected_old']):
        raise ValueError(f"Story precondition mismatch for {op['entity_id']} / {op['predicate']}")
    if removes:
        del facts[key]
    else:
        facts[key] = candidate


def replay(baseline: dict, operations: list[dict], holder: str = 'AUTHOR',
           story_order: int | None = None, disclosure: tuple[int, int, int] | None = None) -> list[Fact]:
    values = {}
    for raw in baseline['facts']:
        if holder == 'AUTHOR' or raw['holder'] == holder:
            fact = parse_fact(raw, tuple(raw['evidence']))
            values[fact_key(fact)] = fact
    for op in sorted(operations, key=_operation_key):
        if holder != 'AUTHOR' and op['holder'] != holder:
            continue
        if disclosure is not None and op['holder'] == 'READER' and position(op['disclosure_order']) > disclosure:
            continue
        if story_order is not None and op['holder'] != 'READER' and op['story_order'] > story_order:
            continue
        apply_operation(values, op)
    return list(values.values())


def state_at(store: Store, branch_id: str, revision: int, story_order: int, holder: str,
             disclosure_order: tuple[int, int, int] | None = None) -> StateView:
    if type(story_order) is not int or not text(holder):
        raise ValueError('State query requires a story time and holder')
    if holder == 'READER' and disclosure_order is None:
        raise ValueError('READER requires a disclosure position')
    disclosure = position(disclosure_order) if disclosure_order is not None else None
    baseline = baseline_for(store, branch_id)
    if ((holder != 'READER' and story_order < baseline['as_of_story_order']) or
            (holder == 'READER' and disclosure < position(baseline['disclosure_order']))):
        raise ValueError('HISTORY_INCOMPLETE')
    snapshot = revision_state(store, StateHead(branch_id, revision))
    facts = replay(baseline, selected_operations(store, snapshot), holder, story_order, disclosure)
    settings, omissions = [], []
    for ref in snapshot['settings']:
        card = read_card(store, CardRef(ref['card_id'], ref['version']))
        body = card['body']
        if (holder == 'AUTHOR' or body['visibility'] == 'public' or
                body['visibility'] == 'holders' and holder in body.get('holders', [])):
            card['status'] = 'approved'
            settings.append(card)
        else:
            omissions.append({'reason': 'VISIBILITY_RESTRICTED'})
    legacy = ([{**asdict(note), 'status': 'legacy_unverified'} for note in store.list('note')]
              if holder == 'AUTHOR' else [])
    return StateView(branch_id, revision, story_order, holder, facts, settings, baseline['coverage'], omissions, legacy)


def project_candidate_state(base_view: StateView, deltas: list[StateDelta]) -> StateView:
    values = {fact_key(f): f for f in base_view.facts}
    seen: dict[str, str] = {}
    for delta in deltas:
        if ((delta.branch_id, delta.base_revision) != (base_view.branch_id, base_view.revision)
                or delta.id in seen):
            raise ValueError('Candidate delta has a different base or is repeated')
        if any(seen.get(ident) != digest for ident, digest in delta.candidate_delta_refs):
            raise ValueError('Candidate dependency is missing, out of order, or has a different hash')
        seen[delta.id] = delta.sha256
        for op in sorted(delta.operations, key=_operation_key):
            if base_view.holder == 'AUTHOR' or op['holder'] == base_view.holder:
                apply_operation(values, op)
    return replace(base_view, facts=list(values.values()))
