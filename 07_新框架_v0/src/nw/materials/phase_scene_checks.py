"""Selected method designs remain concrete obligations for writing and review."""
from nw.task_models import canonical


def selected_checks(records: dict,scene: str,ids: dict | None=None) -> list[dict]:
    ids=ids or {}
    product=lambda stage:records.get(stage,{}).get('products',{})
    scene_product=product('scene_design')
    body=next((r['body'] for r in scene_product.get('members',[]) if r['key']==scene),{})
    result=[]

    def append(kind: str,row: dict,observable: dict,check: str) -> None:
        for key in ('actor','source_entity','target_entity'):
            if key in observable:observable[key]=ids.get(observable[key],observable[key])
        if 'actors' in observable:observable['actors']=[ids.get(key,key) for key in observable['actors']]
        observable['presentation_boundary']=body.get('allowed_disclosure','仅本场POV可见或可知内容')
        result.append({'id':f'work:selected:{kind}:{scene}:{row["id"]}','profile':'method_work',
            'binding':{'observable':canonical(observable),'check':check},'method_artifact':row,
            'evidence_required':'用本稿中的行动、顺序、后果及独立证据验证所选设计；条件预案不是已接受事实。'})

    actions={r['id']:r for r in product('action_design').get('candidates',[])}
    for selection in scene_product.get('selected_actions',[]):
        if selection['scene']!=scene:continue
        row=actions[selection['action']]
        append('action',row,{k:row[k] for k in ('actor','action','steps','requires','cost','limits')},
               '实际呈现所选动作链的对象、动作、障碍、应对、结果及代价；不能仅提到动作名称。')
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
