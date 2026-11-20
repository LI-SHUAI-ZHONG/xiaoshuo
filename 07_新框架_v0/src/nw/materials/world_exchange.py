"""Locate a project's directed quotation and the particular world rule that governs its use."""
from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
import re

from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00533': '两个实际兑换对象按同一价值单位计价、相符的兑换比例和当地交易条件',
    'C00542': '明确使用的两种货币、兑换方向、市场和时期、适用限制及已知或明确待定的报价',
    'C00546': '同一交易所用的汇率、实际兑换时期以及该交易的结算时点和限制',
    'C00548': '同一资源库登记的兑换对象、市场报价来源、汇率及取得或消耗的核算用途',
}
_NAME = r'[\u3400-\u9fffA-Za-z][\u3400-\u9fffA-Za-z0-9·]{0,19}?'
_GENERIC = re.compile(r'(?:本|该|某|指定|相关|适用|当地|另一|规定|对应|目标|其他|任意|具体|实际)?'
                      r'(?:资源|货币|对象|市场|地区|地点|时期|条件|单位|规则|许可|手续|账册|账簿|来源|渠道|交易|基准|价值|情况|时间|票据|凭证|标准|岗位|证件)')
_UNSET = re.compile(r'尚未|假设|反例|旧方案|可能|或许|疑似|据说|拟定|暂定|某种|某个|某地|某年|'
                    r'未批准|未明确|待核|按规定|符合条件|相应条件|相关规定|有资格|合格者|示意|示例|例如|举例')
_VOID = re.compile(r'作废|废止|不再(?:适用|采用|兑换)|(?:不|未)采用|不成立|停兑|停止兑换|取消兑换|暂停挂牌|无效')
_DIGITS = '零一二三四五六七八九'
_D = r'[一二两三四五六七八九]'
_TENS = rf'{_D}十{_D}?'
_HUNDREDS = rf'{_D}百(?:{_TENS}|零{_D})?'
_THOUSANDS = rf'{_D}千(?:{_HUNDREDS}|零(?:{_TENS}|{_D}))?'
_SMALL = rf'(?:{_THOUSANDS}|{_HUNDREDS}|{_D}?十{_D}?|{_D})'
# A missing place needs an explicit zero, avoiding ambiguous shorthand such as 一百二.
_CHINESE = rf'(?:{_SMALL}万(?:{_THOUSANDS}|零{_SMALL})?|{_SMALL}|零)(?:点[零一二三四五六七八九]{{1,6}})?'
NUMBER = rf'(?:\d{{1,12}}(?:[.．]\d{{1,6}})?|{_CHINESE}|半)'
UNIT = r'(?:千克|公斤|标准箱|枚|块|锭|张|袋|份|斤|克|吨|瓶|箱|担|升|桶|点|卷|片|件|斛|贯|两|匹|筐|束|根|颗)'
_PERIOD = r'[\u3400-\u9fffA-Za-z0-9]{1,14}?(?:期间|时期|季节|期|季|年|月|旬|节|日|周|夜|岁)'
# Separate the rate from its scope before parsing the operands, so neither number can become part of a place.
_AMOUNT = r'(?P<{num}>' + NUMBER + r')\s*(?P<{unit}>' + UNIT + r')(?P<{item}>' + _NAME + r')'
_LEFT = _AMOUNT.replace('{num}', 'left_num').replace('{unit}', 'left_unit').replace('{item}', 'left')
_RIGHT = _AMOUNT.replace('{num}', 'right_num').replace('{unit}', 'right_unit').replace('{item}', 'right')
_QUOTE = re.compile(r'(?:每|用|以)?' + _LEFT + r'\s*(?:可兑换为|可兑换|可兑|可换取|可换|兑换为|兑换|换取|换成|换|兑|[=＝])\s*' + _RIGHT)
_OPEN = re.compile(r'(?P<left>' + _NAME + r')(?:兑|换)(?P<right>' + _NAME + r')(?:的)?(?:挂牌汇率|汇率|比率|报价)(?:仍|目前)?(?:待定|尚待公布|待公布|待挂牌)')
_PAIR = r'(?:{left}(?:兑|换|兑换为){right}|将{left}兑换为{right}|用{left}换取{right})'
_SENTENCES = re.compile(r'[。；;！？!?\r\n]+')


