"""Recognize an author's dated changes of historical period in one approved world card."""
from dataclasses import dataclass
import re
import unicodedata

from nw.materials.world_exchange import NUMBER, amount_value
from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00704': '本地创始制度、已发生的扩张及引发时期转换的实际事件与纪年',
    'C00707': '本地已发生的扩张、资源或关系恶化的事实及转入动荡的事件与纪年',
    'C00710': '本地动荡、组织实际改定制度的行动及转入固化的事件与纪年',
    'C00712': '本地已固定的制度、未解冲突与潜伏势力及转入暗流的事件与纪年',
    'C00716': '本地暗流中延续的矛盾、已经改变的结构及转入裂变的事件与纪年',
}
PERIODS = ('创始期', '扩张期', '动荡期', '固化期', '暗流期', '裂变期')
_PAIRS = {key: (PERIODS[i], PERIODS[i + 1]) for i, key in enumerate(RULES)}

# Both digit-by-digit historical dates and counted numerals occur in authors' prose.
YEAR_NUMBER = r'(?:前)?(?:元|[0-9０-９]{1,6}|[〇○零一二三四五六七八九两十百千万]{1,12})'
_DIGITS = str.maketrans('〇○零一二三四五六七八九', '000123456789')


def year_value(text: str) -> int | None:
    """Read an explicit calendar year, including 元年, 十二年 and 二〇一年."""
    if not isinstance(text, str):
        return None
    number = unicodedata.normalize('NFKC', text.strip()).removesuffix('年')
    if not re.fullmatch(YEAR_NUMBER, number):
        return None
    magnitude = number.removeprefix('前')
    if magnitude == '元':
        value = 1
    elif (digits := magnitude.translate(_DIGITS)).isdecimal():
        if len(digits) > 6:
            return None
        value = int(digits)
    elif re.fullmatch(NUMBER, magnitude.replace('〇', '零')):
        value = int(amount_value(magnitude.replace('〇', '零')))
    else:
        return None
    if value > 999999:
        return None
    return -value if number.startswith('前') else value


_INTERVAL_NUMBER = r'(?:[0-9０-９]{1,6}|[〇○零一二三四五六七八九两十百千万]{1,12})'
RELATIVE_OFFSET = (rf'(?:当年|同年|次年|翌年|前一年|上年|去年|(?:前|后){_INTERVAL_NUMBER}年|'
                   rf'{_INTERVAL_NUMBER}年(?:后|前)|之后|以后|之前|以前)')


def relative_direction(text: str, offset: int | None) -> int:
    """Direction when the author gave a date relative to an event."""
    if offset is not None:
        return (offset > 0) - (offset < 0)
    return -1 if text.endswith(('之前', '以前')) else 1


def relative_offset(text: str) -> int | None:
    """Exact offset in calendar years when the author specified one."""
    if text in ('当年', '同年'):
        return 0
    if text in ('次年', '翌年'):
        return 1
    if text in ('上年', '去年'):
        return -1
    match = re.fullmatch(rf'(前|后)({_INTERVAL_NUMBER})年|({_INTERVAL_NUMBER})年(后|前)', text)
    if match:
        amount = year_value(match[2] or match[3])
        if amount is not None:
            return -amount if (match[1] or match[4]) == '前' else amount
    return None


_NAME = r'[\u3400-\u9fffA-Za-z][\u3400-\u9fffA-Za-z·]{0,19}?'
_PERIOD = '(?:' + '|'.join(PERIODS) + ')'
_BREAK = re.compile(r'[。；;！!\r\n]+')
_UNKNOWN = re.compile(r'拟议|拟定|拟将|计划|打算|筹划|准备|可能|或将|据说|听说|传闻|传说|传言|'
                      r'相传|谣称|假设|假如|例如|示例|样例|假想|尚待|待核|待定|尚未|并未|并非|据称|意图|有望|预计|'
                      r'未曾|没有|未能|未予|从未|未遂|未获|未被|本拟|原拟|曾拟|如果|一旦|也许|能否|是否|[“”「」『』？?]')
