"""Small, replayable calls in the original creation order, backed by real products."""
from dataclasses import replace
from typing import Callable

from nw.call_budget import prepare_call
from nw.call_control import model_settings
from nw.config import Config, resolve_stage_runtime
from nw.llm.base import LLMProvider
from nw.materials.binding_reviews import allows_stage_candidate, model_review
from nw.materials.phase_contract import FIELDS,validate_phase,require
from nw.materials.phase_routes import POLICY,REQUIRES,TEMPLATE_STAGES,phase_order,product_ref,route_method,readiness
from nw.materials.phase_lifecycle import requirements_for,writing_sources
from nw.materials.phase_dependencies import deferred_source_ids
from nw.materials.source_semantics import POLICY as SEMANTIC_POLICY
from nw.materials.phase_context import visible_facts
from nw.materials.phase_projection import compile_candidates,verify_chain
from nw.materials.steps import type_connections
from nw.materials.steps import (
    action_design,
    action_design_anchor_network,
    action_design_anchor_network_2,
    action_design_anchor_network_3,
    action_design_deliberation_anchors,
    action_design_anchor_network_4,
    action_design_costs,
    action_design_decisions,
    action_design_dialogue,
    action_design_ethics,
    action_design_information,
    action_design_interaction,
    action_design_meaning,
    action_design_crafting,
    action_design_mechanism_adaptations,
    action_design_misalignment,
    action_design_plot,
    action_design_plot_mechanisms,
    action_design_dynamic_network,
    action_design_dynamic_network_2,
    action_design_dynamic_network_3,
    action_design_dynamic_network_4,
    action_design_dynamic_network_5,
    action_design_static_network,
    action_design_progression,
    action_design_resources,
    action_design_type_expression_adaptations,
    action_design_type_rules,
    anchor_design,
    anchor_design_anchor_network,
    anchor_design_anchor_network_2,
    anchor_design_anchor_network_3,
    anchor_design_body_emotion,
    anchor_design_atmosphere,
    anchor_design_multi_viewpoint,
    anchor_design_scene,
    anchor_design_dynamic_network,
    anchor_design_static_network,
    anchor_design_timeline,
    anchor_design_viewpoint,
    bind_scope_application,
    bind_scope_dynamic_network,
    bind_scope_selection,
    bind_scope_source_tags,
    bind_scope_task_mapping,
    bind_scope_templates,
    bind_scope_type_rules,
    bind_scope_workflow,
    character_design,
    character_design_anchor_network,
    character_design_cognition,
    character_design_ethics,
    character_design_fate,
    character_design_plot_mechanisms,
    character_design_dynamic_network,
    character_design_static_network,
    character_design_supporting,
    character_design_type_expression_adaptations,
    event_design,
    event_design_anchor_network,
    event_design_plot,
    event_design_plot_mechanisms,
    event_design_dynamic_network,
    event_design_static_network,
    event_design_progression,
    event_design_supporting,
    event_design_type_expression_adaptations,
    event_design_type_rules,
    expression_design,
    expression_design_anchor_network,
    expression_design_anchor_network_2,
    expression_design_anchor_network_3,
    expression_design_anchor_network_4,
    expression_design_anchor_network_5,
    expression_design_application,
    expression_design_atmosphere,
    expression_design_classification,
    expression_design_cognition,
    expression_design_continuity,
    expression_design_costs,
    expression_design_dialogue,
    expression_design_disclosure,
    expression_design_ethics,
    expression_design_identification,
    expression_design_interaction,
    expression_design_deliberation,
    expression_design_crafting,
    expression_design_misalignment,
    expression_design_multi_viewpoint,
    expression_design_narrator,
    expression_design_plot,
    expression_design_progression,
    expression_design_reader,
    expression_design_reader_engagement,
    expression_design_resources,
    expression_design_sensory,
    expression_design_space,
    expression_design_dynamic_network,
    expression_design_dynamic_network_2,
    expression_design_dynamic_network_3,
    expression_design_static_network,
    expression_design_supporting,
    expression_design_symbolism,
    expression_design_timeline,
    expression_design_tone_adaptations,
    expression_design_type_choices,
    expression_design_type_expression_adaptations,
    expression_design_age_adaptations,
    expression_design_type_rules,
    expression_design_type_styles,
    expression_design_type_tones,
    expression_design_viewpoint,
    expression_design_world,
    plot_design,
    plot_design_anchor_network,
    plot_design_memory,
    plot_design_chapter_expectations,
    plot_design_chapters,
    plot_design_classification,
    plot_design_continuity,
    plot_design_decisions,
    plot_design_disclosure,
    plot_design_ethics,
    plot_design_fate,
    plot_design_foreshadowing,
    plot_design_identification,
    plot_design_misalignment,
    plot_design_multi_viewpoint,
    plot_design_narrative_structures,
    plot_design_type_materials,
    plot_design_narrator,
    plot_design_opening_ending,
    plot_design_path_templates,
    plot_design_plot_mechanisms,
    plot_design_progression,
    plot_design_promise_workflow,
    plot_design_reader,
    plot_design_reader_engagement,
    plot_design_resources,
    plot_design_dynamic_network,
    plot_design_dynamic_network_2,
    plot_design_dynamic_network_3,
    plot_design_dynamic_network_4,
    plot_design_dynamic_network_5,
    plot_design_dynamic_network_6,
    plot_design_dynamic_network_7,
    plot_design_static_network,
    plot_design_deliberation,
    plot_design_meaning,
    plot_design_crafting,
    plot_design_time,
    plot_design_social_material,
    plot_design_structure,
    plot_design_supporting,
    plot_design_symbolism,
    plot_design_type_expression_adaptations,
    plot_design_type_expectations,
    plot_design_type_rules,
    plot_design_world,
    scene_design,
    scene_design_anchor_network,
    scene_design_memory,
    scene_design_anchor_network_2,
    scene_design_classification,
    scene_design_disclosure,
    scene_design_multi_viewpoint,
    scene_design_narrator,
    scene_design_opening_timeline,
    scene_design_dynamic_network,
    scene_design_static_network,
    scene_design_pacing,
    scene_design_planner,
    scene_design_progression,
    scene_design_space,
    scene_design_structure,
    scene_design_structure_adaptations,
    scene_design_supporting,
    scene_design_type_expression_adaptations,
    scene_design_type_rules,
    scene_design_viewpoint,
    scene_design_workflow_sources,
    state_propagation,
    state_propagation_anchor_network,
    state_propagation_dynamic_network,
    state_propagation_deliberation,
    state_propagation_meaning,
    state_propagation_crafting,
    state_propagation_memory,
    state_propagation_social_material,
    state_propagation_type_rules,
    state_transition,
    state_transition_anchor_network,
    state_transition_anchor_network_2,
    state_transition_anchor_network_3,
    state_transition_anchor_network_4,
    state_transition_anchor_network_5,
    state_transition_cognition,
    state_transition_continuity,
    state_transition_costs,
    state_transition_ethics,
    state_transition_interaction,
    state_transition_plot,
    state_transition_progression,
    state_transition_resources,
    state_transition_dynamic_network,
    state_transition_deliberation,
    state_transition_meaning,
    state_transition_crafting,
    state_transition_memory,
    state_transition_dynamic_network_2,
    state_transition_dynamic_network_3,
    state_transition_static_network,
    state_transition_supporting,
    state_transition_type_rules,
    state_transition_world,
    static_relations,
    static_relations_anchor_network,
    work_connection_patterns,
    work_case_application,
    static_relations_misalignment,
    static_relations_space,
    static_relations_dynamic_network,
    static_relations_action_methods,
    static_relations_static_network,
    static_relations_deliberation,
    static_relations_meaning,
    static_relations_crafting,
    static_relations_time,
    static_relations_social_material,
    static_relations_supporting,
    type_adaptation_audience_tags,
    type_adaptation_classification,
    type_adaptation_dynamic_network,
    type_adaptation_expectations,
    type_adaptation_hybrid_genres,
    type_adaptation_market_tags,
    type_adaptation_plot_mechanisms,
    type_adaptation_reader_engagement,
    type_adaptation_static_network,
    type_adaptation_type_expression_adaptations,
    type_adaptation_type_rules,
    type_adaptation_type_combinations,
    type_adaptation_type_combinations_02,
    type_adaptation_type_combinations_03,
    type_adaptation_type_combinations_04,
    type_adaptation_type_combinations_05,
    type_adaptation_type_combinations_06,
    type_adaptation_type_combinations_07,
    type_adaptation_type_combinations_08,
    type_adaptation_type_combinations_09,
    type_adaptation_type_combinations_10,
    type_adaptation_type_combinations_11,
    type_adaptation_type_combinations_12,
    type_adaptation_type_combinations_13,
    type_adaptation_type_combinations_14,
    type_adaptation_type_combinations_15,
    type_adaptation_type_combinations_16,
    type_adaptation_type_combinations_17,
    type_adaptation_type_combinations_18,
    type_adaptation_type_combinations_19,
    type_adaptation_type_combinations_20,
    type_adaptation_type_combinations_21,
    type_adaptation_type_combinations_22,
    type_adaptation_type_combinations_23,
    type_adaptation_type_combinations_24,
    type_adaptation_type_combinations_25,
    type_adaptation_type_combinations_26,
    type_adaptation_type_combinations_27,
    type_adaptation_type_combinations_28,
    type_adaptation_type_combinations_29,
    type_adaptation_type_combinations_30,
    type_adaptation_type_combinations_31,
    type_adaptation_type_combinations_32,
    type_adaptation_type_combinations_33,
    type_adaptation_type_combinations_34,
    type_adaptation_type_combinations_35,
    type_adaptation_type_combinations_36,
    type_adaptation_type_combinations_37,
    type_adaptation_type_combinations_38,
    type_adaptation_type_combinations_39,
    type_adaptation_type_combinations_40,
    type_adaptation_type_combinations_41,
    type_adaptation_type_combinations_42,
    type_adaptation_type_combinations_43,
    type_adaptation_type_combinations_44,
    type_adaptation_type_combinations_45,
    type_adaptation_type_combinations_46,
    type_adaptation_type_combinations_47,
    type_adaptation_type_combinations_48,
    type_adaptation_type_combinations_49,
    type_adaptation_type_combinations_50,
    type_adaptation_type_combinations_51,
    type_adaptation_type_combinations_52,
    type_adaptation_type_combinations_53,
    type_adaptation_type_combinations_54,
    type_adaptation_type_combinations_55,
    type_adaptation_type_combinations_56,
    type_adaptation_type_combinations_57,
    type_adaptation_type_combinations_58,
    type_adaptation_type_combinations_59,
    type_adaptation_type_combinations_60,
    type_adaptation_type_combinations_61,
    type_adaptation_type_combinations_62,
    type_adaptation_type_combinations_63,
    type_adaptation_type_combinations_64,
    type_adaptation_type_combinations_65,
    type_adaptation_type_combinations_66,
    type_adaptation_type_combinations_67,
    type_adaptation_type_combinations_68,
    type_adaptation_type_combinations_69,
    type_adaptation_type_combinations_70,
    type_adaptation_type_combinations_71,
    type_adaptation_type_combinations_72,
    type_adaptation_type_combinations_73,
    type_adaptation_type_combinations_74,
    type_adaptation_type_combinations_75,
    type_adaptation_type_combinations_76,
    type_adaptation_type_combinations_77,
    type_adaptation_type_combinations_78,
    type_adaptation_history_penalty,
    type_adaptation_age_boundaries,
    type_adaptation_combination_review,
    work_source_review,
    type_adaptation_work_case_rules,
    type_adaptation_genre_profiles,
    type_selection_dianjing_subgenres,
    type_selection_dushi_subgenres,
    type_selection_erciyuan_subgenres,
    type_selection_ertong_subgenres,
    type_selection_genres,
    type_selection_genres_continued,
    type_selection_gongting_subgenres,
    type_selection_jiating_subgenres,
    type_selection_jishi_subgenres,
    type_selection_junshi_subgenres,
    type_selection_kehuan_subgenres,
    type_selection_kongbu_subgenres,
    type_selection_lingyi_subgenres,
    type_selection_lishi_subgenres,
    type_selection_moshi_subgenres,
    type_selection_nvxing_subgenres,
    type_selection_ontology,
    type_selection_qingchun_subgenres,
    type_selection_qingxiaoshuo_subgenres,
    type_selection_qihuan_subgenres,
    type_selection_saibo_subgenres,
    type_selection_shehui_subgenres,
    type_selection_subject_tags,
    type_selection_tiyu_subgenres,
    type_selection_tonghua_subgenres,
    type_selection_tongren_subgenres,
    type_selection_tuili_subgenres,
    type_selection_type_rules,
    type_selection_main_and_subgenres,
    type_selection_weilai_subgenres,
    type_selection_wuxia_subgenres,
    type_selection_xianshi_subgenres,
    type_selection_xianxia_subgenres,
    type_selection_xuanyi_subgenres,
    type_selection_xuanhuan_subgenres,
    type_selection_yanqing_subgenres,
    type_selection_youxi_subgenres,
    type_selection_zhiye_subgenres,
    type_selection_zhutian_subgenres,
    world_design,
    world_design_anchor_network,
    world_design_ecology,
    world_design_plot_mechanisms,
    world_design_resources,
    world_design_setting,
    world_design_space,
    world_design_dynamic_network,
    world_design_dynamic_network_2,
    world_design_dynamic_network_3,
    world_design_static_network,
    world_design_theme,
    world_design_type_expression_adaptations,
)
from nw.materials.work_catalog import SourceDesk
from nw.store import Store
from nw.task_models import InputManifest,TaskRequest,canonical,content_sha256
from nw.tasks import freeze_manifest,read_input_manifest
STEP_PROMPT='''[MATERIAL_STEP] 仅执行当前stage，输出JSON {stage,products}。按本步资料的原义操作实际inputs，
output_contract给出本步JSON结构，所有<填写>必须替换为实际项目内容；描述字段用文字，输出完整闭合JSON。
先读原文及运用层，依据当前任务选择参数、设计实际产物；不能先自由编造方案再登记来源。
只用本步资料及真实上游产品，不索取全库，不重新设计前置步骤。资料是方法，项目结果均为候选，不是已接受事实。
填写本项目实际操作和结果，不能用“外部行动选择”“失败条件和处理”“连续性检查”等栏目名冒充设计。
state_transition的choice/action选定本条候选路线的实际应对，不只列“如果A/如果B”而不选择；failure另写失败分支，continuity写选定后果怎样延续。
mode=execute表示已交付本步请求的完整原文，当前调用必须提交本步骤实际products或逐项说明方法不适用，不重复索取同一资料。
template允许在前置产物齐备时实例化，但不得替来源补定义、改资格、自动生成已完成事件。
products必须含output_schema全部字段及_uses数组；每项{source_id,operation,output_refs}，operation说明具体操作，
本步每个实际_uses来源另有_criteria:{source_id,contract_sha256,clauses,layer_application}。clauses逐source_contracts义务一项，含id、applicability(applies/not_applicable/source_unresolved)、reason、input_refs、output_refs、operation、observable、check、consumer。
input_refs引用本次实际发送的brief:/text、input:上游stage:/实际products内JSON路径、approved:人物ID:/body/字段或fact:索引:/字段；output_refs引用本步products的/JSON路径，不能用_criteria、来源ID或状态标签自证。
semantic_requirements是上游原义条款指定交给本步的工作。逐项回_receipts:[{id:交接ID,operation:怎样承接实际输入执行本步,output_refs:[本步实际产物/JSON路径]}]；所需原文见semantic_requirement_sources。不能只确认收到或更换上游结果。
source_use_reviews给出原文和原工作流已核的本步用途、前置、产物及检验边界；不能改为其他用途。clause_decisions中needs_review的条款用source_unresolved并引用binding_interpretation_needs_review，不补造；全部未核或不适用的来源不能记入_uses。候选检索结果和分类不构成执行许可。
source_readings保留本步请求回读的原件及对应运用层。execution_admitted=false时，按原文识别缺项、冲突或待核用途，继续在本步查找；正式采用看sources和source_use_reviews。
clause_decisions中not_project_instruction是来源追溯层的编号/引用，记not_applicable并说明当前不作为小说指令，不把来源编号或文件名写进正文证明效果；方法真正要求的项目依赖仍须满足。
applies必须把原条件、方法操作落到真实输入和实际产物字段，给出当前可观察表现及下游检验；此记录不是效果已通过。source_unresolved仅用于合同明确列出的局部缺义条款，引用该源问题，不补造；完整可用部分继续执行。
如有运用层，layer_application给出当前项目具体trigger/operation/result/verification；仅已对齐字段可指导执行，被拒字段不得回流。
operation至少八个非空白字符，说明怎样将原文判据用于本步真实产物，不能只回read或已使用。
每份资料ID在_uses最多一项，operation用中文完整说明人物/事件/实际设计怎样符合原文；不是工具调用名，不能写readout_*、读取原文/来源状态/哈希等元数据动作。
output_refs引用实际非空产物：member:key、scene:key、direction:索引、relation:id、selection、boundaries、limitations、unknowns、reader_plan、promise_plan、bindings、guidance:场景key。
新增产物引用concept:id、adaptation:id、focus:id、requirement:id、event_node:id、event_candidate:id、action:id、propagation:id。waiting不算已运用。
method_requirements是上游已按资料形成的本步约束；逐项生成_requirements:[{id,operation,output_refs}]，引用本步实际结果，不能只确认收到。
未选中的事件、行动、传播仍是有效的设计备选，不得全部塞进本场；bind_scope仅对writing_source_ids所列适用方法形成本场具体表现及判据。
使用读者情绪方法必须形成reader_plan的信息顺序、情绪及触发安排；使用伏笔方法必须形成promise_plan的埋设、预期与回收安排，不能只登记用途。
不适用的方法放_excluded:[{source_id,reason}]并说明与当前任务的实际差异，不能只因template或blocked而排除。
只能创建本步骤的产物；后步骤用现有人物、场景、事件和前状态，不能虚构缺失的前置。
dependency_source_ids来自前步实际采用资料的后续引用；只在当前步读取并按真实前置使用或说明不适用，不能把引用关系本身当成已确认事实。
人物和世界卡明确visibility(public、holders、author_only)；场景人物的可见设定必须对该POV可用，私密信息另置author_only卡，不能全设public。
资料不够时可先输出{stage,requests:[{action:search,query:具体用途,cursor:0}或{action:read,id:本步候选ID}]}，
检索结果可翻页；读取全文后才能使用。每次只处理当前步骤，预算不够时停止，不能伪造已读或省略必要资料。'''

