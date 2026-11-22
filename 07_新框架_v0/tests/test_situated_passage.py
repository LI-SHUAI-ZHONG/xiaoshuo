"""Project and prose boundaries for ordinary scene techniques."""
import json
from types import SimpleNamespace

import pytest

from nw.materials import situated_passage as craft
from nw.task_models import content_sha256


def record(**products):
    return {'products':products}


def fixture(kind):
    fact = {'claim':'fact','holder':'READER','value':'旧站仍在东门。','disclosure_order':[1,1,1],'story_order':1}
    ctx = {'accepted_state':[fact]}
    products = {
        'plot_design':record(event_nodes=[{'id':'gate','setting':'晚班验票窗口','goal':'放行旅客','actors':['clerk','qing']}]),
        'character_design':record(members=[{'key':'clerk','kind':'character','body':{'role':'负责核验车票的值班员'}}]),
        'action_design':record(candidates=[{'id':'hand','event':'gate','action':'递交候车凭条','actor':'clerk',
                                            'steps':[{'object':'候车凭条','action':'交给阿青','result':'凭单等候'}]}]),
        'world_design':record(members=[{'key':'rail','kind':'world','body':{'visibility':'public','rule':'验票后须等候点名。'}}]),
    }
    need = {'scene':'east','event':'gate','kind':kind,'need_quote':'验票窗口','reason':'要让读者知道队列如何开始通行'}
    if kind in craft.PARTIES:
        first,second=craft.PARTIES[kind]
        need['parties']={first:'clerk', second:'qing'}
    if kind=='rule_in_force':
        need.update(world='rail',rule_quote='验票后须等候点名。',authority_quote='负责核验车票')
    if kind=='object_transfer':
        need.update(action='hand',step=1,object_quote='凭条')
    if kind=='action_completion':
        products['action_design']['products']['candidates'][0].update(action='关闭列车的手动闸',
            steps=[{'object':'检修手闸','action':'把闸把扳到底','result':'指针落回零位'}])
        need.update(action='hand',step=1,result_quote='指针落回零位')
    if kind=='orientation':
        need['known_quote']=fact['value']
    if kind in ('orientation','spatial_cue'):
        need['place_quote']='东门' if kind=='orientation' else '验票口'
    if kind=='ongoing_activity':
        need.update(subject_quote='值班员',activity_quote='逐张验票')
    scene = {'selected_events':[{'scene':'east','event':'gate'}], 'selected_actions':[{'scene':'east','action':'hand'}],
             'chapters':[{'index':2,'scenes':[{'card':'east','index':1,'story_order':2}]}],
             'members':[{'key':'east','kind':'scene','body':{'pov':'qing','characters':['clerk'],'location':'东门验票口',
                                                            'entering_state':'值班员已在窗口逐张验票。'}}],
             'situated_needs':[need]}
    products['scene_design']=record(**scene)
    return products, ctx, scene


EXAMPLES = {
    'orientation': [('time','黄昏时'),('place','东门窗外'),('ongoing','三排队伍都在往前挪。')],
    'ongoing_activity': [('underway','窗口的值班员逐张验票，票根在桌角积成了小堆。')],
    'event_start': [('ready','最后一班车的旅客到齐了。'),('signal','站员敲响窗口的木铃。'),('response','阿青把票塞进窗口。')],
    'spatial_cue': [('position','验票口在队尾左边。'),('directed_action','站员伸手就拦住了想从队尾溜走的人。')],
    'sensory_evidence': [('sensation','一滴雨敲在檐下的旧壶上。'),('impression','连细弱的水声都听得见。')],
    'expectation_reveal': [('familiar','黑板前竖着成排课桌。'),('exception','翻开笔记，第一页竟画着闸机线路。'),
                           ('understanding','原来这是站员训练班。')],
    'place_function': [('activity','墙边两名学生轮流报站。'),('fixture','桌前的讲台装着整排呼叫按钮。'),
                       ('purpose','读者辨出这里是站务人员的实训室。')],
    'rule_in_force': [('trigger','旧票上的出站时间已经过了。'),('terms','站员告诉阿青须等下一班点名。'),
                      ('decision','阿青点头，在候车栏签下姓名。')],
    'action_completion': [('executed','站员的手掌压住闸把，一直扳到了底。'),('completed','仪表盘上摇晃的指针停在了零位。')],
    'object_transfer': [('delivery','站员把候车凭条推给阿青。'),('received','阿青把纸攥在了手心里。'),
                       ('pending','下一班也许能补到座。')],
}


