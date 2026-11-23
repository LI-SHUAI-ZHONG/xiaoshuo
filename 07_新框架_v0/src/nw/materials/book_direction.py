"""Bind book design stages to the approved short direction."""

from nw.store import Store
from nw.task_models import content_sha256
from nw.tasks import read_input_manifest


STAGE_INSTRUCTIONS = {
    'type_selection': '依据已确认方向解释所选类型怎样服务核心冲突及读者预期。',
    'type_adaptation': '依据核心冲突和长线推进方式落实类型承诺与世界边界。',
    'world_design': '细化会影响主角目标与核心冲突的制度、条件及代价。待核规则仍用本步的未决字段。',
    'character_design': '依据已确认的主角处境、目标和冲突设计人物的判断、选择和行动能力。',
    'static_relations': '依据该方向落实围绕主角目标与阻力成立的人物关系及约束条件。',
    'plot_design': '只提交一项 directions，深化已确认的矛盾和长线推进，写明选择、代价、后果与收束。',
}
SEARCH_FIELDS = {
    'type_selection': ('premise', 'type_fit'),
    'type_adaptation': ('premise', 'type_fit', 'conflict'),
    'world_design': ('world_premise', 'conflict'),
    'character_design': ('protagonist', 'goal', 'conflict'),
    'static_relations': ('protagonist', 'conflict'),
    'plot_design': ('goal', 'conflict', 'long_term_drive'),
}
DIRECTION_FIELDS = {
    'id', 'title', 'premise', 'protagonist', 'goal', 'conflict', 'world_premise', 'long_term_drive', 'type_fit',
}


def approved(context: dict) -> dict | None:
    if 'approved_direction' not in context:
        return None
    row = context['approved_direction']
    if (context.get('scope') != 'book' or not isinstance(row, dict)
            or row.keys() != {'task_id', 'decision_id', 'candidate_id', 'candidate', 'sha256'}
            or not all(isinstance(row[k], str) and row[k].strip() and len(row[k]) <= 160
                       for k in ('task_id', 'decision_id', 'candidate_id'))
            or not isinstance(row['candidate'], dict)):
        raise ValueError('STALE_BOOK_DIRECTION: 已确认全书方向的范围或引用无效')
    candidate = row['candidate']
    if (candidate.get('id') != row['candidate_id']
            or not DIRECTION_FIELDS <= candidate.keys() <= DIRECTION_FIELDS | {'author_fit'}
            or not all(isinstance(key, str) and isinstance(value, str) and 0 < len(value.strip()) <= 500
                       for key, value in candidate.items())
            or sum(map(len, candidate.values())) > 2200
            or content_sha256(candidate) != row['sha256']):
        raise ValueError('STALE_BOOK_DIRECTION: 已确认全书方向的内容与冻结版本不符')
    return row


def stage_input(context: dict, stage: str) -> dict | None:
    return approved(context) if stage in STAGE_INSTRUCTIONS else None


def search_need(context: dict, stage: str) -> list[str]:
    direction = stage_input(context, stage)
    if not direction:
        return []
    return [direction['candidate'][key][:130] for key in SEARCH_FIELDS[stage]
            if key in direction['candidate']]


def stage_instruction(stage: str) -> str:
    return ('approved_direction.candidate 是作者本轮确定的设计前提。沿用其作品前提、主角目标、'
            '核心冲突和长线推进方式，仍按本步资料和已批准事实检验落地条件。'
            '前提是创作约束，故事当前状态仍以输入的已接受事实为准。' + STAGE_INSTRUCTIONS[stage])


def check_receipt(record: dict, context: dict, calls: list[dict]) -> None:
    direction = stage_input(context, record['stage'])
    receipt = record.get('approved_direction_receipt')
    if direction is None:
        if receipt is not None:
            raise ValueError('STALE_BOOK_DIRECTION: 此阶段没有已确认全书方向需要交接')
        return
    original = (record.get('static_relations_basis') or record.get('cast_demand_revision', {}).get('basis')
                or record)
    if (not isinstance(receipt, dict) or receipt not in calls
            or receipt.get('task_id') != original['task_id'] or not receipt.get('manifest_id')):
        raise ValueError('STALE_BOOK_DIRECTION: 制作步骤缺少已确认全书方向的调用记录')


def verify_calls(store: Store, session: dict) -> None:
    direction = approved(session['context'])
    if direction is None:
        return
    calls = session['calls']
    for record in session['stages']:
        check_receipt(record, session['context'], calls)
        if receipt := record.get('approved_direction_receipt'):
            _, saved = read_input_manifest(store, receipt['manifest_id'])
            packet = saved.get('study_input', {})
            if (packet.get('approved_direction') != direction
                    or packet.get('stage') != record['stage'] or packet.get('scope') != 'book'):
                raise ValueError('STALE_BOOK_DIRECTION: 制作调用与已确认全书方向的冻结版本不符')
