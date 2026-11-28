"""Shared foundation for the 4-Pillar Executable Craft Spec Pack (World / Cast / Plot-Pacing / Voice).

Provides a single unified contract, cross-genre contamination firewall, ranking engine,
knob normalizer, atomic per-project JSON storage, and unified `craft_fingerprints`
SQLite registry (100% backward-compatible with legacy `voice_fingerprints` rows).
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from nw.store import Store, now
from nw.studio.catalog import canonical_types
from nw.task_models import canonical, content_sha256

CRAFT_DOMAINS: tuple[str, ...] = ('world', 'cast', 'plot_pacing', 'voice')

DOMAIN_META: dict[str, dict[str, Any]] = {
    'world': {
        'domain': 'world',
        'name': '世界规则基座',
        'short_name': '世界规则',
        'filename': 'world_spec.json',
        'track_id': 'genre_world_rules',
        'stages': ('world_design', 'action_design', 'review'),
        'stage_label': '03 世界定稿 / 08 行动门槛 / 16 规则审稿',
        'max_prompt_chars': 900,
    },
    'cast': {
        'domain': 'cast',
        'name': '人物群像力学基座',
        'short_name': '人物群像',
        'filename': 'cast_spec.json',
        'track_id': 'character_conflict',
        'stages': ('character_design', 'static_relations', 'review'),
        'stage_label': '04 人物定稿 / 05 关系张力 / 16 角色审稿',
        'max_prompt_chars': 900,
    },
    'plot_pacing': {
        'domain': 'plot_pacing',
        'name': '剧情引擎与节奏钩子基座',
        'short_name': '剧情与节奏',
        'filename': 'plot_pacing_spec.json',
        'track_id': 'opening_plot_hooks',
        'stages': ('plot_design', 'event_design', 'scene_design', 'writer', 'review'),
        'stage_label': '06 书卷章纲 / 07 事件 / 09 场景 / 15 本场2行节拍 / 16 审稿',
        'max_prompt_chars': 1100,
    },
    'voice': {
        'domain': 'voice',
        'name': '语感与叙事写法基座',
        'short_name': '语感规范',
        'filename': 'voice_spec.json',
        'track_id': 'scene_prose_craft',
        'stages': ('expression_design', 'writer', 'review'),
        'stage_label': '13 表达设计 / 15 正文写作 / 16 语感审稿',
        'max_prompt_chars': 1100,
    },
}

CRAFT_FINGERPRINT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS craft_fingerprints (
 id TEXT PRIMARY KEY,
 domain TEXT NOT NULL,
 book_id TEXT NOT NULL REFERENCES staging_books(id),
 structure_version INTEGER NOT NULL,
 title TEXT NOT NULL,
 base_id TEXT NOT NULL,
 type_tags_json TEXT NOT NULL DEFAULT '[]',
 excluded_types_json TEXT NOT NULL DEFAULT '[]',
 target_functions_json TEXT NOT NULL DEFAULT '[]',
 body_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'approved',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS craft_fp_domain_book ON craft_fingerprints(domain, book_id, status);
'''

# Coarse genre families used to auto-compute excluded_types so decomposed fingerprints
# never leak classical/xianxia logic into modern urban/suspense books (or vice versa).
_GENRE_FIREWALL_FAMILIES: dict[str, frozenset[str]] = {
    'classical_fantastic': frozenset({
        'GENRE_XIANXIA', 'GENRE_WUXIA', 'GENRE_XUANHUAN', 'GENRE_LISHI', 'GENRE_QUANMOU',
    }),
    'modern_realistic': frozenset({
        'GENRE_DUSHI', 'GENRE_XIANSHI', 'GENRE_ZHIYE', 'GENRE_SHANGZHAN',
        'GENRE_XUANYI', 'GENRE_TUILI', 'GENRE_QINGCHUN', 'GENRE_TIYU',
    }),
    'speculative_dark': frozenset({
        'GENRE_QIHUAN', 'GENRE_KEHUAN', 'GENRE_SAIBO', 'GENRE_WEILAI',
        'GENRE_MOSHI', 'GENRE_LINGYI', 'GENRE_KONGBU',
    }),
    'light_playful': frozenset({
        'GENRE_QINGXIAOSHUO', 'GENRE_ERCIYUAN', 'GENRE_YOUXI', 'GENRE_DIANJING', 'GENRE_TONGREN',
    }),
}

PRIORITY_ARBITRATION_NOTE = (
    '优先级铁律：作者硬约束与已批准的上游具体卡片（方向/世界卡/人物卡/卷章纲/前章正文）'
    ' > 本基座规范 > 通用默认规则；基座用于提升造卡与推演精度，绝不覆盖或篡改已批准的具体故事事实。'
)


def excluded_types_for_genres(type_ids: list[str] | tuple[str, ...]) -> list[str]:
    """Compute clearly incompatible main genres so decomposed fingerprints never cross-contaminate."""
    normalized = set(canonical_types(list(type_ids))) if type_ids else set()
    if not normalized:
        return []
    in_classical = bool(normalized & _GENRE_FIREWALL_FAMILIES['classical_fantastic'])
    in_modern = bool(normalized & _GENRE_FIREWALL_FAMILIES['modern_realistic'])
    in_spec = bool(normalized & _GENRE_FIREWALL_FAMILIES['speculative_dark'])
    excluded: set[str] = set()
    if in_classical and not in_modern:
        excluded |= (_GENRE_FIREWALL_FAMILIES['modern_realistic'] - {'GENRE_SHANGZHAN'})
    elif in_modern and not in_classical:
        excluded |= {'GENRE_XIANXIA', 'GENRE_WUXIA', 'GENRE_XUANHUAN'}
    if in_spec and not in_classical:
        excluded |= {'GENRE_XIANXIA', 'GENRE_WUXIA'}
    return sorted(excluded - normalized)


def is_fingerprint_compatible(
    fp: dict[str, Any],
    genre_ids: list[str] | tuple[str, ...] | None,
) -> bool:
    """Return True if a fingerprint is safe to combine with the target novel's genres."""
    if not genre_ids:
        return True
    normalized = set(canonical_types(list(genre_ids)))
    fp_tags = set(fp.get('type_tags') or ())
    fp_excl = set(fp.get('excluded_types') or ())
    if normalized & fp_excl:
        return False
    if fp_tags and (normalized & fp_tags):
        return True
    if not fp_tags:
        return True
    # Allow cross-subgenre reuse within the same coarse family if not explicitly excluded.
    for fam in _GENRE_FIREWALL_FAMILIES.values():
        if (normalized & fam) and (fp_tags & fam):
            return True
    return False


