"""Freeze narrative jobs before deciding who will perform them."""
from nw.materials.book_direction import approved
from nw.materials.template_support import content, require
from nw.task_models import _text


POLICY = 'plot-driven-casting-v1'
FIELDS = {'id', 'slot', 'need_ref', 'need_quote', 'event', 'obstacle', 'action', 'result',
          'reuse_actor', 'reason', 'assessments'}
ACTOR_FIELDS = ('role', 'want', 'scene_function', 'independent_goal', 'background', 'behavior', 'boundaries',
                'relationship', 'ability_cost', 'strength', 'flaw', 'change_conditions', 'core_conflict',
                'need', 'wound')
PLOT_FIELDS = ('goal', 'conflict', 'choice', 'consequence', 'resistance', 'protagonist_want', 'ending_direction',
               'setup', 'payoff', 'turn', 'cost', 'central_question')
BOOK_SCOPE_INSTRUCTION = '全书只列几个候选方向都需要的人物职责，分支独有的演出者等选定方向后设计。'
WORLD_INSTRUCTION = (
    '在本步独立交付下一步的剧情用人需求 cast_demands。先定剧情，不起新角色名字。'
    '逐项选择 cast_plot_sources 的真实前置，从中摘完整的具体句子 need_quote，写好要发生的 event、'
    '阻止进展的 obstacle、此时需要某人完成的可表演的 action 及其可观察的 result。'
    '先让环境、主角或已有角色解决；没有独立职责无需另列，没有需求交空数组。人物独白、拒绝、传递消息及互相影响的选择也可成为实际行动。'
    + BOOK_SCOPE_INSTRUCTION + '本章须从当前方向、章节任务或前章交接推导。'
    '前章引文只证明实际写出的内容。已核验的个人误信或推断属于该人，开放问题只是可供推进的方向。'
    '每项填 id 和 slot；同一人可以兼任的几项都用同一 slot。reuse_actor 填批准人物的 card_id 或 null（确需新增）。'
    'assessments 列 {actor:已批准人物编号,field:其实际的身份/目标/能力限制等字段名,quote:该字段原文证据,reason:'
    '结合当前障碍和行动说明可承担或不可承担的具体条件}。复用要核对所选演员；确需新增，须逐人排除已批准演员，在 reason 交代缺哪项不可替代的条件。'
)
CHARACTER_INSTRUCTION = (
    '为已批准角色使用资料设计本次行动能力时，_uses.output_refs 可指向 capability:该人物card_id；'
    '只依据 frozen_cast_demands 分派。cast_assignments 每项为 {demand:已冻结需求id,actor:新人物key或批准人物card_id}；'
    '每一项都分配，所有新卡都须有已冻结的新建需求。沿用既有人物时保留其卡与个人目标，把本次变化写在新的分派里。'
    '同一 slot 共用同一演员，分别被设计为不同 slot 的不合并。新卡 scene_function 原样使用其所承担的一项 action，'
    'casting.need_ref 和 need_quote 一同沿用该项原文；creation_reason 可解释他自己的身份、目标与这件事为何会在此刻相交。'
)


def world_instruction(context: dict) -> str:
    if approved(context):
        return WORLD_INSTRUCTION.replace(BOOK_SCOPE_INSTRUCTION,
            '全书按已确认方向的剧情前提、主角目标、核心冲突和长线推进方式确定真实用人职责。')
    return WORLD_INSTRUCTION


def roster(context: dict) -> dict:
    return {row['card_id']: row['body'] for row in context.get('approved_cards', ()) if row['kind'] == 'character'}


def completed_direction(parent: dict | None, chapter_handoff: dict) -> bool:
    chapters = (parent or {}).get('chapters', ())
    return bool(chapters) and max(ch['index'] for ch in chapters) <= chapter_handoff.get('chapter', {}).get('index', 0)


