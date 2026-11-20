"""Market value, exchange and trade evidence used by world design."""
from collections.abc import Iterable
from decimal import Decimal
import re

from nw.materials.world_resources import approved_text, card_proof


POLICY = 'world-market-prerequisites-v1'
RULES = {
    'C00429': '同一市场和时期的实际减产、到市供给、需求、替代资源的可得性及减产所致的实际涨价',
    'C00524': '同一市场和时期的资源用途类别、实际使用、地区供需及明确的价值衡量口径',
}


def market_families() -> tuple:
    from nw.materials import world_exchange, world_trade

    return ((RULES, approved_valuation), (world_exchange.RULES, world_exchange.approved_exchange),
            (world_trade.RULES, world_trade.approved_trade))


_NAME = r'[\u3400-\u9fffA-Za-z]{2,16}?'
_PERIOD = r'[\u3400-\u9fff0-9]{1,10}?(?:期间|期|季|年|月|旬)'
_SCOPE = re.compile(r'(?:在)?(?P<period>' + _PERIOD + r')[，,](?P<market>' + _NAME + r')的(?P<item>'
                    + _NAME + r')(?=属于|列为|归为|每(?:日|周|旬|月|季|年)产量)')
_AMOUNT = r'[0-9]{1,10}(?:\.[0-9]{1,4})?'
_MEASURE = r'(?:千克|公斤|标准箱|[箱袋瓶枚包升斤桶份件块张盏锭筐颗吨片])'
_INTERVAL = r'每(?:日|周|旬|月|季|年)'
_UNCERTAIN = re.compile(r'示例|例如|假设|或许|可能|尚待|待定|未定|待核|待补|拟定|暂定|旧例|作废|撤销|'
                        r'未知|未确认|未生效|草案|仅供讨论|该(?:口径|报价|价格|减产|估价|规则)(?:无效|未生效|不成立)|不再(?:采用|适用|执行)|并非|据说')
_GENERIC = re.compile(r'(?:某种?|该|其他|相关|当地|本地|指定|具体|实际|通常|一般)?'
                      r'(?:资源|物资|货物|市场|地区|类别|用品|用途|资源类型|替代品|货币|钱币|条件|需求|价值|尺度|使用|相关用途)')


def _specific(text: str) -> bool:
    return len(text) >= 2 and not _GENERIC.fullmatch(text) and not _UNCERTAIN.search(text)


def _named_tender(value: str) -> bool:
    return value == '元' or not _GENERIC.fullmatch(value[1:])


