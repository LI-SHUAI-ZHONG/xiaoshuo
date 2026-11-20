"""The character subset must resolve original edges to compatible, actor-owned project evidence."""
import json
from copy import deepcopy

import pytest

from nw.materials import design_network
from nw.materials.character_prerequisites import SPECS, matches, relevant
from nw.materials.design_network_catalog import POLICY
from nw.materials.semantic_application import input_value
from nw.materials.steps.character_design_dynamic_network import MATERIAL as DYNAMIC
from nw.materials.steps.character_design_static_network import MATERIAL as STATIC
from nw.task_models import content_sha256


def record(stage, products):
    return {'stage': stage, 'task_id': 'test-' + stage, 'sha256': content_sha256(products), 'products': products}


def person(key='guard', **body):
    return {'kind': 'character', 'key': key, 'body': {'name': '沈砚', 'role': '验印渡吏', **body}}


def world(rule, limits):
    product = {'members': [{'kind': 'world', 'key': 'rule', 'body': {'rule': rule, 'limits': limits}}]}
    return {'world_design': record('world_design', product)}


def match(key, character, products=None, context=None):
    stages = {'character_design': record('character_design', character), **(products or {})}
    rows = matches(key, character, products=stages, context=context or {})
    for row in rows:
        assert row['paths']
        for ref in [*('input:character_design:' + p for p in row['paths']), *row['upstream_refs']]:
            assert input_value(ref, 'plot_design', stages, context or {}) is not None
    return rows


def test_all_47_preserve_their_distinct_static_and_dynamic_originals():
    blocked = {'C00616', 'C00618', 'C00619', 'C00627', 'C00856', 'C01235', 'C01304', 'C01707'}
    dynamic = {}
    for line in DYNAMIC.splitlines():
        number, sep, data = line.partition('｜')
        if number.isdecimal() and sep:
            row = json.loads(data)
            if row['generated_from_static']:
                dynamic[row['id']] = (int(number), row)
    static = {tuple(line.split('｜')[2:6]) for line in STATIC.splitlines() if line.split('｜')[0].isdecimal()}
    assert set(SPECS) == set(dynamic) - blocked
    assert len(SPECS) == 47
    for key, spec in SPECS.items():
        line, original = dynamic[key]
        assert tuple(spec[k] for k in ('source', 'target', 'relation', 'condition')) in static
        assert (line, original['source'], original['target'], original['type'], original['condition']) == (
            spec['line'], spec['source'], spec['target'], spec['relation'], spec['condition'] + '；且当前故事明确采用该静态关系')
        assert tuple(original['valid_types']) == spec['valid_types']
        assert all(spec[k] for k in ('needs', 'operation', 'check', 'consumers'))
        assert spec['status'] == 'conditional'
        assert set(spec['consumers']) <= {'static_relations', 'plot_design', 'event_design', 'action_design', 'scene_design'}
        assert not match(key, {'members': [person()]})
        assert not relevant(key, '来客递来一封信。')


def worker():
    return {'members': [person()], 'capabilities': [{
        'entity': 'guard', 'can_act': True, 'abilities': ['辨印验签', '骑射'],
        'basis': '沈砚通过渡吏任职验核，受权用辨印验签比对封蜡和岸亭回执。',
        'limits': ['没有岸亭回执时不得单独签放，须扣船复验。']}]}


def port_rule():
    return world('港务官持双印令授权临川渡放行货船，渡吏须比对闸簿封蜡和岸亭回执，验印后才可开闸。',
                 '缺一枚印时，渡吏须拒绝放行。')


