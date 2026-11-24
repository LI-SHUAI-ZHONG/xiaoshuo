"""Original creation order, with source-shaped roles and project prerequisites."""
from functools import cache
import json
import re
from nw.materials.semantic_fields import infer_stages
from nw.materials.steps.type_connections import record_step
from nw.task_models import content_sha256

POLICY='artifact-stage-binding-v4'
STAGED_POLICIES={POLICY,'artifact-stage-binding-v3'}
ORDER=('type_selection','type_adaptation','world_design','character_design','static_relations','plot_design',
       'event_design','action_design','scene_design','state_transition','state_propagation',
       'anchor_design','expression_design','bind_scope')
REQUIRES={
    'type_selection':(), 'type_adaptation':('type_selection',),
    'world_design':('type_selection','type_adaptation'),
    'character_design':('type_selection','type_adaptation','world_design'),
    'static_relations':('type_selection','type_adaptation','world_design','character_design'),
    'plot_design':('type_selection','type_adaptation','world_design','character_design','static_relations'),
    'event_design':('world_design','character_design','static_relations','plot_design'),
    'action_design':('world_design','character_design','static_relations','plot_design','event_design'),
    'scene_design':('world_design','character_design','static_relations','plot_design','event_design','action_design'),
    'state_transition':('character_design','static_relations','plot_design','action_design','scene_design'),
    'state_propagation':('world_design','character_design','static_relations','plot_design','action_design','scene_design','state_transition'),
    'anchor_design':('character_design','static_relations','action_design','scene_design','state_transition','state_propagation'),
    'expression_design':('type_selection','type_adaptation','character_design','world_design','static_relations',
                         'plot_design','action_design','scene_design','state_transition','state_propagation','anchor_design'),
    'bind_scope':(),
}
ROUTES={
    'type_identity':('type_selection',),'type_combination':('type_adaptation',),'type_link':('type_adaptation',),
    'world':('world_design',),'character':('character_design','action_design','scene_design','state_transition','expression_design'),
    'static_relation':('static_relations','plot_design'),'static_binding':('static_relations','plot_design'),
    'plot':('plot_design','event_design'),'opening':('plot_design','event_design','scene_design'),
    'scene':('event_design','action_design','scene_design'),'knowledge':('plot_design','scene_design'),
    'dynamic_relation':('state_transition',),'dynamic_binding':('state_transition',),'type_transition':('state_transition',),
    'anchor':('anchor_design',),'expression':('action_design','expression_design'),'type_expression':('type_adaptation','expression_design'),
    'prose_review':('expression_design','review'),'scope_review':('scene_design','review'),
    'editor':('review',),'character_editor':('character_design','review'),
    'timeline_process':('scene_design',),'promise_process':('plot_design',),
    'pov_process':('scene_design',),'preflight_process':('world_design','character_design','plot_design','scene_design'),
    'usage_process':('bind_scope','review'),'material_selection':('bind_scope',),'material_conversion':('bind_scope',),
    'brief':('type_selection',),'preflight':('bind_scope','writer'),
    'continuity':('review','acceptance'),
}
TEMPLATE_STAGES={'TDR_TEMPLATE_001':'state_propagation','TDR_TEMPLATE_002':'type_adaptation',
                 'TDR_TEMPLATE_003':'state_transition','TDR_TEMPLATE_004':'event_design',
                 'TDR_TEMPLATE_005':'action_design'}
EXTERNAL_REQUIRES={
    'writer':('approved_scene_design','current_pov_context'),
    'review':('frozen_draft','source_bound_design'),
    'acceptance':('passing_independent_review','reviewed_state_delta','author_decision'),
    'governance':('source_original','workflow_policy'),
}


def phase_order(scope: str, *, planning_hierarchy: bool = False) -> list[str]:
    if scope == 'book' or planning_hierarchy and scope == 'volume':
        return [*ORDER[:6], 'bind_scope']
    return list(ORDER)