def _proof_for(key: str, scope: re.Match, text: str, limits: str) -> dict | None:
    market, period, item = (scope[group] for group in ('market', 'period', 'item'))
    if not all(_specific(v) for v in (market, period, item)):
        return None
    # Keep locations and resource names literal when assembling their evidence.
    region, when, good = map(re.escape, (market, period, item))
    bound = (good + r'(?:的)?(?:价值|市价|估价|报价|价格)(?:核算|口径|比较|变动)?'
             + r'(?:仅限于|仅限|仅适用于|只用于)' + region + r'(?:的)?' + when)
    bounds = [s.strip() for s in re.split(r'[。；;！？\r\n]', limits) if re.fullmatch(bound, s.strip())]
    if len(bounds) != 1:
        return None
    parts = [s.strip() for s in re.split(r'[，,。；;！？\r\n]+', text) if s.strip()]
    if len(parts) < 5 or _UNCERTAIN.search(text):
        return None
    if key == 'C00524':
        kind = re.fullmatch(r'(?:属于|列为|归为)(' + _NAME + r')', parts[0])
        use = re.fullmatch(r'(?:' + good + r')?(?:用来|用于|用作)(?P<use>[^，。]{2,24})', parts[1])
        if (not kind or not use or not _specific(kind[1]) or not _specific(use['use'])
                or kind[1] in (item, use['use']) or re.search(r'^(?:不|未|没有|别处|他物)', use['use'])):
            return None
        index = 2
        proof = {'category': parts[0], 'use': parts[1]}
        interval, unit = '', ''
    else:
        harvest = re.fullmatch(r'(?P<interval>' + _INTERVAL + r')产量(?:由|从)(?P<before>' + _AMOUNT
                               + r')(?P<unit>' + _MEASURE + r')(?:降至|减至|降到|减为)(?P<after>'
                               + _AMOUNT + r')(?P=unit)', parts[0])
        if not harvest or Decimal(harvest['before']) <= Decimal(harvest['after']):
            return None
        interval, unit = harvest['interval'], harvest['unit']
        index, proof = 1, {'production': parts[0]}
    supply = re.fullmatch(r'(?:' + good + r')?(?P<interval>' + _INTERVAL + r')?(?:到市|运抵|实际到市|供应|实际供应)'
                          + r'(?P<qty>' + _AMOUNT + r')(?P<unit>' + _MEASURE + r')', parts[index])
    if supply:
        if (unit and unit != supply['unit']) or (interval and supply['interval'] not in (None, interval)):
            return None
        interval, unit = interval or supply['interval'], supply['unit']
        demand = re.fullmatch(r'(?:' + good + r'|当地|本地|本市)?(?P<interval>' + _INTERVAL + r')?(?:需求|需要|实际需求)'
                              + _AMOUNT + re.escape(unit), parts[index+1])
        if not demand or demand['interval'] not in (None, interval):
            return None
    else:
        delivery = re.fullmatch(r'(?P<supplier>' + _NAME + r')(?:从|自)(?P<origin>' + _NAME
                                + r')(?:运入|运来|运抵|调入)' + good, parts[index])
        orders = re.fullmatch(r'(?P<buyer>' + _NAME + r')每(?:夜|日|周|旬|月|季)(?:领用|订购|采购|求购)' + good,
                              parts[index+1])
        if not delivery or not orders or not all(_specific(v) for v in (*delivery.groups(), orders['buyer'])):
            return None
    proof.update(supply=parts[index], demand=parts[index+1])
    quote = r'每' + re.escape(unit) + r'(?:' + good + r')?'
    money = r'(?P<price>' + _AMOUNT + r')(?P<tender>[枚张两厘克锭点][\u3400-\u9fff]{1,8}?|元)'
    # A final price or rank records the author's value. A change requires comparable quotes in the same units.
    if key == 'C00524':
        quoted_unit = re.escape(unit) if unit else _MEASURE
        quote = r'每(?P<quoted_unit>' + quoted_unit + r')(?:' + good + r')?'
        price = re.fullmatch(r'(?:' + good + r'|当地|本市)?(?:的)?(?:市价|估价|价值)(?:为|按|以)'
                             + quote + money + r'(?:计)?', parts[index+2])
        rank = re.fullmatch(good + r'以(?P<basis>[^，。]{2,20})为尺度列为(?P<rank>[\u3400-\u9fff]{1,6}等)', parts[index+2])
        if not ((price and Decimal(price['price']) > 0 and _named_tender(price['tender'])) or (rank and _specific(rank['basis']))):
            return None
        proof['valuation'] = parts[index+2]
        if price:
            proof.update(price=price['price'], tender=price['tender'], unit=price['quoted_unit'])
        last = index + 2
    else:
        alt = re.fullmatch(r'(?:' + good + r')?(?:可用|可由)(?P<other>' + _NAME + r')(?:替代|替换)', parts[index+2])
        if not alt or not _specific(alt['other']) or alt['other'] == item or len(parts) < index + 5:
            return None
        other = re.escape(alt['other'])
        availability = re.fullmatch(r'(?:本期|同期|当地|本旬)?' + other + r'(?:售罄|断供|库存充足|'
                                    + r'(?:只到货|到货|库存|仅剩)' + _AMOUNT + _MEASURE + r')', parts[index+3])
        cause = r'(?:(?:因|由于|受)(?:本次)?减产(?:影响)?[，,]?|(?:本次)?减产(?:使|导致))'
        last = index + 4
        valuation = parts[last]
        if re.fullmatch(cause, valuation) and last + 1 < len(parts):
            joined = re.search(re.escape(valuation) + r'[，,]\s*' + re.escape(parts[last + 1]), text)
            if not joined:
                return None
            valuation = joined[0]
            last += 1
        price = re.fullmatch(cause + r'(?:' + good + r')?(?:的)?(?:当地)?(?:市价|估价|报价)(?:由|从)' + quote + money
                             + r'(?:涨至|升至|升到|涨到)(?:' + quote + r')?(?P<new>' + _AMOUNT
                             + r')(?P=tender)', valuation)
        if not availability or not price or not _named_tender(price['tender']):
            return None
        before, after = Decimal(price['price']), Decimal(price['new'])
        if after <= before:
            return None
        proof.update(substitute=parts[index+2], availability=parts[index+3], valuation=valuation,
                     price=price['new'], previous_price=price['price'], tender=price['tender'], unit=unit)
    if len(parts) != last + 1:
        return None
    return dict(resource=item, market=market, period=period, **proof, boundary=bounds[0])


