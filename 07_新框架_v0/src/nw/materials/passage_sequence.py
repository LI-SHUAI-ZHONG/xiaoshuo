"""Select a passage method for a scene need and bind it to ordered expression beats."""
from nw.materials.template_support import content, events, product, require, rows


POLICY = 'passage-sequence-v1'
ROLES = {
    'procedure_branch': ('demonstration', 'compression', 'different_choice', 'handoff'),
    'focus_relay': ('orientation', 'attention', 'focus', 'handoff'),
}
DETAIL = ('scene', 'summary', 'ellipsis', 'pause')
STATUS = ('observed', 'inference', 'pending')
CHOICE_FIELDS = {'scene', 'event', 'kind', 'source_ref', 'need_quote', 'reason'}
STEP_FIELDS = {'beat', 'role', 'focus_quote', 'bridge_quote', 'connection', 'detail', 'status'}
EVENT_FIELDS = ('goal', 'setting', 'obstacle', 'completion_condition', 'event', 'completion_gate')
COMPARISON_FIELDS = {'gate_quote', 'example_beat', 'example_actor', 'example_choice',
                     'branch_beat', 'branch_actor', 'branch_choice'}

SCENE_INSTRUCTION = (
    '按本场已选事件的需要安排读者先看什么、后来为何换焦。可用 procedure_branch：让有职责的人对一个具体人'
    '示范规则，以问答、手续、物件和实际结果让读者学会流程，略去相同轮次，到另一人面对同一关口作出不同选择时再展开。'
    '可用 focus_relay：时间地点定位，写正在进行的群体活动，选能说明世界或人物的具体声音、物件或动作，'
    '经由目光、声音或动作转向某个人；接下来让读者等什么，由本章任务决定。'
    '逐项对照同类型 passage_references 的适用条件及边界，只移用写法；参考适用时填其冻结 ref，'
    '直接使用内置写法填 null。只要别的手法更合适，选 other 并写具体原因。'
    '以 passage_choices 给出 scene、本场 selected_events 的 event、kind、source_ref、'
    '该事件一个完整字段的原文 need_quote、为何这样安排的 reason。有参考候选时逐场说明取舍。'
    '采用 ref 时另填 fit：原样保留该 ref 的 condition、boundary，以 prior_quote 摘本场所选事件或行动的实际前置，'
    'boundary_check 用这个引文解释为何没有触犯原方法的边界，或本次只适用哪一部分；确实不适用时另选。'
)
EXPRESSION_INSTRUCTION = (
    '落实 passage_choices 里已选的写法，以 passage_sequences 按 scene 列 steps，仅标需要协同的拍。'
    'beat 是本场 guidance 从 1 起的实际序号；一段可容多拍，一拍也可展开多段。'
    'procedure_branch 依次 demonstration（示例办到什么结果）、可选 compression（以时间或群体概述跳过重复）、'
    'different_choice（同一选择点上另一人实际怎样选）、可选 handoff（已交付的东西或仍待办的事）。'
    'focus_relay 依次 orientation（时间空间及在场活动）、attention（具体物件、声音或目光怎样引路）、'
    'focus（被注意的具体人物或动作）、可选 handoff（这次聚焦接出什么）。'
    'focus_quote 摘本拍 observable 能辨认对象或动作的连续原文；从第二拍起，以 bridge_quote 摘上一入选拍的'
    ' observable，connection 说明这个细节怎样转入本拍。第一拍这两项填 null。'
    'detail 用 scene 详写、summary 概述、ellipsis 跳时或 pause 停留特写。status 用 observed 表示此拍实际呈现的事，'
    'inference 表示特定人的推想或评价，pending 表示被承诺、等待、尚未兑现的后续。保留既有 narration 的'
    '叙述者、所知、亲历与见证边界；现场定位和转焦线索各须有可呈现的一拍。读者能接着上拍看，不等于角色因此知道。场面可停在特写或拿到凭证，'
    '勿替当事人预支见面、领取或结果。选了拆解来源的场另在该 sequence 填 source_operation，'
    '完整摘取所用 ref 的一条 operations，并用 source_beat 指明将它改写为本项目实际表现的入选拍。'
    '同一角色的段落功能允许连续多拍。procedure_branch 另填 comparison：gate_quote 摘本场 need_quote '
    '或场卡 goal、conflict、choice、entering_state 中的共同办理关口；example_beat 和 branch_beat 指示范和分岔拍。'
    'example_actor/example_choice、branch_actor/branch_choice 各从相应 observable 摘具体获办人称谓和所作选择。'
    '两人面对同一件事，各自实际所做须能辨别。'
)


def _offers(references: list[dict], products: dict) -> list[dict]:
    if not references:
        return []
    from nw.production_methods.passage_sources import scene_candidates
    return scene_candidates([r for r in references if r['kind'] in ROLES], events(products),
                            product(products, 'action_design').get('candidates', []))


