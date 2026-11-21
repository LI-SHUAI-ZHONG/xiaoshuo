"""An approved reference observation must reach the scene that uses its technique."""
from copy import deepcopy

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
