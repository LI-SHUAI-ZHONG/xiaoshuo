"""Independent receipt cases for a single frozen change of historical period."""
import pytest

from nw.materials.world_history import POLICY, check_history_receipt
from test_material_world_history_periods import CASES, RELATIVE_LIMITS, card


KEY = 'C00704'
SOURCE = 'original:founding-to-expansion'
CITED = '/directions/0/choice'
GOOD = '巡吏取出《分仓令》，将港议会开通东栈航路的记录与船工呈上的港契互相核对。'
TURN = '雾港由创始期转入扩张期'
WRONG = '港历十五年，' + TURN
FROZEN = card(*CASES[KEY])


def check(choice: str = GOOD, *, detail: str = '', other_row: str = '', approved: dict | None = None,
          frozen: dict = FROZEN, legacy: bool = False, refs: list[str] | None = None) -> None:
    rule = '/members/0/body/rule'
    limits = '/members/0/body/limits'
    handoff = {
        'source_id': SOURCE, 'origin': {'stage': 'world_design'},
        'requirement': {'input_refs': ['approved:harbor-history:/body/rule', 'approved:harbor-history:/body/limits']},
        'actual_inputs': [{'path': rule, 'value': frozen['body']['rule']},
                          {'path': limits, 'value': frozen['body']['limits']}],
    }
    products = {'world_design': {'products': {'members': [{'kind': 'world', 'body': frozen['body']}]}}}
    context = {'approved_cards': [approved if approved is not None else frozen], 'world_network_bases': {SOURCE: {}}}
    if not legacy:
        context['world_history_policy'] = POLICY
    output = {'directions': [{'choice': choice, 'observable': detail, 'tags': ['分仓令']}, {'choice': other_row}]}
    check_history_receipt(handoff, refs or [CITED], output, products, context, KEY)


def test_reading_a_calendar_in_town_cannot_substitute_for_using_its_approved_history():
    with pytest.raises(ValueError, match=KEY):
        check('众人在雾港买了本港历，然后去酒楼找丢失的鱼篮。')


@pytest.mark.parametrize('claim', [
    '档案证实雾港由创始期转入扩张期是在港历十五年。',
    '雾港由创始期转入扩张期的时间为港历十五年。',
    '港历十一年，雾港已处于裂变期。',
    '账册记载，港历十二年，雾港由动荡期转入扩张期。',
    '港历十一年，雾港由动荡期转入固化期。',
    '港历十二年，雾港由扩张期转入创始期。',
    '船工说尚未找到账册，但原始档案证实：“港历十五年，雾港由创始期转入扩张期”。',
    '据传旧录改过，然而原始卷宗载明，港历十五年，雾港由创始期转入扩张期。',
], ids=['postposed-year', 'postposed-time', 'later-period-too-early', 'wrong-starting-period',
        'later-turn-too-early', 'reversed-period', 'verified-direct-quotation', 'confirmation-after-rumor'])
def test_false_assertion_in_the_same_plot_direction_is_rejected(claim: str):
    with pytest.raises(ValueError, match=KEY):
        check(detail=claim)


@pytest.mark.parametrize('detail', [
    '档案证实雾港由创始期转入扩张期是在港历十二年。',
    '港历十五年，雾港由创始期转入扩张期的说法未经证实。',
    '港历十五年，雾港由创始期转入扩张期，只是未经证实的传闻。',
    '船工私下说：“港历十五年，雾港由创始期转入扩张期”。',
    '办案人询问，雾港由创始期转入扩张期是在港历十五年吗？',
    '港历十五年，船工重绘航线。雾港由创始期转入扩张期是在港历十二年。',
    '港历十五年，船工重绘航线，另附的旧录记载雾港由创始期转入扩张期是在港历十二年。',
    '雾港由创始期转入扩张期之后，直到港历十五年，船工才补绘航线。',
    '档案证实云港由创始期转入扩张期是在港历十五年。',
    '档案证实雾港由创始期转入扩张期是在潮历十五年。',
    '港历十五年，云港已处于裂变期。',
    '港历十二年，雾港从扩张期转入动荡期。',
    '旧巷里传闻胜露年号有误，但原始档案证实：“港历十二年，雾港由创始期转入扩张期”。',
], ids=['correct-postposed-year', 'unverified-assertion', 'subsequent-retraction', 'quoted-rumor',
        'question', 'other-event-in-separate-sentence', 'other-event-in-same-sentence', 'later-distinct-action',
        'other-city', 'other-calendar', 'other-city-period', 'possible-same-year-turn', 'verified-true-quote'])
def test_distinct_date_scope_or_unconfirmed_account_can_coexist_with_the_real_handoff(detail: str):
    check(detail=detail)


def test_other_plot_direction_does_not_supply_the_evidence_or_date_of_this_one():
    check(other_row=WRONG)
    with pytest.raises(ValueError, match=KEY):
        check(choice='巡吏决定改查另一案，备好进山物资。', other_row=GOOD)


def test_all_directions_claimed_by_one_receipt_must_use_the_history():
    with pytest.raises(ValueError, match=KEY):
        check(other_row='船工决定回家取回蓑衣。', refs=[CITED, '/directions/1/choice'])
    check(other_row='船工沿东栈航路去找港契的见证人。', refs=[CITED, '/directions/1/choice'])


def test_a_nested_tag_cannot_be_the_factual_output_of_a_receipt():
    with pytest.raises(ValueError, match=KEY):
        check(choice='船工决定回家取蓑衣。', refs=['/directions/0/tags/0'])


def test_incompatible_new_world_card_cannot_replace_the_frozen_approved_source():
    latest = card(CASES[KEY][0].replace('港历12年', '港历15年'), CASES[KEY][1], version=3)
    with pytest.raises(ValueError, match=KEY):
        check(approved=latest)


def test_replaying_a_plan_before_history_policy_preserves_its_validation_contract():
    check(detail=WRONG, legacy=True)


@pytest.mark.parametrize('approved_time,claimed_time,compatible', [
    ('之后', '之前', False), ('之前', '之后', False), ('次年', '之前', False),
    ('三年前', '之后', False), ('之后', '次年', False),
    ('之后', '之后', True), ('次年', '之后', True), ('三年前', '之前', True),
])
def test_relative_time_must_preserve_order_even_without_a_known_year(
    approved_time: str, claimed_time: str, compatible: bool,
):
    rule = CASES[KEY][0].replace('港历12年', '《合浦令》施行' + approved_time) + '雾港已施行《合浦令》。'
    frozen = card(rule, RELATIVE_LIMITS.replace('分仓令', '合浦令'))
    statement = '《合浦令》施行' + claimed_time + '，' + TURN + '。'
    if compatible:
        check(detail=statement, frozen=frozen)
    else:
        with pytest.raises(ValueError, match=KEY):
            check(detail=statement, frozen=frozen)
