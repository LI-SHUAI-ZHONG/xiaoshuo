"""Apply a project's measured action cost to its own actor, ability and unit of time."""
from fractions import Fraction
import re
from unicodedata import normalize

from nw.materials.semantic_application import require
from nw.materials.world_exchange import NUMBER, amount_value

TIME = r'(?:个?小时|分钟|秒钟|时辰|回合|息|刻|秒|轮|次)'
RESOURCE = r'(?:格|点|份|缕|单位|灵值|能值|滴|枚)'
RATE = re.compile(rf'(?:每(?:一)?|一)(?P<time>{TIME})(?:需(?:要)?|要)?(?:消耗|耗费|耗去|损耗|用掉|耗用|耗|消去|扣除)'
                  rf'(?:灵力|能量|灵气)?\s*(?P<num>{NUMBER})\s*(?P<unit>{RESOURCE})')
STOCK = re.compile(rf'(?:能量总量|总储量|灵力(?:储量)?|能量储备|剩余能量|余量|存量|储能量|储备|能量|还剩|只剩)'
                   rf'\s*(?P<op>不足|不到|低于|不满|少于|仅剩|仅有|只剩|只有|剩下|为|最多|至多|不超过|剩余|尚余|剩|有)?'
                   rf'\s*(?P<num>{NUMBER})\s*(?P<unit>{RESOURCE})')
CAP = re.compile(rf'(?:最多|至多|上限为?|只能|不超过|不能超过|不得超过|最久)(?:连续)?(?:使用|运行|施展|施术|维持|支撑|持续|撑住|坚持|撑)?'
                 rf'\s*(?P<num>{NUMBER})\s*(?P<time>{TIME})')
RUN = re.compile(rf'(?P<verb>连续(?:使用|施展|施术|支撑|维持|运转|施法)?|持续(?:施术|施法|运转)?|'
                 rf'维持|坚持|支撑|撑足|撑了|撑到|撑过|用原有存量(?:撑|运行)?|运行|施术|施法|施展|运转|'
                 rf'用了|用时|历时|耗时|坚持到|直至|长达|第|用|以)(?:了|满|整整|足足|至)?'
                 rf'\s*(?P<num>{NUMBER})\s*(?P<time>{TIME})')
TIME_AMOUNT = re.compile(rf'(?P<num>{NUMBER})\s*(?P<time>{TIME})(?![钟表])')
STOP = re.compile(r'中断|停手|停下|停止|熄灭|熄火|告罄|力竭|无力为继|无法继续|被迫收手|失败|未能完成|未能坚持')
AVOID = re.compile(r'(?:不足以|未能|没能|不能|无法|不可能|不得|不许|未曾|没有|不敢|办不到|不足以让.{0,8}|不可)$')
INTENT = re.compile(r'想要|原想|本想|企图|试图|打算|原计划|试着|希望|原定|试图让')
SUCCESS = re.compile(r'成功|终于完成|果真|依然做成|仍然完成|顺利|竟然撑过|仍可|也不会耗尽')
CUT = re.compile(r'[。！？；;\n]')
EFFECT = re.compile(r'耗尽|枯竭|收回|收束|缩短|停|收手|中断|熄|力竭|余量|维持|耗|撑|探查|辨明|不足|收招|减弱|作罢')
_FREE = re.compile(r'(?:无需|不需|不必|不再|不会|不)(?:消耗|耗费|耗用|耗损|损耗|耗能)|零消耗|毫无消耗|取之不尽|无限(?:维持|施术)|永不耗尽')
_SCALE = {'秒': ('秒', 1), '秒钟': ('秒', 1), '分钟': ('秒', 60), '小时': ('秒', 3600), '个小时': ('秒', 3600)}


def _time(match: re.Match) -> tuple[str, Fraction]:
    t = match['time']
    dimension, scale = _SCALE.get(t, (t, 1))
    return dimension, amount_value(match['num']) * scale


def _rate(match: re.Match) -> tuple[str, str, Fraction]:
    t = match['time']
    dimension, scale = _SCALE.get(t, (t, 1))
    return dimension, match['unit'], amount_value(match['num']) / scale


def _text(s: str) -> str:
    return normalize('NFKC', s).replace('[FAKE]', '').strip()


def basis(rule: str, limit: str, ability: str, ability_limit: str) -> dict | None:
    """Freeze the measured envelope. A threshold is an upper bound, never an exact balance."""
    world = _text(rule)
    rates = {_rate(m) for m in RATE.finditer(world)}
    if len(rates) != 1 or _text(ability) not in world:
        return None
    dim, unit, rate = next(iter(rates))
    actor_rates = {_rate(m) for m in RATE.finditer(_text(ability_limit))}
    if rate <= 0 or actor_rates and actor_rates != rates:
        return None
    bounds = []
    stocks = set()
    for text in (world, _text(limit), _text(ability_limit)):
        for cap in CAP.finditer(text):
            kind, value = _time(cap)
            if kind == dim:
                bounds.append((value, False))
        for stock in STOCK.finditer(text):
            if stock['unit'] != unit:
                continue
            amount = amount_value(stock['num'])
            strict = stock['op'] in ('不足', '不到', '低于', '不满', '少于')
            stocks.add((amount, strict))
            bounds.append((amount / rate, strict))
    if not bounds:
        return None
    maximum = min(v for v, _ in bounds)
    exclusive = any(v == maximum and strict for v, strict in bounds)
    return {'ability': ability, 'time_unit': dim, 'cost_unit': unit, 'cost': str(rate),
            'maximum': str(maximum), 'exclusive': exclusive,
            'stocks': [[str(n), excl] for n, excl in sorted(stocks)]}


