"""Platform Publish Preflight & Whole-Book Pre-Publish Clean Sweep (Fusion L1).

Provides concrete deterministic pre-publish compliance checks for major Chinese web-novel
platforms (`fanqie` 番茄小说, `qidian` 起点读书, `qimao` 七猫免费小说, `jjwxc` 晋江文学城):
  1. Metadata validation (`validate_publish_package`):
     - Weighted title length (full-width CJK = 1.0, half-width ASCII = 0.5)
     - Banned spaces, emoji, promotional brackets (`【】[]《》★☆`), signing-risk symbols
     - Synopsis min/max length bounds and author-meta clutter checks
     - Category / tag count caps
  2. Whole-book chapter sweep (`sweep_book_for_publish`):
     - Scans every accepted chapter on the branch with `normalize_prose_punctuation` +
       degeneration / censored-pinyin / author-meta-header / Markdown-bold / garbled checks
     - Produces a per-chapter readiness report AND a 1-click normalized clean export text!
"""
from __future__ import annotations

import re
from typing import Any

from nw.craft_evolution import _accepted_chapter_texts
from nw.platform_playbooks import get_platform_playbook
from nw.pre_review_gate import run_pre_review_gate
from nw.prose_normalizer import normalize_prose_punctuation
from nw.store import Store
from nw.voice_specs import load_book_style_whitelist

PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    'fanqie': {
        'id': 'fanqie',
        'name': '番茄小说',
        'max_title_units': 15.0,
        'min_title_units': 2.0,
        'half_width_ascii': True,
        'allow_title_spaces': False,
        'synopsis_min_chars': 40,
        'synopsis_max_chars': 500,
        'max_tags': 5,
        'chapter_min_chars': 1800,
        'chapter_max_chars': 4000,
        'signing_notes': '番茄书名严控 15 字内（半角算半字），禁空格/表情/促销括号；2026年10月起 Lv.0/Lv.1 新人长篇需完本签约（15–30万字），短故事 0.5–3万字完本可投，日更≥4000字且分成达标享全勤。',
    },
    'qidian': {
        'id': 'qidian',
        'name': '起点读书',
        'max_title_units': 15.0,
        'min_title_units': 2.0,
        'half_width_ascii': True,
        'allow_title_spaces': False,
        'synopsis_min_chars': 20,
        'synopsis_max_chars': 500,
        'max_tags': 4,
        'chapter_min_chars': 2000,
        'chapter_max_chars': 5000,
        'signing_notes': '起点建议 6000 字+大纲走编辑内投，签约后 5 天内满 2 万字入库，6 万字分类试水推 PK 追读，约 20 万字/40天上架；全月日更≥4000–6000字不可断更防掉智能推档位。',
    },
    'qimao': {
        'id': 'qimao',
        'name': '七猫免费小说',
        'max_title_units': 15.0,
        'min_title_units': 2.0,
        'half_width_ascii': True,
        'allow_title_spaces': False,
        'synopsis_min_chars': 30,
        'synopsis_max_chars': 400,
        'max_tags': 5,
        'chapter_min_chars': 1800,
        'chapter_max_chars': 3500,
        'signing_notes': '七猫支持千字保底+超保底五五分成或纯分成（3万字训练营可切入），日更≥4000字享全勤（月封顶20万字、可请假1天；纯分成完结须≥20万字且不烂尾），简介严控 400 字内。',
    },
    'jjwxc': {
        'id': 'jjwxc',
        'name': '晋江文学城',
        'max_title_units': 14.0,
        'min_title_units': 2.0,
        'half_width_ascii': False,
        'allow_title_spaces': False,
        'synopsis_min_chars': 30,
        'synopsis_max_chars': 1000,
        'max_tags': 6,
        'chapter_min_chars': 2000,
        'chapter_max_chars': 5000,
        'signing_notes': '晋江书名≤14字（不折半角），签人制5年起（1万字自荐申签），言情~300收/纯爱~300-500收顺V，版权分成8:2作者占大头；注意新晋作者榜同实名限次，入V第3–4天上夹子定生死。',
    },
    'zhihu_yanyan': {
        'id': 'zhihu_yanyan',
        'name': '知乎盐言故事',
        'max_title_units': 30.0,
        'min_title_units': 4.0,
        'half_width_ascii': True,
        'allow_title_spaces': True,
        'synopsis_min_chars': 30,
        'synopsis_max_chars': 600,
        'max_tags': 5,
        'chapter_min_chars': 1500,
        'chapter_max_chars': 6000,
        'signing_notes': '盐言故事单本独家签（不绑人），短篇建议 1万–3万字完结投稿（5:5盐选分成+短剧孵化），前300–500字导语钩子决定免转付转化；硬红线：严禁耽美/纯爱及未成年恋爱！',
    },
    'ciweimao': {
        'id': 'ciweimao',
        'name': '刺猬猫阅读',
        'max_title_units': 15.0,
        'min_title_units': 2.0,
        'half_width_ascii': True,
        'allow_title_spaces': False,
        'synopsis_min_chars': 20,
        'synopsis_max_chars': 500,
        'max_tags': 5,
        'chapter_min_chars': 2000,
        'chapter_max_chars': 4500,
        'signing_notes': '刺猬猫二次元垂直付费 6:4 分成（作者60%），约3万字内投ABCD签、12万字上架；2026年12月起新版全勤为月更12万/日更4000挂钩订阅15%–25%提成。',
    },
}

