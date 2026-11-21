import json
from copy import deepcopy

import pytest

from nw.call_budget import create_budget
from nw.llm.base import GenResult
from nw.materials.casting_editor import _inputs, _judgments, world_conditions
from nw.materials.phase_projection import verify_chain
from nw.materials.work_session import drive_plan
from nw.planning import prepare_plan_task
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_phase_flow import PhaseModel, template_catalog
from test_novel_flow import config


PRICE = '[FAKE] 只替隔壁茶楼报糕点价钱'
BRIEF = '须有人当面交接旧册，验清名册上的新旧印记。'


def output(value):
    return GenResult(json.dumps(value, ensure_ascii=False), 'complete', {}, 'test', {'isolated_test': True})


class CastingModel(PhaseModel):
    def __init__(self, *, repair=True, change_card=False):
        super().__init__()
        self.repair = repair
        self.change_card = change_card
        self.original = []

    def generate(self, messages, **params):
        prompt = messages[0]['content']
        data = json.loads(messages[-1]['content'])
        if '[CASTING_EDITOR]' in prompt:
            self.calls.append(messages)
            assert BRIEF in data['plot_sources'].values()
            return output({'judgments': [
                {'id': d['id'], 'verdict': 'redesign' if d['action'] == PRICE else 'accept',
                 'reason': '[FAKE] 报价不能交付旧册或让印记可查' if d['action'] == PRICE else '[FAKE] 实物交付可供查验印记'}
                for d in data['demands']]})
        if '[CASTING_REDESIGN]' in prompt:
            self.calls.append(messages)
            assert data['corrections'] and data['world_ref']['stage'] == 'world_design'
            return output({'cast_demands': self.original if self.repair else data['demands']})
        result = super().generate(messages, **params)
        if '[MATERIAL_STEP]' in prompt and data['stage'] == 'world_design':
            value = json.loads(result.text)
            self.original = deepcopy(value['products']['cast_demands'])
            value['products']['cast_demands'][0]['action'] = PRICE
            return output(value)
        if self.change_card and '[MATERIAL_STEP]' in prompt and data['stage'] == 'character_design':
            value = json.loads(result.text)
            value['products']['members'][0]['body']['scene_function'] = PRICE
            return output(value)
        return result


def planned(store, model):
    store.init_project('按交接旧册的剧情选人')
    store.add_brief(BRIEF)
    adopt_story(store, baseline(), {})
    budget = create_budget(store, 'casting', Budget(40, 160000, 8000))
    return prepare_plan_task(store, 1, 'book', model, config(store), budget, 'cast-before-cards')


@pytest.mark.parametrize(('repair', 'change_card'), [(False, False), (True, True), (True, False)])
def test_normal_planning_requires_causal_use_before_casting_and_resumes(tmp_path, repair, change_card):
    template_catalog(tmp_path)
    model = CastingModel(repair=repair, change_card=change_card)
    folder = tmp_path / 'story'
    with Store(folder, create=True, test_mode=True) as store:
        request, package = planned(store, model)
        if not repair or change_card:
            reason = '报价不能交付旧册' if not repair else '分派的具体行动'
            with pytest.raises(ValueError, match=reason):
                drive_plan(store, request, package, model, config(store))
            stages = [json.loads(call[-1]['content']).get('stage') for call in model.calls]
            assert ('character_design' in stages) == change_card
            assert 'plot_design' not in stages
            return
        _, result = drive_plan(store, request, package, model, config(store))
        work = result['material_work']
        world = next(row for row in work['stages'] if row['stage'] == 'world_design')
        assert world['products']['cast_demands'] == model.original
        assert world['cast_demand_revision']['demands'][0]['action'] == PRICE
        assert world['cast_editor_review']['judgments'][0]['verdict'] == 'accept'
        order = [json.loads(call[-1]['content']).get('stage') or (
            'redesign' if '[CASTING_REDESIGN]' in call[0]['content'] else 'editor') for call in model.calls]
        assert order[order.index('world_design'):order.index('character_design') + 1] == [
            'world_design', 'editor', 'redesign', 'editor', 'character_design']
        count = len(model.calls)
    with Store(folder, test_mode=True) as store:
        _, reopened = drive_plan(store, request, package, model, config(store))
        assert reopened['material_work'] == work and len(model.calls) == count
        broken = deepcopy(work)
        next(row for row in broken['stages'] if row['stage'] == 'world_design')['cast_editor_review']['input_sha256'] = 'stale'
        with pytest.raises(ValueError, match='当前剧情前置'):
            verify_chain(broken)


def test_editor_must_decide_each_role_exactly_once():
    demands = [{'id': 'transfer'}, {'id': 'witness'}]
    first = {'id': 'transfer', 'verdict': 'accept', 'reason': '交付后才能核验'}
    with pytest.raises(ValueError, match='对象'):
        _judgments({'judgments': [first, first]}, demands)


def test_editor_sees_pinned_limits_and_the_available_actors_state_before_allowing_reuse():
    actor = {'card_id': 'porter', 'kind': 'character', 'body': {'role': '值守人', 'want': '保护弟弟'}}
    rule = {'card_id': 'registry', 'kind': 'world', 'body': {'rule': '交册须有签字', 'limits': '钥匙只能开柜'}}
    fact = {'entity_id': 'key', 'holder': 'porter', 'predicate': 'custody', 'claim': 'knowledge', 'value': '钥匙已归还'}
    context = {'scope': 'chapter', 'approved_cards': [actor, rule], 'accepted_state': [fact],
               'brief': {'text': BRIEF}, 'cast_prior_work': [{'designed_action': '登记过旧册',
                   'evidence': [{'quote': '他把收册的日期写进了簿子。'}]}]}
    context['cast_world_conditions'] = world_conditions({'members': [], 'limitations': []}, context)
    packet = _inputs(context, [])
    assert packet['world_conditions']['rules']['registry']['limits'] == '钥匙只能开柜'
    assert packet['branch_facts'] == [fact] and packet['prior_performances'] == context['cast_prior_work']
