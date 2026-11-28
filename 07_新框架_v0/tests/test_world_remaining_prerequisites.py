"""Frozen project evidence and original inputs for the previously unhandled world relationships."""
from collections import Counter
from pathlib import Path

import pytest

from nw.materials import world_advancement, world_conversion, world_history, world_market, world_network, world_resources
from nw.materials.world_prerequisites import SPECS, matches, relevant
from nw.task_models import content_sha256


def card(rule, limit='仅在北港适用，超过该区须重新核验。', key='harbor'):
    return {'key': key, 'kind': 'world', 'body': {'title': '北港规则', 'rule': rule, 'limits': limit}}


def product(name, body):
    return {'stage': name, 'products': body, 'sha256': content_sha256(body), 'task_id': 'test-' + name}


def evidence(key, *cards, previous=None):
    return matches(key, {'members': list(cards)}, products=previous or {}, context={})


BASIC_EXAMPLES = [
    ('C00035', '船坞用同批原料试烧时，转化效率决定了输出雾晶的纯度。'),
    ('C00103', '北堤磁雾异常时，平时有效的定向罗盘会失灵。'),
    ('C00104', '夜班可见蓝火异常，渡吏无法解释它为何只在退潮出现。'),
    ('C00121', '雾晶浓度在每日夜半持续升高，浓度时间变化导致闸区出现能量潮汐。'),
    ('C00427', '同一井口持续三旬的浓度下降会导致井源枯竭，井底矿线由绿转灰。'),
    ('C00469', '北崖地势隔断暖流，使崖背的栖息层只能容纳耐冻物种。'),
    ('C00154', '古城得名镜井，因当地独有双月倒映的异象，旧称记在港史。'),
    ('C00574', '雾灯经旧主改造后，只有旧灯芯能使夜行功能生效。'),
    ('C00585', '船员反复使用暖雾灯缓解疼痛后，会逐渐依赖灯火才能入睡。'),
    ('C00676', '火种器具只准持证人开启，北港职业权限据此比照，守井岗位另由行会核定。'),
    ('C00748', '本地公设只允许观察者看见潮面反光，潮下回响的来源对他不可知。'),
    ('C00738', '港务官签发双印令后，守档人按号验印才能开卷。'),
    ('C00789', '鱼骨族天生鳃孔畏灰，遇矿尘时只能潜游，失去鸣声定位能力。'),
    ('C00812', '瓷偶腕上接口只与同纹器械兼容，接合后才能稳定提灯。'),
    ('C01754', '港民须持许可证才可在东崖采集雾草，凭刻刀获取可入库的原料。'),
    ('C01808', '渡工用书中设定的解毒仪式后，手上的毒斑会消退，只有这项症状可作解毒征兆。'),
]