_ZHIHU_BANNED_GENRE_RE = re.compile(r'(?:耽美|纯爱|双男主|BL|未成年恋爱|早恋)', re.IGNORECASE)

_FORBIDDEN_TITLE_SYMBOLS_RE = re.compile(r'[【】\[\]《》<>★☆♥❤●◆■▲▼※@#\$%\^&\*\+=\\|/~`]')
_EMOJI_RE = re.compile(r'[\U0001F300-\U0001FAFF\u2600-\u27BF]')
_PROMO_TITLE_RE = re.compile(r'(?:爆款|必看|免费|全本|完结|无敌爽文|求收藏|求推荐)')
_URL_LEAK_RE = re.compile(r'(?:https?://|www\.|加群|QQ群|微信号)', re.IGNORECASE)

_PUBLISH_BLOCKING_CODES = frozenset({
    'PRE_EMPTY_DRAFT',
    'PRE_META_LEAK',
    'PRE_BROKEN_TAIL',
    'PRE_GARBLED_CHAR',
    'PRE_MARKDOWN_BOLD_LEAK',
    'PRE_VERBATIM_REPEAT',
    'PRE_ENGINEERING_META_LEAK',
})
_PUBLISH_ATTENTION_CODES = frozenset({
    'PRE_CENSORED_PINYIN',
    'PRE_AUTHOR_META_HEADER',
    'PRE_UNCLOSED_QUOTES',
})


def weighted_title_length(title: str, *, half_width_ascii: bool = True) -> float:
    """Compute platform title length (ASCII/half-width counts as 0.5 when `half_width_ascii=True`)."""
    total = 0.0
    for ch in (title or ''):
        if half_width_ascii and ord(ch) < 128:
            total += 0.5
        else:
            total += 1.0
    return round(total, 1)


