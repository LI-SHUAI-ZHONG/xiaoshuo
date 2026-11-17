import json

import pytest

from nw.materials.work_catalog import SourceDesk, method_role
from test_material_stage_integration import pins_for


def test_structured_template_is_an_instantiable_method_without_becoming_fact():
    original={'rule_id':'TDR_TEMPLATE_003','status':'template','evidence_type':'template',
              'preconditions':['实体存在','状态变化有事件依据'],
              'selection_constraints':['必须经过外部行动选择','需要连续性验证'],
              'not_guaranteed':['状态变化需要事件证据']}
    assert method_role(original)=='project_method'
    assert original['status']=='template'


def test_parameter_adaptation_is_usable_while_invalid_score_remains_invalid():
    original={'parameters':{'sentence_length':'medium'},'preferred_expressions':[],
              'confidence':999,'not_guaranteed':['不强制人物做某种动作']}
    assert method_role(original)=='project_method'
    assert original['confidence']==999
    assert method_role({'items':[],'count':0,'status':'active'})=='navigation_only'
    assert method_role({'type_id':'GENRE_UNKNOWN','canonical_name':'未知'})=='navigation_only'
    assert method_role('检查1：人物设定一致')=='project_method'
    assert method_role('伏笔')=='navigation_only'


def test_function_search_is_paged_and_read_keeps_exact_original_and_application_layer(tmp_path,monkeypatch):
    text=''
    keys=[]
    for i in range(1,8):
        key=f'1.{i}_动作步骤{i}';keys.append(key)
        text+=f'### {key}\n【定义】动作必须给出目标、阻碍、应对及连续的结果。\n【指令】必须写出动作过程。\n'
    pins=pins_for(tmp_path,monkeypatch,text,keys)
    desk=SourceDesk(tmp_path)
    first=desk.search('动作',limit=3)
    second=desk.search('动作',cursor=first['next_cursor'],limit=3)
    third=desk.search('动作',cursor=second['next_cursor'],limit=3)
    assert first['total']==7 and len(first['items']+second['items']+third['items'])==7
    assert third['next_cursor'] is None
    source=desk.read(pins[0]['id'])
    assert source['source']['sha256']==pins[0]['sha256']
    assert '必须写出动作过程' in source['original_text']
    assert source['use_mode']=='project_method'
    assert source['authority']=='project_candidate_only_not_source_repair_or_story_fact'
    assert '动作' in json.dumps(desk.directory(),ensure_ascii=False)


def test_blocked_source_is_still_discoverable_for_method_reading(tmp_path,monkeypatch):
    text='### 64.1_读者情绪\n【定义】读者情绪由信息顺序和人物遭遇共同形成。\n【指令】将读者设置为一个恐惧的人物。\n'
    pin=pins_for(tmp_path,monkeypatch,text,['64.1_读者情绪'])[0]
    desk=SourceDesk(tmp_path)
    found=desk.search('读者情绪')['items']
    assert any(row['id']==pin['id'] for row in found)
    result=desk.read(pin['id'])
    assert '信息顺序' in result['original_text']
    assert result['source_state'] in {'blocked','design_ready'}
    assert result['source_issues'] is not None


def test_source_payload_tampering_is_rejected(tmp_path,monkeypatch):
    import sqlite3
    pin=pins_for(tmp_path,monkeypatch,'### 1.1_动作\n【定义】动作必须有具体目标。\n',['1.1_动作'])[0]
    desk=SourceDesk(tmp_path)
    with sqlite3.connect(tmp_path/'materials/catalog.db') as db:
        db.execute('UPDATE fragments SET payload=? WHERE id=?',(b'bad',pin['id']))
    with pytest.raises(ValueError):desk.read(pin['id'])


def test_raw_indexed_method_can_be_studied_before_fact_adjudication_exists(tmp_path,monkeypatch):
    from test_material_workflow import anchor_pin
    pin=anchor_pin(tmp_path,monkeypatch)
    desk=SourceDesk(tmp_path)
    source=desk.read(pin['id'])
    assert source['source_state']=='not_adjudicated'
    assert source['use_mode']=='project_method'
    assert source['authority']=='project_candidate_only_not_source_repair_or_story_fact'


def test_empty_structural_labels_are_not_method_meaning():
    assert method_role('### 1.1_动作\n【定义】\n【指令】\n【判定标准】\n【适用条件】\n')=='navigation_only'
    assert method_role('### 1.1_动作\n【定义】无\n【指令】待补\n【判定标准】未提供\n')=='navigation_only'
    assert method_role({'canonical_name':'系统流','definition':'系统流'})=='navigation_only'
    assert method_role({'canonical_name':'系统流','definition':'系统流','parameters':{'reward':'staged'}})=='project_method'


def test_source_contract_remains_discoverable_when_position_is_owned_by_a_container(tmp_path,monkeypatch):
    import sqlite3
    pins=pins_for(tmp_path,monkeypatch,'### 1.1_动作\n【定义】动作必须包含具体目标、阻碍与后果。\n'
                  '### 1.2_目标\n【定义】人物需要有明确的目标和选择。\n',['1.1_动作','1.2_目标'])
    with sqlite3.connect(tmp_path/'materials/adjudication.db') as db:
        db.execute('UPDATE positions SET owner_id=? WHERE id=?',(pins[1]['id'],pins[0]['id']))
    desk=SourceDesk(tmp_path)
    assert pins[0]['id'] in desk.by_id
    assert desk.read(pins[0]['id'])['source']['sha256']==pins[0]['sha256']
