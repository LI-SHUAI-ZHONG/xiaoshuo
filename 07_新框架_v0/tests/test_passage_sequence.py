import json
from copy import deepcopy
from dataclasses import replace

import pytest

from nw.materials import passage_sequence as passage, story_policies
from nw.materials.phase_routes import POLICY as STAGE_POLICY


REFERENCE = {'ref': 'method-a:v2:thread-a', 'kind': 'focus_relay', 'condition': '场景要从排队的群体转到验印的人',
             'boundary': '无公共观察线索时不宜直接从群体跳到私有身份',
             'operations': ['用经手的东西将读者的注意从队列转向负责验印的人。']}
EVENTS = {'plot_design': {'products': {'event_nodes': [
    {'id': 'gate', 'goal': '找出谁在队尾换过印', 'setting': '旧库门口仍在依次验印'}]}}}


def scene(kind, ref=None):
    value = {'selected_events': [{'scene': 'archive', 'event': 'gate'}], 'passage_choices': [
        {'scene': 'archive', 'event': 'gate', 'kind': kind, 'source_ref': ref, 'need_quote': '找出谁在队尾换过印',
         'reason': '从等候的人转到传递印条的手，读者才能在拾起印条之前辨认到场的人。'}]}
    if ref:
        value['passage_choices'][0]['fit'] = {'condition': REFERENCE['condition'], 'boundary': REFERENCE['boundary'],
            'prior_quote': '旧库门口仍在依次验印', 'boundary_check': '旧库门口仍在依次验印，读者可跟随队列中的印条，不用先揭明换印人身份。'}
    return value


def expression(kind, ref=None):
    procedure = kind == 'procedure_branch'
    if procedure:
        descriptions = [('demonstration', '第一个伙计出示旧印，守柜人给出银牌', '给出银牌', 'scene', 'action'),
                        ('compression', '一刻过去，银牌在一双双手上传递', '银牌', 'ellipsis', 'summary'),
                        ('different_choice', '轮到沈砚，他将新印留在桌上，请先验笔迹', '请先验笔迹', 'scene', 'speech')]
    else:
        descriptions = [('orientation', '库门外等候的人挨着站成一列', '站成一列', 'summary', 'summary'),
                        ('attention', '一张带泥的印条顺着这列人传来', '带泥的印条', 'scene', 'perception'),
                        ('focus', '守柜人用袖口遮着右手接住印条', '袖口遮着右手', 'pause', 'perception')]
    guidance, steps = [], []
    for index, (role, wording, focus, detail, mode) in enumerate(descriptions, 1):
        guidance.append({'scene': 'archive', 'observable': wording, 'narration': {'mode': mode, 'time': 'current'}})
        steps.append({'beat': index, 'role': role, 'focus_quote': focus, 'detail': detail, 'status': 'observed',
                      'bridge_quote': descriptions[index - 2][2] if index > 1 else None,
                      'connection': '跟着刚才出现的物件移到下一个人面前' if index > 1 else None})
    sequence = {'scene': 'archive', 'steps': steps}
    if procedure:
        sequence['comparison'] = {'gate_quote': '换过印', 'example_beat': 1, 'example_actor': '伙计',
            'example_choice': '出示旧印', 'branch_beat': 3, 'branch_actor': '沈砚', 'branch_choice': '请先验笔迹'}
    if ref:
        sequence.update(source_operation=REFERENCE['operations'][0], source_beat=2)
    return {'guidance': guidance, 'passage_sequences': [sequence]}


@pytest.mark.parametrize('kind,ref', [('focus_relay', REFERENCE['ref']), ('procedure_branch', None)])
def test_choices_and_expression_have_one_scene_and_the_project_s_own_concrete_beats(kind, ref):
    choices = scene(kind, ref)
    references = [REFERENCE] if ref else []
    passage.validate_choices(choices, EVENTS, references)
    passage.validate_sequences(expression(kind, ref), choices, references)


@pytest.mark.parametrize('key,wrong', [('event', 'absent'), ('need_quote', '这是另一个场景的目标'),
                                      ('source_ref', 'method-a:v1:thread-a'), ('kind', 'procedure_branch')])