def _over(amount: Fraction, budget: dict) -> bool:
    cap = Fraction(budget['maximum'])
    return amount > cap or amount == cap and budget['exclusive']


def _check_length(clause: str, measured: re.Match, budget: dict) -> None:
    before = clause[:measured.start()]
    negative = AVOID.search(before)
    if negative:
        return
    dim, duration = _time(measured)
    if dim == budget['time_unit'] and not _over(duration, budget):
        return
    immediate = re.split('[，,但却]', before)[-1]
    if STOP.search(clause[measured.end():]) and INTENT.search(immediate) and not SUCCESS.search(clause[measured.end():]):
        # The intended duration exceeds the budget; the actual result must still respect it.
        return
    require(dim == budget['time_unit'], 'C00025 行动时长与冻结的消耗单位不能换算')
    require(not _over(duration, budget), 'C00025 已用时长超过本行动的可用储量或明确时限')


def check_conflict(row: dict, text: str, *, stage: str, landing: bool = False) -> None:
    frozen = row['consumption']
    budget = frozen
    for clause in filter(None, CUT.split(_text(text))):
        if not landing and _text(row['ability']) not in clause and not re.search(r'施术|施法|灵力|原有存量|每息耗|能量总量', clause):
            continue
        require(not _FREE.search(clause), 'C00025 付出能耗的行动被写成无消耗或无限维持')
        for measured in RATE.finditer(clause):
            require(_rate(measured) == (budget['time_unit'], budget['cost_unit'], Fraction(budget['cost'])),
                    'C00025 本次行动的耗率、计量单位与冻结前置不符')
        # A smaller explicitly available balance tightens the duration for this action.
        limits = [(0, budget)]
        for stock in STOCK.finditer(clause):
            amount = amount_value(stock['num'])
            require(stock['unit'] == frozen['cost_unit'], 'C00025 本次能源的单位与批准的储量口径不同')
            limit_only = stock['op'] in ('不足', '不到', '低于', '不满', '少于')
            for upper, exclusive in frozen['stocks']:
                require(amount < Fraction(upper) or amount == Fraction(upper) and (limit_only or not exclusive),
                        'C00025 本场声称可用的能量超过对应冻结储量')
            local = amount / Fraction(frozen['cost'])
            if local < Fraction(budget['maximum']) or local == Fraction(budget['maximum']) and limit_only:
                budget = {**budget, 'maximum': str(local), 'exclusive': limit_only or local == Fraction(budget['maximum']) and budget['exclusive']}
                limits.append((stock.end(), budget))
        spans = []
        for active in RUN.finditer(clause):
            current = next(b for start, b in reversed(limits) if start <= active.start())
            _check_length(clause, active, current)
            spans.append(active.span())
        for measured in TIME_AMOUNT.finditer(clause):
            if any(start <= measured.start() < end for start, end in spans):
                continue
            # “十息后回声术仍在运转” is also a successful duration claim.
            if re.match(r'(?:之后|后|过去)(?:仍|还|照常|依旧|仍然).{0,9}(?:施术|施法|运转|维持|未停|未熄|有效|回响)', clause[measured.end():]):
                current = next(b for start, b in reversed(limits) if start <= measured.start())
                _check_length(clause, measured, current)


def check_narrated_action(row: dict, manuscript: str) -> None:
    """Review uncited, explicitly attributed casts; recollections and speech are outside this scene's budget."""
    names = [e['value'] for e in row['evidence'] if e['ref'].endswith('/body/name')]
    if len(names) != 1:
        return
    actor, ability = (_text(s) for s in (names[0], row['ability']))
    location = r'(?:在[^，,。！？；;\n]{1,8}(?:旁|边|内|里|上|下|前|后|中))?'
    cast = re.compile(re.escape(actor) + location + r'(?:亲自|当即|随即|再次|当场|立刻|开始|继续|实际)?'
                      + r'(?:施展|使出|施放|发动|运转|使用)' + re.escape(ability))
    narration = re.sub(r'“[^”]*”|「[^」]*」|‘[^’]*’|"[^"]*"', '', _text(manuscript))
    uncertain = re.compile(r'回忆|回想|想起|往昔|当年|上回|昨日|从前|上一次|过去曾|若是|假设|假如|倘若|据说|传闻|梦见|梦中|设想|要是|如果|以为|谎称|声称')
    for sentence in CUT.split(narration):
        for match in cast.finditer(sentence):
            if uncertain.search(sentence[:match.start()]) or re.search(r'若|将会|本可以|方能', sentence[match.end():]):
                continue
            # A following comma clause may change subject. Retain duration/cost predicates
            # and stop as soon as the narrative changes to another person or activity.
            head, *tail = re.split('[，,]', sentence[match.start():])
            observed = [head]
            for part in tail:
                if not re.match(r'(?:每|连续|持续|施术|运转|维持|支撑|用了|余量|仅|灵力|能量|直至|原想|本想|却|但|直到|第)', part):
                    break
                observed.append(part)
            check_conflict(row, '，'.join(observed), stage='review')


def validate_use(row: dict, text: str, *, operation: str, stage: str) -> None:
    check_conflict(row, text, stage=stage, landing=True)
    check_conflict(row, operation, stage=stage)
    clean = _text(text)
    budget = row['consumption']
    # A receipt must show a use of this bound: its rate, usable time, reserve or observable depletion.
    stocks = {s for s, _ in budget['stocks']}
    stock = any(m['unit'] == budget['cost_unit'] and str(amount_value(m['num'])) in stocks for m in STOCK.finditer(clean))
    require(EFFECT.search(clean) and (stock or RATE.search(clean) or RUN.search(clean) or
            _text(row['ability']) in clean and STOP.search(clean)), 'C00025 产物须体现本次行动的用时、耗量或耗尽后的实际处置')
