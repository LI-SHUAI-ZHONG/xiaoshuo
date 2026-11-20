"""[FAKE] Prior-step requirements, frozen network evidence and scene-level use in real design jobs."""
from copy import deepcopy
import json
from pathlib import Path
from typing import NamedTuple

import pytest

import ai_world_method_fixture as reference
import test_material_world_conversion_flow as six_source
import test_planning
from project_methods_fixture import config
from nw.llm.base import GenResult
from nw.materials.evidence import scene_checks, scene_materials
from nw.materials.phase_flow import STAGE_MATERIALS
from nw.materials.phase_projection import verify_chain
from nw.materials.phase_routes import product_ref
from nw.materials.stage_input import step_uses
from nw.production_methods.contracts import at
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest, start_job
from nw.store import Store
from nw.task_models import Budget, content_sha256
from test_project_methods import approve_direction, start
from test_world_method_creation_flow import finish_design, new_project, packets, policy, stages


class Edge(NamedTuple):
    dynamic_key: str
    static_key: str
    condition: str
    effect: str


AUTHORITY = Edge('C00738', '33.3_权力结构 / 33.4_执行机制 / 转化', '权力决定执行',
                 '当起点成立并满足转化条件时，将起点状态转为终点状态。')
PROFESSION = Edge('C00835', '39.3_职业与能力 / 2.5_角色能力 / 嵌套', '职业需要能力',
                  '当起点成立时，终点作为起点的一部分参与当前状态。')
RULE = '[FAKE] 港务官以双印令授权临川渡放行货船，渡吏收到授权后须比对闸簿封蜡和岸亭回执，验印后才可开闸。'
LIMIT = '[FAKE] 岸亭回执未送达或缺一枚印时，渡吏必须拒绝放行、登记缺据并向船工签发书面回执。'
ROLE = '[FAKE] 临川渡验印渡吏，负责核验闸簿封蜡和岸亭回执。'
ABILITY = '辨印验签'
NEED = '[FAKE] 临川渡双印令的权力结构如何变成真实执行机制，职业与能力如何约束渡吏辨印验签时的选择？'


def catalogue(path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, tuple[str, str]]:
    """Compile the two original edges, using their actual stage texts and isolated source IDs."""
    uses = {}
    for stage, edge in [('world_design', AUTHORITY), ('character_design', PROFESSION)]:
        original = step_uses(STAGE_MATERIALS[stage])
        uses[stage] = ''.join(f'### {key}\n【本步用法】\n{original[key]}\n'
                              for key in (edge.static_key, edge.dynamic_key))
    monkeypatch.setattr(six_source, 'SELECTED_GENRE', (reference.TAXON, '悬疑'))
    # The existing catalogue fixture reads all fixture inputs from world_design before assigning stages.
    monkeypatch.setitem(STAGE_MATERIALS, 'world_design', '\n'.join(uses.values()))
    pairs = six_source._catalog(path, monkeypatch, (AUTHORITY, PROFESSION))
    # The isolated type catalogue contains the two genre identities, without the production TDF_001 fragment.
    monkeypatch.setattr('nw.materials.dynamic_screening.load_dynamic_screening', lambda _: None)
    for stage, material in uses.items():
        monkeypatch.setitem(STAGE_MATERIALS, stage, material)
    return pairs


class TwoScenes(test_planning.Planner):
    def __init__(self, scope: str) -> None:
        super().__init__(scope)
        if scope == 'book':
            return
        for candidate in self.output['candidate_cards']:
            first = next(row for row in candidate['members'] if row['kind'] == 'scene')
            second = deepcopy(first)
            second['key'] = 'verification'
            second['body'].update(title='岸亭复核', goal='复查封蜡上的印记')
            candidate['members'].append(second)
            candidate['chapters'][0]['scenes'].append({'card': second['key'], 'index': 2, 'story_order': 2})


