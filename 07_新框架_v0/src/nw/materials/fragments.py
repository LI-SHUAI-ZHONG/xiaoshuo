"""Locate original material fragments without rewriting the source bytes."""
from dataclasses import dataclass
import json
import re
from typing import Iterator


FAMILIES = frozenset({
    'library', 'types', 'type_links', 'static', 'dynamic', 'anchors',
    'provenance', 'execution', 'routing', 'support',
})
_LIB_ENTRY = re.compile(r'^#{2,5}\s+(\d+\.\d+[^\n]*)$')
_LIB_BLOCK = re.compile(r'^#{2,5}\s+(板块\d+\b.*)$')
_UPGRADE = re.compile(r'^(?:#{1,6}\s+.*运行层升级|【运行层升级】)')
_SOURCE = re.compile(r'^SOURCE:\s*(\S.*)$')
_ANCHOR = re.compile(r'^(?:\|\s*|#{2,6}\s+)([A-Z]{1,2}\d+(?:\.\d+)*)(?=\s|\||$)')
_SECTION = re.compile(r'^#{2,6}\s+(.+)$')
_SUPPORT_SECTION = re.compile(r'^#{1,6}\s+(.+)$')
_LINE_BREAK = re.compile(rb'[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$')
_JSON_FENCE = re.compile(r'^```json[ \t]*\r?$', re.MULTILINE)
_JSON_CLOSE = re.compile(r'[ \t\r\n]*```[ \t]*(?=\r?\n|$)')
_NETWORK_UPGRADE = re.compile(r'(?m)^===== 缺失升级资料吸收开始 =====[ \t]*\r?$')
_NETWORK_UPGRADE_END = re.compile(r'(?m)^===== 缺失升级资料吸收结束 =====[ \t]*\r?$')
_DECODER = json.JSONDecoder()


@dataclass(frozen=True)
class Fragment:
    start: int
    end: int
    kind: str
    key: str | None = None


def _markers(data: bytes, family: str) -> Iterator[tuple[int, str, str]]:
    library_key = ''
    for line in _LINE_BREAK.finditer(data):
        start = line.start()
        text = line[0].decode('utf-8-sig' if start == 0 else 'utf-8').rstrip('\r\n')
        if family == 'library':
            if match := _LIB_ENTRY.match(text):
                library_key = match[1].strip()
                yield start, 'library_entry', library_key
            elif _UPGRADE.match(text):
                yield start, 'library_upgrade', library_key
            elif match := _LIB_BLOCK.match(text):
                library_key = match[1].strip()
                yield start, 'library_block', library_key
        elif family in ('types', 'type_links', 'routing'):
            if match := _SOURCE.match(text):
                yield start, 'source_block', match[1].strip()
        elif family == 'anchors':
            if match := _ANCHOR.match(text):
                first_cell = text.split('|', 2)[1] if text.startswith('|') else text
                kind = 'anchor_upgrade' if '运行层升级' in first_cell else 'anchor'
                yield start, kind, match[1]
            elif match := _SECTION.match(text):
                yield start, 'anchor_section', match[1]
        elif family == 'execution' and (match := _SECTION.match(text)):
            yield start, 'execution_section', match[1]
        elif family == 'support' and (match := _SUPPORT_SECTION.match(text)):
            yield start, 'support_section', match[1]


def _partition(data: bytes, markers: Iterator[tuple[int, str, str]]) -> list[Fragment]:
    first = next(markers, None)
    if first is None:
        return [Fragment(0, len(data), 'unclassified')]
    start, kind, key = first
    result = [Fragment(0, start, 'metadata')] if start else []
    for end, next_kind, next_key in markers:
        result.append(Fragment(start, end, kind, key))
        start, kind, key = end, next_kind, next_key
    result.append(Fragment(start, len(data), kind, key))
    return result


def _edge_array(root: object) -> tuple[tuple[str, ...], list]:
    if not isinstance(root, dict):
        raise ValueError('Expected a network object')
    prefix = ()
    if '动态网络连接_完整版' in root:
        prefix = ('动态网络连接_完整版',)
        root = root['动态网络连接_完整版']
    elif len(root) == 1 and isinstance(next(iter(root.values())), dict):
        prefix = (next(iter(root)),)
        root = next(iter(root.values()))
    if not isinstance(root, dict):
        raise ValueError('Expected a network object')
    for field in ('connections', '连接列表'):
        if isinstance(root.get(field), list):
            return (*prefix, field), root[field]
    raise ValueError('Network connection array is missing')


def _skip(text: str, position: int, chars: str = ' \r\n\t') -> int:
    while position < len(text) and text[position] in chars:
        position += 1
    return position


