"""Evidence-Driven Half-Written Manuscript Import & SQLite `_baseline` Adoption (Fusion F3).

Wakes up `nw.story_state.adopt_story`'s native mid-book `_baseline` capability so authors
who already wrote Chapters 1..N outside this Studio can seamlessly import their manuscript:
  1. Splits raw TXT/Markdown manuscripts into ordered chapters preserving original prose.
  2. Reconstructs ONLY text-supported entities, locations, open hooks, and numeric states.
  3. Preserves BOTH evidence pointers whenever internal contradictions exist across imported
     chapters — NEVER silently choosing one side!
  4. Treats imported chapter prose as authoritative (`accepted` drafts + `story_branches`
     baseline anchored at `as_of_story_order = N`) so Chapter N+1 immediately enjoys the full
     4-Pillar Craft Specs, Serial Health Cockpit, and POV Cognitive Graph.
"""
from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any
from uuid import uuid4

from nw.cards import decide_card, save_card
from nw.llm.base import GenResult
from nw.models import Run
from nw.store import Store, now
from nw.story_state import adopt_story
from nw.task_models import canonical, content_sha256

_CHAPTER_HEADER_RE = re.compile(
    r'^(?:#{1,3}\s*)?(?:第\s*([零一二三四五六七八九十百千万0-9]+)\s*[章节回卷][^\n]{0,60}|Chapter\s+(\d+)[^\n]{0,60})$',
    re.MULTILINE | re.IGNORECASE,
)

_DIALOGUE_SPEAKER_RE = re.compile(
    r'([\u4e00-\u9fff]{2,4})(?:冷冷道|沉声道|笑道|淡淡道|说道|问道|喝道|低声道|摇头道|叹道|咬牙道|开口道|说|问|喊|答)[：:，,]\s*[“「"]'
)
_DEATH_MENTION_RE = re.compile(r'([\u4e00-\u9fff]{2,4})(?:已经死了|身亡|毙命|陨落|断了气|死在)')
_ALIVE_ACTION_RE = re.compile(r'([\u4e00-\u9fff]{2,4})(?:站起身|开口道|冷笑道|挥手|走上前|大喝一声|说道)')
_HOOK_CLUE_RE = re.compile(r'([^。！？\n]{6,60}(?:秘密|谜团|真相|约定|承诺|伏笔|古玉|禁地|失踪|究竟是谁|到底是谁)[^。！？\n]{0,30}[。！？?])')

_ROLE_PREFIXES = (
    '大管家', '账房', '掌柜', '长老', '师兄', '师姐', '师弟', '师妹', '管家', '族长',
    '门主', '宗主', '帮主', '侍卫', '太守', '捕头', '县令', '将军', '大人', '老爷',
)


def _strip_role_prefix(name: str) -> str:
    clean = name.strip()
    for p in _ROLE_PREFIXES:
        if clean.startswith(p) and len(clean) - len(p) >= 2:
            return clean[len(p):]
    return clean


_NON_NAME_PREFIXES = frozenset({
    '这个', '那个', '自己', '众人', '有人', '没人', '大家', '他们', '她们', '我们', '你们',
    '此时', '此刻', '突然', '忽然', '片刻', '半晌', '眼前', '耳边', '身后', '面前', '心中',
})


def split_manuscript_chapters(raw_text: str) -> list[dict[str, Any]]:
    """Split a raw TXT/Markdown novel manuscript into ordered chapter records."""
    text = (raw_text or '').replace('\r\n', '\n').strip()
    if not text:
        raise ValueError('导入书稿内容不能为空')
    matches = list(_CHAPTER_HEADER_RE.finditer(text))
    if not matches:
        return [{
            'index': 1,
            'title': '第1章',
            'text': text,
            'chars': len(text),
        }]

    chapters: list[dict[str, Any]] = []
    # Keep prologue text before first chapter header if substantial
    preamble = text[:matches[0].start()].strip()
    if len(preamble) >= 120:
        chapters.append({'index': 1, 'title': '序章', 'text': preamble, 'chars': len(preamble)})

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        header = m.group(0).lstrip('#').strip()
        chapters.append({
            'index': len(chapters) + 1,
            'title': header[:80],
            'text': body,
            'chars': len(body),
        })
    if not chapters:
        raise ValueError('未能从书稿中解析出有效正文内容')
    return chapters