def test_choice_checks_its_selected_event_and_exact_source(key, wrong):
    choices = scene('focus_relay', REFERENCE['ref'])
    choices['passage_choices'][0][key] = wrong
    with pytest.raises(ValueError):
        passage.validate_choices(choices, EVENTS, [REFERENCE])


@pytest.mark.parametrize('key,bad', [('condition', '来源没有的条件'), ('boundary', '随便转场'),
                                     ('prior_quote', '未曾选中的另一场目标'), ('boundary_check', '可以套用')])
def test_fit_rejects_swapped_source_or_no_project_evidence(key, bad):
    choices = scene('focus_relay', REFERENCE['ref'])
    choices['passage_choices'][0]['fit'][key] = bad
    with pytest.raises(ValueError):
        passage.validate_choices(choices, EVENTS, [REFERENCE])


def test_fit_can_cite_only_actions_actually_chosen_in_this_scene():
    choices = scene('focus_relay', REFERENCE['ref'])
    action = {'id': 'raise', 'event': 'gate', 'action': '将灯压到印泥旁', 'cost': '等候者催促',
              'steps': [], 'requires': [], 'limits': []}
    products = {**EVENTS, 'action_design': {'products': {'candidates': [action]}}}
    choices['passage_choices'][0]['fit'].update(prior_quote=action['action'],
        boundary_check='将灯压到印泥旁，在场者都能看清痕迹，仍不知道换印人的身份。')
    choices['selected_actions'] = [{'scene': 'archive', 'action': 'raise'}]
    passage.validate_choices(choices, products, [REFERENCE])
    choices['selected_actions'][0]['scene'] = 'another_place'
    with pytest.raises(ValueError):
        passage.validate_choices(choices, products, [REFERENCE])


@pytest.mark.parametrize('key,wrong', [('beat', 1), ('beat', True), ('role', 'focus'), ('bridge_quote', '不存在的交接'),
                                      ('focus_quote', '别人的手'), ('status', 'inference')])
def test_expression_cannot_accept_wrong_beat_bridge_or_unowned_judgment(key, wrong):
    plan = expression('focus_relay')
    plan['passage_sequences'][0]['steps'][1][key] = wrong
    with pytest.raises(ValueError):
        passage.validate_sequences(plan, scene('focus_relay'), [])


@pytest.mark.parametrize('field,bad', [('source_beat', 9), ('source_operation', '从未提炼的方法'), ('scene', 'neighbor')])
def test_expression_pins_real_operation_to_actual_selected_beat(field, bad):
    plan = expression('focus_relay', REFERENCE['ref'])
    plan['passage_sequences'][0][field] = bad
    with pytest.raises(ValueError):
        passage.validate_sequences(plan, scene('focus_relay', REFERENCE['ref']), [REFERENCE])


def test_alternative_or_legacy_scene_keeps_ordinary_guidance():
    choices = scene('other')
    passage.validate_choices(choices, EVENTS, [REFERENCE])
    passage.validate_sequences({'guidance': []}, choices, [REFERENCE])
    del choices['passage_choices']
    passage.validate_choices(choices, EVENTS, [])
    with pytest.raises(ValueError):
        passage.validate_choices(choices, EVENTS, [REFERENCE])
    assert not passage.prompt('scene_design', {}, {}, {})
    plan = {**story_policies.current(), 'passage_references': [REFERENCE]}
    session = {'policy': STAGE_POLICY, 'context': deepcopy(plan)}
    story_policies.verify_session(session, plan)
    session['context']['passage_references'][0]['operations'][0] = '另一个版本'
    with pytest.raises(ValueError, match='冻结的段落方法'):
        story_policies.verify_session(session, plan)


@pytest.mark.parametrize('field,bad', [('example_beat', 3), ('branch_actor', '守柜人'), ('branch_choice', '出示旧印'),
                                      ('gate_quote', '从不相关的另一个事件拼接')])
def test_procedure_requires_a_shared_gate_both_participants_and_two_actual_choices(field, bad):
    value = expression('procedure_branch')
    sequence = value['passage_sequences'][0]
    sequence['comparison'][field] = bad
    with pytest.raises(ValueError):
        passage.validate_sequences(value, scene('procedure_branch'), [])


