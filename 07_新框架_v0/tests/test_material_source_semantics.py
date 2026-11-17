"""Source-derived clauses remain obligations, never proof of literary effects."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json

import pytest

from nw.task_models import content_sha256


def compiler():
    # A missing compiler is an assertion failure during the initial red run.
    try:
        return importlib.import_module('nw.materials.source_semantics')
    except ModuleNotFoundError:
        pytest.fail('Source semantics compiler is not implemented')


def snapshot(original, *, key='fixture', profile='metadata'):
    text = json.dumps(original, ensure_ascii=False, separators=(',', ':')) if isinstance(original, (dict, list)) else original
    return {'source': {'id': 'source-fixture', 'key': key, 'profile': profile,
                       'path': '02_原版资料/原始资料/资料库.txt',
                       'file_sha256': 'file-pin', 'sha256': 'owner-pin'},
            'source_state': 'reference', 'original_text': text,
            'original_text_sha256': content_sha256(text),
            'application_layers': [], 'source_issues': {'missing': [], 'conflicts': []},
            'related_sources': []}


CONFLICT = {'confidence': 'high', 'evidence_type': 'template',
            'object_kind': '冲突类型适配_adapter',
            'preferred_conflicts': ['resource_conflict', 'power_conflict', 'capability_conflict'],
            'rule': '动作类型倾向物理冲突', 'schema_version': 'G-3C-1.0', 'source_refs': [],
            'stable_id': 'G3C_ADAPT_冲突类型适配_001', 'status': 'active',
            'type': 'action', 'violence_tendency': 'high'}
FORESHADOW = {'confidence': 'high', 'density': 'high', 'evidence_type': 'template',
             'object_kind': '伏笔类型适配_adapter', 'payoff_pace': 'gradual',
             'rule': '悬疑类型提高伏笔密度，减少显性程度', 'schema_version': 'G-3C-1.0',
             'source_refs': [], 'stable_id': 'G3C_ADAPT_伏笔类型适配_001',
             'status': 'active', 'type': 'mystery', 'visibility': 'low'}


@pytest.mark.parametrize('original,expected', [(CONFLICT, 'resource_conflict'), (FORESHADOW, 'gradual')])
def test_metadata_adapters_keep_real_parameters_and_route_by_original_shape(original, expected):
    compiled = compiler().compile_semantics(snapshot(original), {'source_ref': {
        'fragment_key': '冲突类型适配.json', 'locator': '/adapters/0',
        'byte_start': 3419, 'byte_end': 3913, 'line_start': 94, 'line_end': 110}})
    assert compiled['disposition'] == 'project_method'
    assert 'type_adaptation' in compiled['stages']
    values = [item['value'] for item in compiled['obligations']]
    assert original['rule'] in values and expected in values
    assert 'G-3C-1.0' not in values and 'active' not in values
    rule = next(item for item in compiled['obligations'] if item['value'] == original['rule'])
    assert rule['check_mode'] == 'semantic_review'
    assert rule['locator'] == '/adapters/0/rule'
    assert rule['source_ref']['byte_start'] == 3419


def test_discovery_can_infer_adapter_stages_without_prior_profile_or_key():
    mod = compiler()
    assert 'type_adaptation' in mod.infer_stages(CONFLICT, 'metadata', 'unrelated-key')
    assert mod.infer_stages({'id': 'x', 'status': 'active', 'score': 1}, 'plot', '伏笔') == []


def test_action_bullets_are_separate_exact_text_obligations():
    text = ('### 2.3_角色动作\r\n【指令】\r\n\\*\\*动作写作规则\\*\\*：\r\n'
            '\\- 每个主要动作前应有动因\r\n'
            '\\- 动作序列必须完整，不能跳过中间状态\r\n'
            '\\- 动作在情绪变化时必须出现变化描写\r\n')
    result = compiler().compile_semantics(snapshot(text, profile='character'))
    operations = [o for o in result['obligations'] if o['kind'] == 'operation']
    for expected in ('每个主要动作前应有动因', '动作序列必须完整，不能跳过中间状态',
                     '动作在情绪变化时必须出现变化描写'):
        item = next(o for o in operations if o['value'] == expected)
        pin = item['source_ref']
        assert text[pin['text_start']:pin['text_end']] == expected
        assert item['check_mode'] == 'semantic_review'
    assert 'action_design' in result['stages']


def test_reader_and_foreshadow_checks_preserve_meaning_and_incomplete_definition():
    text = ('### 伏笔埋设\n【定义】伏笔的三种核心特征。\n'
            '【判定标准】首次引入的伏笔在后续2-10章中被揭示其真正含义\n'
            '【例外处理】在不需要伏笔埋设的场景中可不使用\n')
    result = compiler().compile_semantics(snapshot(text, key='板块45#伏笔埋设', profile='plot'))
    check = next(o for o in result['obligations'] if o['kind'] == 'check')
    assert check['value'] == '首次引入的伏笔在后续2-10章中被揭示其真正含义'
    assert any(o['kind'] == 'exception' for o in result['obligations'])
    assert result['source_issues']['compilation']
    assert result['disposition'] == 'project_method'  # The separate complete check remains readable.
    reader = compiler().compile_semantics(snapshot('【判定标准】读者情绪不能是一条直线'))
    assert reader['obligations'][0]['check_mode'] == 'semantic_review'
    assert 'plot_design' in reader['stages']


def test_network_navigation_is_not_an_adopted_project_relationship():
    original = {'source': '145.4_动作', 'target': '50.1_精确动词', 'type': '绑定',
                'condition': '动作需精确动词', 'priority': 1}
    result = compiler().compile_semantics(snapshot(original, profile='static_relation'))
    assert result['stages'] == ['static_relations', 'plot_design']
    assert next(o['value'] for o in result['obligations'] if o['kind'] == 'condition') == '动作需精确动词'
    assert not any('project_entity' in o['source_ref'] for o in result['obligations'])


def test_dynamic_conditions_and_actual_upstream_dependency_survive_compilation():
    original = {'id': 'C00001', 'source': '1.1_主角', 'target': '130_核心悬念', 'type': '绑定',
                'condition': '绑定主线；且当前故事明确采用该静态关系',
                'effect': '终点状态随起点状态更新', 'generated_from_static': True}
    source = snapshot(original, profile='dynamic_binding'); source['related_sources'] = ['actual-static-source-id']
    result = compiler().compile_semantics(source)
    assert result['stages'] == ['state_propagation']
    assert result['dependencies'] == ['actual-static-source-id']
    assert any(o['kind'] == 'condition' and '采用该静态关系' in o['value'] for o in result['obligations'])
    assert any(o['kind'] == 'effect' and o['check_mode'] == 'semantic_review' for o in result['obligations'])


@pytest.mark.parametrize('effect,stage', [('attention_shift', 'type_adaptation'),
                                         ('event_candidate', 'event_design'),
                                         ('candidate_action', 'action_design'),
                                         ('state_change', 'state_transition')])
def test_tdr_effect_shape_routes_without_promoting_candidate_to_fact(effect, stage):
    source = snapshot({'effect_id': 'candidate', 'effect_type': effect,
                       'description': '尚待项目选择的候选效果', 'status': 'template'})
    result = compiler().compile_semantics(source)
    assert stage in result['stages']
    assert all(o.get('status') != 'pass' for o in result['obligations'])


@pytest.mark.parametrize('row,operation,condition', [
    ('| A1.1 | 移动_步行_慢 | 缓慢步行 | 从容/疲惫 | 行动 |', '缓慢步行', '从容/疲惫'),
    ('| ID1.1 | 身份_职业_学徒 | 学徒身份 | 学习阶段 | 身份 | <br>', '学徒身份', '学习阶段'),
])
def test_anchor_row_retains_its_original_content_and_trigger(row, operation, condition):
    source = snapshot(row, profile='anchor')
    result = compiler().compile_semantics(source)
    assert result['stages'] == ['anchor_design']
    assert any(o['kind'] == 'operation' and o['value'] == operation for o in result['obligations'])
    assert any(o['kind'] == 'condition' and o['value'] == condition for o in result['obligations'])


def test_metadata_only_and_title_only_do_not_manufacture_method_obligations():
    for original in ({'id': 'only', 'status': 'active', 'score': 99, 'confidence': 'high'},
                     '### 伏笔读者动作状态变化'):
        result = compiler().compile_semantics(snapshot(original, profile='plot', key='45.1_伏笔'))
        assert result['disposition'] == 'navigation_only'
        assert result['obligations'] == []
        assert result['stages'] == []


def test_unlabelled_original_is_preserved_for_interpretation_not_profile_certified():
    text = '这段原文缺少可确认的操作角色，需要继续核读。'
    result = compiler().compile_semantics(snapshot(text, profile='world'))
    assert any(o['value'] == text for o in result['obligations'])
    assert result['disposition'] == 'project_method'
    assert result['source_issues']['compilation']


def test_application_guidance_only_contains_aligned_unrejected_fields_with_pins():
    source = snapshot('【指令】比较叙述句式、用词和叙述距离')
    raw = '{"safe":"比较叙述句式","unsafe":"触发角色身体信号"}'
    layer = {'source_ref': {'id': 'runtime-id', 'sha256': sha256(raw.encode()).hexdigest(), 'locator': '/运行层升级'},
             'text': raw,
             'aligned_fields': [{'field': 'safe', 'text': '比较叙述句式',
                                 'sha256': sha256('比较叙述句式'.encode()).hexdigest()},
                                {'field': 'unsafe', 'text': '触发角色身体信号',
                                 'sha256': sha256('触发角色身体信号'.encode()).hexdigest()}],
             'rejected_fields': [{'field': 'unsafe', 'reason': '改变原义'}]}
    source['application_layers'] = [layer]
    result = compiler().compile_semantics(source)
    guidance = result['application_guidance'][0]
    assert guidance['source_ref']['id'] == 'runtime-id'
    assert [x['field'] for x in guidance['aligned_fields']] == ['safe']
    assert '触发角色身体信号' not in json.dumps(guidance, ensure_ascii=False)
    assert all('身体信号' not in str(o['value']) for o in result['obligations'])
    assert guidance['rejected_fields'] == layer['rejected_fields']


def test_old_adjudication_definition_cannot_replace_original_and_hashes_are_sensitive():
    source = snapshot('【指令】比较叙述句式、用词和叙述距离')
    context = {'adjudication_contract': {'contract': {'definition': '触发角色身体信号'}}}
    first = compiler().compile_semantics(source, context)
    assert '身体信号' not in json.dumps(first['obligations'], ensure_ascii=False)
    assert first['sha256'] == content_sha256({k: v for k, v in first.items() if k != 'sha256'})
    changed = deepcopy(source); changed['source']['file_sha256'] = 'other-version'
    assert compiler().compile_semantics(changed, context)['sha256'] != first['sha256']
    changed = deepcopy(source); changed['original_text'] += '新增原文'
    with pytest.raises(ValueError, match='hash'):
        compiler().compile_semantics(changed, context)


def test_json_field_offsets_address_original_text_and_keep_nested_prohibitions():
    source = snapshot({'preconditions': ['实体存在', '状态变化已确认'],
                       'propagation_limits': {'max_depth': 3},
                       'forbidden_assumptions': ['不能自动生成completed事件']})
    result = compiler().compile_semantics(source)
    assert len([o for o in result['obligations'] if o['kind'] == 'condition']) == 2
    limit = next(o for o in result['obligations'] if o['locator'] == '/propagation_limits/max_depth')
    assert limit['value'] == 3 and limit['check_mode'] == 'deterministic'
    prohibition = next(o for o in result['obligations'] if o['kind'] == 'prohibition')
    assert prohibition['value'] == '不能自动生成completed事件'
    pin = prohibition['source_ref']
    assert json.loads(source['original_text'][pin['text_start']:pin['text_end']]) == prohibition['value']


def test_actual_mixed_delimiters_keep_selection_and_conversion_in_binding_stage():
    conversion = ('【定义】各板块转换包括伏笔埋设和读者情绪曲线。\n'
                  '【指令]根据当前场景提取参数，填写参数→正文表现的映射并逐项核验。\n')
    selection = ('【定义]第一层确定功能定位，第二层匹配板块，第三层精确到子项级别。\n'
                 '【指令]三层筛选法：第一层确定功能定位→第二层匹配对应板块→第三层精确到子项级别。\n')
    for text in (conversion, selection):
        result = compiler().compile_semantics(snapshot(text))
        assert result['stages'] == ['bind_scope']
        assert any(o['kind'] == 'operation' for o in result['obligations'])
        assert all('【' not in o['value'] for o in result['obligations'])


def test_application_rejection_without_binding_identity_is_conservative():
    source = snapshot('【指令】比较叙述句式')
    raw = '{"unsafe":"触发身体信号"}'
    source['application_layers'] = [{
        'source_ref': {'id': 'runtime', 'sha256': sha256(raw.encode()).hexdigest()},
        'text': raw,
        'aligned_fields': [{'field': 'unsafe', 'text': '触发身体信号'}],
        'rejected_fields': [{'binding': 0, 'field': 'unsafe', 'reason': '改变原义'}]}]
    result = compiler().compile_semantics(source)
    assert result['application_guidance'][0]['aligned_fields'] == []


def test_changed_application_text_cannot_keep_an_old_exact_layer_hash():
    source = snapshot('【指令】比较叙述句式')
    source['application_layers'] = [{'source_ref': {'sha256': sha256(b'old').hexdigest()},
                                     'text': 'changed', 'aligned_fields': [], 'rejected_fields': []}]
    with pytest.raises(ValueError, match='hash'):
        compiler().compile_semantics(source)


def test_navigation_tags_do_not_infer_execution_from_their_keywords():
    result = compiler().compile_semantics(snapshot('【调用标签】#读者情绪_伏笔埋设'))
    assert result['obligations'] == [] and result['stages'] == []


def test_nested_effect_and_dependency_fields_keep_their_container_meaning():
    source = snapshot({'candidate_effects': [{'effect_id': 'e', 'description': '相关状态可能被传播影响'}],
                       'source_refs': [{'source': '静态网络.txt source_index', 'source_key': ['a', 'b']}]})
    result = compiler().compile_semantics(source)
    description = next(o for o in result['obligations'] if o['value'] == '相关状态可能被传播影响')
    dependency = next(o for o in result['obligations'] if o['value'] == '静态网络.txt source_index')
    assert description['kind'] == 'effect' and description['check_mode'] == 'semantic_review'
    assert dependency['kind'] == 'dependency'


def test_network_provenance_is_not_a_creative_requirement():
    source = snapshot({'source': '1.1_主角', 'target': '130_核心悬念', 'type': '绑定',
                       'condition': '本项目已采用对应静态关系', 'effect': '终点随起点变化',
                       'generated_from_static': True, 'field_source': {'condition': '静态网络对应记录'},
                       'normalized_source': '1.1_主角', 'normalized_target': '130_核心悬念',
                       'original_source': '1.1_主角', 'original_target': '130_核心悬念',
                       'source_layer': '未分类', 'target_layer': '未分类', 'needs_review': False,
                       'derivation_contract': 'NET-DYNAMIC-DERIVATION-CONTRACT-1.0'})
    result = compiler().compile_semantics(source)
    assert len(result['obligations']) == 6
    assert all('/field_source/' not in o['locator'] and '/normalized_' not in o['locator']
               for o in result['obligations'])


def test_unknown_field_does_not_block_separate_readable_original_method():
    source = snapshot({'rule': '先核对当前人物能力，再设计动作', 'uninterpreted_native_field': '原文尚待解释'})
    result = compiler().compile_semantics(source)
    assert result['disposition'] == 'project_method'
    assert any(o['value'] == '原文尚待解释' for o in result['obligations'])
    assert any(i['kind'] == 'unclassified_original_field' for i in result['source_issues']['compilation'])


def test_missing_enumeration_points_only_to_the_affected_original_obligation():
    source = snapshot('【定义】伏笔的三种核心特征。\n【判定标准】首次引入后2-10章揭示真正含义。')
    result = compiler().compile_semantics(source)
    issue = next(i for i in result['source_issues']['compilation'] if i['kind'] == 'incomplete_original_enumeration')
    definition = next(o for o in result['obligations'] if o['kind'] == 'definition')
    check = next(o for o in result['obligations'] if o['kind'] == 'check')
    assert issue['obligation_ids'] == [definition['id']]
    assert check['id'] not in issue['obligation_ids']
    assert result['disposition'] == 'project_method'


def test_real_aligned_profile_field_hash_keeps_original_trailing_newlines_and_byte_pin():
    source = snapshot('【指令】先比较当前类型承诺')
    text = '【读者期待】\r\n期待类型核心承诺持续兑现。'
    original_field = text + '\r\n\r\n'
    raw = 'HEAD\n' + original_field
    field_hash = sha256(original_field.encode()).hexdigest()
    source['application_layers'] = [{
        'source_ref': {'id': 'profile-owner', 'sha256': sha256(raw.encode()).hexdigest(),
                       'byte_start': 100, 'byte_end': 100+len(raw.encode()), 'line_start': 10},
        'text': raw, 'rejected_fields': [],
        'aligned_fields': [{'field': 'reader_expectation', 'source_id': 'original-field',
                            'text': text, 'sha256': field_hash}]}]
    result = compiler().compile_semantics(source)
    field = result['application_guidance'][0]['aligned_fields'][0]
    pin = field['source_ref']
    assert pin['id'] == 'original-field' and pin['sha256'] == field_hash
    assert pin['byte_start'] == 105 and pin['byte_end'] == 105+len(original_field.encode())
    assert raw[pin['text_start']:pin['text_end']] == original_field


@pytest.mark.parametrize('rule_kind', [{'type': 'string'}, ['TYPE_STATE_PROPAGATION']])
def test_schema_shaped_rule_kind_is_not_an_executable_rule_discriminator(rule_kind):
    assert compiler().infer_stages({'rule_kind': rule_kind}, 'type_transition') == []
