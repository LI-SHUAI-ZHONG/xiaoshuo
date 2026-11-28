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
        'signing_notes': '番茄书名严控 15 字内（半角算半字），禁空格/表情/促销括号，正文避免作者题外话与拼音代写。',
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
        'signing_notes': '起点重视开篇三章节奏与书名简洁辨识度，书名不超过 15 字，简介突出核心设定与卖点。',
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
        'signing_notes': '七猫偏好直白高辨识书名与紧凑手机端短段，简介不超过 400 字，避免大段设定说明。',
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
        'signing_notes': '晋江书名不超过 14 字，禁特殊装饰符号与表情，文案可包含立意与排雷但禁违规外链。',
    },
}

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
        raise ValueError(f'不支持的发布平台: {platform}（支持 fanqie / qidian / qimao / jjwxc）')
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