_RETRACT = re.compile(r'作废|禁止采用|不予采信|不再(?:采用|沿用)|撤回|撤销|无效|(?:分期|年表|纪年|转折|时点|年代)(?:仍|尚)?(?:存疑|有误|待核|待定)')
_GENERIC = re.compile(r'(?:本|该|某|此|当地|原有|新的|既有|相关|具体|指定|若干|一些|某个|一个|一种|另一)?'
                      r'(?:世界|地方|地区|地域|区域|地点|纪年|事件|制度|规则|组织|势力|团体|矛盾|冲突|结构|变化|政权|秩序|资源|关系|航线|通道|路线|航路|档案|纲领|章程)')
_FROM = rf'(?:从|由)(?P<before>{_PERIOD})(?:过渡到|进入|转入|转为|迈入|走向)(?P<after>{_PERIOD})'
_CHANGE = (rf'(?P<event>[^。；;]{{3,100}}?)[，,]\s*'
           rf'(?:促使|推动|使得|使|标志着|由此|因此|于是|从此)(?P<world>{_NAME}){_FROM}')
_TURN = re.compile(rf'(?P<calendar>{_NAME})(?P<year>{YEAR_NUMBER})年[，,]\s*' + _CHANGE)
_REFERENCE_ACT = r'(?:施行|实施|生效|公布|颁布|签署|成立|解散|启用|开通|开港|通航|决堤|复航|封港|停航|罢运)'
_RELATIVE = re.compile(rf'(?:在)?(?P<anchor>(?P<name>《[^《》，。]{{2,22}}》|{_NAME})(?P<act>{_REFERENCE_ACT}))'
                       rf'(?P<offset>{RELATIVE_OFFSET})[，,]\s*' + _CHANGE)
_TURN_CAUSE = re.compile(rf'(?P<calendar>{_NAME})(?P<year>{YEAR_NUMBER})年[，,]\s*'
                         rf'(?:因|由于)(?P<event>[^。；;]{{3,100}}?)[，,]\s*(?P<world>{_NAME}){_FROM}')
_TURN_FIRST = re.compile(rf'(?P<world>{_NAME})(?:在|于)(?P<calendar>{_NAME})(?P<year>{YEAR_NUMBER})年'
                         rf'(?:因|由于)(?P<event>[^。；;]{{3,100}}?)[，,]?{_FROM}')
_PRIOR = (
    re.compile(rf'(?P<world>{_NAME})(?:在|于|的)?(?P<before>{_PERIOD})[，,]?\s*(?P<fact>.+)'),
    re.compile(rf'(?P<before>{_PERIOD})[，,]\s*(?P<world>{_NAME})(?:曾由|由|曾)(?P<fact>.+)'),
)
_CHARTER = r'(?:颁行|施行|实行|颁布|制定|确立|设立|建立|创设|推行|改行|改设|改定|废除|废止|重订|修订|合并|改组|重建|接管|签订|通过|设立了|建立了)'
_EXPAND = r'(?:开通|开辟|开拓|开设|增设|拓展|扩建|并入|纳入|打通|设立|新设|吞并|兼并|拓垦|拓宽|接通|延伸至|扩展至|延伸到)'
_DESTABILIZE = r'(?:断供|枯竭|告罄|失收|短缺|耗尽|亏空|决裂|解体|破裂|反目|毁约|决堤|失守|动乱|起事|罢运|失联|中断|决口|封锁|断交|失陷|暴涨|争夺|争权|叛乱|围困|饥荒|暴动)'
_CONFLICT = r'(?:未解|未平|僵持|争夺|相争|对峙|积怨|争端|纠纷|宿怨|抵制|扣押|拖欠|克扣|争执|积压|争权|争税|抗税|罢运|密谋|暗斗)'
_COVERT = r'(?:秘密|暗中|地下|潜伏|暗线|密约|密谋|结社|暗结|私下|隐匿|串联)'
_RESTRUCTURE = r'(?:废除|废止|废黜|解散|解体|拆分|取代|重建|改组|改制|改设|取消|撤销|推翻|瓦解|分裂|分立|改由|接管|夺取|改选|改划)'
_INSTITUTION = r'(?:令|法|章程|制|规约|公约|条约|盟约|典章|条例|章则|契约|宪章|宪法|规则|办法|会|署|府|局|司|庭|公社|内阁|衙门|政权|议院|朝廷|同盟)'
_TERRITORY = r'(?:航路|航线|水道|运河|商道|驿道|通道|航道|驿站|商站|港口|码头|疆域|边界|属地|城邦|领地|据点|矿区|辖区|行政区|行省|外埠|新埠|郡|县|关|岛|城|港|埠|盟国|联盟|新镇|贸易网)'
_STRUCTURE = r'(?:权|议院|世袭|制度|委员会|秩序|专营|垄断|联盟|政体|统治|王朝|特许|国界|疆界|执政|双院|领地|' + _INSTITUTION + ')'
_TOOLS = re.compile(r'《([^《》]{2,22})》')


