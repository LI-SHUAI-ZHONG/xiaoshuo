"""Zero-token deterministic Pre-Review Script Gate (Scripts < Model < Author).

Runs immediately after Step 15 drafting and BEFORE expensive Step 16 LLM review:
  1. Completeness, structural integrity & Model Degeneration Guard (empty prose,
     placeholders, broken tail, meta/Markdown bold leaks, garbled chars, verbatim
     looping/repetition, censored-pinyin leaks, author meta headers, context-aware
     engineering-word leaks)
  2. Automatic POV knowledge-boundary leak scan derived from SQLite `story_state`
  3. 150k-chapter empirically calibrated AI-cliche, AI-rhetoric, slow micro-action tic,
     prose balance (`body_action` vs `causal_thought` equilibrium) & book-local
     `style_whitelist` masking
  4. Zero-token Outline-Copy Guard (>=16 contiguous Han chars with surgical anchor excision)
  5. Approved entity canonical name spelling guard (1-char near-miss typo detection)
  6. Optional word-budget check delegating to `scene_length_feedback`

3-Tier Severity Architecture:
  - `blocking` (`severity='hard'`, `overridable=False` for true invariants): auto-rewrite
  - `review_required` (`severity='review_required'`, `overridable=True`): Review-and-Ack
    via `override_ledger` or polish before acceptance
  - `advisory` (`severity='warning'`, `overridable=True`): handed to Step 16 review lens
"""
from __future__ import annotations

import json
import re
from statistics import median
from typing import Any

from nw.cards import read_card
from nw.length_plan import count_words, scene_length_feedback
from nw.outline_copy_guard import check_outline_copy, extract_outline_text_from_scene_card
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

# Degeneration & leakage guards (Fusion H)
_ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c\u200d\ufeff\u2060]')
_MARKDOWN_BOLD_RE = re.compile(r'\*\*[^*\n]{1,60}\*\*')
_CENSORED_PINYIN_RE = re.compile(
    r'(?:身ti|杀si|尸ti|自sha|鲜xue|警cha|暴li|强jian|毒pin|枪zhi|胸bu|下ti|死wang|血xing)',
    re.IGNORECASE,
)
_AUTHOR_META_HEADER_RE = re.compile(
    r'(?:脑子寄存处|作者有话说|求五星好评|求推荐票|求月票|本书又名|架空历史请勿考据|新书启航求支持|每日稳定更新)'
)
_TIER1_ENGINEERING_LEAK_RE = re.compile(
    r'(?:爽点密度|情绪曲线|黄金三章|钩子回收|人设弧光|起承转合模板|剧情节拍卡|章纲目标|场景卡编号|系统提示词)'
)
_TIER2_ENGINEERING_LEAK_RE = re.compile(
    r'(?:主角光环|工具人配角|降智反派|剧情杀|打卡水字数|按大纲推进|推动主线进度)'
)
_SYSTEM_PANEL_RE = re.compile(r'【[^】\n]{1,200}】')

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

# 150k-chapter empirically calibrated AI rhetoric & micro-action patterns (Fusion I)
_NOT_IS_RE = re.compile(
    r'(?:不是[^，。！？\n]{1,18}[，,]?而是|与其说是[^，。！？\n]{1,16}[，,]?不如说是|更像是[^，。！？\n]{1,16}[，,]?而不是)'
)
_VOICE_CONTRAST_RE = re.compile(r'(?:声音不大|语气平淡|话音很轻|语调不高|嗓音低沉)[，,]?却')
_NEGATION_PARADE_RE = re.compile(
    r'(?:没有[^，。！？\n]{1,12}[，,]没有[^，。！？\n]{1,12}[，,]也没有|不[^，。！？\n]{1,8}[，,]不[^，。！？\n]{1,8}[，,]也不)'
)
_TRAILER_ENDING_RE = re.compile(
    r'(?:这场(?:较量|风波|棋局|游戏|风暴)[，,]?才刚刚开始|'
    r'真正的好戏[，,]?还在后头|'
    r'属于(?:他|她|他们)的时代[，,]?(?:正式|才刚刚)拉开帷幕|'
    r'(?:他|她)不知道的是[，,]?更大的(?:风暴|危机|麻烦)|'
    r'一切[，,]?都将在(?:明天|今夜|接下来)揭晓)'
)
_SLOW_MICRO_TIC_RE = re.compile(
    r'(?:指腹(?:轻轻|慢慢|缓缓)?摩挲|慢慢拢住|手往袖里缩|'
    r'视线落(?:在|向)[^。！？\n]{1,12}停了?半秒|'
    r'指尖(?:在|轻敲|轻点)[^。！？\n]{1,10}(?:停了?一下|顿了?顿)|'
    r'唇角微不可察地|喉结上下滚动)'
)
_NEGATION_PAIR_RE = re.compile(r'没[^，。！？\n]{1,12}[，,]也没[^，。！？\n]{1,12}')
_DRAMATIC_CLICHE_WORD_RE = re.compile(r'(?:死寂|轰然|骤然|猛地|瞬间)')
_IDLE_PROP_RE = re.compile(r'(?:磨砂|骨瓷|紫檀|冷白光|空调外机|百叶窗|霓虹倒影|咖啡拉花)')
_CAMERA_ACTION_VERB_RE = re.compile(
    r'(?:拿起|放下|转身|抬头|低头|伸手|收回|迈步|推开|合上|坐下|起身|看向|望向|点点头|摇摇头)'
)

