"""Tie a scene's selected setup and payoffs to the actual project and its prose beats."""
import json
import re

from nw.materials.scene_actions import selected_action_ids
from nw.materials.template_support import content, events, product, require
from nw.task_models import canonical, content_sha256


KINDS = {
    'orientation':'定位当前场地与时间', 'ongoing_activity':'焦点出现之前现场已有活动', 'event_start':'使等待转为行动',
    'spatial_cue':'相对方位引出下一动作', 'sensory_evidence':'由感官细节形成印象',
    'expectation_reveal':'具体证据更新读者的预期', 'place_function':'陈设与活动说明场所用途',
    'rule_in_force':'展示一项制度实际生效', 'action_completion':'关键行动与实际完成标志',
    'object_transfer':'区分交接后的物件和权利',
}
ROLES = {
    'orientation': ('place','time','ongoing'), 'ongoing_activity': ('underway',), 'event_start': ('ready','signal','response'),
    'spatial_cue': ('position','directed_action'), 'sensory_evidence': ('sensation','impression'),
    'expectation_reveal': ('familiar','exception','understanding'),
    'place_function': ('fixture','activity','purpose'),
    'rule_in_force': ('trigger','terms','decision'), 'action_completion': ('executed','completed'),
    'object_transfer': ('delivery','received','pending'),
}
OPTIONAL = {'time','ongoing','pending'}
READER_EFFECT = {'impression','understanding','purpose'}
PARTIES = {'event_start': ('initiator','responder'), 'rule_in_force': ('authority','subject'),
           'object_transfer': ('giver','recipient')}
OWNED = {'signal':'initiator','response':'responder','terms':'authority','decision':'subject','delivery':'giver'}
MODE = {'signal':{'speech','action'}, 'response':{'speech','action'}, 'delivery':{'action'},
        'terms':{'speech','action'}, 'decision':{'speech','action'}}
REVIEWS = {
    'orientation':'地点和时间足够辨认；移去焦点人物姓名后，已在进行的活动仍能成立。沿用读者已知信息时避免重报。',
    'ongoing_activity':'若隐去焦点人物，开场仍能指出谁或什么正在做哪件事。仅给场所或未来打算不能支撑，旁白所见不自动成为尚未到场者的记忆。',
    'event_start':'分清原来已具备的条件、谁实际发出启动信号、谁先响应。仅仅在场或到齐不能证明事情已启动。',
    'spatial_cue':'前后有可定位的人或物，方位解释接下来谁看向哪里、怎样移动或递物。',
    'sensory_evidence':'删去评价词，感官证据仍能使人得到预期印象；仅声称安静、紧张等需要退修。',
    'expectation_reveal':'读者先有熟悉的预期，具体不同之处使他改变理解。不能为此强加角色恍然大悟。',
    'place_function':'指出哪项设施或其缺席与在场的哪种活动相互印证。功能可由读者领会。',
    'rule_in_force':'核对受约束者、触发、经办权限和告知先后；承担义务之前已有机会了解限制，无关制度单独处理。',
    'action_completion':'核对行动者对哪一对象实际做了什么、哪处迹象证明已到选定步骤的结果。意图、命令或开始做仍不足以确认已完成。',
    'object_transfer':'指出谁把哪件东西交到谁手、当下实际完成什么、得到哪种条件；将来可领取或待确定的事仍未实现。',
}
LABELS = {
    'place':'现场位置','time':'开场时间','ongoing':'既有活动','underway':'已在做的事','ready':'启动条件','signal':'启动信号','response':'首位响应',
    'position':'相对方位','directed_action':'由方位引出的行动','sensation':'感官线索','impression':'印象依据',
    'familiar':'熟悉情境','exception':'不同细节','understanding':'改判依据','fixture':'场所陈设',
    'activity':'场所活动','purpose':'用途依据','trigger':'制度触发','terms':'告知条款','decision':'承担决定',
    'delivery':'交付动作','received':'实际所得','pending':'待兑现依据','executed':'关键行动','completed':'完成标志',
}
EXPLAIN = {'impression':'形成印象','understanding':'读者新理解','purpose':'场所用途'}
FIXES = {'situated_evidence':'用本场实际可辨认的言行或细节补足对应作用，分清经办者、接收者和读者所得。',
         'situated_order':'调整成稿的先后与承接，让启动、告知、回应或实际结果各有可定位的证据。'}


