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
    from nw.materials import cast_demands, cast_fulfillment
    cast_enabled = (context or {}).get('cast_demand_policy') == cast_demands.POLICY
    if cast_enabled:
        result.extend(cast_fulfillment.scene_checks(records, scene, context))
    if 'cast_distribution_plan' in scene_product:
        from nw.materials.cast_appearances import review_check
        result.append(review_check(records, scene, ids, context or {}))
    from nw.materials.chapter_progress import POLICIES as PROGRESS_POLICIES, scene_check
    if (context or {}).get('chapter_progress_policy') in PROGRESS_POLICIES:
        if check := scene_check(records, scene, context):
            result.append(check)

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
    from nw.materials.narration import ACCESS_POLICIES
    actors = {}
    if (context or {}).get('narration_policy') in ACCESS_POLICIES:
        actors.update((r['card_id'], r['body']) for r in context.get('approved_cards', []) if r['kind'] == 'character')
        actors.update((r['key'], r['body']) for r in product('character_design').get('members', []))
    for index, ident in enumerate(selected, 1):
        row = actions[ident]
        observable = {k:row[k] for k in ('actor','action','steps','requires','cost','limits')}
        check = '实际呈现所选动作链的对象、动作、障碍、应对、结果及代价；不能仅提到动作名称。'
        if multi:
            observable.update(action_ref=ident, action_order=index)
            check += f' 这是本场第{index}项行动。引用本行动自己的正文片段，核对其与前后行动的实际顺序。'
        append('action', row, observable, check, action_order=index if multi else None)
        actor = actors.get(row['actor'], {})
        if 'casting' in actor or cast_enabled and actor:
            result[-1]['binding']['check'] += ' 从当场可见的措辞、反应或取舍核对这一步怎样体现该人物自己的目的。'
            fields = ('independent_goal', 'behavior', 'want') if cast_enabled else ('independent_goal', 'scene_function', 'behavior')
            result[-1]['actor_design'] = {key: actor[key] for key in fields if key in actor}
            result[-1]['evidence_required'] += ' 以actor_design及实际场内目标核对行动的个人原因；他人视角不能直读其心声。'
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