# Empirical prose-balance markers (calibrated on 151k real human web-novel chapters)
_BODY_ACTION_SENT_RE = re.compile(
    r'(?:指尖|指腹|手指|掌心|手背|袖口|眉梢|眉心|眉头|眼神|视线|目光|嘴角|唇角|喉结|下颌|呼吸|胸口|肩膀|指节)'
)
_CAUSAL_THOUGHT_SENT_RE = re.compile(
    r'(?:因为|所以|省得|免得|索性|偏偏|反正|好在|幸好|亏得|心想|暗想|盘算|掂量|估摸|料到|明白|知道|想来|怕是|保不齐|左右|与其|宁可)'
)
_COLLOQUIAL_CONNECTIVE_RE = re.compile(
    r'(?:因为|所以|省得|免得|索性|偏偏|反正|好在|幸好|倒是|倒也|干脆|罢了|横竖|左右|本就|原是|却说|偏生|不料|谁知)'
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

_FOUR_CHANNEL_FIX_HINT = (
    '用直接情绪、人物利害算账与口语因果推进（因为/所以/省得/免得/索性）、带脾气对白或有真实后果的动作重写，'
    '切勿机械替换为无后果的慢速手眼道具微动作。'
)


def _strip_quotes_keep_len(text: str) -> str:
    """Mask quoted dialogue and `【…】` panels with equal-length spaces for narration-only scans."""
    out = _DIALOGUE_QUOTE_RE.sub(lambda m: ' ' * len(m.group(0)), text)
    out = _SYSTEM_PANEL_RE.sub(lambda m: ' ' * len(m.group(0)), out)
    return out


def _mask_style_whitelist(text: str, whitelist: list[str] | tuple[str, ...] | None) -> str:
    """Mask book-local whitelisted literals with equal-length neutral chars so offsets remain exact."""
    if not text or not whitelist:
        return text
    out = text
    for lit in sorted({str(w) for w in whitelist if isinstance(w, str) and w.strip()}, key=len, reverse=True):
        if lit in out:
            out = out.replace(lit, '〇' * len(lit))
    return out


def _char_bigrams(text: str) -> set[str]:
    clean = re.sub(r'[\s\u3000，。！？、；：“”「」『』（）()—….,!?;:\-]', '', text)
    if len(clean) < 2:
        return set()
    return {clean[i:i + 2] for i in range(len(clean) - 1)}


def compute_prose_stats(text: str) -> dict[str, Any]:
    """Compute zero-token objective statistical prose fingerprint + empirical prose_balance."""
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
            'body_action_sentence_ratio': 0.0,
            'causal_thought_sentence_ratio': 0.0,
            'colloquial_connective_per_1k': 0.0,
            'narration_sentence_median': 0.0,
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

    # Narration-only empirical prose balance metrics
    narration_only = _strip_quotes_keep_len(raw)
    narration_sents = [s.strip() for s in _SENTENCE_SPLIT_RE.split(narration_only) if len(s.strip()) >= 4]
    if narration_sents:
        body_sents = sum(1 for s in narration_sents if _BODY_ACTION_SENT_RE.search(s))
        causal_sents = sum(1 for s in narration_sents if _CAUSAL_THOUGHT_SENT_RE.search(s))
        body_ratio = round(body_sents / len(narration_sents), 3)
        causal_ratio = round(causal_sents / len(narration_sents), 3)
        narr_median = round(float(median(len(s) for s in narration_sents)), 1)
    else:
        body_ratio, causal_ratio, narr_median = 0.0, 0.0, 0.0
    connective_hits = len(_COLLOQUIAL_CONNECTIVE_RE.findall(narration_only))
    connective_per_1k = round(connective_hits * 1000.0 / max(1, total_chars), 2)

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
        'body_action_sentence_ratio': body_ratio,
        'causal_thought_sentence_ratio': causal_ratio,
        'colloquial_connective_per_1k': connective_per_1k,
        'narration_sentence_median': narr_median,
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
    tier: str | None = None,
) -> dict[str, Any]:
    if tier is None:
        if severity == 'hard':
            tier = 'review_required' if overridable else 'blocking'
        elif severity == 'review_required':
            tier = 'review_required'
        else:
            tier = 'advisory'
    return {
        'code': code,
        'category': category,
        'severity': severity,
        'tier': tier,
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
) -> tuple[str, set[str], set[str], dict[str, Any] | None]:
    """Derive secret terms unknown to current POV, approved entity names, and scene card body."""
    if not store.managed_story():
        return '', set(), set(), None
    try:
        head = StateHead(branch, revision) if revision is not None else current_head(store, branch)
        snapshot = revision_state(store, head)
        scene = store.get('scene', scene_id)
        scene_meta = json.loads(scene.card_json).get('story') or {}
        scene_ref = scene_meta.get('scene_ref')
        if not isinstance(scene_ref, dict):
            return '', set(), set(), None
        scene_card = read_card(store, CardRef(str(scene_ref['card_id']), int(scene_ref['version'])))
        scene_card_body = scene_card.get('body') if isinstance(scene_card.get('body'), dict) else None
        pov = str((scene_card_body or {}).get('pov') or '').strip()
        if not pov or pov in ('AUTHOR', 'WORLD', 'READER'):
            return '', set(), set(), scene_card_body
        s_order = story_order if isinstance(story_order, int) else int(scene_meta.get('story_order') or 0)
        ch = store.get('chapter', scene.chapter_id)
        disc = disclosure if disclosure is not None else (ch.index, scene.index, 0)
        pov_view = state_at(store, head.branch_id, head.revision, s_order, pov, disc,
                            before_scene=scene_id, snapshot=snapshot)
        author_view = state_at(store, head.branch_id, head.revision, s_order, 'AUTHOR', disc,
                               before_scene=scene_id, snapshot=snapshot)
    except Exception:
        return '', set(), set(), None

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
    return pov, secret_terms, canonical_names, scene_card_body


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
        if len(name) == 2:
            surname = name[0]
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


