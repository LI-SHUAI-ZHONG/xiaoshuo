"""Streamlined, workflow-aligned setup profile for Manual and AI Auto novel creation.

Separates two fundamentally different layers that were previously conflated:
  1. AUTO_ENFORCED_CAPABILITIES: Universal novel-writing craft foundations (protagonist &
     supporting-cast anti-flattening, character relations & independent side-cast interactions,
     world baseline & anti-genre-leakage, 3-act/arc causality, golden-3 opening & foreshadowing
     payoff, event completion gates, restricted POV & observable anchors, independent review
     redlines) — enforced AUTOMATICALLY by the 15,375 built-in design_ready rules. Authors
     NEVER have to waste time clicking checkboxes for these!
  2. Differentiating creative choices (4 fast steps):
     - Step 1: Genre & Length (主/子/副类型 + 篇幅档位)
     - Step 2: Architecture, Driving Hooks & Special Mechanisms (flat inline choices,
       genre-prioritized, cross-genre collapsed; zero mandatory character/world basics!)
     - Step 3: Narrative Viewpoint, Tone/Style & Optional Corpus Methods (flat inline choices)
     - Step 4: Idea, Hard Constraints & Launch (builtin_enhanced by default — never deadlocked!)
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nw.studio import catalog
from nw.studio.character_materials import character_profile_for_types
from nw.studio.craft_materials import craft_profile_for_types
from nw.studio.plot_materials import plot_profile_for_types
from nw.studio.world_materials import world_profile_for_types

# Universal writing craft enforced automatically behind the scenes (never clutter manual setup).
AUTO_ENFORCED_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        'id': 'auto_world_baseline',
        'title': '世界规则底座与题材边界防污染',
        'stages': ['world_design', 'action_design', 'review'],
        'stage_label': '03 世界定稿 / 08 行动 / 16 审稿',
        'summary': '按所选题材自动加载世界形态前提、社会制度、资源稀缺与道具代价边界，并对非超自然题材自动屏蔽修仙/种族污染。',
    },
    {
        'id': 'auto_character_supporting',
        'title': '主角、反派与配角防工具化体系（无需手动勾选）',
        'stages': ['character_design', 'static_relations'],
        'stage_label': '04 人物定稿 / 05 关系张力',
        'summary': '自动启用主角欲望与弧光、反派独立逻辑、配角五级分层与复用优先、三层人格外化、亲缘/社会关系网及≥2条配角独立互动。',
    },
    {
        'id': 'auto_plot_foreshadow',
        'title': '黄金三章承诺、伏笔回收与因果完成门',
        'stages': ['plot_design', 'event_design'],
        'stage_label': '06 故事大纲 / 07 事件链',
        'summary': '自动约束开篇三章承诺、重/中/轻/空章节奏轮换、伏笔 2–10 章窗口与≥80%回收、前驱完成条件门（104.1 防倒置）。',
    },
    {
        'id': 'auto_pov_anchors_review',
        'title': '受限 POV 守卫、具象锚点与独立审稿红线',
        'stages': ['scene_design', 'anchor_design', 'expression_design', 'writer', 'review', 'acceptance'],
        'stage_label': '09 场景 / 12 锚点 / 13 表达 / 15–17 写审验收',
        'summary': '自动锁定单场 POV 知识边界、身体/感官微反应锚点、潜台词对白、禁用“他心想/意识到”、正文引文审稿及主客观事实隔离。',
    },
)

# Differentiating special character mechanisms (goldfinger/team tropes — NOT basic character craft).
_SPECIAL_CHARACTER_MECHANISM_IDS = frozenset({
    'PLOT_MECHANISM_BLOODLINE',
    'PLOT_MECHANISM_TALENT',
    'PLOT_MECHANISM_INVINCIBLE',
    'PLOT_MECHANISM_GENE',
    'PLOT_MECHANISM_TEAM',
})

# Differentiating narration viewpoint/timeline sections (NOT universal anchors/dialogue/sensory craft).
_VIEWPOINT_NARRATION_GROUPS = (
    'narration.group.scene_design_narrator',
    'narration.group.expression_design_narrator',
    'narration.group.expression_design_timeline',
)

_RELEVANCE_ORDER = {'primary': 0, 'optional': 1, 'out_of_scope': 2}


def _flat_item(row: dict[str, Any], slot: str, category_label: str, *, relevance: str | None = None) -> dict[str, Any]:
    rel = relevance or row.get('relevance') or 'optional'
    rel_labels = {'primary': '本类型推荐', 'optional': '按需可选', 'out_of_scope': '跨题材扩展'}
    return {
        'key': row['key'],
        'id': row['id'],
        'slot': slot,
        'name': row['name'],
        'description': row.get('description') or row.get('definition') or '',
        'stages': list(row.get('stages') or catalog.SLOT_STAGES.get(slot, [])),
        'category_label': category_label,
        'relevance': rel,
        'relevance_label': row.get('relevance_label') or rel_labels.get(rel, '按需可选'),
    }


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda r: (_RELEVANCE_ORDER.get(r['relevance'], 1), r['id']))


def setup_profile_for_types(types: list[str] | tuple[str, ...] | None = None, *, library: Any = None) -> dict[str, Any]:
    """Build the clean, flat, genre-targeted setup profile for the 4-step Manual & AI Auto wizards."""
    normalized = catalog.canonical_types(list(types)) if types else []
    world_bp = world_profile_for_types(normalized)
    char_bp = character_profile_for_types(normalized)
    plot_bp = plot_profile_for_types(normalized)
    craft_bp = craft_profile_for_types(normalized)

    # 1) Narrative structures (flat inline from structure.group.types)
    struct_children = catalog.options('structure', 'structure.group.types', types=normalized)
    structures = _sort_items([_flat_item(r, 'structure', '叙事结构') for r in struct_children])

    # 2) Core driving plot mechanisms (flat inline from hook.group.types)
    hook_children = catalog.options('hook', 'hook.group.types', types=normalized)
    mechanisms = _sort_items([_flat_item(r, 'hook', '核心推进机制') for r in hook_children])

    # 3) Optional special world / goldfinger / crisis mechanisms ONLY (zero universal world/character basics!)
    world_rel_by_cat = {c['id']: c['relevance'] for c in world_bp.get('categories', ())}
    char_rel_by_cat = {c['id']: c['relevance'] for c in char_bp.get('categories', ())}
    special_world_rel = world_rel_by_cat.get('special_mechanism', 'optional')
    supernatural_char_rel = char_rel_by_cat.get('supernatural_ability', 'optional')

    special_mechanisms: list[dict[str, Any]] = []
    # World top-level special mechanisms (system, parallel world, VR, cyberpunk, utopia, multiverse, gamification)
    for row in catalog.options('world', 'world.group.special_mechanism', types=normalized):
        special_mechanisms.append(_flat_item(row, 'world', '特殊世界框架', relevance=special_world_rel))
    # Character goldfinger/team tropes only (bloodline, talent, invincible, gene, team) — never basic cast craft!
    for group_key in ('character.group.supernatural_ability', 'character.group.supporting_cast'):
        for row in catalog.options('character', group_key, types=normalized):
            if row['id'] in _SPECIAL_CHARACTER_MECHANISM_IDS:
                rel = 'optional' if row['id'] == 'PLOT_MECHANISM_TEAM' else supernatural_char_rel
                special_mechanisms.append(_flat_item(row, 'character', '特色主角/团队机制', relevance=rel))
    # Event crisis mechanisms (dungeon, contamination, alien, disaster, biochemical, main_god, rule_task)
    for row in catalog.options('hook', 'hook.group.event_crisis_mechanisms', types=normalized):
        special_mechanisms.append(_flat_item(row, 'hook', '特殊危机机制'))
    special_mechanisms = _sort_items(special_mechanisms)

    # 4) Narrative viewpoint & timeline choices ONLY (no universal anchors/dialogue/sensory basics)
    narration_groups = {g['key']: g for g in catalog.options('narration', types=normalized)}
    viewpoint_choices: list[dict[str, Any]] = []
    for gkey in _VIEWPOINT_NARRATION_GROUPS:
        group = narration_groups.get(gkey)
        if not group:
            continue
        label = group.get('short_name') or group['name']
        for child in group.get('children', ()):
            viewpoint_choices.append(_flat_item(child, 'narration', label, relevance='primary' if 'scene_design_narrator' in gkey else 'optional'))

    # 5) Tones & Styles (flat inline directly selectable, genre-prioritized)
    tones = _sort_items([_flat_item(r, 'tone', '语气基调') for r in catalog.options('tone', 'tone.group.types', types=normalized)])
    styles = _sort_items([_flat_item(r, 'style', '文风质感') for r in catalog.options('style', 'style.group.types', types=normalized)])

    # 6) Optional available corpus methods summary for this genre (never blocking!)
    available_methods: list[dict[str, Any]] = []
    if library is not None and normalized:
        try:
            from nw.production_methods.sources import MethodReader, matching_methods
            from nw.studio.method_recommendations import uses as method_uses, SLOT_TASKS

            reader = MethodReader(library.workspace)
            if reader.db_path.is_file():
                for row, match in matching_methods(reader, normalized):
                    body = row['body']
                    # Find first matching slot for wizard method_preferences compatibility
                    matched_slot = next(
                        (s for s in ('world', 'character', 'structure', 'hook', 'narration', 'tone', 'style')
                         if method_uses(body, s, row['structure_origin'], planning_hierarchy=True)),
                        None,
                    )
                    if not matched_slot:
                        continue
                    placements = method_uses(body, matched_slot, row['structure_origin'], planning_hierarchy=True)
                    available_methods.append({
                        'id': row['id'],
                        'version': row['version'],
                        'slot': matched_slot,
                        'title': body['title'],
                        'type_match': match,
                        'applicability': body['applicability'],
                        'non_applicability': body['non_applicability'],
                        'uses': placements,
                        'tasks': body['tasks'],
                    })
        except Exception:
            available_methods = []

    # 7) Executable Voice Spec Setup (8 built-in voice bases + 4 orthogonal knobs + compatible decomposed fingerprints)
    from nw.voice_specs import (
        VOICE_KNOBS,
        default_voice_base_id,
        recommend_voice_bases,
    )
    ranked_voices = recommend_voice_bases(normalized)
    recommended_voice_id = default_voice_base_id(normalized)
    available_fingerprints: list[dict[str, Any]] = []
    if library is not None and hasattr(library, 'voice_fingerprints'):
        try:
            available_fingerprints = library.voice_fingerprints(types=normalized or None, status='approved')
        except Exception:
            available_fingerprints = []

    voice_setup = {
        'recommended_base_id': recommended_voice_id,
        'voice_bases': ranked_voices,
        'knobs': deepcopy(VOICE_KNOBS),
        'available_fingerprints': available_fingerprints,
    }

    # 8) Genre scope summary for downstream creation_plan injection
    world_oos = [c['short_name'] for c in world_bp.get('categories', ()) if c['relevance'] == 'out_of_scope']
    genre_scope = {
        'type_ids': normalized,
        'world_resources': world_bp.get('resource_profile', {}),
        'world_excluded_domains': world_oos,
        'character_focus': char_bp.get('cast_profile', {}),
        'plot_focus': plot_bp.get('plot_profile', {}),
        'craft_focus': craft_bp.get('craft_profile', {}),
    }

    ai_defaults = auto_select_genre_preferences(normalized, library=library)
    return {
        'version': 2,
        'types': normalized,
        'auto_enforced_capabilities': list(deepcopy(AUTO_ENFORCED_CAPABILITIES)),
        'genre_scope': genre_scope,
        'selection_limits': catalog.wizard_selection_limits(),
        'voice_setup': voice_setup,
        'sections': {
            'structures': structures,
            'mechanisms': mechanisms,
            'special_mechanisms': special_mechanisms,
            'viewpoint_choices': viewpoint_choices,
            'tones': tones,
            'styles': styles,
        },
        'available_corpus_methods': available_methods,
        'ai_auto_defaults': ai_defaults,
    }


def auto_select_genre_preferences(
    types: list[str] | tuple[str, ...],
    *,
    library: Any = None,
) -> dict[str, Any]:
    """Deterministically select clean, non-conflicting genre-aligned defaults for AI Auto mode."""
    from nw.voice_specs import VOICE_BASE_MAP, default_voice_base_id

    normalized = catalog.canonical_types(list(types)) if types else []
    if not normalized:
        return {
            'structure_ids': [], 'mechanism_ids': [], 'tone_ids': [], 'style_ids': [],
            'voice_profile': {'base_voice_id': 'VOICE_GENRE_HYBRID_BALANCED', 'knobs': {}, 'fingerprint_ids': []},
        }

    struct_children = catalog.options('structure', 'structure.group.types', types=normalized)
    primary_structs = [r['id'] for r in struct_children if r.get('relevance') == 'primary']
    # Never select both SINGLE_POV and MULTI_POV together
    picked_structs: list[str] = []
    for sid in primary_structs:
        if sid == 'NARRATIVE_STRUCTURE_MULTI_POV' and 'NARRATIVE_STRUCTURE_SINGLE_POV' in picked_structs:
            continue
        if sid == 'NARRATIVE_STRUCTURE_SINGLE_POV' and 'NARRATIVE_STRUCTURE_MULTI_POV' in picked_structs:
            continue
        picked_structs.append(sid)
        if len(picked_structs) >= 2:
            break

    hook_children = catalog.options('hook', 'hook.group.types', types=normalized)
    picked_mechs = [r['id'] for r in hook_children if r.get('relevance') == 'primary'][:2]

    tone_children = catalog.options('tone', 'tone.group.types', types=normalized)
    picked_tones = [r['id'] for r in tone_children if r.get('relevance') == 'primary'][:1]

    style_children = catalog.options('style', 'style.group.types', types=normalized)
    picked_styles = [r['id'] for r in style_children if r.get('relevance') == 'primary'][:2]
    # Avoid light+gritty competition in automatic defaults
    if 'STYLE_LIGHT' in picked_styles and 'STYLE_GRITTY' in picked_styles:
        picked_styles = [s for s in picked_styles if s != 'STYLE_GRITTY']

    base_voice_id = default_voice_base_id(normalized)
    base_meta = VOICE_BASE_MAP[base_voice_id]
    matched_fp_ids: list[str] = []
    if library is not None and hasattr(library, 'voice_fingerprints'):
        try:
            fps = library.voice_fingerprints(types=normalized, status='approved')
            matched_fp_ids = [fp['id'] for fp in fps[:2] if fp.get('id')]
        except Exception:
            matched_fp_ids = []

    return {
        'structure_ids': picked_structs,
        'mechanism_ids': picked_mechs,
        'tone_ids': picked_tones,
        'style_ids': picked_styles,
        'voice_profile': {
            'base_voice_id': base_voice_id,
            'base_voice_name': base_meta['name'],
            'knobs': deepcopy(base_meta['default_knobs']),
            'fingerprint_ids': matched_fp_ids,
        },
    }


def genre_scope_for_stage(types: list[str] | tuple[str, ...], stage: str) -> dict[str, Any]:
    """Return concise genre-scoped craft guidance & exclusions for a specific creative stage."""
    normalized = catalog.canonical_types(list(types)) if types else []
    if not normalized:
        return {}
    if stage == 'world_design':
        bp = world_profile_for_types(normalized)
        return {
            'preferred_resources': bp.get('resource_profile', {}).get('preferred_resources', []),
            'exchange_media': bp.get('resource_profile', {}).get('exchange_media', []),
            'long_term_constraints': bp.get('resource_profile', {}).get('long_term_constraints', []),
            'excluded_cross_genre_domains': [c['short_name'] for c in bp.get('categories', ()) if c['relevance'] == 'out_of_scope'],
        }
    if stage in ('character_design', 'static_relations'):
        bp = character_profile_for_types(normalized)
        return {
            **bp.get('cast_profile', {}),
            'excluded_cross_genre_domains': [c['short_name'] for c in bp.get('categories', ()) if c['relevance'] == 'out_of_scope'],
        }
    if stage in ('plot_design', 'event_design'):
        bp = plot_profile_for_types(normalized)
        return dict(bp.get('plot_profile', {}))
    if stage in ('anchor_design', 'expression_design'):
        bp = craft_profile_for_types(normalized)
        return dict(bp.get('craft_profile', {}))
    return {}
