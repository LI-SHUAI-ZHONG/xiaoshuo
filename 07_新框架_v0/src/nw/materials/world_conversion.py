"""Recognize confirmed energy paths, rate definitions and balances on one world card."""
from dataclasses import dataclass
from fractions import Fraction
import re
import unicodedata


POLICY = 'world-conversion-prerequisites-v1'
RULES = {
    'C00050': '游离态能量的环境来源、摄取或提取方式、使用条件及实际终点状态',
    'C00058': '凝聚态能量对象、具体转化方式、触发或禁限及实际终点产物',
    'C00061': '固化态能量对象、启动条件、中间过程、实际产物及持有限制',
    'C00064': '同一具体路径的适用条件、投入、有效产出、损耗及作者已定义的计量口径',
    'C00106': '具体转化路径内同一计量口径的投入、有效产出及余能实际去向',
    'C00409': '受守恒约束的具体转化及同批投入、产出和转移、回收或散失去向',
}
_START_FORMS = {'C00050': '游离态', 'C00058': '凝聚态', 'C00061': '固化态'}
_FORM = r'游离态|凝聚态|固化态'
_SENTENCE = re.compile(r'[^。；;！？!?\r\n]+')
_UNCONFIRMED = re.compile(
    r'待定|未定|待核|待补|待确认|尚未|未确定|未确认|暂定|拟采用|或许|可能|假设|例如|示例|'
    r'反例|备选|拟议|仅考虑|旧方案|废止|作废|已取消|<填写')
_INACTIVE = re.compile(r'不再(?:采用|使用)|不采用|未采用|不(?:能|可|会|得)(?:转化|转为|转换|产生)')
_GLOBAL_INACTIVE = re.compile(
    r'(?:全书|本作|本项目|所有阶段|本转化|该转化|本路径|此路径|该路径)[^，,]{0,18}'
    r'(?:不再(?:采用|使用)|不采用|未采用|取消)')
_GENERIC = re.compile(
    r'(?:任何|某种|其他|相关|规定|指定|任意|具体|固定|该|本|对应|正常|特殊|实际|适当|适用|另行|'
    r'有效|目标|新|已知|合格|满足|具备|符合|达到|完成|使用|采用|进行|发生|遵守|调用|的|在|之|'
    r'对象|起点|终点|状态|形态|能量|物质|介质|媒介|东西|产物|结果|方法|设备|装置|'
    r'路径|工序|操作|手段|要求|条件|规则|标准|流程|处理|转化|转换|时候|时|下|内|后|前|方可|可)+')
_DISABLED_PATH = re.compile(
    r'永久(?:停用|封停|封存|禁止)|(?:不得|禁止|不允许|不可)在(?:本项目|本作|全书)?(?:任何|所有)[^，,]{0,12}'
    r'(?:使用|操作|启动|启用|摄取|转化|转换)|(?:任何情况下|所有条件下)(?:不得|不允许|禁止|不可)'
    r'(?:使用|操作|启动|启用|摄取|转化|转换)')
_NON_OBJECT = re.compile(r'散布在|散落在|记录|测量|观察|出现在|存在于|存放于|但是|另一路|另一种')
_REJECTED_SUBJECT = re.compile(r'并非|不是|不属于|未使用|不使用|禁止使用|不可使用|弃用|不用|无关|而非')
_ENVIRONMENT = re.compile(r'(?:(?:来自|取自|采自|源自)(?P<origin>.+?)的|(?P<site>.+?)(?:中|内|里|底|侧)(?:的)?)$')
_EXTRACTION = re.compile(r'摄取|提取|汲取|吸收|抽取|吸入|采集|采收|萃取|收集|过滤|筛滤')
_INTERMEDIATE = re.compile(r'熔解|溶解|冷凝|分解|加热|研磨|粉碎|剥离|分离|释放|析出|蒸发|萃取|加压|冷却|压制|提炼')
_STARTUP = re.compile(r'才可|方可|才能|启动|点火|激活|允许(?:转化|熔解)')
_HOLDING_BOUNDARY = re.compile(
    r'(?:不得|不可|禁止|方可|才可)(?:继续)?持有|(?:仅限|只准|只许).{1,16}持有|持有.{0,10}(?:须|限于|期限|上限)')
