"""Create and verify the immutable, run-scoped execution manifest."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "run-manifest-1.2"

# The full-pipeline profile is deliberately explicit: a manifest is not
# complete merely because it contains some module output.
FULL_PIPELINE_REQUIRED_KINDS = frozenset({
    "input_snapshot",
    "module_output",
    "material_package",
    "consumption_log",
    "prose",
    "structural_quality",
    "literary_review",
    "delivery_report",
})
FULL_PIPELINE_MODULE_IDS = frozenset(f"{number:02d}" for number in range(0, 12))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root)).replace("\\", "/")


def _run_relative_prefix(run_id: str) -> str:
    return f"文档/证据/运行/{run_id}/"


def _embedded_run_ids(path: Path) -> set[str]:
    """Return declared run identifiers from structured run artifacts."""
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            return {str(value.get("run_id")).strip()} if isinstance(value, dict) and str(value.get("run_id") or "").strip() else set()
        if path.suffix.lower() == ".jsonl":
            values = []
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    values.append(json.loads(line))
            return {
                str(value.get("run_id")).strip()
                for value in values
                if isinstance(value, dict) and str(value.get("run_id") or "").strip()
            }
    except (OSError, UnicodeError, json.JSONDecodeError):
        return set()
    return set()


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def manifest_path(project_root: str | Path, run_id: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    return root / "文档" / "证据" / "运行" / run_id / "run_manifest.json"


def _root_id(root: Path) -> str:
    """Use a stable identifier without treating a recovery or archive root as current."""
    return hashlib.sha256(str(root.resolve()).replace("\\", "/").encode("utf-8")).hexdigest()


def _write_manifest(path: Path, manifest: dict[str, Any]) -> Path:
    immutable = {key: value for key, value in manifest.items() if key not in {"updated_at", "manifest_sha256"}}
    manifest["updated_at"] = _now()
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(immutable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def initialize_run(project_root: str | Path, run_id: str, *, input_snapshot_paths: list[str] | None = None) -> Path:
    """Create the run identity before work begins; a prior run cannot be reused."""
    root = Path(project_root).expanduser().resolve()
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id 必须是单个安全目录名")
    path = manifest_path(root, run_id)
    existing = _read(path)
    if existing.get("run_id") not in {None, "", run_id}:
        raise ValueError("运行清单 run_id 不一致")
    snapshot = sorted({str(item).replace("\\", "/") for item in input_snapshot_paths or [] if str(item).strip()})
    snapshot_records = []
    for relative in snapshot:
        target = (root / relative).resolve()
        if target.is_file() and root in target.parents:
            snapshot_records.append({"relative_path": _relative(root, target), "sha256": _sha256(target)})
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "root_id": _root_id(root),
        "root_origin_status": "current_root",
        "created_at": existing.get("created_at") or _now(),
        "run_status": existing.get("run_status") or "running",
        "failed_stage": existing.get("failed_stage") or "",
        "exit_code": existing.get("exit_code"),
        "cleanup_actions": existing.get("cleanup_actions") or [],
        "input_snapshot_paths": snapshot or existing.get("input_snapshot_paths") or [],
        "input_snapshot_records": snapshot_records or existing.get("input_snapshot_records") or [],
        "actual_reads": existing.get("actual_reads") or [],
        "commands": existing.get("commands") or [],
        "artifacts": existing.get("artifacts") or [],
    }
    return _write_manifest(path, manifest)


def register_read(
    project_root: str | Path,
    run_id: str,
    path: str | Path,
    *,
    evidence_layer: str,
    read_source: str = "",
) -> Path:
    """Record a real input read and reject sources outside the current root."""
    root = Path(project_root).expanduser().resolve()
    target = Path(path).resolve()
    if evidence_layer not in {"original_source", "runtime_derived", "historical_artifact", "recovery_candidate"}:
        raise ValueError("evidence_layer 非法")
    if not target.is_file() or root not in target.parents:
        raise ValueError("读取输入必须是当前项目根内的已存在文件")
    manifest_file = initialize_run(root, run_id)
    manifest = _read(manifest_file)
    relative = _relative(root, target)
    reads = [row for row in manifest.get("actual_reads", []) if isinstance(row, dict) and row.get("relative_path") != relative]
    reads.append({
        "relative_path": relative,
        "sha256": _sha256(target),
        "evidence_layer": evidence_layer,
        "read_source": str(read_source),
        "root_id": _root_id(root),
        "read_at": _now(),
    })
    manifest["actual_reads"] = sorted(reads, key=lambda row: str(row["relative_path"]))
    return _write_manifest(manifest_file, manifest)


def finalize_run(project_root: str | Path, run_id: str, *, status: str, exit_code: int, failed_stage: str = "", cleanup_actions: list[str] | None = None) -> Path:
    """Persist the terminal status even for a failed run."""
    if status not in {"passed", "failed", "blocked"}:
        raise ValueError("运行状态必须为 passed、failed 或 blocked")
    root = Path(project_root).expanduser().resolve()
    manifest_file = initialize_run(root, run_id)
    manifest = _read(manifest_file)
    manifest.update({"run_status": status, "exit_code": int(exit_code), "failed_stage": failed_stage if status != "passed" else "", "cleanup_actions": list(cleanup_actions or [])})
    return _write_manifest(manifest_file, manifest)


def write_failure_receipt(
    project_root: str | Path,
    run_id: str,
    *,
    status: str,
    failed_stage: str,
    exit_code: int,
    errors: list[str] | None = None,
    cleanup_actions: list[str] | None = None,
) -> Path:
    """Write and register one current-run receipt before finalizing a non-success run."""
    if status not in {"failed", "blocked"}:
        raise ValueError("失败回执状态必须为 failed 或 blocked")
    root = Path(project_root).expanduser().resolve()
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id 必须是单个安全目录名")
    actions = [str(action) for action in cleanup_actions or [] if str(action).strip()]
    receipt = {
        "schema_version": "execution-pipeline-failure-1.0",
        "record_type": "run_failure",
        "run_id": run_id,
        "project_root": str(root),
        "status": status,
        "failed_stage": str(failed_stage),
        "exit_code": int(exit_code),
        "errors": [str(error) for error in errors or [] if str(error).strip()],
        "cleanup_actions": actions,
        "executed_at": _now(),
    }
    receipt_path = manifest_path(root, run_id).parent / "run_failure.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    initialize_run(root, run_id)
    register_artifact(root, run_id, receipt_path, kind="failure_receipt", status="success", exit_code=0)
    finalize_run(root, run_id, status=status, exit_code=exit_code, failed_stage=failed_stage, cleanup_actions=actions)
    return receipt_path


def register_command_execution(project_root: str | Path, run_id: str, command_records: list[dict[str, Any]]) -> Path:
    """Persist command outcomes in the current run manifest without shell aggregation."""
    root = Path(project_root).expanduser().resolve()
    manifest_file = initialize_run(root, run_id)
    manifest = _read(manifest_file)
    manifest["commands"] = [row for row in command_records if isinstance(row, dict)]
    return _write_manifest(manifest_file, manifest)


def register_artifact(
    project_root: str | Path, run_id: str, path: str | Path, *, kind: str, module_id: str = "",
    status: str = "success", exit_code: int | None = None,
) -> Path:
    """Append or replace one artifact record after the artifact is durably written."""
    root = Path(project_root).expanduser().resolve()
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id 必须是单个安全目录名")
    target = Path(path).resolve()
    if not target.is_file() or root not in target.parents:
        raise ValueError("运行产物必须是项目目录内的已存在文件")
    manifest_file = initialize_run(root, run_id)
    manifest = _read(manifest_file)
    if manifest.get("run_id") not in {None, "", run_id}:
        raise ValueError("运行清单 run_id 不一致")
    # A file can have both a module-output record and a domain-specific evidence
    # record (for example, scene_selection). Preserve both attestations.
    relative_path = _relative(root, target)
    artifacts = [
        row for row in manifest.get("artifacts", [])
        if isinstance(row, dict) and not (
            row.get("relative_path") == relative_path
            and row.get("kind") == kind
            and str(row.get("module_id") or "") == str(module_id)
        )
    ]
    artifacts.append({
        "kind": kind, "module_id": str(module_id), "relative_path": _relative(root, target),
        "sha256": _sha256(target), "bytes": target.stat().st_size, "status": status,
        "exit_code": exit_code, "recorded_at": _now(),
    })
    manifest["artifacts"] = sorted(artifacts, key=lambda row: (str(row.get("kind")), str(row.get("module_id")), str(row.get("relative_path"))))
    return _write_manifest(manifest_file, manifest)


def verify_manifest(
    project_root: str | Path,
    run_id: str,
    *,
    required_kinds: set[str] | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    path = manifest_path(root, run_id)
    manifest = _read(path)
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("run_id") != run_id:
        errors.append("运行清单不存在或格式无效")
    if manifest.get("root_id") != _root_id(root) or manifest.get("root_origin_status") != "current_root":
        errors.append("运行清单根目录身份无效")
    actual_reads = manifest.get("actual_reads", []) if isinstance(manifest.get("actual_reads"), list) else []
    declared_snapshot_value = manifest.get("input_snapshot_paths")
    declared_snapshot = set(declared_snapshot_value) if isinstance(declared_snapshot_value, list) else set()
    snapshot_records = manifest.get("input_snapshot_records") if isinstance(manifest.get("input_snapshot_records"), list) else []
    expected_hashes = {
        str(row.get("relative_path")): str(row.get("sha256"))
        for row in snapshot_records
        if isinstance(row, dict) and row.get("relative_path") and row.get("sha256")
    }
    snapshot_reads = [
        row for row in actual_reads
        if isinstance(row, dict) and row.get("evidence_layer") != "runtime_derived"
    ]
    read_paths = {str(row.get("relative_path")) for row in snapshot_reads}
    if not isinstance(declared_snapshot_value, list) or read_paths != declared_snapshot:
        errors.append("实际读取集合与输入快照集合不一致")
    if declared_snapshot and set(expected_hashes) != declared_snapshot:
        errors.append("输入快照缺少路径或哈希记录")
    for row in actual_reads:
        if not isinstance(row, dict) or row.get("evidence_layer") not in {"original_source", "runtime_derived", "historical_artifact", "recovery_candidate"}:
            errors.append("实际读取记录无效或证据层非法")
            continue
        artifact = (root / str(row.get("relative_path") or "")).resolve()
        if not artifact.is_file() or root not in artifact.parents or row.get("sha256") != _sha256(artifact):
            errors.append(f"实际读取输入不存在、越界或哈希漂移：{row.get('relative_path')}")
        elif row.get("evidence_layer") != "runtime_derived" and expected_hashes.get(str(row.get("relative_path"))) != row.get("sha256"):
            errors.append(f"实际读取输入与快照哈希不一致：{row.get('relative_path')}")
    artifacts = manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []
    profile_errors: list[str] = []
    profile_required_kinds = set(required_kinds or set())
    if profile == "full_pipeline":
        profile_required_kinds.update(FULL_PIPELINE_REQUIRED_KINDS)
    elif profile not in {None, ""}:
        profile_errors.append(f"未知运行清单 profile：{profile}")
    kinds = {str(row.get("kind")) for row in artifacts if isinstance(row, dict)}
    for kind in sorted(profile_required_kinds):
        if kind not in kinds:
            errors.append(f"运行清单缺少必需产物类别：{kind}")
    if profile == "full_pipeline":
        module_ids = {
            str(row.get("module_id"))
            for row in artifacts
            if isinstance(row, dict) and row.get("kind") == "module_output"
        }
        missing_module_ids = sorted(FULL_PIPELINE_MODULE_IDS - module_ids)
        if missing_module_ids:
            errors.append("运行清单缺少必需模块输出：" + ", ".join(missing_module_ids))
    for row in artifacts:
        if not isinstance(row, dict):
            errors.append("运行清单包含无效产物记录")
            continue
        relative = str(row.get("relative_path") or "").replace("\\", "/")
        artifact = (root / relative).resolve()
        if not relative or root not in artifact.parents or not artifact.is_file():
            errors.append(f"运行产物不存在或路径非法：{relative}")
        elif row.get("sha256") != _sha256(artifact):
            errors.append(f"运行产物哈希不匹配：{relative}")
        if row.get("status") not in {"success", "passed"}:
            errors.append(f"运行产物状态未通过：{relative}")
        if row.get("exit_code") not in {None, 0}:
            errors.append(f"运行产物退出码非零：{relative}")
        if not relative.startswith(_run_relative_prefix(run_id)):
            errors.append(f"运行产物不在当前运行目录：{relative}")
            continue
        if str(row.get("kind")) in {
            "input_snapshot", "scene_selection", "runtime_material_package", "material_package",
            "module_output", "consumption_log", "failure_receipt", "command_log", "prose",
            "structural_quality", "literary_review", "delivery_report",
        }:
            embedded_run_ids = _embedded_run_ids(artifact)
            if embedded_run_ids != {run_id}:
                errors.append(f"运行产物 run_id 不一致或缺失：{relative}")
    errors.extend(profile_errors)
    return {"passed": not errors, "run_id": run_id, "profile": profile or "default", "manifest_path": _relative(root, path), "errors": list(dict.fromkeys(errors)), "manifest": manifest}


def verify_full_pipeline_manifest(project_root: str | Path, run_id: str) -> dict[str, Any]:
    """Verify the complete 00-11 production manifest with one stable entry point."""
    return verify_manifest(project_root, run_id, profile="full_pipeline")