"""Verify independent prose evidence for actions selected in scene order."""
import json

from nw.materials import evidence
from nw.materials import narration_review
from nw.materials import cast_fulfillment
from nw.materials.design_semantics import check_review_evidence
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


def _design_problems(checks: list[dict], rows: list[dict], draft: Draft):
    by_id = {c['id']: c for c in checks}
    for row in rows:
        if row['status'] == 'pass' and row['id'].startswith('work:design-network:'):
            try:
                check_review_evidence(by_id[row['id']], row['evidence'], draft)
            except ValueError as error:
                yield row, str(error)


def review_result(run: Run, contract: dict | None, draft: Draft, comparison: Draft | None,
                  *, ending: bool = False) -> dict:
    result = evidence.review_result(run, contract, draft, comparison)
    if ending:
        from nw.chapter_break import break_is_natural, chapter_break_from_notes
        result['chapter_break'] = chapter_break_from_notes(result['notes'])
        if not break_is_natural(result['chapter_break'], draft):
            result['recommendation'] = 'revise'
    if contract:
        rows = result['material_checks']
        narration_review.assess_beats(contract['checks'], rows, draft)
        cast_fulfillment.assess(contract['checks'], rows, draft)
        if any(row['status'] != 'pass' for row in rows):
            result['recommendation'] = 'revise'
        for row, reason in _design_problems(contract['checks'], result['material_checks'], draft):
            row.update(status='failed', reason=reason)
            result['recommendation'] = 'revise'
    actions = _actions(contract['checks']) if contract else []
    if len(actions) >= 2 and result['recommendation'] == 'pass':
        failed = _first_missing(actions, result['material_checks'], draft.id)
        if failed is not None:
            failed.update(status='failed', reason=ACTION_ORDER_REASON)
            result['recommendation'] = 'revise'
    return result


def check_material_acceptance(store: Store, draft: Draft, delta: StateDelta) -> list[dict]:
    rows = evidence.check_material_acceptance(store, draft, delta)
    if (any(row['id'].startswith('work:design-network:') for row in rows)
            or any(row['id'].startswith(cast_fulfillment.PREFIX) for row in rows)
            or any(row['id'].startswith(narration_review.PREFIX) for row in rows)
            or sum(row['id'].startswith(_ACTION_CHECK_PREFIX) for row in rows) >= 2):
        # The base check has matched this frozen review message to the current contract.
        _, package = read_input_manifest(store, delta.manifest_id)
        review_run_id = package.get('material_review_run')
        if not review_run_id:
            raise ValueError('MATERIAL_EVIDENCE: 已规划材料约束的场景必须先完成独立审稿并通过核验后再接受')
        reviewed = store.get('run', review_run_id)
        snapshot = json.loads(reviewed.input_snapshot_json)
        contract = json.loads(snapshot['messages'][-1]['content'])['material_review']
        narration_review.assess_beats(contract['checks'], rows, draft)
        cast_fulfillment.assess(contract['checks'], rows, draft)
        if any(row['status'] != 'pass' and row['id'].startswith(cast_fulfillment.PREFIX) for row in rows):
            raise ValueError('MATERIAL_EVIDENCE: 人物职责须有本稿所选行动与后果的独立审稿依据')
        if any(row['status'] != 'pass' for row in rows):
            raise ValueError('MATERIAL_EVIDENCE: the approved narration requires a passing review of the current draft')
        reader_only = narration_review.reader_spans(contract['checks'], rows, draft)
        if reader_only:
            narration_review.check_state_audience(delta.operations, reader_only)
        for _, reason in _design_problems(contract['checks'], rows, draft):
            raise ValueError(reason)
        actions = _actions(contract['checks'])
        if len(actions) >= 2 and _first_missing(actions, rows, draft.id) is not None:
            raise ValueError('MATERIAL_EVIDENCE: ' + ACTION_ORDER_REASON)
    return rows