_SUBSTANTIVE = r'[^，,：:。；;！？!?\r\n]{1,46}?'
_PATH = re.compile(
    r'^(?P<subject>(?P<environment>[^，,：:]{0,36}?)(?P<form>' + _FORM + r')(?:的)?(?P<source>' + _SUBSTANTIVE + r'))'
    r'\s*(?:[，,]\s*)?(?:经由|经过|通过|借助|使用|利用|以|用|经)\s*(?P<mechanism>' + _SUBSTANTIVE + r')'
    r'\s*(?:[，,]\s*)?(?:方可|方能|才能|可|将)?(?:转化为|转换为|转换成|转成|转为|化作|化为|变成|制成)'
    r'\s*(?P<product>[^，,]{1,46})$')
_LABEL = re.compile(r'^([^，,：:]{2,22}(?:转化路径|路径|转化法|转化))\s*[：:]\s*')
_TRIGGER = re.compile(r'^\s*(?:仅(?:当|在)|只有|若|在)?\s*(?P<detail>[^，,]{3,36}?)(?:条件下|时|后)\s*[，,]\s*')
_METHOD_CONDITION = re.compile(r'在[^，,]{1,32}(?:条件下|时|后)(?:摄取|加压|萃取|熔解|冷凝|筛滤)?$')
_METHOD_OPERATION = re.compile(r'(?:摄取|加压|萃取|熔解|冷凝|筛滤|过滤|净化|提炼|处理|压制|加热|冷却)$')
_BOUNDARY = re.compile(
    r'仅(?:当|限于|在|适用于)?|只(?:在|限于|有|适用于)|限于|不可|不得|禁止|必须|须|在.{1,24}(?:时|后)|'
    r'(?:时|后)(?:才|方可|方能|停止|暂停|不再)')
_CONDITIONAL_BOUND = re.compile(
    r'^(?:仅在|只在|只有|仅当|在).{1,40}?(?:时|后|条件下|才(?:可|能)|方(?:可|能))\s*(?P<action>.+)$')
_OPERATION = r'(?:使用|启用|启动|开启|点火|操作|运行|转化|转换|摄取|提取|回收|熔解|熔化|萃取|收集|过滤|加压|持有)'
_BOUND_ACTION = re.compile(_OPERATION)
_UNNAMED_ACTION = re.compile(r'(?:(?:可|能|允许|必须|须|不得|不可|禁止|停止|暂停|才|方)+)?' + _OPERATION)
_PATH_REF = r'(?:本|此|该|同一|这条|这一|这次)(?:次转化|条路径|转化路径|路径|转化|工序)'
_RATE_SCOPE = re.compile(r'^(?:' + _PATH_REF + r')(?:的)?\s*')
_RATE_HEAD = re.compile(r'^(?:转化效率|有效产出比例|转化损耗率|损耗率)\s*(?:=|＝|为|是|以|按|[:：])\s*')
_MEASURE = r'(?:投入(?:能量|量|值)?|总投入(?:能量|量|值)?)'
_YIELD = r'(?:有效产出(?:能量|量|值)?|有效输出(?:能量|量|值)?)'
_LOSS = r'(?:损耗(?:能量|量|值)|散失(?:能量|量|值))'
_RATE_BODY = {
    'yield': re.compile(
        r'(?:' + _YIELD + r'\s*(?:/|／|÷|除以)\s*' + _MEASURE
        + r'|' + _YIELD + r'\s*(?:与|占)\s*' + _MEASURE + r'\s*(?:的)?(?:比值|比例))\s*(?:计|计算|核算)?'),
    'loss': re.compile(
        r'(?:' + _LOSS + r'\s*(?:/|／|÷|除以)\s*' + _MEASURE
        + r'|' + _LOSS + r'\s*(?:与|占)\s*' + _MEASURE + r'\s*(?:的)?(?:比值|比例))\s*(?:计|计算|核算)?'),
}
_PERIOD = re.compile(r'^(?:每次|每批|单次|单批|同批|当批|按一次转化单独核算)[：:，,\s]*')
_OTHER_PERIOD = re.compile(r'每|另一次|上一批|下一批|上批|下批|跨批|此前|曾经')
_QUANTITY = r'(?P<amount>[0-9０-９]+(?:[.．][0-9０-９]+)?)\s*(?P<unit>[A-Za-z\u3400-\u9fff]{1,10}?)'
_INPUT = re.compile(r'(?P<origin>[^，,]{1,30}?)\s*(?:投入|输入)\s*' + _QUANTITY)
_OUTPUT = re.compile(r'(?P<product>[^，,]{0,30}?)\s*(?:有效产出|产出|输出)\s*' + _QUANTITY)
_DISPOSITION = re.compile(
    r'(?:剩余|余下|余能|损耗|散失|未形成产物的)\s*' + _QUANTITY
    + r'\s*(?:(?:由|通过|经由|经)\s*(?P<channel>[^，,]{2,24}?)(?:回收|储存|收集)'
    r'|(?:转移至|转入|转给|散为|散入|散到|进入|存入|储存在|留在|流入|回流至|排入|以热量散至)'
    r'\s*(?P<destination>[^，,]{2,24}))')