def test_job_requires_its_own_world_duty_and_the_actors_usable_skill():
    assert relevant('C00835', '渡吏接到授权后要验签。')
    assert 'plot_design' in SPECS['C00835']['consumers']
    row, = match('C00835', worker(), port_rule())
    assert row['member'] == 'guard'
    assert set(row['paths']) == {'/members/0/body/role', '/members/0/body/name', '/capabilities/0/basis', '/capabilities/0/abilities/0',
                                '/capabilities/0/limits/0'}
    assert set(row['upstream_refs']) == {'input:world_design:/members/0/body/rule', 'input:world_design:/members/0/body/limits'}
    assert not match('C00835', worker())
    assert not match('C00835', worker(), world('库吏须比对闸簿封蜡和岸亭回执。', '缺印不得签放。'))
    assert not match('C00835', worker(), world('渡吏无需比对闸簿封蜡，工头须比对岸亭回执。', '缺印不得签放。'))
    assert not match('C00835', worker(), world('渡吏须比对闸簿封蜡。', '限制待确认'))
    for field, value in [('abilities', ['骑射']), ('basis', '在北山随师习武。'), ('entity', '库吏')]:
        draft = worker()
        draft['capabilities'][0][field] = value
        assert not match('C00835', draft, port_rule())


def test_existing_approved_person_is_used_only_with_actual_evidence_in_this_stage():
    draft = worker()
    existing = draft['members'].pop()
    context = {'approved_cards': [{'card_id': 'guard', 'kind': 'character', 'body': existing['body']}]}
    row, = match('C00835', draft, port_rule(), context)
    assert row['member'] == 'guard' and 'approved:guard:/body/role' in row['upstream_refs']
    assert '/capabilities/0/abilities/0' in row['paths']
    draft['capabilities'] = []
    assert not match('C00835', draft, port_rule(), context)


def test_unrelated_state_and_another_characters_state_cannot_supply_initial_design():
    draft = {'members': [person(behavior='遇警钟便停止翻账，寻找最近的出口。'),
                         person('other', name='云宜', behavior='受压时先喊巡卫。')],
             'states': [{'entity': 'guard', 'status': 'candidate', 'state': {'伤/势': '右腕骨折，无法提灯'}},
                        {'entity': 'other', 'status': 'candidate', 'state': {'心情': '听见鼓声时分神'}},
                        ]}
    physical, = match('C00462', draft)
    mental, = match('C00463', draft)
    assert (physical['member'], mental['member']) == ('guard', 'other')
    assert '/states/0/state/伤~1势' in physical['paths']
    assert '/states/1/state/心情' in mental['paths']
    draft['states'][0].update(status='rejected')
    assert not match('C00462', draft)


def test_deep_need_and_current_goal_have_to_be_distinct_fields_of_one_person():
    draft = {'members': [person(need='洗清旧案冤屈'), person('other', want='抢先调出巡检记录')]}
    assert not match('C00275', draft)
    body = draft['members'][0]['body']
    body['want'] = body['need']
    assert not match('C00275', draft)
    body['want'] = '天亮前调出当年巡检记录'
    row, = match('C00275', draft)
    assert set(row['paths']) == {'/members/0/body/need', '/members/0/body/want', '/members/0/body/name'}


def test_commitment_to_named_relative_must_wait_for_an_established_relationship():
    draft = {'members': [person(relationship='沈砚答应在洪水退前接回小青。', want='护送小青上岸。'),
                         person('sister', name='小青'), person('other', name='云宜')]}
    relation = {'source': 'guard', 'target': 'sister', 'relation': '同胞姐弟', 'condition': '庄簿和两人的出生证均已核实。'}
    def relation_stage(**updates):
        return {'static_relations': record('static_relations', {'relations': [{**relation, **updates}]})}
    assert not match('C01153', draft)
    row, = match('C01153', draft, relation_stage())
    assert row['member'] == 'guard'
    assert set(row['upstream_refs']) >= {'input:static_relations:/relations/0/condition',
           'input:static_relations:/relations/0/target', 'input:character_design:/members/1/body/name'}
    twin = deepcopy(draft)
    twin['members'][2]['body']['name'] = '小青'
    assert not match('C01153', twin, relation_stage())
    for updates in ({'target': 'other'}, {'source': 'sister'}, {'relation': '合作'},
                    {'relation': '非亲缘'}, {'condition': '据说是亲生姐弟'}, {'condition': '两人不是亲生姐弟'}):
        assert not match('C01153', draft, relation_stage(**updates))
    draft['members'][0]['body']['relationship'] = '他认识小青。沈砚答应照顾云宜。'
    assert not match('C01153', draft, relation_stage())