def _scan_degeneration(
    raw_text: str,
    scan_text: str,
    narration_text: str,
    issues: list[dict[str, Any]],
) -> None:
    """Zero-token model degeneration, corruption, censored-pinyin, and meta-header guards."""
    if not raw_text:
        return

    # Garbled replacement character (HARD blocking)
    if '\ufffd' in raw_text:
        pos = raw_text.find('\ufffd')
        issues.append(_issue(
            'PRE_GARBLED_CHAR', 'degeneration', 'hard',
            '正文中出现乱码替换符（\\ufffd），存在编码损坏或模型输出异常。',
            quote=_snippet(raw_text, pos, pos + 1),
            location=_paragraph_index_at(raw_text, pos),
            fix_hint='清除乱码字符并补写受损语句。',
            overridable=False,
            tier='blocking',
        ))

    # Zero-width invisible chars (advisory, auto-cleanable via prose_normalizer)
    if m := _ZERO_WIDTH_RE.search(raw_text):
        issues.append(_issue(
            'PRE_ZERO_WIDTH_CHAR', 'degeneration', 'warning',
            '正文中包含不可见零宽字符（如 U+200B / U+FEFF），可能导致上架排版异常。',
            quote=_snippet(raw_text, m.start(), m.end()),
            location=_paragraph_index_at(raw_text, m.start()),
            fix_hint='运行「标点与排版归一化」自动清除零宽字符。',
            overridable=True,
            tier='advisory',
        ))

    # Markdown bold leak (**...**) outside whitelist (HARD blocking)
    if m := _MARKDOWN_BOLD_RE.search(scan_text):
        issues.append(_issue(
            'PRE_MARKDOWN_BOLD_LEAK', 'degeneration', 'hard',
            f'正文中混入 Markdown 加粗标记「{raw_text[m.start():m.end()]}」。',
            quote=_snippet(raw_text, m.start(), m.end()),
            location=_paragraph_index_at(raw_text, m.start()),
            fix_hint='删除所有 Markdown 星号标记，只保留纯小说正文。',
            overridable=False,
            tier='blocking',
        ))

    # Verbatim repetition & near-repeat degeneration
    lines = [(idx + 1, ln.strip()) for idx, ln in enumerate(scan_text.splitlines()) if ln.strip()]
    verbatim_flagged = False
    for i in range(1, len(lines)):
        prev_no, prev_ln = lines[i - 1]
        cur_no, cur_ln = lines[i]
        stripped_no_q = _strip_quotes_keep_len(cur_ln).strip()
        if cur_ln == prev_ln and len(re.sub(r'\s+', '', stripped_no_q)) >= 8:
            issues.append(_issue(
                'PRE_VERBATIM_REPEAT', 'degeneration', 'hard',
                f'检测到相邻行完全重复复读（第{prev_no}行与第{cur_no}行完全一致），疑似模型生成退化。',
                quote=cur_ln[:120],
                location=f'第{cur_no}段',
                fix_hint='删除重复复读段落，确认上下文衔接正常。',
                overridable=False,
                tier='blocking',
            ))
            verbatim_flagged = True
            break

    if not verbatim_flagged:
        # Check long non-quoted sentences repeated >= 3 times
        sent_counts: dict[str, int] = {}
        for s in _SENTENCE_SPLIT_RE.split(narration_text):
            cleaned = re.sub(r'\s+', '', s)
            if len(cleaned) >= 12:
                sent_counts[cleaned] = sent_counts.get(cleaned, 0) + 1
                if sent_counts[cleaned] >= 3:
                    issues.append(_issue(
                        'PRE_VERBATIM_REPEAT', 'degeneration', 'hard',
                        f'同一句长叙述在单场内逐字重复 {sent_counts[cleaned]} 次，疑似模型复读退化。',
                        quote=cleaned[:120],
                        fix_hint='删去复读句，保留必要推进。',
                        overridable=False,
                        tier='blocking',
                    ))
                    verbatim_flagged = True
                    break

    # Non-adjacent near-repeat (Bigram Jaccard >= 0.85 within 20-line window -> advisory)
    if not verbatim_flagged and len(lines) >= 2:
        line_bgs = [(no, ln, _char_bigrams(_strip_quotes_keep_len(ln))) for no, ln in lines]
        near_found = False
        for i in range(len(line_bgs)):
            if near_found:
                break
            no_a, ln_a, bg_a = line_bgs[i]
            if len(bg_a) < 16:
                continue
            for j in range(i + 2, min(len(line_bgs), i + 21)):
                no_b, ln_b, bg_b = line_bgs[j]
                if len(bg_b) < 16:
                    continue
                union = len(bg_a | bg_b)
                if union and (len(bg_a & bg_b) / union) >= 0.85:
                    issues.append(_issue(
                        'PRE_NEAR_REPEAT', 'degeneration', 'warning',
                        f'检测到相距不远的近重复段落（第{no_a}行与第{no_b}行高度重合），疑似无意重复描写。',
                        quote=ln_b[:120],
                        location=f'第{no_b}段',
                        fix_hint='核对是否属刻意呼应；若为无意重复，合并或重写其中一处。',
                        overridable=True,
                        tier='advisory',
                    ))
                    near_found = True
                    break

    # Censored-pinyin leak (review_required)
    if m := _CENSORED_PINYIN_RE.search(scan_text):
        issues.append(_issue(
            'PRE_CENSORED_PINYIN', 'degeneration', 'review_required',
            f'正文中出现敏感词拼音代写残留「{raw_text[m.start():m.end()]}」。',
            quote=_snippet(raw_text, m.start(), m.end()),
            location=_paragraph_index_at(raw_text, m.start()),
            fix_hint='改为正常中文表达或自然隐写，不要混入半中文半拼音谐音。',
            overridable=True,
            tier='review_required',
        ))

    # Author meta header in first 500 visible chars (review_required)
    head_500 = scan_text[:500]
    if m := _AUTHOR_META_HEADER_RE.search(head_500):
        issues.append(_issue(
            'PRE_AUTHOR_META_HEADER', 'degeneration', 'review_required',
            f'开篇混入网文作者题外话/求票栏「{raw_text[m.start():m.end()]}」。',
            quote=_snippet(raw_text, m.start(), m.end()),
            location=_paragraph_index_at(raw_text, m.start()),
            fix_hint='正文只保留故事内容，删除“脑子寄存处/作者有话说/求票”等戏外话。',
            overridable=True,
            tier='review_required',
        ))

    # Context-aware engineering-word leak (narration-only outside dialogue & system panels)
    if m := _TIER1_ENGINEERING_LEAK_RE.search(narration_text):
        issues.append(_issue(
            'PRE_ENGINEERING_META_LEAK', 'degeneration', 'hard',
            f'正文中混入写作工程/系统内部术语「{raw_text[m.start():m.end()]}」。',
            quote=_snippet(raw_text, m.start(), m.end()),
            location=_paragraph_index_at(raw_text, m.start()),
            fix_hint='删除一切大纲、节拍、情绪曲线、爽点密度等制作后台术语。',
            overridable=False,
            tier='blocking',
        ))
    elif m := _TIER2_ENGINEERING_LEAK_RE.search(narration_text):
        issues.append(_issue(
            'PRE_ENGINEERING_META_SOFT', 'degeneration', 'warning',
            f'旁白中出现出戏网文评论/套路术语「{raw_text[m.start():m.end()]}」。',
            quote=_snippet(raw_text, m.start(), m.end()),
            location=_paragraph_index_at(raw_text, m.start()),
            fix_hint='若非穿书/快穿刻意玩梗，建议改回故事内人物视角的自然叙述。',
            overridable=True,
            tier='advisory',
        ))