def test_two_beat_procedure_can_skip_repetitions_but_must_show_different_options():
    value = expression('procedure_branch')
    [sequence] = value['passage_sequences']
    sequence['steps'].pop(1)
    sequence['steps'][1]['bridge_quote'] = sequence['steps'][0]['focus_quote']
    passage.validate_sequences(value, scene('procedure_branch'), [])
    value['guidance'][2]['observable'] += '，之后也出示旧印'
    sequence['comparison']['branch_choice'] = '出示旧印'
    with pytest.raises(ValueError, match='同一选项'):
        passage.validate_sequences(value, scene('procedure_branch'), [])


def test_multiple_contiguous_focus_beats_can_bridge_both_space_and_person():
    value = expression('focus_relay')
    guides, steps = value['guidance'], value['passage_sequences'][0]['steps']
    guides.insert(2, {**guides[1], 'observable': '守柜人对着印条举起了一盏灯'})
    steps.insert(2, {**steps[1], 'beat': 3, 'focus_quote': '一盏灯', 'bridge_quote': '带泥的印条'})
    steps[-1].update(beat=4, bridge_quote='一盏灯')
    passage.validate_sequences(value, scene('focus_relay'), [])


def test_pending_clue_alone_cannot_turn_attention_until_it_is_visible():
    value = expression('focus_relay')
    value['passage_sequences'][0]['steps'][1]['status'] = 'pending'
    with pytest.raises(ValueError, match='可见线索'):
        passage.validate_sequences(value, scene('focus_relay'), [])


def test_normal_design_driver_carries_scene_choice_into_expression_and_reopen(tmp_path):
    from nw.call_budget import create_budget
    from nw.materials.template_support import events
    from nw.materials.work_session import drive_plan
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_novel_flow import config

    class PassageModel(PhaseModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            stage = payload.get('stage')
            if stage not in ('scene_design', 'expression_design'):
                return result
            response = json.loads(result.text)
            products = response['products']
            if stage == 'scene_design':
                assert payload['passage_policy'] == passage.POLICY
                [selected] = products['selected_events']
                project_event = events(payload['inputs'])[selected['event']]
                products['passage_choices'] = [{**selected, 'need_quote': project_event['goal'],
                    'kind': 'focus_relay', 'source_ref': None, 'reason': '从药铺门前转到封条，让读者顺着灯光注意到旧印。'}]
            else:
                [choice] = payload['passage_choices']
                assert choice['kind'] == 'focus_relay'
                model_plan = expression('focus_relay')
                anchor = products['guidance'][-1]
                offset = len(products['guidance'])
                for guide in model_plan['guidance']:
                    products['guidance'].append({**anchor, 'observable': guide['observable'],
                        'narration': {**anchor['narration'], 'mode': guide['narration']['mode']}})
                [sequence] = model_plan['passage_sequences']
                sequence['scene'] = choice['scene']
                for step in sequence['steps']:
                    step['beat'] += offset
                products['passage_sequences'] = [sequence]
            return replace(result, text=json.dumps(response, ensure_ascii=False))

    template_catalog(tmp_path)
    provider = PassageModel()
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('段落转焦'); store.add_brief('从药铺门前的动作转到封条'); adopt_story(store, baseline(), {})
        budget = create_budget(store, 'passage', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'passage')
        package = {**package, 'scope': 'chapter'}
        driven, frozen = drive_plan(store, request, package, provider, config(store))
        stages = {row['stage']: row['products'] for row in frozen['material_work']['stages']}
        assert stages['scene_design']['passage_choices'][0]['source_ref'] is None
        assert stages['expression_design']['passage_sequences'][0]['steps'][-1]['focus_quote'] == '袖口遮着右手'
        story_policies.verify_plan(frozen)
        count = len(provider.calls)
    with Store(tmp_path / 'story', test_mode=True) as store:
        again, reopened = drive_plan(store, request, package, provider, config(store))
        assert again == driven and reopened == frozen and len(provider.calls) == count
