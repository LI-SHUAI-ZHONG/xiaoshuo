"""Prepare and apply explicit human literary-review decisions for model drafts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "full-source-literary-review-1.0"
EVIDENCE_FILE = "全量资料正文消费证据.json"
DECISIONS_FILE = "全量资料文学审校裁决.json"
REPORT_FILE = "全量资料文学审校报告.json"
REGISTRY_FILE = "全量资料历史消费隔离清单.json"
QUALITY_PASSED = "semantic_editorial_review_passed"
REVIEW_PASSED = "semantic_editorial_review_passed"
REVIEW_PENDING = "pending_human_literary_review"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _historical_ids(evidence: Path) -> set[str]:
    registry = _read(evidence / REGISTRY_FILE, {})
    return {
        str(row.get("consumption_id"))
        for row in registry.get("entries", [])
        if isinstance(row, dict)
        and row.get("quarantine_status") == "historical_unverified_nonrelease"
        and row.get("consumption_id")
    }


def review(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    document = _read(evidence / EVIDENCE_FILE, {"records": []})
    decisions_document = _read(evidence / DECISIONS_FILE, {"decisions": []})
    decision_rows = decisions_document.get("decisions", []) if isinstance(decisions_document, dict) else []
    decision_rows = [item for item in decision_rows if isinstance(item, dict)]
    decision_ids = [str(item.get("consumption_id") or "") for item in decision_rows]
    duplicate_ids = {item for item in decision_ids if item and decision_ids.count(item) > 1}
    decisions = {str(item.get("consumption_id")): item for item in decision_rows}
    records = document.get("records", []) if isinstance(document, dict) else []
    historical_ids = _historical_ids(evidence)
    expected_ids = {
        str(row.get("consumption_id") or "")
        for row in records
        if isinstance(row, dict) and str(row.get("consumption_id") or "") not in historical_ids
    }
    blocked = []
    if duplicate_ids:
        blocked.append("文学审校裁决包含重复 consumption_id：" + ", ".join(sorted(duplicate_ids)))
    unknown_ids = sorted({item for item in decision_ids if item} - expected_ids)
    if unknown_ids:
        blocked.append("文学审校裁决包含不在当前批次消费证据中的 consumption_id：" + ", ".join(unknown_ids))
    invalid_ids = sorted(
        str(item.get("consumption_id") or "")
        for item in decision_rows
        if item.get("decision") not in {"pending", "approved", "rejected"}
    )
    if invalid_ids:
        blocked.append("文学审校裁决包含无效 decision：" + ", ".join(invalid_ids))
    pending, passed, rejected = [], 0, []
    for row in records:
        if not isinstance(row, dict):
            continue
        consumption_id = str(row.get("consumption_id") or "")
        if consumption_id in historical_ids:
            continue
        decision = {} if consumption_id in duplicate_ids else decisions.get(consumption_id, {})
        approved = (
            row.get("quality_status") == QUALITY_PASSED
            and decision.get("decision") == "approved"
            and str(decision.get("reviewer") or "").strip()
            and str(decision.get("rationale") or "").strip()
            and decision.get("paragraph_sha256") == row.get("paragraph_sha256")
        )
        if approved:
            row["literary_review_status"] = REVIEW_PASSED
            row["literary_review"] = {"schema_version": SCHEMA_VERSION, "reviewed_at": datetime.now(timezone.utc).isoformat(), "reviewer": decision["reviewer"], "rationale": decision["rationale"], "status": "approved"}
            passed += 1
        else:
            row["literary_review_status"] = REVIEW_PENDING
            rejected_decision = (
                decision.get("decision") == "rejected"
                and str(decision.get("reviewer") or "").strip()
                and str(decision.get("rationale") or "").strip()
                and decision.get("paragraph_sha256") == row.get("paragraph_sha256")
            )
            if rejected_decision:
                reason = "人工文学审校退回，须修改正文后以新段落哈希重新审校"
                row["literary_review"] = {"schema_version": SCHEMA_VERSION, "reviewed_at": datetime.now(timezone.utc).isoformat(), "reviewer": decision["reviewer"], "rationale": decision["rationale"], "status": "rejected", "reason": reason}
                rejected.append(consumption_id)
            elif row.get("quality_status") != QUALITY_PASSED:
                reason = "来源语义审校未通过"
            elif decision.get("decision") == "approved" and decision.get("paragraph_sha256") != row.get("paragraph_sha256"):
                reason = "人工文学审校裁决未绑定当前正文段落哈希"
            elif decision.get("decision") == "rejected" and decision.get("paragraph_sha256") != row.get("paragraph_sha256"):
                reason = "人工文学审校退回裁决未绑定当前正文段落哈希"
            else:
                reason = "缺少具名人工文学审校裁决"
            if not rejected_decision:
                row["literary_review"] = {"schema_version": SCHEMA_VERSION, "status": "pending", "reason": reason}
            pending.append(consumption_id)
    document["records"] = records
    evidence.joinpath(EVIDENCE_FILE).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"schema_version": SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(), "policy": "文学审校必须由具名人工裁决，并绑定当前正文段落哈希；重复、未知或无效裁决一律阻断通过。退回裁决保留审计原因但不得进入正文消费完成。脚本不会从模型输出推断或伪造人工通过。通过文学审校也不授予正式发布许可。", "reviewed_count": len(records), "passed_count": passed, "rejected_consumption_ids": rejected, "pending_consumption_ids": pending, "blocked_count": len(blocked), "blockers": blocked, "formal_release_allowed": False, "status": "passed" if records and not pending and not blocked else "in_progress"}
    evidence.joinpath(REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = review(args.project_root)
    print(json.dumps({key: report[key] for key in ("status", "reviewed_count", "passed_count")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())