def validate_publish_package(
    platform: str,
    *,
    title: str,
    synopsis: str,
    tags: list[str] | tuple[str, ...] | None = None,
    category: str = '',
) -> dict[str, Any]:
    """Validate book metadata (title, synopsis, tags, category) against platform publish specs."""
    pid = str(platform or 'fanqie').strip().lower()
    if pid not in PLATFORM_SPECS:
        raise ValueError(f'不支持的发布平台: {platform}（支持 fanqie / qidian / qimao / jjwxc / zhihu_yanyan / ciweimao）')
    spec = PLATFORM_SPECS[pid]
    raw_title = str(title or '')
    clean_title = raw_title.strip()
    clean_syn = str(synopsis or '').strip()
    clean_tags = [str(t).strip() for t in (tags or ()) if str(t).strip()]

    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    t_len = weighted_title_length(clean_title, half_width_ascii=spec['half_width_ascii'])
    if not clean_title:
        blocking.append({'field': 'title', 'code': 'TITLE_EMPTY', 'message': '书名不能为空。'})
    else:
        if t_len < spec['min_title_units']:
            blocking.append({
                'field': 'title', 'code': 'TITLE_TOO_SHORT',
                'message': f'书名过短（当前 {t_len} 字，{spec["name"]}至少需要 {spec["min_title_units"]:g} 字）。',
            })
        if t_len > spec['max_title_units']:
            blocking.append({
                'field': 'title', 'code': 'TITLE_TOO_LONG',
                'message': f'书名超出 {spec["name"]} 上限（当前 {t_len} 字，上限 {spec["max_title_units"]:g} 字）。',
            })
        if not spec['allow_title_spaces'] and re.search(r'\s', raw_title):
            blocking.append({
                'field': 'title', 'code': 'TITLE_HAS_WHITESPACE',
                'message': f'{spec["name"]} 书名禁止包含空格或换行。',
            })
        if m := _FORBIDDEN_TITLE_SYMBOLS_RE.search(clean_title):
            blocking.append({
                'field': 'title', 'code': 'TITLE_FORBIDDEN_SYMBOL',
                'message': f'书名包含平台禁用的装饰/括号符号「{m.group(0)}」，存在审核驳回风险。',
            })
        if _EMOJI_RE.search(clean_title):
            blocking.append({
                'field': 'title', 'code': 'TITLE_FORBIDDEN_EMOJI',
                'message': '书名包含 Emoji 表情符号，无法通过平台过审。',
            })
        if m := _PROMO_TITLE_RE.search(clean_title):
            warnings.append({
                'field': 'title', 'code': 'TITLE_PROMO_RISK',
                'message': f'书名含促销导流词「{m.group(0)}」，可能触发人工复审或降权。',
            })

    syn_len = len(clean_syn)
    if syn_len < spec['synopsis_min_chars']:
        blocking.append({
            'field': 'synopsis', 'code': 'SYNOPSIS_TOO_SHORT',
            'message': f'简介字数不足（当前 {syn_len} 字，{spec["name"]}要求至少 {spec["synopsis_min_chars"]} 字）。',
        })
    elif syn_len > spec['synopsis_max_chars']:
        blocking.append({
            'field': 'synopsis', 'code': 'SYNOPSIS_TOO_LONG',
            'message': f'简介超出字数上限（当前 {syn_len} 字，{spec["name"]}上限 {spec["synopsis_max_chars"]} 字）。',
        })
    if _EMOJI_RE.search(clean_syn):
        warnings.append({
            'field': 'synopsis', 'code': 'SYNOPSIS_HAS_EMOJI',
            'message': '简介包含 Emoji 表情，部分渠道审核可能拒绝，建议改用纯中文标点。',
        })
    if m := _URL_LEAK_RE.search(clean_syn):
        blocking.append({
            'field': 'synopsis', 'code': 'SYNOPSIS_EXTERNAL_CONTACT',
            'message': f'简介中出现外链或引流联系方式「{m.group(0)}」，违反平台签约规范。',
        })

    if len(clean_tags) > spec['max_tags']:
        blocking.append({
            'field': 'tags', 'code': 'TAGS_OVER_LIMIT',
            'message': f'标签数量超限（当前 {len(clean_tags)} 个，{spec["name"]}上限 {spec["max_tags"]} 个）。',
        })
    elif not clean_tags:
        warnings.append({
            'field': 'tags', 'code': 'TAGS_EMPTY',
            'message': '尚未填写发书标签，建议补齐 2–4 个精准核心卖点标签以利冷启动分发。',
        })
    if not str(category or '').strip():
        warnings.append({
            'field': 'category', 'code': 'CATEGORY_UNSET',
            'message': '尚未指定目标频道/大类分类。',
        })

    if pid == 'zhihu_yanyan':
        meta_blob = ' '.join([clean_title, clean_syn, str(category or ''), *clean_tags])
        if bm := _ZHIHU_BANNED_GENRE_RE.search(meta_blob):
            blocking.append({
                'field': 'category', 'code': 'PLATFORM_REDLINE_ZHIHU',
                'message': f'命中知乎盐言故事内容硬红线「{bm.group(0)}」（官方严禁耽美/纯爱及未成年恋爱题材），请改投晋江或调整设定。',
            })

    pb = get_platform_playbook(pid) or {}
    playbook_summary = {
        'tier': pb.get('tier', ''),
        'monetization_model': (pb.get('monetization') or {}).get('model', ''),
        'revenue_split': (pb.get('monetization') or {}).get('revenue_split', ''),
        'full_attendance': (pb.get('monetization') or {}).get('full_attendance', ''),
        'signing_threshold': (pb.get('signing') or {}).get('threshold', ''),
        'recent_2026_alert': (pb.get('signing') or {}).get('recent_2026_alert', ''),
        'daily_words': (pb.get('craft_requirements') or {}).get('daily_words', ''),
        'redlines': list((pb.get('craft_requirements') or {}).get('redlines') or ()),
        'progression_ladder': list(pb.get('progression_ladder') or ()),
    }

    return {
        'passed': len(blocking) == 0,
        'platform': pid,
        'platform_name': spec['name'],
        'weighted_title_length': t_len,
        'max_title_length': spec['max_title_units'],
        'synopsis_length': syn_len,
        'synopsis_range': [spec['synopsis_min_chars'], spec['synopsis_max_chars']],
        'tag_count': len(clean_tags),
        'max_tags': spec['max_tags'],
        'signing_notes': spec['signing_notes'],
        'playbook_summary': playbook_summary,
        'blocking_issues': blocking,
        'warnings': warnings,
    }


