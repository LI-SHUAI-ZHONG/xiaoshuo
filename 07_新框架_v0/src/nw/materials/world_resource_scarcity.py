"""Read scarcity claims for one named resource, place and period from an approved card."""
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
import re

from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00483': '同地同期的资源产出、消耗、相符的供需结论及可用替代品的折算条件',
    'C00529': '资源的实际用途类别、地区供需、补充条件、已定稀缺等级和符合 125.8 的分级依据',
    'C00562': '同一资源在具体地区、时期的生产、消耗、再生及已确认的短缺与补充条件',
}
_NAME = r'[\u3400-\u9fffA-Za-z]{2,14}?'
_PERIOD = r'[\u3400-\u9fffA-Za-z0-9]{1,10}?(?:期间|季节|季|时期|期|年|月|旬)'
_SCOPE = (
    re.compile(r'^(?:在)?(?P<area>' + _NAME + r')(?:进入|处于|在)(?P<period>' + _PERIOD + r')(?:时)?[，,]'),
    re.compile(r'^(?P<period>' + _PERIOD + r')[，,](?P<area>' + _NAME + r')的'),
)
_AMOUNT = r'(?P<num>\d{1,12}(?:\.\d{1,6})?)\s*(?P<unit>[\u3400-\u9fffA-Za-z]{1,6})'
_INTERVAL = r'(?P<interval>每(?:日|天|周|旬|月|季|年|批))?'
_IN = re.compile(r'(?P<name>' + _NAME + r')' + _INTERVAL + r'(?P<label>新产|生产|产出|产量|供给|供应)(?:为|量为)?\s*' + _AMOUNT)
_OUT = re.compile(r'(?P<name>' + _NAME + r')?' + _INTERVAL + r'(?P<label>消耗|消费|需求)(?:为|量为)?\s*' + _AMOUNT)
_BALANCES = {'短缺': -1, '不足': -1, '供不应求': -1, '平衡': 0, '供需持平': 0, '盈余': 1, '过剩': 1}
_IMPRECISE = re.compile(r'待定|另议|待核|暂定|未定|待补|待确认|假设|举例|例如|示例|样本|旧案|原方案|'
                        r'作废|废止|撤销|停用|不采用|不再采用|尚未|某种|某地|某时期|某资源|替代品甲|可能|据说|不适用')
_PLACEHOLDERS = {'资源', '某资源', '本资源', '该资源', '替代资源', '当地', '地区', '区域', '本地', '指定地区', '相关区域', '某港', '本期', '某物'}
_GRADE_BASIS = {
    '极端稀缺': r'全书(?:只有|仅有|仅|至多|不超过)[123一二两三](?:位|名|个)持有者',
    '高度稀缺': r'仅由(?:顶层势力|最高层势力)(?P<actor>' + _NAME + r')(?:独占|控制|掌控)',
    '中度稀缺': r'(?:仅可通过|只能通过|须通过)(?P<actor>' + _NAME + r')(?:取得|获得|领取|购买)',
    '轻度稀缺': r'在(?P<actor>' + _NAME + r')流通但(?:须|仅向)[\u3400-\u9fff]{2,18}',
    '自由流通': r'在(?P<actor>' + _NAME + r')(?:可)?自由买卖(?:且|，)?(?:无需许可|不设准入门槛)',
}


@dataclass(frozen=True)
class _Account:
    area: str
    period: str
    resource: str
    kind: str
    unit: str
    interval: str
    net: Decimal
    clauses: list[str]
    statement: str
    boundary: str


