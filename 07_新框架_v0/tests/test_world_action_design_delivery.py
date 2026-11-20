"""Two action-only world edges must follow a specific actor, ability and event into writing."""
from copy import deepcopy

import pytest

from nw.materials import design_network
from nw.materials.design_network_catalog import POLICY
from nw.materials.evidence import scene_checks, writer_checks
from nw.materials.phase_routes import POLICY as STAGED
from nw.materials.template_candidates import validate_scene_selection
from nw.task_models import content_sha256


SPELL = '回声术'
OTHER = '照影术'
GOAL = '在船灯熄灭前用回声术核验井底石刻。'
RULE = '回声术能量总量不足六格时，每息耗两格，只能维持两息。'
PURITY = '回声术使用同招时纯度越高，术式效果的回响延迟越久。'
LIMIT = '只有在旧港雾井旁能施展回声术。'


def record(stage, value, offered=()):
    return {'stage': stage, 'products': value, 'sha256': content_sha256(value), 'task_id': 'fixture-' + stage,
            'network_design_candidates': list(offered)}


def projects(key='C00025'):
    people = [('keeper', '班恒'), ('witness', '曲宁')]
    chars = {'members': [{'key': key, 'kind': 'character', 'body': {'name': name}} for key, name in people],
             'capabilities': [{'entity': key, 'can_act': True, 'abilities': [SPELL, OTHER],
                               'limits': ['回声术每息耗两格灵力。', '回声术的纯度会限制同招的回响时间。',
                                          '照影术只能照亮一尺水面。']} for key, _ in people]}
    world = {'members': [{'key': 'well', 'kind': 'world', 'body': {'rule': RULE if key == 'C00025' else PURITY, 'limits': LIMIT}}]}
    plot = {'event_nodes': [
        {'id': 'well1', 'actors': ['keeper'], 'goal': GOAL},
        {'id': 'well2', 'actors': ['keeper'], 'goal': GOAL},
        {'id': 'well3', 'actors': ['witness'], 'goal': GOAL},
        {'id': 'group', 'actors': ['keeper', 'witness'], 'goal': '曲宁亲自施展回声术探井，班恒守住井口。'},
        {'id': 'both', 'actors': ['keeper', 'witness'], 'goal': '班恒与曲宁联手施展回声术听清井声。'},
        {'id': 'watches', 'actors': ['keeper'], 'goal': '班恒目睹路人施展回声术，记下来人的相貌。'},
        {'id': 'unclear', 'actors': ['keeper', 'witness'], 'goal': GOAL}]}
    successor = {'candidates': [
        {'id': 'successor', 'actors': ['keeper'], 'event': GOAL, 'completion_gate': '井主抵达。'},
        {'id': 'gate', 'actors': ['keeper'], 'event': '前往盐仓等旧渡工到来。', 'completion_gate': GOAL},
        {'id': 'disabled', 'actors': ['keeper'], 'event': '守井人不能使用回声术，改用竹篙探井。', 'completion_gate': GOAL}]}
    products = {stage: record(stage, body) for stage, body in [('world_design', world), ('character_design', chars),
                                                               ('plot_design', plot), ('event_design', successor)]}
    pins = {'owner': 'world_design', 'source': {'id': '[FAKE]' + key}, 'static': {'id': '[FAKE]static'},
            'valid_types': ['悬疑'], 'basis_stage': 'action_design'}
    context = {'scope': 'chapter', 'design_network_policy': POLICY, 'design_network_catalog': {key: pins},
               'network_type_scope': {'GENRE_XUANYI': ['悬疑']}}
    return products, context


def apply(row, path):
    operation = ('按回声术每息耗两格的上限安排探井时间。' if row['key'] == 'C00025'
                 else '按回声术使用同招时的纯度差异设计回响的延迟。')
    return {'id': row['id'], 'operation': operation, 'output_refs': [path]}


def action(ident, actor, event, ability=SPELL):
    return {'id': ident, 'event': event, 'actor': actor, 'action': '回声术能量总量不足六格时，先收回探井的第二声。',
            'requires': [ability], 'steps': [], 'cost': '每息耗两格灵力。', 'limits': [LIMIT]}


