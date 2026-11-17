from copy import deepcopy

import pytest

from nw.materials.work_contract import functions_for,validate_study
from nw.materials.work_application import validate_work,work_checks


def studied():
    source={'source':{'id':'method','key':'动作方法','sha256':'a'*64},
            'original_text':'动作需要目标、阻碍、连续应对与实际后果。','use_mode':'project_method'}
    tasks=[{'id':function,'function':function,'role':'design','required':function=='action_design',
            'reason':'本场借检查封条推进调查，其余功能由本次明确范围决定','deliverable':'具体动作与调查后果'}
           for function in functions_for('chapter')]
    output={'status':'ready','tasks':tasks,'requests':[],
            'understanding':[{'source_id':'method','quotes':[source['original_text']],
                'meaning':'行动过程需要有目标和阻碍以及真实后果','operation':'按调查目标安排受阻及调整的动作步骤',
                'inputs':'本场目标及可用物品与行动限制','outputs':'具体动作过程与结果','limits':'不从动作自动推定人物已经成功',
                'check':'比较正文中的动作过程与真实结果'}],
            'work_plan':[{'task_id':'action_design','source_ids':['method'],
                'steps':['确定检查对象与接触前的动作','安排封条限制以及调整步骤'],
                'output':'本场检查动作链与产生的新问题','check':'动作必须实际影响调查的下一步'}]}
    return {'id':'study','scope':'chapter','sources':[source],'result':output}


def candidate():
    return {'body':{'choice':'先借灯看封条再决定是否接触'},'members':[
        {'key':'scene','kind':'scene','body':{'choice':'先借灯看封条再决定是否接触'}}],
        'material_work':{'session_id':'study','applications':[{
            'task_id':'action_design','source_ids':['method'],'operation':'按原方法设计先观察再调整的检查过程',
            'artifact':{'action_chain':['借灯','照见封条裂口','收回手并改用木片'],
                        'steps':[{'input':'调查封条需要先确定眼前可见的阻碍',
                                  'operation':'先借灯照见裂口再收手改用木片检查',
                                  'result':'将检查变为先观察再调整的具体行动过程',
                                  'placement':0,'design_value':'先借灯看封条再决定是否接触'}]},
            'placements':[{'target':'scene','field':'choice','value':'先借灯看封条再决定是否接触'}],
            'scene_guidance':[{'scene':'scene','observable':'借灯看清封条裂口，收手并改用木片检查',
                               'check':'动作应对封条的限制并推进实际调查'}]}]}}


def test_ready_requires_read_original_quotes_and_actual_work_plan():
    session=studied();validate_study(session['result'],session['sources'],'chapter','调查封条的动作')
    for mutate in ('unread','quote','no_plan','skipped_action'):
        result=deepcopy(session['result'])
        if mutate=='unread':result['understanding'][0]['source_id']='unread'
        elif mutate=='quote':result['understanding'][0]['quotes']=['不存在于原文的自造方法定义']
        elif mutate=='no_plan':result['work_plan']=[]
        else:result['tasks'][0]['required']=False;result['work_plan']=[]
        with pytest.raises(ValueError,match='MATERIAL_WORK'):
            validate_study(result,session['sources'],'chapter','调查封条的动作')


def test_method_application_has_actual_placements_and_cannot_just_claim_use():
    session=studied();raw=candidate();validate_work(raw,session)
    for mutate in ('missing','wrong_value','wrong_source','empty_artifact'):
        changed=deepcopy(raw);application=changed['material_work']['applications'][0]
        if mutate=='missing':changed.pop('material_work')
        elif mutate=='wrong_value':application['placements'][0]['value']='模型实际没有这样设计'
        elif mutate=='wrong_source':application['source_ids']=['invented']
        else:application['artifact']={}
        with pytest.raises(ValueError,match='MATERIAL_WORK'):validate_work(changed,session)
    label=deepcopy(raw)
    label['material_work']['applications'][0]['artifact']={'status':'已完成/已使用'}
    with pytest.raises(ValueError,match='MATERIAL_WORK'):validate_work(label,session)


def test_writer_receives_only_current_visible_guidance_but_reviewer_has_original():
    session=studied();raw=candidate()
    raw['material_work']['applications'][0]['artifact']['hidden']='第十章才揭示守井人是幕后主使'
    checks=work_checks(session,raw['material_work'],'scene')
    assert checks[0]['profile']=='method_work'
    assert '动作需要目标' in str(checks[0]['method_sources'])
    visible={k:checks[0]['binding'][k] for k in ('observable','check')}
    assert '第十章' not in str(visible)