ASSEMBLY_PROMPT='''[MATERIAL_ASSEMBLY] 当前阶段的设计已由前面各步模型真实生成并通过前置产物校验。
只输出输入output_contract的JSON引用以确认组装，不另造、替换或补写故事内容。'''

STAGE_INSTRUCTIONS={
 'type_adaptation':'TDR_TEMPLATE_002 按已选类型和已激活项目概念调整关注重点。实体状态变化沿对应步骤核对。',
 'event_design':'TDR_TEMPLATE_004 先引用前事件完成条件，再设计后继候选。条件未满足时保留条件预案。',
 'action_design':'TDR_TEMPLATE_005 按人物实际能力设计可选择的行动链，采用时核对真实事件参与者及能力前置。',
 'scene_design':'明确选择已有事件及动作，scene.body.choice原样采用所选action.action；所选候选须承接上游_requirements。',
 'state_transition':'每个事件至多一条transition，每场至多一个patch。action选择具体应对；cost、failure、continuity各用一完整短句，避免重复条目。',
 'state_propagation':'TDR_TEMPLATE_001 用于条件传播预案。gates必须包含require_root_confirmation、require_external_action_selection、require_continuity_validation且均为true。accepted_fact须匹配accepted_changes中的真实变化。',
}

STAGE_MATERIALS = {
    'type_selection': '\n'.join((
        type_selection_ontology.MATERIAL,
        type_selection_genres.MATERIAL, type_selection_genres_continued.MATERIAL,
        type_selection_xuanhuan_subgenres.MATERIAL, type_selection_xianxia_subgenres.MATERIAL,
        type_selection_qihuan_subgenres.MATERIAL, type_selection_wuxia_subgenres.MATERIAL,
        type_selection_dushi_subgenres.MATERIAL,
        type_selection_lishi_subgenres.MATERIAL, type_selection_junshi_subgenres.MATERIAL,
        type_selection_kehuan_subgenres.MATERIAL, type_selection_xuanyi_subgenres.MATERIAL,
        type_selection_tuili_subgenres.MATERIAL,
        type_selection_lingyi_subgenres.MATERIAL, type_selection_kongbu_subgenres.MATERIAL,
        type_selection_youxi_subgenres.MATERIAL, type_selection_dianjing_subgenres.MATERIAL,
        type_selection_tiyu_subgenres.MATERIAL, type_selection_yanqing_subgenres.MATERIAL,
        type_selection_xianshi_subgenres.MATERIAL, type_selection_qingchun_subgenres.MATERIAL,
        type_selection_erciyuan_subgenres.MATERIAL, type_selection_qingxiaoshuo_subgenres.MATERIAL,
        type_selection_tongren_subgenres.MATERIAL, type_selection_zhutian_subgenres.MATERIAL,
        type_selection_moshi_subgenres.MATERIAL, type_selection_saibo_subgenres.MATERIAL,
        type_selection_weilai_subgenres.MATERIAL,
        type_selection_tonghua_subgenres.MATERIAL, type_selection_ertong_subgenres.MATERIAL,
        type_selection_jishi_subgenres.MATERIAL, type_selection_zhiye_subgenres.MATERIAL,
        type_selection_nvxing_subgenres.MATERIAL, type_selection_jiating_subgenres.MATERIAL,
        type_selection_gongting_subgenres.MATERIAL, type_selection_shehui_subgenres.MATERIAL,
        type_selection_subject_tags.MATERIAL,
        type_selection_type_rules.MATERIAL,
        type_selection_main_and_subgenres.MATERIAL,
    )),
    'type_adaptation': '\n'.join((
        type_adaptation_expectations.MATERIAL, type_adaptation_reader_engagement.MATERIAL,
        type_adaptation_classification.MATERIAL, type_adaptation_hybrid_genres.MATERIAL,
        type_adaptation_plot_mechanisms.MATERIAL,
        type_adaptation_audience_tags.MATERIAL, type_adaptation_market_tags.MATERIAL,
        type_adaptation_type_expression_adaptations.MATERIAL,
        type_adaptation_type_rules.MATERIAL,
        type_adaptation_type_combinations.MATERIAL,
        type_adaptation_type_combinations_02.MATERIAL,
        type_adaptation_type_combinations_03.MATERIAL,
        type_adaptation_type_combinations_04.MATERIAL,
        type_adaptation_type_combinations_05.MATERIAL,
        type_adaptation_type_combinations_06.MATERIAL,
        type_adaptation_type_combinations_07.MATERIAL,
        type_adaptation_type_combinations_08.MATERIAL,
        type_adaptation_type_combinations_09.MATERIAL,
        type_adaptation_type_combinations_10.MATERIAL,
        type_adaptation_type_combinations_11.MATERIAL,
        type_adaptation_type_combinations_12.MATERIAL,
        type_adaptation_type_combinations_13.MATERIAL,
        type_adaptation_type_combinations_14.MATERIAL,
        type_adaptation_type_combinations_15.MATERIAL,
        type_adaptation_type_combinations_16.MATERIAL,
        type_adaptation_type_combinations_17.MATERIAL,
        type_adaptation_type_combinations_18.MATERIAL,
        type_adaptation_type_combinations_19.MATERIAL,
        type_adaptation_type_combinations_20.MATERIAL,
        type_adaptation_type_combinations_21.MATERIAL,
        type_adaptation_type_combinations_22.MATERIAL,
        type_adaptation_type_combinations_23.MATERIAL,
        type_adaptation_type_combinations_24.MATERIAL,
        type_adaptation_type_combinations_25.MATERIAL,
        type_adaptation_type_combinations_26.MATERIAL,
        type_adaptation_type_combinations_27.MATERIAL,
        type_adaptation_type_combinations_28.MATERIAL,
        type_adaptation_type_combinations_29.MATERIAL,
        type_adaptation_type_combinations_30.MATERIAL,
        type_adaptation_type_combinations_31.MATERIAL,
        type_adaptation_type_combinations_32.MATERIAL,
        type_adaptation_type_combinations_33.MATERIAL,
        type_adaptation_type_combinations_34.MATERIAL,
        type_adaptation_type_combinations_35.MATERIAL,
        type_adaptation_type_combinations_36.MATERIAL,
        type_adaptation_type_combinations_37.MATERIAL,
        type_adaptation_type_combinations_38.MATERIAL,
        type_adaptation_type_combinations_39.MATERIAL,
        type_adaptation_type_combinations_40.MATERIAL,
        type_adaptation_type_combinations_41.MATERIAL,
        type_adaptation_type_combinations_42.MATERIAL,
        type_adaptation_type_combinations_43.MATERIAL,
        type_adaptation_type_combinations_44.MATERIAL,
        type_adaptation_type_combinations_45.MATERIAL,
        type_adaptation_type_combinations_46.MATERIAL,
        type_adaptation_type_combinations_47.MATERIAL,
        type_adaptation_type_combinations_48.MATERIAL,
        type_adaptation_type_combinations_49.MATERIAL,
        type_adaptation_type_combinations_50.MATERIAL,
        type_adaptation_type_combinations_51.MATERIAL,
        type_adaptation_type_combinations_52.MATERIAL,
        type_adaptation_type_combinations_53.MATERIAL,
        type_adaptation_type_combinations_54.MATERIAL,
        type_adaptation_type_combinations_55.MATERIAL,
        type_adaptation_type_combinations_56.MATERIAL,
        type_adaptation_type_combinations_57.MATERIAL,
        type_adaptation_type_combinations_58.MATERIAL,
        type_adaptation_type_combinations_59.MATERIAL,
        type_adaptation_type_combinations_60.MATERIAL,
        type_adaptation_type_combinations_61.MATERIAL,
        type_adaptation_type_combinations_62.MATERIAL,
        type_adaptation_type_combinations_63.MATERIAL,
        type_adaptation_type_combinations_64.MATERIAL,
        type_adaptation_type_combinations_65.MATERIAL,
        type_adaptation_type_combinations_66.MATERIAL,
        type_adaptation_type_combinations_67.MATERIAL,
        type_adaptation_type_combinations_68.MATERIAL,
        type_adaptation_type_combinations_69.MATERIAL,
        type_adaptation_type_combinations_70.MATERIAL,
        type_adaptation_type_combinations_71.MATERIAL,
        type_adaptation_type_combinations_72.MATERIAL,
        type_adaptation_type_combinations_73.MATERIAL,
        type_adaptation_type_combinations_74.MATERIAL,
        type_adaptation_type_combinations_75.MATERIAL,
        type_adaptation_type_combinations_76.MATERIAL,
        type_adaptation_type_combinations_77.MATERIAL,
        type_adaptation_type_combinations_78.MATERIAL,
        type_adaptation_history_penalty.MATERIAL,
        type_adaptation_age_boundaries.MATERIAL,
        type_adaptation_combination_review.MATERIAL,
        work_source_review.MATERIAL,
        type_adaptation_work_case_rules.MATERIAL,
        work_case_application.TYPE_ADAPTATION_MATERIAL,
        type_adaptation_genre_profiles.MATERIAL,
        type_adaptation_dynamic_network.MATERIAL,
        type_adaptation_static_network.MATERIAL,
    )),
    'world_design': '\n'.join((
        world_design.MATERIAL, world_design_ecology.MATERIAL, world_design_setting.MATERIAL,
        world_design_theme.MATERIAL, world_design_space.MATERIAL, world_design_resources.MATERIAL,
        world_design_plot_mechanisms.MATERIAL,
        world_design_type_expression_adaptations.MATERIAL,
        work_case_application.WORLD_DESIGN_MATERIAL,
        world_design_dynamic_network.MATERIAL,
        world_design_dynamic_network_2.MATERIAL,
        world_design_dynamic_network_3.MATERIAL,
        world_design_static_network.MATERIAL,
        world_design_anchor_network.MATERIAL,
    )),
    'character_design': '\n'.join((
        character_design.MATERIAL, character_design_cognition.MATERIAL, character_design_ethics.MATERIAL,
        character_design_fate.MATERIAL, character_design_supporting.MATERIAL,
        character_design_plot_mechanisms.MATERIAL,
        character_design_type_expression_adaptations.MATERIAL,
        work_case_application.CHARACTER_DESIGN_MATERIAL,
        character_design_dynamic_network.MATERIAL,
        character_design_static_network.MATERIAL,
        character_design_anchor_network.MATERIAL,
    )),
    'static_relations': '\n'.join((
        static_relations.MATERIAL, static_relations_space.MATERIAL, static_relations_misalignment.MATERIAL,
        static_relations_supporting.MATERIAL,
        static_relations_dynamic_network.MATERIAL,
        static_relations_static_network.MATERIAL,
        static_relations_deliberation.MATERIAL,
        static_relations_meaning.MATERIAL,
        static_relations_crafting.MATERIAL,
        static_relations_time.MATERIAL,
        static_relations_social_material.MATERIAL,
        static_relations_anchor_network.MATERIAL,
        static_relations_action_methods.MATERIAL,
        work_connection_patterns.STATIC_MATERIAL,
        work_case_application.STATIC_RELATIONS_MATERIAL,
    )),
    'plot_design': '\n'.join((
        plot_design.MATERIAL, plot_design_world.MATERIAL, plot_design_structure.MATERIAL,
        plot_design_foreshadowing.MATERIAL, plot_design_chapters.MATERIAL, plot_design_reader.MATERIAL,
        plot_design_decisions.MATERIAL, plot_design_ethics.MATERIAL, plot_design_fate.MATERIAL,
        plot_design_continuity.MATERIAL, plot_design_narrator.MATERIAL, plot_design_symbolism.MATERIAL,
        plot_design_opening_ending.MATERIAL, plot_design_type_expectations.MATERIAL, plot_design_disclosure.MATERIAL,
        plot_design_misalignment.MATERIAL, plot_design_identification.MATERIAL, plot_design_multi_viewpoint.MATERIAL,
        plot_design_supporting.MATERIAL, plot_design_progression.MATERIAL, plot_design_chapter_expectations.MATERIAL,
        plot_design_reader_engagement.MATERIAL, plot_design_path_templates.MATERIAL,
        plot_design_classification.MATERIAL, plot_design_resources.MATERIAL,
        plot_design_promise_workflow.MATERIAL, plot_design_plot_mechanisms.MATERIAL,
        plot_design_narrative_structures.MATERIAL,
        plot_design_type_materials.MATERIAL,
        work_case_application.PLOT_DESIGN_MATERIAL,
        plot_design_type_expression_adaptations.MATERIAL,
        plot_design_type_rules.MATERIAL,
        plot_design_dynamic_network.MATERIAL,
        plot_design_dynamic_network_2.MATERIAL,
        plot_design_dynamic_network_3.MATERIAL,
        plot_design_dynamic_network_4.MATERIAL,
        plot_design_dynamic_network_5.MATERIAL,
        plot_design_dynamic_network_6.MATERIAL,
        plot_design_dynamic_network_7.MATERIAL,
        plot_design_static_network.MATERIAL,
        plot_design_deliberation.MATERIAL,
        plot_design_meaning.MATERIAL,
        plot_design_crafting.MATERIAL,
        plot_design_time.MATERIAL,
        plot_design_social_material.MATERIAL,
        plot_design_anchor_network.MATERIAL,
        plot_design_memory.MATERIAL,
    )),
    'event_design': '\n'.join((
        event_design.MATERIAL, event_design_plot.MATERIAL, event_design_supporting.MATERIAL,
        event_design_progression.MATERIAL, event_design_plot_mechanisms.MATERIAL,
        event_design_type_expression_adaptations.MATERIAL,
        event_design_type_rules.MATERIAL,
        event_design_dynamic_network.MATERIAL,
        event_design_static_network.MATERIAL,
        event_design_anchor_network.MATERIAL,
    )),
    'action_design': '\n'.join((
        action_design.MATERIAL, action_design_plot.MATERIAL, action_design_dialogue.MATERIAL,
        action_design_decisions.MATERIAL, action_design_ethics.MATERIAL, action_design_interaction.MATERIAL, action_design_meaning.MATERIAL, action_design_crafting.MATERIAL,
        action_design_information.MATERIAL, action_design_misalignment.MATERIAL, action_design_costs.MATERIAL,
        action_design_progression.MATERIAL, action_design_resources.MATERIAL,
        action_design_plot_mechanisms.MATERIAL,
        action_design_type_expression_adaptations.MATERIAL,
        action_design_mechanism_adaptations.MATERIAL,
        action_design_type_rules.MATERIAL,
        action_design_dynamic_network.MATERIAL,
        action_design_dynamic_network_2.MATERIAL,
        action_design_dynamic_network_3.MATERIAL,
        action_design_dynamic_network_4.MATERIAL,
        action_design_dynamic_network_5.MATERIAL,
        action_design_static_network.MATERIAL,
        action_design_anchor_network.MATERIAL,
        action_design_anchor_network_2.MATERIAL,
        action_design_anchor_network_3.MATERIAL,
        action_design_deliberation_anchors.MATERIAL,
        action_design_anchor_network_4.MATERIAL,
    )),
    'scene_design': '\n'.join((
        scene_design.MATERIAL, scene_design_structure.MATERIAL, scene_design_viewpoint.MATERIAL,
        scene_design_pacing.MATERIAL, scene_design_planner.MATERIAL, scene_design_narrator.MATERIAL,
        scene_design_opening_timeline.MATERIAL, scene_design_space.MATERIAL, scene_design_disclosure.MATERIAL,
        scene_design_multi_viewpoint.MATERIAL, scene_design_supporting.MATERIAL, scene_design_progression.MATERIAL,
        scene_design_classification.MATERIAL, scene_design_workflow_sources.MATERIAL,
        scene_design_type_expression_adaptations.MATERIAL,
        scene_design_structure_adaptations.MATERIAL,
        scene_design_type_rules.MATERIAL,
        scene_design_dynamic_network.MATERIAL,
        scene_design_static_network.MATERIAL,
        scene_design_anchor_network.MATERIAL,
        scene_design_memory.MATERIAL,
        scene_design_anchor_network_2.MATERIAL,
    )),
    'state_transition': '\n'.join((
        state_transition.MATERIAL, state_transition_world.MATERIAL, state_transition_plot.MATERIAL,
        state_transition_cognition.MATERIAL, state_transition_ethics.MATERIAL, state_transition_interaction.MATERIAL,
        state_transition_continuity.MATERIAL, state_transition_costs.MATERIAL,
        state_transition_supporting.MATERIAL, state_transition_progression.MATERIAL, state_transition_resources.MATERIAL,
        state_transition_type_rules.MATERIAL,
        work_connection_patterns.TRANSITION_MATERIAL,
        state_transition_dynamic_network.MATERIAL,
        state_transition_deliberation.MATERIAL,
        state_transition_meaning.MATERIAL,
        state_transition_crafting.MATERIAL,
        state_transition_memory.MATERIAL,
        state_transition_dynamic_network_2.MATERIAL,
        state_transition_dynamic_network_3.MATERIAL,
        state_transition_static_network.MATERIAL,
        state_transition_anchor_network.MATERIAL,
        state_transition_anchor_network_2.MATERIAL,
        state_transition_anchor_network_3.MATERIAL,
        state_transition_anchor_network_4.MATERIAL,
        state_transition_anchor_network_5.MATERIAL,
    )),
    'state_propagation': '\n'.join((
        state_propagation.MATERIAL, state_propagation_type_rules.MATERIAL,
        work_connection_patterns.PROPAGATION_MATERIAL,
        state_propagation_dynamic_network.MATERIAL,
        state_propagation_deliberation.MATERIAL,
        state_propagation_meaning.MATERIAL,
        state_propagation_crafting.MATERIAL,
        state_propagation_memory.MATERIAL,
        state_propagation_social_material.MATERIAL,
        state_propagation_anchor_network.MATERIAL,
    )),
    'anchor_design': '\n'.join((
        anchor_design.MATERIAL, anchor_design_scene.MATERIAL, anchor_design_viewpoint.MATERIAL,
        anchor_design_atmosphere.MATERIAL, anchor_design_timeline.MATERIAL, anchor_design_multi_viewpoint.MATERIAL,
        anchor_design_dynamic_network.MATERIAL,
        anchor_design_static_network.MATERIAL,
        anchor_design_anchor_network.MATERIAL,
        anchor_design_anchor_network_2.MATERIAL,
        anchor_design_body_emotion.MATERIAL,
        anchor_design_anchor_network_3.MATERIAL,
    )),
    'expression_design': '\n'.join((
        expression_design.MATERIAL, expression_design_world.MATERIAL, expression_design_plot.MATERIAL,
        expression_design_sensory.MATERIAL, expression_design_dialogue.MATERIAL, expression_design_viewpoint.MATERIAL,
        expression_design_reader.MATERIAL, expression_design_cognition.MATERIAL, expression_design_ethics.MATERIAL,
        expression_design_interaction.MATERIAL, expression_design_deliberation.MATERIAL, expression_design_crafting.MATERIAL, expression_design_continuity.MATERIAL,
        expression_design_narrator.MATERIAL, expression_design_atmosphere.MATERIAL, expression_design_symbolism.MATERIAL,
        expression_design_timeline.MATERIAL, expression_design_space.MATERIAL, expression_design_disclosure.MATERIAL,
        expression_design_misalignment.MATERIAL, expression_design_costs.MATERIAL, expression_design_identification.MATERIAL,
        expression_design_multi_viewpoint.MATERIAL, expression_design_supporting.MATERIAL,
        expression_design_progression.MATERIAL, expression_design_reader_engagement.MATERIAL,
        expression_design_classification.MATERIAL, expression_design_resources.MATERIAL,
        expression_design_application.MATERIAL,
        expression_design_type_styles.MATERIAL, expression_design_type_tones.MATERIAL,
        expression_design_type_expression_adaptations.MATERIAL,
        expression_design_age_adaptations.MATERIAL,
        expression_design_tone_adaptations.MATERIAL,
        expression_design_type_choices.MATERIAL,
        work_case_application.EXPRESSION_MATERIAL,
        expression_design_type_rules.MATERIAL,
        expression_design_dynamic_network.MATERIAL,
        expression_design_dynamic_network_2.MATERIAL,
        expression_design_dynamic_network_3.MATERIAL,
        expression_design_static_network.MATERIAL,
        expression_design_anchor_network.MATERIAL,
        expression_design_anchor_network_2.MATERIAL,
        expression_design_anchor_network_3.MATERIAL,
        expression_design_anchor_network_4.MATERIAL,
        expression_design_anchor_network_5.MATERIAL,
    )),
    'bind_scope': '\n'.join((
        bind_scope_workflow.MATERIAL, bind_scope_selection.MATERIAL, bind_scope_templates.MATERIAL,
        bind_scope_task_mapping.MATERIAL, bind_scope_application.MATERIAL,
        bind_scope_source_tags.MATERIAL,
        bind_scope_type_rules.MATERIAL,
        bind_scope_dynamic_network.MATERIAL,
    )),
}

