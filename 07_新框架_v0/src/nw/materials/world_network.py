"""Match world-design rules to the selected type and one approved world card."""
from collections.abc import Callable, Iterator
import ast
import math
import re
import unicodedata

from nw.materials.phase_routes import phase_order, product_ref
from nw.materials.world_market import POLICY as MARKET_POLICY, market_families
from nw.materials.world_history import POLICY as HISTORY_POLICY, history_families, consistent_history_cards
from nw.materials.world_resources import POLICY as RESOURCE_POLICY, resource_families
from nw.materials.semantic_application import has_content, pointer_tokens, require


POLICY = 'world-formula-prerequisites-v1'
RULES = {
    'C00029': ('能量总量', ('能量总量', '总能量', '能量储备', '储能总量', '储能量', '总量')),
    'C00034': ('能量纯度', ('能量纯度', '纯度指数', '纯度系数', '纯度')),
    'C00039': ('能量运用技巧', ('能量运用技巧', '运用技巧', '技巧倍率', '技巧系数', '技巧')),
}

_CLAUSE = re.compile(r'[。；;！？!?\r\n]+')
_SEGMENT = re.compile(r'[，,]')
_UNSET = re.compile(r'待定|待补|待确认|待议|另议|尚未|未确定|未知|暂定|例如|假设|仅作示例|<填写')
_NOT_ADOPTED = re.compile(r'不采用|未采用|取消|不再(?:使用|采用)')
_RHS = r'(?P<rhs>[^，,：:。；;！？!?\r\n]+)'
_POWER_EXPRESSION = re.compile(
    r'(?P<lhs>力量(?:评分|值|输出)?|战力(?:评分|值)?|实际威力|输出威力|能量输出强度)\s*[=＝]\s*' + _RHS)
_POWER_ALIAS = re.compile(
    r'(?:力量|战力|威力)(?:公式|计算式|表达式)\s*[:：]?\s*'
    r'(?P<lhs>[A-Za-z][A-Za-z_0-9]*)\s*[=＝]\s*' + _RHS)
_OPERATORS = str.maketrans({'×': '*', '÷': '/', '^': '**', '−': '-'})
_FORMULA_NODES = {ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.UAdd, ast.USub}
_MEASURE = re.compile(
    r'单位(?:为|是|用|取|[:：])|按.{1,16}(?:计量|计分|分级|记录|计算)|以.{1,16}(?:为单位|计|记|评分)|'
    r'(?:\d|[一二两三四五六七八九十])\s*(?:档|级|格|分|度|灵值|百分点|[%％])|百分比|无量纲')
_BOUNDARY = re.compile(r'仅|只|限于|限制|适用|可用|不得|禁止|条件|范围|门槛|在.{1,20}时|超过|比较')
_CONTINUED_MEASURE = re.compile(r'^\s*(?:其|该变量|该量)?\s*(?:计量单位|单位|按|以)')
_ALIAS_MAPPING = r'(?:\s+|\s*(?:变量|记为|用|写作|为|对应|[:：=＝])\s*)'
_REVERSE_MAPPING = r'\s*(?:是|表示|为|对应|衡量|指|代表|[=＝:：])\s*'


def _compact(value: str) -> str:
    return ''.join(unicodedata.normalize('NFKC', value).split())


def _formula_names(rhs: str) -> list[str]:
    text = unicodedata.normalize('NFKC', rhs).translate(_OPERATORS)
    try:
        expression = ast.parse(text, mode='eval')
    except (SyntaxError, ValueError, RecursionError):
        return []
    names = {}
    for node in ast.walk(expression):
        if type(node) not in _FORMULA_NODES:
            return []
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float)
                or type(node.value) is float and not math.isfinite(node.value)):
            return []
        if isinstance(node, ast.Name):
            names[node.id] = None
    return list(names)


def _expressions(rule: str) -> list[tuple[str, str]]:
    expressions = []
    for clause in _CLAUSE.split(rule):
        for pattern in (_POWER_ALIAS, _POWER_EXPRESSION):
            for match in pattern.finditer(clause):
                rhs = match['rhs'].strip()
                assertion = clause[:match.end()]
                if _UNSET.search(assertion) or _NOT_ADOPTED.search(assertion) or not _formula_names(rhs):
                    continue
                expressions.append((clause[match.start('lhs'):match.end('rhs')].strip(), rhs))
    return expressions


def _variable_definition(rhs: str, texts: list[str], terms: tuple[str, ...]) -> tuple[str, str] | None:
    operands = _formula_names(rhs)
    label = '(?:' + '|'.join(map(re.escape, terms)) + ')'
    other_labels = re.compile('|'.join(re.escape(word) for _, words in RULES.values() for word in words if word not in terms))
    for text in texts:
        for clause in _CLAUSE.split(text):
            clause = clause.strip()
            if not clause or _UNSET.search(clause) or _NOT_ADOPTED.search(clause):
                continue
            segments = _SEGMENT.split(clause)
            for index, segment in enumerate(segments):
                next_segment = segments[index + 1] if index + 1 < len(segments) else ''
                if other_labels.search(segment) or not (_MEASURE.search(segment)
                        or _CONTINUED_MEASURE.search(next_segment) and _MEASURE.search(next_segment)):
                    continue
                for operand in operands:
                    if operand in terms and re.search(label, segment):
                        return operand, clause
                    if re.fullmatch(r'[A-Za-z][A-Za-z_0-9]*', operand):
                        symbol = r'(?<![A-Za-z_0-9])' + re.escape(operand) + r'(?![A-Za-z_0-9])'
                        if (re.search(label + _ALIAS_MAPPING + symbol, segment)
                                or re.search(symbol + _REVERSE_MAPPING + label, segment)):
                            return operand, clause
    return None


