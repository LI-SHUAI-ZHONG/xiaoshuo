
"""Historical geography and institutions need the author's scoped cause and consequence."""
import pytest

from nw.materials.world_history_impacts import approved_history_impact, check_impact_claims


CASES = {
    'C00694': ('枯水期，北港因白石峡阻断灯盐船，海仓会与盐务司围绕灯盐运权的争夺成为核心矛盾。',
               '灯盐运权之争仅适用于北港枯水期。'),
    'C00705': ('创始期，北港因潮祭师铸成镇潮碑，确立潮雾穿堤的先验规则：潮雾只能在退潮时穿过堤门，此后由守潮人每旬校准碑纹维持。',
               '潮雾穿堤仅在北港的堤门潮纹完整时生效。'),
    'C00708': ('扩张期，北港因盐务司开凿支港，白沙航道由封闭改为通航。',
               '白沙航道的通行变更仅适用于北港扩张期。'),
    'C00709': ('动荡期，北港因盐务司废除了旧盐引，海仓会与盐工团围绕领盐资格的争夺成为核心矛盾。',
               '领盐资格之争仅适用于北港动荡期，只要新盐引仍决定配给，该矛盾就会延续。'),
    'C00713': ('固化期，北港因盐务司施行新盐籍，持青印盐引的盐商被列为上户，按户取得每旬两袋配盐。',
               '盐商的上户资格仅适用于北港固化期。'),
    'C00714': ('固化期，北港因港议会颁布封仓令，议盐院取得北仓配盐的裁定权，由仓丞凭双印仓券执行。',
               '北仓配盐的裁定权仅适用于北港固化期。'),
}


def card(rule, limits, **attrs):
    return {'card_id': 'harbor-history', 'kind': 'world', 'status': 'approved', 'version': 2,
            'body': {'rule': rule, 'limits': limits}, **attrs}


@pytest.mark.parametrize('key', CASES)
def test_requires_evidence_from_the_approved_historical_setting(key):
    rule, limits = CASES[key]
    proof = approved_history_impact(card(rule, limits), key)
    assert (proof['rule'], proof['limits'], proof['version']) == (rule, limits, 2)
    assert proof['evidence']['region'] == '北港'
    assert proof['evidence']['event'] in rule
    assert proof['evidence']['anchors'] and all(anchor in rule for anchor in proof['evidence']['anchors'])
    assert proof['evidence']['boundary'] in limits
    assert not approved_history_impact(card(rule, limits, status='draft'), key)
    assert not approved_history_impact(card(rule, limits.replace('北港', '南港')), key)
    assert not approved_history_impact(card(rule.replace('北港因', '北港据传因'), limits), key)
    assert not approved_history_impact(card(rule.replace('北港因', '北港因计划'), limits), key)
    assert not approved_history_impact(card(rule, limits.replace('仅', '或许仅')), key)


@pytest.mark.parametrize(('key', 'old', 'replacement'), [
    ('C00694', '白石峡阻断灯盐船', '历史事件'), ('C00694', '灯盐船', '通行'),
    ('C00694', '盐务司', '海仓会'), ('C00694', '灯盐运权', '资源'),
    ('C00705', '潮祭师铸成镇潮碑', '发生事件'), ('C00705', '潮雾只能在退潮时穿过堤门', '待定'),
    ('C00705', '每旬校准碑纹', '口头提议'), ('C00708', '开凿支港', '筹备开凿支港'),
    ('C00708', '封闭改为通航', '开放改为通航'), ('C00708', '由封闭', '由某种状态'),
    ('C00709', '盐务司废除了旧盐引', '有人去过旧仓'), ('C00709', '海仓会与盐工团', '海仓会与海仓会'),
    ('C00713', '持青印盐引的', ''), ('C00713', '每旬两袋配盐', '资源'),
    ('C00714', '双印仓券', '凭证'), ('C00714', '颁布封仓令', '讨论封仓令'),
])
def test_missing_or_unconfirmed_link_cannot_be_adopted(key, old, replacement):
    rule, limits = CASES[key]
    assert old in rule
    assert not approved_history_impact(card(rule.replace(old, replacement), limits), key)


@pytest.mark.parametrize('key', CASES)
def test_independent_rules_can_coexist_on_one_card(key):
    combined = card(''.join(rule for rule, limits in CASES.values()), ''.join(limits for rule, limits in CASES.values()))
    assert approved_history_impact(combined, key)


def test_conflicting_reports_about_one_route_remain_unusable():
    route, limits = CASES['C00708']
    assert not approved_history_impact(card(route + route.replace('封闭改为通航', '通航改为封闭'), limits), 'C00708')
    assert not approved_history_impact(card(route, limits + '白沙航道的通行变更已撤销。'), 'C00708')


