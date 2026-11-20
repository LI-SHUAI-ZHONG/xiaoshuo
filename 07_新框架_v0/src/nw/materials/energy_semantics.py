"""Check the project batch, conversion direction and system boundary for three world methods."""
from fractions import Fraction
import re
from unicodedata import normalize

from nw.materials.semantic_application import require

PURITY = 'C00035'
CONSERVATION = {'C00107', 'C00410'}
RULES = {PURITY, *CONSERVATION}

_RATE = r'(?:转化效率|转换效率|转化率|转换率|炼化收率|转化收率|收率|产率)'
_PURITY = r'(?:纯度|纯净度|杂质含量|杂质比例|杂质)'
_BATCH = r'(?:同(?:一)?(?:批|炉|次)|本(?:批|炉|次)|这(?:一)?(?:批|炉)|该(?:批|炉)|逐批|每批|批次)'
_PROCESS = r'(?:试烧|烧炼|炼制|精炼|熔炼|炼化|筛炼|煅烧|提纯|萃取|转换|转化|提炼|加工|结晶|净化|产出|制成)'
_FLOW = r'(?:转移|转入|流出|流入|回收|收回|去向|耗散|散入|转化|移入|汇入|传入|传到|分流|余热|损耗|释放|吸收|流向|改道|排入|输入|输出|补入|注入)'
_TOTAL = r'(?:总能量|总灵能|总热量|总储量|能量总量|系统总量|系统能量|系统总和|总量|总账|收支|总数|合计)'
_BOUNDARY = r'(?:封闭|密闭|闭合|开放系统|为界|边界|界内|不与外界交换|与外界隔绝|无外部输入|无外来输入)'
_CLOSED = re.compile(r'封闭|密闭|闭合|不与外界交换|与外界隔绝|无外部输入|无外来输入')
_OPEN = re.compile(r'开放系统|系统(?:是|为|保持)?开放|允许与外界交换|与外界有交换|接收外部(?:热|能量|输入)')
_LIMIT = re.compile(r'只限|仅限|限于|仅|只有|只在|只准|只对|须|必须|只许|只算|只计|不得|禁止|不能|方可|适用于|不适用|超出|除外|以内|才可|才能|为界')
_UNCERTAIN = re.compile(r'待核|待确认|未定|未证实|未知|传闻|假设|仅为示例|未能证明')
_DENY = re.compile(r'(?:没有|并未|不能|不会|不得|不可|不许|禁止|防止|避免|拒绝|否认|否决|并非|未曾|未能|尚未)[^，,。；;]{0,8}$')
_OTHER_BATCH = re.compile(r'(?:另一(?:批|炉)|别(?:批|炉)|不同(?:批|炉)|跨(?:批|炉))')
# A field saying where this rule applies is itself a scope. A limit on an unrelated activity is not.
_GEOGRAPHIC = re.compile(r'(?:仅|只)(?:在|限于|限|对)[^，,。；;]{1,14}(?:范围内)?(?:适用|有效|生效)(?:[，,。；;]|$)')
_UNITS = r'[A-Za-z\u3400-\u9fff·/]{1,12}'
_NUM = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|[零〇一二两三四五六七八九十百千万]+)'
_TO = r'(?:升至|升到|升为|增至|增到|增为|降至|降到|降为|减至|减到|减为|变成|变为|变到|增加至|增加到|增长至|增长到|上升至|上升到|跌至|变作|变至|涨到|涨至|成为|→|->|至|到)'
_TOTAL_PAIR = re.compile(_TOTAL + r'[^，,。；;\d]{0,12}?(?P<a>' + _NUM + r')\s*(?P<u>[A-Za-z\u3400-\u9fff·/]{0,12}?)\s*'
                         + _TO + r'\s*(?P<b>' + _NUM + r')\s*(?P<v>' + _UNITS + r')?')
_READING = re.compile(_TOTAL + r'(?:为|是|共|达|计|共计|等于|仅有|只剩|记作|录得|测得|仍为|=|：|:)?\s*'
                      + r'(?P<amount>' + _NUM + r')\s*(?P<unit>' + _UNITS + r')')
