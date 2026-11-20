from copy import deepcopy

import pytest

from nw.materials.phase_routes import product_ref
from nw.materials.semantic_handoff import handoffs_for, validate_handoffs
from nw.materials.type_network import POLICY, RULES, availability, validate_adaptation_inputs, validate_type_network_use
from nw.task_models import content_sha256


AUTHOR_WORDS = {
    'reader_promise': '让读者凭前文的封条和家谱辨认作伪时间',
    'convention': '传统侦探说明由办案者在终段集中揭开',
    'departure': '让相关人物先用家谱作证而保留嫌疑',
    'innovation_scope': '只调整证人亮相顺序并保留实物证据',
    'fusion_method': '以档案调查串起亲密关系并写入同一主线',
    'fusion_roles': '悬疑承担档案追查言情承担保护亲友的取舍',
    'length': '作品篇幅定为三卷共二十四章',
    'commercial_strategy': '采用面向推理读者的爱情辅线融合策略',
    'fusion_measure': '按有效场计算悬疑与感情的构成比例',
    'market_position': '面向重视证据闭环的都市推理连载读者',
    'market_check': '用试读者能否解释两条关键证据衡量易读性',
}


def _stage(stage, products):
    return {'stage': stage, 'task_id': 'record-' + stage, 'sha256': content_sha256(products), 'products': products}


def _case(key='C00077'):
    fields = RULES[key]
    brief = '\n'.join(AUTHOR_WORDS[field] for field in fields)
    evidence = {field: {'ref': 'brief:/text', 'quote': AUTHOR_WORDS[field]} for field in fields}
    selection = {'selection': [{'id': 'G1', 'label': '悬疑', 'basis': '作者选择悬疑查证作为主要类型'},
                               {'id': 'G2', 'label': '言情', 'basis': '作者明定两位证人的亲密关系'}],
                 'concepts': [], 'boundaries': [], 'adaptation_inputs': evidence}
    products = {'type_selection': _stage('type_selection', selection)}
    pin = {'static_id': 'edge', 'source': {'id': 'edge', 'profile': 'static_relation', 'sha256': 'content',
                                      'file_sha256': 'file', 'path': '原件/静态网络.txt'},
           'edge': {'source': '源', 'target': '目的', 'type': '转化', 'condition': '实际条件'}}
    context = {'type_network_policy': POLICY, 'scope': 'book', 'brief': {'text': brief, 'constraints': ''},
               'network_type_scope': {'G1': ['悬疑'], 'G2': ['言情']},
               'type_network_families': {'G1': 'G1', 'G2': 'G2'}, 'type_network_bases': {'dynamic': pin}}
    source = {'source': {'key': key, 'id': 'dynamic'}, 'related_sources': ['edge']}
    raw = {**pin['edge'], 'id': key, 'generated_from_static': True,
           'condition': '实际条件；且当前故事明确采用该静态关系', 'valid_types': ['悬疑', '言情']}
    return source, raw, products, context


def _adopt(key='C00077'):
    source, raw, products, context = _case(key)
    ready, missing = availability(key, raw['valid_types'], products, context)
    assert not missing
    target = ready['output']
    value = {'adaptations': [{'id': 'actual', 'type_refs': ready['type_ids'], 'limits': [],
                              'parameters': {'clue': '用不同笔迹将两份家谱串联'}}],
             'boundaries': ['本案保留证据闭环并改变证人提前出场的顺序'], 'focuses': []}
    value['_uses'] = [{'source_id': 'dynamic', 'output_refs': ['adaptation:actual' if target == 'adaptations' else 'boundaries']}]
    value['_criteria'] = [{'source_id': 'dynamic', 'contract_sha256': 'fixture', 'clauses': [
        {'id': 'first-clause', 'applicability': 'applies', 'input_refs': [*ready['type_refs'].values(), *ready['inputs'].values()],
         'consumer': 'plot_design', 'output_refs': ['/adaptations/0/parameters/clue' if target == 'adaptations' else '/boundaries/0']}
    ]}]
    return source, raw, value, products, context


@pytest.mark.parametrize('key', RULES)
def test_each_source_category_needs_actual_premises_and_exact_outputs(key):
    source, raw, value, products, context = _adopt(key)
    validate_type_network_use(source, raw, value, products, context)
    selection = products['type_selection']['products']
    evidence = deepcopy(selection['adaptation_inputs'])
    for field in RULES[key]:
        selection['adaptation_inputs'] = {k: v for k, v in evidence.items() if k != field}
        products['type_selection'] = _stage('type_selection', selection)
        ready, missing = availability(key, raw['valid_types'], products, context)
        assert ready is None and len(missing) == 1


