"""Immutable card versions and a separate log of author decisions."""
from dataclasses import asdict
import json
import sqlite3
from uuid import uuid4

from nw.sources import read_span
from nw.store import Store, now
from nw.story_models import CardLink, CardRef, DecisionRecord, DecisionRef, SourceRef
from nw.task_models import Ref, _ref, canonical, content_sha256


class CardConflict(ValueError):
    pass


_REQUIRED = {
    'brief': ('title', 'goal', 'constraints'),
    'world': ('title', 'rule', 'limits'),
    'character': ('name', 'role', 'want'),
    'style': ('title', 'guidance', 'check'),
    'taboo': ('title', 'constraint', 'check'),
    'plot': ('title', 'conflict', 'consequence'),
    'scene': ('title', 'goal', 'pov'),
    'promise': ('title', 'setup', 'payoff'),
    'rule': ('title', 'role', 'original_meaning', 'applies_when', 'excludes_when', 'operation',
             'counterexample', 'check', 'explanation'),
    'volume': ('title', 'goal', 'turn'),
    'chapter': ('title', 'goal', 'consequence'),
}
_OPTIONAL = {
    'brief': ('pov', 'reader_promise', 'author_words', 'interpretation', 'completion', 'acceptance'),
    'world': ('cost', 'history'),
    'character': ('need', 'wound', 'strength', 'flaw', 'voice', 'relationship', 'scene_function',
                  'background', 'core_conflict', 'behavior', 'boundaries', 'change_conditions',
                  'ability_cost', 'independent_goal'),
    'style': ('reference', 'pov', 'syntax', 'avoid'),
    'taboo': ('reason',),
    'plot': ('choice', 'resistance', 'ending_direction', 'central_question', 'payoff_window',
             'reader_promise', 'protagonist_want', 'cost'),
    'scene': ('function', 'location', 'story_time', 'entering_state', 'conflict', 'choice',
              'planned_result', 'allowed_disclosure', 'length_flexibility', 'narrative_person'),
    'promise': ('due', 'introduced_at', 'misdirection', 'partial_payoff', 'invalidation_reason'),
    'rule': ('number',),
    'volume': ('ending_direction',),
    'chapter': ('reader_promise',),
}
_LISTS = {'brief': ('dependencies',), 'plot': ('choice_chain', 'turning_points', 'flexible_parts'),
          'scene': ('characters',), 'rule': ('effect_notes',)}
_MAPS = {'scene': ('character_goals',)}
_DECISIONS = frozenset({'trial', 'approved', 'disabled'})
_RELATIONS = frozenset({'interprets', 'corrects', 'contradicts', 'depends_on', 'contains', 'supersedes'})


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_text(value: object) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value)


def _body(kind: str, value: object) -> dict:
    required = set(_REQUIRED[kind])
    optional = set(_OPTIONAL[kind]) | {'creation_reason'}
    lists = set(_LISTS.get(kind, ())) | {'holders', 'tags', 'unknowns'}
    maps = set(_MAPS.get(kind, ()))
    structured = {'plot': {'length_plan'}, 'chapter': {'word_budget'}, 'volume': {'word_budget'},
                  'scene': {'word_budget', 'chapter_word_budget', 'length_policy'}}.get(kind, set())
    extra = {'character': {'casting'}, 'plot': {'members'}}.get(kind, set())
    if (not isinstance(value, dict) or
            not required <= value.keys() or
            value.keys() - required - optional - lists - maps - structured - extra - {'visibility'} or
            any(not _text(value[key]) for key in required) or
            any(value[key] is not None and not _text(value[key]) for key in optional & value.keys()) or
            any(not _list_of_text(value[key]) for key in lists & value.keys()) or
            any(not isinstance(value[key], dict) or
                any(not _text(k) or not _text(v) for k, v in value[key].items()) for key in maps & value.keys())):
        raise ValueError(f'Invalid {kind} card body')
    if kind == 'character' and 'casting' in value:
        from nw.materials.cast_design import validate_card
        validate_card(value)
    if included := structured & value.keys():
        from nw.length_plan import check_book, check_budget
        for key in included:
            if key == 'length_policy':
                from nw.length_settings import parse_length_changes
                policy = value[key]
                if (not isinstance(policy, dict) or parse_length_changes(policy) != policy
                        or any(type(v) is not int for k, v in policy.items() if k != 'length_mode')):
                    raise ValueError('场景引用的项目篇幅必须是冻结的篇幅配置')
            elif key == 'length_plan':
                check_book(value[key])
            else:
                check_budget(value[key])
    if kind == 'scene' and 'narrative_person' in value:
        from nw.materials.narration import PERSONS
        if value['narrative_person'] not in PERSONS:
            raise ValueError('场景叙述人称不在可用形式中')
    if 'members' in value and (not isinstance(value['members'], list) or
            any(not _ref(ref) or set(ref) != {'kind', 'id', 'version', 'sha256'} or ref['kind'] != 'card'
                for ref in value['members'])):
        raise ValueError('Plan members require pinned card references')
    result = {'visibility': 'author_only', **value}
    if (result['visibility'] not in ('author_only', 'public', 'holders') or
            bool(result.get('holders')) != (result['visibility'] == 'holders')):
        raise ValueError('Invalid card body visibility or lists')
    if kind == 'rule' and result['role'] not in ('method', 'source_definition', 'rejected_instruction'):
        raise ValueError('Invalid rule body role')
    return result


