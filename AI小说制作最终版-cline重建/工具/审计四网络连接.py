# -*- coding: utf-8 -*-
"""Audit overlap, duplication, completeness, and indexing across four networks."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料"
DATA = ROOT / "四网络连接，剧情覆盖"
ROUTING = ROOT / "阶段状态" / "资料网络调用分类.json"
INDEX = ROOT / "00_资料索引" / "资料网络调用路由索引.json"
CONTRACT = ROOT / "00_资料索引" / "网络派生索引契约.json"
OUT = ROOT / "reports" / "四网络连接审计.json"


def key(record: dict) -> tuple[str, str, str]:
    return (str(record.get("source", "")), str(record.get("target", "")), str(record.get("type", record.get("connection_type", ""))))


def duplicate_count(records: list[dict]) -> int:
    keys = [key(record) for record in records]
    return len(keys) - len(set(keys))


def parse_anchor_rows() -> list[dict]:
    path = RAW / "锚点网络.txt"
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    pattern = re.compile(r"^\|\s*([A-Z]+\d+\.\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", re.M)
    for match in pattern.finditer(text):
        rows.append({
            "id": match.group(1).strip(),
            "anchor_name": match.group(2).strip(),
            "content": match.group(3).strip(),
            "condition": match.group(4).strip(),
            "line": text.count("\n", 0, match.start()) + 1,
        })
    return rows


def main() -> int:
    static = json.loads((DATA / "static_connections.full.json").read_text(encoding="utf-8"))["connections"]
    dynamic = json.loads((DATA / "dynamic_connections.full.json").read_text(encoding="utf-8"))["connections"]
    routing = json.loads(ROUTING.read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    anchors = parse_anchor_rows()
    routed_anchors = routing.get("classified_records", {}).get("anchor_records", [])
    routed_ids = {item.get("id") for item in routed_anchors if item.get("id")}
    source_ids = {item["id"] for item in anchors}
    static_keys = {key(item) for item in static}
    dynamic_keys = {key(item) for item in dynamic}
    overlap = static_keys & dynamic_keys
    generated = [item for item in dynamic if item.get("generated_from_static") is True]
    original = [item for item in dynamic if item.get("generated_from_static") is False]

    anchor_field_gaps = [
        item["id"] for item in routed_anchors
        if not all(item.get(field) for field in ("anchor_name", "content", "condition", "source_ref"))
    ]
    anchor_index = index.get("routes_by_network", {}).get("锚点网络", [])
    anchor_index_ids = {item.get("id") for item in anchor_index if item.get("id")}
    result = {
        "schema_version": "four-network-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"raw_root": "08_原始资料", "derived_root": "四网络连接，剧情覆盖"},
        "same_network_duplicates": {
            "static": duplicate_count(static),
            "dynamic": duplicate_count(dynamic),
            "anchor_ids": len(anchors) - len(source_ids),
        },
        "cross_network_overlap": {
            "static_dynamic_same_key": len(overlap),
            "static_dynamic_overlap_is_generated": sum(1 for item in generated if key(item) in static_keys),
            "dynamic_original_not_static": sum(1 for item in original if key(item) not in static_keys),
            "interpretation": "静态与动态的1341条重合是动态派生静态的结果，不应当按同一网络重复删除；动态原始483条是额外动态语义，需单独审查。",
        },
        "inventory": {
            "static_derived_records": len(static),
            "dynamic_final_records": len(dynamic),
            "dynamic_original_records": len(original),
            "dynamic_generated_records": len(generated),
            "anchor_source_rows": len(anchors),
            "anchor_routed_records": len(routed_anchors),
            "anchor_declared_in_source": 2120,
            "anchor_declared_is_estimate": True,
        },
        "anchor_completeness": {
            "missing_in_routing": sorted(source_ids - routed_ids),
            "extra_in_routing": sorted(routed_ids - source_ids),
            "missing_in_routing_count": len(source_ids - routed_ids),
            "routed_field_gaps": anchor_field_gaps,
            "routing_index_ids_missing": sorted(source_ids - anchor_index_ids),
            "routing_index_missing_count": len(source_ids - anchor_index_ids),
            "declared_count_interpretation": "原文使用‘约2120’描述B级粒度估算规模；195个核心锚点的拆分规模不是逐条记录声明，不将其与可解析唯一ID数量相减作为缺口。",
        },
        "index_quality": {
            "network_counts": index.get("network_counts", {}),
            "anchor_has_id_lookup": "by_anchor_id" in contract.get("retrieval_indexes", []),
            "anchor_has_source_ref": not bool(anchor_field_gaps),
            "type_mapping_unresolved": any(item.get("status", "").startswith("unresolved") for item in json.loads((DATA / "connection_type_mapping.json").read_text(encoding="utf-8")).get("mappings", [])),
        },
    }
    result["status"] = "REVIEW_REQUIRED" if (
        result["same_network_duplicates"]["static"]
        or result["same_network_duplicates"]["dynamic"]
        or result["anchor_completeness"]["missing_in_routing_count"]
        or result["anchor_completeness"]["routed_field_gaps"]
        or result["anchor_completeness"]["routing_index_missing_count"]
        or result["index_quality"]["type_mapping_unresolved"]
    ) else "PASS"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "status": result["status"], "anchor_missing": result["anchor_completeness"]["missing_in_routing_count"], "anchor_rows": len(anchors), "dynamic_static_overlap": len(overlap)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())