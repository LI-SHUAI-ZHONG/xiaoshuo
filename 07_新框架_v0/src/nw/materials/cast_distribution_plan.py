"""Verify how a chapter's cast serves its events against the frozen genre sample."""
from nw.materials.template_support import content, events, references, require, rows
from nw.studio.corpus_catalog import CAST_ROSTER_OPTIONS


POLICY = 'chapter-cast-distribution-v1'
FUNCTIONS = {key: label for key, label in CAST_ROSTER_OPTIONS['function_kind'].items() if key != 'unknown'}
FIELDS = {'chapter', 'band', 'reference_scope', 'appearing_range', 'comparison', 'differences', 'reason', 'people'}
PERSON_FIELDS = {'actor', 'scene', 'event', 'appearance', 'functions', 'basis_quote', 'reason'}
INSTRUCTION = (
    '每章在 cast_distribution_plan 各交一项。根据本项目实际章节 index 和 cast_distribution_context 的批准总章数选择 band；'
    '第一章为 opening（明确仅一章为 unknown），多章按 (index-1)/(总章数-1) 严格小于1/3为 opening、大于2/3为 ending，'
    '其余 middle；无法定位或超过规划用 unknown。优先取该章段的可靠范围 reference_scope=band，无该段则用总体逐章范围 chapter，'
    '再缺则 insufficient。若所定位章段的候选章全待核，也用 insufficient，勿拿其他章段冒充。'
    '单场任务或本轮只给已经存在的章节追加场景（chapters.card=null），reference_scope 为 partial、范围为 null、差异留空，'
    '继续依据实际本场逐人记录取舍，不把局部场次人数与整章比较。'
    'appearing_range 原样抄该范围，无则 null；comparison 是本章人数相对范围的 within/below/above/insufficient。'
    '每章 people 逐人去重，含每一场的视角和在场者。各选一个该人实际在场的 scene 和该场 selected_events.event，以本场该人 '
    'character_goals 的完整原文为 basis_quote；reason 引用这句目标并说明为何此人出面或继续承担。'
    'appearance 以 cast_distribution_context.previous_appearances 已核章稿首次位置和本轮较早章判断 returning，其余 first；'
    '更早章有未核稿而无法证明首次时填 unknown。'
    'functions 为这一章此人实际承担的职责分类（可多项），应与事件及行动相称，其他明确职能可用 other。'
    '逐项比较 appearing、first、returning，以及同一参考段实际提供的 positions.地位 和 functions.职责；'
    'differences 写出所有人数超出参考上下限的上述键名，不含未提供范围的类别；有 unknown 出场史时暂缓首次和再次两项比较。'
    '旧人物卡地位不明时，只登记即使把所有不明人物计入也确实不足、或已经超额的类别。'
    '章 reason 引用本章一项实际人物目标，再引用本章已选上游事件 goal/obstacle/completion_condition/event/completion_gate '
    '中的一个完整原文字段，结合前置说明为什么沿用或偏离这些范围。交接、提供信息、对抗等人数与样本不同可按具体剧情说明；'
    '样本不足也要根据事件选人。不得为凑数改变剧情。')


def chapter_band(index: int, chapter_count: int | None) -> str:
    if index == 1 and chapter_count != 1:
        return 'opening'
    if not chapter_count or chapter_count == 1 or index > chapter_count:
        return 'unknown'
    position = 3 * (index - 1)
    if position < chapter_count - 1:
        return 'opening'
    return 'ending' if position > 2 * (chapter_count - 1) else 'middle'


def planning_context(context: dict) -> dict:
    parent = context.get('cast_distribution_book_plan') or (context.get('length_context') or {}).get('parent_plan') or {}
    return {'chapter_count': parent.get('chapter_count'), 'target_words': parent.get('target_words'),
            'unverified_chapters': context.get('cast_history_unverified_chapters', []),
            'previous_appearances': context.get('cast_verified_first_positions', {}),
            'functions': FUNCTIONS}


def reference_for(sample: dict, band: str, *, partial: bool = False) -> tuple[str, dict]:
    if partial:
        return 'partial', {}
    observed = sample.get('chapter_bands', {}).get(band, {})
    if observed.get('appearing'):
        return 'band', observed
    if sample.get('uncertainty', {}).get('band_chapter_counts', {}).get(band, 0):
        return 'insufficient', {}
    overall = sample.get('chapter_ranges', {})
    return ('chapter', overall) if overall.get('appearing') else ('insufficient', {})


def comparison(number: int, span: dict | list | None) -> str:
    if not span:
        return 'insufficient'
    low, high = (span['min'], span['max']) if isinstance(span, dict) else span
    return 'below' if number < low else 'above' if number > high else 'within'