def schema_fields(stage: str) -> dict:
    from nw.materials.phase_schema import TEXT, array, obj, strings
    if stage == 'scene_design':
        extras = {kind: obj(strings(*parties)) for kind,parties in PARTIES.items()}
        need = {**strings('scene','event','need_quote','reason'), 'kind':{'enum':list(KINDS)},
                'known_quote':TEXT, 'place_quote':TEXT, 'parties':{'anyOf':list(extras.values())}, 'world':TEXT, 'rule_quote':TEXT, 'authority_quote':TEXT,
                'action':TEXT, 'step':{'type':'integer','minimum':1}, 'object_quote':TEXT,'result_quote':TEXT,
                'subject_quote':TEXT,'activity_quote':TEXT}
        return {'situated_needs':array(obj(need, ('known_quote','place_quote','parties','world','rule_quote','authority_quote',
                                                  'action','step','object_quote','result_quote','subject_quote','activity_quote')))}
    if stage == 'expression_design':
        mark = obj({'beat':{'type':'integer','minimum':1}, 'role':{'enum':sorted({r for roles in ROLES.values() for r in roles})}, 'quote':TEXT})
        return {'situated_beats':array(obj({'scene':TEXT, 'kind':{'enum':list(KINDS)}, 'marks':array(mark,1)}))}
    return {}


def prompt(stage: str, payload: dict, products: dict, context: dict) -> str:
    if stage == 'event_design':
        return '涉及点名、办理或执行制度时，事件要区分到齐等候、谁启动、谁响应以及哪一步真正生效。'
    if stage == 'scene_design':
        return ('本场普通写法可按已选事件或行动选 situated_needs，逐项含 scene,event,kind,need_quote（前置原句）,reason。'
                '按需选 '+ '、'.join(f'{k}({v})' for k,v in KINDS.items())+'。'
                'orientation/spatial_cue 从本场location或本事件场地摘place_quote；orientation可另引known_quote（此前读者确知的完整事实）。'
                'ongoing_activity 从本场entering_state或本事件setting同一字段分别摘subject_quote和activity_quote，指出谁已在做什么。'
                'event_start、rule_in_force、object_transfer '
                '另写 parties，键依次为 initiator/responder、authority/subject、giver/recipient，值为本场人物key。制度另引world与完整原句rule_quote；'
                'authority_quote摘经办者人物卡的职责或身份原文。交接或关键行动另引本场所选action、第几步step(从1起)；'
                '交接用object_quote摘物件，关键行动用result_quote保留原步骤完整result。')
    if stage == 'expression_design':
        needs = product(products,'scene_design').get('situated_needs',[])
        if needs:
            kinds = {n['kind'] for n in needs}
            payload['situated_needs'] = needs
            payload['situated_roles'] = {k:list(v) for k,v in ROLES.items() if k in kinds}
            actions = {a['id']:a for a in product(products,'action_design').get('candidates',())}
            if steps := [{'scene':n['scene'],'kind':n['kind'],'actor':actions[n['action']]['actor'],
                          'selected_step':actions[n['action']]['steps'][n['step']-1]} for n in needs if 'action' in n]:
                payload['situated_action_steps'] = steps
            return ('每项situated_needs写一个situated_beats={scene,kind,marks:[{role,beat,quote}]}列表项。'
                    '按现场实际先后引用本场guidance的拍号（从1起）和observable原句；同拍引用不同分句可合段。'
                    'situated_roles中的地点、时间、进行中活动可调整讲述顺序；场所的陈设和用途活动也可互换。其余按因果次序。'
                    'impression/understanding/purpose引同一或随后拍的narration.effect，让读者自行领会。'
                    'time、ongoing、pending按实际需要；place/position引文须带所选场地标志，物件名须在交付拍引文中，领取资格以后才能产生的结果只作为待办。'
                    'underway写已开始的具体活动，保留其主体与活动依据；旁白可先交代，不替尚未目睹者获知。'
                    'signal/response/terms/decision/delivery由指定人当场实施，对方须实际听见或看见。')
    return ''


