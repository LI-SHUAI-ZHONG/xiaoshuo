"""Unified 4-Pillar Book Craft Specs Facade (`world`, `cast`, `plot_pacing`, `voice`).

Provides one clean, consistent interface for:
  - Wizard setup & AI Auto defaults (`recommend_all_craft_setup`, `auto_select_craft_profiles`)
  - Compiling & persisting per-novel spec JSON files (`compile_craft_spec`, `load_all_craft_specs`, `save_craft_spec`)
  - Strictly step-scoped, budget-bounded injection into Stages 00, 03, 04, 05, 06, 07, 08, 09, 13, 15, and 16
  - Unified base-name resolution for `craft_fingerprints` across all 4 decomposition tracks.
"""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from nw.cast_specs import (
    CAST_BASE_MAP,
    CAST_BASES,
    CAST_KNOBS,
    build_character_stage_packet,
    build_relations_stage_packet,
    build_review_cast_guard,
    compile_cast_spec,
    default_cast_base_id,
    load_cast_spec,
    recommend_cast_bases,
    save_cast_spec,
)
from nw.craft_specs_base import (
    CRAFT_DOMAINS,
    DOMAIN_META,
    truncate_lines_to_budget,
)
from nw.plot_pacing_specs import (
    PLOT_BASE_MAP,
    PLOT_BASES,
    PLOT_KNOBS,
    build_event_scene_pacing_packet,
    build_plot_stage_packet,
    build_review_plot_guard,
    build_writer_scene_beat_hint,
    compile_plot_pacing_spec,
    compute_scale_profile,
    default_plot_base_id,
    load_plot_pacing_spec,
    recommend_plot_bases,
    save_plot_pacing_spec,
)
from nw.store import Store
from nw.voice_specs import (
    VOICE_BASE_MAP,
    VOICE_BASES,
    VOICE_KNOBS,
    build_review_voice_guard_from_package,
    compile_book_voice_spec,
    default_voice_base_id,
    load_book_voice_spec,
    recommend_voice_bases,
    save_book_voice_spec,
)
from nw.world_specs import (
    WORLD_BASE_MAP,
    WORLD_BASES,
    WORLD_KNOBS,
    build_action_world_gate_packet,
    build_review_world_guard,
    build_world_stage_packet,
    compile_world_spec,
    default_world_base_id,
    load_world_spec,
    recommend_world_bases,
    save_world_spec,
)


def all_base_name_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for mapping in (WORLD_BASE_MAP, CAST_BASE_MAP, PLOT_BASE_MAP, VOICE_BASE_MAP):
        for k, v in mapping.items():
            out[k] = str(v.get('name') or k)
    return out


def domain_base_map(domain: str) -> dict[str, dict[str, Any]]:
    if domain == 'world':
        return WORLD_BASE_MAP
    if domain == 'cast':
        return CAST_BASE_MAP
    if domain == 'plot_pacing':
        return PLOT_BASE_MAP
    if domain == 'voice':
        return VOICE_BASE_MAP
    raise ValueError(f'未知的基座域: {domain}')


def domain_knobs(domain: str) -> dict[str, dict[str, Any]]:
    if domain == 'world':
        return deepcopy(WORLD_KNOBS)
    if domain == 'cast':
        return deepcopy(CAST_KNOBS)
    if domain == 'plot_pacing':
        return deepcopy(PLOT_KNOBS)
    if domain == 'voice':
        return deepcopy(VOICE_KNOBS)
    raise ValueError(f'未知的基座域: {domain}')


def recommend_domain_bases(domain: str, types: list[str] | tuple[str, ...] | None) -> list[dict[str, Any]]:
    if domain == 'world':
        return recommend_world_bases(types)
    if domain == 'cast':
        return recommend_cast_bases(types)
    if domain == 'plot_pacing':
        return recommend_plot_bases(types)
    if domain == 'voice':
        return recommend_voice_bases(types)
    raise ValueError(f'未知的基座域: {domain}')