@pytest.mark.parametrize('statement', [
    '扩张期，北港的白沙航道仍然封闭。', '北港在扩张期，白沙航道始终禁航。',
    '账簿证实扩张期的北港，白沙航道并未通航。',
    '据传白沙航道已通航，但档案证实扩张期，北港的白沙航道仍然封闭。',
    '北港在扩张期，白沙航道由通航改为封闭。', '扩张期北港，白沙航道仍未开放。',
    '扩张期内，北港的白沙航道一直不通船。', '史书记载扩张期，北港盐务司开凿支港。白沙航道却从未开放。',
])
def test_plot_cannot_reverse_the_approved_route_outcome(statement):
    p = approved_history_impact(card(*CASES['C00708']), 'C00708')
    with pytest.raises(ValueError, match='C00708'):
        check_impact_claims('C00708', p['evidence'], [statement])


@pytest.mark.parametrize('statement', [
    '北港在扩张期，白沙航道已经通航。', '扩张期，北港的白沙航道由封闭改为通航。',
    '扩张期，南港的白沙航道仍然封闭。', '动荡期，北港的白沙航道仍然封闭。',
    '扩张期，北港的青石航道仍然封闭。', '听说扩张期，北港的白沙航道仍然封闭。',
    '扩张期，北港的白沙航道仍然封闭吗？', '扩张期，北港的白沙航道此前封闭。',
    '如果扩张期，北港的白沙航道封闭，船工就走旧道。',
    '据传扩张期，北港盐务司开凿支港。白沙航道却从未开放。',
    '扩张期，北港盐务司开凿支港。动荡期移居南港。白沙航道却从未开放。',
    '扩张期，北港的白沙航道是否封闭仍待核实。', '扩张期，北港的白沙航道封闭区立着旧碑。',
])
def test_other_context_or_speculation_does_not_overwrite_history(statement):
    p = approved_history_impact(card(*CASES['C00708']), 'C00708')
    check_impact_claims('C00708', p['evidence'], [statement])


@pytest.mark.parametrize(('key', 'statement'), [
    ('C00694', '枯水期，北港的海仓会与盐务司围绕灯盐运权一直没有争端。'),
    ('C00705', '创始期，北港从未确立潮雾穿堤的先验规则。'),
    ('C00709', '动荡期，北港的海仓会与盐工团围绕领盐资格一直没有争端。'),
    ('C00713', '固化期，北港的持青印盐引的盐商被列为下户。'),
    ('C00714', '固化期，北港的北仓配盐的裁定权专属于船行。'),
])
def test_directly_conflicting_history_in_a_cited_field_is_rejected(key, statement):
    p = approved_history_impact(card(*CASES[key]), key)
    with pytest.raises(ValueError, match=key):
        check_impact_claims(key, p['evidence'], [statement])



def test_printed_exception_condition_and_distinct_time_windows_are_preserved():
    from nw.materials.world_history_impacts import impact_comparison

    rule, limit = CASES['C00708']
    summer = limit.rstrip('。') + '，且仅在夏汛水位过线时生效。'
    winter = limit.rstrip('。') + '，且仅在冬汛水位过线时生效。'
    e = approved_history_impact(card(rule, summer), 'C00708')['evidence']
    other = approved_history_impact(card(rule.replace('封闭改为通航', '通航改为封闭'), winter), 'C00708')['evidence']
    assert impact_comparison('C00708', e)[0] != impact_comparison('C00708', other)[0]
    check_impact_claims('C00708', e, ['冬汛水位过线时，扩张期，北港的白沙航道仍然封闭。'])
    with pytest.raises(ValueError, match='C00708'):
        check_impact_claims('C00708', e, ['夏汛水位过线时，扩张期，北港的白沙航道仍然封闭。'])



def test_geography_need_not_invent_a_historical_period_for_a_permanent_bottleneck():
    rule, limits = CASES['C00694']
    proof = approved_history_impact(card(rule.removeprefix('枯水期，'), limits.replace('枯水期', '')), 'C00694')
    assert proof['evidence']['region'] == '北港' and proof['evidence']['period'] == ''
    with pytest.raises(ValueError, match='C00694'):
        check_impact_claims('C00694', proof['evidence'], ['海图记载北港的海仓会与盐务司围绕灯盐运权一直没有争端。'])


