"""Paragraph decisions grounded in the scene's actual telling and reviewed manuscript."""
from collections import defaultdict
from fractions import Fraction
import re

from nw.materials.passage_sequence import EVENT_FIELDS
from nw.materials.template_support import content, events, product, require
from nw.materials.world_exchange import NUMBER, amount_value


KINDS = {'pace_switch':'概述与现场的详略转换', 'presentation_mode':'本拍概述或现场展开', 'reader_change':'读者所得与现场进展',
         'paragraph_turn':'段界的停顿或连读', 'local_handoff':'已办、可办与待揭示', 'detail_value':'删去细节的得失'}
FUNCTIONS = ('place','meaning','atmosphere','voice','rhythm','expectation')
CUT_REASONS = ('platform','repetition','unused_scale','explanation')
OUTCOMES = {'completed':'已完成','eligible':'已获条件','open':'尚待揭示'}
FIXES = {'effect_review':'核对本拍对读者的具体作用，区分读者理解和角色获知。',
         'effect_layout':'依当前稿两处的实际先后落实详略转换、断段或连读，让上拍的变化接到下拍。',
         'effect_estimate':'按本拍获准依据保留人数或比例的约略程度，删去对同一统计擅自给出的精确值。',
         'effect_handoff':'写清这一步办到哪里，取得的条件和有待发生的结果各用实际字句体现。'}
FORMATS = {
    'pace_switch': 'pace_switch 加 from_beat/from_cue、mode=resume_scene/enter_summary、reason 说明何处可略、为哪个变化展开。',
    'presentation_mode': 'presentation_mode 加 mode=summary/scene、owner（本拍 narration.owner）和 reason。概述交代读者当前需要的背景或惯例，现场展开由实际在场者完成其决定、承诺、误判或发现。',
    'paragraph_turn': 'paragraph_turn 给前一拍 from_beat/from_cue、mode=break/join、reason，按等待、停顿或回答决定断段或连读。',
    'reader_change': 'reader_change 加 before、after 分写读者先前理解与所得；story_cue 摘本拍另有的现场进展，仅读者改观填 null。',
    'local_handoff': 'local_handoff 加 status=completed/eligible/open 对应已办、取得条件、待解，next 在后两种写可做事项或问题，已办填 null。',
    'detail_value': 'detail_value 保留时 decision=keep，function=place/meaning/atmosphere/voice/rhythm/expectation，loss 说明删后实际损失。'
                    '可删时 decision=omit，function=platform/repetition/unused_scale/explanation，cut_text 填本项目拟删的确切冗句，'
                    'cut_scope=paragraph 限 cue 所在自然段，scene_lead 仅限本场第一拍开始前的题外引子。cue 指实际保留的表现，loss 说明删后仍靠什么成立。'}


def _needs(scene_plan: dict, products: dict) -> dict:
    from nw.materials.passage_craft import _required
    result = {(r['scene'],r['kind']):r['need_quote'] for r in scene_plan.get('effect_needs', ())}
    for scene, rows in _required(products,scene_plan).items():
        for row in rows:
            if row['kind'] in KINDS:
                result.setdefault((scene,row['kind']),row['need_quote'])
    for row in scene_plan.get('scene_progress', ()):
        if row['change']=='reader':
            result.setdefault((row['scene'],'reader_change'),row['basis_quote'])
    return result


def prompt(stage: str, payload: dict, products: dict, context: dict) -> str:
    if stage == 'plot_design' and (payload.get('chapter_handoff') or {}).get('reviewed_progress'):
        return ('前章 reviewed_progress 中 paragraph_outcome.completed 是办毕，eligible 为已获条件，open 为待解，'
                'reader 只交代读者理解。按已接受原句承接；人物获知或世界变化另用对应凭据。')
    if stage=='scene_design':
        return ('本场确有段落需求时填 effect_needs[{scene,kind,need_quote}]，摘该事件的完整需求。仅读者改观时人物与世界可保持原状。'
                +'、'.join(k+'='+v for k,v in KINDS.items())+'。')
    if stage != 'expression_design':
        return ''
    needs = _needs(product(products,'scene_design'),products)
    if not needs:
        return ''
    kinds = list(dict.fromkeys(k for _,k in needs))
    payload['effect_needs'] = [{'scene':s,'kind':k,'need_quote':q} for (s,k),q in needs.items()]
    return ('按 effect_needs 填 effects_plan，各行 scene,kind,beat(本场 guidance 序号从1起),cue(本拍 observable 短引)。'
            + ''.join(FORMATS[k] for k in kinds))


