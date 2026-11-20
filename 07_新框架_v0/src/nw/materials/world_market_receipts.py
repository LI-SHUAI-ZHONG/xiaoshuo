"""Check explicit, scoped market claims in the actual products cited by a receipt."""
from collections.abc import Iterator
from fractions import Fraction
import re

from nw.materials.semantic_application import require
from nw.materials.world_exchange import RULES as EXCHANGE_RULES, NUMBER, UNIT, amount_value, approved_exchange
from nw.materials.world_market import POLICY, RULES as VALUE_RULES, factual_market_claim


_TRADE_RECEIPTS = {'C00544', 'C00550', 'C00555'}
_SENTENCES = re.compile(r'[^。；;！!？?\n]+[。；;！!？?]?')
_SCOPE_CHANGE = re.compile(r'钱市|盐市|集市|市场|钱庄|交易所|兑换所|柜台|(?:到|在|转至|进入|入|说起|改用|回忆|翌|下|次|另)[^，,。]{0,8}(?:期间|期|季|周|年|月)')
_LOCAL_DESK = re.compile(r'(?:^的?|向(?:当地|该)?|的|当地|该|本地|本市场的)(?:钱庄|柜台|兑换所)')
_NUM_CHAR = r'[\d.．零〇一二两三四五六七八九十百千万点半]'
_CLAIM_UNIT = rf'(?:{UNIT}|盒|包|盘|篮|缸|捆|扎|叠|组)'
_VERB = r'(?:实际)?(?:可兑换为|可兑换|兑换为|兑换到|兑换了|兑换|可兑|兑得|兑成|换取了|换取|折合|折算为|相当于|等值于|换回|可换|换成|换得|换|兑|[=＝])'


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _in_scope(prefix: str, market: str, period: str) -> bool:
    # Scope belongs to this assertion. A journey to another market or season ends it.
    def changed(text: str) -> bool:
        return bool(_SCOPE_CHANGE.search(_LOCAL_DESK.sub('', text)))

    start = r'(?:^|[\s，,：:。的在于到至从当逢值是]|证实|确认|查明|载明|记录显示)'
    area = start + re.escape(market)
    time = start + re.escape(period)
    adjacent = start + '(?:' + re.escape(market + period) + '|' + re.escape(period + market) + ')'
    if any(not changed(prefix[m.end():]) for m in re.finditer(adjacent, prefix)):
        return True
    for a in re.finditer(area, prefix):
        for t in re.finditer(time, prefix):
            first, last = sorted((a, t), key=lambda m: m.start())
            between = prefix[first.end():last.start()]
            tail = prefix[last.end():]
            if len(between) <= 32 and not changed(between) and not changed(tail):
                return True
    return False


def _check_claim(evidence: dict, statement: str, claim: re.Match, inverse: bool) -> None:
    prefix = statement[:claim.start()]
    if not _in_scope(prefix, evidence['market'], evidence['period']):
        return
    if claim.groupdict().get('payout') and not re.search(r'(?:付出|支付|付了|交出|交付|交了|付|交)$', prefix):
        return
    if not factual_market_claim(statement, claim.start(), claim.end()):
        return
    operator = claim.groupdict().get('operator', '') or claim.groupdict().get('payout', '')
    accounted = re.search(r'折合|折算|相当于|等值|[=＝]', operator)
    if not operator:
        accounted = re.search(r'折合|折算|对账|账面换算', re.split(r'[，,]', prefix)[-1][-16:])
    if inverse and accounted:
        # An accounting equivalence also used to execute a trade needs permission in that direction.
        after = statement[claim.end():]
        if re.match(r'(?:[，,]\s*)?(?:(?:的|该|上述)?(?:比率|比例|牌价|汇率))?(?:据此|按此|来|当场|当即|实际|已经|完成|反向)*'
                    r'(?:兑付|成交|完成兑换|结清货款)', after):
            accounted = False
    basis = evidence
    if inverse and not accounted:
        basis = evidence.get('reverse_quote')
        require(basis is not None, '市场回执中的反向兑付或挂牌缺少独立批准的反向汇率与权限')
    require('rate_numerator' in basis and 'rate_denominator' in basis,
            '市场回执不能把已批准的待定汇率写成已挂牌或已成交的数值')
    expected = Fraction(basis['rate_numerator'], basis['rate_denominator'])
    units = (basis['from_unit'], basis['to_unit'])
    if inverse and accounted:
        expected = 1 / expected
        units = units[::-1]
    if operator:
        require((claim['u'], claim['v']) == units, '市场回执使用了该报价未经批准的计量单位')
    incoming, outgoing = amount_value(claim['a']), amount_value(claim['b'])
    require(incoming > 0 and outgoing == incoming * expected, '市场回执中的成交或挂牌汇率与同市场、同时期的批准报价不符')


