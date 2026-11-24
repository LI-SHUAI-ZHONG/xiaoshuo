"""An approved reference observation must reach the scene that uses its technique."""
from copy import deepcopy
import json

import pytest

from corpus_fixture import start_analysis
from nw.production_methods.contracts import narration_handoff, validate
from nw.production_methods.handoff import scene_checks
from nw.production_methods.inputs import binding
from nw.production_methods.policy import needed, normalize
from nw.production_methods.sources import MethodReader
from nw.studio.corpus_methods import manual_method
from nw.studio.library import LibraryService
from nw.studio.method_recommendations import freeze_preferences, recommendations
from nw.task_models import content_sha256
from test_studio_project_methods import client


def test_outline_volume_continues_delivering_approved_book_method_to_scene():
    from nw.production_methods.handoff import deliveries, inherited, outputs

    ref = {'card_id': 'book', 'version': 2}
    definition = {'key': 'disclosure', 'stage': 'plot_design', 'field': 'reader_plan',
                  'artifact_kind': 'stage_product'}
    method = {'id': 'book-clue-order', 'version': 1, 'body': {
        'outputs': [definition],
        'downstream': [{'output_key': 'disclosure', 'consumer': 'scene_design'}],
        'acceptance': [{'output_key': 'disclosure', 'check': '[FAKE] 先呈现替换痕迹再问当事人'}],
    }}
    effect = '[FAKE] 让本书人物先辨封条旧印，再核查当事人的换班记录。'
    products = {'reader_plan': [effect], '_method_applications': [{
        'method_id': method['id'], 'outputs': [{'key': 'disclosure', 'scene_guidance': [],
                                               'placements': [{'path': ['reader_plan', 0], 'value': effect}]}]}]}
    record = {'stage': 'plot_design', 'task_id': 'book-plot', 'sha256': content_sha256(products),
              'products': products, 'production_methods': {'selected': [{'method': method}]}}
    [original] = outputs([record], parent=ref)
    package = {'scope': 'chapter', 'parent': {'card_id': 'approved-volume', 'version': 1},
               'parent_material_work': {'stages': [{'stage': 'world_design', 'products': {'members': []}}],
                                        'production_method_parents': [original],
                                        'outline_only_volume': True}}

    forwarded = inherited(package)
    assert forwarded == [original]
    assert forwarded[0]['approved_parent'] == ref
    assert deliveries('scene_design', {}, forwarded) == [original]
    package['parent_material_work'].pop('outline_only_volume')
    assert inherited(package) == []


def test_studio_preserves_book_method_until_the_approved_scene_plan(client):
    from project_methods_fixture import ProjectModel

    request, settled, server, method = client
    config, _ = server.production._runtime()

    class Model(ProjectModel):
        def generate(self, messages, **params):
            response = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if payload.get('scope') == 'volume' and payload.get('stage') == 'plot_design':
                raw = json.loads(response.text)
                members = raw['products']['members']
                members[:] = [m for m in members if m['kind'] not in ('volume', 'chapter')]
                members.append({'key': 'investigation', 'kind': 'volume', 'body': {
                    'title': '[FAKE] 换印案', 'goal': '[FAKE] 找到印章出处',
                    'turn': '[FAKE] 守井人因调查被罢黜',
                    'ending_direction': '[FAKE] 取得当年名单交给后续查证'}})
                response.text = json.dumps(raw, ensure_ascii=False)
            return response

    model = Model()
    server.production.runtime_factory = lambda: (config, model)
    status, created = request('POST', '/api/novels', {
        'title': '[FAKE] 逐级保留悬念', 'idea': '[FAKE] 核查两枚旧印的日期', 'genre_ids': ['GENRE_XUANYI'],
        'planning_hierarchy': True, 'production_methods': {'tasks': ['hook']}})
    assert status == 201, created
    ident = created['novel']['id']
    path = f'/api/novels/{ident}'

    def gate(progress, **fields):
        assert progress['status'] == 'WAITING', progress['reason']
        waiting = progress['gates'][0]
        status, reply = request('POST', f"{path}/gates/{waiting['id']}", {
            'action': 'approve', 'token': waiting['token'], 'reason': '[FAKE] 核对批准', **fields})
        assert status == 200, reply
        return settled(ident)

    def apply(progress):
        assert progress['status'] == 'WAITING', progress['reason']
        root = progress['gates'][0]['target']['candidates'][0]['root']['card_id']
        return gate(progress, root=root)

    book = apply(gate(settled(ident), method_ids=[method['id']]))
    assert book['status'] == 'DONE', book['reason']
    book_root = book['job']['outputs']['application']['root']['card_id']
    # Only new selections are disabled. The book method still has a scene
    # obligation, including when no direct world method carries its parents.
    status, configured = request('POST', path + '/methods', {
        'policy': None, 'reason': '[FAKE] 后续只落实原已批准的拆解方法'})
    assert status == 200, configured
    assert request('POST', path + '/run', {})[0] == 200
    volume = apply(settled(ident))
    assert volume['status'] == 'DONE', volume['reason']
    assert request('POST', path + '/run', {})[0] == 200
    ready = gate(settled(ident))
    assert ready['status'] == 'WAITING', ready['reason']
    scene = next(packet for call in model.calls
                 if (packet := json.loads(call[-1]['content'])).get('stage') == 'scene_design')
    inherited_method, = [entry for entry in scene['method_handoffs'] if entry['method']['id'] == method['id']]
    assert inherited_method['approved_parent']['card_id'] == book_root
    assert inherited_method['output']['placements'][0]['path'] == ['directions', 0, 'choice']
    assert apply(ready)['status'] == 'DONE'