def _excerpt(quote: object, value: object) -> bool:
    return isinstance(value,str) and content(quote) and any(ch.isalnum() for ch in quote) and quote in value


def _known(scene: str, value: dict, context: dict, quote: str) -> dict:
    point = next(((s['story_order'],[c['index'],s['index'],0]) for c in value.get('chapters',())
                  for s in c['scenes'] if s['card']==scene), None)
    matches = [f for f in context.get('narration_facts',context.get('accepted_state',())) if
               f.get('holder')=='READER' and f.get('claim')=='fact' and f.get('value')==quote and point
               and f.get('story_order', point[0]+1)<=point[0] and list(f.get('disclosure_order',point[1]))<point[1]]
    require(len(matches)==1, '已知定位须可追到本场之前唯一已接受的读者事实；他人私知或未来事实不能代替')
    return matches[0]


def _validate_needs(value: dict, products: dict, context: dict) -> None:
    event_ids = {r['scene']:r['event'] for r in value['selected_events']}
    bodies = {r['key']:r['body'] for r in value['members'] if r.get('kind')=='scene'}
    candidates = events(products)
    actions = {r['id']:r for r in product(products,'action_design').get('candidates',())}
    assigned = selected_action_ids(value)
    worlds = {r['card_id']:r['body'] for r in context.get('approved_cards',()) if r['kind']=='world'}
    worlds.update({r['key']:r['body'] for r in product(products,'world_design').get('members',()) if r['kind']=='world'})
    people = {r['card_id']:r['body'] for r in context.get('approved_cards',()) if r['kind']=='character'}
    people.update({r['key']:r['body'] for r in product(products,'character_design').get('members',()) if r['kind']=='character'})
    seen = set()
    needs = value['situated_needs']
    require(isinstance(needs,list), '本场制作需求须为列表')
    for row in needs:
        require(isinstance(row,dict) and isinstance(row.get('kind'),str) and row['kind'] in KINDS
                and isinstance(row.get('scene'),str) and row['scene'] in bodies, '未知场景或现场写法')
        kind, scene = row['kind'], row['scene']
        fields = {'scene','event','kind','need_quote','reason'}
        if kind in PARTIES:
            fields.add('parties')
        if kind=='rule_in_force':
            fields.update(('world','rule_quote','authority_quote'))
        if kind=='object_transfer':
            fields.update(('action','step','object_quote'))
        if kind=='action_completion':
            fields.update(('action','step','result_quote'))
        if kind=='orientation' and 'known_quote' in row:
            fields.add('known_quote')
        if kind in ('orientation','spatial_cue'):
            fields.add('place_quote')
        if kind=='ongoing_activity':
            fields.update(('subject_quote','activity_quote'))
        require(set(row)==fields and event_ids.get(scene)==row['event'] and content(row['reason'])
                and (scene,kind) not in seen, '现场写法须对应本场已选事件，有具体理由且不能重复')
        seen.add((scene,kind))
        event = candidates.get(row['event'],{})
        inputs = [event.get(key) for key in ('goal','setting','obstacle','completion_condition','event','completion_gate')]
        selected = [actions[key] for key in assigned.get(scene,()) if key in actions and actions[key]['event']==row['event']]
        for action in selected:
            inputs.append(action['action'])
            inputs.extend(text for step in action['steps'] for text in step.values())
        require(any(_excerpt(row['need_quote'],v) for v in inputs), '现场写法缺少本场已选事件或行动的前置引文')
        if kind in ('orientation','spatial_cue'):
            require(any(_excerpt(row['place_quote'],v) for v in (bodies[scene].get('location'), event.get('setting'),
                    event.get('event'))), '本场定位须有已选事件或该场卡的真实地点依据')
        if kind=='ongoing_activity':
            subject, activity = row['subject_quote'], row['activity_quote']
            require(any(_excerpt(subject,v) and _excerpt(activity,v) for v in
                        (bodies[scene].get('entering_state'),event.get('setting')))
                    and subject not in activity and activity not in subject,
                    '现场原已进行的活动须从开场状态或事件场地提取不同的主体和具体活动，后续打算不能代替')
        if 'known_quote' in row:
            require(content(row['known_quote']), '缺少读者已知的实际定位依据')
            _known(scene,value,context,row['known_quote'])
        if kind in PARTIES:
            parties = row['parties']
            present = {bodies[scene]['pov'], *bodies[scene].get('characters',())}
            require(isinstance(parties,dict) and set(parties)==set(PARTIES[kind])
                    and all(isinstance(p,str) and p in present and p in event.get('actors',()) for p in parties.values())
                    and len(set(parties.values()))==2, '须区分本场实际在场的双方')
        if kind=='rule_in_force':
            world = worlds.get(row['world']) if isinstance(row['world'],str) else None
            require(world is not None and (world.get('visibility')=='public' or world.get('visibility')=='holders'
                    and row['parties']['authority'] in world.get('holders',())), '经办者必须有权获知本项目制度')
            rule = world['rule'].strip()
            sentences = [p.strip() for p in re.findall(r'[^。！？\n]+[。！？]?',rule)]
            require(content(row['rule_quote']) and row['rule_quote'] in [rule,*sentences],
                    '制度引文须保留本项目世界卡的完整原句及其触发、限制')
            staff = people.get(row['parties']['authority'],{})
            require(any(_excerpt(row['authority_quote'],staff.get(k)) for k in ('role','scene_function')),
                    '经办权限须有此人的身份或职责依据，知道制度不能单独证明有权执行')
        if kind in ('object_transfer','action_completion'):
            action = next((a for a in selected if a['id']==row['action']), None)
            step = row['step']
            require(action and type(step) is int and 1<=step<=len(action['steps']), '须选本场实际采用的行动及其真实步骤')
            selected_step = action['steps'][step-1]
            if kind=='object_transfer':
                require(action['actor']==row['parties']['giver'] and _excerpt(row['object_quote'],selected_step['object']),
                        '交付人及物件须来自已选的实际行动步骤')
            else:
                require(content(row['result_quote']) and row['result_quote']==selected_step['result'],
                        '须保留本项目关键步骤的完整结果，包括限制或未决条件')


