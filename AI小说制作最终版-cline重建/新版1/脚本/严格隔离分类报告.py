"""Classify strict-source-upgrade quarantines without changing source status or prose."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATEGORY_RULES = (
    ("candidate_identity_missing", "候选且对象标识缺失", "candidate source must be replaced or explicitly confirmed; add a stable object identifier before any re-audit", {"来源对象状态为 candidate", "类型连接对象缺少可核验标识"}),
    ("candidate_requires_project_confirmation", "候选状态", "candidate source requires explicit project-level confirmation or replacement; it must remain quarantined", {"来源对象状态为 candidate"}),
    ("pending_requires_project_confirmation", "待定状态", "pending source requires explicit project-level confirmation or replacement; it must remain quarantined", {"来源对象状态为 pending"}),
    ("locator_invalid_or_out_of_range", "定位无效或越界", "repair only with an exact source locator and object-identity proof, then re-audit", {"source_ref 文本数组或下标无效"}),
    ("object_boundary_missing", "对象边界缺失", "define one exact source object boundary with stable locator and object hash, then re-audit", {"source_ref 不具备可精确回读的受控定位格式"}),
)


def _category(errors: list[str]) -> tuple[str, str, str]:
    error_set = set(errors)
    for category_id, label, disposition, required_errors in CATEGORY_RULES:
        if error_set == required_errors:
            return category_id, label, disposition
    return "other_quarantine", "其他隔离原因", "do not confirm automatically; define a dedicated strict parser or obtain explicit project confirmation", ", ".join(errors)


def build(root: str | Path, sample_limit: int = 10) -> dict[str, Any]:
    if sample_limit < 1:
        raise ValueError("sample_limit 必须为正整数")
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    source_dir = evidence / "严格资料升级"
    archive = source_dir / "严格资料升级档案.jsonl"
    if not archive.is_file():
        raise FileNotFoundError(f"找不到严格升级档案: {archive}")
    records = [json.loads(line) for line in archive.read_text(encoding="utf-8").splitlines() if line.strip()]
    quarantined = [record for record in records if record.get("status") == "quarantined"]
    categorized: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in quarantined:
        category_id, label, disposition = _category(list(record.get("errors") or []))
        categorized[category_id].append({
            "category_id": category_id,
            "category_label": label,
            "required_disposition": disposition,
            "upgrade_id": record.get("upgrade_id"),
            "consumption_id": record.get("consumption_id"),
            "binding_id": record.get("binding_id"),
            "source_id": record.get("source_id"),
            "source_kind": record.get("source_kind"),
            "source_ref": record.get("source_ref"),
            "source_ref_sha256": record.get("source_ref_sha256"),
            "source_item_sha256": record.get("source_item_sha256"),
            "errors": record.get("errors"),
            "prose_write_allowed": False,
            "formal_fact_eligible": False,
        })
    output = source_dir / "严格隔离分类"
    staging = source_dir / ".严格隔离分类_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    categories = []
    for category_id in sorted(categorized):
        items = categorized[category_id]
        categories.append({
            "category_id": category_id,
            "category_label": items[0]["category_label"],
            "required_disposition": items[0]["required_disposition"],
            "count": len(items),
            "source_kind_counts": dict(Counter(str(item["source_kind"]) for item in items)),
            "samples": items[:sample_limit],
        })
    report = {
        "schema_version": "strict-quarantine-classification-report-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_classification_of_existing_strict_quarantines",
        "input_archive": "文档/证据/严格资料升级/严格资料升级档案.jsonl",
        "quarantined_record_count": len(quarantined),
        "category_count": len(categories),
        "prose_write_allowed": False,
        "formal_fact_eligible": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
        "categories": categories,
    }
    (staging / "严格隔离分类报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    detail_rows = [item for category_id in sorted(categorized) for item in categorized[category_id]]
    (staging / "严格隔离分类清单.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in detail_rows), encoding="utf-8")
    if len(detail_rows) != len(quarantined):
        raise RuntimeError("隔离分类清单完整性检查失败")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--sample-limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.sample_limit), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())