"""Record project-level adoption of validated derived material.

This module deliberately stops at a design adoption decision. It never reads
chapter briefs, creates scene bindings, writes prose, or emits consumption
evidence. Scene translation and prose verification are separate downstream
stages governed by their own explicit inputs and gates.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_ID = "20260816T061711Z-fb0cf077"
TERMINAL_STATUSES = {"validated_candidate", "validated_no_change"}
TYPE_MATERIAL = {"类型系统", "类型系统来源块", "类型连接"}
GENERIC_DECISIONS = {"采用", "使用", "参考", "待定", "匹配", "相关", "有效"}
TASK_FILE = "派生资料项目任务声明.json"
DECISION_FILE = "项目采用决策.json"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    result: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                result.append(row)
    return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _run_chain(root: Path) -> list[Path]:
    runs = root / "文档" / "证据" / "全量资料升级运行"
    chain: list[Path] = []
    run_id, seen = RUN_ID, set()
    while run_id and run_id not in seen:
        seen.add(run_id)
        run_dir = runs / run_id
        manifest = _read(run_dir / "manifest.json", {})
        if not isinstance(manifest, dict) or str(manifest.get("run_id") or "") != run_id:
            return []
        chain.append(run_dir)
        run_id = str(manifest.get("parent_run_id") or "")
    return chain


def _upgrade_states(root: Path) -> tuple[dict[str, dict[str, Any]], set[str], list[str]]:
    """Return latest terminal state and explicit quarantine from the run chain."""
    chain = _run_chain(root)
    if not chain:
        return {}, set(), ["升级运行链缺失、断裂或 manifest 的 run_id 不匹配"]
    states: dict[str, dict[str, Any]] = {}
    quarantined: set[str] = set()
    for run_dir in reversed(chain):
        for row in _rows(run_dir / "records.jsonl"):
            binding_id = str(row.get("binding_id") or "")
            status = str(row.get("terminal_status") or row.get("status") or "")
            if not binding_id or not status:
                continue
            states[binding_id] = {"status": status, "run_id": run_dir.name, "original_object_sha256": str(row.get("original_object_sha256") or "")}
            if status == "quarantined":
                quarantined.add(binding_id)
    return states, quarantined, []


def _project_id(root: Path) -> str:
    config = _read(root / "配置" / "project_config.json", {})
    return str(config.get("project_id") or "") if isinstance(config, dict) else ""


def _non_generic_decision(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) >= 16 and text not in GENERIC_DECISIONS


def _preflight(root: Path) -> dict[str, Any]:
    evidence = root / "文档" / "证据"
    task = _read(evidence / TASK_FILE, {})
    bindings_doc = _read(evidence / "全量资料解释词创作绑定.json", {})
    states, quarantined, errors = _upgrade_states(root)
    project_id = _project_id(root)
    if not project_id:
        errors.append("project_config.json 缺少 project_id")
    if not isinstance(task, dict):
        errors.append(f"{TASK_FILE} 必须是 JSON 对象")
        task = {}
    if task.get("project_id") != project_id:
        errors.append("任务声明 project_id 与项目配置不一致")
    requests = task.get("requests")
    if not isinstance(requests, list) or not requests:
        errors.append("任务声明 requests 必须是非空数组")
        requests = []
    records = bindings_doc.get("records") if isinstance(bindings_doc, dict) else None
    if not isinstance(records, list):
        errors.append("全量资料解释词创作绑定.json 缺少 records 数组")
        records = []
    bindings = {str(row.get("binding_id") or ""): row for row in records if isinstance(row, dict)}
    approved: list[dict[str, Any]] = []
    seen: set[str] = set()
    type_confirmed = task.get("project_type_confirmation") is True
    for index, request in enumerate(requests):
        prefix = f"requests[{index}]"
        if not isinstance(request, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        binding_id = str(request.get("binding_id") or "")
        decision = request.get("decision_statement")
        if not binding_id or binding_id in seen:
            errors.append(f"{prefix} binding_id 缺失或重复")
            continue
        seen.add(binding_id)
        binding, state = bindings.get(binding_id), states.get(binding_id)
        if not binding:
            errors.append(f"{binding_id}: 不在冻结绑定基线中")
            continue
        if not _non_generic_decision(decision):
            errors.append(f"{binding_id}: decision_statement 必须是具体项目设计决策")
            continue
        if binding_id in quarantined or not state or state["status"] not in TERMINAL_STATUSES:
            errors.append(f"{binding_id}: 未通过可采用的升级终态或已隔离")
            continue
        binding_hash = str(binding.get("original_object_sha256") or "")
        state_hash = state["original_object_sha256"]
        if not state_hash:
            errors.append(f"{binding_id}: 升级记录缺少锁定的原始对象哈希")
            continue
        if binding_hash and binding_hash != state_hash:
            errors.append(f"{binding_id}: 冻结绑定与升级记录的原始对象哈希不一致")
            continue
        source_kind = str(binding.get("source_kind") or "")
        if source_kind in TYPE_MATERIAL and not type_confirmed:
            errors.append(f"{binding_id}: 类型材料需要显式 project_type_confirmation")
            continue
        approved.append({"binding_id": binding_id, "source_id": binding.get("source_id"), "source_kind": source_kind,
                         "source_ref": binding.get("source_ref"), "original_object_sha256": state_hash,
                         "upgrade_terminal_status": state["status"], "upgrade_run_id": state["run_id"],
                         "decision_statement": str(decision).strip()})
    return {"schema_version": "derived-material-project-adoption-preflight-2.0", "run_id": RUN_ID,
            "project_id": project_id, "scope": "project_design_adoption_only", "formal_release_allowed": False,
            "approved": approved, "errors": errors, "status": "passed" if not errors else "blocked"}


def _build_decision(preflight: dict[str, Any]) -> dict[str, Any]:
    records = []
    for item in preflight["approved"]:
        records.append({"adoption_id": f"ADOPT-{RUN_ID}-{item['binding_id']}", "run_id": RUN_ID,
                        "project_id": preflight["project_id"], **item, "adoption_status": "adopted_for_project_design_only",
                        "downstream_status": "not_scene_bound_not_consumed_not_narrativized", "adopted_at": _now()})
    return {"schema_version": "derived-material-project-adoption-2.0", "run_id": RUN_ID,
            "project_id": preflight["project_id"], "scope": "project_design_adoption_only",
            "policy": "本记录不构成场景绑定、正文消费、事实确认或正式发布授权。", "status": "passed",
            "formal_release_allowed": False, "records": records}


def _validate_staging(preflight: dict[str, Any], staged: str) -> list[str]:
    document = _read(Path(staged), {})
    if not isinstance(document, dict) or document.get("status") != "passed":
        return ["暂存采用决策无效"]
    expected = {item["binding_id"]: item for item in preflight["approved"]}
    actual = document.get("records")
    if not isinstance(actual, list) or len(actual) != len(expected):
        return ["暂存采用记录数量不一致"]
    errors = []
    for row in actual:
        if not isinstance(row, dict) or row.get("binding_id") not in expected:
            errors.append("暂存采用记录包含未预检条目")
            continue
        item = expected[row["binding_id"]]
        for key in ("original_object_sha256", "upgrade_terminal_status", "decision_statement"):
            if row.get(key) != item[key]:
                errors.append(f"{row['binding_id']}: 暂存记录 {key} 被篡改")
    return errors


def run(project_root: str | Path, apply: bool = False) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    preflight = _preflight(root)
    if not apply or preflight["status"] != "passed":
        return {"run_id": RUN_ID, "mode": "dry_run", "quality_status": preflight["status"], "formal_release_allowed": False, "errors": preflight["errors"]}
    target = root / "文档" / "证据" / "派生资料项目采用" / RUN_ID / DECISION_FILE
    if target.exists():
        return {"run_id": RUN_ID, "mode": "apply_rejected", "quality_status": "blocked", "formal_release_allowed": False, "errors": ["该 run_id 的项目采用决策已存在，禁止覆盖"]}
    staging = target.parent / ".staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    staged = staging / DECISION_FILE
    _atomic_write(staged, json.dumps(_build_decision(preflight), ensure_ascii=False, indent=2) + "\n")
    errors = _validate_staging(preflight, str(staged))
    if errors:
        shutil.rmtree(staging, ignore_errors=True)
        return {"run_id": RUN_ID, "mode": "apply_rejected", "quality_status": "blocked", "formal_release_allowed": False, "errors": errors}
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, target)
    staging.rmdir()
    return {"run_id": RUN_ID, "mode": "apply", "quality_status": "passed", "formal_release_allowed": False, "errors": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--apply", action="store_true", help="Append a project-design adoption decision after validation.")
    parser.add_argument("--dry-run", action="store_true", help="Explicit read-only preflight (the default).")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run cannot be used together")
    report = run(args.project_root, apply=args.apply)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["quality_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())