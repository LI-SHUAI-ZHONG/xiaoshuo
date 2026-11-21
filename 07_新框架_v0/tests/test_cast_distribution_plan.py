from copy import deepcopy

import pytest

from nw.materials import cast_distribution_plan as distribution
from nw.materials import story_policies


def example():
    context = {'cast_distribution_policy':distribution.POLICY, 'cast_distribution_book_plan':{'chapter_count':9},
               'cast_sample_reference':{'chapter_bands':{
                   'opening':{'appearing':{'min':2,'max':2},'first':{'min':2,'max':2},'returning':{'min':0,'max':0},
                              'positions':{'protagonist':[1,1],'supporting':[1,1]},'functions':{'handoff':[1,1]}},
                   'ending':{'appearing':{'min':1,'max':2},'first':{'min':0,'max':0},'returning':{'min':1,'max':2}}},
                   'chapter_ranges':{'appearing':{'min':1,'max':2}}},
               'cast_previous_appearances':{}}
    products = {'character_design':{'products':{'members':[{'key':'yan','body':{'casting':{'standing':'protagonist'}}}]}}}
    products['plot_design'] = {'products':{'event_nodes':[{'id':'discover','obstacle':'档案在门卫手里'},
                                                          {'id':'finish','goal':'取出铁柜封存的原件'}]}}
    scene = {'members':[{'key':'steps','body':{'character_goals':{'yan':'查清旧封条的去向'}}},
                        {'key':'office','body':{'character_goals':{'yan':'带回印鉴'}}}],
             'chapters':[{'index':1,'card':'c1','scenes':[{'card':'steps'}]},{'index':9,'card':'c9','scenes':[{'card':'office'}]}],
             'selected_events':[{'scene':'steps','event':'discover'},{'scene':'office','event':'finish'}]}
    opening = {'chapter':1,'band':'opening','reference_scope':'band','appearing_range':{'min':2,'max':2},
               'comparison':'below','differences':['appearing','first','positions.supporting','functions.handoff'],
               'reason':'档案在门卫手里。为了查清旧封条的去向他得自己看，旁人递交档案会打草惊蛇。',
               'people':[{'actor':'yan','scene':'steps','event':'discover','appearance':'first','functions':['driver'],
                          'basis_quote':'查清旧封条的去向','reason':'查清旧封条的去向是他坚持亲临的原因。'}]}
    ending = {'chapter':9,'band':'ending','reference_scope':'band','appearing_range':{'min':1,'max':2},
              'comparison':'within','differences':[],'reason':'要取出铁柜封存的原件，仍由沈砚带回印鉴，守住先前的约定。',
              'people':[{'actor':'yan','scene':'office','event':'finish','appearance':'returning','functions':['driver'],
                         'basis_quote':'带回印鉴','reason':'他曾验过印痕，带回印鉴须他亲自确认。'}]}
    scene['cast_distribution_plan'] = [ending, opening]
    return scene, products, context


def test_can_deviate_from_reference_for_actual_plot_with_subsequent_return():
    scene, products, context = example()
    distribution.validate(scene, products, context)


@pytest.mark.parametrize('change', ['no_decision', 'wrong_range', 'wrong_band', 'wrong_role', 'wrong_goal',
                                    'wrong_event', 'wrong_person', 'missing_chapter', 'false_first', 'stock_reason', 'wrong_project_basis'])
