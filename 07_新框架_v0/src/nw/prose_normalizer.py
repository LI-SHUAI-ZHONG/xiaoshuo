"""Fixed-Point Empirical Chinese Web-Novel Punctuation Normalizer (Fusion H).

Calibrated against real published Chinese web fiction:
  - Standard `……` (exact two U+2026) and `——` (exact two U+2014) are VALID and preserved!
  - Fixes ONLY genuinely malformed forms:
      * Zero-width invisible chars (`\u200B-\u200D\uFEFF\u2060`)
      * Orphan Markdown horizontal rules (`---`, `***`, `===`)
      * Malformed ellipses (`...`, `。。。`, single `…`, `………`, mixed `.……..`) -> `……`
      * Numeric hyphen/dash ranges (`10--20`, `10—20`) -> `10到20`
      * Malformed dashes (single `—`, `———`, ASCII `--` between prose) -> `——`
      * Optional quotation-mark style conversion (`keep` | `curly` `“”` | `yan` `「」`)
  - Protects HTML comments (`<!-- ... -->`) and book-local `style_whitelist` spans verbatim.
  - Strictly idempotent (fixed-point): `normalize(normalize(x)) == normalize(x)`.
"""
from __future__ import annotations

import re
from typing import Any

QUOTE_MODES = frozenset({'keep', 'curly', 'yan'})

_ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c\u200d\ufeff\u2060]')
_HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
_MD_HR_RE = re.compile(r'(?m)^[ \t]*(?:-{3,}|\*{3,}|={3,})[ \t]*\r?\n?')

# Malformed ellipses: mixed dot+ellipsis, 3+ ASCII dots, 3+ Chinese periods, 3+ ellipsis, or standalone single ellipsis
_MIXED_ELLIPSIS_RE = re.compile(r'(?:\.+…+[\.…]*|…+\.+[\.…]*)')
_DOT_ELLIPSIS_RE = re.compile(r'\.{3,}')
_CJK_PERIOD_ELLIPSIS_RE = re.compile(r'。{3,}')
_OVERLONG_ELLIPSIS_RE = re.compile(r'…{3,}')
_SINGLE_ELLIPSIS_RE = re.compile(r'(?<!…)…(?!…)')

# Numeric range with malformed double-hyphen or single em-dash (e.g. `10--20`, `3—5`)
_NUMERIC_RANGE_RE = re.compile(r'(\d+)\s*(?:--+|(?<!—)—(?!—))\s*(\d+)')

# Malformed dashes (preserve exact `——` untouched)
_OVERLONG_DASH_RE = re.compile(r'—{3,}')
_SINGLE_DASH_RE = re.compile(r'(?<!—)—(?!—)')
_ASCII_DOUBLE_DASH_RE = re.compile(r'(?<![-\d])-{2,}(?![-\d])')

# Paired quotes for optional quote_mode conversion
_YAN_PAIR_RE = re.compile(r'「([^」\n]+)」')
_CURLY_PAIR_RE = re.compile(r'“([^”\n]+)”')
_STRAIGHT_CJK_QUOTE_RE = re.compile(r'"([^"\n]*[\u4e00-\u9fff][^"\n]*)"')


def _protect_spans(text: str, whitelist: list[str] | tuple[str, ...] | None) -> tuple[str, list[tuple[str, str]]]:
    """Replace HTML comments and book-local whitelist literals with inert sentinels."""
    tokens: list[tuple[str, str]] = []

    def _stash(match_str: str) -> str:
        key = f'\ue000NWPROT{len(tokens)}\ue001'
        tokens.append((key, match_str))
        return key

    out = _HTML_COMMENT_RE.sub(lambda m: _stash(m.group(0)), text)
    if whitelist:
        cleaned = sorted({str(w) for w in whitelist if isinstance(w, str) and w.strip()}, key=len, reverse=True)
        for literal in cleaned:
            if literal in out:
                key = _stash(literal)
                out = out.replace(literal, key)
    return out, tokens


def _restore_spans(text: str, tokens: list[tuple[str, str]]) -> str:
    out = text
    for key, original in reversed(tokens):
        out = out.replace(key, original)
    return out


def normalize_prose_punctuation(
    text: str,
    *,
    quote_mode: str = 'keep',
    style_whitelist: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Run deterministic fixed-point punctuation normalization on Chinese web-novel prose."""
    mode = str(quote_mode or 'keep').strip().lower()
    if mode not in QUOTE_MODES:
        raise ValueError(f'无效的引号格式模式: {quote_mode}（仅支持 keep / curly / yan）')

    original = text or ''
    if not original:
        return {
            'text': '',
            'changed': False,
            'quote_mode': mode,
            'stats': {
                'zero_width_removed': 0,
                'hr_removed': 0,
                'ellipsis_fixed': 0,
                'range_fixed': 0,
                'dash_fixed': 0,
                'quotes_converted': 0,
            },
        }

    protected, tokens = _protect_spans(original, style_whitelist)
    stats = {
        'zero_width_removed': 0,
        'hr_removed': 0,
        'ellipsis_fixed': 0,
        'range_fixed': 0,
        'dash_fixed': 0,
        'quotes_converted': 0,
    }

    work = protected

    # 1. Strip zero-width invisible characters
    work, n = _ZERO_WIDTH_RE.subn('', work)
    stats['zero_width_removed'] += n

    # 2. Remove standalone Markdown horizontal rule lines (`---`, `***`, `===`)
    work, n = _MD_HR_RE.subn('', work)
    stats['hr_removed'] += n

    # 3. Fix malformed ellipses while preserving standard `……`
    for pat in (_MIXED_ELLIPSIS_RE, _DOT_ELLIPSIS_RE, _CJK_PERIOD_ELLIPSIS_RE, _OVERLONG_ELLIPSIS_RE, _SINGLE_ELLIPSIS_RE):
        work, n = pat.subn('……', work)
        stats['ellipsis_fixed'] += n

    # 4. Fix numeric ranges written with `--` or single `—` (e.g. `10--20` -> `10到20`)
    work, n = _NUMERIC_RANGE_RE.subn(r'\1到\2', work)
    stats['range_fixed'] += n

    # 5. Fix malformed dashes while preserving standard `——`
    for pat in (_OVERLONG_DASH_RE, _SINGLE_DASH_RE, _ASCII_DOUBLE_DASH_RE):
        work, n = pat.subn('——', work)
        stats['dash_fixed'] += n

    # 6. Optional quote style normalization (`keep` / `curly` / `yan`)
    if mode == 'curly':
        work, n1 = _YAN_PAIR_RE.subn(r'“\1”', work)
        work, n2 = _STRAIGHT_CJK_QUOTE_RE.subn(r'“\1”', work)
        stats['quotes_converted'] += n1 + n2
    elif mode == 'yan':
        work, n1 = _CURLY_PAIR_RE.subn(r'「\1」', work)
        work, n2 = _STRAIGHT_CJK_QUOTE_RE.subn(r'「\1」', work)
        stats['quotes_converted'] += n1 + n2

    restored = _restore_spans(work, tokens)
    return {
        'text': restored,
        'changed': restored != original,
        'quote_mode': mode,
        'stats': stats,
    }