def _member_offset(text: str, start: int, member: str) -> int:
    position = start + 1
    while True:
        position = _skip(text, position, ' \r\n\t,')
        if position >= len(text) or text[position] == '}':
            raise ValueError(f'Cannot locate network field {member}')
        key, end = _DECODER.raw_decode(text, position)
        value_start = _skip(text, _skip(text, end) + 1)
        if key == member:
            return value_start
        _, position = _DECODER.raw_decode(text, value_start)


def _network_root(text: str) -> tuple[int, int, object]:
    start = _skip(text, 0)
    fence = None if text[start:start+1] == '{' else _JSON_FENCE.search(text)
    if fence is not None:
        start = _skip(text, fence.end())
    root, end = _DECODER.raw_decode(text, start)
    if fence is not None:
        close = _JSON_CLOSE.match(text, end)
        if close is None:
            raise ValueError('Unclosed historical JSON fence')
        end = close.end()
    return start, end, root


def _network_suffix(text: str, start: int) -> Iterator[tuple[int, int, str]]:
    position = start
    while True:
        opening = _NETWORK_UPGRADE.search(text, position)
        if opening is None:
            if position < len(text):
                yield position, len(text), 'network_residual' if text[position:].strip() else 'metadata'
            return
        if opening.start() > position:
            kind = 'network_residual' if text[position:opening.start()].strip() else 'metadata'
            yield position, opening.start(), kind
        closing = _NETWORK_UPGRADE_END.search(text, opening.end())
        if closing is None:
            yield opening.start(), len(text), 'network_residual'
            return
        yield opening.start(), closing.end(), 'network_upgrade'
        position = closing.end()


def _network(data: bytes, text: str) -> list[Fragment]:
    position, root_end, root = _network_root(text)
    field_path, expected = _edge_array(root)
    for member in field_path:
        position = _member_offset(text, position, member)
    if text[position] != '[':
        raise ValueError('Cannot locate connection array in original bytes')
    position += 1
    byte_position = (3 if data.startswith(b'\xef\xbb\xbf') else 0) + len(text[:position].encode('utf-8'))
    fragments: list[Fragment] = []
    for expected_edge in expected:
        start = _skip(text, position, ' \t\r\n,')
        edge, end = _DECODER.raw_decode(text, start)
        if not isinstance(edge, dict) or edge != expected_edge:
            raise ValueError('Invalid network edge')
        byte_start = byte_position + len(text[position:start].encode('utf-8'))
        byte_end = byte_start + len(text[start:end].encode('utf-8'))
        preceding_end = fragments[-1].end if fragments else 0
        if preceding_end < byte_start:
            fragments.append(Fragment(preceding_end, byte_start, 'metadata'))
        key = edge.get('id') or edge.get('connection_id')
        if not key:
            key = ' / '.join(str(edge.get(k, '')) for k in ('source', 'target', 'type'))
        fragments.append(Fragment(byte_start, byte_end, 'network_edge', str(key)))
        position, byte_position = end, byte_end
    root_end_byte = byte_position + len(text[position:root_end].encode('utf-8'))
    previous_end = fragments[-1].end if fragments else 0
    if previous_end < root_end_byte:
        fragments.append(Fragment(previous_end, root_end_byte, 'metadata'))
    byte_position = root_end_byte
    for start, end, kind in _network_suffix(text, root_end):
        next_byte = byte_position + len(text[start:end].encode('utf-8'))
        fragments.append(Fragment(byte_position, next_byte, kind))
        byte_position = next_byte
    return fragments


def parse_fragments(data: bytes, family: str) -> tuple[str, list[Fragment]]:
    if b'\0' in data:
        return 'NUL', [Fragment(0, len(data), 'quarantined')]
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return 'INVALID_ENCODING', [Fragment(0, len(data), 'quarantined')]
    if not text.strip():
        return 'EMPTY', [Fragment(0, len(data), 'quarantined')]
    if family == 'support' and text.lstrip().startswith(('{', '[')):
        try:
            json.loads(text)
        except (ValueError, RecursionError):
            return 'INVALID_JSON', [Fragment(0, len(data), 'quarantined')]
        return 'INDEXED', [Fragment(0, len(data), 'support_json')]
    if family in ('static', 'dynamic', 'provenance'):
        try:
            if family == 'provenance':
                json.loads(text)
                return 'INDEXED', [Fragment(0, len(data), 'provenance')]
            fragments = _network(data, text)
            status = 'PARTIAL' if any(f.kind == 'network_residual' for f in fragments) else 'INDEXED'
            return status, fragments
        except (ValueError, RecursionError):
            return 'INVALID_JSON', [Fragment(0, len(data), 'quarantined')]
    fragments = _partition(data, _markers(data, family))
    if family == 'support' and fragments[0].kind == 'unclassified':
        return 'INDEXED', [Fragment(0, len(data), 'support_document')]
    return ('PARTIAL' if fragments[0].kind == 'unclassified' else 'INDEXED'), fragments