@pytest.mark.parametrize(('field', 'quote', 'text'), [
    ('commercial_strategy', '采用商业叙事策略', '作者不采用商业叙事策略。'),
    ('fusion_method', '采用副线并入主线', '是否采用副线并入主线尚未确认。'),
    ('market_position', '市场定位为都市悬疑连载', '市场定位待定，市场定位为都市悬疑连载只是示例。'),
    ('reader_promise', '连载每章以硬线索推进', '读者承诺暂无。'),
    ('reader_promise', 'genre: GENRE_XUANYI', '实际构想\n\n作者偏好（不代替设计步骤与冻结产物）：\ngenre: GENRE_XUANYI'),
    ('length', '计划另行看情况', '篇幅计划另行看情况。'),
])
def test_quote_must_come_from_actual_affirmative_author_input(field, quote, text):
    with pytest.raises(ValueError, match='actual affirmative author quotation'):
        validate_adaptation_inputs({'adaptation_inputs': {field: {'ref': 'brief:/text', 'quote': quote}}}, {},
                                   {'type_network_policy': POLICY, 'brief': {'text': text}})


@pytest.mark.parametrize(('field', 'text'), [
    ('market_position', '主角名叫陆景，住在老车站北面'),
    ('commercial_strategy', AUTHOR_WORDS['market_position']),
    ('fusion_measure', AUTHOR_WORDS['fusion_method']),
    ('market_check', AUTHOR_WORDS['market_position']),
    ('departure', AUTHOR_WORDS['convention']),
    ('fusion_roles', '作品的主线是重新寻找二十年前走失的孩子'),
    ('reader_promise', '题材确定为推理向现代悬疑作品'),
    ('reader_promise', '主角向母亲承诺会在第二天带回旧信'),
])
def test_exact_but_unrelated_author_words_do_not_prove_another_role(field, text):
    with pytest.raises(ValueError, match='supports this specific role'):
        validate_adaptation_inputs({'adaptation_inputs': {field: {'ref': 'brief:/text', 'quote': text}}}, {},
                                   {'type_network_policy': POLICY, 'brief': {'text': text}})


def test_dedicated_approved_reader_promise_has_its_role_without_a_literal_label():
    phrase = '每处伏笔都提供可回查的物证'
    context = {'type_network_policy': POLICY, 'approved_cards': [
        {'card_id': 'approved-plot', 'kind': 'plot', 'body': {'reader_promise': phrase}}]}
    evidence = {'ref': 'approved:approved-plot:/body/reader_promise', 'quote': phrase}
    validate_adaptation_inputs({'adaptation_inputs': {'reader_promise': evidence}}, {}, context)
    with pytest.raises(ValueError, match='supports this specific role'):
        validate_adaptation_inputs({'adaptation_inputs': {'market_check': evidence}}, {}, context)


def test_author_can_state_a_promise_before_its_rejected_alternative():
    phrase = '读者可以依公开证据复盘案情'
    message = phrase + '，而不是靠末尾临时揭晓推理。'
    context = {'type_network_policy': POLICY, 'brief': {'constraints': message}}
    adaptation = {'reader_promise': {'ref': 'brief:/constraints', 'quote': phrase}}
    validate_adaptation_inputs({'adaptation_inputs': adaptation}, {}, context)
    adaptation['reader_promise']['quote'] = '靠末尾临时揭晓推理'
    with pytest.raises(ValueError, match='actual affirmative author quotation'):
        validate_adaptation_inputs({'adaptation_inputs': adaptation}, {}, context)


def test_length_can_use_exact_existing_wizard_value_and_nothing_else_from_its_tail():
    text = ('实际构想\n\n作者偏好（不代替设计步骤与冻结产物）：\ngenre: GENRE_XUANYI'
            '\n\n立项参数：\n{"chapter_count":36,"target_words":160000}')
    context = {'type_network_policy': POLICY, 'brief': {'text': text}}
    evidence = {'ref': 'brief:/text', 'quote': '"target_words":160000'}
    validate_adaptation_inputs({'adaptation_inputs': {'length': evidence}}, {}, context)
    with pytest.raises(ValueError, match='actual affirmative author quotation'):
        validate_adaptation_inputs({'adaptation_inputs': {'reader_promise': evidence}}, {}, context)
    with pytest.raises(ValueError, match='actual affirmative author quotation'):
        validate_adaptation_inputs({'adaptation_inputs': {'length': {**evidence, 'quote': '"target_words":16000'}}}, {}, context)


