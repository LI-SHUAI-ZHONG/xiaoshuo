"""Exercise C00025 through the client design, writing, review and acceptance jobs on isolated data."""
from copy import deepcopy
import json

import pytest

import ai_world_method_fixture as reference
import test_material_world_conversion_flow as six
from nw.materials.evidence import scene_checks, scene_materials
from nw.materials.phase_flow import STAGE_MATERIALS
from nw.materials.phase_projection import verify_chain
from nw.materials.stage_input import step_uses
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest, start_job
from nw.production_methods.contracts import at
from nw.store import Store
from nw.task_models import Budget
from project_methods_fixture import config
from test_project_methods import approve_direction, start
from test_stage_network_design_flow import Edge, NetworkDesignModel
from test_world_action_design_delivery import GOAL, LIMIT, RULE, SPELL
from test_world_method_creation_flow import finish_design, new_project, packets, policy, stages


EDGE = Edge('C00025', '10.1_能量总量 / 16.1_消耗速率 / 约束', '总量影响消耗',
            '当起点成立时，限制终点可采取的状态或行为范围。')
NEED = '[FAKE] 井底传来的回声是判断封条被谁动过的旁证。查验人需要在灵力耗尽前核对刻痕。'
LEGAL = '[FAKE] 沈砚在井旁施展回声术，每息耗两格，维持两息便停手，只听清首道刻痕。'
OVERDRAW = '[FAKE] 沈砚在井旁施展回声术，每息耗两格，连续维持十息成功听清全部刻痕。'
OMITTED_OVERDRAW = LEGAL + '\n' + OVERDRAW.removeprefix('[FAKE] ')
UNRELATED_DURATIONS = LEGAL + (
    '\n梁亭在另一口井施展回声术，连续维持十息成功听清全部刻痕。'
    '沈砚笑道：“我在井旁施展回声术，连续维持十息成功听清全部刻痕。”'
    '沈砚想起去年自己在旧井施展回声术，连续维持十息成功听清全部刻痕。'
    '沈砚设想若有足够灵力，自己或可施展回声术维持十息。')


def compile_edge(path, monkeypatch):
    world = step_uses(STAGE_MATERIALS['world_design'])[EDGE.dynamic_key]
    action = step_uses(STAGE_MATERIALS['action_design'])[EDGE.static_key]
    dynamic = f'### {EDGE.dynamic_key}\n【本步用法】\n{world}\n'
    static = f'### {EDGE.static_key}\n【本步用法】\n{action}\n'
    monkeypatch.setattr(six, 'SELECTED_GENRE', (reference.TAXON, '悬疑'))
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', dynamic + static)
    six._catalog(path, monkeypatch, (EDGE,))
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', dynamic)
    monkeypatch.setitem(STAGE_MATERIALS, 'action_design', static)
    # The synthetic type catalogue contains only its two genre identities.
    monkeypatch.setattr('nw.materials.dynamic_screening.load_dynamic_screening', lambda _: None)


class ConsumptionModel(NetworkDesignModel):
    def __init__(self, action_text, first_draft):
        super().__init__()
        self.action_text = action_text
        self.first_draft = first_draft
        self.review_verdicts = []

    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        data = json.loads(messages[-1]['content'])
        if any(item['source'].startswith('material:work:design-network:') for item in data.get('items', [])):
            result.text = self.first_draft
            return result
        if '只输出完整修订正文' in messages[0]['content']:
            result.text = LEGAL
            return result
        if 'material_review' in data:
            verdict = json.loads(result.text)
            [obligation] = [r for r in data['material_review']['checks'] if r.get('network_design_key') == EDGE.dynamic_key]
            check = next(r for r in verdict['material_checks'] if r['id'] == obligation['id'])
            if data['draft']['text'] in (OMITTED_OVERDRAW, UNRELATED_DURATIONS):
                # A plausible but incomplete citation: the reviewer only quotes the compliant opening.
                [span] = check['evidence']
                span.update(start=0, end=len(LEGAL), quote=LEGAL)
                result.text = json.dumps(verdict, ensure_ascii=False)
            self.review_verdicts.append((verdict['recommendation'], check['status'], check['evidence'][0]['quote']))
            return result
        stage = data.get('stage')
        if stage not in ('type_adaptation', 'world_design', 'character_design', 'plot_design', 'action_design', 'scene_design'):
            return result
        value = json.loads(result.text)
        if 'products' not in value:
            return result
        products = value['products']
        if stage == 'type_adaptation':
            products['adaptations'][0]['parameters']['investigation'] = NEED
        elif stage == 'world_design':
            for demand in products.get('cast_demands', []):
                demand.update(event=GOAL, action='在井边施展回声术', result='只听清第一道刻痕')
            if data.get('production_methods'):
                products['members'][0]['body'].update(title='旧港雾井', rule=RULE, limits=LIMIT)
                for application in products['_method_applications']:
                    for output in application['outputs']:
                        for place in output['placements']:
                            place['value'] = deepcopy(at(products, place['path']))
        elif stage == 'character_design':
            for capability in products['capabilities']:
                capability.update(abilities=[SPELL, '观察印痕'], limits=['回声术每息耗两格灵力。'])
        elif stage == 'plot_design':
            for event in products['event_nodes']:
                event.update(goal=GOAL, setting='旧港雾井')
        elif stage == 'action_design':
            [action] = products['candidates']
            row = next(r for r in data['network_design_candidates']
                       if r['actor'] == action['actor'] and r['event'] == action['event'] and r['key'] == EDGE.dynamic_key)
            action.update(action=self.action_text, requires=[SPELL], cost='每息耗两格灵力。', limits=[LIMIT])
            action['steps'][0].update(object='井壁刻痕', action='在井边施展回声术', obstacle='第二声越来越弱',
                                      response='停止施术', result='只听清第一道刻痕')
            products['_network_design_uses'] = [{'id': row['id'], 'operation': LEGAL, 'output_refs': ['/candidates/0/action']}]
        elif stage == 'scene_design':
            [row] = [r for r in data['network_design_candidates'] if r['key'] == EDGE.dynamic_key and r['required']]
            products['members'][0]['body']['conflict'] = LEGAL
            products['_network_design_uses'] = [{'id': row['id'], 'operation': LEGAL, 'output_refs': ['/members/0/body/conflict']}]
        result.text = json.dumps(value, ensure_ascii=False)
        return result


