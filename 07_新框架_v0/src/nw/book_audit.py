"""Zero-Token Whole-Book 12-Dimension Mechanical Audit Engine (Fusion M).

Fuses the mechanical whole-book reader audit innovations from `chinese-novelist-skill`
(`scripts/visual/analysis.mjs`) directly onto our SQLite v15 Store (`character` cards,
`accepted` chapter texts, `chapter_summaries`, `serial_chapter_metrics`, `override_ledger`):

  1. Numbering continuity (gaps / duplicates)
  2. Chapter word floor check
  3. Quote balance (`「」`, `『』`, `“”`)
  4. Summary / content freshness hash check (`stale_after_edit`)
  5. Summary coverage
  6. Rhythm word-count drift (`>=1.45x` or `<=0.62x` of book median)
  7. Dialogue-ratio plunge (`<0.4x` of book median when book median >= 12%)
  8. Character presence matrix + consecutive gap (`>=4` chapters) + tail-25% disappearance
  9. Character catchphrase/voice fulfillment with interrupted-dialogue stitching (`<=12` chars)
  10. Chapter ending hook shape (`<=2` sentences & `<=140` CJK chars isolated paragraph)
  11. O(N) two-stage seed-and-extend repeated-phrase / motif-tic detector (4–12 CJK chars)
  12. Consecutive hook-type monotony detector

Runs in milliseconds with ZERO LLM tokens and automatically exports top steering warnings
to `serial_health` / `06 plot_design`!
"""
from __future__ import annotations

import hashlib
import json
import re
from statistics import median
from typing import Any

from nw.cards import read_card
from nw.craft_evolution import _accepted_chapter_texts
from nw.override_ledger import list_overrides
from nw.store import Store
from nw.story_models import CardRef
from nw.story_state import current_head, revision_state

_CJK_RE = re.compile(r'[\u4e00-\u9fff]')
_CJK_RUN_RE = re.compile(r'[\u4e00-\u9fff]+')
_STRIP_PUNCT_RE = re.compile(r'[。！？…，、；：\s「」『』“”"\']')

# Pan-titles and meta notes that must never be counted as character aliases
_NOTE_WORDS = frozenset({
    '已故', '去世', '回忆', '番外', '幼年', '老年', '拟写', '待定', '原型',
    '大哥', '大姐', '师兄', '师姐', '师父', '师傅', '父亲', '母亲', '爸爸', '妈妈',
    '爷爷', '奶奶', '叔叔', '舅舅', '姑姑', '哥哥', '姐姐', '弟弟', '妹妹', '儿子',
    '女儿', '妻子', '丈夫', '老板', '老大', '上司', '下属', '同事', '朋友', '助手',
    '保镖', '管家', '女主', '男主', '主角', '反派', '配角', '原作', '原创', '同人',
    '私设', '改编', '衍生', '客串', '龙套', '次要', '主要',
})

_SEVERITY_RANK = {'fix': 0, 'advise': 1, 'note': 2}


def _cjk_count(text: str) -> int:
    return len(_CJK_RE.findall(text or ''))


