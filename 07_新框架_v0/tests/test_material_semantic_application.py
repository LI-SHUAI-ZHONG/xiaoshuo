from copy import deepcopy
from pathlib import Path
import json

import pytest

from nw.materials.phase_contract import validate_phase
from nw.task_models import content_sha256
from test_material_phase_projection import chain


def source(key):
    data=json.loads((Path(__file__).parents[1]/'fixtures/material_semantics/source_samples.json').read_text(encoding='utf-8'))
    return deepcopy(next(row for row in data['samples'] if row['source']['key']==key))


def at(stage):
    records=chain()['stages'];index=next(i for i,r in enumerate(records) if r['stage']==stage)
    return {r['stage']:r for r in records[:index]},deepcopy(records[index]['products'])


def used(value,item,ref):
    value['_uses']=[{'source_id':item['source']['id'],'operation':'[FAKE] 按来源原义安排当前项目实际设计及检验',
                     'output_refs':[ref]}]


def test_reader_wave_cannot_be_an_arbitrary_nonempty_string():
    item=source('板块64 读者情感#读者情绪波形设计')
    products,value=at('plot_design');value['reader_plan']=['全部场景情绪保持同一水平']
    used(value,item,'reader_plan')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[item],{'scope':'chapter'})


def test_real_foreshadow_subitem_cannot_omit_its_promise_plan():
    item=source('板块45 伏笔与反转#伏笔埋设')
    products,value=at('plot_design');value['promise_plan']=[]
    used(value,item,'direction:0')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[item],{'scope':'chapter'})


def test_native_dynamic_edge_cannot_apply_without_its_adopted_static_relation():
    item=source('C00001')
    products,value=at('state_transition');used(value,item,'scene:scene')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'state_transition','products':value},'state_transition',products,[item],{'scope':'chapter'})


def test_anchor_needs_an_actual_selected_action_and_trigger_basis():
    item=source('A1.1')
    products,value=at('anchor_design');value['beats'][0]['action']='全速冲刺'
    for field in ('action_ref','step_index','timing','trigger_basis'):value['beats'][0].pop(field,None)
    used(value,item,'scene:scene')
    with pytest.raises(ValueError,match='MATERIAL_'):
        validate_phase({'stage':'anchor_design','products':value},'anchor_design',products,[item],{'scope':'chapter'})
    # Historical v3 output remains inspectable under its own recorded contract.
    validate_phase({'stage':'anchor_design','products':value},'anchor_design',products,[item],
                   {'scope':'chapter','legacy_replay':True})


def test_real_reader_and_foreshadow_methods_accept_actual_plans_and_keep_unknown_future():
    products,value=at('plot_design')
    for key,ref in (('板块64 读者情感#读者情绪波形设计','reader_plan'),
                    ('板块45 伏笔与反转#伏笔埋设','promise_plan')):
        item=source(key);used(value,item,ref)
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[item],{'scope':'chapter'})
    assert value['promise_plan'][0]['payoff_chapter'] is None


def test_static_relationship_waits_for_real_plot_endpoint_then_dynamic_uses_it():
    from nw.materials.semantic_products import validate_dynamic_dependencies
    from nw.materials.template_candidates import validate_propagations
    static=source('1.1_主角 / 130_核心悬念 / 绑定');dynamic=source('C00001')
    products,value=at('plot_design');used(value,static,'relation:core')
    promise=next(r['key'] for r in value['members'] if r['kind']=='promise')
    value['static_bindings']=[{'id':'core','source_id':static['source']['id'],
        'source':'yan','target':promise,'relation':'绑定','condition':'[FAKE] 人物采用调查旧印的主线悬念'}]
    validate_phase({'stage':'plot_design','products':value},'plot_design',products,[static],{'scope':'chapter'})
    later,propagation=at('state_propagation')
    later['plot_design']['products']=value;later['plot_design']['sha256']=content_sha256(value)
    row=propagation['candidates'][0];row['source_ids']=[dynamic['source']['id']];row['target_entity']=promise
    used(propagation,dynamic,'propagation:'+row['id'])
    context={'scope':'chapter','method_sources':[static,dynamic]}
    validate_dynamic_dependencies('state_propagation',propagation,later,[dynamic],context)
    validate_propagations(propagation,later,[dynamic],context)
    value['static_bindings'][0]['target']='not-created'
    with pytest.raises(ValueError,match='endpoints'):
        validate_phase({'stage':'plot_design','products':value},'plot_design',products,[static],context)