_PRE = r'此前|起初|原先|初始|开始时|原有|转移前|转化前|结算前|启动前|之前|起始'
_POST = r'随后|此后|最终|结算后|转移后|转化后|结束时|之后|启动后|期末|现在'
_PHASE_QUANTITY = re.compile(r'(' + _PRE + '|' + _POST + r')(?:的)?(?:能量|热量|总量|系统能量|总能量)?'
                             r'(?:为|共|是|还有|有|变为|为止|降为|升为|余下)?\s*(' + _NUM + r')\s*(' + _UNITS + ')')
_TOTAL_CLAIM = re.compile(_TOTAL + r'[^，,。；;]{0,12}?(?:凭空|无中生有|无故|无来源)(?:增加|产生|增生|消失|减少|翻倍|倍增)'
                          + r'|(?:凭空|无故)(?:增加|增生|翻倍|减少|抹去)[^，,。；;]{0,8}' + _TOTAL)
_LOCAL = re.compile(r'(?:局部|其中一|单个|单舱|子系统|单缸|内仓|蓄热壁内|仅计[^，,。]{1,8})[^，,。；;]{0,8}$')


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'[。；;！？!?\r\n]+', normalize('NFKC', text)) if s.strip()]


def _affirmed(pattern, text: str) -> bool:
    return any(not _DENY.search(text[:m.start()]) for m in re.finditer(pattern, text))


def _identified(rule: str, text: str) -> bool:
    """Look for the same project object, suppressing generic method vocabulary before comparing."""
    generic = '|'.join((_RATE, _PURITY, _BATCH, _PROCESS, _FLOW, _TOTAL, _BOUNDARY,
                        r'世界|规则|原料|成品|产物|系统|条件|影响|决定|根据|必须|适用|不得|只有|才能|记录|账目|核对|能量|测量|变化|实际'))
    def phrases(value: str) -> set[str]:
        return {word[i:i+2] for word in re.findall(r'[\u3400-\u9fff]{2,}', re.sub(generic, ' ', value))
                for i in range(len(word)-1)}
    return bool(phrases(rule) & phrases(text))


def _batch_link(text: str) -> bool:
    if not (re.search(_RATE, text) and re.search(_PURITY, text)):
        return False
    cause = r'(?:决定|影响|改变|导致|使得|带来|提高了|降低了)'
    depend = r'(?:取决于|随(?:着)?|由|受制于|受)'
    # Compare efficiency to purity in the direction defined by the static condition.
    if re.search(_PURITY + r'.{0,10}?' + cause + r'.{0,12}?' + _RATE, text) or re.search(
            _RATE + r'.{0,8}?' + depend + r'.{0,10}?' + _PURITY, text):
        return False
    if re.search(r'不再影响|不影响|没有关系|无关|毫不相关|不能据此|与[^，,。]{0,12}无关', text):
        return False
    return bool(re.search(_RATE + r'[^。；;]{0,30}?(?:' + cause + r'|使|越|愈)[^。；;]{0,26}?' + _PURITY, text)
                or re.search(_PURITY + r'[^。；;]{0,18}?' + depend + r'[^。；;]{0,16}?' + _RATE, text))


def _scope(key: str, rule: str, limit: str) -> bool:
    if not _LIMIT.search(limit) or _UNCERTAIN.search(limit):
        return False
    if _GEOGRAPHIC.search(limit):
        return True
    if key == PURITY:
        if _affirmed(_OTHER_BATCH, limit):
            return bool(re.search(r'不同(?:批|炉)(?:次)?(?:不得|不能|严禁)(?:混|并|合|代|比)', limit))
        return bool((_identified(rule, limit) or re.search(_BATCH, limit))
                    and re.search('|'.join((_RATE, _PURITY, _BATCH, _PROCESS, r'投料|原料|样品|成品')), limit))
    return bool((_identified(rule, limit) or re.search(_BOUNDARY + '|' + _TOTAL, limit))
                and re.search('|'.join((_BOUNDARY, _TOTAL, _FLOW, r'核算|计入|入账|交换')), limit))


