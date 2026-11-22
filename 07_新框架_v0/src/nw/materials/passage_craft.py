"""Carry a chapter's selected techniques to the actual event, expression beat and draft."""
from nw.materials import passage_effects, passage_people, situated_passage
from nw.materials.passage_sequence import EVENT_FIELDS, ROLES as SEQUENCES
from nw.materials.template_support import content, events, product, require
from nw.passage_catalog import OBSERVATIONS
from nw.selection import _keywords


POLICY = 'scene-craft-v1'
MODULES = (situated_passage, passage_people, passage_effects)
EVENT_KINDS = (*OBSERVATIONS,*SEQUENCES)
FIXES = {'craft_source':'按选中的方法和适用边界落实本拍，指出当前稿具体哪里采用了它。'}


def schema_fields(stage: str, effect_kinds=None) -> dict:
    from nw.materials.phase_schema import array, obj, strings
    fields = {}
    for module in (situated_passage,passage_people):
        fields.update(module.schema_fields(stage))
    fields.update(passage_effects.schema_fields(stage,effect_kinds))
    if stage == 'plot_design':
        fields['event_techniques'] = array(obj({**strings('event','need_quote'), 'kind':{'enum':list(EVENT_KINDS)}}))
    if stage == 'scene_design':
        fields['craft_choices'] = array(obj({**strings('scene','event','need_quote','reason'),
                                            'kind':{'enum':[*OBSERVATIONS,'other']},
                                            'source_ref':{'type':['string','null']}}))
        fields['craft_deferrals'] = array(obj({**strings('scene','event','parent_event','reason','need_quote'),
                                              'kind':{'enum':list(EVENT_KINDS)}}))
    if stage == 'expression_design':
        fields['craft_applications'] = array(obj({**strings('scene','source_ref','operation','boundary_check'),
                                                  'beat':{'type':'integer','minimum':1}}))
    return fields


def _offers(products: dict, context: dict) -> list[dict]:
    from nw.production_methods.passage_sources import scene_candidates
    refs = [r for r in context.get('passage_references', []) if r['kind'] in OBSERVATIONS]
    if not refs:
        return []
    options = events(products)
    actions = product(products,'action_design').get('candidates', [])
    declared = product(products,'plot_design').get('event_techniques', [])
    offers = scene_candidates(refs,options,actions)
    # Preserve all requested kinds. Additional ideas compete for space on the event
    # they can serve, independently of how many other genres or scenes are in this plan.
    by_ref = {r['ref']:r for r in refs}
    picked = {}
    for event_id, event in options.items():
        wanted = {r['kind'] for r in declared if r['event'] in (event_id,event.get('predecessor'))}
        needs = _keywords([str(event.get(k,'')) for k in EVENT_FIELDS] +
                          [str(a.get('action','')) for a in actions if a.get('event') == event_id])
        extra = []
        selected = []
        for offer in offers:
            if event_id not in offer['events']:
                continue
            if offer['kind'] in wanted:
                selected.append(offer)
                continue
            ref = by_ref[offer['ref']]
            score = len(needs & _keywords([ref['condition'],*ref.get('prerequisites', []),*ref.get('operations', [])]))
            if score:
                extra.append((score,offer))
        selected.extend(row for _,row in sorted(extra,key=lambda pair:pair[0],reverse=True)[:2])
        for offer in selected:
            picked.setdefault(offer['ref'],{**offer,'events':[]})['events'].append(event_id)
    return list(picked.values())


def _required(products: dict, scene_plan: dict) -> dict:
    upstream = product(products, 'plot_design').get('event_techniques', [])
    parents = {e['id']:e['predecessor'] for e in product(products,'event_design').get('candidates',[])}
    deferred = {(d['scene'],d['parent_event'],d['kind']) for d in scene_plan.get('craft_deferrals',[])}
    needs = {}
    for item in scene_plan.get('selected_events', []):
        event = item['event']
        scene = item['scene']
        needs[scene] = [r for r in upstream if r['event'] == event or r['event'] == parents.get(event)
                        and (scene,r['event'],r['kind']) not in deferred]
    for row in scene_plan.get('craft_choices', []):
        if row.get('source_ref') and row.get('scene') in needs:
            needs[row['scene']].append(row)
    return {s:rows for s,rows in needs.items() if rows}


