"""A studio genre choice may resolve combination review only for the corresponding actual selection."""
from copy import deepcopy
import json

import pytest

from nw.materials.governance_runtime import (
    check_stage_governance, freeze_report, require_governance_clear, stage_governance_inputs, verify_stage_governance,
)
from nw.studio.library import LibraryService
from nw.studio.production_inputs import freeze_wizard, governance
from nw.task_models import canonical
from test_material_governance_runtime import runtime


MAIN = 'GENRE_XUANYI'
SUB = 'SUB_XUANYI_01'
SECONDARY = 'GENRE_DUSHI'
COMBINATION_RULES = {
    'CONFIG-requires_manual_review', 'CONFIG-auto_combination_forbidden',
    'CONFIG-rule-0', 'CONFIG-rule-1', 'CONFIG-rule-2',
}


@pytest.fixture(scope='module')
def library(tmp_path_factory):
    return LibraryService(tmp_path_factory.mktemp('single_genre'))


def studio_context(library, genre_ids, **choices):
    wizard = freeze_wizard({'title':'渡口', 'idea':'谁接了路引', 'genre_ids':genre_ids, **choices}, library)
    return {'governance_inputs':governance(wizard)}


def product(config):
    ids = [ident for values in config.values() for ident in values]
    return {'selection':[{'id':ident, 'label':ident, 'basis':'本书已选类型'} for ident in ids],
            '_governance':{'project_config':deepcopy(config)}, '_uses':[]}


def evaluate(context, value):
    return check_stage_governance(runtime(), 'type_selection', value, {}, [], context)


def statuses(report):
    return {row['rule_id']:row['status'] for row in report['checks']}


@pytest.mark.parametrize('genres', [[MAIN], [MAIN, SUB]])
def test_single_wizard_genre_replays_its_source_governance_after_save(tmp_path, library, genres):
    context = studio_context(library, genres, tone_ids=['TONE_SERIOUS'], style_ids=['STYLE_REALISTIC'])
    config = context['governance_inputs']['type_selection']['project_config']
    value = product(config)
    inputs = stage_governance_inputs('type_selection',value,{},[],context)
    assert inputs['project_config'] == config
    report = evaluate(context, value)
    require_governance_clear(report)
    checks = statuses(report)
    assert all(checks[key] in ('pass','not_applicable') for key in COMBINATION_RULES)
    assert checks['CONFIG-max_genre_combination'] == checks['CONFIG-max_tones_per_project'] == 'pass'
    path = tmp_path / 'frozen.json'
    path.write_text(canonical({'context':context, 'value':value, 'report':freeze_report(report)}), encoding='utf-8')
    saved = json.loads(path.read_text(encoding='utf-8'))
    verified = verify_stage_governance(runtime(),saved['report'],'type_selection',saved['value'],{},[],saved['context'])
    require_governance_clear(verified)


@pytest.mark.parametrize('genres', [[MAIN, SECONDARY], [MAIN, SUB, SECONDARY]])
def test_wizard_with_an_independent_secondary_still_needs_combination_review(library, genres):
    context = studio_context(library, genres)
    value = product(context['governance_inputs']['type_selection']['project_config'])
    report = evaluate(context, value)
    assert all(statuses(report)[key] == 'waiting' for key in COMBINATION_RULES)
    with pytest.raises(ValueError,match='GOVERNANCE'):
        require_governance_clear(report)


def test_saved_request_without_a_declaration_cannot_receive_or_forge_an_exemption(library):
    stage = studio_context(library, [MAIN])['governance_inputs']['type_selection']
    legacy = {'governance_inputs':{'type_selection':{key:stage[key] for key in ('author_preferences','project_config')}}}
    value = product(stage['project_config'])
    value['_governance'].update(deepcopy(stage))
    report = evaluate(json.loads(canonical(legacy)), value)
    assert all(statuses(report)[key] == 'waiting' for key in COMBINATION_RULES)
    with pytest.raises(ValueError,match='GOVERNANCE'):
        require_governance_clear(report)


@pytest.mark.parametrize('model_genres,model_tones', [
    ([SECONDARY], []),               # substitute a new genre
    ([MAIN, SUB, SECONDARY], []),    # add a second genre
    ([MAIN], []),                    # omit the selected child
    ([MAIN], [SUB]),                 # same selected IDs, put the child under tone
    ([MAIN, SUB], [SECONDARY]),      # hide a new genre among otherwise valid selections
    ([MAIN, SUB], ['HYBRID_XUANHUAN_XUANYI']),  # a source-defined hybrid absent from the wizard genre list
])
def test_model_types_cannot_change_or_reclassify_the_frozen_choice(library, model_genres, model_tones):
    context = studio_context(library, [MAIN, SUB])
    config = deepcopy(context['governance_inputs']['type_selection']['project_config'])
    config.update(genre_ids=model_genres, tone_ids=model_tones)
    report = evaluate(context, product(config))
    assert report['status'] == 'failed'
    with pytest.raises(ValueError,match='GOVERNANCE'):
        require_governance_clear(report)


def test_model_claiming_a_correct_configuration_is_checked_against_the_real_selection(library):
    context = studio_context(library, [MAIN])
    config = context['governance_inputs']['type_selection']['project_config']
    value = product(config)
    value['selection'][0]['id'] = SECONDARY
    report = evaluate(context, value)
    assert report['status'] == 'failed'


def test_single_genre_declaration_revalidates_the_parent_of_the_frozen_subgenre(library):
    context = studio_context(library, [MAIN, SUB])
    stage = context['governance_inputs']['type_selection']
    mismatched = [SECONDARY, SUB]
    stage.update(single_genre_selection=mismatched, project_config={**stage['project_config'],'genre_ids':mismatched})
    with pytest.raises(ValueError,match='GOVERNANCE'):
        evaluate(context, product(stage['project_config']))


def test_non_combination_limits_still_apply_to_the_actual_frozen_preferences(library):
    context = studio_context(library, [MAIN], tone_ids=['TONE_SERIOUS','TONE_LIGHT','TONE_DARK'])
    config = context['governance_inputs']['type_selection']['project_config']
    report = evaluate(context, product(config))
    assert statuses(report)['CONFIG-max_tones_per_project'] == 'failed'
    with pytest.raises(ValueError,match='GOVERNANCE'):
        require_governance_clear(report)


def test_single_genre_explicitly_using_a_cross_genre_combination_still_needs_review(library):
    context = studio_context(library, [MAIN])
    config = context['governance_inputs']['type_selection']['project_config']
    value = product(config)
    source = {'source':{'id':'cross_genre_method'}, 'original_text':json.dumps({
        'combination_id':'XUANYI_DUSHI', 'combination_kind':'动态', 'type_ids':[MAIN,SECONDARY],
        'schema_version':'H0D-1.0.0', 'source_refs':[]})}
    def check():
        return check_stage_governance(runtime(),'type_selection',value,{},[source],context)
    require_governance_clear(check())  # A candidate in the search results has not been chosen.
    value['_uses'] = [{'source_id':source['source']['id']}]
    report = check()
    assert report['input_snapshot']['subjects']['combinations'][0]['type_ids'] == [MAIN,SECONDARY]
    assert all(statuses(report)[key] == 'waiting' for key in COMBINATION_RULES)
