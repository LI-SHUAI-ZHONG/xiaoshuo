"""Find addressable records and fields inside the frozen material fragments."""
from dataclasses import dataclass
import json
import re
from typing import Iterator


@dataclass(frozen=True)
class Unit:
    start: int
    end: int
    kind: str
    key: str | None
    label: str | None
    locator: str
    origin: str = 'source'


_LIBRARY_FIELDS = {
    '定义': 'definition', '调用条件': 'condition', '适用条件': 'condition', '触发条件': 'condition',
    '指令': 'instruction', '设计指令': 'instruction', '写作指令': 'instruction',
    '判定标准': 'check', '检验点': 'check', '修正指南': 'correction', '例外处理': 'exception',
    '示例': 'example', '反面案例': 'counterexample', '反例': 'counterexample',
    '禁止清单': 'prohibition', '替代方式': 'alternative', '关联板块': 'dependency',
    '关联路径': 'dependency', '调用标签': 'tag', '优先级': 'priority', '分级标准': 'grade',
    '场景变体': 'variation', '映射表': 'mapping', '补充说明': 'note',
}
_PROFILE_FIELDS = {
    '核心元素': 'profile_element', '读者期待': 'reader_expectation', '风格约束': 'style_constraint',
    '篇幅适配': 'length_guidance', '风险点': 'risk', '类型画像补全': 'upgrade',
}
_FIELD = re.compile(r'^\s*(?:[【\[（(]([^】\]）)》\n]{1,25})[】\]）)》]|\*\*([^*\n]{1,25})\*\*[:：])')
_FENCE = re.compile(r'^\s*(?:```|~~~)')
_EMBEDDED_NUMBER = re.compile(r'(?m)^-[ \t]*\*\*板块\*\*[:：][ \t]*(\d+\.\d+)[ \t]*\r?$')
_EMBEDDED_TITLE = re.compile(r'(?m)^#{1,6}[ \t]+([^\r\n]+)')
_NUMBERED_BOLD = re.compile(r'^\*\*(\d+\.\d+)[ _\t]+([^*\r\n]+)\*\*[ \t]*\r?$')
_EMBEDDED_KIND = re.compile(r'(?m)^-[ \t]*\*\*条目类型\*\*[^\r\n]*')
_HEADER = re.compile(r'^SOURCE:[^\r\n]*(?:\r\n|\r|\n)[ \t]*={3,}[ \t]*(?:\r\n|\r|\n)')
_PROFILE = re.compile(r'(?m)^#[ \t]+类型画像补全[ \t]*\r?$')
_PROFILE_ENTRY = re.compile(r'(?m)^##[ \t]+([^\r\n]+)')
_APPEND = re.compile(r'(?m)^#{2,4}[ \t]+(?:(?:类型系统|锚点网络)?原版条目补全)[ \t]*\r?$'
                     r'|^===== 缺失升级资料吸收开始 =====[ \t]*\r?$')
