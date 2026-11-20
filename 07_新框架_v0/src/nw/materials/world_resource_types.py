"""Locate the resource, its acquisition or distribution and its bounds on one approved card."""
from collections.abc import Iterator
import re

from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00060': '同一凝聚态资源的具体来源、有条件的储存和实际消耗',
    'C00467': '资源类别、实际生态层级，以及该地点何时能获得这项资源',
    'C00478': '资源类别、具体流向和沿途限制，以及起止地之一的实际可得性',
    'C00527': '实际资源类别、产地、获取渠道、准入和完成获取所需的能力或工具',
    'C00569': '同一资源获取渠道的地区范围、权限、成本和获取风险',
    'C00844': '职业在实际地区取得指定资源的渠道、资格与限制',
}

_NAME = r'[\u3400-\u9fffA-Za-z0-9·]{2,24}?'
_SUBJECT = re.compile(
    rf'^(?:(?:凝聚态资源|凝聚态的资源)(?P<condensed>{_NAME})(?=产自|采自|取自|来自|由|$)'
    rf'|(?P<form>{_NAME})(?:是|属于)凝聚态资源$'
    rf'|(?P<resource>{_NAME})(?:属于|属|是一种|是|作为)(?P<category>{_NAME})(?:资源|材料)$)')
_ORIGIN = r'(?:原产于|产自|采自|取自|来自|产于)'
_WAYS = r'(?:采集|采掘|采收|打捞|开采|购买|交易|兑换|交换|领取|制造|继承|发现|掠夺)'
_UNSET = re.compile(r'待定|待补|待核|待确认|未确定|未明确|暂定|例如|举例|示例|假设|计划改为|也许|或许|可能作为|拟作|占位|[<>〈〉]|某种|某个|某地|某处|某职业|某资源|另行确定')
_UNKNOWN = re.compile(r'(?:符合|具备|满足|达到|持有|取得|持|该|本|某|此|对应|指定|相关|任意|合适|必要|正常|具体|实际|特定|特殊|一种|若干|适用|相应|其他|已有|已设|足够|一些|某些|普通|一般|有效|独有|其他的|的)*'
                      r'(?:资源|产地|来源|地区|地点|地方|类型|分类|层级|系统|权限|凭证|资格|条件|要求|操作|方式|能力|工具|容器|地点|设备|通道|物品|道具|材料|费用|代价|风险|部门|渠道|仓库|储存点|位置|职业|范围|时期|数量|情况|东西)+')
_VAGUE = re.compile(r'不少|极少|极高|很多|不菲|适量|大量|少量|若干|合适|未知|一个|空白|视情况而定')
_NEGATED = re.compile(r'并非|不是|不属|取消|作废|暂不|不再|不作为|仅供参考|假想|未获准')
_ACT = rf'(?:{_WAYS}|储存|存放|储备|保存|消耗|耗用|使用|运输|取得|获取)'


def _specific(value: str) -> bool:
    return len(value) >= 2 and not (_UNKNOWN.fullmatch(value) or _VAGUE.fullmatch(value) or _UNSET.search(value) or _NEGATED.search(value))


def _match(parts: list[str], expression: str, resource: str) -> re.Match | None:
    pattern = re.compile(expression.replace('@', re.escape(resource)))
    matches = []
    for part in parts:
        match = pattern.fullmatch(part)
        if not match and part.startswith((resource, '该资源', '这种资源', '这项资源')):
            scoped = re.sub(r'^(?:' + re.escape(resource) + '|该资源|这种资源|这项资源)', '', part, count=1)
            match = pattern.fullmatch(scoped)
        if match and all(_specific(text) for text in match.groupdict().values() if text):
            matches.append(match)
    return matches[0] if len(matches) == 1 else None


