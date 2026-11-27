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
SLOTS = ('genre', 'world', 'character', 'structure', 'hook', 'narration', 'tone', 'style')
SLOT_LABELS = {
    'genre': '类型',
    'world': '世界观',
    'character': '人物',
    'structure': '结构篇幅',
    'hook': '卖点',
    'narration': '写法',
    'tone': '风格',
    'style': '文笔',
}
SLOT_STAGES = {
    'genre': ['type_selection', 'type_adaptation'],
    'world': ['world_design'],
    'character': ['character_design'],
    'structure': ['plot_design', 'scene_design'],
    'hook': ['plot_design', 'event_design'],
    'narration': ['scene_design', 'expression_design'],
    'tone': ['expression_design'],
    'style': ['expression_design'],
}


def wizard_selection_limits() -> dict[str, int]:
    from nw.materials.steps.type_connections import material_document

    limits = material_document('类型组合约束.json')
    return {
        'genre': limits['max_genre_combination'],
        'tone': limits['max_tones_per_project'],
        'style': limits['max_styles_per_project'],
        'narration': 30,
        'world': 30,
        'character': 30,
        'structure': limits['max_structures_per_project'],
        'hook': limits['max_mechanisms_per_project'],
    }


def _eval_string_node(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'strip' and not node.args and not node.keywords):
        return _eval_string_node(node.func.value).strip()
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _eval_string_node(node.left) + _eval_string_node(node.right)
    return str(ast.literal_eval(node))


