"""Procedural materials require their own artifacts, not generic action bindings."""
from copy import deepcopy

import pytest

from nw.materials.process_workflow import validate_processes
from nw.materials.evidence import scene_checks, writer_checks


def members():
    return [{'key': 'yan', 'kind': 'character', 'body': {'name': '沈砚', 'want': '调查', 'role': '主角'}},
            {'key': 'secret', 'kind': 'promise', 'body': {'title': '旧印', 'setup': '见旧印', 'payoff': '识破替换'}},
            {'key': 'scene', 'kind': 'scene', 'body': {'pov': 'yan', 'characters': ['yan'], 'goal': '查封条'}}]


def candidate():
    return {'members': members(), 'chapters': [{'index': 1, 'scenes': [
        {'card': 'scene', 'index': 1, 'story_order': 1}]}]}


def material(profile):
    return {'source': {'id': 'source-id', 'key': profile}, 'profile': profile,
            'request': {'disposition': 'required'}, 'review': {'meaning': '按原条件执行阶段流程',
            'evidence_required': '逐项核对阶段产物及同稿证据', 'contract': {'obligations': []}}}


def output(profile):
    common = {'function': '把阶段要求落实到当前章场', 'parameter': '调查封条的当前设计',
              'observable': '沈砚在当夜发现旧印并保留线索', 'check': '核对当前阶段要求与正文证据'}
    values = {
        'timeline_process': {'anchor': '进入暗井为第零时', 'unit': '小时', 'events': [
            {'scene': 'scene', 'start': 0, 'end': 1, 'season': '秋季', 'expected_old': None}]},
        'promise_process': {'entries': [{'scene': 'scene', 'promise': 'secret', 'phase': 'plant',
            'before': None, 'after': 'planted', 'observable': '看见封条上有旧印'}],
            'review_interval': 3, 'payoff_min': .8, 'closing': False},
        'pov_process': {'protagonist': 'yan', 'switches': [{'scene': 'scene', 'from_pov': None,
            'to_pov': 'yan', 'reason': '由主角进入暗井的观察开场'}], 'review_interval': 5,
            'min_share': .7, 'reset_sentences': 3, 'opening_chars': 500},
        'preflight_process': {'checks': [{'kind': 'character_creation', 'target': 'yan',
            'artifact': members()[0]['body']}, {'kind': 'opening', 'target': 'scene',
            'artifact': members()[2]['body']}]},
        'usage_process': {'records': [], 'review_interval': 3, 'unit_start': 1, 'unit_end': False},
    }
    return {**common, **values[profile]}


@pytest.mark.parametrize('profile', ['timeline_process','promise_process','pov_process','preflight_process','usage_process'])
def test_each_workflow_procedure_accepts_only_its_actual_stage_artifact(profile):
    data = candidate(); data['process_bindings'] = {'source-id': output(profile)}
    validate_processes(data, 'chapter', [material(profile)])
    broken = deepcopy(data)
    broken['process_bindings']['source-id'] = {k: output(profile)[k] for k in ('function','parameter','observable','check')}
    with pytest.raises(ValueError, match='MATERIAL_PROCESS'):
        validate_processes(broken, 'chapter', [material(profile)])


@pytest.mark.parametrize('field,value', [('end', -1), ('start', True), ('scene', 'nonexistent')])
def test_timeline_cannot_invent_a_scene_or_a_negative_or_boolean_duration(field,value):
    data = candidate(); data['process_bindings'] = {'source-id': output('timeline_process')}
    data['process_bindings']['source-id']['events'][0][field] = value
    with pytest.raises(ValueError, match='MATERIAL_PROCESS'):
        validate_processes(data, 'chapter', [material('timeline_process')])


def test_promise_cannot_be_recovered_before_it_was_planted():
    data = candidate(); data['process_bindings'] = {'source-id': output('promise_process')}
    data['process_bindings']['source-id']['entries'][0].update(phase='payoff', before=None, after='paid_off')
    with pytest.raises(ValueError, match='MATERIAL_PROCESS'):
        validate_processes(data, 'chapter', [material('promise_process')])


def test_pov_procedure_must_use_the_scene_actual_viewpoint():
    data = candidate(); data['process_bindings'] = {'source-id': output('pov_process')}
    data['process_bindings']['source-id']['switches'][0]['to_pov'] = 'secret'
    with pytest.raises(ValueError, match='MATERIAL_PROCESS'):
        validate_processes(data, 'chapter', [material('pov_process')])


def test_pov_review_interval_must_be_an_integer_before_it_drives_chapter_ranges():
    data=candidate(); data['process_bindings']={'source-id':output('pov_process')}
    data['process_bindings']['source-id']['review_interval']=5.0
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_processes(data,'chapter',[material('pov_process')])


def test_process_state_and_complete_chapter_review_enter_the_existing_evidence_pipeline():
    design = {'materials': [material('timeline_process')], 'bindings': {},
              'process_bindings': {'source-id': output('timeline_process')}, 'material_key': 'scene',
              'scene_card_id': 'scene-card-id', 'chapter_index': 1, 'scene_members': members()}
    checks = scene_checks(design)
    assert checks and checks[0]['binding']['state'][0]['predicate'] == 'timeline_span'
    assert checks[0]['binding']['state'][0]['entity_id'] == 'scene-card-id'
    assert scene_checks(design, scoped=True)[0]['binding']['review_scope']['chapters'] == [1]
    visible = writer_checks(design)
    assert visible and '0' in str(visible)
    assert 'entries' not in str(visible)


@pytest.mark.parametrize('profile',['timeline_process','promise_process','pov_process'])
def test_global_procedure_notes_do_not_leak_future_revelations_into_this_writer(profile):
    artifact=output(profile)
    artifact['observable']='直到第二场才揭晓的作者秘密：馆主伪造血印，密钥为青铜蝉。'
    artifact['check']='核对全案幕后秘密：青铜蝉是密钥，不应提前披露。'
    design={'materials':[material(profile)],'bindings':{},'process_bindings':{'source-id':artifact},
            'material_key':'scene','scene_card_id':'scene-card-id','chapter_index':1,'scene_members':members()}
    assert '青铜蝉' not in str(writer_checks(design))


def test_unit_end_reviews_the_entire_declared_story_unit():
    artifact=output('usage_process'); artifact.update(unit_end=True,unit_start=1)
    design={'materials':[material('usage_process')],'bindings':{},'process_bindings':{'source-id':artifact},
            'material_key':'scene','scene_card_id':'scene-card-id','chapter_index':2,'scene_members':members()}
    assert scene_checks(design,scoped=True)[0]['binding']['review_scope']['chapters']==[1,2]
