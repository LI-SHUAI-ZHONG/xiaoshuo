
"""Trace six geographical and institutional effects to the author's approved history."""
from collections import defaultdict
from collections.abc import Iterable
import re

from nw.materials.semantic_application import require
from nw.materials.world_exchange import NUMBER, UNIT, amount_value
from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00694': '具体地形对当地资源通行或分配的限制、因而发生的双方争端和地域范围',
    'C00705': '创始期确立先验的实际事件、规则内容、生效条件和延续机制',
    'C00708': '扩张期的实际拓展事件、区域及路线、边界或土地用途在此前此后的变化',
    'C00709': '动荡期发生的制度或利益变化、形成的实际争端及矛盾延续的条件',
    'C00713': '固化期已施行的制度、实际群体和资格、稳定的阶层位置及资源分配',
    'C00714': '固化期形成权力的制度事件、权力方可支配的事项、执行方及程序凭据',
}
_PERIOD = r'(?:[\u3400-\u9fff]{1,8}期)'
_NAME = r'[\u3400-\u9fffA-Za-z0-9]{2,22}?'
_TEXT = r'[^，,。；;：:\n\r！？!?]{2,40}?'
_COMMA = r'\s*[，,]\s*'
_SENTENCE = re.compile(r'[^。；;！？!?\r\n]+[！？!?]?')
_SCOPES = (
    re.compile(rf'^(?:在)?(?P<period>{_PERIOD})(?:的|{_COMMA})(?P<region>{_NAME})(?:{_COMMA})?(?=因|由于)'),
    re.compile(rf'^(?P<region>{_NAME})(?:在|于)(?P<period>{_PERIOD})(?:{_COMMA})?(?=因|由于)'),
)
_REGIONAL = re.compile(rf'^(?:在)?(?P<region>{_NAME})(?:{_COMMA})?(?=因|由于)')
_UNSET = re.compile(r'待定|未定|据传|据说|听说|传闻|可能|未知|计划|筹备|拟定|正拟|预定|打算|准备|预计|'
                    r'疑似|暂拟|或许|若是|假设|示例|举例|讨论|传言|并未|并非|不是|作废|撤销|失效|不再适用')
_GENERIC = re.compile(r'(?:某个?|某一|有关|相关|相应|指定|原有|现有|实际|具体|既定|已定|各个|当地|本地|其他|某项)?'
                      r'(?:地点|地区|区域|时期|条件|范围|物资|东西|货物|资源|双方|组织|群体|机构|单位|权力方|'
                      r'执行者|角色|凭证|文件|历史事件|规则|权益|争端|事项|制度|对象|资源分配|某物|地形|通行|状态)')
_PERIODS = {'C00705': '创始期', 'C00708': '扩张期', 'C00709': '动荡期', 'C00713': '固化期', 'C00714': '固化期'}
_TERRAIN = rf'{_NAME}(?:峡谷?|山口|河口|海峡|山脊|渡口|山道|隘口|河道|山脉|盆地|平原|高原|谷地|群岛|水系|滩|河|岭|堤|湾|渠)'
_GEOGRAPHIC = re.compile(rf'(?P<terrain>{_TERRAIN})(?:阻断|封阻|限制|隔断|截断|阻隔|垄断|缺少|缺乏|分隔|截留|汇集|独占)(?P<resource>{_NAME})')
_INSTITUTION = re.compile(rf'{_NAME}(?:废除|颁布|确立|取消|收回|夺取|没收|改征|推行|施行|接管|剥夺|改订|'
                          rf'重订|剥离|接收|封存|征用|强征|废止|割让|封禁)(?:了)?{_NAME}')
_FOUNDING = re.compile(rf'{_NAME}(?:建立|颁布|铸成|铸造|确立|创立|立下|订立|修筑|建成|签订|开辟|'
                       rf'奠定|启动|缔结|修成|立起){_NAME}')