def test_talent_and_energy_gates_require_the_corresponding_frozen_world_mechanism():
    draft = worker()
    cap = draft['capabilities'][0]
    cap.update(abilities=['感知灵能余波'], basis='灵能余波来自石室，天赋等级甲等，可打开石门。', limits=['隔水即失效'])
    rule = world('石室残留的灵能可由持镜者感知。', '隔水镜面即失效')
    assert match('C00127', draft, rule)
    assert not match('C00041', draft, rule)
    rule = world('天赋等级决定能打开哪一层石门。', '损坏的石门失去测量能力')
    assert match('C00041', draft, rule)
    assert not match('C00127', draft, rule)
    rule['world_design']['products']['members'][0]['body']['rule'] = '事后改写'
    with pytest.raises(ValueError, match='hash mismatch'):
        match('C00127', draft, rule)


def designed(body, *, ability='', basis='', limit='', state=None):
    product = {'members': [person(**body)]}
    if ability:
        product['capabilities'] = [{'entity': 'guard', 'can_act': True, 'abilities': [ability],
                                    'basis': basis, 'limits': [limit]}]
    if state:
        product['states'] = [{'entity': 'guard', 'status': 'candidate', 'state': state}]
    return product


def cases():
    # Each small project has a different frozen design and a specific downstream use.
    selected = {'type_selection': record('type_selection', {'selection': [
        {'id': 'mystery', 'label': '悬疑', 'basis': '全书通过交叉印证证言查明失船去向。'}]})}
    yield ('C00022 C00023 C00269 C00270',
           designed({'role': '重要配角与证人', 'relationship': '替主角保存轮班记录',
                     'scene_function': '在悬疑查案中以轮班记录推翻第一份证词。',
                     'independent_goal': '先救回被船主扣押的妹妹。'}), selected)
    yield ('C00158', designed({'role': '查案人的对手', 'independent_goal': '夺回自己的船契',
                              'core_conflict': '公开船契会暴露自己串换证词。'},
                             ability='调取轮班船簿', basis='本人负责港务登记。', limit='不能调阅外港船簿。'), {})
    yield ('C00041 C00044 C00193 C00194 C00206 C00209',
           designed({'background': '在石室训练时遭遇天赋瓶颈，换到山脚后重新测过。',
                     'change_conditions': '石镜重铸后，允许再尝试突破瓶颈。'},
                    ability='吸收石镜中的能量', basis='石镜实测天赋等级乙等，每刻吸收两缕灵气。',
                    limit='当前上限是四缕，镜面光熄后不能继续操作。'),
           world('石镜通过天赋品质评定等级，每个等级有独立的吸收速度。'
                 '石镜天赋等级限制成长上限，天赋瓶颈也可能因训练环境出现。石镜术法操作上限可在重铸后提升。',
                 '石镜在雨中没有读数，不能用于判级。'))
    yield ('C00053 C00069 C00205 C00460',
           designed({}, ability='吸收游离灵气并转化为储备',
                    basis='石镜吸收游离态灵气，每刻能吸收两缕，进入储备的比例为六成。',
                    limit='伤后每刻至多容纳一缕。', state={'灵力储备': '封镜前剩余十二缕'}),
           world('石镜从外界吸收游离态灵气。石镜转化灵气时按六成比例进入储备。灵气储备在闭镜时停止增加。',
                 '封镜后不能补充。'))
    yield ('C00127 C00461 C00876', designed({'background': '目前仍在石室的感知期。'},
           ability='学习辨认墙内的灵能震动', basis='在石室镜旁学习辨认能量的变化。',
           limit='离开镜座便不能辨识震源。'), world('石室内的灵能可被持镜人感知。感知期只可在石室练习辨识波峰。', '离座后镜面熄灭。'))
    yield ('C00275 C00291 C00292 C00457 C00459 C01521 C01527',
           designed({'need': '始终想让遇难船工得到公道。', 'want': '取回案发当夜的船契。',
                     'strength': '他坚韧而坚定。', 'behavior': '见客时先放下记事笔，私下每天把船契末字重描一遍。'
                     '面对压力与劝阻仍坚持重抄船契，始终没有改口。',
                     'scene_function': '逼问时他露出沾墨的手指，审官才注意到契纸。'}), {})
    yield ('C00345 C00347 C00451',
           designed({'role': '公开身份是港务官', 'background': '隐藏身份为旧案证人。被动身份是死者遗产的受托人。'
                     '袖口的徽记来自当年验船队。', 'boundaries': '码头众人只知其公开身份，可见徽记，港务官有权查阅船簿。'}), {})
    yield ('C00462 C00463', designed({'behavior': '警钟响起时先寻出口，右手不能提灯。'},
           state={'腕部': '右腕骨折', '情绪': '听见警钟时焦虑'}), {})
    yield ('C00649 C00734', designed({'need': '她立志晋升为渡头的调度官。',
           'background': '升迁资格要有两次成功调船的记录。'}), world('渡头晋升资格要求两次成功调船。', '大潮期间暂停考核。'))
    yield ('C00655 C01573 C01585', designed({'relationship': '她依照看守契约，亲口答应老船工把船簿送回。',
           'want': '承担送达船簿的责任', 'need': '她自认欠老船工一笔人情，想承担这份责任。',
           'behavior': '收工后她仍亲自把湿透的船簿放入油布袋。'}), {})
    yield ('C00726 C01568', designed({'role': '军籍渡吏', 'background': '军籍随役期间亲历船工因身份被拒载。',
           'boundaries': '持军籍文牒有权领取渡资。', 'need': '让拒载和扣款都有公平的复核机会。'}),
           world('军籍允许领取渡资并进入外港。', '跨府后须重新登记。'))
    yield ('C00787 C00790 C00793',
           designed({'role': '青羽族人', 'background': '青羽族群的天赋在初次换羽后才显现，离山后须登记居留。',
                     'boundaries': '持居留印才有权进入南市。'}, ability='逆风滑翔',
                    basis='她是青羽族人，天赋等级乙，成年翼能承受额外负荷。', limit='雨天负荷上限三斤。'),
           world('青羽族人的族群天赋与换羽相关。青羽族人耐受的负荷由翼展决定。青羽族人迁入市镇要登记族籍。', '幼羽不能负重。'))
    yield ('C00804', designed({'background': '她的外壳由旧船铁片铆成。'}, ability='抬起石闸',
           basis='外壳有三列支架分担负荷。', limit='负荷超过石臼重量时铆眼开裂。'),
           world('铁片外壳承受负荷的能力受铆接结构限制。', '锈蚀后不得按满额提闸。'))
    yield ('C00830 C00832 C00835', designed({'role': '验印渡吏', 'background': '沈砚经港务官任命才领到朱印。',
           'boundaries': '持印时获准查阅闸簿。'}, ability='辨印验签', basis='渡吏用辨印验签比对封蜡和岸亭回执。',
           limit='没有回执须扣船复验。'), port_rule())
    kin = designed({'relationship': '沈砚答应在洪水退前接回小青。', 'want': '护送小青上岸。'})
    kin['members'].append(person('sister', name='小青'))
    edges = {'relations': [{'source': 'guard', 'target': 'sister', 'relation': '同胞姐弟', 'condition': '两人经户籍证实属同一父母。'}]}
    yield ('C01153', kin, {'static_relations': record('static_relations', edges)})
    yield ('C01532', designed({'strength': '他有长期守夜练成的意志。',
           'behavior': '面对压力先稳住呼吸再复诵船号。', 'change_conditions': '一夜休息才能恢复守夜时长。'}),
           world('巡防院以守夜时长分级记录意志承受能力。', '伤病时不得按常态折算。'))
    yield ('C01566', designed({'core_conflict': '如何在紧急时维持公正又善待无辜者。', 'want': '救助失去小船的证人。',
           'behavior': '她把自己的船位让给被拒载的证人。'}), {})