def expression(kind):
    seq, guides = [], []
    for role, line in EXAMPLES[kind]:
        if role in craft.READER_EFFECT:
            guides[-1]['narration']['effect']=line
        else:
            owner = ('clerk' if role in ('signal','terms','delivery','executed') else 'qing')
            mode = 'speech' if role in ('terms','pending') else 'action'
            guides.append({'scene':'east','observable':line,'narration':{'time':'current','mode':mode,'owner':owner,
                          'witnesses':['qing' if owner=='clerk' else 'clerk'],'effect':'读者能据此辨明现场变化'}})
        seq.append({'role':role,'beat':len(guides),'quote':line})
    return {'guidance':guides,'situated_beats':[{'scene':'east','kind':kind,'marks':seq}]}


def checks_for(value):
    return [{'id':f'work:narration:east:{i}', 'narration_order':i,'binding':{'observable':json.dumps(
        {'observable':g['observable'],'effect':g['narration']['effect']}),'check':'核对此拍'}} for i,g in enumerate(value['guidance'],1)]


@pytest.mark.parametrize('kind', craft.KINDS)
def test_one_scene_uses_upstream_need_and_only_approved_observables_reach_prose(kind):
    from nw.materials import passage_craft
    products,ctx,scene=fixture(kind)
    plot=products['plot_design']['products']
    plot['event_techniques']=[{'event':'gate','kind':kind,'need_quote':'放行旅客'}]
    passage_craft.validate('plot_design',plot,products,ctx)
    passage_craft.validate('scene_design',scene,products,ctx)
    value=expression(kind)
    passage_craft.validate('expression_design',value,products,ctx)
    assert craft.uses(value,'east')=={kind:set(range(1,len(value['guidance'])+1))}
    assert not craft.uses(value,'neighbor')
    checks=checks_for(value)
    passage_craft.attach(checks,{**products, 'expression_design':record(**value)},'east',ctx)
    assert all('situated_roles' in json.loads(c['binding']['observable']) and 'situated_checks' in c for c in checks)
    assert all('要让读者知道队列' not in c['binding']['observable'] for c in checks)
    assert craft.REVIEWS[kind] in craft.review_prompt(checks)
    if kind=='orientation':
        assert next(c['situated_known_sha256'] for c in checks if 'situated_known_sha256' in c)==content_sha256(ctx['accepted_state'][0])
    if kind=='object_transfer':
        assert [bool(c.get('situated_pending')) for c in checks]==[False,False,True]
        assert checks[1]['situated_checks'][0]['selected_step']['result']=='凭单等候'


@pytest.mark.parametrize('change', ['unseen','future','uncertain','cropped'])
def test_previously_known_must_have_been_available_to_this_reader(change):
    products,ctx,scene=fixture('orientation')
    if change=='unseen':
        ctx['accepted_state'][0]['holder']='clerk'
    if change=='future':
        ctx['accepted_state'][0]['disclosure_order']=[3,1,0]
    if change=='uncertain':
        ctx['accepted_state'][0]['claim']='suspicion'
    if change=='cropped':
        scene['situated_needs'][0]['known_quote']='东门'
    with pytest.raises(ValueError, match='读者事实'):
        craft.validate('scene_design',scene,products,ctx)