def _approved_formula(card: dict, terms: tuple[str, ...]) -> dict | None:
    if (card.get('kind') != 'world' or card.get('status') != 'approved'
            or not isinstance(card.get('card_id'), str) or not card['card_id'].strip()
            or type(card.get('version')) is not int or card['version'] < 1):
        return None
    body = card.get('body', {})
    rule, limits = body.get('rule'), body.get('limits')
    if (not isinstance(rule, str) or not isinstance(limits, str) or not has_content(limits)
            or not _BOUNDARY.search(limits) or _UNSET.search(limits)):
        return None
    formulae = _expressions(rule)
    if len({_compact(formula) for formula, _ in formulae}) != 1:
        return None
    formula, rhs = formulae[0]
    definition = _variable_definition(rhs, [rule, limits], terms)
    if definition is None:
        return None
    variable, sentence = definition
    ident = card['card_id']
    return {'card_id': ident, 'version': card['version'], 'formula': formula, 'variable': variable,
            'definition': sentence, 'limits': limits, 'rule_ref': f'approved:{ident}:/body/rule',
            'limits_ref': f'approved:{ident}:/body/limits'}


def project_families(context: dict) -> Iterator[tuple[str, dict, Callable[[dict, str], dict | None]]]:
    for group, policy, families in (('resource', RESOURCE_POLICY, resource_families),
                                    ('market', MARKET_POLICY, market_families),
                                    ('history', HISTORY_POLICY, history_families)):
        if context.get('world_' + group + '_policy') == policy:
            for requirements, approved in families():
                yield group, requirements, approved


def enabled_rules(context: dict) -> set[str]:
    from nw.materials.world_advancement import POLICY as ADVANCEMENT_POLICY, RULES as ADVANCEMENT_RULES
    from nw.materials.world_conversion import POLICY as CONVERSION_POLICY, RULES as CONVERSION_RULES

    rules = set(RULES) if context.get('world_network_policy') == POLICY else set()
    if context.get('world_advancement_policy') == ADVANCEMENT_POLICY:
        rules.update(ADVANCEMENT_RULES)
    if context.get('world_conversion_policy') == CONVERSION_POLICY:
        rules.update(CONVERSION_RULES)
    for _, requirements, _ in project_families(context):
        rules.update(requirements)
    return rules


def availability(key: str, valid_types: object, products: dict, context: dict) -> tuple[dict | None, list[str]]:
    from nw.materials.network_workflow import type_matches
    from nw.materials.world_advancement import RULES as ADVANCEMENT_RULES, approved_advancement
    from nw.materials.world_conversion import RULES as CONVERSION_RULES, approved_conversion

    if key not in enabled_rules(context):
        return None, []
    selection = products.get('type_selection', {})
    if selection.get('stage') != 'type_selection' or not selection.get('sha256'):
        return None, ['冻结的类型选择']
    product_ref(selection)
    scope = context.get('network_type_scope', {})
    refs = {}
    for index, row in enumerate(selection['products'].get('selection', [])):
        ident = row['id']
        if ident in scope and has_content(row.get('basis')) and type_matches(valid_types, {ident: scope[ident]}):
            refs[ident] = f'input:type_selection:/selection/{index}'
    if not refs:
        return None, ['已选且符合原条的类型']
    packet = {'type_ids': list(refs), 'type_refs': refs, 'output': 'members'}
    families = [('advancement', ADVANCEMENT_RULES, approved_advancement),
                ('conversion', CONVERSION_RULES, approved_conversion)]
    families.extend(project_families(context))
    for kind, requirements, approved in families:
        if key in requirements:
            cards = [proof for card in context.get('approved_cards', [])
                     if (proof := approved(card, key)) is not None]
            if not cards:
                return None, ['同一份已批准世界卡中的' + requirements[key]]
            if kind == 'history':
                cards = consistent_history_cards(key, cards, context['approved_cards'])
                if not cards:
                    return None, ['裁定同一历史分期或同一地区同期历史后果的冲突记录']
            return {**packet, 'cards': cards, 'kind': kind}, []
    factor, terms = RULES[key]
    cards = [proof for card in context.get('approved_cards', []) if (proof := _approved_formula(card, terms)) is not None]
    if not cards:
        return None, [f'同一份已批准世界卡中的力量公式、{factor}计量和适用限制']
    return {**packet, 'cards': cards}, []


