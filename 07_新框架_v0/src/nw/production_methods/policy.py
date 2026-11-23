"""Explicit project requirements; legacy jobs keep their frozen behavior."""
from nw.studio.catalog import canonical_types
from nw.studio.method_catalog import TASKS

POLICY='project-corpus-methods-v1'
DEFAULT_TASKS=['character_arc','main_plot','hook','pacing']


def normalize(raw: object, *, types: list[str] = ()) -> dict:
    if raw is None:return {}
    if not isinstance(raw,dict) or set(raw)-{'tasks','type_ids','max_methods','policy','preferred_methods','world_selection',
                                            'recommendation_mode','recommended_slots'}:
        raise ValueError('制作方法配置须包含实际生产任务和类型')
    tasks=raw.get('tasks',DEFAULT_TASKS)
    if not isinstance(tasks,list) or not tasks or len(tasks)>len(TASKS) or any(not isinstance(t,str) or t not in TASKS for t in tasks) or len(set(tasks))!=len(tasks):
        raise ValueError(f'请选择1–{len(TASKS)}项真实制作任务')
    mode = raw.get('world_selection')
    if 'world_selection' in raw and mode != 'ai':
        raise ValueError('未知的世界方法选择方式')
    if mode == 'ai' and 'world_rules' not in tasks:
        tasks = [*tasks, 'world_rules']
    maximum=raw.get('max_methods',6)
    if type(maximum) is not int or not 1<=maximum<=12:raise ValueError('每步采用方法数须为1–12')
    if raw.get('policy',POLICY)!=POLICY:raise ValueError('未知的项目制作方法策略')
    ids=canonical_types(raw.get('type_ids',list(types)))
    if not ids and not (mode == 'ai' and tasks == ['world_rules']):
        raise ValueError('使用拆解方法须明确项目实际类型')
    if types and ids!=canonical_types(list(types)):raise ValueError('制作方法类型须与立项类型一致')
    preferred = raw.get('preferred_methods', {})
    if (not isinstance(preferred, dict) or len(preferred) > 24
            or any(not isinstance(key, str) or not key or len(key) > 100 or type(version) is not int or version < 1
                   for key, version in preferred.items())):
        raise ValueError('无效的立项优选方法版本')
    result = {'policy':POLICY,'tasks':list(tasks),'type_ids':ids,'max_methods':maximum}
    if mode == 'ai':
        result['world_selection'] = mode
    if 'recommendation_mode' in raw:
        if raw['recommendation_mode'] not in ('manual', 'auto'):
            raise ValueError('未知的推荐方法选择方式')
        result['recommendation_mode'] = raw['recommendation_mode']
    if 'recommended_slots' in raw:
        from nw.materials.phase_routes import phase_order
        from nw.studio.method_recommendations import AUTO_SLOT_TASKS

        slots = raw['recommended_slots']
        if (result.get('recommendation_mode') != 'auto' or mode != 'ai'
                or not isinstance(slots, dict) or slots.keys() != AUTO_SLOT_TASKS.keys()):
            raise ValueError('AI 自动须有各板块的制作方法与对应步骤')
        for slot, route in slots.items():
            if (not isinstance(route, dict) or set(route) != {'scope', 'stage', 'versions'}
                    or route['scope'] not in ('book','chapter') or route['stage'] not in phase_order(route['scope'])
                    or slot == 'world' and (route['scope'], route['stage']) != ('book', 'world_design')):
                raise ValueError('无效的自动推荐制作步骤')
            versions = route['versions']
            if (not isinstance(versions, dict) or not 1 <= len(versions) <= 3
                    or any(not isinstance(key, str) or not key or len(key) > 100 or type(v) is not int or v < 1
                           for key, v in versions.items())):
                raise ValueError('无效的自动推荐方法版本')
        result['recommended_slots'] = slots
    if preferred:
        result['preferred_methods'] = preferred.copy()
    return result


def needed(policy: dict,stage: str,scope: str, routes: dict | None = None) -> list[str]:
    scope='chapter' if scope=='replan' else scope
    return [key for key in policy['tasks'] if scope in TASKS[key]['scopes']
            and (routes or {}).get(key,TASKS[key]['stages'][0])==stage]
