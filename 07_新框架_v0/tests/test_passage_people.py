from copy import deepcopy
import json

import pytest

from nw.materials import passage_people as people
from nw.materials.narration import scene_check


SCENE = 'counter'
CARDS = {
    'examiner': {'role':'验票员','name':'老黄','voice':'报清号码再说明手续','background':'经办过三年挂失'},
    'traveler': {'role':'候车人','name':'旅客','casting':{'public_identity':'灰衣旅客'}},
}
NEED = '柜台需要辨清谁提出挂失'


def guide(text, mode, owner=None, witnessed=(), ref='scene:counter:goal'):
    return {'scene':SCENE,'observable':text,'check':'核实本拍可见行为',
            'narration':{'mode':mode,'owner':owner,'time':'current','basis_ref':ref,'basis_quote':'柜台',
                         'effect':'下一拍有人响应','witnesses':list(witnessed)}}


GUIDES = [
    guide('候车厅外一排人看向柜台。','summary'),
    guide('验票员当面叫号，他让后面的人亮出票。','speech','examiner',['traveler']),
    guide('灰衣旅客抬起票说：“我的票撕了一角，我报失。”','speech','traveler',['examiner']),
    guide('验票员用手比了比撕口，看到半个墨印。','perception','examiner'),
    guide('“六三七，缺右角。先到东窗销旧号。”验票员把票递回来。','speech','examiner',['traveler']),
    guide('灰衣旅客转身到了东窗，把旧票压在账台上。','action','traveler',['examiner']),
    guide('教练的办公室里只剩一盏手电。','summary'),
    guide('票面还有半个蓝印，兴许是昨天补的。','summary'),
    guide('验票员心想，他多半是想抢在封账之前补票。','inference','examiner'),
]


def plan(kind, actor, other, outcome, positions, **extra):
    return {'scene':SCENE,'kind':kind,'actor':actor,'other':other,'outcome':outcome,**extra,
            'steps':[{'role':role,'beat':number,'quote':quote} for role,number,quote in positions]}


PLANS = {
    'identity_slice':plan('identity_slice','traveler',None,'partial',[('identity',3,'灰衣旅客')]),
    'authority_response':plan('authority_response','examiner','traveler','observed',
                              [('authority',2,'当面叫号'),('reaction',3,'抬起票')],position_quote='验票员'),
    'dialogue_turn':plan('dialogue_turn','examiner','traveler','answered',[('speech',2,'亮出票'),('response',3,'我报失')],
                         purpose='让对方说明票据的来意'),
    'professional_voice':plan('professional_voice','examiner','traveler','issued',
                              [('cue',4,'半个墨印'),('speech',5,'六三七，缺右角')],voice_quote='报清号码',practice_quote='经办过三年挂失'),
    'focus_boundary':plan('focus_boundary',None,None,'location_cut',
                          [('first',1,'候车厅外一排人'),('next',7,'教练的办公室里')],from_place='候车厅外',to_place='办公室'),
    'qualified_claim':plan('qualified_claim',None,None,'estimate',[('basis',4,'半个墨印'),('judgment',8,'兴许是昨天补的')],
                           qualifier='兴许'),
    'interpreted_motive':plan('interpreted_motive','examiner','traveler','interpretation',
                              [('decision',3,'我报失'),('reading',9,'他多半是想抢在封账之前补票')],experience_quote='经办过三年挂失'),
}


def case(plans, guides=None):
    needs = [{'scene':SCENE,'need_quote':NEED,'kind':kind} for kind in {p['kind'] for p in plans}]
    stage = {'people_needs':needs,'members':[{'key':SCENE,'kind':'scene',
             'body':{'goal':NEED,'pov':'examiner','characters':['traveler']}}],
             'selected_events':[{'scene':SCENE,'event':'checking'}]}
    products = {'scene_design':{'products':stage},'character_design':{'products':{'members':[
        {'key':key,'kind':'character','body':card} for key,card in CARDS.items()]}}}
    value = {'guidance':deepcopy(GUIDES if guides is None else guides),'people_design':deepcopy(plans)}
    return stage,products,value


@pytest.mark.parametrize('kind', PLANS)
def test_ordinary_scene_translates_each_selected_need_to_its_actual_character_turns(kind):
    stage,products,value = case([PLANS[kind]])
    people.validate('scene_design',stage,products,{})
    people.validate('expression_design',value,products,{})
    uses = people.uses(value,SCENE)
    assert uses[kind] == {s['beat'] for s in PLANS[kind]['steps']}
    payload = {}
    assert kind in people.prompt('scene_design',payload,products,{})
    assert 'people_design' in people.prompt('expression_design',payload,products,{})
    assert payload['people_needs']==stage['people_needs']
    with pytest.raises(ValueError, match='缺少本场实际表达'):
        people.validate('expression_design',{'guidance':value['guidance']},products,{})


