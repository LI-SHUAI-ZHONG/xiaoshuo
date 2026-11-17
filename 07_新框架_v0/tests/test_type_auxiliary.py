"""Type methods must remain conditional and bind real state evidence."""
from hashlib import sha256
import json

import pytest

from nw.materials.adjudication import build_adjudications
from nw.materials.binding import resolve_materials, validate_bindings
from nw.materials.catalog import build_catalog
from nw.materials.route_catalog import route
from nw.materials.unit_catalog import index_units, list_units
from test_material_catalog import _manifest


def fixture(tmp_path, *, state_adapter=False, empty_effect=False):
    genre = {'type_id': 'GENRE_A', 'canonical_name': '规则成长', 'definition': '规则和资源限制下作出成长选择',
             'status': 'active', 'confidence': .8}
    method = ({'state_adaptation_id': 'TSA_001', 'state_type': 'body_state',
               'allowed_fields': ['body_state_value'], 'preferred_changes': ['候选更新优先级调整'],
               'forbidden_changes': ['跳过事件证据', '未知信息自动变成已知'],
               'preconditions': ['状态变化有事件依据'], 'validation_rules': ['变化必须来自事件'],
               'status': 'active', 'confidence': .6}
              if state_adapter else
              {'rule_id': 'TDR_001', 'rule_scope': '身体状态在类型世界中的传播', 'rule_kind': 'TYPE_STATE_PROPAGATION',
               'trigger_concepts': ['身体状态'], 'preconditions': ['身体状态变化已确认'],
               'candidate_effects': [{'effect_id': 'TDR_001_E01', 'description': '' if empty_effect else '饥饿改变关注与行动候选'}],
               'selection_constraints': ['必须经过行动选择'], 'propagation_limits': {'max_depth': 3},
               'forbidden_assumptions': ['类型不能决定确定行为'], 'not_guaranteed': ['候选不一定选中'],
               'status': 'active', 'confidence': .8})
    block = '类型状态变化适配.json' if state_adapter else '类型动态规则总表.json'
    data = ('SOURCE: 主类型.json\n=====\n' + json.dumps([genre], ensure_ascii=False) +
            '\nSOURCE: ' + block + '\n=====\n' + json.dumps([method], ensure_ascii=False)).encode()
    mf = _manifest(tmp_path / 'sources', tmp_path, [('types.txt', 'types', data)])
    build_catalog(tmp_path, tmp_path / 'sources', mf)
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    records = list_units(tmp_path, source_id=None, fragment_id=None, key=None, kind='record', limit=100, offset=0)['units']
    roots = [route(tmp_path, row['unit_id']) for row in records]
    return next(row for row in roots if row['source']['key'] == 'GENRE_A'), next(
        row for row in roots if row['source']['fragment_key'] == block)


@pytest.mark.parametrize('adapter', [False, True])
def test_complete_conditional_type_method_can_be_bound_without_becoming_a_fact(tmp_path, adapter):
    genre, method = fixture(tmp_path, state_adapter=adapter)
    assert method['profile'] == 'type_transition'
    pins = [{**{key: row['source'][key] for key in ('id', 'file_sha256', 'sha256')},
             'disposition': 'required', 'reason': '有选择和证据的状态候选'} for row in (genre, method)]
    adopted = resolve_materials(tmp_path, pins)
    ident = method['source']['id']
    obligations = next(row for row in adopted if row['source']['id'] == ident)['review']['contract']['obligations']
    labels = {field['label'] for field in obligations}
    assert ('allowed_fields' if adapter else 'candidate_effects') in labels
    value = {'function': '状态改变后重新作选择', 'parameter': '身体状态', 'observable': '人物先感到饥饿，再选择取食',
             'check': '饥饿不自动决定行动', 'target_card': 'person', 'type_sources': [genre['source']['id']],
             'trigger': '人物已饥饿', 'choice': '取食而非追赶', 'cost': '花费时间', 'failure': '没有食物则继续忍耐',
             'knowledge_boundary': '仅本人知道饥饿',
             'state': [{'entity_id': 'person', 'predicate': 'body_state_value', 'holder': 'WORLD',
                        'expected_old': '饥饿', 'new_value': '进食后缓解'}],
             'source_scope': {field['id']: {'disposition': 'required', 'reason': '明确采用该条件和边界'} for field in obligations}}
    other = adopted[0]
    base = {'disposition': 'selected', 'reason': '本场遵守所选类型', 'function': '兑现承诺', 'parameter': '规则与资源',
            'observable': '受资源约束作选择', 'check': '有后果', 'source_scope': {
                field['id']: {'disposition': 'required', 'reason': '采用'} for field in other['review']['contract']['obligations']}}
    candidate = {'chapters': [{'index': 1, 'card': 'ch', 'scenes': [{'index': 1, 'card': 's', 'story_order': 1}]}],
                 'material_bindings': {'s': {genre['source']['id']: base, ident: value}}}
    members = {'s': {'kind': 'scene', 'body': {'pov': 'person', 'characters': ['person']}},
               'person': {'kind': 'character', 'body': {}}}
    validate_bindings(candidate, 'chapter', members, {}, adopted)
    if adapter:
        value['state'][0]['predicate'] = 'unlisted_magic'
        with pytest.raises(ValueError, match='allowed_fields'):
            validate_bindings(candidate, 'chapter', members, {}, adopted)
    else:
        value['type_sources'] = []
        with pytest.raises(ValueError, match='adopted type'):
            validate_bindings(candidate, 'chapter', members, {}, adopted)


def test_blank_candidate_effect_cannot_be_completed_from_its_id(tmp_path):
    _, method = fixture(tmp_path, empty_effect=True)
    assert method['adjudication']['can_offer_for_design'] is False


def test_conditions_keep_their_own_identity_when_they_share_a_parent_rule(tmp_path):
    from nw.materials.catalog import _connect
    from nw.materials.route_catalog import _UNITS
    from nw.materials.type_adjudication import TypeAdjudicator

    values = [{'condition_id': f'COND_{index}', 'rule_id': 'TDR_001', 'status': 'active',
               'field': field, 'expected_value': True} for index, field in enumerate(('alive', 'awake'))]
    data = ('SOURCE: 类型动态触发条件.json\n=====\n' + json.dumps(values)).encode()
    mf = _manifest(tmp_path / 'sources', tmp_path, [('types.txt', 'types', data)])
    build_catalog(tmp_path, tmp_path / 'sources', mf)
    index_units(tmp_path, None)
    with _connect(tmp_path, write=False) as db:
        engine = TypeAdjudicator(db)
        rows = [dict(row) for row in db.execute(_UNITS + " WHERE u.kind='record'")]
        assert {row['key'] for row in rows} == {'COND_0', 'COND_1'}
        assert all(not engine.review(row)['conflicts'] for row in rows)
