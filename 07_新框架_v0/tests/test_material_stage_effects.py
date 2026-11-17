"""Periodic numeric checks use actual prose and accepted/evidenced state."""
import pytest


def test_pov_ratio_counts_real_text_instead_of_a_planned_percentage():
    from nw.materials.stage_effects import stage_metrics, metric_failure
    check = {'profile':'pov_process','binding':{'review_scope':{'chapters':[1,2,3,4,5]}},
             'process_artifact':{'protagonist':'yan','review_interval':5,'min_share':.7}, 'process_ids':{}}
    drafts = [{'chapter_index':i,'pov':'yan' if i==1 else 'other','text':'字'*100} for i in range(1,6)]
    result = stage_metrics(check,drafts,{})
    assert result['protagonist_share']==.2
    assert metric_failure(check,result)
    drafts[0]['text']='字'*1000
    assert not metric_failure(check,stage_metrics(check,drafts,{}))


def test_promise_closure_uses_the_whole_state_register_not_only_selected_payoffs():
    from nw.materials.stage_effects import stage_metrics, metric_failure
    check={'profile':'promise_process','binding':{'review_scope':{'chapters':[1,2,3]}},
           'process_artifact':{'closing':True,'payoff_min':.8}, 'process_ids':{}}
    states={f'promise-{i}':'paid_off' if i<2 else 'sleeping' for i in range(5)}
    result=stage_metrics(check,[],states)
    assert result['registered']==5 and result['paid_off']==2
    assert metric_failure(check,result)


def test_unknown_viewpoint_does_not_count_as_verified_protagonist_prose():
    from nw.materials.stage_effects import stage_metrics, metric_failure
    check={'profile':'pov_process','binding':{'review_scope':{'chapters':[1,2,3,4,5]}},
           'process_artifact':{'protagonist':'yan','review_interval':5,'min_share':.7}, 'process_ids':{}}
    drafts=[{'chapter_index':i,'pov':None,'text':'字'*100} for i in range(1,6)]
    assert metric_failure(check,stage_metrics(check,drafts,{}))


def test_previous_chapter_context_is_not_revalidated_as_a_current_switch():
    from nw.materials.stage_effects import viewpoint_mismatches
    check={'binding':{'review_scope':{'chapters':[2]}},'process_ids':{},'process_artifact':{'switches':[
        {'scene':'s1','from_pov':None}, {'scene':'s2','from_pov':'yan'}, {'scene':'s3','from_pov':'yan'}]}}
    drafts=[{'scene_id':'scene2','scene_card_id':'s2','chapter_index':1,'scene_index':2,'pov':'yan'},
            {'scene_id':'scene3','scene_card_id':'s3','chapter_index':2,'scene_index':1,'pov':'yan'}]
    assert viewpoint_mismatches(check,drafts)==[]