def _bounds(limits: str, resource: str, key: str) -> str | None:
    name = re.escape(resource)
    action = _ACT if key in {'C00060', 'C00478'} else rf'(?:{_WAYS}|取得|获取)'
    for clause in re.split(r'[，,。；;！？!?\n]', limits):
        clause = clause.strip()
        if not clause or _UNSET.search(clause) or _NEGATED.search(clause):
            continue
        # The named item must be the subject or direct object of the limited resource operation.
        for expression in (
            rf'(?:只有|仅限|仅|只允许|只准)(?P<condition>{_NAME})(?:者)?(?:才可|方可|可以|可|才能|方能){action}{name}',
            rf'(?P<condition>{_NAME})(?:时|后|期间|者)(?:才可|方可|不得|禁止|不能|须停止){action}{name}',
            rf'{name}(?:仅在|只在|仅限)(?P<condition>{_NAME})(?:时|后|者)?(?:才可|方可|可以|可)?{action}',
        ):
            if match := re.fullmatch(expression, clause):
                if _specific(match['condition']):
                    return clause
    return None


def _proof(key: str, resource: str, category: str, condensed: bool,
           first: str, parts: list[str]) -> dict | None:
    def find(expression: str) -> re.Match | None:
        return _match(parts, expression, resource)

    origin = find(rf'(?:@)?{_ORIGIN}(?P<origin>{_NAME})')
    if key == 'C00060' and condensed and origin:
        store = rf'(?:储存在|储存于|存入|存于|封存于)(?P<store>{_NAME})'
        storage = find(rf'(?P<condition>{_NAME})(?:后|时)(?:将|把)@' + store)
        if not storage:
            processing = r'(?:蜡封|封蜡|冷却|干燥|脱水|净化|密封|装瓶|封罐|验标|验收|过滤|称重|降温|结晶)'
            storage = find(rf'(?:@)?(?P<condition>{processing}[\u3400-\u9fff]{{0,6}})(?:后|时)' + store)
        spent = find(rf'(?P<occasion>{_NAME})(?:时|后)(?:每次|每炉|每批)?(?:须|需)?(?:耗用|消耗|耗去)'
                     rf'(?:[零一二两三四五六七八九十百千\d]+(?:枚|份|瓶|袋|块|克|单位|升|斤))?@')
        if storage and spent:
            return {'resource': resource, 'identity': first, 'origin': origin[0],
                    'storage': storage[0], 'consumption': spent[0]}
    if key == 'C00467' and category:
        ecology = find(rf'(?:@)?{_ORIGIN}(?P<ecosystem>{_NAME})的(?P<layer>{_NAME}层)')
        harvest = find(rf'(?:仅|只)在(?P<location>{_NAME})(?P<condition>退潮|涨潮|解冻|封冻|雨季|枯水期|融雪|开花|汛期)'
                       rf'(?:后|时|期间)?(?:才可|才能|可以|可){_WAYS}@')
        if not harvest:
            harvest = find(rf'(?:仅|只)在(?P<location>{_NAME})(?:待|且当)(?P<condition>{_NAME})'
                           rf'(?:时|后)(?:才可|才能|可以|可){_WAYS}@')
        if ecology and harvest:
            return {'resource': resource, 'type': first, 'ecology': ecology[0], 'region_condition': harvest[0]}
    if key == 'C00478' and category:
        route = find(rf'(?:@)?(?:从|由)(?P<start>{_NAME})(?:沿|经由|经)(?P<channel>{_NAME})'
                     rf'(?:运往|运至|流向|流入|送往|输往)(?P<end>{_NAME})')
        if route and route['start'] != route['end']:
            place = '(?:' + '|'.join(re.escape(route[n]) for n in ('start', 'end', 'channel')) + ')'
            effect = find(rf'(?P<obstacle>{_NAME})(?:时|后|期间){place}(?:无法|难以|才可|可)(?:取得|获得|采集|补充)@')
            if effect and any(route[site] in effect['obstacle'] for site in ('start', 'end', 'channel')):
                return {'resource': resource, 'type': first, 'route': route[0], 'local_availability': effect[0]}
    if key == 'C00527' and category and origin:
        access = find(rf'(?:凭|持)(?P<permit>{_NAME})(?:者)?(?:才可|方可|须|需)(?:用|以|借助)(?P<tool>{_NAME}){_WAYS}@')
        if access:
            return {'resource': resource, 'type': first, 'origin': origin[0], 'access': access[0]}
    if key == 'C00569':
        channel = find(rf'在(?P<region>{_NAME})(?:通过|经由)(?P<way>{_WAYS})(?:取得|获得)@')
        if channel:
            way = re.escape(channel['way'])
            permit = find(rf'{way}@(?:须持|须凭|需出示)(?P<permission>{_NAME})')
            cost = find(rf'每次{way}(?:须|需)?(?:耗用|消耗|支付|缴纳)(?P<cost>{_NAME})')
            risk = find(rf'{way}(?:时|中|过程)(?P<trigger>{_NAME})(?:可能|会|有)(?P<risk>{_NAME})(?:的风险)?')
            if permit and cost and risk and re.search(r'风险|危险|倾覆|损坏|受伤|断裂|流失|罚没|破碎|被困|沉没|损失|枯竭|耗尽', risk[0]):
                return {'resource': resource, 'identity': first, 'channel': channel[0],
                        'permission': permit[0], 'cost': cost[0], 'risk': risk[0]}
    if key == 'C00844':
        access = find(rf'(?:仅限|只有)(?P<occupation>{_NAME})(?:在)(?P<region>{_NAME})'
                      rf'(?:凭|持)(?P<permit>{_NAME})(?:才可|方可)(?P<way>{_WAYS})@')
        if access and (access['occupation'].startswith('职业为') or re.search(r'(?:工|匠|师|员|吏|夫|贩|商|卫|士|捕头|掌柜|药农|渔民|猎人|采药人)$', access['occupation'])):
            return {'resource': resource, 'identity': first, 'occupational_access': access[0]}
    return None