@pytest.mark.parametrize('change', ['other_event','other_action','wrong_item','wrong_step','outsider','missing_rule','lost_condition','private_rule','no_authority'])
def test_cannot_copy_wrong_prerequisite_or_unavailable_rule(change):
    kind='rule_in_force' if change in ('missing_rule','lost_condition','private_rule','no_authority') else 'object_transfer'
    products,ctx,scene=fixture(kind)
    need=scene['situated_needs'][0]
    if change=='other_event':
        need['event']='late'
    if change=='other_action':
        scene['selected_actions']=[]
    if change=='wrong_item':
        need['object_quote']='站台钥匙'
    if change=='wrong_step':
        need['step']=0
    if change=='outsider':
        need['parties']['recipient']='absent'
    if change=='missing_rule':
        need['world']='foreign'
    if change=='lost_condition':
        need['rule_quote']='须等候点名。'
    if change=='private_rule':
        products['world_design']['products']['members'][0]['body'].update(visibility='holders',holders=['qing'])
    if change=='no_authority':
        products['character_design']['products']['members'][0]['body']['role']='来取票的旅客'
    with pytest.raises(ValueError):
        craft.validate('scene_design',scene,products,ctx)


@pytest.mark.parametrize('change', ['wrong_speaker','unheard','before_signal','only_thought','late_terms','same_detail','lost_role',
                                     'foreign_scene','skip','promised','wrong_object','same_outcome'])
def test_scene_expression_rejects_broken_orders_and_bad_evidence(change):
    kind = ('rule_in_force' if change in ('late_terms','unheard') else
            'expectation_reveal' if change in ('only_thought','same_detail') else
            'object_transfer' if change in ('promised','wrong_object','same_outcome') else 'event_start')
    products,ctx,_=fixture(kind)
    value=expression(kind)
    plan=value['situated_beats'][0]
    marks=plan['marks']
    if change=='wrong_speaker':
        value['guidance'][1]['narration']['owner']='qing'
    if change=='unheard':
        value['guidance'][1]['narration']['witnesses']=[]
    if change in ('late_terms','before_signal'):
        marks[1],marks[2]=marks[2],marks[1]
    if change=='only_thought':
        value['guidance'][1]['narration']['mode']='thought'
    if change=='same_detail':
        marks[1].update(beat=1,quote=marks[0]['quote'])
    if change=='lost_role':
        marks.pop(1)
    if change=='foreign_scene':
        plan['scene']='other'
    if change=='skip':
        value.pop('situated_beats')
    if change=='promised':
        value['guidance'][1]['narration']['mode']='speech'
    if change=='wrong_object':
        value['guidance'][0]['observable']=marks[0]['quote']='站员把门钥匙交给阿青。'
    if change=='same_outcome':
        marks[-1].update(beat=2,quote='将来或能补座')
        value['guidance'][1]['observable']+='将来或能补座'
    with pytest.raises(ValueError):
        craft.validate('expression_design',value,products,ctx)


def test_ordinary_scene_does_not_inherit_other_scene_techniques():
    products,ctx,scene=fixture('orientation')
    del scene['situated_needs']
    products['scene_design']=record(**scene)
    ordinary={'guidance':[]}
    craft.validate('expression_design',ordinary,products,ctx)
    assert craft.prompt('expression_design',{},products,ctx)==''
    assert craft.schema_fields('world_design')=={}
    assert 'object_transfer' in craft.prompt('scene_design',{},products,ctx)
    assert craft.review_prompt([])==''


def test_key_action_supports_non_transfer_and_distinguishes_intent_from_completion():
    products,ctx,scene=fixture('action_completion')
    need=scene['situated_needs'][0]
    need['result_quote']='事故已经排除'
    with pytest.raises(ValueError,match='完整结果'):
        craft.validate('scene_design',scene,products,ctx)
    need['result_quote']='指针落回零位'
    value=expression('action_completion')
    value['guidance'][-1]['narration']['mode']='speech'
    with pytest.raises(ValueError,match='完成标志'):
        craft.validate('expression_design',value,products,ctx)


def test_relative_position_cannot_be_relocated_between_the_card_and_expression():
    products,ctx,scene=fixture('spatial_cue')
    need=scene['situated_needs'][0]
    need['place_quote']='码头'
    with pytest.raises(ValueError,match='真实地点'):
        craft.validate('scene_design',scene,products,ctx)
    need['place_quote']='验票口'
    value=expression('spatial_cue')
    value['guidance'][0]['observable']=value['situated_beats'][0]['marks'][0]['quote']='码头在队尾左侧。'
    with pytest.raises(ValueError,match='场地标志'):
        craft.validate('expression_design',value,products,ctx)


