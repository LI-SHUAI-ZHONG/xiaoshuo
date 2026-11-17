import json

import pytest

from nw.call_budget import create_budget,read_budget
from nw.llm.base import GenResult
from nw.materials.work_session import legacy_study_plan as drive_plan
from nw.planning import prepare_plan_task
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_stage_integration import pins_for
from test_novel_flow import Model,config
from fake_material_work import study_output


class Studier(Model):
    def __init__(self,source_id,*,invalid=False):
        super().__init__();self.source_id=source_id;self.invalid=invalid

    def generate(self,messages,**params):
        self.calls.append(messages);payload=json.loads(messages[-1]['content'])
        if payload['round']==0:
            result={'status':'retrieve','tasks':[],'understanding':[],'work_plan':[],
                    'requests':[{'action':'search','query':'动作'},{'action':'read','id':self.source_id}]}
        else:
            result=study_output(payload)
            if self.invalid:result['understanding'][0]['quotes']=['凭空发明的资料原文，不可以被接受']
        return GenResult(json.dumps(result,ensure_ascii=False),'complete',{},'test',{'isolated_test':True})


def test_real_search_read_rounds_precede_design_and_reopen_without_duplicate_calls(tmp_path,monkeypatch):
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_动作\n【定义】动作必须有目标、阻碍、应对和实际后果。\n',['1.1_动作'])[0]
    path=tmp_path/'story';provider=Studier(pin['id'])
    with Store(path,create=True,test_mode=True) as store:
        store.init_project('研读');store.add_brief('动作调查');adopt_story(store,baseline(),{})
        budget=create_budget(store,'driver',Budget(6,90000,5000))
        request,package=prepare_plan_task(store,1,'book',provider,config(store),budget,'fixed-plan')
        driven,frozen=drive_plan(store,request,package,provider,config(store))
        assert len(provider.calls)==2 and frozen['material_work']['result']['status']=='ready'
        assert frozen['material_work']['result']['understanding'][0]['source_id']==pin['id']
        assert 'material_work' in json.loads(driven.payload['messages'][-1]['content'])
        assert not store.list('draft') and not store.list('accepted')
        assert read_budget(store,budget).used_calls==2
    with Store(path,test_mode=True) as store:
        request,package=prepare_plan_task(store,1,'book',provider,config(store),'driver','fixed-plan')
        again,_=drive_plan(store,request,package,provider,config(store))
        assert again==driven and len(provider.calls)==2


@pytest.mark.parametrize('invalid,calls',[(True,6),(False,1)])
def test_false_understanding_or_budget_stop_cannot_reach_story_generation(tmp_path,monkeypatch,invalid,calls):
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_动作\n【定义】动作必须有目标、阻碍、应对和实际后果。\n',['1.1_动作'])[0]
    with Store(tmp_path/'blocked',create=True,test_mode=True) as store:
        store.init_project('停止');store.add_brief('动作调查');adopt_story(store,baseline(),{})
        budget=create_budget(store,'driver',Budget(calls,90000,5000));provider=Studier(pin['id'],invalid=invalid)
        request,package=prepare_plan_task(store,1,'book',provider,config(store),budget,'blocked-plan')
        with pytest.raises(ValueError,match='MATERIAL_WORK'):
            drive_plan(store,request,package,provider,config(store))
        assert not store.list('draft')
        assert store.connection.execute("SELECT count(*) FROM task_calls WHERE kind='plan'").fetchone()[0]==0