def rank_bases_for_genres(
    bases: tuple[dict[str, Any], ...],
    types: list[str] | tuple[str, ...] | None,
    *,
    fallback_id: str,
) -> list[dict[str, Any]]:
    """Rank a domain's built-in executable bases for the chosen genres."""
    normalized = canonical_types(list(types)) if types else []
    primary = normalized[0] if normalized else ''
    type_set = set(normalized)

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for idx, base in enumerate(bases):
        rec = set(base.get('recommended_genres') or ())
        incompat = set(base.get('incompatible_genres') or ())
        if primary and primary in rec:
            tier, label = 0, '本类型首选'
        elif type_set & rec:
            tier, label = 1, '契合副类型'
        elif base['id'] == fallback_id:
            tier, label = 1 if not normalized else 2, '通用稳健'
        elif primary and primary in incompat:
            tier, label = 3, '跨题材慎用'
        else:
            tier, label = 2, '按需可选'
        item = deepcopy(base)
        item['relevance_tier'] = tier
        item['relevance_label'] = label
        item['recommended'] = tier == 0 or (not normalized and base['id'] == fallback_id)
        ranked.append((tier, idx, item))
    ranked.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in ranked]


def normalize_spec_knobs(
    knobs_schema: dict[str, dict[str, Any]],
    raw: dict[str, Any] | None,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a domain's orthogonal knob values against its schema."""
    src = raw if isinstance(raw, dict) else {}
    out: dict[str, Any] = {}
    for knob_key, meta in knobs_schema.items():
        allowed = {opt['id'] for opt in meta['options']}
        if meta.get('multi'):
            vals = src.get(knob_key, defaults.get(knob_key, []))
            if not isinstance(vals, (list, tuple)):
                vals = list(defaults.get(knob_key, []))
            cleaned: list[str] = []
            for v in vals:
                sv = str(v).strip()
                if sv in allowed and sv not in cleaned:
                    cleaned.append(sv)
            out[knob_key] = cleaned
        else:
            val = str(src.get(knob_key) or defaults.get(knob_key) or '').strip()
            if val not in allowed:
                val = str(defaults.get(knob_key) or meta['options'][0]['id'])
            out[knob_key] = val
    return out


def knob_option_map(knobs_schema: dict[str, dict[str, Any]]) -> dict[str, dict[str, dict[str, str]]]:
    return {
        k: {opt['id']: opt for opt in meta['options']}
        for k, meta in knobs_schema.items()
    }


def load_spec_file(store: Store, filename: str) -> dict[str, Any] | None:
    path = store.data_file(filename)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        return raw if isinstance(raw, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_spec_file(store: Store, filename: str, spec: dict[str, Any]) -> dict[str, Any]:
    path = store.data_file(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(spec, ensure_ascii=False, indent=2)
    with NamedTemporaryFile('w', encoding='utf-8', dir=str(path.parent), delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
    return deepcopy(spec)


def ensure_craft_fingerprint_table(conn: Any) -> None:
    conn.executescript(CRAFT_FINGERPRINT_SCHEMA)


def _decode_craft_fp_row(row: Any, *, base_names: dict[str, str] | None = None) -> dict[str, Any]:
    item = dict(row)
    domain = item.get('domain') or 'voice'
    base_id = item.get('base_id') or item.get('base_voice_id') or ''
    type_tags = json.loads(item.pop('type_tags_json', '[]') or '[]')
    excluded_types = json.loads(item.pop('excluded_types_json', '[]') or '[]')
    target_funcs_raw = item.pop('target_functions_json', None)
    if target_funcs_raw is None:
        target_funcs_raw = item.pop('scene_functions_json', '[]')
    target_functions = json.loads(target_funcs_raw or '[]')
    body = json.loads(item.pop('body_json', '{}') or '{}')
    result = {
        'id': item['id'],
        'domain': domain,
        'book_id': item['book_id'],
        'structure_version': item['structure_version'],
        'title': item['title'],
        'base_id': base_id,
        'base_name': (base_names or {}).get(base_id, base_id),
        'type_tags': type_tags,
        'excluded_types': excluded_types,
        'target_functions': target_functions,
        'body': body,
        'status': item['status'],
        'created_at': item['created_at'],
        'updated_at': item['updated_at'],
    }
    if domain == 'voice':
        result['base_voice_id'] = base_id
        result['base_voice_name'] = result['base_name']
        result['scene_functions'] = target_functions
    return result


def save_craft_fingerprint(
    conn: Any,
    *,
    domain: str,
    book_id: str,
    structure_version: int,
    title: str,
    base_id: str,
    type_tags: list[str] | tuple[str, ...],
    body: dict[str, Any],
    status: str = 'approved',
    target_functions: list[str] | tuple[str, ...] | None = None,
    ts: str | None = None,
    base_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Persist a plot-free, genre-bounded craft fingerprint into library.db (`craft_fingerprints`)."""
    if domain not in CRAFT_DOMAINS:
        raise ValueError(f'未知的基座指纹域: {domain}')
    ensure_craft_fingerprint_table(conn)
    norm_types = canonical_types(list(type_tags)) if type_tags else []
    excl = excluded_types_for_genres(norm_types)
    funcs = list(dict.fromkeys(
        str(f).strip() for f in (target_functions or body.get('target_functions') or body.get('scene_functions') or ())
        if str(f).strip()
    ))
    stamp = ts or now()
    existing = conn.execute(
        'SELECT id, created_at FROM craft_fingerprints WHERE domain=? AND book_id=? AND structure_version=?',
        (domain, book_id, int(structure_version)),
    ).fetchone()
    prefix = {'world': 'wfp', 'cast': 'cfp', 'plot_pacing': 'pfp', 'voice': 'vfp'}[domain]
    fp_id = existing['id'] if existing else f'{prefix}-{uuid4().hex[:12]}'
    created = existing['created_at'] if existing else stamp
    clean_body = {
        'dimensions': {str(k): str(v).strip()[:240] for k, v in (body.get('dimensions') or {}).items() if str(v).strip()},
        'techniques': [str(x).strip()[:200] for x in (body.get('techniques') or ()) if str(x).strip()][:6],
        'drift_guards': [str(x).strip()[:180] for x in (body.get('drift_guards') or ()) if str(x).strip()][:5],
        'function_notes': {
            str(k): str(v).strip()[:200]
            for k, v in (body.get('function_notes') or body.get('scene_function_notes') or {}).items()
            if str(v).strip()
        },
        'evidence_spans': list(body.get('evidence_spans') or ())[:6],
    }
    if existing:
        conn.execute(
            '''UPDATE craft_fingerprints
               SET title=?, base_id=?, type_tags_json=?, excluded_types_json=?,
                   target_functions_json=?, body_json=?, status=?, updated_at=?
               WHERE id=?''',
            (
                title.strip()[:80], base_id, json.dumps(norm_types, ensure_ascii=False),
                json.dumps(excl, ensure_ascii=False), json.dumps(funcs, ensure_ascii=False),
                json.dumps(clean_body, ensure_ascii=False), status, stamp, fp_id,
            ),
        )
    else:
        conn.execute(
            '''INSERT INTO craft_fingerprints(
                 id, domain, book_id, structure_version, title, base_id,
                 type_tags_json, excluded_types_json, target_functions_json,
                 body_json, status, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                fp_id, domain, book_id, int(structure_version), title.strip()[:80], base_id,
                json.dumps(norm_types, ensure_ascii=False), json.dumps(excl, ensure_ascii=False),
                json.dumps(funcs, ensure_ascii=False), json.dumps(clean_body, ensure_ascii=False),
                status, created, stamp,
            ),
        )
    row = conn.execute('SELECT * FROM craft_fingerprints WHERE id=?', (fp_id,)).fetchone()
    return _decode_craft_fp_row(row, base_names=base_names)


def list_craft_fingerprints(
    conn: Any,
    *,
    domain: str | None = None,
    types: list[str] | tuple[str, ...] | None = None,
    status: str = 'approved',
    include_incompatible: bool = False,
    base_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """List craft fingerprints from `craft_fingerprints` (merging legacy `voice_fingerprints` when applicable)."""
    ensure_craft_fingerprint_table(conn)
    params: list[Any] = []
    clauses: list[str] = []
    if domain:
        clauses.append('domain=?')
        params.append(domain)
    if status:
        clauses.append('status=?')
        params.append(status)
    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    rows = conn.execute(
        f'SELECT * FROM craft_fingerprints {where} ORDER BY updated_at DESC, id',
        tuple(params),
    ).fetchall()
    decoded = [_decode_craft_fp_row(r, base_names=base_names) for r in rows]
    seen_ids = {r['id'] for r in decoded}

    # Merge legacy voice_fingerprints seamlessly when domain is None or 'voice'.
    if domain in (None, 'voice'):
        tbl = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='voice_fingerprints'"
        ).fetchone()
        if tbl:
            vrows = conn.execute(
                'SELECT * FROM voice_fingerprints WHERE (?="" OR status=?) ORDER BY updated_at DESC, id',
                (status or '', status or ''),
            ).fetchall()
            for vr in vrows:
                if vr['id'] not in seen_ids:
                    item = _decode_craft_fp_row({**dict(vr), 'domain': 'voice'}, base_names=base_names)
                    decoded.append(item)
                    seen_ids.add(vr['id'])

    if not types:
        return decoded
    norm = canonical_types(list(types))
    out: list[dict[str, Any]] = []
    for fp in decoded:
        compat = is_fingerprint_compatible(fp, norm)
        if not compat and not include_incompatible:
            continue
        fp['compatible'] = compat
        exact = bool(set(norm) & set(fp.get('type_tags') or ()))
        fp['match_rank'] = 0 if exact else (1 if compat else 2)
        out.append(fp)
    out.sort(key=lambda r: (r['match_rank'], r['updated_at']), reverse=False)
    return out


def get_craft_fingerprints_by_ids(
    conn: Any,
    ids: list[str] | tuple[str, ...],
    *,
    domain: str | None = None,
    base_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    cleaned = [str(i).strip() for i in ids if str(i).strip()]
    if not cleaned:
        return []
    ensure_craft_fingerprint_table(conn)
    placeholders = ','.join('?' for _ in cleaned)
    params: list[Any] = [*cleaned]
    extra = ''
    if domain:
        extra = ' AND domain=?'
        params.append(domain)
    rows = conn.execute(
        f'SELECT * FROM craft_fingerprints WHERE id IN ({placeholders}){extra}',
        tuple(params),
    ).fetchall()
    by_id = {r['id']: _decode_craft_fp_row(r, base_names=base_names) for r in rows}
    if domain in (None, 'voice'):
        missing = [i for i in cleaned if i not in by_id]
        if missing:
            tbl = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='voice_fingerprints'"
            ).fetchone()
            if tbl:
                m_ph = ','.join('?' for _ in missing)
                vrows = conn.execute(
                    f'SELECT * FROM voice_fingerprints WHERE id IN ({m_ph})',
                    tuple(missing),
                ).fetchall()
                for vr in vrows:
                    by_id[vr['id']] = _decode_craft_fp_row({**dict(vr), 'domain': 'voice'}, base_names=base_names)
    return [by_id[i] for i in cleaned if i in by_id]


def finalize_spec_payload(spec: dict[str, Any]) -> dict[str, Any]:
    """Attach deterministic content sha256 to a compiled spec payload."""
    copy = {k: v for k, v in spec.items() if k != 'sha256'}
    copy['sha256'] = content_sha256(copy)
    return copy


def truncate_lines_to_budget(lines: list[str], max_chars: int) -> str:
    """Join lines cleanly without exceeding max_chars."""
    out: list[str] = []
    used = 0
    for ln in lines:
        text = str(ln).strip()
        if not text:
            continue
        cost = len(text) + (1 if out else 0)
        if used + cost > max_chars:
            remain = max_chars - used - (1 if out else 0)
            if remain >= 24:
                out.append(text[:remain - 1].rstrip() + '…')
            break
        out.append(text)
        used += cost
    return '\n'.join(out)
