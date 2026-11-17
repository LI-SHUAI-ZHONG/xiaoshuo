"""Procedural artifacts traverse real plan, write, review, state and reopen paths."""
import json

import pytest

from nw.llm.base import GenResult
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story, baseline_for, current_head, replay, revision_state, selected_operations
from nw.task_models import Budget
from story_fixture import baseline
from test_material_stage_integration import pins_for
from test_material_stage_procedures import output
from test_material_workflow import choose
from test_novel_flow import Model, author, config

KEYS = {'timeline_process':'126.9_时间线模板调用', 'promise_process':'126.10_伏笔网络模板调用',
        'pov_process':'126.11_多视角切换模板调用', 'preflight_process':'126.12_创作前一次性模板调用',
        'usage_process':'126.16_模板版本管理'}


class StageModel(Model):
    def __init__(self, profile, *, fail_scope=False):
        super().__init__(); self.profile=profile; self.fail_scope=fail_scope

    def generate(self,messages,**params):
        prompt=messages[0]['content']; data=json.loads(messages[-1]['content'])
        if any(marker in prompt for marker in ('[MATERIAL_WORK]','[MATERIAL_STEP]','[MATERIAL_ASSEMBLY]')):
            return super().generate(messages,**params)
        if 'candidate_cards' in prompt:
            generated=super().generate(messages,**params); raw=json.loads(generated.text)
            if data['scope']!='book' or self.profile=='preflight_process':
                material=data['materials'][0]; ident=material['source']['id']
                for candidate in raw['candidate_cards']:
                    if self.profile=='promise_process':
                        candidate['members'].append({'key':'secret','kind':'promise','body':{
                            'title':'旧印来历','setup':'封条上出现旧印','payoff':'识破替换'}})
                    artifact=output(self.profile)
                    if self.profile=='preflight_process':
                        artifact['checks']=[{'kind':'character_creation' if row['kind']=='character' else 'world_creation',
                            'target':row['key'],'artifact':row['body']} for row in candidate['members']
                            if row['kind'] in {'character','world'}]
                        artifact['checks'] += [{'kind':'opening','target':row['key'],'artifact':row['body']}
                            for row in candidate['members'] if row['kind']=='scene']
                    artifact['source_scope']={f['id']:{'disposition':'required','reason':'核对当前触发阶段的完整产物和正文'}
                        for f in material['review']['contract']['obligations']}
                    candidate['process_bindings']={ident:artifact}
            generated.text=json.dumps(raw,ensure_ascii=False); return generated
        self.calls.append(messages)
        if 'material_scope_review' in data:
            contract=data['material_scope_review']; spans=[{**row['ref'],'start':0,'end':len(row['text']),
                'quote':row['text']} for row in contract['drafts']]
            checks=[self.check(check,[span for span in spans if any(row['ref']['id']==span['id']
                    and row['chapter_index'] in check['binding']['review_scope']['chapters'] for row in contract['drafts'])],
                    status='unverified' if self.fail_scope else 'pass') for check in contract['checks']]
            raw={'recommendation':'pass','notes':'独立核对阶段产物与整章实际正文','material_checks':checks}
        elif 'material_review' in data:
            contract=data['material_review']; text=data['draft']['text']
            spans=[{**contract['draft'],'start':0,'end':len(text),'quote':text}]
            raw={'recommendation':'pass','notes':'逐项核对当前正文','core_changes':[],
                 'material_checks':[self.check(check,spans) for check in contract['checks']]}
        elif '{"recommendation"' in prompt:
            raw={'recommendation':'pass','notes':'核对场景与事实','core_changes':[]}
        elif '{"operations"' in prompt:
            raw={'operations':[{**transition,'op':'set','claim':'fact','story_order':data['story_order'],
                'disclosure_order':data['disclosure_order'],'evidence':[data['evidence_format']]}
                for item in data['context'].get('material_hypotheses',[]) for transition in item['transitions']]}
        elif '{"findings"' in prompt:
            raw={'findings':[]}
        else:
            return GenResult('[FAKE] 入井已过一小时，沈砚迎着秋风借灯查看封条，认出了印记的轮廓。',
                             'complete',{},'isolated-procedure-test',{})
        return GenResult(json.dumps(raw,ensure_ascii=False),'complete',{},'isolated-procedure-test',{})

    @staticmethod
    def check(check,spans,status='pass'):
        row={'id':check['id'],'status':status,'reason':'阶段对象与条件相符，操作和结果在本稿有可定位依据','evidence':spans,
             'source_checks':[{'id':field['id'],'status':status,'reason':'对照原始字段和当前触发阶段的实际稿件',
                               'evidence':spans} for field in check.get('source_contract',{}).get('obligations',[])]}
        if 'source_contract' not in check:row.pop('source_checks')
        if 'layer_contract' in check:
            row['layer_check']={'status':status,'reason':'原义与当前阶段效果相符','evidence':spans}
        return row


