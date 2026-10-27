"""Audit and terminalize current-root runs for 28-H recovery evidence.

This utility never resumes by copying files and never changes source material.
Resume is allowed only when the manifest snapshot and all registered artifacts
still match. Repeating a resume audit is idempotent and does not append records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 运行清单复核 import _root_id, manifest_path, write_failure_receipt


SCHEMA_VERSION = "run-recovery-idempotency-1.0"
PRIMARY_MATERIAL_PATHS = {
    "资料库": "原始资料/资料库.txt",
    "类型系统": "原始资料/类型系统.txt",
    "类型连接": "原始资料/类型连接.txt",
    "静态网络": "原始资料/静态网络.txt",
    "动态网络": "原始资料/动态网络.txt",
    "锚点网络": "原始资料/锚点网络.txt",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _six_materials_digest(root: Path) -> dict[str, str | None]:
    return {
        name: _sha256(root / relative) if (root / relative).is_file() else None
        for name, relative in PRIMARY_MATERIAL_PATHS.items()
    }


def _inside(root: Path, relative: str) -> Path | None:
    target = (root / relative.replace("\\", "/")).resolve()
    return target if target.is_file() and root in target.parents else None


def audit_run(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    path = manifest_path(root, run_id)
    manifest = _read(path)
    errors: list[str] = []
    if manifest.get("run_id") != run_id:
        errors.append("manifest 缺失或 run_id 不一致")
    if manifest.get("root_id") and manifest.get("root_id") != _root_id(root):
        errors.append("manifest root_id 与当前项目根不一致")
    snapshot_file = root / "文档" / "证据" / "运行" / run_id / "run_input_snapshot.json"
    run_snapshot = _read(snapshot_file)
    expected_materials = run_snapshot.get("six_materials_sha256") if isinstance(run_snapshot, dict) else None
    if expected_materials is not None and expected_materials != _six_materials_digest(root):
        errors.append("输入快照哈希漂移：six_materials_sha256")
    if isinstance(run_snapshot, dict) and run_snapshot.get("run_id") not in {None, "", run_id}:
        errors.append("运行输入快照 run_id 不一致")
    snapshot = manifest.get("input_snapshot_records", [])
    if not isinstance(snapshot, list):
        snapshot = []
    for record in snapshot:
        if not isinstance(record, dict):
            errors.append("输入快照包含无效记录")
            continue
        relative = str(record.get("relative_path") or "")
        target = _inside(root, relative)
        if target is None:
            errors.append(f"输入快照文件不存在或越界：{relative}")
        elif record.get("sha256") != _sha256(target):
            errors.append(f"输入快照哈希漂移：{relative}")
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        artifacts = []
    seen: set[tuple[str, str]] = set()
    duplicate_count = 0
    for record in artifacts:
        if not isinstance(record, dict):
            errors.append("产物清单包含无效记录")
            continue
        key = (str(record.get("kind") or ""), str(record.get("relative_path") or ""))
        if key in seen:
            duplicate_count += 1
        seen.add(key)
        relative = key[1]
        target = _inside(root, relative)
        if target is None:
            errors.append(f"登记产物不存在或越界：{relative}")
        elif record.get("sha256") != _sha256(target):
            errors.append(f"登记产物哈希漂移：{relative}")
        if record.get("run_id") not in {None, "", run_id}:
            errors.append(f"产物 run_id 不一致：{relative}")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "project_root": str(root),
        "manifest_status": manifest.get("run_status"),
        "snapshot_count": len(snapshot),
        "artifact_count": len(artifacts),
        "duplicate_artifact_records": duplicate_count,
        "passed": not errors and duplicate_count == 0,
        "errors": list(dict.fromkeys(errors)),
        "checked_at": _now(),
    }


def terminalize_interrupted_run(project_root: str | Path, run_id: str, reason: str) -> dict[str, Any]:
    """Record an external interruption; a running run is never silently resumed."""
    root = Path(project_root).expanduser().resolve()
    audit = audit_run(root, run_id)
    errors = list(audit["errors"])
    errors.append("运行在看门器检查时仍为 running，未发现可安全完成的进程回执")
    receipt = write_failure_receipt(
        root, run_id, status="failed", failed_stage="external_interruption", exit_code=130,
        errors=errors + [reason],
        cleanup_actions=["拒绝复用未验证进度", "未授予正文写入或正式交付资格", "恢复前必须重新校验输入快照"],
    )
    return {"run_id": run_id, "status": "failed", "exit_code": 130, "receipt": str(receipt), "audit": audit}


def resume_audit(project_root: str | Path, run_id: str) -> dict[str, Any]:
    """Validate a resumable run without writing duplicate artifacts."""
    root = Path(project_root).expanduser().resolve()
    audit = audit_run(root, run_id)
    manifest = _read(manifest_path(root, run_id))
    if manifest.get("run_status") not in {"failed", "blocked"}:
        audit["errors"].append("只有 failed 或 blocked 运行允许进入恢复审计")
    audit["errors"] = list(dict.fromkeys(audit["errors"]))
    audit["passed"] = not audit["errors"]
    audit["resume_allowed"] = audit["passed"]
    audit["idempotent"] = audit.get("duplicate_artifact_records", 0) == 0
    audit["status"] = "resume_allowed" if audit["resume_allowed"] else "resume_blocked"
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--terminate-interrupted", action="store_true")
    parser.add_argument("--reason", default="外部中断，无法证明原进程仍在运行")
    args = parser.parse_args()
    if args.terminate_interrupted:
        result = terminalize_interrupted_run(args.project_root, args.run_id, args.reason)
        print(json.dumps(result, ensure_ascii=False))
        return 2
    result = resume_audit(args.project_root, args.run_id)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["resume_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())