def _specific(*names: str) -> bool:
    return all(len(name) >= 2 and not _GENERIC.fullmatch(name) and not _UNSET.search(name)
               and not re.search(r'并非|不是|未使用|禁止|不能|不再|无关|改为|转述|并未|不得|不允许|不准|不可', name)
               for name in names)


def amount_value(text: str) -> Fraction:
    """Return the exact positive or zero quantity represented by a NUMBER match."""
    if text == '半':
        return Fraction(1, 2)
    if text[0].isdecimal():
        return Fraction(text.replace('．', '.'))
    whole, _, decimal = text.replace('两', '二').partition('点')
    digit = subtotal = total = 0
    for character in whole:
        if character in _DIGITS:
            digit = _DIGITS.index(character)
        elif character == '万':
            total = (subtotal + digit) * 10000
            subtotal = digit = 0
        else:
            weight = {'十': 10, '百': 100, '千': 1000}[character]
            subtotal += (digit or 1) * weight
            digit = 0
    digits = ''.join(str(_DIGITS.index(ch)) for ch in decimal)
    return Fraction(str(total + subtotal + digit) + ('.' + digits if digits else ''))


@dataclass(frozen=True)
class _Quote:
    text: str
    market: str
    period: str
    left: str
    right: str
    left_unit: str
    right_unit: str
    ratio: Fraction | None

    @property
    def pair(self) -> str:
        return _PAIR.format(left=re.escape(self.left), right=re.escape(self.right))


def _quote(text: str, market_names: list[str]) -> _Quote | None:
    if _UNSET.search(text) or _VOID.search(text):
        return None
    templates = (
        r'(?P<period>' + _PERIOD + r')[，,]\s*(?:在)?(?P<market>' + _NAME + r')',
        r'(?:在)?(?P<market>' + _NAME + r')(?:在|于|进入)(?P<period>' + _PERIOD + r')(?:时)?[，,]\s*',
    )
    for scope in templates:
        for expr in (_QUOTE, _OPEN):
            used_scope = scope
            if expr is _OPEN and scope.startswith(r'(?P<period>'):
                # Without a quantity between the market and the first asset, require a named market ending.
                district = _NAME + r'(?:钱市|市场|钱庄|商会|柜台|兑换所|交易所|镇|港|城|市)'
                market = '|'.join([*(re.escape(name) for name in market_names), district])
                used_scope = scope.replace('(?P<market>' + _NAME + ')', '(?P<market>' + market + ')')
            prefix = used_scope + r'(?:的)?(?:(?:挂牌价|牌价|报价|汇率)(?:为|是|[：:])?)?'
            match = re.fullmatch(prefix + expr.pattern, text)
            if not match or not _specific(*(match[k] for k in ('market', 'period', 'left', 'right'))):
                continue
            if match['left'] == match['right']:
                return None
            if expr is _OPEN:
                return _Quote(text, match['market'], match['period'], match['left'], match['right'], '', '', None)
            incoming, outgoing = amount_value(match['left_num']), amount_value(match['right_num'])
            if incoming > 0 and outgoing > 0:
                return _Quote(text, match['market'], match['period'], match['left'], match['right'],
                              match['left_unit'], match['right_unit'], outgoing / incoming)
    return None


def _one(lines: list[str], pattern: str) -> re.Match | None:
    hits = [match for line in lines if (match := re.fullmatch(pattern, line))
            and not _UNSET.search(line) and not _VOID.search(line)]
    return hits[0] if len(hits) == 1 else None


def _bounds(q: _Quote, limits: list[str]) -> str | None:
    participant = r'(?:仅|只有)(?P<permit>持有?' + _NAME + r'|凭' + _NAME + r')(?:者)?(?:才可|方可|可)在'
    market = re.escape(q.market)
    allowed = _one(limits, participant + market + q.pair)
    if allowed and _specific(re.sub(r'^(?:持有|持|凭)', '', allowed['permit'])):
        return allowed[0]
    match = _one(limits, market + r'(?:的)?' + q.pair + r'(?:只限|仅限)(?P<who>' + _NAME + r')(?:持|凭)(?P<permit>' + _NAME + r')(?:办理|兑换)')
    return match[0] if match and _specific(match['who'], match['permit']) else None


