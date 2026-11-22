"""Tie a scene's selected character technique to the people, audience and actual turns."""
import json

from nw.materials.template_support import content, events, product, require
from nw.task_models import canonical


KINDS = {
    'identity_slice': '分次辨认身份', 'authority_response': '从他人的反应看出地位',
    'dialogue_turn': '对白改变当场进程', 'professional_voice': '职业观察与发话',
    'focus_boundary': '区分换地点、换对象与进入内心', 'qualified_claim': '有依据的未证判断',
    'interpreted_motive': '旁人对当事人动机的解释',
}
OUTCOMES = {
    'identity_slice': ('partial', 'revealed'), 'authority_response': ('observed',),
    'dialogue_turn': ('awaiting', 'answered', 'acted'), 'professional_voice': ('issued', 'performed'),
    'focus_boundary': ('location_cut', 'subject_cut', 'inside_pov'),
    'qualified_claim': ('estimate', 'possibility'), 'interpreted_motive': ('interpretation',),
}
ROLES = {
    'identity_slice': ('identity',), 'authority_response': ('authority', 'reaction'),
    'dialogue_turn': ('speech', 'response'), 'professional_voice': ('cue', 'speech', 'performed'),
    'focus_boundary': ('first', 'next'), 'qualified_claim': ('basis', 'judgment'),
    'interpreted_motive': ('decision', 'reading'),
}
REVIEW = {
    'identity_slice': '根据称谓、动作或本场已获准的披露辨认人物。把姓名、身世提早说穿须退修。',
    'authority_response': '指出谁行使了什么职权、别人如何回应；删去地位形容词后仍可辨认关系。',
    'dialogue_turn': '从实际台词辨认发话人、对象和当场目的，区分提出问题、得到回答、已经照做。',
    'professional_voice': '对照说者的职业声线和现场线索。遮住姓名，仍可从他具体注意什么、怎样发话辨认其身份。命令执行另引行动。',
    'focus_boundary': '辨清叙述地点、跟随谁和看谁。位置切换不凭空加赶路，写到一个人不自动进入其内心。',
    'qualified_claim': '依照原有知情范围保留判断依据、语气和归属，归属未明时保留未明，猜测或可能收益继续待证。',
    'interpreted_motive': '分别定位当事人说过或做过的事及旁人如何解释。解释只归解释者，无法据此确证他人真实动机。',
}
_EXTRA = {'professional_voice':'voice_quote', 'dialogue_turn':'purpose', 'qualified_claim':'qualifier',
          'authority_response':'position_quote', 'interpreted_motive':'experience_quote'}
_MARKS = {'identity':'身份线索', 'authority':'职权动作', 'reaction':'他人反应', 'speech':'实际台词',
          'response':'当场回应', 'cue':'职业线索', 'performed':'已做动作', 'first':'转移前', 'next':'转移后',
          'basis':'判断根据', 'judgment':'判断原句', 'decision':'当事人选择', 'reading':'旁人解释'}
FIXES = {'people_evidence':'用本场可以辨认的称谓、动作、台词或带限定的判断呈现此拍，区分谁所见、所说与所想。',
         'people_order':'把所见、发话及当场回应落实到可分别定位且先后相接的语句。'}
_HEDGES = ('估计','像是','看似','似乎','好像','约莫','约摸','大约','大概','可能','也许','兴许','想必',
           '大抵','多半','八成','猜','说不准','说不定','未必','恐怕','怕是','莫非','难道','未可知','不一定')
_FORMAT = {
    'identity_slice':'actor=所辨认的人，other=null。identity 拍摘批准的公开称谓/线索；获准揭晓用 revealed，否则 partial。',
    'authority_response':'actor=具有影响或职权者，other=回应者或人群(null)。position_quote 摘此人既有职责、关系或经历。authority、reaction 各摘一拍，可先反应再点出职权；有人听话只说明表现出的影响。',
    'dialogue_turn':'actor=说者，other=实际听者，purpose 写这句话要对方知道或做什么。speech 后未答 awaiting；answered/acted 另引听者 response。',
    'professional_voice':'actor=说者，other=听者或null。voice_quote 摘此人用词习惯或职责，practice_quote 摘职业、经历或工作。cue 引其可见或亲口点出的具体线索，speech 引据此发出的台词。issued 止于发话，performed 另引听者实际行动。',
    'focus_boundary':'actor=感知者或旁白null，other=描写对象或null。first、next 是转移前后的实际拍。location_cut 用旁白切换空间，另填 from_place、to_place 摘两拍不同位置；subject_cut 换描写对象，inside_pov 仅能进入本场视角自己的内心。',
    'qualified_claim':'actor=作判断者，未点明时null，other=被估计者或null。basis 摘看见或听到的根据，judgment 摘含 qualifier 的完整判断。outcome=estimate/possibility。',
    'interpreted_motive':'actor=解释者，other=被解释的人，experience_quote 摘解释者本人的经历/职责。decision 摘对方确实作出的选择，reading 摘归属解释者的判断，outcome=interpretation。',
}