def schema_fields(stage: str, kinds=None) -> dict:
    if stage not in ('scene_design','expression_design'):
        return {}
    from nw.materials.phase_schema import array, obj, strings
    if stage=='scene_design':
        return {'effect_needs':array(obj({**strings('scene','need_quote'),'kind':{'enum':list(KINDS)}}))}
    number = {'type':'integer','minimum':1}
    nullable = {'type':['string','null']}
    pair = {'from_beat':number, **strings('from_cue','reason')}
    by_kind = {
        'pace_switch': {**pair,'mode':{'enum':['resume_scene','enter_summary']}},
        'paragraph_turn': {**pair,'mode':{'enum':['break','join']}},
        'presentation_mode': {'mode':{'enum':['summary','scene']},'owner':nullable,**strings('reason')},
        'reader_change': {**strings('before','after'),'story_cue':nullable},
        'local_handoff': {'status':{'enum':list(OUTCOMES)},'next':nullable}}
    shapes = [obj({**strings('scene','cue'),'kind':{'const':kind},'beat':number,**extra}) for kind,extra in by_kind.items()
              if kinds is None or kind in kinds]
    if kinds is None or 'detail_value' in kinds:
        base = {**strings('scene','cue','loss'),'kind':{'const':'detail_value'},'beat':number}
        shapes.extend([
            obj({**base,'function':{'enum':list(FUNCTIONS)}, 'decision':{'const':'keep'}}, ('decision',)),
            obj({**base,'function':{'enum':list(CUT_REASONS)},'decision':{'const':'omit'},
                 'cut_scope':{'enum':['paragraph','scene_lead']}, **strings('cut_text')})])
    return {'effects_plan':array({'anyOf':shapes})} if shapes else {}


def _quote(quote: object, text: str) -> bool:
    return content(quote) and any(c.isalnum() for c in quote) and quote in text


_ROUGH = r'大约|大概|大致|约莫|约有|约占|约为|差不多|差不离|接近|将近|近乎|近|约'
_STAT = re.compile(
    rf'(?P<before>{_ROUGH})?\s*(?:各占|各有|占了|占到|占|有)?\s*(?:了)?'
    rf'(?:(?P<half>一半一半|五五开|半数|各半|对半|一半)|百分之\s*(?P<percent_cn>{NUMBER})|'
    rf'(?P<percent>{NUMBER})\s*[%％]|(?P<tenth>{NUMBER})成|'
    rf'(?P<count>{NUMBER})(?P<extra>余|来|多)?\s*(?:名|位|人))(?P<after>左右|上下|前后|出头)?')
_BALANCED = re.compile(r'(?:两边|双方|两方|两拨|两队|两者)(?:人数|的人数|的人)?(?:也|都)?(?:相差不大|差不多|差不离|不相上下|大体相当|基本持平)|人数相差不大')
_RECOUNT = re.compile(r'^[ \t，,。；;（(：:]*(?:也就是(?:说)?|换算(?:下来)?|折合|准确地说|精确地说|精确到|确切地说|具体来说|恰好|正好)')
_CANCEL_ESTIMATE = re.compile(r'(?:并非|绝非|并不是|不是|并没有|恰好|正好|严格(?:地)?|精确(?:地)?(?:为|是|到)?|准确(?:地)?(?:为|是)?)\s*$')


