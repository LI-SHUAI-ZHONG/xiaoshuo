"""Attach executable corpus methods to existing design stages without bypassing them."""
from nw.production_methods.contracts import schema,validate
from nw.production_methods.handoff import deliveries
from nw.task_models import canonical

PROMPT='''
[PROJECT_METHOD_EXECUTION]
production_methods是作者已选并已确认前置版本的参考制作方法，不是原作情节可直接变成本项目事实的许可。
逐项按适用/不适用条件、绑定的本项目前置、实际操作和拆解实例完成设计；前置不足须停止补设计，不让写作代猜。
products另含_method_applications，每项严格为{method_id,operations:[{key,explanation}],
outputs:[{key,placements:[{path:[字段,序号,子字段...],value:该实际值}],scene_guidance:[{scene,observable,check}]}]}。
每个所选方法、其本步操作和产物都须出现；explanation解释怎样执行本项目设计，不复制方法说明。
placements必须指向本步真实products字段和卡片；value须与该位置完全相同，不能只写已使用、名称、标签。
产物为directions时覆盖每个可选方向。scene_guidance使用真实场景key和该视角能看到的呈现；书级无场景时为空。
method_handoffs是上游/已批准父纲的具体产物。另含_method_receipts，逐项严格为
{id:交接id,operation:如何承接其具体设计,placements:[{path,value}],scene_guidance:[{scene,observable,check}]}。
每个交接都要落到本步真实产物；场景步骤须将它交给实际场景，供正文和独立审稿逐项核验。
方法或交接列表为空，相应数组为空。设计产物仍是候选，只有作者最终批准后才能供正式写作。
'''


def prompt(plan: dict | None, incoming: tuple | list = ()) -> str:
    if plan and plan['target'].get('selection_mode') == 'inherit_world':
        return PROMPT + ('\n本章/卷沿用production_method_selection.approved_world_members中的项目世界卡。'
                         '逐张保留其key、rule和limits，_method_applications为空。根据这些已批准规则推进后续剧情与场景。')
    if not plan or plan['target'].get('selection_mode') != 'ai':
        active=[*plan['selected'], *incoming] if plan else []
        instruction=PROMPT
        if any((item['method'].get('structure_origin') or {}).get('observation_domains') for item in active):
            instruction+=('\n采用人物出场或章场进展方法时，从本书当前问题与已知事实出发，把角色承担的工作、'
                          '自身理由、获知身份的途径或章场实际改变落实到本书所选产物。'
                          '复用已有角色时可按冻结需求引用cast_assignments完整行，剧情与本场职责用cast_events或'
                          'cast_payoffs完整行；章场进展用scene_progress，前章问题接续用continuations。'
                          '只填写本步已声明和启用的产物。本轮职责的回执须定位到相同demand的cast_events或cast_payoffs。'
                          '拆解实例source_context提供原作人物、章节、引文位置的对应关系。'
                          '参考书中的姓名与结局只作实例。场景或表达步骤将采用处定位到具体场次或节拍；'
                          'scene_guidance须来自所选场次，表达交接复用该场同一行的observable和check。')
        if any('narration' in item['method']['body']['tasks'] for item in active):
            instruction += ('\n采用叙述方法时，使用拆解实例中有引文支持的叙述次序、说话或观察者及读者获得的信息，'
                             '根据本项目人物、事件与披露许可重新设计。表达步骤的 placements 指向 guidance 的具体行'
                             '或该行的 narration、observable、check。场景设计的落点定位到具体场卡、场次、事件或选定行动；'
                             '每项用 scene_guidance 交给这些落点所属的实际场景。表达步骤每场取所用节拍中一行的'
                             'observable 和 check 原样填写该场的交接；各拍仍按实际设计顺序提交。')
        return instruction
    return PROMPT.replace(
        'production_methods是作者已选并已确认前置版本的参考制作方法，不是原作情节可直接变成本项目事实的许可。',
        'production_methods是已核实原作证据及前置版本的候选。参照production_method_selection.demand，按'
        '每个候选自己的adaptation_indices定位与该方法及原作类型相符的具体参数或限制，逐项核对'
        '适用与不适用条件。选用本页适用的1至max_methods项；若本页全部不适用，提交world_method_gap说明依据。'
        '同一次世界设计调用完成选择和项目规则设计。项目世界设定可以从零设计，无需作者预填世界卡。'
        '保留原作方法的作用机制，本项目人物、地点、规则、限制与代价须依据前置重新创作。'
    ).replace(
        '每个所选方法、其本步操作和产物都须出现；',
        '只为实际采用的方法提交_method_applications，每项还须提供design_basis:[{kind:"type_adaptation",'
        'path:["adaptations",实际序号,"parameters",参数名]}]，或指向limits的实际限制条目。'
        '落点说明这条世界规则及限制怎样体现该前置。每个所选方法、其本步操作和产物都须出现；'
    )


def split(value: dict) -> tuple[dict,dict]:
    products=value.get('products')
    if not isinstance(products,dict):return value,{}
    extras={k:products[k] for k in ('_method_applications','_method_receipts') if k in products}
    return {**value,'products':{k:v for k,v in products.items() if k not in extras}},extras


def extra_fields(transport: dict, *, ai_world: bool = False) -> dict:
    if 'anyOf' in transport:
        for variant in transport['anyOf']:extra_fields(variant, ai_world=ai_world)
    fields=transport.get('properties',{}).get('products',{})
    if fields:
        extra = schema(ai_world=ai_world)
        fields['properties'].update(extra);fields['required'].extend(extra)
    return transport


def scenes(products: dict,previous: dict) -> set[str]:
    return {m['key'] for m in [*previous.get('scene_design',{}).get('products',{}).get('members',[]),
                               *products.get('members',[])] if m['kind']=='scene'}


def validate_output(value: dict,stage: str,previous: dict,plan: dict | None,parents: list[dict]) -> None:
    if 'products' not in value:return
    validate(value['products'],stage,plan,deliveries(stage,previous,parents),scenes(value['products'],previous))


def packet(plan: dict | None,incoming: list[dict]) -> dict:
    if plan is None:return {}
    target = plan['target']
    if target.get('selection_mode') == 'inherit_world':
        return {'production_methods': [], 'method_handoffs': incoming, 'production_method_decision': None,
                'production_method_selection': {'mode': 'inherit_world',
                    'approved_world_members': target['approved_world_members'], 'parent_deliveries': target['parent_deliveries']}}
    if target.get('selection_mode') == 'ai':
        return {'production_methods': target['candidates'][:target['page_size']], 'method_handoffs': incoming,
                'production_method_decision': None,
                'production_method_selection': {'mode': 'ai', 'max_methods': target['max_methods'],
                    'demand': target['demand'], 'upstream_refs': target['upstream_refs'],
                    'adaptation_indices': target['adaptation_indices']}}
    return {'production_methods':plan['selected'],'method_handoffs':incoming,
            'production_method_decision':plan['decision']}


def verify_plan_source(store: object,plan: dict | None) -> None:
    if plan is None:return
    from nw.production_methods.selection import verify_sources
    verify_sources(store,{'stages':[{'production_methods':plan}]})
