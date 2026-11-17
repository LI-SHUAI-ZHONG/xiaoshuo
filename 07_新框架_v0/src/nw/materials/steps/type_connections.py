"""原版《类型连接》在现有创作步骤内的原值和用途。"""
from functools import cache
from importlib.resources import files
import json

from nw.task_models import canonical

FILE_SHA256 = 'e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0'
DATA = files(__package__).joinpath('type_connection_data')
STEPS = ('type_adaptation', 'world_design', 'character_design', 'plot_design', 'event_design', 'scene_design')

ENTITY_USES = {
    'BUILDING': ('world_design', '核对现有建筑为何需要该布置或功能'),
    'CHARACTER': ('character_design', '核对当前人物设计需要关注的外观或功能'),
    'CLOTHING': ('character_design', '核对当前人物相关服饰的外观或用途'),
    'CLUE': ('plot_design', '核对已有线索怎样让读者察觉或用于后续推断'),
    'DOCUMENT': ('plot_design', '核对已有文书在当前信息安排中的可读取内容及用途'),
    'EVENT': ('event_design', '核对当前项目前置所指事件需要关注的功能'),
    'FACTION': ('world_design', '核对现有势力在设定中的范围与作用'),
    'FAMILY': ('character_design', '核对当前人物已知家族在身份或关系设计中的作用'),
    'FOOD': ('world_design', '核对已有食物在生计、生存条件或环境中的用途'),
    'IDENTITY': ('character_design', '核对当前人物的身份呈现和已有身份约束'),
    'INFORMATION': ('plot_design', '核对当下明确的信息用途及披露顺序'),
    'INJURY': ('character_design', '核对已有伤势怎样限制该人物的能力或外观'),
    'ITEM': ('world_design', '核对项目已有物品的用途和使用边界'),
    'LOCATION': ('world_design', '核对现有地点可提供的活动条件或空间限制'),
    'MEDICINE': ('world_design', '核对当前设定里药品的作用、获取和使用条件'),
    'MONEY': ('world_design', '核对项目已确定的货币用途、持有和取得条件'),
    'QUEST': ('plot_design', '核对已有任务的目标、完成条件和现阶段剧情用途'),
    'RESOURCE': ('world_design', '核对已有资源的取得、可用范围和分配边界'),
    'RULE': ('world_design', '核对当前设定规则何时适用、限制哪些对象'),
    'SCENE': ('scene_design', '核对已选事件和行动需要怎样的场景功能或空间呈现'),
    'SECRET': ('plot_design', '核对已有秘密的知情范围和在剧情中的披露条件'),
    'SECT': ('world_design', '核对现有宗门的制度、所属关系和活动范围'),
    'SKILL': ('character_design', '依据人物已有能力核对技能的适用条件和限制'),
    'VEHICLE': ('world_design', '核对现有交通工具的使用条件和空间限制'),
    'WEAPON': ('world_design', '核对项目已有武器的归属、用途和使用条件'),
}
RELATION_USES = {
    'TYPE_SUPPORTS_CONCEPT': ('type_adaptation',
        '按已选类型和项目已激活的概念，从 limitations 核对是否有必要在 focuses 提出关注重点。'),
    'TYPE_SUPPORTS_EVENT': ('event_design',
        '按现有事件需求、事件类型和前事件条件调整取材优先级。原条的事件倾向只作用于检索。'),
    'TYPE_SUPPORTS_INFORMATION': ('plot_design',
        '按已有信息类别和实际知情者，核对关系是否适用于本步的信息关注或信息差安排。'),
    'TYPE_SUPPORTS_RESOURCE': ('world_design',
        '按实际资源类别和用途核对适用范围。取用、短缺和流动以项目设定及后续事件为据。'),
    'TYPE_SUPPORTS_FORESHADOWING': ('plot_design',
        '按已有伏笔需求核对其类别、密度、显隐和连续性风险。落实埋设、披露与回收时沿用现有 promise_plan。'),
    'TYPE_REFINES': ('type_adaptation',
        '核对已有主、子类型与原端点是否相符。子类型的细化范围以同一现用定义内的 parent_id 为据。'),
    'TYPE_COMBINES_WITH': ('type_adaptation',
        '核对现有混合类型和真实组成所选关系。项目确认后再把符合需求的取舍写入适配。'),
    'TYPE_USES_MECHANISM': ('type_adaptation',
        '用两端的类型和机制核对当前需求，按原条件考虑是否使用该机制。'),
    'TYPE_DISTINGUISHED_FROM': ('type_adaptation',
        '沿 limitations 核对这两个已考虑类型在当前项目需求上的具体区别，保留可混合的空间。'),
}
ADAPTATION_RELATIONS = {'TYPE_REFINES', 'TYPE_COMBINES_WITH', 'TYPE_USES_MECHANISM', 'TYPE_COMPATIBLE_WITH'}
COMPATIBILITY_USES = {
    'style': '项目明确需要某种写法时，核对作者所选风格候选的相容条件和场景范围。',
    'tone': '项目明确需要某种语气时，核对所选语气是否适用于当前表达。作者可独立确定语气。',
}
DYNAMIC_USE = (
    '从已选类型、机制、结构和当前阶段需求核对 dynamic_rule_ids 与 candidate_effect_ids 的归属。'
    '按项目已有触发、行动选择、限制和真实前状态确定可用性。空触发、失败及备选分支保持待补。'
    '按 propagation_profile 和 continuity_constraints 向后续步骤交付有依据的条件候选。'
)
STATIC_USE = (
    '按实际已选类型、机制、结构和当前需求核对 static_connection_ids 的两端及关系。'
    '用具体项目对象核对 concept_focus_ids、entity_focus_types 等适用项，风格由作者需求独立选用。'
    '适用的项目限制写入 adaptations 或 boundaries，空的相容和冲突字段保留待核。'
)