@pytest.mark.parametrize(('action_text', 'first_draft'), [
    (LEGAL, LEGAL), (OVERDRAW, LEGAL), (LEGAL, OVERDRAW), (LEGAL, OMITTED_OVERDRAW), (LEGAL, UNRELATED_DURATIONS),
], ids=['two-breaths', 'ten-breath-design', 'ten-breath-draft', 'omitted-ten-breaths', 'unrelated-times'])
def test_consumption_from_approved_project_design_to_review(tmp_path, monkeypatch, action_text, first_draft):
    compile_edge(tmp_path, monkeypatch)
    reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    model = ConsumptionModel(action_text, first_draft)
    path = tmp_path / 'fiction'
    with Store(path, create=True, test_mode=True) as store:
        new_project(store, NEED)
        book = finish_design(store, model)
        chapter, outcome = start(store, model, 'chapter', book.outputs['proposal_id'], policy())
        action_call = packets(model, 'action_design')[-1]
        [offer] = [r for r in action_call['network_design_candidates'] if r['key'] == EDGE.dynamic_key]
        assert (offer['ability'], offer['consumption']['maximum']) == (SPELL, '2')
        if action_text == OVERDRAW:
            assert outcome.status == 'BLOCKED' and '可用储量' in outcome.reason, outcome.reason
            assert not packets(model, 'scene_design')
            return
        assert outcome.status == 'WAITING', outcome.reason
        approved = approve_direction(store, chapter, model, outcome)
        assert approved.status == 'DONE', approved.reason
        application = approved.outputs['application']
        session = application['material_design']['work_session']
        verify_chain(session)
        action = stages(session)['action_design']['products']['candidates'][0]
        scene = stages(session)['scene_design']['products']
        assert scene['selected_actions'][0]['action'] == action['id']
        assert scene['selected_events'][0]['event'] == offer['event'] == action['event']
        [published] = application['chapters'][0]['scenes']
        scene_id = published['scene_id']

    with Store(path, test_mode=True) as store:
        [guide] = [c for c in scene_checks(scene_materials(store, scene_id))
                   if c.get('network_design_key') == EDGE.dynamic_key]
        assert '维持两息' in guide['binding']['observable']
        names = [e['value'] for e in guide['method_artifact']['prerequisites'] if e['ref'].endswith('/body/name')]
        assert names == ['沈砚']
        job = start_job(store, JobRequest('write', scene_ids=[scene_id], budget=Budget(20, 200000, 6000)))
        draft = resume_job(store, job.id, model, config(store))
        assert draft.status == 'WAITING' and draft.step == 'batch:confirm', draft.reason
        reviews = [p for m in model.calls if 'material_review' in (p := json.loads(m[-1]['content']))]
        revised = first_draft in (OVERDRAW, OMITTED_OVERDRAW)
        expected = [first_draft, LEGAL] if revised else [first_draft]
        assert [r['draft']['text'] for r in reviews] == expected
        assert all(guide in r['material_review']['checks'] for r in reviews)
        quotes = [LEGAL if text in (OMITTED_OVERDRAW, UNRELATED_DURATIONS) else text for text in expected]
        assert model.review_verdicts == [('pass', 'pass', quote) for quote in quotes]
        if revised:
            [revision] = [json.loads(m[-1]['content']) for m in model.calls if '只输出完整修订正文' in m[0]['content']]
            assert revision['draft']['text'] == first_draft
            assert revision['review']['recommendation'] == 'revise'
            assert {'id': guide['id'], 'status': 'failed'} in revision['review']['material_checks']
        assert not store.list('accepted')
        accepted = resume_job(store, job.id, model, config(store),
                              lambda *_: {'action': 'accept', 'reason': '[FAKE] 使用两息、耗能和停止施术均与本场一致。'})
        assert accepted.status == 'DONE', accepted.reason

    with Store(path, test_mode=True) as store:
        archived = store.drafts(scene_id)
        assert [(r.version, r.text) for r in archived] == list(enumerate(expected, 1))
        [accepted_record] = store.list('accepted')
        assert accepted_record.draft_id == archived[-1].id