_CASES = {key: (draft, stages) for keys, draft, stages in cases() for key in keys.split()}


@pytest.mark.parametrize('key', sorted(SPECS))
def test_each_eligible_edge_can_reach_verifiable_project_fields(key):
    draft, stages = _CASES[key]
    result = match(key, draft, stages)
    assert {r['member'] for r in result} == {'guard'}
    if not stages:
        return
    if key in {'C00023', 'C00269', 'C00270'}:
        return  # These three depend on a supporting character's design inside this one product.
    assert all(r['upstream_refs'] for r in result)
    assert not match(key, draft)


def _book_delivery():
    pins = {'owner': 'character_design', 'source': {'id': 'dynamic-stage-C00835'}, 'static': {'id': 'static-job'},
            'basis_stage': 'character_design', 'valid_types': ['悬疑']}
    context = {'design_network_policy': POLICY, 'design_network_catalog': {'C00835': pins},
               'network_type_scope': {'mystery': ['悬疑']}, 'scope': 'book'}
    product = worker()
    stages = {'character_design': record('character_design', product), **port_rule()}
    plot_row, = design_network.candidates('plot_design', stages, context)
    direction = {'title': '封蜡', 'conflict': '守闸人发现辨印验签所需的岸亭回执被调换。',
                 'consequence': '沈砚扣船，收回换班关印。'}
    selected = record('plot_design', {
        'directions': [direction], '_network_design_uses': [{'id': plot_row['id'], 'operation': '扣船复核错印',
                                                             'output_refs': ['/directions/0/conflict']}]})
    selected['network_design_candidates'] = [plot_row]
    # Planning publishes members using the proposal prefix, so the next job sees card ID rather than "guard".
    person_pin = {'card_id': 'plan-001-guard', 'version': 1}
    world_pin = {'card_id': 'plan-001-port', 'version': 1}
    parent = {'selected_direction': direction, 'stages': [selected]}
    handed = design_network.inherited(parent, {'guard': person_pin, 'rule': world_pin})
    assert len(handed) == 1 and handed[0]['card'] == person_pin
    cap = deepcopy(product['capabilities'][0])
    cap['entity'] = person_pin['card_id']
    current = {'character_design': record('character_design', {'members': [], 'capabilities': [cap]}),
               'world_design': record('world_design', {'members': []})}
    for stage, field in [('plot_design', 'directions'), ('event_design', 'candidates'), ('action_design', 'candidates')]:
        current[stage] = record(stage, {field: []})
    approvals = [{**person_pin, 'kind': 'character', 'body': deepcopy(product['members'][0]['body'])},
                 {**world_pin, 'kind': 'world', 'body': deepcopy(stages['world_design']['products']['members'][0]['body'])}]
    return current, {**context, 'scope': 'chapter', 'approved_cards': approvals, 'parent_design_network': handed}


