"""A plot may return a grounded, bounded request to revise the current cast."""
from nw.materials.phase_contract import require
from nw.materials.phase_routes import product_ref
from nw.task_models import _text, content_sha256


STAGES = ('character_design', 'static_relations', 'plot_design')
INSTRUCTION = (
    '剧情细化时先尝试用当前人物和非人物障碍完成。只有新发现的因果转折确实需要新增或调整行动职责，'
    '才单独回复 {"stage":"plot_design","cast_gap":{"turns":[...],"cast_demands":[...]}}。'
    '一次交齐本轮的缺口。turns 每项含 id、source_ref（plot_gap_sources键）、source_quote（原文）、event、'
    'obstacle、change、current_cast。current_cast 按每项需求 demand 逐一引用初版新人物的 actor、field、quote 和 reason，'
    'decision 取 reuse 或 unavailable。cast_demands 使用前置步骤相同字段，其 event、obstacle 与该 turn 相同，'
    'need_ref 引用 plot-gap:<turn id>:obstacle 或 :change。原人物兼任时沿用其 slot。'
    '若原人无法参与且须换人，修改该职责并给替代者新的 slot，保留其他分派。')


def sources(gap: dict) -> dict:
    return {f'plot-gap:{row["id"]}:{key}': row[key]
            for row in gap.get('turns', ()) for key in ('obstacle', 'change')}


def origins(products: dict, context: dict) -> dict:
    from nw.materials.cast_demands import source_options
    result = source_options(context)
    for row in products['world_design']['products']['cast_demands']:
        for key in ('event', 'obstacle', 'result'):
            result[f'initial-demand:{row["id"]}:{key}'] = row[key]
    for row in products['static_relations']['products']['relations']:
        for key in ('relation', 'condition'):
            result[f'relation:{row["id"]}:{key}'] = row[key]
    return result


def validate(raw: dict, products: dict, context: dict) -> None:
    from nw.materials import cast_demands
    require(context.get('cast_demand_policy') == cast_demands.POLICY, '本任务未启用剧情回补人物')
    require(raw.keys() == {'stage', 'cast_gap'} and raw['stage'] == 'plot_design', '人物缺口只能由剧情步骤单独交回')
    gap = raw['cast_gap']
    require(isinstance(gap, dict) and gap.keys() == {'turns', 'cast_demands'}
            and isinstance(gap['turns'], list) and gap['turns']
            and isinstance(gap['cast_demands'], list) and gap['cast_demands'], '剧情缺口须含明确转折与人物职责')
    available = origins(products, context)
    cast = products['character_design']['products']
    people = {r['key']: r['body'] for r in cast['members']}
    previous = {r['id']: r for r in products['world_design']['products']['cast_demands']}
    slots = {previous[a['demand']]['slot']: a['actor'] for a in cast['cast_assignments']}
    turns = {}
    for turn in gap['turns']:
        required = {'id', 'source_ref', 'source_quote', 'event', 'obstacle', 'change'}
        require(isinstance(turn, dict) and turn.keys() == required | {'current_cast'}
                and all(_text(turn[k]) for k in required)
                and turn['id'] not in turns and turn['source_quote'] in available.get(turn['source_ref'], ''),
                '回补须引用初版剧情前置或关系中的实际依据')
        require(isinstance(turn['current_cast'], list), '须逐项核对本轮演员')
        considered = set()
        for candidate in turn['current_cast']:
            require(isinstance(candidate, dict) and candidate.keys() == {'demand', 'actor', 'field', 'quote', 'reason', 'decision'}
                    and _text(candidate['demand']) and candidate['actor'] in people
                    and (candidate['demand'], candidate['actor']) not in considered
                    and candidate['field'] in cast_demands.ACTOR_FIELDS and candidate['decision'] in ('reuse', 'unavailable')
                    and _text(candidate['reason']) and _text(candidate['quote'])
                    and _text(people[candidate['actor']].get(candidate['field']))
                    and candidate['quote'] in people[candidate['actor']][candidate['field']],
                    '回补须引用本轮已有演员承担或无法承担职责的具体人物依据')
            considered.add((candidate['demand'], candidate['actor']))
        turns[turn['id']] = turn
    evidence = sources(gap)
    cast_demands.validate_demands(gap['cast_demands'], evidence, cast_demands.roster(context))
    covered = {key: set() for key in turns}
    for demand in gap['cast_demands']:
        key = demand['need_ref'].removeprefix('plot-gap:').rsplit(':', 1)[0]
        turn = turns[key]
        require((demand['event'], demand['obstacle']) == (turn['event'], turn['obstacle'])
                and demand != previous.get(demand['id']), '回补职责须落实本轮新发现的剧情转折')
        checked = {c['actor']: c['decision'] for c in turn['current_cast'] if c['demand'] == demand['id']}
        require(checked.keys() == people.keys(), '回补职责遗漏了本轮已有演员')
        reuse = {actor for actor, decision in checked.items() if decision == 'reuse'}
        chosen = slots.get(demand['slot'])
        if reuse or chosen in people:
            require(chosen in reuse, '可兼任的本轮演员须沿用原有职责位置')
        covered[key].add(demand['id'])
    for key, ids in covered.items():
        require(bool(ids) and all(c['demand'] in ids for c in turns[key]['current_cast']),
                '剧情转折与回补职责没有逐项对齐')
    revised = {**context, 'plot_cast_gap': gap}
    cast_demands.validate_demands(cast_demands.effective_demands(products, revised),
                                  cast_demands.source_options(revised), cast_demands.roster(revised))


