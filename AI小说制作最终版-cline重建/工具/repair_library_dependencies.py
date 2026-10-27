# -*- coding: utf-8 -*-
"""Repair library entry dependencies from the source material in priority order."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "library_index.jsonl"
SOURCE_PATH = ROOT / "08_原始资料" / "资料库.txt"
LOG_PATH = ROOT / "docs" / "evidence" / "library_dependency_repair_log.jsonl"

ENTRY_HEADER = re.compile(r"^###\s+(.+?)\s*$", re.M)
SECTION_HEADER = re.compile(r"^【(.+?)】\s*$", re.M)
ID_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?_[^\s，。、；：:（）()\[\]【】]+")
BOARD_RE = re.compile(r"板块\s*(\d+(?:\.\d+)?)")


def read_index() -> tuple[list[dict], set[str]]:
    rows = []
    with INDEX_PATH.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row.get("entry_id"), str):
                raise ValueError(f"line {line_number}: missing entry_id")
            rows.append(row)
    ids = {row["entry_id"] for row in rows}
    if len(rows) != 418 or len(ids) != 418:
        raise ValueError(f"expected 418 unique index entries, got rows={len(rows)}, ids={len(ids)}")
    return rows, ids


def parse_source() -> dict[str, dict[str, str]]:
    text = SOURCE_PATH.read_text(encoding="utf-8")
    matches = list(ENTRY_HEADER.finditer(text))
    entries = {}
    for position, match in enumerate(matches):
        entry_id = match.group(1).strip()
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        body = text[match.end():end]
        sections = {}
        section_matches = list(SECTION_HEADER.finditer(body))
        for index, section in enumerate(section_matches):
            section_end = section_matches[index + 1].start() if index + 1 < len(section_matches) else len(body)
            sections[section.group(1).strip()] = body[section.end():section_end].strip()
        entries[entry_id] = sections
    return entries


def board_ids(value: str, valid_ids: set[str]) -> set[str]:
    result = set()
    for number in BOARD_RE.findall(value):
        prefix = number + "."
        result.update(entry_id for entry_id in valid_ids if entry_id.startswith(prefix))
    return result


def explicit_ids(value: str, valid_ids: set[str]) -> set[str]:
    return {candidate for candidate in ID_RE.findall(value) if candidate in valid_ids}


def dependencies_for(entry_id: str, sections: dict[str, str], valid_ids: set[str]) -> tuple[list[str], str]:
    related_board = sections.get("关联板块", "")
    related_path = sections.get("关联路径", "")
    definition = sections.get("定义", "")

    dependencies = board_ids(related_board, valid_ids) | explicit_ids(related_board, valid_ids)
    source = "关联板块"
    if not dependencies:
        dependencies = explicit_ids(related_path, valid_ids) | board_ids(related_path, valid_ids)
        source = "关联路径"
    if not dependencies:
        dependencies = explicit_ids(definition, valid_ids)
        source = "定义扫描"
    dependencies.discard(entry_id)
    return sorted(dependencies), source


def main() -> int:
    rows, valid_ids = read_index()
    source_entries = parse_source()
    now = datetime.now(timezone.utc).isoformat()
    logs = []
    repaired = 0
    unresolved = 0

    for row in rows:
        entry_id = row["entry_id"]
        old = [item for item in row.get("dependencies", []) if item in valid_ids and item != entry_id]
        if old:
            new = sorted(set(old))
            source = "existing"
        else:
            new, source = dependencies_for(entry_id, source_entries.get(entry_id, {}), valid_ids)
        row["dependencies"] = new
        status = "existing" if old else ("repaired" if new else "unresolved")
        if status == "repaired":
            repaired += 1
        elif status == "unresolved":
            unresolved += 1
        logs.append({
            "entry_id": entry_id,
            "old_dependencies": old,
            "new_dependencies": new,
            "source": source,
            "status": status,
            "generated_at": now,
        })

    INDEX_PATH.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in logs),
        encoding="utf-8",
    )
    print(f"总条目数: {len(rows)}")
    print(f"已补依赖数: {repaired}")
    print(f"仍无依赖数: {unresolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())