ADDITIONAL_EXAMPLES = [
    ('C00098', '雾井跌破六格临界值后，水面以下的剩余储量封存，船工只可动用井沿的一格。'),
    ('C00107', '港闸验算以封闭水轮为界，守恒账把船工收回的余热也按实际去向记入总量。'),
    ('C00410', '石窑密闭后窑芯矿火守恒，转移到水缸的热量须计入封闭窑室的总账。'),
    ('C00051', '井口的游离能量在内湾汇集，形成的浓度比潮沟出口高一个刻度。'),
    ('C00109', '峡口的灵雾流经内湾后会使湾内浓度升高，放下阻隔闸时峰值回落。'),
    ('C00112', '港堤更换导能矿脉后，铁灰介质的低传导会降低下游井水的浓度。'),
    ('C00113', '同材矿脉的传导系数升高时，井口到闸楼的传输时间缩短半息。'),
    ('C00115', '北港井场的浓度降低后，原本可吸收的游离能量只剩井栏以内的一圈。'),
    ('C00126', '双月牵引雾湾潮汐，以两次退潮为一个周期，覆盖范围止于庙前浅滩。'),
    ('C00135', '巡楼铜锣的扰动会让石英介质的传导延迟，影响范围到石阶第三级为止。'),
    ('C00412', '北港沿岸流向以实测浮屑为准，流经石屏障时会出现贴岸回流。'),
    ('C00413', '峡口改道后灵雾的流向决定湾内富集的分布，两侧地形将支流隔开。'),
    ('C00416', '北堤两段矿脉的传导差异使来雾在西侧富集，同一来源的东侧岩层仅存薄霜。'),
    ('C00418', '岸站按同日三个测点的读数画出浓度分布，用同地等浓线给封港区域划界。'),
    ('C00421', '井吏按每日夜半的测点记录浓度的时间变化，同一根井绳上才可对照峰谷。'),
    ('C00424', '北港能量潮汐按双月牵引划定周期，覆盖旧闸流域的同一组峰谷由两岸轮值员共同登记。'),
    ('C00426', '东井三旬浓度下降后，每日能够收存的游离能量减少一半。'),
    ('C00435', '本季潮汐减弱时，岸线按与上次实测相同的刻尺登记，峰谷幅度只剩两格。'),
    ('C00438', '渡工记录锣响后水面出现的异常，只看见逆行的浮屑，无法解释其来处。'),
    ('C00439', '北堤例外只在重雾逆行时生效，每次发动须由守闸人支付一枚旧堤印作为代价。'),
    ('C00441', '行井护符作为封闸例外仅可开启一扇侧门，每次功能生效便磨去一道锁纹。'),
    ('C00487', '湾内轮捕维持岸滩的生态均衡，鲜鱼每日按时供应，使旧街仍保持原有秩序。'),
    ('C00496', '东北雾井每夜熵增，导致同一测点在闭闸后的时段持续出现浓度下降。'),
    ('C00817', '旧镜的镀层部件老化时，倒影周围的灵雾浓度下降，记录须对照同日未换镜的邻井。'),
    ('C00746', '北港公设规定封闭水轮中的潮能守恒，渗到轴心的热量也须计入系统。'),
    ('C00751', '旧港公设规定境内各井在封闭时盐印总数恒定，过闸时须另计移交的印。'),
    ('C00776', '两处井室实测的盐印总数始终不变，验证了闸内总印量封闭的世界公设。'),
    ('C00155', '镜浪异象只在退潮留下可见的重影，渡工只能看到石阶上水痕，须待下次涨潮才能验证来处。'),
    ('C00691', '港史记下殉堤者的名录，旧闸因此得名守灵坞，现今渡祭仍保有肃穆的基调。'),
    ('C00692', '北港浮市的名称取自该地独有的潮汐奇观，史载潮退后整条街会随旧船回湾。'),
    ('C00693', '县志把港湾正式名定为月箕，官文登记须用正名，本地方言却按潮形俗称弯筐。'),
    ('C00196', '行会按登记的天赋档发放见习潜工的准入资格，仍须下井考核才能领工具。'),
    ('C00210', '港务署按本季各档占比分配培训名额，再经考核发放见习资格，名额按全湾登记人数核算。'),
    ('C00212', '三港资质分布不均时，旧条令据此调整各族待遇，族内仍须分别核准参与资格。'),
    ('C00346', '县库登记的家籍身份决定本地户册的阶层，家籍未经核验就不能享受免税待遇。'),
    ('C00730', '北港按户别分别开放升迁渠道，渔户须通过潮汛考试才有报名资格。'),
    ('C00731', '北港按户别征收夜航税，巡吏执行禁令时对无担保的下户强征一日劳役。'),
    ('C00780', '苇湾族群在沼泽环境中靠鳃维持水下听力，离开湿地后这项能力只能维持一刻。'),
    ('C00783', '北港族群申请潜工岗位时按实际潜游能力核准资格，无法久潜者须改报岸巡。'),
    ('C00785', '南湾族人的鳃遇矿尘堵塞时其水下行动受限，须返回净井才能恢复听力。'),
    ('C00791', '迁入北港的外港族群须按盐务条例登记户籍，取得同等待遇前须完成值闸义务。'),
    ('C00794', '迁居的螺港族群按行会制度申请北港职业，持证后才可任职于井场。'),
    ('C00839', '渡吏升任闸长须先通过三季考核，这项升迁是盐务署认可的晋升通道。'),
    ('C00842', '封闸岗位的职权只准负责检验持印人的签文，超出验印任务须请港署核准。'),
    ('C00847', '账房认可的护航工分须满六十才可报考升任闸长，累计工分还须并列通过识潮考核。'),
    ('C00945', '北港强征船担的法令只对下户阶层执行，税吏征收时须在负担人名下登记。'),
    ('C00965', '远籍盐吏的双重身份触发渡口条例中的户别裁定，只能按临时资格通行。'),
    ('C00579', '使用旧港钥匙每次开启潮门，都会从持有人交存的盐印中扣除一枚作为代价。'),
    ('C00580', '旧井钥匙只能由登记持有者本人使用一次，第二次入锁时锁齿便收紧。'),
    ('C00613', '潮灯升级后才可照见井底，灯匠须记录触发改造时该器物原有的暖光范围。'),
    ('C00674', '雾灯的用途仅供照路，这件器物只对盐苔石阶生效，干石阶上的灯影不显形。'),
    ('C00684', '铸师按旧工艺制造的那把钥匙只能开启一口井，其铸记是持有人交接账的第一笔。'),
    ('C00803', '岸亭吊臂的构造只容许两排卡齿受力，载重上限为三桶，过载时铁舌会脱扣。'),
    ('C00825', '潜工的能力边界可比照护耳器具的使用边界，器具只能保温，潜工也无法靠它延长闭气时限。'),
    ('C00826', '雾语听辨的能力边界决定其作用对象，只对仍在敲击岸壁的舟工手铃生效。'),
    ('C00872', '井港工匠制成的引潮法器须标明工坊和第一位持有者，后主换手时沿用同一枚铸记。'),
    ('C00045', '北港潜工的天赋档位决定战力核算中的灵力纯度折算上限。'),
    ('C00062', '寒井凝成的晶化灵能可嵌作夜航雾灯的照明器物，燃尽三刻后晶核碎裂。'),
    ('C00110', '内湾灵雾流动在闸门开启时遵循梯度散逸的流动规律，遇矿核屏障才转为局部回流。'),
    ('C00116', '内湾两岸的浓度分布决定浅滩产出的盐晶资源品级，低浓潮沟只结粗盐。'),
    ('C00415', '堤下铜脉的传导系数决定潮能沿矿脉传导时的衰减速率。'),
    ('C00419', '北港实测的空间浓度分布决定海底晶矿资源的富集界线，测点三格以下无伴生矿线。'),
    ('C00881', '井港技能树的深水节点比照资质档设两级修习门槛，仍须先修辨流才能解锁。'),
    ('C00882', '守闸技能树的验印节点是升任闸吏的门槛，只有掌握真蜡辨识后才可参加升职考核。'),
]