def _scan_empirical_ai_patterns(
    raw_text: str,
    scan_text: str,
    narration_text: str,
    stats: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    """150k-chapter empirically calibrated AI-rhetoric and micro-action checks (Fusion I)."""
    if not raw_text:
        return
    total_chars = max(1, stats['chars'])

    # ── review_required tier (overridable=True -> integrates with override_ledger) ──
    not_is_hits = list(_NOT_IS_RE.finditer(narration_text))
    if len(not_is_hits) >= 3:
        first = not_is_hits[0]
        issues.append(_issue(
            'PRE_NOT_IS_CLUSTER', 'voice_rhetoric', 'review_required',
            f'单场旁白高频堆叠「不是……而是……/与其说是……不如说是……」对比句（共 {len(not_is_hits)} 处），呈典型 AI 论证腔。',
            quote=_snippet(raw_text, first.start(), first.end()),
            location=_paragraph_index_at(raw_text, first.start()),
            fix_hint='直接陈述事物本身或人物利害判断，单场最多保留 1 处转折对比。' + _FOUR_CHANNEL_FIX_HINT,
            overridable=True,
            tier='review_required',
        ))

    voice_contrast_hits = list(_VOICE_CONTRAST_RE.finditer(narration_text))
    if len(voice_contrast_hits) >= 2:
        first = voice_contrast_hits[0]
        issues.append(_issue(
            'PRE_VOICE_CONTRAST', 'voice_rhetoric', 'review_required',
            f'单场重复出现「声音不大，却……/语气平淡，却……」模板（共 {len(voice_contrast_hits)} 处）。',
            quote=_snippet(raw_text, first.start(), first.end()),
            location=_paragraph_index_at(raw_text, first.start()),
            fix_hint='直接写台词内容与对方反应，用话本身的份量压场。',
            overridable=True,
            tier='review_required',
        ))

    neg_parade_hits = list(_NEGATION_PARADE_RE.finditer(narration_text))
    if len(neg_parade_hits) >= 2:
        first = neg_parade_hits[0]
        issues.append(_issue(
            'PRE_NEGATION_PARADE', 'voice_rhetoric', 'review_required',
            f'单场出现 {len(neg_parade_hits)} 处三连否定排比（没有……没有……也没有……），易显模板抒情腔。',
            quote=_snippet(raw_text, first.start(), first.end()),
            location=_paragraph_index_at(raw_text, first.start()),
            fix_hint='直接写现场真正存在的东西或人物当下的决定。',
            overridable=True,
            tier='review_required',
        ))

    tail_start = max(0, len(narration_text) - 250)
    tail_chunk = narration_text[tail_start:]
    if m := _TRAILER_ENDING_RE.search(tail_chunk):
        abs_s = tail_start + m.start()
        abs_e = tail_start + m.end()
        issues.append(_issue(
            'PRE_TRAILER_ENDING', 'voice_rhetoric', 'review_required',
            f'章尾/场尾出现预告片式总结句「{raw_text[abs_s:abs_e]}」，削弱现场追读感。',
            quote=_snippet(raw_text, abs_s, abs_e),
            location='末段',
            fix_hint='删掉预告式拔高总结，把结尾停在具体动作、未了异象或刚甩出的台词上。',
            overridable=True,
            tier='review_required',
        ))

    narr_dash_count = narration_text.count('——')
    narr_dash_per_1k = narr_dash_count * 1000.0 / total_chars
    if narr_dash_count >= 10 and narr_dash_per_1k >= 2.5:
        pos = narration_text.find('——')
        issues.append(_issue(
            'PRE_NARRATION_EM_DASH_OVERLOAD', 'voice_rhetoric', 'review_required',
            f'旁白破折号「——」过密（{narr_dash_count} 处，{narr_dash_per_1k:.1f}/千字；人类正常破折号不禁用但单场不宜高频堆叠）。',
            quote=_snippet(raw_text, pos, pos + 2),
            location=_paragraph_index_at(raw_text, pos),
            fix_hint='保留关键转折/对话打断处的破折号，其余改为自然句号或逗号顺叙。',
            overridable=True,
            tier='review_required',
        ))

    # ── advisory tier (calibrated false-positive-guarded style alerts) ──
    micro_hits = list(_SLOW_MICRO_TIC_RE.finditer(narration_text))
    micro_per_1k = len(micro_hits) * 1000.0 / total_chars
    if len(micro_hits) >= 4 and micro_per_1k >= 1.5:
        first = micro_hits[0]
        issues.append(_issue(
            'PRE_SLOW_MICRO_ACTION_TIC', 'voice_balance', 'warning',
            f'高频出现无后果慢速手眼道具套动作（{len(micro_hits)} 处，如指腹摩挲/慢慢拢住/视线停半秒），警惕“展示而非讲述”矫枉过正。',
            quote=_snippet(raw_text, first.start(), first.end()),
            location=_paragraph_index_at(raw_text, first.start()),
            fix_hint=_FOUR_CHANNEL_FIX_HINT,
            overridable=True,
            tier='advisory',
        ))

    # Action-list camera paragraph check
    for idx, para in enumerate(narration_text.split('\n'), start=1):
        p = para.strip()
        if len(p) < 40:
            continue
        commas = p.count('，') + p.count(',')
        verbs = len(_CAMERA_ACTION_VERB_RE.findall(p))
        if commas >= 4 and verbs >= 5 and not _COLLOQUIAL_CONNECTIVE_RE.search(p):
            issues.append(_issue(
                'PRE_ACTION_LIST_CAMERA', 'voice_balance', 'warning',
                f'第{idx}段呈摄像机式连续动作清单（{verbs} 处机械动作动词连缀、缺少内心因果衔接）。',
                quote=p[:120],
                location=f'第{idx}段',
                fix_hint='删去无后果过场动作，补入人物当下判断或直接情绪。',
                overridable=True,
                tier='advisory',
            ))
            break

    neg_pairs = list(_NEGATION_PAIR_RE.finditer(narration_text))
    if len(neg_pairs) >= 3:
        first = neg_pairs[0]
        issues.append(_issue(
            'PRE_NEGATION_PAIR_TIC', 'voice_rhetoric', 'warning',
            f'单场出现 {len(neg_pairs)} 处「没A，也没B」对称否定句式。',
            quote=_snippet(raw_text, first.start(), first.end()),
            location=_paragraph_index_at(raw_text, first.start()),
            fix_hint='改用正面动作或人物直接意图推进，减少对称否定填充。',
            overridable=True,
            tier='advisory',
        ))

    excl_count = narration_text.count('！') + narration_text.count('!')
    excl_per_1k = excl_count * 1000.0 / total_chars
    if excl_count >= 12 and excl_per_1k >= 10.0:
        issues.append(_issue(
            'PRE_EXCLAMATION_ROAR', 'voice_balance', 'warning',
            f'旁白感叹号过密（{excl_count} 处，{excl_per_1k:.1f}/千字），情绪持续满格易疲劳。',
            fix_hint='只把感叹号留给真正震撼或爆发的 1–2 句，其余回落句号以拉出反差。',
            overridable=True,
            tier='advisory',
        ))

    siji_count = narration_text.count('死寂')
    dramatic_hits = list(_DRAMATIC_CLICHE_WORD_RE.finditer(narration_text))
    dramatic_per_1k = len(dramatic_hits) * 1000.0 / total_chars
    if siji_count >= 2 or (len(dramatic_hits) >= 6 and dramatic_per_1k >= 3.5):
        first = dramatic_hits[0] if dramatic_hits else None
        issues.append(_issue(
            'PRE_DRAMATIC_CLICHE_TIC', 'voice_rhetoric', 'warning',
            f'强情绪套词聚集（死寂 {siji_count} 次，死寂/轰然/骤然/猛地/瞬间 合计 {len(dramatic_hits)} 次）。',
            quote=_snippet(raw_text, first.start(), first.end()) if first else '',
            location=_paragraph_index_at(raw_text, first.start()) if first else '',
            fix_hint='用具体声音/动作后果代替抽象的“死寂/骤然/猛地”。',
            overridable=True,
            tier='advisory',
        ))

    unique_props = set(_IDLE_PROP_RE.findall(narration_text))
    if len(unique_props) >= 3 and stats['colloquial_connective_per_1k'] <= 7.0:
        issues.append(_issue(
            'PRE_IDLE_PROP_DECORATION', 'voice_balance', 'warning',
            f'检测到多处闲置精装物件摆拍（{"、".join(sorted(unique_props)[:4])}）且口语推进偏少。',
            fix_hint='只保留与当前冲突或人物利害直接相关的物件，删去纯氛围摆拍。',
            overridable=True,
            tier='advisory',
        ))

    if stats['chars'] >= 400 and stats['colloquial_connective_per_1k'] <= 5.5 and stats['narration_sentence_median'] >= 28.0:
        issues.append(_issue(
            'PRE_DRY_NARRATION', 'voice_balance', 'warning',
            f'叙述偏干硬（口语连接词 {stats["colloquial_connective_per_1k"]:.1f}/千字，纯叙述中位句长 {stats["narration_sentence_median"]:.0f} 字，人类手机端常模约 23 字）。',
            fix_hint='补入自然的人物内心因果算账（因为/所以/省得/免得/索性/偏偏）并拉短过长说明句。',
            overridable=True,
            tier='advisory',
        ))


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
    style_whitelist: list[str] | tuple[str, ...] | None = None,
    outline_text: str = '',
    verbatim_anchors: list[str] | tuple[str, ...] | None = None,
    outline_copy_min_han: int = 16,
) -> dict[str, Any]:
    """Run zero-token deterministic checks on a freshly drafted scene before Step 16 LLM review."""
    raw = (draft_text or '')
    stripped = raw.strip()
    issues: list[dict[str, Any]] = []
    stats = compute_prose_stats(stripped)

    # Load voice spec & book-local style whitelist (strictly per-book, never cross-book)
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

    eff_whitelist: list[str] = list(style_whitelist or ())
    if style_whitelist is None:
        if isinstance(voice_spec, dict) and isinstance(voice_spec.get('style_whitelist'), list):
            eff_whitelist = [str(w).strip() for w in voice_spec['style_whitelist'] if str(w).strip()]
        elif store is not None:
            try:
                from nw.voice_specs import load_book_style_whitelist
                eff_whitelist = load_book_style_whitelist(store)
            except Exception:
                eff_whitelist = []

    scan_text = _mask_style_whitelist(stripped, eff_whitelist)
    narration_text = _strip_quotes_keep_len(scan_text)

    # 1. Completeness, structural integrity & Degeneration Guard
    if not stripped:
        issues.append(_issue(
            'PRE_EMPTY_DRAFT', 'completeness', 'hard',
            '草稿正文为空，无法进入审稿。',
            fix_hint='重新生成本场完整正文。',
            overridable=False,
            tier='blocking',
        ))
    else:
        for pid, pat in _PLACEHOLDER_PATTERNS:
            for m in list(pat.finditer(scan_text))[:3]:
                issues.append(_issue(
                    f'PRE_PLACEHOLDER_{pid.upper()}', 'completeness', 'hard',
                    f'正文中残留未填写的占位标记「{stripped[m.start():m.end()]}」。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='将占位标记补写为真实剧情细节或正式名称。',
                    overridable=False,
                    tier='blocking',
                ))
        if m := _META_LEAK_RE.search(scan_text):
            issues.append(_issue(
                'PRE_META_LEAK', 'completeness', 'hard',
                f'正文中混入了系统提示词或内部字段标记「{stripped[m.start():m.end()]}」。',
                quote=_snippet(stripped, m.start(), m.end()),
                location=_paragraph_index_at(stripped, m.start()),
                fix_hint='删除所有非正文的系统标题、JSON 字段或规则说明，只输出纯小说正文。',
                overridable=False,
                tier='blocking',
            ))
        # Broken tail / unclosed quote detection (only on non-trivial prose)
        clean_tail = _ZERO_WIDTH_RE.sub('', stripped)
        if len(clean_tail) >= 60:
            if clean_tail[-1] in (',', '，', '、', '：', ':', '（', '(', '“', '「', '『'):
                issues.append(_issue(
                    'PRE_BROKEN_TAIL', 'completeness', 'hard',
                    f'正文结尾异常截断（以「{clean_tail[-1]}」结尾，未自然收句）。',
                    quote=clean_tail[-60:],
                    location='末段',
                    fix_hint='补全最后一句动作或对白，以自然句末标点收束。',
                    overridable=False,
                    tier='blocking',
                ))
            for open_q, close_q in (('“', '”'), ('「', '」')):
                diff = clean_tail.count(open_q) - clean_tail.count(close_q)
                if abs(diff) >= 2:
                    issues.append(_issue(
                        'PRE_UNCLOSED_QUOTES', 'completeness', 'warning',
                        f'正文引号配对不平衡（{open_q} 出现 {clean_tail.count(open_q)} 次，{close_q} 出现 {clean_tail.count(close_q)} 次）。',
                        fix_hint='核对对白起止引号，补齐遗漏的半边引号。',
                        overridable=True,
                        tier='advisory',
                    ))
        _scan_degeneration(stripped, scan_text, narration_text, issues)

    # 2. Automatic POV knowledge-boundary leak scan (derived from SQLite story_state)
    pov_id = ''
    secret_terms: set[str] = set(extra_secret_terms or ())
    canonical_names: set[str] = set(extra_canonical_names or ())
    scene_card_body: dict[str, Any] | None = None
    if store is not None and scene_id:
        pov_id, derived_secrets, derived_names, scene_card_body = _derive_pov_secret_terms(
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
                    tier='blocking',
                ))

    # 3. AI-cliche, empirically calibrated AI-rhetoric & active voice_spec anti-drift bans
    active_bans: set[str] = set()
    if isinstance(voice_spec, dict) and voice_spec.get('enabled', True):
        knobs = voice_spec.get('knobs') if isinstance(voice_spec.get('knobs'), dict) else {}
        active_bans.update(str(x) for x in (knobs.get('anti_drift_bans') or ()) if x)

    cliche_matches: list[tuple[str, str, int, int]] = []
    if stripped:
        for cid, label, pat in _AI_CLICHE_PATTERNS:
            for m in pat.finditer(scan_text):
                cliche_matches.append((cid, label, m.start(), m.end()))
        if len(cliche_matches) >= 5:
            sample = '、'.join(dict.fromkeys(row[1] for row in cliche_matches[:4]))
            issues.append(_issue(
                'PRE_AI_CLICHE_OVERLOAD', 'voice_cliche', 'hard',
                f'单场命中 {len(cliche_matches)} 处高频 AI 腔/翻译腔套句（{sample}），触发写后自动打回重写阈值。',
                quote=_snippet(stripped, cliche_matches[0][2], cliche_matches[0][3]),
                location=_paragraph_index_at(stripped, cliche_matches[0][2]),
                fix_hint='删除“冷笑/瞳孔一缩/寒意顺脊背/空气凝固”等模板词，' + _FOUR_CHANNEL_FIX_HINT,
                overridable=True,
                tier='review_required',
            ))
        elif cliche_matches:
            for cid, label, s_pos, e_pos in cliche_matches[:3]:
                issues.append(_issue(
                    f'PRE_{cid.upper()}', 'voice_cliche', 'warning',
                    f'检测到 {label}。',
                    quote=_snippet(stripped, s_pos, e_pos),
                    location=_paragraph_index_at(stripped, s_pos),
                    fix_hint=_FOUR_CHANNEL_FIX_HINT,
                    overridable=True,
                    tier='advisory',
                ))

        _scan_empirical_ai_patterns(stripped, scan_text, narration_text, stats, issues)

        if 'no_modern_slang' in active_bans:
            if m := _MODERN_SLANG_RE.search(scan_text):
                issues.append(_issue(
                    'PRE_MODERN_SLANG_BAN', 'voice_cliche', 'hard',
                    f'违反语感禁令（禁现代网梗）：正文中出现「{stripped[m.start():m.end()]}」。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='替换为符合本书时代与语体寄存器的自然表达。',
                    overridable=True,
                    tier='review_required',
                ))
        if 'no_narrator_preaching' in active_bans:
            if m := _PREACHING_RE.search(scan_text):
                issues.append(_issue(
                    'PRE_NARRATOR_PREACHING', 'voice_cliche', 'warning',
                    f'疑似违反语感禁令（禁旁白说教）：出现说教总结句「{stripped[m.start():m.end()]}」。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='删除旁白升华总结，改写人物当下真实情绪或具体选择。',
                    overridable=True,
                    tier='advisory',
                ))
        if 'no_idiom_stacking' in active_bans:
            if m := _IDIOM_STACK_RE.search(scan_text):
                issues.append(_issue(
                    'PRE_IDIOM_STACKING', 'voice_cliche', 'warning',
                    '疑似违反语感禁令（禁四字成语堆砌）：检测到连续 4 个以上四字词排比。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='拆成自然口语叙述和可感细节，避免空泛四字堆叠。',
                    overridable=True,
                    tier='advisory',
                ))
        if 'no_telegraph_chop' in active_bans:
            if m := _TELEGRAPH_CHOP_RE.search(scan_text):
                issues.append(_issue(
                    'PRE_TELEGRAPH_CHOP', 'voice_cliche', 'warning',
                    '疑似违反语感禁令（禁电报体碎短句）：检测到连续 4 句以上超短碎句排比。',
                    quote=_snippet(stripped, m.start(), m.end()),
                    location=_paragraph_index_at(stripped, m.start()),
                    fix_hint='按意思自然连贯说完，长短句交替。',
                    overridable=True,
                    tier='advisory',
                ))

        # Paragraph wall check
        if stats['max_paragraph_chars'] > 450:
            issues.append(_issue(
                'PRE_PARAGRAPH_WALL', 'voice_cliche', 'warning',
                f'存在超长段落墙（最长单段 {stats["max_paragraph_chars"]} 字，建议不超过 350 字以利手机端阅读）。',
                fix_hint='按动作切换、视角转移或对话起承拆分成自然短段。',
                overridable=True,
                tier='advisory',
            ))

    # 4. Zero-Token Outline-Copy Guard (Fusion G)
    eff_outline = (outline_text or '').strip()
    eff_anchors = list(verbatim_anchors or ())
    if not eff_outline and scene_card_body:
        card_out, card_anchors = extract_outline_text_from_scene_card(scene_card_body)
        eff_outline = card_out
        eff_anchors.extend(card_anchors)
    outline_copy_report: dict[str, Any] | None = None
    if stripped and eff_outline:
        outline_copy_report = check_outline_copy(
            stripped, eff_outline, extra_anchors=eff_anchors, min_han=outline_copy_min_han,
        )
        for hit in outline_copy_report['hits'][:3]:
            issues.append(_issue(
                'PRE_OUTLINE_COPY', 'outline_copy', 'warning',
                f'疑似逐字抄写章纲/场景卡原句（连续重合 {hit["han_length"]} 个汉字）。',
                quote=hit['draft_quote'],
                location=hit['draft_location'],
                fix_hint='将提纲概述拆成现场发生的对白、直接心理与具体推进，而非把纲要句子直接贴进正文。',
                overridable=True,
                tier='advisory',
            ))

    # 5. Canonical entity spelling guard (1-char near-miss detection)
    if stripped and canonical_names:
        for canon_name, cand, pos in _find_near_miss_typos(stripped, canonical_names):
            issues.append(_issue(
                'PRE_ENTITY_SPELLING_DRIFT', 'entity_spelling', 'warning',
                f'疑似人名/专名错字：「{cand}」（已批准设定名录为「{canon_name}」）。',
                quote=_snippet(stripped, pos, pos + len(cand)),
                location=_paragraph_index_at(stripped, pos),
                fix_hint=f'若指同一人物/专名，请统一更正为「{canon_name}」。',
                overridable=True,
                tier='advisory',
            ))

    # 6. Optional word budget check via existing scene_length_feedback
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
                tier='advisory',
            ))

    hard_count = sum(1 for row in issues if row['severity'] == 'hard')
    review_required_items = [row for row in issues if row.get('tier') == 'review_required']
    review_required_count = len(review_required_items)
    advisory_count = sum(1 for row in issues if row.get('tier') == 'advisory')
    warning_count = sum(1 for row in issues if row['severity'] != 'hard')

    if hard_count > 0:
        action = 'auto_rewrite'
    elif review_required_count > 0:
        action = 'review_required'
    elif warning_count > 0:
        action = 'warn_to_review'
    else:
        action = 'pass'

    handoff_lines: list[str] = []
    if issues:
        handoff_lines.append('【0-Token 写后机检线索（事实与工艺镜头须重点核实，无需凭空重找）】')
        for idx, row in enumerate(issues[:8], start=1):
            sev = '硬错' if row['severity'] == 'hard' else ('须核验' if row['severity'] == 'review_required' else '预警')
            loc = f'（{row["location"]}）' if row.get('location') else ''
            q = f'｜摘录：{row["quote"]}' if row.get('quote') else ''
            handoff_lines.append(f'{idx}. [{sev}/{row["category"]}]{loc} {row["message"]}{q}')

    return {
        'passed': hard_count == 0 and review_required_count == 0,
        'action': action,
        'hard_count': hard_count,
        'review_required_count': review_required_count,
        'advisory_count': advisory_count,
        'warning_count': warning_count,
        'issues': issues,
        'review_required_items': review_required_items,
        'pov_id': pov_id,
        'pov_secret_terms_checked': len(secret_terms),
        'canonical_names_checked': len(canonical_names),
        'style_whitelist_applied': len(eff_whitelist),
        'outline_copy': outline_copy_report,
        'metrics': stats,
        'review_handoff_note': '\n'.join(handoff_lines),
    }


def format_pre_review_rewrite_feedback(report: dict[str, Any]) -> str:
    """Format hard/review_required pre-review failures into an actionable Step 15 rewrite note."""
    target_items = [
        row for row in (report.get('issues') or ())
        if row.get('severity') in ('hard', 'review_required')
    ]
    if not target_items:
        return ''
    lines = ['写后机检发现以下必须修正的硬问题，请在保持剧情、POV边界与已批准设定不变的前提下原地重写修正：']
    for idx, row in enumerate(target_items[:6], start=1):
        loc = f'[{row["location"]}] ' if row.get('location') else ''
        lines.append(f'{idx}. {loc}{row["message"]} → 修法：{row["fix_hint"]}')
    return '\n'.join(lines)