def prompt(stage: str, payload: dict, products: dict, context: dict) -> str:
    if context.get('scope') == 'book':
        return ''
    text = [s for module in MODULES if (s := module.prompt(stage,payload,products,context))]
    if stage == 'plot_design':
        text.append('章纲有明确呈现需求时把 event_techniques 填为 event、kind、need_quote（本节点目标/场地/阻力/完成条件原文）。'
                    '可选写法：' + '、'.join(k+' '+v[0] for k,v in OBSERVATIONS.items()) +
                    '。每个事件可另选一种连续安排 procedure_branch（先示范再分岔）或 focus_relay（循可见线索转焦），可结合多种单项。')
    elif stage == 'scene_design':
        offers = _offers(products,context)
        if offers:
            payload['craft_candidates'] = offers
            text.append('对获推荐的本场事件填 craft_choices，选用时写 scene,event,kind,source_ref,need_quote（该事件具体字段原文）和 reason。'
                        '以来源条件及禁用情形判断本场是否适用。均不适用写 kind=other、source_ref=null 和具体理由。')
        if requested := product(products,'plot_design').get('event_techniques'):
            payload['event_techniques'] = requested
            text.append('本场节点及其父节点已经指定的写法须交给相应场卡需求，其中两种连续安排用 passage_choices。派生事件若另有用途，可在 craft_deferrals '
                        '填 scene,event,parent_event,kind,need_quote（派生事件的实际字段原文）及具体 reason，再决定后续怎样呈现。')
    elif stage == 'expression_design':
        scene_plan = product(products,'scene_design')
        needs = _required(products,scene_plan)
        if needs:
            payload['scene_techniques'] = needs
            text.append('把各场已采用的写法落实到本场对应的实际表达拍。')
        selected = {r['source_ref'] for r in scene_plan.get('craft_choices', []) if r['source_ref']}
        if selected:
            payload['selected_craft_methods'] = [r for r in context['passage_references'] if r['ref'] in selected]
            text.append('craft_applications 每项填 scene、source_ref、从该 ref 的 operations 摘一条完整操作、'
                        '放在 operation 字段；beat 填本场呈现该写法的一拍。boundary_check 引用所选事件 need_quote，说明怎样守住来源边界。')
    return '\n'.join(text)


def _require_event(row: dict, options: dict) -> None:
    event = options.get(row['event'], {})
    require(content(row['need_quote']) and any(row['need_quote'] == event.get(k) for k in EVENT_FIELDS),
            '须引用本章选中事件的具体需求')


def validate(stage: str, value: dict, products: dict, context: dict) -> None:
    for module in MODULES:
        module.validate(stage,value,products,context)
    if stage == 'plot_design':
        options = {r['id']:r for r in value.get('event_nodes',[])}
        seen = set()
        for row in _rows(value,'event_techniques',{'event','kind','need_quote'}):
            require(isinstance(row['event'],str) and row['kind'] in EVENT_KINDS and (row['event'],row['kind']) not in seen,
                    '章纲写法重复或未知')
            if row['kind'] in SEQUENCES:
                require(not any((row['event'],kind) in seen for kind in SEQUENCES),'同一事件须明确主要的连续安排')
            _require_event(row,options)
            seen.add((row['event'],row['kind']))
    elif stage == 'scene_design':
        refs = {r['ref']:r for r in _offers(products,context)}
        options = events(products)
        scenes = {r['scene']:r['event'] for r in value['selected_events']}
        parent_needs = {(r['event'],r['kind']) for r in product(products,'plot_design').get('event_techniques', [])}
        deferred = set()
        for row in _rows(value,'craft_deferrals',{'scene','event','parent_event','kind','need_quote','reason'}):
            s, e, parent, k = row['scene'], row['event'], row['parent_event'], row['kind']
            require(scenes.get(s)==e and options.get(e,{}).get('predecessor')==parent and
                    (parent,k) in parent_needs and (s,k) not in deferred and content(row['reason']),
                    '只能在派生事件需求有变化时说明为何推迟原节点的写法')
            _require_event(row,options)
            deferred.add((s,k))
        chosen = {}
        for row in _rows(value,'craft_choices',{'scene','event','kind','source_ref','need_quote','reason'}):
            s, k, ref = row['scene'], row['kind'], row['source_ref']
            require(scenes.get(s) == row['event'] and content(row['reason']), '方法取舍须属于本场所选事件并说明理由')
            _require_event(row,options)
            kinds = chosen.setdefault(s,set())
            require(k not in kinds and 'other' not in kinds and (k != 'other' or not kinds), '同场取舍重复或矛盾')
            if k == 'other':
                require(ref is None, '拒用时不能登记采用来源')
            else:
                require(isinstance(ref,str) and ref in refs and refs[ref]['kind'] == k and row['event'] in refs[ref]['events'],
                        '此写法须来自给本场事件的同类型候选')
            kinds.add(k)
        offered_events = {eid for r in refs.values() for eid in r['events']}
        require(all(s in chosen for s,e in scenes.items() if e in offered_events), '本场获推荐的方法尚未说明取舍')
        designed = {(r['scene'],r['kind']) for r in value.get('situated_needs', [])}
        sequences = {(r['scene'],r['kind']) for r in value.get('passage_choices', [])}
        for s, rows in _required(products,value).items():
            for need in rows:
                if need['kind'] in situated_passage.KINDS:
                    require((s,need['kind']) in designed, '章纲或来源选定的现场写法缺少本场设计前置')
                if need['kind'] in SEQUENCES:
                    require((s,need['kind']) in sequences, '章纲指定的连续安排尚未交给本场对应的段落写法')
    elif stage == 'expression_design':
        scene_plan = product(products,'scene_design')
        needs = _required(products,scene_plan)
        adopted = {(s,r['source_ref']):r for s,rows in needs.items() for r in rows if r.get('source_ref')}
        sources = {r['ref']:r for r in context.get('passage_references', [])}
        used = {s:{k:beats for mod in MODULES for k,beats in mod.uses(value,s).items()} for s in needs}
        for s,rows in needs.items():
            for r in rows:
                if r['kind'] not in SEQUENCES:  # validate_sequences owns the actual ordered run of these beats.
                    require(used[s].get(r['kind']), f"场景 {s} 尚未落实上游指定的 {r['kind']} 写法")
        for row in _rows(value,'craft_applications',{'scene','source_ref','operation','beat','boundary_check'}):
            key = row['scene'],row['source_ref']
            require(key in adopted, '表达方法重复、串场或未经本场采用')
            choice = adopted.pop(key)
            require(row['operation'] in sources[key[1]]['operations'] and type(row['beat']) is int
                    and row['beat'] in used[key[0]][choice['kind']], '须将此来源的一条真实操作落实到对应写法的实际拍')
            why = row['boundary_check']
            require(content(why) and choice['need_quote'] in why and content(why.replace(choice['need_quote'],'')),
                    '须用本场需求解释来源的适用边界')
        require(not adopted, '本场选用的方法尚未交给表达')


