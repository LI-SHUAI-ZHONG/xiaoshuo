"""Audit the complete authorization boundary before full-source prose release."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 全量资料输入与正文授权 import AUTHORIZATION_DIR, AUDITED_FILE, authorized_bindings
from 全量资料历史消费隔离 import ARCHIVE_FILE, CONSUMPTION_FILE, REGISTRY_FILE, _canonical_hash


SCHEMA_VERSION = "full-source-strict-isolation-audit-1.0"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append({"_line": number, "_parse_error": str(exc)})
            continue
        rows.append(row if isinstance(row, dict) else {"_line": number, "_parse_error": "JSONL 行必须为对象"})
    return rows


def _issue(scope: str, record: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "scope": scope,
        "binding_id": record.get("binding_id"),
        "consumption_id": record.get("consumption_id"),
        "source_id": record.get("source_id") or record.get("source", {}).get("source_id"),
        "message": message,
    }


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _legacy_quarantine_errors(evidence: Path, consumed: list[dict[str, Any]], archive: list[dict[str, Any]], active_ids: set[str]) -> list[str]:
    if not consumed and not archive:
        return []
    registry = _read(evidence / REGISTRY_FILE, {})
    if not isinstance(registry, dict):
        return ["历史消费隔离清单缺失或无法解析"]
    entries = registry.get("entries", [])
    indexed = {row.get("consumption_id"): row for row in entries if isinstance(row, dict) and row.get("consumption_id")}
    archive_by_id = {row.get("consumption_id"): row for row in archive if row.get("consumption_id")}
    consumed_ids = {row.get("consumption_id") for row in consumed if row.get("consumption_id")}
    expected = set(indexed)
    errors = []
    current_archive_ids = set(archive_by_id) - expected
    current_consumed_ids = consumed_ids - expected
    if current_consumed_ids != current_archive_ids:
        errors.append("当前正文消费证据与当前升级档案的覆盖范围不一致")
    for consumption_id in expected:
        entry, consumption, archive_row = indexed.get(consumption_id), next((row for row in consumed if row.get("consumption_id") == consumption_id), None), archive_by_id.get(consumption_id)
        if not isinstance(entry, dict) or not isinstance(archive_row, dict):
            errors.append(f"历史隔离清单记录无法回读: {consumption_id}")
            continue
        if entry.get("quarantine_status") != "historical_unverified_nonrelease" or entry.get("prose_write_allowed") is not False or entry.get("formal_release_allowed") is not False:
            errors.append(f"历史隔离状态不满足不可发布要求: {consumption_id}")
        archive_hash_matches = entry.get("archive_record_sha256") == _canonical_hash(archive_row)
        drift_is_quarantined = (
            entry.get("archive_integrity_status") == "historical_archive_drift_nonrelease"
            and entry.get("observed_archive_record_sha256") == _canonical_hash(archive_row)
        )
        if not archive_hash_matches and not drift_is_quarantined:
            errors.append(f"历史隔离记录哈希不一致: {consumption_id}")
        if isinstance(consumption, dict):
            errors.append(f"历史隔离记录重新进入当前消费证据: {consumption_id}")
        if consumption_id in active_ids:
            errors.append(f"历史隔离记录进入当前生产面: {consumption_id}")
    return errors


def audit(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    bindings_doc = _read(evidence / "全量资料解释词创作绑定.json", {})
    bindings = [row for row in bindings_doc.get("records", []) if isinstance(row, dict)] if isinstance(bindings_doc, dict) else []
    binding_by_id = {row.get("binding_id"): row for row in bindings if row.get("binding_id")}
    grants = authorized_bindings(root, bindings)
    plan = _read(evidence / "全量资料正文生产编排.json", {})
    planned = [row for row in plan.get("records", []) if isinstance(row, dict)] if isinstance(plan, dict) else []
    queue = _jsonl(evidence / "全量资料正文生产队列.jsonl")
    batches = _jsonl(evidence / "全量资料正文生产批次.jsonl")
    consumed_doc = _read(evidence / "全量资料正文消费证据.json", {})
    consumed = [row for row in consumed_doc.get("records", []) if isinstance(row, dict)] if isinstance(consumed_doc, dict) else []
    archive = _jsonl(evidence / "全量资料升级档案.jsonl")
    validation = _read(evidence / "全量资料正文消费验证报告.json", {})
    issues: list[dict[str, Any]] = []

    for binding in bindings:
        binding_id = binding.get("binding_id")
        has_grant = binding_id in grants
        permissions = binding.get("model_input_eligible") is True and binding.get("prose_write_allowed") is True
        if permissions != has_grant:
            issues.append(_issue("binding", binding, "绑定权限字段与独立审计授权清单不一致"))

    plan_ids = {row.get("consumption_id") for row in planned}
    for row in planned:
        binding = binding_by_id.get(row.get("binding_id"))
        if row.get("binding_id") not in grants:
            issues.append(_issue("production_plan", row, "生产计划引用了未审计授权的绑定"))
        if not isinstance(binding, dict) or binding.get("model_input_eligible") is not True or binding.get("prose_write_allowed") is not True:
            issues.append(_issue("production_plan", row, "生产计划与绑定权限字段不一致"))
        if row.get("status") != "queued_for_authored_prose":
            issues.append(_issue("production_plan", row, "生产计划记录不具有 queued_for_authored_prose 状态"))

    queue_ids = {row.get("consumption_id") for row in queue}
    inactive_quality_plan = (
        isinstance(plan, dict)
        and plan.get("schema_version") == "scene-to-release-quality-plan-1.0"
        and plan.get("prose_write_allowed") is not True
    )
    if not inactive_quality_plan and queue_ids != plan_ids:
        issues.append({"scope": "production_queue", "message": "正文生产队列不是生产计划记录的精确投影", "missing_from_queue": sorted(plan_ids - queue_ids), "unexpected_in_queue": sorted(queue_ids - plan_ids)})
    for row in queue:
        if row.get("binding_id") not in grants:
            issues.append(_issue("production_queue", row, "正文生产队列引用了未审计授权的绑定"))

    batch_members = [consumption_id for row in batches for consumption_id in row.get("consumption_ids", []) if isinstance(consumption_id, str)]
    if not inactive_quality_plan and Counter(batch_members) != Counter(row.get("consumption_id") for row in planned):
        issues.append({"scope": "production_batches", "message": "生产批次不是生产计划记录的精确投影"})

    active_ids = plan_ids | queue_ids | set(batch_members)
    legacy_errors = _legacy_quarantine_errors(evidence, consumed, archive, active_ids)
    for error in legacy_errors:
        issues.append({"scope": "legacy_quarantine", "message": error})
    for row in consumed:
        binding_id = row.get("binding_id")
        binding = binding_by_id.get(binding_id)
        if binding_id not in grants and legacy_errors:
            issues.append(_issue("consumption_evidence", row, "历史正文消费证据没有当前逐条审计授权"))
        if not isinstance(binding, dict) or binding.get("source_id") != row.get("source_id"):
            issues.append(_issue("consumption_evidence", row, "历史正文消费证据无法与当前绑定身份一致回链"))
    for row in archive:
        binding_id = row.get("binding_id")
        if binding_id not in grants and legacy_errors:
            issues.append(_issue("upgrade_archive", row, "历史升级档案没有当前逐条审计授权"))

    quarantined_ids = {row.get("consumption_id") for row in _read(evidence / REGISTRY_FILE, {}).get("entries", []) if isinstance(row, dict) and row.get("quarantine_status") == "historical_unverified_nonrelease"}
    current_consumed = [row for row in consumed if row.get("consumption_id") not in quarantined_ids]
    current_archive = [row for row in archive if row.get("consumption_id") not in quarantined_ids]
    current_ids = {row.get("consumption_id") for row in current_consumed}
    validation_allows_release = (
        isinstance(validation, dict)
        and validation.get("status") == "passed"
        and validation.get("planned_count") == validation.get("prose_realized_count") == len(current_ids)
        and validation.get("queued_or_missing_count") == 0
        and validation.get("status_counts", {}).get("invalid_evidence", 0) == 0
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": "模型输入、生产计划、正文队列和批次均必须逐条回链到已审计授权。历史未授权消费只能以哈希锁定的不可发布隔离记录存在，且不得进入当前生产面；历史隔离不构成正式发布授权。",
        "authorization_file": f"{AUTHORIZATION_DIR}/{AUDITED_FILE}",
        "binding_count": len(bindings),
        "authorized_binding_count": len(grants),
        "planned_count": len(planned),
        "queue_count": len(queue),
        "batch_member_count": len(batch_members),
        "consumption_evidence_count": len(consumed),
        "upgrade_archive_count": len(archive),
        "historical_quarantined_count": len(quarantined_ids),
        "current_consumption_evidence_count": len(current_consumed),
        "current_upgrade_archive_count": len(current_archive),
        "prose_consumption_validation_status": validation.get("status") if isinstance(validation, dict) else "missing",
        "legacy_quarantine_status": "passed" if not legacy_errors else "failed",
        "legacy_quarantine_error_count": len(legacy_errors),
        "future_production_allowed": not any(issue["scope"] in {"binding", "production_plan", "production_queue", "production_batches"} for issue in issues),
        "formal_release_allowed": not issues and validation_allows_release and bool(current_ids),
        "issue_count": len(issues),
        "issues": issues,
        "status": "passed" if not issues else "failed",
    }
    target = evidence / "全量资料严格隔离审计报告.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    detail = evidence / "全量资料严格隔离审计问题清单.jsonl"
    detail.write_text("".join(json.dumps(issue, ensure_ascii=False) + "\n" for issue in issues), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = audit(args.project_root)
    print(json.dumps({key: report[key] for key in ("status", "future_production_allowed", "formal_release_allowed", "issue_count")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())