def _uncertain(text: str) -> bool:
    # An unresolved dispute is an attested historical circumstance.
    factual = re.sub(r'(?:尚未|仍未|未曾|并未)(?:解决|平息|化解|消除|和解)', '未解', text)
    return bool(_UNKNOWN.search(factual))


def _named(value: str) -> bool:
    return bool(value.strip()) and not _GENERIC.fullmatch(value) and not _uncertain(value)


def _act(text: str, verbs: str, *, subject: bool = True) -> tuple[str, str] | None:
    """Keep concrete parties and the object of their action for downstream evidence."""
    for clause in re.split(r'[，,]', text):
        verb = re.search(verbs, clause)
        if not verb:
            continue
        actor = clause[:verb.start()].removeprefix('由').removeprefix('已').strip()
        target = clause[verb.end():].removeprefix('了').strip('《》')
        if ((not subject or _named(actor)) and 1 < len(target) <= 36 and _named(target)
                and not re.search(r'(?:没有|未|将|拟|欲|计划|尝试|准备)$', actor)):
            return actor, target
    return None


def _observed(text: str, markers: str) -> bool:
    # For e.g. 东栈粮仓断供 or 两埠工会争夺仓权, the change has a local subject.
    for clause in re.split(r'[，,]', text):
        for mark in re.finditer(markers, clause):
            subject = clause[:mark.start()].strip('因由')
            if len(subject) >= 2 and _named(subject) and not re.search(r'(?:未|拟|将|欲)$', subject):
                return True
    return False


def _changes(text: str, verbs: str, target_kind: str, *, subject: bool = True) -> bool:
    for clause in re.split(r'[，,]', text):
        action = _act(clause, verbs, subject=subject)
        if action and re.search(target_kind, action[1]):
            return True
    return False


def _evidence_terms(key: str, prior: str, event: str) -> list[str]:
    if _uncertain(prior + event):
        return []
    if key == 'C00704':
        if not _changes(prior, _CHARTER, _INSTITUTION, subject=False) or not _changes(event, _EXPAND, _TERRITORY):
            return []
    elif key == 'C00707':
        if not _changes(prior, _EXPAND, _TERRITORY, subject=False) or not _observed(event, _DESTABILIZE):
            return []
    elif key == 'C00710':
        if not _observed(prior, _DESTABILIZE + '|' + _CONFLICT) or not _changes(event, _CHARTER, _INSTITUTION):
            return []
    elif key == 'C00712':
        if not (_changes(prior, _CHARTER, _INSTITUTION, subject=False) and _observed(event, _COVERT)
                and _observed(prior + '，' + event, _CONFLICT)):
            return []
    elif key == 'C00716':
        if not _observed(prior, _CONFLICT) or not _changes(event, _RESTRUCTURE, _STRUCTURE):
            return []
    names = [event, *_TOOLS.findall(prior + '。' + event)]
    for clause in (prior, event):
        if action := _act(clause, '|'.join((_CHARTER, _EXPAND, _RESTRUCTURE)), subject=False):
            names.append(action[1])
    return list(dict.fromkeys(names))


@dataclass(frozen=True)
class _Turn:
    world: str
    calendar: str
    year: int | None
    before: str
    after: str
    event: str
    text: str
    time_text: str
    time_anchor: str = ''
    offset: int | None = None
    date_source: str = ''