def _validate_marks(value: dict, products: dict) -> None:
    scene_plan = product(products,'scene_design')
    actions = {a['id']:a for a in product(products,'action_design').get('candidates',())}
    needs = {(n['scene'],n['kind']):n for n in scene_plan.get('situated_needs',())}
    rows = value.get('situated_beats',[])
    require(isinstance(rows,list), '现场表达落点须为列表')
    seen = set()
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'scene','kind','marks'}
                and isinstance(row['scene'],str) and isinstance(row['kind'],str)
                and isinstance(row['marks'],list), '现场表达须说明场景、写法和实际落点')
        key = (row['scene'],row['kind'])
        require(key in needs and key not in seen, '现场表达与本场选定写法不符或重复')
        seen.add(key)
        need = needs[key]
        guides = [g for g in value['guidance'] if g['scene']==row['scene']]
        expected = ROLES[row['kind']]
        roles, previous, end = [], 0, 0
        for mark in row['marks']:
            require(isinstance(mark,dict) and set(mark)=={'role','beat','quote'}, '现场表达缺少实际拍号、作用和引文')
            role, n, quote = mark['role'],mark['beat'],mark['quote']
            require(role in expected and type(n) is int and previous<=n<=len(guides) and n>=1,
                    '现场表达须在本场实际表达拍中按先后落实')
            guide = guides[n-1]
            beat = guide['narration']
            reader = role in READER_EFFECT
            material = beat['effect'] if reader else guide['observable']
            require(_excerpt(quote,material), '现场原句与本拍可见表现或读者所得不符')
            if reader:
                require(beat['mode'] not in ('thought','inference'), '读者理解的更新不能登记成角色的私下顿悟')
            else:
                start = material.find(quote,end if n==previous else 0)
                require(start>=0 and beat['time']=='current' and beat['mode'] not in ('thought','inference'),
                        '各现场细节要有依次出现的实际根据，不能拿想法、未来或同一句复用')
                end = start+len(quote)
            if role in OWNED:
                owner = need['parties'][OWNED[role]]
                other, = (p for p in need['parties'].values() if p!=owner)
                require(beat.get('owner')==owner and beat['mode'] in MODE[role]
                        and (role not in ('terms','signal','delivery') or other in beat.get('witnesses',())),
                        '启动、应答、告知或交付须由对应的在场者进行，并落实给实际听者或见证者')
            if role=='delivery':
                require(need['object_quote'] in quote, '交付拍须实际呈现本场所选的那件物品')
            if role in ('place','position'):
                require(need['place_quote'] in quote, '地点或位置关系须在表达拍中接住本场选定的场地标志')
            if role=='underway':
                require(need['subject_quote'] in quote and need['activity_quote'] in quote
                        and beat['mode'] in ('action','perception','summary'),
                        '原有活动须有当前具体主体的可见过程，只有场地、意向或关于现场的说法不足为据')
            if role=='executed':
                require(beat.get('owner')==actions[need['action']]['actor'] and beat['mode'] in ('speech','action'),
                        '关键行动必须由选中步骤的实际执行者当场实施')
            if role=='completed':
                require(beat['mode'] in ('action','summary','perception'), '完成标志须有实际表现，只有相关说法不能核实结果')
            if role=='received':
                receiver = need['parties']['recipient']
                require(beat['mode'] in ('action','perception','summary') and (beat.get('owner') in (receiver,None)
                        or receiver in beat.get('witnesses',())), '获得物件或权利须由现场行为或可见状态支持，单凭允诺不能确认收到')
            if role=='pending':
                require(previous<n, '尚待兑现须与已经交付的证据分别定位')
            previous = n
            roles.append(role)
        ordered = [r for r in expected if r in roles]
        if row['kind']=='orientation':
            ordered = list(dict.fromkeys(roles))
        elif row['kind']=='place_function':
            ordered = [r for r in dict.fromkeys(roles) if r!='purpose']+['purpose']
        require(set(expected)-OPTIONAL<=set(roles) and roles==ordered,
                '所采用写法缺少关键落点或因果顺序颠倒')
    require(seen==needs.keys(), '场卡选定的现场写法须逐一落实到本场表达')


