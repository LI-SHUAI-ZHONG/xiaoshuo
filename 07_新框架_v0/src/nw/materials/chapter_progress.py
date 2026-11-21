"""Bind the change in a scene to its chosen event or an accepted earlier change."""
from nw.materials.template_support import content, events, product, require, rows
from nw.materials.phase_context import new_character_keys
from nw.story_models import Fact
from nw.task_models import canonical, content_sha256


POLICY = 'chapter-progress-v2'
LEGACY_POLICY = 'chapter-progress-v1'
POLICIES = (LEGACY_POLICY, POLICY)
PRESSURE_MARK = '【未决原文】'
ORIGINS = ('conversation', 'reflection', 'discovery', 'incident', 'continuation')
CONNECTIONS = ('causal', 'coincident', 'unresolved')
CHANGES = ('knowledge', 'decision', 'relationship', 'ability', 'resource', 'situation', 'emotion', 'reader', 'setup')
FIELDS = {'scene', 'basis_ref', 'basis_quote', 'origin', 'connection', 'stimulus', 'change', 'next_pressure'}
PLOT_INSTRUCTION = (
    '以已有方向、章前处境和未解决的问题定章任务。event_nodes.setting说明人物抵达前世界或他人已在做什么；'
    '用章卡goal/consequence写明章初问题与章末实际推进，可以是一句对话、一次改判或关系变化。'
    '有前章交接时，按人物各自已知、误信、意图及已付代价决定什么会改变本次选择。'
)
SCENE_INSTRUCTION = (
    '每场提供一条scene_progress。basis_ref可用event:本场selected_event的id，basis_quote逐字取其'
    'setting/goal/obstacle/completion_condition或event/completion_gate完整字段；也可从chapter_changes选择有实际作用的'
    '前章变化并完整摘其text，保留holder/claim。WORLD只说明客观处境，不能替人物想起或默知；'
    '由此形成新认知、决定或情绪时，选conversation或discovery说明本人当场怎样听到、看到或查到。'
    'origin选conversation/reflection/discovery/incident/continuation，'
    'stimulus写这个视角此刻遇到什么，为什么会反应；connection选causal/coincident/unresolved，不能把同时发生写成因果。'
    'change选knowledge/decision/relationship/ability/resource/situation/emotion/reader；单场只负责铺垫可选setup。'
    '用场卡entering_state与planned_result写清前后差别；next_pressure写对后续行动留下的条件，没有则null。'
    '一整章至少有一项实质进展，可在中段实现，章末允许安静收束。剧情无需凑齐各类。'
)


def chapter_changes(handoff: dict) -> dict:
    changes = [*handoff.get('changes', ()), *handoff.get('character_changes', ()),
               *handoff.get('identity_disclosures', ())]
    result = {}
    for index, change in enumerate(changes):
        value = change['new_value']
        if change['holder'] == 'READER':
            continue
        result[f'prior:{index}'] = {key: change[key] for key in
            ('entity_id', 'predicate', 'holder', 'claim', 'story_order', 'disclosure_order')}
        result[f'prior:{index}']['text'] = value if value is None or isinstance(value, str) else canonical(value)
        if change.get('evidence'):
            result[f'prior:{index}']['evidence_sha256'] = content_sha256(change['evidence'])
    return result


def chapter_openings(handoff: dict, policy: str = POLICY) -> dict:
    evidence_key = 'evidence' if policy == LEGACY_POLICY else 'pressure_evidence'
    return {f'open:{index}': {'draft_ref': row['draft_ref'], 'delta_id': row['delta_id'],
            'review_run_id': row['review_run_id'], 'evidence': row[evidence_key],
            'disclosure_order': row['disclosure_order'],
            'possible_next_pressure': row['possible_next_pressure']}
            for index, row in enumerate(handoff.get('reviewed_progress', ()))
            if row.get('possible_next_pressure') and row.get(evidence_key)}


