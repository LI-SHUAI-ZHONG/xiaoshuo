"""Real design/store/review/acceptance paths; fake prose is isolated to tests."""
from hashlib import sha256
import json

import pytest

from nw.materials.adjudication import build_adjudications
from nw.materials import library_adjudication
from nw.materials.catalog import build_catalog,list_catalog
from nw.materials.route_catalog import route
from nw.materials.unit_catalog import index_units
from nw.novel_flow import JobRequest,start_job,resume_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_adjudication import AdjudicatedModel
from test_material_catalog import _manifest
from test_material_scope import ScopeModel,designed_story
from test_material_workflow import choose
from test_novel_flow import author,config


def pins_for(tmp_path,monkeypatch,text,keys):
    data=text.encode()
    monkeypatch.setitem(library_adjudication._PINNED,'library',sha256(data).hexdigest())
    manifest=_manifest(tmp_path/'source',tmp_path,[('library.txt','library',data)])
    build_catalog(tmp_path,tmp_path/'source',manifest); index_units(tmp_path,None); build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    pins=[]
    for key in keys:
        found=list_catalog(tmp_path,None,key)['fragments'][0]
        source=route(tmp_path,found['fragment_id'])['source']
        pins.append({**{k:source[k] for k in ('id','file_sha256','sha256')},
                     'disposition':'required','reason':'核对真实阶段执行'})
    return pins


def test_process_artifacts_are_validated_and_survive_author_approval_and_restart(tmp_path,monkeypatch):
    text=('### 1.1_行动动机\n【定义】人物行动必须有具体目标，选择必须承担行动后果。\n'
          '【指令】在决定前展示目标，决定后兑现代价。\n'
          '### 128.4_板块调用的三层筛选法\n【定义】按任务功能、支撑板块、具体子项筛选资料。\n'
          '【指令】必须登记确切选用来源及未选原因。\n'
          '### 127.5_各板块设计应用对应表\n【定义】把所选资料转换为项目参数和正文表现。\n'
          '【指令】必须把每个参数与具体表现和核验点对应。\n')
    pins=pins_for(tmp_path,monkeypatch,text,['1.1_行动动机','128.4_板块调用的三层筛选法','127.5_各板块设计应用对应表'])
    class ProcessModel(AdjudicatedModel):
        def generate(self,messages,**params):
            output=super().generate(messages,**params)
            data=json.loads(messages[-1]['content'])
            if 'candidate_cards' in messages[0]['content'] and data['scope']!='book':
                raw=json.loads(output.text)
                material=data['materials'][0]
                for candidate in raw['candidate_cards']:
                    candidate['process_bindings']={}
                    binding=candidate['material_bindings']['scene'][material['source']['id']]
                    for process in data['materials'][1:]:
                        value=({'task_function':'把调查目标转成有代价的行动',
                                'selections':[{'id':material['source']['id'],'block_id':material['source']['fragment_id'],
                                               'reason':'行动动机支撑调查的前因后果'}],'exclusions':[]}
                               if process['profile']=='material_selection' else {'mappings':[
                                   {'scene':'scene','id':material['source']['id'],
                                    **{k:binding[k] for k in ('parameter','observable','check')}}]})
                        value['source_scope']={f['id']:{'disposition':'required','reason':'核对本次真实设计产物'}
                                               for f in process['review']['contract']['obligations']}
                        candidate['process_bindings'][process['source']['id']]=value
                output.text=json.dumps(raw,ensure_ascii=False)
            return output
    path=tmp_path/'process_story'; model=ProcessModel()
    with Store(path,create=True,test_mode=True) as store:
        store.init_project('流程记录'); store.add_brief('调查旧印'); adopt_story(store,baseline(),{})
        job=start_job(store,JobRequest('design',materials=pins,budget=Budget(32,90000,4000))).id
        assert resume_job(store,job,model,config(store)).step=='plan:book:confirm'
        result=resume_job(store,job,model,config(store),choose)
        assert result.step=='plan:chapter:confirm',result.reason
        result=resume_job(store,job,model,config(store),choose)
        assert result.status=='DONE',result.reason
    with Store(path,test_mode=True) as store:
        applications=[json.loads(r[0]) for r in store.connection.execute('SELECT mapping_json FROM plan_applications')]
        records=[a['material_design']['process_bindings'] for a in applications if a.get('material_design',{}).get('process_bindings')]
        assert len(records)==1 and set(records[0])=={pins[1]['id'],pins[2]['id']}
        assert records[0][pins[2]['id']]['mappings'][0]['parameter']=='沈砚要查封条'
        from nw.materials.evidence import scene_materials
        application=next(a for a in applications if a.get('material_design',{}).get('process_bindings'))
        scene=application['chapters'][0]['scenes'][0]['scene_id']
        assert scene_materials(store,scene)['bindings']
        for proposal_id,payload in store.connection.execute('SELECT proposal_id,mapping_json FROM plan_applications').fetchall():
            changed=json.loads(payload)
            if changed.get('material_design',{}).get('process_bindings'):
                changed['material_design'].pop('process_bindings')
                with store.connection:
                    store.connection.execute('UPDATE plan_applications SET mapping_json=? WHERE proposal_id=?',
                                             (json.dumps(changed,ensure_ascii=False),proposal_id))
        with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
            scene_materials(store,scene)


