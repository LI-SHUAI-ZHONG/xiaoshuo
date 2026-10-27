"""Turn one auditable model_error record into a terminal quarantine child run."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 严格全量资料模型升级 as strict


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_parent_record(root: Path, run_id: str, binding_id: str) -> dict[str, Any] | None:
    runs = root / "文档" / "证据" / "全量资料升级运行"
    seen: set[str] = set()
    while run_id and run_id not in seen:
        seen.add(run_id)
        run_dir = runs / run_id
        manifest = strict.load_json(run_dir / "manifest.json")
        if manifest.get("run_id") != run_id:
            raise ValueError(f"父链运行 manifest 不匹配: {run_id}")
        for record in strict.iter_rows(run_dir / "records.jsonl"):
            if record.get("binding_id") == binding_id:
                return record
        run_id = str(manifest.get("parent_run_id") or "")
    return None


def run(root: Path, run_id: str, parent_run_id: str, binding_id: str) -> dict[str, Any]:
    runs = root / "文档" / "证据" / "全量资料升级运行"
    output_dir = runs / run_id
    if output_dir.exists():
        raise ValueError(f"新 run_id 已存在，禁止覆盖: {run_id}")
    parent_manifest = strict.load_json(runs / parent_run_id / "manifest.json")
    source = find_parent_record(root, parent_run_id, binding_id)
    if not source or source.get("terminal_status") != "model_error":
        raise ValueError("只能隔离父链中现有的 model_error 记录")
    output_dir.mkdir(parents=True)
    source_run_id = source.get("run_id")
    record = dict(source)
    record.update({
        "run_id": run_id,
        "batch_id": f"ISOLATE-{run_id}",
        "terminal_status": "quarantined",
        "automatic_validation": {
            "passed": False,
            "errors": list(source.get("automatic_validation", {}).get("errors", [])) + ["模型调用失败后按隔离政策终止，不重试模型"],
        },
        "model_metadata": {
            **source.get("model_metadata", {}), "executed": False,
            "isolation_source_run_id": source_run_id,
            "isolation_reason": "prior_model_error",
        },
    })
    with (output_dir / "records.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(strict.canonical(record) + "\n")
        stream.flush()
    manifest = {
        "schema_version": "full-source-material-upgrade-execution-2.0", "run_id": run_id,
        "parent_run_id": parent_run_id, "generated_at": now(), "execution_mode": "isolate_model_error",
        "policy_schema": strict.POLICY_SCHEMA,
        "baseline_binding_count": parent_manifest["baseline_binding_count"],
        "binding_baseline_sha256": parent_manifest["binding_baseline_sha256"],
        "processed_count": 1, "complete_full_run": False, "records_mode": "delta",
        "status_counts": {"quarantined": 1}, "audit_state": "micro_batch_complete",
        "formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--parent-run-id", required=True)
    parser.add_argument("--binding-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.project_root).resolve(), args.run_id, args.parent_run_id, args.binding_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())