def _card_values(store: Store, card: dict) -> tuple[str, str, str, str, str]:
    if (not isinstance(card, dict) or
            card.keys() - {'card_id', 'kind', 'origin', 'body', 'source_refs', 'status', 'version'}):
        raise ValueError('Invalid card envelope')
    if card.get('status', 'proposal') != 'proposal':
        raise ValueError('New card versions must be proposal')
    card_id, kind, origin = card.get('card_id'), card.get('kind'), card.get('origin')
    if not _text(card_id) or not _text(kind) or kind not in _REQUIRED or origin not in ('repository', 'author', 'model'):
        raise ValueError('Card requires an ID, known kind and explicit origin')
    refs = card.get('source_refs', [])
    if not isinstance(refs, list) or (origin == 'repository' and not refs):
        raise ValueError('Repository cards require a verified source')
    seen: set[SourceRef] = set()
    for item in refs:
        try:
            ref = SourceRef(**item)
        except TypeError:
            raise ValueError('Invalid card source reference') from None
        read_span(store, ref)
        if ref in seen:
            raise ValueError('Duplicate card source reference')
        seen.add(ref)
    return card_id, kind, origin, canonical(_body(kind, card.get('body'))), canonical(refs)


def _row(store: Store, ref: CardRef) -> sqlite3.Row:
    if not _text(ref.card_id) or type(ref.version) is not int or ref.version < 1:
        raise ValueError('Invalid card reference')
    row = store.connection.execute('SELECT * FROM cards WHERE card_id=? AND version=?',
                                   (ref.card_id, ref.version)).fetchone()
    if row is None:
        raise ValueError('Card version not found')
    return row


def _append(store: Store, card: dict, expected_version: int | None) -> CardRef:
    card_id, kind, origin, body, refs = _card_values(store, card)
    row = store.connection.execute('SELECT version,kind FROM cards WHERE card_id=? ORDER BY version DESC LIMIT 1',
                                   (card_id,)).fetchone()
    actual = row['version'] if row else None
    if (expected_version is not None and (type(expected_version) is not int or expected_version < 1) or
            expected_version != actual or card.get('version', expected_version) != expected_version):
        raise CardConflict(f'Card {card_id} expected version {expected_version}, found {actual}')
    if row and row['kind'] != kind:
        raise CardConflict(f'Card {card_id} cannot change kind')
    version = (actual or 0) + 1
    store.connection.execute('INSERT INTO cards VALUES (?,?,?,?,?,?,?)',
                             (card_id, version, kind, origin, body, refs, now()))
    return CardRef(card_id, version)


def save_card(store: Store, card: dict, expected_version: int | None) -> CardRef:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        return _append(store, card, expected_version)


def decision_history(store: Store, ref: CardRef) -> list[DecisionRef]:
    _row(store, ref)
    rows = store.connection.execute(
        'SELECT id,decision FROM card_decisions WHERE card_id=? AND version=? ORDER BY rowid',
        (ref.card_id, ref.version))
    return [DecisionRef(row['id'], ref, row['decision']) for row in rows]