def _statistics(text: str):
    """Read only ratios and headcounts. Distances, clock times and other subjects keep their own precision."""
    for match in _STAT.finditer(text):
        half = match['half']
        number = next((match[group] for group in ('percent_cn','percent','tenth','count') if match[group]), '')
        scale = 100 if match['percent_cn'] or match['percent'] else 10 if match['tenth'] else 1
        value = Fraction(1,2) if half else amount_value(number)/scale
        decimal = re.search(r'[.．点](.+)$',number)
        precision = len(decimal[1]) if decimal else 0
        rough = bool(match['before'] or match['after'] or match['extra'] or half in ('一半一半','五五开'))
        yield match, ('people' if match['count'] else 'ratio',value), rough, precision
    for match in _BALANCED.finditer(text):
        yield match, ('ratio',Fraction(1,2)), True, 0


def _summary_beat(plan: dict) -> int | None:
    if plan['kind']=='pace_switch':
        return plan['from_beat'] if plan['mode']=='resume_scene' else plan['beat']
    if plan['kind']=='presentation_mode' and plan['mode']=='summary':
        return plan['beat']
    return None


def _source_estimates(text: str) -> list[str]:
    by_amount = {}
    for match, amount, rough, _ in _statistics(text):
        if rough and not _CANCEL_ESTIMATE.search(text[:match.start()]):
            by_amount.setdefault(amount,match.group().strip())
    return list(by_amount.values())


def _check_estimate_excerpt(guide: dict, guides: list, products: dict, context: dict, bases: dict) -> None:
    narration = guide['narration']
    ref, quote = narration.get('basis_ref'), narration.get('basis_quote','')
    if not ref or next(_statistics(quote),None) is None:
        return
    scene = guide['scene']
    if ref.startswith('beat:'):
        text = guides[int(ref.split(':')[1])-1]['observable']
    else:
        from nw.materials.narration import scene_bases
        if scene not in bases:
            bases[scene] = scene_bases(products,context,scene)[scene]
        text = bases[scene][ref]['text']
    preserved = {key for _,key,rough,_ in _statistics(quote) if rough}
    inferred = [(m,key) for m,key,rough,_ in _statistics(text) if rough and key not in preserved]
    for occurrence in re.finditer(re.escape(quote),text):
        require(not any(m.start()<occurrence.end() and m.end()>occurrence.start() for m,_ in inferred),
                '概述的前置引文须保留原有人数或比例的估计程度')


