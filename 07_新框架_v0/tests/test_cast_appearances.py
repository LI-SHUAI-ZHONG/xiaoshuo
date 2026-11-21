from copy import deepcopy
from types import SimpleNamespace

import pytest

from nw.materials import cast_appearances
from nw.materials.action_review import review_result
from nw.models import Draft
from test_material_action_review import review_run, span


def reviewed():
    draft = Draft('d', 's', 2, '沈砚按住门闩，向窗外报出了自己的姓名。他说起去年在这里值班的老许。', 'complete', 'r', '')
    split = draft.text.index('。') + 1
    rule = {'id': 'work:cast-presence:scene', 'profile':'cast_presence_review',
            'roster':{'yan':'沈砚','lu':'陆昭'}, 'other_named':{'xu':'老许'}, 'must_appear':['yan']}
    row = {'id': rule['id'], 'status':'pass', 'reason':'逐人核对了本场发言与回忆中的人',
           'evidence':[span(draft, 0, split),span(draft, split, len(draft.text))],
           'people':[{'actor':'yan','mode':'speech','cue':'报出了自己的姓名','span':0,'reason':'沈砚借报上姓名回应门外的人'},
                     {'actor':'lu','mode':'absent','cue':'','span':None,'reason':'全场没有陆昭出面'},
                     {'actor':'xu','mode':'mentioned','cue':'去年在这里值班的老许','span':1,'reason':'老许只出现在回忆里'}]}
    return draft, rule, row


def test_review_distinguishes_absence_mention_and_onstage_speech():
    draft, rule, row = reviewed()
    reviewed_row = review_result(review_run(draft, [row]), {'checks':[rule]}, draft, None)['material_checks'][0]
    people = cast_appearances.checked_people(rule, reviewed_row)
    assert [(p['actor'],p['presence']) for p in people] == [('yan','onstage'),('xu','mentioned')]
    for person in people:
        assert draft.text[person['start']:person['end']] == person['quote']


def test_missing_prior_census_does_not_force_existing_character_to_introduce_herself_again():
    from nw.materials.cast_design import entry_bases
    from test_cast_design import actor
    scenes = {'members':[{'key':'desk', 'body':{'pov':'lin','characters':['lin']}}],
              'chapters':[{'index':3, 'scenes':[{'card':'desk', 'index':1, 'story_order':3}]}]}
    people = [('lin','character',actor())]
    old = entry_bases(scenes, people, {}, unverified_chapters=[1])
    assert 'cast:lin:entry' not in old['desk'] and 'cast:lin:reveal' in old['desk']
    new = entry_bases(scenes, people, {}, unverified_chapters=[1], new_people={'lin'})
    assert 'cast:lin:entry' in new['desk']


@pytest.mark.parametrize('problem', ['missing','duplicate','name_only','reported_as_action','not_quoted','missing_promised',
                                     'after_revision','unplanned_actor','unknown_id'])
def test_invalid_personal_receipts_cannot_pass(problem):
    draft, rule, row = reviewed()
    yan, _, xu = row['people']
    if problem == 'missing':
        row['people'].pop(1)
    elif problem == 'duplicate':
        row['people'].append(dict(yan))
    elif problem == 'name_only':
        yan['cue'] = '沈砚'
    elif problem == 'reported_as_action':
        xu['mode'] = 'action'
    elif problem == 'not_quoted':
        yan['cue'] = '老许抽走门闩'
    elif problem == 'missing_promised':
        yan.update(mode='absent',span=None,cue='')
    elif problem == 'after_revision':
        row['evidence'][0]['version'] = 1
    elif problem == 'unplanned_actor':
        xu.update(mode='visible')
    else:
        xu['actor'] = 'guess'
    with pytest.raises(ValueError, match='MATERIAL_EVIDENCE'):
        review_result(review_run(draft, [row]), {'checks':[rule]}, draft, None)


def test_fork_replacement_and_retirement_use_only_the_slots_in_the_selected_revision(monkeypatch):
    def item(**fields):
        return SimpleNamespace(**fields)
    chapters = [item(id=f'ch{i}',index=i) for i in (1,2,3)]
    scenes = [item(id=f's{i}',chapter_id=f'ch{i}',index=1) for i in (1,2,3)]
    store = item(list=lambda kind: chapters if kind == 'chapter' else scenes)
    records = {'a':['yan'], 'b':['mei'], 'unverified':[], 'now':['yan','lu']}
    def actual(store, scene, slot):
        ident = slot['draft_id']
        return {'scene_id':scene, 'draft_id':ident,'complete':ident!='unverified',
                'people':[{'actor':a,'presence':'onstage','mode':'action','reason':a+'独立推开门',
                           'start':0,'end':12,'quote':'他独立推开了挡路的那扇门'} for a in records[ident]]}
    monkeypatch.setattr(cast_appearances, 'accepted_scene',actual)
    monkeypatch.setattr('nw.story_state.approved_scene_positions',lambda s,snapshot:{})
    slots = {'s1':{'draft_id':'a','reviewed_cast':{'onstage':['yan'],'complete':True}},
             's2':{'draft_id':'unverified'},'s3':{'draft_id':'now'}}
    history = cast_appearances.planning_history(store, {'slots':slots})
    assert history['returning'] == ['yan'] and history['first_observed'] == ['lu']
    assert history['unverified_chapters'] == [2]
    replacement = deepcopy(slots)
    replacement['s1'] = {'draft_id':'b', 'reviewed_cast':{'onstage':['mei'],'complete':True}}
    fork = cast_appearances.planning_history(store, {'slots':replacement, 'stale_plan_scenes':['s2']})
    assert fork['first'] == ['lu','yan'] and not fork['returning'] and not fork['unverified_chapters']
    assert fork['first_positions'] == {'mei':[1,1], 'yan':[3,1], 'lu':[3,1]}