def test_ready_input_requires_current_approved_card_and_valid_frozen_selection():
    _, raw, products, context = _case()
    quote = AUTHOR_WORDS['reader_promise']
    selection = products['type_selection']['products']
    selection['adaptation_inputs']['reader_promise']['ref'] = 'approved:promise:/body/reader_promise'
    with pytest.raises(ValueError, match='upstream product hash mismatch'):
        availability('C00077', raw['valid_types'], products, context)
    products['type_selection'] = _stage('type_selection', selection)
    with pytest.raises(ValueError, match='approved brief or plot'):
        availability('C00077', raw['valid_types'], products, context)
    context['approved_cards'] = [{'card_id': 'promise', 'kind': 'plot', 'body': {'reader_promise': quote}}]
    ready, missing = availability('C00077', raw['valid_types'], products, context)
    assert ready['inputs'] == {'reader_promise': 'input:type_selection:/adaptation_inputs/reader_promise/quote'}
    assert not missing


def test_subtype_does_not_supply_a_second_independent_genre_and_unpermitted_type_stays_out():
    _, raw, products, context = _case('C00085')
    context['type_network_families']['G2'] = 'G1'
    ready, missing = availability('C00085', raw['valid_types'], products, context)
    assert ready is None and '独立主类型' in missing[0]
    context['type_network_families']['G2'] = 'G2'
    ready, missing = availability('C00085', ['悬疑'], products, context)
    assert ready is None and '独立主类型' in missing[0]


@pytest.mark.parametrize(('defect', 'message'), [
    ('wrong_edge', 'unique pinned original static edge'),
    ('wrong_condition', 'unique pinned original static edge'),
    ('omitted_quote_input', 'omitted a required author premise'),
    ('missing_type_input', 'cite its actual selected type'),
    ('wrong_type', 'adaptation row must use and cite'),
    ('broad_output', 'field of the adaptation'),
    ('other_output', 'field of the adaptation'),
    ('only_limit', 'every adopted adaptation needs an actual parameter'),
    ('unavailable_consumer', 'later stage in scope'),
])
def test_rule_rejects_stale_basis_wrong_input_only_metadata_or_unreachable_output(defect, message):
    source, raw, value, products, context = _adopt()
    clause = value['_criteria'][0]['clauses'][0]
    if defect == 'wrong_edge':
        source['related_sources'] = ['other']
    if defect == 'wrong_condition':
        raw['condition'] = '偷换的条件；且当前故事明确采用该静态关系'
    if defect == 'omitted_quote_input':
        clause['input_refs'].pop()
    if defect == 'missing_type_input':
        clause['input_refs'] = [clause['input_refs'][-1]]
    if defect == 'wrong_type':
        value['adaptations'][0]['type_refs'] = ['G1']
    if defect == 'broad_output':
        clause['output_refs'] = ['/adaptations/0/parameters']
    if defect == 'other_output':
        value['adaptations'].append({'id': 'other', 'type_refs': ['G1', 'G2'], 'limits': [],
                                    'parameters': {'clue': '独立的错误适配'}})
        clause['output_refs'] = ['/adaptations/1/parameters/clue']
    if defect == 'only_limit':
        value['adaptations'][0]['limits'] = ['不可让证人预先说出全部实情']
        clause['output_refs'] = ['/adaptations/0/limits/0']
    if defect == 'unavailable_consumer':
        clause['consumer'] = 'scene_design'
    with pytest.raises(ValueError, match=message):
        validate_type_network_use(source, raw, value, products, context)


def test_adoption_delivers_concrete_parameter_and_needs_real_plot_receipt():
    source, raw, value, products, context = _adopt()
    validate_type_network_use(source, raw, value, products, context)
    products['type_adaptation'] = _stage('type_adaptation', value)
    [row] = handoffs_for('plot_design', products)
    assert row['origin'] == product_ref(products['type_adaptation'])
    assert row['actual_inputs'] == [{'path': '/adaptations/0/parameters/clue', 'value': '用不同笔迹将两份家谱串联'}]
    downstream = {'directions': [{'choice': '比对两份家谱的笔迹并调查抄录先后'}]}
    with pytest.raises(ValueError, match='disappeared'):
        validate_handoffs('plot_design', downstream, products)
    downstream['_receipts'] = [{'id': row['id'], 'operation': '使用家谱笔迹设置反证和调查方向',
                                'output_refs': ['/directions/0/choice']}]
    validate_handoffs('plot_design', downstream, products)


def test_previous_plan_shape_does_not_create_new_authority():
    _, raw, products, context = _case()
    context.pop('type_network_policy')
    assert availability('C00077', raw['valid_types'], products, context) == (None, [])
    with pytest.raises(ValueError, match='no frozen type network policy'):
        validate_adaptation_inputs(products['type_selection']['products'], {}, context)