_EXPANSION = re.compile(rf'{_NAME}(?:开凿|收购|并入|占领|兼并|开拓|占据|吞并|修筑|开辟|打通|修通|筑成|'
                        rf'拓宽|割让|迁移|扩建|封锁|攻占|收复|围垦|疏浚|纳入|夺取){_NAME}')
_MECHANISM = re.compile(r'校准|巡查|核验|复核|补刻|修补|续刻|维护|更换|重刻|补充|轮换|监测|供给|'
                        r'执行|巡守|复诵|宣读|续签|修缮|补给|重新刻录')
_GATES = {'C00694': _GEOGRAPHIC, 'C00705': _FOUNDING, 'C00708': _EXPANSION,
          'C00709': _INSTITUTION, 'C00713': _INSTITUTION, 'C00714': _INSTITUTION}
_OPEN = ('通航', '开放', '开通', '通行', '通船', '可通航', '可通行', '允许通航', '允许通行', '恢复通航')
_CLOSED = ('禁航', '封航', '封闭', '关闭', '禁行', '封锁', '中断', '禁止通航', '禁止通行', '停止通航', '不可通行', '不通船')
_ROUTE_STATE = '(?:' + '|'.join(sorted((*_OPEN, *_CLOSED), key=len, reverse=True)) + ')'
_COMBAT = rf'(?P<first>{_NAME})(?:与|和|同)(?P<second>{_NAME})围绕(?P<subject>{_NAME})的(?:争夺|争端|冲突)(?:成为|构成|形成)(?:当地|本地)?(?:的)?核心矛盾'
_PATTERNS = {
    'C00694': _COMBAT,
    'C00705': (rf'(?:确立|定下|立下)(?P<subject>{_NAME})的先验(?:规则|法则)[：:](?P<premise>{_TEXT})'
               + _COMMA + rf'(?:此后|后来|此后一直)(?:由|靠|依靠)(?P<maintenance>{_TEXT})(?:维持|维护|保持生效)'),
    'C00708': (rf'(?P<subject>{_NAME})(?:的(?P<aspect>用途|边界|辖界|通行状态))?(?:由|从)(?P<before>{_NAME})'
               rf'(?:改为|改作|转为|迁至|移至|改至|划为|变为)(?P<after>{_NAME})'),
    'C00709': _COMBAT,
    'C00713': (rf'(?P<entry>持|凭|缴清|服满|修完|继承)(?P<permit>{_NAME})的(?P<subject>{_NAME})(?:被列为|划入|定为)(?P<rank>{_NAME})'
               + _COMMA + rf'(?P<distribution>按户|按人|按籍|据此)(?:取得|获配|分得|领取)(?P<allocation>{_TEXT})'),
    'C00714': (rf'(?P<holder>{_NAME})(?:取得|掌握|获授)(?P<subject>{_NAME})的(?P<power>裁定权|分配权|征收权|调配权|'
               rf'审批权|处置权|管辖权|调拨权|统辖权)' + _COMMA + rf'(?P<exclusive_executor>仅|只)?由(?P<executor>{_NAME})(?:'
               rf'(?P<exclusive_warrant>仅|只)?(?:凭|依据|按照)(?P<warrant>{_NAME})执行|(?:通过|以)(?P<procedure>{_TEXT})(?:执行|落实))'),
}
_MATCHES = {key: re.compile(pattern) for key, pattern in _PATTERNS.items()}
_QUOTA = re.compile(rf'每(?P<interval>日|天|周|旬|月|季|年)\s*(?P<count>{NUMBER})\s*(?P<unit>{UNIT})(?P<item>{_NAME})')
_PREMISE = re.compile(rf'(?P<actor>{_NAME})(?:只能|只可|仅可)在(?P<window>{_NAME})时(?P<action>{_NAME})')
_WINDOWS = {'退潮': '退潮', '落潮': '退潮', '涨潮': '涨潮', '白天': '白昼', '白昼': '白昼', '夜间': '夜间', '夜里': '夜间'}
_OPPOSITE_WINDOW = {'退潮': '涨潮', '涨潮': '退潮', '白昼': '夜间', '夜间': '白昼'}


