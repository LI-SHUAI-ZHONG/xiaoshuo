"""Tie studied methods to actual design fields and visible writing work."""
from nw.task_models import _text,canonical
from nw.store import Store
import json
from nw.materials.phase_routes import STAGED_POLICIES

APPLICATION_PROMPT=''' 你必须先执行material_work.result.work_plan中的原义步骤来构造本方案。
每案另含material_work={session_id:输入material_work.id,applications:[...]};
每个适用task一项，严格含task_id、source_ids、operation、artifact、placements、scene_guidance。
operation解释本案怎样执行已读方法；artifact是实际设计结果对象，不能是“已完成/已使用”标签。
artifact必须含steps数组，每一步严格包含input、operation、result（三个不同的具体说明，各至少八个非空白字符）、
placement（placements中的位置整数）、design_value（与该落点的实际value完全一致）。所有落点都要有实际步骤。
可另加动作链、情绪曲线、伏笔网等领域产物。不能只填状态、资料名称或“已使用”。
读者体验给出信息顺序和情绪变化，伏笔给出埋设与回收的关系，动作给出有阻碍和应对的行动链。
placements每项含target(direction或成员key)、field(该body的实际字段名)、value(与该实际值完全一致)，
把资料操作落到真正的方案字段。不能只在旁边登记资料。不得把项目候选当作来源定义或已经发生的事实。
scene_guidance每项含scene(本案真实场景key)、observable(该POV本场可见表现)、check(实际效果判据)；
书级没有场景则为空，细化阶段每项实际方法至少落实一个场景。幕后原因和远期结果不放进可见表现。
后续细化要继承parent_material_work的真实产物并继续按需求调资料，不把书级伏笔和读者体验延后补写。'''


def _require(ok: bool,message: str) -> None:
    if not ok:raise ValueError('MATERIAL_WORK: '+message)


def validate_work(candidate: dict,session: dict | None) -> None:
    if session and session.get('policy') in STAGED_POLICIES:
        from nw.materials.phase_projection import validate_candidate
        validate_candidate(candidate,session);return
    value=candidate.get('material_work')
    if session is None:
        _require(value is None,'unrequested method application');return
    _require(isinstance(value,dict) and set(value)=={'session_id','applications'}
             and value['session_id']==session['id'] and isinstance(value['applications'],list),'missing studied-method application')
    expected={row['task_id']:row for row in session['result']['work_plan']}
    members={row['key']:row for row in candidate.get('members',[])}
    scenes={key for key,row in members.items() if row['kind']=='scene'}
    for row in value['applications']:
        _require(isinstance(row,dict) and set(row)=={'task_id','source_ids','operation','artifact','placements','scene_guidance'}
                 and _text(row['task_id']) and row['task_id'] in expected,'invalid or duplicate method application')
        plan=expected.pop(row['task_id'])
        _require(row['source_ids']==plan['source_ids'] and _text(row['operation'])
                 and isinstance(row['artifact'],dict) and bool(row['artifact'])
                 and len(canonical(row['artifact']))>=12,'method needs its actual project artifact and read sources')
        _require(isinstance(row['placements'],list) and bool(row['placements']),'method must affect an actual design field')
        seen=set()
        for placement in row['placements']:
            _require(isinstance(placement,dict) and set(placement)=={'target','field','value'}
                     and _text(placement['target']) and _text(placement['field']),'invalid actual design placement')
            body=candidate['body'] if placement['target']=='direction' else members.get(placement['target'],{}).get('body',{})
            identity=placement['target'],placement['field']
            _require(identity not in seen and placement['field'] in body
                     and canonical(placement['value'])==canonical(body[placement['field']]),'method placement differs from actual design')
            seen.add(identity)
        steps=row['artifact'].get('steps')
        _require(isinstance(steps,list) and bool(steps),'artifact must contain actual method execution steps')
        covered=set()
        for step in steps:
            _require(isinstance(step,dict) and set(step)=={'input','operation','result','placement','design_value'}
                     and all(_text(step[k]) and len(''.join(step[k].split()))>=8 for k in ('input','operation','result'))
                     and len({step[k].strip() for k in ('input','operation','result')})==3
                     and type(step['placement']) is int and 0<=step['placement']<len(row['placements'])
                     and canonical(step['design_value'])==canonical(row['placements'][step['placement']]['value']),
                     'artifact step must execute the method at an actual matching design placement')
            covered.add(step['placement'])
        _require(covered==set(range(len(row['placements']))),'artifact does not execute every declared design placement')
        _require(isinstance(row['scene_guidance'],list) and (not scenes or bool(row['scene_guidance'])),'method has no current scene work')
        guided=set()
        for guide in row['scene_guidance']:
            _require(isinstance(guide,dict) and set(guide)=={'scene','observable','check'}
                     and _text(guide['scene']) and guide['scene'] in scenes-guided
                     and _text(guide['observable']) and _text(guide['check']),'invalid scene method guidance')
            guided.add(guide['scene'])
    _require(not expected,'selected methods were not actually applied')


