"""Audit independently supplied replacement objects for later model-input review.

Passing this audit validates only the submitted replacement object's binding and
review metadata. It never grants formal-fact, model-input, or prose permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "strict-quarantine-replacement-source-reaudit-1.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = (
    "replacement_draft_id", "replacement_source_id", "exact_locator", "source_object_id",
    "source_object", "source_object_sha256", "source_rights_or_approval", "scope",
    "reviewed_by", "reviewed_at", "review_rationale",
)


def _canonical_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if line.strip():
            try:
                value = json.loads(line)
                rows.append(value if isinstance(value, dict) else {"_line": line_number, "_parse_error": "提交行必须为对象"})
            except json.JSONDecodeError as exc:
                rows.append({"_line": line_number, "_parse_error": str(exc)})
    return rows


def _template(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "replacement_draft_id": draft["replacement_draft_id"],
        "replacement_source_id": None,
        "exact_locator": None,
        "source_object_id": None,
        "source_object": None,
        "source_object_sha256": None,
        "source_rights_or_approval": None,
        "scope": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "review_rationale": None,
        "submission_status": "pending_independent_replacement_source",
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
    }


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据" / "严格资料升级"
    drafts_path = evidence / "严格隔离替代来源方案" / "替代来源草案清单.jsonl"
    drafts = _read_jsonl(drafts_path)
    candidates = [draft for draft in drafts if draft.get("draft_kind") == "bounded_content_candidate"]
    output = evidence / "严格隔离替代来源重审"
    staging = evidence / ".严格隔离替代来源重审_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    report = {
        "schema_version": SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "submission_template_only; no_source_or_eligibility_promotion",
        "candidate_draft_count": len(candidates), "mandatory_external_replacement_count": len(drafts) - len(candidates),
        "formal_fact_eligible_count": 0, "model_input_eligible_count": 0, "prose_write_allowed": False,
    }
    (staging / "严格隔离替代来源重审报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "待替代来源重审提交模板.jsonl").write_text("".join(json.dumps(_template(draft), ensure_ascii=False) + "\n" for draft in candidates), encoding="utf-8")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def _audit_row(row: dict[str, Any], baseline: dict[str, dict[str, Any]], seen: set[str]) -> list[str]:
    if "_parse_error" in row:
        return [f"提交 JSON 无效: {row['_parse_error']}"]
    errors = []
    draft_id = row.get("replacement_draft_id")
    if not isinstance(draft_id, str) or draft_id not in baseline:
        return ["replacement_draft_id 不存在、为空或不属于有界内容草案"]
    if draft_id in seen:
        errors.append("replacement_draft_id 重复提交")
    seen.add(draft_id)
    for field in REQUIRED:
        value = row.get(field)
        if field == "source_object":
            if not isinstance(value, (dict, list)):
                errors.append("source_object 必须是独立提交的 JSON 对象或数组")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"缺少 {field}")
    declared_hash = row.get("source_object_sha256")
    if isinstance(declared_hash, str) and not SHA256_RE.fullmatch(declared_hash):
        errors.append("source_object_sha256 必须是小写 SHA-256")
    if isinstance(row.get("source_object"), (dict, list)):
        actual_hash = _canonical_hash(row["source_object"])
        if declared_hash != actual_hash:
            errors.append("source_object_sha256 与提交对象的规范化 SHA-256 不一致")
        if actual_hash != baseline[draft_id]["content_object_sha256"]:
            errors.append("提交对象哈希与对应草案的有界内容对象不一致")
    if isinstance(row.get("reviewed_at"), str):
        try:
            datetime.fromisoformat(row["reviewed_at"].replace("Z", "+00:00"))
        except ValueError:
            errors.append("reviewed_at 必须是 ISO 8601 时间")
    return errors


def audit(root: str | Path, submission_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据" / "严格资料升级"
    queue_dir = evidence / "严格隔离替代来源重审"
    drafts = _read_jsonl(evidence / "严格隔离替代来源方案" / "替代来源草案清单.jsonl")
    baseline = {draft["replacement_draft_id"]: draft for draft in drafts if draft.get("draft_kind") == "bounded_content_candidate"}
    submission = Path(submission_path).expanduser().resolve() if submission_path else root / "配置" / "严格隔离替代来源提交.jsonl"
    rows = _read_jsonl(submission)
    seen: set[str] = set()
    results = []
    eligible = []
    for row in rows:
        errors = _audit_row(row, baseline, seen)
        accepted = not errors
        result = {"replacement_draft_id": row.get("replacement_draft_id"), "replacement_source_id": row.get("replacement_source_id"), "accepted_for_later_model_input_review": accepted, "errors": errors, "formal_fact_eligible": False, "model_input_eligible": False, "prose_write_allowed": False}
        results.append(result)
        if accepted:
            draft = baseline[row["replacement_draft_id"]]
            eligible.append({
                "schema_version": SCHEMA_VERSION, "replacement_draft_id": row["replacement_draft_id"],
                "replacement_source_id": row["replacement_source_id"], "exact_locator": row["exact_locator"],
                "source_object_id": row["source_object_id"], "source_object_sha256": row["source_object_sha256"],
                "scope": row["scope"], "reviewed_by": row["reviewed_by"], "reviewed_at": row["reviewed_at"],
                "upgrade_id": draft["upgrade_id"], "consumption_id": draft["consumption_id"],
                "formal_fact_eligible": False, "model_input_eligible": False, "prose_write_allowed": False,
            })
    report = {
        "schema_version": SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "strict_reaudit_of_independently_submitted_bounded_replacement_objects; acceptance_requires_separate_authorization_before_any_use",
        "submitted_record_count": len(rows), "accepted_for_later_model_input_review_count": len(eligible),
        "rejected_record_count": len(results) - len(eligible), "unsubmitted_candidate_count": len(set(baseline) - seen),
        "mandatory_external_replacement_count": len(drafts) - len(baseline),
        "formal_fact_eligible_count": 0, "model_input_eligible_count": 0, "prose_write_allowed": False,
        "source_status_modified": False, "project_confirmation_modified": False,
    }
    staging = queue_dir / ".严格隔离替代来源重审审计_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "严格隔离替代来源重审审计报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "严格隔离替代来源重审审计清单.jsonl").write_text("".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results), encoding="utf-8")
    (staging / "模型输入资格清单.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in eligible), encoding="utf-8")
    for name in ("严格隔离替代来源重审审计报告.json", "严格隔离替代来源重审审计清单.jsonl", "模型输入资格清单.jsonl"):
        target = queue_dir / name
        target.unlink(missing_ok=True)
        (staging / name).replace(target)
    staging.rmdir()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--submission-path")
    args = parser.parse_args()
    print(json.dumps(audit(args.project_root, args.submission_path) if args.audit else build(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())