def prompt(stage: str, payload: dict, products: dict, context: dict) -> str:
    if context.get('passage_policy') != POLICY:
        return ''
    if stage == 'plot_design':
        return ('按章的实际需要在 event_nodes 中设计地点、谁本来在做什么、谁来此办什么事及到哪里算完成；'
                '同一流程有人作不同选择时，预留分岔点。需要从群体转向个人时，给出本来在场的人和活动。'
                '读者看懂规则、看出反常、产生待解问题也可以是本段进展，不必为每段新增事件。')
    if stage == 'scene_design':
        payload['passage_policy'] = POLICY
        payload['passage_references'] = _offers(context.get('passage_references', []), products)
        return SCENE_INSTRUCTION
    if stage == 'expression_design':
        choices = [row for row in product(products, 'scene_design').get('passage_choices', []) if row['kind'] in ROLES]
        if not choices:
            return ''
        selected = {row['source_ref'] for row in choices if row['source_ref']}
        payload['passage_policy'] = POLICY
        payload['passage_choices'] = choices
        payload['passage_references'] = [row for row in context.get('passage_references', []) if row['ref'] in selected]
        return EXPRESSION_INSTRUCTION
    return ''


def validate_choices(value: dict, products: dict, references: list[dict]) -> None:
    if 'passage_choices' not in value and not any(r['kind'] in ROLES for r in references):
        return
    selected = {row['scene']: row['event'] for row in value['selected_events']}
    options = events(products)
    offered = _offers(references, products)
    sources = {row['ref']: row for row in offered}
    seen = set()
    choices = value.get('passage_choices')
    require(isinstance(choices, list), '本场需要明确的段落写法取舍')
    for choice in choices:
        require(isinstance(choice, dict), '段落写法取舍需要逐场给出')
        ref = choice.get('source_ref')
        require(set(choice) == (CHOICE_FIELDS | {'fit'} if ref else CHOICE_FIELDS),
                '采用拆解来源的场卡须核对适用条件和不适用边界')
        scene, event, kind = choice['scene'], choice['event'], choice['kind']
        require(scene not in seen and scene in selected and selected[scene] == event and event in options,
                '段落写法须承接本场实际选中的事件')
        require(kind in (*ROLES, 'other') and content(choice['reason'])
                and content(choice['need_quote']) and any(choice['need_quote'] == options[event].get(key) for key in EVENT_FIELDS),
                '段落写法取舍须说明理由并引用本场事件的一项原文需求')
        require(ref is None or (isinstance(ref, str) and kind in ROLES and ref in sources and sources[ref]['kind'] == kind
                                and event in sources[ref]['events']),
                '段落写法来源须对应冻结的同类型方法、版本及段组')
        if ref:
            _validate_fit(choice, sources[ref], options[event], value, products)
        seen.add(scene)
    offered_events = {event for option in offered for event in option['events']}
    require(all(scene in seen for scene, event in selected.items() if event in offered_events),
            '已有同类段落候选，各场须依据所选事件说明采用或另选写法')


def _excerpt(quote: object, source: object) -> bool:
    return isinstance(source, str) and content(quote) and any(c.isalnum() for c in quote) and quote in source


def _validate_fit(choice: dict, source: dict, event: dict, scenes: dict, products: dict) -> None:
    fit = choice['fit']
    require(isinstance(fit, dict) and set(fit) == {'condition', 'boundary', 'prior_quote', 'boundary_check'}
            and all(fit[key] == source[key] for key in ('condition', 'boundary')),
            '须核对本场实际采用的拆解来源的适用条件与不适用边界')
    evidence = [event.get(key) for key in EVENT_FIELDS]
    selected = {row['action'] for row in scenes.get('selected_actions', []) if row['scene'] == choice['scene']}
    for action in product(products, 'action_design').get('candidates', ()):
        if action['id'] in selected and action['event'] == choice['event']:
            evidence.extend((action['action'], action['cost'], *action['requires'], *action['limits']))
            for step in action['steps']:
                evidence.extend(step.values())
    quote, check = fit['prior_quote'], fit['boundary_check']
    require(any(_excerpt(quote, field) for field in evidence) and content(check) and quote in check
            and any(c.isalnum() for c in check.replace(quote, '')) and check not in (fit['condition'], fit['boundary']),
            '须用本场已选事件或实际采用的行动细节，解释拆解写法在原边界内如何适用')