def _concrete(text: str) -> bool:
    return not _GENERIC.fullmatch(text) and not _UNSET.search(text) and not re.match(r'某种|某个|有人|某地|某方', text)


def _state(text: str) -> str:
    if text in _OPEN:
        return '通航'
    if text in _CLOSED:
        return '封闭'
    return text


def _subject_label(key: str, e: dict) -> str:
    subject = e['subject']
    if key in ('C00694', 'C00709'):
        return subject + '之争'
    if key == 'C00708':
        return subject + '的' + ('通行' if e['aspect'] == '通行状态' else e['aspect']) + '变更'
    if key == 'C00713':
        return subject + '的' + e['rank'] + '资格'
    if key == 'C00714':
        return subject + '的' + e['power']
    return subject


def _bounds(key: str, e: dict, limits: str) -> dict | None:
    subject, region, period = map(re.escape, (_subject_label(key, e), e['region'], e['period']))
    if key == 'C00705':
        expression = subject + rf'(?:仅在|只在){region}(?:的)?(?P<condition>{_TEXT})(?:时|后)(?:生效|有效|适用)'
    else:
        expression = subject + rf'(?:仅适用于|只适用于|仅限于|限于){region}(?:的)?{period}'
        if key in ('C00708', 'C00714'):
            expression += rf'(?:{_COMMA}(?:且)?(?:仅在|只在)(?P<qualifier>{_TEXT})时(?:生效|适用))?'
        if key == 'C00709':
            expression += _COMMA + rf'(?:只要|若)(?P<condition>{_TEXT}){_COMMA}(?:该|上述)矛盾(?:就会|便|仍会|将)(?:延续|持续)'
    bounds = []
    for sentence in _SENTENCE.findall(limits):
        sentence = sentence.strip()
        if (bound := re.fullmatch(expression, sentence)) and all(_concrete(t) for t in bound.groupdict().values() if t):
            bounds.append(dict(boundary=sentence, **{k: v for k, v in bound.groupdict().items() if v}))
        elif sentence.startswith((_subject_label(key, e), '上述变更', '该历史规则', '本先验规则')):
            # An extra limitation on the same effect cannot be silently discarded.
            return None
    return bounds[0] if len(bounds) == 1 else None


def _effect(key: str, body: str, region: str, period: str) -> dict | None:
    parts = re.split(_COMMA, body, maxsplit=1)
    if len(parts) != 2 or _UNSET.search(body):
        return None
    cause = re.fullmatch(r'(?:因|由于)(.+)', parts[0])
    if not cause or not (event := _GATES[key].fullmatch(cause[1])):
        return None
    result = _MATCHES[key].fullmatch(parts[1])
    if result is None and key == 'C00708':
        result = re.fullmatch(rf'原(?:本|先)(?P<before>{_ROUTE_STATE})的(?P<subject>{_NAME})'
                              rf'(?:因而|从此|由此|随之)(?:改为|转为|恢复)?(?P<after>{_ROUTE_STATE})', parts[1])
    if not result:
        return None
    data = {k: v for k, v in (event.groupdict() | result.groupdict()).items() if v is not None}
    if not all(_concrete(t) for t in data.values()):
        return None
    if key in ('C00694', 'C00709') and data['first'] == data['second']:
        return None
    if key == 'C00705' and (not _MECHANISM.search(data['maintenance'])
                             or not re.search(r'只能|仅|不得|一律|每当|必|无法|才|不可|均|须|则|只在|总会', data['premise'])):
        return None
    if key == 'C00714' and 'procedure' in data and not re.search(r'核验|封锁|盘点|扣留|逐户登记|验票|轮值|逐笔复核|巡查|封存|查验|轮岗', data['procedure']):
        return None
    if key == 'C00708':
        aspect = data.setdefault('aspect', '通行状态')
        before, after = data['before'], data['after']
        if (aspect == '通行状态' and not (re.fullmatch(_ROUTE_STATE, before) and re.fullmatch(_ROUTE_STATE, after))
                or _state(before) == _state(after)):
            return None
    if key == 'C00713' and (quota := _QUOTA.fullmatch(data['allocation'])):
        data['quota'] = quota.groupdict()
    if key == 'C00705' and (premise := _PREMISE.fullmatch(data['premise'])):
        data['constrained_action'] = premise.groupdict()
    anchors = [data['subject'], event[0]]
    if key in ('C00694', 'C00709'):
        anchors.extend([data['first'], data['second']])
    elif key == 'C00714':
        anchors.extend([data['holder'], data.get('warrant') or data['procedure']])
    elif key == 'C00713':
        anchors.append(data['permit'])
    return dict(region=region, period=period, event=event[0], anchors=anchors, **data)