def _reference(match: re.Match, lines: list[str]) -> tuple[str, int | None, str] | None:
    world, name, act = map(re.escape, (match['world'], match['name'], match['act']))
    in_world = rf'{world}(?:的|已)?'
    exact_date = re.compile(in_world + name + rf'(?:已)?(?:在|于)(?P<calendar>{_NAME})(?P<year>{YEAR_NUMBER})年(?:正式)?' + act)
    subject = rf'(?:由{_NAME})?(?:已|正式|曾)?'
    observed = re.compile(rf'(?:{subject}{act}(?:了)?{name}|{name}(?:已|正式)?{act})')
    references = {}
    undated = False
    for line in lines:
        if _uncertain(line):
            continue
        dated = exact_date.fullmatch(line)
        if dated and (year := year_value(dated['year'])) is not None and _named(dated['calendar']):
            references[(dated['calendar'], year)] = line
        # The card must actually say the reference event took place in this world.
        elif re.fullmatch(in_world + observed.pattern, line):
            undated = True
        else:
            for form in _PRIOR:
                prior = form.fullmatch(line)
                if prior and prior['world'] == match['world'] and observed.fullmatch(prior['fact']):
                    undated = True
    if len(references) == 1:
        (calendar, year), line = next(iter(references.items()))
        return calendar, year, line
    return ('', None, '') if not references and undated else None


def _turn(text: str, lines: list[str]) -> _Turn | None:
    match = _TURN.fullmatch(text) or _TURN_FIRST.fullmatch(text) or _TURN_CAUSE.fullmatch(text)
    if _uncertain(text):
        return None
    if match:
        year = year_value(match['year'])
        if year is None or not _named(match['calendar']):
            return None
        turn = _Turn(match['world'], match['calendar'], year, match['before'], match['after'], match['event'], text,
                     match['calendar'] + match['year'] + '年')
    else:
        match = _RELATIVE.fullmatch(text)
        if not match or not _named(match['name'].strip('《》')) or not (ref := _reference(match, lines)):
            return None
        offset = relative_offset(match['offset'])
        if offset is None and match['offset'] not in ('之后', '以后', '之前', '以前'):
            return None
        calendar, reference_year, source = ref
        year = reference_year + offset if reference_year is not None and offset is not None else None
        if reference_year is not None and year is not None and reference_year * year <= 0 and offset:
            year = None  # Whether the project's epochs include a year zero is not given.
        turn = _Turn(match['world'], calendar, year, match['before'], match['after'], match['event'], text,
                     match['anchor'] + match['offset'], match['anchor'], offset, source)
    return turn if _named(turn.world) and turn.before != turn.after else None


def _boundary(turn: _Turn, limits: list[str]) -> str | None:
    place, era, anchor = map(re.escape, (turn.world, turn.calendar, turn.time_anchor))
    region = rf'(?:该|此|本|上述|以上)?(?:历史)?分期(?:仅|只)(?:适用于|限于|限){place}'
    patterns = []
    if era:
        patterns.extend((region + rf'(?:的)?{era}(?:纪年|年表)?',
                         rf'{place}(?:的)?(?:历史|上述)?分期(?:以|按){era}(?:纪年|年表)(?:为准|核定|为据)?'))
    if anchor:
        patterns.extend((region + rf'[，,]以{anchor}为(?:起点|参照|时间基准)',
                         region + rf'(?:的)?(?:地方)?史(?:事|实|记载|年表)?'))
    for statement in limits:
        if any(re.fullmatch(expr, statement) for expr in patterns):
            return statement
    return None


def _retracted(lines: list[str], turn: _Turn) -> bool:
    for line in lines:
        if not _RETRACT.search(line):
            continue
        if re.search(r'(?:本卡|上述|以上|该|这段|本次)(?:历史)?(?:分期|年表|纪年|转折|规则)', line):
            return True
        if turn.world in line and (turn.before in line or turn.after in line or '分期' in line):
            return True
    return False