def schema_fields(stage: str) -> dict:
    from nw.materials.phase_schema import TEXT, array, obj, strings
    if stage == 'scene_design':
        return {'people_needs': array(obj({**strings('scene','need_quote'), 'kind':{'enum':list(KINDS)}}))}
    if stage != 'expression_design':
        return {}
    person = {'type':['string','null']}
    role = {'enum': sorted({role for roles in ROLES.values() for role in roles})}
    step = obj({'role':role,'beat':{'type':'integer','minimum':1},'quote':TEXT})
    optional = (*_EXTRA.values(),'practice_quote','from_place','to_place')
    fields = {**strings('scene','outcome',*optional), 'kind':{'enum':list(KINDS)},
              'actor':person,'other':person,'steps':array(step,1)}
    return {'people_design': array(obj(fields, optional))}


def prompt(stage: str, payload: dict, products: dict, context: dict) -> str:
    if stage == 'scene_design':
        return ('按本场事件选人物写法 people_needs[{scene,kind,need_quote}]，引本场一个具体需求。'
                + '，'.join(f'{k}={v}' for k,v in KINDS.items()) + '。普通场同样可选，无此需求可省。')
    if stage != 'expression_design':
        return ''
    needs = _scene_needs(product(products,'scene_design'), products)
    if not needs:
        return ''
    payload['people_needs'] = needs
    instructions = ' '.join(_FORMAT[k] for k in dict.fromkeys(n['kind'] for n in needs))
    return ('按每项 people_needs 填people_design[{scene,kind,actor,other,outcome,steps:[{role,beat,quote}]}]。'
            'beat 从本场 guidance 第一拍起算，quote 在该拍 observable 中可定位。' + instructions)


def _snippet(quote: object, text: object) -> bool:
    return content(quote) and isinstance(text, str) and any(c.isalnum() for c in quote) and quote in text


def _scene_needs(plan: dict, products: dict) -> list[dict]:
    from nw.materials.passage_craft import _required
    needs = {(n['scene'],n['kind']):n for n in plan.get('people_needs', [])}
    for scene,rows in _required(products,plan).items():
        for row in rows:
            if row['kind'] in KINDS:
                needs.setdefault((scene,row['kind']), {'scene':scene,'kind':row['kind'],'need_quote':row['need_quote']})
    return list(needs.values())


def _needs(value: dict, products: dict) -> None:
    scenes = {r['key']:r['body'] for r in value.get('members', []) if r['kind']=='scene'}
    selected = {r['scene']:r['event'] for r in value.get('selected_events', [])}
    options = events(products)
    seen = set()
    needs = value.get('people_needs', [])
    require(isinstance(needs, list), '人物写法需求须为列表')
    for row in needs:
        require(isinstance(row,dict) and set(row)=={'scene','kind','need_quote'}, '人物写法需求字段不完整')
        scene, kind = row['scene'], row['kind']
        require(isinstance(scene,str) and scene in scenes and isinstance(kind,str) and kind in KINDS
                and (scene,kind) not in seen, '人物写法须属于实际场景和各自的制作需求')
        sources = [scenes[scene].get(k) for k in ('goal','conflict','choice','entering_state','planned_result')]
        event = options.get(selected.get(scene), {})
        sources.extend(event.get(k) for k in ('goal','setting','obstacle','event','completion_gate','completion_condition'))
        require(any(_snippet(row['need_quote'], s) for s in sources), '所引人物写法需求必须出自本场或已选事件')
        seen.add((scene,kind))


def _proof(row: dict, guides: list[dict]) -> dict:
    kind, outcome = row['kind'], row['outcome']
    actual = {}
    steps = row['steps']
    require(isinstance(steps,list), '人物流程须有可定位的实际段落')
    for step in steps:
        require(isinstance(step,dict) and set(step)=={'role','beat','quote'}, '人物落点字段不完整')
        role, number = step['role'], step['beat']
        require(role in ROLES[kind] and role not in actual and type(number) is int and 1 <= number <= len(guides),
                '人物落点角色重复、未知或指向另一场')
        guide = guides[number-1]
        require(_snippet(step['quote'],guide['observable']), '人物设计须摘本拍实际可写表现')
        actual[role] = (number, step['quote'], guide['narration'])
    roles = ROLES[kind]
    if outcome in ('awaiting','issued'):
        roles = roles[:-1]
    require(set(actual)==set(roles), '说过、请求与实际执行须各有相应的本场原文落点')
    ordered = [actual[r][0] for r in roles]
    require(kind=='authority_response' or ordered==sorted(ordered), '人物所依据的观察、发话和回应次序错误')
    require(len({(n,q) for n,q,_ in actual.values()})==len(actual), '同一句同一位置不能充作两项不同表现')
    return actual