@pytest.mark.parametrize('stage', ['plot_design', 'action_design', 'scene_design'])
def test_book_key_and_approved_character_id_rebind_to_current_fields(stage):
    stages, context = _book_delivery()
    candidate, = design_network.candidates(stage, stages, context)
    assert candidate['member'] == 'plan-001-guard'
    assert candidate['required'] == (stage in ('plot_design', 'scene_design'))
    assert {e['ref'] for e in candidate['evidence']} >= {'approved:plan-001-guard:/body/name',
           'approved:plan-001-guard:/body/role', 'approved:plan-001-port:/body/rule', 'approved:plan-001-port:/body/limits',
           'input:character_design:/capabilities/0/abilities/0', 'input:character_design:/capabilities/0/limits/0'}
    assert candidate['approved'] == [{'card_id': 'plan-001-guard', 'version': 1}, {'card_id': 'plan-001-port', 'version': 1}]
    if stage != 'action_design':
        assert {d['path'] for d in candidate['deliveries']} == {'/directions/0/conflict'}


@pytest.mark.parametrize('change', ['reassigned', 'role', 'skill', 'can_act', 'basis', 'limit', 'world', 'world_limit',
                                    'new_world', 'different_local_person', 'missing_local_capability'])
def test_approved_project_changes_never_reuse_the_old_book_obligation(change):
    stages, context = _book_delivery()
    current = deepcopy(stages['character_design']['products'])
    cap = current['capabilities'][0]
    person_card, world_card = context['approved_cards']
    if change == 'reassigned':
        cap['entity'] = 'another-approved-person'
    elif change == 'role':
        person_card['body']['role'] = '后山药医'
        person_card['version'] = 2
    elif change == 'skill':
        cap['abilities'] = ['骑射']
    elif change == 'can_act':
        cap['can_act'] = False
    elif change == 'basis':
        cap['basis'] = '渡吏在换班验核后，用辨印验签独立比对岸亭回执。'
    elif change == 'limit':
        cap['limits'] = ['即使拿到岸亭回执，现任渡吏也须等潮水退后才能放行。']
    elif change == 'world':
        world_card['body']['rule'] = '工头须核对岸亭回执，渡吏只负责摆船。'
        world_card['version'] = 2
    elif change == 'world_limit':
        world_card['body']['limits'] = '夜航总须在岸亭复验后才可放行。'
        world_card['version'] = 2
    elif change == 'new_world':
        stages.update(world('看灯人须核验岸亭回执，新制渡吏只负责收桨。', '夜航时收起全部船桨。'))
    elif change == 'different_local_person':
        # The same local key, profession, training and limits cannot transfer an obligation to somebody else.
        current['members'] = [person(name='赵绮')]
        cap['entity'] = 'guard'
    else:
        current['capabilities'].clear()
    stages['character_design'] = record('character_design', current)
    for stage in ('plot_design', 'action_design', 'scene_design'):
        candidates = design_network.candidates(stage, stages, context)
        assert not any(r['required'] or r['deliveries'] for r in candidates)
        if change in {'limit', 'basis', 'world_limit', 'different_local_person'}:
            assert len(candidates) == 1
        else:
            assert candidates == []