class BoatmanWitness(TwoScenes):
    def __init__(self, scope: str) -> None:
        super().__init__(scope)
        if scope == 'book':
            return
        for candidate in self.output['candidate_cards']:
            candidate['members'].append({'key': 'boatman', 'kind': 'character', 'body': {
                'name': '梁亭', 'role': '船工', 'want': '找回船货', 'visibility': 'public'}})
            scene = next(m for m in candidate['members'] if m['key'] == 'verification')
            scene['body'].update(pov='boatman', characters=['boatman'], character_goals={'boatman': '查船货'})


class NetworkDesignModel(reference.WorldModel):
    def __init__(self, *, invalid: str = '', taxon: str = reference.TAXON) -> None:
        super().__init__(taxon=taxon)
        self.defect = invalid

    def generate(self, messages: list[dict], **params) -> GenResult:
        response = super().generate(messages, **params)
        packet = json.loads(messages[-1]['content'])
        stage = packet.get('stage')
        if '{"operations"' in messages[0]['content']:
            known = {(r['entity_id'], r['predicate'], r['holder']): r['value']
                     for r in packet['context']['facts'] if r['claim'] == 'fact'}
            result = json.loads(response.text)
            for operation in result['operations']:
                operation['expected_old'] = known.get((operation['entity_id'], operation['predicate'], operation['holder']))
            response.text = json.dumps(result, ensure_ascii=False)
            return response
        draft_guidance = [json.loads(item['text']) for item in packet.get('items', [])
                          if item['source'].startswith('material:work:design-network:')]
        if draft_guidance:
            if ABILITY in draft_guidance[0]['observable']:
                response.text = '[FAKE] 沈砚包好手背的伤，辨印验签，指腹在错位的封蜡上停了一下。他把船扣在岸边，叫人去岸亭复核。'
            else:
                response.text = '[FAKE] 船工将岸亭回执递进闸窗。沈砚扒开封条，被铜丝划伤了手背，仍亮出收回的双印令，写下拒绝放行的缘由。'
            return response
        if stage not in ('type_selection', 'type_adaptation', 'world_design', 'character_design',
                         'plot_design', 'action_design', 'scene_design', 'state_transition', 'bind_scope'):
            return response
        value = json.loads(response.text)
        if 'products' not in value:
            return response
        products = value['products']
        if stage == 'bind_scope' and (requirements := packet.get('required_scene_sources')):
            independent = set(packet['scene_independent_sources'])
            for item in products['method_guidance']:
                item['source_ids'] = [s for s in item['source_ids'] if s in independent or s not in requirements
                                      or item['scene'] in requirements[s]]
            products['method_guidance'] = [item for item in products['method_guidance'] if item['source_ids']]
        elif stage == 'type_selection' and self.taxon != reference.TAXON:
            products['selection'][0]['label'] = '二次元'
        elif stage == 'type_adaptation':
            products['adaptations'][0]['parameters']['investigation'] = NEED
        elif stage == 'world_design' and packet.get('production_methods'):
            products['members'][0]['body'].update(title='[FAKE] 临川渡授权放行程序', rule=RULE, limits=LIMIT)
            for app in products['_method_applications']:
                for output in app['outputs']:
                    for place in output['placements']:
                        place['value'] = deepcopy(at(products, place['path']))
        elif stage == 'character_design':
            person = products['members'][0]
            person['body'].update(role=ROLE, strength=ABILITY, ability_cost='二次验签要耗用仅存的朱砂')
            for cap in products['capabilities']:
                if cap['entity'] == person['key']:
                    cap.update(abilities=[ABILITY, '观察印痕'],
                               basis='[FAKE] 沈砚通过渡吏任职验核，受权用辨印验签比对封蜡和岸亭回执。',
                               limits=['[FAKE] 没有岸亭回执时不得单独签放，须扣船复验。'])
        elif stage == 'state_transition':
            for transition in products['transitions']:
                if transition['before_state'].get('hand') == '划伤':
                    transition.update(after_state={'hand': '包扎'}, action='[FAKE] 复查伤口并包扎之后再查封蜡',
                                      continuity='[FAKE] 此后手背保持包扎状态直到拆下布条')
        elif stage in ('plot_design', 'action_design', 'scene_design'):
            if stage == 'scene_design' and len(products['events']) == 2:
                first, second = products['events']
                if second['entity'] == first['entity']:
                    second['before_state'] = {'hand': '划伤'}
            uses = []
            for row in packet.get('network_design_candidates', []):
                if row['key'] not in (AUTHORITY.dynamic_key, PROFESSION.dynamic_key):
                    continue
                if self.defect == 'skip':
                    continue
                action_test = self.defect in ('action_only', 'wrong_action_scene')
                if action_test and (row['key'] != PROFESSION.dynamic_key or stage == 'plot_design'):
                    continue
                if stage == 'action_design' and not action_test:
                    continue
                if self.defect == 'missing_scene' and stage == 'scene_design' and row['key'] == PROFESSION.dynamic_key:
                    continue
                is_world = row['key'] == AUTHORITY.dynamic_key
                field = 'conflict' if is_world else 'resistance'
                detail = ('[FAKE] 港务官收回双印令，船工只得出示岸亭回执，请守闸人书面说明为何拒绝放行。' if is_world else
                          '[FAKE] 渡吏沈砚用辨印验签查出封蜡被调换，缺少岸亭回执，只能先扣船再请站头复验。')
                if stage == 'plot_design':
                    products['directions'][0][field] = detail
                    paths = [f'/directions/0/{field}']
                elif stage == 'action_design':
                    products['candidates'][1]['steps'][0]['response'] = detail
                    paths = ['/candidates/1/steps/0/response']
                else:
                    position = 0 if is_world or self.defect == 'wrong_action_scene' else 1
                    products['members'][position]['body']['conflict'] = detail
                    paths = [f'/members/{position}/body/conflict']
                if self.defect == 'empty' and is_world and stage == 'plot_design':
                    for direction in products['directions']:
                        direction[field] = '已经依照此前批准的规则完成上述设计。'
                if self.defect == 'label' and not is_world and stage == 'plot_design':
                    paths = ['/directions/0/title']
                if self.defect == 'world_only' and not is_world and stage == 'plot_design':
                    products['directions'][0][field] = '[FAKE] 港务官要求船工递交岸亭回执，封存未放行的双印令。'
                uses.append({'id': row['id'], 'operation': detail, 'output_refs': paths})
            if uses:
                products['_network_design_uses'] = uses
        response.text = json.dumps(value, ensure_ascii=False)
        return response


