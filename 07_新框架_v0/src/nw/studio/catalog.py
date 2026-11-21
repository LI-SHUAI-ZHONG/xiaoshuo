"""Read-only presentation catalogue extracted from the existing step materials.

These are choices, never corpus recommendations. Source IDs and missing values
are preserved; presentation groups do not invent new type IDs or definitions.
"""
from __future__ import annotations

import ast
import colorsys
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

STEPS = Path(__file__).resolve().parents[1] / 'materials' / 'steps'
SLOTS = ('genre', 'tone', 'style', 'narration', 'world', 'character', 'structure', 'hook')
SLOT_LABELS = dict(zip(SLOTS, ('类型', '风格', '文笔', '写法', '世界观', '人物', '结构篇幅', '卖点')))
SLOT_STAGES = {
    'genre': ['type_selection', 'type_adaptation'],
    'tone': ['expression_design'], 'style': ['expression_design'],
    'narration': ['scene_design', 'expression_design'], 'world': ['world_design'],
    'character': ['character_design'], 'structure': ['plot_design', 'scene_design'],
    'hook': ['plot_design', 'event_design'],
}


@lru_cache(maxsize=256)
def material(filename: str) -> str:
    tree = ast.parse((STEPS / filename).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MATERIAL' for t in node.targets):
            if (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr == 'strip' and not node.value.args and not node.value.keywords):
                return ast.literal_eval(node.value.func.value).strip()
            return ast.literal_eval(node.value)
    return ''


def _rows(filename: str) -> list[dict]:
    result = []
    for line in material(filename).splitlines():
        match = re.match(r'^\s*(\d+)\s*\|\s*([A-Z][A-Z_0-9]+)\s*\|\s*(.+)$', line)
        if not match:
            continue
        fields = [p.strip() for p in match[3].split('|')]
        name = fields[0] if len(fields) > 1 else fields[0].split('：', 1)[0]
        definition = fields[1] if len(fields) > 1 else fields[0]
        result.append({'id': match[2], 'name': name, 'definition': definition,
                       'source_ref': {'file': filename, 'original_line': int(match[1])}})
    return result


@lru_cache(maxsize=1)
def _genres() -> list[dict]:
    parents = _rows('type_selection_genres.py') + _rows('type_selection_genres_continued.py')
    mapping = {row['id']: row for row in parents}
    for i, row in enumerate(parents):
        rgb = colorsys.hls_to_rgb((i * 137.508 % 360) / 360, .48, .48)
        color = '#' + ''.join(f'{round(channel * 255):02x}' for channel in rgb)
        row.update(children=[], color=color, channel=None)
    for path in sorted(STEPS.glob('type_selection_*_subgenres.py')):
        if path.name == 'type_selection_main_and_subgenres.py':
            continue
        parent = re.search(r'parent_id="([A-Z_]+)"', material(path.name))
        if parent and parent[1] in mapping:
            for child in _rows(path.name):
                child['parent_id'] = parent[1]
                mapping[parent[1]]['children'].append(child)
    return parents


def genres() -> list[dict]:
    return deepcopy(_genres())


def type_map() -> dict[str, dict]:
    return {r['id']: r for p in _genres() for r in [p, *p['children']]}


def single_genre_path(values: list[str]) -> bool:
    """One main genre, optionally narrowed to one of its subgenres."""
    if not isinstance(values, list) or len(values) not in (1, 2) or not all(isinstance(v, str) for v in values):
        return False
    mapping = type_map()
    main = mapping.get(values[0])
    if not main or main.get('parent_id'):
        return False
    return len(values) == 1 or mapping.get(values[1], {}).get('parent_id') == values[0]


def matches_single_genre(config: dict, chosen: list[str]) -> bool:
    if not isinstance(config, dict) or config.get('genre_ids') != chosen:
        return False
    for field, slot in (('mechanism_ids', 'hook'), ('structure_ids', 'structure'),
                        ('style_ids', 'style'), ('tone_ids', 'tone')):
        items = config.get(field)
        if not isinstance(items, list):
            return False
        if items:
            known = {r['id'] for r in option_map(slot).values() if r.get('selectable', True)}
            if any(not isinstance(ident, str) or ident not in known for ident in items):
                return False
    return True


def canonical_types(values: list[str]) -> list[str]:
    if not isinstance(values, list) or len(values) > 8 or any(not isinstance(v, str) for v in values):
        raise ValueError('类型必须是最多 8 个 ID 的列表')
    mapping = type_map()
    result: list[str] = []
    for value in values:
        ident = value.removeprefix('genre.')
        if ident not in mapping:
            raise ValueError(f'未知类型: {ident}')
        parent = mapping[ident].get('parent_id')
        for item in ([parent, ident] if parent else [ident]):
            if item not in result:
                result.append(item)
    return result


def _typed(slot: str, filename: str) -> list[dict]:
    return [{'key': f'{slot}.{r["id"]}', **r, 'description': r['definition'],
             'children': [], 'stages': SLOT_STAGES[slot]} for r in _rows(filename)]


def _sections(slot: str, filename: str, sections: set[str] | None = None) -> list[dict]:
    text = material(filename)
    matches = list(re.finditer(r'^### ([\d.]+)_([^\r\n]+)', text, re.M))
    result = []
    for i, match in enumerate(matches):
        if sections and match[1].split('.')[0] not in sections:
            continue
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        definition = re.search(r'(?:【定义】|\*\*定义\*\*：)\s*([^\n]+)', body)
        desc = definition[1].replace('\\', '').strip() if definition else ''
        result.append({'key': f'{slot}.{match[1]}', 'id': match[1], 'name': match[2].replace('_', '·'),
                       'description': desc, 'definition': desc, 'children': [],
                       'source_ref': {'file': filename, 'section': match[1]},
                       'stages': SLOT_STAGES[slot], 'source_excerpt': body[:1800]})
    return result


def _group(slot: str, key: str, name: str, children: list[dict]) -> dict:
    parent = f'{slot}.group.{key}'
    for child in children:
        child['parent'] = parent
    return {'key': parent, 'id': parent, 'name': name, 'description': '',
            'selectable': False, 'children': children, 'parent': None}


@lru_cache(maxsize=8)
def _options(slot: str) -> list[dict]:
    if slot not in SLOTS:
        raise ValueError('未知板块')
    if slot == 'genre':
        return [{'key': f'genre.{p["id"]}', **p, 'description': p['definition'], 'children': [
            {'key': f'genre.{c["id"]}', **c, 'description': c['definition'], 'children': []}
            for c in p['children']]} for p in _genres()]
    typed = {'tone': ('expression_design_type_tones.py', '语气与情绪'),
             'style': ('expression_design_type_styles.py', '文风与语言质感'),
             'structure': ('plot_design_narrative_structures.py', '叙事结构'),
             'hook': ('plot_design_plot_mechanisms.py', '情节推进机制')}
    result = []
    if slot in typed:
        filename, label = typed[slot]
        result.append(_group(slot, 'types', label, _typed(slot, filename)))
    section_sources = {
        'narration': [('expression_design_narrator.py', '叙述声音与距离', None),
                      ('scene_design_narrator.py', '视角与信息边界', None),
                      ('expression_design_timeline.py', '叙述时序、速度与回忆', None),
                      ('expression_design_disclosure.py', '信息如何透露', None)],
        'world': [('world_design_setting.py', '世界设定', None), ('world_design.py', '力量与资源规则', {'9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19'})],
        'character': [('character_design.py', '人物与动机', {'1', '2', '3', '4'}),
                      ('character_design_supporting.py', '配角配置', None)],
        'structure': [('plot_design_structure.py', '结构与节奏', {'41', '42', '43', '44'})],
        'hook': [('plot_design_reader_engagement.py', '读者承诺与钩子', None)],
    }
    seen: set[str] = set()
    for filename, label, sections in section_sources.get(slot, []):
        children = []
        for row in _sections(slot, filename, sections):
            if row['key'] not in seen:
                children.append(row)
                seen.add(row['key'])
        if children:
            result.append(_group(slot, filename.removesuffix('.py'), label, children))
    return result


def options(slot: str, parent: str = '') -> list[dict]:
    rows = _options(slot)
    if parent:
        found = option_map(slot).get(parent)
        if found is None:
            raise ValueError('未知选项分组')
        rows = found['children']
    return deepcopy(rows)


def option_map(slot: str | None = None) -> dict[str, dict]:
    result = {}
    def visit(rows: list[dict]) -> None:
        for row in rows:
            result[row['key']] = row
            visit(row.get('children', []))
    for current in ([slot] if slot else SLOTS):
        visit(_options(current))
    return result


@lru_cache(maxsize=1)
def combinations() -> list[dict[str, Any]]:
    """Keep source status: blocked combinations are warnings, not approvals."""
    result = []
    for path in sorted(STEPS.glob('type_adaptation_type_combinations*.py')):
        common: dict = {}
        for line in material(path.name).splitlines():
            if line.startswith('【各条共用原文值】{'):
                common = json.loads(line.split('】', 1)[1])
            match = re.match(r'^(\d+)｜([^｜]+)｜(\{.*\})$', line)
            if not match:
                continue
            data = {**common, **json.loads(match[3])}
            types = list(dict.fromkeys(data.get('type_ids', []) + data.get('subtype_ids', [])))
            result.append({'id': data.get('combination_id'), 'name': data.get('combination_name'),
                           'types': types, 'primary_type_id': data.get('primary_type_id'),
                           'status': match[2], 'description': data.get('description', ''),
                           'source_ref': {'file': path.name, 'original_line': int(match[1])}})
    return result