_APPEND_ITEM = re.compile(r'(?m)^#{3,5}[ \t]+([^\r\n]+)')
_UPGRADE_END = re.compile(r'(?m)^===== 缺失升级资料吸收结束 =====[ \t]*\r?$')
_JSON_SPACE = re.compile(r'[ \r\n\t]*')
_JSON = json.JSONDecoder()
_IDENTITY_FIELDS = (
    'id', 'entry_id', 'object_id', 'connection_id', 'dynamic_combination_id',
    'static_combination_id', 'combination_id', 'condition_id', 'effect_id', 'state_adaptation_id',
    'propagation_id', 'stable_id', 'rule_id', 'dynamic_rule_id', 'anchor_id',
    'adaptation_id', 'pattern_id', 'work_id', 'trigger_condition_id', 'candidate_effect_id',
    'example_id', 'validation_id', 'signature_id', 'source_record_id',
    'hybrid_id', 'mechanism_id', 'structure_id', 'style_id', 'tone_id', 'tag_id', 'type_id',
)
_SEMANTIC_FIELDS = {
    'definition': 'definition', 'description': 'definition', '定义': 'definition',
    'conditions': 'condition', 'condition': 'condition', 'preconditions': 'condition',
    'trigger_conditions': 'condition', 'trigger_condition': 'condition',
    'trigger_condition_ids': 'dependency', 'applicable_when': 'condition', '适用条件': 'condition',
    'effects': 'effect', 'effect': 'effect', 'candidate_effect_ids': 'dependency',
    'selection_constraints': 'constraint', 'continuity_constraints': 'constraint',
    'constraints': 'constraint', 'limitations': 'constraint', 'not_guaranteed': 'guarantee_boundary',
    'failure_branches': 'exception', 'alternative_branches': 'alternative',
    'exceptions': 'exception', 'forbidden_assumptions': 'prohibition',
    'source_ref': 'provenance', 'source_refs': 'provenance',
    'source': 'endpoint', 'target': 'endpoint', 'source_id': 'endpoint', 'target_id': 'endpoint',
    'valid_types': 'applicability', 'validation_rules': 'check', 'validation': 'check',
    'examples': 'example', 'counterexamples': 'counterexample',
    'scope': 'applicability', 'applicable_to': 'applicability', 'inclusions': 'constraint',
    'exclusions': 'prohibition', 'not_overrides': 'prohibition', 'forbidden_triggers': 'prohibition',
    'continuity_risks': 'constraint', 'compatibility_constraints': 'constraint',
    'conflict_constraints': 'constraint', 'conflicts_between_components': 'constraint',
    'propagation_limits': 'constraint', 'propagation_profile': 'constraint',
    'required_context': 'condition', 'required_information': 'condition', 'required_resources': 'condition',
    'required_capabilities': 'condition', 'required_relationships': 'condition',
    'required_identity_conditions': 'condition', 'required_moral_conditions': 'condition',
    'distinguishing_features': 'constraint', 'validation_requirements': 'check',
    'supported_uses': 'applicability', 'parameters': 'constraint',
    'preferred_expressions': 'instruction', 'alternative_expressions': 'alternative',
    'avoid_expressions': 'prohibition', 'combination_reason': 'definition', 'component_weights': 'constraint',
    'candidate_effects': 'effect', 'allowed_fields': 'constraint', 'preferred_changes': 'instruction',
    'forbidden_changes': 'prohibition', 'rule_scope': 'definition', 'required_conditions': 'condition',
    'verification_requirement': 'check', 'validation_rule': 'check',
    'trigger_concepts': 'condition', 'trigger_entities': 'condition', 'trigger_event_types': 'condition',
    'trigger_information_types': 'condition', 'trigger_resource_types': 'condition',
    'trigger_relationship_types': 'condition', 'trigger_foreshadowing_types': 'condition',
}


def _pointer(path: str, component: str) -> str:
    return path + '/' + component.replace('~', '~0').replace('/', '~1')


def _json_members(text: str, start: int, value: list | dict) -> Iterator[tuple[str, int, int, object]]:
    position = _JSON_SPACE.match(text, start + 1).end()
    if isinstance(value, list):
        for i, member in enumerate(value):
            _, end = _JSON.raw_decode(text, position)
            yield str(i), position, end, member
            position = _JSON_SPACE.match(text, _JSON_SPACE.match(text, end).end() + 1).end()
        return
    while text[position] != '}':
        key, key_end = _JSON.raw_decode(text, position)
        start = _JSON_SPACE.match(text, _JSON_SPACE.match(text, key_end).end() + 1).end()
        member, end = _JSON.raw_decode(text, start)
        yield key, start, end, member
        position = _JSON_SPACE.match(text, end).end()
        if text[position] == '}':
            break
        position = _JSON_SPACE.match(text, position + 1).end()


