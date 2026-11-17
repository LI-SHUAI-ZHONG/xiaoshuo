"""Selection and conversion consume real design records rather than prose events."""
from copy import deepcopy

import pytest

from nw.materials.binding import validate_bindings


def scenario(profile):
    common={'request':{'disposition':'required'},'source':{'id':'rule','key':'行动目标','fragment_id':'block'},
            'profile':'character','review':{}}
    process={'request':{'disposition':'required'},'source':{'id':'process','key':'选材或转化'},
             'profile':profile,'review':{}}
    candidate={'material_bindings':{'scene':{'rule':{'function':'调查行动', 'parameter':'要看清旧印',
        'observable':'举灯检查封条留下烧伤', 'check':'先有目标，再有行动与后果'}}}}
    return candidate,{'scene':{'kind':'scene','body':{}}},[common,process]


@pytest.mark.parametrize('profile',['material_selection','material_conversion'])
def test_process_rule_cannot_pass_without_its_stage_artifact(profile):
    candidate,members,materials=scenario(profile)
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_bindings(candidate,'chapter',members,{},materials)


def test_selection_points_to_actual_source_block_and_explains_each_choice():
    candidate,members,materials=scenario('material_selection')
    candidate['process_bindings']={'process':{'task_function':'设计一次有目标、有后果的调查行动',
        'selections':[{'id':'rule','block_id':'block','reason':'行动目标支撑调查的因果推进'}], 'exclusions':[]}}
    validate_bindings(candidate,'chapter',members,{},materials)
    candidate['process_bindings']['process']['selections'][0]['id']='invented'
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_bindings(candidate,'chapter',members,{},materials)


def test_conversion_requires_the_actual_approved_parameter_and_expression():
    candidate,members,materials=scenario('material_conversion')
    binding=candidate['material_bindings']['scene']['rule']
    candidate['process_bindings']={'process':{'mappings':[
        {'scene':'scene','id':'rule',**{k:binding[k] for k in ('parameter','observable','check')}}]}}
    validate_bindings(candidate,'chapter',members,{},materials)
    candidate['process_bindings']['process']['mappings'][0]['observable']='只重复资料名称'
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_bindings(candidate,'chapter',members,{},materials)


def test_conversion_cannot_hide_a_used_rule_by_omitting_its_mapping():
    candidate,members,materials=scenario('material_conversion')
    candidate['process_bindings']={'process':{'mappings':[]}}
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_bindings(candidate,'chapter',members,{},materials)


def test_chapter_template_selection_method_is_a_process_not_an_example(tmp_path,monkeypatch):
    from test_material_stage_integration import pins_for
    from nw.materials.binding import resolve_materials
    text=('### 126.3_按章节类型的模板调用\n【定义】重章和轻章需要不同的支撑板块。\n'
          '【指令】重章必须优先选择冲突与剧情推进；轻章选择氛围与人物感知。\n')
    pin=pins_for(tmp_path,monkeypatch,text,['126.3_按章节类型的模板调用'])[0]
    resolved=resolve_materials(tmp_path,[pin])[0]
    assert resolved['profile']=='material_selection'