def test_network_design_from_empty_cards_through_book_chapter_and_replay(tmp_path, monkeypatch):
    pairs = catalogue(tmp_path, monkeypatch)
    _, method = reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    monkeypatch.setattr(test_planning, 'Planner', TwoScenes)
    path = tmp_path / '[FAKE]-network-story'
    model = NetworkDesignModel()
    with Store(path, create=True, test_mode=True) as store:
        new_project(store, NEED)
        book = finish_design(store, model)
        book_session = book.outputs['application']['material_design']['work_session']
        chapter = finish_design(store, model, 'chapter', book.outputs['proposal_id'])
        application = chapter.outputs['application']
        session = application['material_design']['work_session']
        guidance = packets(model, 'world_design')[0]
        assert not guidance['approved_cards']
        assert method['id'] in [m['method']['id'] for m in guidance['production_methods']]
        assert AUTHORITY.dynamic_key in str(guidance['network_design_guidance'])
        assert PROFESSION.dynamic_key in str(packets(model, 'character_design')[0]['network_design_guidance'])
        for row in (book_session, session):
            verify_chain(row)
            character = stages(row)['character_design']
            assert character['products']['capabilities'][0]['abilities'][0] == ABILITY
        plot = packets(model, 'plot_design')[0]
        candidates = {r['key']: r for r in plot['network_design_candidates']}
        assert set(candidates) == set(pairs)
        assert all(c['evidence'] and all(e['value'] for e in c['evidence']) for c in candidates.values())
        assert candidates[AUTHORITY.dynamic_key]['member'] == 'seal'
        assert candidates[PROFESSION.dynamic_key]['member'] == 'yan'
        scene_call = packets(model, 'scene_design')[0]
        required = {r['key'] for r in scene_call['network_design_candidates'] if r['required']}
        assert required == set(pairs)
        for line in scene_call['network_design_candidates']:
            assert line['member'] == candidates[line['key']]['member']
            assert line['origin']['task_id'] != candidates[line['key']]['origin']['task_id']
        scene_rows = application['chapters'][0]['scenes']
        assert len(scene_rows) == 2
        for s, edge, marker in zip(scene_rows, (AUTHORITY, PROFESSION), ('岸亭回执', ABILITY), strict=True):
            [guide] = [c for c in scene_checks(scene_materials(store, s['scene_id']))
                       if c['id'].startswith('work:design-network:')]
            assert guide['network_design_key'] == edge.dynamic_key
            assert guide['profile'] == 'method_work' and guide['method_artifact']
            assert marker in guide['binding']['observable']
            write_job = start_job(store, JobRequest('write', scene_ids=[s['scene_id']], budget=Budget(20, 200000, 6000)))
            result = resume_job(store, write_job.id, model, config(store))
            assert result.status == 'WAITING', result.reason
            review = [p for m in model.calls if 'material_review' in (p := json.loads(m[-1]['content']))][-1]
            assert marker in review['draft']['text']
            assert [c for c in review['material_review']['checks'] if c['id'].startswith('work:design-network:')] == [guide]
            result = resume_job(store, write_job.id, model, config(store),
                                lambda *_: {'action': 'accept', 'reason': '[FAKE] 已核对本场落点与可见后果。'})
            assert result.status == 'DONE', result.reason
        proposal = chapter.outputs['proposal_id']

    with Store(path, test_mode=True) as reopened:
        raw = reopened.connection.execute('SELECT mapping_json FROM plan_applications WHERE proposal_id=?', (proposal,)).fetchone()
        recovered = json.loads(raw[0])['material_design']['work_session']
        verify_chain(recovered)
        changed = deepcopy(recovered)
        scene = stages(changed)['scene_design']
        scene['products']['_network_design_uses'][0]['output_refs'] = ['/members/1/body/title']
        scene['sha256'] = content_sha256(scene['products'])
        for row in changed['stages']:
            for ref in row['inputs']:
                if ref['stage'] == 'scene_design':
                    ref.update(product_ref(scene))
            if row.get('source_selection'):
                row['source_selection']['upstream'] = deepcopy(row['inputs'])
        with pytest.raises(ValueError, match='世界与人物方法须落实到本步允许的具体设计字段'):
            verify_chain(changed)