@pytest.mark.parametrize('kind,change', [
    ('identity_slice',{'outcome':'revealed'}),
    ('authority_response',{'other':'examiner'}),
    ('authority_response',{'position_quote':'主角'}),
    ('dialogue_turn',{'outcome':'acted'}),
    ('dialogue_turn',{'other':None}),
    ('professional_voice',{'outcome':'performed'}),
    ('professional_voice',{'voice_quote':'市长的秘密'}),
    ('professional_voice',{'practice_quote':'反派'}),
    ('focus_boundary',{'to_place':'验票室'}),
    ('qualified_claim',{'actor':'traveler'}),
    ('qualified_claim',{'qualifier':'肯定'}),
    ('interpreted_motive',{'actor':'traveler','other':'examiner'}),
    ('interpreted_motive',{'experience_quote':'亲历了该旅客的内心想法'}),
])
def test_labels_cannot_substitute_for_observed_speaker_source_or_result(kind,change):
    _,products,value = case([PLANS[kind]])
    value['people_design'][0].update(change)
    with pytest.raises(ValueError):
        people.validate('expression_design',value,products,{})


def test_command_response_can_be_absent_or_subsequently_performed_by_listener():
    row = deepcopy(PLANS['professional_voice'])
    row.update(outcome='performed')
    row['steps'].append({'role':'performed','beat':6,'quote':'把旧票压在账台上'})
    _,products,value=case([row])
    people.validate('expression_design',value,products,{})
    value['guidance'][5]['narration']['owner']='examiner'
    with pytest.raises(ValueError, match='实际听者本人'):
        people.validate('expression_design',value,products,{})


def test_subject_cut_is_not_travel_or_an_opportunity_to_enter_the_traveler_s_thoughts():
    row=plan('focus_boundary','examiner','traveler','subject_cut',
             [('first',2,'后面的人亮出票'),('next',3,'灰衣旅客抬起票')])
    _,products,value=case([row])
    people.validate('expression_design',value,products,{})
    row['outcome']='inside_pov'
    value['people_design']=[row]
    with pytest.raises(ValueError,match='本场的视角人物'):
        people.validate('expression_design',value,products,{})


def test_uncertain_narrator_cannot_be_recycled_as_confirmation_and_author_private_basis_stays_out_of_writer():
    _,products,value=case([PLANS['qualified_claim'],PLANS['interpreted_motive']])
    value['guidance'].append(guide('旧票果真是昨天补的。','summary',ref='beat:8'))
    with pytest.raises(ValueError,match='不能被后续旁白'):
        people.validate('expression_design',value,products,{})
    value['guidance'].pop()
    products['expression_design']={'products':value}
    ids={'examiner':'card001','traveler':'card002'}
    checks=[scene_check(g,i,i,'examiner',ids,{'kind':'scene','text':'柜台'},evidence_policy=True)
            for i,g in enumerate(value['guidance'],1)]
    people.attach(checks,products,SCENE)
    check=checks[8]
    assert '经办过三年挂失' not in json.dumps(check['binding'],ensure_ascii=False)
    assert check['people_design'][0]['experience_quote']=='经办过三年挂失'
    assert '旁人如何解释' in people.review_prompt(checks)
    limit={'time':'current','start':24,'end':39,'holders':['card001','card002']}
    people.mark_audience(check,limit)
    assert limit['judgment_owner']=='card001' and limit['reported_only']
    for claim in ('belief','suspicion','plan'):
        op={'predicate':'挂失的意图','holder':'card002','claim':claim,'evidence':[{'start':26,'end':33}]}
        with pytest.raises(ValueError,match='当事人自己的想法'):
            people.validate_audience([op],[limit])
        people.validate_audience([{**op,'holder':'card001'}],[limit])
        people.validate_audience([{**op,'evidence':[*op['evidence'],{'start':42,'end':50}]}],[limit])
    unknown={}
    people.mark_audience(checks[7],unknown)
    assert unknown=={'reported_only':True, 'judgment_owner':None}