def _validate_basis(source: dict, raw: dict, context: dict) -> None:
    from nw.materials.network_workflow import STATIC_PROFILES

    pin = context.get('world_network_bases', {}).get(source['source']['id'], {})
    original = pin.get('source', {})
    edge = pin.get('edge', {})
    require(isinstance(original, dict) and isinstance(edge, dict) and isinstance(pin.get('static_id'), str)
            and pin['static_id'] == original.get('id') and original.get('profile') in STATIC_PROFILES
            and all(isinstance(original.get(field), str) and original[field] for field in ('path', 'sha256', 'file_sha256'))
            and source.get('related_sources') == [pin['static_id']]
            and all(isinstance(edge.get(field), str) and edge[field] == raw.get(field) for field in ('source', 'target', 'type'))
            and isinstance(edge.get('condition'), str) and edge['condition'].strip()
            and raw.get('condition') == edge['condition'] + '；且当前故事明确采用该静态关系',
            'world formula use needs the same pinned static original')


def _cited_card(clause: dict, cards: list[dict]) -> dict:
    supplied = set(clause['input_refs'])
    matches = [card for card in cards if {card['rule_ref'], card['limits_ref']} <= supplied]
    require(len(matches) == 1, 'world clause must cite rule and bounds from one approved world card')
    card = matches[0]
    world_refs = {path for path in supplied if path.startswith('approved:') and path.endswith(('/body/rule', '/body/limits'))}
    require(world_refs == {card['rule_ref'], card['limits_ref']}, 'world formula clause cannot mix calculation cards')
    return card


def _validate_formula_output(body: dict, card: dict) -> None:
    approved = _compact(card['formula'])
    lhs = re.split(r'[=＝]', card['formula'], maxsplit=1)[0].strip()
    assignment = re.compile(r'(?<![A-Za-z_0-9])' + re.escape(lhs) + r'\s*[=＝]\s*' + _RHS)
    produced = {_compact(match.group()) for match in assignment.finditer(body['rule'])}
    require(produced == {approved} and {_compact(formula) for formula, _ in _expressions(body['rule'])} <= {approved},
            'world output must preserve the approved formula without changing or adding coefficients')
    combined = _compact(body['rule'] + body['limits'])
    require(_compact(card['definition']) in combined and _compact(body['limits']) == _compact(card['limits']),
            'world output must keep the approved variable definition, scale and applicability limits')


def validate_world_network_use(source: dict, raw: dict, value: dict, products: dict, context: dict) -> None:
    """Require each adopted rule to use the approved world mechanics and hand them off."""
    key, source_id = source['source']['key'], source['source']['id']
    require(raw.get('id') == key and raw.get('generated_from_static') is True, 'world formula use needs its derived dynamic original')
    _validate_basis(source, raw, context)
    ready, missing = availability(key, raw.get('valid_types'), products, context)
    require(ready is not None, key + ' 缺少：' + '、'.join(missing))
    use = next((item for item in value.get('_uses', []) if item['source_id'] == source_id), None)
    criterion = next((item for item in value.get('_criteria', []) if item['source_id'] == source_id), {})
    applied = [row for row in criterion.get('clauses', []) if row['applicability'] == 'applies']
    rows = {'member:' + row['key']: index for index, row in enumerate(value['members']) if row['kind'] == 'world'}
    require(use is not None and bool(use['output_refs']) and len(set(use['output_refs'])) == len(use['output_refs'])
            and set(use['output_refs']) <= rows.keys() and bool(applied),
            'world formula use needs exact world members and applied original clauses')
    order = phase_order(context.get('scope', 'chapter'))
    later = set(order[order.index('world_design') + 1:])
    selected = {rows[ref] for ref in use['output_refs']}
    cited: dict[int, dict] = {}
    fields = {index: set() for index in selected}
    for clause in applied:
        refs = {ref.replace(':/products/', ':/', 1) for ref in clause['input_refs']}
        require(any(prefix in refs or prefix + '/basis' in refs or prefix + '/id' in refs
                    for prefix in ready['type_refs'].values()), 'world formula clause must cite an actually selected type')
        basis = _cited_card(clause, ready['cards'])
        require(clause['consumer'] in later and bool(clause['output_refs']),
                'world formula clause must hand the actual result to a later stage in scope')
        for output in clause['output_refs']:
            path = pointer_tokens(output)
            require(len(path) == 4 and path[0] == 'members' and path[1].isdigit() and int(path[1]) in selected
                    and path[2] == 'body' and path[3] in ('rule', 'limits'),
                    'world formula clause must cite an exact rule or limits field of the member it used')
            index = int(path[1])
            require(index not in cited or cited[index] == basis, 'a world output cannot combine different approved formulae')
            cited[index] = basis
            fields[index].add(path[3])
    for index in selected:
        require(fields[index] == {'rule', 'limits'}, 'each adopted world member must hand off both its rule and limits')
        body, basis = value['members'][index]['body'], cited[index]
        if kind := ready.get('kind'):
            require(body['rule'] == basis['rule'] and body['limits'] == basis['limits'],
                    f'world {kind} must preserve the complete approved requirements and applicability limits')
        else:
            _validate_formula_output(body, basis)