@pytest.mark.parametrize(('defect', 'reason'), [
    ('label', '须落实到本步允许的具体设计字段'), ('empty', '落点未保留'), ('world_only', '落点未保留'),
])
def test_unrelated_world_or_character_placement_cannot_publish(tmp_path, monkeypatch, defect, reason):
    catalogue(tmp_path, monkeypatch)
    reference.available_method(tmp_path, monkeypatch)
    model = NetworkDesignModel(invalid=defect)
    with Store(tmp_path/'[FAKE]-wrong-binding', create=True, test_mode=True) as store:
        new_project(store, NEED)
        _, outcome = start(store, model, policy=policy())
        assert outcome.status == 'BLOCKED' and reason in outcome.reason, outcome.reason
        assert not store.connection.execute('SELECT 1 FROM plan_applications').fetchone()


@pytest.mark.parametrize(('defect', 'cast', 'reason'), [
    ('missing_scene', TwoScenes, '本范围已采用的剧情设计缺少实际承接字段'),
    ('wrong_actor', BoatmanWitness, '人物资料被登记给本产物之外的人物'),
])
def test_chapter_must_deliver_an_adopted_ability_to_its_own_character(tmp_path, monkeypatch, defect, cast, reason):
    catalogue(tmp_path, monkeypatch)
    reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    monkeypatch.setattr(test_planning, 'Planner', cast)
    model = NetworkDesignModel(invalid=defect)
    with Store(tmp_path / '[FAKE]-missing-scene', create=True, test_mode=True) as store:
        new_project(store, NEED)
        book = finish_design(store, model)
        _, outcome = start(store, model, 'chapter', book.outputs['proposal_id'], policy=policy())
        assert outcome.status == 'BLOCKED' and reason in outcome.reason, outcome.reason
        [packet] = packets(model, 'scene_design')
        assert any(c['required'] and c['key'] == PROFESSION.dynamic_key for c in packet['network_design_candidates'])
        assert store.connection.execute('SELECT COUNT(*) FROM plan_applications').fetchone()[0] == 1