def pressure_evidence(review: dict, draft_id: str) -> list[dict]:
    """Extract only the passage the independent reviewer designates as an open thread."""
    lines = review['reason'].strip().splitlines()
    if (not lines or not lines[-1].strip().startswith(PRESSURE_MARK)
            or any(line.strip().startswith(PRESSURE_MARK) for line in lines[:-1])):
        return []
    quote = lines[-1].strip()[len(PRESSURE_MARK):].strip()
    if sum(ch.isalnum() for ch in quote) < 4:
        return []
    for span in review['evidence']:
        if span['id'] != draft_id or span['quote'].count(quote) != 1:
            continue
        start = span['start'] + span['quote'].index(quote)
        return [{**span, 'start': start, 'end': start + len(quote), 'quote': quote}]
    return []


def validate_continuations(value: dict, options: dict) -> None:
    nodes = {node['id']: node for node in value['event_nodes']}
    seen = set()
    for row in rows(value, 'continuations', {'ref', 'event', 'target_quote', 'reason'}):
        ref, event = row['ref'], row['event']
        require(isinstance(ref, str) and ref in options and isinstance(event, str) and event in nodes
                and (ref, event) not in seen and content(row['reason']), '章末遗留事项须选自前章审稿与当前真实事件节点')
        require(any(row['target_quote'] == nodes[event].get(k) for k in ('goal', 'obstacle', 'completion_condition')),
                '接续安排须落到新事件的目标、阻碍或完成条件')
        seen.add((ref, event))


def _continuations(products: dict, event: str) -> list[dict]:
    node = next((r['predecessor'] for r in product(products, 'event_design').get('candidates', ())
                 if r['id'] == event), event)
    return [r for r in product(products, 'plot_design').get('continuations', ()) if r['event'] == node]


def validate(value: dict, products: dict, context: dict) -> None:
    places = {place['card']: (place['story_order'], (chapter['index'], place['index'], 0))
              for chapter in value['chapters'] for place in chapter['scenes']}
    bodies = {row['key']: row['body'] for row in value['members']}
    selected = {row['scene']: row['event'] for row in value['selected_events']}
    event_options = events(products)
    prior = context.get('chapter_changes', {})
    new_people = new_character_keys(products, context)
    seen = set()
    carried = set()
    for row in rows(value, 'scene_progress', FIELDS):
        scene = row['scene']
        require(isinstance(scene, str) and scene in places and scene not in seen, '重复或无对应场景的推进设计')
        seen.add(scene)
        body = bodies[scene]
        require(row['origin'] in ORIGINS and row['connection'] in CONNECTIONS and row['change'] in CHANGES
                and content(row['stimulus']) and (row['next_pressure'] is None or content(row['next_pressure'])),
                '需具体说明本场的触发、前因关系、进展及确有的后续条件')
        require(row['change'] == 'setup' or body['entering_state'].strip() != body['planned_result'].strip(),
                '本场起止状态完全相同，缺少实际推进')
        ref, quote = row['basis_ref'], row['basis_quote']
        require(isinstance(ref, str) and content(quote), '场景推进缺少可核对的前置')
        for link in _continuations(products, selected[scene]):
            earlier = context['chapter_openings'][link['ref']]['disclosure_order']
            require(tuple(earlier) < places[scene][1], '不能在前章问题出现之前将它当作读者已知的接续点')
            carried.add((link['ref'], link['event']))
        if ref == 'event:' + selected[scene]:
            event = event_options[selected[scene]]
            require(any(quote == event.get(field) for field in ('goal', 'setting', 'obstacle', 'completion_condition',
                        'event', 'completion_gate')), '推进依据与本场已选事件原文不符')
            continue
        source = prior.get(ref)
        require(source is not None and quote == source['text'], '场景推进没有对应的已选事件或前章变化')
        require(source['holder'] not in new_people and source['entity_id'] not in new_people,
                '新造人物与旧记录的标识重名，不能继承其过往知识或状态')
        require(source['holder'] == body['pov'] or source['holder'] == 'WORLD' and source['claim'] == 'fact',
                '不能把他人的私人判断当作本场视角已知')
        if source['holder'] == 'WORLD':
            require(row['origin'] != 'reflection' and (row['change'] not in ('knowledge', 'decision', 'emotion')
                    or row['origin'] in ('conversation', 'discovery')),
                    '客观处境不能替人物默知或回忆；本人的新认知或决定需要本场交流、听见或发现的途径')
        order, disclosure = places[scene]
        require(source['story_order'] <= order and tuple(source['disclosure_order']) < disclosure,
                '前章变化尚未在本场的故事时间或披露顺序发生')
        applicable = [key for key, change in prior.items() if all(change[field] == source[field]
                      for field in ('entity_id', 'predicate', 'holder', 'claim'))
                      and change['story_order'] <= order and tuple(change['disclosure_order']) < disclosure]
        latest = max(applicable, key=lambda key: (prior[key]['story_order'], prior[key]['disclosure_order'],
                                                   int(key.split(':')[1])))
        require(ref == latest, '本场之前该状态已经改变，需要使用此时有效的前章变化')
    require(seen == set(places), '每个实际场景须有自己的推进设计')
    required = {(r['ref'], r['event']) for r in product(products, 'plot_design').get('continuations', ())}
    require(required == carried, '本章已采用的接续事项须落在至少一个实际选中该事件的场景')
    if context.get('scope') in ('chapter', 'volume', 'replan'):
        changes = {row['scene']: row['change'] for row in value['scene_progress']}
        for chapter in value['chapters']:
            if chapter['card'] is not None:
                require(any(changes[s['card']] != 'setup' for s in chapter['scenes']), '完整章不能每场都只作铺垫')