def validate(stage: str, value: dict, products: dict, context: dict) -> None:
    if stage=='scene_design' and 'effect_needs' in value:
        selected = {r['scene']:r['event'] for r in value['selected_events']}
        available = events(products)
        needs = value['effect_needs']
        require(isinstance(needs,list),'段落需求须为本场选择列表')
        seen = set()
        for row in needs:
            require(isinstance(row,dict) and set(row)=={'scene','kind','need_quote'}
                    and isinstance(row['scene'],str) and row['scene'] in selected and isinstance(row['kind'],str)
                    and row['kind'] in KINDS and (row['scene'],row['kind']) not in seen and content(row['need_quote'])
                    and any(row['need_quote']==available[selected[row['scene']]].get(k) for k in EVENT_FIELDS),
                    '段落需求须逐场选用本场事件实际需求，不能借用别场或重复选择')
            seen.add((row['scene'],row['kind']))
    if stage != 'expression_design':
        return
    needs = _needs(product(products,'scene_design'),products)
    if not needs and 'effects_plan' not in value:
        return
    plans = value.get('effects_plan', [])
    require(isinstance(plans,list),'段落作用须为本场实际表达拍的列表')
    by_scene = defaultdict(list)
    for guide in value.get('guidance', ()):
        by_scene[guide['scene']].append(guide)
    seen = set()
    bases = {}
    for plan in plans:
        require(isinstance(plan,dict),'段落作用须为对象')
        scene, kind, beat = (plan.get(k) for k in ('scene','kind','beat'))
        require(isinstance(scene,str) and scene in by_scene and isinstance(kind,str) and kind in KINDS
                and type(beat) is int and 1<=beat<=len(by_scene[scene]) and (scene,kind,beat) not in seen,
                '段落作用须对应本场一处实际表达拍，同一作用不重复登记')
        seen.add((scene,kind,beat))
        guides = by_scene[scene]
        guide = guides[beat-1]
        require('narration' in guide and _quote(plan.get('cue'),guide['observable']),'落点须能在本拍可见表达中定位')
        base = {'scene','kind','beat','cue'}
        if kind in ('pace_switch','paragraph_turn'):
            require(set(plan)==base|{'from_beat','from_cue','mode','reason'},'详略或段界须有前拍、引文及采用理由')
            prior = plan['from_beat']
            require(type(prior) is int and 1<=prior<beat and _quote(plan['from_cue'],guides[prior-1]['observable'])
                    and content(plan['reason']),'切换理由和前拍引文须来自本场前文')
            if kind=='paragraph_turn':
                require(prior==beat-1 and plan['mode'] in ('break','join'),'段界须对应紧邻的两拍')
            else:
                require(plan['mode'] in ('resume_scene','enter_summary'),'详略转换方向无效')
                slow,quick = (beat,prior) if plan['mode']=='resume_scene' else (prior,beat)
                detail = next((s['detail'] for seq in value.get('passage_sequences', ()) if seq['scene']==scene
                               for s in seq['steps'] if s['beat']==quick),None)
                require((guides[quick-1]['narration']['mode']=='summary' or detail in ('summary','ellipsis'))
                        and guides[slow-1]['narration']['mode']!='summary','概述或跳时与展开须各有对应的表达拍')
        elif kind=='presentation_mode':
            narration=guide['narration']
            require(set(plan)==base|{'mode','owner','reason'} and content(plan['reason'])
                    and plan['owner']==narration['owner'] and (plan['mode']=='summary' and narration['mode']=='summary'
                    or plan['mode']=='scene' and narration['time']=='current' and content(plan['owner'])
                    and narration['mode'] in ('speech','action','thought','perception','inference')),
                    '概述或现场展开须对应本拍真实呈现手法、时序和获准的言行或感知人')
        elif kind=='reader_change':
            require(set(plan)==base|{'before','after','story_cue'} and content(plan['before']) and content(plan['after'])
                    and plan['before'].strip()!=plan['after'].strip()
                    and (plan['story_cue'] is None or _quote(plan['story_cue'],guide['observable'])),
                    '读者理解前后须有差别，另有事件变化时须能定位')
        elif kind=='local_handoff':
            require(set(plan)==base|{'status','next'} and isinstance(plan['status'],str) and plan['status'] in OUTCOMES
                    and (plan['next'] is None if plan['status']=='completed' else content(plan['next']) and plan['next']!=plan['cue']),
                    '已办、可办与待揭示须标清，确有的下一步另列')
        else:
            decision = plan.get('decision','keep')
            require(content(plan.get('loss')) and plan['loss'].strip()!=plan['cue'].strip(),
                    '删改对照须交代删后损失或何种表现仍可保留')
            if decision == 'omit':
                require(set(plan)==base|{'function','loss','decision','cut_text','cut_scope'} and plan['function'] in CUT_REASONS
                        and plan['cut_scope'] in ('paragraph','scene_lead') and content(plan['cut_text'])
                        and sum(c.isalnum() for c in plan['cut_text'])>=2 and plan['cut_text'] not in plan['cue']
                        and (plan['cut_scope']!='scene_lead' or beat==1),'拟删细节须指明原措辞、有限范围和要保留的落点')
            else:
                require(decision=='keep' and set(plan)-{'decision'}==base|{'function','loss'} and plan['function'] in FUNCTIONS,
                        '要能说明本场此处细节值得占篇幅的具体作用')
        summary = _summary_beat(plan)
        if summary:
            _check_estimate_excerpt(guides[summary-1],guides,products,context,bases)
    require(set(needs)=={(s,k) for s,k,_ in seen},
            '本章所需、场卡选定的段落作用和读者理解推进均须在本场落实，不能另加无需求的设计')


