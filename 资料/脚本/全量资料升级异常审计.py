"""Build read-only exception evidence from a completed delta run chain."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 全量资料升级执行器 import _binding_summary, _load_resume_selected_records, _read_json


SCHEMA_VERSION = "full-source-material-upgrade-exception-audit-1.0"
EXCEPTION_STATES = {"quarantined", "model_error"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _error_signature(errors: Any) -> str:
    if not isinstance(errors, list) or not errors:
        return "未记录错误详情"
    text = str(errors[0])
    if "source_ref" in text:
        return text
    if text.startswith("模型执行失败"):
        return "模型执行失败"
    return text


def _binding_ids(path: str | Path) -> tuple[set[str], str]:
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        raise ValueError("binding_id_file 不存在")
    ids = {
        line.strip() for line in file_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not ids:
        raise ValueError("binding_id_file 为空")
    return ids, hashlib.sha256(file_path.read_bytes()).hexdigest()


def audit(project_root: str | Path, run_id: str, binding_id_file: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    count, baseline_hash = _binding_summary(root)
    binding_id_file_sha256 = None
    if binding_id_file is None:
        bindings_path = root / "文档" / "证据" / "全量资料升级运行" / "绑定清单索引.jsonl"
        requested_ids: set[str] = set()
        with bindings_path.open(encoding="utf-8") as handle:
            for line in handle:
                requested_ids.add(str(json.loads(line)["binding_id"]))
    else:
        requested_ids, binding_id_file_sha256 = _binding_ids(binding_id_file)
    records, manifest = _load_resume_selected_records(root, run_id, baseline_hash, requested_ids)
    if len(records) != len(requested_ids):
        raise ValueError("运行链未覆盖所选 binding_id")
    if binding_id_file is None and (manifest.get("complete_full_run") is not True or len(records) != count):
        raise ValueError("只能审计覆盖完整绑定基线的完成运行")
    exceptions = []
    for binding_id in sorted(records):
        record = records[binding_id]
        if record.get("terminal_status") in EXCEPTION_STATES:
            exceptions.append({
                "binding_id": binding_id,
                "terminal_status": record.get("terminal_status"),
                "source_id": record.get("source_id"),
                "source_kind": record.get("source_kind"),
                "source_ref": record.get("source_ref"),
                "errors": record.get("errors", []),
                "error_signature": _error_signature(record.get("errors")),
                "original_object_sha256": record.get("original_object_sha256"),
                "run_id": record.get("run_id"),
            })
    groups: dict[tuple[str, str, str], list[str]] = {}
    for item in exceptions:
        key = (str(item["terminal_status"]), str(item["source_kind"]), str(item["error_signature"]))
        groups.setdefault(key, []).append(str(item["binding_id"]))
    output = root / "文档" / "证据" / "全量资料升级运行" / f"{run_id}-异常审计"
    output.mkdir(parents=True, exist_ok=False)
    exceptions_path = output / "exceptions.jsonl"
    with exceptions_path.open("w", encoding="utf-8") as handle:
        for item in exceptions:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    grouped = [
        {"terminal_status": key[0], "source_kind": key[1], "error_signature": key[2], "count": len(ids), "binding_ids": ids}
        for key, ids in sorted(groups.items())
    ]
    actual_counts = dict(Counter(str(record.get("terminal_status")) for record in records.values()))
    declared_counts = manifest.get("status_counts") if isinstance(manifest.get("status_counts"), dict) else {}
    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "audited_run_id": run_id,
        "baseline_binding_count": count,
        "binding_baseline_sha256": baseline_hash,
        "audit_scope": "binding_id_file" if binding_id_file is not None else "full_baseline",
        "selected_binding_id_count": len(requested_ids),
        "binding_id_file_sha256": binding_id_file_sha256,
        "status_counts": actual_counts,
        "declared_status_counts": declared_counts,
        "declared_status_counts_match_records": declared_counts == actual_counts,
        "exception_count": len(exceptions),
        "exception_groups": grouped,
        "automatic_repair_allowed": False,
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
        "formal_release_allowed": False,
        "exceptions_file": "exceptions.jsonl",
    }
    result["manifest_sha256"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    (output / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--binding-id-file", help="审计指定增量 ID；未指定时只允许完整基线运行")
    args = parser.parse_args()
    print(json.dumps(audit(args.project_root, args.run_id, args.binding_id_file), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())