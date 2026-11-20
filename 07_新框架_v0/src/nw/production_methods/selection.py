"""Freeze candidates and approve applicability plus exact upstream versions."""
from dataclasses import replace

from nw.production_methods.inputs import binding,registry
from nw.production_methods.policy import needed
from nw.production_methods.sources import MethodReader,relevant
from nw.task_models import InputManifest,canonical,content_sha256
from nw.tasks import freeze_manifest,read_input_manifest


def preflight(store: object,package: dict) -> None:
    policy=package.get('production_method_policy')
    if not policy:return
    from nw.materials.phase_routes import phase_order
    reader=MethodReader(store.directory.parent)
    for stage in phase_order(package['scope']):
        required=needed(policy,stage,package['scope'])
        if not required:continue
        rows=relevant(reader,policy,stage,package['scope'],policy['type_ids'])
        covered={t for row in rows for t in row['body']['tasks']}
        if not set(required)<=covered:
            raise ValueError('METHOD_DESIGN_REQUIRED: '+stage+' 缺少对应类型、层级的已批准拆解方法：'+','.join(sorted(set(required)-covered))+'；尚未请求制作模型，请先补方法资料')


def prepare(store: object,request: object,package: dict,stage: str,products: dict,choose: object = None) -> dict | None:
    policy=package.get('production_method_policy')
    if not policy:return None
    scope=package['scope'];inputs=registry(package,products);required=needed(policy,stage,scope)
    reader=MethodReader(store.directory.parent);ident=f'project-methods:{request.id}:{stage}'
    saved=store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?',(ident,)).fetchone()
    if saved:_,target=read_input_manifest(store,ident)
    else:
        actual=products.get('type_selection',{}).get('products',{}).get('_governance',{}).get('project_config',{}).get('genre_ids')
        types=actual or policy['type_ids']
        rows=relevant(reader,policy,stage,scope,types)
        candidates=[binding(row,stage,inputs) for row in rows]
        if len(candidates)>40:raise ValueError('METHOD_DESIGN_REQUIRED: 本步候选方法超过40条，请缩小制作任务或整理适用范围后重建，未截断候选')
        ready={task for c in candidates if not c['missing'] for task in c['method']['body']['tasks']}
        missing=set(required)-ready
        if missing:
            from nw.studio.method_catalog import TASKS
            names='、'.join(TASKS[t]['name'] for t in sorted(missing))
            unavailable=[p for c in candidates for p in c['missing']]
            raise ValueError('METHOD_DESIGN_REQUIRED: '+stage+' 缺少可执行的已批准方法或前置：'+names+
                ('；请先补设计：'+canonical(unavailable) if unavailable else '；请到预存库拆解对应类型作品并在类型资料库批准方法'))
        target={'kind':'production_method_selection','stage':stage,'scope':scope,'required_tasks':required,
            'demand':package['brief'],'type_ids':types,'candidates':candidates,'max_methods':policy['max_methods'],
            'instruction':'核对适用/不适用条件，选择方法并批准其绑定的具体前置。只采用方法，不把原作情节当成本项目事实。'}
        base,_=read_input_manifest(store,request.manifest_id)
        manifest=replace(InputManifest(**base),id=ident,purpose='material_work',context_sha256=content_sha256(target))
        freeze_manifest(store,manifest,target)
    for candidate in target['candidates']:
        for key,actual in candidate['inputs'].items():
            current=inputs.get(actual['kind'])
            if not current or canonical(current)!=canonical(actual):raise ValueError('STALE_PROJECT_METHOD: 上游版本已改变，须重新选择方法')
    ready={c['method']['id']:c for c in target['candidates'] if not c['missing']}
    if not ready and not required:return {'target':target,'selected':[],'decision':None}
    if choose is None:raise ValueError('METHOD_AUTHOR_APPROVAL_REQUIRED: 请在制作台核对方法及其前置后确认')
    def validate(choice: dict) -> None:
        if choice['action']=='reject':return
        selected=choice.get('method_ids')
        if not isinstance(selected,list) or len(selected)>policy['max_methods'] or any(not isinstance(k,str) or k not in ready for k in selected) or len(set(selected))!=len(selected):
            raise ValueError('请选择有效、前置就绪的方法，不能重复或超过每步上限')
        covered={task for key in selected for task in ready[key]['method']['body']['tasks']}
        if not set(required)<=covered:raise ValueError('METHOD_DESIGN_REQUIRED: 所选方法没有覆盖当前必须完成的制作任务')
        for key in selected:reader.verify(ready[key]['method'])
    decision=choose(stage,target,validate)
    validate(decision['choice'])
    if decision['choice']['action']=='reject':raise ValueError('METHOD_DESIGN_REQUIRED: 作者退回方法或前置，须补设计后重建任务')
    selected=[ready[key] for key in decision['choice']['method_ids']]
    return {'target':target,'selected':selected,'decision':decision}


def verify_sources(store: object,session: dict) -> None:
    reader=MethodReader(store.directory.parent)
    for entry in session.get('production_method_parents',[]):reader.verify(entry['method'])
    for record in session.get('stages',[]):
        plan=record.get('production_methods')
        if not plan:continue
        for item in plan['selected']:reader.verify(item['method'])
        if plan['selected']:
            decision=plan['decision'];row=store.connection.execute('SELECT targets_json FROM story_decisions WHERE id=?',(decision['decision_id'],)).fetchone()
            if not row:raise ValueError('STALE_PROJECT_METHOD: 作者的方法/前置确认记录缺失')
            import json
            raw=json.loads(row[0])
            if canonical(raw['target'])!=canonical(plan['target']) or canonical(raw['choice'])!=canonical(decision['choice']):
                raise ValueError('STALE_PROJECT_METHOD: 方法/前置确认与当前冻结设计不一致')
            chosen={item['method']['id'] for item in plan['selected']}
            if chosen!=set(raw['choice']['method_ids']):raise ValueError('STALE_PROJECT_METHOD: 实际方法与作者选择不一致')
