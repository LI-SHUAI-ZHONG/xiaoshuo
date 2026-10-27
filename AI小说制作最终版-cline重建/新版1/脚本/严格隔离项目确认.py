"""Prepare and audit explicit project confirmations for strict quarantines.

This module never changes source status or formal-fact eligibility. A passing
confirmation audit is evidence for a later, separately authorized re-audit.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONFIRMABLE_CATEGORIES = {
    "candidate_requires_project_confirmation",
    "pending_requires_project_confirmation",
}
SCHEMA_VERSION = "strict-quarantine-project-confirmation-1.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append({"_line": number, "_parse_error": str(exc)})
            continue
        rows.append(row if isinstance(row, dict) else {"_line": number, "_parse_error": "确认记录必须是对象"})
    return rows


def _confirmation_template(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "upgrade_id": record["upgrade_id"],
        "source_id": record["source_id"],
        "source_object_id": record["source_id"],
        "exact_locator": record["source_ref"],
        "source_ref_sha256": record["source_ref_sha256"],
        "source_object_sha256": record["source_item_sha256"],
        "intended_scope": None,
        "decision": None,
        "approved_by": None,
        "approved_at": None,
        "decision_rationale": None,
        "confirmation_status": "pending_explicit_project_decision",
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
    }


def _schema() -> dict[str, Any]:
    return {
        "schema_version": "strict-quarantine-project-confirmation-schema-1.0",
        "confirmation_record_schema_version": SCHEMA_VERSION,
        "scope": "explicit_review_only; does_not_grant_formal_fact_eligibility",
        "required_fields_for_approved_decision": [
            "schema_version", "upgrade_id", "source_id", "source_object_id", "exact_locator",
            "source_ref_sha256", "source_object_sha256", "intended_scope", "decision",
            "approved_by", "approved_at", "decision_rationale",
        ],
        "allowed_decisions": ["approved", "rejected"],
        "immutable_binding": [
            "upgrade_id", "source_id", "source_object_id", "exact_locator",
            "source_ref_sha256", "source_object_sha256",
        ],
        "prohibitions": [
            "不得确认 candidate_identity_missing、locator_invalid_or_out_of_range 或 object_boundary_missing 条目。",
            "不得以文件名和数组下标推断 source_object_id。",
            "确认审计通过不自动授予 formal_fact_eligible，也不允许正文写入。",
        ],
    }


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    source_dir = root / "文档" / "证据" / "严格资料升级"
    classification = source_dir / "严格隔离分类" / "严格隔离分类清单.jsonl"
    if not classification.is_file():
        raise FileNotFoundError(f"找不到隔离分类清单: {classification}")
    records = _read_jsonl(classification)
    if any("_parse_error" in record for record in records):
        raise ValueError("隔离分类清单包含无效 JSON")
    confirmable = [record for record in records if record.get("category_id") in CONFIRMABLE_CATEGORIES]
    replacement = [record for record in records if record.get("category_id") not in CONFIRMABLE_CATEGORIES]
    templates = [_confirmation_template(record) for record in confirmable]
    output = source_dir / "严格隔离项目确认"
    staging = source_dir / ".严格隔离项目确认_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    report = {
        "schema_version": "strict-quarantine-project-confirmation-queue-report-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_queue_for_explicit_project_confirmation",
        "input_classification": "文档/证据/严格资料升级/严格隔离分类/严格隔离分类清单.jsonl",
        "confirmable_record_count": len(templates),
        "replacement_required_record_count": len(replacement),
        "confirmable_category_counts": dict(Counter(record["category_id"] for record in confirmable)),
        "replacement_category_counts": dict(Counter(record["category_id"] for record in replacement)),
        "formal_fact_eligible_count": 0,
        "prose_write_allowed": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
    }
    (staging / "严格隔离项目确认模式.json").write_text(json.dumps(_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "待项目确认清单.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in templates), encoding="utf-8")
    (staging / "必须替换来源清单.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in replacement), encoding="utf-8")
    (staging / "严格隔离项目确认队列报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if len(templates) + len(replacement) != len(records):
        raise RuntimeError("项目确认队列完整性检查失败")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def _audit_row(row: dict[str, Any], baseline: dict[str, dict[str, Any]], seen: set[str]) -> list[str]:
    if "_parse_error" in row:
        return [f"无效 JSON: {row['_parse_error']}"]
    errors: list[str] = []
    upgrade_id = row.get("upgrade_id")
    if not isinstance(upgrade_id, str) or not upgrade_id:
        return ["缺少 upgrade_id"]
    if upgrade_id in seen:
        errors.append("重复的 upgrade_id 确认")
    seen.add(upgrade_id)
    expected = baseline.get(upgrade_id)
    if expected is None:
        return errors + ["upgrade_id 不在可确认队列中，可能属于未批准状态或缺少身份链接的隔离项"]
    if row.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version 不匹配")
    for field in ("source_id", "source_object_id", "exact_locator", "source_ref_sha256", "source_object_sha256"):
        if row.get(field) != expected.get(field):
            errors.append(f"不可变绑定不匹配: {field}")
    for field in ("source_ref_sha256", "source_object_sha256"):
        if not isinstance(row.get(field), str) or not SHA256_RE.fullmatch(row[field]):
            errors.append(f"SHA-256 格式无效: {field}")
    decision = row.get("decision")
    if decision not in {"approved", "rejected"}:
        errors.append("decision 必须为 approved 或 rejected")
    if decision == "approved":
        for field in ("intended_scope", "approved_by", "approved_at", "decision_rationale"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"approved 决策缺少 {field}")
        if isinstance(row.get("approved_at"), str):
            try:
                datetime.fromisoformat(row["approved_at"].replace("Z", "+00:00"))
            except ValueError:
                errors.append("approved_at 必须是 ISO 8601 时间")
    return errors


def audit(root: str | Path, confirmation_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    queue_dir = root / "文档" / "证据" / "严格资料升级" / "严格隔离项目确认"
    queue = queue_dir / "待项目确认清单.jsonl"
    if not queue.is_file():
        raise FileNotFoundError(f"找不到项目确认队列: {queue}")
    submission = Path(confirmation_path).expanduser().resolve() if confirmation_path else root / "配置" / "严格隔离项目确认.jsonl"
    baseline = {row["upgrade_id"]: row for row in _read_jsonl(queue)}
    rows = _read_jsonl(submission)
    seen: set[str] = set()
    results = []
    for row in rows:
        errors = _audit_row(row, baseline, seen)
        results.append({
            "upgrade_id": row.get("upgrade_id"),
            "decision": row.get("decision"),
            "accepted_for_later_reaudit": not errors and row.get("decision") == "approved",
            "errors": errors,
            "formal_fact_eligible": False,
            "prose_write_allowed": False,
        })
    report = {
        "schema_version": "strict-quarantine-project-confirmation-audit-report-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "confirmation_validation_only; no_source_or_eligibility_promotion",
        "queue_path": str(queue.relative_to(root)),
        "submission_path": str(submission),
        "submitted_record_count": len(rows),
        "approved_for_later_reaudit_count": sum(result["accepted_for_later_reaudit"] for result in results),
        "rejected_record_count": sum(bool(result["errors"]) for result in results),
        "formal_fact_eligible_count": 0,
        "prose_write_allowed": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
    }
    staging = queue_dir / ".严格隔离项目确认审计_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "严格隔离项目确认审计报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "严格隔离项目确认审计清单.jsonl").write_text("".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results), encoding="utf-8")
    for name in ("严格隔离项目确认审计报告.json", "严格隔离项目确认审计清单.jsonl"):
        target = queue_dir / name
        target.unlink(missing_ok=True)
        (staging / name).replace(target)
    staging.rmdir()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--confirmation-path")
    args = parser.parse_args()
    result = audit(args.project_root, args.confirmation_path) if args.audit else build(args.project_root)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())