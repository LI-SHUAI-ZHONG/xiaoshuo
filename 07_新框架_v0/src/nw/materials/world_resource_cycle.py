"""Match resource cycles to conversion, transport and storage evidence on a world card."""
import re
from dataclasses import dataclass

from nw.materials import world_conversion
from nw.materials.world_resources import approved_text, card_proof


RULES = {
    'C00066': '同一资源已批准的生产、储存、消耗与再生，具体能量转化路径及与实际环节的衔接条件',
    'C00479': '同一资源完整循环中已相接的起讫地点、实际流向、运输路线和通行条件',
    'C01763': '同一资源循环的生产来源、储存位置、具体耗损、支取与再补充条件',
}

_NAME = r'[\w·-]{2,24}?'
_PRODUCE = r'(?:产出|生产|制成|制出|出产|产下|提炼出)'
_STORAGE = r'(?:送入|存入|储入|储存在|存储在|储于|存储于|储存于|存放在|存放于|封存于|送往)'
_COMBINED = re.compile(
    rf'(?P<producer>{_NAME}){_PRODUCE}(?:的)?(?P<resource>{_NAME})[，,]?\s*(?:随即|随后|再|直接)?'
    rf'{_STORAGE}(?P<store>{_NAME})')
_PRODUCTION = re.compile(rf'(?P<producer>{_NAME}){_PRODUCE}(?P<resource>{_NAME})')
_STORAGE_ONLY = re.compile(rf'(?P<resource>{_NAME}){_STORAGE}(?P<store>{_NAME})')
_WASTE = r'(?:蒸散|耗损|损耗|蒸发|漏失|损失)'
_AMOUNT = r'(?:[零〇一二两三四五六七八九十百千\d]+(?:[.．点][零一二三四五六七八九\d]+)?(?:成|%|％|升|滴|斤|克|两|枚|份|单位|瓶|桶|格))'
_CONSUMPTION = re.compile(r'消耗|耗用|用尽|烧尽|点灯|燃灯|照明|加热|燃烧|供能|炼制|冶炼|熔炼|'
                          r'铸造|熬制|酿造|蒸煮|冷却|供暖|发电|烧制|转化为|转换为|转为|驱动|灌溉|疗伤')
_NON_CONSUMING = re.compile(r'暂存|陈列|展览|封存|囤积|仅作|展示|仅供参考|记录|讨论|打算')
_ROUTE = re.compile(
    rf'(?P<resource>{_NAME})(?:从|自|由)(?P<start>{_NAME})(?:沿|经由|经过|循|经)'
    rf'(?P<via>{_NAME})(?:运至|送到|送往|运往|运到|流入|流向|流至)(?P<end>{_NAME})')
_GENERIC_NAME = re.compile(
    r'(?:[\d一二三四五六七八九十]+|某种|这个|该|某个|一个|其他|任意|相关|指定|实际|特定|已知|'
    r'对应|当地|本地|批准的?|具体|某|生产|储存|消耗|再生|资源|原料|材料|产物|仓库|设施|工坊|'
    r'地点|位置|机构|区域|人员|条件|权限|票据|用途|使用|工具|渠道|设备|线路|路线|源头|目标|工艺|采购)+')
_UNCERTAIN = re.compile(r'待[定核补]|未[定知]|例如|示例|假设|或许|可能|拟议|暂定|尚未|未确认|备选|取消|废止|仅作|如果采用')
_NEGATED = re.compile(r'并非|不是|未曾|没有|从不|不再|不可|不得|并未|未能|禁止|并不|不能|不许|不予|未必|不含|无需|不从|未从|不生产|不产出|不存|不再生|不领用|不消耗|不运|另一个|另一种')
_GLOBAL_STOP = re.compile(r'(?:本作|本项目|本资源循环|该资源循环|本循环|该循环).{0,10}?(?:弃用|不采用|停用|未采用|尚未采用|取消)(?:本循环|本资源循环)?(?:[。；;]|$)')
_CANCELLATION = re.compile(r'停止|取消|撤销|废止|废弃|停用|不再|永久封存|永久禁用|已经停|已停|从不|并不|不生产|不产出|不存|不再生|不领用|禁止')
_CONDITIONAL_STOP = re.compile(r'^(?:仅当|若|如果|当|一旦)|(?:时|期间|之前|以后|条件下|以前|后)[，,]?(?:将|暂|才|须)?(?:停止|取消|禁止|暂停|不得)')
_EXAMPLE_SECTION = re.compile(r'(?:^|[。；;\n])\s*(?:以下(?:仅为)?|仅作)?(?:备选|示例|假设|反例|举例)(?:方案|情景|设定)?[：:]')
_SPLIT = re.compile(r'[。；;！？!?\r\n]+')
_CONDITION = r'(?P<condition>[\w·-]{2,38}?)'
_BOUND_PREFIX = rf'(?:仅在|只有|仅当|只在|在)?{_CONDITION}(?:后|时|条件下)[，,]?\s*(?:才可|方可|方能|才准|允许|才|可)?'
_PERMIT = rf'(?:仅(?:凭|持)|须(?:凭|持)|凭|持){_CONDITION}(?:方可|才可|可|方能)'
_PLACEHOLDER_CONDITION = re.compile(r'(?:满足|具备|达到|完成|通过|符合|遵守)?(?:相关|所需|相应|全部|指定)?(?:条件|规定|要求|标准|手续|流程|权限)')


