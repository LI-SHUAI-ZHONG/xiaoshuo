"""Assess whether strict quarantines can be recovered without source confirmation."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGET_CATEGORIES = {"locator_invalid_or_out_of_range", "object_boundary_missing"}


def _disposition(record: dict[str, Any]) -> tuple[str, str]:
    category = record["category_id"]
    if category == "locator_invalid_or_out_of_range":
        return (
            "requires_replacement_or_explicit_project_confirmation",
            "命名来源块可回读为单个 JSON 对象，但原 source_id 不对应对象内可核验标识；不得仅以文件名和 [1] 自动确认。",
        )
    if category == "object_boundary_missing":
        return (
            "permanently_unsuitable_unless_replaced",
            "matched_lines 跨越多个不连续位置，不能证明为同一来源对象；必须由具有单一边界和稳定定位的替代来源取代。",
        )
    raise ValueError(f"不支持的隔离分类: {category}")


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    source_dir = root / "文档" / "证据" / "严格资料升级"
    source = source_dir / "严格隔离分类" / "严格隔离分类清单.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"找不到隔离分类清单: {source}")
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    targets = [record for record in records if record.get("category_id") in TARGET_CATEGORIES]
    assessed: list[dict[str, Any]] = []
    for record in targets:
        disposition, reason = _disposition(record)
        assessed.append({
            "upgrade_id": record["upgrade_id"],
            "consumption_id": record["consumption_id"],
            "binding_id": record["binding_id"],
            "source_id": record["source_id"],
            "source_kind": record["source_kind"],
            "source_ref": record["source_ref"],
            "source_ref_sha256": record["source_ref_sha256"],
            "source_item_sha256": record["source_item_sha256"],
            "original_errors": record["errors"],
            "recoverability_disposition": disposition,
            "assessment_reason": reason,
            "formal_fact_eligible": False,
            "prose_write_allowed": False,
        })
    by_disposition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in assessed:
        by_disposition[record["recoverability_disposition"]].append(record)
    report = {
        "schema_version": "strict-quarantine-recoverability-assessment-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_assessment_of_locator_and_object_boundary_quarantines",
        "input_classification": "文档/证据/严格资料升级/严格隔离分类/严格隔离分类清单.jsonl",
        "assessed_record_count": len(assessed),
        "recoverable_by_deterministic_parser_count": 0,
        "formal_fact_eligible_count": 0,
        "prose_write_allowed": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
        "dispositions": [
            {
                "disposition": disposition,
                "count": len(items),
                "source_kind_counts": dict(Counter(item["source_kind"] for item in items)),
                "reason": items[0]["assessment_reason"],
            }
            for disposition, items in sorted(by_disposition.items())
        ],
    }
    output = source_dir / "严格隔离可恢复性评估"
    staging = source_dir / ".严格隔离可恢复性评估_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "严格隔离可恢复性评估报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "严格隔离可恢复性评估清单.jsonl").write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in assessed), encoding="utf-8")
    if len(assessed) != len(targets):
        raise RuntimeError("可恢复性评估清单完整性检查失败")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())