def _assert_quote(evidence: dict, text: str) -> None:
    for inverse in (False, True):
        left, right = evidence['from'], evidence['to']
        if inverse:
            left, right = right, left
        source, target = re.escape(left), re.escape(right)
        price = (rf'(?<!{_NUM_CHAR})(?P<a>{NUMBER})\s*(?P<u>{_CLAIM_UNIT}){source}\s*(?P<operator>{_VERB})\s*'
                 rf'(?P<b>{NUMBER})\s*(?P<v>{_CLAIM_UNIT}){target}(?!券|筹|票|凭证|碎片|样币)')
        paid = (rf'(?<!{_NUM_CHAR})(?P<a>{NUMBER})\s*(?P<u>{_CLAIM_UNIT}){source}\s*[，,]\s*'
                rf'(?P<payout>(?:当场|当即|实际)?(?:换回|兑得|兑回|实收))\s*'
                rf'(?P<b>{NUMBER})\s*(?P<v>{_CLAIM_UNIT}){target}(?!券|筹|票|凭证|碎片|样币)')
        ratio = (rf'{source}(?:兑|换|兑换为){target}(?:的)?(?:挂牌价|汇率|牌价|兑换比例|报价)'
                 rf'(?:是|为|按|报|[：:])\s*(?P<a>{NUMBER})\s*[:：比]\s*(?P<b>{NUMBER})(?!{_NUM_CHAR})')
        for sentence in _SENTENCES.finditer(text):
            for expr in (price, paid, ratio):
                for claim in re.finditer(expr, sentence[0]):
                    _check_claim(evidence, sentence[0], claim, inverse)


def check_market_receipt(handoff: dict, fields: list[object], products: dict, context: dict, key: str) -> None:
    if (context.get('world_market_policy') != POLICY or handoff['origin']['stage'] != 'world_design'
            or key not in EXCHANGE_RULES and key not in VALUE_RULES and key not in _TRADE_RECEIPTS):
        return
    refs = handoff['requirement']['input_refs']
    bodies = products['world_design']['products']['members']
    indices = {int(ref['path'].split('/')[2]) for ref in handoff['actual_inputs']
               if re.fullmatch(r'/members/\d+/body/(rule|limits)', ref['path'])}
    texts = [text for field in fields for text in _strings(field)]
    for index in indices:
        body = bodies[index]['body']
        if key in VALUE_RULES:
            from nw.materials.world_market import check_valuation_claims
            check_valuation_claims(key, body['rule'], body['limits'], texts)
            continue
        if key in _TRADE_RECEIPTS:
            from nw.materials.world_trade_receipts import check_trade_claims
            check_trade_claims(key, body['rule'], body['limits'], texts)
            continue
        for card in context['approved_cards']:
            ident = card.get('card_id')
            if (not ident or f'approved:{ident}:/body/rule' not in refs or f'approved:{ident}:/body/limits' not in refs
                    or card['body'].get('rule') != body['rule'] or card['body'].get('limits') != body['limits']):
                continue
            proof = approved_exchange(card, key)
            require(proof is not None, '市场回执缺少世界规则采用的同卡汇率依据')
            for text in texts:
                _assert_quote(proof['evidence'], text)
            break
        else:
            require(False, '市场回执引用的批准卡与世界产物不相符')