@dataclass(frozen=True)
class _Cycle:
    resource: str
    producer: str
    store: str
    consumer: str
    purpose: str
    renewer: str
    feed: str
    evidence: dict[str, str]


def _named(*values: str) -> bool:
    return all(len(value) >= 2 and not _GENERIC_NAME.fullmatch(value)
               and not _UNCERTAIN.search(value) and not _NEGATED.search(value) for value in values)


def _production(lines: list[str]) -> list[tuple[str, str, str, str, str]]:
    stores = [(m, line) for line in lines if (m := _STORAGE_ONLY.fullmatch(line))]
    found = []
    for line in lines:
        if match := _COMBINED.fullmatch(line):
            found.append((match['resource'], match['producer'], match['store'], line, line))
        elif match := _PRODUCTION.fullmatch(line):
            found.extend((match['resource'], match['producer'], store['store'], line, store_line)
                         for store, store_line in stores if store['resource'] == match['resource'])
    return found


def _cycles(lines: list[str]) -> list[_Cycle]:
    cycles = []
    for resource, producer, store, produced, stored in _production(lines):
        if not _named(resource, producer, store) or resource in {producer, store}:
            continue
        item, depot = re.escape(resource), re.escape(store)
        used = re.compile(rf'(?P<consumer>{_NAME})(?:从|自){depot}(?:领用|领取|支取|取出|取用)'
                          rf'{item}[，,]?(?:用于|以供|用以|用来|供|来)?(?P<purpose>{_NAME})')
        renewal = re.compile(rf'(?P<renewer>{_NAME})(?:用|以|凭|借助|利用)(?P<feed>{_NAME})'
                             rf'(?:再生|补产|重新制成|再产出){item}[，,]?\s*(?:并|随后|再)?'
                             rf'(?:送回|回补|补入|回流至|补回|送入|存入){depot}')
        uses = [(m, line) for line in lines if (m := used.fullmatch(line))
                and _named(m['consumer'], m['purpose']) and _CONSUMPTION.search(m['purpose'])
                and not _NON_CONSUMING.search(m['purpose'])]
        renewals = [(m, line) for line in lines if (m := renewal.fullmatch(line))
                    and _named(m['renewer'], m['feed']) and m['feed'] != resource]
        if len(uses) == len(renewals) == 1:
            (use, consumed), (renew, regenerated) = uses[0], renewals[0]
            evidence = dict(production=produced, storage=stored, consumption=consumed, regeneration=regenerated)
            cycles.append(_Cycle(resource, producer, store, use['consumer'], use['purpose'],
                                 renew['renewer'], renew['feed'], evidence))
    return cycles


def _cancelled(cycle: _Cycle, lines: list[str]) -> bool:
    stages = ((cycle.producer, _PRODUCE), (cycle.store, _STORAGE + '|封存|支取|储存'),
              (cycle.consumer, '消耗|领用|领取|取用|支取'), (cycle.renewer, '再生|回补|生产'))
    for line in lines:
        if (cycle.resource not in line or not _CANCELLATION.search(line)
                or _CONDITIONAL_STOP.search(line) or any(term in line for term in ('曾经', '往年', '上月曾', '其他项目'))):
            continue
        if any(actor in line and re.search(verb, line) for actor, verb in stages):
            return True
    return False


def _permits(limits: list[str], action: str) -> str | None:
    pattern = re.compile(rf'(?:{_BOUND_PREFIX})(?:{action})')
    permit = re.compile(rf'(?:{_PERMIT})(?:{action})')
    for line in limits:
        if _UNCERTAIN.search(line) or _NEGATED.search(line):
            continue
        match = pattern.fullmatch(line) or permit.fullmatch(line)
        if match and _named(match['condition']) and not _PLACEHOLDER_CONDITION.fullmatch(match['condition']):
            return line
    return None