@dataclass(frozen=True)
class _Path:
    index: int
    statement: str
    label: str
    form: str
    source: str
    method: str
    product: str
    environment: str
    operation: str
    end_form: str

    @property
    def anchors(self) -> tuple[str, ...]:
        return tuple(value for value in (self.label, self.source, self.method, self.product) if value)


def _confirmed(text: str) -> bool:
    return not (_UNCONFIRMED.search(text) or _INACTIVE.search(text))


def _concrete(value: str) -> bool:
    value = value.strip().strip('“”《》「」')
    return len(value) >= 2 and not _GENERIC.fullmatch(value) and not _NON_OBJECT.search(value)


def _statements(value: str) -> list[str]:
    return [match.group().strip() for match in _SENTENCE.finditer(value) if match.group().strip()]


def _paths(statements: list[str]) -> list[_Path]:
    paths = []
    for index, statement in enumerate(statements):
        if not _confirmed(statement):
            continue
        remainder = statement
        label = ''
        if match := _LABEL.match(remainder):
            label, remainder = match[1], remainder[match.end():]
        if trigger := _TRIGGER.match(remainder):
            if not re.search(_FORM, trigger.group()):
                remainder = remainder[trigger.end():].strip()
        match = _PATH.fullmatch(remainder)
        if not match or _REJECTED_SUBJECT.search(match['subject']):
            continue
        source = match['source'].strip()
        operation = match['mechanism'].strip()
        method = _METHOD_OPERATION.sub('', _METHOD_CONDITION.sub('', operation)).strip()
        result = re.sub(r'^(?:可储存的|可用的|可测的)', '', match['product'].strip())
        end_form = re.match(_FORM, result)
        if end_form and end_form[0] == match['form']:
            continue
        product = result[end_form.end():].removeprefix('的') if end_form else result
        environment = match['environment'].strip()
        if all(_concrete(value) for value in (source, method, product)):
            paths.append(_Path(index, statement, label, match['form'], source, method, product,
                               environment, operation, end_form[0] if end_form else ''))
    return paths


def _boundaries(path: _Path, limits: list[str], paths: list[_Path]) -> list[str]:
    boundaries = []
    for line in limits:
        if _DISABLED_PATH.search(line) and (_RATE_SCOPE.match(line) or any(anchor in line for anchor in path.anchors)):
            return []
        if not _confirmed(line):
            continue
        for clause in re.split(r'[，,]', line):
            marker = _BOUNDARY.search(clause)
            if not marker:
                continue
            detail = clause[marker.end():].strip(' ：:')
            if not _concrete(detail) or not _BOUND_ACTION.search(clause):
                continue
            if condition := _CONDITIONAL_BOUND.match(clause.strip()):
                action = condition['action'].strip()
                if not (_UNNAMED_ACTION.fullmatch(action) or any(anchor in action for anchor in path.anchors)):
                    continue
            anchored = any(anchor in clause for anchor in path.anchors)
            refers_to_only_path = len(paths) == 1 and (
                (path.label and path.label in line) or _RATE_SCOPE.match(clause.strip()))
            if anchored or refers_to_only_path:
                boundaries.append(clause.strip())
    return boundaries


def _path_detail(path: _Path, statement: str) -> str:
    """Remove only a scope phrase that refers to the preceding path."""
    detail = _RATE_SCOPE.sub('', statement, count=1)
    if path.label and detail.startswith(path.label):
        after = detail[len(path.label):]
        if after.startswith(('的', '：', ':', '每次', '每批', '单次', '单批')):
            return after.lstrip('的：: ')
    return detail


def _same_origin(path: _Path, origin: str) -> bool:
    names = {path.source, path.form + path.source, path.environment + path.form + path.source,
             path.environment + path.source}
    if location := _ENVIRONMENT.fullmatch(path.environment):
        site = location['origin'] or location['site']
        names.update(site + suffix for suffix in ('', '内', '中', '里'))
    elif holder := re.fullmatch(r'(.+?)(?:持有|保管|储存)的', path.environment):
        names.add(holder[1])
    return origin in names


