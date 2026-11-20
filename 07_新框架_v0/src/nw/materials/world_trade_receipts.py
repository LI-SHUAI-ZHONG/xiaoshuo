"""Compare explicit in-scope transaction charges with the adopted world-card terms."""
from collections.abc import Iterable, Iterator
from fractions import Fraction
import re

from nw.materials import world_trade as trade
from nw.materials.semantic_application import require
from nw.materials.world_exchange import NUMBER, amount_value
from nw.materials.world_market import factual_market_claim


# Keep the same grammar as approved fee clauses while accepting written equivalents of their numbers.
_FIXED = re.compile(trade._FEE.pattern.replace(trade._NUMBER, NUMBER))
_DENOMINATION = re.compile(rf'({NUMBER})({trade._UNIT})(.+)')
_FEE_FORMS = (_FIXED, trade._RATE_FEE, trade._ZERO_FEE)
_SENTENCE = re.compile(r'[^。；;！？!?\r\n]+[？?]?')
_ALTERNATE = re.compile(r'另行|特批|例外|另按|另据|临时|优惠|特殊|若|假如|(?:期间|时期|季节|期|季|时|后|前|夜间)\s*$')
_CONFIRMED = re.compile(r'^(?:核实后|确认后|查明|证实|账册载明|实际|确已|最终实际)')
_ACTUAL_PAYMENT = re.compile(r'(' + trade._ROLE + r')(?:实际|确已|已经|最终|当场|确实)(?=支付|缴纳|承担|按|免缴)')
_FEE_FIRST = re.compile(r'(每笔|每次)?(手续费|佣金|托管费|鉴定费|过秤费|交易税)由(.+)')


def _fee(match: re.Match) -> tuple:
    if 'fee' in match.groupdict():
        measure = _DENOMINATION.fullmatch(match['fee'])
        assert measure is not None  # _FIXED supplied the same number/unit grammar.
        number, unit, currency = measure.groups()
        value = amount_value(number)
        return ('fixed', value, unit, currency) if value else ('free',)
    if 'rate' in match.groupdict():
        basis = match['basis'].replace('成交金额', '成交额')
        percent = Fraction(match['rate'][:-1])
        return ('rate', percent, basis) if percent else ('free',)
    return ('free',)


def _read_fee(clause: str) -> re.Match | None:
    if m := _FEE_FIRST.fullmatch(clause):
        clause = (m[1] or '') + m[3] + m[2]
    clause = _ACTUAL_PAYMENT.sub(r'\1', clause)
    return next((m for form in _FEE_FORMS if (m := form.fullmatch(clause))), None)


def _claims(text: str, deal: trade._Deal, boundary: str) -> Iterator[re.Match]:
    market, method = re.escape(deal.market), re.escape(deal.method)
    # An explicit market and transaction method limit the comparison to this approved deal.
    scope = re.compile(r'(?:^|[\s，,：:]|确认|证实|核实|查明|载明|实际)'
                       + rf'(?:(?:在|于){market}(?:进行|举行|办理|开展){method}|(?:在|于)?{market}的{method})'
                       + r'(?:中|时|期间)?[，,：:]?\s*')
    known = {m[0] for matches in deal.facts.values() for m in matches}
    for found in _SENTENCE.finditer(text):
        statement = found[0]
        for venue in scope.finditer(statement):
            before = statement[:venue.start()].rsplit('，', 1)[-1].strip()
            if before and _ALTERNATE.search(before) and before not in boundary and not _CONFIRMED.match(venue[0]):
                continue
            for part in re.finditer(r'[^，,：:]+', statement[venue.end():]):
                start = venue.end() + part.start()
                clause = part[0].strip().rstrip('？?')
                if not clause:
                    break
                if clause in known or (clause in boundary and re.search(r'时|后|期间', clause)):
                    continue
                confirmed = _CONFIRMED.match(clause)
                if confirmed:
                    start += confirmed.end()
                    clause = clause[confirmed.end():]
                recognized = (_read_fee(clause) or trade._TENDER.fullmatch(clause) or trade._REFUSAL.fullmatch(clause))
                if not recognized:
                    break
                if factual_market_claim(statement, start, venue.end() + part.end()):
                    yield recognized


def check_trade_claims(key: str, rule: str, limits: str, texts: Iterable[str]) -> None:
    """Check only determinate, factual charges or tender assertions in the receipt's cited fields."""
    if key not in ('C00544', 'C00550', 'C00555'):
        return
    fields = tuple(texts)
    for deal in trade._deals(rule):
        proof = trade._proof(deal, key, rule, limits)
        if not proof:
            continue
        approved: dict[str, dict[str, tuple]] = {}
        for form in (trade._FEE, trade._RATE_FEE, trade._ZERO_FEE):
            for fee in deal.facts[form]:
                approved.setdefault(fee['component'], {})[fee['actor']] = _fee(fee)
        tender = deal.one(trade._TENDER)
        for text in fields:
            for match in _claims(text, deal, proof['boundary']):
                if key == 'C00544':
                    if tender and match.re is trade._REFUSAL and match['receiver'] in (None, tender['receiver']):
                        require(match['money'] != tender['money'], key + ' 下游交易拒收了本场获准通行的货币')
                    if (tender and match.re is trade._TENDER and match['object'] == tender['object']
                            and match['receiver'] == tender['receiver'] and re.search(r'(?:只|仅)接受', tender[0])):
                        require((match['payer'], match['money']) == (tender['payer'], tender['money']),
                                key + ' 下游支付方或币种与该接受方的专用收款条件不符')
                    continue
                if 'component' not in match.groupdict() or match['component'] not in approved:
                    continue
                payers = approved[match['component']]
                actor, claimed = match['actor'], _fee(match)
                if actor not in payers:
                    if claimed == ('free',) or all(value == ('free',) for value in payers.values()):
                        continue  # Another participant's exemption does not change the approved payer's fee.
                    if not re.fullmatch(trade._ROLE, actor):
                        continue  # An added name or qualifier does not establish a different payer.
                    if any(payer.startswith(actor) for payer in payers):
                        continue
                    require(False, key + ' 下游交易费用的承担方与该市场及方式的批准规则不符')
                agreed = payers[actor]
                # A particular payment against a percentage might be correct at an unstated sale price.
                if agreed[0] == 'rate' and claimed[0] == 'fixed' and not match[0].startswith(('每次', '每笔')):
                    continue
                require(agreed == claimed, key + ' 下游交易费用与批准的金额、费率口径或免缴条件不符')
