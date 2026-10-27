# -*- coding: utf-8 -*-
"""Build a project-independent JSONL knowledge index for 资料库.txt."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "资料库.txt"
OUTPUT = ROOT / "docs" / "library_index.jsonl"

ENTRY_RE = re.compile(r"^###\s+(?P<header>(?P<entry_id>\d+(?:\.\d+)*_[^\r\n]+?))\s*$", re.M)
FIELD_RE = re.compile(r"^【(?P<field>[^】]+)】\s*$", re.M)
ID_RE = re.compile(r"(?<![\w.])(?P<entry_id>\d+(?:\.\d+)*_[^\s，。；：、（）()【】\[\]{}<>]+)")
EMPTY_VALUES = {"", "无", "暂无", "待补充", "待确认", "空", "[]", "{}"}
KNOWN_FIELDS = {"定义", "调用条件", "指令", "设计指令", "写作指令", "分级标准", "场景变体", "判定标准", "修正指南", "示例", "反面案例", "关联板块", "关联路径", "优先级", "例外处理", "调用标签"}


def meaningful(value: str) -> bool:
    value = re.sub(r"\\-", "-", value).strip()
    return value not in EMPTY_VALUES


def parse_fields(body: str) -> dict[str, str]:
    matches = list(FIELD_RE.finditer(body))
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group("field").strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        fields[name] = body[match.end() : end].strip()
    return fields


def infer_type(name: str, body: str, fields: dict[str, str]) -> str:
    text = f"{name}\n{body}"
    if re.search(r"模板|表格|格式|填空|清单|档案模板", text):
        return "模板"
    if "定义" in fields:
        # The library uses normative language inside ordinary definitions.
        # Treat the explicit definition section as the stronger type signal.
        return "概念"
    if re.search(r"规则|必须|禁止|不得|不可|不能|约束|门禁|判定标准|修正指南", text):
        return "规则"
    return "参考"


def parse_entries(text: str) -> tuple[list[dict], list[str]]:
    matches = list(ENTRY_RE.finditer(text))
    known_ids = {match.group("entry_id").strip() for match in matches}
    records: list[dict] = []
    invalid: list[str] = []
    for index, match in enumerate(matches):
        entry_id = match.group("entry_id").strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        name = entry_id.split("_", 1)[1].strip()
        fields = parse_fields(body)
        nonempty_fields = [field for field, value in fields.items() if field in KNOWN_FIELDS and meaningful(value)]
        if not body or not nonempty_fields:
            invalid.append(entry_id)

        dependency_text = "\n".join(
            fields.get(field, "") for field in ("调用条件", "关联板块", "关联路径", "例外处理", "修正指南")
        )
        dependencies = sorted(
            {
                dependency
                for dependency in ID_RE.findall(dependency_text)
                if dependency in known_ids and dependency != entry_id
            },
            key=lambda value: (tuple(int(part) for part in value.split("_", 1)[0].split(".")), value),
        )
        example = fields.get("示例", "")
        condition = fields.get("调用条件", "")
        records.append(
            {
                "entry_id": entry_id,
                "name": name,
                "type": infer_type(name, body, fields),
                "key_attributes": nonempty_fields,
                "dependencies": dependencies,
                "has_examples": meaningful(example),
                "has_conditions": meaningful(condition),
            }
        )
    return records, invalid


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8-sig")
    records, invalid = parse_entries(text)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"总条目数: {len(records)}")
    print(f"已索引条目数: {len(records) - len(invalid)}")
    print(f"无效/空条目数: {len(invalid)}")
    print(f"无效/空条目编号: {json.dumps(invalid, ensure_ascii=False)}")
    print(f"输出: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())