def test_chapter_does_not_inherit_methods_of_an_unselected_book_direction(tmp_path, monkeypatch):
    catalogue(tmp_path, monkeypatch)
    reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    monkeypatch.setattr(test_planning, 'Planner', TwoScenes)
    model = NetworkDesignModel()
    with Store(tmp_path / '[FAKE]-unused-direction', create=True, test_mode=True) as store:
        new_project(store, NEED)
        job, result = start(store, model, policy=policy())
        assert result.status == 'WAITING', result.reason
        alternative = result.outputs['gate']['candidates'][1]['root']['card_id']
        book = resume_job(store, job.id, model, config(store),
                          lambda *_: {'action': 'approve', 'reason': '[FAKE] 审核第二案', 'root': alternative})
        assert book.status == 'DONE', book.reason
        model.defect = 'skip'
        chapter = finish_design(store, model, 'chapter', book.outputs['proposal_id'])
        [scene] = packets(model, 'scene_design')
        assert not any(c['required'] for c in scene.get('network_design_candidates', []))
        for row in chapter.outputs['application']['chapters'][0]['scenes']:
            checks = scene_checks(scene_materials(store, row['scene_id']))
            assert not any(c['id'].startswith('work:design-network:') for c in checks)


@pytest.mark.parametrize('wrong_scene', [False, True])
def test_character_ability_follows_the_selected_action_into_its_actual_scene(tmp_path, monkeypatch, wrong_scene):
    catalogue(tmp_path, monkeypatch)
    reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    monkeypatch.setattr(test_planning, 'Planner', TwoScenes)
    model = NetworkDesignModel(invalid='wrong_action_scene' if wrong_scene else 'action_only')
    with Store(tmp_path / '[FAKE]-selected-action', create=True, test_mode=True) as store:
        new_project(store, NEED)
        book = finish_design(store, model)
        job, chapter = start(store, model, 'chapter', book.outputs['proposal_id'], policy=policy())
        [packet] = packets(model, 'scene_design')
        [ability] = [row for row in packet['network_design_candidates'] if row['key'] == PROFESSION.dynamic_key]
        assert ability['required'] and {d['candidate'] for d in ability['deliveries']} == {'lift_2'}
        if wrong_scene:
            assert chapter.status == 'BLOCKED' and '该场景的实际选择不一致' in chapter.reason, chapter.reason
        else:
            done = approve_direction(store, job, model, chapter)
            assert done.status == 'DONE', done.reason
            first, second = done.outputs['application']['chapters'][0]['scenes']
            for slot, expected in [(first, []), (second, [PROFESSION.dynamic_key])]:
                checks = scene_checks(scene_materials(store, slot['scene_id']))
                assert [c['network_design_key'] for c in checks if 'network_design_key' in c] == expected


def test_wrong_actual_genre_does_not_recommend_world_or_character_network_edges(tmp_path, monkeypatch):
    catalogue(tmp_path, monkeypatch)
    def alternate_genre(library, text):
        imported = library.import_book({'filename':'[FAKE] alternate.md', 'title':'[FAKE] 二次元参考作品', 'text':text})
        return library.review_book(imported['id'], {'types':['GENRE_ERCIYUAN'], 'decompose':False})
    monkeypatch.setattr(reference, 'make_book', alternate_genre)
    reference.available_method(tmp_path, monkeypatch, scopes=('book',))
    model = NetworkDesignModel(taxon='GENRE_ERCIYUAN')
    with Store(tmp_path/'[FAKE]-other-genre', create=True, test_mode=True) as store:
        new_project(store, NEED)
        finish_design(store, model)
        for stage in ('world_design', 'character_design', 'plot_design'):
            [packet] = packets(model, stage)
            for field in ('network_design_guidance', 'network_design_candidates'):
                assert not any(key in str(packet.get(field)) for key in (AUTHORITY.dynamic_key, PROFESSION.dynamic_key))
