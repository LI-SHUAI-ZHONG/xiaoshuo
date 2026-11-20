"""Prepare plot's static dependencies using authored instructions before execution."""
from copy import deepcopy

from nw.materials.network_workflow import EARLY_POLICY, POLICY, early_waiting, prepared_static_source, step_sources


def fixture() -> tuple[dict, dict, dict, dict]:
    authored = {
        'type_adaptation': {'type-rule': '已有读者承诺和类型边界'},
        'world_design': {}, 'character_design': {},
        'static_relations': {'same-step-rule': '静网已经独立保存后才适用'},
        'plot_design': {'plot-basis': '确认项目中的缺席者和已写明的旧事', 'plot-rule': '布局缺席者造成的信息缺口'},
        'action_design': {'late-basis': '已有搭档时核对共同任务', 'late-rule': '按分工回应障碍'},
    }
    rules = {ident: {'key': ident, 'valid_types': ['悬疑'], 'derived': True, 'static_id': basis, 'relation': '绑定'}
             for ident, basis in (('plot-rule', 'plot-basis'), ('late-rule', 'late-basis'),
                                  ('type-rule', 'plot-basis'), ('same-step-rule', 'plot-basis'))}
    rows = {ident: {'key': ident, 'state': 'design_ready',
                   'profile': 'dynamic_relation' if ident in rules else 'static_relation'}
            for pool in authored.values() for ident in pool}
    context = {'network_prerequisite_policy': POLICY, 'early_network_policy': EARLY_POLICY,
               'network_type_scope': {'GENRE_XUANYI': ['悬疑']}}
    return authored, rules, rows, context


def test_prepares_plot_basis_and_requires_a_frozen_static_use() -> None:
    authored, rules, rows, context = fixture()
    pool, prepared = step_sources('static_relations', authored, rules, {}, context, rows)
    assert 'same-step-rule' not in pool
    assert list(prepared) == ['plot-basis']
    assert 'plot-rule' in prepared['plot-basis'] and authored['plot_design']['plot-basis'] in prepared['plot-basis']
    frozen = {'static_relations': {'products': {'relations': [{
        'id': 'real', 'source': 'person', 'target': 'archive', 'relation': '绑定', 'condition': '共有档案归属'}], '_uses': []}}}
    assert 'plot-rule' not in step_sources('plot_design', authored, rules, frozen, context, rows)[0]
    frozen['static_relations']['products']['_uses'] = [{'source_id': 'plot-basis', 'output_refs': ['relation:real']}]
    ordinary, later = step_sources('plot_design', authored, rules, frozen, context, rows)
    assert 'plot-rule' in ordinary and list(later) == ['late-basis']
    assert early_waiting('plot_design', authored, rules, frozen, context, rows) == {}


def test_early_rules_wait_without_qualifying_themselves() -> None:
    authored, rules, rows, context = fixture()
    for stage, key, expected in (
            ('type_adaptation', 'type-rule', '早于静网关系阶段'),
            ('static_relations', 'same-step-rule', '本轮产物不能自证'),
            ('plot_design', 'plot-rule', '上游未落实')):
        report = early_waiting(stage, authored, rules, {}, context, rows)
        assert len(report['examples']) == 1 and sum(report['counts'].values()) == 1
        assert report['examples'][0]['key'] == key and expected in report['examples'][0]['reason']
    wrong_type = {**context, 'network_type_scope': {'X': ['二次元']}}
    assert step_sources('static_relations', authored, rules, {}, wrong_type, rows)[1] == {}
    assert early_waiting('plot_design', authored, rules, {}, wrong_type, rows) == {}
    ambiguous = deepcopy(rules)
    ambiguous['plot-rule']['static_id'] = None
    assert step_sources('static_relations', authored, ambiguous, {}, context, rows)[1] == {}
    assert '唯一静网依据' in early_waiting('plot_design', authored, ambiguous, {}, context, rows)['examples'][0]['reason']


def test_earlier_static_authority_needs_the_new_frozen_policy_and_real_study_pool() -> None:
    authored, rules, rows, context = fixture()
    static = {'source': {'id': 'plot-basis', 'profile': 'static_relation'}}
    context['early_static_sources'] = ['plot-basis']
    assert prepared_static_source(static, 'static_relations', context)
    assert not prepared_static_source(static, 'plot_design', context)
    legacy = {**context, 'early_network_policy': None}
    assert not prepared_static_source(static, 'static_relations', legacy)
    assert step_sources('static_relations', authored, rules, {}, legacy, rows)[1] == {}
    rows['plot-basis']['state'] = 'reference'
    assert step_sources('static_relations', authored, rules, {}, context, rows)[1] == {}