def _number(value: str) -> Fraction:
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value):
        return Fraction(value)
    digits = dict(zip('零〇一二两三四五六七八九', (0,0,1,2,2,3,4,5,6,7,8,9)))
    if all(v in digits for v in value):
        return Fraction(int(''.join(str(digits[v]) for v in value)))
    large = block = last = 0
    for token in value:
        if token in digits:
            last = digits[token]
        elif token == '万':
            large += (block + last or 1) * 10000
            block = last = 0
        else:
            block += (last or 1) * {'十': 10, '百': 100, '千': 1000}[token]
            last = 0
    return Fraction(large + block + last)


def _unit(text: str | None) -> str:
    return re.split(r'但|而|却|且|仍|则|保持|不变|无需|并|同时|如果|来自|通过|流入|流出|差额|以后|登记|入账|记入|计入', text or '', maxsplit=1)[0]


def _quantity(amount: str, unit: str) -> tuple[Fraction, str]:
    # Only ordinary standardized energy units are interchangeable without a project conversion rule.
    if unit in ('J', '焦', '焦耳', 'kJ', '千焦', '千焦耳'):
        return _number(amount) * (1000 if unit in ('kJ', '千焦', '千焦耳') else 1), 'J'
    return _number(amount), unit


def _external_flows(text: str) -> dict[str, Fraction]:
    ledger = {}
    for part in re.split(r'[，,。；;]', text):
        if not re.search(r'外部|外界|外来|闸外|炉外|窑外|边界外|界外|境外|从[^，,]{1,10}补|由[^，,]{1,10}输', part):
            continue
        for m in re.finditer(r'(输入|注入|流入|补入|汇入|送入|输出|转出|流出|排出)(?:的|了)?\s*('
                             + _NUM + r')\s*(' + _UNITS + ')', part):
            if _DENY.search(part[:m.start()]):
                continue
            amount, unit = _quantity(m[2], _unit(m[3]))
            sign = -1 if m[1] in ('输出', '转出', '流出', '排出') else 1
            ledger[unit] = ledger.get(unit, 0) + sign * amount
    return ledger


def _unbalanced(text: str, exchange: dict | None = None) -> bool:
    def difference(first: tuple, last: tuple) -> bool:
        return first[1] != last[1] or last[0] - first[0] != (exchange or {}).get(first[1], 0)

    for pair in _TOTAL_PAIR.finditer(text):
        if _LOCAL.search(text[:pair.start()]) or _DENY.search(text[:pair.start()]):
            continue
        if re.match(r'[A-Za-z\u3400-\u9fff/]{0,8}?[”」"]?的?(?:假账|虚账|错误读数|虚假记录|说法被驳回|说法不成立)',
                    text[pair.end('b'):]):
            continue
        unit_a, unit_b = _unit(pair['u']), _unit(pair['v'])
        if difference(_quantity(pair['a'], unit_a or unit_b), _quantity(pair['b'], unit_b or unit_a)):
            return True
    earlier = {}
    for part in re.split(r'[，,；;。]', text):
        for item in _READING.finditer(part):
            lead = part[:item.start()]
            if _LOCAL.search(lead) or _DENY.search(lead):
                continue
            amount, unit = _quantity(item['amount'], _unit(item['unit']))
            if re.search(_PRE, lead):
                earlier[unit] = (amount, unit)
            if re.search(_POST, lead) and earlier and (unit not in earlier or difference(earlier[unit], (amount, unit))):
                return True
    # Some project cards identify the whole system once, then omit "总量" from its ending observation.
    phase_start = None
    for part in re.split(r'[，,；;。]', text):
        for measured in _PHASE_QUANTITY.finditer(part):
            lead = part[:measured.start()]
            if _LOCAL.search(lead) or _DENY.search(lead):
                continue
            observed = _quantity(measured[2], _unit(measured[3]))
            if re.fullmatch(_PRE, measured[1]) and re.search(r'(?:系统|总量|总能量|整个水轮|同一边界)(?:内|中|的)?$', lead):
                phase_start = observed
            if re.fullmatch(_POST, measured[1]) and phase_start and difference(phase_start, observed):
                return True
    return False