@pytest.mark.parametrize(('key', 'rule'), BASIC_EXAMPLES + ADDITIONAL_EXAMPLES)
def test_specialist_world_rule_matches_its_frozen_card(key, rule):
    [match] = evidence(key, card(rule))
    assert match['member'] == 'harbor'
    assert match['paths'] == ['/members/0/body/rule', '/members/0/body/limits']
    assert match['rule_excerpt'] in rule


def test_similar_vocabulary_does_not_reverse_the_source_or_join_cards():
    to_jobs = card('北港按门第决定可以任职的岗位，只有登记商户才有仓吏准入资格。')
    to_class = card('北港仓吏任职后由巡署授予阶层地位，按其官职列入上户待遇。')
    assert evidence('C00727', to_jobs) and not evidence('C00827', to_jobs)
    assert evidence('C00827', to_class) and not evidence('C00727', to_class)
    assert not evidence('C00121', card('北港能量潮汐决定每日夜间井口的浓度时间变化。'))
    assert not evidence('C00738', card('港务官每旬签发双印令。'), card('守档人按双印执行放行。', key='vault'))
    assert not evidence('C00738', card('港务官签发双印令，守档人放行。', '待定'))
    assert not evidence('C00738', card('据说港务官能签发双印令，守档人会按号验印。'))
    assert not evidence('C00738', card('港务官签发双印令，守档人按号验印才能开卷。',
                                       '旧例已取消了港务官签发双印令和守档人验印的整套规则。'))
    assert not evidence('C00738', card('权力结构与执行机制。'))
    assert not evidence('C00676', card('行会把道具列在职业装备清单，花名册列出岗位职责。'))
    assert relevant('C00738', '北港案卷授权和执行机制该如何影响调阅权？')
    assert not relevant('C00738', '北港的天赋分档应如何用于晋升？')