def default_domain_base_id(domain: str, types: list[str] | tuple[str, ...] | None) -> str:
    if domain == 'world':
        return default_world_base_id(types)
    if domain == 'cast':
        return default_cast_base_id(types)
    if domain == 'plot_pacing':
        return default_plot_base_id(types)
    if domain == 'voice':
        return default_voice_base_id(types)
    raise ValueError(f'未知的基座域: {domain}')


def compile_craft_spec(
    domain: str,
    genre_ids: list[str] | tuple[str, ...],
    *,
    base_id: str | None = None,
    knobs: dict[str, Any] | None = None,
    fingerprints: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    custom_notes: str = '',
    enabled: bool = True,
    target_words: int | None = None,
    wizard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile any of the 4 craft spec domains into its canonical JSON payload."""
    wiz = wizard if isinstance(wizard, dict) else {}
    if domain == 'world':
        world_mechs = list(wiz.get('world_ids') or ()) + [
            m for m in (wiz.get('mechanism_ids') or ()) if str(m).startswith('PLOT_MECHANISM_')
        ]
        return compile_world_spec(
            genre_ids,
            base_id=base_id,
            knobs=knobs,
            world_mechanism_ids=world_mechs,
            fingerprints=fingerprints,
            custom_notes=custom_notes,
            enabled=enabled,
        )
    if domain == 'cast':
        char_mechs = list(wiz.get('character_ids') or ())
        return compile_cast_spec(
            genre_ids,
            base_id=base_id,
            knobs=knobs,
            character_mechanism_ids=char_mechs,
            fingerprints=fingerprints,
            custom_notes=custom_notes,
            enabled=enabled,
        )
    if domain == 'plot_pacing':
        tw = target_words if target_words is not None else wiz.get('target_words')
        return compile_plot_pacing_spec(
            genre_ids,
            base_id=base_id,
            target_words=tw if isinstance(tw, int) else None,
            knobs=knobs,
            structure_ids=wiz.get('structure_ids') or (),
            mechanism_ids=wiz.get('mechanism_ids') or (),
            fingerprints=fingerprints,
            custom_notes=custom_notes,
            enabled=enabled,
        )
    if domain == 'voice':
        return compile_book_voice_spec(
            genre_ids,
            base_voice_id=base_id,
            knobs=knobs,
            tone_ids=wiz.get('tone_ids') or (),
            style_ids=wiz.get('style_ids') or (),
            fingerprints=fingerprints,
            custom_notes=custom_notes,
            enabled=enabled,
        )
    raise ValueError(f'未知的基座域: {domain}')


def load_craft_spec(store: Store, domain: str) -> dict[str, Any] | None:
    if domain == 'world':
        return load_world_spec(store)
    if domain == 'cast':
        return load_cast_spec(store)
    if domain == 'plot_pacing':
        return load_plot_pacing_spec(store)
    if domain == 'voice':
        return load_book_voice_spec(store)
    raise ValueError(f'未知的基座域: {domain}')


def save_craft_spec(store: Store, domain: str, spec: dict[str, Any]) -> dict[str, Any]:
    if domain == 'world':
        return save_world_spec(store, spec)
    if domain == 'cast':
        return save_cast_spec(store, spec)
    if domain == 'plot_pacing':
        return save_plot_pacing_spec(store, spec)
    if domain == 'voice':
        return save_book_voice_spec(store, spec)
    raise ValueError(f'未知的基座域: {domain}')


def load_all_craft_specs(
    store: Store | None,
    *,
    wizard: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """Load all 4 craft specs from project store, falling back to frozen wizard specs if present."""
    wiz = wizard if isinstance(wizard, dict) else {}
    wiz_specs = wiz.get('craft_specs') if isinstance(wiz.get('craft_specs'), dict) else {}
    out: dict[str, dict[str, Any] | None] = {}
    for domain in CRAFT_DOMAINS:
        spec = load_craft_spec(store, domain) if store is not None else None
        if spec is None:
            if domain == 'voice' and isinstance(wiz.get('voice_spec'), dict):
                spec = wiz['voice_spec']
            elif isinstance(wiz_specs.get(domain), dict):
                spec = wiz_specs[domain]
        out[domain] = spec
    return out


def recommend_all_craft_setup(
    types: list[str] | tuple[str, ...] | None,
    *,
    target_words: int | None = None,
    library: Any = None,
) -> dict[str, dict[str, Any]]:
    """Build wizard/drawer setup profiles for all 4 craft spec domains."""
    result: dict[str, dict[str, Any]] = {}
    for domain in CRAFT_DOMAINS:
        bases = recommend_domain_bases(domain, types)
        rec_id = bases[0]['id'] if bases else default_domain_base_id(domain, types)
        fps: list[dict[str, Any]] = []
        if library is not None:
            try:
                if hasattr(library, 'craft_fingerprints'):
                    fps = library.craft_fingerprints(domain=domain, types=types or None, status='approved')
                elif domain == 'voice' and hasattr(library, 'voice_fingerprints'):
                    fps = library.voice_fingerprints(types=types or None, status='approved')
            except Exception:
                fps = []
        entry: dict[str, Any] = {
            **DOMAIN_META[domain],
            'recommended_base_id': rec_id,
            'bases': bases,
            'knobs': domain_knobs(domain),
            'available_fingerprints': fps,
        }
        if domain == 'plot_pacing':
            default_speed = (bases[0].get('default_knobs') or {}).get('pacing_speed', 'steady_wave') if bases else 'steady_wave'
            entry['scale_profile'] = compute_scale_profile(target_words, pacing_speed=default_speed)
        result[domain] = entry
    return result


def auto_select_craft_profiles(
    types: list[str] | tuple[str, ...] | None,
    *,
    target_words: int | None = None,
    library: Any = None,
) -> dict[str, dict[str, Any]]:
    """Deterministically pick non-conflicting genre-aligned profiles for all 4 craft domains."""
    out: dict[str, dict[str, Any]] = {}
    for domain in CRAFT_DOMAINS:
        bid = default_domain_base_id(domain, types)
        meta = domain_base_map(domain)[bid]
        fp_ids: list[str] = []
        if library is not None and types:
            try:
                if hasattr(library, 'craft_fingerprints'):
                    fps = library.craft_fingerprints(domain=domain, types=types, status='approved')
                elif domain == 'voice' and hasattr(library, 'voice_fingerprints'):
                    fps = library.voice_fingerprints(types=types, status='approved')
                else:
                    fps = []
                fp_ids = [fp['id'] for fp in fps[:2] if fp.get('id')]
            except Exception:
                fp_ids = []
        prof: dict[str, Any] = {
            'base_id': bid,
            'base_name': meta['name'],
            'knobs': deepcopy(meta['default_knobs']),
            'fingerprint_ids': fp_ids,
        }
        if domain == 'voice':
            prof['base_voice_id'] = bid
            prof['base_voice_name'] = meta['name']
        if domain == 'plot_pacing':
            prof['scale_profile'] = compute_scale_profile(
                target_words, pacing_speed=prof['knobs'].get('pacing_speed', 'steady_wave'),
            )
        out[domain] = prof
    return out


def build_direction_specs_summary(specs: dict[str, dict[str, Any] | None]) -> str:
    """Ultra-compact 4-pillar summary (<=300 chars) for 00 `book_direction`."""
    lines: list[str] = []
    for domain, label in (
        ('world', '世界'),
        ('cast', '人物'),
        ('plot_pacing', '剧情节奏'),
        ('voice', '语感'),
    ):
        sp = specs.get(domain)
        if not isinstance(sp, dict) or not sp.get('enabled', True):
            continue
        name = sp.get('base_name') or sp.get('base_voice_name') or ''
        tag = sp.get('tagline') or ''
        extra = ''
        if domain == 'plot_pacing' and isinstance(sp.get('scale_profile'), dict):
            sc = sp['scale_profile']
            extra = f"（{sc.get('tier_label', '')}，小高潮每{'–'.join(str(x) for x in sc.get('small_climax_every_chapters', [5, 8]))}章）"
        lines.append(f"{label}：{name}{extra}—{tag[:42]}")
    if not lines:
        return ''
    return truncate_lines_to_budget(['本书四维创作基座摘要（提案须与之兼容）：', *lines], 300)


def build_stage_craft_spec_packet(
    stage: str,
    scope: str,
    specs: dict[str, dict[str, Any] | None],
) -> dict[str, Any] | None:
    """Strict Step-Scoped Injection Matrix — each design stage receives ONLY its own domain slice."""
    if stage == 'world_design':
        return build_world_stage_packet(specs.get('world'), scope=scope, max_chars=900)
    if stage == 'action_design':
        return build_action_world_gate_packet(specs.get('world'), max_chars=260)
    if stage == 'character_design':
        return build_character_stage_packet(specs.get('cast'), scope=scope, max_chars=900)
    if stage == 'static_relations':
        return build_relations_stage_packet(specs.get('cast'), max_chars=400)
    if stage == 'plot_design':
        return build_plot_stage_packet(specs.get('plot_pacing'), scope=scope, max_chars=1100)
    if stage in ('event_design', 'scene_design'):
        return build_event_scene_pacing_packet(specs.get('plot_pacing'), max_chars=340)
    return None


def build_review_craft_guards(
    package: dict[str, Any],
    *,
    specs: dict[str, dict[str, Any] | None] | None = None,
    max_chars: int = 450,
) -> str:
    """Assemble same-source anti-drift redlines across all enabled pillars (<=450 chars) for 16 review/revise."""
    parts: list[str] = []
    # 1. Voice redlines embedded inside the frozen story package (always preferred for Step 16).
    voice_guard = build_review_voice_guard_from_package(package)
    if voice_guard:
        parts.append(voice_guard)

    # 2. Plot-pacing redlines embedded inside frozen package `scene-beat` item (if present) or live specs.
    pkg_beat_redlines: list[str] = []
    for item in (package.get('items') or ()):
        if isinstance(item, dict) and item.get('source') == 'scene-beat':
            try:
                parsed = json.loads(item.get('text') or item.get('content') or '{}')
                if isinstance(parsed, dict) and isinstance(parsed.get('review_redlines'), list):
                    pkg_beat_redlines = [str(x).strip() for x in parsed['review_redlines'] if str(x).strip()]
            except ValueError:
                pass
            break
    if pkg_beat_redlines:
        parts.append('【剧情节奏防漂移】' + '；'.join(pkg_beat_redlines[:2]))
    elif specs and (pg := build_review_plot_guard(specs.get('plot_pacing'))):
        parts.append(pg)

    if specs:
        if wg := build_review_world_guard(specs.get('world')):
            parts.append(wg)
        if cg := build_review_cast_guard(specs.get('cast')):
            parts.append(cg)

    if not parts:
        return ''
    return truncate_lines_to_budget(parts, max_chars)


def summarize_craft_specs(specs: dict[str, dict[str, Any] | None]) -> dict[str, dict[str, Any]]:
    """Compact status summary for Studio quality/header panels."""
    summary: dict[str, dict[str, Any]] = {}
    for domain in CRAFT_DOMAINS:
        sp = specs.get(domain)
        if isinstance(sp, dict):
            summary[domain] = {
                'enabled': bool(sp.get('enabled', True)),
                'base_id': sp.get('base_id') or sp.get('base_voice_id') or '',
                'base_name': sp.get('base_name') or sp.get('base_voice_name') or '',
                'fingerprint_count': len(sp.get('fingerprint_ids') or ()),
                'redlines_count': len(sp.get('anti_drift_redlines') or sp.get('drift_redlines') or ()),
                'sha256': sp.get('sha256', ''),
                **({'tier_label': (sp.get('scale_profile') or {}).get('tier_label', '')} if domain == 'plot_pacing' else {}),
            }
        else:
            summary[domain] = {'enabled': False, 'base_id': '', 'base_name': '', 'fingerprint_count': 0, 'redlines_count': 0}
    return summary
