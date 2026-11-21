"""Production tasks for reusable methods; classifications are not writing rules."""
from copy import deepcopy

from nw.materials.phase_contract import FIELDS
from nw.materials.phase_routes import EXTERNAL_REQUIRES, ORDER, REQUIRES, phase_order

CAST_OUTPUTS = {'character_design': {'cast_assignments'}, 'plot_design': {'cast_events'},
                'scene_design': {'cast_payoffs'}}
PROGRESS_OUTPUTS = {'plot_design': {'continuations'}, 'scene_design': {'scene_progress'}}
METHOD_FIELDS = {stage: fields | CAST_OUTPUTS.get(stage, set()) | PROGRESS_OUTPUTS.get(stage, set())
                 for stage, fields in FIELDS.items()}

def conditional_outputs(stage: str) -> dict[str, str]:
    conditions = {field: '启用剧情职责分派时' for field in CAST_OUTPUTS.get(stage, ())}
    if stage == 'scene_design':
        conditions['scene_progress'] = '启用章场进展设计时'
    if stage == 'plot_design':
        conditions['continuations'] = '启用章场进展，且有前章审稿核实的遗留事项时'
    return conditions


SCOPES = {'book': '全书', 'volume': '卷', 'chapter': '章', 'scene': '场景'}
STAGES = dict(zip(ORDER, ('类型选择', '类型适配', '世界设计', '人物设计', '静态关系',
    '剧情设计', '事件设计', '行动设计', '场景设计', '状态变化', '状态传播', '锚点设计', '表达设计', '绑定汇总')))
INPUTS = {'brief': '立项需求', 'parent_outline': '已批准的上层大纲',
          'accepted_state': '已接受正文及状态', **STAGES}
CONSUMERS = {**STAGES, 'writer': '正文写作', 'review': '独立审稿', 'acceptance': '范围验收'}
ARTIFACTS = {'stage_product': '步骤产物', 'world': '世界卡', 'character': '人物卡',
    'plot': '剧情卡', 'promise': '伏笔/承诺卡', 'volume': '卷纲', 'chapter': '章纲', 'scene': '场景卡'}
OUTPUT_LABELS = {'selection': '实际类型选择', 'concepts': '类型概念', 'boundaries': '边界',
    'adaptations': '适配方案', 'focuses': '本书侧重', 'members': '具体设计卡',
    'limitations': '规则限制', 'unknowns': '待定事项', 'states': '人物状态',
    'capabilities': '能力与边界', 'relations': '关系设计', 'requirements': '关系使用要求',
    'directions': '剧情方向', 'reader_plan': '读者信息与情绪序列', 'promise_plan': '伏笔与承诺安排',
    'event_nodes': '剧情事件节点', 'candidates': '条件候选', 'waiting': '待补前置',
    'chapters': '章场安排', 'events': '实际场景事件', 'selected_events': '选定事件',
    'selected_actions': '选定行动', 'patches': '状态变更单', 'transitions': '变化依据',
    'beats': '可观察的呈现节拍', 'selected_propagations': '选定传播', 'guidance': '表达指导',
    'material_bindings': '资料到产物的绑定', 'process_bindings': '制作过程绑定',
    'method_guidance': '方法执行要求', 'cast_assignments': '已冻结剧情职责与受派人物',
    'cast_events': '受派职责与具体剧情节点', 'cast_payoffs': '角色职责落实的场景与行动步骤',
    'scene_progress': '本场进展的前因、触发与结果', 'continuations': '前章遗留事项与本章事件'}
MEMBER_KINDS = {'world_design': ('world',), 'character_design': ('character',),
    'plot_design': ('plot', 'promise', 'volume', 'chapter'), 'scene_design': ('scene',)}


def output_artifacts(stage: str, field: str) -> tuple[str, ...]:
    return ('stage_product', *MEMBER_KINDS.get(stage, ())) if field == 'members' else ('stage_product',)

