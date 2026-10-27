# -*- coding: utf-8 -*-
"""Seed schema-valid test placeholder consumption records for four evidence files."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    header = {"schema_version": "1.0", "total_records": len(records), "last_updated": timestamp()}
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in [header, *records]) + "\n", encoding="utf-8")


def main() -> None:
    type_index = read_json(EVIDENCE / "type_connection_global_index.json")
    combinations = type_index["combinations"][:3]
    type_records = []
    for number, combo in enumerate(combinations, 1):
        mechanisms = combo.get("recommended_mechanisms") or ["测试占位机制，待项目确认"]
        type_records.append({
            "record_id": f"TCA-TEST-{number:03d}",
            "project_id": "TEST-PROJECT",
            "combination_id": combo["combination_id"],
            "source_type": "from_type_connection",
            "source_connection_ids": combo.get("connection_ids", []),
            "selected_mechanisms": mechanisms[:1],
            "selected_reason": "测试占位记录，待项目确认",
            "status": "test_placeholder",
            "adopted_at": timestamp(),
        })
    write_jsonl(EVIDENCE / "type_connection_adoption.jsonl", type_records)

    dynamic_rows = read_jsonl(EVIDENCE / "dynamic_chain_index.jsonl")
    dynamic_full = read_json(ROOT / "四网络连接，剧情覆盖" / "dynamic_connections.full.json")["connections"]
    original_ids = {row["id"] for row in dynamic_full if row.get("status") == "original"}
    selected_chains = [chain for chain in dynamic_rows if any(edge_id in original_ids for edge_id in chain.get("ids", []))][:3]
    if len(selected_chains) < 3:
        raise ValueError("动态链索引中不足 3 条可关联 original 连接的链")
    dynamic_records = [{
        "record_id": f"DCC-TEST-{number:03d}",
        "project_id": "TEST-PROJECT",
        "chain_id": chain["chain_id"],
        "consumed_in_design": "测试占位记录，待项目确认",
        "status": "test_placeholder",
        "consumed_at": timestamp(),
    } for number, chain in enumerate(selected_chains, 1)]
    write_jsonl(EVIDENCE / "dynamic_chain_consumption.jsonl", dynamic_records)

    static_logs = read_jsonl(EVIDENCE / "static_network_binding_repair_log.jsonl")
    core_edges = [row for row in static_logs if row.get("new_mainline_level") == "核心"][:3]
    if len(core_edges) < 3:
        raise ValueError("静态网络核心级连接少于 3 条")
    static_records = [{
        "record_id": f"SCC-TEST-{number:03d}",
        "project_id": "TEST-PROJECT",
        "edge_id": edge["edge_id"],
        "source": edge["source"],
        "target": edge["target"],
        "bound_to": {"type": "角色", "id": f"TEST-CHAR-{number:03d}"},
        "confidence": "high",
        "status": "test_placeholder",
        "consumed_at": timestamp(),
    } for number, edge in enumerate(core_edges, 1)]
    write_jsonl(EVIDENCE / "static_connection_consumption.jsonl", static_records)

    anchor_logs = read_jsonl(EVIDENCE / "anchor_network_repair_log.jsonl")
    anchors = []
    categories_seen = set()
    for row in anchor_logs:
        if row.get("category") not in categories_seen and row.get("status") != "duplicate":
            categories_seen.add(row["category"])
            anchors.append(row)
        if len(anchors) == 3:
            break
    if len(anchors) < 3:
        raise ValueError("锚点类别不足 3 个")
    anchor_records = [{
        "record_id": f"AC-TEST-{number:03d}",
        "project_id": "TEST-PROJECT",
        "anchor_id": row["new_anchor_id"],
        "anchor_category": row["category"],
        "bound_to_scene": f"SCENE-TEST-{number:03d}",
        "confidence": "high",
        "status": "test_placeholder",
        "consumed_at": timestamp(),
    } for number, row in enumerate(anchors, 1)]
    write_jsonl(EVIDENCE / "anchor_consumption.jsonl", anchor_records)

    print(json.dumps({
        "type_connection_adoption": {"new_records": len(type_records), "preview": type_records[0]},
        "dynamic_chain_consumption": {"new_records": len(dynamic_records), "preview": dynamic_records[0]},
        "static_connection_consumption": {"new_records": len(static_records), "preview": static_records[0]},
        "anchor_consumption": {"new_records": len(anchor_records), "preview": anchor_records[0]},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()