@pytest.mark.parametrize(('forward', 'reverse', 'statement'), [
    ('C00051', 'C00115', '东井口的游离能量汇集后决定湾内浓度，渡工每日采集一管作比。'),
    ('C00115', 'C00051', '同井浓度从三格升到五格后，可吸收的游离能量才可以在封闭渠内汇集。'),
    ('C00751', 'C00776', '北港公设规定同一封闭井内盐印总数恒定，每夜须观测一次。'),
    ('C00776', 'C00751', '各地点实测的盐印总量始终不变，这项观察印证了北港公设。')])
def test_observation_and_reverse_cause_have_distinct_prerequisites(forward, reverse, statement):
    assert evidence(forward, card(statement)) and not evidence(reverse, card(statement))


def test_adjudicated_world_edges_enforce_explicit_mechanism_and_boundary_guards():
    assert {k for k, r in SPECS.items() if r['status'] == 'unresolved'} == set()
    for key in ('C00045', 'C00110'):
        assert SPECS[key]['status'] == 'conditional'
    # Arbitrary independent multiplier or unbounded universal flow claims remain rejected.
    assert not evidence('C00045', card('天赋品质以五分计入港内力量公式，为独立变量。'))
    assert not evidence('C00110', card('港内流动规律规定能量永远由高浓度扩散至低浓度。'))
    assert evidence('C00045', card('北港潜工的天赋档位决定战力核算中的灵力纯度折算上限。'))
    assert evidence('C00110', card('内湾灵雾流动在闸门开启时遵循梯度散逸的流动规律，遇矿核屏障才转为局部回流。'))


@pytest.mark.parametrize(('key', 'ability_limit', 'rule'), [
    ('C00025', '回声术每息耗两格灵力。', '回声术能量总量不足六格时，每息耗两格，只能维持两息。'),
    ('C00032', '回声术的纯度会限制同招的回响时间。', '回声术使用同招时纯度越高，术式效果的回响延迟越久。'),
])
def test_cross_stage_static_source_requires_a_real_ability_and_event_for_the_same_actor(key, ability_limit, rule):
    limit = '仅在旧港雾井旁能使用回声术。'
    character = {'capabilities': [{'can_act': True, 'entity': 'keeper', 'abilities': ['回声术'], 'limits': [ability_limit]}]}
    event = {'event_nodes': [{'actors': ['keeper'], 'goal': '在灯熄前用回声术核验井底石刻。'}]}
    assert SPECS[key]['consumers'] == ('action_design',)
    assert not evidence(key, card(rule, limit))
    previous = {'character_design': product('character_design', character), 'plot_design': product('plot_design', event)}
    [match] = evidence(key, card(rule, limit), previous=previous)
    assert match['upstream_refs'] == ['input:character_design:/capabilities/0/abilities/0',
                                      'input:character_design:/capabilities/0/limits/0',
                                      'input:plot_design:/event_nodes/0/goal']
    wrong = {'event_nodes': [{'actors': ['stranger'], 'goal': '在灯熄前用回声术核验井底石刻。'}]}
    assert not evidence(key, card(rule, limit), previous={**previous, 'plot_design': product('plot_design', wrong)})
    assert not evidence(key, card(rule.replace('回声术', '织影术'), limit.replace('回声术', '织影术')), previous=previous)


