"""Sequentially run strict source-material upgrades in policy-sized batches.

This coordinator never changes source materials, bindings, or prior evidence.
Each model batch is an independent append-only strict run.  Failed terminal
states are recorded in a separate append-only review index while later
bindings continue to be processed.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 严格全量资料模型升级 as strict
import 全量资料升级模型错误隔离 as isolation


SCHEMA_VERSION = "strict-continuous-source-upgrade-1.0"
REVIEW_STATUSES = {"model_error", "quarantined"}
# A model error is terminal for the first-pass model stage. It remains in the
# review index and is quarantined only after every binding has had that pass.
COMPLETED_STATUSES = {"validated_candidate", "validated_no_change", "model_error", "quarantined"}
GATES = {"formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_bindings(root: Path) -> list[dict[str, Any]]:
    document = strict.load_json(root / "文档" / "证据" / "全量资料解释词创作绑定.json")
    bindings = [row for row in document.get("records", []) if isinstance(row, dict)]
    if document.get("binding_count") != len(bindings) or len(bindings) != 13345:
        raise ValueError("绑定基线数量不符合严格连续执行要求")
    return bindings


def binding_baseline(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the immutable campaign baseline used by every child run."""
    return {
        "baseline_binding_count": len(bindings),
        "binding_baseline_sha256": strict.digest(bindings),
    }


def require_matching_baseline(expected: dict[str, Any], actual: dict[str, Any], context: str) -> None:
    for field in ("baseline_binding_count", "binding_baseline_sha256"):
        if actual.get(field) != expected.get(field):
            raise ValueError(f"{context} 的 {field} 与 campaign 冻结基线不一致")


def parent_manifest(root: Path, run_id: str) -> dict[str, Any]:
    path = root / "文档" / "证据" / "全量资料升级运行" / run_id / "manifest.json"
    manifest = strict.load_json(path)
    if not isinstance(manifest, dict) or manifest.get("run_id") != run_id:
        raise ValueError("父链运行 manifest 缺失或 run_id 不匹配")
    return manifest


def pending_indexes(bindings: list[dict[str, Any]], statuses: dict[str, str], resume_start: int = 0) -> list[int]:
    """Return bindings that have not yet received a first-pass terminal record."""
    return [
        index for index, binding in enumerate(bindings) if index >= resume_start
        if str(binding.get("binding_id") or "") not in statuses
        or statuses[str(binding.get("binding_id") or "")] not in COMPLETED_STATUSES
    ]


def next_window(pending: list[int], batch_size: int) -> tuple[int, int]:
    """Return the next policy-sized contiguous window, or fail before rerunning items."""
    if not pending:
        raise ValueError("不存在待处理 binding")
    count = min(batch_size, len(pending))
    if count < 5:
        raise ValueError("剩余待处理 binding 少于政策允许的最小批次，必须由新的合规续跑计划处理")
    window = pending[:count]
    if window != list(range(window[0], window[0] + count)):
        raise ValueError("待处理 binding 不连续，禁止通过重跑已终态记录来填充模型批次")
    return window[0], count


def review_entry(record: dict[str, Any], campaign_baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    model_metadata = record.get("model_metadata")
    if not isinstance(model_metadata, dict):
        model_metadata = {}
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": now(),
        "run_id": record.get("run_id"),
        "binding_id": record.get("binding_id"),
        "source_id": record.get("source_id"),
        "source_kind": record.get("source_kind"),
        "source_ref": record.get("source_ref"),
        "terminal_status": record.get("terminal_status"),
        "deterministic_errors": record.get("deterministic_validation", {}).get("errors", []),
        "automatic_errors": record.get("automatic_validation", {}).get("errors", []),
        "response_sha256": model_metadata.get("response_sha256"),
        **(campaign_baseline or {}), **GATES,
    }


def append_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    if items:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            for item in items:
                stream.write(strict.canonical(item) + "\n")


