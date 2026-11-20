"""Project length preferences shared by the wizard and frozen design tasks."""
import json
from typing import Mapping

from nw.task_models import canonical

WORD_FIELDS = ('target_words', 'chapter_target_words', 'scene_target_words')
LENGTH_FIELDS = (*WORD_FIELDS, 'chapter_count', 'volume_count', 'word_tolerance_pct')
BRIEF_LENGTH = '\n\n立项参数：\n'


def length_fields(values: Mapping) -> dict:
    return {key: values[key] for key in LENGTH_FIELDS if values.get(key) is not None}


def parse_length_changes(raw: dict) -> dict:
    changes = {}
    for key in LENGTH_FIELDS:
        if key not in raw:
            continue
        value = raw[key]
        if value is None or value == '':
            changes[key] = None
            continue
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            value = int(value)
        lower, upper = (0, 99) if key == 'word_tolerance_pct' else (1, 10_000_000)
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f'无效的篇幅设置 {key}，须为 {lower} 至 {upper} 之间的整数')
        changes[key] = value
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
