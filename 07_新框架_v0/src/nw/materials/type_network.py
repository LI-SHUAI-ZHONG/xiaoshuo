"""Ground early network rules in explicit author choices and actual type products."""
from collections import defaultdict
import json
import re

from nw.length_settings import LENGTH_FIELDS
from nw.materials.phase_routes import phase_order, product_ref
from nw.materials.semantic_application import has_content, input_value, pointer_tokens, require


POLICY = 'type-network-prerequisites-v1'
ELEMENTS = ('reader_promise',)
CONVENTION = ('convention', 'departure', 'innovation_scope')
EXPECTATION = ('reader_promise', 'innovation_scope')
FUSION = ('fusion_method', 'fusion_roles')
COMMERCIAL_FUSION = (*FUSION, 'commercial_strategy', 'fusion_measure')
MARKET = ('market_position', 'reader_promise', 'market_check')

RULES = {
    'C00077': ELEMENTS, 'C00079': CONVENTION, 'C00082': CONVENTION, 'C00084': EXPECTATION,
    'C00085': FUSION, 'C00086': COMMERCIAL_FUSION, 'C00152': COMMERCIAL_FUSION,
    'C00153': COMMERCIAL_FUSION, 'C00156': MARKET, 'C00179': ELEMENTS, 'C00180': MARKET,
    'C00182': (*FUSION, 'length'), 'C00183': ELEMENTS, 'C00184': FUSION,
    'C00185': FUSION, 'C00186': COMMERCIAL_FUSION,
}
INPUT_FIELDS = tuple(dict.fromkeys(field for fields in RULES.values() for field in fields))
FIELD_LABELS = {
    'reader_promise': '已明确的读者承诺', 'convention': '已核实的具体类型惯例',
    'departure': '作者选择的具体突破', 'innovation_scope': '作者已定的保留与调整范围',
    'fusion_method': '作者选择的融合方式', 'fusion_roles': '主辅类型的实际分工',
    'length': '已确定的篇幅', 'commercial_strategy': '作者采用的商业策略',
    'fusion_measure': '项目已确定的构成口径', 'market_position': '作者明确的商业定位',
    'market_check': '可供核查的商业目标或评价依据',
}

_AUTHOR_PREFERENCES = '\n\n作者偏好（不代替设计步骤与冻结产物）：\n'
_WIZARD_LENGTH = '\n\n立项参数：\n'
_LENGTH_VALUE = re.compile(r'(?:(?<![第\d零〇一二两三四五六七八九十百千万亿])[\d零〇一二两三四五六七八九十百千万亿][\d零〇一二两三四五六七八九十百千万亿,.，]*\s*(?:字|章|卷)|长篇|中篇|短篇|微型小说)')
_NO_DECISION = re.compile(r'(?:待定|待补|待确认|待选择|待讨论|尚未|暂定|暂无|未决定|未确定|未提供|还没确定|是否|或许|也许|可能会|可考虑|拟考虑|由设计步骤提出方案|仅供参考|仅为示例|只是示例|<填写)')
_NEGATIVE = re.compile(r'(?:不采用|不打算|不选择|不考虑|不做|不进行|并非|不是|取消|不需要|无需|暂不|先不|不用|拒绝采用|不明确|没有)')
_CLAUSE_END = re.compile(r'[。！？!?；;\r\n]')
_REJECTED_ALTERNATIVE = re.compile(r'[，,]?\s*而(?:不是|非)')
_CARD_FIELDS = {
    'brief': {'reader_promise', 'author_words', 'goal', 'constraints', 'completion', 'acceptance'},
    'plot': {'reader_promise', 'choice', 'ending_direction', 'central_question', 'protagonist_want', 'cost'},
}
_ROLE_MARKERS = {
    'reader_promise': (r'读者|阅读体验|读完|读到|阅读时|(?:本作|本书)(?:的)?承诺|预期体验|读起来',),
    'convention': (r'惯例|约定俗成|常见|常规|常用|惯常|传统|一般会|通常|向来|习惯于|固定套路',),
    'departure': (r'突破|偏离|改用|改成|改为|改由|换成|改换|提前|延后|不同于|反过来|先.+(?:后|而|再)|替代',),
    'innovation_scope': (r'只调整|只改变|只在|只改|仅限|限于|保留|不改|允许|绝不改变|范围|边界|保持',),
    'fusion_method': (r'融合|混合|合流|并线|串起|串联|并入|合并|揉进|交错|交织|并行|穿插|结合',),
    'fusion_roles': (r'(?:主线|辅线|副线|支线|主类|辅类|主类型|副类型|承担|负责|提供|驱动|服务于).*(?:主线|辅线|副线|支线|主类|辅类|主类型|副类型|承担|负责|提供|驱动|服务于)',),
    'commercial_strategy': (r'商业|市场|受众|推广|订阅|连载|平台|榜单|付费|试读|卖点|面向.{0,24}读者',
                            r'策略|方向|包装|吸引|推广|导流|聚焦|强化|留存|主打|试水|推出|投放'),
    'fusion_measure': (r'比例|比重|分母|占比|构成|口径|计算|配额|[：:]\s*\d|\d\s*[%％]|[一二两三四五六七八九十]成',
                       r'场次|有效场|场景|章节|每章|整卷|字数|篇幅|线索|段落|节拍|分钟|[：:]\s*\d|\d\s*[%％]|[一二两三四五六七八九十]成'),
    'market_position': (r'定位|面向|瞄准|针对|目标读者|主要读者|主打|读者群|聚焦|争取',
                        r'读者|受众|人群|平台|市场|赛道|粉丝|用户|群体'),
    'market_check': (r'试读|评论|回访|读者反馈|订阅|完读|留存|追读|追更|点击|分享|推荐|评价|问卷|反馈',
                     r'核对|验证|检验|衡量|统计|记录|对照|观察|能否|比例|超过|达到|评估|作为.{0,12}依据'),
}