# Each row names an actual production responsibility, not a new genre law.
_ROWS = (
    ('type_choice', '类型选择与边界', '确定本项目采用的类型、读者预期和边界。',
     'type_selection', 'book volume chapter scene', 'brief'),
    ('type_adaptation', '类型组合与适配', '把已选类型及其冲突落实为可执行的适配条件。',
     'type_adaptation', 'book volume chapter scene', 'type_selection'),
    ('world_rules', '世界规则与限制', '明确规则、资源、例外、未知及行动限制。',
     'world_design', 'book volume chapter scene', 'type_selection type_adaptation'),
    ('character_arc', '人物目标与弧光', '明确独立目标、行为边界、变化条件及事件中的选择和代价。',
     'character_design plot_design state_transition', 'book volume chapter scene', 'world_design'),
    ('relationships', '人物关系与势力', '确定真实关系端点、成立条件和后续变化的前置。',
     'static_relations state_propagation', 'book volume chapter scene', 'world_design character_design'),
    ('main_plot', '全书主线与结局兑现', '建立总问题、关键选择、代价、转折及结局兑现的因果关系。',
     'plot_design', 'book', 'type_adaptation world_design character_design static_relations'),
    ('subplot', '支线与主线交汇', '规定支线的独立目标、交汇事件及对主线的实际作用。',
     'plot_design event_design', 'book volume chapter scene', 'plot_design character_design static_relations'),
    ('volume_outline', '分卷目标与转折', '承接全书主线，确定本卷目标、关键事件、转向与交接。',
     'plot_design', 'volume', 'parent_outline accepted_state'),
    ('chapter_outline', '连续章纲与承接', '说明每章承担的目标、选择、后果及相邻章问题的回应。',
     'plot_design scene_design', 'chapter', 'parent_outline accepted_state'),
    ('event_chain', '事件触发与因果', '把剧情节点落实为有前驱、参与者和完成门的事件候选。',
     'event_design', 'volume chapter scene', 'world_design character_design static_relations plot_design'),
    ('action_chain', '行动、阻碍与代价', '定义对象、动作、阻碍、应对、结果及失败或等待条件。',
     'action_design', 'volume chapter scene', 'event_design character_design world_design'),
    ('scene_composition', '场景职责与选择', '落实视角、进入状态、人物目标、冲突、选择与计划结果。',
     'scene_design', 'chapter scene', 'parent_outline event_design action_design'),
    ('state_change', '人物与关系状态变化', '以事件和行动为依据确定实际前后值及变化条件。',
     'state_transition', 'volume chapter scene', 'character_design action_design scene_design'),
    ('state_propagation', '后果与影响传播', '明确多实体影响条件、确认门和不能自动传播的情况。',
     'state_propagation', 'volume chapter scene', 'static_relations state_transition'),
    ('anchors', '可见线索与表现锚点', '把行动、信息和状态落实到观察者可感知的具体表现。',
     'anchor_design', 'volume chapter scene', 'action_design scene_design state_transition state_propagation'),
    ('information', '信息披露与悬念', '规定读者和各人物所知、披露次序、误读及纠正依据。',
     'plot_design scene_design expression_design', 'book volume chapter scene', 'character_design plot_design'),
    ('hook', '钩子与问题接力', '说明设问、利益或危险、当前回应、下一步升级及兑现。',
     'plot_design event_design scene_design expression_design', 'book volume chapter scene', 'plot_design accepted_state'),
    ('foreshadow', '伏笔埋设、提示与回收', '区分埋设、提示、误读、揭示与回收，并保留多处证据。',
     'plot_design scene_design expression_design', 'book volume chapter scene', 'plot_design parent_outline accepted_state'),
    ('pacing', '节奏与情绪序列', '在实际事件和章场序列上设计张弛、情绪触发及转换。',
     'plot_design scene_design anchor_design expression_design', 'book volume chapter scene', 'plot_design parent_outline'),
    ('expression', '叙事、对话与文风', '按场景功能、声线、知情边界和已选结果确定具体呈现。',
     'expression_design', 'volume chapter scene', 'character_design scene_design anchor_design'),
    ('narration', '叙述时序、视角与呈现', '将有原作证据的讲述次序迁移到本场。区分已发生的事、此时谁知道什么、人物怎样理解，以及读者从哪句话看出变化。',
     'expression_design scene_design', 'chapter scene', 'parent_outline world_design character_design plot_design event_design scene_design accepted_state'),
    ('method_binding', '方法交接与核验', '确定方法产物的消费者、执行任务及可回查的检查证据。',
     'bind_scope', 'book volume chapter scene', 'parent_outline accepted_state'),
)

TASKS = {ident: {'id': ident, 'name': name, 'purpose': purpose, 'stages': stages.split(),
    'scopes': scopes.split(), 'input_kinds': inputs.split()} for ident, name, purpose, stages, scopes, inputs in _ROWS}


def method_catalog(*, include_story_outputs: bool = True) -> dict:
    fields = METHOD_FIELDS if include_story_outputs else FIELDS
    labels = set.union(*fields.values())
    stages = [{'id': stage, 'name': STAGES[stage], 'required_stages': list(REQUIRES[stage]),
        'scopes': [scope for scope in SCOPES if stage in phase_order(scope)],
        'output_fields': sorted(fields[stage]),
        **({'conditional_output_fields': conditional_outputs(stage)} if include_story_outputs else {}),
        'consumers': [consumer for consumer in ORDER if stage in REQUIRES[consumer]],
        'note': '绑定读取本范围实际前步；命名交接可追加输入。'} for stage in ORDER]
    tasks = []
    for row in TASKS.values():
        outputs = [{'stage': stage, 'field': field, 'artifact_kinds': output_artifacts(stage, field),
                    'scopes': [scope for scope in row['scopes'] if stage in phase_order(scope)]}
                   for stage in row['stages'] for field in sorted(fields[stage])]
        tasks.append({**deepcopy(row), 'allowed_outputs': outputs})
    return {'schema_version': 1, 'tasks': tasks, 'scopes': SCOPES, 'stages': stages,
        'input_kinds': INPUTS, 'consumers': CONSUMERS, 'artifact_kinds': ARTIFACTS,
        'output_labels': {field: label for field, label in OUTPUT_LABELS.items() if field in labels},
        'output_artifact_kinds': {stage: {field: output_artifacts(stage, field) for field in fields[stage]}
                                  for stage in ORDER},
        'external_requires': {key: list(value) for key, value in EXTERNAL_REQUIRES.items()},
        'required_sections': {'applicability': '适用条件', 'prerequisites': '所需前置',
            'operations': '具体操作', 'outputs': '预期产物', 'downstream': '下游用途',
            'acceptance': '验收方法', 'evidence': '原作证据', 'non_applicability': '不适用情况'},
        'missing_input_policy': 'return_design',
        'runtime_integration': 'project_design_and_review',
        'notes': ['目录是生产需求，不能当作原作拆解或类型写法的完整经验。',
                  '项目启用后按实际类型、任务、前置确认和具体产物执行；方法获批不代表已经用于任何小说。']}
