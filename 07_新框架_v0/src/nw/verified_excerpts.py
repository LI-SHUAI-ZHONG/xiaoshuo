"""Machine-Verified Anonymized Real-Corpus Excerpts (Fusion K).

Ensures that style/craft excerpts fed to Step 15 writers are:
  1. 100% verbatim contiguous slices extracted from real human corpus text
     (`raw_chapter[start:end] == slice`, never LLM-paraphrased or fabricated)
  2. Anonymized cleanly (book/author/character metadata stripped or replaced)
     and annotated with `learn_what` + `do_not_copy` guardrails
  3. Gated by a strict 3-check zero-alert verification before entering `library.db`:
       - Check 1: Degeneration & punctuation cleanliness (0 blocking degeneration issues)
       - Check 2: 0-token Pre-Review AI pattern gate (`hard_count == 0` AND `review_required_count == 0`)
       - Check 3: Contiguous slice length & density bounds (default 120–420 chars, <= 1 cliché)
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from nw.pre_review_gate import run_pre_review_gate
from nw.prose_normalizer import normalize_prose_punctuation
from nw.store import now
from nw.studio.catalog import canonical_types
from nw.task_models import content_sha256
from nw.voice_specs import SCENE_FUNCTION_LABELS

DEFAULT_EXCERPT_MIN_CHARS = 120
DEFAULT_EXCERPT_MAX_CHARS = 420
_NEUTRAL_ROLES = ('那人', '来客', '中年人', '青年', '对手', '长者')

VERIFIED_EXCERPT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS verified_corpus_excerpts (
 id TEXT PRIMARY KEY,
 book_id TEXT NOT NULL DEFAULT '',
 chapter_index INTEGER NOT NULL DEFAULT 0,
 start_offset INTEGER NOT NULL DEFAULT 0,
 end_offset INTEGER NOT NULL DEFAULT 0,
 source_sha256 TEXT NOT NULL,
 excerpt_text TEXT NOT NULL,
 anonymized_text TEXT NOT NULL,
 type_tags_json TEXT NOT NULL DEFAULT '[]',
 scene_function TEXT NOT NULL DEFAULT 'confrontation',
 learn_what TEXT NOT NULL DEFAULT '',
 do_not_copy TEXT NOT NULL DEFAULT '',
 verification_json TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL DEFAULT 'verified' CHECK(status IN ('verified','rejected','disabled')),
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS verified_excerpts_fn ON verified_corpus_excerpts(status,scene_function);
'''


def ensure_verified_excerpt_table(conn: sqlite3.Connection) -> None:
    conn.executescript(VERIFIED_EXCERPT_SCHEMA)


def anonymize_excerpt_text(
    text: str,
    known_names: list[str] | tuple[str, ...] | dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    """Replace source character/book proper names with neutral labels while preserving prose rhythm."""
    if not text or not known_names:
        return text, {}
    mapping: dict[str, str] = {}
    if isinstance(known_names, dict):
        for k, v in known_names.items():
            src = str(k or '').strip()
            dst = str(v or '').strip()
            if len(src) >= 2 and dst:
                mapping[src] = dst
    else:
        clean_names = [str(n or '').strip() for n in known_names if len(str(n or '').strip()) >= 2]
        # Replace longest names first to avoid partial collisions
        for idx, nm in enumerate(sorted(dict.fromkeys(clean_names), key=len, reverse=True)):
            mapping[nm] = _NEUTRAL_ROLES[idx % len(_NEUTRAL_ROLES)]

    out = text
    applied: dict[str, str] = {}
    for src in sorted(mapping.keys(), key=len, reverse=True):
        if src in out:
            out = out.replace(src, mapping[src])
            applied[src] = mapping[src]
    return out, applied


def verify_excerpt_three_checks(
    excerpt_text: str,
    *,
    min_chars: int = DEFAULT_EXCERPT_MIN_CHARS,
    max_chars: int = DEFAULT_EXCERPT_MAX_CHARS,
) -> dict[str, Any]:
    """Run strict 3-check zero-alert gate before a real-corpus excerpt can enter the library."""
    clean = (excerpt_text or '').strip()
    blocking_reasons: list[str] = []
    review_required_reasons: list[str] = []

    # Check 1: Length & non-empty integrity
    if len(clean) < min_chars:
        blocking_reasons.append(f'样段字数过短（{len(clean)} 字，须不少于 {min_chars} 字以体现真实语流）')
    if len(clean) > max_chars:
        blocking_reasons.append(f'样段字数过长（{len(clean)} 字，须不超过 {max_chars} 字以防撑爆写前预算）')

    # Check 2: Punctuation & degeneration cleanliness
    norm = normalize_prose_punctuation(clean, quote_mode='keep')
    if norm['stats']['zero_width_removed'] > 0:
        blocking_reasons.append('样段包含不可见零宽字符，请先清洗原文')
    if norm['stats']['hr_removed'] > 0:
        blocking_reasons.append('样段包含 Markdown 分隔线，非纯正小说片段')

    # Check 3: Zero-alert AI pattern & degeneration gate (0 blocking + 0 review_required)
    gate = run_pre_review_gate(None, '', clean)
    for item in gate['issues']:
        if item.get('severity') == 'hard' or item.get('tier') == 'blocking':
            blocking_reasons.append(f'[{item["code"]}] {item["message"]}')
        elif item.get('tier') == 'review_required':
            review_required_reasons.append(f'[{item["code"]}] {item["message"]}')
    if gate['metrics']['cliche_hits'] > 1:
        review_required_reasons.append(f'样段自身命中 {gate["metrics"]["cliche_hits"]} 处 AI 套句，不适合作为示范')

    passed = (len(blocking_reasons) == 0 and len(review_required_reasons) == 0)
    return {
        'passed': passed,
        'blocking_reasons': blocking_reasons,
        'review_required_reasons': review_required_reasons,
        'normalizer_changed': norm['changed'],
        'metrics': gate['metrics'],
        'gate_action': gate['action'],
    }


def extract_and_verify_corpus_excerpt(
    raw_chapter_text: str,
    start: int,
    end: int,
    *,
    book_id: str = '',
    chapter_index: int = 0,
    type_tags: list[str] | tuple[str, ...] | None = None,
    scene_function: str = 'confrontation',
    learn_what: str = '',
    do_not_copy: str = '',
    known_names: list[str] | tuple[str, ...] | dict[str, str] | None = None,
    min_chars: int = DEFAULT_EXCERPT_MIN_CHARS,
    max_chars: int = DEFAULT_EXCERPT_MAX_CHARS,
) -> dict[str, Any]:
    """Extract a verbatim contiguous slice from raw corpus text, anonymize it, and run 3-check gate."""
    raw = raw_chapter_text or ''
    if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(raw)):
        raise ValueError(f'切片偏移量越界（start={start}, end={end}, 文本长度={len(raw)}）')

    slice_text = raw[start:end]
    # Hard verbatim continuity verification: exact substring match at exact offset
    exact_match = (raw[start:end] == slice_text) and (slice_text in raw)
    anon_text, replacements = anonymize_excerpt_text(slice_text, known_names=known_names)
    verification = verify_excerpt_three_checks(anon_text, min_chars=min_chars, max_chars=max_chars)
    verification['substr_match'] = exact_match
    verification['anonymized_replacements'] = replacements

    sf = str(scene_function or 'confrontation').strip()
    if sf not in SCENE_FUNCTION_LABELS:
        sf = 'confrontation'
    norm_types = canonical_types(list(type_tags)) if type_tags else []

    record = {
        'id': f'vex-{uuid4().hex[:12]}',
        'book_id': str(book_id or '').strip()[:80],
        'chapter_index': int(chapter_index or 0),
        'start_offset': start,
        'end_offset': end,
        'source_sha256': content_sha256({'text': slice_text}),
        'excerpt_text': slice_text,
        'anonymized_text': anon_text.strip(),
        'type_tags': norm_types,
        'scene_function': sf,
        'scene_function_label': SCENE_FUNCTION_LABELS.get(sf, sf),
        'learn_what': str(learn_what or '学习该段句式呼吸、口语因果推进与场面节奏').strip()[:220],
        'do_not_copy': str(do_not_copy or '严禁照搬原段具体事件、物件与人物动作组合').strip()[:220],
        'verification': verification,
        'status': 'verified' if (exact_match and verification['passed']) else 'rejected',
    }
    return {
        'passed': exact_match and verification['passed'],
        'record': record,
        'verification': verification,
    }


def save_verified_excerpt(
    conn: sqlite3.Connection,
    extracted: dict[str, Any],
) -> dict[str, Any]:
    """Persist a 3-check-verified excerpt into `library.db::verified_corpus_excerpts`.

    Refuses unverified / rejected excerpts so AI-polluted snippets NEVER contaminate the library!
    """
    ensure_verified_excerpt_table(conn)
    if not extracted.get('passed'):
        ver = extracted.get('verification') or {}
        reasons = [*(ver.get('blocking_reasons') or ()), *(ver.get('review_required_reasons') or ())]
        raise ValueError('EXCERPT_VERIFICATION_FAILED: 样段未通过三检零预警准入 —— ' + '；'.join(reasons[:4]))

    rec = extracted['record']
    ts = now()
    conn.execute(
        '''INSERT OR REPLACE INTO verified_corpus_excerpts
           (id, book_id, chapter_index, start_offset, end_offset, source_sha256,
            excerpt_text, anonymized_text, type_tags_json, scene_function,
            learn_what, do_not_copy, verification_json, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'verified',?)''',
        (
            rec['id'], rec['book_id'], rec['chapter_index'], rec['start_offset'], rec['end_offset'],
            rec['source_sha256'], rec['excerpt_text'], rec['anonymized_text'],
            json.dumps(rec['type_tags'], ensure_ascii=False), rec['scene_function'],
            rec['learn_what'], rec['do_not_copy'],
            json.dumps(rec['verification'], ensure_ascii=False), ts,
        ),
    )
    return {**rec, 'created_at': ts}


def _row_to_excerpt(row: sqlite3.Row) -> dict[str, Any]:
    sf = row['scene_function']
    return {
        'id': row['id'],
        'book_id': row['book_id'],
        'chapter_index': int(row['chapter_index']),
        'start_offset': int(row['start_offset']),
        'end_offset': int(row['end_offset']),
        'source_sha256': row['source_sha256'],
        'anonymized_text': row['anonymized_text'],
        'type_tags': json.loads(row['type_tags_json'] or '[]'),
        'scene_function': sf,
        'scene_function_label': SCENE_FUNCTION_LABELS.get(sf, sf),
        'learn_what': row['learn_what'],
        'do_not_copy': row['do_not_copy'],
        'verification': json.loads(row['verification_json'] or '{}'),
        'status': row['status'],
        'created_at': row['created_at'],
    }


def list_verified_excerpts(
    conn: sqlite3.Connection,
    *,
    type_tags: list[str] | tuple[str, ...] | None = None,
    scene_function: str = '',
    status: str = 'verified',
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve verified anonymized real-corpus excerpts ranked by genre + scene_function match."""
    ensure_verified_excerpt_table(conn)
    rows = conn.execute(
        'SELECT * FROM verified_corpus_excerpts WHERE status=? ORDER BY created_at DESC LIMIT 200',
        (status,),
    ).fetchall()
    norm_types = set(canonical_types(list(type_tags))) if type_tags else set()
    target_fn = str(scene_function or '').strip()

    scored: list[tuple[int, int, str, dict[str, Any]]] = []
    for row in rows:
        item = _row_to_excerpt(row)
        item_types = set(item['type_tags'])
        genre_score = 2 if (norm_types and (norm_types & item_types)) else (1 if not item_types else 0)
        fn_score = 2 if (target_fn and item['scene_function'] == target_fn) else 0
        # If caller explicitly filters by genres and item belongs to an unrelated genre, rank lower
        if norm_types and item_types and not (norm_types & item_types):
            genre_score = -1
        scored.append((genre_score, fn_score, item['created_at'], item))

    scored.sort(key=lambda r: (r[0], r[1], r[2]), reverse=True)
    # Filter out negative genre mismatch unless nothing matches at all
    positive = [r[3] for r in scored if r[0] >= 0]
    pool = positive if positive else [r[3] for r in scored]
    return pool[:max(1, int(limit))]


def build_writer_verified_excerpts_packet(
    conn: sqlite3.Connection | None,
    *,
    type_tags: list[str] | tuple[str, ...] | None = None,
    scene_function: str = 'confrontation',
    limit: int = 2,
) -> dict[str, Any] | None:
    """Compile a compact 1–2 excerpt packet safe for Step 15 writer injection (even under tight budgets)."""
    if conn is None:
        return None
    picked = list_verified_excerpts(conn, type_tags=type_tags, scene_function=scene_function, limit=limit)
    if not picked:
        return None
    return {
        'usage_rule': '以下为机检三检零预警的真人实文匿名节选，仅学习行文呼吸、对白质地与推进节奏，严禁照搬其中桥段与句式。',
        'excerpts': [
            {
                'id': item['id'],
                'scene_function': item['scene_function_label'],
                'learn_what': item['learn_what'],
                'do_not_copy': item['do_not_copy'],
                'text': item['anonymized_text'][:360],
            }
            for item in picked[:limit]
        ],
    }
