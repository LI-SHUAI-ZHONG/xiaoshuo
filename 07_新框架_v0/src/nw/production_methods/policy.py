"""Explicit project requirements; legacy jobs keep their frozen behavior."""
from nw.studio.catalog import canonical_types
from nw.studio.method_catalog import TASKS

POLICY='project-corpus-methods-v1'
DEFAULT_TASKS=['character_arc','main_plot','hook','pacing']


def normalize(raw: object, *, types: list[str] = ()) -> dict:
    if raw is None:return {}
    if not isinstance(raw,dict) or set(raw)-{'tasks','type_ids','max_methods','policy','preferred_methods'}:
        raise ValueError('制作方法配置须包含实际生产任务和类型')
    tasks=raw.get('tasks',DEFAULT_TASKS)
    if not isinstance(tasks,list) or not tasks or len(tasks)>21 or any(not isinstance(t,str) or t not in TASKS for t in tasks) or len(set(tasks))!=len(tasks):
        raise ValueError('请选择1–21项真实制作任务')
    maximum=raw.get('max_methods',6)
    if type(maximum) is not int or not 1<=maximum<=12:raise ValueError('每步采用方法数须为1–12')
    if raw.get('policy',POLICY)!=POLICY:raise ValueError('未知的项目制作方法策略')
    ids=canonical_types(raw.get('type_ids',list(types)))
    if not ids:raise ValueError('使用拆解方法须明确项目实际类型')
    if types and ids!=canonical_types(list(types)):raise ValueError('制作方法类型须与立项类型一致')
    preferred = raw.get('preferred_methods', {})
    if (not isinstance(preferred, dict) or len(preferred) > 24
            or any(not isinstance(key, str) or not key or len(key) > 100 or type(version) is not int or version < 1
                   for key, version in preferred.items())):
        raise ValueError('无效的立项优选方法版本')
    result = {'policy':POLICY,'tasks':list(tasks),'type_ids':ids,'max_methods':maximum}
    if preferred:
        result['preferred_methods'] = preferred.copy()
    return result


def needed(policy: dict,stage: str,scope: str) -> list[str]:
    scope='chapter' if scope=='replan' else scope
    return [key for key in policy['tasks'] if scope in TASKS[key]['scopes'] and TASKS[key]['stages'][0]==stage]