def validate(stage: str, value: dict, products: dict, context: dict) -> None:
    if stage=='scene_design' and 'situated_needs' in value:
        _validate_needs(value,products,context)
    if stage=='expression_design':
        _validate_marks(value,products)


def uses(value: dict, scene: str) -> dict[str,set[int]]:
    return {row['kind']:{m['beat'] for m in row['marks']} for row in value.get('situated_beats',()) if row['scene']==scene}


def attach(checks: list[dict], records: dict, scene: str, context: dict) -> None:
    scene_plan = product(records,'scene_design')
    needs = {n['kind']:n for n in scene_plan.get('situated_needs',()) if n['scene']==scene}
    if not needs:
        return
    beats = {c['narration_order']:c for c in checks if 'narration_order' in c}
    actions = {a['id']:a for a in product(records,'action_design').get('candidates',())}
    for plan in product(records,'expression_design').get('situated_beats',()):
        if plan['scene']!=scene:
            continue
        kind = plan['kind']
        need = needs[kind]
        for index,mark in enumerate(plan['marks']):
            check = beats[mark['beat']]
            visible = json.loads(check['binding']['observable'])
            visible.setdefault('situated_roles',[]).append({'kind':kind, 'method':KINDS[kind], 'role':mark['role'], 'quote':mark['quote']})
            check['binding']['observable'] = canonical(visible)
            audit = {'scene':scene,'kind':kind, **mark}
            if mark['role'] in OWNED:
                audit['actor'] = need['parties'][OWNED[mark['role']]]
            if mark['role']=='executed':
                audit['actor'] = actions[need['action']]['actor']
            if index==0:
                audit['need'] = need
            if kind=='object_transfer' and mark['role']=='received':
                audit['selected_step'] = actions[need['action']]['steps'][need['step']-1]
                check['binding']['check'] += ' 写清此时到手的物品、资格或信息，将实际兑现留到发生时。'
            if mark['role']=='completed':
                audit['selected_step'] = actions[need['action']]['steps'][need['step']-1]
            check.setdefault('situated_checks',[]).append(audit)
            if mark['role']=='pending':
                check['situated_pending'] = True
                check['binding']['check'] += ' 将仍待办理或尚待确认的后续写成可能或待办。'
            if mark['role']=='place' and 'known_quote' in need:
                check['situated_known_sha256'] = content_sha256(_known(scene,scene_plan,context,need['known_quote']))


