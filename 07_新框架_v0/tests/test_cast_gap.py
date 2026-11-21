import json
from copy import deepcopy

import pytest

from nw.materials.phase_projection import verify_chain
from nw.materials.work_session import drive_plan
from nw.store import Store
from project_methods_fixture import ProjectModel
from test_casting_editor import BRIEF, output, planned
from test_material_phase_flow import PhaseModel, template_catalog
from test_novel_flow import config


class PlotGapModel(PhaseModel):
    def __init__(self, *, reuse=False, interrupt=False):
        super().__init__()
        self.reuse = reuse
        self.interrupt = interrupt
        self.original = None

    def generate(self, messages, **params):
        data = json.loads(messages[-1]['content'])
        stage = data.get('stage')
        if '[CASTING_EDITOR]' in messages[0]['content']:
            self.calls.append(messages)
            return output({'judgments': [{'id': d['id'], 'verdict': 'accept',
                           'reason': '验印者与登记职责有具体的交接时刻可核对'} for d in data['demands']]})
        if stage == 'plot_design' and 'cast_gap_format' in data:
            self.calls.append(messages)
            initial = data['inputs']['world_design']['products']['cast_demands'][0]
            actor = self.original['products']['members'][0]
            obstacle = '书册交给验印人以后，交接时刻还没有登记'
            responsibility = {**initial, 'id': 'record_transfer', 'need_ref': 'plot-gap:register:obstacle',
                              'need_quote': obstacle, 'obstacle': obstacle,
                              'action': '在交接簿写下验印时刻', 'result': '交接双方都能核对验印时间',
                              'slot': initial['slot'] if self.reuse else 'independent_witness'}
            turn = {'id': 'register', 'source_ref': 'brief:text', 'source_quote': BRIEF,
                    'event': initial['event'], 'obstacle': obstacle, 'change': responsibility['result'],
                    'current_cast': [{'demand': responsibility['id'], 'actor': actor['key'], 'field': 'boundaries',
                        'quote': actor['body']['boundaries'],
                        'decision': 'reuse' if self.reuse else 'unavailable',
                        'reason': '自己验印可以记下时刻' if self.reuse else '独立见证人不能由经手人兼任'}]}
            return output({'stage': stage, 'cast_gap': {'turns': [turn], 'cast_demands': [responsibility]}})
        if stage == 'character_design' and 'plot_cast_gap' in data:
            self.calls.append(messages)
            if self.interrupt:
                self.interrupt = False
                return output({'stage': stage, 'products': {}})
            revised = deepcopy(self.original)
            products = revised['products']
            assert data['previous_cast']['members'] == products['members']
            demand = data['frozen_cast_demands'][-1]
            key = products['members'][0]['key']
            if not self.reuse:
                key = 'registrar'
                body = deepcopy(products['members'][0]['body'])
                body.update(name='见证人', role='交接簿的值守人', scene_function=demand['action'])
                body['casting'].update(standing='ordinary', entry='self', public_identity='值守人',
                                       need_ref=demand['need_ref'], need_quote=demand['need_quote'])
                products['members'].append({'key': key, 'kind': 'character', 'body': body})
                products['capabilities'].append({**products['capabilities'][0], 'entity': key})
            products['cast_assignments'].append({'demand': demand['id'], 'actor': key})
            return output(revised)
        result = super().generate(messages, **params)
        if stage == 'character_design':
            self.original = json.loads(result.text)
        if stage == 'plot_design' and 'plot_cast_gap' in data and not self.reuse:
            value = json.loads(result.text)
            node = value['products']['event_nodes'][0]
            node['actors'].append('registrar')
            value['products']['cast_events'].append({'demand': 'record_transfer', 'event': node['id']})
            return output(value)
        return result