def work_checks(session: dict,application: dict,scene: str,ids: dict | None=None) -> list[dict]:
    if session.get('policy') in STAGED_POLICIES:
        from nw.materials.phase_projection import method_checks
        return method_checks(session,scene,ids)
    sources={row['source']['id']:row for row in session['sources']}
    understandings={row['source_id']:row for row in session['result']['understanding']}
    result=[]
    for row in application['applications']:
        for guide in row['scene_guidance']:
            if guide['scene']!=scene:continue
            obligations=[{'id':f'work:{ident}:quote:{index}','text':quote,'source_id':ident}
                         for ident in row['source_ids'] for index,quote in enumerate(understandings[ident]['quotes'])]
            result.append({'id':'work:'+row['task_id'],'profile':'method_work',
                'binding':{'observable':guide['observable'],'check':guide['check'],
                           'source_scope':{o['id']:{'disposition':'required','reason':'按已读原文核对实际方法效果'} for o in obligations}},
                'source_contract':{'obligations':obligations},
                'method_sources':[{'source':sources[i]['source'],'original_quotes':understandings[i]['quotes'],
                                   'meaning':understandings[i]['meaning'],'operation':understandings[i]['operation'],
                                   'limits':understandings[i]['limits']} for i in row['source_ids']],
                'method_artifact':row['artifact'],'method_operation':row['operation'],
                'evidence_required':'依据原义、实际设计及当前完整稿件，判断方法是否真正产生所需效果；只提到动作或情绪不算通过。'})
    return result


def validate_saved_work(store: Store,proposal_id: str,design: dict,root: dict) -> None:
    from nw.materials.work_catalog import SourceDesk
    from nw.tasks import read_input_manifest
    row=store.connection.execute('SELECT manifest_id,result_json FROM task_calls WHERE id=?',(proposal_id,)).fetchone()
    _require(row is not None,'missing original method design task')
    _,frozen=read_input_manifest(store,row['manifest_id'])
    if not frozen.get('material_work'):
        _require(not any(design.get(key) for key in ('work_session','work_application','work_context')),
                 'method work was not in the frozen design');return
    _require(all(isinstance(design.get(key),dict) and bool(design[key]) for key in
                 ('work_session','work_application','work_context')),'required method work was removed')
    _require(canonical(frozen.get('material_work'))==canonical(design['work_session']),'studied sources differ from frozen design')
    original=json.loads(row['result_json']).get('plan_proposal',{})
    chosen=next((item for item in original.get('materialization',[]) if item['root']==root),{})
    expected=chosen.get('material_design',{})
    _require(all(canonical(expected.get(key))==canonical(design.get(key)) for key in
                 ('work_session','work_application','work_context')),'approved method work was edited')
    validate_work(design['work_context'],design['work_session'])
    SourceDesk(store.directory.parent).verify(design['work_session']['sources'])
    if design['work_session'].get('policy') in STAGED_POLICIES:
        from nw.materials.binding_reviews import verify_session_bindings
        verify_session_bindings(design['work_session'],store.directory.parent,test_mode=store.test_mode)
        from nw.materials.governance_runtime import verify_session_governance
        verify_session_governance(design['work_session'],store.directory.parent,adopting=True)
