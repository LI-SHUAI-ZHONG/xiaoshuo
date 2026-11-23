"""The saved wizard, real stage input and stage product share the same choices."""
from copy import deepcopy

import pytest

from nw.materials.author_references import author_stage_input
from nw.materials.phase_contract import validate_phase
from nw.materials.phase_routes import product_ref, REQUIRES
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production_inputs import freeze_wizard, governance
from nw.task_models import content_sha256


@pytest.fixture
def library(tmp_path):
    return LibraryService(StudioService(tmp_path).workspace)


def manual(**options):
    return {'genre_ids': ['GENRE_XUANYI'], 'title': '封条', 'idea': '值夜员想找出被调换的档案。',
            'design_mode': 'manual', **options}


def test_manual_plan_freezes_meaning_and_routes_only_to_responsible_steps(library):
    wizard = freeze_wizard(manual(constraints='明示线索不得事后改写。', style_ids=['STYLE_GRITTY'],
                                  structure_ids=['NARRATIVE_STRUCTURE_MULTI_POV']), library)
    plan = wizard['creation_plan']
    assert plan['mode'] == 'manual' and plan['constraints'] == '明示线索不得事后改写。'
    assert plan['types'][0]['id'] == 'GENRE_XUANYI'
    assert plan['preferences'][0]['name'] == '写实风格'
    assert plan['preferences'][0]['source_ref']['original_line']
    package = {'governance_inputs': governance(wizard, library=library)}
    expression = author_stage_input(package, 'expression_design')['creation_plan']
    assert [pref['id'] for pref in expression['preferences']] == ['STYLE_GRITTY']
    assert '粗粝' in expression['preferences'][0]['meaning']
    plot = author_stage_input(package, 'plot_design')['creation_plan']
    assert [pref['id'] for pref in plot['preferences']] == ['NARRATIVE_STRUCTURE_MULTI_POV']
    assert 'creation_plan' not in author_stage_input(package, 'world_design')
    assert author_stage_input(package, 'type_adaptation')['creation_plan']['types'][0] == plan['types'][0]


def test_all_seven_manual_board_choices_reach_their_responsible_steps(library):
    wizard = freeze_wizard(manual(
        tone_ids=['TONE_SERIOUS'], style_ids=['STYLE_GRITTY'], narration_ids=['109.2'],
        world_ids=['31.1'], character_ids=['1.1'], structure_ids=['NARRATIVE_STRUCTURE_LINEAR'],
        mechanism_ids=['PLOT_MECHANISM_UPGRADE'],
    ), library)
    packet = {'governance_inputs': governance(wizard)}
    expected = {'world_design': {'world'}, 'character_design': {'character'},
                'plot_design': {'structure', 'hook'}, 'event_design': {'hook'},
                'scene_design': {'narration', 'structure'}, 'expression_design': {'tone', 'style', 'narration'}}
    for stage, slots in expected.items():
        rows = author_stage_input(packet, stage)['creation_plan']['preferences']
        assert {row['slot'] for row in rows} == slots
        assert all(row['meaning'] and row['source_ref']['material_sha256'] for row in rows)
    plot = author_stage_input(packet, 'plot_design')['creation_plan']['preferences']
    assert '先后' in next(row for row in plot if row['slot'] == 'structure')['step_use']


