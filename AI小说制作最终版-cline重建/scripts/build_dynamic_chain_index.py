"""Build a compact global index from validated chain metadata."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CANDIDATES = (
    ROOT / "docs" / "evidence" / "validated_by_tags.jsonl",
    ROOT / "validated_by_tags.jsonl",
)
INDEX = ROOT / "docs" / "evidence" / "dynamic_chain_index.jsonl"
SUMMARY = ROOT / "docs" / "evidence" / "dynamic_chain_index_summary.json"


def source_path() -> Path:
    for candidate in SOURCE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("validated_by_tags.jsonl not found in the supported paths")


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
        records.append(record)
    return records


def primary_tags(record: dict) -> list[str]:
    validation = record.get("tag_validation") or {}
    tags: list[str] = []
    seen: set[str] = set()
    for key in ("ab_overlap", "bc_overlap"):
        for tag in validation.get(key) or []:
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def main() -> None:
    source = source_path()
    records = load_records(source)
    tag_counts: Counter[str] = Counter()
    sources: set[str] = set()
    targets: set[str] = set()

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with INDEX.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            tags = primary_tags(record)
            tag_counts.update(tags)
            sources.update(record.get("sources") or [])
            targets.update(record.get("targets") or [])
            compact = {
                "chain_id": record.get("chain_id"),
                "ids": record.get("ids") or [],
                "sources": record.get("sources") or [],
                "targets": record.get("targets") or [],
                "primary_tags": tags,
            }
            stream.write(json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n")

    summary = {
        "total_chains": len(records),
        "tag_frequency": dict(sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))),
        "unique_source_nodes": sorted(sources),
        "unique_target_nodes": sorted(targets),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    top_tags = list(summary["tag_frequency"].items())[:5]
    print(f"总链数：{len(records)}")
    print("前 5 个最频繁的标签：" + ("、".join(f"{tag}({count})" for tag, count in top_tags) if top_tags else "无"))
    print(f"索引文件大小（行数）：{len(records)}")
    print("摘要文件已生成")


if __name__ == "__main__":
    main()