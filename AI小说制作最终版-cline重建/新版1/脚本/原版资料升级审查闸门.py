"""Classify review-only object upgrades before any human approval or fusion."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "original-material-upgrade-review-gate-1.0"
EXECUTION_ROOT = Path("文档/证据/原版资料升级执行")
OUTPUT_ROOT = Path("文档/证据/原版资料升级审查闸门")
DERIVED_METADATA_FIELDS = {"derivation_contract", "field_source", "generated_from_static", "source_refs", "validation_status"}
DERIVED_MARKERS = ("静态网络", "默认规则", "派生", "derivation")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _protected_reasons(record: dict[str, Any]) -> list[str]:
    before = record.get("before")
    changes = record.get("changes")
    if not isinstance(before, dict) or not isinstance(changes, list):
        return ["记录缺少可验证的 before 或 changes。"]
    field_source = before.get("field_source") if isinstance(before.get("field_source"), dict) else {}
    reasons = []
    for change in changes:
        field = change.get("field_path") if isinstance(change, dict) else None
        if not isinstance(field, str):
            reasons.append("变更缺少有效字段路径。")
            continue
        if field in DERIVED_METADATA_FIELDS:
            reasons.append(f"{field} 是派生元数据字段。")
        source = str(field_source.get(field, ""))
        if any(marker in source.lower() for marker in DERIVED_MARKERS):
            reasons.append(f"{field} 的字段来源为派生/静态规则：{source}")
    return reasons


def gate(root: str | Path, execution_run_id: str, gate_run_id: str) -> dict[str, Any]:
    project = Path(root).expanduser().resolve()
    source = project / EXECUTION_ROOT / execution_run_id / "upgrade_records.jsonl"
    output = project / OUTPUT_ROOT / gate_run_id
    if output.exists() or Path(gate_run_id).name != gate_run_id:
        raise ValueError("gate_run_id 非法或输出目录已存在")
    decisions = []
    for record in _rows(source):
        status = record.get("status")
        reasons = _protected_reasons(record) if status == "requires_human_review" else [f"执行状态为 {status}，没有可审查候选。"]
        decision = "rejected_protected_derived_change" if reasons and status == "requires_human_review" else "pending_human_review" if status == "requires_human_review" else "quarantined_execution_error"
        decisions.append({
            "schema_version": SCHEMA_VERSION,
            "upgrade_id": record.get("upgrade_id"),
            "original_object_id": record.get("original_object_id"),
            "source_id": record.get("source_id"),
            "execution_run_id": execution_run_id,
            "decision": decision,
            "reasons": reasons,
            "changes": record.get("changes", []),
            "writeback_allowed": False,
            "fusion_allowed": False,
        })
    output.mkdir(parents=True)
    for name, values in {
        "decisions": decisions,
        "pending_human_review": [row for row in decisions if row["decision"] == "pending_human_review"],
        "rejected": [row for row in decisions if row["decision"] != "pending_human_review"],
    }.items():
        (output / f"{name}.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in values), encoding="utf-8")
    report = {"schema_version": SCHEMA_VERSION, "generated_at": _now(), "execution_run_id": execution_run_id, "record_count": len(decisions), "decision_counts": dict(sorted(Counter(row["decision"] for row in decisions).items())), "writeback_allowed_count": 0, "fusion_allowed_count": 0, "original_sources_modified": False}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="对对象级升级候选执行派生字段保护预审")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--execution-run-id", required=True)
    parser.add_argument("--gate-run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(gate(args.project_root, args.execution_run_id, args.gate_run_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())