def basis(products: dict) -> dict:
    return {stage: {**product_ref(products[stage]), 'products': products[stage]['products']}
            for stage in STAGES[:2]}


def editor_inputs(products: dict, context: dict, gap: dict) -> dict:
    from nw.materials.cast_demands import ACTOR_FIELDS
    available = origins(products, context)
    return {'initial_versions': [product_ref(products[s]) for s in STAGES[:2]],
            'origin_texts': {row['source_ref']: available[row['source_ref']] for row in gap['turns']},
            'initial_cast': {r['key']: {k: r['body'][k] for k in ACTOR_FIELDS if k in r['body']}
                             for r in products['character_design']['products']['members']},
            'initial_assignments': products['character_design']['products']['cast_assignments']}


def stable_cast(products: dict, value: dict, initial: dict, gap: dict) -> None:
    from nw.materials.cast_demands import effective_demands
    original_demands = products['world_design']['products']['cast_demands']
    old = {r['id']: r['slot'] for r in original_demands}
    before = {old[r['demand']]: r['actor'] for r in initial['cast_assignments']}
    active = {r['id']: r['slot'] for r in effective_demands(products, {'plot_cast_gap': gap})}
    for assignment in value['cast_assignments']:
        slot = active[assignment['demand']]
        if slot in before:
            require(assignment['actor'] == before[slot], '补人时替换了沿用原职责的演员')
    prior = {r['key']: r['body'] for r in initial['members']}
    compared = {key: {'name', 'role', 'background', 'independent_goal', 'boundaries'} for key in prior}
    for turn in gap['turns']:
        for candidate in turn['current_cast']:
            compared[candidate['actor']].add(candidate['field'])
    for person in value['members']:
        key = person['key']
        if key in prior:
            old, new = prior[key], person['body']
            require(all(old.get(field) == new.get(field) for field in compared[key])
                    and all(old['casting'].get(field) == new['casting'].get(field)
                            for field in ('standing', 'public_identity', 'secret')),
                    '回补不能改写同一人的身份、经历、目标边界或用于判断其能否承担职责的依据')


def verify_archive(session: dict, store=None) -> None:
    context = session['context']
    gap = context.get('plot_cast_gap')
    archive = session.get('cast_repair')
    if gap is None and archive is None:
        return
    require(isinstance(archive, dict) and bool(gap) and archive['gap_sha256'] == content_sha256(gap),
            '剧情回补缺少原始请求或其内容已变化')
    records = {r['stage']: r for r in session['stages']}
    original = archive['superseded']
    original_products = {**records, **original}
    before = {k: v for k, v in context.items() if k != 'plot_cast_gap'}
    raw = {'stage': 'plot_design', 'cast_gap': gap}
    validate(raw, original_products, before)
    require(context.get('cast_gap_inputs') == editor_inputs(original_products, before, gap),
            '补人编辑没有收到初版角色和触发该转折的原文')
    stable_cast(records, records['character_design']['products'], original['character_design']['products'], gap)
    refs = {r['task_id'] for r in session['calls']}
    require(archive['receipt'] in session['calls'] and original.keys() == set(STAGES[:2])
            and all(product_ref(r)['task_id'] in refs and r['task_id'] != records[s]['task_id']
                    for s, r in original.items()), '初版及回补后的阶段版本无法区分')
    from nw.materials.casting_editor import require_approved
    require_approved(archive['editor_review'], context, gap['cast_demands'], session['calls'])
    if store is not None:
        from nw.tasks import read_input_manifest, read_task
        receipt = archive['receipt']
        call = read_task(store, receipt['task_id'])
        _, saved = read_input_manifest(store, receipt['manifest_id'])
        packet = saved['study_input']
        require(call.validation == 'VALID' and call.parsed == raw and packet['stage'] == 'plot_design'
                and all(packet['inputs'][s] == {'ref': product_ref(r), 'products': r['products']}
                        for s, r in original.items()), '回补请求与剧情步骤实际收到的初版设计不符')


def schema() -> dict:
    from nw.materials.phase_schema import array, obj, strings
    from nw.materials.cast_demands import add_schema
    cast = obj({**strings('demand', 'actor', 'field', 'quote', 'reason'), 'decision': {'enum': ['reuse', 'unavailable']}})
    turn = obj({**strings('id', 'source_ref', 'source_quote', 'event', 'obstacle', 'change'), 'current_cast': array(cast)})
    fields = {'turns': array(turn, 1)}
    add_schema('world_design', fields)
    fields['cast_demands']['minItems'] = 1
    return obj({'stage': {'const': 'plot_design'}, 'cast_gap': obj(fields)})
