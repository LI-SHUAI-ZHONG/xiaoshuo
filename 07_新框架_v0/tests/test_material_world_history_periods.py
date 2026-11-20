"""Approved, locally dated history controls each of the five changes of period."""
import pytest

from nw.materials.world_history_periods import approved_period, relative_offset, year_value


LIMITS = '该分期仅适用于雾港的港历纪年。'
CASES = {
    'C00704': ('雾港在创始期由港议会颁行《分仓令》。港历12年，港议会开通东栈航路，促使雾港由创始期转入扩张期。', LIMITS),
    'C00707': ('雾港在扩张期开通东栈航路。港历19年，东栈粮仓断供，促使雾港由扩张期转入动荡期。', LIMITS),
    'C00710': ('雾港在动荡期因三埠罢运而封仓。港历24年，港议会颁行《复仓章程》，促使雾港由动荡期转入固化期。', LIMITS),
    'C00712': ('雾港在固化期施行《复仓章程》。港历30年，盐盟因两埠税争未解而秘密串联仓户，促使雾港由固化期转入暗流期。', LIMITS),
    'C00716': ('雾港在暗流期因两埠争夺仓权而屡次封仓。港历37年，三埠公会废除世袭仓权，促使雾港由暗流期转入裂变期。', LIMITS),
}


def card(rule: str, limits: str = LIMITS, **updates) -> dict:
    return {'card_id': 'harbor-history', 'version': 2, 'status': 'approved', 'kind': 'world',
            'body': {'rule': rule, 'limits': limits}, **updates}


@pytest.mark.parametrize('key', CASES)
def test_every_transition_needs_its_own_prior_and_event(key):
    rule, limits = CASES[key]
    result = approved_period(card(rule, limits), key)
    assert result['rule'] == rule and result['limits'] == limits
    assert (result['version'], result['rule_ref'], result['limits_ref']) == (
        2, 'approved:harbor-history:/body/rule', 'approved:harbor-history:/body/limits')
    e = result['evidence']
    assert e['world'] == '雾港' and e['calendar'] == '港历' and type(e['year']) is int
    assert e['event'] in e['anchors'] and e['event'] in rule
    assert e['transition'] in rule and e['prior_fact'] in rule and e['boundary'] in limits
    assert all(anchor in rule for anchor in e['anchors'])
    assert all(approved_period(card(rule, limits), other) is None for other in CASES if other != key)
    for change in (rule.split('。', 1)[1], rule.replace('促使', '后来听说'),
                   rule.replace('促使雾港', '促使西岸'), rule.replace('港历', '星历')):
        assert approved_period(card(change, limits), key) is None


@pytest.mark.parametrize('key', CASES)
def test_one_history_can_warrant_multiple_stages_on_the_same_world_card(key):
    combined = ''.join(rule for rule, _ in CASES.values())
    value = approved_period(card(combined), key)
    assert value['rule'] == combined and value['evidence']['year'] == approved_period(card(CASES[key][0]), key)['evidence']['year']


@pytest.mark.parametrize(('year', 'expected'), [('港历十二年', None), ('12', 12), ('十二', 12), ('二十', 20),
                          ('二百零三年', 203), ('二〇一年', 201), ('元年', 1), ('前五年', -5),
                          ('２４', 24), ('两百一', None), ('２０点五', None), ('十二余', None),
                          ('假设', None), ('世纪', None), ('二三十', None)])
def test_numerals_have_one_unambiguous_year(year, expected):
    assert year_value(year) == expected


