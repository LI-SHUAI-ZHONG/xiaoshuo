"""Audit a completed strict continuous-upgrade campaign without reopening any write gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 严格全量资料模型升级 as strict


SCHEMA_VERSION = "strict-continuous-source-upgrade-final-audit-1.0"
GATES = {"formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return list(strict.iter_rows(path))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root: Path, campaign_id: str) -> dict[str, Any]:
    campaign_dir = root / "文档" / "证据" / "严格连续资料升级运行" / campaign_id
    batches = load_jsonl(campaign_dir / "batches.jsonl")
    if not batches:
        raise ValueError("缺少已登记的首轮批次")

    baseline = {field: batches[0].get(field) for field in ("baseline_binding_count", "binding_baseline_sha256")}
    resume_start = int(batches[0].get("start", -1))
    if resume_start != 0:
        raise ValueError("首轮登记必须从冻结基线索引 0 开始；续跑尾段不能作为完整活动审核")
    cursor = resume_start
    parent_run_id = None
    first_pass: dict[str, dict[str, Any]] = {}
    batch_checks: list[dict[str, Any]] = []
    runs = root / "文档" / "证据" / "全量资料升级运行"
    for event in batches:
        if {field: event.get(field) for field in baseline} != baseline:
            raise ValueError("登记批次冻结基线不一致")
        count = int(event.get("count", 0))
        if count < 5 or count > 10 or int(event.get("start", -1)) != cursor:
            raise ValueError("登记批次窗口不连续或不符合批次政策")
        run_id = str(event.get("run_id") or "")
        if event.get("parent_run_id") != parent_run_id and parent_run_id is not None:
            raise ValueError("登记批次父链不连续")
        manifest = strict.load_json(runs / run_id / "manifest.json")
        records = load_jsonl(runs / run_id / "records.jsonl")
        actual_counts = dict(Counter(str(record.get("terminal_status")) for record in records))
        if (manifest.get("run_id") != run_id or manifest.get("parent_run_id") != event.get("parent_run_id")
                or {field: manifest.get(field) for field in baseline} != baseline
                or manifest.get("processed_count") != count or len(records) != count
                or manifest.get("status_counts") != actual_counts or event.get("status_counts") != actual_counts):
            raise ValueError(f"批次 {run_id} 的登记、manifest 与 records 不一致")
        for record in records:
            binding_id = str(record.get("binding_id") or "")
            if not binding_id or binding_id in first_pass:
                raise ValueError("首轮 binding 缺失或重复")
            first_pass[binding_id] = record
        batch_checks.append({"run_id": run_id, "count": count, "status_counts": actual_counts})
        cursor += count
        parent_run_id = run_id

    if cursor != int(baseline["baseline_binding_count"]):
        raise ValueError("首轮登记覆盖未到达冻结基线末尾")
    if len(first_pass) != int(baseline["baseline_binding_count"]):
        raise ValueError("首轮记录数未覆盖完整冻结基线")

    expected_errors = {(record["run_id"], binding_id) for binding_id, record in first_pass.items()
                       if record.get("terminal_status") == "model_error"}
    isolated: set[tuple[str | None, str]] = set()
    isolate_runs = sorted(runs.glob(f"{campaign_id}-q*"))
    isolate_parent = parent_run_id
    for run_dir in isolate_runs:
        manifest = strict.load_json(run_dir / "manifest.json")
        records = load_jsonl(run_dir / "records.jsonl")
        if (manifest.get("run_id") != run_dir.name or manifest.get("parent_run_id") != isolate_parent
                or manifest.get("execution_mode") != "isolate_model_error" or len(records) != 1
                or manifest.get("processed_count") != 1 or manifest.get("status_counts") != {"quarantined": 1}):
            raise ValueError(f"隔离运行 {run_dir.name} 不完整或父链不连续")
        record = records[0]
        metadata = record.get("model_metadata") or {}
        source = metadata.get("isolation_source_run_id")
        binding_id = str(record.get("binding_id") or "")
        if record.get("terminal_status") != "quarantined" or metadata.get("executed") is not False:
            raise ValueError(f"隔离运行 {run_dir.name} 不是无模型 quarantined 记录")
        isolated.add((source, binding_id))
        isolate_parent = run_dir.name
    if isolated != expected_errors:
        raise ValueError("首轮 model_error 与隔离记录未一一对应")

    final_status_counts = Counter(record.get("terminal_status") for record in first_pass.values())
    final_status_counts["quarantined"] += len(isolated)
    result = {
        "schema_version": SCHEMA_VERSION, "campaign_id": campaign_id, "audited_at": now(),
        "status": "audited_complete", "latest_run_id": isolate_parent, "resume_start": resume_start,
        **baseline, "registered_batch_count": len(batches), "first_pass_record_count": len(first_pass),
        "first_pass_status_counts": dict(Counter(record.get("terminal_status") for record in first_pass.values())),
        "model_error_count": len(expected_errors), "isolation_record_count": len(isolated),
        "isolation_coverage_exact": True, "final_status_counts": dict(final_status_counts),
        "batches_sha256": sha256_file(campaign_dir / "batches.jsonl"),
        "batch_checks": batch_checks, **GATES,
    }
    (campaign_dir / "final-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = {"schema_version": "strict-continuous-source-upgrade-1.0", "campaign_id": campaign_id,
             "started_at": strict.load_json(campaign_dir / "state.json").get("started_at"), "updated_at": now(),
             "status": "audited_complete", "latest_run_id": isolate_parent, "resume_start": resume_start,
             **baseline, "completed_bindings": len(first_pass), "remaining_bindings": 0,
             "final_audit": "final-audit.json", **GATES}
    (campaign_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--campaign-id", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(Path(args.project_root).resolve(), args.campaign_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())