def test_conflicting_preferences_require_distinct_real_output_scope(library):
    wizard = freeze_wizard(manual(style_ids=['STYLE_LIGHT', 'STYLE_GRITTY']), library)
    plan = wizard['creation_plan']
    assert set(plan['preference_interactions'][0]['keys']) == {'style.STYLE_LIGHT', 'style.STYLE_GRITTY'}
    context = {'governance_inputs': governance(wizard)}
    stage = 'expression_design'
    products = {}
    for dep in REQUIRES[stage]:
        value = {'_uses': []}
        products[dep] = {'stage': dep, 'task_id': dep, 'sha256': content_sha256(value), 'products': value}
        assert product_ref(products[dep])
    products['scene_design']['products'] = {'members': [{'key': 'archive'}, {'key': 'canteen'}]}
    products['scene_design']['sha256'] = content_sha256(products['scene_design']['products'])
    value = {'_uses': [], 'guidance': [
        {'scene': 'archive', 'observable': '压低声音说出断档风险', 'check': '保持交涉的严重性'},
        {'scene': 'canteen', 'observable': '伙伴拿皱巴巴的饭票打趣', 'check': '交谈暂缓紧张'},
    ]}
    with pytest.raises(ValueError, match='立项偏好'):
        validate_phase({'stage': stage, 'products': value}, stage, products, [], context)
    value['preference_resolutions'] = [
        {'key': 'style.STYLE_LIGHT', 'status': 'applied', 'reason': '食堂伙伴彼此熟识',
         'output_ref': '/guidance/1/observable'},
        {'key': 'style.STYLE_GRITTY', 'status': 'applied', 'reason': '档案室谈判决定证据能否保留',
         'output_ref': '/guidance/0/observable'},
    ]
    from nw.materials.creation_preferences import validate_resolutions
    validate_resolutions(stage, value, context)
    validate_phase({'stage': stage, 'products': value}, stage, products, [], context)
    overlapping = deepcopy(value)
    overlapping['preference_resolutions'][0]['output_ref'] = '/guidance/0/observable'
    with pytest.raises(ValueError, match='立项偏好'):
        validate_resolutions(stage, overlapping, context)
    invalid = deepcopy(value)
    invalid['preference_resolutions'][0]['output_ref'] = '/guidance/7/observable'
    with pytest.raises(ValueError, match='立项偏好'):
        validate_resolutions(stage, invalid, context)
    deferred = deepcopy(value)
    deferred['preference_resolutions'][0].update(
        status='deferred', output_ref='', reason='这一段在通报事故，轻松语气等交涉结束后再考虑')
    validate_phase({'stage': stage, 'products': deferred}, stage, products, [], context)


def test_incompatible_global_viewpoint_choices_fail_at_intake(library):
    with pytest.raises(ValueError, match='单视角叙事.*多视角叙事'):
        freeze_wizard(manual(structure_ids=['NARRATIVE_STRUCTURE_MULTI_POV',
                                           'NARRATIVE_STRUCTURE_SINGLE_POV']), library)


def test_type_selection_preserves_the_saved_main_and_secondary_genres(library):
    chosen = ['GENRE_XUANYI', 'GENRE_XUANHUAN']
    wizard = freeze_wizard(manual(genre_ids=chosen), library)
    context = {'scope': 'book', 'governance_inputs': governance(wizard)}
    raw = {'stage': 'type_selection', 'products': {
        '_uses': [], 'concepts': [], 'boundaries': ['悬疑主线承接玄幻的规则限制'],
        'selection': [{'id': ident, 'label': ident, 'basis': '按立项选定类型'} for ident in chosen]}}
    validate_phase(raw, 'type_selection', {}, [], context)
    raw['products']['selection'][1]['id'] = 'GENRE_DUSHI'
    with pytest.raises(ValueError, match='立项所选类型'):
        validate_phase(raw, 'type_selection', {}, [], context)


def test_ollama_preferences_are_required_only_in_product_replies():
    from nw.materials.creation_preferences import add_resolution_schema
    from nw.materials.phase_schema import schema

    for allow_requests in (True, False):
        shape = schema('expression_design', [], allow_requests=allow_requests)
        add_resolution_schema(shape, ['style.STYLE_LIGHT', 'style.STYLE_GRITTY'])
        alternatives = shape.get('anyOf', [shape])
        output = alternatives[0]['properties']['products']
        assert 'preference_resolutions' in output['required']
        assert output['properties']['preference_resolutions']['minItems'] == 2
        if allow_requests:
            assert 'preference_resolutions' not in alternatives[1]['properties']