def record_id(original: dict) -> str:
    for field in ('connection_id', 'dynamic_combination_id', 'static_combination_id'):
        if field in original:
            return original[field]
    raise ValueError('MATERIAL_TYPE_CONNECTION: missing original record ID')


def record_use(original: dict) -> tuple[str, str]:
    """Decide the owning step from fields in the original table."""
    if 'dynamic_combination_id' in original:
        return 'type_adaptation', DYNAMIC_USE
    if 'static_combination_id' in original:
        return 'type_adaptation', STATIC_USE
    relation = original['connection_type']
    target = original['target_id']
    if relation == 'TYPE_SUPPORTS_ENTITY':
        stage, use = ENTITY_USES[target]
        return stage, f'以当前项目的实际 {target} 需求为据，{use}。沿用原限制，具体对象及属性以项目输入为据。'
    if relation == 'TYPE_COMPATIBLE_WITH':
        return 'type_adaptation', COMPATIBILITY_USES[original['target_kind']]
    return RELATION_USES[relation]


@cache
def blocks() -> tuple[dict, ...]:
    return tuple(json.loads(DATA.joinpath('blocks.json').read_text(encoding='utf-8')))


@cache
def records() -> dict[str, tuple[str, dict]]:
    result = {}
    for stage in STEPS:
        with DATA.joinpath(stage + '.jsonl').open(encoding='utf-8') as body:
            for line in body:
                row = json.loads(line)
                key = record_id(row['original'])
                if key in result:
                    raise ValueError('MATERIAL_TYPE_CONNECTION: duplicate embedded record: ' + key)
                result[key] = stage, row
    return result


def record_step(ref: dict) -> str | None:
    if ref.get('file_sha256') == FILE_SHA256:
        entry = records().get(ref.get('key'))
        if entry:
            return entry[0]
    return None


def allows_adaptation(source: dict, selection: dict) -> bool:
    ref = source['source']
    if record_step(ref) != 'type_adaptation':
        return False
    original = records()[ref['key']][1]['original']
    if original.get('connection_type') not in ADAPTATION_RELATIONS or original['status'] != 'active':
        return False
    selected = {item['id'] for item in selection.get('selection', [])}
    return ({original['source_id'], original['target_id']} <= selected
            and canonical(original) == source['original_text'])


def material_document(name: str) -> object:
    return next(block['original'] for block in blocks() if block['name'] == name)


def apply_step_text(result: dict, source: dict, stage: str) -> None:
    ref = source['source']
    if record_step(ref) != stage:
        return
    _, row = records()[ref['key']]
    original = row['original']
    text = canonical(original)
    if text != source['original_text']:
        raise ValueError('MATERIAL_TYPE_CONNECTION: embedded original differs from current source: ' + ref['key'])
    _, use = record_use(original)
    result['original_text'] = text
    result['type_connection_use'] = {
        'step': stage, 'purpose': use, 'original_id': ref['key'],
        'source_state': source.get('source_state'),
        'scope': '按当前步骤的真实前置核对原文适用条件；原有来源资格、条款、产物及复验规则继续适用。',
    }


STEP_ROLES = {
    'character_design': '人物相关类型连接按当前人物已有外观、身份、服饰、伤势或能力核对适用条件与限制。',
    'event_design': '事件相关类型连接按当前前置所指事件、前事件条件和事件需求核对适用条件与检索倾向。',
}


def step_instructions(stage: str) -> str:
    roles = [block['step_use'] for block in blocks()
             if stage in block['steps'] and 'step_use' in block]
    if stage in STEP_ROLES:
        roles.append(STEP_ROLES[stage])
    if stage in STEPS:
        roles.insert(0, '《类型连接》原条按需要读取。已有明确类型和目标分类时，用原类型 ID、目标分类或条目 ID 查询当步条目。以交付的原条件和限制核对项目实际需求。')
    return '\n'.join(roles)
