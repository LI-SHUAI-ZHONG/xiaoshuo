"""Keep the original plan and the staged story checks on the same contract versions."""
from nw.materials import cast_demands, chapter_progress, narration
from nw.materials.phase_routes import POLICY, STAGED_POLICIES


VERSIONS = {
    'narration_policy': narration.POLICIES,
    'chapter_progress_policy': chapter_progress.POLICIES,
    'cast_demand_policy': (cast_demands.POLICY,),
}


def current() -> dict[str, str]:
    return {'narration_policy': narration.EVIDENCE_POLICY, 'chapter_progress_policy': chapter_progress.POLICY,
            'cast_demand_policy': cast_demands.POLICY}


def verify(context: dict, plan: dict | None = None) -> None:
    for key, supported in VERSIONS.items():
        if key in context and context[key] not in supported:
            raise ValueError(f'MATERIAL_STAGE: 无法识别冻结的制作校验版本 {key}={context[key]}')
        if plan is not None and ((key in plan) != (key in context) or plan.get(key) != context.get(key)):
            raise ValueError(f'MATERIAL_STAGE: 阶段的 {key} 与原设计任务冻结的版本不同，请重新读取原方案')


def verify_session(session: dict, plan: dict | None = None) -> None:
    context = session.get('context')
    if session.get('policy') not in STAGED_POLICIES or not isinstance(context, dict):
        raise ValueError('MATERIAL_STAGE: 已冻结的分步制作缺少原阶段及校验版本')
    if session['policy'] != POLICY and VERSIONS.keys() & context.keys():
        raise ValueError('MATERIAL_STAGE: 此制作校验版本需要支持人物和章场设计的阶段装配程序')
    verify(context, plan)


def verify_plan(plan: dict) -> None:
    verify(plan)
    if plan.get('material_mode') == 'source_driven_staged' or ('material_work' in plan and VERSIONS.keys() & plan.keys()):
        session = plan.get('material_work') or {}
        verify_session(session, plan)
