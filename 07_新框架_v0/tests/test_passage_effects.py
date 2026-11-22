"""Design, independently localize and carry only the effects which survive the manuscript."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from nw.materials import chapter_progress, passage_effects as effects
from test_chapter_progress import designs
from test_material_action_review import draft, review_run, span


TEXTS = ['一刻钟后，等候的人少了一半。','卷角压着一本《气血入门》，学生们照常答题。','他拿到了明天可以领卷的凭单。']


def design():
    guides = [{'scene':'river','observable':line,'narration':{'mode':mode}} for line,mode in zip(TEXTS,('summary','action','action'))]
    def row(kind,beat,**extra):
        return {'kind':kind,'scene':'river','beat':beat,'cue':TEXTS[beat-1][0:4],**extra}
    pair = {'from_beat':1,'from_cue':'一刻钟后','reason':'等候的人已经变少，接下来展开卷上真正的科目'}
    effects_plan = [row('pace_switch',2,**pair,mode='resume_scene'),row('paragraph_turn',2,**pair,mode='break'),
                    row('detail_value',2,function='meaning', loss='少了辨认课程的书名'),
                    row('reader_change',2,before='以为普通高考',after='看出是武道科目',story_cue=None),
                    row('local_handoff',3,status='eligible',next='明天拿凭单领卷')]
    return {'guidance':guides,'effects_plan':effects_plan}


def case():
    value=design()
    checks=[{'id':str(i),'narration_order':i,'binding':{'check':'现场可见'},
             'method_artifact':{'scene':'river'}} for i in range(1,4)]
    records={'expression_design':{'products':value}}
    effects.attach(checks,records,'river')
    draft=SimpleNamespace(text='\n'.join(TEXTS),id='draft1')
    reasons=['通过', '独立核过课程和段界。\n【详略前】一刻钟后\n【详略后】卷角压着\n【细节原句】《气血入门》\n'
             '【删后】读者就无法辨别正在考的是哪门课程\n【段界前】少了一半。\n【段界后】卷角压着\n【读者所得】《气血入门》',
             '只得到可以明日使用的凭单。\n【已获条件】他拿到了\n【尚待兑现】明天可以领卷']
    rows=[]
    for i,(line,reason) in enumerate(zip(TEXTS,reasons),1):
        pos=draft.text.index(line)
        rows.append({'id':str(i),'status':'pass','reason':reason,'evidence':[
            {'id':draft.id,'start':pos,'end':pos+len(line),'quote':line}]})
    return value,checks,rows,draft


def test_real_positions_and_separate_reader_and_eligibility_receipts():
    value,checks,rows,draft=case()
    records = {'scene_design':{'products':{'effect_needs':[
        {'scene':'river','kind':i['kind'],'need_quote':'已经在查验'} for i in value['effects_plan']]}}}
    effects.validate('expression_design',value,records, {})
    effects.assess(checks,rows,draft)
    assert all(r['status']=='pass' for r in rows)
    reader,=effects.accepted_outcomes(checks[1],rows[1],draft.id)
    available,=effects.accepted_outcomes(checks[2],rows[2],draft.id)
    assert reader['paragraph_outcome']=={'status':'reader','before':'以为普通高考','after':'看出是武道科目'}
    assert reader['evidence'][0]['quote']=='《气血入门》' and reader['possible_next_pressure'] is None
    assert available['paragraph_outcome']=={'status':'eligible'} and available['pressure_evidence'][0]['quote']=='明天可以领卷'
    assert [s['quote'] for s in effects.pending_spans(checks[2],rows[2],draft.id)]==['明天可以领卷']
    assert [s['quote'] for s in effects.effect_spans(checks[2],rows[2],draft.id)]==['他拿到了','明天可以领卷']
    assert all(s['start']>=rows[1]['evidence'][0]['start'] for s in effects.effect_spans(checks[1],rows[1],draft.id))
    assert effects.uses(value,'river')['paragraph_turn']=={1,2} and not effects.uses(value,'elsewhere')
    assert 'effects_plan' in effects.schema_fields('expression_design') and 'effect_needs' in effects.schema_fields('scene_design')
    assert effects.review_prompt(checks) and not effects.review_prompt([])


@pytest.mark.parametrize('failure',('wrong_scene','backward','misleading_summary','identical_reader','invented_state','completed_plus_promise','empty_loss'))
def test_cannot_substitute_labels_for_the_selected_scene(failure):
    value=design()
    p=value['effects_plan']
    if failure=='wrong_scene': p[0]['scene']='bank'
    if failure=='backward': p[1]['from_beat']=3
    if failure=='misleading_summary': value['guidance'][0]['narration']['mode']='speech'
    if failure=='identical_reader': p[3]['after']=p[3]['before']
    if failure=='invented_state': p[3]['story_cue']='学生突然明白了世界的真相'
    if failure=='completed_plus_promise': p[4]['status']='completed'
    if failure=='empty_loss': p[2]['loss']=p[2]['cue']
    with pytest.raises(ValueError): effects.validate('expression_design',value,{}, {})


@pytest.mark.parametrize('failure,issue',(('no_break','effect_layout'),('not_prior_evidence','effect_layout'),
                                         ('meaningless_cut','effect_review'),('future_act','effect_handoff')))
def test_review_catches_fake_break_wrong_prior_cut_and_advanced_receipt(failure,issue):
    value,checks,rows,draft=case()
    if failure=='no_break': draft.text=draft.text.replace('\n',' ')
    if failure=='not_prior_evidence': rows[1]['reason']=rows[1]['reason'].replace('【详略前】一刻钟后','【详略前】其他教室')
    if failure=='meaningless_cut': rows[1]['reason']=rows[1]['reason'].replace('读者就无法辨别正在考的是哪门课程','《气血入门》')
    if failure=='future_act': rows[2]['reason']=rows[2]['reason'].replace('【已获条件】他拿到了','【已获条件】他已经领到了试卷')
    effects.assess(checks,rows,draft)
    failed,=[r for r in rows if r['status']=='failed']
    assert failed['narration_issue']==issue


def test_reader_only_advance_can_leave_character_and_world_unchanged():
    scene,records,context=designs()
    context['passage_craft_policy']='scene-craft-v1'
    progress=scene['scene_progress'][0]
    progress['change']='reader'
    body=scene['members'][0]['body']
    body['planned_result']=body['entering_state']
    chapter_progress.validate(scene,records,context)
    value=design()
    value['effects_plan']=[r for r in value['effects_plan'] if r['kind']=='reader_change']
    effects.validate('expression_design',value,records,context)
    with pytest.raises(ValueError,match='读者理解推进'):
        effects.validate('expression_design',{'guidance':value['guidance']},records,context)
    with pytest.raises(ValueError,match='实际推进'):
        chapter_progress.validate(scene,records,{**context,'passage_craft_policy':None})


def test_free_scene_chooses_just_its_own_event_effect_and_pays_no_expression_cost_otherwise():
    scene,records,_ = designs()
    empty={}
    assert effects.prompt('expression_design',empty,records,{})=='' and empty=={}
    assert not effects.schema_fields('expression_design',[])
    scene['effect_needs']=[{'scene':'river','kind':'detail_value','need_quote':'雨幕'}]
    effects.validate('scene_design',scene,records,{})
    payload={}
    text=effects.prompt('expression_design',payload,records,{})
    assert 'detail_value' in text and 'reader_change' not in text
    assert payload['effect_needs']==scene['effect_needs']
    selected=effects.schema_fields('expression_design',['detail_value'])['effects_plan']['items']['anyOf']
    assert {s['properties']['kind']['const'] for s in selected}=={'detail_value'}
    assert {s['properties']['decision']['const'] for s in selected}=={'keep','omit'}
    with pytest.raises(ValueError,match='须在本场落实'):
        effects.validate('expression_design',{},records,{})
    scene['effect_needs'][0]['need_quote']='另一个场的需求'
    with pytest.raises(ValueError): effects.validate('scene_design',scene,records,{})


def test_an_unstated_future_is_not_eligible_as_a_confirmed_next_chapter_opening():
    _,checks,rows,draft=case()
    text='他拿到了一张盖有登记印的凭单。'
    draft.text=draft.text.replace(TEXTS[2],text)
    rows[2]['evidence'][0].update(end=len(draft.text),quote=text)
    rows[2]['reason']=rows[2]['reason'].replace('【尚待兑现】明天可以领卷','【后续呈现】本段未写')
    effects.assess(checks,rows,draft)
    carry,=effects.accepted_outcomes(checks[2],rows[2],draft.id)
    assert carry['paragraph_outcome']['status']=='eligible' and not carry['possible_next_pressure']
    assert not effects.pending_spans(checks[2],rows[2],draft.id)


def test_derived_event_inherits_effect_until_its_scene_explicitly_defers_it():
    scene,records,_=designs()
    records['plot_design']['products']['event_techniques']=[{'event':'patrol','kind':'detail_value','need_quote':'雨幕'}]
    records['event_design']={'products':{'candidates':[{'id':'follow','predecessor':'patrol'}]}}
    scene['selected_events'][0]['event']='follow'
    payload={}
    assert 'detail_value' in effects.prompt('expression_design',payload,records,{})
    assert payload['effect_needs']==[{'scene':'river','kind':'detail_value','need_quote':'雨幕'}]
    scene['craft_deferrals']=[{'scene':'river','parent_event':'patrol','kind':'detail_value'}]
    assert not effects.prompt('expression_design',{},records,{})


@pytest.mark.parametrize('scope',('paragraph','scene_lead'))
def test_omission_passes_using_retained_prose_and_only_fails_on_residue_in_the_chosen_scope(scope):
    kept='教室里只听得见铅笔在纸上摩擦的细响。'
    cut='靓女报到处' if scope=='scene_lead' else '教室一共五百平方米'
    kind='detail_value'
    item={'scene':'river','kind':kind,'beat':1,'cue':'铅笔在纸上','function':'platform' if scope=='scene_lead' else 'unused_scale',
          'decision':'omit','loss':'保留笔尖的声音就能说明教室此刻的安静与秩序','cut_text':cut,'cut_scope':scope}
    value={'guidance':[{'scene':'river','observable':kept,'narration':{'mode':'summary'}}],'effects_plan':[item]}
    records={'scene_design':{'products':{'effect_needs':[{'scene':'river','kind':kind,'need_quote':'定位教室'}]}},
             'expression_design':{'products':value}}
    effects.validate('expression_design',value,records,{})
    check={'id':'s','narration_order':1,'binding':{'check':'笔触可听见'},'method_artifact':{'scene':'river'}}
    effects.attach([check],records,'river')
    assert cut not in check['binding']['check']
    for contaminated in (False,True):
        text=(cut+('\n' if scope=='scene_lead' else '。') if contaminated else '')+kept+'\n另一页展板上印着：'+cut+'。'
        start=text.index(kept)
        row={'id':'s','status':'pass','reason':'已经写到教室里的秩序。\n【保留原句】铅笔在纸上摩擦的细响\n【删后】人群的安静仍能从实际声音中听出来',
             'evidence':[{'id':'d','start':start,'end':start+len(kept),'quote':kept}]}
        effects.assess([check],[row],SimpleNamespace(id='d',text=text))
        assert (row['status']=='failed')==contaminated


@pytest.mark.parametrize('mode,owner,actual',(('summary',None,'summary'),('scene','lin','speech')))
def test_one_ordinary_beat_can_choose_summary_or_enactment_without_a_switch(mode,owner,actual):
    sentence='往常查凭单只要一盏灯。' if mode=='summary' else '林执事说：“把凭单放进灯下。”'
    row={'scene':'river','kind':'presentation_mode','beat':1,'cue':'凭单','mode':mode,'owner':owner,'reason':'手续只在此处生效'}
    value={'guidance':[{'scene':'river','observable':sentence,'narration':{'owner':owner,'time':'current','mode':actual}}],
           'effects_plan':[row]}
    records={'scene_design':{'products':{'effect_needs':[{'scene':'river','kind':'presentation_mode','need_quote':'查凭单'}]}},
             'expression_design':{'products':value}}
    effects.validate('expression_design',value,records,{})
    check={'id':'beat','narration_order':1,'binding':{'check':'办理人用语'},'method_artifact':{'scene':'river'}}
    effects.attach([check],records,'river')
    mark='概述原句' if mode=='summary' else '现场原句'
    review={'id':'beat','status':'pass','reason':'核对本拍读者实际所见。\n【'+mark+'】'+sentence,
            'evidence':[{'id':'draft','start':0,'end':len(sentence),'quote':sentence}]}
    effects.assess([check],[review],SimpleNamespace(id='draft',text=sentence))
    assert review['status']=='pass'
    row['owner']='冒用旁人'
    with pytest.raises(ValueError,match='获准'): effects.validate('expression_design',value,records,{})


@pytest.mark.parametrize('line,reported,accepted',[
    ('选两条路的人数差不多，两边人数差不多。','两边人数差不多',True),
    ('选相亲的大约有半数。','大约有半数',True),
    ('选相亲的大约占50%。','大约占50%',True),
    ('选相亲的占50.00%。','占50.00%',False),
    ('选相亲的正好占百分之五十。','正好占百分之五十',False),
    ('选两条路的人数恰好一半一半。','一半一半',False),
    ('选相亲的绝非大概半数。','大概半数',False),
    ('选相亲的一共有九十八人。','一共有九十八人',False),
    ('选相亲的约占48.73%。','约占48.73%',False),
    ('选相亲的约占50.00%。','约占50.00%',False),
    ('选相亲的大约占五成，也就是50.00%。','大约占五成',False),
    ('选相亲的大约占五成，正好隔壁免考的占20%。','大约占五成',True),
    ('选相亲的大约占了五成，隔壁免考的占20%。','大约占了五成',True)])
def test_independent_summary_review_preserves_estimated_split_but_allows_other_recorded_figures(draft,line,reported,accepted):
    from nw.materials import action_review
    statement='选相亲的学子大概半数。'
    separate_fact='登记簿上有十二名执事。'
    guide={'scene':'river','observable':'交代两条去向的分布','narration':{'basis_quote':statement,'owner':None,'mode':'summary','time':'current'}}
    item={'kind':'presentation_mode','scene':'river','beat':1,'cue':'两条去向','owner':None,'mode':'summary','reason':'同类登记只须交代概况'}
    checks=[{'id':'work:narration:river:1','profile':'method_work','narration_order':1,'binding':{'check':'保持范围'},'method_artifact':guide},
            {'id':'work:narration:river:2','profile':'method_work','narration_order':2,'binding':{'check':'源于名册'},
             'method_artifact':{'scene':'river','narration':{'basis_quote':separate_fact}}}]
    records={'expression_design':{'products':{'guidance':[guide,checks[1]['method_artifact']],'effects_plan':[item]}}}
    effects.attach(checks,records,'river')
    assert checks[0]['summary_estimates']==['大概半数'] and 'summary_estimates' not in checks[1]
    assert '【概数1】' in effects.review_prompt(checks)
    draft=replace(draft,text=line+separate_fact)
    rows=[{'id':checks[0]['id'],'status':'pass','reason':'核过读者看到的两种选择。\n【概述原句】'+line+'\n【概数1】'+reported,
           'evidence':[span(draft,0,len(line))]},
          {'id':checks[1]['id'],'status':'pass','reason':'名册印证现有的执事人数。',
           'evidence':[span(draft,len(line),len(draft.text))]}]
    result=action_review.review_result(review_run(draft,rows),{'checks':checks},draft,None)
    assert result['recommendation']==('pass' if accepted else 'revise')
    assert result['material_checks'][0]['narration_issue']==('as_designed' if accepted else 'effect_estimate')
    assert result['material_checks'][1]['status']=='pass'


@pytest.mark.parametrize('mode,quick', [('resume_scene',1),('enter_summary',2)])
def test_pace_switch_only_guards_an_estimate_in_its_summary_basis(mode,quick):
    a,b=1,2
    step={'scene':'river','kind':'pace_switch','beat':b,'from_beat':a,'mode':mode}
    for source in ('登记后堂内大约二十人。','执事核实堂内二十人。','他向前走了半步。'):
        guides=[{'scene':'river','narration':{'basis_quote':source}} for _ in (a,b)]
        records={'expression_design':{'products':{'guidance':guides,'effects_plan':[step]}}}
        checks=[{'id':str(i),'narration_order':i,'method_artifact':g,'binding':{'check':'按选择的快慢切换。'}}
                for i,g in enumerate(guides,1)]
        effects.attach(checks,records,'river')
        guarded=[c for c in checks if 'summary_estimates' in c]
        if '大约' in source:
            assert [c['narration_order'] for c in guarded]==[quick]
            assert guarded[0]['summary_estimates']==['大约二十人']
            assert '【概数1】' in effects.review_prompt(guarded)
            for text,good in [('约有20位学子',True),('20位学子',False),('大约二十人，另有三人候补',True)]:
                assert effects._kept_estimate('大约二十人',{'quote':text,'start':0},text)==good
        else:
            assert not guarded and '概数1' not in effects.review_prompt(checks)


def test_summary_cannot_strip_the_qualifier_from_an_approved_earlier_beat():
    scene,records,_=designs()
    scene['effect_needs']=[{'scene':'river','kind':'presentation_mode','need_quote':'雨幕'}]
    guide={'scene':'river','observable':'交代往年入门登记的两种去向','narration':{'mode':'summary','time':'current','owner':None,
           'basis_ref':'beat:1','basis_quote':'半数'}}
    value={'guidance':[{'scene':'river','observable':'前一批选择相亲的约有半数，另一栏已经核验有十二名执事。'},guide],
           'effects_plan':[{'scene':'river','kind':'presentation_mode','beat':2,'cue':'两种去向','mode':'summary','owner':None,'reason':'同类过程已经交代'}]}
    with pytest.raises(ValueError,match='估计程度'):
        effects.validate('expression_design',value,records,{})
    for permitted in ('约有半数','十二名执事'):
        guide['narration']['basis_quote']=permitted
        effects.validate('expression_design',value,records,{})


def test_accepted_manuscript_distinguishes_completed_eligible_and_the_readers_inference_on_reopen(tmp_path):
    from nw.chapter_state import continuation_chapter_state
    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.store import Store
    from nw.story_state import adopt_story, current_head, revision_state
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import template_catalog
    from test_material_workflow import choose
    from test_novel_flow import author, config
    from test_passage_prose import PassageModel

    class OutcomeModel(PassageModel):
        def generate(self,messages,**params):
            data=json.loads(messages[-1]['content'])
            result=super().generate(messages,**params)
            if data.get('stage')=='scene_design':
                raw=json.loads(result.text)
                selected,=raw['products']['passage_choices']
                raw['products']['effect_needs']=[{'scene':selected['scene'],'kind':kind,'need_quote':selected['need_quote']}
                                                for kind in ('reader_change','local_handoff')]
                scene_body=next(r['body'] for r in raw['products']['members'] if r['key']==selected['scene'])
                scene_body['planned_result']=scene_body['entering_state']
                raw['products']['scene_progress'][0]['change']='reader'
                result.text=json.dumps(raw,ensure_ascii=False)
            if data.get('stage')=='state_transition':
                raw=json.loads(result.text)
                for patch in raw['products']['patches']:
                    patch['planned_result']=next(r['body']['entering_state'] for r in data['inputs']['scene_design']['products']['members']
                                                 if r['key']==patch['scene'])
                result.text=json.dumps(raw,ensure_ascii=False)
            if data.get('stage')=='expression_design':
                raw=json.loads(result.text)
                prod=raw['products']
                seq,=prod['passage_sequences']
                scene=seq['scene']
                demo,skip,choice,end=seq['steps']
                prod['effects_plan']=[
                    {'scene':scene,'kind':'local_handoff','beat':demo['beat'],'cue':'当场拿到一盏灯','status':'completed','next':None},
                    {'scene':scene,'kind':'reader_change','beat':choice['beat'],'cue':'把借条推回去','before':'以为每个人都要借灯',
                     'after':'知道还可借日光看看','story_cue':'他把借条推回去'},
                    {'scene':scene,'kind':'local_handoff','beat':end['beat'],'cue':'午后才能来取封条','status':'eligible','next':'午后拿凭单取件'}]
                result.text=json.dumps(raw,ensure_ascii=False)
            if 'material_review' in data:
                raw=json.loads(result.text)
                checks={c['id']:c for c in data['material_review']['checks']}
                for row in raw['material_checks']:
                    for item in checks[row['id']].get('paragraph_effects',()):
                        if row['status']!='pass':
                            continue
                        if item['kind']=='reader_change':
                            row['reason']+='\n【读者所得】指了指窗下的日光\n【现场所得】他把借条推回去'
                        elif item['status']=='completed':
                            row['reason']+='\n【已完成】当场拿到一盏灯'
                        else:
                            row['reason']+='\n【已获条件】他翻开领件凭单\n【尚待兑现】午后才能来取封条'
                result.text=json.dumps(raw,ensure_ascii=False)
            return result

    template_catalog(tmp_path)
    folder=tmp_path/'isolated'
    with Store(folder,create=True,test_mode=True) as store:
        store.init_project('[FAKE] 段落交接')
        store.add_brief('借日光核对被换的封条')
        adopt_story(store,baseline(),{})
        model=OutcomeModel('procedure_branch')
        runtime=replace(config(store),source_driven=True)
        ident=start_job(store,JobRequest('design',budget=Budget(44,140000,4800))).id
        for decision in (None,choose,choose):
            result=resume_job(store,ident,model,runtime,decision) if decision else resume_job(store,ident,model,runtime)
        assert result.status=='DONE',result.reason
        scene,=store.list('scene')
        writing=start_job(store,JobRequest('write',scene_ids=[scene.id],budget=Budget(16,140000,4800,1))).id
        done=resume_job(store,writing,model,runtime,author())
        assert done.status=='DONE',done.reason
    with Store(folder,test_mode=True) as store:
        head=current_head(store)
        state=revision_state(store,head)
        carry=continuation_chapter_state(store,head,state)
        selected={r['paragraph_outcome']['status']:r for r in carry['reviewed_progress'] if r.get('paragraph_outcome')}
        assert selected.keys()=={'reader','completed','eligible'}
        assert selected['reader']['paragraph_outcome']['story_evidence'][0]['quote']=='他把借条推回去'
        assert selected['completed']['evidence'][0]['quote']=='当场拿到一盏灯'
        options=chapter_progress.chapter_openings(carry)
        receipt,=[v for v in options.values() if v.get('paragraph_outcome')]
        assert receipt['possible_next_pressure']=='午后拿凭单取件' and receipt['evidence'][0]['quote']=='午后才能来取封条'
        assert all('paragraph_outcome' not in r for r in carry['changes']+carry.get('character_changes',[]))
        chapter_progress.verify_current([{'continuations':[{'prior':receipt}]}],[],state['slots'],(2,1,0))
        with pytest.raises(ValueError,match='已接受稿已经改变'):
            chapter_progress.verify_current([{'continuations':[{'prior':receipt}]}],[],{})
