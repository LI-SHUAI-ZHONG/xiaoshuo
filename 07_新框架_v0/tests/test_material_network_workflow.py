from copy import deepcopy

import pytest

from nw.materials.network_workflow import POLICY, resolve_type_scope, step_sources
from nw.materials.semantic_products import original, validate_dynamic_dependencies, validate_prepared_static
from test_material_semantic_application import at, source, used


def relationship(item: dict) -> dict:
    return {'id': 'defined', 'source_id': item['source']['id'], 'source': 'yan', 'target': 'partner',
            'relation': original(item)['type'], 'condition': '[FAKE] 双方就共同调查任务达成分工'}


def test_dynamic_scope_uses_typed_ids_and_verified_parent_names(tmp_path, monkeypatch) -> None:
    from nw.materials import type_sources

    definitions = [
        ('GENRE_XUANYI', '悬疑', 'GENRE', None),
        ('GENRE_ERCIYUAN', '二次元', 'GENRE', None),
        ('SUB_ENTRY', '档案谜案', 'SUBGENRE', 'GENRE_XUANYI'),
        ('AMBIGUOUS', '奇幻', 'GENRE', None),
        ('AMBIGUOUS', '仙侠', 'GENRE', None),
    ]
    records = [({}, dict(type_id=ident, canonical_name=name, type_kind=kind, parent_id=parent), [])
               for ident, name, kind, parent in definitions]
    monkeypatch.setattr(type_sources, 'original_type_records', lambda *_: {'fixture': records})
    selected = {'selection': [{'id': k, 'label': '悬疑'} for k in ('SUB_ENTRY', 'GENRE_ERCIYUAN', 'AMBIGUOUS')]}
    assert resolve_type_scope(tmp_path, selected) == {'SUB_ENTRY': ['悬疑', '档案谜案'], 'GENRE_ERCIYUAN': ['二次元']}


def test_prepare_plot_then_filter_derived_rules_by_exact_relation_and_type() -> None:
    static = 'duty-cooperation'
    dynamic = 'C00010'
    rules = {dynamic: {'key': dynamic, 'valid_types': ['悬疑'], 'relation': '转化',
                       'derived': True, 'static_id': static}}
    authored = {'static_relations': {}, 'plot_design': {'plot-rule': '调查布局'}, 'action_design': {
        static: '按已定配角能力核对共同任务', dynamic: '核对合作的同意与分工', 'independent': '核对体力'}}
    rows = {ident: {'state': 'design_ready'} for ident in (static, dynamic)}
    context = {'network_prerequisite_policy': POLICY, 'network_type_scope': {'GENRE_XUANYI': ['悬疑']}}

    ordinary, prepared = step_sources('plot_design', authored, rules, {}, context, rows)
    assert static not in ordinary and dynamic in prepared[static]
    assert dynamic not in step_sources('action_design', authored, rules, {}, context, rows)[0]
    plot = {'plot_design': {'products': {'static_bindings': [{'id': 'cooperate', 'source_id': static,
              'source': 'lu', 'target': 'yan', 'relation': '转化', 'condition': '[FAKE] 两人先同意按分工查档'}], '_uses': []}}}
    assert dynamic not in step_sources('action_design', authored, rules, plot, context, rows)[0]
    plot['plot_design']['products']['_uses'] = [{'source_id': static, 'output_refs': ['relation:cooperate']}]
    assert dynamic in step_sources('action_design', authored, rules, plot, context, rows)[0]
    wrong_type = {**context, 'network_type_scope': {'GENRE_ERCIYUAN': ['二次元']}}
    assert step_sources('plot_design', authored, rules, {}, wrong_type, rows)[1] == {}
    assert dynamic not in step_sources('action_design', authored, rules, plot, wrong_type, rows)[0]
    assert 'independent' in step_sources('action_design', authored, rules, plot, wrong_type, rows)[0]


def test_prepared_static_use_has_a_real_relationship_and_clause_output() -> None:
    static = source('1.1_主角 / 130_核心悬念 / 绑定')
    ident = static['source']['id']
    context = {'network_prerequisite_policy': POLICY, 'prepared_static_sources': [ident]}
    value = {'static_bindings': [relationship(static)]}
    used(value, static, 'relation:defined')
    clause = {'applicability': 'applies', 'output_refs': ['/static_bindings/0/condition']}
    value['_criteria'] = [{'source_id': ident, 'clauses': [clause]}]
    validate_prepared_static(value, [static], context)
    clause['output_refs'] = ['/directions/0/choice']
    with pytest.raises(ValueError, match='clauses must establish'):
        validate_prepared_static(value, [static], context)


@pytest.mark.parametrize('defect', ['missing_use', 'unrelated_ref', 'id_only', 'wrong_actor', 'wrong_type'])
def test_dynamic_action_must_use_its_actual_prior_relation(defect: str) -> None:
    static = source('1.1_主角 / 130_核心悬念 / 绑定')
    dynamic = source('C00001')
    products, value = at('action_design')
    people = products['character_design']['products']['members']
    people += [{'key': 'partner'}, {'key': 'other-actor'}]
    plot = products['plot_design']['products']
    plot['static_bindings'] = [relationship(static), {**relationship(static), 'id': 'different'}]
    used(plot, static, 'relation:defined')
    action = value['candidates'][0]
    action['source_ids'] = [dynamic['source']['id']]
    used(value, dynamic, 'action:' + action['id'])
    clause = {'applicability': 'applies', 'input_refs': ['input:plot_design:/static_bindings/0/condition'],
              'output_refs': ['/candidates/0/action']}
    value['_criteria'] = [{'source_id': dynamic['source']['id'], 'clauses': [clause]}]
    context = {'network_prerequisite_policy': POLICY, 'network_type_scope': {'GENRE_XUANYI': ['悬疑']},
               'method_sources': [static, dynamic]}
    validate_dynamic_dependencies('action_design', value, products, [dynamic], context)

    if defect == 'missing_use':
        plot['_uses'] = []
    elif defect == 'unrelated_ref':
        clause['input_refs'] = ['input:plot_design:/static_bindings/1/condition']
    elif defect == 'id_only':
        clause['input_refs'] = ['input:plot_design:/static_bindings/0/id']
    elif defect == 'wrong_actor':
        action['actor'] = 'other-actor'
    else:
        context['network_type_scope'] = {'GENRE_ERCIYUAN': ['二次元']}
    with pytest.raises(ValueError, match='MATERIAL_SEMANTICS'):
        validate_dynamic_dependencies('action_design', value, products, [dynamic], context)
