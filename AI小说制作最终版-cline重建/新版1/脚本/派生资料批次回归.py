"""Verify a completed derived-material upgrade batch without consuming prose."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_ID = "20260816T061711Z-fb0cf077"
TERMINAL_STATUSES = {"validated_candidate", "validated_no_change", "quarantined"}


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        return [], [f"无法读取升级记录：{error}"]
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"升级记录第 {number} 行不是 JSON")
            continue
        if not isinstance(row, dict):
            errors.append(f"升级记录第 {number} 行不是对象")
        else:
            rows.append(row)
    return rows, errors


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _object_hash(row: dict[str, Any]) -> str:
    """Accept object-hash locations emitted by full and mapped upgrade deltas."""
    direct = str(row.get("original_object_sha256") or "")
    if direct:
        return direct
    derived = str(row.get("derived_original_object_sha256") or "")
    if derived:
        return derived
    original = row.get("original_object")
    if isinstance(original, dict):
        nested = str(original.get("derived_original_object_sha256") or "")
        if nested:
            return nested
    source_ref = row.get("source_ref")
    if isinstance(source_ref, dict):
        mapping = source_ref.get("derived_mapping")
        if isinstance(mapping, dict):
            return str(mapping.get("derived_original_object_sha256") or "")
    return ""


def _has_valid_quarantine_provenance(row: dict[str, Any]) -> bool:
    """An unresolved original object is valid only when explicitly quarantined."""
    return (
        str(row.get("terminal_status") or row.get("status") or "") == "quarantined"
        and row.get("original_object") is None
        and isinstance(row.get("errors"), list)
        and any(str(error).strip() for error in row["errors"])
    )


def _run_chain(root: Path, run_id: str) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    runs = root / "文档" / "证据" / "全量资料升级运行"
    chain: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    current_run_id, seen = run_id, set()
    while current_run_id and current_run_id not in seen:
        seen.add(current_run_id)
        run_dir = runs / current_run_id
        manifest = _read_json(run_dir / "manifest.json", {})
        if not isinstance(manifest, dict) or manifest.get("run_id") != current_run_id:
            errors.append(f"升级运行链缺失、断裂或 manifest 的 run_id 不匹配：{current_run_id}")
            return [], errors
        chain.append((run_dir, manifest))
        if manifest.get("records_mode") == "snapshot":
            current_run_id = ""
            break
        current_run_id = str(manifest.get("parent_run_id") or "")
    if current_run_id:
        errors.append("升级运行链存在循环")
    return list(reversed(chain)), errors


def run(project_root: str | Path, run_id: str | None = None) -> dict[str, Any]:
    """Run material-only regression checks; never read scene or prose artifacts."""
    root = Path(project_root).expanduser().resolve()
    run_id = run_id or RUN_ID
    chain, errors = _run_chain(root, run_id)
    manifest = chain[-1][1] if chain else {}
    if not isinstance(manifest, dict):
        errors.append("升级 manifest 无效")
        manifest = {}
    if manifest.get("run_id") != run_id:
        errors.append("升级 manifest 的 run_id 不匹配")
    if manifest.get("contract_status") != "passed" or manifest.get("audit_state") != "completed":
        errors.append("升级运行未完成合同与审计门")
    if manifest.get("complete_full_run") is not True:
        errors.append("升级运行不是完整全量批次")
    if manifest.get("prose_write_allowed") is not False or manifest.get("formal_release_allowed") is not False:
        errors.append("升级批次权限越界：必须禁止正文写入和正式发布")

    by_binding: dict[str, dict[str, Any]] = {}
    statuses: Counter[str] = Counter()
    missing_hashes = 0
    for run_dir, _ in chain:
        rows, row_errors = _records(run_dir / "records.jsonl")
        errors.extend(row_errors)
        for row in rows:
            binding_id = str(row.get("binding_id") or "")
            if not binding_id:
                errors.append("升级记录存在缺少 binding_id 的条目")
                continue
            by_binding[binding_id] = row
    for binding_id, row in by_binding.items():
        status = str(row.get("terminal_status") or row.get("status") or "")
        if status not in TERMINAL_STATUSES:
            errors.append(f"{binding_id}: 非法或缺失终态：{status or '空'}")
        else:
            statuses[status] += 1
        if len(_object_hash(row)) != 64 and not _has_valid_quarantine_provenance(row):
            missing_hashes += 1

    expected_count = manifest.get("baseline_binding_count")
    if not isinstance(expected_count, int) or expected_count < 1:
        errors.append("升级 manifest 缺少有效 baseline_binding_count")
    elif len(by_binding) != expected_count:
        errors.append(f"全量覆盖不守恒：预期 {expected_count}，实际 {len(by_binding)}")
    if missing_hashes:
        errors.append(f"{missing_hashes} 条升级记录缺少 64 位原始对象哈希")

    execution_statuses = manifest.get("status_counts")
    if not isinstance(execution_statuses, dict):
        errors.append("升级 manifest 缺少 status_counts")
    elif manifest.get("records_mode") == "snapshot" and dict(statuses) != execution_statuses:
        errors.append("升级 snapshot manifest 的终态统计与 records 不一致")
    elif manifest.get("records_mode") == "snapshot" and sum(value for value in execution_statuses.values() if isinstance(value, int)) != expected_count:
        errors.append("升级 snapshot manifest 的终态统计不守恒")

    task = _read_json(root / "文档" / "证据" / "派生资料项目任务声明.json", {})
    task_status = "not_present"
    if isinstance(task, dict) and task:
        task_status = "present"
        if task.get("scope") != "project_design_adoption_only":
            errors.append("项目任务声明越出项目设计范围")
        for request in task.get("requests", []):
            if not isinstance(request, dict) or str(request.get("binding_id") or "") not in by_binding:
                errors.append("项目任务声明引用了升级批次之外的 binding_id")

    return {
        "schema_version": "derived-material-batch-regression-1.0",
        "run_id": run_id,
        "checked_at": _now(),
        "scope": "material_batch_only_no_scene_or_prose_read",
        "quality_status": "passed" if not errors else "blocked",
        "formal_release_allowed": False,
        "downstream_status": "project_design_only; scene_and_prose_consumption_not_authorized",
        "counts": {"baseline": expected_count, "records": len(by_binding), "chain_terminal_statuses": dict(statuses),
                   "chain_quarantined": statuses["quarantined"], "declared_status_counts": execution_statuses},
        "project_task_declaration": task_status,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    args = parser.parse_args()
    report = run(args.project_root, args.run_id)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["quality_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())