def test_need_and_design_are_bound_to_current_scene_but_optional_in_unrelated_work():
    stage,products,_=case([PLANS['dialogue_turn']])
    stage['people_needs'][0]['need_quote']='别的场景，拿不到的私事'
    with pytest.raises(ValueError,match='本场或已选事件'):
        people.validate('scene_design',stage,products,{})
    stage.pop('people_needs')
    people.validate('expression_design',{},products,{})
    assert not people.prompt('expression_design',{},products,{})


@pytest.mark.parametrize('origin', ['event','source'])
def test_matching_upstream_requirement_is_applied_without_duplicate_scene_declaration(origin):
    stage,products,value=case([PLANS['dialogue_turn']])
    row = {**stage.pop('people_needs')[0], 'event':'checking'}
    if origin=='event':
        products['plot_design']={'products':{'event_techniques':[row]}}
    else:
        stage['craft_choices']=[{**row,'source_ref':'test-source'}]
    packet={}
    people.prompt('expression_design',packet,products,{})
    assert packet['people_needs'][0]['kind']=='dialogue_turn'
    people.validate('expression_design',value,products,{})
    with pytest.raises(ValueError,match='缺少本场实际表达'):
        people.validate('expression_design',{'guidance':value['guidance']},products,{})


def test_independent_clauses_can_share_a_paragraph_but_one_phrase_cannot_certify_both_turns():
    from types import SimpleNamespace
    draft=SimpleNamespace(id='isolated-review')
    text='验票员叫他亮票。灰衣旅客把撕去一角的半票推过来。'
    evidence=[{'id':draft.id,'start':0,'end':len(text),'quote':text}]
    checks=[{'id':str(i),'narration_order':i,'people_design':[{'role':role,'scene':SCENE,'use':0}]}
            for i,role in enumerate(('speech','response'),1)]
    def judge(first,second):
        rows={str(i):{'status':'pass','reason':reason,'evidence':evidence} for i,reason in enumerate((first,second),1)}
        people.assess(checks,rows,draft)
        return rows
    assert judge('【实际台词】亮票','【当场回应】把撕去一角的半票推过来')['2']['status']=='pass'
    assert judge('笼统认为符合剧本','【当场回应】半票推过来')['1']['narration_issue']=='people_evidence'
    assert judge('【实际台词】亮票','【当场回应】亮票')['2']['narration_issue']=='people_order'


def test_qualifier_preserves_uncertainty_in_later_state_and_allows_new_wording():
    from types import SimpleNamespace
    draft=SimpleNamespace(id='isolated-review')
    item={'role':'judgment','kind':'qualified_claim','qualifier':'兴许','scene':SCENE,'use':0}
    check={'id':'uncertain','narration_order':1,'people_design':[item]}
    def assess(text,quote,marker):
        row={'status':'pass','reason':f'【判断原句】{quote}\n【限定词】{marker}', 'evidence':[
            {'id':draft.id,'start':0,'end':len(text),'quote':text}]}
        people.assess([check],{'uncertain':row},draft)
        return row
    source='他拿到旧票。右角似乎是后来补上的。他把票收回夹层。'
    row=assess(source,'右角似乎是后来补上的','似乎')
    assert row['status']=='pass'
    bound,=people.judgment_spans(check,row,draft.id)
    assert (bound['start'],bound['quote'])==(source.index('右角'),'右角似乎是后来补上的')
    row=assess('右角肯定是后来补上的。','右角肯定是后来补上的','肯定')
    assert row['narration_issue']=='people_evidence'