for _stage in STAGE_MATERIALS:
    if _type_connection_text := type_connections.step_instructions(_stage):
        STAGE_MATERIALS[_stage] += '\n\n' + _type_connection_text

DEFAULT_STAGE_MATERIALS = dict(STAGE_MATERIALS)

SCHEMAS={
 'type_selection':'selection:[{id,label:本项目所选类型,basis:原义或作者需求依据}],concepts:[{id,label,type_refs:[selection.id],activation_basis:在项目中为何激活}],boundaries:[边界]；不凭名称补造来源定义',
 'type_adaptation':'adaptations:[{id,type_refs:[实际已选类型id],parameters:{参数:具体值},limits:[限制]}],focuses:[{id,concept:已激活concept.id,from_focus,to_focus,application:实际关注重点设计}],boundaries:[非保证边界]；组合、连接与表达适配只限定已选类型，概念触发不得变成实体状态变化',
 'world_design':'members:[{key,kind:world,body:{title,rule,limits}}],limitations:[限制],unknowns:[待作者确认事项]',
 'character_design':'members:[{key,kind:character,body:{name,role,want,visibility:public或holders或author_only}}],states:[{entity:key,state:{属性:前值},status:candidate}],capabilities:[{entity:人物key,can_act:true或false,abilities:[已有或明确提议的项目能力],basis:人设或行为依据,limits:[限制]}]；沿用approved_cards时不重建同ID；私密信息另置author_only卡',
 'static_relations':'relations:[{id,source:实际实体key,target:实际实体key,relation,condition}],requirements:[{id,source_id:本步方法ID,target_stage:后续阶段,constraint:方法给下游的设计要求,project_refs:[member:key或type:selection.id或brief]}]；读者情绪等方法关系转成设计约束，不虚构书内读者实体；不适用时空数组',
 'plot_design':'directions:[{title,conflict,consequence,reader_promise,protagonist_want,resistance,choice,cost,ending_direction}],members:[{key,kind:plot或promise或chapter或volume,body}],reader_plan:[信息顺序与情绪变化],promise_plan:[埋设、预期、回收安排],event_nodes:[{id,actors:[人物key],goal,setting,obstacle,completion_condition,status:planned}]；book给2至3个方向，细化只围绕所选父方向给1个实际设计，另起方向必须另建细化方案',
 'event_design':'candidates:[{id,source_ids:[本步资料ID或空数组表示纯项目设计],predecessor:plot.event_nodes.id,event:后继事件设计,actors:[实际人物key],completion_gate:原样采用前事件completion_condition,status:conditional_candidate}]；前事件未完成时保留条件预案，不假称事实；本阶段不生成场景卡',
 'action_design':'candidates:[{id,source_ids:[本步资料ID或空数组],event:上游event_node或event_candidate.id,actor:实际人物key,action:完整行动选择,steps:[{object,action,obstacle,response,result}],requires:[人物capabilities中已有的最低能力],cost,limits:[限制],status:candidate}],waiting:[{source_id,missing:[缺失前置],reason}]；人物必须可行动，先按资料设计具体动作再供场景选择',
 'scene_design':'members:[{key,kind:scene,body:{title,goal,pov:实际人物key,characters:[key],character_goals:{key:目标},entering_state,conflict,choice:所选动作的action原文,planned_result,allowed_disclosure}}],chapters:[{index:正整数,card:上游chapter成员key或null,scenes:[{card:场景key,index:正整数,story_order:正整数}]}],events:[{id,scene:场景key,entity:实体key,trigger:候选事件,before_state:{属性:前值}}],selected_events:[{scene,event:实际上游event_node或event_candidate.id}],selected_actions:[{scene,action:上游action_candidate.id}]；每场明确选一个事件和一个动作，不能把候选当作已发生',
 'state_transition':'patches:[{scene,choice,planned_result}],transitions:[{scene,entity,event:上游事件id,before_state:与上游完全一致,action:本场具体的外部行动及应对选择,after_state:{属性:事件后的实际值，至少一项不同于前值},cost:实际损失或限制的文字,failure:失败情形及应对,continuity:事件原因及后场如何保留变化}]；先回答事件改变什么、人物怎样应对、付出什么代价、变化怎样延续；没有适用变化则空数组并解释方法不适用',
 'state_propagation':'candidates:[{id,source_ids:[本步资料ID或空数组],root_kind:planned_change或accepted_fact,root_id:上游transition.event或fact:accepted_state索引,source_entity:可行动人物key,target_entity:人物或世界key,external_action,proposed_effect:{属性:候选值},continuity,scene:实际场景key或null,status:conditional_candidate,gates:{require_root_confirmation:true,require_external_action_selection:true,require_continuity_validation:true},activation_condition:根变化确认且外部行动被选择后才考虑的明确条件}],waiting:[{source_id,missing:[缺失前置],reason}]；纯设计预案不自动生成WORLD事实',
 'anchor_design':'beats:[{scene,observer:该场POV,object,action,observable:可见节拍,check:效果判据}],selected_propagations:[{scene,propagation:本场确实采用的上游传播候选id}]；不选的传播保留为后续预案',
 'expression_design':'guidance:[{scene,observable:本场具体动作情绪对白表现,check:实际效果判据}]',
 'bind_scope':'material_bindings:{按binding_contract绑定实际成员},process_bindings:{按binding_contract绑定实际过程},method_guidance:[{scene:实际场景key,source_ids:[已读且已运用的方法ID],observable:本场POV可见行动情绪等表现,check:原义对应效果}]；每项实际方法在适用场景给出可写表现和审稿判据，不改写上游设计；book没有场景时method_guidance为空',
}

