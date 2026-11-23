"""Keep the confirmed direction on the actual book-stage and replay paths."""
from copy import deepcopy
import json

import pytest

from nw.call_budget import create_budget
from nw.materials.phase_projection import expand_output, verify_chain
from nw.materials.work_session import drive_plan
from nw.planning import _run_plan, prepare_plan_task
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, content_sha256
from nw.tasks import read_input_manifest
from story_fixture import baseline
from test_material_stage_integration import pins_for
from test_novel_flow import Model, config


BOOK_STAGES = ('type_selection', 'type_adaptation', 'world_design', 'character_design',
               'static_relations', 'plot_design')


def direction(*, title='[FAKE] 沉井旧印'):
    candidate = {
        'id': 'direction-2',
        'title': title,
        'premise': '[FAKE] 废井封条留有两代不同的印痕，关井记录和现存证物互相矛盾。',
        'protagonist': '[FAKE] 沈砚熟悉旧印，却没有独立进入封井的资格。',
        'goal': '[FAKE] 沈砚要查到哪一晚有人更换封条。',
        'conflict': '[FAKE] 查档须由掌钥人签字，对方怕担责，只肯交不完整的回执。',
        'world_premise': '[FAKE] 关井一律双人验封，回执须同时载有两代官印之一与值守签记。',
        'long_term_drive': '[FAKE] 每次找回一份签记，旧案就指向新的井口，并暴露一段证人的隐瞒。',
        'type_fit': '[FAKE] 让可查印痕承担悬疑和回收。',
        'author_fit': '[FAKE] 用可见线索推动调查，保留近景视角。',
    }
    return {'task_id': 'direction-task', 'decision_id': 'job:direction:book:confirm',
            'candidate_id': candidate['id'], 'candidate': candidate, 'sha256': content_sha256(candidate)}


class DirectionModel(Model):
    def __init__(self, *, alternatives=False):
        super().__init__()
        self.alternatives = alternatives

    def generate(self, messages, **params):
        response = super().generate(messages, **params)
        packet = json.loads(messages[-1]['content'])
        if packet.get('approved_direction') and not self.alternatives:
            output = json.loads(response.text)
            if packet.get('stage') == 'plot_design':
                output['products']['directions'] = output['products']['directions'][:1]
            elif 'candidate_cards' in output:
                output['candidate_cards'] = output['candidate_cards'][:1]
            response.text = json.dumps(output, ensure_ascii=False)
        return response


def start(store):
    store.init_project('[FAKE] 沉井调查')
    store.add_brief('[FAKE] 一场对废井封条的追查', '保持受限第三人称。')
    adopt_story(store, baseline(), {})
    return create_budget(store, 'direction-handoff', Budget(28, 150000, 8000))


def test_selected_direction_reaches_real_book_stage_inputs_and_reopen(tmp_path, monkeypatch):
    key = '1.1_行动动机'
    pins_for(tmp_path, monkeypatch, f'### {key}\n【定义】人物行动要有能影响选择的真实目标。\n【指令】先写实际目标，再设计行动。\n', [key])
    path = tmp_path / '[FAKE]-direction-stages'
    model = DirectionModel()
    approved = direction()
    with Store(path, create=True, test_mode=True) as store:
        budget = start(store)
        task, package = prepare_plan_task(store, 1, 'book', model, config(store), budget, 'direction-stages',
                                          approved_direction=approved)
        staged_task, staged = drive_plan(store, task, package, model, config(store))
        inputs = {packet['stage']: packet for call in model.calls
                  if (packet := json.loads(call[-1]['content'])).get('stage')}
        for stage in BOOK_STAGES:
            assert inputs[stage]['approved_direction'] == approved
        assert 'approved_direction' not in inputs['bind_scope']
        assert '更换封条' in inputs['plot_design']['retrieval_need']
        plot_schema = inputs['plot_design']['output_schema']
        assert '只深化已确认的全书方向' in plot_schema and '2至3个方向' not in plot_schema
        assert inputs['world_design']['cast_plot_sources']['confirmed-direction:goal'] == approved['candidate']['goal']
        assert len(staged['material_work']['candidates']) == 1
        assert len(expand_output(json.loads(staged_task.payload['messages'][-1]['content'])['output_contract'],
                             staged)['candidate_cards']) == 1
    with Store(path, test_mode=True) as store:
        _, saved = read_input_manifest(store, staged_task.manifest_id)
        assert saved['approved_direction'] == approved
        broken = deepcopy(saved['material_work'])
        broken['stages'][0].pop('approved_direction_receipt')
        with pytest.raises(ValueError, match='全书方向'):
            verify_chain(broken)
        resumed, package = prepare_plan_task(store, 1, 'book', model, config(store), budget, 'direction-stages')
        assert package['approved_direction'] == approved
        assert resumed.manifest_id == task.manifest_id
        with pytest.raises(ValueError, match='全书方向'):
            prepare_plan_task(store, 1, 'book', model, config(store), budget, 'direction-stages',
                              approved_direction=direction(title='[FAKE] 未经批准的替换方向'))


@pytest.mark.parametrize('alternatives', [False, True])
def test_legacy_model_path_expands_exactly_one_approved_direction(tmp_path, alternatives):
    model = DirectionModel(alternatives=alternatives)
    approved = direction()
    with Store(tmp_path / '[FAKE]-direction', create=True, test_mode=True) as store:
        budget = start(store)
        task, package = prepare_plan_task(store, 1, 'book', model, config(store), budget, 'direction-legacy',
                                          approved_direction=approved)
        assert json.loads(task.payload['messages'][-1]['content'])['approved_direction'] == approved
        assert '只提交一个' in task.payload['messages'][0]['content']
        if alternatives:
            with pytest.raises(ValueError, match='INVALID_STRUCTURED_OUTPUT'):
                _run_plan(store, task, package, model, config(store))
        else:
            proposal = _run_plan(store, task, package, model, config(store))
            assert len(proposal.candidate_cards) == 1
