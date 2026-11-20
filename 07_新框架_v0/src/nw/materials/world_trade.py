"""Check each adopted transaction against its own venue, participants and conditions."""
from collections import defaultdict
from dataclasses import dataclass, field
import re

from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00544': '可用货币、具体交易场合、接受方以及同种货币的通行限制',
    'C00550': '至少两种实际交易方式各自的准入条件、费用、争议处理和适用范围',
    'C00555': '具体交易方式中实际承担费用、时间或风险的参与方和成本适用条件',
    'C00556': '交易渠道、作者确定的阶层资格或份额及该资格的明确例外规定',
    'C01762': '既有交易方式、实际交换资源、参与资格、交割条件和该交易的例外规定',
}

_NAME = r'[\u3400-\u9fffA-Za-z0-9]{2,20}?'
_METHOD = (r'(?:[\u3400-\u9fff]{0,8}?(?:交易|买卖|拍卖|议价|竞拍|寄售|赊购|赊销|竞价|易物|代销|直购|预购|交割))')
_HEADERS = (
    re.compile(rf'^(?:在|于)(?P<market>{_NAME})(?:进行|举行|办理|开展)(?P<method>{_METHOD})(?:时|期间|中)?[，,：:]'),
    re.compile(rf'^(?P<market>{_NAME})的(?P<method>{_METHOD})(?:中|时|期间)?[，,：:]'),
)
_ROLE = r'(?:买方|卖方|双方|委托方|寄售人|竞买人|竞拍人|承运方|承兑方|承买人|出卖人|收货方|投标人|供货方|摊主)'
_ACTOR = rf'(?:{_ROLE})(?:[\u3400-\u9fff]{{2,8}})?'
_NUMBER = r'(?:[1-9]\d{0,7}(?:\.\d{1,6})?|[一二两三四五六七八九十百千万]+)'
_UNIT = r'(?:枚|张|两|块|元|文|袋|箱|斤|升|束|包|瓶|桶|份|锭|颗|匹|件|丈|根|克|船|捆|支|卷|罐|片|条)'
_AMOUNT = _NUMBER + _UNIT
_UNSET = re.compile(r'尚未确定|待定|未定|待核|待确认|待补|仅作示例|举例|例如|假设|仅作演示|拟定|暂定|旧方案|仅供参考|已废止')
_NEGATED = re.compile(r'并非|不是|尚未|不再|并未|不会|不必|不须|无需等待|不应|拒绝|不接受|不得|未获|取消|作废|暂停|未授权')
_GENERIC = re.compile(r'(?:相关|某种|某个|指定|若干|特定|相应|有关|正常|一般|某地|某市|某方|任意|'
                      r'已定|符合条件|满足要求|按规定|完成手续)|^(?:货币|物品|资源|商品|市场|地点|'
                      r'接受方|权限|证件|凭证|文件|条件|通用单位|阶层|风险|成本|货款|交易类型|交易方式)$')
_TENDER = re.compile(rf'(?P<receiver>{_NAME})(?:只|仅)?(?:接受|准许)(?P<payer>{_ROLE})(?:使用|用|以)(?P<explicit>货币)?'
                     rf'(?P<money>{_NAME})(?:支付|结清)(?P<object>{_NAME})')
_REFUSAL = re.compile(rf'(?P<receiver>{_NAME})?(?:一律|现已|已)?(?:拒收|禁止使用|不接受|不再收取)'
                      rf'(?P<money>{_NAME})(?:支付|结算)?')
_ENTRY = re.compile(rf'(?P<actor>{_ACTOR})(?:须|需|必须)(?:出示|提交|验明|持有)(?P<permit>{_NAME})(?:才可入场)?')
_FEE = re.compile(rf'(?:每(?:笔|次)(?:由)?)?(?P<actor>{_ACTOR})(?:须|要|需)?(?:支付|缴纳|承担)'
                  rf'(?P<fee>{_AMOUNT}{_NAME})(?:作为|的)?(?P<component>手续费|佣金|托管费|鉴定费|过秤费|交易税)')
_RATE_FEE = re.compile(rf'(?:每(?:笔|次)(?:由)?)?(?P<actor>{_ACTOR})(?:须|需)?按(?:本笔|当笔)?'
                       r'(?P<basis>成交额|成交金额|货值|寄售价款)(?:的)?(?P<rate>\d{1,3}(?:\.\d{1,4})?[%％])'
                       r'(?:支付|缴纳)(?P<component>手续费|佣金|交易税)')
_ZERO_FEE = re.compile(rf'(?P<actor>{_ACTOR})(?:免缴|免付|无需支付)(?P<component>手续费|佣金|交易税)')
_TIME = re.compile(rf'(?P<actor>{_ACTOR})(?:须|需|必须)(?:等候|等待)(?P<duration>{_NUMBER}(?:日|天|个时辰|小时|刻钟|周))'
                   r'(?P<operation>验货|验票|核印|结算|清算|过秤|交割)')
