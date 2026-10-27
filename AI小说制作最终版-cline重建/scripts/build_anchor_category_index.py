"""Extract anchor identifiers and build a compact category index."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "锚点网络.txt"
OUTPUT = ROOT / "docs" / "evidence" / "anchor_category_index.json"

CATEGORY_LIMITS = OrderedDict(
    (
        ("M", (9, 20)),
        ("S", (4, 20)),
        ("P", (5, 40)),
        ("B", (4, 40)),
        ("E", (4, 60)),
        ("C", (4, 40)),
        ("T", (3, 40)),
        ("D", (4, 40)),
        ("A", (5, 40)),
        ("L", (3, 30)),
        ("ID", (3, 20)),
        ("U", (3, 20)),
    )
)
ANCHOR_PATTERN = re.compile(r"(?<![A-Za-z0-9])(ID|M|S|P|B|E|C|T|D|A|L|U)(\d+)\.(\d+)(?![A-Za-z0-9])")


def extract_anchor_ids(text: str) -> list[str]:
    seen: set[str] = set()
    anchor_ids: list[str] = []
    for match in ANCHOR_PATTERN.finditer(text):
        prefix, major_text, minor_text = match.groups()
        major = int(major_text)
        minor = int(minor_text)
        max_major, max_minor = CATEGORY_LIMITS[prefix]
        if not (1 <= major <= max_major and 1 <= minor <= max_minor):
            continue
        anchor_id = match.group(0)
        if anchor_id not in seen:
            seen.add(anchor_id)
            anchor_ids.append(anchor_id)
    return anchor_ids


def main() -> None:
    anchor_ids = extract_anchor_ids(SOURCE.read_text(encoding="utf-8", errors="replace"))
    category_counts = OrderedDict((prefix, 0) for prefix in CATEGORY_LIMITS)
    for anchor_id in anchor_ids:
        prefix = "ID" if anchor_id.startswith("ID") else anchor_id[0]
        category_counts[prefix] += 1

    payload = {
        "total_anchors": len(anchor_ids),
        "category_counts": category_counts,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"总锚点数：{len(anchor_ids)}")
    print("各分类数量（" + ", ".join(f"{prefix}:{count}" for prefix, count in category_counts.items()) + "）")
    print("索引文件已生成")


if __name__ == "__main__":
    main()