def assemble(key='C00025'):
    products, context = projects(key)
    offered = design_network.candidates('action_design', products, context)
    first = next(r for r in offered if (r['actor'], r['event']) == ('keeper', 'well1'))
    value = {'candidates': [action('listen', 'keeper', 'well1'), action('spare', 'keeper', 'well2'),
                            action('other', 'witness', 'well3')],
             '_network_design_uses': [apply(first, '/candidates/0/action')]}
    if key == 'C00032':
        value['candidates'][0]['action'] = '回声术使用同招时纯度越高，探井人等待回响的时间就更长。'
    design_network.validate('action_design', value, offered)
    products['action_design'] = record('action_design', value, offered)
    scene_options = design_network.candidates('scene_design', products, context)
    [carry] = scene_options
    scenes = {'members': [{'key': 'stone', 'kind': 'scene', 'body': {'pov': 'keeper', 'characters': [],
                         'goal': '回声术能量总量不足六格时，以两息辨明井下的石刻。'}},
                         {'key': 'ferry', 'kind': 'scene', 'body': {'pov': 'witness', 'characters': [],
                         'goal': '回声术能量总量不足六格时，先听清渡工的答话。'}}],
              'selected_actions': [{'scene': 'stone', 'action': 'listen'}, {'scene': 'ferry', 'action': 'other'}],
              'selected_events': [{'scene': 'stone', 'event': 'well1'}, {'scene': 'ferry', 'event': 'well3'}],
              '_network_design_uses': [apply(carry, '/members/0/body/goal')]}
    if key == 'C00032':
        scenes['members'][0]['body']['goal'] = '回声术使用同招时纯度越高，越要留出等待石壁回响的时间。'
    return products, context, scene_options, scenes


def test_enumerates_each_actor_event_including_both_identical_nodes_and_new_successor():
    products, context = projects()
    offered = design_network.candidates('action_design', products, context)
    identities = {(c['actor'], c['event'], c['ability']) for c in offered}
    assert identities == {('keeper', 'well1', SPELL), ('keeper', 'well2', SPELL), ('witness', 'well3', SPELL),
                          ('witness', 'group', SPELL), ('keeper', 'successor', SPELL),
                          ('witness', 'both', SPELL), ('keeper', 'both', SPELL)}
    assert len(offered) == len({r['id'] for r in offered}) == len(identities)
    assert not design_network.candidates('plot_design', products, {**context, 'scope': 'book'})


def test_a_different_skill_cannot_supply_this_skills_energy_limit():
    products, context = projects()
    chars = deepcopy(products['character_design']['products'])
    for cap in chars['capabilities']:
        cap['limits'] = ['照影术每息耗两格灵力。']
    products['character_design'] = record('character_design', chars)
    assert not design_network.candidates('action_design', products, context)


@pytest.mark.parametrize(('actor', 'event', 'ability'), [('witness', 'well1', SPELL), ('keeper', 'well2', SPELL),
                                                         ('keeper', 'well1', OTHER)])
def test_world_rule_cannot_be_adopted_by_a_different_actor_event_or_ability(actor, event, ability):
    products, context = projects()
    options = design_network.candidates('action_design', products, context)
    first = next(r for r in options if (r['actor'], r['event']) == ('keeper', 'well1'))
    value = {'candidates': [action('listen', actor, event, ability)],
             '_network_design_uses': [apply(first, '/candidates/0/action')]}
    with pytest.raises(ValueError):
        design_network.validate('action_design', value, options)


@pytest.mark.parametrize('key', ['C00025', 'C00032'])
def test_only_the_scene_selecting_the_applied_action_gets_the_writer_and_reviewer_obligation(key):
    products, context, options, scenes = assemble(key)
    validate_scene_selection(scenes, products, context)
    design_network.validate('scene_design', scenes, options)
    products['scene_design'] = record('scene_design', scenes, options)
    products['bind_scope'] = record('bind_scope', {'method_guidance': []})
    session = {'policy': STAGED, 'context': context, 'sources': [], 'stages': list(products.values())}
    def delivered(scene, reader):
        design = {'material_key': scene, 'work_session': session, 'work_application': {}}
        return [r for r in reader(design) if r['id'].startswith('work:design-network:')]
    [audit] = delivered('stone', scene_checks)
    [writer] = delivered('stone', writer_checks)
    assert writer['id'] == audit['id'] and writer['observable'] == scenes['members'][0]['body']['goal']
    assert audit['network_design_key'] == key
    assert any(e['ref'] == 'input:plot_design:/event_nodes/0/goal' for e in audit['method_artifact']['prerequisites'])
    assert not delivered('ferry', scene_checks) and not delivered('ferry', writer_checks)


def test_cross_scene_reassignment_and_carrying_an_unselected_action_are_rejected():
    products, context, options, scenes = assemble()
    [carry] = options
    wrong = deepcopy(scenes)
    wrong['_network_design_uses'] = [apply(carry, '/members/1/body/goal')]
    with pytest.raises(ValueError, match='实际选择不一致'):
        design_network.validate('scene_design', wrong, options)
    wrong = deepcopy(scenes)
    wrong['selected_actions'][0]['action'] = 'spare'
    wrong['selected_events'][0]['event'] = 'well2'
    validate_scene_selection(wrong, products, context)
    with pytest.raises(ValueError, match='实际选择不一致'):
        design_network.validate('scene_design', wrong, options)
    del wrong['_network_design_uses']
    design_network.validate('scene_design', wrong, options)
    wrong['selected_actions'][0]['action'] = 'other'
    with pytest.raises(ValueError, match='actor or event'):
        validate_scene_selection(wrong, products, context)
