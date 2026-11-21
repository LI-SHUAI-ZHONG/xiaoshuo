"""[FAKE] Approve one promise choice through normal book/chapter jobs and reject substituted outcomes."""
import json

import pytest

import ai_world_method_fixture as reference
import test_material_world_conversion_flow as six_source
from nw.materials.evidence import scene_checks, scene_materials
from nw.materials.phase_flow import STAGE_MATERIALS
from nw.materials.phase_projection import verify_chain
from nw.materials.stage_input import step_uses
from nw.store import Store
from test_project_methods import start
from test_stage_network_design_flow import Edge
from test_world_method_creation_flow import finish_design, new_project, packets, policy

PROMISE = Edge('C00655', '3.4_责任 / 74.5_义务 / 触发', '激活', '当起点条件成立时，推动终点进入下一状态。')
BRIEF = '[FAKE] 渡吏调查封蜡之余，要在冬至前归还向祖母借走的旧船，木材商又想雇用这条船。'
KEEP = '[FAKE] 沈砚在冬至前把旧船交还给祖母，再到岸亭核验封蜡。'
BREAK = '[FAKE] 沈砚拒绝归还旧船而食言，祖母因此只得另租一船出港。'
CHOICE = '[FAKE] 沈砚拒绝把旧船归还祖母，决定食言。'
AFTERMATH = '[FAKE] 祖母因此只得另租一条船出港。'
FALSE = '[FAKE] 沈砚改替雇主护送木材去北山，把这件差事算作已经兑现对祖母归还旧船的承诺。'


def setup_library(path, monkeypatch):
    original = step_uses(STAGE_MATERIALS['character_design'])
    material = ''.join(f'### {k}\n【本步用法】\n{original[k]}\n' for k in (PROMISE.static_key, PROMISE.dynamic_key))
    monkeypatch.setattr(six_source, 'SELECTED_GENRE', (reference.TAXON, '悬疑'))
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', material)
    six_source._catalog(path, monkeypatch, (PROMISE,))
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', '')
    monkeypatch.setitem(STAGE_MATERIALS, 'character_design', material)
    monkeypatch.setattr('nw.materials.dynamic_screening.load_dynamic_screening', lambda _: None)
    reference.available_method(path, monkeypatch, scopes=('book',))


class PromiseModel(reference.WorldModel):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def generate(self, messages, **kwargs):
        result = super().generate(messages, **kwargs)
        packet = json.loads(messages[-1]['content'])
        stage = packet.get('stage')
        if stage not in ('character_design', 'plot_design', 'scene_design', 'state_transition'):
            return result
        data = json.loads(result.text)
        if 'products' not in data:
            return result
        value = data['products']
        if stage == 'character_design':
            for person in value['members']:
                person['body'].update(
                    relationship='[FAKE] 沈砚答应祖母在冬至前送回旧船。', want='[FAKE] 他准备把旧船归还给祖母。',
                    behavior='[FAKE] 一见到旧船上的祖母刻印，就回港检查船况。')
        if stage in ('plot_design', 'scene_design'):
            [row] = [r for r in packet['network_design_candidates'] if r['key'] == 'C00655']
            text = {'breach': BREAK, 'split_breach': CHOICE}.get(self.case, KEEP)
            if stage == 'plot_design':
                path = '/directions/0/consequence'
                if self.case == 'false_plot':
                    text = FALSE
                if self.case == 'split_breach':
                    path = '/directions/0/conflict'
                    value['directions'][0]['conflict'] = text
                    value['directions'][0]['consequence'] = AFTERMATH
                else:
                    value['directions'][0]['consequence'] = text
            else:
                path = '/members/0/body/conflict'
                value['members'][0]['body']['conflict'] = text
                if self.case == 'split_breach':
                    value['members'][0]['body']['planned_result'] = AFTERMATH
            value['_network_design_uses'] = [{'id': row['id'], 'operation': text, 'output_refs': [path]}]
        if stage == 'state_transition' and self.case == 'split_breach':
            value['patches'][0].update(choice=CHOICE, planned_result=AFTERMATH)
        if stage == 'state_transition' and self.case == 'false_result':
            value['patches'][0]['planned_result'] = FALSE
        result.text = json.dumps(data, ensure_ascii=False)
        return result


@pytest.mark.parametrize('case', ['keep', 'breach', 'split_breach', 'false_plot', 'false_result'])
def test_adopted_promise_reaches_only_its_project_scene_or_blocks_on_false_fulfilment(tmp_path, monkeypatch, case):
    setup_library(tmp_path, monkeypatch)
    model = PromiseModel(case)
    with Store(tmp_path / '[FAKE]-promise', create=True, test_mode=True) as store:
        new_project(store, BRIEF)
        if case == 'false_plot':
            _, outcome = start(store, model, policy=policy())
            assert outcome.status == 'BLOCKED' and '承诺采用' in outcome.reason, outcome.reason
            return
        book = finish_design(store, model)
        parent = book.outputs['proposal_id']
        if case == 'false_result':
            _, outcome = start(store, model, 'chapter', parent, policy())
            assert outcome.status == 'BLOCKED' and '承诺采用' in outcome.reason, outcome.reason
            assert packets(model, 'state_transition') and not packets(model, 'anchor_design')
            return
        chapter = finish_design(store, model, 'chapter', parent)
        application = chapter.outputs['application']
        session = application['material_design']['work_session']
        verify_chain(session)
        [scene] = packets(model, 'scene_design')
        [row] = [r for r in scene['network_design_candidates'] if r['key'] == 'C00655']
        assert row['required'] and row['commitment']['promisee'] == '祖母' and row['commitment']['subject'] == '旧船'
        actual = application['chapters'][0]['scenes'][0]['scene_id']
        [guide] = [r for r in scene_checks(scene_materials(store, actual)) if r.get('network_design_key') == 'C00655']
        assert guide['binding']['observable'] == {'breach': BREAK, 'split_breach': CHOICE}.get(case, KEEP)