def sweep_book_for_publish(
    store: Store,
    *,
    branch: str = 'main',
    platform: str = 'fanqie',
    quote_mode: str = 'keep',
    style_whitelist: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Scan all accepted chapters with the empirical punctuation normalizer + degeneration gate.

    Returns a per-chapter readiness report AND a ready-to-publish clean normalized full-book export!
    """
    pid = str(platform or 'fanqie').strip().lower()
    spec = PLATFORM_SPECS.get(pid) or PLATFORM_SPECS['fanqie']
    whitelist = list(style_whitelist) if style_whitelist is not None else load_book_style_whitelist(store)

    chapter_titles = {c.index: c.title for c in store.list('chapter')}
    ch_texts = _accepted_chapter_texts(store, branch)

    chapters_report: list[dict[str, Any]] = []
    export_chunks: list[str] = []
    blocked_chapters = 0
    attention_chapters = 0
    auto_cleaned_chapters = 0
    total_chars = 0

    for ch_idx, raw_text in sorted(ch_texts.items()):
        ch_title = chapter_titles.get(ch_idx) or f'第{ch_idx}章'
        norm = normalize_prose_punctuation(raw_text, quote_mode=quote_mode, style_whitelist=whitelist)
        cleaned_text = norm['text']
        gate = run_pre_review_gate(None, '', cleaned_text, style_whitelist=whitelist)

        ch_blocking = [
            row for row in gate['issues']
            if row['code'] in _PUBLISH_BLOCKING_CODES or str(row['code']).startswith('PRE_PLACEHOLDER_')
        ]
        ch_attention = [
            row for row in gate['issues']
            if row['code'] in _PUBLISH_ATTENTION_CODES
        ]
        ch_len = len(cleaned_text.strip())
        total_chars += ch_len
        length_note = ''
        if ch_len < spec['chapter_min_chars']:
            length_note = f'字数偏短（{ch_len} 字，{spec["name"]}建议 ≥ {spec["chapter_min_chars"]} 字）'
        elif ch_len > spec['chapter_max_chars']:
            length_note = f'字数偏长（{ch_len} 字，{spec["name"]}建议 ≤ {spec["chapter_max_chars"]} 字）'

        if ch_blocking:
            status = 'blocked'
            blocked_chapters += 1
        elif ch_attention:
            status = 'needs_attention'
            attention_chapters += 1
        elif norm['changed']:
            status = 'auto_cleanable'
            auto_cleaned_chapters += 1
        else:
            status = 'clean'

        chapters_report.append({
            'chapter_index': ch_idx,
            'title': ch_title,
            'chars': ch_len,
            'status': status,
            'punctuation_changed': norm['changed'],
            'punctuation_stats': norm['stats'],
            'blocking_issues': ch_blocking,
            'attention_issues': ch_attention,
            'length_note': length_note,
        })
        heading = ch_title if ch_title.startswith(f'第{ch_idx}章') else f'第{ch_idx}章 {ch_title}'
        export_chunks.append(f'{heading}\n\n{cleaned_text.strip()}')

    return {
        'passed': blocked_chapters == 0 and len(chapters_report) > 0,
        'branch_id': branch,
        'platform': spec['id'],
        'platform_name': spec['name'],
        'quote_mode': quote_mode,
        'chapter_count': len(chapters_report),
        'total_chars': total_chars,
        'blocked_chapters': blocked_chapters,
        'attention_chapters': attention_chapters,
        'auto_cleaned_chapters': auto_cleaned_chapters,
        'chapters': chapters_report,
        'clean_export_text': '\n\n\n'.join(export_chunks),
    }
