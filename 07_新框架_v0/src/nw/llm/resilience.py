"""Production LLM resilience: safe leading <think> stripping, exact-overlap continuation,
empty/thinking-only retry, and provider parameter sanitization.

Design invariants:
  - Never swallows real HTTP/network/transport failures (network errors stay hard).
  - Never strips mid-prose <think> tags or unclosed leading <think> blocks (no silent data loss).
  - Never fabricates 'complete' status when output remains truncated after continuation passes.
  - Accumulates token usage across continuation passes so budget accounting remains accurate.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from nw.llm.base import GenResult

_LEADING_THINK_BLOCK_RE = re.compile(r'^\s*<think>(.*?)</think>\s*', re.IGNORECASE | re.DOTALL)
_UNCLOSED_LEADING_THINK_RE = re.compile(r'^\s*<think>', re.IGNORECASE)

DEFAULT_CONTINUATION_PROMPT = (
    '上文因输出长度限制中断。请从已写正文的末尾直接无缝续写剩余内容，'
    '不要重复前面已写好的段落，不要输出解释或元信息，自然完成本场收尾。'
)


def strip_leading_think_blocks(text: str) -> tuple[str, str]:
    """Strip ONLY complete leading <think>...</think> blocks.

    Returns `(cleaned_text, stripped_thinking)`.
    Mid-prose `<think>` tags and unclosed leading `<think>` blocks are preserved untouched.
    """
    if not isinstance(text, str) or not text:
        return '', ''
    remaining = text
    stripped_parts: list[str] = []
    while True:
        match = _LEADING_THINK_BLOCK_RE.match(remaining)
        if match is None:
            break
        thought = match.group(1).strip()
        if thought:
            stripped_parts.append(thought)
        remaining = remaining[match.end():]
    if not stripped_parts:
        return text, ''
    return remaining, '\n\n'.join(stripped_parts)


def has_unclosed_leading_think(text: str) -> bool:
    if not isinstance(text, str) or not text:
        return False
    return bool(_UNCLOSED_LEADING_THINK_RE.match(text)) and _LEADING_THINK_BLOCK_RE.match(text) is None


def merge_exact_continuation(prefix: str, suffix: str, *, max_overlap: int = 2048) -> str:
    """Stitch continuation suffix onto prefix using exact suffix/prefix overlap deduplication."""
    if not prefix:
        return suffix or ''
    if not suffix:
        return prefix
    cleaned_suffix = suffix.lstrip('\r\n')
    if not cleaned_suffix:
        return prefix

    # 1. Exact character suffix/prefix overlap (longest overlap wins, up to max_overlap)
    limit = min(len(prefix), len(cleaned_suffix), max(1, int(max_overlap)))
    best = 0
    for n in range(limit, 0, -1):
        if prefix.endswith(cleaned_suffix[:n]):
            best = n
            break
    if best > 0:
        return prefix + cleaned_suffix[best:]

    # 2. Trailing-whitespace-tolerant overlap (when model repeats the last sentence with a newline)
    trimmed_prefix = prefix.rstrip()
    if trimmed_prefix and len(trimmed_prefix) != len(prefix):
        t_limit = min(len(trimmed_prefix), len(cleaned_suffix), max(1, int(max_overlap)))
        for n in range(t_limit, 5, -1):
            if trimmed_prefix.endswith(cleaned_suffix[:n]):
                return trimmed_prefix + cleaned_suffix[n:]

    # 3. Direct stitch: preserve natural join without injecting extra breaks mid-sentence
    return prefix + suffix


def merge_usage(base: dict[str, Any] | None, extra: dict[str, Any] | None) -> dict[str, Any]:
    """Sum numeric token counters across multi-pass continuation calls."""
    merged: dict[str, Any] = dict(base or {})
    for key, val in (extra or {}).items():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            prev = merged.get(key)
            if isinstance(prev, (int, float)) and not isinstance(prev, bool):
                merged[key] = prev + val
            else:
                merged[key] = val
        elif key not in merged:
            merged[key] = val
    return merged


def sanitize_provider_params(base_url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Strip known upstream-incompatible params for specific OpenAI-compatible gateways."""
    clean = dict(params)
    url_low = (base_url or '').lower()
    if 'generativelanguage.googleapis.com' in url_low or 'aiplatform.googleapis.com' in url_low:
        clean.pop('store', None)
    return clean


