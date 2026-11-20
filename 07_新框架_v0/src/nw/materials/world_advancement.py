"""Recognize confirmed advancement conditions without awarding advancement."""
from collections.abc import Callable
import re
import unicodedata


POLICY = 'world-advancement-prerequisites-v1'
RULES = {
    'C00047': '实际力量公式及对应结果的进阶门槛',
    'C00099': '进阶所测的实际指标、临界值、方向和单位',
    'C00195': '明确的天赋等级及所限制的进阶阶段',
    'C00242': '可观察的结晶标志、对应阶段及独立进阶条件',
    'C00736': '社会晋升和能力进阶的独立判据及明确共用条件',
    'C00808': '实际构造、承载上限及其影响的进阶条件',
}

_SENTENCES = re.compile(r'[^。；;！？!?\r\n]+')
_UNCONFIRMED = re.compile(
    r'待定|未定|待核|待补|待确认|尚未|未确定|未确认|未公布|暂定|拟采用|或许|可能|假设|例如|示例|'
    r'反例|旧方案|废止|作废|已取消|<填写')
_INACTIVE = re.compile(r'不再(?:采用|使用)|不采用|未采用')
_GLOBAL_INACTIVE = re.compile(r'(?:全书|本作|本项目|所有阶段)[^，,]{0,16}(?:不再(?:采用|使用)|不采用|未采用)')
_OTHER_UNCONFIRMED = re.compile(r'[，,]\s*(?:其余|其他|额外)(?:的)?(?:进阶|晋级|核验)?(?:条件|判据|要求|步骤)')
_NOT_A_GATE = re.compile(
    r'(?:不是|并非|不属于|不构成|不能作为|不作为|不影响|与.{0,10}无关)'
    r'.{0,12}(?:进阶|突破|晋升|晋级|门槛|条件|标志|判据)')
_ADVANCE = re.compile(r'进阶|突破|晋级|提升境界|进入[^，,\s]{1,8}(?:境|阶|阶段|期)')
_GATE = re.compile(r'必要条件|门槛|判据|必须|须|需要|要求|方可|方能|才能|才可|才允许|不得')
_LINKED_GATE = re.compile(r'^(?:方可|方能|才能|才可|才允许|是|作为|可作为|构成|计入|用于)')
_GATE_INTRO = re.compile(r'(?:必要条件|门槛|判据|必须|条件|要求)(?:是|为|包括)?\s*[:：]\s*$')
_SOCIAL = re.compile(r'(?:社会|阶层|职位|职级|官阶|职衔|职务|公会|行会|教团|宗门|学徒|外门|内门)[^，,]{0,10}晋升|录任|任职')
_ABILITY = re.compile(r'能力进阶|修炼进阶|境界(?:进阶|突破)|进阶|突破[^，,]{1,12}(?:境|階|阶)')
_INDEPENDENT = re.compile(r'另须|另需|另要|还须|还需|仍须|仍需|还要|并须|并需|同时须')
_COLLECTIVE = re.compile(r'两者|二者|两套规则|两条路径')
_SHARED = re.compile(r'共同(?:前置|要求|条件|判据|要求核验)(?:是|为|包括)?|共用(?:的)?(?:前置|要求|条件|判据)?|均须|都须|都需|都要')
_VAGUE_TAIL = re.compile(r'(?:(?:完成|符合|达到|满足|遵守|通过|核验)?(?:全部|其他|相关|必要|既定|正常|法定)*(?:要求|条件|规则|流程|程序|核验|业已确定的规则))+(?:即可)?[。；]?$')
_BOUNDARY = re.compile(r'仅|只|限于|限制|适用|不可|不得|禁止|须|条件|范围|门槛|在.{1,20}时')
_NUMBER = r'[-−+＋]?(?:[0-9０-９]+(?:[.．][0-9０-９]+)?|[零〇一二两三四五六七八九十百千万亿]+)'
_UNIT = (r'(?:灵值|灵格|灵压值|灵力值|灵能值|能量单位|标准单位|单位|百分点|百帕|千帕|兆帕|焦耳|瓦特|斤|克|千克|吨|格|度|点|分|'
         r'档|级|阶|成|枚|%|％|[A-Za-z][A-Za-z0-9]*(?![A-Za-z0-9_]))')
_COMPARISON = (r'(?:[<>＜＞]\s*[=＝]?|[≥≤]|大于等于|小于等于|不得低于|不得超过|不低于|不高于|不超过|'
               r'不小于|不少于|不多于|至少(?:为|达到)?|低于|超过|高于|达到|等于|大于|小于|上限(?:是|为|到)|'
               r'临界值(?:是|为)|阈值(?:是|为)|最多(?:为|达到)?|[=＝])')