def approved_history_impact(card: dict, key: str) -> dict | None:
    texts = approved_text(card)
    if key not in RULES or not texts:
        return None
    rule, limits = texts
    if re.search(r'(?:本卡|上述内容|整张卡|本段历史)(?:所述)?(?:均|全|仅|只)?(?:作|为|是|属)(?:设想|推演|示例|假设|传闻)', rule + '。' + limits):
        return None
    candidates = []
    for sentence in _SENTENCE.findall(rule):
        sentence = sentence.strip()
        scope = next((m for form in _SCOPES if (m := form.match(sentence))), None)
        if scope is None and key == 'C00694':
            scope = _REGIONAL.match(sentence)
        if not scope or not _concrete(scope['region']):
            continue
        period = scope.groupdict().get('period', '')
        if period != _PERIODS.get(key, period):
            continue
        if not (e := _effect(key, sentence[scope.end():], scope['region'], period)):
            continue
        if bound := _bounds(key, e, limits):
            candidates.append(e | bound)
    if len(candidates) != 1:
        return None
    evidence = candidates[0]
    if any(sentence.strip().startswith((_subject_label(key, evidence), '上述变更', '该历史规则')) and _UNSET.search(sentence)
           for sentence in _SENTENCE.findall(rule)):
        return None
    if _has_conflict(key, evidence, (rule, limits)):
        return None
    return card_proof(card, rule, limits, evidence)


def impact_comparison(key: str, evidence: dict) -> tuple[tuple, tuple] | None:
    """Compare only exclusive outcomes for the same period, place and historical subject."""
    scope = (evidence['region'], evidence['period'], evidence['subject'])
    if key == 'C00708':
        return (*scope, evidence['aspect'], evidence.get('qualifier')), (_state(evidence['after']),)
    if key == 'C00713':
        return (*scope, '持' if evidence['entry'] == '凭' else evidence['entry'], evidence['permit']), (evidence['rank'],)
    return None


def impact_comparisons(key: str, evidence: dict) -> Iterable[tuple[tuple, tuple, bool]]:
    """Yield scope, outcome and whether a different outcome excludes this historical fact."""
    if base := impact_comparison(key, evidence):
        subject, outcome = base
        yield subject, outcome, True
        if key == 'C00713' and (quota := evidence.get('quota')) and evidence['distribution'] != '据此':
            identity = (*subject, evidence['distribution'], quota['item'], quota['interval'].replace('天', '日'))
            yield identity, (quota['unit'], amount_value(quota['count'])), True
    scope = evidence['region'], evidence['period'], evidence['subject']
    if key == 'C00705' and (action := evidence.get('constrained_action')):
        if window := _WINDOWS.get(action['window']):
            # Two calendars can impose independent restrictions on the same action (e.g. tide and daylight).
            dimension = frozenset((window, _OPPOSITE_WINDOW[window]))
            identity = (*scope, evidence['condition'], action['actor'], action['action'], dimension)
            yield identity, (window,), True
    elif key == 'C00714':
        grant = (*scope, evidence['holder'], evidence['power'], evidence.get('qualifier'))
        yield (*grant, '执行方'), (evidence['executor'],), bool(evidence.get('exclusive_executor'))
        if evidence.get('warrant'):
            yield (*grant, '凭据', evidence['executor']), (evidence['warrant'],), bool(evidence.get('exclusive_warrant'))