@pytest.mark.parametrize('key,original,replacement', [
    ('C00704', '颁行《分仓令》', '准备颁行《分仓令》'), ('C00704', '开通东栈航路', '向东栈航路送货'),
    ('C00704', '开通东栈航路', '将开通东栈航路'), ('C00704', '开通东栈航路', '开通柜台照明'),
    ('C00704', '颁行《分仓令》', '建立港口雕像'),
    ('C00707', '东栈粮仓断供', '东栈粮仓可能断供'), ('C00707', '东栈粮仓断供', '相关资源短缺'),
    ('C00710', '港议会颁行《复仓章程》', '港议会修建一座码头'),
    ('C00710', '罢运', '开市'), ('C00712', '秘密串联仓户', '公开登记仓户'),
    ('C00712', '因两埠税争未解而', '开始'), ('C00716', '废除世袭仓权', '可能废除世袭仓权'),
    ('C00716', '废除世袭仓权', '取消门前宴席'), ('C00716', '争夺仓权', '商定仓单'),
])
def test_projected_and_unrelated_events_cannot_be_used(key, original, replacement):
    rule, limits = CASES[key]
    assert original in rule
    assert approved_period(card(rule.replace(original, replacement), limits), key) is None


@pytest.mark.parametrize('key', CASES)
def test_wrong_scope_unapproved_retracted_or_ambiguous_record(key):
    rule, limits = CASES[key]
    assert approved_period(card(rule, limits, status='proposed'), key) is None
    assert approved_period(card(rule, limits, version=False), key) is None
    assert approved_period(card(rule, '以正史为准。'), key) is None
    assert approved_period(card(rule, limits.replace('雾港', '西岸')), key) is None
    assert approved_period(card(rule + '上述分期作废。', limits), key) is None
    assert approved_period(card(rule + rule.replace('港历', '新历'), limits + limits.replace('港历', '新历')), key) is None


def test_unresolved_material_dispute_can_be_a_separate_scoped_fact():
    value, limits = CASES['C00712']
    assert approved_period(card(value.replace('税争未解', '税争尚未解决'), limits), 'C00712')
    rule = value.replace('盐盟因两埠税争未解而', '盐盟').replace(
        '港历30年', '雾港在固化期两埠税争尚未解决。港历30年')
    proof = approved_period(card(rule, limits), 'C00712')['evidence']
    assert '雾港在固化期两埠税争尚未解决' in proof['prior_facts']
    assert approved_period(card(rule.replace('雾港在固化期两埠', '西岸在固化期两埠'), limits), 'C00712') is None


def test_known_prior_period_is_not_enough_to_invent_another_era():
    rule, limits = CASES['C00712']
    assert approved_period(card(rule + '盐盟希望世界由暗流期转为裂变期。', limits), 'C00712')
    assert approved_period(card(rule + '港历37年，三埠公会可能废除世袭仓权，促使雾港由暗流期转入裂变期。', limits), 'C00716') is None


def test_date_validation_in_an_adjacent_history_is_local_to_the_authored_calendar_and_world():
    first, limits = CASES['C00704']
    second = CASES['C00707'][0]
    for key in ('C00704', 'C00707'):
        assert approved_period(card(first + second, limits), key)
        assert approved_period(card(first + second.replace('19年', '11年'), limits), key) is None
        assert approved_period(card(first + second.replace('19年', '十二年'), limits), key)
    distant = CASES['C00712'][0].replace('30年', '七年')
    assert approved_period(card(first + distant, limits), 'C00704') is None
    assert approved_period(card(first + distant, limits), 'C00712') is None
    other = second.replace('19年', '1年').replace('雾港', '西岸')
    assert approved_period(card(first + other, limits + limits.replace('雾港', '西岸')), 'C00704')
    assert approved_period(card(first + first.replace('12年', '14年'), limits), 'C00704') is None


def test_scope_and_event_are_not_borrowed_from_another_story():
    rule, limits = CASES['C00704']
    fact, turn, _ = rule.split('。')
    assert approved_period(card(fact.replace('雾港', '西岸') + '。' + turn, limits), 'C00704') is None
    assert approved_period(card(fact + '。港历十二年，传闻港议会开通东栈航路，促使雾港由创始期转入扩张期。', limits), 'C00704') is None
    assert approved_period(card(fact + '。港历十二年，港议会开通东栈航路。雾港由创始期转入扩张期。', limits), 'C00704') is None
    assert approved_period(card('以下分期仅供参考。' + rule, limits), 'C00704') is None
    assert approved_period(card(rule.replace('期由港议会', '期于港历20年由港议会'), limits), 'C00704') is None
    proof = approved_period(card(rule + '别处下次庆典日期待核。', limits), 'C00704')['evidence']
    assert {'分仓令', '东栈航路'} <= set(proof['anchors'])