_QUANTITY = r'(?P<value>' + _NUMBER + r')\s*(?P<unit>' + _UNIT + r')?'
_METRIC = re.compile(r'能量(?:浓度|密度|总量|纯度|储备|储量|输出|强度)?|灵压|灵力|灵能|浓度|密度|蓄能|储能|纯度|聚合度|灵脉通量')
_TALENT = re.compile(r'天赋(?:评级|评定|品阶|等级|测定|评测)?\s*(?:(?:必须|须|需要|需)?\s*'
                     r'(?:至少(?:达到)?|不得低于|不低于|达到|定为|为|是|属于|[:：])\s*)?'
                     r'(?:[甲乙丙丁戊己庚辛壬癸]|[SABCDsabcd][+＋\-－]?|' + _NUMBER + r')\s*'
                     r'(?:等|级|阶|档|品|段)(?:以上|以下)?')
_CRYSTAL = re.compile(r'结晶|晶核|晶纹')
_VISIBLE = re.compile(r'可见|可测|可查|可观察|形成[^，,]{1,10}(?:晶|纹|斑|棱)|出现[^，,]{1,10}(?:晶|纹|光|声|棱|环)|呈现|显出|显现|响声|回响')
_SIGN = re.compile(r'标志|标记|判定标识|观察指标|据此辨认|用来辨认|识别标识|观察判据')
_PHASE = re.compile(r'(?:是(?:进入)?|表示|表明|标志着|对应|辨认|识别|进入|处于|属于|到达|转入|判定)\s*'
                    r'(?P<phase>[^，,\s]{1,8}?(?:阶段|境|阶|期))(?=$|[的，,]|时|之后|开始|仍|还|另|须|需|必须)')
_NAMED_ADVANCE = re.compile(r'(?:进阶至|进阶到|突破(?:至|到)?|晋级至|进入|晋级到|进阶)\s*'
                            r'(?P<destination>[^，,\s]{1,8}?(?:阶段|境|阶|期))(?=$|[的，,]|时|仍|还|另|须|需|必须|才|方)'
                            r'|(?:从|由|向)\s*(?P<origin>[^，,\s]{1,8}?(?:阶段|境|阶|期)?)进阶')
_GENERAL_ADVANCE = re.compile(r'(?:所有|各个|各)进阶阶段')
_VAGUE_PHASES = {'某阶段', '该阶段', '本阶段', '此阶段', '前一阶段', '下一阶段', '新阶段', '某个阶段'}
_STRUCTURE = re.compile(r'构造|构件|体质|[灵符晶金铁玉钢铜]骨|[灵经]脉|经络|脉络|骨架|骨骼|机体|躯体|甲胄|外骨骼|义肢')
_CAPACITY = re.compile(r'承载|承压|负荷|耐压|承受|上限|容纳上限|容量上限')


def _assertions(text: str) -> list[str]:
    lines = []
    for match in _SENTENCES.finditer(text):
        line = match.group().strip()
        other = _OTHER_UNCONFIRMED.search(line)
        if other and _UNCONFIRMED.search(line[other.end():]):
            line = line[:other.start()].rstrip()
        if line and not (_UNCONFIRMED.search(line) or _INACTIVE.search(line) or _NOT_A_GATE.search(line)):
            lines.append(line)
    return lines


def _advance_gate(line: str) -> bool:
    return bool(_ADVANCE.search(line) and _GATE.search(line))


def _named_gate(line: str) -> bool:
    return bool(_GENERAL_ADVANCE.search(line) or any((match['destination'] or match['origin']) not in _VAGUE_PHASES
            for match in _NAMED_ADVANCE.finditer(line)))


def _rest_after(marker: re.Match[str], line: str) -> str:
    return re.split(r'[，,、]', line[marker.end():].strip(' ：:，,'), maxsplit=1)[0].strip()


def _explicit_requirement(text: str) -> bool:
    return len(text) >= 4 and not _VAGUE_TAIL.fullmatch(text)


def _condition_segment(line: str, match: re.Match[str]) -> str | None:
    """Require the detected quantity or grade to be the stated condition for advancing."""
    before = re.split(r'[，,]', line[:match.start()])
    after = re.split(r'[，,]', line[match.end():])
    segment = before[-1] + match.group() + after[0]
    if _advance_gate(segment):
        return segment.strip()
    if len(after) > 1 and _LINKED_GATE.match(after[1].strip()) and _advance_gate(after[1]):
        return segment.strip() + '，' + after[1].strip()
    if len(before) > 1 and _ADVANCE.search(before[-2]) and _GATE_INTRO.search(before[-2]):
        return before[-2].strip() + '，' + segment.strip()
    return None


def _thresholds(line: str, first: re.Pattern[str]) -> list[re.Match[str]]:
    pattern = re.compile(r'(?:' + first.pattern + r')\s*(?:计量值|数值|实际值|读数|实测值|计算值|结果)?\s*'
                         r'(?:必须|须|需要)?\s*' + _COMPARISON + r'\s*' + _QUANTITY, first.flags)
    return list(pattern.finditer(line))