def test_adopting_a_skill_in_an_action_requires_that_actual_actions_own_capability():
    stages, context = _book_delivery()
    row, = design_network.candidates('action_design', stages, context)
    action = {'candidates': [{'actor': row['member'], 'requires': ['辨印验签'], 'steps': [
                 {'response': '渡吏用辨印验签，翻过纸面查看背后的封蜡。'}]}],
              '_network_design_uses': [{'id': row['id'], 'operation': '用辨印验签比对封蜡，要求岸亭复核。',
                                        'output_refs': ['/candidates/0/steps/0/response']}]}
    design_network.validate('action_design', action, [row])
    action['candidates'][0]['requires'] = ['骑射']
    with pytest.raises(ValueError, match='所需能力'):
        design_network.validate('action_design', action, [row])


def test_plot_naming_another_person_must_identify_the_guard_whose_job_and_skill_it_uses():
    stages, context = _book_delivery()
    context['approved_cards'].append({'card_id': 'plan-001-sailor', 'version': 1, 'kind': 'character',
                                      'body': {'name': '梁亭', 'role': '船工'}})
    row, = design_network.candidates('plot_design', stages, context)
    plot = {'directions': [{'choice': '沈砚用辨印验签向船工梁亭核对封蜡背纸。'}],
            '_network_design_uses': [{'id': row['id'], 'operation': '沈砚核验船工交来的纸契与封蜡。',
                                      'output_refs': ['/directions/0/choice']}]}
    design_network.validate('plot_design', plot, [row], products=stages, context=context)
    plot['directions'][0]['choice'] = '梁亭用辨印验签核对封蜡背纸。'
    with pytest.raises(ValueError, match='另一人物'):
        design_network.validate('plot_design', plot, [row], products=stages, context=context)