def _witness(beat: dict, who: str | None) -> bool:
    return who is not None and (beat['owner']==who or who in beat.get('witnesses', []))


def _current(beat: dict, modes: tuple, owner: str | None) -> bool:
    return beat['time']=='current' and beat['mode'] in modes and beat['owner']==owner


def _practice(quote: object, card: dict) -> bool:
    positions = ('主角','主人公','反派','主角团','男主','女主','配角','普通角色','主要人物','protagonist','antagonist','major','supporting','ordinary')
    return content(quote) and quote.strip() not in positions and any(card.get(field) not in positions and _snippet(quote,card.get(field))
        for field in ('role','background','scene_function','relationship','behavior'))


def _validate_row(row: dict, proof: dict, cards: dict, pov: str) -> None:
    kind, actor, other, outcome = (row[k] for k in ('kind','actor','other','outcome'))
    need_actor = kind not in ('qualified_claim','focus_boundary')
    require(not need_actor or actor is not None, '此项人物写法缺少实际行为人')
    if kind == 'identity_slice':
        _, quote, beat = proof['identity']
        card = cards[actor]
        profile = card.get('casting', {})
        if outcome=='revealed':
            require(beat['basis_ref']==f'cast:{actor}:reveal', '揭晓身份须有该人物实际揭晓的前置')
        else:
            labels = [profile.get('public_identity'), profile.get('clue'), card.get('role'),card.get('name')]
            require(beat['basis_ref']!=f'cast:{actor}:reveal' and any(_snippet(v,quote) for v in labels),
                    '分次介绍要出现这个人物已经允许公开的称谓、职务或线索')
        require(other is None, '身份分次设计须指向一个人物')
    elif kind == 'authority_response':
        a,_,act = proof['authority']
        b,_,reaction = proof['reaction']
        require(_practice(row['position_quote'],cards[actor]), '职权或威望须有本人的职责、关系或经历作前置')
        require(a!=b and _current(act, ('speech','action'), actor) and actor!=other,
                '职权须由行使职权者实际做事或开口，并有他人的反应')
        require(_current(reaction, ('action','speech'),other) if other else
                _current(reaction, ('perception',),pov) or _current(reaction, ('summary',),None),
                '响应须属于实际他人或直接见到的人群')
        require(b<a or other is None or _witness(act,other), '回应先前的职权行动或命令要实际看到或听到')
    elif kind in ('dialogue_turn','professional_voice'):
        n,_,said = proof['speech']
        require(_current(said,('speech',),actor) and actor!=other
                and (other is None or other in said.get('witnesses', [])), '台词须由本人说出并标明在场的实际听者')
        if kind=='dialogue_turn':
            require(other is not None and content(row['purpose']), '一轮交流需要实际对象及要改变的具体事情')
        else:
            require(any(_snippet(row['voice_quote'], cards[actor].get(f)) for f in ('voice','role')),
                    '职业声音须引实际发话人的用词习惯或既定职责')
            require(_practice(row['practice_quote'],cards[actor]), '职业发话须有具体的本业或经历依据')
            _,_,cue = proof['cue']
            require(cue['time']=='current' and cue['mode'] in ('perception','action','speech') and _witness(cue,actor),
                    '说者须能看见相关表现、听到有关说法或在自己台词中指出现场问题')
        if outcome in ('answered','acted','performed'):
            nxt,_,response = proof['response' if kind=='dialogue_turn' else 'performed']
            modes = ('speech',) if outcome=='answered' else ('action',)
            require(nxt>n and other is not None and _current(response,modes,other),
                    '回应或执行须发生在发话以后，且属于实际听者本人')
            require(outcome!='answered' or _witness(response,actor), '答复要送达发问的人')
    elif kind == 'focus_boundary':
        n,first,before = proof['first']
        m,nxt,after = proof['next']
        require(n<m and before['time']==after['time']=='current','空间或注意切换须是可区分的前后拍')
        if outcome=='inside_pov':
            require(actor==other==pov and _current(after,('thought','inference'),pov),
                    '直接进入内心须属于本场的视角人物')
        elif outcome=='location_cut':
            require(actor is None and _current(after,('summary',),None)
                    and _snippet(row['from_place'],first) and _snippet(row['to_place'],nxt)
                    and row['from_place']!=row['to_place'],
                    '旁白切到另一处，需要由旁白定位；不能自动写成人物到了那里')
        else:
            require(actor in (None,pov) and after['mode'] in ('action','speech','summary','perception')
                    and (after['mode']!='perception' or after['owner']==actor),
                    '改变观察对象不能把其他人物的私下想法写成正在被观察的事')
            if other:
                card = cards[other]
                require(after['owner']==other or any(_snippet(v,nxt) for v in
                        (card.get('name'), card.get('casting',{}).get('public_identity'),card.get('role'))),
                        '应从该人物自己的言行或足以辨认他的公开称谓定位实际聚焦对象')
    elif kind == 'qualified_claim':
        _,_,basis = proof['basis']
        _,words,claim = proof['judgment']
        require(_snippet(row['qualifier'], words) and words.strip()!=row['qualifier'].strip(),
                '判断须引用含推测或可能性语气的实际表达')
        require(_current(claim,('summary',),None) if actor is None else
                _current(claim,('thought','inference','speech'),actor),'须区分归属未明的估计与人物本人的判断')
        require(basis['mode'] in ('action','perception','speech','summary') if actor is None else _witness(basis,actor),
                '判断所引的前置须是可供观察的依据或判断者自己知道的事')
    else:
        _,_,decision = proof['decision']
        _,_,reading = proof['reading']
        require(other is not None and actor!=other and _current(decision,('action','speech'),other)
                and _witness(decision,actor), '旁人的解释须先有他所见所闻的当事人实际选择')
        require(_current(reading,('thought','inference','speech'),actor)
                and any(_snippet(row['experience_quote'],cards[actor].get(f)) for f in ('background','role','behavior')),
                '对动机的解释须属于判断者，并有该人已设定的职务或经历支撑')


