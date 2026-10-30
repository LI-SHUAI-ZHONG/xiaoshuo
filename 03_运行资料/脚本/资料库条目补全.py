"""Backfill runtime-readable fields from every raw library entry.

The raw library remains authoritative. This command only rebuilds the derived
index and normalized governance view; it never invents missing instructions.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "文档" / "资料库索引.jsonl"
NORMALIZED = ROOT / "文档" / "证据" / "全量资料治理" / "资料库_规范化.json"


def _load_repair_module():
    path = Path(__file__).with_name("修复资料库全量索引.py")
    spec = importlib.util.spec_from_file_location("library_index_repair_for_backfill", path)
    if not spec or not spec.loader:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    module = _load_repair_module()
    module.ROOT = root
    module.RAW = root / "原始资料" / "资料库.txt"
    module.INDEX = root / "文档" / "资料库索引.jsonl"
    rows = module.parse_raw()
    old_rows = module.load_index()
    old_by_id = {str(row.get("entry_id")): row for row in old_rows if row.get("entry_id")}
    # Keep legacy rows so existing bindings remain auditable, while current raw
    # entries receive the new source-derived fields.
    for entry_id, old in old_by_id.items():
        if entry_id not in rows:
            legacy = dict(old)
            legacy["source_status"] = "legacy_unmatched"
            legacy["legacy_reason"] = "旧索引存在，但当前原始资料没有同名条目标题；保留以兼容既有运行引用"
            rows[entry_id] = legacy
    index = module.INDEX
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in sorted(rows.values(), key=lambda row: module.sort_key(row["entry_id"]))) + "\n", encoding="utf-8", newline="\n")
    normalized = root / "文档" / "证据" / "全量资料治理" / "资料库_规范化.json"
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text(json.dumps(list(sorted(rows.values(), key=lambda row: module.sort_key(row["entry_id"]))), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending = sum((row.get("usage_method") or {}).get("status") != "source_complete" for row in rows.values())
    return {"status": "passed", "entry_count": len(rows), "raw_entry_count": len(module.parse_raw()), "legacy_preserved_count": len(rows) - len(module.parse_raw()), "pending_usage_method_count": pending, "index": str(index), "normalized": str(normalized)}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))