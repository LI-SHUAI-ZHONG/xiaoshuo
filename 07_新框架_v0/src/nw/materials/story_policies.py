"""Keep the original plan and the staged story checks on the same contract versions."""
from nw.materials import cast_demands, cast_distribution_plan, chapter_progress, narration, passage_sequence
from nw.materials.phase_routes import POLICY, STAGED_POLICIES
from nw.materials.passage_craft import POLICY as CRAFT_POLICY
from nw.materials.scene_knowledge import POLICY as KNOWLEDGE_POLICY


VERSIONS = {
    'narration_policy': narration.POLICIES,
    'scene_knowledge_policy': (KNOWLEDGE_POLICY,),
    'chapter_progress_policy': chapter_progress.POLICIES,
    'cast_demand_policy': (cast_demands.POLICY,),
    'cast_distribution_policy': (cast_distribution_plan.POLICY,),
    'passage_policy': (passage_sequence.POLICY,),
    'passage_craft_policy': (CRAFT_POLICY,),
}


def current() -> dict[str, str]:
    return {'narration_policy': narration.EVIDENCE_POLICY, 'chapter_progress_policy': chapter_progress.POLICY,
            'cast_demand_policy': cast_demands.POLICY, 'passage_policy': passage_sequence.POLICY,
            'passage_craft_policy': CRAFT_POLICY}


def verify(context: dict, plan: dict | None = None) -> None:
    from nw.materials.book_direction import approved

    direction = approved(context)
    if plan is not None and direction != approved(plan):
        raise ValueError('STALE_BOOK_DIRECTION: 阶段交接与原任务冻结的全书方向不同')
    if plan is not None and any(context.get(key) != plan.get(key) for key in (
            'planning_hierarchy', 'outline_lineage', 'chapter_target_index', 'promise_continuity',
            'creative_workflow_policy')):
        raise ValueError('STALE_PLAN_HIERARCHY: 阶段交接与原任务冻结的上级方案不同')
    if plan is not None and plan.get('planning_hierarchy'):
        from nw.materials.planning_hierarchy import inherited_types

        if context.get('hierarchy_inherited_types') != inherited_types(plan):
            raise ValueError('STALE_PLAN_HIERARCHY: 阶段采用了不同的已批准类型与适配')
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
    if context.get('passage_craft_policy') and context.get('passage_policy') != passage_sequence.POLICY:
        raise ValueError('MATERIAL_STAGE: 章场写法需要原任务冻结的叙述设计版本')
    if context.get('passage_policy'):
        if context.get('narration_policy') != narration.EVIDENCE_POLICY:
            raise ValueError('MATERIAL_STAGE: 连续段落需要原设计任务的带证据叙述节拍')
        if plan is not None and context.get('passage_references', []) != plan.get('passage_references', []):
            raise ValueError('MATERIAL_STAGE: 分步制作与原设计任务冻结的段落方法引用不同')
    if plan is not None and context.get('cast_distribution_policy'):
        for key in ('cast_sample_reference', 'cast_distribution_book_plan', 'cast_previous_appearances'):
            if context.get(key) != plan.get(key):
                raise ValueError('MATERIAL_STAGE: 阵容取舍的样本、章段依据或既有人物出场记录与原设计任务不同')
        if context.get('cast_history_unverified_chapters', []) != plan.get('accepted_cast_history', {}).get('unverified_chapters', []):
            raise ValueError('MATERIAL_STAGE: 既有章稿的出场待核记录与原设计任务不同')
        if context.get('cast_verified_first_positions', {}) != plan.get('accepted_cast_history', {}).get('first_positions', {}):
            raise ValueError('MATERIAL_STAGE: 既有章稿的已核出场位置与原设计任务不同')


def verify_plan(plan: dict) -> None:
    verify(plan)
    if plan.get('scene_knowledge_policy') and (not plan.get('branch_head') or not plan.get('narration_policy') or
            plan['scope'] == 'book' or plan.get('planning_hierarchy') and plan['scope'] == 'volume'):
        raise ValueError('MATERIAL_STAGE: 人物所知核对需要已冻结的分支与章场叙述方案')
    if plan.get('material_mode') == 'source_driven_staged' or ('material_work' in plan and VERSIONS.keys() & plan.keys()):
        session = plan.get('material_work') or {}
        verify_session(session, plan)