def _conservation(path: _Path, statement: str, normalized: str, strict: bool) -> str | None:
    period = _PERIOD.match(normalized)
    if not period:
        return None
    parts = [part.strip() for part in re.split(r'[，,]', normalized[period.end():])]
    if len(parts) < 3:
        return None
    input_text, output_text, *destination_texts = parts
    incoming = _INPUT.fullmatch(input_text)
    output = _OUTPUT.fullmatch(output_text)
    destinations = [_DISPOSITION.fullmatch(part) for part in destination_texts]
    if not (incoming and output and destinations
            and all(match and _concrete(match['destination'] or match['channel']) for match in destinations)):
        return None
    origin = incoming['origin'].removeprefix('由').strip()
    product = output['product'].strip()
    identifies_source = (_same_origin(path, origin) if strict else
                         normalized != statement or path.source in origin or origin in path.environment)
    if (not _concrete(origin) or product != path.product
            or not identifies_source
            or any(_OTHER_PERIOD.search(part) for part in parts)):
        return None
    flows = [incoming, output, *(match for match in destinations if match)]
    units = {unicodedata.normalize('NFKC', match['unit']) for match in flows}
    values = [Fraction(unicodedata.normalize('NFKC', match['amount'])) for match in flows]
    if len(units) != 1 or not all(value > 0 for value in values) or values[0] != sum(values[1:]):
        return None
    return statement


def _measurements(path: _Path, statements: list[str], strict: bool) -> tuple[dict[str, str], str | None]:
    """Read consecutive definitions explicitly belonging to this path."""
    definitions: dict[str, str] = {}
    conservation = None
    for line in statements[path.index + 1:]:
        if not _confirmed(line):
            break
        detail = _path_detail(path, line)
        if head := _RATE_HEAD.match(detail):
            if detail == line:
                break
            is_loss = '损耗率' in head.group()
            kind = 'loss_rate' if is_loss else 'efficiency'
            expression = _RATE_BODY['loss' if is_loss else 'yield']
            if kind in definitions or not expression.fullmatch(detail[head.end():].strip()):
                return {}, None
            definitions[kind] = line
        elif _PERIOD.match(detail):
            if conservation or not (conservation := _conservation(path, line, detail, strict)):
                return {}, None
        else:
            break
    return definitions, conservation


def approved_conversion(card: dict, key: str, *, strict: bool = True) -> dict | None:
    """Return verbatim project evidence for a candidate, or leave it waiting."""
    if (key not in RULES or card.get('kind') != 'world' or card.get('status') != 'approved'
            or not isinstance(card.get('card_id'), str) or not card['card_id'].strip()
            or type(card.get('version')) is not int or card['version'] < 1):
        return None
    body = card.get('body')
    if not isinstance(body, dict):
        return None
    rule, limits = body.get('rule'), body.get('limits')
    if (not isinstance(rule, str) or not isinstance(limits, str)
            or _GLOBAL_INACTIVE.search(rule) or _GLOBAL_INACTIVE.search(limits)):
        return None
    statements = _statements(rule)
    paths = _paths(statements)
    start_form = _START_FORMS.get(key)
    matching = [path for path in paths if not start_form or path.form == start_form]
    if len(matching) != 1:
        return None
    path = matching[0]
    boundaries = _boundaries(path, _statements(limits), paths)
    if not boundaries:
        return None
    evidence = {'path': path.statement, 'boundary': boundaries[0]}
    if key == 'C00050':
        environment = _ENVIRONMENT.fullmatch(path.environment)
        if (not environment or not _concrete(environment['origin'] or environment['site'])
                or not _EXTRACTION.search(path.operation) or not path.end_form):
            return None
        evidence['environment'] = path.environment
    if key == 'C00061':
        startup = next((line for line in boundaries if _STARTUP.search(line)), None)
        holding = next((line for line in boundaries if _HOLDING_BOUNDARY.search(line) and path.source in line), None)
        if not (startup and holding and _INTERMEDIATE.search(path.operation)):
            return None
        evidence.update(startup=startup, holding=holding)
    if key not in _START_FORMS:
        definitions, conservation = _measurements(path, statements, strict)
        if key == 'C00064':
            if not definitions or (len(definitions) != 2 and not conservation):
                return None
            evidence.update(definitions)
        elif not conservation:
            return None
        if conservation:
            evidence['conservation'] = conservation
    ident = card['card_id']
    return {'card_id': ident, 'version': card['version'], 'rule': rule, 'limits': limits,
            'rule_ref': f'approved:{ident}:/body/rule', 'limits_ref': f'approved:{ident}:/body/limits',
            'evidence': evidence}