def _from_wizard_length(quote: str, text: str) -> bool:
    if _AUTHOR_PREFERENCES not in text:
        return False
    _, divider, data = text.rpartition(_WIZARD_LENGTH)
    if not divider:
        return False
    try:
        values = json.loads(data)
    except ValueError:
        return False
    if (not isinstance(values, dict) or not values or not values.keys() <= set(LENGTH_FIELDS)
            or any(type(value) is not int or (not 0 <= value <= 99 if key == 'word_tolerance_pct' else value < 1)
                   for key, value in values.items())):
        return False
    lines = {f'{json.dumps(key)}:{value}' for key, value in values.items() if key != 'word_tolerance_pct'}
    return bool(lines) and quote in data and (quote == data or quote in lines)


def _commitment_found(field: str, quote: str, text: str) -> bool:
    if not text or quote not in text or _NO_DECISION.search(quote):
        return False
    if field == 'length' and not _LENGTH_VALUE.search(quote):
        return False
    for match in re.finditer(re.escape(quote), text):
        # Check the surrounding assertion as well, so a clipped positive substring
        # cannot turn an author's rejection into permission.
        prior = _CLAUSE_END.split(text[:match.start()])[-1]
        suffix = _CLAUSE_END.split(text[match.end():], maxsplit=1)[0]
        assertion = prior + quote + suffix
        alternative = _REJECTED_ALTERNATIVE.search(assertion)
        if alternative and len(prior) + len(quote) <= alternative.start():
            assertion = assertion[:alternative.start()]
        if _NO_DECISION.search(assertion):
            continue
        if field != 'innovation_scope' and _NEGATIVE.search(assertion):
            continue
        return True
    return False


def _right_role(field: str, quote: str, approved_leaf: str = '') -> bool:
    if field == 'reader_promise' and approved_leaf == field:
        return True
    return all(re.search(pattern, quote) for pattern in _ROLE_MARKERS.get(field, ()))


