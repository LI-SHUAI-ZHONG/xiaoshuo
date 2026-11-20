"""Compare adopted book-specific costs through the action, final scene and pinned manuscript review."""
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from nw.materials import design_network
from nw.materials.action_consumption import basis, validate_use
from nw.materials.design_network_catalog import LEGACY_POLICY, POLICY
from nw.materials.action_review import review_result
from nw.materials.evidence import writer_checks
from nw.materials.phase_routes import POLICY as STAGED
from nw.models import Draft
from nw.story_delta import draft_ref
from test_world_action_design_delivery import SPELL, action, apply, assemble, projects, record


@pytest.mark.parametrize(('text', 'valid'), [
    ('回声术维持两息后熄灭。', True),
    ('回声术维持四十息后成功探明石刻。', False),
    ('回声术原想维持十息，却在第二息中断。', True),
    ('回声术无法维持十息，只能在第二息收手。', True),
    ('回声术原想维持十息，却在第九息中断。', False),
    ('回声术每息耗一格，连续施术两息。', False),
    ('回声术每息耗两份，持续两息。', False),
    ('回声术无需消耗灵力，持续两息。', False),
    ('回声术灵力仅有两格，维持两息后成功。', False),
    ('回声术灵力仅有两格。回声术持续两息后完成。', False),
    ('回声术灵力仅有六格，持续两息。', False),
    ('回声术持续一息，余量为零格时中断。', True),
    ('回声术储备为两枚，顺利维持两息。', False),
    ('回声术持续两分钟后顺利完成。', False),
])
def test_action_cost_checks_the_landed_result(text, valid):
    products, context = projects()
    [row, *_] = design_network.candidates('action_design', products, context)
    value = {'candidates': [action('current', row['actor'], row['event'])],
             '_network_design_uses': [apply(row, '/candidates/0/action')]}
    value['candidates'][0]['action'] = text
    if valid:
        design_network.validate('action_design', value, [row], products, context)
    else:
        with pytest.raises(ValueError, match='C00025'):
            design_network.validate('action_design', value, [row], products, context)


def test_rate_and_duration_convert_in_compatible_units_only():
    row = {'key': 'C00025', 'ability': SPELL,
           'consumption': basis('回声术灵力为六格，每分钟耗两格。', '', SPELL, '每分钟耗两格。')}
    validate_use(row, '回声术维持180秒后停止。', operation='', stage='action_design')
    with pytest.raises(ValueError, match='时长超过'):
        validate_use(row, '回声术维持181秒后停止。', operation='', stage='action_design')


def test_the_witnesses_other_spell_is_independent_but_a_changed_sibling_step_is_checked():
    products, context, options, scenes = assemble()
    other = action('unrelated', 'keeper', 'well2', '照影术')
    other['action'] = '照影术连续施术四十息才找到出口。'
    products['action_design']['products']['candidates'].append(other)
    scenes['selected_actions'].append({'scene': 'stone', 'action': 'unrelated'})
    design_network.validate('scene_design', scenes, options, products, context)
    products['action_design']['products']['candidates'][0]['steps'] = [
        {'result': '回声术连续维持四十息后顺利解开石刻。'}]
    with pytest.raises(ValueError, match='C00025'):
        design_network.validate('scene_design', scenes, options, products, context)


def test_state_patch_cannot_reverse_the_approved_action():
    products, context, options, scenes = assemble()
    products['scene_design'] = record('scene_design', scenes, options)
    change = {'patches': [{'scene': 'stone', 'choice': '照井底石刻。', 'planned_result': '回声术持续十息后成功开门。'}]}
    with pytest.raises(ValueError, match='C00025'):
        design_network.validate('state_transition', change, [], products, context)
    change['patches'][0]['planned_result'] = '回声术维持两息后熄灭，井下余声停歇。'
    design_network.validate('state_transition', change, [], products, context)


def test_review_checks_pinned_narration_and_writer_receives_the_measured_limit():
    products, context, options, scenes = assemble()
    scene = record('scene_design', scenes, options)
    products['scene_design'] = scene
    products['bind_scope'] = record('bind_scope', {'method_guidance': []})
    session = {'policy': STAGED, 'context': context, 'sources': [], 'stages': list(products.values())}
    [writer] = [r for r in writer_checks({'material_key': 'stone', 'work_session': session, 'work_application': {}})
                if r['id'].startswith('work:design-network:')]
    assert '只能维持两息' in writer['check'] and '每息耗两格' in writer['check']
    [check] = design_network.scene_checks(scene, 'stone')
    assert check['id'] == writer['id']
    for text, blocked in [('回声术连续施术十息，班恒听清了井底的声音。', True),
                          ('班恒夸口：“回声术能维持十息。”回声术在第二息熄灭。', False)]:
        draft = Draft('draft', 'stone', 1, text, 'complete', 'run', 'now')
        span = {**asdict(draft_ref(draft)), 'start': 0, 'end': len(text), 'quote': text}
        result = {'id': check['id'], 'status': 'pass', 'evidence': [span], 'reason': '以井底余声和火光核验实际用时。'}
        def run_review():
            raw = {'recommendation': 'pass', 'notes': '', 'core_changes': [], 'material_checks': [result]}
            return review_result(SimpleNamespace(output_text=json.dumps(raw)), {'checks': [check]}, draft, None)
        if blocked:
            repaired = run_review()
            assert repaired['material_checks'][0]['status'] == 'failed'
            assert 'C00025' in repaired['material_checks'][0]['reason']
            result['status'] = 'failed'
        assert run_review()['recommendation'] == ('revise' if blocked else 'pass')


def test_saved_v1_candidate_and_v2_obligation_use_their_frozen_contracts():
    products, context = projects()
    for policy in (LEGACY_POLICY, POLICY):
        context['design_network_policy'] = policy
        [row, *_] = design_network.candidates('action_design', products, context)
        assert ('consumption' in row) == (policy == POLICY)
        value = {'candidates': [action('cast', row['actor'], row['event'])],
                 '_network_design_uses': [apply(row, '/candidates/0/action')]}
        value['candidates'][0]['action'] = '回声术能量总量不足六格时，却能维持十息并成功。'
        if policy == LEGACY_POLICY:
            design_network.validate('action_design', value, [row], products, context)
        else:
            with pytest.raises(ValueError, match='C00025'):
                design_network.validate('action_design', value, [row], products, context)
