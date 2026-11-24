"""Resolve approved outline ancestry on the current story branch."""
from dataclasses import asdict
import json

from nw.cards import card_input_ref, read_card, read_decision
from nw.store import Store
from nw.story_models import CardRef
from nw.story_state import current_head, revision_state
from nw.tasks import read_input_manifest


PARENT_SCOPE = {'volume': 'book', 'chapter': 'volume', 'scene': 'chapter'}
SCOPE_LABELS = {'book': '全书', 'volume': '卷', 'chapter': '章', 'scene': '场景'}

_APPLICATIONS = """SELECT a.proposal_id,a.decision_id,a.mapping_json,t.manifest_id,
    json_extract(m.package_json,'$.scope') AS scope
    FROM plan_applications a JOIN task_calls t ON t.id=a.proposal_id
    JOIN input_manifests m ON m.id=t.manifest_id
    WHERE t.kind='plan' AND t.status='FINISHED' AND t.validation='VALID'"""


def _active_decisions(store: Store, branch: str) -> dict[CardRef, str]:
    snapshot = revision_state(store, current_head(store, branch))
    return {CardRef(row['card_id'], row['version']): row['decision_id'] for row in snapshot['settings']}


def _volume_artifact(store: Store, root: dict, app: dict, active: dict[CardRef, str]) -> dict:
    approvals = {CardRef(row['card_id'], row['version']): row['decision_id'] for row in app['approvals']}
    volumes = []
    for frozen in root['body']['members']:
        ref = CardRef(frozen['id'], frozen['version'])
        card = read_card(store, ref)
        if card['kind'] != 'volume':
            continue
        pin = card_input_ref(card)
        if (active.get(ref) is None or active[ref] != approvals.get(ref)
                or card['status'] != 'approved' or asdict(pin) != frozen):
            raise ValueError('STALE_PLAN_PARENT: 卷级产物的批准版本在当前分支不可用')
        decision = read_decision(store, approvals[ref]).ref
        if decision.card_ref != ref or decision.decision != 'approved':
            raise ValueError('STALE_PLAN_PARENT: 卷级产物缺少对应的批准记录')
        body = {key: card['body'][key] for key in ('title', 'goal', 'turn')}
        if ending := card['body'].get('ending_direction'):
            body['ending_direction'] = ending
        volumes.append({'kind': 'volume', 'ref': {'card_id': pin.id, 'version': pin.version, 'sha256': pin.sha256},
                        'body': body})
    if len(volumes) != 1:
        raise ValueError('PLAN_PARENT_REQUIRED: 卷方案须包含一份可核实的批准卷级产物')
    return volumes[0]


def _application(store: Store, proposal_id: str, scope: str, active: dict[CardRef, str]) -> tuple[dict, dict, dict | None]:
    row = store.connection.execute(_APPLICATIONS + ' AND a.proposal_id=?', (proposal_id,)).fetchone()
    if row is None or row['scope'] != scope:
        raise ValueError(f'PLAN_PARENT_REQUIRED: 必须引用已批准并应用的{SCOPE_LABELS[scope]}方案')
    try:
        app = json.loads(row['mapping_json'])
        _, frozen = read_input_manifest(store, row['manifest_id'])
        ref = CardRef(**app['root'])
        decision = read_decision(store, row['decision_id']).ref
        card = read_card(store, ref)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('STALE_PLAN_PARENT: 上级方案缺少可核实的审批产物') from exc
    if (frozen.get('scope') != scope or active.get(ref) != decision.id or decision.card_ref != ref
            or app.get('decision_id') != decision.id or decision.decision != 'approved'
            or card['kind'] != 'plot' or card['status'] != 'approved'):
        raise ValueError(f'STALE_PLAN_PARENT: {SCOPE_LABELS[scope]}方案的批准版本在当前分支不可用')
    artifact = None
    if scope == 'volume':
        try:
            artifact = _volume_artifact(store, card, app, active)
        except (KeyError, TypeError) as exc:
            raise ValueError('STALE_PLAN_PARENT: 卷级产物缺少可核实的审批记录') from exc
    return card, frozen, artifact