def test_ordinary_project_inherits_qualified_claim_writes_repairs_and_reopens(tmp_path):
    from dataclasses import replace
    from nw.materials.evidence import scene_materials
    from nw.materials.narration_review import check_state_audience
    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_material_stage_roundtrip import StageModel
    from test_material_workflow import choose
    from test_novel_flow import author, config

    basis = '封条底下透出半枚发灰的蓝印。'
    guess = '那道蓝印兴许是在交班时压上去的。'
    wrong = guess.replace('兴许是','肯定是')

    class OrdinaryModel(PhaseModel,StageModel):
        def __init__(self):
            super().__init__('fixture')
            self.reviews=0
            self.repairs=0

        def generate(self,messages,**params):
            payload=json.loads(messages[-1]['content'])
            result=super().generate(messages,**params)
            stage=payload.get('stage')
            if stage=='plot_design' and payload['scope']!='book':
                raw=json.loads(result.text); node=raw['products']['event_nodes'][0]
                raw['products']['event_techniques']=[{'kind':'qualified_claim','event':node['id'],'need_quote':node['goal']}]
                result.text=json.dumps(raw,ensure_ascii=False)
            elif stage=='expression_design' and payload['scope']!='book':
                assert payload['people_needs'][0]['kind']=='qualified_claim' and not payload.get('passage_choices')
                raw=json.loads(result.text)
                guides=raw['products']['guidance']; last=guides[-1]; n=len(guides)+1; scene=last['scene']
                actual=payload['inputs']['scene_design']['products']['members'][0]['body']['goal']
                pre=guide(basis,'summary',ref=f'scene:{scene}:goal')
                pre['scene']=scene; pre['narration']['basis_quote']=actual
                follow=guide(guess,'summary',ref=f'beat:{n}')
                follow['scene']=scene; follow['narration']['basis_quote']=basis
                guides.extend((pre,follow))
                row=plan('qualified_claim',None,None,'estimate',[('basis',n,'半枚发灰的蓝印'),('judgment',n+1,guess)],
                         qualifier='兴许')
                raw['products']['people_design']=[{**row,'scene':scene}]; result.text=json.dumps(raw,ensure_ascii=False)
            elif 'material_review' in payload:
                self.reviews+=1
                assert '判断原句' in messages[0]['content']
                raw=json.loads(result.text)
                checks={r['id']:r for r in payload['material_review']['checks']}
                for r in raw['material_checks']:
                    check=checks[r['id']]
                    if items:=check.get('people_design'):
                        if items[0]['role']=='basis':
                            r['reason']='当下看到封条印迹。\n【判断根据】半枚发灰的蓝印'
                        else:
                            text=wrong if self.reviews==1 else guess
                            word='肯定' if self.reviews==1 else '兴许'
                            r['reason']=f'从印的位置推测交班经过。\n【判断原句】{text}\n【限定词】{word}'
                result.text=json.dumps(raw,ensure_ascii=False)
            elif 'items' in payload or payload.get('review'):
                packet=payload.get('context',payload)
                assert any('people_craft' in i['text'] for i in packet['items'] if i['source'].startswith('material:work:narration:'))
                if payload.get('review'):
                    self.repairs+=1
                    assert any(r.get('fix')==people.FIXES['people_evidence'] for r in payload['review']['material_checks'])
                result.text='[FAKE] 沈砚举灯揭开旧封条，纸边在他手上划了一道口子。'+basis+(guess if self.repairs else wrong)
            elif '{"operations"' in messages[0]['content']:
                limits=payload['context']['reader_only_spans']; restricted=next(s for s in limits if 'judgment_owner' in s)
                assert restricted['judgment_owner'] is None
                with pytest.raises(ValueError,match='独立凭据'):
                    check_state_audience([{'claim':'fact','holder':'WORLD','predicate':'补印时间','evidence':[restricted]}],limits)
                raw=json.loads(result.text)
                for op in raw['operations']:
                    op.setdefault('expected_old',None)
                    op['evidence'][0]['end']=payload['draft']['text'].index('。')+1
                result.text=json.dumps(raw,ensure_ascii=False)
            return result

    folder=tmp_path/'isolated'
    template_catalog(tmp_path)
    model=OrdinaryModel()
    with Store(folder,create=True,test_mode=True) as store:
        store.init_project('[FAKE] 估计的来由'); store.add_brief('沈砚从药铺柜前的封条追查交班。')
        adopt_story(store,baseline(),{})
        runtime=replace(config(store),source_driven=True)
        design=start_job(store,JobRequest('design',budget=Budget(42,140000,4800))).id
        result=resume_job(store,design,model,runtime)
        assert result.step=='plan:book:confirm',result.reason
        result=resume_job(store,design,model,runtime,choose)
        assert result.step=='plan:chapter:confirm',result.reason
        assert resume_job(store,design,model,runtime,choose).status=='DONE'
        scene,=store.list('scene')
        job=start_job(store,JobRequest('write',scene_ids=[scene.id],budget=Budget(16,140000,4800,1))).id
        result=resume_job(store,job,model,runtime,author())
        assert result.status=='DONE',result.reason
        assert (model.reviews,model.repairs)==(2,1)
    with Store(folder,test_mode=True) as reopened:
        assert reopened.get('draft',reopened.accepted(scene.id).draft_id).text.endswith(guess)
        records={r['stage']:r['products'] for r in scene_materials(reopened,scene.id)['work_session']['stages']}
        assert not records['scene_design'].get('passage_choices')
        assert records['expression_design']['people_design'][0]['actor'] is None