def validate(stage: str, value: dict, products: dict, context: dict) -> None:
    if stage=='scene_design':
        _needs(value,products)
    if stage!='expression_design':
        return
    plan = product(products,'scene_design')
    selected = {(row['scene'],row['kind']) for row in _scene_needs(plan, products)}
    uses_rows = value.get('people_design', [])
    require(isinstance(uses_rows,list),'人物表达安排须为列表')
    if not uses_rows and not selected:
        return
    scenes = {row['key']:row['body'] for row in plan['members'] if row['kind']=='scene'}
    cards = {row['card_id']:row['body'] for row in context.get('approved_cards', []) if row['kind']=='character'}
    cards.update({row['key']:row['body'] for row in product(products,'character_design').get('members', []) if row['kind']=='character'})
    used = set()
    uncertain = {}
    for row in uses_rows:
        require(isinstance(row,dict) and isinstance(row.get('kind'),str) and isinstance(row.get('scene'),str)
                and (row['scene'],row['kind']) in selected, '表达采用的人物写法需与本场已选需求一致')
        kind, scene = row['kind'], row['scene']
        extra = {_EXTRA[kind]} if kind in _EXTRA else set()
        if kind=='professional_voice':
            extra.add('practice_quote')
        if kind=='focus_boundary' and row.get('outcome')=='location_cut':
            extra |= {'from_place','to_place'}
        require(set(row)=={'kind','scene','actor','other','outcome','steps'} | extra
                and row['outcome'] in OUTCOMES[kind], '人物写法缺少具体条件或填入未知结果')
        people = {scenes[scene]['pov'], *scenes[scene].get('characters', [])}
        require(all(person is None or (isinstance(person,str) and person in people and person in cards)
                    for person in (row['actor'],row['other'])), '人物须已设计且在本场')
        guides = [g for g in value['guidance'] if g['scene']==scene]
        proof = _proof(row,guides)
        _validate_row(row,proof,cards,scenes[scene]['pov'])
        if kind in ('qualified_claim','interpreted_motive'):
            number = proof['judgment' if kind=='qualified_claim' else 'reading'][0]
            uncertain.setdefault(scene,set()).add(number)
        used.add((scene,kind))
    require(used==selected, '场卡选用的人物写法缺少本场实际表达')
    for scene, marked in uncertain.items():
        for i,guide in enumerate((g for g in value['guidance'] if g['scene']==scene),1):
            narration = guide['narration']
            ref = narration['basis_ref']
            if ref.startswith('beat:') and ref[5:].isdigit() and int(ref[5:]) in marked:
                require(i in marked or narration['mode'] in ('speech','thought','inference','action'),
                        '人物估计或他人动机解释不能被后续旁白单独认证为事实')