FUNCTION_QUERIES={
 'type_selection':('类型本体 读者承诺',),
 'type_adaptation':('类型组合 类型连接','表达适配 候选参数','概念触发 关注重点'),
 'world_design':('世界设定 规则 限制',),
 'character_design':('人物目标 动机 行为','人物能力 关系 初始状态'),
 'static_relations':('稳定关系 关系限制',),
 'plot_design':('剧情结构 因果 选择 后果','读者情绪 信息顺序','伏笔 埋设 回收'),
 'event_design':('事件候选 前一事件 完成条件','剧情因果 后继事件'),
 'action_design':('行动候选 能力 限制','动作 对象 障碍 应对 结果'),
 'scene_design':('场景 目标 冲突 阻碍','视角 知情 披露','时间线 场景'),
 'state_transition':('状态变化 外部行动 连续性','动作 阻碍 应对 代价'),
 'state_propagation':('状态传播 变化确认 外部选择',),
 'anchor_design':('锚点 可见动作 对象 节拍',),
 'expression_design':('动作描写 具体表现','情绪描写 表现','对白 文风 叙述'),
 'bind_scope':('资料筛选 实际参数 检验点',),
}

# Non-schema providers receive the same explicit transport fields as Ollama.
SCHEMAS['plot_design']+='''
reader_plan每项严格为{id,event:event_nodes实际id,order:从1连续排列的整数,information,before_emotion,after_emotion,trigger,intended_effect,check}；不是人物情绪代替读者体验。
promise_plan每项严格为{id,promise:本步或已批准promise卡key,plant_event:event_nodes实际id,payoff_event:已设计event_nodes.id或null,plant_chapter:正整数,payoff_chapter:正整数或null,payoff_window:null或{min_offset:非负整数,max_offset:非负整数},setup:与promise卡完全一致,expected_meaning,payoff:与promise卡完全一致,check}；没有确定的远期事件/章节填null，原文明确的回收窗口须保留，不补原文缺失的列举成员。
static_bindings可选数组，每项严格为{id,source_id:已读静态方法ID,source:实际项目key,target:实际项目key,relation,condition}。用于上一步等待剧情端点的关系；在本步真实promise/plot产物建好后绑定，并用_uses引用relation:id。没有实际端点时不得造人物/世界替代。'''
SCHEMAS['anchor_design']+='''
使用锚点资料的beat另含action_ref:本场selected_actions的实际action.id,step_index:该动作steps内从0开始的整数,timing:before/during/after之一,trigger_basis:实际输入如何满足原文触发条件；不能只提锚点名称或绑定无关动作。'''