def _scoped_statements(rule: str) -> Iterator[tuple[str, re.Match]]:
    """Keep adjacent sentences about the same account together and preserve verbatim evidence."""
    sentences = list(re.finditer(r'[^。；;！？\r\n]+', rule))
    for index, entry in enumerate(sentences):
        text = entry[0].strip()
        scope = next((m for pattern in _SCOPE if (m := pattern.match(text))), None)
        if not scope:
            continue
        detail = re.split(r'[，,]', text[scope.end():], maxsplit=1)[0].strip()
        named = _IN.fullmatch(detail) or re.fullmatch(r'(?P<name>' + _NAME + r')按[\u3400-\u9fff]{1,4}核算', detail)
        if not named:
            continue
        resource = named['name']
        end = entry.end()
        for following in sentences[index + 1:]:
            line = following[0].strip()
            if any(pattern.match(line) for pattern in _SCOPE):
                break
            if not (line.startswith(resource) or line.endswith(resource) or
                    re.match(r'每(?:一|1)?[\u3400-\u9fff]{1,4}' + re.escape(resource), line)):
                break
            end = following.end()
        yield rule[entry.start():end].strip(), scope


def _accounts(rule: str, limits: str) -> list[_Account]:
    records = []
    for text, scope in _scoped_statements(rule):
        clauses = [item.strip() for item in re.split(r'[，,。；;\r\n]+', text[scope.end():]) if item.strip()]
        if len(clauses) < 3:
            continue
        incoming, outgoing = _IN.fullmatch(clauses[0]), _OUT.fullmatch(clauses[1])
        area, period = scope['area'], scope['period']
        if incoming and outgoing:
            name, unit, interval = incoming['name'], incoming['unit'], incoming['interval'] or ''
            if (outgoing['name'] not in (None, name) or outgoing['unit'] != unit
                    or outgoing['interval'] not in (None, interval)):
                continue
            if incoming['label'] in ('供给', '供应') and outgoing['label'] == '需求':
                kind = 'market'
            elif incoming['label'] in ('新产', '生产', '产出', '产量') and outgoing['label'] in ('消费', '消耗'):
                kind = 'new' if incoming['label'] == '新产' else 'production'
            else:
                continue
            net = Decimal(incoming['num']) - Decimal(outgoing['num'])
        else:
            basis = re.fullmatch(r'(?P<name>' + _NAME + r')按(?P<unit>[\u3400-\u9fff]{1,4})核算', clauses[0])
            trend = re.fullmatch(r'产量(?:持续|已)?(高于|低于|等于)同期消耗量', clauses[1])
            if not basis or not trend:
                continue
            name, unit, interval = basis['name'], basis['unit'], ''
            net = Decimal({'高于': 1, '等于': 0, '低于': -1}[trend[1]])
            kind = 'trend'
        if {name, area, period} & _PLACEHOLDERS:
            continue
        for boundary in re.split(r'[。；;！？\r\n]', limits):
            line = boundary.strip()
            # The scope restricts this resource's accounting, not an unrelated activity in the same place.
            subject = re.escape(name) + r'(?:的)?(?:供需|收支|产销|稀缺性|生产与消耗)(?:核算|统计|估算|口径|账)?'
            region = re.escape(area) + r'(?:的)?' + re.escape(period)
            if re.fullmatch(subject + r'(?:仅限于|仅限|仅适用于|仅覆盖|只统计)' + region, line):
                records.append(_Account(area, period, name, kind, unit, interval, net, clauses[2:], text, line))
                break
    return records


def _single(clauses: list[str], pattern: str) -> re.Match | None:
    matches = [m for clause in clauses if (m := re.fullmatch(pattern, clause))]
    return matches[0] if len(matches) == 1 else None


def _replenishment(record: _Account) -> str | None:
    resource = re.escape(record.resource)
    # A source and a real release condition are required for an imported or regenerated supply.
    condition = r'(?P<when>[^，,]{2,16}?(?:开闸|解冻|复航|验收|退潮|复产|开炉|蓄满|收割|发芽|成熟|通行))'
    pattern = (r'(?:仅在|要等|须等|只在)' + condition + r'后(?:才)?(?:能|可)?(?:从|由)'
               + r'(?P<source>' + _NAME + r')(?:补充|补给|调入|再生|再产)' + resource)
    matched = _single(record.clauses, pattern)
    if not matched or matched['source'] in _PLACEHOLDERS or matched['source'] == record.resource:
        return None
    return matched[0]


