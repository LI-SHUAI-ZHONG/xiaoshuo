"""Freeze candidates and approve applicability plus exact upstream versions."""
from dataclasses import replace
import json

from nw.production_methods.inputs import binding,registry
from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.production_methods.policy import needed
from nw.production_methods.sources import MethodReader,relevant,stage_tasks
from nw.studio.method_catalog import TASKS
from nw.task_models import InputManifest,canonical,content_sha256
from nw.tasks import freeze_manifest,read_input_manifest


def method_step(scope: str, stage: str) -> str:
    return f'plan:{scope}:methods:{stage}'


def preflight(store: object,package: dict,request_id: str) -> None:
    policy=package.get('production_method_policy')
    if not policy:return
    from nw.materials.phase_routes import phase_order
    scope = package['scope']
    stages = phase_order(scope)
    # A plan that already started keeps its pending gates and completed calls.
    first = f'project-methods:{request_id}:{stages[0]}'
    if store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (first,)).fetchone():
        return
    reader=MethodReader(store.directory.parent)
    for stage in stages:
        required=needed(policy,stage,scope)
        if not required:continue
        rows=relevant(reader,policy,stage,scope,policy['type_ids'])
        covered={t for row in rows for t in stage_tasks(row['body'], stage, scope)}
        if not set(required)<=covered:
            raise ValueError('METHOD_DESIGN_REQUIRED: '+stage+' 缺少对应类型、层级的已批准拆解方法：'+','.join(sorted(set(required)-covered))+'；尚未请求制作模型，请先补方法资料')


def build_target(reader: MethodReader, package: dict, stage: str, products: dict) -> dict:
    policy = package['production_method_policy']
    scope = package['scope']
    inputs = registry(package, products)
    required = needed(policy, stage, scope)
    config = products.get('type_selection', {}).get('products', {}).get('_governance', {}).get('project_config', {})
    types = config.get('genre_ids') or policy['type_ids']
    preferred = policy.get('preferred_methods', {})
    candidates = []
    for method in relevant(reader, policy, stage, scope, types):
        candidate = binding(method, stage, inputs)
        candidate['type_match'] = type_match(types, method['body']['type_tags'])
        candidate['preferred'] = preferred.get(method['id']) == method['version']
        candidates.append(candidate)
    candidates.sort(key=lambda item: (
        bool(item['missing']), TYPE_PRIORITY[item['type_match']['level']], not item['preferred'],
        -len(set(required) & stage_tasks(item['method']['body'], stage, scope))))
    if len(candidates) > 40:
        raise ValueError('METHOD_DESIGN_REQUIRED: 本步候选方法超过40条，请缩小制作任务或整理适用范围后重建，未截断候选')
    covered = {task for item in candidates if not item['missing']
               for task in stage_tasks(item['method']['body'], stage, scope)}
    return {'kind': 'production_method_selection', 'stage': stage, 'scope': scope, 'required_tasks': required,
            'missing_tasks': sorted(set(required) - covered),
            'demand': package['brief'], 'type_ids': types, 'candidates': candidates, 'max_methods': policy['max_methods'],
            'instruction': '核对适用条件，选择方法并批准其绑定的具体前置。原作情节只作为参考案例。'}


def gate_target(gate: dict) -> dict:
    return {key: value for key, value in gate.items() if key not in ('token', 'actions')}


def check_bindings(target: dict, inputs: dict) -> None:
    for candidate in target['candidates']:
        for actual in candidate['inputs'].values():
            current = inputs.get(actual['kind'])
            if not current or canonical(current) != canonical(actual):
                raise ValueError('STALE_PROJECT_METHOD: 上游版本已改变，须重新选择方法')


def validate_choice(reader: MethodReader, target: dict, choice: dict) -> None:
    if choice['action'] == 'reject':
        return
    ready = {item['method']['id']: item['method'] for item in target['candidates'] if not item['missing']}
    selected = choice.get('method_ids')
    if (not isinstance(selected, list) or len(selected) > target['max_methods']
            or any(not isinstance(key, str) or key not in ready for key in selected)
            or len(set(selected)) != len(selected)):
        raise ValueError('请选择当前有效且前置就绪的方法；不能重复或超过每步上限')
    covered = set()
    for key in selected:
        method = ready[key]
        tasks = stage_tasks(method['body'], target['stage'], target['scope'])
        if not tasks or not type_match(target['type_ids'], method['body']['type_tags']):
            raise ValueError('所选方法不适用于当前类型或制作步骤，请刷新方法候选')
        reader.verify(method)
        covered.update(tasks)
    if not set(target['required_tasks']) <= covered:
        raise ValueError('METHOD_DESIGN_REQUIRED: 所选方法没有覆盖当前必须完成的制作任务')