def uses(value: dict, scene: str) -> dict:
    result = defaultdict(set)
    for row in value.get('effects_plan', ()):
        if row['scene']==scene:
            result[row['kind']].add(row['beat'])
            if 'from_beat' in row:
                result[row['kind']].add(row['from_beat'])
    return dict(result)


def attach(checks: list[dict], records: dict, scene: str) -> None:
    beats = {r['narration_order']:r for r in checks if 'narration_order' in r}
    expression = product(records,'expression_design')
    guides = [g for g in expression.get('guidance', ()) if g['scene']==scene]
    visible = {'reader_change':'让读者从眼前细节改观，人物是否新知按其获知途径。',
               'local_handoff':'交代这一步实际达到的程度，保留取得的条件或尚待解答的问题。',
               'detail_value':'用具体现场细节实现本拍作用，把题外互动与正文分开。'}
    for item in expression.get('effects_plan', ()):
        if item['scene'] != scene:
            continue
        check, kind = beats[item['beat']], item['kind']
        check.setdefault('paragraph_effects', []).append(item.copy())
        summary = _summary_beat(item)
        if summary and 'summary_estimates' not in beats[summary]:
            quote = guides[summary-1]['narration'].get('basis_quote','')
            estimates = _source_estimates(quote)
            if estimates:
                beats[summary]['summary_estimates'] = estimates
                beats[summary]['binding']['check'] += ' 概述人数或比例时保留依据中的估计程度。'
        if kind=='paragraph_turn':
            tip = '与前拍在段界停顿后再写。' if item['mode']=='break' else '与前拍在同一自然段内连读。'
        elif kind=='pace_switch':
            tip = '从概述转到值得展开的新进展。' if item['mode']=='resume_scene' else '上拍的过程已看清，此处概述。'
        elif kind=='presentation_mode':
            tip = '概述本拍所需背景或惯例，读者看懂即可收住。' if item['mode']=='summary' else '展开这一次实际发生的言行、感知或判断。'
        elif kind=='detail_value' and item.get('decision')=='omit':
            tip = '保留本拍实际要传达的现场细节，略去题外文字或多余说明。'
        else:
            tip = visible[kind]
        check['binding']['check'] += ' '+tip
        if kind=='local_handoff' and item['status'] in ('open','eligible'):
            check['paragraph_pending'] = True


def _marks(item: dict) -> tuple:
    kind = item['kind']
    if kind=='reader_change':
        return ('读者所得','现场所得') if item['story_cue'] is not None else ('读者所得',)
    if kind=='local_handoff':
        return (OUTCOMES[item['status']],)
    if kind=='paragraph_turn':
        return ('段界前','段界后')
    if kind=='pace_switch':
        return ('详略前','详略后')
    if kind=='presentation_mode':
        return ('概述原句',) if item['mode']=='summary' else ('现场原句',)
    return ('保留原句',) if item.get('decision')=='omit' else ('细节原句',)


