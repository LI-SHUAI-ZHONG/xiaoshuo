
from dataclasses import replace

import pytest

from nw.cards import decide_card, save_card
from nw.selection import select_rules, validate_selected_ids
from nw.store import Store
from nw.story_models import StateView


def add_card(store, ident, kind, body):
    return save_card(store, {'card_id': ident, 'kind': kind, 'origin': 'author', 'body': body}, None)


def method(store, ident, tag='调查'):
    ref = add_card(store, ident, 'rule', {
        'title': '证物', 'role': 'method', 'original_meaning': '以行动验证线索',
        'applies_when': '证物调查', 'excludes_when': '无证物', 'operation': '查封条',
        'counterexample': '直接交代', 'check': '线索能回看', 'explanation': '让证物参与冲突',
        'tags': [tag],
    })
    decide_card(store, ref, 'trial', '隔离测试')
    return ref


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('选择')
        scene = add_card(store, 'scene', 'scene', {'title': '暗井', 'goal': '调查证物', 'pov': 'yan'})
        yield store, scene, StateView('main', 0, 0, 'yan', [], [], {}, [], [])


def test_zero_rule_selection_is_valid(case):
    assert select_rules(*case).selected_refs == []


def test_candidate_limit_and_stable_order(case):
    store, _, _ = case
    for i in reversed(range(25)):
        method(store, f'rule-{i:02d}')
    result = select_rules(*case)
    assert [ref.card_id for ref in result.selected_refs] == [f'rule-{i:02d}' for i in range(5)]
    assert len(result.candidates) == 20
    assert len(result.excluded_reasons) == 20
    assert result.mappings[0]['action'] == '查封条'


def test_model_cannot_invent_selected_id(case):
    method(case[0], 'rule-1')
    selection = select_rules(*case)
    with pytest.raises(ValueError, match='candidate'):
        validate_selected_ids(selection, ['invented'])
    assert validate_selected_ids(selection, []) == []


def test_disabled_rule_not_recalled(case):
    store, _, _ = case
    ref = method(store, 'off')
    decide_card(store, ref, 'disabled', '停用')
    assert select_rules(*case).candidates == []