_ANCHOR_TABLE_SHA256 = '9b7ea71e53613a453fe71fa0a862411f65f22328a38ee7b97db7fd5bab7be759'
_LIBRARY_SHA256 = '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed'
_TYPE_SYSTEM_SHA256 = 'aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582'
_STATIC_NETWORK_SHA256 = '0a415d8d38642b352521abc15650f93e1fda10f1c3b4225f2c17cab70c89d197'
_DYNAMIC_NETWORK_SHA256 = 'd6093b82fe6e072bdff7300fadcf175112b988d319c6b836f5d5b881b5282cc6'
_ANCHOR_KEY_RE = re.compile(r'^[A-Z]+\d+\.\d+$')

# These originals also have uses written into later steps, which have their own inputs.
_LIBRARY_STEP_USES = {
    ('scene', '159.1_事前计划显性化'): ('expression_design',),
    ('world', '40.2_制作'): ('action_design', 'expression_design'),
    ('world', '40.1_制造'): ('action_design', 'expression_design'),
    ('world', '37.4_构造与兼容性'): ('action_design', 'expression_design'),
    ('world', '30.3_道具制造_制作工艺'): ('action_design', 'expression_design'),
    ('knowledge', '158.3_回忆设计'): ('expression_design',),
    ('world', '32.7_未写明的历史'): ('plot_design', 'expression_design'),
    ('character', '5.1_亲缘关系'): ('static_relations', 'plot_design'),
    ('character', '5.2_社会关系'): ('static_relations',),
    ('character', '5.3_情感关系'): ('static_relations', 'expression_design'),
    ('character', '5.6_权力不对称'): ('static_relations',),
    ('character', '5.8_情感债务'): ('static_relations', 'plot_design'),
    ('character', '5.9_信任-怀疑光谱'): ('static_relations', 'plot_design'),
    ('character', '5.11_立场与关系位置'): ('static_relations',),
    ('character', '1.7_角色关系网络'): ('static_relations',),
    ('plot', '板块45 伏笔与反转#反转合理性'): ('expression_design',),
    ('plot', '板块45 伏笔与反转#伏笔休眠期'): ('scene_design',),
    ('plot', '板块45 伏笔与反转#伏笔揭示'): ('event_design', 'scene_design', 'expression_design'),
    ('plot', '板块45 伏笔与反转#伏笔延迟解码'): ('scene_design', 'expression_design'),
    ('plot', '板块45 伏笔与反转#深层伏笔掩体设计'): ('expression_design',),
    ('plot', '板块45 伏笔与反转#伏笔与反转联动'): ('event_design', 'expression_design'),
    ('knowledge', '120.20_视角与伏笔系统'): ('scene_design',),
    ('world', '125.30_资源库的“空位”设计'): ('plot_design', 'scene_design'),
    ('scene', '板块46 场景结构#场景过渡'): ('expression_design',),
    ('knowledge', '120.7_读者重置成本'): ('expression_design',),
    ('knowledge', '120.17_信息补偿'): ('expression_design',),
    ('world', '125.24_资源库与时间线的同步'): ('scene_design', 'state_transition'),
    ('plot', '板块48 章节结构#结尾规则'): ('scene_design',),
    ('plot', '板块48 章节结构#章节连续性'): ('scene_design',),
    ('plot', '板块62 节奏控制#场景内快慢交替'): ('scene_design', 'expression_design'),
    ('plot', '板块62 节奏控制#情绪承接'): ('scene_design', 'expression_design'),
    ('plot', '板块65 读者认知#读者不确定性管理'): ('scene_design',),
    ('plot', '113.3_时间跳跃规则'): ('scene_design', 'expression_design'),
    ('plot', '155.2_“谁在哪、为什么去”共情铺垫'): ('scene_design',),
    ('plot', '155.3_节奏类型与情感密度的强制匹配'): ('scene_design',),
    ('plot', '44.2_爽点身体反应'): ('expression_design',),
    ('plot', '44.8_高潮三层情感叠加'): ('expression_design',),
    ('character', '6.1_基础情感'): ('plot_design',),
    ('anchor', '110.2_氛围与角色情绪的映射'): ('expression_design',),
    ('expression', '板块59 视角规则#配角POV强制性内容'): ('scene_design',),
    ('expression', '板块59 视角规则#配角POV前500字限制'): ('scene_design',),
    ('world', '19.3_例外的代价'): ('action_design', 'state_transition'),
    ('world', '28.2_道具功能边界'): ('plot_design', 'action_design', 'scene_design', 'expression_design'),
    ('world', '28.3_道具代价机制'): ('plot_design', 'action_design', 'state_transition', 'expression_design'),
    ('world', '28.4_道具成瘾性'): ('plot_design', 'state_transition'),
    ('world', '28.5_道具记忆载体'): ('plot_design', 'expression_design'),
    ('world', '28.6_道具象征化'): ('plot_design', 'expression_design'),
    ('world', '29.1_道具与角色交互'): ('action_design', 'anchor_design', 'expression_design'),
    ('world', '29.2_道具与环境交互'): ('action_design', 'scene_design'),
    ('world', '29.3_道具反功能'): ('plot_design', 'action_design', 'scene_design', 'expression_design'),
    ('world', '29.4_道具进化'): ('plot_design', 'state_transition', 'expression_design'),
    ('world', '30.2_功能边界测试与突破'): ('action_design', 'scene_design'),
    ('world', '30.4_道具维护与升级'): ('action_design', 'state_transition', 'expression_design'),
    ('world', '30.5_道具失效与转化'): ('plot_design', 'scene_design', 'state_transition', 'expression_design'),
    ('character', '121.4_配角的登场时机'): ('plot_design',),
    ('expression', '156.3_外貌审美'): ('expression_design',),
    ('plot', '板块48 章节结构#视角分配规则'): ('scene_design',),
    ('expression', '板块59 视角规则#主角POV功能'): ('scene_design',),
    ('expression', '板块59 视角规则#配角POV功能'): ('scene_design',),
    ('expression', '板块59 视角规则#场景内视角一致'): ('scene_design',),
    ('expression', '板块59 视角规则#视角切换标记'): ('scene_design',),
    ('expression', '板块59 视角规则#视角与不可见信息'): ('scene_design',),
    ('expression', '板块59 视角规则#信息差设计'): ('plot_design', 'scene_design'),
    ('character', '121.9_配角独立行动线'): ('plot_design',),
    ('character', '121.9_配角独立行动规则'): ('event_design',),
    ('character', '121.11_配角之间的互动关系'): ('static_relations',),
    ('character', '121.19_配角群的网络关系'): ('static_relations',),
    ('knowledge', '116.6_信息释放时机控制'): ('expression_design',),
    ('world', '15.4_突破的代价类型'): ('action_design', 'state_transition'),
    ('world', '15.5_突破失败后果'): ('plot_design', 'action_design', 'state_transition'),
    ('plot', '42.6_岔路设计与回撤机制'): ('action_design', 'state_transition'),
    ('plot', '42.8_失败设计'): ('action_design', 'state_transition'),
    ('plot', '43.1_资源争夺'): ('action_design', 'scene_design'),
    ('plot', '43.2_信息博弈'): ('scene_design', 'expression_design'),
    ('plot', '43.3_制度压迫'): ('action_design',),
    ('plot', '43.4_道德困境'): ('action_design', 'scene_design', 'expression_design'),
    ('plot', '43.5_信任危机'): ('state_transition', 'expression_design'),
    ('plot', '43.6_时间压力'): ('action_design', 'expression_design'),
    ('plot', '43.7_身份冲突'): ('action_design', 'scene_design'),
    ('plot', '43.9_冲突叠加'): ('scene_design',),
    ('plot', '板块145 五节点链条'): ('action_design',),
}


