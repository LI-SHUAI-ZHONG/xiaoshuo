"""Project length preferences shared by the wizard and frozen design tasks."""
import json
from typing import Mapping

from nw.task_models import canonical

WORD_FIELDS = ('target_words', 'chapter_target_words', 'scene_target_words')
LENGTH_FIELDS = (*WORD_FIELDS, 'chapter_count', 'volume_count', 'word_tolerance_pct', 'length_mode')
LEGACY_QUOTAS = ('chapter_count', 'chapter_target_words', 'scene_target_words', 'word_tolerance_pct')
CHAPTER_MIN_WORDS, CHAPTER_MAX_WORDS = 2000, 2500
# At a midpoint the larger tier starts. The outside tiers extend half of their adjacent gap.
_TIER_RANGES = {
    300_000: (200_000, 399_999),
    500_000: (400_000, 749_999),
    1_000_000: (750_000, 1_249_999),
    1_500_000: (1_250_000, 1_749_999),
    2_000_000: (1_750_000, 2_250_000),
}
WORD_TIERS = tuple(_TIER_RANGES)
BRIEF_LENGTH = '\n\n立项参数：\n'


def book_word_range(target: int) -> tuple[int, int]:
    """Inclusive accepted manuscript interval for a selectable tier."""
    if type(target) is not int or target not in _TIER_RANGES:
        raise ValueError('全书篇幅请选择 30 万、50 万、100 万、150 万或 200 万字档')
    return _TIER_RANGES[target]


def nearest_word_tier(actual_words: int) -> int | None:
    return next((tier for tier, (low, high) in _TIER_RANGES.items()
                 if low <= actual_words <= high), None)


def validate_length_mode(values: Mapping) -> None:
    if values.get('length_mode') == 'tiered':
        if values.get('target_words') is not None:
            book_word_range(values['target_words'])
        if any(values.get(k) is not None for k in LEGACY_QUOTAS):
            raise ValueError('档位篇幅按每章 2000–2500 字自然收束，章数由剧情决定，请移除旧的固定配额')


def length_fields(values: Mapping) -> dict:
    return {key: values[key] for key in LENGTH_FIELDS if values.get(key) is not None}


def parse_length_changes(raw: dict) -> dict:
    changes = {}
    for key in LENGTH_FIELDS:
        if key not in raw:
            continue
        value = raw[key]
        if key == 'length_mode':
            if value != 'tiered':
                raise ValueError('无效的篇幅模式')
            changes[key] = value
            continue
        if value is None or value == '':
            changes[key] = None
            continue
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            value = int(value)
        lower, upper = (0, 99) if key == 'word_tolerance_pct' else (1, 10_000_000)
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f'无效的篇幅设置 {key}，须为 {lower} 至 {upper} 之间的整数')
        changes[key] = value
    validate_length_mode(changes)
    return changes


def saved_brief_length(text: str) -> dict:
    """Recover the optional fields stored by earlier Studio wizards."""
    _, separator, tail = text.rpartition(BRIEF_LENGTH)
    if not separator:
        return {}
    try:
        raw = json.loads(tail)
    except ValueError:
        return {}
    return length_fields(parse_length_changes(raw)) if isinstance(raw, dict) else {}


def effective_brief_text(text: str, policy: dict | None) -> str:
    if policy is None:
        return text
    prefix, separator, tail = text.rpartition(BRIEF_LENGTH)
    if separator:
        try:
            old = json.loads(tail)
        except ValueError:
            old = None
        if isinstance(old, dict) and set(old) <= set(LENGTH_FIELDS):
            text = prefix
    return text + BRIEF_LENGTH + canonical(length_fields(policy))
