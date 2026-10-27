"""Validate the indexed-data to execution-output closure and write its report."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"
OUTPUT_DIR = EVIDENCE / "execution_outputs"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def main() -> dict:
    execution = load_jsonl(EVIDENCE / "execution_consumption.jsonl")
    execution_records = execution[1:]
    by_module = {row["module_id"]: row for row in execution_records}
    expected_inputs = {
        "02": {"08_原始资料\\类型系统.txt", "docs\\evidence\\type_connection_global_index.json"},
        "04": {"docs\\evidence\\static_network_index.json"},
        "05": {"docs\\evidence\\anchor_category_index.json"},
        "06": {"四网络连接，剧情覆盖\\dynamic_connections.full.json"},
        "08": {"四网络连接，剧情覆盖\\dynamic_connections.full.json", "docs\\evidence\\anchor_category_index.json"},
        "09": {"docs\\evidence\\anchor_category_index.json"},
    }
    data_flow = {
        f"module_{module_id}": by_module.get(module_id, {}).get("status") == "success"
        and expected.issubset(set(by_module[module_id].get("input_files", [])))
        for module_id, expected in expected_inputs.items()
    }
    transfer = load_json(OUTPUT_DIR / "module_11_transfer_summary.json")
    data_flow["module_11"] = transfer.get("module_count") == 10 and set(transfer.get("modules_received", [])) == {f"{i:02d}" for i in range(1, 11)}

    output_paths = sorted(OUTPUT_DIR.glob("module_*.json"))
    valid_outputs = len(output_paths) == 11 and all(path.stat().st_size > 2 and isinstance(load_json(path), dict) for path in output_paths)

    type_records = load_jsonl(EVIDENCE / "type_connection_adoption.jsonl")[1:]
    dynamic_records = load_jsonl(EVIDENCE / "dynamic_chain_consumption.jsonl")[1:]
    static_records = load_jsonl(EVIDENCE / "static_connection_consumption.jsonl")[1:]
    anchor_records = load_jsonl(EVIDENCE / "anchor_consumption.jsonl")[1:]
    type_index = load_json(EVIDENCE / "type_connection_global_index.json")
    dynamic_index = load_jsonl(EVIDENCE / "dynamic_chain_index.jsonl")
    dynamic_full = load_json(ROOT / "四网络连接，剧情覆盖" / "dynamic_connections.full.json").get("connections", [])
    static_index = load_json(EVIDENCE / "static_network_index.json")
    static_log = load_jsonl(EVIDENCE / "static_network_binding_repair_log.jsonl")
    anchor_index = load_json(EVIDENCE / "anchor_category_index.json")
    anchor_log = load_jsonl(EVIDENCE / "anchor_network_repair_log.jsonl")

    combinations = {item["combination_id"]: item for item in type_index.get("combinations", [])}
    type_traceable = all(row["combination_id"] in combinations and set(row["source_connection_ids"]).issubset(set(combinations[row["combination_id"]].get("connection_ids", []))) for row in type_records)
    full_dynamic_ids = {row.get("id") for row in dynamic_full}
    dynamic_traceable = all(row["chain_id"] in {item["chain_id"] for item in dynamic_index} and set(next(item["ids"] for item in dynamic_index if item["chain_id"] == row["chain_id"])).issubset(full_dynamic_ids) for row in dynamic_records)
    static_edge_rows = static_index.get("edges") or static_index.get("connections") or static_log
    static_edges = {edge.get("edge_id"): edge for edge in static_edge_rows}
    static_traceable = all(row["edge_id"] in static_edges and static_edges[row["edge_id"]].get("source") == row["source"] and static_edges[row["edge_id"]].get("target") == row["target"] for row in static_records)
    category_codes = {"M": "物质", "S": "空间", "P": "感知", "B": "身体", "E": "情绪", "C": "认知", "T": "想法", "D": "决策", "A": "行动", "L": "语言", "ID": "身份", "U": "意外"}
    anchors = {row.get("new_anchor_id"): row for row in anchor_log}
    def anchor_code(anchor_id: str) -> str:
        match = re.match(r"[A-Za-z]+", anchor_id)
        return match.group(0) if match else ""

    anchor_traceable = all(row["anchor_id"] in anchors and anchors[row["anchor_id"]].get("category") == row["anchor_category"] and anchor_code(row["anchor_id"]) in anchor_index.get("category_counts", {}) and anchor_index["category_counts"][anchor_code(row["anchor_id"])] > 0 for row in anchor_records)

    report = {
        "validation_date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "execution_pipeline": {"success": len(execution_records) == 11 and all(row.get("status") == "success" for row in execution_records), "modules": len(execution_records), "failed": sum(row.get("status") != "success" for row in execution_records)},
        "data_flow": data_flow,
        "output_files": {"generated": len(output_paths) if valid_outputs else len(output_paths), "expected": 11},
        "consumption_records": {"execution": len(execution_records), "type_connection": len(type_records), "dynamic": len(dynamic_records), "static": len(static_records), "anchor": len(anchor_records)},
        "source_traceability": {"type_connection": type_traceable, "dynamic": dynamic_traceable, "static": static_traceable, "anchor": anchor_traceable},
    }
    closed = report["execution_pipeline"]["success"] and all(data_flow.values()) and valid_outputs and all(value == 3 for key, value in report["consumption_records"].items() if key != "execution") and all(report["source_traceability"].values())
    report["conclusion"] = "CLOSED" if closed else "PARTIAL" if report["execution_pipeline"]["modules"] else "FAILED"
    (EVIDENCE / "closure_validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"execution_pipeline": report["execution_pipeline"], "data_flow": report["data_flow"], "output_files": report["output_files"], "consumption_records": report["consumption_records"], "source_traceability": report["source_traceability"], "conclusion": report["conclusion"]}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    main()