@pytest.mark.parametrize('failure',['','omit_layer','unverified_layer'])
def test_complete_scope_also_checks_translation_effects(tmp_path,monkeypatch,failure):
    key='91.1_整章场景检查'
    translation={'canonical_source_id':key,'runtime_calling_layer':[{
        'source_id':key,'binding_id':'TB-scope','semantic_interpretation':{
            'source_semantic_anchor':'每章包含两个目标清楚的场景。',
            'operational_meaning':'让角色承担代价并产生状态变化。'}}]}
    text=('### '+key+'\n【定义】每章包含两个目标清楚的场景。\n'
          '【指令】全章必须从进入调查推进到取得证据。\n'
          '【判定标准】整章有两个场景，各场目标与章末后果相连。\n'
          '【运行层升级】\n```json\n'+json.dumps(translation,ensure_ascii=False)+'\n```\n')
    pin=pins_for(tmp_path,monkeypatch,text,[key])[0]
    class LayerScopeModel(ScopeModel):
        def generate(self,messages,**params):
            output=super().generate(messages,**params)
            data=json.loads(messages[-1]['content']); raw=None
            if 'candidate_cards' in messages[0]['content'] and data['scope']!='book':
                raw=json.loads(output.text)
                for candidate in raw['candidate_cards']:
                    for mappings in candidate['material_bindings'].values():
                        for binding in mappings.values():
                            if 'function' in binding:
                                binding['layer_application']={'trigger':'本章全部计划场景都有完整现行稿',
                                    'operation':'逐场提取行动目标并与章末后果对照',
                                    'result':'两个场景分别推进调查并取得可核查的证据',
                                    'verification':'引用两场的目标行动和取得印记证据的完整句段'}
            elif 'material_scope_review' in data and failure!='omit_layer':
                raw=json.loads(output.text)
                for check in raw['material_checks']:
                    check['layer_check']={'status':'unverified' if failure else 'pass',
                        'reason':'对照完整两场稿件，调查行动因果推进并在章末取得印记证据',
                        'evidence':check['evidence']}
            if raw is not None:
                output.text=json.dumps(raw,ensure_ascii=False)
            return output
    model=LayerScopeModel(); store,scenes=designed_story(tmp_path,pin,model)
    with store:
        job=start_job(store,JobRequest('write',scene_ids=scenes,budget=Budget(16,90000,4000,0))).id
        result=resume_job(store,job,model,config(store),author())
        assert result.status==('BLOCKED' if failure else 'DONE'),result.reason
        assert len(store.list('accepted'))==(0 if failure else 2)