@pytest.mark.parametrize(('key', 'rule'), [
    ('C00702', '灰港冷峻的基调呼应本书悬疑类型的读者承诺，镜面线索只能由渡工观察。'),
    ('C00782', '苇湾族群在夜汛中的回声感知呼应已选悬疑类型的读者承诺，只有触水的证人能辨别假铃声。')])
def test_type_promise_comes_from_actual_type_selection(key, rule):
    world = card(rule)
    assert not evidence(key, world)
    chosen = product('type_selection', {'selection': [{'label': '悬疑', 'basis': '基于证词重建渡船经过'}]})
    assert evidence(key, world, previous={'type_selection': chosen})[0]['upstream_refs'] == [
        'input:type_selection:/selection/0/label']


def test_specs_cover_all_formal_remaining_original_edges_in_the_mystery_sample():
    from nw.materials.network_workflow import type_matches
    from nw.materials.phase_flow import STAGE_MATERIALS, _step_source_pool
    from nw.materials.stage_input import STEP_SOURCE_POLICY
    from nw.materials.type_network_catalog import edge_proof
    from nw.materials.work_catalog import SourceDesk

    assert len(SPECS) == 86
    specialized = {'C00025', 'C00032', 'C00702', 'C00782', 'C00727', 'C00827'}
    assert {key for key, _ in BASIC_EXAMPLES + ADDITIONAL_EXAMPLES} | specialized == {
        key for key, spec in SPECS.items() if spec['status'] == 'conditional'}
    assert Counter(r['family'] for r in SPECS.values()) == {
        '能量计量与转化': 7, '能量场与生态': 25, '例外与知情范围': 9,
        '命名与类型承诺': 7, '群体与制度': 20, '道具、功能与技能': 18}
    workspace = Path(__file__).resolve().parents[1] / 'workspace'
    if not (workspace / 'materials/catalog.db').exists():
        pytest.skip('正式资料目录不在此工作区')
    desk = SourceDesk(workspace)
    package = {'stage_source_policy': STEP_SOURCE_POLICY, 'stage_materials': STAGE_MATERIALS}
    world = _step_source_pool(desk, 'world_design', package)
    action = _step_source_pool(desk, 'action_design', package)
    previous = world_network.enabled_rules({f'world_{name}_policy': module.POLICY for name, module in (
        ('network', world_network), ('advancement', world_advancement), ('conversion', world_conversion),
        ('resource', world_resources), ('market', world_market), ('history', world_history))})
    rules = desk.dynamic_rules()
    verified, in_action = set(), set()
    for ident in world:
        rule = rules.get(ident)
        if (not rule or not rule['derived'] or desk.by_id[ident]['state'] != 'design_ready'
                or rule['key'] in previous or not type_matches(rule['valid_types'], {'GENRE_XUANYI': ['悬疑']})):
            continue
        key = rule['key']
        proof = edge_proof(desk.read(ident), desk.read(rule['static_id']))
        assert proof and proof['edge'] == {k: SPECS[key]['relation' if k == 'type' else k]
                                            for k in ('source', 'target', 'type', 'condition')}
        if rule['static_id'] not in world:
            assert rule['static_id'] in action
            in_action.add(key)
        verified.add(key)
    assert verified == set(SPECS)
    assert in_action == {'C00025', 'C00032'}