def scene_check(records: dict, scene: str, context: dict) -> dict | None:
    scenes = product(records, 'scene_design')
    row = next((r for r in scenes.get('scene_progress', ()) if r['scene'] == scene), None)
    if not row:
        return None
    body = next(r['body'] for r in scenes['members'] if r['key'] == scene)
    patch = next((p for p in product(records, 'state_transition').get('patches', ()) if p['scene'] == scene), {})
    chapter = next(ch for ch in scenes['chapters'] if any(s['card'] == scene for s in ch['scenes']))
    positions = sorted(chapter['scenes'], key=lambda s: s['index'])
    observable = {k: row[k] for k in ('origin', 'connection', 'stimulus', 'change')}
    observable.update(entering_state=body['entering_state'], candidate_result=patch.get('planned_result', body['planned_result']))
    source = context.get('chapter_changes', {}).get(row['basis_ref'])
    if source and source['holder'] == body['pov']:
        observable['personal_basis'] = {key: source[key] for key in ('claim', 'predicate', 'text')}
    check = ('以本稿原句核对场面为后续建立的具体处境，不虚构人物改变。' if row['change'] == 'setup'
             else '以本稿原句核对这个视角遇到的触发、回应及实际变化；保留误信、意图、偶合或未决的原意。')
    check += ' 只有正文兑现且状态审核接受的结果才成为后续事实。'
    if chapter['card'] is not None:
        if positions[0]['card'] == scene:
            check += ' 核对章首问题怎样出现。'
        if positions[-1]['card'] == scene:
            check += ' 核对章末解决了什么、怎样承接章中已发生的改变，或在哪里留下未决问题。'
    selected = next(r['event'] for r in scenes['selected_events'] if r['scene'] == scene)
    continuations = _continuations(records, selected)
    if continuations:
        check += ' 核对本场是否实际回应前章留下的问题，区分人物尝试和已经实现的结果。'
    evidence_required = '引用当前稿中能辨认前因和结果的段落，说明本场推进是否成立。'
    chapter_task = {}
    if chapter['card'] is not None and context.get('chapter_progress_policy') == POLICY:
        card = next((r['body'] for r in product(records, 'plot_design').get('members', ())
                     if r['key'] == chapter['card']), {})
        if positions[0]['card'] == scene and card.get('goal'):
            chapter_task['goal'] = card['goal']
        if positions[-1]['card'] == scene and card.get('consequence'):
            chapter_task['consequence'] = card['consequence']
        if chapter_task:
            evidence_required += ' 对照 chapter_task 的章纲目标或预期后果，说明本场实际贡献；安静收束允许承接前场已发生的改变。'
    pressure_review = bool(row['next_pressure']) and context.get('chapter_progress_policy') == POLICY
    if pressure_review:
        evidence_required += (' 单独判断本稿是否确实留下 method_artifact.next_pressure。只有成立时，'
            '在 reason 末尾另起一行写“【未决原文】”并逐字摘录本项 evidence 中能表明该问题仍未解决的具体原文。'
            '未呈现、已经解决或另有进展时省略该行，仍可通过本场进展。')
    return {'id': f'work:progress:{scene}', 'profile': 'method_work',
            'binding': {'observable': canonical(observable), 'check': check}, 'method_artifact': row,
            **({'chapter_task': chapter_task} if chapter_task else {}),
            **({'pressure_review': POLICY} if pressure_review else {}),
            **({'chapter_progress_prior': source} if source else {}),
            **({'continuations': [{**link, 'prior': context['chapter_openings'][link['ref']]} for link in continuations]}
               if continuations else {}),
            'evidence_required': evidence_required}