def test_approved_class_membership_and_enforcement_can_come_from_practice():
    rule, limits = CASES['C00713']
    proof = approved_history_impact(card(rule.replace('持青印盐引', '缴清五年盐税'), limits), 'C00713')
    assert proof['evidence']['permit'] == '五年盐税'
    with pytest.raises(ValueError, match='C00713'):
        check_impact_claims('C00713', proof['evidence'], ['固化期，北港的缴清五年盐税的盐商被列为下户。'])
    rule, limits = CASES['C00714']
    rule = rule.replace('凭双印仓券执行', '通过封锁码头落实')
    assert approved_history_impact(card(rule, limits), 'C00714')['evidence']['procedure'] == '封锁码头'


def test_later_statement_on_same_card_cannot_establish_an_opposing_history():
    rule, limits = CASES['C00708']
    for text in ('扩张期，北港的白沙航道始终封闭。', '白沙航道的通行变更已撤销。', '本卡仅作示例。'):
        assert not approved_history_impact(card(rule + text, limits), 'C00708')
    assert approved_history_impact(card(rule + '动荡期，北港的白沙航道始终封闭。', limits), 'C00708')


def test_alternate_attested_route_description_preserves_the_original_wording():
    rule = '扩张期的北港，由于盐务司修通了新闸，原本封闭的白沙航道从此开放。'
    assert approved_history_impact(card(rule, CASES['C00708'][1]), 'C00708')['evidence']['after'] == '开放'



@pytest.mark.parametrize('claim', [
    '固化期，北港的持青印盐引的盐商按户取得每旬九袋配盐。',
    '固化期，北港的持青印盐引的盐商被列为上户，按户取得每旬九袋配盐。',
    '固化期，北港的持青印盐引的盐商按户取得每旬两箱配盐。',
])
def test_known_quota_in_anotherwise_correct_class_grant_is_checked(claim):
    e = approved_history_impact(card(*CASES['C00713']), 'C00713')['evidence']
    with pytest.raises(ValueError, match='C00713'):
        check_impact_claims('C00713', e, [claim])
    check_impact_claims('C00713', e, [claim.replace('九袋', '2袋').replace('两箱', '2袋'),
                                      claim.replace('配盐', '煤炭'), claim.replace('青印', '金印')])


def test_independent_class_entitlements_are_compared_only_with_their_own_quota():
    from nw.materials.world_history_impacts import impact_comparisons

    rule, limits = CASES['C00713']
    def pairs(sentence):
        facts = impact_comparisons('C00713', approved_history_impact(card(sentence, limits), 'C00713')['evidence'])
        return {identity: outcome for identity, outcome, _ in facts}
    original = pairs(rule)
    changed = pairs(rule.replace('两袋', '九袋'))
    assert len(original) == 2 and original.keys() == changed.keys()
    assert len(set(original.values()) & set(changed.values())) == 1
    assert len(original.keys() & pairs(rule.replace('配盐', '米粮')).keys()) == 1
    assert original == pairs(rule.replace('两袋', '2袋'))


def test_only_exclusive_mandates_can_rule_out_another_enforcer_or_document():
    rule, limits = CASES['C00714']
    normal = approved_history_impact(card(rule, limits), 'C00714')['evidence']
    exclusive = approved_history_impact(card(rule.replace('由仓丞凭', '仅由仓丞只凭'), limits), 'C00714')['evidence']
    scope = '固化期，北港的北仓配盐的裁定权'
    for alternative in ('由仓丞凭蓝印仓券执行。', '由码头巡守凭双印仓券执行。'):
        check_impact_claims('C00714', normal, [scope + alternative])
        with pytest.raises(ValueError, match='C00714'):
            check_impact_claims('C00714', exclusive, [scope + alternative])
    for claim in ('由仓丞仅凭蓝印仓券执行。', '仅由码头巡守凭双印仓券执行。'):
        with pytest.raises(ValueError, match='C00714'):
            check_impact_claims('C00714', normal, [scope + claim])


def test_founding_premise_checks_mutually_exclusive_conditions_of_the_same_action():
    e = approved_history_impact(card(*CASES['C00705']), 'C00705')['evidence']
    prefix = '创始期，北港的潮雾穿堤的先验法则规定潮雾只能在'
    end = '时穿过堤门。'
    with pytest.raises(ValueError, match='C00705'):
        check_impact_claims('C00705', e, [prefix + '涨潮' + end])
    check_impact_claims('C00705', e, [prefix + '落潮' + end, prefix + '月出' + end,
                                      prefix + '涨潮' + end.replace('堤门', '南墙')])