def _consistent(turn: _Turn, turns: list[_Turn]) -> bool:
    for other in turns:
        if other == turn or turn.world != other.world:
            continue
        if turn.year is not None and other.year is not None and turn.calendar == other.calendar:
            delta = turn.year - other.year
        elif turn.time_anchor and turn.time_anchor == other.time_anchor:
            if turn.offset is not None and other.offset is not None:
                delta = turn.offset - other.offset
            else:
                first = relative_direction(turn.time_text, turn.offset)
                second = relative_direction(other.time_text, other.offset)
                if first * second >= 0:
                    continue
                delta = first - second
        else:
            continue
        if ((turn.before, turn.after) == (other.before, other.after)
                or (turn.event == other.event and (delta or turn.after != other.after))):
            return False
        # Compare only expressly recorded changes in this same local timeline.
        if (other.before, other.after) in _PAIRS.values():
            order = PERIODS.index(turn.before) - PERIODS.index(other.before)
            if order * delta < 0:
                return False
    return True


def approved_period(card: dict, key: str) -> dict | None:
    texts = approved_text(card)
    if key not in RULES or not texts:
        return None
    rule, limits = texts
    lines, boundaries = ([s.strip() for s in _BREAK.split(text) if s.strip()] for text in texts)
    if any(re.fullmatch(r'(?:以下|下述|本卡|整张卡片|这些|上述)?(?:分期|例子|历史|年表|内容)?(?:均|全)?(?:仅供|仅作|只是|作为)?(?:假设|示例|参考|传闻|推测|旧稿|旧方案|草案)[：:]?', s)
           for s in lines + boundaries):
        return None
    turns = list(dict.fromkeys(turn for line in lines if (turn := _turn(line, lines)) is not None))
    candidates = []
    for turn in turns:
        if ((turn.before, turn.after) != _PAIRS[key] or not _consistent(turn, turns)
                or _retracted(lines + boundaries, turn)):
            continue
        scope = _boundary(turn, boundaries)
        if not scope:
            continue
        prior_facts = {}
        for line in lines:
            match = next((m for p in _PRIOR if (m := p.fullmatch(line))), None)
            if match and (match['world'], match['before']) == (turn.world, turn.before) and not _uncertain(line):
                prior_facts[line] = match['fact']
        disputes = [(line, fact) for line, fact in prior_facts.items()
                    if key == 'C00712' and _observed(fact, _CONFLICT)]
        priors = []
        for line, fact in prior_facts.items():
            anchors = _evidence_terms(key, fact, turn.event)
            if not anchors and disputes and _changes(fact, _CHARTER, _INSTITUTION, subject=False):
                # A lasting rule and the unresolved grievance can be two separately scoped records.
                supplement, dispute = disputes[0]
                anchors = _evidence_terms(key, fact + '，' + dispute, turn.event)
                if anchors:
                    priors.append((supplement, [dispute]))
            if anchors:
                priors.append((line, anchors))
        for line, _ in priors:
            if turn.year is not None:
                dates = re.findall(re.escape(turn.calendar) + '(' + YEAR_NUMBER + ')年', prior_facts[line])
                if any((value := year_value(date)) is None or value > turn.year for date in dates):
                    return None
            if turn.time_anchor and ((turn.offset is not None and turn.offset < 0)
                                     or turn.time_text.endswith(('之前', '以前'))):
                relative = _RELATIVE.fullmatch(turn.text)
                if relative and _reference(relative, [line]):
                    return None
        if priors:
            facts = list(dict.fromkeys(line for line, _ in priors))
            anchors = list(dict.fromkeys(anchor for _, terms in priors for anchor in terms))
            candidates.append(dict(world=turn.world, calendar=turn.calendar, year=turn.year, before=turn.before,
                                   after=turn.after, event=turn.event, transition=turn.text, boundary=scope,
                                   prior_fact=facts[0], prior_facts=facts, anchors=anchors, time_text=turn.time_text,
                                   time_kind='relative' if turn.time_anchor else 'calendar', time_anchor=turn.time_anchor,
                                   offset=turn.offset, date_source=turn.date_source))
    return card_proof(card, rule, limits, candidates[0]) if len(candidates) == 1 else None