def review_records(records: dict[str, dict[str, Any]], campaign_baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [review_entry(record, campaign_baseline) for record in records.values() if record.get("terminal_status") in REVIEW_STATUSES]


def parent_chain_summary(root: Path, run_id: str, campaign_baseline: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Stream parent evidence, retaining only completion state and review rows."""
    runs = root / "文档" / "证据" / "全量资料升级运行"
    chain: list[Path] = []
    seen: set[str] = set()
    while run_id and run_id not in seen:
        seen.add(run_id)
        run_dir = runs / run_id
        manifest = strict.load_json(run_dir / "manifest.json")
        if manifest.get("run_id") != run_id:
            raise ValueError(f"旧运行 manifest 不匹配: {run_id}")
        chain.append(run_dir)
        run_id = str(manifest.get("parent_run_id") or "")
    statuses: dict[str, str] = {}
    review_by_binding: dict[str, dict[str, Any]] = {}
    for run_dir in reversed(chain):
        for record in strict.iter_rows(run_dir / "records.jsonl"):
            binding_id = str(record.get("binding_id") or "")
            status = str(record.get("terminal_status") or "")
            if not binding_id:
                continue
            statuses[binding_id] = status
            if status in REVIEW_STATUSES:
                review_by_binding[binding_id] = review_entry(record, campaign_baseline)
            else:
                review_by_binding.pop(binding_id, None)
    return statuses, list(review_by_binding.values())


def run(root: Path, campaign_id: str, parent_run_id: str, batch_size: int, sleep_seconds: float,
        resume_start: int = 0) -> dict[str, Any]:
    if not 5 <= batch_size <= 10:
        raise ValueError("batch_size 必须介于 5 和 10")
    bindings = load_bindings(root)
    campaign_dir = root / "文档" / "证据" / "严格连续资料升级运行" / campaign_id
    previous_state: dict[str, Any] = {}
    if campaign_dir.exists():
        state_path = campaign_dir / "state.json"
        previous_state = strict.load_json(state_path) if state_path.exists() else {}
        if previous_state.get("status") == "completed":
            raise ValueError(f"campaign_id 已完成，禁止覆盖: {campaign_id}")
        if previous_state and previous_state.get("status") not in {"stopped", "preparing_parent_index"}:
            raise ValueError(f"campaign_id 已存在且状态不可恢复: {campaign_id}")
    else:
        campaign_dir.mkdir(parents=True)
    if not 0 <= resume_start < len(bindings):
        raise ValueError("resume_start 必须指向绑定基线中的有效项目")
    baseline = binding_baseline(bindings)
    require_matching_baseline(baseline, parent_manifest(root, parent_run_id), "父链运行")
    campaign_dir.mkdir(parents=True, exist_ok=True)
    (campaign_dir / "campaign-baseline.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "campaign_id": campaign_id, "parent_run_id": parent_run_id,
        "frozen_at": now(), "resume_start": resume_start, "resume_binding_id": bindings[resume_start].get("binding_id"), **baseline, **GATES,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    batches_path = campaign_dir / "batches.jsonl"
    review_path = campaign_dir / "待统一处理索引.jsonl"
    started = str(previous_state.get("started_at") or now())
    (campaign_dir / "state.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "campaign_id": campaign_id, "started_at": started, "updated_at": started,
        "status": "preparing_parent_index", "latest_run_id": parent_run_id, "resume_start": resume_start,
        "resume_binding_id": bindings[resume_start].get("binding_id"), **baseline, **GATES,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if resume_start:
        # Recovery progress is exclusively the append-only registered batch
        # index. Scanning a potentially complete historical parent chain here
        # is both unnecessary and can delay recovery before any model work.
        statuses, parent_review = {}, []
    else:
        statuses, parent_review = parent_chain_summary(root, parent_run_id, baseline)
        unexpected = set(statuses) - {str(row.get("binding_id") or "") for row in bindings}
        if unexpected:
            raise ValueError("父链包含不在当前绑定基线中的 binding_id")
    binding_indexes = {str(binding.get("binding_id") or ""): index for index, binding in enumerate(bindings)}
    batches_path = campaign_dir / "batches.jsonl"
    registered_batches = list(strict.iter_rows(batches_path))
    current_parent = parent_run_id
    for event in registered_batches:
        run_id = str(event.get("run_id") or "")
        if not run_id.startswith(f"{campaign_id}-b"):
            raise ValueError("campaign 批次索引包含不属于当前 campaign 的 run_id")
        require_matching_baseline(baseline, event, f"登记批次 {run_id}")
        run_records = strict.rows(root / "文档" / "证据" / "全量资料升级运行" / run_id / "records.jsonl")
        if len(run_records) != event.get("count"):
            raise ValueError(f"登记批次 {run_id} 的 records 与索引数量不一致")
        statuses.update({str(record.get("binding_id") or ""): str(record.get("terminal_status") or "") for record in run_records})
        current_parent = run_id
    # A recovery campaign deliberately reruns its declared range despite older-chain terminals.
    if resume_start:
        statuses = {binding_id: status for binding_id, status in statuses.items()
                    if binding_indexes[binding_id] < resume_start}
        for event in registered_batches:
            run_id = str(event.get("run_id") or "")
            for record in strict.rows(root / "文档" / "证据" / "全量资料升级运行" / run_id / "records.jsonl"):
                statuses[str(record.get("binding_id") or "")] = str(record.get("terminal_status") or "")
    pending = pending_indexes(bindings, statuses, resume_start)
    append_jsonl(review_path, parent_review)
    batch_number = len(registered_batches)
    try:
        while pending:
            require_matching_baseline(baseline, binding_baseline(load_bindings(root)), "当前绑定资料")
            start, count = next_window(pending, batch_size)
            run_id = f"{campaign_id}-b{batch_number:04d}"
            while (root / "文档" / "证据" / "全量资料升级运行" / run_id).exists():
                batch_number += 1
                run_id = f"{campaign_id}-b{batch_number:04d}"
            manifest = strict.run(root, run_id, current_parent, start, count, expected_baseline=baseline)
            require_matching_baseline(baseline, manifest, f"子运行 {run_id}")
            run_records = strict.rows(root / "文档" / "证据" / "全量资料升级运行" / run_id / "records.jsonl")
            if len(run_records) != count:
                raise RuntimeError(f"{run_id} 记录数量与请求窗口不一致")
            batch_event = {"schema_version": SCHEMA_VERSION, "recorded_at": now(), "run_id": run_id,
                           "parent_run_id": current_parent, "start": start, "count": count, **baseline,
                           "status_counts": manifest.get("status_counts"), **GATES}
            append_jsonl(batches_path, [batch_event])
            append_jsonl(review_path, review_records({str(record.get("binding_id") or ""): record for record in run_records}, baseline))
            current_parent = run_id
            statuses.update({str(record.get("binding_id")): str(record.get("terminal_status") or "") for record in run_records})
            pending = pending_indexes(bindings, statuses, resume_start)
            batch_number += 1
            if pending and sleep_seconds:
                time.sleep(sleep_seconds)

        # Do not retry the model. Once the first pass covers the complete
        # declared range, terminalize retained failures as isolated children.
        failed_binding_ids = [
            binding_id for binding_id, status in statuses.items()
            if status == "model_error" and binding_indexes.get(binding_id, -1) >= resume_start
        ]
        for isolation_number, binding_id in enumerate(failed_binding_ids):
            run_id = f"{campaign_id}-q{isolation_number:04d}"
            manifest = isolation.run(root, run_id, current_parent, binding_id)
            require_matching_baseline(baseline, manifest, f"隔离运行 {run_id}")
            run_records = strict.rows(root / "文档" / "证据" / "全量资料升级运行" / run_id / "records.jsonl")
            if len(run_records) != 1 or run_records[0].get("binding_id") != binding_id:
                raise RuntimeError(f"{run_id} 隔离记录与请求 binding 不一致")
            append_jsonl(review_path, review_records({binding_id: run_records[0]}, baseline))
            statuses[binding_id] = "quarantined"
            current_parent = run_id
    except Exception as error:
        state = {"schema_version": SCHEMA_VERSION, "campaign_id": campaign_id, "started_at": started, "updated_at": now(),
                 "status": "stopped", "latest_run_id": current_parent, "resume_start": resume_start,
                 "completed_bindings": len(statuses),
                  "remaining_bindings": len(pending), "stop_reason": f"{type(error).__name__}: {error}", **baseline, **GATES}
        (campaign_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    final = {"schema_version": SCHEMA_VERSION, "campaign_id": campaign_id, "started_at": started, "completed_at": now(),
              "status": "completed", "initial_parent_run_id": parent_run_id, "latest_run_id": current_parent, "resume_start": resume_start,
              **baseline, "completed_bindings": len(statuses), "remaining_bindings": len(pending),
             "final_status_counts": dict(Counter(statuses.values())),
             "review_index": str(review_path.relative_to(root)), **GATES}
    (campaign_dir / "final-summary.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--parent-run-id", required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    parser.add_argument("--resume-start", type=int, default=0)
    args = parser.parse_args()
    result = run(Path(args.project_root).resolve(), args.campaign_id, args.parent_run_id, args.batch_size, args.sleep_seconds,
                 args.resume_start)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())