def _purity_conflict(text: str) -> bool:
    if _affirmed(_OTHER_BATCH.pattern + r'.{0,12}(?:代替|代入|充当|冒充|当作|作为).{0,15}(?:本批|本炉|该批|本次)', text):
        return True
    if not (re.search(_RATE, text) and re.search(_PURITY, text)):
        return False
    return bool(re.search(_PURITY + r'.{0,12}(?:决定|导致|支配).{0,12}' + _RATE, text)
                or re.search(_RATE + r'.{0,10}(?:取决于|受制于).{0,14}' + _PURITY, text)
                or re.search(_RATE + r'.{0,6}(?:就是|等于|一律视为|等同于).{0,4}' + _PURITY, text)
                or re.search(r'不再影响|不影响|毫不相关|与[^，,。]{0,14}无关', text))


def _closed_conflict(text: str) -> bool:
    for claim in _TOTAL_CLAIM.finditer(text):
        before = re.split(r'凭空|无中生有|无故|无来源', claim[0], maxsplit=1)[0]
        if not _DENY.search(text[:claim.start()]) and not _DENY.search(before):
            return True
    return _unbalanced(text)


def _fixed_values(key: str, text: str) -> set[tuple[str, Fraction, str]]:
    """Only a declared constant on this batch or boundary fixes a later value."""
    metric = _TOTAL if key in CONSERVATION else _RATE + '|' + _PURITY
    find = r'(' + metric + r')(?:恒为|始终为|恒定为|固定为|固定在|锁定为|测得为|实测为)\s*(' + _NUM + r')\s*(%|' + _UNITS + ')'
    return {(m[1], _number(m[2]), _unit(m[3])) for m in re.finditer(find, text)}


def _changed_value(key: str, evidence: str, text: str) -> bool:
    for metric, fixed, unit in _fixed_values(key, evidence):
        names = _TOTAL if key in CONSERVATION else _RATE if re.fullmatch(_RATE, metric) else re.escape(metric)
        for m in re.finditer(r'(?:' + names + r')(?:为|是|共|计|变成|变为|实为|固定为|达到|测得为|实测为|=)?\s*('
                             + _NUM + r')\s*' + re.escape(unit), text):
            if _number(m[1]) != fixed and not _LOCAL.search(text[:m.start()]) and not _DENY.search(text[:m.start()]):
                return True
    return False


def _trend(text: str) -> int:
    m = re.search(_RATE + r'(?:越|愈|提高则|下降则)([高低大小增减])?[^。；;]{0,20}?(' + _PURITY
                  + r')(?:也|就|相应)?(?:越|愈|升|降)([高低多少大小])', text)
    if not m or not m[1]:
        return 0
    first = 1 if m[1] in '高大增' else -1
    second = 1 if m[3] in '高多大' else -1
    return first * second * (-1 if '杂质' in m[2] else 1)


def eligible(key: str, rule: str, limit: str, *, full_rule: str | None = None, full_limits: str | None = None) -> bool:
    if key not in RULES or not all(isinstance(s, str) and s for s in (rule, limit)):
        return False
    rule, limit = normalize('NFKC', rule), normalize('NFKC', limit)
    if _UNCERTAIN.search(rule) or not _scope(key, rule, limit):
        return False
    if key == PURITY:
        if not (re.search(_BATCH, rule + limit) and re.search(_PROCESS, rule) and _batch_link(rule)):
            return False
        if _affirmed(_OTHER_BATCH, rule):
            return False
    elif not (re.search(_BOUNDARY, rule + limit) and re.search(r'守恒|不增不减|总量不变|总量不增|收支平衡', rule)
              and re.search(_FLOW, rule) and re.search(_TOTAL + '|' + _BOUNDARY, rule)):
        return False
    full = '。'.join((full_rule or rule, full_limits or limit))
    return not _contradiction(key, rule, limit, full, adopted=True)