def _evidence(record: _Account, key: str) -> dict | None:
    name = re.escape(record.resource)
    clauses = record.clauses
    proof = {'account': record.statement, 'boundary': record.boundary}
    if key == 'C00529':
        if record.kind != 'market':
            return None
        category = _single(clauses, name + r'(?:属于|归为|列为)(?P<type>' + _NAME + r')')
        if not category or category['type'] in _PLACEHOLDERS | {record.resource, '类别', '类型', '物品', '其他资源', '某类资源', '同类资源'}:
            return None
        grade = _single(clauses, r'(?:' + name + r')?(?:稀缺等级为|评为|定为)(' + '|'.join(_GRADE_BASIS) + r')')
        refill = _replenishment(record)
        if not grade or not refill:
            return None
        access = _single(clauses, _GRADE_BASIS[grade[1]])
        if not access or access.groupdict().get('actor') in _PLACEHOLDERS:
            return None
        if len(clauses) != 4 or set(clauses) != {category[0], grade[0], access[0], refill}:
            return None
        proof.update(category=category[0], grade=grade[0], access=access[0], replenishment=refill)
        return proof
    if record.kind == 'market':
        return None
    outcome = _single(clauses, r'(?:因此|故|因而)?(?:' + name + r'|当地|本期)?(?:出现|呈|处于|收支)?(' + '|'.join(_BALANCES) + r')')
    if not outcome:
        return None
    substitution = _single(
        clauses, r'每(?:一|1)?' + re.escape(record.unit) + name + r'(?:可用|可由|可换)'
        + r'(?P<quantity>[1-9]\\d{0,6}|[一二两三四五六七八九十])(?P<unit>[袋箱瓶枚块斤升份吨克桶片锭支筐颗件])'
        + r'(?P<other>' + _NAME + r')(?:替代|折抵|代替)')
    if substitution and (substitution['other'] == record.resource or substitution['other'] in _PLACEHOLDERS):
        return None
    refill = _replenishment(record)
    dormant = _single(clauses, r'(?:' + re.escape(record.period) + r'|本期)(?:内)?'
                      + name + r'(?:停止再生|无法再生|不能再生|再生量为零|再生量为0)')
    regenerated = _single(clauses, name + re.escape(record.interval) + r'再生' + _AMOUNT)
    net = record.net
    if regenerated:
        if dormant or record.kind != 'new' or regenerated['unit'] != record.unit:
            return None
        net += Decimal(regenerated['num'])
    elif record.kind == 'new' and not dormant:
        return None
    result = _BALANCES[outcome[1]]
    if result != ((net > 0) - (net < 0)):
        return None
    renewal = dormant or regenerated
    if key == 'C00483' and not substitution:
        return None
    if key == 'C00562' and (result != -1 or not renewal or not refill):
        return None
    proof['balance'] = outcome[0]
    if substitution:
        proof['alternative'] = substitution[0]
    if renewal:
        proof['regeneration'] = renewal[0]
    if refill:
        proof['replenishment'] = refill
    # Do not attach an unrecognized resource or a second claim to the accepted account.
    used = {proof[field] for field in ('balance', 'alternative', 'regeneration', 'replenishment') if field in proof}
    if len(clauses) != len(used) or set(clauses) != used:
        return None
    return proof


def approved_scarcity(card: dict, key: str) -> dict | None:
    texts = approved_text(card)
    if not texts or key not in RULES or any(_IMPRECISE.search(text) for text in texts):
        return None
    rule, limits = texts
    accounts = _accounts(rule, limits)
    scopes = {(account.resource, account.area, account.period, account.kind == 'market') for account in accounts}
    if len(scopes) != len(accounts):
        return None
    matches = [proof for account in accounts if (proof := _evidence(account, key))]
    return card_proof(card, rule, limits, matches[0]) if len(matches) == 1 else None