def consistent_impact_cards(key: str, cards: list[dict]) -> list[dict]:
    if len(cards) < 2:
        return cards
    facts = defaultdict(list)
    for index, card in enumerate(cards):
        for identity, outcome, exclusive in impact_comparisons(key, card['evidence']):
            facts[identity].append((index, outcome, exclusive))
    held = set()
    for group in facts.values():
        exclusive = {outcome for _, outcome, sole in group if sole}
        if exclusive and len({outcome for _, outcome, _ in group}) > 1:
            # Only positive grants contradicted by an exclusive assertion need reconciliation.
            held.update(i for i, outcome, sole in group if sole or exclusive != {outcome})
    return [card for i, card in enumerate(cards) if i not in held]


def _claim_pattern(key: str, e: dict) -> str:
    subject = re.escape(e['subject'])
    if key == 'C00708':
        if e['aspect'] == '通行状态':
            previous = rf'(?:(?:由|从)(?P<before>{_ROUTE_STATE})(?:改为|转为|变为))?'
            return (subject + r'(?:的通行状态)?(?:却|至此)?(?:已经|现已|仍然|始终|一直|仍为|仍|已|现在|当前)?'
                    + r'(?P<negated>并未|并非|没有|从未|未曾|未)?' + previous + rf'(?P<state>{_ROUTE_STATE})'
                    + r'(?!区|段|线|前|之初|以前|之前|的旧|的往事|事宜|记录待核)')
        return (subject + '(?:的)?' + re.escape(e['aspect']) + r'(?:仍为|现为|定为|改作|改为|迁至|移至|是)'
                + rf'(?P<state>{_NAME})(?=[，,。；;！？!?]|$)')
    if key in ('C00694', 'C00709'):
        a, b = re.escape(e['first']), re.escape(e['second'])
        return rf'(?:{a}(?:与|和){b}|{b}(?:与|和){a})围绕{subject}(?:一直|从来)?(?:没有|不存在|毫无)(?:争端|冲突|矛盾)'
    end = r'(?=[，,。；;！？!?]|$)'
    if key == 'C00705':
        denied = r'(?:从未|没有|未曾)(?:确立|定下|采用)' + subject + r'的先验(?:规则|法则)'
        if p := e.get('constrained_action'):
            changed = (subject + r'的先验(?:规则|法则)(?:规定|为|是|记作)[：:]?' + re.escape(p['actor'])
                       + rf'(?:只能|只可|仅可)在(?P<window>{_NAME})时' + re.escape(p['action']) + end)
            return '(?:' + denied + '|' + changed + ')'
        return denied
    if key == 'C00713':
        entry = '(?:持|凭)' if e['entry'] in ('持', '凭') else re.escape(e['entry'])
        rank = rf'(?:被列为|划入|定为)(?P<rank>{_NAME})' + end
        recipient = ''
        if quota := e.get('quota'):
            same_item = _QUOTA.pattern.replace('(?P<item>' + _NAME + ')', re.escape(quota['item']))
            recipient = (rf'(?P<distribution>按户|按人|按籍)(?:取得|获配|分得|领取){same_item}' + end)
        result = '(' + rank + ')?' + '(?:[，,]?' + recipient + ')?' if recipient else rank
        return '(?:' + entry + re.escape(e["permit"]) + '的' + subject + result + ')'
    exclusive = rf'(?:专属于|只归|专归|唯独归)(?P<state>{_NAME})'
    action = (rf'(?P<exclusive_executor>仅|只)?由(?P<executor>{_NAME})(?P<exclusive_warrant>仅|只)?'
              rf'(?:凭|依据|按照)(?P<warrant>{_NAME})执行')
    return subject + '的' + re.escape(e['power']) + '(?:' + exclusive + '|' + action + ')' + end


