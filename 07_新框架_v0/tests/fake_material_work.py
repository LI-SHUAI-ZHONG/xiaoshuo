"""Explicit fake responses for isolated workflow tests; never used by production."""
from copy import deepcopy


def study_output(payload):
    sources=[row for row in payload['sources'] if row['use_mode']=='project_method']
    source=sources[0];quote=source['original_text']
    required=payload['required_functions']
    tasks=[{'id':'task'+str(i),'function':function,'role':'design','required':i==0,
            'reason':'[FAKE] 隔离测试只验证当前方法的调用、保存与执行路径','deliverable':'[FAKE] 可核验的具体设计产物'}
           for i,function in enumerate(required)]
    # Explicit demand cues stay required in tests just as in the real contract.
    cues={'动作':'action_design','伏笔':'foreshadowing','读者情绪':'reader_experience','情绪描写':'emotion_design'}
    for cue,function in cues.items():
        if cue in payload['demand']:
            task=next((t for t in tasks if t['function']==function),None)
            if task:task['required']=True
            else:tasks.append({'id':'extra'+str(len(tasks)),'function':function,'role':'design','required':True,
                               'reason':'[FAKE] 明确需求的测试任务','deliverable':'[FAKE] 对应原义的测试产物'})
    return {'status':'ready','tasks':tasks,'requests':[],
            'understanding':[{'source_id':source['source']['id'],'quotes':[quote],
                **{k:'[FAKE] 根据该孤立夹具的原义产生具体测试操作和核验产物'
                   for k in ('meaning','operation','inputs','outputs','limits','check')}}],
            'work_plan':[{'task_id':t['id'],'source_ids':[source['source']['id']],
                          'steps':['[FAKE] 读取方法原义并具体化到测试方案'],
                          'output':'[FAKE] 实际字段与可见表现','check':'[FAKE] 核对真实测试产物'} for t in tasks if t['required']]}


def apply_work(candidate,session):
    candidate=deepcopy(candidate);applications=[]
    scenes=[row for row in candidate['members'] if row['kind']=='scene']
    for plan in session['result']['work_plan']:
        target=scenes[0] if scenes else {'key':'direction','body':candidate['body']}
        applications.append({'task_id':plan['task_id'],'source_ids':plan['source_ids'],
            'operation':'[FAKE] 把资料原义落实到当前真实选择及其可见行动',
            'artifact':{'designed_choice':target['body']['choice'],'test_only':'[FAKE] 此对象不是文学效果证明',
                        'steps':[{'input':'[FAKE] 本场以调查封条为目标，需要确定可见对象及限制',
                                  'operation':'[FAKE] 先借灯观察封条边缘，再决定接触与应对方式',
                                  'result':'[FAKE] 将调查选择落为先观察后采取行动的实际方案',
                                  'placement':0,'design_value':target['body']['choice']}]},
            'placements':[{'target':target['key'],'field':'choice','value':target['body']['choice']}],
            'scene_guidance':[{'scene':s['key'],'observable':'[FAKE] 沈砚借灯观察封条边角后才伸手检查',
                               'check':'[FAKE] 核对先观察再接触的实际动作及影响'} for s in scenes]})
    candidate['material_work']={'session_id':session['id'],'applications':applications}
    return candidate