def test_reference_narration_reaches_its_own_scene_after_reopen(tmp_path, monkeypatch):
    library = LibraryService(tmp_path)
    book, job, _ = start_analysis(library, monkeypatch, extent='excerpt')
    assert job['status'] == 'completed', job['error']
    library.review_corpus(book['id'], {'version': 1, 'decision': 'approve', 'accept_limitations': True,
                                       'note': '[FAKE] 此摘录只支持当前场景的叙述观察'})
    draft = manual_method(library, book['id'], {'version': 1, 'thread_ids': ['T_narration']})
    body = deepcopy(draft['body'])
    body.update(scopes=['chapter'], applicability=['[FAKE] 此场需要先让读者看到一个待解释的结果'],
                non_applicability=['[FAKE] 此场尚无足以披露的结果'],
                prerequisites=[{'key': 'scene', 'input_kind': 'scene_design', 'artifact': '场景卡',
                                'requirement': '[FAKE] 已经有可见线索与此时在场的人'}],
                operations=[{'key': 'place', 'instruction': '[FAKE] 指出读者先见到什么，以及下一问由谁提出',
                             'input_keys': ['scene'], 'output_keys': ['beat']}],
                outputs=[{'key': 'beat', 'stage': 'expression_design', 'field': 'guidance',
                          'artifact_kind': 'stage_product', 'description': '[FAKE] 本场的可见线索和谁注意到它'}],
                downstream=[{'output_key': 'beat', 'consumer': c, 'usage': '[FAKE] 按此场归属写作并核对当事人知情范围'}
                            for c in ('writer', 'review')],
                acceptance=[{'output_key': 'beat', 'check': '[FAKE] 指出谁先看到了结果',
                             'evidence_required': '[FAKE] 成稿中能看出观察者及其所见的句子'}])
    saved = library.save_method({'body': body, 'expected_version': 1}, draft['id'])
    approved = library.review_method(saved['id'], {'version': 2, 'decision': 'approve', 'note': '[FAKE] 引文已核实'})
    assert approved['available']

    reader = MethodReader(tmp_path)
    types = ['GENRE_XUANYI']
    choices = recommendations(reader, 'narration', types, [])['recommendations']
    assert [row['id'] for row in choices] == [approved['id']]
    preference = {'id': approved['id'], 'version': 2, 'slot': 'narration'}
    assert freeze_preferences(reader, [preference], types)[0]['structure_origin'] == saved['structure_origin']
    assert needed(normalize({'tasks': ['narration']}, types=types), 'expression_design', 'chapter') == ['narration']
    pin = reader.snapshot(reader.get_method(approved['id']))
    reader.verify(pin)
    assert pin['instance']['threads'][0]['domain'] == 'narration'
    assert pin['instance']['events'] and pin['body']['evidence']
    requirement = {'status': 'approved', 'kind': 'scene_design', 'value': {'scene': 'ferry'}}
    spec = binding(pin, 'expression_design', {'scene_design': requirement})
    assert not spec['missing']
    plan = {'target': {'stage': 'expression_design'}, 'selected': [spec]}
    guide = {'scene': 'ferry', 'observable': '[FAKE] 听见桨声的人先看见空船靠岸',
             'check': '[FAKE] 正文交代谁看见了空船，将失踪的原因留到后面求证'}
    beat = {**guide, 'narration': {'time': 'current', 'mode': 'perception', 'owner': 'boatman',
                                  'basis_ref': 'scene:ferry:entering_state', 'basis_quote': '空船靠岸',
                                  'effect': '读者先知道船回来了，船上的人下落未明'}}
    output = {'key': 'beat', 'placements': [{'path': ['guidance', 0], 'value': beat}], 'scene_guidance': [guide]}
    app = {'method_id': pin['id'], 'operations': [{'key': 'place', 'explanation': '[FAKE] 用船工先看见空船的过程提出失踪问题'}],
           'outputs': [output]}
    products = {'guidance': [beat], '_method_applications': [app], '_method_receipts': []}
    validate(products, 'expression_design', plan, [], {'ferry', 'market'})
    record = {'stage': 'expression_design', 'task_id': 'call', 'sha256': content_sha256(products),
              'products': products, 'production_methods': plan}
    session = {'stages': [record]}
    assert scene_checks(session, 'ferry')[0]['binding']['observable'] == guide['observable']
    assert not scene_checks(session, 'market')
    output['scene_guidance'] = [{**guide, 'scene': 'market'}]
    with pytest.raises(ValueError, match='与实际采用的节拍不一致'):
        validate(products, 'expression_design', plan, [], {'ferry', 'market'})
    other_guide = {**guide, 'scene': 'market', 'observable': '[FAKE] 店主发现今晨货单少记了一车货'}
    other_beat = {**beat, **other_guide}
    swapped = {'placements': [*output['placements'], {'path': ['guidance', 1], 'value': other_beat}],
               'scene_guidance': [{**guide, 'scene': 'market'}, {**other_guide, 'scene': 'ferry'}]}
    with pytest.raises(ValueError, match='来自该场同一已设计'):
        narration_handoff({'guidance': [beat, other_beat]}, 'expression_design', swapped)

    placed_scene = {'members': [{'key': 'ferry', 'kind': 'scene', 'body': {'choice': '先检查空船'}}]}
    place = {'path': ['members', 0, 'body', 'choice'], 'value': '先检查空船'}
    with pytest.raises(ValueError, match='与实际采用的节拍不一致'):
        narration_handoff(placed_scene, 'scene_design', {'placements': [place], 'scene_guidance': output['scene_guidance']})
    # A locally valid receipt for a different scene must still match the producing stage.
    misplaced = {'members': [dict(placed_scene['members'][0], key='market')]}
    receipt = {'id': 'handoff', 'operation': '[FAKE] 按已交接的空船线索安排下游人物的回应',
               'placements': [place], 'scene_guidance': output['scene_guidance']}
    delivery = {'id': 'handoff', 'method': pin, 'output': {'scene_guidance': [guide]}}
    with pytest.raises(ValueError, match='转交给了另一场'):
        validate({**misplaced, '_method_receipts': [receipt]}, 'scene_design', {'selected': [], 'target': {}},
                 [delivery], {'ferry', 'market'})

    # Three recently approved, general style methods must not hide an exact narration match.
    others = [dict(approved, id=f'generic-{i}', body={**body, 'tasks': ['expression']}) for i in range(3)]
    from nw.production_methods.matching import type_match
    match = type_match(types, types)
    monkeypatch.setattr('nw.studio.method_recommendations.matching_methods',
                        lambda *_: [(row, match) for row in [*others, approved]])
    ranked = recommendations(reader, 'narration', types, [])['recommendations']
    assert [row['id'] for row in ranked] == [approved['id'], 'generic-0', 'generic-1']