def test_date_and_cause_can_be_given_from_the_worlds_point_of_view():
    rule = '创始期，雾港曾由港议会颁行《分仓令》。雾港于港历十二年因港议会开辟东栈航路，从创始期进入扩张期。'
    evidence = approved_period(card(rule, '雾港的历史分期以港历纪年为准。'), 'C00704')['evidence']
    assert evidence['year'] == 12 and evidence['event'] == '港议会开辟东栈航路'


RELATIVE_RULE = CASES['C00704'][0].replace('颁行', '施行').replace('港历12年', '《分仓令》施行次年')
RELATIVE_LIMITS = '该分期仅适用于雾港，以《分仓令》施行为起点。'


@pytest.mark.parametrize(('interval', 'offset'), [('次年', 1), ('后两年', 2), ('三年后', 3),
                                                 ('同年', 0), ('之后', None)])
def test_established_event_is_a_time_reference_without_inventing_a_year(interval, offset):
    rule = RELATIVE_RULE.replace('施行次年', '施行' + interval)
    result = approved_period(card(rule, RELATIVE_LIMITS), 'C00704')
    e = result['evidence']
    assert e['time_kind'] == 'relative' and e['year'] is None and e['calendar'] == ''
    assert e['time_anchor'] == '《分仓令》施行' and e['offset'] == relative_offset(interval) == offset
    assert e['time_text'] == '《分仓令》施行' + interval and e['date_source'] == ''


def test_year_can_only_be_derived_from_an_attested_date_for_the_same_local_event():
    dated = '雾港的《分仓令》于港历十一年施行。'
    e = approved_period(card(RELATIVE_RULE + dated, RELATIVE_LIMITS), 'C00704')['evidence']
    assert e['calendar'] == '港历' and e['year'] == 12 and e['date_source'] == dated.rstrip('。')
    for other in (dated.replace('雾港', '西岸'), dated.replace('施行', '签署'), dated.replace('分仓令', '别港令')):
        result = approved_period(card(RELATIVE_RULE + other, RELATIVE_LIMITS), 'C00704')
        assert result['evidence']['year'] is None
    assert approved_period(card(RELATIVE_RULE + dated + dated.replace('十一', '十六'), RELATIVE_LIMITS), 'C00704') is None


def test_reference_action_must_have_occurred_and_be_recognized_within_the_authorized_scope():
    never = RELATIVE_RULE.replace('由港议会施行', '由港议会颁行')
    for other in ('', '西岸已施行《分仓令》。', '雾港旁观西岸施行《分仓令》。', '雾港准备施行《分仓令》。'):
        assert approved_period(card(never + other, RELATIVE_LIMITS), 'C00704') is None
    assert approved_period(card(RELATIVE_RULE, RELATIVE_LIMITS.replace('分仓令', '安粮令')), 'C00704') is None
    for before in ('之前', '前一年', '三年前'):
        assert approved_period(card(RELATIVE_RULE.replace('次年', before), RELATIVE_LIMITS), 'C00704') is None


def test_relative_sequence_compares_only_events_with_the_same_origin():
    second = CASES['C00707'][0].replace('港历19年', '《分仓令》施行当年')
    assert approved_period(card(RELATIVE_RULE + second, RELATIVE_LIMITS), 'C00704') is None
    assert approved_period(card(RELATIVE_RULE + second.replace('施行当年', '施行后四年'), RELATIVE_LIMITS), 'C00707')
    assert approved_period(card(RELATIVE_RULE.replace('次年', '之后') + second.replace('当年', '之前'), RELATIVE_LIMITS), 'C00704') is None
    absolute = CASES['C00707'][0]
    assert approved_period(card(RELATIVE_RULE + absolute, RELATIVE_LIMITS + LIMITS), 'C00704')
    assert approved_period(card(RELATIVE_RULE + absolute, RELATIVE_LIMITS + LIMITS), 'C00707')