def differences(reference: dict, people: dict, standings: dict) -> set[str]:
    counts = {'appearing': len(people)}
    if all(person['appearance'] != 'unknown' for person in people.values()):
        for appearance, metric in [('first', 'first'), ('returning', 'returning')]:
            counts[metric] = sum(person['appearance'] == appearance for person in people.values())
    spans = dict(reference)
    uncertain = sum(standings.get(actor, 'unknown') == 'unknown' for actor in people)
    for category in reference.get('positions', {}):
        key = 'positions.' + category
        spans[key] = reference['positions'][category]
        known = sum(standings.get(actor, 'unknown') == category for actor in people)
        if category != 'unknown' and uncertain and comparison(known, spans[key]) == 'below':
            if comparison(known + uncertain, spans[key]) != 'below':
                continue
        counts[key] = known
    for function in reference.get('functions', {}):
        key = 'functions.' + function
        spans[key] = reference['functions'][function]
        counts[key] = sum(function in person['functions'] for person in people.values())
    return {key for key, number in counts.items() if comparison(number, spans.get(key)) in ('below', 'above')}


def validate(value: dict, products: dict, context: dict) -> None:
    plans = rows(value, 'cast_distribution_plan', FIELDS)
    chapters = {c['index']: c for c in value['chapters']}
    require(all(type(row['chapter']) is int for row in plans) and len(plans) == len(chapters)
            and {row['chapter'] for row in plans} == chapters.keys(), '每个实际章节都须有独立的阵容取舍')
    bodies = {r['key']: r['body'] for r in value['members']}
    selected = {r['scene']: r['event'] for r in value['selected_events']}
    event_options = events(products)
    standings = {r['card_id']: r['body'].get('casting', {}).get('standing', 'unknown')
                 for r in context.get('approved_cards', ()) if r['kind'] == 'character'}
    standings.update((r['key'], r['body'].get('casting', {}).get('standing', 'unknown'))
                     for r in products['character_design']['products']['members'])
    params = planning_context(context)
    prior = dict(params['previous_appearances'])
    for row in sorted(plans, key=lambda plan: plan['chapter']):
        index = row['chapter']
        scenes = {s['card'] for s in chapters[index]['scenes']}
        present = {actor for scene in scenes for actor in bodies[scene]['character_goals']}
        people = {}
        band = chapter_band(index, params['chapter_count'])
        partial = context.get('scope') == 'scene' or chapters[index]['card'] is None
        scope, reference = reference_for(context['cast_sample_reference'], band, partial=partial)
        span = reference.get('appearing')
        require(row['band'] == band and row['reference_scope'] == scope and row['appearing_range'] == span
                and row['comparison'] == comparison(len(present), span), '章段、来源范围或本章人数比较与冻结样本不符')
        for person in rows(row, 'people', PERSON_FIELDS):
            actor, scene, quote = person['actor'], person['scene'], person['basis_quote']
            require(scene in scenes and actor in bodies[scene]['character_goals'] and actor not in people
                    and person['event'] == selected.get(scene), '阵容取舍须关联本章该人在场的真实事件')
            require(content(quote) and quote == bodies[scene]['character_goals'][actor]
                    and content(person['reason']) and quote in person['reason'] and quote != person['reason'].strip(),
                    '引入或复用人物须引用本场该人目标并另作解释')
            require(references(person['functions'], FUNCTIONS), '本章须说明该人在实际事件中的职能')
            appeared = actor in prior and prior[actor][0] < index
            uncertain = any(i < index for i in params['unverified_chapters'])
            expected = 'returning' if appeared else 'unknown' if uncertain else 'first'
            require(person['appearance'] == expected, '该人的首次或再次出场判定与前章证据不符')
            people[actor] = person
        require(people.keys() == present, '人物分布取舍遗漏了本章的实际在场者')
        gaps = differences(reference, people, standings)
        require(references(row['differences'], gaps, nonempty=False) and set(row['differences']) == gaps,
                '须逐项说明实际人数、首登回归、人物地位和职责与参考范围的差异')
        reason = row['reason']
        upstream = [event_options.get(selected.get(scene), {}) for scene in scenes]
        require(content(reason) and any(p['basis_quote'] in reason and reason.strip() != p['basis_quote'] for p in people.values())
                and any(content(event.get(field)) and event[field] in reason for event in upstream
                        for field in ('goal', 'obstacle', 'completion_condition', 'event', 'completion_gate')),
                '全章阵容取舍须引用已选上游事件的具体前置和人物目标，说明采用或偏离的理由')
        for actor in present:
            prior[actor] = min(prior.get(actor, [index, 0]), [index, 0])


def schema() -> dict:
    from nw.materials.phase_schema import TEXT, array, obj, strings
    people = obj({**strings('actor', 'scene', 'event', 'basis_quote', 'reason'),
                  'appearance': {'enum': ['first', 'returning', 'unknown']},
                  'functions': array({'enum': list(FUNCTIONS)}, 1)})
    bounds = obj({key: {'type': 'integer', 'minimum': 0} for key in ('min', 'max')})
    return array(obj({'chapter': {'type': 'integer', 'minimum': 1}, 'band': {'enum': ['opening','middle','ending','unknown']},
                      'reference_scope': {'enum': ['band','chapter','insufficient','partial']},
                      'appearing_range': {'anyOf': [bounds, {'type': 'null'}]},
                      'comparison': {'enum': ['within','below','above','insufficient']}, 'differences': array(TEXT),
                      'reason': TEXT, 'people': array(people, 1)}), 1)
