"""Zero-token deterministic Pre-Review Script Gate (Scripts < Model < Author).

Runs immediately after Step 15 drafting and BEFORE expensive Step 16 LLM review:
  1. Completeness & structural integrity (empty prose, placeholders, broken tail, meta leaks)
  2. Automatic POV knowledge-boundary leak scan derived from SQLite `story_state`
  3. AI-cliche, translationese & `voice_spec` anti-drift redline regex/stat scan
  4. Approved entity canonical name spelling guard (1-char near-miss typo detection)
  5. Optional word-budget check delegating to `scene_length_feedback`

Hard failures can bounce the draft straight back to Step 15 auto-rewrite at 0 review tokens.
Warnings are packaged into `review_handoff_note` so Step 16 Fact Lens verifies true positives
instead of hunting blindly across long prose.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Any

from nw.cards import read_card
from nw.length_plan import count_words, scene_length_feedback
from nw.store import Store
from nw.story_models import CardRef, StateHead
from nw.story_state import IDENTITY_STATUS_PREFIX, current_head, revision_state, state_at

# Common placeholders that must never leak into prose
_PLACEHOLDER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ('bracket_todo', re.compile(r'[\[【\(（]\s*(?:待补|待定|待填|待写|占位|暂名|此处补|TODO|TBD|FIXME)[^\]】\)）]{0,30}[\]】\)）]', re.IGNORECASE)),
    ('brace_placeholder', re.compile(r'\{[^{}\n]{1,24}(?:占位|章纲|目标|人名|待填|待定)[^{}\n]{0,24}\}')),
    ('raw_xxx', re.compile(r'(?<![A-Za-z])(?:XXX+|TBD|TODO|FIXME)(?![A-Za-z])')),
)

# Meta-prompt leakage markers (writer leaking system/card structure into prose)
_META_LEAK_RE = re.compile(
    r'(?:```(?:json)?|##\s*[一二三四五]、本场硬约束|"card_id"\s*:|"voice_spec"\s*:|"disclosure_order"\s*:|'
    r'本场写前处境卡|本书语感规范卡|防漂移红线)'
)

# High-confidence Chinese AI-cliche & translationese phrases
_AI_CLICHE_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ('cliche_chill_spine', '翻译腔套句「寒意顺着脊背」', re.compile(r'一股(?:冰冷的)?寒意(?:瞬间)?顺着脊背')),
    ('cliche_smirk', 'AI 高频套动作「嘴角勾起一抹冷笑/弧度」', re.compile(r'嘴角(?:微微)?勾起一抹(?:冷笑|嘲讽|诡异的弧度|玩味的笑)')),
    ('cliche_pupil', 'AI 高频套反应「瞳孔骤然一缩/猛地一缩」', re.compile(r'瞳孔(?:骤然|猛地|瞬间)?一缩')),
    ('cliche_air_freeze', 'AI 高频空洞氛围「空气瞬间/仿佛凝固」', re.compile(r'空气(?:瞬间|仿佛|陡然)(?:彻底)?凝固')),
    ('cliche_storm_heart', 'AI 抽象情绪标签「内心掀起惊涛骇浪」', re.compile(r'(?:内心|心中)(?:瞬间)?掀起了?惊涛骇浪')),
    ('cliche_destiny_gear', 'AI 开篇套话「命运的齿轮开始转动」', re.compile(r'命运的齿轮(?:悄然)?开始转动')),
    ('cliche_did_not_think', '剧透指路句「当时并没有多想/殊不知」', re.compile(r'(?:他|她)当时并没有多想|殊不知这将成为')),
    ('cliche_thunder_struck', 'AI 抽象情绪标签「如遭雷击/难以言喻的」', re.compile(r'瞬间如遭雷击|难以言喻的(?:恐惧|愤怒|悲痛|震撼)')),
    ('cliche_emit_sneer', '译制腔「发出一声冷笑/轻笑」', re.compile(r'发出一声(?:冷笑|嗤笑|叹息)')),
    ('cliche_unconscious', '高频虚副词「不由自主地/情不自禁地」', re.compile(r'(?:不由自主|情不自禁)地')),
)

# Knob-triggered extra checks
_MODERN_SLANG_RE = re.compile(
    r'(?:yyds|绝绝子|破防了|芭比Q|显眼包|社死|内卷|摆烂|PUA|CPU|DNA动了|emo了|纯爱战神|泰裤辣|尊嘟假嘟)',
    re.IGNORECASE,
)
_PREACHING_RE = re.compile(
    r'(?:其实人生就是这样|他终于明白了一个道理|这或许就是生活的真相|世事无常，人生亦然|命运总是喜欢开玩笑)'
)
_IDIOM_STACK_RE = re.compile(r'(?:[\u4e00-\u9fff]{4}[、，,]){3,}[\u4e00-\u9fff]{4}')
_TELEGRAPH_CHOP_RE = re.compile(r'(?:^|\n)(?:[^。！？\n]{1,6}[。！？]){4,}')

# Common 2-4 CJK words that should never be treated as leaked secret terms or typo candidates
_COMMON_STOPWORDS = frozenset({
    '自己', '这里', '那里', '什么', '没有', '不是', '知道', '时候', '现在', '已经', '可以', '不能',
    '一个', '这个', '那个', '他们', '她们', '我们', '你们', '如此', '虽然', '但是', '因为', '所以',
    '主角', '反派', '配角', '人物', '世界', '地点', '组织', '物品', '身份', '秘密', '事实', '计划',
    '规则', '境界', '力量', '时间', '空间', '任务', '目标', '冲突', '线索', '伏笔', '承诺', '正常',
    '存活', '死亡', '受伤', '失踪', '安全', '危险', '未知', '公开', '隐藏', '真实', '虚假', '表面',
})

_SENTENCE_SPLIT_RE = re.compile(r'[。！？!?…\n]+')
_DIALOGUE_QUOTE_RE = re.compile(r'“[^”\n]{1,400}”|「[^」\n]{1,400}」|"[^"\n]{1,400}"')
_CJK_TOKEN_RE = re.compile(r'[\u4e00-\u9fff]{2,6}')


def compute_prose_stats(text: str) -> dict[str, Any]:
    """Compute zero-token objective statistical prose fingerprint for a draft or chapter."""
    raw = (text or '').strip()
    if not raw:
        return {
            'chars': 0,
            'cjk_words': 0,
            'paragraphs': 0,
            'avg_paragraph_chars': 0.0,
            'max_paragraph_chars': 0,
            'sentences': 0,
            'avg_sentence_len': 0.0,
            'short_sentence_ratio': 0.0,
            'dialogue_ratio': 0.0,
            'cliche_hits': 0,
            'cliche_density_per_1k': 0.0,
        }
    paragraphs = [p.strip() for p in re.split(r'\n+', raw) if p.strip()]
    para_lens = [len(p) for p in paragraphs]
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(raw) if len(s.strip()) >= 2]
    sent_lens = [len(s) for s in sentences]
    short_sents = sum(1 for n in sent_lens if n <= 12)
    dialogue_chars = sum(len(m.group(0)) for m in _DIALOGUE_QUOTE_RE.finditer(raw))
    cjk_words = count_words(raw)
    cliche_hits = sum(len(pat.findall(raw)) for _, _, pat in _AI_CLICHE_PATTERNS)
    total_chars = len(raw)
    return {
        'chars': total_chars,
        'cjk_words': cjk_words,
        'paragraphs': len(paragraphs),
        'avg_paragraph_chars': round(sum(para_lens) / max(1, len(para_lens)), 1),
        'max_paragraph_chars': max(para_lens, default=0),
        'sentences': len(sentences),
        'avg_sentence_len': round(sum(sent_lens) / max(1, len(sent_lens)), 1),
        'short_sentence_ratio': round(short_sents / max(1, len(sent_lens)), 3),
        'dialogue_ratio': round(min(1.0, dialogue_chars / max(1, total_chars)), 3),
        'cliche_hits': cliche_hits,
        'cliche_density_per_1k': round(cliche_hits * 1000.0 / max(1, total_chars), 2),
    }


def _issue(
    code: str,
    category: str,
    severity: str,
    message: str,
    *,
    quote: str = '',
    fix_hint: str = '',
    overridable: bool = False,
    location: str = '',
) -> dict[str, Any]:
    return {
        'code': code,
        'category': category,
        'severity': severity,
        'message': message,
        'quote': quote[:160],
        'fix_hint': fix_hint,
        'overridable': overridable,
        'location': location,
    }


def _snippet(text: str, start: int, end: int, pad: int = 22) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    return text[lo:hi].replace('\n', ' ').strip()


def _paragraph_index_at(text: str, pos: int) -> str:
    idx = text[:max(0, pos)].count('\n') + 1
    return f'第{idx}段'


def _extract_cjk_terms(val: Any) -> set[str]:
    terms: set[str] = set()
    if isinstance(val, str):
        s = val.strip()
        if 2 <= len(s) <= 8 and re.fullmatch(r'[\u4e00-\u9fff]{2,8}', s):
            if s not in _COMMON_STOPWORDS:
                terms.add(s)
    elif isinstance(val, dict):
        for k in ('identity', 'name', 'title', 'alias', 'secret_name', 'true_identity'):
            if k in val:
                terms.update(_extract_cjk_terms(val[k]))
    elif isinstance(val, list):
        for item in val[:10]:
            terms.update(_extract_cjk_terms(item))
    return terms


def _derive_pov_secret_terms(
    store: Store,
    *,
    scene_id: str,
    branch: str,
    revision: int | None,
    story_order: int | None,
    disclosure: tuple[int, int, int] | None,
) -> tuple[str, set[str], set[str]]:
    """Derive secret terms unknown to current POV and canonical approved entity names from SQLite."""
    if not store.managed_story():
        return '', set(), set()
    try:
        head = StateHead(branch, revision) if revision is not None else current_head(store, branch)
        snapshot = revision_state(store, head)
        scene = store.get('scene', scene_id)
        scene_meta = json.loads(scene.card_json).get('story') or {}
        scene_ref = scene_meta.get('scene_ref')
        if not isinstance(scene_ref, dict):
            return '', set(), set()
        scene_card = read_card(store, CardRef(str(scene_ref['card_id']), int(scene_ref['version'])))
        pov = str(scene_card['body'].get('pov') or '').strip()
        if not pov or pov in ('AUTHOR', 'WORLD', 'READER'):
            return '', set(), set()
        s_order = story_order if isinstance(story_order, int) else int(scene_meta.get('story_order') or 0)
        ch = store.get('chapter', scene.chapter_id)
        disc = disclosure if disclosure is not None else (ch.index, scene.index, 0)
        pov_view = state_at(store, head.branch_id, head.revision, s_order, pov, disc,
                            before_scene=scene_id, snapshot=snapshot)
        author_view = state_at(store, head.branch_id, head.revision, s_order, 'AUTHOR', disc,
                               before_scene=scene_id, snapshot=snapshot)
    except Exception:
        return '', set(), set()

    visible_card_ids = {c['card_id'] for c in pov_view.settings}
    visible_terms: set[str] = set()
    canonical_names: set[str] = set()
    for card in pov_view.settings:
        body = card.get('body') or {}
        for key in ('name', 'title'):
            nm = str(body.get(key) or '').strip()
            if 2 <= len(nm) <= 6 and re.fullmatch(r'[\u4e00-\u9fff]{2,6}', nm):
                visible_terms.add(nm)
                if card.get('kind') in ('character', 'world'):
                    canonical_names.add(nm)
        for alias in (body.get('aliases') or ()):
            if isinstance(alias, str) and 2 <= len(alias.strip()) <= 6:
                visible_terms.add(alias.strip())
                canonical_names.add(alias.strip())
    for fact in pov_view.facts:
        visible_terms.update(_extract_cjk_terms(fact.value))

    secret_terms: set[str] = set()
    # 1) Hidden cards (visibility='holders' without POV or casting.entry=='withheld')
    for ref in snapshot.get('settings', ()):
        cid = ref['card_id']
        if cid in visible_card_ids:
            continue
        try:
            hidden = read_card(store, CardRef(cid, ref['version']))
        except Exception:
            continue
        body = hidden.get('body') or {}
        if hidden.get('kind') == 'character':
            secret_terms.update(_extract_cjk_terms(body.get('name')))
            secret_terms.update(_extract_cjk_terms(body.get('aliases')))
            casting = body.get('casting') if isinstance(body.get('casting'), dict) else {}
            secret_terms.update(_extract_cjk_terms(casting.get('secret_identity')))
    # 2) Facts known to AUTHOR/WORLD with hidden identity_status not yet known to POV
    pov_fact_sigs = {(f.entity_id, f.predicate, json.dumps(f.value, ensure_ascii=False, sort_keys=True))
                     for f in pov_view.facts}
    for fact in author_view.facts:
        if fact.holder not in ('WORLD', 'AUTHOR'):
            continue
        sig = (fact.entity_id, fact.predicate, json.dumps(fact.value, ensure_ascii=False, sort_keys=True))
        if sig in pov_fact_sigs:
            continue
        if fact.predicate.startswith(IDENTITY_STATUS_PREFIX) or 'secret' in fact.predicate.lower() or '隐藏' in fact.predicate:
            secret_terms.update(_extract_cjk_terms(fact.value))

    secret_terms -= visible_terms
    secret_terms -= _COMMON_STOPWORDS
    return pov, secret_terms, canonical_names


def _find_near_miss_typos(text: str, canonical_names: set[str]) -> list[tuple[str, str, int]]:
    """Detect 1-char near-miss spelling drifts for 2-3 char Chinese character names."""
    if not canonical_names or not text:
        return []
    target_names = [n for n in sorted(canonical_names) if 2 <= len(n) <= 3]
    if not target_names:
        return []
    hits: list[tuple[str, str, int]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for name in target_names:
        # Look for same-surname 2-char typo or same-prefix/suffix 3-char typo occurring right next to common verb/punct
        if len(name) == 2:
            surname, given = name[0], name[1]
            # Only flag if the canonical name itself also appears or is short-list approved,
            # and we find `surname + other_char` followed by dialogue/action verbs
            pat = re.compile(rf'(?<![\u4e00-\u9fff]){re.escape(surname)}([\u4e00-\u9fff])(?=(?:道|说|问|笑|冷|看|望|皱|点|摇|站|走|转|伸|握|叹|沉))')
            for m in pat.finditer(text):
                cand = surname + m.group(1)
                if cand == name or cand in canonical_names or cand in _COMMON_STOPWORDS:
                    continue
                if (name, cand) not in seen_pairs:
                    seen_pairs.add((name, cand))
                    hits.append((name, cand, m.start()))
        elif len(name) == 3:
            prefix = name[:2]
            pat = re.compile(rf'{re.escape(prefix)}([\u4e00-\u9fff])')
            for m in pat.finditer(text):
                cand = prefix + m.group(1)
                if cand == name or cand in canonical_names or cand in _COMMON_STOPWORDS:
                    continue
                if (name, cand) not in seen_pairs:
                    seen_pairs.add((name, cand))
                    hits.append((name, cand, m.start()))
    return hits[:6]


def run_pre_review_gate(
    store: Store | None,
    scene_id: str,
    draft_text: str,
    *,
    branch: str = 'main',
    revision: int | None = None,
    story_order: int | None = None,
    disclosure: tuple[int, int, int] | None = None,
    manifest: dict[str, Any] | None = None,
    voice_spec: dict[str, Any] | None = None,
    craft_specs: dict[str, Any] | None = None,
    extra_secret_terms: set[str] | None = None,
    extra_canonical_names: set[str] | None = None,
) -> dict[str, Any]:
    """Run zero-token deterministic checks on a freshly drafted scene before Step 16 LLM review."""
    raw = (draft_text or '')
    stripped = raw.strip()
    issues: list[dict[str, Any]] = []
    stats = compute_prose_stats(stripped)

    # 1. Completeness & structural integrity (HARD)
    if not stripped:
        issues.append(_issue(
            'PRE_EMPTY_DRAFT', 'completeness', 'hard',
            '草稿正文为空，无法进入审稿。',
            fix_hint='重新生成本场完整正文。',
            overridable=False,
        ))
    else:
        for pid, pat in _PLACEHOLDER_PATTERNS:
            for m in list(pat.finditer(stripped))[:3]:
                issues.append(_issue(
                    f'PRE_PLACEHOLDER_{pid.upper()}', 'completeness', 'hard',
                    f'正文中残留未填写的占位标记「{m.group(0)}」。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='将占位标记补写为真实剧情细节或正式名称。',
                    overridable=False,
                ))
        if m := _META_LEAK_RE.search(stripped):
            issues.append(_issue(
                'PRE_META_LEAK', 'completeness', 'hard',
                f'正文中混入了系统提示词或内部字段标记「{m.group(0)}」。',
                quote=_snippet(stripped, m.start(), m.end()),
                location=_paragraph_index_at(stripped, m.start()),
                fix_hint='删除所有非正文的系统标题、JSON 字段或规则说明，只输出纯小说正文。',
                overridable=False,
            ))
        # Broken tail / unclosed quote detection (only on non-trivial prose)
        if len(stripped) >= 60:
            if stripped[-1] in (',', '，', '、', '：', ':', '（', '(', '“', '「', '『'):
                issues.append(_issue(
                    'PRE_BROKEN_TAIL', 'completeness', 'hard',
                    f'正文结尾异常截断（以「{stripped[-1]}」结尾，未自然收句）。',
                    quote=stripped[-60:],
                    location='末段',
                    fix_hint='补全最后一句动作或对白，以自然句末标点收束。',
                    overridable=False,
                ))
            for open_q, close_q in (('“', '”'), ('「', '」')):
                diff = stripped.count(open_q) - stripped.count(close_q)
                if abs(diff) >= 2:
                    issues.append(_issue(
                        'PRE_UNCLOSED_QUOTES', 'completeness', 'warning',
                        f'正文引号配对不平衡（{open_q} 出现 {stripped.count(open_q)} 次，{close_q} 出现 {stripped.count(close_q)} 次）。',
                        fix_hint='核对对白起止引号，补齐遗漏的半边引号。',
                        overridable=True,
                    ))

    # 2. Automatic POV knowledge-boundary leak scan (derived from SQLite story_state)
    pov_id = ''
    secret_terms: set[str] = set(extra_secret_terms or ())
    canonical_names: set[str] = set(extra_canonical_names or ())
    if store is not None and scene_id:
        pov_id, derived_secrets, derived_names = _derive_pov_secret_terms(
            store, scene_id=scene_id, branch=branch, revision=revision,
            story_order=story_order, disclosure=disclosure,
        )
        secret_terms.update(derived_secrets)
        canonical_names.update(derived_names)

    if stripped and secret_terms:
        for term in sorted(secret_terms):
            pos = stripped.find(term)
            if pos >= 0:
                issues.append(_issue(
                    'PRE_POV_SECRET_LEAK', 'pov_leak', 'warning',
                    f'正文出现当前视角（{pov_id or "POV"}）尚未获知的隐藏身份/秘密词「{term}」，疑似越界泄密。',
                    quote=_snippet(stripped, pos, pos + len(term)),
                    location=_paragraph_index_at(stripped, pos),
                    fix_hint='核查该词是否属于获准的读者旁白节拍；若属 POV 视角越界，请改为视角人物可见的外在迹象，绝不提前点破。',
                    overridable=False,
                ))

    # 3. AI-cliche & active voice_spec anti-drift bans
    if voice_spec is None and store is not None:
        try:
            from nw.voice_specs import load_book_voice_spec
            voice_spec = load_book_voice_spec(store)
        except Exception:
            voice_spec = None
    if craft_specs is None and store is not None:
        try:
            from nw.craft_specs import load_all_craft_specs
            craft_specs = load_all_craft_specs(store)
        except Exception:
            craft_specs = None

    active_bans: set[str] = set()
    if isinstance(voice_spec, dict) and voice_spec.get('enabled', True):
        knobs = voice_spec.get('knobs') if isinstance(voice_spec.get('knobs'), dict) else {}
        active_bans.update(str(x) for x in (knobs.get('anti_drift_bans') or ()) if x)

    cliche_matches: list[tuple[str, str, int, int]] = []
    if stripped:
        for cid, label, pat in _AI_CLICHE_PATTERNS:
            for m in pat.finditer(stripped):
                cliche_matches.append((cid, label, m.start(), m.end()))
        if len(cliche_matches) >= 5:
            sample = '、'.join(dict.fromkeys(row[1] for row in cliche_matches[:4]))
            issues.append(_issue(
                'PRE_AI_CLICHE_OVERLOAD', 'voice_cliche', 'hard',
                f'单场命中 {len(cliche_matches)} 处高频 AI 腔/翻译腔套句（{sample}），触发写后自动打回重写阈值。',
                quote=_snippet(stripped, cliche_matches[0][2], cliche_matches[0][3]),
                location=_paragraph_index_at(stripped, cliche_matches[0][2]),
                fix_hint='用具体动作、物件和贴身白话重写上述套句，删除“冷笑/瞳孔一缩/寒意顺脊背/空气凝固”等AI模板词。',
                overridable=True,
            ))
        elif cliche_matches:
            for cid, label, s_pos, e_pos in cliche_matches[:3]:
                issues.append(_issue(
                    f'PRE_{cid.upper()}', 'voice_cliche', 'warning',
                    f'检测到 {label}。',
                    quote=_snippet(stripped, s_pos, e_pos),
                    location=_paragraph_index_at(stripped, s_pos),
                    fix_hint='建议改为更具体的现场动作或自然口语表达。',
                    overridable=True,
                ))

        if 'no_modern_slang' in active_bans:
            if m := _MODERN_SLANG_RE.search(stripped):
                issues.append(_issue(
                    'PRE_MODERN_SLANG_BAN', 'voice_cliche', 'hard',
                    f'违反语感禁令（禁现代网梗）：正文中出现「{m.group(0)}」。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='替换为符合本书时代与语体寄存器的自然表达。',
                    overridable=True,
                ))
        if 'no_narrator_preaching' in active_bans:
            if m := _PREACHING_RE.search(stripped):
                issues.append(_issue(
                    'PRE_NARRATOR_PREACHING', 'voice_cliche', 'warning',
                    f'疑似违反语感禁令（禁旁白说教）：出现说教总结句「{m.group(0)}」。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='删除旁白升华总结，让人物动作和后果自己说话。',
                    overridable=True,
                ))
        if 'no_idiom_stacking' in active_bans:
            if m := _IDIOM_STACK_RE.search(stripped):
                issues.append(_issue(
                    'PRE_IDIOM_STACKING', 'voice_cliche', 'warning',
                    '疑似违反语感禁令（禁四字成语堆砌）：检测到连续 4 个以上四字词排比。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='拆成具体动词和可感细节，避免空泛四字堆叠。',
                    overridable=True,
                ))
        if 'no_telegraph_chop' in active_bans:
            if m := _TELEGRAPH_CHOP_RE.search(stripped):
                issues.append(_issue(
                    'PRE_TELEGRAPH_CHOP', 'voice_cliche', 'warning',
                    '疑似违反语感禁令（禁电报体碎短句）：检测到连续 4 句以上超短碎句排比。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='按意思自然连贯说完，长短句交替。',
                    overridable=True,
                ))

        # Paragraph wall check
        if stats['max_paragraph_chars'] > 450:
            issues.append(_issue(
                'PRE_PARAGRAPH_WALL', 'voice_cliche', 'warning',
                f'存在超长段落墙（最长单段 {stats["max_paragraph_chars"]} 字，建议不超过 350 字以利手机端阅读）。',
                fix_hint='按动作切换、视角转移或对话起承拆分成自然短段。',
                overridable=True,
            ))

    # 4. Canonical entity spelling guard (1-char near-miss detection)
    if stripped and canonical_names:
        for canon_name, cand, pos in _find_near_miss_typos(stripped, canonical_names):
            issues.append(_issue(
                'PRE_ENTITY_SPELLING_DRIFT', 'entity_spelling', 'warning',
                f'疑似人名/专名错字：「{cand}」（已批准设定名录为「{canon_name}」）。',
                quote=_snippet(stripped, pos, pos + len(cand)),
                location=_paragraph_index_at(stripped, pos),
                fix_hint=f'若指同一人物/专名，请统一更正为「{canon_name}」。',
                overridable=True,
            ))

    # 5. Optional word budget check via existing scene_length_feedback
    if store is not None and scene_id and manifest and stripped:
        try:
            length_issues = scene_length_feedback(store, scene_id, manifest, stripped)
        except Exception:
            length_issues = []
        for msg in length_issues:
            issues.append(_issue(
                'PRE_WORD_BUDGET', 'word_budget', 'warning',
                msg,
                fix_hint='按批准的章场篇幅预算补充场景展开或压缩冗余说明。',
                overridable=True,
            ))

    hard_count = sum(1 for row in issues if row['severity'] == 'hard')
    warning_count = sum(1 for row in issues if row['severity'] == 'warning')
    if hard_count > 0:
        action = 'auto_rewrite'
    elif warning_count > 0:
        action = 'warn_to_review'
    else:
        action = 'pass'

    handoff_lines: list[str] = []
    if issues:
        handoff_lines.append('【0-Token 写后机检线索（事实与工艺镜头须重点核实，无需凭空重找）】')
        for idx, row in enumerate(issues[:8], start=1):
            sev = '硬错' if row['severity'] == 'hard' else '预警'
            loc = f'（{row["location"]}）' if row.get('location') else ''
            q = f'｜摘录：{row["quote"]}' if row.get('quote') else ''
            handoff_lines.append(f'{idx}. [{sev}/{row["category"]}]{loc} {row["message"]}{q}')

    return {
        'passed': hard_count == 0,
        'action': action,
        'hard_count': hard_count,
        'warning_count': warning_count,
        'issues': issues,
        'pov_id': pov_id,
        'pov_secret_terms_checked': len(secret_terms),
        'canonical_names_checked': len(canonical_names),
        'metrics': stats,
        'review_handoff_note': '\n'.join(handoff_lines),
    }


def format_pre_review_rewrite_feedback(report: dict[str, Any]) -> str:
    """Format hard pre-review failures into a concise, actionable Step 15 rewrite instruction."""
    hard_items = [row for row in (report.get('issues') or ()) if row.get('severity') == 'hard']
    if not hard_items:
        return ''
    lines = ['写后机检发现以下必须修正的硬问题，请在保持剧情、POV边界与已批准设定不变的前提下原地重写修正：']
    for idx, row in enumerate(hard_items[:6], start=1):
        loc = f'[{row["location"]}] ' if row.get('location') else ''
        lines.append(f'{idx}. {loc}{row["message"]} → 修法：{row["fix_hint"]}')
    return '\n'.join(lines)