@cache
def _in_step_stage_map() -> dict[str, tuple[str, ...]]:
    from nw.materials.phase_flow import DEFAULT_STAGE_MATERIALS
    from nw.materials.stage_input import extract_step_keys

    by_key: dict[str, list[str]] = {}
    for stage in ORDER:
        for key in extract_step_keys(DEFAULT_STAGE_MATERIALS.get(stage, '')):
            stages = by_key.setdefault(key, [])
            if stage not in stages:
                stages.append(stage)
    return {key: tuple(stages) for key, stages in by_key.items()}


@cache
def _in_step_anchor_routes() -> dict[str, str]:
    steps: dict[str, str] = {}
    for key, stages in _in_step_stage_map().items():
        if _ANCHOR_KEY_RE.fullmatch(key):
            if len(stages) > 1:
                raise ValueError(f'MATERIAL_ROUTE: conflicting in-step anchor {key}')
            steps[key] = stages[0]
    return steps


def route_method(source: dict) -> dict:
    ref=source.get('source',source);key=ref.get('key','');profile=ref.get('profile','metadata')
    stages=list(ROUTES.get(profile,('governance',)))
    raw=source.get('original_text',source.get('function_text'))
    try:raw=json.loads(raw) if isinstance(raw,str) else raw
    except ValueError:pass
    inferred=infer_stages(raw,profile,key) if raw is not None else []
    discovered=source.get('execution_stages') or ref.get('execution_stages')
    basis='profile_discovery'
    if isinstance(discovered,list) and discovered:stages=list(discovered);basis='pinned_source_index'
    elif inferred:stages=inferred;basis='original_shape'
    template=next((stage for name,stage in TEMPLATE_STAGES.items() if key.startswith(name)),None)
    if template:stages=[template];basis='original_template_contract'
    if step := record_step(ref):
        stages = [step]; basis = 'in_step_type_connection'
    fsha = ref.get('file_sha256')
    if (profile == 'anchor' and fsha == _ANCHOR_TABLE_SHA256 and
            (step := _in_step_anchor_routes().get(key))):
        stages = list(dict.fromkeys((step, *stages)))
        if key.startswith('ID'):
            basis = 'in_step_identity_anchor'
        elif key.startswith('U'):
            basis = 'in_step_unexpected_anchor'
        else:
            basis = 'in_step_anchor'
    if fsha == _LIBRARY_SHA256:
        later_steps = (*(_LIBRARY_STEP_USES.get((profile, key)) or ()), *_in_step_stage_map().get(key, ()))
        if later_steps:
            stages = list(dict.fromkeys((*stages, *later_steps)))
            basis = 'in_step_library'
    if not template and fsha in (_DYNAMIC_NETWORK_SHA256, _STATIC_NETWORK_SHA256, _TYPE_SYSTEM_SHA256):
        if in_steps := _in_step_stage_map().get(key):
            if fsha in (_DYNAMIC_NETWORK_SHA256, _STATIC_NETWORK_SHA256):
                stages = list(in_steps)
                basis = 'in_step_dynamic_network' if fsha == _DYNAMIC_NETWORK_SHA256 else 'in_step_static_network'
            else:
                stages = list(dict.fromkeys((*in_steps, *stages)))
                basis = 'in_step_type_system'
    requires=sorted({name for stage in stages for name in REQUIRES.get(stage,())},key=ORDER.index)
    return {'policy':POLICY,'stages':stages,'requires':requires,'role_basis':basis,
            'authority':'candidate_discovery_only_not_execution_binding',
            'requires_by_stage':{stage:list(REQUIRES.get(stage,EXTERNAL_REQUIRES.get(stage,()))) for stage in stages},
            'requires_policy':'union_for_discovery_only_execute_with_current_stage_requirements',
            'source_state':source.get('source_state',source.get('state')),
            'template_policy':'instantiate_after_project_inputs_without_promoting_source_or_completed_facts'}


def readiness(stage: str,products: dict,scope: str='chapter', *, planning_hierarchy: bool = False) -> dict:
    required=(phase_order(scope, planning_hierarchy=planning_hierarchy)[:-1] if stage=='bind_scope' else REQUIRES[stage])
    missing=[name for name in required if not isinstance(products.get(name),dict)
             or not products[name].get('products') or not products[name].get('sha256')]
    return {'stage':stage,'state':'waiting_for_inputs' if missing else 'ready','missing':missing,
            'source_qualification_changed':False}


def product_ref(record: dict) -> dict:
    if content_sha256(record['products'])!=record['sha256']:
        raise ValueError('MATERIAL_STAGE: upstream product hash mismatch')
    return {'stage':record['stage'],'task_id':record['task_id'],'sha256':record['sha256']}
