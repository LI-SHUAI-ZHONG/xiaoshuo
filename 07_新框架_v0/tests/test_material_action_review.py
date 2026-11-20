from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from nw.materials import action_review
from nw.models import Draft, Run
from nw.story_delta import draft_ref


FIRST = 'work:selected:action:scene:first'
SECOND = 'work:selected:action:scene:second'


@pytest.fixture
def draft() -> Draft:
    return Draft('draft', 'scene', 1, '沈砚把两张封存单平铺并核对编号。陆昭照着编号找出缺失的那页登记。', 'complete', 'write', '')


def contract(draft: Draft, ordered: bool = True) -> dict:
    checks = [{'id': ident, 'profile': 'method_work'} for ident in (FIRST, SECOND)]
    if ordered:
        for index, check in enumerate(checks, 1):
            check['action_order'] = index
    return {'draft': asdict(draft_ref(draft)), 'checks': checks}


def span(draft: Draft, start: int, end: int) -> dict:
    return {**asdict(draft_ref(draft)), 'start': start, 'end': end, 'quote': draft.text[start:end]}


def review_rows(first: list[dict], second: list[dict]) -> list[dict]:
    return [{'id': ident, 'status': 'pass', 'reason': '正文写出了实际动作和结果', 'evidence': quotes}
            for ident, quotes in ((SECOND, second), (FIRST, first))]


def review_run(draft: Draft, rows: list[dict]) -> Run:
    output = json.dumps({'recommendation': 'pass', 'notes': '', 'core_changes': [], 'material_checks': rows})
    return Run('review', draft.scene_id, 'review', 'test', 'test', '{}', '{}', '{}', output,
               'complete', '{}', '', '')


def test_ordered_action_review_uses_available_distinct_spans_instead_of_return_order(draft: Draft) -> None:
    split = draft.text.index('。') + 1
    first = span(draft, 0, split)
    second = span(draft, split, len(draft.text))
    rows = review_rows([second, first], [second])

    reviewed = action_review.review_result(review_run(draft, rows), contract(draft), draft, None)

    assert reviewed['recommendation'] == 'pass'
    assert reviewed['material_checks'] == rows


@pytest.mark.parametrize('bad_evidence', ['shared', 'overlap', 'reversed'])
def test_ordered_action_review_returns_for_revision_on_contradictory_passes(draft: Draft, bad_evidence: str) -> None:
    split = draft.text.index('。') + 1
    first = span(draft, 0, split)
    second = span(draft, split, len(draft.text))
    spans = {'shared': (first, first), 'overlap': (first, span(draft, split - 3, len(draft.text))),
             'reversed': (second, first)}
    a, b = spans[bad_evidence]
    rows = review_rows([a], [b])

    reviewed = action_review.review_result(review_run(draft, rows), contract(draft), draft, None)

    assert reviewed['recommendation'] == 'revise'
    assert reviewed['material_checks'][0] == {**rows[0], 'status': 'failed', 'reason': action_review.ACTION_ORDER_REASON}
    assert reviewed['material_checks'][1] == rows[1]
    assert action_review.review_result(review_run(draft, rows), contract(draft, False), draft, None)['recommendation'] == 'pass'


def test_acceptance_rechecks_order_after_the_base_verification(draft: Draft, monkeypatch: pytest.MonkeyPatch) -> None:
    first = span(draft, 0, draft.text.index('。') + 1)
    rows = review_rows([first], [first])
    monkeypatch.setattr(action_review.evidence, 'check_material_acceptance', lambda *_: rows)
    monkeypatch.setattr(action_review, 'read_input_manifest', lambda *_: ({}, {'material_review_run': 'review'}))
    reviewed_payload = json.dumps({'material_review': contract(draft)})
    snapshot = json.dumps({'messages': [{'content': reviewed_payload}]})
    store = SimpleNamespace(get=lambda *_: SimpleNamespace(input_snapshot_json=snapshot))
    delta = SimpleNamespace(manifest_id='delta')

    with pytest.raises(ValueError, match='MATERIAL_EVIDENCE'):
        action_review.check_material_acceptance(store, draft, delta)
