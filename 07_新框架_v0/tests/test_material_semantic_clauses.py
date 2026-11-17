"""Stage provenance and per-clause checks do not substitute for prose review."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import importlib
import json

import pytest

from nw.materials.source_semantics import compile_semantics
from nw.task_models import content_sha256


def module():
    try:
        return importlib.import_module('nw.materials.semantic_application')
    except ModuleNotFoundError:
        pytest.fail('Per-clause semantic application validation is not implemented')


def source(ident='method', original='【指令】主要动作前应有可信动因\n【判定标准】动作序列必须完整'):
    return {'source': {'id': ident, 'key': '2.3_角色动作', 'profile': 'character',
                       'sha256': 'original-owner-pin', 'file_sha256': 'original-file-pin'},
            'source_state': 'reference', 'original_text': original,
            'original_text_sha256': content_sha256(original), 'application_layers': [],
            'source_issues': {'missing': [], 'conflicts': []}, 'related_sources': []}


def record(stage, value):
    return {'stage': stage, 'task_id': 'isolated-'+stage, 'products': value,
            'sha256': content_sha256(value)}


def criterion(contract, output='/candidates/0/steps/0/action'):
    return {'source_id': contract['source_id'], 'contract_sha256': contract['sha256'],
            'clauses': [{'id': item['id'], 'applicability': 'applies',
                         'reason': '[FAKE] 本场调查需要完整动作链以解释人物选择',
                         'input_refs': ['brief:/text', 'input:character_design:/capabilities/0/can_act'],
                         'output_refs': [output], 'operation': '[FAKE] 依人物调查目标设计绕开铜丝的具体动作',
                         'observable': '[FAKE] 借灯看见铜丝后压低木片绕行',
                         'check': '[FAKE] 核对观察阻碍和改变动作之间的因果顺序',
                         'consumer': 'scene_design'} for item in contract['obligations']],
            'layer_application': {}}


def fixture():
    s = source(); contract = compile_semantics(s)
    upstream = {'character_design': record('character_design', {'capabilities': [
        {'entity': 'yan', 'can_act': True, 'abilities': ['移动木片']}], '_uses': []})}
    value = {'candidates': [{'id': 'action-a', 'actor': 'yan',
                            'action': '[FAKE] 压低木片绕过铜丝托起纸角',
                            'steps': [{'action': '[FAKE] 压低木片绕过铜丝托起纸角'}]}],
             '_uses': [{'source_id': 'method', 'operation': '[FAKE] 按原义形成实际动作链',
                        'output_refs': ['action:action-a']}], '_criteria': [criterion(contract)]}
    context = {'require_semantics': True, 'brief': {'text': '[FAKE] 调查封条且不可凭空获得能力'},
               'approved_cards': [], 'accepted_state': [],
               'allowed_input_stages': ['character_design'], 'semantic_contracts': [contract]}
    return s, contract, upstream, value, context


def validate(data):
    s, _, upstream, value, context = data
    return module().validate_semantic_applications('action_design', value, upstream, [s], context)


def test_legacy_without_criteria_is_not_forced_but_explicit_or_required_criteria_are():
    s, _, upstream, value, context = fixture()
    value.pop('_criteria'); context['require_semantics'] = False
    module().validate_semantic_applications('action_design', value, upstream, [s], context)
    context['require_semantics'] = True
    with pytest.raises(ValueError, match='semantic'):
        module().validate_semantic_applications('action_design', value, upstream, [s], context)
    context['require_semantics'] = False; value['_criteria'] = []
    with pytest.raises(ValueError, match='semantic'):
        module().validate_semantic_applications('action_design', value, upstream, [s], context)


def test_actual_clause_contract_input_and_output_paths_are_accepted_without_literary_pass():
    data = fixture(); before = deepcopy(data)
    assert validate(data) is None
    assert data == before


@pytest.mark.parametrize('defect', ['missing_clause', 'duplicate_clause', 'unknown_clause',
                                  'missing_source', 'duplicate_source', 'stale_contract', 'edited_contract'])
def test_missing_duplicated_or_changed_semantic_coverage_is_rejected(defect):
    data = fixture(); _, contract, _, value, _ = data; current = value['_criteria'][0]
    if defect == 'missing_clause': current['clauses'].pop()
    elif defect == 'duplicate_clause': current['clauses'].append(deepcopy(current['clauses'][0]))
    elif defect == 'unknown_clause': current['clauses'][0]['id'] = 'invented'
    elif defect == 'missing_source': value['_criteria'] = []
    elif defect == 'duplicate_source': value['_criteria'].append(deepcopy(current))
    elif defect == 'stale_contract': current['contract_sha256'] = 'old-hash'
    else: contract['obligations'][0]['value'] = 'silently changed original'
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


@pytest.mark.parametrize('reference', ['input:absent:/capabilities',
                                     'input:character_design:/capabilities/8',
                                     'input:character_design:/ref/sha256', 'brief:/missing'])
def test_input_refs_must_resolve_to_real_sent_values(reference):
    data = fixture(); data[3]['_criteria'][0]['clauses'][0]['input_refs'] = [reference]
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


def test_input_products_are_hash_checked_and_respect_actual_sent_stage_boundary():
    for defect in ('changed_product', 'undelivered_stage'):
        data = fixture()
        if defect == 'changed_product': data[2]['character_design']['products']['capabilities'][0]['can_act'] = False
        else: data[4]['allowed_input_stages'] = []
        with pytest.raises(ValueError, match='semantic'):
            validate(data)


@pytest.mark.parametrize('pointer', ['/_criteria/0/clauses/0/operation', '/_uses/0/operation',
                                   '/candidates/0/id', '/candidates/99', '/empty', '/label_only'])
def test_output_refs_cannot_be_missing_empty_identity_or_self_proof(pointer):
    data = fixture(); value = data[3]; value['empty'] = []; value['label_only'] = {'id': 'x', 'status': 'done'}
    value['_criteria'][0]['clauses'][0]['output_refs'] = [pointer]
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


@pytest.mark.parametrize('operation', ['read_original_source', '读取原文来源哈希并记录状态',
                                     '按原文要求逐条执行', '已应用已应用已应用'])
def test_metadata_readouts_and_generic_execution_labels_are_not_method_operations(operation):
    data = fixture(); data[3]['_criteria'][0]['clauses'][0]['operation'] = operation
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


def test_consumer_must_be_a_real_downstream_stage_or_independent_review():
    data = fixture(); data[3]['_criteria'][0]['clauses'][0]['consumer'] = 'character_design'
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


def test_approved_cards_and_current_fact_refs_preserve_holder_without_promoting_truth():
    data = fixture(); context = data[4]
    context['approved_cards'] = [{'card_id': 'yan', 'body': {'want': '[FAKE] 查清换印日期'}}]
    context['accepted_state'] = [{'entity_id': 'yan', 'claim': 'belief', 'holder': 'yan',
                                  'value': '[FAKE] 他怀疑封条曾被更换'}]
    data[3]['_criteria'][0]['clauses'][0]['input_refs'] = ['approved:yan:/body/want', 'fact:0:/value']
    validate(data)
    assert context['accepted_state'][0]['holder'] == 'yan'
    assert context['accepted_state'][0]['claim'] == 'belief'


def test_frozen_payload_contract_is_used_instead_of_recompiling_visible_projection():
    data = fixture(); s = data[0]
    s['original_text'] = '{"projected":"visible text with omitted empty fields"}'
    s['original_text_sha256'] = content_sha256(s['original_text'])
    validate(data)


def test_source_unresolved_only_names_explicit_compiler_issue_and_does_not_fill_missing_meaning():
    s = source(original='【定义】伏笔的三种核心特征。\n【判定标准】首次引入后2-10章揭示真正含义。')
    contract = compile_semantics(s); data = list(fixture()); data[0] = s; data[1] = contract
    data[4]['semantic_contracts'] = [contract]; data[3]['_criteria'] = [criterion(contract)]
    row = data[3]['_criteria'][0]['clauses'][0]
    row.update(applicability='source_unresolved', reason='incomplete_original_enumeration 原文未列出三特征，等待恢复',
               input_refs=[], output_refs=[], operation='', observable='', check='', consumer='review')
    validate(data)
    row['applicability'] = 'applies'; row['input_refs'] = ['brief:/text']; row['output_refs'] = ['/candidates/0/action']
    row.update(operation='[FAKE] 自己补造三条伏笔核心特征', observable='[FAKE] 按补造特征安排伏笔表现', check='[FAKE] 自行判定补造规则已经成立')
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


def test_qualification_alone_is_not_a_project_nonapplicability_reason():
    data = fixture(); row = data[3]['_criteria'][0]['clauses'][0]
    row.update(applicability='not_applicable', reason='template 来源资格尚为reference',
               input_refs=[], output_refs=[], operation='', observable='', check='')
    with pytest.raises(ValueError, match='semantic'):
        validate(data)
    row['reason'] = '[FAKE] 本场没有情绪转变，暂不要求相应动作变化'
    validate(data)


def add_layer(data):
    s = data[0]; raw = '{"safe":"比较实际动作顺序","unsafe":"触发身体信号作为所有叙事法的表现"}'
    s['application_layers'] = [{'source_ref': {'id': 'runtime', 'sha256': sha256(raw.encode()).hexdigest()},
        'text': raw, 'aligned_fields': [{'field': 'safe', 'text': '比较实际动作顺序'}],
        'rejected_fields': [{'field': 'unsafe', 'reason': '改变原义'}]}]
    contract = compile_semantics(s); data[4]['semantic_contracts'] = [contract]
    data[3]['_criteria'] = [criterion(contract)]
    return data


def layer_application():
    return {'trigger': '[FAKE] 当前人物为查旧印必须绕开可见铜丝',
            'operation': '[FAKE] 先观察铜丝方向再改用木片托起纸角',
            'result': '[FAKE] 旧印被露出同时留下纸角破损的代价',
            'verification': '[FAKE] 审稿引用观察改招和纸角破损的具体段落'}


def test_layer_application_is_required_and_copied_rejected_runtime_value_is_blocked():
    data = add_layer(list(fixture()))
    with pytest.raises(ValueError, match='semantic'):
        validate(data)
    data[3]['_criteria'][0]['layer_application'] = layer_application(); validate(data)
    data[3]['_criteria'][0]['layer_application']['operation'] = '触发身体信号作为所有叙事法的表现'
    with pytest.raises(ValueError, match='semantic'):
        validate(data)


def session_fixture(with_layer=False):
    data = add_layer(list(fixture())) if with_layer else list(fixture())
    if with_layer: data[3]['_criteria'][0]['layer_application'] = layer_application()
    s, _, upstream, value, context = data
    action = record('action_design', value)
    scene = record('scene_design', {'members': [{'key': 'scene-a', 'kind': 'scene',
        'body': {'pov': 'yan', 'allowed_disclosure': '[FAKE] 仅本场可见封条变化'}}],
        'selected_actions': [{'scene': 'scene-a', 'action': 'action-a'}], 'selected_events': [], '_uses': []})
    binding = record('bind_scope', {'_uses': [], 'method_guidance': [{'scene': 'scene-a',
        'source_ids': ['method'], 'observable': '[FAKE] 本场人物按已选动作查看封条',
        'check': '[FAKE] 核对观察与应对形成完整顺序'}]})
    return {'id': 'isolated-semantic-session', 'sources': [s], 'context': context,
            'stages': [*upstream.values(), action, scene, binding]}, data


def test_each_actual_original_clause_becomes_its_own_pinned_current_scene_check():
    session, data = session_fixture(); checks = module().make_semantic_checks(session, 'scene-a', {'yan': 'actual-yan'})
    original = data[4]['semantic_contracts'][0]['obligations']
    assert len(checks) == len(original)
    assert {c['source_contract']['obligations'][0]['id'] for c in checks} == {o['id'] for o in original}
    for check in checks:
        clause = check['source_contract']['obligations'][0]
        assert clause['kind'] in ('operation', 'check') and clause['ref']['sha256'] == 'original-owner-pin'
        assert check['binding']['source_scope'][clause['id']]['disposition'] == 'required'
        assert '压低木片' in check['binding']['observable'] and '/candidates/0/steps/0/action' in check['binding']['observable']
        assert check.get('status') != 'pass' and '原义' in check['evidence_required']
        assert check['method_sources'][0]['original_quotes'] == [clause['text']]


def test_unselected_future_action_is_not_forced_into_current_scene_checks():
    session, _ = session_fixture(); action = next(r for r in session['stages'] if r['stage'] == 'action_design')
    action['products']['candidates'].append({'id': 'future-action', 'action': '[FAKE] 下章离开药铺'})
    action['products']['_criteria'][0]['clauses'][1]['output_refs'] = ['/candidates/1/action']
    action['products']['_uses'][0]['output_refs'].append('action:future-action')
    action['sha256'] = content_sha256(action['products'])
    checks = module().make_semantic_checks(session, 'scene-a')
    assert len(checks) == 1 and '下章离开' not in checks[0]['binding']['observable']


def test_source_reference_example_is_recorded_without_requiring_a_prose_effect():
    from fake_binding_reviews import review_fixture

    session, data = session_fixture()
    original = '【指令】主要动作前应有可信动因\n【示例】过河前先看河水的深浅'
    item = source(original=original)
    contract = compile_semantics(item)
    review = review_fixture(item, ['action_design'])
    review['clause_reviews'][1]['status'] = 'not_project_instruction'
    review['sha256'] = content_sha256({k: v for k, v in review.items() if k != 'sha256'})
    application = criterion(contract)
    application['clauses'][1].update(
        applicability='not_applicable', reason='[FAKE] 本场依动作原义执行，此例只供回查',
        input_refs=[], output_refs=[], operation='', observable='', check='', consumer='review',
    )
    action = next(row for row in session['stages'] if row['stage'] == 'action_design')
    action['products']['_criteria'] = [application]
    action['sha256'] = content_sha256(action['products'])
    session['sources'] = [item]
    data[4].update(semantic_contracts=[contract], binding_policy=review['policy'],
                   binding_test_mode=True, binding_reviews={'method': review})

    checks = module().make_semantic_checks(session, 'scene-a')

    assert len(checks) == 1
    assert checks[0]['source_contract']['obligations'][0]['text'] == '主要动作前应有可信动因'
    assert action['products']['_criteria'][0]['clauses'][1]['applicability'] == 'not_applicable'


@pytest.mark.parametrize(('stage', 'pointer', 'expected'), [
    ('scene_design', '/members', True),
    ('scene_design', '/members/1', False),
    ('scene_design', '/members/1/body', False),
    ('scene_design', '/chapters', True),
    ('scene_design', '/chapters/0/scenes', True),
    ('scene_design', '/chapters/0/scenes/1/card', False),
    ('scene_design', '/chapters/1/index', False),
    ('anchor_design', '/beats', True),
    ('anchor_design', '/beats/1', False),
])
def test_original_clause_projection_only_sends_current_scene_artifacts(stage, pointer, expected):
    session, data = session_fixture()
    scenes = [
        {'key': 'scene-a', 'kind': 'scene', 'body': {'pov': 'yan', 'title': '[FAKE] 当前封条'}},
        {'key': 'scene-b', 'kind': 'scene', 'body': {'pov': 'lu', 'title': '[FAKE] 后场秘密'}},
        {'key': 'scene-c', 'kind': 'scene', 'body': {'pov': 'lu', 'title': '[FAKE] 下章秘密'}},
    ]
    chapters = [
        {'index': 1, 'card': 'chapter-now', 'scenes': [
            {'card': 'scene-a', 'index': 1, 'story_order': 1},
            {'card': 'scene-b', 'index': 2, 'story_order': 2},
        ]},
        {'index': 2, 'card': 'chapter-later', 'scenes': [
            {'card': 'scene-c', 'index': 1, 'story_order': 3},
        ]},
    ]
    scene = {'members': scenes, 'chapters': chapters, '_uses': []}
    anchor = {'beats': [
        {'scene': 'scene-a', 'observable': '[FAKE] 当前封条'},
        {'scene': 'scene-b', 'observable': '[FAKE] 后场秘密'},
    ], '_uses': []}
    value = scene if stage == 'scene_design' else anchor
    value['_uses'] = [{'source_id': 'method', 'operation': '[FAKE] 把原句用于当前场产物',
                       'output_refs': ['scene:scene-a']}]
    value['_criteria'] = [criterion(data[1], pointer)]
    for clause in value['_criteria'][0]['clauses']:
        clause['consumer'] = 'review'
    session['stages'] = [session['stages'][0], record('scene_design', scene),
                         record('anchor_design', anchor), session['stages'][-1]]
    original = deepcopy(session['stages'])

    checks = module().make_semantic_checks(session, 'scene-a', {'scene-a': 'actual-a'})

    assert bool(checks) is expected
    assert session['stages'] == original
    for check in checks:
        visible = check['binding']['observable']
        assert pointer in visible and 'actual-a' in visible
        for other in ('scene-b', 'scene-c', 'chapter-later', '后场秘密', '下章秘密'):
            assert other not in visible


def test_layer_pins_trigger_existing_independent_layer_check_without_evidence_changes():
    from nw.materials.evidence import validate_review
    from nw.models import Draft
    from nw.story_delta import draft_ref
    session, _ = session_fixture(with_layer=True)
    check = module().make_semantic_checks(session, 'scene-a')[0]
    assert check['layer_contract']['application_guidance'][0]['source_ref']['id'] == 'runtime'
    assert 'unsafe' not in json.dumps(check['layer_contract']['application_guidance'][0]['aligned_fields'])
    draft = Draft('draft-a', 'scene-a', 1, '[FAKE] 他看清铜丝才压低木片，纸角破损后旧印露了出来。', 'complete', 'run-a', 'now')
    span = {**asdict(draft_ref(draft)), 'start': 0, 'end': len(draft.text), 'quote': draft.text}
    row = {'id': check['id'], 'status': 'pass', 'reason': '观察到阻碍后确实改变动作并留下代价', 'evidence': [span],
           'source_checks': [{'id': check['source_contract']['obligations'][0]['id'], 'status': 'pass',
                              'reason': '本稿的观察应对和结果形成完整动作链', 'evidence': [span]}]}
    with pytest.raises(ValueError, match='MATERIAL_EVIDENCE'):
        validate_review([row], {'checks': [check]}, draft, None)
    row['layer_check'] = {'status': 'pass', 'reason': '原文动作顺序经当前项目转译后在具体段落中成立', 'evidence': [span]}
    validate_review([row], {'checks': [check]}, draft, None)


def test_review_package_growth_is_linear_in_original_clause_count():
    def size(count):
        session,data=session_fixture()
        s=source(original='【指令】\n'+'\n'.join(f'{n}. 当前人物动作须保持调查动因并呈现第{n}项阻碍的应对后果。' for n in range(count)))
        contract=compile_semantics(s)
        session['sources']=[s];session['context']['semantic_contracts']=[contract]
        action=next(r for r in session['stages'] if r['stage']=='action_design')
        action['products']['_criteria']=[criterion(contract)]
        action['sha256']=content_sha256(action['products'])
        return len(json.dumps(module().make_semantic_checks(session,'scene-a'),ensure_ascii=False))
    assert size(12)<size(4)*4