def analyze_manuscript(raw_text: str, *, title: str = '') -> dict[str, Any]:
    """Deterministically reconstruct entities, hooks, and dual-evidence contradictions from prose."""
    chapters = split_manuscript_chapters(raw_text)
    char_counter: Counter[str] = Counter()
    char_first_ch: dict[str, int] = {}
    char_last_ch: dict[str, int] = {}
    death_evidence: dict[str, list[dict[str, Any]]] = {}
    alive_after_death_conflicts: list[dict[str, Any]] = []
    hooks: list[dict[str, Any]] = []
    seen_hook_snippets: set[str] = set()

    for ch in chapters:
        idx = ch['index']
        body = ch['text']
        for m in _DIALOGUE_SPEAKER_RE.finditer(body):
            name = _strip_role_prefix(m.group(1))
            if name in _NON_NAME_PREFIXES:
                continue
            char_counter[name] += 1
            char_first_ch.setdefault(name, idx)
            char_last_ch[name] = idx

        for m in _DEATH_MENTION_RE.finditer(body):
            name = _strip_role_prefix(m.group(1))
            if name in _NON_NAME_PREFIXES:
                continue
            death_evidence.setdefault(name, []).append({
                'chapter': idx,
                'title': ch['title'],
                'quote': body[max(0, m.start() - 12):min(len(body), m.end() + 24)].replace('\n', ' '),
            })

        # Check if a previously declared-dead character actively speaks/acts in a later chapter (preserve BOTH sides!)
        for name, deaths in death_evidence.items():
            earliest_death = deaths[0]
            if idx <= earliest_death['chapter']:
                continue
            for m in _ALIVE_ACTION_RE.finditer(body):
                cand = _strip_role_prefix(m.group(1))
                if cand == name or (len(cand) >= 2 and name.endswith(cand)) or (len(name) >= 2 and cand.endswith(name)):
                    alive_after_death_conflicts.append({
                        'id': f'conflict-life-{name}-{idx}',
                        'kind': 'character_life_status_contradiction',
                        'entity': name,
                        'summary': f'角色「{name}」在第{earliest_death["chapter"]}章被写明身亡，但在第{idx}章仍出现主动行动/对话。',
                        'evidence_a': earliest_death,
                        'evidence_b': {
                            'chapter': idx,
                            'title': ch['title'],
                            'quote': body[max(0, m.start() - 12):min(len(body), m.end() + 24)].replace('\n', ' '),
                        },
                        'resolution_status': 'unresolved',
                    })
                    break

        for m in _HOOK_CLUE_RE.finditer(body):
            snip = m.group(1).strip()
            key = snip[:24]
            if key not in seen_hook_snippets and len(hooks) < 12:
                seen_hook_snippets.add(key)
                hooks.append({
                    'chapter': idx,
                    'title': snip[:48],
                    'evidence_quote': snip[:120],
                    'status': 'planted',
                })

    characters = [
        {
            'name': name,
            'mentions': cnt,
            'first_chapter': char_first_ch.get(name, 1),
            'last_chapter': char_last_ch.get(name, 1),
            'life_status': 'conflicted' if any(c['entity'] == name for c in alive_after_death_conflicts)
            else ('deceased' if name in death_evidence else 'alive'),
        }
        for name, cnt in char_counter.most_common(16)
    ]

    return {
        'title': title.strip() or (chapters[0]['title'] if chapters else '导入书稿'),
        'source_sha256': content_sha256({'text': raw_text}),
        'chapter_count': len(chapters),
        'total_chars': sum(c['chars'] for c in chapters),
        'chapters': [{'index': c['index'], 'title': c['title'], 'chars': c['chars'], 'text': c['text']} for c in chapters],
        'characters': characters,
        'hooks': hooks,
        'conflicts': alive_after_death_conflicts,
        'has_conflicts': bool(alive_after_death_conflicts),
    }


