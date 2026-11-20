"""Selected method designs remain concrete obligations for writing and review."""
from nw.materials.scene_actions import MULTI_ACTION_POLICY, selected_action_ids
from nw.task_models import canonical


def anchor_beat_observable(guide: dict, records: dict, scene: str, ids: dict | None = None) -> str:
    if 'action_ref' not in guide:
        return guide['observable']
    ids = ids or {}
    ref, step = guide['action_ref'], guide['step_index']
    chosen = selected_action_ids(records['scene_design']['products'])[scene]
    action = next(row for row in records['action_design']['products']['candidates'] if row['id'] == ref)
    return canonical({'action_ref': ref, 'action_order': chosen.index(ref) + 1, 'step_index': step,
                      'action_step': action['steps'][step], 'observer': ids.get(guide['observer'], guide['observer']),
                      'object': guide['object'], 'anchor_action': guide['action'], 'timing': guide['timing'],
                      'trigger_basis': guide['trigger_basis'], 'observable': guide['observable']})


def selected_checks(records: dict, scene: str, ids: dict | None = None, context: dict | None = None) -> list[dict]:
    ids=ids or {}
    product=lambda stage:records.get(stage,{}).get('products',{})
    scene_product=product('scene_design')
    body=next((r['body'] for r in scene_product.get('members',[]) if r['key']==scene),{})
    result=[]

    def append(kind: str,row: dict,observable: dict,check: str, *, action_order: int | None = None) -> None:
        for key in ('actor','source_entity','target_entity'):
            if key in observable:observable[key]=ids.get(observable[key],observable[key])
        if 'actors' in observable:observable['actors']=[ids.get(key,key) for key in observable['actors']]
        observable['presentation_boundary']=body.get('allowed_disclosure','仅本场POV可见或可知内容')
        result.append({'id':f'work:selected:{kind}:{scene}:{row["id"]}','profile':'method_work',
            **({'action_order': action_order} if action_order is not None else {}),
            'binding':{'observable':canonical(observable),'check':check},'method_artifact':row,
            'evidence_required':'用本稿中的行动、顺序、后果及独立证据验证所选设计；条件预案不是已接受事实。'})

    actions={r['id']:r for r in product('action_design').get('candidates',[])}
    selected = selected_action_ids(scene_product).get(scene, [])
    multi = (context or {}).get('multi_action_policy') == MULTI_ACTION_POLICY and len(selected) > 1
    for index, ident in enumerate(selected, 1):
        row = actions[ident]
        observable = {k:row[k] for k in ('actor','action','steps','requires','cost','limits')}
        check = '实际呈现所选动作链的对象、动作、障碍、应对、结果及代价；不能仅提到动作名称。'
        if multi:
            observable.update(action_ref=ident, action_order=index)
            check += f' 这是本场第{index}项行动。引用本行动自己的正文片段，核对其与前后行动的实际顺序。'
        append('action', row, observable, check, action_order=index if multi else None)
    events={r['id']:r for r in product('event_design').get('candidates',[])}
    for selection in scene_product.get('selected_events',[]):
        if selection['scene']!=scene or selection['event'] not in events:continue
        row=events[selection['event']]
        append('event',row,{k:row[k] for k in ('predecessor','event','completion_gate','actors','status')},
               '先核对前事件完成条件在前文、当前稿或已接受证据中得到满足，再呈现后继事件；未满足则退回设计。')
    propagations={r['id']:r for r in product('state_propagation').get('candidates',[])}
    for selection in product('anchor_design').get('selected_propagations',[]):
        if selection['scene']!=scene:continue
        row=propagations[selection['propagation']]
        append('propagation',row,{k:row[k] for k in ('root_kind','root_id','source_entity','target_entity',
            'external_action','proposed_effect','continuity','activation_condition','gates','status')},
            '逐项核对根变化确认、外部行动选择及传播后果的证据；不因设计了传播就认定已发生，不自动提交状态变化。')
    return result