def uses(value: dict, scene: str) -> dict:
    result = {}
    for row in value.get('people_design', []):
        if row['scene']==scene:
            result.setdefault(row['kind'],set()).update(s['beat'] for s in row['steps'])
    return result


def attach(checks: list, records: dict, scene: str) -> None:
    beats = {c['narration_order']:c for c in checks if 'narration_order' in c}
    for use,row in enumerate(product(records,'expression_design').get('people_design', [])):
        if row['scene']!=scene:
            continue
        for step in row['steps']:
            check = beats[step['beat']]
            check.setdefault('people_design', []).append({**{k:v for k,v in row.items() if k!='steps'},
                                                         'use':use, 'role':step['role'], 'quote':step['quote']})
            visible = json.loads(check['binding']['observable'])
            visible.setdefault('people_craft', []).append({'kind':KINDS[row['kind']], 'role':step['role'],
                                                         'focus':step['quote'], 'outcome':row['outcome']})
            check['binding']['observable'] = canonical(visible)
            check['binding']['check'] += ' ' + REVIEW[row['kind']]


def review_prompt(checks: list[dict]) -> str:
    rows = [row for check in checks for row in check.get('people_design', [])]
    if not rows:
        return ''
    kinds = {row['kind'] for row in rows}
    marks = '、'.join(r+'=【'+_MARKS[r]+'】' for r in dict.fromkeys(row['role'] for row in rows))
    return ('人物专项的 reason 另起行按这个检查所含 role 写标签加本稿原句，各拍独立定位。使用'+marks+
            '。judgment 再写【限定词】摘判断原句中保留不确定的词。不能定位或语义错用报 [people_evidence]，先后错误报 [people_order]。'
            + ' '.join(REVIEW[k] for k in sorted(kinds)))


def assess(checks: list[dict], by_id: dict, draft) -> None:
    from nw.materials.passage_effects import _line, _span
    locations = {}
    for check in sorted(checks, key=lambda c:c.get('narration_order',0)):
        result = by_id[check['id']]
        for item in check.get('people_design', []):
            if result['status']!='pass':
                break
            role,number = item['role'],check['narration_order']
            span = _span(result,_MARKS[role],draft.id)
            qualifier = _line(result['reason'],'限定词') if role=='judgment' else ''
            if not span or role=='judgment' and (not _snippet(qualifier,span['quote'])
                    or not (qualifier==item['qualifier'] or any(hedge in qualifier for hedge in _HEDGES))):
                result.update(status='failed', narration_issue='people_evidence', reason=FIXES['people_evidence'])
                break
            key = item['scene'],item['use']
            previous = locations.get(key, [])
            if any((n!=number and pin['end']>span['start']) or (pin['start'],pin['end'])==(span['start'],span['end'])
                   for n,pin in previous):
                result.update(status='failed', narration_issue='people_order', reason=FIXES['people_order'])
                break
            locations.setdefault(key, []).append((number,span))


def judgment_spans(check: dict, row: dict, draft_id: str) -> list[dict]:
    from nw.materials.passage_effects import _span
    return [span for role in dict.fromkeys(r['role'] for r in check.get('people_design', ()))
            if role in ('judgment','reading') and (span:=_span(row,_MARKS[role],draft_id))]


def people_spans(check: dict, row: dict, draft_id: str) -> list[dict]:
    from nw.materials.passage_effects import _span
    return [span for role in dict.fromkeys(r['role'] for r in check.get('people_design', ()))
            if (span:=_span(row,_MARKS[role],draft_id))]


def mark_audience(check: dict, limit: dict) -> None:
    if any(row['role'] in ('judgment','reading') for row in check.get('people_design', [])):
        visible = json.loads(check['binding']['observable'])
        limit.update(reported_only=True, judgment_owner=visible['owner'])


def validate_audience(operations: list[dict], limits: list[dict]) -> None:
    judgments = [span for span in limits if 'judgment_owner' in span]
    if not judgments:
        return
    for op in operations:
        if op['claim'] not in ('suspicion','belief','plan') or op['holder']=='READER':
            continue
        incompatible = [s for s in judgments if s['judgment_owner']!=op['holder']]
        if incompatible and not any(all(q['end']<=s['start'] or q['start']>=s['end'] for s in incompatible)
                                    for q in op['evidence']):
            raise ValueError('MATERIAL_EVIDENCE: 旁人的判断不能单独成为当事人自己的想法或计划，须另引本人的反应')