def _rows(value: dict, field: str, keys: set) -> list:
    rows = value.get(field, [])
    require(isinstance(rows,list) and all(isinstance(r,dict) and set(r)==keys for r in rows), field+' 的产物字段不符')
    return rows


def attach(checks: list[dict], records: dict, scene: str, context: dict) -> None:
    situated_passage.attach(checks,records,scene,context)
    passage_people.attach(checks,records,scene)
    passage_effects.attach(checks,records,scene)
    beats = {c['narration_order']:c for c in checks if 'narration_order' in c}
    for row in product(records,'expression_design').get('craft_applications',[]):
        if row['scene'] != scene:
            continue
        ref = next((r for r in context['passage_references'] if r['ref']==row['source_ref']),None)
        require(ref and row['beat'] in beats, '本场写审依据与冻结版本不符')
        beats[row['beat']].setdefault('craft_sources',[]).append({**row, 'kind':ref['kind'], 'condition':ref['condition'],
            'boundary':ref['boundary'], 'prerequisites':ref['prerequisites'], 'non_applicability':ref['non_applicability']})


def review_prompt(checks: list[dict]) -> str:
    parts = [text for module in MODULES if (text := module.review_prompt(checks))]
    if any(c.get('craft_sources') for c in checks):
        parts.append('按每项检查的 craft_sources 数组从1编号，对各来源在 reason 另起行写【来源1落点】本稿的准确短引、'
                     '【来源1适用】说明该句怎样采用操作并守住本场边界；第二条依次用来源2。稿件证据无法支持时退修。')
    return ' '.join(parts)


def assess_sources(checks: list[dict], rows: dict, draft_id: str) -> None:
    # The earlier half of a cut is cited from its own review. The review of the
    # later beat identifies which of those words actually led into the cut.
    preceding = {}
    for target in checks:
        target_row = rows[target['id']]
        if target_row['status']!='pass':
            continue
        for effect in target.get('paragraph_effects',()):
            if effect['kind'] in ('pace_switch','paragraph_turn'):
                label = '详略前' if effect['kind']=='pace_switch' else '段界前'
                preceding.setdefault((effect['scene'],effect['from_beat'],effect['kind']),[]).append((target_row,label))
    for check in checks:
        row = rows[check['id']]
        if row['status']!='pass':
            continue
        for n, source in enumerate(check.get('craft_sources',()),1):
            wording = passage_effects._span(row,f'来源{n}落点',draft_id)
            fit = passage_effects._line(row['reason'],f'来源{n}适用')
            kind = source['kind']
            own = []
            for field, locate in (('situated_checks',situated_passage.situated_spans),('people_design',passage_people.people_spans),
                                  ('paragraph_effects',passage_effects.effect_spans)):
                own.extend(locate({field:[v for v in check.get(field,()) if v['kind']==kind]},row,draft_id))
            for later, label in preceding.get((source.get('scene'),source.get('beat'),kind),()):
                if pin := passage_effects._span({**later,'evidence':row['evidence']},label,draft_id):
                    own.append(pin)
            if (not wording or not any(s['start']<wording['end'] and wording['start']<s['end'] for s in own)
                    or not content(fit) or fit in (wording['quote'],source['operation'],source['boundary_check'])):
                row.update(status='failed',narration_issue='craft_source',reason=FIXES['craft_source'])
                break