def _value_basis(q: _Quote, lines: list[str]) -> dict | None:
    # Both per-unit valuations must use the same numeraire and agree with the named direction.
    market = re.escape(q.market)

    def operand(unit: str, asset: str, suffix: str) -> str:
        return (r'每(?:一|1)?' + re.escape(unit + asset) + r'(?:作价|折合|值|计)'
                + rf'(?P<n{suffix}>' + NUMBER + rf')(?P<v{suffix}>' + _NAME + r')')
    first = operand(q.left_unit, q.left, '1')
    second = operand(q.right_unit, q.right, '2')
    priced = market + r'按(?P<basis>' + _NAME + r')计价[，,]'
    prices = [match for line in lines for ordering in (first + r'[，,]' + second, second + r'[，,]' + first)
              if (match := re.fullmatch(priced + ordering, line)) and not _UNSET.search(line) and not _VOID.search(line)]
    if len(prices) > 1:
        return None
    vals = prices[0] if prices else None
    relative = _one(lines, market + r'按(?P<basis>' + _NAME + r')(?:计价|折价)[，,]每(?:一|1)?'
                    + re.escape(q.left_unit + q.left) + r'(?:的)?(?:票面价值|计价价值|计价值|价值)(?:是|为)每(?:一|1)?'
                    + re.escape(q.right_unit + q.right) + r'的(?P<factor>' + NUMBER + r')倍')
    supplied = [value for value in (vals, relative) if value is not None]
    if len(supplied) != 1 or not _specific(supplied[0]['basis']):
        return None
    if supplied[0]['basis'] in {'价值', '价格', '价值口径', '计价口径'}:
        return None
    if vals:
        if vals['v1'] != vals['v2'] or not _specific(vals['v1']):
            return None
        left, right = amount_value(vals['n1']), amount_value(vals['n2'])
        if right <= 0 or q.ratio != left / right:
            return None
    elif q.ratio != amount_value(relative['factor']):
        return None
    return {'valuation': supplied[0][0]}


def _domain(q: _Quote, key: str, rules: list[str], limits: list[str]) -> dict | None:
    market, left, right = map(re.escape, (q.market, q.left, q.right))
    if key == 'C00542':
        assets = r'(?:' + left + r'(?:与|和|、)' + right + r'|' + right + r'(?:与|和|、)' + left + r')'
        declared = r'(?:均为|均是|是|为)' + market + r'(?:的)?(?:通行|流通|法定|结算)?货币'
        currencies = _one(rules, assets + declared)
        if currencies:
            return {'currencies': currencies[0]}
        first, second = _one(rules, left + declared), _one(rules, right + declared)
        if first and second:
            return {'from_currency': first[0], 'to_currency': second[0]}
        return None
    if q.ratio is None:
        return None
    if key == 'C00533':
        return _value_basis(q, rules)
    if key == 'C00546':
        agreement = _one(rules, market + r'(?:采用|按|依)' + q.pair
                         + r'(?:的)?(?:挂牌比例|挂牌价|牌价|汇率)(?:为|用以)?结算(?P<trade>' + _NAME + r')(?:交易|买卖)')
        settle = _one(limits, market + r'(?:的)?' + q.pair + r'(?:须|必须|仅可)在'
                      + r'(?P<window>[^，,]{2,15}?(?:闭市前|开市后|交割日|到期日|交付后|验收后|退潮时))'
                      + r'(?:持|凭)(?P<permit>' + _NAME + r')结算')
        if agreement and settle and _specific(agreement['trade'], settle['permit']):
            return {'transaction': agreement[0], 'settlement': settle[0]}
    if key == 'C00548':
        ledger = _one(rules, r'(?P<book>' + _NAME + r'(?:资源簿|资源账|资源库|库账|入库簿))'
                      + r'(?:引用|依据|据)' + market + r'(?:的)?《(?P<source>[^《》，,]{2,25})》'
                      + r'(?:记录|登记|收录)' + q.pair + r'[，,](?:用于|供|据以)核算'
                      + r'(?P<application>' + right + r'(?:的)?(?:取得|入账|取得数)量|'
                      + left + r'(?:的)?(?:消耗|支出|扣除)量)')
        if ledger and _specific(ledger['book'], ledger['source']):
            return {'ledger': ledger[0], 'origin': ledger['source'], 'accounting': ledger['application']}
    return None


