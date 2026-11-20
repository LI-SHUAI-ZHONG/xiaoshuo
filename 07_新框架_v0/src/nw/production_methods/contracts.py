"""Method operations must land in real fields, never in an adjacent usage label."""
from nw.materials.phase_contract import FIELDS
from nw.task_models import canonical,content_sha256


def require(ok: bool,message: str) -> None:
    if not ok:raise ValueError('PROJECT_METHOD: '+message)


def explanation(value: object) -> bool:
    return isinstance(value,str) and len(''.join(value.split()))>=12 and value.strip() not in ('已使用该方法完成设计','已完成该方法的实际使用')


def at(value: object,path: list) -> object:
    require(isinstance(path,list) and bool(path) and len(path)<=12,'产物落点须为明确字段路径')
    for key in path:
        require(type(key) is int or isinstance(key,str),'落点只能包含字段名或数组序号')
        if isinstance(value,list):require(type(key) is int and 0<=key<len(value),'产物数组落点不存在')
        else:require(isinstance(value,dict) and isinstance(key,str) and key in value,'产物字段不存在')
        value=value[key]
    return value


def placements(rows: object,products: dict,stage: str,*,definition: dict | None=None) -> list[dict]:
    require(isinstance(rows,list) and bool(rows) and len(rows)<=100,'方法需要具体产物落点')
    seen=set()
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'path','value'},'落点须含path及实际value')
        path=row['path'];require(isinstance(path,list) and path and isinstance(path[0],str) and path[0] in FIELDS[stage],'不能落到方法标签或虚构字段')
        key=canonical(path);require(key not in seen,'方法落点重复');seen.add(key)
        value=at(products,path)
        require(canonical(value)==canonical(row['value']) and value not in (None,'',[],{}),'方法值与本项目实际产物不一致或为空')
        if definition:
            require(path[0]==definition['field'],'方法产物放错了制作字段')
            if definition['artifact_kind']!='stage_product':
                require(len(path)>=2 and path[0]=='members' and type(path[1]) is int,'设计卡须明确对应实际成员')
                member=products['members'][path[1]]
                require(member['kind']==definition['artifact_kind'],'方法声明的卡种与实际产物不一致')
    if definition and definition['field']=='directions':
        whole=any(len(r['path'])==1 for r in rows)
        indices={r['path'][1] for r in rows if len(r['path'])>1}
        require(whole or indices==set(range(len(products['directions']))),'方法须落实到每个可选剧情方向，不能让其他方案缺少设计')
    return rows


def guides(rows: object,scenes: set[str],*,required: bool=False) -> None:
    require(isinstance(rows,list),'场景交接须为列表')
    seen=set()
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'scene','observable','check'} and isinstance(row['scene'],str) and row['scene'] in scenes and row['scene'] not in seen,
                '交接只能指向本方案的实际场景')
        require(explanation(row['observable']) and explanation(row['check']),'场景交接须写明可见呈现及实际验收方法')
        seen.add(row['scene'])
    require(not required or bool(rows),'面向写作/审稿的方法须交给实际场景，不能仅登记已用')


def validate(products: dict,stage: str,plan: dict | None,incoming: list[dict],scenes: set[str]) -> None:
    apps=products.get('_method_applications',[]);receipts=products.get('_method_receipts',[])
    if plan is None:
        require(not apps and not receipts,'未请求的制作方法使用记录');return
    require(isinstance(apps,list) and isinstance(receipts,list),'缺少方法执行与下游回执')
    selected={r['method']['id']:r for r in plan['selected']}
    require(len(apps)==len(selected),'每项所选方法都须执行')
    ai_world = stage == 'world_design' and plan['target'].get('selection_mode') == 'ai'
    world_members = set()
    for app in apps:
        fields = {'method_id', 'operations', 'outputs'}
        if ai_world:
            fields.add('design_basis')
        require(isinstance(app,dict) and set(app)==fields and isinstance(app['method_id'],str) and app['method_id'] in selected,'方法执行标识无效或重复')
        spec=selected.pop(app['method_id']);body=spec['method']['body']
        if ai_world:
            from nw.production_methods.world_design import check_basis
            check_basis(app['design_basis'], {**plan['target'], 'adaptation_indices': spec['adaptation_indices']})
        require(isinstance(app['operations'],list),'必须说明本步实际执行的操作')
        expected={r['key']:r for r in spec['operations']}
        for op in app['operations']:
            require(isinstance(op,dict) and set(op)=={'key','explanation'} and isinstance(op['key'],str) and op['key'] in expected,'方法操作缺失或重复')
            original=expected.pop(op['key']);require(explanation(op['explanation']) and op['explanation']!=original['instruction'],'操作须解释如何用本项目的前置产生设计，不能复制说明')
        require(not expected,'部分方法操作未执行')
        expected={r['key']:r for r in spec['outputs']}
        require(isinstance(app['outputs'],list),'须提交方法的实际产物')
        for output in app['outputs']:
            require(isinstance(output,dict) and set(output)=={'key','placements','scene_guidance'} and isinstance(output['key'],str) and output['key'] in expected,'产物缺失或重复')
            definition=expected.pop(output['key']);placements(output['placements'],products,stage,definition=definition)
            if ai_world and definition['artifact_kind'] == 'world':
                from nw.production_methods.world_design import check_world_output
                world_members.update(check_world_output(output['placements'], products, spec['method']))
            visible=any(d['output_key']==output['key'] and d['consumer'] in ('writer','review','acceptance') for d in body['downstream'])
            guides(output['scene_guidance'],scenes,required=bool(scenes) and visible)
        require(not expected,'方法预期产物未全部落实')
    if ai_world:
        expected_world = {i for i, member in enumerate(products['members']) if member['kind'] == 'world'}
        require(world_members and world_members == expected_world, '每个本书世界卡都须能追溯实际采用的拆解方法')
    expected={r['id']:r for r in incoming};require(len(receipts)==len(expected),'下游必须逐项回执，不能只收到资料却不使用')
    for receipt in receipts:
        require(isinstance(receipt,dict) and set(receipt)=={'id','operation','placements','scene_guidance'} and isinstance(receipt['id'],str) and receipt['id'] in expected,
                '下游回执引用不存在或重复')
        delivery=expected.pop(receipt['id']);require(explanation(receipt['operation']),'下游须解释怎样承接已有设计')
        placements(receipt['placements'],products,stage)
        guides(receipt['scene_guidance'],scenes,required=stage=='scene_design')
        if delivery.get('world_design_basis'):
            from nw.production_methods.world_design import check_receipt
            check_receipt(receipt, products, stage)


def schema(*, ai_world: bool = False) -> dict:
    text={'type':'string'};any_value={'type':['string','number','boolean','object','array','null']}
    def obj(fields: dict) -> dict:return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
    def arr(item: dict) -> dict:return {'type':'array','items':item}
    place=obj({'path':arr({'type':['string','integer']}),'value':any_value})
    guide=obj({'scene':text,'observable':text,'check':text})
    app = {'method_id':text, 'operations':arr(obj({'key':text,'explanation':text})),
           'outputs':arr(obj({'key':text,'placements':arr(place),'scene_guidance':arr(guide)}))}
    if ai_world:
        app['design_basis'] = arr(obj({'kind': {'type': 'string', 'enum': ['type_adaptation', 'type_selection', 'brief']},
                                       'path': arr({'type': ['string','integer']})}))
    return {'_method_applications':arr(obj(app)),
            '_method_receipts':arr(obj({'id':text,'operation':text,'placements':arr(place),'scene_guidance':arr(guide)}))}