def _contradiction(key: str, rule: str, limit: str, text: str, *, adopted: bool) -> bool:
    explicit_open = bool(_OPEN.search(rule + limit))
    closed = bool(_CLOSED.search(rule + limit)) and not explicit_open
    scoped = []
    for sentence in _sentences(text):
        if re.search(r'另(?:一处|一座|一套|一个|一口|一间|一路|一批|一个开放系统|外一批|一台)', sentence) and not _identified(rule, sentence):
            continue
        related = (_identified(rule, sentence) or sentence in (rule, limit)
                   or re.search(r'(?:本|此|该|上述|同一)(?:系统|边界|批|炉|水轮|路径|窑室)|封闭系统(?:内|的)?(?:总|转移前|起始|初始)', sentence))
        if related or adopted:
            scoped.append(sentence)
            if key == PURITY and (_purity_conflict(sentence) or _trend(rule) * _trend(sentence) < 0):
                return True
            if key in CONSERVATION:
                if closed and _closed_conflict(sentence):
                    return True
                if explicit_open and _TOTAL_PAIR.search(sentence):
                    flows = _external_flows(sentence) or _external_flows(rule + '。' + limit) or _external_flows(text)
                    if _unbalanced(sentence, flows):
                        return True
            if _changed_value(key, rule + '。' + limit, sentence):
                return True
    current = '。'.join(scoped)
    if explicit_open and not _TOTAL_PAIR.search(current):
        # Beginning and ending observations may be in separate sentences.
        flows = _external_flows(current) or _external_flows(rule + '。' + limit)
        return _unbalanced(current, flows)
    return closed and _unbalanced(current)


def _pinned_constants(row: dict) -> str:
    rule, limit = row['excerpts']
    statements = [rule, limit]
    for item in row.get('evidence', []):
        if not item['ref'].endswith(('/body/rule', '/body/limits')) or not isinstance(item['value'], str):
            continue
        for statement in _sentences(item['value']):
            if _identified(rule, statement) or re.search(r'(?:本|此|该|上述)(?:系统|批|炉|水轮|窑室)', statement):
                statements.append(statement)
    return '。'.join(statements)


def check_conflict(row: dict, text: str, *, stage: str = '') -> None:
    key = row['key']
    if key not in RULES or not isinstance(text, str):
        return
    excerpts = row.get('excerpts', [])
    if len(excerpts) != 2:
        return
    require(not _contradiction(key, *excerpts, text, adopted=False), '当前设计与同批转化或同一系统总账的冻结依据冲突')
    if _identified(excerpts[0], text) or re.search(r'(?:本|此|该|上述)(?:系统|批|炉|水轮|窑室)', text):
        require(not _changed_value(key, _pinned_constants(row), text), '当前字段改写了本批或本系统已冻结的量')


def validate_use(row: dict, text: str, *, operation: str = '', stage: str = '') -> None:
    key = row['key']
    if key not in RULES:
        return
    rule, limit = row['excerpts']
    statement = normalize('NFKC', text)
    action = normalize('NFKC', operation)
    require(not _contradiction(key, rule, limit, statement, adopted=True)
            and not _contradiction(key, rule, limit, action, adopted=True), '采用字段与冻结转化方向、批次或系统总账冲突')
    require(not _changed_value(key, _pinned_constants(row), statement), '采用字段改写了本批或本系统已冻结的量')
    require(_identified(rule + limit, statement), '采用字段缺少实际核算对象或同批转化对象')
    if key == PURITY:
        linked = _batch_link(statement) or _batch_link(action) and bool(re.search(_PURITY + '|' + _RATE, statement))
        require(linked, '采用字段须落实本批次转化对成品纯度的实际影响')
    else:
        require(bool(re.search(_FLOW, statement) and re.search(_TOTAL + '|' + _BOUNDARY + r'|入账|计入|计回|核算|盘点|对账', statement)),
                '采用字段须落实追查能量去向及其在系统边界内的核算')