def read_decision(store: Store, decision_id: str) -> DecisionRecord:
    row = store.connection.execute(
        'SELECT * FROM card_decisions WHERE id=?', (decision_id,)).fetchone()
    if row is None:
        raise ValueError('Card decision not found')
    ref = DecisionRef(row['id'], CardRef(row['card_id'], row['version']), row['decision'])
    return DecisionRecord(ref, row['reason'], row['created_at'])


def read_card(store: Store, ref: CardRef) -> dict:
    row = _row(store, ref)
    decision = store.connection.execute(
        'SELECT decision FROM card_decisions WHERE card_id=? AND version=? ORDER BY rowid DESC LIMIT 1',
        (ref.card_id, ref.version)).fetchone()
    return {**asdict(ref), 'kind': row['kind'], 'origin': row['origin'], 'body': json.loads(row['body_json']),
            'source_refs': json.loads(row['source_refs_json']), 'status': decision['decision'] if decision else 'proposal'}


def card_input_ref(card: dict) -> Ref:
    payload = {key: value for key, value in card.items() if key != 'status'}
    return Ref('card', card['card_id'], card['version'], content_sha256(payload))


def decide_card(store: Store, ref: CardRef, decision: str, reason: str, *,
                decision_id: str | None = None) -> DecisionRef:
    if not _text(decision) or decision not in _DECISIONS or not _text(reason):
        raise ValueError('A card decision requires trial, approved or disabled and a reason')
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        row = _row(store, ref)
        if row['kind'] == 'rule' and decision != 'disabled':
            if json.loads(row['body_json'])['role'] != 'method':
                raise ValueError('A source-only rule cannot be made usable')
            if row['origin'] == 'model' and not json.loads(row['source_refs_json']):
                raise ValueError('A model rule needs a verified source or an explicit author version')
        ident = decision_id or uuid4().hex
        if decision_id and store.connection.execute('SELECT 1 FROM card_decisions WHERE id=?', (ident,)).fetchone():
            saved = read_decision(store, ident)
            if saved.ref != DecisionRef(ident, ref, decision) or saved.reason != reason:
                raise ValueError('Card decision ID already binds a different decision')
            return saved.ref
        store.connection.execute('INSERT INTO card_decisions VALUES (?,?,?,?,?,?)',
                                 (ident, ref.card_id, ref.version, decision, reason, now()))
    return DecisionRef(ident, ref, decision)


def eligible_rule_refs(store: Store) -> list[CardRef]:
    """Use the newest decided version; pending proposals do not remove earlier guidance."""
    return [CardRef(*row) for row in store.connection.execute("""
        SELECT c.card_id,c.version FROM cards c
        WHERE c.kind='rule' AND json_extract(c.body_json,'$.role')='method'
          AND c.version=(SELECT MAX(v.version) FROM card_decisions v WHERE v.card_id=c.card_id)
          AND (SELECT decision FROM card_decisions d WHERE d.card_id=c.card_id AND d.version=c.version
               ORDER BY d.rowid DESC LIMIT 1) IN ('trial','approved')
        ORDER BY c.card_id
    """)]


def _link(store: Store, source: CardRef, target: CardRef, relation: str) -> CardLink:
    if not _text(relation) or relation not in _RELATIONS or source == target:
        raise ValueError('Invalid card relation')
    _row(store, source)
    _row(store, target)
    store.connection.execute(
        'INSERT INTO card_links VALUES (?,?,?,?,?,?) '
        'ON CONFLICT(from_card_id,from_version,to_card_id,to_version,relation) DO NOTHING',
        (uuid4().hex, source.card_id, source.version, target.card_id, target.version, relation))
    return CardLink(source, target, relation)


def link_cards(store: Store, source: CardRef, target: CardRef, relation: str) -> CardLink:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        return _link(store, source, target, relation)


def read_links(store: Store, ref: CardRef) -> list[CardLink]:
    _row(store, ref)
    rows = store.connection.execute(
        'SELECT to_card_id,to_version,relation FROM card_links WHERE from_card_id=? AND from_version=? ORDER BY rowid',
        (ref.card_id, ref.version))
    return [CardLink(ref, CardRef(r[0], r[1]), r[2]) for r in rows]