def _admission(desk: SourceDesk, source: dict, stage: str, package: dict, *,
               type_selection: dict | None=None) -> tuple[dict | None, bool]:
    review=desk.binding_review(source,stage,package['scope'])
    if review:
        return review, True
    context={'scope':package['scope'],'current_source_set':package.get('current_source_set'),
             'binding_reviews':desk.binding_reviews,'type_selection':type_selection or {}}
    return None, allows_stage_candidate(source,stage,context)


def _stage_search(desk: SourceDesk,stage: str,query: str,cursor: int=0,*,trace: dict | None=None) -> dict:
    profiles={r['profile'] for r in desk.rows if stage in route_method(r)['stages']}
    result=desk.search(query,cursor=cursor,limit=40,profiles=profiles)
    result['items']=[row for row in result['items'] if stage in route_method(row)['stages']]
    if trace is not None:trace['queries'].append({'query':query,'cursor':cursor,
        'returned':[{'id':r['id'],'key':r['key'],'sha256':r['sha256']} for r in result['items']]})
    return result


def output_contract(stage: str,products: dict,sources: list[dict]) -> dict:
    """A transport shape, never a source of invented story content."""
    shape={key:([] if key not in ('material_bindings','process_bindings') else {}) for key in sorted(FIELDS[stage])}
    shape['_uses']=[]
    shape['_criteria']=[]
    if stage=='state_transition':
        events=products['scene_design']['products']['events']
        if events:
            event=events[0];scene=event['scene']
            shape['patches']=[{'scene':scene,'choice':'<填写具体行动选择>','planned_result':'<填写本场候选结果>'}]
            shape['transitions']=[{'scene':scene,'entity':event['entity'],'event':event['id'],
                'before_state':event['before_state'],'action':'<填写因果明确的外部行动和应对>',
                'after_state':{key:'<填写事件后实际值，至少一项改变，其余可保留>' for key in event['before_state']},
                'cost':'<填写本项目实际损失、麻烦或行动限制的文字>',
                'failure':'<填写失败条件和处理>','continuity':'<填写事件到后续状态的连续性检查>'}]
            shape['_uses']=[{'source_id':row['source']['id'],'operation':'<填写怎样按原文判据执行本步方法>',
                             'output_refs':['scene:'+scene]} for row in sources]
    return {'stage':stage,'products':shape}