def _has_conflict(key: str, evidence: dict, texts: Iterable[str]) -> bool:
    from nw.materials.world_history import factual_history_claim

    region, period = re.escape(evidence['region']), re.escape(evidence['period'])
    start = r'(?:^|[\s，,：:]|在|证实|确认|记载|载明|查明|表明)'
    scope = (rf'(?:{period}(?:内|期间)?(?:[，,]\s*|的|在)?{region}|{region}(?:在|于){period})(?:的|[，,]\s*)?'
             if period else rf'{region}(?:的|[，,]\s*)')
    assertion = '(?P<assertion>' + _claim_pattern(key, evidence) + ')'
    pattern = re.compile(start + scope + assertion)
    heading = re.compile(start + scope + r'(?:因|由于|在)?' + re.escape(evidence['event']) + r'(?:后|之后)?$')
    local_assertion = re.compile(r'^\s*' + assertion)
    for text in texts:
        previous_event = ''
        for sentence in _SENTENCE.findall(text):
            claims = list(pattern.finditer(sentence))
            # Only the immediately preceding, explicitly scoped event can locate a bare assertion.
            if previous_event and (claim := local_assertion.match(sentence)):
                claims.append(claim)
            for claim in claims:
                context = sentence[:claim.start('assertion')]
                if claim.re is local_assertion:
                    context = previous_event + context
                if (qualifier := evidence.get('qualifier')) and qualifier not in context:
                    continue
                if not factual_history_claim(sentence, claim.start('assertion'), claim.end()):
                    continue
                state = claim.groupdict().get('state')
                if key == 'C00708':
                    same = _state(state) == _state(evidence['after'])
                    prior = claim.groupdict().get('before')
                    valid = (same != bool(claim.groupdict().get('negated'))
                             and (prior is None or _state(prior) == _state(evidence['before'])))
                elif key == 'C00705' and (window := claim.groupdict().get('window')):
                    established = _WINDOWS.get(evidence['constrained_action']['window'])
                    valid = established is None or _OPPOSITE_WINDOW[established] != _WINDOWS.get(window)
                elif key == 'C00713':
                    valid = claim['rank'] in (None, evidence['rank'])
                    if claim.groupdict().get('count') and claim['distribution'] == evidence['distribution']:
                        quota = evidence['quota']
                        valid = valid and (claim['interval'].replace('天', '日') == quota['interval'].replace('天', '日')
                                           and claim['unit'] == quota['unit']
                                           and amount_value(claim['count']) == amount_value(quota['count']))
                elif key == 'C00714':
                    valid = state in (None, evidence['holder'])
                    if claim['executor'] and (claim['exclusive_executor'] or evidence.get('exclusive_executor')):
                        valid = valid and claim['executor'] == evidence['executor']
                    if (claim['executor'] == evidence['executor'] and evidence.get('warrant')
                            and (claim['exclusive_warrant'] or evidence.get('exclusive_warrant'))):
                        valid = valid and claim['warrant'] == evidence['warrant']
                else:
                    valid = False
                if not valid:
                    return True
            event = heading.search(sentence)
            previous_event = sentence if event and factual_history_claim(sentence, event.start(), event.end()) else ''
    return False


def check_impact_claims(key: str, evidence: dict, texts: Iterable[str]) -> None:
    require(not _has_conflict(key, evidence, texts), key + ' 下游产物改写了同一地区、时期和对象已批准的历史后果')