def _resource_blocks(rule: str) -> Iterator[list[str]]:
    """Continue a paragraph across full stops only while its resource remains explicit."""
    block = []
    resource = ''
    for sentence in re.split(r'[。！？!?\r\n]', rule):
        clauses = [part.strip() for part in re.split(r'[，,；;]', sentence.strip()) if part.strip()]
        if not clauses:
            continue
        first = clauses[0]
        if subject := _SUBJECT.match(first):
            if block:
                yield block
            resource = subject['resource'] or subject['form'] or subject['condensed']
            block = clauses
        elif block and (first.startswith((resource, '该资源', '这种资源', '这项资源')) or first.endswith(resource)):
            block.extend(clauses)
        elif block:
            yield block
            block = []
    if block:
        yield block


def approved_resource_type(card: dict, key: str) -> dict | None:
    """Read a cohesive resource rule and its explicit applicability on this card."""
    text = approved_text(card)
    if key not in RULES or not text:
        return None
    rule, limits = text
    if _UNSET.search(rule) or _NEGATED.search(rule) or _NEGATED.search(limits):
        return None
    candidates = []
    for clauses in _resource_blocks(rule):
        if not (subject := _SUBJECT.match(clauses[0])):
            continue
        resource = subject['resource'] or subject['form'] or subject['condensed']
        category = subject['category'] or ''
        if not _specific(resource) or (category and not _specific(category)):
            continue
        parts = clauses[1:]
        if clauses[0][subject.end():]:
            parts = [clauses[0][subject.end():], *parts]
        if any(_SUBJECT.match(part) or re.search(r'另有|另一(?:条|种|项)|至于|改述|的(?:保管|流通|取得)规定', part) for part in parts):
            continue
        boundary = _bounds(limits, resource, key)
        if not boundary:
            continue
        evidence = _proof(key, resource, category, bool(subject['form'] or subject['condensed']), clauses[0], parts)
        if evidence:
            candidates.append({**evidence, 'boundary': boundary})
    if len(candidates) != 1:
        return None
    return card_proof(card, rule, limits, candidates[0])
