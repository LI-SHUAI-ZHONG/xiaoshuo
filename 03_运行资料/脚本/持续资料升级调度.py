"""Build an exhaustive, non-admitting work ledger for strict-source upgrades.

The ledger coordinates existing review queues.  It does not alter source records,
accept evidence, or turn a routed candidate into a project fact.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "continuous-source-upgrade-ledger-1.0"
PROJECT_CONFIRMATION_CATEGORIES = {
    "candidate_requires_project_confirmation",
    "pending_requires_project_confirmation",
}
BOUNDED_REPLACEMENT_CATEGORY = "candidate_identity_missing"
REPLACEMENT_ONLY_CATEGORIES = {
    "locator_invalid_or_out_of_range",
    "object_boundary_missing",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"找不到必需的升级输入: {path}")
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"升级输入第 {number} 行无法解析: {path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"升级输入第 {number} 行必须为对象: {path}")
        records.append(value)
    return records


def _action(record: dict[str, Any]) -> tuple[str, str, str]:
    category = record.get("category_id")
    if category in PROJECT_CONFIRMATION_CATEGORIES:
        return (
            "submit_explicit_project_confirmation",
            "严格隔离项目确认/待项目确认清单.jsonl",
            "项目确认仅作为后续重审证据，不自动授予来源资格或正文写入权限。",
        )
    if category == BOUNDED_REPLACEMENT_CATEGORY:
        return (
            "submit_independent_bounded_replacement_source",
            "严格隔离替代来源重审/待替代来源重审提交模板.jsonl",
            "现有内容指纹只能用于逐对象一致性核验；必须补充独立来源、权利、范围和稳定对象 ID。",
        )
    if category in REPLACEMENT_ONLY_CATEGORIES:
        return (
            "obtain_independent_replacement_source",
            "严格隔离替代来源方案/替代来源草案清单.jsonl",
            "原对象身份或边界不可由现有记录推定，必须取得带单一对象边界和稳定定位的新来源。",
        )
    raise ValueError(f"没有定义升级策略的隔离分类: {category!r}")


def _ledger_row(record: dict[str, Any]) -> dict[str, Any]:
    upgrade_id = record.get("upgrade_id")
    if not isinstance(upgrade_id, str) or not upgrade_id:
        raise ValueError("隔离记录缺少 upgrade_id")
    action, evidence_entry, rationale = _action(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "upgrade_id": upgrade_id,
        "consumption_id": record.get("consumption_id"),
        "binding_id": record.get("binding_id"),
        "source_kind": record.get("source_kind"),
        "source_id": record.get("source_id"),
        "category_id": record.get("category_id"),
        "historical_source_ref": record.get("source_ref"),
        "next_action": action,
        "evidence_entry": evidence_entry,
        "rationale": rationale,
        "completion_condition": "独立提交通过相应审计后，才可进入单独授权的后续重审。",
        "formal_fact_eligible": False,
        "model_input_eligible": False,
        "prose_write_allowed": False,
    }


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    source_dir = root / "文档" / "证据" / "严格资料升级"
    classification_path = source_dir / "严格隔离分类" / "严格隔离分类清单.jsonl"
    archive_path = source_dir / "严格资料升级档案.jsonl"
    classification = _read_jsonl(classification_path)
    archive = _read_jsonl(archive_path)
    archive_ids = {row.get("upgrade_id") for row in archive}
    rows = [_ledger_row(record) for record in classification]
    ids = [row["upgrade_id"] for row in rows]
    duplicate_ids = [key for key, count in Counter(ids).items() if count > 1]
    missing_archive_ids = sorted(set(ids) - archive_ids)
    if duplicate_ids:
        raise ValueError(f"升级调度存在重复 upgrade_id: {duplicate_ids[:3]}")
    if missing_archive_ids:
        raise ValueError(f"升级调度引用的档案记录缺失: {missing_archive_ids[:3]}")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "exhaustive_governance_dispatch_only; no_source_or_eligibility_promotion",
        "input_classification": str(classification_path.relative_to(root)),
        "input_archive": str(archive_path.relative_to(root)),
        "quarantined_record_count": len(classification),
        "ledger_record_count": len(rows),
        "unassigned_record_count": 0,
        "next_action_counts": dict(sorted(Counter(row["next_action"] for row in rows).items())),
        "category_counts": dict(sorted(Counter(str(row["category_id"]) for row in rows).items())),
        "formal_fact_eligible_count": 0,
        "model_input_eligible_count": 0,
        "prose_write_allowed": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
    }
    if report["ledger_record_count"] != report["quarantined_record_count"]:
        raise RuntimeError("持续升级调度覆盖性检查失败")
    output = source_dir / "持续资料升级调度"
    staging = source_dir / ".持续资料升级调度_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "持续资料升级调度报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "持续资料升级清单.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
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