def _active_quotes(quotes: list[_Quote], lines: list[str]) -> Iterator[_Quote]:
    for q in quotes:
        related = [other for other in quotes if (other.market, other.left, other.right) == (q.market, q.left, q.right)]
        if len(related) != 1:
            # Without a single quotation, shared currency and valuation facts do not select a period.
            continue
        if q.ratio is not None and any(re.fullmatch(
                r'(?:该|本|上述|此)(?:汇率|报价)(?:仍|尚|目前)?(?:待定|待确认|未确定|未核准|待公布|待挂牌)', line)
                for line in lines):
            continue
        reversed_direction = _PAIR.format(left=re.escape(q.right), right=re.escape(q.left))
        if any(_VOID.search(line) and (
                re.match(r'(?:上述|该|本)(?:报价|汇率|兑换规则)', line)
                or (q.left in line and q.right in line and q.market in line
                    and (re.search(q.pair, line) or not re.search(reversed_direction, line))))
               for line in lines):
            continue
        ban = re.escape(q.market) + r'(?:一律|已)?(?:禁止|不准|不得|不允许)(?:办理)?' + q.pair
        if any(re.fullmatch(ban, line) for line in lines):
            continue
        yield q


def _quote_evidence(q: _Quote, boundary: str) -> dict:
    evidence = {'quote': q.text, 'boundary': boundary, 'market': q.market, 'period': q.period,
                'from': q.left, 'to': q.right, 'rate_status': 'pending' if q.ratio is None else 'quoted'}
    if q.ratio is not None:
        evidence.update(from_unit=q.left_unit, to_unit=q.right_unit,
                        rate_numerator=q.ratio.numerator, rate_denominator=q.ratio.denominator)
    return evidence


def approved_exchange(card: dict, key: str) -> dict | None:
    texts = approved_text(card)
    if key not in RULES or not texts:
        return None
    rule, limits = texts
    if re.search(r'仅供(?:示例|演示|参考)|(?:以下|下述|上述)(?:报价|汇率|兑换|规则)?(?:仅为|只是|为|是)?(?:实例|示例|假设|旧案|旧方案)|'
                 r'(?:^|[。；;！？!?\r\n])\s*(?:旧方案|原方案|示例|反例|假设|弃案)(?:如下|如下所示)?[：:。；;！？!?\r\n]',
                 rule + '。' + limits):
        return None
    rules = [s.strip() for s in _SENTENCES.split(rule) if s.strip()]
    bounds = [s.strip() for s in _SENTENCES.split(limits) if s.strip()]
    # A pending quote has no numeric separator. Recover the named market from its actual boundary.
    named = set()
    for line in bounds:
        match = re.search(r'(?:可|限)在(?P<market>' + _NAME + r')(?=将|用)', line)
        match = match or re.match(r'(?P<market>' + _NAME + r')的(?=' + _NAME + r'(?:兑|换))', line)
        if match:
            named.add(match['market'])
    markets = sorted(named, key=len, reverse=True)
    quotes = [q for line in rules if (q := _quote(line, markets))]
    active = list(_active_quotes(quotes, rules + bounds))
    candidates = []
    for q in active:
        detail = _domain(q, key, rules, bounds)
        if detail and (boundary := _bounds(q, bounds) or detail.get('settlement')):
            candidates.append((q, {**_quote_evidence(q, boundary), **detail}))
    if len(candidates) != 1:
        return None
    adopted, evidence = candidates[0]
    reverse = [_quote_evidence(other, permit) for other in active
               if (other.market, other.period, other.left, other.right)
               == (adopted.market, adopted.period, adopted.right, adopted.left)
               and other.ratio is not None and (permit := _bounds(other, bounds))]
    if len(reverse) == 1:
        evidence['reverse_quote'] = reverse[0]
    return card_proof(card, rule, limits, evidence)
