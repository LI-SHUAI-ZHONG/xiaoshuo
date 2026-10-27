"""Repair library_index dependencies from the read-only source material."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "library_index.jsonl"
SOURCE = ROOT / "08_原始资料" / "资料库.txt"
LOG = ROOT / "docs" / "evidence" / "library_dependency_repair_log.jsonl"
EMPTY = {"", "无", "暂无", "没有", "空", "[]", "{}"}
ID_PREFIX = re.compile(r"(?<![\w.])(\d+\.\d+)(?:[_-])")


def field(section: str, label: str) -> str:
    marker = f"【{label}】"
    start = section.find(marker)
    if start < 0:
        return ""
    value_start = start + len(marker)
    next_markers = [section.find("【", value_start), section.find("---", value_start)]
    ends = [value for value in next_markers if value >= 0]
    end = min(ends) if ends else len(section)
    return section[value_start:end].strip()


def extract_ids(text: str, entry_ids: set[str], by_number: dict[str, list[str]]) -> list[str]:
    found: list[str] = []
    # Matching the known IDs prevents arbitrary numeric strings in prose from
    # becoming dependencies. Longer IDs win when one name contains another.
    for entry_id in sorted(entry_ids, key=len, reverse=True):
        if entry_id in text and entry_id not in found:
            found.append(entry_id)
    board_refs = re.findall(r"板块\s*(\d+)(?:\s*[-~至到]\s*(\d+))?", text)
    for start_text, end_text in board_refs:
        start = int(start_text)
        end = int(end_text or start_text)
        for number, candidates in by_number.items():
            board = int(number.split(".", 1)[0])
            if start <= board <= end:
                found.extend(item for item in candidates if item not in found)
    if found:
        return sorted(found, key=lambda value: (float(value.split("_", 1)[0]), value))
    # A bare numeric reference is accepted only when it maps to one known ID.
    for number in dict.fromkeys(ID_PREFIX.findall(text)):
        candidates = by_number.get(number, [])
        if len(candidates) == 1 and candidates[0] not in found:
            found.append(candidates[0])
    return sorted(found, key=lambda value: (float(value.split("_", 1)[0]), value))


def main() -> int:
    records = [json.loads(line) for line in INDEX.read_text(encoding="utf-8").splitlines() if line.strip()]
    entry_ids = {record["entry_id"] for record in records}
    by_number: dict[str, list[str]] = {}
    for entry_id in entry_ids:
        number = entry_id.split("_", 1)[0]
        by_number.setdefault(number, []).append(entry_id)

    source_text = SOURCE.read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"(?=^###\s+\d+\.\d+_)", source_text, flags=re.M)
    source_sections = {}
    for section in sections:
        heading = re.match(r"^###\s+([^\r\n]+)", section)
        if heading:
            source_sections[heading.group(1).strip()] = section

    logs = []
    sources = Counter()
    repaired = 0
    unresolved = []
    for record in records:
        entry_id = record["entry_id"]
        section = source_sections.get(entry_id, "")
        related_block = field(section, "关联板块")
        related_path = field(section, "关联路径")
        definition = field(section, "定义")
        dependencies: list[str] = []
        source = "none"
        for label, value, source_name in (("关联板块", related_block, "关联板块"), ("关联路径", related_path, "关联路径"), ("定义", definition, "定义扫描")):
            if value.strip() in EMPTY:
                continue
            dependencies = [item for item in extract_ids(value, entry_ids, by_number) if item != entry_id]
            if dependencies or source_name == "定义扫描":
                source = source_name
                break
        old = record.get("dependencies", [])
        record["dependencies"] = dependencies
        if dependencies:
            repaired += 1
            sources[source] += 1
            status = "repaired"
        else:
            unresolved.append(entry_id)
            status = "unresolved"
        logs.append({"entry_id": entry_id, "old_dependencies": old, "new_dependencies": dependencies, "source": source, "status": status})

    # Validate every dependency against the exact input ID set before writing.
    invalid = [(log["entry_id"], dep) for log in logs for dep in log["new_dependencies"] if dep not in entry_ids]
    if invalid:
        raise RuntimeError(f"invalid dependencies: {invalid[:5]}")
    INDEX.write_text("\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records) + "\n", encoding="utf-8", newline="\n")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(json.dumps(log, ensure_ascii=False, separators=(",", ":")) for log in logs) + "\n", encoding="utf-8", newline="\n")
    print(f"总条目数：{len(records)}")
    print(f"已补全依赖的条目数：{repaired}")
    print(f"仍无依赖的条目数：{len(unresolved)}")
    print("依赖来源分布：" + "、".join(f"{name}={sources[name]}" for name in ("关联板块", "关联路径", "定义扫描")))
    if unresolved:
        print("仍无依赖条目：" + "、".join(unresolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())