def validate_adaptation_inputs(value: dict, products: dict, context: dict) -> None:
    """Check exact source quotations added to a type selection, never infer consent."""
    if 'adaptation_inputs' not in value:
        return
    require(context.get('type_network_policy') == POLICY, 'adaptation inputs have no frozen type network policy')
    evidence = value['adaptation_inputs']
    require(isinstance(evidence, dict) and evidence.keys() <= set(INPUT_FIELDS), 'unknown type adaptation premise')
    for field, piece in evidence.items():
        require(isinstance(piece, dict) and set(piece) == {'ref', 'quote'}, 'type premise needs an exact author quotation')
        reference, quote = piece['ref'], piece['quote']
        require(isinstance(reference, str) and isinstance(quote, str) and quote == quote.strip()
                and 2 <= len(''.join(quote.split())) <= 400 and has_content(quote), 'type premise is missing concrete author text')
        leaf = ''
        if reference in ('brief:/text', 'brief:/constraints'):
            text = context.get('brief', {}).get(reference.removeprefix('brief:/'))
            require(isinstance(text, str), 'type premise has no current frozen brief')
            if field == 'length' and reference == 'brief:/text' and _from_wizard_length(quote, text):
                continue
            text = text.split(_AUTHOR_PREFERENCES, 1)[0] if reference == 'brief:/text' else text
        else:
            match = re.fullmatch(r'approved:(.+):/body/([a-z_]+)', reference)
            require(match is not None, 'type premise must cite the frozen brief or an approved card field')
            card_id, leaf = match.groups()
            card = next((row for row in context.get('approved_cards', [])
                         if row.get('card_id', row.get('id')) == card_id), {})
            require(leaf in _CARD_FIELDS.get(card.get('kind'), ()), 'type premise must cite an approved brief or plot field')
            text = input_value(reference, 'type_selection', products, context)
        require(isinstance(text, str) and _commitment_found(field, quote, text),
                FIELD_LABELS[field] + ' requires an actual affirmative author quotation')
        require(_right_role(field, quote, leaf), FIELD_LABELS[field] + ' requires an author quotation that supports this specific role')


def _type_references(selected: dict, scope: dict, valid_types: object) -> dict[str, str]:
    from nw.materials.network_workflow import type_matches

    result = {}
    for index, row in enumerate(selected.get('selection', [])):
        ident = row['id']
        if ident in scope and has_content(row.get('basis')) and type_matches(valid_types, {ident: scope[ident]}):
            result[ident] = f'input:type_selection:/selection/{index}'
    return result


def _many_families(ids: list[str], context: dict) -> bool:
    families = context.get('type_network_families', {})
    return len({families[ident] for ident in ids if families.get(ident)}) >= 2


def availability(key: str, valid_types: object, products: dict, context: dict) -> tuple[dict | None, list[str]]:
    """Return the stage packet for this rule only after its real premises exist."""
    if context.get('type_network_policy') != POLICY or key not in RULES:
        return None, []
    record = products.get('type_selection')
    if not record or record.get('stage') != 'type_selection' or not record.get('sha256'):
        return None, ['已冻结的类型选择']
    product_ref(record)
    selected = record['products']
    validate_adaptation_inputs(selected, products, context)
    type_refs = _type_references(selected, context.get('network_type_scope', {}), valid_types)
    fields = RULES[key]
    evidence = selected.get('adaptation_inputs', {})
    missing = [FIELD_LABELS[field] for field in fields if field not in evidence]
    if not type_refs:
        missing.insert(0, '已选且符合原条的类型')
    elif 'fusion_method' in fields and not _many_families(list(type_refs), context):
        missing.insert(0, '至少两类已选且符合原条的独立主类型')
    if missing:
        return None, missing
    return {'type_ids': list(type_refs), 'type_refs': type_refs,
            'inputs': {field: f'input:type_selection:/adaptation_inputs/{field}/quote' for field in fields},
            'output': 'boundaries' if fields == CONVENTION else 'adaptations'}, []