def review_prompt(checks: list[dict]) -> str:
    items = [i for row in checks for i in row.get('paragraph_effects', ())]
    estimated = any(r.get('summary_estimates') for r in checks)
    estimate_prompt = ('有 summary_estimates 时逐一用【概数1】【概数2】等摘出本拍相应人数或比例的完整稿句，'
                       '须在本项 evidence 中；按下标逐项核对统计对象、量级和约略程度，同段其他有依据的确数另计。') if estimated else ''
    if not items:
        return estimate_prompt
    marks = list(dict.fromkeys(mark for item in items for mark in _marks(item)))
    prompt = ('逐项核对 paragraph_effects 的本稿实际效果。通过项 reason 另起行按对应标记写「【项目名】本稿精确短引」，'
              '短引须在本项 evidence 中；段界前、详略前从设计的前拍审稿项自己的 evidence 摘取，无需重复引用。对应标记为'
              +'、'.join(marks)+'。')
    if any(i['kind']=='detail_value' for i in items):
        prompt += ('保留时想象删去本句，另写【删后】加现场作用的实际损失。omit 用【保留原句】定位本拍仍成立的现场，'
                   '【删后】交代保留了什么；核对 cut_scope 内冗句或同义重复的实际残留，已省略的内容无需引文。')
    if any(i['kind']=='paragraph_turn' for i in items):
        prompt += '段界前取前拍末处、段界后取后拍开始处，分别引文，按实际自然段核对。'
    if any(i['kind']=='presentation_mode' for i in items):
        prompt += '概述核对制度或经历交代到哪里即可收住，现场展开核对有权限的人此刻怎样做、说或发现。'
    prompt += estimate_prompt
    if any(i['kind']=='local_handoff' for i in items):
        prompt += '预告、凭证和获准不等于已经办完，说法和题外章题也不能证实结果。'
    if any(i['kind']=='local_handoff' and i['status']=='eligible' for i in items):
        prompt += ('【已获条件】定位已经发生的交付或授权。如果这拍也写到将来才办的事，另以【尚待兑现】'
                   '摘本项稿件 evidence 中的待办语句。若后续未写，注明【后续呈现】本段未写。')
    return prompt


def _line(reason: str, mark: str) -> str:
    prefix = f'【{mark}】'
    matches = [s.strip()[len(prefix):].strip() for s in reason.splitlines() if s.strip().startswith(prefix)]
    return matches[0] if len(matches)==1 else ''


def _span(row: dict, mark: str, draft_id: str) -> dict | None:
    quote = _line(row['reason'],mark)
    if not any(c.isalnum() for c in quote):
        return None
    pins = {}
    for span in row['evidence']:
        if span['id']!=draft_id or span['quote'].count(quote)!=1:
            continue
        start = span['start']+span['quote'].index(quote)
        pins[start] = {**span,'start':start,'end':start+len(quote),'quote':quote}
    return next(iter(pins.values())) if len(pins)==1 else None


def pending_spans(check: dict, row: dict, draft_id: str) -> list[dict]:
    """Scope uncertainty to the actual promise or question; physical receipt can remain factual."""
    marks = [{'open':'尚待揭示','eligible':'尚待兑现'}[item['status']]
             for item in check.get('paragraph_effects', ()) if item['kind']=='local_handoff'
             and item['status'] in ('open','eligible')]
    return [span for mark in marks if (span := _span(row,mark,draft_id))]


def effect_spans(check: dict, row: dict, draft_id: str) -> list[dict]:
    """The audience of this beat does not inherit its preceding beat's quotation."""
    if row['status']!='pass':
        return []
    marks = {mark for item in check.get('paragraph_effects', ()) for mark in _marks(item)
             if mark not in ('段界前','详略前')}
    if any(i['kind']=='local_handoff' and i['status']=='eligible' for i in check.get('paragraph_effects', ())):
        marks.add('尚待兑现')
    spans = [span for mark in marks if (span := _span(row,mark,draft_id))]
    return sorted(spans,key=lambda s:(s['start'],s['end']))


def _kept_estimate(source: str, quote: dict, text: str) -> bool:
    _, target, _, precision = next(_statistics(source))
    stats = list(_statistics(quote['quote']))
    hits = [match for match, amount, rough, digits in stats if amount==target and rough and digits<=precision]
    for hit in hits:
        if _CANCEL_ESTIMATE.search(text[:quote['start']+hit.start()]):
            continue
        # Also inspect an immediate arithmetic restatement even when the reviewer clipped the quotation early.
        suffix = text[quote['start']+hit.end():]
        recount = _RECOUNT.match(suffix)
        if recount:
            clause = re.split(r'[，,。；;！？!?\r\n]',suffix[recount.end():],maxsplit=1)[0]
            for match, amount, rough, _ in _statistics(clause):
                lead = clause[:match.start()].strip()
                direct = re.fullmatch(r'(?:[：:、]\s*)?(?:两边|双方|每边|两种|两者)?(?:分别|各自|共有|各有|比例为|占比为|为|是)?',lead)
                if direct and not rough and (target[0]==amount[0] or '各' in lead or '各有' in match.group()):
                    break
            else:
                return True
            continue
        return True
    return False