def model_semantics(contract: dict) -> dict:
    return {**{k:contract[k] for k in ('policy','source_id','sha256','disposition','source_issues')},
        'obligations':[{k:r[k] for k in ('id','kind','locator','value','check_mode')} for r in contract['obligations']],
        'application_required':bool(contract.get('application_guidance'))}


def retrieval_need(stage: str,package: dict,products: dict) -> str:
    cues=[package['brief']['text'],package['brief']['constraints']]
    fields={'title','name','want','goal','conflict','choice','planned_result','voice','rule','limits',
            'trigger','information','expectation','emotion','setup','payoff','observable','action','condition','relation'}
    def visit(value: object,parent: str='') -> None:
        if isinstance(value,dict):
            for key,item in value.items():
                if key.startswith('_'):continue
                if key in fields and isinstance(item,str):cues.append(item[:120])
                elif isinstance(item,(dict,list)):visit(item,key)
        elif isinstance(value,list):
            for item in value[:8]:
                if isinstance(item,str) and parent in {'selection','boundaries','limitations','reader_plan','promise_plan'}:
                    cues.append(item[:120])
                elif isinstance(item,(dict,list)):visit(item,parent)
    required=list(products) if stage=='bind_scope' else REQUIRES[stage]
    for name in required:
        if name in products:visit(products[name]['products'])
    return ' '.join(cues)[:2200]


def _sources(desk: SourceDesk,stage: str,package: dict,products: dict,studied_sources: list[dict] | None=None,
             *,reviewed_only: bool=False,deferrals: list | None=None,trace: dict | None=None) -> list[dict]:
    type_selection=products.get('type_selection',{}).get('products')
    def usable(source: dict) -> bool:
        if not reviewed_only:return source['use_mode']=='project_method'
        if _admission(desk,source,stage,package,type_selection=type_selection)[1]:return True
        if deferrals is not None and source['source']['id'] not in {r['source']['id'] for r in deferrals}:
            known=desk.binding_review(source)
            status='waiting_for_inputs' if known and any(u['stage']==stage for u in known['uses']) else 'other_step' if known else 'needs_review'
            reason=('本用途已核，但当前范围缺少该用途要求的章场产物' if status=='waiting_for_inputs' else
                '已有用途审核用于另一步，本步不执行' if status=='other_step' else
                '候选检索不构成用途审核；本原文版本在本步骤的用途、前置、产物及检验依据尚待核')
            deferrals.append({'source':source['source'],'candidate_stage':stage,'status':status,'reason':reason})
        return False
    # Mandatory source commitments are not silently truncated by a top-k cap.
    ids=[row['source']['id'] for row in package.get('materials',[])
         if row['request']['disposition']=='required' and (desk.binding_review(desk.read(row['source']['id']),stage,
             package['scope']) is not None if reviewed_only else
             stage in route_method({**row['source'],'profile':row['profile']})['stages'])]
    ids=list(dict.fromkeys([*ids,*deferred_source_ids(desk,stage,products,studied_sources or [])]))
    demand=retrieval_need(stage,package,products)
    candidates=_stage_search(desk,stage,demand,trace=trace)['items']
    template=next((key for key,value in TEMPLATE_STAGES.items() if value==stage),None)
    if template:candidates=_stage_search(desk,stage,template,trace=trace)['items']+candidates
    brief_text = (str(package.get('brief', {}).get('text', '')) + ' '
                  + str(package.get('brief', {}).get('constraints', ''))).casefold()
    single_pov = (any(w in brief_text for w in ('单视角', '单一视角', '固定视角', '受限第三人称', '第三人称有限', '第一人称'))
                  and not any(w in brief_text for w in ('多视角', '切换视角', '视角切换', '视角轮换', '双视角', '群像', '配角pov', '配角视角')))
    stage_has_default = (package.get('current_source_set') is True
                         and STAGE_MATERIALS.get(stage) == DEFAULT_STAGE_MATERIALS.get(stage))
    if stage_has_default:
        from nw.materials.stage_input import extract_step_keys
        in_stage_keys = extract_step_keys(DEFAULT_STAGE_MATERIALS.get(stage, ''))
        conn_recs = type_connections.records() if stage in type_connections.STEPS else {}
    else:
        in_stage_keys = set()
        conn_recs = {}

    def auto_fit(source: dict) -> bool:
        skey = source['source'].get('key') or ''
        if single_pov and (skey.startswith(('120.', '板块120', '126.11_多视角', '板块59 视角规则#配角POV', '板块92 视角规则检查#配角POV'))
                           or skey in ('STRUCTURE_MULTILINE', 'STRUCTURE_VIEWPOINT_ROTATION', 'STRUCTURE_MOSAIC', 'STRUCTURE_ENSEMBLE')):
            return False
        if skey.startswith('SUB_QINGXIAOSHUO_') and '轻小说' not in brief_text and '二次元' not in brief_text:
            return False
        if stage_has_default and skey and skey not in in_stage_keys:
            conn_entry = conn_recs.get(skey)
            if conn_entry is None or conn_entry[0] != stage:
                return False
        return True

    # A bounded initial working set; the model can search/read more at THIS step.
    selected_count=0
    for row in candidates:
        source=desk.read(row['id'])
        if usable(source) and auto_fit(source):
            if row['id'] not in ids:ids.append(row['id'])
            selected_count+=1
            if selected_count==2:break
    # Story-specific nouns seldom occur in method manuals. Search the actual
    # function of THIS step as well, without asking the model to read a library.
    for query in FUNCTION_QUERIES[stage]:
        cursor=0;selected=False
        for _ in range(3):
            page=_stage_search(desk,stage,query,cursor,trace=trace)
            for row in page['items']:
                source=desk.read(row['id'])
                if usable(source) and auto_fit(source):
                    if row['id'] not in ids:ids.append(row['id'])
                    selected=True;break
            if selected or page['next_cursor'] is None:break
            cursor=page['next_cursor']
    result=[source for ident in ids if usable(source:=desk.read(ident))]
    if trace is not None:trace['offered']=[s['source'] for s in result]
    return result


def _requests(value: dict,stage: str,readable: set[str] | None=None) -> None:
    require(set(value)=={'stage','requests'} and value['stage']==stage
            and isinstance(value['requests'],list) and 1<=len(value['requests'])<=6,'invalid step lookup')
    for row in value['requests']:
        require(isinstance(row,dict) and row.get('action') in ('search','read'),'unknown step lookup action')
        if row['action']=='search':
            require(set(row)<= {'action','query','cursor'} and isinstance(row.get('query'),str)
                    and bool(row['query'].strip()) and type(row.get('cursor',0)) is int
                    and row.get('cursor',0)>=0,'invalid step search')
        else:
            require(set(row)=={'action','id'} and isinstance(row['id'],str),'invalid step read')
            require(readable is None or row['id'] in readable,'read is outside the current step source IDs')