def source_card_ids(parent: dict | None, cards: list[dict], chapter_handoff: dict, scope: str = 'chapter') -> list[str]:
    """Choose the approved direction's live outline, excluding chapters already completed."""
    if not parent or completed_direction(parent, chapter_handoff):
        return []
    completed = chapter_handoff.get('chapter', {}).get('index', 0)
    phases = parent.get('material_design', {}).get('process_context', {})
    mapped = phases.get('ids', {})
    several_chapters = scope in ('volume', 'replan')
    next_chapters = {mapped[ch['card']] for ch in phases.get('chapters', ()) if ch.get('card') in mapped
                     and (ch['index'] > completed if several_chapters else ch['index'] == completed + 1)}
    ids = {ref['card_id'] for ref in parent['approvals']} - {parent['root']['card_id']}
    outline = [card for card in cards if card['card_id'] in ids and card['kind'] in ('plot', 'chapter', 'volume', 'promise')]
    chapter_ids = {card['card_id'] for card in outline if card['kind'] == 'chapter'}
    if not phases.get('chapters') and completed == 0 and (several_chapters or len(chapter_ids) == 1):
        next_chapters = chapter_ids
    return sorted({card['card_id'] for card in outline} - (chapter_ids - next_chapters))


def source_options(context: dict) -> dict:
    """Only plot premises may commission a character. A world rule by itself cannot."""
    result = {}
    if direction := approved(context):
        selected = direction['candidate']
        for field in ('premise', 'protagonist', 'goal', 'conflict', 'long_term_drive'):
            if _text(value := selected.get(field)):
                result[f'confirmed-direction:{field}'] = value
    parent = context.get('cast_parent', {})
    for field in PLOT_FIELDS:
        if _text(value := parent.get(field)):
            result['direction:' + field] = value
    for card in context.get('approved_cards', ()):
        if (card['card_id'] not in context.get('cast_source_cards', ())
                or card['kind'] not in ('plot', 'volume', 'chapter', 'promise')):
            continue
        for field in PLOT_FIELDS:
            if _text(value := card['body'].get(field)):
                result[f'approved:{card["card_id"]}:{field}'] = value
    for key, item in context.get('chapter_openings', {}).items():
        if _text(value := item.get('possible_next_pressure')):
            result[key + ':pressure'] = value
    for key, item in context.get('chapter_changes', {}).items():
        if _text(value := item.get('text')):
            result[key + ':change'] = f'{item["holder"]}（{item["claim"]}）关于{item["entity_id"]}的{item["predicate"]}：{value}'
    for index, duty in enumerate(context.get('cast_prior_work', ())):
        for span_index, span in enumerate(duty['evidence']):
            if _text(quote := span.get('quote')):
                result[f'prior-cast:{index}:span:{span_index}'] = quote
    if not result or context.get('scope') == 'book':
        brief = context.get('brief', {})
        if _text(brief.get('text')):
            result['brief:text'] = brief['text']
    if gap := context.get('plot_cast_gap'):
        from nw.materials.cast_gap import sources
        result.update(sources(gap))
    return result


def effective_demands(products: dict, context: dict) -> list[dict]:
    current = {row['id']: row for row in products['world_design']['products']['cast_demands']}
    for row in context.get('plot_cast_gap', {}).get('cast_demands', ()):
        current[row['id']] = row
    return list(current.values())