def prepare(store: object,request: object,package: dict,stage: str,products: dict,choose: object = None) -> dict | None:
    policy=package.get('production_method_policy')
    if not policy:return None
    scope = package['scope']
    key = method_step(scope, stage)
    reader = MethodReader(store.directory.parent)
    ident = f'project-methods:{request.id}:{stage}'
    saved_gate = store.connection.execute('''SELECT attempt,input_json FROM novel_steps WHERE job_id=? AND step_key=?
        ORDER BY attempt DESC LIMIT 1''', (request.budget_id, key)).fetchone()
    saved = store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (ident,)).fetchone()
    if saved:
        _, target = read_input_manifest(store, ident)
        if saved_gate and saved_gate['attempt'] > 1:
            target = gate_target(json.loads(saved_gate['input_json']))
            if target.get('candidate_revision') != saved_gate['attempt']:
                raise ValueError('STALE_PROJECT_METHOD: 刷新记录与候选版本不一致')
    elif saved_gate:
        raise ValueError('STALE_PROJECT_METHOD: 本步最初的选材记录缺失')
    else:
        target = build_target(reader, package, stage, products)
        missing = target['missing_tasks']
        if missing:
            names='、'.join(TASKS[t]['name'] for t in missing)
            unavailable=[p for c in target['candidates'] for p in c['missing']]
            raise ValueError('METHOD_DESIGN_REQUIRED: '+stage+' 缺少可执行的已批准方法或前置：'+names+
                ('；请先补设计：'+canonical(unavailable) if unavailable else '；请到预存库拆解对应类型作品并在类型资料库批准方法'))
        base,_=read_input_manifest(store,request.manifest_id)
        manifest=replace(InputManifest(**base),id=ident,purpose='material_work',context_sha256=content_sha256(target))
        freeze_manifest(store,manifest,target)
    check_bindings(target, registry(package, products))
    ready={c['method']['id']:c for c in target['candidates'] if not c['missing']}
    if not ready and not target['required_tasks'] and not saved_gate:return {'target':target,'selected':[],'decision':None}
    if choose is None:raise ValueError('METHOD_AUTHOR_APPROVAL_REQUIRED: 请在制作台核对方法及其前置后确认')
    decision=choose(stage,target,lambda choice: validate_choice(reader, target, choice))
    if decision['choice']['action']=='reject':raise ValueError('METHOD_DESIGN_REQUIRED: 作者退回方法或前置，须补设计后重建任务')
    selected=[ready[key] for key in decision['choice']['method_ids']]
    return {'target':target,'selected':selected,'decision':decision}


def verify_sources(store: object,session: dict) -> None:
    reader=MethodReader(store.directory.parent)
    for entry in session.get('production_method_parents',[]):reader.verify(entry['method'], require_current=False)
    for record in session.get('stages',[]):
        plan=record.get('production_methods')
        if not plan:continue
        for item in plan['selected']:reader.verify(item['method'], require_current=False)
        if plan['selected']:
            decision=plan['decision'];row=store.connection.execute('SELECT targets_json FROM story_decisions WHERE id=?',(decision['decision_id'],)).fetchone()
            if not row:raise ValueError('STALE_PROJECT_METHOD: 作者的方法/前置确认记录缺失')
            raw=json.loads(row[0])
            if canonical(raw['target'])!=canonical(plan['target']) or canonical(raw['choice'])!=canonical(decision['choice']):
                raise ValueError('STALE_PROJECT_METHOD: 方法/前置确认与当前冻结设计不一致')
            chosen={item['method']['id'] for item in plan['selected']}
            if chosen!=set(raw['choice']['method_ids']):raise ValueError('STALE_PROJECT_METHOD: 实际方法与作者选择不一致')
            frozen = {item['method']['id']: item for item in raw['target']['candidates']}
            if any(canonical(item) != canonical(frozen.get(item['method']['id'])) for item in plan['selected']):
                raise ValueError('STALE_PROJECT_METHOD: 实际方法版本或前置已偏离作者批准的快照')