@pytest.mark.parametrize('profile',list(KEYS))
def test_each_procedure_reaches_real_scope_review_acceptance_and_restart(tmp_path,monkeypatch,profile):
    key=KEYS[profile]
    pin=pins_for(tmp_path,monkeypatch,f'### {key}\n【定义】必须核对阶段输入和具体执行产物。\n【指令】必须独立核对正文和阶段记录。\n',[key])[0]
    model=StageModel(profile); path=tmp_path/'story'
    with Store(path,create=True,test_mode=True) as store:
        store.init_project('阶段流程'); store.add_brief('在秋夜调查封条'); adopt_story(store,baseline(),{})
        job=start_job(store,JobRequest('design',materials=[pin],budget=Budget(32,90000,4000))).id
        assert resume_job(store,job,model,config(store)).step=='plan:book:confirm'
        detail=resume_job(store,job,model,config(store),choose)
        assert detail.step=='plan:chapter:confirm',detail.reason
        done=resume_job(store,job,model,config(store),choose)
        assert done.status=='DONE',done.reason
        scene=done.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        writing=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(12,90000,4000))).id
        result=resume_job(store,writing,model,config(store),author())
        assert result.status=='DONE',result.reason
        assert any('material_scope_review' in json.loads(call[-1]['content']) for call in model.calls)
    with Store(path,test_mode=True) as store:
        assert len(store.list('accepted'))==1
        head=current_head(store)
        facts=replay(baseline_for(store,'main'),selected_operations(store,revision_state(store,head)))
        if profile=='timeline_process':
            assert any(f.predicate=='timeline_span' and f.value['end']==1 for f in facts)
        if profile=='promise_process':
            assert any(f.predicate=='promise_stage' and f.value=='planted' for f in facts)


def test_missing_procedural_effect_review_blocks_the_acceptance_transaction(tmp_path,monkeypatch):
    profile='timeline_process'; key=KEYS[profile]
    pin=pins_for(tmp_path,monkeypatch,f'### {key}\n【定义】必须核对时间锚点和实际结果。\n【指令】必须独立核对正文时间。\n',[key])[0]
    model=StageModel(profile,fail_scope=True)
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('阶段拦截'); store.add_brief('调查封条'); adopt_story(store,baseline(),{})
        job=start_job(store,JobRequest('design',materials=[pin],budget=Budget(32,90000,4000))).id
        resume_job(store,job,model,config(store)); resume_job(store,job,model,config(store),choose)
        done=resume_job(store,job,model,config(store),choose)
        scene=done.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        job=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(12,90000,4000,0))).id
        result=resume_job(store,job,model,config(store),author())
        assert result.status=='BLOCKED' and 'MATERIAL_SCOPE_REVIEW' in result.reason
        assert not store.list('accepted')


@pytest.mark.parametrize('correct_previous',[False,True])
def test_cross_chapter_pov_switch_is_checked_against_the_real_previous_scene(tmp_path,monkeypatch,correct_previous):
    profile='pov_process'; key=KEYS[profile]
    pin=pins_for(tmp_path,monkeypatch,f'### {key}\n【定义】每次切换必须核对前后视角。\n【指令】必须明确新场实际观察者。\n',[key])[0]
    model=StageModel(profile)
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('跨章视角'); store.add_brief('调查封条'); adopt_story(store,baseline(),{})
        job=start_job(store,JobRequest('design',materials=[pin],budget=Budget(32,90000,4000))).id
        resume_job(store,job,model,config(store)); resume_job(store,job,model,config(store),choose)
        first=resume_job(store,job,model,config(store),choose)
        scene=first.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        writing=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(12,90000,4000))).id
        assert resume_job(store,writing,model,config(store),author()).status=='DONE'
        from nw.cards import read_card
        from nw.story_models import CardRef
        previous_pov=read_card(store,CardRef(**first.outputs['application']['chapters'][0]['scenes'][0]['scene_ref']))['body']['pov']
        class Later(StageModel):
            def generate(self,messages,**params):
                output=super().generate(messages,**params)
                if 'candidate_cards' in messages[0]['content']:
                    raw=json.loads(output.text)
                    for candidate in raw['candidate_cards']:
                        candidate['chapters'][0]['index']=2
                        candidate['chapters'][0]['scenes'][0]['story_order']=2
                        if correct_previous and pin['id'] in candidate['process_bindings']:
                            candidate['process_bindings'][pin['id']]['switches'][0]['from_pov']=previous_pov
                    output.text=json.dumps(raw,ensure_ascii=False)
                elif correct_previous and 'material_scope_review' in json.loads(messages[-1]['content']):
                    contract=json.loads(messages[-1]['content'])['material_scope_review']
                    spans=[{**row['ref'],'start':0,'end':len(row['text']),'quote':row['text']} for row in contract['drafts']]
                    assert {row['chapter_index'] for row in contract['drafts']}=={1,2}
                    raw=json.loads(output.text)
                    for check in raw['material_checks']:
                        check['evidence']=spans
                        for field in check.get('source_checks',[]):
                            field['evidence']=spans
                    output.text=json.dumps(raw,ensure_ascii=False)
                return output
        later=Later(profile)
        from nw.story_state import fork_story
        fork_story(store,current_head(store),'pov-candidate')
        job=start_job(store,JobRequest('design',branch_id='pov-candidate',parent_id=first.outputs['proposal_id'],budget=Budget(32,90000,4000))).id
        waiting=resume_job(store,job,later,config(store)); assert waiting.step=='plan:chapter:confirm',waiting.reason
        second=resume_job(store,job,later,config(store),choose)
        assert second.status=='DONE',second.reason
        scene=second.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        writing=start_job(store,JobRequest('write',branch_id='pov-candidate',scene_ids=[scene],budget=Budget(12,90000,4000,0))).id
        result=resume_job(store,writing,later,config(store),author())
        if correct_previous:
            assert result.status=='DONE',result.reason
        else:
            assert result.status=='BLOCKED' and 'MATERIAL_SCOPE_REVIEW' in result.reason
        assert len(store.list('accepted'))==1