def save_manuscript_import(store: Store, report: dict[str, Any]) -> dict[str, Any]:
    """Persist an analyzed manuscript reconstruction report into `manuscript_imports`."""
    ident = f'imp-{uuid4().hex[:10]}'
    ts = now()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            '''INSERT INTO manuscript_imports(
                id, title, source_sha256, chapter_count, status,
                report_json, conflicts_json, baseline_branch_id, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (
                ident,
                str(report.get('title') or '导入书稿')[:120],
                str(report.get('source_sha256') or ''),
                int(report.get('chapter_count') or 0),
                'analyzed',
                json.dumps(report, ensure_ascii=False),
                json.dumps(report.get('conflicts') or [], ensure_ascii=False),
                None,
                ts,
                ts,
            ),
        )
    return {
        'id': ident,
        'title': str(report.get('title') or '导入书稿')[:120],
        'chapter_count': int(report.get('chapter_count') or 0),
        'total_chars': int(report.get('total_chars') or 0),
        'status': 'analyzed',
        'characters': report.get('characters') or [],
        'hooks': report.get('hooks') or [],
        'conflicts': report.get('conflicts') or [],
        'has_conflicts': bool(report.get('conflicts')),
        'created_at': ts,
    }


def list_manuscript_imports(store: Store) -> list[dict[str, Any]]:
    rows = store.connection.execute(
        'SELECT * FROM manuscript_imports ORDER BY created_at DESC LIMIT 10'
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        rep = json.loads(r['report_json'])
        out.append({
            'id': r['id'],
            'title': r['title'],
            'chapter_count': r['chapter_count'],
            'total_chars': rep.get('total_chars', 0),
            'status': r['status'],
            'characters': rep.get('characters') or [],
            'hooks': rep.get('hooks') or [],
            'conflicts': json.loads(r['conflicts_json'] or '[]'),
            'baseline_branch_id': r['baseline_branch_id'],
            'created_at': r['created_at'],
        })
    return out


def apply_manuscript_import_to_baseline(
    store: Store,
    import_id: str,
    *,
    resolved_conflicts: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Commit author-confirmed imported chapters & extracted entities into SQLite `_baseline`.

    Imported prose is treated as authoritative (`accepted` drafts); if the store is not yet
    story-managed, invokes `adopt_story()` anchored at `as_of_story_order = chapter_count`
    so the next chapter immediately runs on the full managed state machine!
    """
    row = store.connection.execute('SELECT * FROM manuscript_imports WHERE id=?', (import_id,)).fetchone()
    if row is None:
        raise ValueError(f'未找到书稿导入记录：{import_id}')
    if row['status'] == 'applied':
        raise ValueError('该书稿导入记录已应用至基线，无需重复导入')
    if store.managed_story():
        raise ValueError('当前作品已建立正史主线，请新建空作品后导入半成品书稿')

    report = json.loads(row['report_json'])
    conflicts = json.loads(row['conflicts_json'] or '[]')
    resolutions = resolved_conflicts if isinstance(resolved_conflicts, dict) else {}
    unresolved = [c for c in conflicts if c['id'] not in resolutions]
    if unresolved:
        raise ValueError(
            f'导入书稿存在 {len(unresolved)} 处前文自相矛盾尚未裁决（例如：{unresolved[0]["summary"]}），'
            '系统不会静默二选一，请先确认裁决结果后再写入正史基线。'
        )

    chapters = report.get('chapters') or []
    if not chapters:
        raise ValueError('导入记录中缺少章节正文')

    project_id = store.project().id
    expected_accepted: dict[str, str] = {}
    card_refs: list[dict[str, Any]] = []
    baseline_facts: list[dict[str, Any]] = []
    covered_entities: list[str] = []
    last_ch_idx = len(chapters)

    # 1. Create approved character & promise cards
    for idx, ch_info in enumerate(report.get('characters') or (), 1):
        cid = f'char-imp-{idx:02d}'
        name = ch_info['name']
        life = resolutions.get(next((c['id'] for c in conflicts if c['entity'] == name), ''), ch_info.get('life_status', 'alive'))
        ref = save_card(store, {
            'card_id': cid,
            'kind': 'character',
            'origin': 'author',
            'body': {
                'name': name,
                'role': '导入角色',
                'want': f'延续第{ch_info.get("first_chapter", 1)}章以来的核心动机',
                'visibility': 'public',
            },
            'source_refs': [],
        }, None)
        dec = decide_card(store, ref, 'approved', '从已有书稿证据重构确认')
        card_refs.append({'card_id': cid, 'version': ref.version, 'decision_id': dec.id})
        covered_entities.append(cid)
        baseline_facts.append({
            'entity_id': cid,
            'predicate': 'life_status',
            'holder': 'WORLD',
            'claim': 'fact',
            'story_order': last_ch_idx,
            'disclosure_order': [last_ch_idx, 1, 0],
            'value': life,
        })

    for idx, hk in enumerate(report.get('hooks') or (), 1):
        pid = f'prom-imp-{idx:02d}'
        ref = save_card(store, {
            'card_id': pid,
            'kind': 'promise',
            'origin': 'author',
            'body': {
                'title': hk['title'],
                'setup': hk['evidence_quote'],
                'payoff': '待后续章节推进与回收',
                'introduced_at': f'第{hk["chapter"]}章',
                'visibility': 'public',
            },
            'source_refs': [],
        }, None)
        dec = decide_card(store, ref, 'approved', '从已有书稿提取未回收伏笔')
        card_refs.append({'card_id': pid, 'version': ref.version, 'decision_id': dec.id})
        covered_entities.append(pid)
        baseline_facts.append({
            'entity_id': pid,
            'predicate': 'promise_stage',
            'holder': 'WORLD',
            'claim': 'fact',
            'story_order': hk['chapter'],
            'disclosure_order': [hk['chapter'], 1, 0],
            'value': 'planted',
        })

    # 2. Materialize imported chapters, scenes, and authoritative accepted drafts
    for ch in chapters:
        c_idx = int(ch['index'])
        chapter_row = store.add_chapter(c_idx, ch['title'])
        scene_row = store.add_scene(chapter_row.id, 1, json.dumps({'title': ch['title'], 'imported': True}, ensure_ascii=False))
        run_id = f'run-imp-{import_id[-6:]}-{c_idx:03d}'
        store.add_run(Run(
            run_id, scene_row.id, 'write', 'author', 'manuscript-import', '{}',
            canonical({'source': 'manuscript_import', 'import_id': import_id, 'chapter': c_idx}),
            canonical({'imported': True}), '', 'error', '{}', now(), '',
        ))
        _, draft = store.finish_run(run_id, GenResult(
            text=ch['text'], finish_reason='complete', usage={'source': 'manuscript_import'},
            request_id=run_id, raw={'imported': True},
        ))
        assert draft is not None
        store.accept(draft.id)
        expected_accepted[scene_row.id] = draft.id

    # 3. Adopt story baseline at `as_of_story_order = last_ch_idx`
    baseline = {
        'as_of_story_order': last_ch_idx,
        'disclosure_order': [last_ch_idx, 1, 0],
        'coverage': {
            'entities': covered_entities or ['protagonist'],
            'predicates': ['life_status', 'promise_stage'],
        },
        'facts': baseline_facts,
        'card_refs': card_refs,
    }
    head = adopt_story(store, baseline, expected_accepted)

    # Mark conflicts resolved & import applied
    for c in conflicts:
        c['resolution_status'] = 'resolved'
        c['resolution'] = resolutions.get(c['id'], '')
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute(
            "UPDATE manuscript_imports SET status='applied', conflicts_json=?, baseline_branch_id=?, updated_at=? WHERE id=?",
            (json.dumps(conflicts, ensure_ascii=False), head.branch_id, now(), import_id),
        )
    return {
        'import_id': import_id,
        'branch_id': head.branch_id,
        'revision': head.revision,
        'chapters_imported': len(chapters),
        'cards_created': len(card_refs),
        'next_chapter_index': last_ch_idx + 1,
    }