def _key(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    return next((value[k] for k in _IDENTITY_FIELDS if isinstance(value.get(k), str) and value[k]), None)


def _walk_json(text: str, value: object, start: int, end: int, path: str, label: str,
               key: str | None, *, record: bool = False) -> Iterator[Unit]:
    identity = _key(value)
    if not isinstance(value, (dict, list)):
        lookup = value if isinstance(value, str) and len(value) <= 160 else key
        yield Unit(start, end, 'json_value', lookup, label, path)
        return
    is_record = record or identity is not None
    if identity is not None:
        key = identity
    if is_record:
        mixed = isinstance(value, dict) and bool({'运行层升级', 'runtime_calling_layer'} & value.keys())
        yield Unit(start, end, 'record', key, label, path, 'mixed' if mixed else 'source')
    if not value:
        yield Unit(start, end, 'empty_collection', key, label, path)
        return
    member_names: set[str] = set()
    for name, left, right, member in _json_members(text, start, value):
        child = _pointer(path, name)
        if name in member_names:
            yield Unit(left, right, 'duplicate_member', key, name, child, 'residual')
        member_names.add(name)
        if name in {'运行层升级', 'runtime_calling_layer'}:
            yield Unit(left, right, 'upgrade', key, name, child, 'upgrade')
            continue
        semantic = _SEMANTIC_FIELDS.get(name)
        if semantic:
            yield Unit(left, right, semantic, key, name, child)
        if is_record and _key(member) is None:
            continue
        if isinstance(member, (dict, list)):
            if not semantic and isinstance(member, dict) and member and _key(member) is None and not isinstance(value, list):
                yield Unit(left, right, 'json_group', key, name, child)
            yield from _walk_json(text, member, left, right, child, name, key,
                                  record=isinstance(value, list) and isinstance(member, dict))
        elif not semantic:
            yield from _walk_json(text, member, left, right, child, name, key)


def _profiles(text: str, heading_end: int, end: int) -> Iterator[Unit]:
    headings = list(_PROFILE_ENTRY.finditer(text, heading_end, end))
    if not headings:
        yield Unit(heading_end, end, 'residual', '类型画像补全', '类型画像补全', 'profiles', 'residual')
    for n, heading in enumerate(headings):
        stop = headings[n+1].start() if n+1 < len(headings) else end
        key = heading[1].strip()
        locator = f'profiles/{n}'
        yield Unit(heading.start(), stop, 'type_profile', key, '类型画像补全', locator, 'supplement')
        for unit in _text_fields(text[heading.start():stop], key, _PROFILE_FIELDS):
            yield Unit(heading.start()+unit.start, heading.start()+unit.end, unit.kind, unit.key,
                       unit.label, f'{locator}/{unit.locator}', 'upgrade' if unit.kind == 'upgrade' else 'supplement')


def _supplement(text: str, start: int, label: str) -> Iterator[Unit]:
    position = _JSON_SPACE.match(text, start).end()
    heading = _APPEND.search(text, position)
    profiles = _PROFILE.search(text, position, heading.start() if heading else len(text))
    if profiles is not None:
        if text[position:profiles.start()].strip() not in {'', '---'}:
            yield Unit(position, profiles.start(), 'residual', label, label, 'before_profiles', 'residual')
        position = heading.start() if heading else len(text)
        yield from _profiles(text, profiles.end(), position)
    if heading is None:
        if position < len(text):
            yield Unit(position, len(text), 'residual', label, label, 'tail', 'residual')
        return
    if heading.start() > position:
        yield Unit(position, heading.start(), 'residual', label, label, 'tail', 'residual')
    if heading[0].startswith('#'):
        headings = list(_APPEND_ITEM.finditer(text, heading.end()))
        if not headings:
            yield Unit(heading.start(), len(text), 'residual', label, label, 'supplement', 'residual')
        for i, item in enumerate(headings):
            stop = headings[i+1].start() if i+1 < len(headings) else len(text)
            yield Unit(item.start(), stop, 'upgrade', item[1].strip(), label, f'supplement/{i}', 'upgrade')
        return
    while heading is not None:
        close = _UPGRADE_END.search(text, heading.end())
        if close is None:
            yield Unit(heading.start(), len(text), 'residual', label, label, 'unclosed_upgrade', 'residual')
            return
        yield Unit(heading.start(), close.end(), 'upgrade', label, label, f'append/{heading.start()}', 'upgrade')
        position = _JSON_SPACE.match(text, close.end()).end()
        heading = _APPEND.search(text, position)
        stop = heading.start() if heading else len(text)
        if position < stop:
            yield Unit(position, stop, 'residual', label, label, f'tail/{position}', 'residual')


def _source_block(text: str, label: str) -> Iterator[Unit]:
    header = _HEADER.match(text)
    if header is None:
        yield Unit(0, len(text), 'residual', label, label, 'header', 'residual')
        return
    start = _JSON_SPACE.match(text, header.end()).end()
    if not label.casefold().endswith(('.json', '.jsonl')):
        if start < len(text):
            yield Unit(start, len(text), 'attachment', label, label, 'attachment')
        return
    if label.casefold().endswith('.jsonl'):
        position = start
        for n, line in enumerate(text[start:].splitlines(keepends=True)):
            if line.strip():
                left = _JSON_SPACE.match(text, position).end()
                try:
                    value, end = _JSON.raw_decode(text, left)
                    if end > position + len(line) or text[end:position+len(line)].strip():
                        raise ValueError('Invalid JSON line')
                except (ValueError, RecursionError):
                    yield Unit(left, position+len(line), 'invalid_json', label, label, f'line/{n}', 'residual')
                else:
                    yield from _walk_json(text, value, left, end, f'/lines/{n}', label, label,
                                          record=isinstance(value, dict))
            position += len(line)
        return
    try:
        value, end = _JSON.raw_decode(text, start)
    except (ValueError, RecursionError):
        yield Unit(start if start < len(text) else 0, len(text), 'invalid_json', label, label, 'json', 'residual')
        return
    yield Unit(start, end, 'json_document', label, label, '', 'container')
    yield from _walk_json(text, value, start, end, '', label, label)
    yield from _supplement(text, end, label)


def chapter_checklist(text: str) -> list[Unit]:
    """Read the original chapter editing checklist with its item spans."""
    heading = text.partition('\n')[0].rstrip('\r')
    match = _NUMBERED_BOLD.fullmatch(heading)
    if not match or match[1] != '162.2' or match[2] != '审美检查清单':
        return []
    lead = re.search(r'(?m)^每章编辑模式检查[：:]', text)
    if lead is None:
        return []
    key = '162.2_审美检查清单'
    fields = [Unit(lead.start(), lead.end(), 'condition', key, '每章编辑模式检查', 'chapter_checklist/condition')]
    position = lead.end()
    for raw in text[position:].splitlines(keepends=True):
        if raw.strip():
            item = re.fullmatch(r'-[ \t]+\[ \][ \t]+(\S[^\r\n]*)', raw.rstrip('\r\n'))
            if item is None:
                break
            fields.append(Unit(position+item.start(1), position+item.end(1), 'check', key,
                               '检查项', f'chapter_checklist/{len(fields)}'))
        elif len(fields) > 1:
            break
        position += len(raw)
    return fields if len(fields) > 1 else []


def _text_fields(text: str, key: str | None, labels: dict[str, str]) -> Iterator[Unit]:
    fields = []
    position = 0
    inside_fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            inside_fence = not inside_fence
        elif not inside_fence and (m := _FIELD.match(line)):
            label = (m[1] or m[2]).strip()
            if label in labels:
                fields.append((position, label))
        position += len(line)
    for i, (start, label) in enumerate(fields):
        stop = fields[i+1][0] if i+1 < len(fields) else len(text)
        yield Unit(start, stop, labels[label], key, label, f'field/{i}')
    if key == '162.2_审美检查清单':
        yield from chapter_checklist(text)


def _anchor_fields(text: str, key: str | None) -> Iterator[Unit]:
    first_line = text.splitlines()[0]
    if not first_line.startswith('|'):
        marker = re.search(r'(?m)^【运行层升级】', text)
        if marker:
            yield Unit(marker.start(), len(text), 'upgrade', key, '运行层升级', 'anchor_upgrade', 'upgrade')
        return
    bars = [m.start() for m in re.finditer(r'(?<!\\)\|', first_line)]
    if len(bars) != 6:
        yield Unit(0, len(first_line), 'residual', key, '锚点列数', 'anchor_table', 'residual')
        return
    for i, (kind, label) in enumerate((('identity','编号'),('definition','锚点名称'),
                                       ('definition','具体内容'),('condition','触发条件'),('tag','类别'))):
        yield Unit(bars[i]+1, bars[i+1], kind, key, label, f'cell/{i}')
    suffix = first_line[bars[-1]+1:]
    if '<summary>运行层升级</summary>' in suffix:
        yield Unit(bars[-1]+1, len(first_line), 'upgrade', key, '运行层升级', 'anchor_inline', 'upgrade')
    elif suffix.strip():
        yield Unit(bars[-1]+1, len(first_line), 'residual', key, '锚点附记', 'anchor_inline', 'residual')


def _embedded_entries(text: str, parent: str | None) -> Iterator[Unit]:
    markers = []
    excluded, position, fenced = [], 0, False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            fenced = not fenced
        if fenced or _FENCE.match(line):
            excluded.append((position, position + len(line)))
        position += len(line)
    previous = 0
    for match in _EMBEDDED_NUMBER.finditer(text):
        if any(start <= match.start() < end for start, end in excluded):
            continue
        number = match[1]
        if parent and parent.split('_')[0] == number:
            continue
        titles = list(_EMBEDDED_TITLE.finditer(text, previous, match.start()))
        kinds = list(_EMBEDDED_KIND.finditer(text, previous, match.start()))
        start = kinds[-1].start() if kinds else match.start()
        if titles and not text[titles[-1].end():start].strip():
            start = titles[-1].start()
        markers.append((start, number))
        previous = match.end()
    for index, (start, number) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        body = text[start:end]
        heading = _EMBEDDED_TITLE.match(body)
        tag = re.search(r'\*\*调用标签\*\*[:：][ \t]*#([^\r\n]+)', body)
        title = heading[1].strip() if heading else tag[1].split('·')[-1].strip() if tag else number
        key = f'{number}_{title}'
        locator = f'embedded/{number}/{index}'
        yield Unit(start, end, 'embedded_entry', key, title, locator)
        for field in _text_fields(body, key, _LIBRARY_FIELDS):
            yield Unit(start + field.start, start + field.end, field.kind, key, field.label,
                       f'{locator}/{field.locator}', field.origin)


def _section_entries(text: str, parent: str | None) -> Iterator[Unit]:
    markers, position, fenced, appended = [], 0, False, False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            heading, numbered = _EMBEDDED_TITLE.match(line), _NUMBERED_BOLD.match(line)
            if heading or numbered:
                title = heading[1].strip() if heading else numbered[2].strip()
                appended = appended or '原版条目补全' in title or '运行层升级' in title
                prologue = text[position + len(line):].lstrip()
                metadata = prologue.startswith(('- **条目类型**', '- **板块**'))
                key = f'{numbered[1]}_{title}' if numbered else f'{parent}#{title}'
                emit = bool(position and not appended and not metadata)
                markers.append((position, key, title, bool(numbered), emit))
        position += len(line)
    for index, (start, key, title, numbered, emit) in enumerate(markers):
        if not emit:
            continue
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        locator = f'section/{start}'
        yield Unit(start, end, 'embedded_entry' if numbered else 'embedded_block', key, title, locator)
        for field in _text_fields(text[start:end], key, _LIBRARY_FIELDS):
            yield Unit(start + field.start, start + field.end, field.kind, key, field.label,
                       f'{locator}/{field.locator}', field.origin)


def _whole_number_sections(text: str) -> Iterator[Unit]:
    headings,position,fenced = [],0,False
    pattern = re.compile(r'^#{2,6}[ \t]+(\d+_[^\r\n]+)')
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced and (match := pattern.match(line)):
            headings.append((position,match[1].strip()))
        position += len(line)
    for index,(left,owner_key) in enumerate(headings):
        right = headings[index+1][0] if index+1<len(headings) else len(text)
        marker = re.search(r'(?m)^【运行层升级】',text[left:right])
        if marker:
            right=left+marker.start()
        locator=f'tail/{left}'
        yield Unit(left,right,'embedded_block',owner_key,owner_key,locator)
        for field in _text_fields(text[left:right],owner_key,_LIBRARY_FIELDS):
            yield Unit(left+field.start,left+field.end,field.kind,owner_key,field.label,
                       f'{locator}/{field.locator}',field.origin)


def units_for_fragment(text: str, kind: str, key: str | None) -> Iterator[Unit]:
    if kind == 'source_block':
        yield from _source_block(text, key or '')
    elif kind == 'support_json':
        start = _JSON_SPACE.match(text, int(text.startswith('\ufeff'))).end()
        value, end = _JSON.raw_decode(text, start)
        yield from _walk_json(text, value, start, end, '', 'provenance', key)
    elif kind in ('library_block', 'library_entry'):
        yield from _text_fields(text, key, _LIBRARY_FIELDS)
        yield from _embedded_entries(text, key)
        yield from _section_entries(text, key)
        yield from _whole_number_sections(text)
    elif kind == 'anchor':
        yield from _anchor_fields(text, key)
    elif kind == 'network_edge':
        value = _JSON.decode(text)
        for label, start, end, _ in _json_members(text, 0, value):
            if label == '运行层升级':
                yield Unit(start, end, 'upgrade', key, label, _pointer('', label), 'upgrade')
            elif label in _SEMANTIC_FIELDS:
                yield Unit(start, end, _SEMANTIC_FIELDS[label], key, label, _pointer('', label))
    elif kind in ('library_upgrade', 'anchor_upgrade', 'network_upgrade'):
        yield Unit(0, len(text), 'upgrade', key, '运行层升级', kind, 'upgrade')
        if kind == 'library_upgrade':
            yield from _whole_number_sections(text)
    elif kind in ('network_residual', 'unclassified'):
        yield Unit(0, len(text), 'residual', key, '未识别原文', kind, 'residual')