def _perform_stage(store: Store,request: TaskRequest,package: dict,provider: LLMProvider,config: Config,
                   desk: SourceDesk,stage: str,products: dict,context: dict,retry_failed: bool,
                   verify: Callable | None,max_rounds: int,index: int,*,studied_sources: list[dict] | None=None,
                   governance: dict | None=None) -> tuple[dict,list[dict],list[dict]]:
    from nw.materials.work_session import _study_call,model_source
    from nw.materials.step_guard import build_continuity_ledger, build_joint_material_plan
    stage_config, stage_provider = resolve_stage_runtime(config, provider, stage)
    state=readiness(stage,products,package['scope'])
    if state['missing']:raise ValueError('MATERIAL_WAITING_INPUTS: '+','.join(state['missing']))
    from nw.materials.semantic_handoff import input_stages,handoffs_for
    screening=context.get('dynamic_screening')
    screen_scene=bool(screening) and (stage=='scene_design' or 'scene_design' in products)
    deps=input_stages(stage,products,dynamic_screening=bool(screening))
    inputs={key:{'ref':product_ref(products[key]),'products':products[key]['products']} for key in deps}
    deferred=[]
    prompt = STEP_PROMPT + '\n' + STAGE_INSTRUCTIONS.get(stage, '')
    material = package.get('stage_materials', {}).get(stage, '')
    chapter_handoff = package.get('chapter_handoff') if stage == 'plot_design' else None
    handoff_instruction = '\n' + plot_design_chapters.CHAPTER_HANDOFF if chapter_handoff is not None else ''
    chapter_summary = package.get('chapter_summary') if chapter_handoff is not None else None
    if chapter_summary is not None:
        handoff_instruction += '\n' + plot_design_chapters.CHAPTER_SUMMARY
    chapter_reviews = package.get('chapter_reviews') if chapter_handoff is not None else None
    if chapter_reviews:
        handoff_instruction += '\n' + plot_design_chapters.CHAPTER_REVIEWS
    selection={'policy':'task-block-subitem-selection-v1','before_stage':stage,
        'function':{'stage':stage,'task':retrieval_need(stage,package,products)},
        'upstream':[product_ref(products[n]) for n in deps],
        'control_review_sha256':context.get('retrieval_control',{}).get('review',{}).get('sha256'),
        'queries':[],'offered':[],'selected':[]}
    sources=_sources(desk,stage,package,products,studied_sources,reviewed_only=True,deferrals=deferred,trace=selection)
    responses=[];offered=set();calls=[];read_full=set();readings={}
    for turn in range(max_rounds):
        contracts=[desk.semantic_contract(source) for source in sources]
        reviews={s['source']['id']:review for s in sources
                 if (review:=desk.binding_review(s,stage,package['scope'])) is not None}
        stage_context={**context,'require_semantics':True,'semantic_contracts':contracts,
            'binding_reviews':{**context.get('binding_reviews',{}),**reviews},
            'brief':package['brief'],'allowed_input_stages':deps,
            'accepted_state':visible_facts(stage,products,context),
            'method_sources':[*(studied_sources or []),*sources]}
        payload={'policy':POLICY,'stage':stage,'scope':package['scope'],
            'mode':'execute' if read_full else 'read_or_execute',
            'function_queries':list(FUNCTION_QUERIES[stage]),
            'dependency_source_ids':deferred_source_ids(desk,stage,products,studied_sources or []),
            'brief':package['brief'],
            'retrieval_need':retrieval_need(stage,package,products),
            'demand':' '.join((package['brief']['text'],package['brief']['constraints'])),
            'inputs':inputs,'sources':[model_source(s,stage=stage,full_text=s['source']['id'] in read_full,
                semantics=next(c for c in contracts if c['source_id']==s['source']['id'])) for s in sources],
            'source_contracts':[model_semantics(c) for c in contracts],
            'semantic_requirements':handoffs_for(stage,products),
            'source_use_reviews':[model_review(reviews[c['source_id']],c,stage)
                for c in contracts if c['source_id'] in reviews],
            'deferred_source_reviews':deferred,
            'source_selection':selection,
            'readable_source_ids':sorted(offered|{s['source']['id'] for s in sources}),
            'responses':responses,'output_schema':SCHEMAS[stage],
            'method_requirements':requirements_for(stage,products),
            'approved_cards':context['approved_cards'],'parent':package.get('parent')}
        if (continuity_ledger := build_continuity_ledger(stage, products, deps, context)) is not None:
            payload['continuity_ledger'] = continuity_ledger
        if (joint_plan := build_joint_material_plan(stage, sources)) is not None:
            payload['joint_material_plan'] = joint_plan
        if chapter_handoff is not None:
            payload['chapter_handoff'] = chapter_handoff
        if chapter_summary is not None:
            payload['chapter_summary'] = chapter_summary
        if chapter_reviews:
            payload['chapter_reviews'] = chapter_reviews
        suffix = handoff_instruction
        if stage == 'type_adaptation' and governance and context.get('dynamic_reference_checks'):
            suffix += '\n' + type_adaptation_combination_review.DYNAMIC_REFERENCE_USE
        if screen_scene:
            payload['dynamic_filter']={key:screening[key] for key in ('filter_id','source_ref','limits')}
            suffix += '\n' + bind_scope_type_rules.DYNAMIC_CANDIDATE_USE
            if stage=='scene_design':
                suffix += '\n' + scene_design_type_rules.INFORMATION_REVEAL_USE
        if stage=='state_propagation' and screen_scene:
            payload['dynamic_filter']['branch_head']=package.get('branch_head')
            suffix+='\n'+state_propagation_type_rules.DYNAMIC_FILTER_INPUTS
        source_scope = package.get('type_source_scope_enabled', False)
        if source_scope and stage == 'plot_design':
            suffix += '\n' + plot_design_type_rules.FORESHADOWING_USE
        if source_scope and stage == 'scene_design':
            suffix += '\n' + scene_design_type_rules.FORESHADOWING_DISCLOSURE_USE
        if stage in ('type_selection', 'type_adaptation'):
            from nw.materials.type_sources import mapping_evidence, ontology_name_evidence, selection_source_refs

            type_sources = [*sources, *(source for source, _ in readings.values())]
            prior_choice = products['type_selection'] if stage == 'type_adaptation' else None
            chosen_sources = selection_source_refs(prior_choice) if prior_choice else []
            if stage == 'type_selection' and package.get('type_hierarchy_enabled'):
                from nw.materials.type_hierarchy import selection_hierarchy

                hierarchy = selection_hierarchy(desk.workspace, type_sources, exact_sources=source_scope)
                if hierarchy:
                    payload['type_hierarchy'] = hierarchy
                    instruction = (type_selection_genres.SCOPED_HIERARCHY_USE if source_scope
                                   else type_selection_genres.HIERARCHY_USE)
                    suffix += '\n' + instruction
            if package.get('type_name_evidence_enabled'):
                chosen_terms = []
                if prior_choice:
                    chosen = prior_choice['products']
                    chosen_terms = [entry[field] for kind in ('selection', 'concepts') for entry in chosen[kind]
                                    for field in ('id', 'label')]
                labels = '' if stage == 'type_adaptation' else payload['demand']
                if names := ontology_name_evidence(desk.workspace, labels, selected_terms=chosen_terms,
                        selected_sources=chosen_sources, related_mechanisms=type_selection_ontology.RELATED_MECHANISMS):
                    payload['type_name_evidence'] = names
                    instruction = (type_adaptation_type_rules.NAME_EVIDENCE_USE if prior_choice
                                   else type_selection_ontology.NAME_EVIDENCE_USE)
                    suffix += '\n' + instruction
            if source_scope:
                refs = [source['source'] for source in type_sources
                        if source['source']['profile'] in ('type_identity', 'type_expression')]
                refs.extend(chosen_sources)
                if evidence := mapping_evidence(desk.workspace, refs, desk.by_id):
                    payload['type_source_mappings'] = evidence
                    suffix += '\n' + type_selection_type_rules.SOURCE_MAPPING_USE
        if readings:
            payload['source_readings']=[
                {**reading, 'source':model_source(source,stage=stage,full_text=True,semantics=desk.semantic_contract(source))}
                for source,reading in readings.values()]
        if governance:
            payload['governance']={'contract_fingerprint':governance['contract']['fingerprint'],
                'configuration_required':stage=='type_selection',
                'instruction':'类型选择用_governance.project_config逐一归入genre_ids/mechanism_ids/structure_ids/style_ids/tone_ids；只填本步selection的实际ID。规则检查会在本步、重开及采用前重跑，不能自行签署作者/独立评审。'}
        if payload['method_requirements']:
            payload['method_requirement_sources']=[model_source(s,stage=stage,full_text=True,semantics=desk.semantic_contract(s))
                for ident in sorted({r['source_id'] for r in payload['method_requirements']})
                for s in [desk.read(ident)]]
        if payload['semantic_requirements']:
            payload['semantic_requirement_sources']=[model_source(s,stage=stage,full_text=True,semantics=desk.semantic_contract(s))
                for ident in sorted({r['source_id'] for r in payload['semantic_requirements']})
                for s in [desk.read(ident)]]
        if stage_provider.name!='ollama':payload['output_contract']=output_contract(stage,products,sources)
        inherited=next((row for row in package.get('parent_material_work',{}).get('stages',[]) if row['stage']==stage),None)
        if inherited:
            payload['inherited_stage']={'ref':product_ref(inherited),'products':inherited['products'],
                'authority':'author_selected_parent_design_preserve_unless_explicit_replan'}
        if stage in ('character_design','scene_design','state_transition','state_propagation'):
            from nw.materials.phase_contract import entity_ids
            entities=entity_ids(products,context)
            payload['accepted_state']=stage_context['accepted_state']
            if stage=='state_propagation':payload['accepted_changes']=package.get('accepted_changes',[])
        if stage=='bind_scope':
            from nw.materials.binding import material_prompt
            from nw.materials.stage_input import model_material
            payload['binding_contract']=material_prompt(package.get('materials',[]),book=package['scope']=='book',
                                                        deferrals=package.get('material_deferrals'))
            payload['binding_sources']=[model_material(r,book=package['scope']=='book') for r in package.get('materials',[])]
            payload['writing_source_ids']=sorted(writing_sources(products,[]))
        def validate(value: dict) -> None:
            if 'requests' in value:
                require(payload['mode']!='execute','requested method originals are delivered; actual step products are required')
                _requests(value,stage,set(payload['readable_source_ids']))
            else:
                validate_phase(value,stage,products,sources,stage_context)
                if screen_scene:
                    from nw.materials.dynamic_screening import require_scene_limits,screening_report

                    used={row['source_id'] for row in value['products']['_uses']}
                    current={'products':value['products'],'source_selection':{
                        'selected':[s['source'] for s in sources if s['source']['id'] in used]}}
                    require_scene_limits(screening_report({**products,stage:current},screening))
                from nw.materials.governance_runtime import check_stage_governance
                report=check_stage_governance(governance,stage,value['products'],products,sources,context)
                if report and report['status']=='failed':
                    bad=[r['rule_id'] for r in report['checks'] if r['status']=='failed']
                    raise ValueError('MATERIAL_GOVERNANCE: '+','.join(dict.fromkeys(bad)))
        raw,receipt=_study_call(store,request,stage_config,stage_provider,index*max_rounds+turn,payload,sources,
            desk,retry_failed,verify,prompt=prompt,validator=validate,
            version='source-step-v4',read_only_sources=[source for source,_ in readings.values()],
            step_material=material,prompt_suffix=suffix)
        calls.append(receipt)
        if 'products' in raw:
            from nw.materials.governance_runtime import check_stage_governance,freeze_report
            selection['offered']=[s['source'] for s in sources]
            used={u['source_id'] for u in raw['products']['_uses']}
            selection['selected']=[s['source'] for s in sources if s['source']['id'] in used]
            record={'stage':stage,'task_id':receipt['task_id'],'products':raw['products'],
                    'sha256':content_sha256(raw['products']),'inputs':[product_ref(products[k]) for k in deps],
                    'semantic_contracts':contracts,
                    'binding_reviews':reviews,'deferred_sources':deferred,
                    'source_selection':selection,
                    'source_ids':[s['source']['id'] for s in sources]}
            if screening and stage=='bind_scope':
                from nw.materials.dynamic_screening import screening_report

                record['dynamic_screening']=screening_report({**products,stage:record},screening)
            if governance:record['governance']=freeze_report(check_stage_governance(
                governance,stage,raw['products'],products,sources,context))
            return record,sources,calls
        responses=[]
        for action in raw['requests']:
            if action['action']=='search':
                found=_stage_search(desk,stage,action['query'],action.get('cursor',0),trace=selection);responses.append(found)
                offered.update(row['id'] for row in found['items'])
            else:
                require(action['id'] in set(payload['readable_source_ids']),'read was not requested from this step search results')
                source=desk.read(action['id'])
                review, admitted=_admission(desk,source,stage,package,
                    type_selection=products.get('type_selection',{}).get('products'))
                require(stage in route_method(source)['stages'] or review is not None,
                        'method belongs to a different step')
                if not admitted:
                    ident=source['source']['id']
                    if ident not in readings:
                        entry=next((item for item in deferred if item['source']['id']==ident),None)
                        if entry is None:
                            entry={'source':source['source'],'candidate_stage':stage,'status':'needs_review',
                                'reason':'当前步骤的原义用途还需核定。'}
                            deferred.append(entry)
                        reading={'status':entry['status'],'reason':entry['reason'],'execution_admitted':False,
                                 'complete_original_delivered':True}
                        readings[ident]=(source,reading)
                        selection.setdefault('read',[]).append({'source':source['source'],**reading})
                    responses.append({'read':ident,**readings[ident][1]})
                    continue
                if action['id'] not in {s['source']['id'] for s in sources}:sources.append(source)
                read_full.add(action['id'])
                reading={'read':action['id'],'use_mode':source['use_mode'],'execution_admitted':True,
                         'complete_original_delivered':True}
                selection.setdefault('read',[]).append({'source':source['source'],**reading})
                responses.append(reading)
    raise ValueError('MATERIAL_STAGE: '+stage+' lookup budget exhausted before producing actual products')


