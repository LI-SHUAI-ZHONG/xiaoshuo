import json

import pytest

from nw.llm.base import GenResult
from nw.novel_flow import JobRequest,start_job,resume_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_adjudication import AdjudicatedModel
from test_material_stage_integration import pins_for
from test_material_workflow import choose
from test_novel_flow import config,author
from fake_material_work import study_output,apply_work


class Worker(AdjudicatedModel):
    def __init__(self,*,missing=False,failed=False):
        super().__init__();self.missing=missing;self.failed=failed

    def generate(self,messages,**params):
        payload=json.loads(messages[-1]['content']);prompt=messages[0]['content']
        if '[MATERIAL_STEP]' in prompt:
            result=super().generate(messages,**params)
            if self.missing and payload['stage']=='character_design':
                output=json.loads(result.text);output['products'].pop('_uses')
                result.text=json.dumps(output,ensure_ascii=False)
            return result
        if '[MATERIAL_WORK]' in prompt:
            self.calls.append(messages)
            return GenResult(json.dumps(study_output(payload),ensure_ascii=False),'complete',{},'test',{})
        result=super().generate(messages,**params)
        if 'candidate_cards' in prompt and payload.get('material_work') and not self.missing:
            output=json.loads(result.text)
            output['candidate_cards']=[apply_work(row,payload['material_work']) for row in output['candidate_cards']]
            result.text=json.dumps(output,ensure_ascii=False)
        elif 'candidate_cards' in prompt and self.missing:
            output=json.loads(result.text)
            for row in output['candidate_cards']:row.pop('material_work',None)
            result.text=json.dumps(output,ensure_ascii=False)
        if '{"recommendation"' in prompt and self.failed:
            output=json.loads(result.text)
            for row in output['material_checks']:
                if row['id'].startswith('work:'):row['status']='failed';row['reason']='实际正文没有方法要求的应对过程'
            result.text=json.dumps(output,ensure_ascii=False)
        return result


def setup(store):
    store.init_project('资料干活');store.add_brief('调查封条');adopt_story(store,baseline(),{})


def design(store,provider,pin):
    job=start_job(store,JobRequest('design',materials=[pin],budget=Budget(32,90000,5000))).id
    assert resume_job(store,job,provider,config(store)).step=='plan:book:confirm'
    assert resume_job(store,job,provider,config(store),choose).step=='plan:chapter:confirm'
    result=resume_job(store,job,provider,config(store),choose)
    assert result.status=='DONE',result.reason
    return result.outputs['application']['chapters'][0]['scenes'][0]['scene_id']


def test_normal_workflow_saves_ordered_products_and_checks_prose_after_restart(tmp_path,monkeypatch):
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_行动\n【定义】行动必须由目标推动，并承担实际后果。\n',['1.1_行动'])[0]
    path=tmp_path/'story';provider=Worker()
    with Store(path,create=True,test_mode=True) as store:
        setup(store);scene=design(store,provider,pin)
        kinds=[row['kind'] for row in store.connection.execute('SELECT kind FROM task_calls ORDER BY rowid')]
        assert kinds==['material_work']*7+['plan']+['material_work']*14+['plan']
        application=json.loads(store.connection.execute('SELECT mapping_json FROM plan_applications ORDER BY rowid DESC LIMIT 1').fetchone()[0])
        character_stage=next(row for row in application['material_design']['work_session']['stages']
                             if row['stage']=='character_design')
        assert character_stage['products']['members']
    with Store(path,test_mode=True) as store:
        from nw.context.story import build_story_context,scene_scope
        package=build_story_context(store,scene,scene_scope(store,scene),90000).package
        assert any('work:' in str(item) for item in package['items'])
        job=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(10,90000,5000))).id
        result=resume_job(store,job,provider,config(store));assert result.step=='batch:confirm',result.reason
        result=resume_job(store,job,provider,config(store),author());assert result.status=='DONE',result.reason


