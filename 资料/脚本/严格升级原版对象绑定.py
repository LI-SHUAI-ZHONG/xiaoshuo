"""Bind frozen strict-upgrade records to hash-locked original-material objects."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "strict-upgrade-original-object-binding-1.0"
FREEZE_ROOT = Path("文档/资料融合工作区/输入冻结V1")
INDEX_PATH = Path("文档/证据/原版资料对象索引_V2/对象索引.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _records(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((root / FREEZE_ROOT / "严格升级批次").glob("SOURCE-UPGRADE-*.json")):
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        rows.extend(document.get("records", []))
    return rows


def bind(root: str | Path, output_name: str = "严格升级原版对象绑定") -> dict[str, Any]:
    project = Path(root).expanduser().resolve()
    output = project / "文档" / "证据" / output_name
    if output.exists():
        raise FileExistsError(f"绑定输出已存在，拒绝覆盖: {output}")
    objects = _jsonl(project / INDEX_PATH)
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in objects:
        if item.get("object_kind") == "json_object" and isinstance(item.get("identity"), str):
            by_identity[item["identity"]].append(item)
    rows = []
    for record in _records(project):
        source_id = str(record.get("source_id") or "")
        candidates = by_identity.get(source_id, [])
        status = "verified" if len(candidates) == 1 else "unmatched" if not candidates else "conflict"
        row = {
            "schema_version": SCHEMA_VERSION,
            "upgrade_id": record.get("upgrade_id"),
            "binding_id": record.get("binding_id"),
            "source_id": source_id,
            "source_kind": record.get("source_kind"),
            "historical_source_ref": record.get("source_ref"),
            "historical_source_item_sha256": record.get("source_item_sha256"),
            "binding_status": status,
            "original_object_id": candidates[0]["object_id"] if status == "verified" else None,
            "original_object_sha256": candidates[0]["content_sha256"] if status == "verified" else None,
            "original_source_file": candidates[0]["source_file"] if status == "verified" else None,
            "candidate_object_ids": [item["object_id"] for item in candidates] if status != "verified" else [],
            "writeback_allowed": False,
            "reason": "仅完成对象定位；严格升级记录没有 before/after 或候选字段值，不得写回。",
        }
        rows.append(row)
    rows.sort(key=lambda row: str(row["upgrade_id"]))
    output.mkdir(parents=True)
    groups = {
        "bindings": rows,
        "unmatched": [row for row in rows if row["binding_status"] == "unmatched"],
        "conflicts": [row for row in rows if row["binding_status"] == "conflict"],
    }
    for name, values in groups.items():
        (output / f"{name}.jsonl").write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "strict_upgrade_record_count": len(rows),
        "binding_status_counts": dict(sorted(Counter(row["binding_status"] for row in rows).items())),
        "writeback_allowed_count": 0,
        "files": {"bindings": "bindings.jsonl", "unmatched": "unmatched.jsonl", "conflicts": "conflicts.jsonl"},
        "original_sources_modified": False,
    }
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="绑定严格升级记录与当前原版资料对象")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-name", default="严格升级原版对象绑定")
    args = parser.parse_args()
    print(json.dumps(bind(args.project_root, args.output_name), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())