def _formula_case(rule: str, lines: list[str]) -> dict[str, str] | None:
    from nw.materials.world_network import _compact, _expressions

    formulae = _expressions(rule)
    if len({_compact(entry[0]) for entry in formulae}) != 1:
        return None
    formula = formulae[0][0]
    lhs = re.split('[=＝]', formula, maxsplit=1)[0].strip()
    atom = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(lhs) + r'(?![A-Za-z0-9_])')
    # A second definition of the same result variable is ambiguous even without the formula label.
    assignment = re.compile(atom.pattern + r'\s*[=＝]\s*([^，,。；;！？!?\r\n]+)')
    if {_compact(match.group()) for match in assignment.finditer(rule)} != {_compact(formula)}:
        return None
    for line in lines:
        for match in _thresholds(line, atom):
            if (segment := _condition_segment(line, match)) and _named_gate(segment):
                return {'formula': formula, 'threshold': match.group(), 'gate': line}
    return None


def _threshold_case(lines: list[str]) -> dict[str, str] | None:
    for line in lines:
        for match in _thresholds(line, _METRIC):
            if match['unit'] and (segment := _condition_segment(line, match)) and _named_gate(segment):
                return {'threshold': match.group(), 'gate': line}
    return None


def _talent_case(lines: list[str]) -> dict[str, str] | None:
    for line in lines:
        if (level := _TALENT.search(line)) and (segment := _condition_segment(line, level)):
            if _named_gate(segment):
                return {'talent_grade': level.group(), 'gate': line}
    return None


def _crystal_case(lines: list[str]) -> dict[str, str] | None:
    for index, line in enumerate(lines):
        if not all(pattern.search(line) for pattern in (_CRYSTAL, _VISIBLE, _SIGN)):
            continue
        phase = _PHASE.search(line)
        if not phase or phase['phase'] in _VAGUE_PHASES:
            continue
        # An explicitly additional requirement can share the sentence or follow a marked stage.
        for condition in lines[index:index + 2]:
            if marker := _INDEPENDENT.search(condition):
                tail = _rest_after(marker, condition)
                other_phase = _PHASE.search(condition)
                if (_explicit_requirement(tail) and not _CRYSTAL.search(tail)
                        and (not other_phase or other_phase['phase'] == phase['phase'])
                        and (condition == line or _ADVANCE.search(condition) or '该阶段' in condition)):
                    return {'observable_sign': line, 'separate_gate': condition}
    return None


def _promotion_case(lines: list[str]) -> dict[str, str] | None:
    roles = [(index, line) for index, line in enumerate(lines)
             if _SOCIAL.search(line) and _GATE.search(line) and not _ABILITY.search(line)]
    abilities = [(index, line) for index, line in enumerate(lines) if _advance_gate(line) and not _SOCIAL.search(line)]
    if len(roles) != 1 or len(abilities) != 1:
        return None
    [(role_index, role)], [(ability_index, ability)] = roles, abilities
    for index, line in enumerate(lines):
        marker = _SHARED.search(line)
        if not marker or not _explicit_requirement(_rest_after(marker, line)):
            continue
        named = _SOCIAL.search(line) and _ABILITY.search(line)
        if named or (_COLLECTIVE.search(line) and {role_index, ability_index} == {index - 2, index - 1}):
            return {'social_gate': role, 'ability_gate': ability, 'shared_prerequisite': line}
    return None


def _structure_case(lines: list[str]) -> dict[str, str] | None:
    for line in lines:
        for match in _thresholds(line, _CAPACITY):
            if (match['unit'] and (segment := _condition_segment(line, match)) and _STRUCTURE.search(segment)
                    and _named_gate(segment)):
                return {'load_limit': match.group(), 'gate': line}
    return None


_MATCHERS: dict[str, Callable[[list[str]], dict[str, str] | None]] = {
    'C00099': _threshold_case,
    'C00195': _talent_case,
    'C00242': _crystal_case,
    'C00736': _promotion_case,
    'C00808': _structure_case,
}


def approved_advancement(card: dict, key: str) -> dict | None:
    if (key not in RULES or card.get('kind') != 'world' or card.get('status') != 'approved'
            or not isinstance(card.get('card_id'), str) or not card['card_id'].strip()
            or type(card.get('version')) is not int or card['version'] < 1):
        return None
    body = card.get('body', {})
    rule, limits = body.get('rule'), body.get('limits')
    if (not isinstance(rule, str) or not isinstance(limits, str) or _GLOBAL_INACTIVE.search(limits)
            or not any(_BOUNDARY.search(line) and not _UNCONFIRMED.search(line)
                       for line in _SENTENCES.findall(limits))):
        return None
    # Keep the two fields intact, and only match proof within this approved card.
    lines = [*_assertions(rule), *_assertions(limits)]
    evidence = _formula_case(rule, lines) if key == 'C00047' else _MATCHERS[key](lines)
    if evidence is None:
        return None
    ident = card['card_id']
    return {'card_id': ident, 'version': card['version'], 'rule': rule, 'limits': limits,
            'rule_ref': f'approved:{ident}:/body/rule', 'limits_ref': f'approved:{ident}:/body/limits', 'evidence': evidence}