def _conversion(cycle: _Cycle, rule: str, limits: str) -> dict[str, str] | None:
    statements = world_conversion._statements(rule)
    paths = world_conversion._paths(statements)
    matches = []
    for path in paths:
        boundary = world_conversion._boundaries(path, world_conversion._statements(limits), paths)
        if not boundary or world_conversion._GLOBAL_INACTIVE.search(rule + '。' + limits):
            continue
        if path.product == cycle.resource and path.method == cycle.producer:
            attached = cycle.evidence['production']
        elif (path.source == cycle.resource and path.method in cycle.purpose
              and path.product in cycle.purpose and re.search(r'转化|转换|制成|转为', cycle.purpose)):
            attached = cycle.evidence['consumption']
        elif path.product == cycle.resource and path.method == cycle.renewer and path.source in cycle.feed:
            attached = cycle.evidence['regeneration']
        elif path.product == cycle.resource:
            item, depot, tool, source = map(re.escape, (cycle.resource, cycle.store, path.method, path.source))
            storage_join = re.compile(rf'{item}(?:存入|送入){depot}前(?:须|必须|需)(?:由|经){tool}'
                                      rf'将{source}(?:转化为|转为){item}')
            attached = next((line for line in statements if storage_join.fullmatch(line)), None)
            if not attached:
                continue
        else:
            continue
        matches.append(dict(path=path.statement, attached_stage=attached, boundary=boundary[0]))
    return matches[0] if len(matches) == 1 else None


def _flow(cycle: _Cycle, lines: list[str], limits: list[str], statements: list[str]) -> dict[str, str] | None:
    linked = {(cycle.producer, cycle.store), (cycle.store, cycle.consumer), (cycle.renewer, cycle.store)}
    candidates = []
    for line in lines:
        route = _ROUTE.fullmatch(line)
        if (not route or route['resource'] != cycle.resource or not _named(route['via'])
                or len({route['via'], route['start'], route['end']}) != 3
                or (route['start'], route['end']) not in linked):
            continue
        if any(route['via'] in line and cycle.resource in line and _CANCELLATION.search(line)
               and not _CONDITIONAL_STOP.search(line) and re.search(r'运送|运输|放运|转运|流动', line)
               for line in statements + limits):
            continue
        via, item = re.escape(route['via']), re.escape(cycle.resource)
        action = rf'(?:沿|循|经由|经){via}(?:运送|运输|放运|转运){item}'
        boundary = _permits(limits, action)
        if boundary:
            candidates.append(dict(route=line, boundary=boundary))
    return candidates[0] if len(candidates) == 1 else None


def _storage(cycle: _Cycle, lines: list[str], limits: list[str]) -> dict[str, str] | None:
    item, depot = re.escape(cycle.resource), re.escape(cycle.store)
    loss = re.compile(rf'{item}(?:储存)?在{depot}(?:每(?:夜|日|月|批|周|年|季)|封存期间|储存期间)'
                      rf'(?:{_WASTE}{_AMOUNT}|(?:密封时)?(?:零损耗|无损耗))')
    losses = [line for line in lines if loss.fullmatch(line)]
    withdraw = _permits(limits, rf'(?:从|自){depot}(?:支取|领用|领取|取用){item}')
    # The return must give a real replenishment event / time or prerequisite.
    restock = (_permits(limits, rf'(?:将)?{item}(?:补入|回补|送回){depot}')
               or (cycle.evidence['regeneration'] if re.search(r'后|时|期|每|残|余|废|回收|熄|退潮', cycle.feed) else ''))
    if len(losses) != 1 or not withdraw or not restock:
        return None
    return dict(loss=losses[0], withdrawal=withdraw, refill=restock, boundary=withdraw)


def approved_resource_cycle(card: dict, key: str) -> dict | None:
    """Keep exact, same-card evidence for each resource-stage dependency."""
    if key not in RULES or not (text := approved_text(card)):
        return None
    rule, limits = text
    # Only assertions before a labelled block of examples provide project facts.
    factual_rule = _EXAMPLE_SECTION.split(rule, maxsplit=1)[0]
    if _GLOBAL_STOP.search(factual_rule) or _GLOBAL_STOP.search(limits):
        return None
    statements = [s.strip() for s in _SPLIT.split(factual_rule) if s.strip()]
    lines = [s for s in statements if not _UNCERTAIN.search(s) and not _NEGATED.search(s)]
    conditions = [s.strip() for s in _SPLIT.split(limits) if s.strip()]
    candidates = []
    for cycle in _cycles(lines):
        if _cancelled(cycle, statements + conditions):
            continue
        if key == 'C00066':
            proof = _conversion(cycle, factual_rule, limits)
        elif key == 'C00479':
            proof = _flow(cycle, lines, conditions, statements)
        else:
            proof = _storage(cycle, lines, conditions)
        if proof:
            candidates.append(dict(resource=cycle.resource, **cycle.evidence, **proof))
    return card_proof(card, rule, limits, candidates[0]) if len(candidates) == 1 else None