def _is_hard_transport_failure(res: GenResult) -> bool:
    raw = res.raw if isinstance(res.raw, dict) else {}
    return bool(
        raw.get('http_status') is not None
        or raw.get('network_failure') is not None
        or raw.get('error_type') is not None
    )


def apply_think_stripping(res: GenResult) -> tuple[GenResult, bool]:
    """Strip complete leading <think> blocks from a GenResult.

    Returns `(updated_result, empty_after_think)`.
    """
    cleaned, thinking = strip_leading_think_blocks(res.text)
    raw = dict(res.raw) if isinstance(res.raw, dict) else {}
    if thinking:
        raw['_stripped_thinking'] = thinking
    empty_after_think = bool(thinking) and not cleaned.strip()
    reason = res.finish_reason
    if empty_after_think and reason == 'complete':
        reason = 'error'
        raw['_resilience_reason'] = 'MODEL_EMPTY_AFTER_THINK'
    elif reason == 'complete' and not cleaned.strip():
        reason = 'error'
        raw['_resilience_reason'] = 'MODEL_EMPTY_RESPONSE'
    return GenResult(cleaned, reason, res.usage, res.request_id, raw), empty_after_think


def resilient_generate(
    call_once: Callable[[list[dict[str, Any]]], GenResult],
    messages: list[dict[str, Any]],
    *,
    allow_continuation: bool = False,
    max_empty_retries: int = 2,
    max_continuation_passes: int = 3,
    continuation_prompt: str = DEFAULT_CONTINUATION_PROMPT,
    max_overlap: int = 2048,
) -> GenResult:
    """Wrap a single-turn LLM call with think stripping, empty retry, and exact-overlap continuation."""
    attempt = 0
    total_usage: dict[str, Any] = {}
    last_result: GenResult | None = None
    empty_retries = 0

    # Phase 1: initial generation with retry ONLY on blank / thinking-only empty outputs
    while True:
        res = call_once(messages)
        res, _ = apply_think_stripping(res)
        total_usage = merge_usage(total_usage, res.usage)
        last_result = res

        raw = res.raw if isinstance(res.raw, dict) else {}
        is_retryable_empty = (
            res.finish_reason == 'error'
            and not res.text.strip()
            and not _is_hard_transport_failure(res)
            and raw.get('_resilience_reason') in ('MODEL_EMPTY_RESPONSE', 'MODEL_EMPTY_AFTER_THINK', None)
        )
        if is_retryable_empty and attempt < max(0, int(max_empty_retries)):
            attempt += 1
            empty_retries += 1
            continue
        break

    assert last_result is not None
    raw_out = dict(last_result.raw) if isinstance(last_result.raw, dict) else {}
    if empty_retries:
        raw_out['_empty_retries'] = empty_retries

    # Phase 2: long-form exact-overlap continuation ONLY when explicitly enabled and truncated
    if (
        not allow_continuation
        or last_result.finish_reason != 'truncated'
        or not last_result.text.strip()
        or max_continuation_passes <= 0
    ):
        return GenResult(last_result.text, last_result.finish_reason, total_usage, last_result.request_id, raw_out)

    accumulated = last_result.text
    request_id = last_result.request_id
    final_reason = last_result.finish_reason
    cont_passes = 0

    for _ in range(int(max_continuation_passes)):
        cont_messages = [
            *messages,
            {'role': 'assistant', 'content': accumulated},
            {'role': 'user', 'content': continuation_prompt},
        ]
        cont_raw = call_once(cont_messages)
        cont_res, _ = apply_think_stripping(cont_raw)
        total_usage = merge_usage(total_usage, cont_res.usage)
        if cont_res.request_id:
            request_id = cont_res.request_id
        if cont_res.finish_reason in ('error', 'refused') or not cont_res.text.strip():
            # Never pretend truncation succeeded if continuation failed or yielded empty output.
            raw_out['_continuation_aborted'] = cont_res.finish_reason
            final_reason = 'truncated'
            break
        merged = merge_exact_continuation(accumulated, cont_res.text, max_overlap=max_overlap)
        if len(merged) <= len(accumulated):
            # Model made zero forward progress; stop safely as truncated.
            raw_out['_continuation_aborted'] = 'no_progress'
            final_reason = 'truncated'
            break
        accumulated = merged
        cont_passes += 1
        final_reason = cont_res.finish_reason
        if final_reason == 'complete':
            break

    raw_out['_continuation_passes'] = cont_passes
    return GenResult(accumulated, final_reason, total_usage, request_id, raw_out)