@pytest.mark.parametrize('field', ['name', 'background', 'boundaries', 'behavior'])
def test_reused_key_cannot_change_the_person_or_the_evidence_for_reuse(tmp_path, field):
    class DisguisedActor(PlotGapModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            packet = json.loads(messages[-1]['content'])
            if 'cast_gap_format' in packet and field == 'behavior':
                raw = json.loads(result.text)
                assessed = raw['cast_gap']['turns'][0]['current_cast'][0]
                assessed.update(field=field, quote=self.original['products']['members'][0]['body'][field])
                return output(raw)
            if packet.get('stage') == 'character_design' and 'plot_cast_gap' in packet:
                value = json.loads(result.text)
                value['products']['members'][0]['body'][field] = '调包后的姓名、经历或权限'
                return output(value)
            return result

    template_catalog(tmp_path)
    model = DisguisedActor(reuse=True)
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        request, package = planned(store, model)
        with pytest.raises(ValueError, match='回补不能改写同一人'):
            drive_plan(store, request, package, model, config(store))


@pytest.mark.parametrize(('reuse', 'interrupt'), [(False, True), (True, False)])
def test_late_plot_duty_rebuilds_cast_relations_and_plot_with_frozen_evidence(tmp_path, reuse, interrupt):
    template_catalog(tmp_path)
    model = PlotGapModel(reuse=reuse, interrupt=interrupt)
    folder = tmp_path / 'story'
    with Store(folder, create=True, test_mode=True) as store:
        request, package = planned(store, model)
        if interrupt:
            with pytest.raises(ValueError):
                drive_plan(store, request, package, model, config(store))
    with Store(folder, test_mode=True) as store:
        _, revised = drive_plan(store, request, package, model, config(store), retry_failed=interrupt)
        session = revised['material_work']
        history = session['cast_repair']
        regular = {r['stage']: r for r in session['stages']}
        initial = history['superseded']['character_design']['products']
        final = regular['character_design']['products']
        assert len(final['members']) == len(initial['members']) + int(not reuse)
        before = initial['cast_assignments'][0]['actor']
        assert final['cast_assignments'][-1]['actor'] == (before if reuse else 'registrar')
        assert any(r['demand'] == 'record_transfer' for r in regular['plot_design']['products']['cast_events'])
        for stage in ('character_design', 'static_relations'):
            old = history['superseded'][stage]['task_id']
            assert old != regular[stage]['task_id']
            assert old not in {ref['task_id'] for r in regular.values() for ref in r['inputs']}
        broken = deepcopy(session)
        broken['context']['plot_cast_gap']['turns'][0]['change'] += '无来源的变动'
        with pytest.raises(ValueError, match='回补'):
            verify_chain(broken)
        count = len(model.calls)
    with Store(folder, test_mode=True) as store:
        assert drive_plan(store, request, package, model, config(store), retry_failed=interrupt)[1] == revised
        assert drive_plan(store, request, revised, model, config(store))[1] == revised
        assert len(model.calls) == count


class ProjectPlotGapModel(PlotGapModel, ProjectModel):
    pass


def test_second_unresolved_plot_gap_reports_the_specific_action_without_another_restart(tmp_path):
    class StillBlocked(PlotGapModel):
        def generate(self, messages, **params):
            packet = json.loads(messages[-1]['content'])
            if 'cast_gap_limit_instruction' in packet:
                self.calls.append(messages)
                return output({'stage': 'plot_design', 'cast_gap': packet['plot_cast_gap']})
            return super().generate(messages, **params)

    template_catalog(tmp_path)
    model = StillBlocked()
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        request, package = planned(store, model)
        with pytest.raises(ValueError, match='仍缺角色.*在交接簿写下验印时刻'):
            drive_plan(store, request, package, model, config(store))
        stages = [json.loads(call[-1]['content']).get('stage') for call in model.calls]
        assert stages.count('character_design') == stages.count('plot_design') == 2
        assert 'bind_scope' not in stages


def test_budget_exhausted_on_gap_cannot_create_cards_and_resumes_from_paid_turns(tmp_path):
    from nw.call_budget import BudgetExceeded, create_budget, extend_budget, read_budget
    from nw.planning import prepare_plan_task
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline

    template_catalog(tmp_path)
    model = PlotGapModel()
    folder = tmp_path / 'story'
    with Store(folder, create=True, test_mode=True) as store:
        store.init_project('限额内回补')
        store.add_brief(BRIEF)
        adopt_story(store, baseline(), {})
        budget = create_budget(store, 'limited', Budget(7, 160000, 8000))
        request, package = prepare_plan_task(store, 1, 'book', model, config(store), budget, 'limited-repair')
        with pytest.raises((ValueError, BudgetExceeded), match='(?i)budget'):
            drive_plan(store, request, package, model, config(store))
        count = len(model.calls)
        assert read_budget(store, budget).used_calls == count == 7
        assert 'cast_gap_format' in json.loads(model.calls[-1][-1]['content'])
    with Store(folder, test_mode=True) as store:
        extend_budget(store, budget, 20, None)
        _, revised = drive_plan(store, request, package, model, config(store), retry_failed=True)
        assert 'cast_repair' in revised['material_work']
        later = [json.loads(call[-1]['content']) for call in model.calls[count:]]
        assert all('cast_gap_format' not in packet for packet in later)
        assert read_budget(store, budget).used_calls == len(model.calls)


def test_repaired_plot_method_approval_uses_revised_character_version_and_can_refresh(tmp_path, monkeypatch):
    from nw.novel_flow import resume_job
    from nw.production_methods.refresh import refresh_pending
    from nw.story_state import adopt_story
    from project_methods_fixture import approve_method_gate, seed_method
    from story_fixture import baseline
    from test_project_methods import approve_direction, start

    template_catalog(tmp_path)
    seed_method(tmp_path, monkeypatch, input_kind='character_design')
    model = ProjectPlotGapModel()
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('补人后重选本轮方法')
        store.add_brief(BRIEF)
        adopt_story(store, baseline(), {})
        job, first = start(store, model)
        first_gate = first.outputs['gate']
        assert first_gate['stage'] == 'plot_design'
        def approve_initial(step, target):
            return None if target.get('cast_revision') else approve_method_gate(step, target)
        second = resume_job(store, job.id, model, config(store), approve_initial)
        assert second.status == 'WAITING', second.reason
        second_gate = second.outputs['gate']
        assert second_gate['stage'] == 'plot_design' and second_gate['cast_revision']
        first_ref, second_ref = (g['candidates'][0]['inputs']['i1']['ref'] for g in (first_gate, second_gate))
        assert first_ref['task_id'] != second_ref['task_id'] and first_ref['sha256'] != second_ref['sha256']
        assert refresh_pending(store, job.id, second_gate['token']) == (second_gate, False)
        final = approve_direction(store, job, model, second)
        assert final.status == 'DONE', final.reason