def _validate_steps(steps: list, kind: str, guides: list[dict]) -> None:
    previous = None
    roles = []
    observables = set()
    visible_roles = set()
    last_beat = 0
    for step in rows({'steps': steps}, 'steps', STEP_FIELDS):
        beat, role = step['beat'], step['role']
        require(type(beat) is int and last_beat < beat <= len(guides) and role in ROLES[kind],
                '段落顺序须对应同场真实表达拍，手法须与场卡一致')
        guide = guides[beat - 1]
        require(guide['observable'].strip() not in observables, '同一段表现不能重复充当不同推进步骤')
        observables.add(guide['observable'].strip())
        require(_excerpt(step['focus_quote'], guide['observable']) and step['detail'] in DETAIL and step['status'] in STATUS,
                '段落焦点须可在本拍核对，并标清详略和事实、推断或待办')
        if previous is None:
            require(step['bridge_quote'] is None and step['connection'] is None, '段首不能伪引前拍')
        else:
            require(_excerpt(step['bridge_quote'], previous['observable']) and content(step['connection']),
                    '转场须引用上一入选拍中真实出现的细节并交代怎样转入本拍')
        mode = guide['narration']['mode']
        if step['status'] == 'observed' and mode in ('action', 'speech', 'perception', 'summary', 'reenactment'):
            visible_roles.add(role)
        require(mode != 'inference' or step['status'] == 'inference', '人物推断不能写成实证或待办')
        require(step['status'] != 'inference' or mode in ('inference', 'thought', 'speech'),
                '推想或评价须落实到本拍人物的判断、想法或说法')
        if role == 'compression':
            require(step['detail'] in ('summary', 'ellipsis'), '跳过重复过程应选择概述或跳时')
        if role in ('demonstration', 'different_choice'):
            require(step['status'] == 'observed', '流程示例和实际选择必须落到已呈现的过程')
        if role == 'different_choice':
            require(guide['narration']['time'] == 'current' and mode in ('action', 'speech'),
                    '分岔须用本场实际行动或回答体现选择')
        roles.append(role)
        last_beat, previous = beat, guide
    required = ('demonstration', 'different_choice') if kind == 'procedure_branch' else ('orientation', 'attention', 'focus')
    require(all(role in roles for role in required) and roles == sorted(roles, key=ROLES[kind].index),
            '段落缺少写法成立的关键拍或发生倒序')
    if kind == 'focus_relay':
        require({'orientation', 'attention'} <= visible_roles, '现场与转焦线索各须有可呈现的一拍；推测和待办不能独自充当可见线索')


def _validate_comparison(sequence: dict, guides: list[dict], choice: dict, body: dict) -> None:
    pair = sequence['comparison']
    require(isinstance(pair, dict) and pair.keys() == COMPARISON_FIELDS, '同一关口需要示范与分岔的实际办理人和选项')
    require(any(_excerpt(pair['gate_quote'], source) for source in
                (choice['need_quote'], *(body.get(key, '') for key in ('goal', 'conflict', 'choice', 'entering_state')))),
            '示范与分岔的共同关口须有本场已选事件或场卡的前置依据')
    steps = {step['beat']: step['role'] for step in sequence['steps']}
    for side, role in (('example', 'demonstration'), ('branch', 'different_choice')):
        beat = pair[side + '_beat']
        require(type(beat) is int and steps.get(beat) == role, '用于对照的两拍须分别落在真实示范和分岔上')
        wording = guides[beat - 1]['observable']
        actor, selected = pair[side + '_actor'], pair[side + '_choice']
        require(content(actor) and actor in wording and _excerpt(selected, wording) and actor != selected,
                '获办人称谓和实际选择须可分别从自己这一拍辨认')
    for field in ('actor', 'choice'):
        first, second = (''.join(c for c in pair[key + '_' + field].casefold() if c.isalnum()) for key in ('example', 'branch'))
        require(first and second and first != second, '重复同一人或同一选项不能冒充另一个人的实际分岔')


def validate_sequences(value: dict, scenes: dict, references: list[dict]) -> None:
    choices = {row['scene']: row for row in scenes.get('passage_choices', ()) if row['kind'] in ROLES}
    if not choices and 'passage_sequences' not in value:
        return
    sources = {row['ref']: row for row in references}
    bodies = {row['key']: row['body'] for row in scenes.get('members', ())}
    sequences = value.get('passage_sequences')
    require(isinstance(sequences, list), '场卡已经选定的段落写法缺少表达安排')
    seen = set()
    for sequence in sequences:
        require(isinstance(sequence, dict), '连续段落缺少场景或节拍')
        scene = sequence.get('scene')
        require(scene in choices and scene not in seen, '连续段落不得串场、重复或冒用未选的写法')
        selected = choices[scene]
        ref = selected['source_ref']
        extra = {'source_operation', 'source_beat'} if ref else set()
        if selected['kind'] == 'procedure_branch':
            extra.add('comparison')
        require(set(sequence) == {'scene', 'steps'} | extra, '连续段落缺少所选写法的对照或来源落点，或包含未选写法的字段')
        guides = [row for row in value['guidance'] if row['scene'] == scene]
        _validate_steps(sequence['steps'], selected['kind'], guides)
        if selected['kind'] == 'procedure_branch':
            _validate_comparison(sequence, guides, selected, bodies.get(scene, {}))
        if ref:
            require(ref in sources and sources[ref]['kind'] == selected['kind'] and
                    sequence['source_operation'] in sources[ref]['operations'] and
                    type(sequence['source_beat']) is int and sequence['source_beat'] in {s['beat'] for s in sequence['steps']},
                    '拆解原操作须来自本场已选版本，且落到当前连续段落中实际采用的一拍')
        seen.add(scene)
    require(seen == choices.keys(), '场卡已经选定的段落写法缺少表达安排')