def validate_demands(rows: object, sources: dict, roster: dict) -> None:
    require(isinstance(rows, list), '须先交付剧情用人需求列表')
    seen = set()
    actions = set()
    owners = {}
    reused = {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == FIELDS
                and all(content(row[k]) for k in FIELDS - {'reuse_actor', 'assessments'}),
                '剧情用人需求须分别交代前置、事件、障碍、行动、可观察结果与选人理由')
        key, slot, actor = row['id'], row['slot'], row['reuse_actor']
        require(key not in seen and row['need_ref'] in sources and row['need_quote'] in sources[row['need_ref']],
                '剧情用人需求重复或没有引用可核对的剧情前置')
        require(row['result'].strip() not in (row['action'].strip(), row['obstacle'].strip()),
                '须写出行动如何改变处境的具体结果')
        action = tuple(row[k].strip() for k in ('event', 'obstacle', 'action', 'result'))
        require((slot, action) not in actions, '同一演出者在同一事件的重复任务须合并')
        actions.add((slot, action))
        seen.add(key)
        require(actor is None or isinstance(actor, str) and actor in roster, '复用对象必须来自已批准人物卡')
        require(slot not in owners or owners[slot] == actor, '同一演员位置被指定了不同的复用安排')
        owners[slot] = actor
        if actor is not None:
            require(actor not in reused or reused[actor] == slot, '同一已批准人物的兼任职责须沿用同一演员位置')
            reused[actor] = slot
        require(isinstance(row['assessments'], list), '选人须核对已有演员的实际条件')
        considered = set()
        for option in row['assessments']:
            require(isinstance(option, dict) and set(option) == {'actor', 'field', 'quote', 'reason'}
                    and all(content(item) for item in option.values()), '已有演员须有当前条件的原文与判断')
            person, field, quote = option['actor'], option['field'], option['quote']
            require(person in roster and person not in considered and field in ACTOR_FIELDS
                    and _text(roster[person].get(field)) and quote in roster[person][field],
                    '已有演员的条件必须可追溯到该人的真实人物卡')
            considered.add(person)
        require((actor is None and considered == roster.keys()) or (actor is not None and actor in considered),
                '新增前须核对现有演员；复用须核对指定演员的条件')


def validate_assignments(value: dict, products: dict, context: dict) -> None:
    needs = {row['id']: row for row in effective_demands(products, context)}
    new = {card['key']: card['body'] for card in value['members']}
    require(isinstance(value.get('cast_assignments'), list), '人物设计须分派已冻结的剧情需求')
    assignments = {}
    slots = {}
    actors = {}
    roles = {}
    for row in value['cast_assignments']:
        require(isinstance(row, dict) and set(row) == {'demand', 'actor'} and all(_text(v) for v in row.values()),
                '每项分派须写真实需求编号与演员编号')
        key, actor = row['demand'], row['actor']
        require(key in needs and key not in assignments, '人物设计自造或重复了上游需求')
        demand = needs[key]
        slot, existing = demand['slot'], demand['reuse_actor']
        require((actor in new if existing is None else actor == existing), '分派偏离上游确定的复用或新建对象')
        require(slots.get(slot, actor) == actor and actors.get(actor, slot) == slot, '兼任或不同人的安排偏离上游剧情')
        slots[slot], actors[actor] = actor, slot
        assignments[key] = actor
        roles.setdefault(actor, []).append(demand)
    require(assignments.keys() == needs.keys() and new.keys() <= roles.keys(),
            '所有用人需求和所有新增人物必须有对应的分派')
    for key, body in new.items():
        profile = body['casting']
        require(any(body['scene_function'] == demand['action'] and profile['need_ref'] == demand['need_ref']
                    and profile['need_quote'] == demand['need_quote'] for demand in roles[key]),
                '新增人物卡须落实本人被分派的具体行动及其同一剧情前置')


def add_schema(stage: str, fields: dict) -> None:
    from nw.materials.phase_schema import TEXT, array, obj, strings
    if stage == 'world_design':
        fields['cast_demands'] = array(obj({**strings(*sorted(FIELDS - {'assessments', 'reuse_actor'})),
            'reuse_actor': {'type': ['string', 'null']},
            'assessments': array(obj({**strings('actor', 'quote', 'reason'), 'field': {'enum': list(ACTOR_FIELDS)}}))}))
    elif stage == 'character_design':
        fields['cast_assignments'] = array(obj(strings('demand', 'actor')))