_RISK = re.compile(rf'(?P<actor>{_ACTOR})(?:在|遇)(?P<trigger>{_NAME})时(?:承担|负担)(?P<loss>{_NAME})'
                   r'(?:的风险|风险|损失)')
_DISPUTE = re.compile(rf'(?:发生)?(?:争议|纠纷)(?:时)?由(?P<judge>{_NAME})(?:凭|依据|按)(?P<basis>{_NAME})'
                      r'(?:裁定|仲裁|调解|裁决|复核)')
_CLASS = re.compile(rf'(?:仅|只限|只有)(?P<rank>{_NAME})阶层的(?P<actor>{_NAME})(?:凭|持)(?P<permit>{_NAME})'
                    rf'(?:可|方可|才可)(?P<operation>竞买|竞拍|购买|承购|寄售|换取)(?P<item>{_NAME})')
_QUOTA = re.compile(rf'(?P<rank>{_NAME})阶层的(?P<actor>{_NAME})(?:凭|持)(?P<permit>{_NAME})'
                    rf'(?:每笔|每次|每日)(?:至多|限)(?P<operation>竞买|竞拍|购买|承购|寄售|换取)'
                    rf'(?P<quota>{_AMOUNT})(?P<item>{_NAME})')
_SWAP = re.compile(rf'(?:只有|仅)?持(?P<permit>{_NAME})的(?P<actor>{_NAME})(?:可|方可|才能|才可)'
                   rf'(?:用|以)(?P<give_amount>{_AMOUNT})(?P<give>{_NAME})'
                   rf'(?:换取|换得|兑换|购买|购入|买下)(?P<get_amount>{_AMOUNT})(?P<get>{_NAME})')
_DELIVER = re.compile(rf'(?P<actor>{_ROLE})(?:须|必须|需)在(?P<when>{_NAME})(?:前|后|时)'
                      rf'(?:核对|交付|验明|签收|出示)(?P<document>{_NAME})')
_CONDITION = r'(?:只在|仅在|仅当|遇)(?P<condition>[\u3400-\u9fff]{2,18}?)(?:后|时|期间)'
_OPEN = re.compile(_CONDITION + r'(?:才可|方可|才)?(?:受理|开市|成交|结算|办理|交割)')
_ITEMS = (_TENDER, _ENTRY, _FEE, _RATE_FEE, _ZERO_FEE, _TIME, _RISK, _DISPUTE, _CLASS, _QUOTA, _SWAP, _DELIVER)


def _specific(value: str) -> bool:
    return not _GENERIC.search(value) and not _NEGATED.search(value) and not _UNSET.search(value)


@dataclass
class _Deal:
    market: str
    method: str
    facts: dict = field(default_factory=lambda: defaultdict(list))
    refused: list[re.Match] = field(default_factory=list)
    interrupted: bool = False

    def one(self, *patterns: re.Pattern) -> re.Match | None:
        matches = [m for pattern in patterns for m in self.facts[pattern]]
        return matches[0] if len(matches) == 1 else None


def _deals(rule: str) -> list[_Deal]:
    found: dict[tuple[str, str], _Deal] = {}
    current = None
    for sentence in re.split(r'[。！？!?；;\r\n]', rule):
        text = sentence.strip()
        if not text:
            continue
        header = next((m for pattern in _HEADERS if (m := pattern.match(text))), None)
        if header:
            key = header['market'], header['method']
            current = found.setdefault(key, _Deal(*key)) if all(_specific(s) for s in key) else None
            text = text[header.end():]
        if current is None:
            continue
        for part in re.split(r'[，,]', text):
            clause = part.strip()
            if not clause:
                continue
            if refusal := _REFUSAL.fullmatch(clause):
                current.refused.append(refusal)
                continue
            if _UNSET.search(clause) or _NEGATED.search(clause):
                current.interrupted = True
                current = None
                break
            pair = next(((pattern, m) for pattern in _ITEMS if (m := pattern.fullmatch(clause))), None)
            if not pair:
                # A following subject cannot lend an unstated participant or fee to this transaction.
                current = None
                break
            pattern, match = pair
            if all(_specific(value) for name, value in match.groupdict().items() if name != 'explicit' and value):
                current.facts[pattern].append(match)
    return list(found.values())


def _scoped_tails(deal: _Deal, text: str) -> list[tuple[str, str]]:
    """Return only statements that identify this particular market and method."""
    tails = []
    prefix = re.escape(deal.market) + '的' + re.escape(deal.method)
    for sentence in re.split(r'[。；;！？!?\r\n]', text):
        line = sentence.strip()
        short = re.match(prefix, line)
        if short:
            tails.append((line, line[short.end():].lstrip('，,：: ')))
        else:
            scope = next((m for pattern in _HEADERS if (m := pattern.match(line))), None)
            if scope and (scope['market'], scope['method']) == (deal.market, deal.method):
                tails.append((line, line[scope.end():]))
    return tails