def assess(checks: list[dict], rows, draft) -> None:
    by_id = rows if isinstance(rows,dict) else {r['id']:r for r in rows}
    by_position = {(r['method_artifact']['scene'],r['narration_order']):r['id'] for r in checks
                   if 'narration_order' in r and isinstance(r.get('method_artifact'),dict)
                   and 'scene' in r['method_artifact']}
    for check in checks:
        for index, source in enumerate(check.get('summary_estimates',()),1):
            row = by_id[check['id']]
            if row['status']!='pass':
                break
            span = _span(row,f'概数{index}',draft.id)
            if not span or not _kept_estimate(source,span,draft.text):
                row.update(status='failed',narration_issue='effect_estimate',reason=FIXES['effect_estimate'])
        for item in check.get('paragraph_effects', ()):
            row,kind = by_id[check['id']],item['kind']
            if row['status']!='pass':
                break
            spans = [_span(row,m,draft.id) for m in _marks(item)]
            valid,code = all(spans),'effect_review'
            if kind in ('paragraph_turn','pace_switch'):
                code = 'effect_layout'
                prior = by_id.get(by_position.get((item['scene'],item['from_beat'])))
                spans[0] = _span({**row,'evidence':prior['evidence']},_marks(item)[0],draft.id) if prior and prior['status']=='pass' else None
                valid = all(spans)
                if valid:
                    before,after = spans
                    valid = before['end']<=after['start']
                    if valid and kind=='paragraph_turn':
                        gap = draft.text[before['end']:after['start']].replace('\r','\n')
                        valid = ('\n' in gap)==(item['mode']=='break')
            elif kind=='local_handoff':
                code = 'effect_handoff'
                if item['status']=='eligible':
                    implicit = _line(row['reason'],'后续呈现')=='本段未写'
                    cited = _span(row,'尚待兑现',draft.id)
                    valid = valid and (implicit != bool(cited))
            elif kind=='detail_value':
                loss = _line(row['reason'],'删后')
                valid = valid and content(loss) and loss!=spans[0]['quote'] and loss!=item['function']
                if valid and item.get('decision')=='omit':
                    start,end = spans[0]['start'],spans[0]['end']
                    if item['cut_scope']=='scene_lead':
                        candidate = draft.text[:start]
                    else:
                        left = draft.text.rfind('\n',0,start)+1
                        right = draft.text.find('\n',end)
                        candidate = draft.text[left:len(draft.text) if right<0 else right]
                    valid = item['cut_text'] not in candidate
            if not valid:
                row.update(status='failed',narration_issue=code,reason=FIXES[code])


def accepted_outcomes(rule: dict, row: dict, draft_id: str) -> list[dict]:
    result = []
    for item in rule.get('paragraph_effects', ()):
        if item['kind'] not in ('reader_change','local_handoff') or row['status']!='pass':
            continue
        spans = [_span(row,m,draft_id) for m in _marks(item)]
        if not all(spans):
            continue
        if item['kind']=='reader_change':
            outcome = {'status':'reader','before':item['before'],'after':item['after']}
            if len(spans)>1:
                outcome['story_evidence'] = [spans[1]]
            result.append({'paragraph_outcome':outcome,'evidence':[spans[0]],'change':'reader','possible_next_pressure':None})
        else:
            pending = pending_spans(rule,row,draft_id) if item['status']=='eligible' else []
            pressure = item['next'] if item['status']=='open' or pending else None
            result.append({'paragraph_outcome':{'status':item['status']},'evidence':spans,
                           'change':'setup' if item['status']=='open' else 'situation',
                           'possible_next_pressure':pressure,'pressure_evidence':(pending or spans) if pressure else []})
    return result