def drive_phases(store: Store,request: TaskRequest,package: dict,provider: LLMProvider,config: Config,*,
                 retry_failed: bool=False,verify: Callable | None=None,max_rounds: int=8) -> tuple[TaskRequest,dict]:
    workspace=store.directory.parent
    if not (workspace/'materials/catalog.db').is_file():
        if config.source_driven or package.get('governance_inputs'):
            raise ValueError('MATERIAL_WORK: MATERIAL_CATALOG_REQUIRED: index source materials before novel design')
        return request,package
    desk=SourceDesk(workspace,test_mode=store.test_mode)
    from nw.materials.binding_reviews import POLICY as BINDING_POLICY,verify_session_bindings
    from nw.materials.governance_runtime import load_governance,verify_session_governance
    from nw.materials.source_set import selection_status
    selected=selection_status(workspace)
    if selected:
        package={**package,'current_source_set':selected['sha256']}
    governance=load_governance(workspace)
    if package.get('material_work'):
        session=package['material_work']
        require(session.get('policy')==POLICY,'legacy global study must be redesigned through actual creation steps')
        verify_chain(session);desk.verify(session['sources'])
        verify_session_bindings(session,workspace,test_mode=store.test_mode)
        verify_session_governance(session,workspace);return request,package
    products={};sources={};calls=[]
    context={'scope':package['scope'],'brief':package['brief'],'semantic_policy':SEMANTIC_POLICY,
             'binding_policy':BINDING_POLICY,'binding_test_mode':store.test_mode,'binding_reviews':{},
             'material_source_snapshots':{},
             'approved_cards':package.get('approved_cards',[]),
             'accepted_state':package.get('accepted_state',[]),'accepted_changes':package.get('accepted_changes',[])}
    if selected:
        context['current_source_set']=selected['sha256']
    if package.get('dynamic_reference_checks'):
        context['dynamic_reference_checks'] = True
    if package.get('dynamic_screening_enabled') and package['scope']!='book':
        from nw.materials.dynamic_screening import load_dynamic_screening

        if screening := load_dynamic_screening(workspace):
            context['dynamic_screening']=screening
    controls=[r for r in desk.binding_reviews.values() if any(u['stage']=='retrieval' for u in r['uses'])
              and r['source']['id'] in desk.by_id]
    require(len(controls)<=1,'ambiguous source retrieval control')
    if controls:
        source=desk.read(controls[0]['source']['id'])
        context['retrieval_control']={'source':source,'review':desk.binding_review(source,'retrieval')}
    if package.get('governance_inputs'):
        if governance is None:
            raise ValueError('MATERIAL_GOVERNANCE: exact governance source is absent')
        context['governance_inputs']=package['governance_inputs']
        from nw.materials.governance_runtime import verify_dynamic_registries

        if proof := verify_dynamic_registries(workspace, package['governance_inputs']):
            context['verified_dynamic_rules'] = proof
    from nw.materials.binding_assembly import freeze_required_sources
    freeze_required_sources(desk,package.get('materials',[]),context)
    for index,stage in enumerate(phase_order(package['scope'])):
        record,read,receipts=_perform_stage(store,request,package,provider,config,desk,stage,products,context,
                                          retry_failed,verify,max_rounds,index,studied_sources=list(sources.values()),governance=governance)
        products[stage]=record;sources.update({row['source']['id']:row for row in read});calls.extend(receipts)
        context['binding_reviews'].update(record['binding_reviews'])
    session={'policy':POLICY,'id':'stages:'+request.id,'scope':package['scope'],'context':context,
             'stages':list(products.values()),'sources':list(sources.values()),'calls':calls}
    if governance:session['governance']=governance
    session['semantic_contracts']=list({c['source_id']:c for row in products.values()
        for c in row['semantic_contracts']}.values())
    verify_chain(session);desk.verify(session['sources'])
    session['candidates']=compile_candidates(session)
    package={**package,'material_work':session,'material_mode':'source_driven_staged'}
    output={'scope':package['scope'],'candidate_cards':[{'kind':'plot','body':{'assembly_ref':content_sha256(row)}}
                                                       for row in session['candidates']]}
    messages=[{'role':'system','content':ASSEMBLY_PROMPT},{'role':'user','content':canonical({'output_contract':output})}]
    params,_=prepare_call(store,request.budget_id,provider.name,config.params,messages)
    manifest_id=request.manifest_id+':stages'
    previous,_=read_input_manifest(store,request.manifest_id)
    manifest=replace(InputManifest(**previous),id=manifest_id,
                     settings=model_settings(provider,config.model,params,'story-plan-v3-stages'),
                     context_sha256=content_sha256(package))
    freeze_manifest(store,manifest,package)
    return replace(request,manifest_id=manifest_id,payload={'messages':messages}),package