def test_chapter_can_require_running_activity_without_requiring_location_or_a_protagonist_entrance():
    from nw.materials import passage_craft
    products,ctx,scene=fixture('ongoing_activity')
    products['plot_design']['products']['event_techniques']=[{'event':'gate','kind':'ongoing_activity','need_quote':'放行旅客'}]
    required=scene['situated_needs'].pop()
    # A place reference is a valid design in its own right. It cannot fulfil the other order.
    scene['situated_needs']=[{'scene':'east','event':'gate','kind':'orientation','place_quote':'东门',
                              'need_quote':'验票窗口','reason':'先认出队伍所在的门。'}]
    with pytest.raises(ValueError,match='现场写法缺少'):
        passage_craft.validate('scene_design',scene,products,ctx)
    scene['situated_needs']=[required]
    products['scene_design']=record(**scene)
    passage_craft.validate('scene_design',scene,products,ctx)
    value=expression('ongoing_activity')
    beat=value['guidance'][0]['narration']
    beat.update(owner=None,mode='summary',witnesses=[])
    passage_craft.validate('expression_design',value,products,ctx)
    checks=checks_for(value)
    checks[0]['binding']['observable']=json.dumps({'observable':value['guidance'][0]['observable'],'audience':'reader_only'})
    passage_craft.attach(checks,{**products,'expression_design':record(**value)},'east',ctx)
    assert json.loads(checks[0]['binding']['observable'])['audience']=='reader_only'
    with pytest.raises(ValueError,match='须逐一落实'):
        passage_craft.validate('expression_design',{'guidance':value['guidance']},products,ctx)
    mark=value['situated_beats'][0]['marks'][0]
    mark['quote']=value['guidance'][0]['observable']='东门验票口外一片红。'
    with pytest.raises(ValueError,match='原有活动'):
        passage_craft.validate('expression_design',value,products,ctx)


@pytest.mark.parametrize('kind', craft.KINDS)
def test_review_marks_require_real_scene_local_evidence_and_roles_in_order(kind):
    products,ctx,_=fixture(kind)
    expr=expression(kind)
    checks=checks_for(expr)
    craft.attach(checks,{**products,'expression_design':record(**expr)},'east',ctx)
    draft=SimpleNamespace(id='d',text=''.join(g['observable'] for g in expr['guidance']))
    evidence=[{'id':'d','start':0,'end':len(draft.text),'quote':draft.text}]
    rows={}
    for check,guide in zip(checks,expr['guidance']):
        reason=[]
        for item in check['situated_checks']:
            role=item['role']
            label=craft.LABELS[role]
            reason.append(f'【{label}】{guide["observable"]}')
            if 'actor' in item:
                reason.append(f'【{label}归属】{item["actor"]}')
            if role in craft.EXPLAIN:
                reason.append(f'【{craft.EXPLAIN[role]}】{guide["narration"]["effect"]}')
        rows[check['id']]={'id':check['id'],'reason':'\n'.join(reason),'status':'pass','evidence':evidence}
    craft.assess(checks,rows,draft)
    assert all(r['status']=='pass' for r in rows.values())
    for check,guide in zip(checks,expr['guidance']):
        spans=craft.situated_spans(check,rows[check['id']],draft.id)
        assert [s['quote'] for s in spans]==[guide['observable']]
    if kind=='object_transfer':
        [pending] = craft.pending_spans(rows[checks[-1]['id']],draft.id)
        assert pending['quote']=='下一班也许能补到座。'
        assert pending['start']==draft.text.index(pending['quote'])
    bad=rows[checks[-1]['id']]
    if kind=='event_start':
        bad['reason']=bad['reason'].replace('】qing','】clerk')
    elif kind in ('orientation','object_transfer','spatial_cue'):
        bad['reason']=bad['reason'].replace(expr['guidance'][-1]['observable'],expr['guidance'][0]['observable'])
    else:
        bad['reason']='这些方面在正文中都已经清楚。'
    craft.assess(checks,rows,draft)
    assert bad['status']=='failed' and bad['narration_issue'] in craft.FIXES
    assert not craft.situated_spans(checks[-1],bad,draft.id)