def review_prompt(checks: list[dict]) -> str:
    marks = [mark for check in checks for mark in check.get('situated_checks',())]
    kinds = {m['kind'] for m in marks}
    if not kinds:
        return ''
    tags = list(dict.fromkeys(LABELS[m['role']] for m in marks))
    extras = list(dict.fromkeys(EXPLAIN[m['role']] for m in marks if m['role'] in EXPLAIN))
    return ('每个situated_checks落点在该审稿项reason中另起行写【对应标签】本稿精确短引；证据必须在该项evidence内。'
            '标签依role为'+ '、'.join(f"{r}={label}" for r,label in LABELS.items() if label in tags)
            + '。有actor时另写【相应标签归属】该人的actor值，以成稿确认谁行动。'
            + ('读者效果另写【'+ '】/【'.join(extras)+'】解释具体所得，可以共引使读者领会的现场细节。' if extras else '')
            + ''.join(REVIEWS[k] for k in KINDS if k in kinds))


def assess(checks: list[dict], rows, draft) -> None:
    from nw.materials.passage_effects import _line, _span
    by_id = rows if isinstance(rows,dict) else {r['id']:r for r in rows}
    previous = {}
    for check in sorted(checks,key=lambda c:c.get('narration_order',0)):
        row = by_id.get(check['id'])
        if not row or row['status']!='pass':
            continue
        for mark in check.get('situated_checks',()):
            role = mark['role']
            label = LABELS[role]
            span = _span(row,label,draft.id)
            valid = span and draft.text[span['start']:span['end']]==span['quote']
            if 'actor' in mark:
                valid = valid and _line(row['reason'],label+'归属')==mark['actor']
            if role in EXPLAIN:
                why = _line(row['reason'],EXPLAIN[role])
                valid = valid and content(why) and why!=span['quote'] and why!=label
            code = 'situated_evidence'
            if valid:
                key = mark['scene'],mark['kind']
                prior = previous.get(key)
                if prior and not (prior['beat']==mark['beat'] and role in READER_EFFECT):
                    valid = span['start']>=prior['end']
                    code = 'situated_order'
                if valid:
                    previous[key] = {'beat':mark['beat'],'end':span['end']}
            if not valid:
                row.update(status='failed',narration_issue=code,reason=FIXES[code])
                break


def pending_spans(row: dict, draft_id: str) -> list[dict]:
    from nw.materials.passage_effects import _span
    span = _span(row,LABELS['pending'],draft_id)
    return [span] if span else []


def situated_spans(check: dict, row: dict, draft_id: str) -> list[dict]:
    from nw.materials.passage_effects import _span
    if row['status']!='pass':
        return []
    locations = {}
    for mark in check.get('situated_checks',()):
        if span := _span(row,LABELS[mark['role']],draft_id):
            locations[span['start'],span['end']] = span
    return [locations[key] for key in sorted(locations)]