def _sha12(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()[:12]


def _is_valid_alias(val: str) -> bool:
    s = str(val or '').strip()
    if not s or s in _NOTE_WORDS:
        return False
    if re.fullmatch(r'[\u4e00-\u9fff]{1,4}', s):
        return True
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z'’\-. ·]{2,23}", s))


def _extract_catchphrases_from_text(text: str) -> list[str]:
    found: list[str] = []
    if not text:
        return found
    for m in re.finditer(r'[「“"『]([^」”"』]{1,20})[」”"』]', text):
        before = text[max(0, m.start() - 6):m.start()]
        if re.search(r'(?:极少|从不|不用|避免|没有|别说|忌)[^」”]{0,3}$', before):
            continue
        after = text[m.end():m.end() + 1]
        if after in ('：', ':'):
            continue
        cleaned = _STRIP_PUNCT_RE.sub('', m.group(1))
        if 1 <= len(cleaned) <= 14 and re.fullmatch(r'[\u4e00-\u9fff]+', cleaned) and cleaned not in found:
            found.append(cleaned)
    return found


def load_cast_from_store(store: Store, *, branch: str = 'main') -> list[dict[str, Any]]:
    """Load canonical character roster (name, role, aliases, catchphrases) from approved SQLite cards."""
    cast: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    cards_to_read: list[dict[str, Any]] = []
    if store.managed_story():
        head = current_head(store, branch)
        snap = revision_state(store, head)
        for ref in snap.get('settings') or ():
            card = read_card(store, CardRef(ref['card_id'], ref['version']))
            if card.get('kind') == 'character':
                cards_to_read.append(card.get('body') or {})
    else:
        rows = store.connection.execute(
            "SELECT card_id, body_json FROM cards WHERE kind='character' ORDER BY version DESC"
        ).fetchall()
        seen_ids: set[str] = set()
        for r in rows:
            if r['card_id'] in seen_ids:
                continue
            seen_ids.add(r['card_id'])
            cards_to_read.append(json.loads(r['body_json'] or '{}'))

    for body in cards_to_read:
        if not isinstance(body, dict):
            continue
        raw_name = str(body.get('name') or '').strip()
        if not raw_name:
            continue
        # Handle inline alias parentheses like "苏晚（阿晚）"
        m = re.match(r'^([^（(]+?)(?:[（(](.*)[）)])?\s*$', raw_name)
        name = m.group(1).strip() if m else raw_name
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        role_raw = str(body.get('role') or '').strip()
        role = '主角' if any(k in role_raw for k in ('主角', '男主', '女主', 'protagonist')) else (
            '反派' if any(k in role_raw for k in ('反派', '对手', '敌', 'antagonist')) else '配角'
        )
        aliases: list[str] = []
        if m and m.group(2):
            for tok in re.split(r'[,，、/]', m.group(2)):
                if _is_valid_alias(tok):
                    aliases.append(tok.strip())
        for raw_al in (body.get('aliases') or ()):
            if isinstance(raw_al, str) and _is_valid_alias(raw_al) and raw_al.strip() != name and raw_al.strip() not in aliases:
                aliases.append(raw_al.strip())

        catchphrases: list[str] = []
        raw_cp = body.get('catchphrases')
        if isinstance(raw_cp, list):
            for item in raw_cp:
                cleaned = _STRIP_PUNCT_RE.sub('', str(item or ''))
                if 1 <= len(cleaned) <= 14 and re.fullmatch(r'[\u4e00-\u9fff]+', cleaned) and cleaned not in catchphrases:
                    catchphrases.append(cleaned)
        elif isinstance(raw_cp, str):
            for item in _extract_catchphrases_from_text(raw_cp):
                if item not in catchphrases:
                    catchphrases.append(item)
        for field in ('voice', 'speech_style', 'speaking_style', 'verbal_tics'):
            val = body.get(field)
            if isinstance(val, str):
                for item in _extract_catchphrases_from_text(val):
                    if item not in catchphrases:
                        catchphrases.append(item)

        cast.append({
            'name': name,
            'role': role,
            'aliases': aliases,
            'catchphrases': catchphrases,
        })
    return cast


def quote_balance(text: str) -> dict[str, Any]:
    pairs = (('「', '」'), ('『', '』'), ('“', '”'))
    broken = [op for op, cl in pairs if text.count(op) != text.count(cl)]
    return {'balanced': len(broken) == 0, 'broken': broken}


def ending_shape(text: str) -> dict[str, Any]:
    paras = [p.strip() for p in re.split(r'\n{2,}', (text or '').strip()) if p.strip()]
    if not paras:
        paras = [ln.strip() for ln in (text or '').splitlines() if ln.strip()]
    last = paras[-1] if paras else ''
    plain = re.sub(r'^[>#\s\-*]+', '', last)
    plain = re.sub(r'[*_`「」『』“”"\']', '', plain)
    sentences = [s.strip() for s in re.split(r'[。！？!?…]+', plain) if s.strip()]
    return {'text': plain[:160], 'chars': _cjk_count(plain), 'sentences': len(sentences)}


def repeated_phrases(
    chapter_texts: list[str],
    *,
    min_length: int = 4,
    max_length: int = 12,
    floor: int = 4,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """O(N) two-stage seed-and-extend repeated CJK phrase detector across the whole book."""
    runs: list[str] = []
    for text in chapter_texts:
        for m in _CJK_RUN_RE.finditer(text or ''):
            r = m.group(0)
            if len(r) >= min_length:
                runs.append(r)

    positions: dict[str, list[tuple[int, int]]] = {}
    for r_idx, run in enumerate(runs):
        for at in range(0, len(run) - min_length + 1):
            gram = run[at:at + min_length]
            positions.setdefault(gram, []).append((r_idx, at))

    best: dict[str, int] = {}
    for occs in positions.values():
        cnt = len(occs)
        if cnt < floor:
            continue
        length = min_length
        while length < max_length:
            nxt: str | None = None
            agree = True
            for r_idx, at in occs:
                run = runs[r_idx]
                ch = run[at + length] if (at + length) < len(run) else None
                if ch is None or (nxt is not None and ch != nxt):
                    agree = False
                    break
                nxt = ch
            if not agree:
                break
            length += 1
        r0, at0 = occs[0]
        phrase = runs[r0][at0:at0 + length]
        if phrase not in best or cnt > best[phrase]:
            best[phrase] = cnt

    # Suppress strict substrings with identical or lower counts so results stay crisp
    ordered = sorted(best.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    pruned: list[dict[str, Any]] = []
    for phrase, cnt in ordered:
        if any(phrase in kept['phrase'] and cnt <= kept['count'] for kept in pruned):
            continue
        pruned.append({'phrase': phrase, 'count': cnt})
        if len(pruned) >= limit:
            break
    return pruned


def _name_regex(needle: str) -> re.Pattern[str]:
    esc = re.escape(needle)
    if re.search(r'[A-Za-z]', needle):
        return re.compile(rf'(?<![A-Za-z]){esc}(?![A-Za-z])')
    return re.compile(esc)


def compute_presence(cast: list[dict[str, Any]], chapter_texts: list[str]) -> list[dict[str, Any]]:
    all_names = [nm for m in cast for nm in [m['name'], *m.get('aliases', ())]]
    results: list[dict[str, Any]] = []
    for member in cast:
        own_names = set([member['name'], *member.get('aliases', ())])
        names = sorted(own_names, key=len, reverse=True)
        # Mask any OTHER character's strictly longer superstring name (e.g. mask `苏晚晴` before counting `苏晚`)!
        other_superstrings = sorted(
            {
                other for other in all_names
                if other not in own_names and any(len(other) > len(own) and own in other for own in own_names)
            },
            key=len,
            reverse=True,
        )
        counts: list[int] = []
        for text in chapter_texts:
            rest = text or ''
            for sup in other_superstrings:
                pat = _name_regex(sup)
                rest = pat.sub(lambda m: '\u0001' * len(m.group(0)), rest)
            total_ch = 0
            for nm in names:
                pat = _name_regex(nm)
                hits = len(pat.findall(rest))
                if hits:
                    total_ch += hits
                    rest = pat.sub(lambda m: '\u0001' * len(m.group(0)), rest)
            counts.append(total_ch)
        total = sum(counts)
        ch_at = [i for i, n in enumerate(counts) if n > 0]
        results.append({
            **member,
            'counts': counts,
            'total': total,
            'first': ch_at[0] if ch_at else None,
            'last': ch_at[-1] if ch_at else None,
            'appearances': len(ch_at),
        })
    return results


def detect_presence_gaps(
    members: list[dict[str, Any]],
    *,
    gap: int = 4,
    prior_mentions: int = 3,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for member in members:
        if member.get('role') == '主角' or member['total'] < prior_mentions or member['appearances'] == 0:
            continue
        counts = member['counts']
        absent = 0
        seen = 0
        run: dict[str, int] | None = None
        for idx, n in enumerate(counts):
            if n > 0:
                if absent >= gap and seen >= prior_mentions and run is not None:
                    findings.append({'name': member['name'], **run})
                absent = 0
                run = None
                seen += n
            elif seen >= prior_mentions:
                absent += 1
                if absent == gap:
                    run = {'from_idx': idx - gap + 1, 'to_idx': idx, 'chapters': absent}
                elif run is not None:
                    run['to_idx'] = idx
                    run['chapters'] = absent
    return findings


def _count_catchphrase(text: str, phrase: str) -> int:
    """Count catchphrase occurrences, stitching interrupted Chinese dialogue across <=12 char narration beats."""
    raw = text or ''
    merged = re.sub(r'[」”』"][^「“『」”』"\n]{0,12}[「“『"]', '', raw)
    if len(phrase) == 1:
        runs = [
            _STRIP_PUNCT_RE.sub('', m.group(1))
            for m in re.finditer(r'[「“『]([^」”』]*)[」”』]', merged)
        ]
        return sum(r.count(phrase) for r in runs)
    return max(
        raw.count(phrase),
        _STRIP_PUNCT_RE.sub('', raw).count(phrase),
        _STRIP_PUNCT_RE.sub('', merged).count(phrase),
    )


def compute_catchphrase_stats(cast: list[dict[str, Any]], chapter_texts: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for member in cast:
        for phrase in member.get('catchphrases') or ():
            counts = [_count_catchphrase(t, phrase) for t in chapter_texts]
            rows.append({
                'name': member['name'],
                'phrase': phrase,
                'counts': counts,
                'total': sum(counts),
            })
    return rows


def _dialogue_ratio(text: str) -> float:
    total = _cjk_count(text)
    if total == 0:
        return 0.0
    spoken = sum(_cjk_count(m.group(1)) for m in re.finditer(r'[「“『]([^」”』\n]*)[」”』]', text or ''))
    return round(spoken / total, 4)


def run_whole_book_audit(
    store: Store,
    *,
    branch: str = 'main',
    min_chapter_words: int = 1800,
    presence_gap: int = 4,
) -> dict[str, Any]:
    """Run 0-token 12-dimension whole-book mechanical audit against accepted SQLite chapters."""
    ch_texts_map = _accepted_chapter_texts(store, branch)
    chapter_objs = {c.index: c for c in store.list('chapter')}
    ch_indices = sorted(ch_texts_map.keys())
    texts = [ch_texts_map[idx] for idx in ch_indices]
    titles = [chapter_objs[idx].title if idx in chapter_objs else f'第{idx}章' for idx in ch_indices]

    # Chapter summaries & accepted timestamps for freshness checks
    summaries_by_ch: dict[int, dict[str, Any]] = {}
    try:
        for r in store.connection.execute(
            'SELECT chapter_index, summary_text, updated_at FROM chapter_summaries WHERE branch_id=?', (branch,)
        ).fetchall():
            summaries_by_ch[int(r['chapter_index'])] = dict(r)
    except Exception:
        pass

    latest_draft_ts_by_ch: dict[int, str] = {}
    for ch_idx in ch_indices:
        row = store.connection.execute(
            '''SELECT MAX(d.created_at) AS ts
               FROM drafts d JOIN accepted a ON a.draft_id=d.id
               JOIN scenes s ON s.id=a.scene_id JOIN chapters c ON c.id=s.chapter_id
               WHERE c."index"=?''',
            (ch_idx,),
        ).fetchone()
        latest_draft_ts_by_ch[ch_idx] = str(row['ts'] or '') if row else ''

    # Active overrides so authors can intentionally exempt characters/endings
    active_overrides = list_overrides(store, branch_id=branch, status='active', limit=100)
    exempt_codes = {(o.get('constraint_code'), o.get('chapter_index')) for o in active_overrides}

    findings: list[dict[str, Any]] = []

    def add(severity: str, kind: str, chapter: int | None, title: str, detail: str) -> None:
        findings.append({
            'severity': severity,
            'kind': kind,
            'chapter': chapter,
            'title': title,
            'detail': detail,
        })

    # 1. Numbering continuity
    if ch_indices:
        max_ch = max(ch_indices)
        missing_nums = [n for n in range(1, max_ch + 1) if n not in ch_texts_map]
        if missing_nums:
            add('fix', 'numbering', missing_nums[0], f'章节编号断档：缺第 {"、".join(str(x) for x in missing_nums[:6])} 章',
                '已接受正文存在跳章空洞，请核对章节编排与验收状态。')

    # 2, 3, 4, 5. Per-chapter word floor, quote balance, summary coverage & freshness
    rhythm_rows: list[dict[str, Any]] = []
    spoken_total = 0
    char_total = 0
    for idx, ch_no in enumerate(ch_indices):
        text = texts[idx]
        ctitle = titles[idx]
        wc = _cjk_count(text)
        dr = _dialogue_ratio(text)
        char_total += wc
        spoken_total += int(round(wc * dr))
        rhythm_rows.append({'chapter': ch_no, 'title': ctitle, 'words': wc, 'dialogue_ratio': dr, 'level': None})

        if min_chapter_words > 0 and wc < min_chapter_words and ('WORD_FLOOR', ch_no) not in exempt_codes:
            add('fix', 'words', ch_no, f'第{ch_no}章 {ctitle}',
                f'实测 {wc} 汉字，低于设定的单章下限 {min_chapter_words} 字，建议使用诊断式定向扩充补足。')

        qb = quote_balance(text)
        if not qb['balanced']:
            add('fix', 'quote', ch_no, f'第{ch_no}章 {ctitle}',
                f'引号未成对闭合（{"、".join(qb["broken"])} 数量不等），请检查对白排版。')

        sum_row = summaries_by_ch.get(ch_no)
        if not sum_row or not str(sum_row.get('summary_text') or '').strip():
            add('advise', 'summary', ch_no, f'第{ch_no}章 {ctitle}',
                '本章已有接受正文但尚未保存章节摘要，可能影响后续工作记忆承接。')
        elif latest_draft_ts_by_ch.get(ch_no) and str(sum_row.get('updated_at') or '') < latest_draft_ts_by_ch[ch_no]:
            add('advise', 'hash', ch_no, f'第{ch_no}章 {ctitle}',
                '正文在最近一次章节摘要更新后发生改动，摘要指纹可能已过期，建议同步复核。')

    # 6. Rhythm word-count drift
    valid_words = [r['words'] for r in rhythm_rows if r['words'] > 0]
    med_words = int(median(valid_words)) if valid_words else 0
    for r in rhythm_rows:
        if min_chapter_words > 0 and r['words'] < min_chapter_words:
            r['level'] = 'fix'
        elif med_words >= 1000:
            ratio = r['words'] / med_words
            if ratio >= 1.45 or ratio <= 0.62:
                r['level'] = 'advise'
                direction = '明显长于' if r['words'] > med_words else '明显短于'
                add('advise', 'rhythm', r['chapter'], f'第{r["chapter"]}章 {r["title"]}',
                    f'本章 {r["words"]} 字，{direction}全书节奏（中位约 {med_words} 字），请确认是否刻意调速。')

    # 7. Dialogue-ratio plunge
    dial_ratios = sorted(r['dialogue_ratio'] for r in rhythm_rows if r['dialogue_ratio'] > 0)
    med_dial = dial_ratios[len(dial_ratios) // 2] if len(dial_ratios) >= 5 else None
    if med_dial is not None and med_dial >= 0.12:
        for r in rhythm_rows:
            if r['dialogue_ratio'] < med_dial * 0.4:
                add('advise', 'dialogue', r['chapter'], f'第{r["chapter"]}章 {r["title"]}',
                    f'对白仅占 {round(r["dialogue_ratio"] * 100)}%，远低于全书中位 {round(med_dial * 100)}%；请排查是否出现大段纯叙述/设定说明。')

    # 8. Character presence, gaps & tail-25% disappearance
    cast = load_cast_from_store(store, branch=branch)
    members = compute_presence(cast, texts) if cast and texts else []
    for gap_item in detect_presence_gaps(members, gap=presence_gap):
        from_ch = ch_indices[gap_item['from_idx']]
        to_ch = ch_indices[gap_item['to_idx']]
        add('advise', 'presence', from_ch, f'角色「{gap_item["name"]}」连续断档',
            f'第 {from_ch}–{to_ch} 章连续 {gap_item["chapters"]} 章未出场（此前已有实质戏份），建议下章安排露面或暗线交代。')
    for m in members:
        if m['total'] == 0 and m['role'] != '主角':
            add('note', 'presence', None, f'角色「{m["name"]}」全书未出场',
                '已批准人物卡中登记但正文从未提及，请确认是否遗漏或可精简阵容。')
    if len(ch_indices) >= 8:
        tail_start = int(len(ch_indices) * 0.75)
        for m in members:
            if m['role'] == '主角' or m['appearances'] == 0:
                continue
            if all(n == 0 for n in m['counts'][tail_start:]) and sum(m['counts'][:tail_start]) >= 3:
                start_ch = ch_indices[tail_start]
                add('note', 'presence', start_ch, f'角色「{m["name"]}」后段缺席',
                    f'自第 {start_ch} 章起（后 25% 篇幅）再未出场；如非刻意离场，请确认是否遗忘交代下落。')

    # 9. Catchphrase / voice fulfillment
    catchphrase_rows = compute_catchphrase_stats(cast, texts) if cast and texts else []
    for row in catchphrase_rows:
        if row['total'] == 0:
            add('advise', 'voice', None, f'口头禅「{row["phrase"]}」全书未落实',
                f'角色「{row["name"]}」登记的标志语癖全书出现 0 次，对话声部辨识度可能不足。')
        elif row['total'] >= 15:
            add('note', 'voice', None, f'口头禅「{row["phrase"]}」复读偏密',
                f'角色「{row["name"]}」的口头禅全书已出现 {row["total"]} 次，注意防止沦为机械复读机。')

    # 10. Chapter ending hook shape
    for idx, ch_no in enumerate(ch_indices):
        shape = ending_shape(texts[idx])
        if shape['sentences'] > 2 or shape['chars'] > 140:
            add('note', 'ending', ch_no, f'第{ch_no}章 {titles[idx]}',
                f'章末段共 {shape["sentences"]} 句 / {shape["chars"]} 字，建议章尾钩子独立短段收束（≤2 句 / ≤140 字）增强追读余韵。')

    # 11. O(N) whole-book repeated phrases / unconscious AI tics
    repeats = repeated_phrases(texts) if texts else []
    heavy_repeats = [r for r in repeats if r['count'] >= 8]
    if heavy_repeats:
        top = heavy_repeats[0]
        add('advise', 'repeat', None, f'全书高频重复短语 {len(heavy_repeats)} 组',
            f'最高频「{top["phrase"]}」全书重复 {top["count"]} 次；若非刻意递进母题，写作时须主动换写收敛。')

    # 12. Consecutive hook-type monotony from serial_chapter_metrics
    try:
        mrows = store.connection.execute(
            'SELECT chapter_index, hook_type FROM serial_chapter_metrics WHERE branch_id=? ORDER BY chapter_index',
            (branch,),
        ).fetchall()
        hooks = [(int(r['chapter_index']), str(r['hook_type'] or '')) for r in mrows if r['hook_type'] and r['hook_type'] != 'none']
        for i in range(2, len(hooks)):
            if hooks[i][1] == hooks[i - 1][1] == hooks[i - 2][1]:
                add('advise', 'hook_variety', hooks[i][0], f'第{hooks[i-2][0]}–{hooks[i][0]}章钩子同质',
                    f'连续 3 章使用同类结尾钩子「{hooks[i][1]}」，建议参照 13 式钩子矩阵切换异质钩子防疲劳。')
    except Exception:
        pass

    findings.sort(key=lambda f: (_SEVERITY_RANK.get(f['severity'], 3), f['chapter'] if f['chapter'] is not None else 10**9))

    check_groups = (
        ('编号连续', ('numbering',)),
        ('字数门槛', ('words',)),
        ('引号配对', ('quote',)),
        ('指纹新鲜度', ('hash',)),
        ('摘要覆盖', ('summary',)),
        ('节奏突变', ('rhythm',)),
        ('对话占比', ('dialogue',)),
        ('人物在场', ('presence',)),
        ('口头禅声部', ('voice',)),
        ('章末钩子形态', ('ending',)),
        ('全书重复短语', ('repeat',)),
        ('钩子多样性', ('hook_variety',)),
    )
    checks = []
    for label, kinds in check_groups:
        hits = [f for f in findings if f['kind'] in kinds]
        if label in ('人物在场', '口头禅声部') and not cast:
            checks.append({'name': label, 'level': 'skip', 'count': 0})
        elif hits:
            worst = min(hits, key=lambda h: _SEVERITY_RANK.get(h['severity'], 3))['severity']
            checks.append({'name': label, 'level': worst, 'count': len(hits)})
        else:
            checks.append({'name': label, 'level': 'pass', 'count': 0})

    return {
        'branch_id': branch,
        'stats': {
            'chapters': len(ch_indices),
            'total_words': sum(valid_words),
            'avg_words': round(sum(valid_words) / len(valid_words)) if valid_words else 0,
            'median_words': med_words,
            'min_chapter_words': min_chapter_words,
            'dialogue_pct': round(spoken_total * 100 / max(1, char_total)) if char_total else 0,
            'cast_count': len(cast),
            'findings': {
                'fix': sum(1 for f in findings if f['severity'] == 'fix'),
                'advise': sum(1 for f in findings if f['severity'] == 'advise'),
                'note': sum(1 for f in findings if f['severity'] == 'note'),
            },
        },
        'checks': checks,
        'findings': findings,
        'rhythm': rhythm_rows,
        'presence': {
            'chapters': ch_indices,
            'members': [
                {k: m[k] for k in ('name', 'role', 'aliases', 'total', 'appearances', 'counts')}
                for m in members
            ],
        },
        'catchphrases': catchphrase_rows,
        'repeats': repeats,
    }


def build_book_audit_steering_lines(audit: dict[str, Any], *, limit: int = 3) -> list[str]:
    """Extract top cross-chapter mechanical audit alerts to feed back into 06 plot / 11 writing."""
    lines: list[str] = []
    for f in audit.get('findings') or ():
        if f.get('severity') not in ('fix', 'advise'):
            continue
        if f.get('kind') in ('presence', 'repeat', 'voice', 'dialogue', 'hook_variety', 'words'):
            lines.append(f'全书机械审读提醒：{f["title"]}——{f["detail"]}')
            if len(lines) >= limit:
                break
    return lines
