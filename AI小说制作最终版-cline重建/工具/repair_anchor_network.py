# -*- coding: utf-8 -*-
"""Normalize anchor IDs and categories in the Markdown anchor tables."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "锚点网络.txt"
LOG = ROOT / "docs" / "evidence" / "anchor_network_repair_log.jsonl"
SUMMARY = ROOT / "docs" / "evidence" / "anchor_network_summary.json"
CONSUMPTION = ROOT / "docs" / "evidence" / "anchor_consumption.jsonl"

ID_RE = re.compile(r"^(ID|M|S|P|B|E|C|T|D|A|L|U)(\d+)\.(\d+)(?:_(\d+))?$")
CATEGORY = {
    "M": "物质", "S": "空间", "P": "感知", "B": "身体", "E": "情绪", "C": "认知",
    "T": "想法", "D": "决策", "A": "行动", "L": "语言", "ID": "身份", "U": "意外",
}


def split_row(line: str) -> list[str] | None:
    if not line.lstrip().startswith("|"):
        return None
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    return parts if len(parts) >= 4 else None


def canonical_id(value: str) -> tuple[str, bool]:
    raw = value.strip()
    match = ID_RE.fullmatch(raw)
    if not match:
        return raw, False
    prefix, major, minor, suffix = match.groups()
    # The source tables use B1.1-style IDs; a trailing item suffix is retained
    # only as an input note and normalized to the same canonical anchor ID.
    return f"{prefix}{int(major)}.{int(minor)}", raw == f"{prefix}{int(major)}.{int(minor)}"


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8-sig")
    text = text.replace("| 编号 | 锚点名称 | 具体内容 | 触发条件 |", "| 编号 | 锚点名称 | 具体内容 | 触发条件 | 类别 |")
    text = text.replace("|------|---------|---------|---------|", "|------|---------|---------|---------|------|")
    lines = text.splitlines(keepends=True)
    seen: set[str] = set()
    logs: list[dict] = []
    categories = Counter()
    duplicates = 0
    total = 0
    output: list[str] = []

    for line in lines:
        parts = split_row(line)
        if not parts:
            output.append(line)
            continue
        original_id = parts[0]
        canonical, already_normal = canonical_id(original_id)
        if not ID_RE.fullmatch(original_id):
            output.append(line)
            continue
        total += 1
        prefix = ID_RE.fullmatch(canonical).group(1)
        category = CATEGORY.get(prefix)
        if category is None:
            name_blob = parts[1]
            category = next((value for key, value in CATEGORY.items() if key in name_blob), "待定")
        is_duplicate = canonical in seen
        if is_duplicate:
            duplicates += 1
            logs.append({
                "original_anchor_id": original_id,
                "new_anchor_id": canonical,
                "category": category,
                "name": parts[1],
                "status": "duplicate",
                "reason": "规范化后锚点 ID 与此前记录重复，保留第一条",
            })
            continue
        seen.add(canonical)
        categories[category] += 1
        new_parts = [canonical, parts[1], parts[2], parts[3], category]
        output.append("| " + " | ".join(new_parts) + " |\n")
        logs.append({
            "original_anchor_id": original_id,
            "new_anchor_id": canonical,
            "category": category,
            "name": parts[1],
            "status": "repaired" if not already_normal else "repaired",
        })

    SOURCE.write_text("".join(output), encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in logs), encoding="utf-8")
    ordered_categories = ("物质", "空间", "感知", "身体", "情绪", "认知", "想法", "决策", "行动", "语言", "身份", "意外")
    summary = {
        "total_anchors": total,
        "unique_anchors": len(seen),
        "duplicates": duplicates,
        "categories": {key: categories[key] for key in ordered_categories},
        "consumption_records": 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    header = {"schema_version": "1.0", "total_records": 0, "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    CONSUMPTION.write_text(json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "source": str(SOURCE), "repair_log": str(LOG), "summary": str(SUMMARY)}, ensure_ascii=False))


if __name__ == "__main__":
    main()