_PENDING_EXCHANGE = re.compile(_NAME + r'(?:在|于)' + _PERIOD + r'[，,]\s*' + _NAME + r'(?:兑|兑换为)' + _NAME
                               + r'(?:的)?(?:挂牌价|汇率)(?:仍|尚)?(?:待定|待确认|待公布)')


def _valuation_evidence(key: str, rule: str, limits: str) -> dict | None:
    # A card can approve a resource price while a separate currency pair still awaits its own quote.
    rule = '。'.join(part for part in re.split(r'[。；;\n]', rule) if not _PENDING_EXCHANGE.fullmatch(part.strip()))
    if _UNCERTAIN.search(limits) or _UNCERTAIN.search(rule):
        return None
    starts = [m for m in _SCOPE.finditer(rule)
              if not rule[:m.start()].strip() or re.search(r'[。；;\n]\s*$', rule[:m.start()])]
    candidates = []
    accounts = set()
    for index, scope in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(rule)
        text = rule[scope.end():end]
        is_classification = text.startswith(('属于', '列为', '归为'))
        if is_classification != (key == 'C00524'):
            continue
        identity = scope['market'], scope['period'], scope['item']
        if identity in accounts:
            return None
        accounts.add(identity)
        # An independent rule may follow the quotation on a card shared with other steps.
        # Keep subsequent qualifications about this quotation attached to it.
        for sentence in re.finditer(r'[。；;\n]\s*(?=[^。；;\s])', text):
            after = text[sentence.end():]
            if (scope['item'] not in after and scope['market'] not in after
                    and not re.search(r'(?:上述|本次|原有|该)(?:估价|报价|市价|口径|规则)|实际(?:市价|售价|供应|需求)', after)):
                prefix = text[:sentence.start()]
                if proof := _proof_for(key, scope, prefix, limits):
                    candidates.append(proof)
                    break
        else:
            if proof := _proof_for(key, scope, text, limits):
                candidates.append(proof)
    return candidates[0] if len(candidates) == 1 else None


def approved_valuation(card: dict, key: str) -> dict | None:
    texts = approved_text(card)
    if key not in RULES or not texts:
        return None
    rule, limits = texts
    evidence = _valuation_evidence(key, rule, limits)
    return card_proof(card, rule, limits, evidence) if evidence else None


_NONFACT = re.compile(r'若按|假设|如果|倘若|假如|设想|打算|拟按|计划|准备|询问|打听|询价|猜测|怀疑|质疑|'
                      r'调查|查证|查核|核查|核对是否|核验是否|是否|能否|谣言|谣传|传闻|传言|听说|听闻|听到|'
                      r'据称|据说|声称|谎称|假称|佯称|冒称|伪造|假消息|拒绝|否认|并非|不是|尚未|并未|'
                      r'没有按|不按|不会按|未按|取消|作废|不再按|待核|试图|未能|[他她]说')
_CONFIRMATION = re.compile(r'但实际上|但实际|实则|事实上|确认后|核实后|随后实际|最终实际|'
                           r'(?:但|然而|随后|最终)(?:经|当地|查验)?(?:账册|钱庄|账房|公告|实账|票据)?(?:证实|载明|确认|查明)')
