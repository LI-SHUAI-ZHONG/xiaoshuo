"""Prepare and audit per-binding permission for model input and authored prose.

This is the only producer of use-permission evidence. Qualification, project
confirmation, and replacement-source review remain separate prerequisite
evidence and do not grant either permission by themselves.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "full-source-model-input-prose-authorization-1.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
AUTHORIZATION_DIR = "全量资料输入与正文授权"
AUDITED_FILE = "已审计授权清单.jsonl"


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            rows.append({"_line": number, "_parse_error": str(exc)})
            continue
        rows.append(value if isinstance(value, dict) else {"_line": number, "_parse_error": "JSONL 行必须为对象"})
    return rows


def _baseline(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row["binding_id"]): {
            "binding_id": str(row["binding_id"]),
            "source_id": str(row.get("source_id") or ""),
            "source_ref_sha256": _sha256_text(row.get("source_ref")),
        }
        for row in records
        if isinstance(row, dict) and row.get("binding_id") and row.get("source_id")
    }


def _template(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        **row,
        "model_input_eligible": False,
        "prose_write_allowed": False,
        "authorization_scope": None,
        "authorized_by": None,
        "authorized_at": None,
        "authorization_rationale": None,
        "authorization_status": "pending_explicit_use_authorization",
    }


def initialize_submission_template(root: str | Path) -> dict[str, Any]:
    """Create the empty submission template without touching audited grants."""
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    bindings = _read_json(evidence / "全量资料解释词创作绑定.json", {})
    baseline = _baseline(bindings.get("records", []) if isinstance(bindings, dict) else [])
    output = evidence / AUTHORIZATION_DIR
    staging = evidence / f".{AUTHORIZATION_DIR}_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "submission_template_only; no_permission_granted",
        "binding_count": len(baseline),
        "authorized_binding_count": 0,
        "model_input_eligible_count": 0,
        "prose_write_allowed_count": 0,
    }
    (staging / "待授权提交模板.jsonl").write_text(
        "".join(json.dumps(_template(row), ensure_ascii=False) + "\n" for row in baseline.values()), encoding="utf-8"
    )
    (staging / "授权字段说明.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "required_for_any_true_permission": ["authorization_scope", "authorized_by", "authorized_at", "authorization_rationale"],
        "immutable_binding": ["binding_id", "source_id", "source_ref_sha256"],
        "prohibitions": [
            "来源资格、项目确认或替代来源重审通过不自动授予模型输入或正文写作权限。",
            "未由本审计器输出的授权布尔值不得进入模型输入或正文生产。",
            "两项权限必须同时为 true 才能进入正文生产队列。",
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "授权模板报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Initialization is destructive only to the template directory and must
    # never silently replace an existing audited authorization result.
    if output.exists():
        raise FileExistsError(f"授权目录已存在，拒绝覆盖：{output}")
    staging.replace(output)
    return report


def _row_errors(row: dict[str, Any], baseline: dict[str, dict[str, Any]], seen: set[str]) -> list[str]:
    errors = [str(row["_parse_error"])] if "_parse_error" in row else []
    binding_id = row.get("binding_id")
    if not isinstance(binding_id, str) or binding_id not in baseline:
        return errors + ["binding_id 不在当前绑定基线中"]
    if binding_id in seen:
        errors.append("binding_id 重复提交")
    seen.add(binding_id)
    expected = baseline[binding_id]
    if row.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version 不匹配")
    for field in ("source_id", "source_ref_sha256"):
        if row.get(field) != expected[field]:
            errors.append(f"不可变绑定不匹配: {field}")
    for field in ("model_input_eligible", "prose_write_allowed"):
        if not isinstance(row.get(field), bool):
            errors.append(f"{field} 必须为布尔值")
    requested = row.get("model_input_eligible") is True or row.get("prose_write_allowed") is True
    if requested and not (row.get("model_input_eligible") is True and row.get("prose_write_allowed") is True):
        errors.append("模型输入与正文写作权限必须同时明确授权")
    if requested:
        for field in ("authorization_scope", "authorized_by", "authorized_at", "authorization_rationale"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"授权记录缺少 {field}")
        if isinstance(row.get("authorized_at"), str):
            try:
                datetime.fromisoformat(row["authorized_at"].replace("Z", "+00:00"))
            except ValueError:
                errors.append("authorized_at 必须是 ISO 8601 时间")
    return errors


def audit(root: str | Path, submission_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    bindings = _read_json(evidence / "全量资料解释词创作绑定.json", {})
    baseline = _baseline(bindings.get("records", []) if isinstance(bindings, dict) else [])
    if not baseline:
        raise ValueError("当前绑定基线缺失或为空")
    output = evidence / AUTHORIZATION_DIR
    submission = Path(submission_path).expanduser().resolve() if submission_path else root / "配置" / "全量资料输入与正文授权.jsonl"
    seen: set[str] = set()
    results, authorized = [], []
    for row in _read_jsonl(submission):
        errors = _row_errors(row, baseline, seen)
        allowed = not errors and row.get("model_input_eligible") is True and row.get("prose_write_allowed") is True
        result = {"binding_id": row.get("binding_id"), "source_id": row.get("source_id"), "accepted_for_use": allowed, "errors": errors}
        results.append(result)
        if allowed:
            authorized.append({key: row[key] for key in (
                "schema_version", "binding_id", "source_id", "source_ref_sha256", "model_input_eligible", "prose_write_allowed",
                "authorization_scope", "authorized_by", "authorized_at", "authorization_rationale",
            )})
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "per_binding_explicit_use_authorization_audit",
        "baseline_binding_count": len(baseline),
        "submitted_record_count": len(results),
        "authorized_binding_count": len(authorized),
        "rejected_record_count": len(results) - len(authorized),
        "unsubmitted_binding_count": len(set(baseline) - seen),
        "model_input_eligible_count": len(authorized),
        "prose_write_allowed_count": len(authorized),
    }
    output.mkdir(parents=True, exist_ok=True)
    staging = output / ".授权审计_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    (staging / "授权审计报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "授权审计清单.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8")
    (staging / AUDITED_FILE).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in authorized), encoding="utf-8")
    for name in ("授权审计报告.json", "授权审计清单.jsonl", AUDITED_FILE):
        target = output / name
        target.unlink(missing_ok=True)
        (staging / name).replace(target)
    staging.rmdir()
    return report


def authorized_bindings(root: str | Path, records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    root = Path(root).expanduser().resolve()
    baseline = _baseline(records)
    authorized: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for row in _read_jsonl(root / "文档" / "证据" / AUTHORIZATION_DIR / AUDITED_FILE):
        errors = _row_errors(row, baseline, seen)
        if not errors and row.get("model_input_eligible") is True and row.get("prose_write_allowed") is True:
            authorized[row["binding_id"]] = row
    return authorized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--initialize-template", action="store_true")
    parser.add_argument("--submission-path")
    args = parser.parse_args()
    if args.audit and args.initialize_template:
        parser.error("--audit 与 --initialize-template 不能同时使用")
    if args.audit:
        result = audit(args.project_root, args.submission_path)
    elif args.initialize_template:
        result = initialize_submission_template(args.project_root)
    else:
        parser.error("必须显式指定 --audit 或 --initialize-template")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())