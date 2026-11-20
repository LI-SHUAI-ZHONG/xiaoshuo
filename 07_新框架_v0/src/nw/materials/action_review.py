"""Verify independent prose evidence for actions selected in scene order."""
import json

from nw.materials import evidence
from nw.models import Draft, Run
from nw.store import Store
from nw.story_models import StateDelta
from nw.tasks import read_input_manifest


_ACTION_CHECK_PREFIX = 'work:selected:action:'
ACTION_ORDER_REASON = '按写作包的顺序呈现每条行动，为每条行动留下可独立引用的正文。'
ACTION_REVIEW_PROMPT = (
    '对含 action_order 的选定行动按指定顺序逐项核对。每项通过时引用能独立支持该行动的当前正文。'
    '各项必须能取到一组按顺序排列、互不重叠的实质引文。'
)


def _actions(checks: list[dict]) -> list[dict]:
    return sorted((row for row in checks if row['id'].startswith(_ACTION_CHECK_PREFIX)
                   and type(row.get('action_order')) is int), key=lambda row: row['action_order'])


def _first_missing(actions: list[dict], rows: list[dict], draft_id: str) -> dict | None:
    bound = 0
    by_id = {row['id']: row for row in rows}
    for action in actions:
        row = by_id[action['id']]
        ends = [span['end'] for span in row['evidence'] if span['id'] == draft_id and span['start'] >= bound
                and len(''.join(span['quote'].split())) >= 8 and span['quote'] != row['id']]
        if not ends:
            return row
        # An earlier end leaves at least as much room for every following action.
        bound = min(ends)
    return None


def review_result(run: Run, contract: dict | None, draft: Draft, comparison: Draft | None) -> dict:
    result = evidence.review_result(run, contract, draft, comparison)
    actions = _actions(contract['checks']) if contract else []
    if len(actions) >= 2 and result['recommendation'] == 'pass':
        failed = _first_missing(actions, result['material_checks'], draft.id)
        if failed is not None:
            failed.update(status='failed', reason=ACTION_ORDER_REASON)
            result['recommendation'] = 'revise'
    return result


def check_material_acceptance(store: Store, draft: Draft, delta: StateDelta) -> list[dict]:
    rows = evidence.check_material_acceptance(store, draft, delta)
    if sum(row['id'].startswith(_ACTION_CHECK_PREFIX) for row in rows) >= 2:
        # The base check has matched this frozen review message to the current contract.
        _, package = read_input_manifest(store, delta.manifest_id)
        reviewed = store.get('run', package['material_review_run'])
        snapshot = json.loads(reviewed.input_snapshot_json)
        contract = json.loads(snapshot['messages'][-1]['content'])['material_review']
        actions = _actions(contract['checks'])
        if len(actions) >= 2 and _first_missing(actions, rows, draft.id) is not None:
            raise ValueError('MATERIAL_EVIDENCE: ' + ACTION_ORDER_REASON)
    return rows