_RETRACTED = re.compile(r'^\s*[，,]?\s*(?:的说法|的消息|此说|这|那|该说法|该价格|该报价)?'
                        r'(?:只|仅|纯|实)?(?:是|属|系|为)?(?:未经证实|未获证实|传闻|传言|谣言|假消息|假设|伪造)')


def factual_market_claim(statement: str, start: int, end: int) -> bool:
    """Exclude hearsay, questions and intentions local to this particular quotation."""
    if statement.rstrip().endswith(('?', '？')):
        return False
    prefix = _CONFIRMATION.split(statement[:start])[-1]
    if _NONFACT.search(prefix):
        return False
    if any(prefix.rfind(opening) > prefix.rfind(closing) for opening, closing in (('“', '”'), ('「', '」'), ('『', '』'))):
        return False
    tail = statement[end:]
    first = re.split(r'[，,。；;]', tail, maxsplit=1)[0]
    return not (re.search(r'的(?:传言|传闻|谣言|说法未经证实|假消息)', first) or _RETRACTED.match(tail))


def check_valuation_claims(key: str, rule: str, limits: str, texts: Iterable[str]) -> None:
    """Compare explicit local market quotations in the fields cited by this receipt."""
    from nw.materials.semantic_application import require
    from nw.materials.world_exchange import NUMBER, amount_value

    if not (basis := _valuation_evidence(key, rule, limits)):
        return
    area, when, good = (re.escape(basis[field]) for field in ('market', 'period', 'resource'))
    scope = rf'(?:(?:在)?{when}(?:的|[，,])?(?:在)?{area}(?:的|[，,])?|{area}(?:在|于){when}[，,]?)'
    subject = r'(?:^|[，,：:\s]|查明|核实|证实|确认|载明|公布|宣布|记录显示)' + scope + good
    label = r'(?:的)?(?:官方)?(?:现行市价|当前市价|挂牌价|市价|估价|报价|售价|现价)'
    head = subject + label
    quantity = rf'每\s*(?:(?P<count>{NUMBER})\s*)?(?P<unit>{_MEASURE})(?:{good})?\s*'
    money = rf'(?P<paid>{NUMBER})\s*(?P<tender>[枚张两厘克锭点][\u3400-\u9fff]{{1,8}}?|元)'
    end = r'(?=$|[，,。；;！!]|结算|成交|计价)'
    point = quantity + money
    direct = re.compile(head + r'(?:为|按|以|现为|定为|是|现报)' + point + end)
    per_unit = re.compile(subject + quantity + label + r'(?:为|按|是|定为)?' + money + end)
    earlier = point.replace('<count>', '<old_count>').replace('<unit>', '<old_unit>').replace('<paid>', '<old_paid>').replace('<tender>', '<old_tender>')
    movement = re.compile(head + r'(?:由|从)' + earlier + r'(?P<direction>升至|涨至|涨到|跌至|降至|跌到|持平于)' + point + end)

    def verify(match: re.Match, prefix: str, approved: str | None) -> None:
        count = amount_value(match[prefix + 'count'] or '1')
        require(approved is not None and count > 0 and match[prefix + 'unit'] == basis.get('unit')
                and match[prefix + 'tender'] == basis.get('tender')
                and amount_value(match[prefix + 'paid']) == count * amount_value(approved),
                key + ' 下游产物所述当地市价与批准的计量、币种或金额不符')

    for text in texts:
        for sentence in re.findall(r'[^。；;！？!?\r\n]+[。；;！？!?]?', text):
            for form in (direct, per_unit):
                for match in form.finditer(sentence):
                    if factual_market_claim(sentence, match.start('paid'), match.end()):
                        verify(match, '', basis.get('price'))
            for match in movement.finditer(sentence):
                if not factual_market_claim(sentence, match.start('old_paid'), match.end()):
                    continue
                verify(match, '', basis.get('price'))
                if 'previous_price' in basis:
                    verify(match, 'old_', basis['previous_price'])
                    require(match['direction'] in ('升至', '涨至', '涨到'), key + ' 下游产物改写了减产所致的涨价方向')