def test_cannot_skip_sample_or_cite_unrelated_chapter_and_cast(change):
    scene, products, context = example()
    end, opening = scene['cast_distribution_plan']
    person = opening['people'][0]
    if change == 'no_decision':
        del scene['cast_distribution_plan']
    elif change == 'wrong_range':
        opening['appearing_range']['max'] = 4
    elif change == 'wrong_band':
        end['band'] = 'opening'
    elif change == 'wrong_role':
        opening['differences'].remove('functions.handoff')
    elif change == 'wrong_goal':
        person['basis_quote'] = '带回印鉴'
    elif change == 'wrong_event':
        person['event'] = 'finish'
    elif change == 'wrong_person':
        person['actor'] = '许'
    elif change == 'missing_chapter':
        scene['cast_distribution_plan'] = [end]
    elif change == 'false_first':
        end['people'][0]['appearance'] = 'first'
    elif change == 'stock_reason':
        opening['reason'] = '依照本章实际安排角色。'
    else:
        opening['reason'] = '为了查清旧封条的去向，才需要取出铁柜封存的原件。'
    with pytest.raises(ValueError):
        distribution.validate(scene, products, context)


def test_history_or_chapter_band_can_be_unknown_without_a_false_first_or_precise_count():
    scene, products, context = example()
    scene['chapters'] = scene['chapters'][1:]
    scene['cast_distribution_plan'] = scene['cast_distribution_plan'][:1]
    context.update(cast_history_unverified_chapters=[1], cast_distribution_book_plan={})
    context['cast_sample_reference'] = {'chapter_bands':{},'chapter_ranges':{'appearing':None}}
    row = scene['cast_distribution_plan'][0]
    row.update(band='unknown',reference_scope='insufficient',appearing_range=None,comparison='insufficient')
    row['people'][0]['appearance'] = 'unknown'
    distribution.validate(scene, products, context)
    row['people'][0]['appearance'] = 'first'
    with pytest.raises(ValueError, match='前章证据'):
        distribution.validate(scene, products, context)


def test_historical_task_replays_but_frozen_sample_cannot_be_exchanged():
    from nw.materials.phase_routes import POLICY
    _, _, context = example()
    story_policies.verify_session({'policy':POLICY,'context':{}}, {'cast_sample_reference':{'old':True}})
    current = deepcopy(context)
    story_policies.verify_session({'policy':POLICY,'context':current}, context)
    current['cast_sample_reference']['chapter_bands'] = {}
    with pytest.raises(ValueError, match='原设计任务'):
        story_policies.verify_session({'policy':POLICY,'context':current}, context)


def test_transport_requests_and_completion_both_permit_sampled_chapter():
    from nw.materials.phase_schema import schema
    shape = schema('scene_design', [], cast_distribution=True)['anyOf'][0]['properties']['products']
    assert 'cast_distribution_plan' in shape['required']
    assert 'band' in shape['properties']['cast_distribution_plan']['items']['required']


def test_pending_opening_cannot_inherit_precise_counts_from_an_ending():
    sample = {'chapter_bands':{'ending':{'appearing':{'min':1,'max':1}}},
              'uncertainty':{'band_chapter_counts':{'opening':1}}, 'chapter_ranges':{'appearing':{'min':1,'max':1}}}
    assert distribution.reference_for(sample, 'opening') == ('insufficient', {})
    assert distribution.reference_for(sample, 'ending')[0] == 'band'
    assert distribution.reference_for(sample, 'unknown')[0] == 'chapter'


def test_schedule_does_not_prove_appearance_in_prose():
    scene, products, context = example()
    scene['chapters'] = scene['chapters'][1:]
    scene['cast_distribution_plan'] = scene['cast_distribution_plan'][:1]
    context.update(cast_previous_appearances={'yan':[1,1]}, cast_history_unverified_chapters=[1])
    with pytest.raises(ValueError, match='前章证据'):
        distribution.validate(scene, products, context)
    context['cast_verified_first_positions'] = {'yan':[2,1]}
    distribution.validate(scene, products, context)


def test_appending_one_scene_to_existing_chapter_cannot_stand_for_whole_chapter():
    scene, products, context = example()
    scene['chapters'][0]['card'] = None
    with pytest.raises(ValueError, match='人数比较'):
        distribution.validate(scene, products, context)
    scene['cast_distribution_plan'][1].update(reference_scope='partial', appearing_range=None,
                                               comparison='insufficient', differences=[])
    distribution.validate(scene, products, context)