def _validate_basis(source: dict, raw: dict, context: dict) -> None:
    from nw.materials.network_workflow import STATIC_PROFILES

    pin = context.get('type_network_bases', {}).get(source['source']['id'], {})
    proof, edge = pin.get('source', {}), pin.get('edge', {})
    require(isinstance(proof, dict) and isinstance(edge, dict) and isinstance(pin.get('static_id'), str)
            and pin['static_id'] == proof.get('id') and proof.get('profile') in STATIC_PROFILES
            and all(isinstance(proof.get(field), str) and proof[field] for field in ('sha256', 'file_sha256', 'path'))
            and source.get('related_sources') == [pin['static_id']]
            and all(isinstance(edge.get(field), str) and edge[field] == raw.get(field) for field in ('source', 'target', 'type'))
            and isinstance(edge.get('condition'), str) and edge['condition'].strip()
            and raw.get('condition') == edge['condition'] + '；且当前故事明确采用该静态关系',
            'type network use must keep its unique pinned original static edge')


def _path_type_ids(clause: dict, ready: dict) -> set[str]:
    normalized = {ref.replace(':/products/', ':/', 1) for ref in clause['input_refs']}
    require(set(ready['inputs'].values()) <= normalized, 'type network clause omitted a required author premise')
    return {ident for ident, prefix in ready['type_refs'].items()
            if prefix in normalized or prefix + '/basis' in normalized or prefix + '/id' in normalized}


def validate_type_network_use(source: dict, raw: dict, value: dict, products: dict, context: dict) -> None:
    """Verify each adopted type rule's exact design output and actual downstream use."""
    key, source_id = source['source']['key'], source['source']['id']
    require(raw.get('id') == key and raw.get('generated_from_static') is True, 'type network use needs the matching dynamic original')
    _validate_basis(source, raw, context)
    ready, missing = availability(key, raw.get('valid_types'), products, context)
    require(ready is not None, key + '缺少：' + '、'.join(missing))
    use = next(row for row in value.get('_uses', []) if row['source_id'] == source_id)
    criterion = next((row for row in value.get('_criteria', []) if row['source_id'] == source_id), {})
    applied = [row for row in criterion.get('clauses', []) if row['applicability'] == 'applies']
    require(bool(applied), 'type network use needs an applied original clause')
    paths = use['output_refs']
    require(bool(paths) and len(set(paths)) == len(paths), 'type network use needs distinct actual output refs')
    target = ready['output']
    if target == 'adaptations':
        rows = {'adaptation:' + row['id']: index for index, row in enumerate(value['adaptations'])}
        require(set(paths) <= rows.keys(), 'type network use must name its actual adaptation rows')
        covered = {rows[ref] for ref in paths}
    else:
        require(paths == ['boundaries'], 'convention network use must name the actual boundaries')
        covered = set()
    order = phase_order(context.get('scope', 'chapter'))
    consumers = set(order[order.index('type_adaptation') + 1:])
    uses_by_row = defaultdict(set)
    parameter_rows = set()
    for clause in applied:
        provided = _path_type_ids(clause, ready)
        require(bool(provided), 'type network clause must cite its actual selected type')
        require(clause['consumer'] in consumers, 'type network clause must hand off to a real later stage in scope')
        require(bool(clause['output_refs']), 'type network rule must identify an actual output field')
        for path in clause['output_refs']:
            path_parts = pointer_tokens(path)
            require(len(path_parts) >= 2 and path_parts[0] == target and path_parts[1].isdigit(),
                    'type network clause must identify a precise output row')
            index = int(path_parts[1])
            if target == 'boundaries':
                require(len(path_parts) == 2 and index < len(value['boundaries']), 'type network clause must cite an actual boundary')
                continue
            require(index in covered and len(path_parts) >= 4 and path_parts[2] in ('parameters', 'limits'),
                    'type network clause must cite a field of the adaptation it claims to use')
            row = value['adaptations'][index]
            require(provided <= set(row['type_refs']) <= set(ready['type_ids']),
                    'adaptation row must use and cite only its actual permitted selected types')
            uses_by_row[index].update(provided)
            if path_parts[2] == 'parameters':
                parameter_rows.add(index)
    for index in covered:
        ids = value['adaptations'][index]['type_refs']
        require(index in parameter_rows and uses_by_row[index] == set(ids),
                'every adopted adaptation needs an actual parameter and citations for each type used')
        if 'fusion_method' in RULES[key]:
            require(_many_families(ids, context), 'a fusion adaptation needs the two distinct selected main families it uses')