def test_design_without_method_artifact_is_blocked_even_if_old_bindings_pass(tmp_path,monkeypatch):
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_行动\n【定义】行动必须由目标推动，并承担实际后果。\n',['1.1_行动'])[0]
    with Store(tmp_path/'missing',create=True,test_mode=True) as store:
        setup(store);provider=Worker(missing=True)
        job=start_job(store,JobRequest('design',materials=[pin],budget=Budget(32,90000,5000))).id
        result=resume_job(store,job,provider,config(store))
        assert result.status=='BLOCKED' and 'MATERIAL_WORK' in result.reason
        assert not store.list('scene')


@pytest.mark.parametrize('tamper',['edit','remove'])
def test_edited_stored_method_work_is_rejected_on_reopen(tmp_path,monkeypatch,tamper):
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_行动\n【定义】行动必须由目标推动，并承担实际后果。\n',['1.1_行动'])[0]
    with Store(tmp_path/'tamper',create=True,test_mode=True) as store:
        setup(store);scene=design(store,Worker(),pin)
        row=store.connection.execute('SELECT proposal_id,mapping_json FROM plan_applications ORDER BY rowid DESC LIMIT 1').fetchone()
        value=json.loads(row['mapping_json'])
        if tamper=='edit':
            first_stage=next(item for item in value['material_design']['work_application']['stage_uses']
                             if item['stage']=='type_selection')
            first_stage['sha256']='a'*64
        else:
            for key in ('work_session','work_application','work_context'):value['material_design'].pop(key)
        with store.connection:store.connection.execute('UPDATE plan_applications SET mapping_json=? WHERE proposal_id=?',(json.dumps(value,ensure_ascii=False),row['proposal_id']))
        from nw.materials.evidence import scene_materials
        with pytest.raises(ValueError,match='MATERIAL_WORK'):scene_materials(store,scene)


@pytest.mark.parametrize('outcome',['invalid','unknown'])
def test_explicit_retry_reopens_failed_study_with_original_frozen_input(tmp_path,monkeypatch,outcome):
    from nw.call_budget import finish_reservation
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_行动\n【定义】行动必须由目标推动，并承担实际后果。\n',['1.1_行动'])[0]
    class Flaky(Worker):
        def __init__(self):super().__init__();self.failed_once=False
        def generate(self,messages,**params):
            if '[MATERIAL_STEP]' in messages[0]['content'] and not self.failed_once:
                self.failed_once=True;self.calls.append(messages)
                return GenResult('not JSON' if outcome=='invalid' else '',
                    'complete' if outcome=='invalid' else 'error',{},None,{} if outcome=='invalid' else {'error_type':'TimeoutError'})
            return super().generate(messages,**params)
    with Store(tmp_path/'retry',create=True,test_mode=True) as store:
        setup(store);provider=Flaky();job=start_job(store,JobRequest('design',materials=[pin],budget=Budget(32,90000,5000))).id
        first=resume_job(store,job,provider,config(store));assert first.status=='BLOCKED'
        if outcome=='unknown':
            hold=store.connection.execute("SELECT id FROM call_reservations WHERE call_kind='task'").fetchone()[0]
            finish_reservation(store,hold,{},'FINISHED')
        second=resume_job(store,job,provider,config(store),retry_failed=True)
        assert second.step=='plan:book:confirm',second.reason
        attempts=store.connection.execute("SELECT attempt,manifest_id FROM task_calls WHERE kind='material_work' ORDER BY rowid").fetchall()
        assert [row['attempt'] for row in attempts]==[1,2,1,1,1,1,1,1]
        assert attempts[0]['manifest_id']==attempts[1]['manifest_id']


def test_default_design_cannot_generate_a_story_without_source_catalog(tmp_path):
    from dataclasses import replace
    from nw.planning import propose_plan
    with Store(tmp_path/'no-sources',create=True,test_mode=True) as store:
        setup(store);provider=Worker();settings=replace(config(store),source_driven=True)
        with pytest.raises(ValueError,match='MATERIAL_CATALOG_REQUIRED'):
            propose_plan(store,1,'book',provider,settings,Budget(4,90000,5000))
        assert not provider.calls and not store.connection.execute('SELECT * FROM task_calls').fetchall()
