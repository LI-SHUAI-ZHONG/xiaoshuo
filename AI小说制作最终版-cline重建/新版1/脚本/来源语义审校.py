"""Audit model draft provenance before it can enter human literary review."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "full-source-semantic-editorial-review-1.0"
EVIDENCE_FILE = "全量资料正文消费证据.json"
PLAN_FILE = "全量资料正文生产编排.json"
REPORT_FILE = "全量资料来源语义审校报告.json"
REGISTRY_FILE = "全量资料历史消费隔离清单.json"
QUALITY_PASSED = "semantic_editorial_review_passed"
QUALITY_PENDING = "automatic_draft_requires_semantic_editorial_review"
INTERNAL_TERMS = ("source→target", "source", "target", "binding_id", "source_id", "资料ID", "创作合同", "读者能看到", "未确认的类型偏好不得自动写入正文")


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


def _paragraph_at(root: Path, location: str) -> str:
    match = re.fullmatch(r"(.+)#lines\[(\d+)\]", location)
    if not match:
        return ""
    path = root / match.group(1)
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    line = int(match.group(2))
    return lines[line - 1] if 0 < line <= len(lines) else ""


def _errors(root: Path, row: dict[str, Any], assignment: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    paragraph = str(row.get("paragraph") or "").strip()
    if assignment is None:
        errors.append("候选不在当前质量门生产编排内")
    elif assignment.get("binding_id") != row.get("binding_id") or assignment.get("source_id") != row.get("source_id"):
        errors.append("候选与生产编排的 binding_id/source_id 不一致")
    policy = _read(root / "配置" / "文本生成模型.json", {}).get("generation_policy", {})
    minimum = int(policy.get("minimum_paragraph_characters", 100))
    if len(paragraph) < minimum:
        errors.append(f"正文不足模型候选最低 {minimum} 字要求")
    if row.get("paragraph_sha256") != hashlib.sha256(paragraph.encode("utf-8")).hexdigest():
        errors.append("正文段落哈希不一致")
    if _paragraph_at(root, str(row.get("prose_location") or "")) != paragraph:
        errors.append("正文位置与证据段落不一致")
    hits = [term for term in INTERNAL_TERMS if term.lower() in paragraph.lower()]
    if hits:
        errors.append("正文泄漏内部术语或规则：" + ", ".join(hits))
    for field in ("trigger", "action", "observable_result", "cost_or_change"):
        value = str(row.get(field) or "").strip()
        if not value:
            errors.append(f"缺少 {field}")
        elif value not in paragraph:
            errors.append(f"证据字段未在正文中逐字落地：{field}")
    support = str(row.get("semantic_support") or "").strip()
    if len(support) < 8:
        errors.append("缺少可审阅的来源语义支持")
    return errors


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    plan = _read(evidence / PLAN_FILE, {})
    document = _read(evidence / EVIDENCE_FILE, {"records": []})
    assignments = {str(row.get("consumption_id")): row for row in plan.get("records", []) if isinstance(row, dict)}
    findings: list[dict[str, Any]] = []
    passed, reviewed = 0, 0
    historical_ids = _historical_ids(evidence)
    records = document.get("records", []) if isinstance(document, dict) else []
    for row in records:
        if not isinstance(row, dict):
            continue
        reviewed += 1
        consumption_id = str(row.get("consumption_id") or "")
        if consumption_id in historical_ids:
            continue
        errors = _errors(root, row, assignments.get(consumption_id))
        row["quality_status"] = QUALITY_PASSED if not errors else QUALITY_PENDING
        row["semantic_editorial_review"] = {
            "schema_version": SCHEMA_VERSION,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed" if not errors else "blocked",
            "errors": errors,
        }
        if errors:
            findings.append({"consumption_id": consumption_id, "errors": errors})
        else:
            passed += 1
    document["records"] = records
    evidence.joinpath(EVIDENCE_FILE).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": "仅审查 draft_only 候选的来源语义可追溯性与正文落地一致性；通过不等于文学审校通过，不授予正式发布许可。",
        "reviewed_count": reviewed,
        "passed_count": passed,
        "blocked_count": len(findings),
        "findings": findings,
        "formal_release_allowed": False,
        "status": "passed" if reviewed and not findings else "blocked",
    }
    evidence.joinpath(REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = audit(args.project_root)
    print(json.dumps({key: report[key] for key in ("status", "reviewed_count", "passed_count", "blocked_count")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())