@lru_cache(maxsize=256)
def material(filename: str) -> str:
    tree = ast.parse((STEPS / filename).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MATERIAL' for t in node.targets):
            return _eval_string_node(node.value)
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
        row = {'id': match[2], 'name': name, 'definition': definition,
               'source_ref': {'file': filename, 'original_line': int(match[1])}}
        if len(fields) > 2:
            row['step_use'] = ' | '.join(fields[2:])
        result.append(row)
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


def _typed(slot: str, filename: str, *, stages: list[str] | None = None,
           include_ids: set[str] | None = None, key_prefix: str = '') -> list[dict]:
    result = []
    for r in _rows(filename):
        if include_ids is not None and r['id'] not in include_ids:
            continue
        ident = f'{key_prefix}{r["id"]}'
        result.append({
            'key': f'{slot}.{ident}', **r, 'id': ident, 'description': r['definition'],
            'children': [], 'stages': list(stages or SLOT_STAGES[slot]),
        })
    return result


def _sections(slot: str, filename: str, sections: set[str] | None = None, *,
              stages: list[str] | None = None, key_prefix: str = '',
              exclude_ids: set[str] | None = None) -> list[dict]:
    text = material(filename)
    matches = list(re.finditer(r'^### ([\d.]+)_([^\r\n]+)', text, re.M))
    result = []
    for i, match in enumerate(matches):
        if sections and match[1].split('.')[0] not in sections:
            continue
        if exclude_ids and match[1] in exclude_ids:
            continue
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        definition = re.search(r'(?:【定义】|\*\*定义\*\*：)\s*([^\n]+)', body)
        use = re.search(r'【本步用法】\s*(.*?)(?=\n【|\Z)', body, re.S)
        desc = definition[1].replace('\\', '').strip() if definition else ''
        if not desc and use:
            desc = use[1].strip().splitlines()[0]
        ident = f'{key_prefix}{match[1]}'
        row = {'key': f'{slot}.{ident}', 'id': ident, 'name': match[2].replace('_', '·'),
               'description': desc, 'definition': desc, 'children': [],
               'source_ref': {'file': filename, 'section': match[1]},
               'stages': list(stages or SLOT_STAGES[slot]), 'source_excerpt': body[:1800]}
        if use:
            row['step_use'] = use[1].strip()
        result.append(row)
    return result


def _blocks(slot: str, filename: str, *, stages: list[str] | None = None,
            key_prefix: str = '') -> list[dict]:
    text = material(filename)
    matches = list(re.finditer(r'^### (板块(\d+)\s+([^\r\n]+))', text, re.M))
    result = []
    for i, match in enumerate(matches):
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        block_no = match[2]
        raw_title = match[3].strip()
        if '#' in raw_title:
            parent_title, sub_title = [p.strip() for p in raw_title.split('#', 1)]
            display_name = f'{parent_title}·{sub_title}'
            ident = f'{key_prefix}block.{block_no}.{sub_title}'
        else:
            display_name = raw_title
            ident = f'{key_prefix}block.{block_no}'
        definition = re.search(r'(?:【定义】|\*\*定义\*\*：)\s*([^\n]+)', body)
        use = re.search(r'【本步用法】\s*(.*?)(?=\n【|\Z)', body, re.S)
        desc = definition[1].replace('\\', '').strip() if definition else ''
        if not desc and use:
            desc = use[1].strip().splitlines()[0]
        row = {'key': f'{slot}.{ident}', 'id': ident, 'name': display_name,
               'description': desc, 'definition': desc, 'children': [],
               'source_ref': {'file': filename, 'section': match[1]},
               'stages': list(stages or SLOT_STAGES[slot]), 'source_excerpt': body[:1800]}
        if use:
            row['step_use'] = use[1].strip()
        result.append(row)
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
    result = []
    if slot == 'world':
        world_groups = [
            ('foundation', '世界基础、形态与底层前提', [
                ('sections', 'world_design_setting.py', {'31', '34', '35', '123'}),
                ('sections', 'world_design_resources.py', {'124'}),
            ]),
            ('institution', '社会阶层、权力、职业与制度', [
                ('sections', 'world_design_setting.py', {'33', '39'}),
            ]),
            ('history', '时代分期、历史演化与未写明史实', [
                ('sections', 'world_design_setting.py', {'32'}),
            ]),
            ('resource_market', '资源库、货币汇率与交易市场', [
                ('sections', 'world_design_resources.py', {'125'}),
                ('sections', 'world_design_ecology.py', {'24', '25', '26', '27'}),
            ]),
            ('items_props', '道具功能边界、代价与制造工艺', [
                ('sections', 'world_design_ecology.py', {'28', '29', '30'}),
                ('sections', 'world_design_setting.py', {'40'}),
            ]),
            ('ecology_space', '生态格局、势力张力与空间时间性', [
                ('sections', 'world_design_ecology.py', {'20', '21', '22', '23'}),
                ('sections', 'world_design_space.py', {'115'}),
            ]),
            ('race_construct', '种族差异与生命构造边界', [
                ('sections', 'world_design_setting.py', {'36', '37', '38'}),
            ]),
            ('power_energy', '力量体系、能量三态转化与突破代价', [
                ('sections', 'world_design.py', {'9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19'}),
            ]),
            ('special_mechanism', '特殊世界运行机制', [
                ('typed', 'world_design_plot_mechanisms.py', None),
            ]),
        ]
        seen_world: set[str] = set()
        for group_key, label, specs in world_groups:
            children = []
            for kind, filename, sections in specs:
                rows = _typed(slot, filename) if kind == 'typed' else _sections(slot, filename, sections)
                for row in rows:
                    if row['key'] not in seen_world:
                        children.append(row)
                        seen_world.add(row['key'])
            if children:
                result.append(_group(slot, group_key, label, children))
        return result
    if slot == 'character':
        char_groups = [
            ('core_drive', '核心定位、属性、欲望执念与弧光', ['character_design'], [
                ('sections', 'character_design.py', {'1', '2', '3', '4'}, None, ''),
            ]),
            ('supporting_cast', '配角层级、反派逻辑、人格外化与背景身份', ['character_design'], [
                ('sections', 'character_design_supporting.py', None, {'126.12'}, ''),
                ('blocks', 'character_design_supporting.py', None, None, ''),
                ('typed', 'character_design_plot_mechanisms.py', {'PLOT_MECHANISM_TEAM'}, None, ''),
            ]),
            ('cognition_ethics', '认知偏差、心智模型、意志与道德立场', ['character_design'], [
                ('blocks', 'character_design_cognition.py', None, None, ''),
                ('blocks', 'character_design_ethics.py', None, None, ''),
            ]),
            ('status_profession', '初始状态、职业定位与技能边界', ['character_design'], [
                ('sections', 'character_design.py', {'8', '39', '40'}, None, ''),
            ]),
            ('fate_attitude', '命运态度（抗争/接受/逃避/利用/超越）', ['character_design'], [
                ('blocks', 'character_design_fate.py', None, None, ''),
            ]),
            ('supernatural_ability', '超凡能量、种族构造与血脉/天赋/基因机制', ['character_design'], [
                ('sections', 'character_design.py', {'10', '12', '13', '36', '37', '38'}, None, ''),
                ('typed', 'character_design_plot_mechanisms.py',
                 {'PLOT_MECHANISM_BLOODLINE', 'PLOT_MECHANISM_TALENT', 'PLOT_MECHANISM_INVINCIBLE', 'PLOT_MECHANISM_GENE'}, None, ''),
            ]),
            ('relation_network', '亲缘/社会/情感关系网与配角独立互动', ['static_relations'], [
                ('sections', 'static_relations.py', {'1', '5', '8'}, {'5.6', '5.7', '5.8', '5.9', '5.10', '5.11'}, 'rel.'),
                ('blocks', 'static_relations.py', None, None, 'rel.'),
                ('sections', 'static_relations_supporting.py', None, None, 'rel.'),
            ]),
            ('relation_tension', '不对称权力/信息、情感债务、光谱与对立错位', ['static_relations'], [
                ('sections', 'static_relations.py', {'5'}, {'5.1', '5.2', '5.3'}, 'rel.'),
                ('sections', 'static_relations_misalignment.py', None, None, 'rel.'),
                ('blocks', 'static_relations_supporting.py', None, None, 'rel.'),
            ]),
            ('faction_hierarchy', '势力互动、阶层权力、资源依赖与空间权限', ['static_relations'], [
                ('sections', 'static_relations.py', {'20', '22', '27', '33', '39'}, None, 'rel.'),
                ('sections', 'static_relations_space.py', {'115'}, None, 'rel.'),
            ]),
            ('racial_relation', '种族社会嵌入与种族间结构性张力', ['static_relations'], [
                ('sections', 'static_relations.py', {'36'}, None, 'rel.'),
            ]),
        ]
        seen_char: set[str] = set()
        for group_key, label, stages, specs in char_groups:
            children = []
            for kind, filename, selector, exclude_ids, prefix in specs:
                if kind == 'typed':
                    rows = _typed(slot, filename, stages=stages, include_ids=selector, key_prefix=prefix)
                elif kind == 'blocks':
                    rows = _blocks(slot, filename, stages=stages, key_prefix=prefix)
                else:
                    rows = _sections(slot, filename, selector, stages=stages, key_prefix=prefix, exclude_ids=exclude_ids)
                for row in rows:
                    if row['key'] not in seen_char:
                        children.append(row)
                        seen_char.add(row['key'])
            if children:
                result.append(_group(slot, group_key, label, children))
        return result
    if slot == 'structure':
        structure_groups = [
            ('types', '叙事结构与视角框架（15 类标准结构）', ['plot_design', 'scene_design'], [
                ('typed', 'plot_design_narrative_structures.py', None, None, ''),
            ]),
            ('plot_design_structure', '三幕/起承转合骨架、主支线、冲突类型与高潮余波', ['plot_design'], [
                ('sections', 'plot_design_structure.py', {'41', '42', '43', '44'}, None, ''),
                ('blocks', 'plot_design_structure.py', None, None, ''),
            ]),
            ('opening_ending', '开篇承诺、终章收束、首尾呼应与连续性底线', ['plot_design'], [
                ('sections', 'plot_design_opening_ending.py', None, None, ''),
                ('sections', 'plot_design_type_expectations.py', None, None, ''),
                ('blocks', 'plot_design_type_expectations.py', None, None, ''),
                ('sections', 'plot_design_continuity.py', None, None, ''),
            ]),
            ('chapter_rhythm', '推进动力、重/中/轻/空章节奏轮换与章内结构', ['plot_design'], [
                ('sections', 'plot_design_progression.py', None, None, ''),
                ('blocks', 'plot_design_chapters.py', None, None, ''),
                ('blocks', 'plot_design_reader.py', None, None, ''),
            ]),
            ('subplot_resource', '配角支线交汇、退场弧光与资源剧情绑定', ['plot_design'], [
                ('sections', 'plot_design_supporting.py', None, None, ''),
                ('sections', 'plot_design_resources.py', None, None, ''),
            ]),
            ('multi_viewpoint', '多角色视角切换与交错编排', ['plot_design', 'scene_design'], [
                ('sections', 'plot_design_multi_viewpoint.py', None, None, ''),
            ]),
        ]
        seen_struct: set[str] = set()
        for group_key, label, stages, specs in structure_groups:
            children = []
            for kind, filename, selector, exclude_ids, prefix in specs:
                if kind == 'typed':
                    rows = _typed(slot, filename, stages=stages, include_ids=selector, key_prefix=prefix)
                elif kind == 'blocks':
                    rows = _blocks(slot, filename, stages=stages, key_prefix=prefix)
                else:
                    rows = _sections(slot, filename, selector, stages=stages, key_prefix=prefix, exclude_ids=exclude_ids)
                for row in rows:
                    if row['key'] not in seen_struct:
                        children.append(row)
                        seen_struct.add(row['key'])
            if children:
                result.append(_group(slot, group_key, label, children))
        return result
    if slot == 'hook':
        hook_groups = [
            ('types', '核心情节推进机制（23 类标准机制）', ['plot_design', 'event_design'], [
                ('typed', 'plot_design_plot_mechanisms.py', None, None, ''),
            ]),
            ('plot_design_reader_engagement', '黄金三章、追读钩子、情绪波形与读者承诺', ['plot_design'], [
                ('sections', 'plot_design_reader_engagement.py', None, None, ''),
            ]),
            ('foreshadow_twist', '伏笔埋设、休眠延迟解码、回收率与反转联动', ['plot_design'], [
                ('blocks', 'plot_design_foreshadowing.py', None, None, ''),
                ('sections', 'plot_design_foreshadowing.py', {'120'}, None, ''),
                ('sections', 'plot_design_promise_workflow.py', None, None, ''),
            ]),
            ('disclosure_suspense', '信息差设计、延迟信息释放与认知错位悬念', ['plot_design'], [
                ('sections', 'plot_design_disclosure.py', {'116'}, None, ''),
                ('blocks', 'plot_design_disclosure.py', None, None, ''),
                ('sections', 'plot_design_misalignment.py', None, None, ''),
                ('sections', 'plot_design_symbolism.py', None, None, ''),
            ]),
            ('event_chain_triggers', '前驱完成门、因果顺序、决策连锁与自动运转事件', ['event_design'], [
                ('sections', 'event_design.py', None, None, 'ev.'),
                ('blocks', 'event_design.py', None, None, 'ev.'),
                ('sections', 'event_design_progression.py', None, None, 'ev.'),
                ('sections', 'event_design_supporting.py', None, None, 'ev.'),
            ]),
            ('event_crisis_mechanisms', '特殊事件危机机制（副本/污染/外星/灾难/生化/主神/规则任务）', ['event_design'], [
                ('typed', 'event_design_plot_mechanisms.py', None, None, ''),
            ]),
        ]
        seen_hook: set[str] = set()
        for group_key, label, stages, specs in hook_groups:
            children = []
            for kind, filename, selector, exclude_ids, prefix in specs:
                if kind == 'typed':
                    rows = _typed(slot, filename, stages=stages, include_ids=selector, key_prefix=prefix)
                elif kind == 'blocks':
                    rows = _blocks(slot, filename, stages=stages, key_prefix=prefix)
                else:
                    rows = _sections(slot, filename, selector, stages=stages, key_prefix=prefix, exclude_ids=exclude_ids)
                for row in rows:
                    if row['key'] not in seen_hook:
                        children.append(row)
                        seen_hook.add(row['key'])
            if children:
                result.append(_group(slot, group_key, label, children))
        return result
    typed = {'tone': ('expression_design_type_tones.py', '语气与情绪（10 类标准语气）'),
             'style': ('expression_design_type_styles.py', '文风与语言质感（20 类标准风格）')}
    if slot in typed:
        filename, label = typed[slot]
        result.append(_group(slot, 'types', label, _typed(slot, filename)))
        return result
    if slot == 'narration':
        narration_groups = [
            ('expression_design_narrator', '叙述声音、可信度与距离', ['scene_design', 'expression_design'], [
                ('sections', 'expression_design_narrator.py', None, ''),
            ]),
            ('scene_design_narrator', '视角形态与叙述知识边界', ['scene_design', 'expression_design'], [
                ('sections', 'scene_design_narrator.py', None, ''),
            ]),
            ('expression_design_timeline', '叙述时序、速度与回忆', ['scene_design', 'expression_design'], [
                ('sections', 'expression_design_timeline.py', None, ''),
            ]),
            ('expression_design_disclosure', '信息释放方式', ['scene_design', 'expression_design'], [
                ('sections', 'expression_design_disclosure.py', None, ''),
            ]),
            ('anchor_beats', '具象锚点、镜头聚焦与脉搏/呼吸点', ['anchor_design'], [
                ('blocks', 'anchor_design_viewpoint.py', None, 'anc.'),
                ('blocks', 'anchor_design_scene.py', None, 'anc.'),
                ('sections', 'anchor_design_atmosphere.py', None, 'anc.'),
                ('sections', 'anchor_design_timeline.py', None, 'anc.'),
                ('sections', 'anchor_design_multi_viewpoint.py', None, 'anc.'),
            ]),
            ('dialogue_subtext', '对白目的、潜台词与非直接回答技术', ['expression_design'], [
                ('blocks', 'expression_design_dialogue.py', None, 'expr.'),
            ]),
            ('sensory_atmosphere', '五感距离、语言质感轮换、氛围与语体统一', ['expression_design'], [
                ('blocks', 'expression_design_sensory.py', None, 'expr.'),
                ('sections', 'expression_design_atmosphere.py', None, 'expr.'),
                ('sections', 'expression_design_continuity.py', None, 'expr.'),
            ]),
        ]
        seen_nar: set[str] = set()
        for group_key, label, stages, specs in narration_groups:
            children = []
            for kind, filename, sections, prefix in specs:
                rows = _blocks(slot, filename, stages=stages, key_prefix=prefix) if kind == 'blocks' else _sections(
                    slot, filename, sections, stages=stages, key_prefix=prefix)
                for row in rows:
                    if row['key'] not in seen_nar:
                        children.append(row)
                        seen_nar.add(row['key'])
            if children:
                result.append(_group(slot, group_key, label, children))
        return result
    return result


def options(slot: str, parent: str = '', types: list[str] | None = None) -> list[dict]:
    rows = _options(slot)
    if parent:
        found = option_map(slot).get(parent)
        if found is None:
            raise ValueError('未知选项分组')
        if slot in ('structure', 'hook'):
            from nw.studio.plot_materials import annotate_plot_children
            return annotate_plot_children(slot, parent, found['children'], types)
        if slot in ('narration', 'tone', 'style'):
            from nw.studio.craft_materials import annotate_craft_children
            return annotate_craft_children(slot, parent, found['children'], types)
        return deepcopy(found['children'])
    if slot == 'world':
        from nw.studio.world_materials import annotate_world_groups
        return annotate_world_groups(rows, types)
    if slot == 'character':
        from nw.studio.character_materials import annotate_character_groups
        return annotate_character_groups(rows, types)
    if slot in ('structure', 'hook'):
        from nw.studio.plot_materials import annotate_plot_groups
        return annotate_plot_groups(slot, rows, types)
    if slot in ('narration', 'tone', 'style'):
        from nw.studio.craft_materials import annotate_craft_groups
        return annotate_craft_groups(slot, rows, types)
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