def cast_preconditions(session: dict, scene: str) -> list[dict]:
    """Follow only the selected cast duties, including a plot-requested replacement."""
    records = {r['stage']: r for r in session.get('stages', ())}
    links = [r for r in product(records, 'scene_design').get('cast_payoffs', ()) if r['scene'] == scene]
    if not links:
        return []
    context = session['context']
    initial = {r['id']: r['need_ref'] for r in product(records, 'world_design')['cast_demands']}
    gap = context.get('plot_cast_gap') or {}
    demands = {**initial, **{r['id']: r['need_ref'] for r in gap.get('cast_demands', ())}}
    turns = {r['id']: r['source_ref'] for r in gap.get('turns', ())}
    checks = []
    for link in links:
        ref = demands[link['demand']]
        if ref.startswith('plot-gap:'):
            ref = turns[ref[len('plot-gap:'):].rsplit(':', 1)[0]]
        if ref.startswith('initial-demand:'):
            ref = initial[ref[len('initial-demand:'):].rsplit(':', 1)[0]]
        if ref.startswith('prior:'):
            checks.append({'chapter_progress_prior': context['chapter_changes'][ref.rsplit(':', 1)[0]]})
        elif ref.startswith('open:'):
            prior = context['chapter_openings'][ref.rsplit(':', 1)[0]]
            checks.append({'continuations': [{'prior': prior}]})
        elif ref.startswith('prior-cast:'):
            prior = context['cast_prior_work'][int(ref.split(':')[1])]
            checks.append({'cast_performance': prior})
    return checks


def writing_preconditions(checks: list[dict], session: dict, scene: str) -> list[dict]:
    selected = [check for check in checks if check.get('chapter_progress_prior') or check.get('continuations')]
    selected.extend(cast_preconditions(session, scene))
    if (session.get('context', {}).get('chapter_progress_policy') == LEGACY_POLICY
            and any(check.get('continuations') for check in selected)):
        raise ValueError('MATERIAL_PRECONDITION: 本场依赖旧版未单独核实的遗留问题，请按前章实际证据重新设计')
    return selected


def verify_current(checks: list[dict], facts: list[Fact], slots: dict, disclosure: tuple | None = None) -> None:
    accepted = {(slot['draft_id'], slot.get('delta_id')) for slot in slots.values()}
    for check in checks:
        receipts = [link['prior'] for link in check.get('continuations', ())]
        if performance := check.get('cast_performance'):
            receipts.append(performance)
        for prior in receipts:
            if ((prior['draft_ref']['id'], prior['delta_id']) not in accepted
                    or disclosure is not None and tuple(prior['disclosure_order']) >= disclosure):
                raise ValueError('MATERIAL_PRECONDITION: 章场引用的已接受稿已经改变或尚未披露，请按当前分支重新设计')
        if not (prior := check.get('chapter_progress_prior')):
            continue
        if disclosure is not None and tuple(prior['disclosure_order']) >= disclosure:
            raise ValueError('MATERIAL_PRECONDITION: 本场所依前章变化尚未披露，请按当前场次重新设计')
        for fact in facts:
            if not all(getattr(fact, field) == prior[field] for field in ('entity_id', 'predicate', 'holder', 'claim')):
                continue
            text = fact.value if isinstance(fact.value, str) else canonical(fact.value)
            if (prior['text'] == text and prior['story_order'] == fact.story_order
                    and tuple(prior['disclosure_order']) == fact.disclosure_order
                    and ('evidence_sha256' not in prior or prior['evidence_sha256'] == content_sha256(fact.evidence))):
                break
        else:
            raise ValueError('MATERIAL_PRECONDITION: 本场所依前章变化或稿件证据已经改变，请按当前分支重新设计')