def _limits(deal: _Deal, limits: str, patterns: list[str]) -> str | None:
    matches = []
    for text, tail in _scoped_tails(deal, limits):
        if _UNSET.search(tail):
            return None
        for pattern in patterns:
            match = re.fullmatch(pattern, tail)
            if match and all(_specific(v) for v in match.groupdict().values() if v):
                matches.append(text)
    return matches[0] if len(matches) == 1 else None


def _exception(deal: _Deal, limits: str, item: str, operation: str, subject: str, actor: str = '') -> str | None:
    allowed_actor = re.escape(actor) if actor else _NAME
    exception = (_CONDITION + rf'(?:例外)?允许(?P<person>{allowed_actor})(?:凭|持)(?P<permit>{_NAME})'
                 + operation + re.escape(item))
    return _limits(deal, limits, [exception, '对上述' + subject + '(?:不设|没有)例外'])


def _proof(deal: _Deal, key: str, rule: str, limits: str) -> dict | None:
    terms = [tail for _, tail in _scoped_tails(deal, rule + '。' + limits)]
    if deal.interrupted or any(re.match(r'(?:现已|目前|一律|已)?(?:取消|停办|废止|撤销|拒绝受理|永久关闭|不再采用|不再受理)', t) for t in terms):
        return None
    evidence = {'market': deal.market, 'method': deal.method}
    if key == 'C00544':
        tender = deal.one(_TENDER)
        if not tender or (not tender['explicit'] and not re.search(r'币|钱|银票|金票|灵石|信用点|通宝|金铢', tender['money'])):
            return None
        money = re.escape(tender['money'])
        refused = r'(?:' + re.escape(tender['receiver']) + r')?(?:一律|已)?(?:拒收|禁止使用|不接受|不再收取)' + money
        if any(m['money'] == tender['money'] and m['receiver'] in (None, tender['receiver']) for m in deal.refused):
            return None
        if any(re.fullmatch(refused + r'(?:支付|结算)?', clause.strip())
               for term in terms for clause in re.split(r'[，,]', term)):
            return None
        boundary = _limits(deal, limits, [_CONDITION + r'(?:才|方可)?(?:接受|准用|收取)' + money])
        if boundary:
            return {**evidence, 'acceptance': tender[0], 'currency': tender['money'], 'boundary': boundary}
    elif key in ('C00550', 'C00555'):
        boundary = _limits(deal, limits, [_OPEN.pattern])
        fees = [m for pattern in (_FEE, _RATE_FEE, _ZERO_FEE) for m in deal.facts[pattern]]
        if not boundary or len({(m['actor'], m['component']) for m in fees}) != len(fees):
            return None
        if key == 'C00550':
            entry, dispute = deal.one(_ENTRY), deal.one(_DISPUTE)
            if entry and fees and dispute:
                return {**evidence, 'entry': entry[0], 'fees': [m[0] for m in fees],
                        'dispute': dispute[0], 'boundary': boundary}
        else:
            for pattern, dimension in ((_TIME, 'operation'), (_RISK, 'trigger')):
                terms = deal.facts[pattern]
                if len({(m['actor'], m[dimension]) for m in terms}) != len(terms):
                    return None
            costs = [m[0] for m in [*fees, *deal.facts[_TIME], *deal.facts[_RISK]]]
            if costs:
                return {**evidence, 'costs': costs, 'boundary': boundary}
    elif key == 'C00556':
        gate = deal.one(_CLASS, _QUOTA)
        if gate:
            exception = _exception(deal, limits, gate['item'], gate['operation'], '资格')
            if exception:
                return {**evidence, 'qualification': gate[0], 'boundary': exception}
    else:
        swap, delivery = deal.one(_SWAP), deal.one(_DELIVER)
        if swap and delivery and swap['give'] != swap['get']:
            exception = _exception(deal, limits, swap['get'], r'(?:延期|提前|分批)交付', '交割', swap['actor'])
            if exception:
                return {**evidence, 'exchange': swap[0], 'delivery': delivery[0], 'boundary': exception}
    return None


def approved_trade(card: dict, key: str) -> dict | None:
    texts = approved_text(card)
    if not texts or key not in RULES:
        return None
    rule, limits = texts
    if _UNSET.search(rule) or _UNSET.search(limits):
        return None
    deals = _deals(rule)
    proofs = [proof for deal in deals if (proof := _proof(deal, key, rule, limits))]
    if not proofs:
        return None
    if key == 'C00550' and (len({d.method for d in deals}) < 2 or len(proofs) != len(deals)):
        return None
    evidence = proofs[0] if len(proofs) == 1 else {'transactions': proofs}
    return card_proof(card, rule, limits, evidence)