def _chain(store: Store, scope: str, proposal_id: str | None, active: dict[CardRef, str]) -> list[dict]:
    chain = []
    parent_card = None
    while scope in PARENT_SCOPE:
        scope = PARENT_SCOPE[scope]
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(f'PLAN_PARENT_REQUIRED: 先确认并应用{SCOPE_LABELS[scope]}方案')
        card, frozen, artifact = _application(store, proposal_id, scope, active)
        pin = card_input_ref(card)
        if parent_card is not None and card_input_ref(parent_card) != pin:
            raise ValueError(f'STALE_PLAN_PARENT: 已冻结的{SCOPE_LABELS[scope]}产物与应用版本不一致')
        proof = {'scope': scope, 'proposal_id': proposal_id,
                 'root': {'card_id': pin.id, 'version': pin.version, 'sha256': pin.sha256},
                 'decision_id': active[CardRef(pin.id, pin.version)], 'title': card['body']['title']}
        if artifact:
            proof['title'] = artifact['body']['title']
            proof['artifact'] = artifact
        chain.append(proof)
        proposal_id, parent_card = frozen.get('parent_id'), frozen.get('parent')
        if scope == 'book':
            if proposal_id is not None or parent_card is not None:
                raise ValueError('STALE_PLAN_PARENT: 全书方案存在无效的上级')
        elif not isinstance(proposal_id, str) or not isinstance(parent_card, dict) or not {
            'card_id', 'version',
        } <= parent_card.keys():
            missing = SCOPE_LABELS[PARENT_SCOPE[scope]]
            raise ValueError(f'PLAN_PARENT_REQUIRED: {SCOPE_LABELS[scope]}方案缺少冻结的{missing}级依据')
    return list(reversed(chain))


def parent_chain(store: Store, scope: str, proposal_id: str | None, *, branch: str = 'main') -> list[dict]:
    """Check exact parent decisions and card versions, from the book to the immediate parent."""
    if scope == 'book' and proposal_id is None:
        return []
    if scope not in PARENT_SCOPE:
        raise ValueError('PLAN_PARENT_REQUIRED: 当前规划层级不支持指定上级方案')
    return _chain(store, scope, proposal_id, _active_decisions(store, branch))


def _active_candidates(store: Store, scope: str, active: dict[CardRef, str]) -> list[str]:
    proposals = []
    rows = store.connection.execute(_APPLICATIONS + " AND json_extract(m.package_json,'$.scope')=?"
                                    ' ORDER BY a.rowid DESC', (scope,))
    for row in rows:
        try:
            root = CardRef(**json.loads(row['mapping_json'])['root'])
            active_decision = active.get(root)
        except (KeyError, TypeError):
            continue
        if active_decision == row['decision_id']:
            proposals.append(row['proposal_id'])
    return proposals


def approved_parent(store: Store, scope: str, branch: str = 'main', *, proposal_id: str | None = None) -> str | None:
    """Resolve the immediate approved parent, defaulting to the latest active book's lineage."""
    if proposal_id is not None:
        parent_chain(store, scope, proposal_id, branch=branch)
        return proposal_id
    if scope == 'book':
        return None
    if scope not in PARENT_SCOPE:
        raise ValueError('PLAN_PARENT_REQUIRED: 当前规划层级不支持自动选择上级方案')
    active = _active_decisions(store, branch)
    book = None
    for ident in _active_candidates(store, 'book', active):
        try:
            _chain(store, 'volume', ident, active)
        except ValueError:
            continue
        book = ident
        break
    if book is None or scope == 'volume':
        return book
    for ident in _active_candidates(store, PARENT_SCOPE[scope], active):
        try:
            chain = _chain(store, scope, ident, active)
        except ValueError:
            continue
        if chain[0]['proposal_id'] == book:
            return ident
    return None
