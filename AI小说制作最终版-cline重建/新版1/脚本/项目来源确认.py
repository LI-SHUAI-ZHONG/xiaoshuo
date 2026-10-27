"""Validate explicit human confirmation for derived project input.

The project configuration may be executable while still being derived. This
gate keeps that distinction machine-readable and refuses formal delivery until
the project owner has acknowledged the derived fields and remaining gaps.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def validate_confirmation(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    config_path = root / "配置" / "project_config.json"
    gap_path = root / "文档" / "证据" / "项目输入缺失清单.json"
    confirmation_path = root / "配置" / "project_source_confirmation.json"
    config = read_json(config_path, {})
    gaps = read_json(gap_path, {})
    confirmation = read_json(confirmation_path, None)
    project_id = config.get("project_id") or config.get("project_name")
    required_fields = ["project_id", "genre_selection", "book_title", "world_stage", "mainline_conflict", "core_mystery", "protagonist", "chapter_plan"]
    still_missing = [item.get("field") for item in gaps.get("still_missing_not_derivable", []) if item.get("field")]
    derived_candidates = [item.get("field") for item in gaps.get("derived_candidate_confirmation", []) if item.get("field")]
    errors: list[str] = []
    status = "pending"
    if not project_id:
        errors.append("项目配置缺少 project_id/project_name")
    if confirmation is None:
        errors.append("缺少配置/project_source_confirmation.json；派生项目输入尚未获得项目所有者确认")
    elif not isinstance(confirmation, dict):
        errors.append("来源确认文件必须是 JSON 对象")
    else:
        if confirmation.get("schema_version") != "project-source-confirmation-1.0":
            errors.append("来源确认文件 schema_version 不匹配")
        if confirmation.get("project_id") != project_id:
            errors.append("来源确认文件 project_id 与项目配置不一致")
        if confirmation.get("status") != "confirmed":
            errors.append("来源确认状态不是 confirmed")
        if not str(confirmation.get("confirmed_by", "")).strip():
            errors.append("来源确认缺少 confirmed_by")
        if not str(confirmation.get("confirmed_at", "")).strip():
            errors.append("来源确认缺少 confirmed_at")
        if confirmation.get("source_quality_ack") is not True:
            errors.append("来源确认必须明确 source_quality_ack=true")
        accepted = {str(field) for field in confirmation.get("accepted_fields", [])}
        missing_acceptance = [field for field in required_fields if field not in accepted]
        if missing_acceptance:
            errors.append("来源确认未覆盖字段：" + ", ".join(missing_acceptance))
        if confirmation.get("unresolved_fields"):
            errors.append("仍存在未解决项目字段：" + ", ".join(map(str, confirmation["unresolved_fields"])))
        status = "confirmed" if not errors else "rejected"
    accepted = {str(field) for field in (confirmation or {}).get("accepted_fields", [])} if isinstance(confirmation, dict) else set()
    explicit_unresolved = [str(field) for field in (confirmation or {}).get("unresolved_fields", [])] if isinstance(confirmation, dict) else []
    unresolved = sorted(set(
        [field for field in derived_candidates if field not in accepted]
        + [field for field in still_missing if field not in accepted]
        + explicit_unresolved
    ))
    report = {
        "schema_version": "project-source-confirmation-report-1.0",
        "generated_at": now(),
        "project_id": project_id,
        "confirmation_path": str(confirmation_path),
        "status": status,
        "required_fields": required_fields,
        "derived_or_unresolved_fields": sorted(set(unresolved)),
        "errors": errors,
        "allow_formal_pipeline": status == "confirmed" and not unresolved,
        "delivery_status": "project_delivery_candidate" if status == "confirmed" and not unresolved else "draft_only",
    }
    evidence = root / "文档" / "证据"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "项目来源确认报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = validate_confirmation(args.project_root)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["allow_formal_pipeline"] else 1


if __name__ == "__main__":
    raise SystemExit(main())