@pytest.mark.parametrize('wrong_first', [False, True], ids=['reopen-changed-quota', 'reject-in-production'])
def test_unchanged_historical_rank_does_not_hide_an_invented_allotment(tmp_path, monkeypatch, wrong_first):
    from dataclasses import replace
    from test_material_world_conversion_flow import SELECTED_GENRE, assert_world_flow
    from test_material_world_history_flow import ROUTE

    rule, limits = CASES['C00713']
    choice = '[FAKE] 固化期，北港的持青印盐引的盐商被列为上户，按户取得每旬两袋配盐。'
    wrong = choice.replace('两袋', '九袋')
    case = replace(ROUTE, dynamic_key='C00713', static_key='32.4_固化期 / 33.1_阶层 / 转化',
                   condition='固化期固化阶层', rule=rule, limits=limits, waiting_reason='固化期',
                   title='北港上户的盐籍', choice=wrong if wrong_first else choice,
                   observable='[FAKE] 盐商在上户栏指认青印盐引与配盐份额，簿上每旬实拨两袋。',
                   check='[FAKE] 剧情核对青印盐引与上户盐籍规定的份额。',
                   expected_evidence=(('region', '北港'), ('rank', '上户')),
                   changed_rule=rule.replace('持青印盐引的', ''), changed_limits=limits.replace('北港', '南港'))
    assert_world_flow(tmp_path, monkeypatch, case, rule, SELECTED_GENRE, False,
                      rejection='C00713' if wrong_first else None, altered_plot=(wrong, 'C00713'))



def select_approved(key, entries):
    from nw.materials.world_history import consistent_history_cards

    approved = [card(rule, limits, card_id=f'harbor-{i}') for i, (rule, limits) in enumerate(entries)]
    proofs = [approved_history_impact(source, key) for source in approved]
    assert all(proofs)
    return [p['card_id'] for p in consistent_history_cards(key, proofs, approved)]


def test_founding_exclusions_use_the_same_norm_subject_action_condition_and_time_axis():
    rule, limits = CASES['C00705']
    rise = rule.replace('退潮', '涨潮')
    entries = [(rule, limits), (rise, limits),
               (rise.replace('穿过堤门', '越过石墙'), limits), (rise, limits.replace('潮纹完整', '潮纹封闭')),
               (rule.replace('退潮', '夜间'), limits), (rule.replace('退潮', '落潮'), limits)]
    assert select_approved('C00705', entries) == ['harbor-2', 'harbor-3', 'harbor-4']
    assert select_approved('C00705', [entries[0], entries[-1]]) == ['harbor-0', 'harbor-1']


def test_exclusive_executor_only_holds_grants_that_disagree_with_a_competing_card():
    rule, limits = CASES['C00714']
    other = rule.replace('由仓丞凭', '由巡河官凭')
    sole = rule.replace('由仓丞凭', '仅由仓丞凭')
    alternate_scope = limits.rstrip('。') + '，仅在封港警钟敲响时生效。'
    assert select_approved('C00714', [(rule, limits), (other, limits)]) == ['harbor-0', 'harbor-1']
    assert select_approved('C00714', [(sole, limits), (other, limits), (rule, limits), (other, alternate_scope)]) == [
        'harbor-2', 'harbor-3']
    assert select_approved('C00714', [(sole, limits), (other.replace('由巡河官', '仅由巡河官'), limits)]) == []


def test_only_exclusive_documents_of_the_same_executor_share_a_conflict():
    rule, limits = CASES['C00714']
    blue = rule.replace('双印仓券', '蓝印仓券')
    sole = rule.replace('仓丞凭', '仓丞只凭')
    entries = [(rule, limits), (sole, limits), (blue, limits), (blue.replace('仓丞凭', '巡河官只凭'), limits)]
    assert select_approved('C00714', entries) == ['harbor-0', 'harbor-3']
    assert select_approved('C00714', [(sole, limits), (blue.replace('仓丞凭', '仓丞只凭'), limits)]) == []
    # A single named enforcer can hold several ordinary procedures.
    assert select_approved('C00714', [(rule, limits), (blue, limits)]) == ['harbor-0', 'harbor-1']


def test_region_use_and_boundary_changes_do_not_need_a_navigation_state():
    rule = '扩张期，北港因商会收购旧滩，红苇滩的用途由盐田改为粮仓。'
    limits = '红苇滩的用途变更仅适用于北港扩张期。'
    proof = approved_history_impact(card(rule, limits), 'C00708')
    assert proof['evidence']['before'] == '盐田'
    with pytest.raises(ValueError, match='C00708'):
        check_impact_claims('C00708', proof['evidence'], ['扩张期，北港的红苇滩的用途仍为盐田。'])
    border = '北港在扩张期，因巡河司并入东汊，北渠辖区的边界由白石桥迁至芦亭。'
    proof = approved_history_impact(card(border, '北渠辖区的边界变更仅适用于北港扩张期。'), 'C00708')
    assert proof['evidence']['after'] == '芦亭'
