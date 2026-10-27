"""Run source diagnosis windows unattended with default-deny safety checks."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from 全量资料升级执行器 import TERMINAL_STATES, _binding_summary, _binding_window, _load_resume_selected_records, run


SCHEMA_VERSION = "full-source-material-upgrade-guardian-1.0"
SAFE_STATES = {"validated_candidate", "validated_no_change"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON 证据：{path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 证据必须为对象：{path}")
    return value


def _run_directory(root: Path, run_id: str) -> Path:
    if Path(run_id).name != run_id:
        raise ValueError("run_id 必须是运行目录名称")
    return root / "文档" / "证据" / "全量资料升级运行" / run_id


def _records(root: Path, run_id: str, start_index: int | None = None, item_count: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    directory = _run_directory(root, run_id)
    manifest = _read_json(directory / "manifest.json")
    if manifest.get("run_id") != run_id:
        raise ValueError("运行清单 run_id 不匹配")
    baseline_count, expected_hash = _binding_summary(root)
    if start_index is None:
        indexed_rows = _binding_window(root, 0, None)
    else:
        indexed_rows = _binding_window(root, start_index, item_count or 1)
    requested = {str(row["binding_id"]) for row in indexed_rows}
    mapped, _ = _load_resume_selected_records(root, run_id, expected_hash, requested)
    records = [mapped.get(str(row["binding_id"]), {"binding_id": row["binding_id"], "terminal_status": None}) for row in indexed_rows]
    return manifest, records


def _validate_window(manifest: dict[str, Any], records: list[dict[str, Any]], start_index: int, item_count: int) -> str | None:
    gates = ("formal_fact_eligible", "prose_write_allowed", "formal_release_allowed")
    if manifest.get("execution_mode") != "execute" or manifest.get("contract_status") != "passed":
        return "执行模式或升级合同异常"
    if any(manifest.get(gate) is not False for gate in gates):
        return "正式门禁意外打开"
    window = records[start_index:start_index + item_count]
    if len(window) != item_count:
        return "运行记录窗口长度异常"
    for record in window:
        if record.get("terminal_status") not in SAFE_STATES:
            return f"记录 {record.get('binding_id')} 终态不安全：{record.get('terminal_status')}"
        if not record.get("model_input_sha256") or not record.get("original_object_sha256"):
            return f"记录 {record.get('binding_id')} 缺少证据哈希"
        if record.get("original_source_modified") is not False or record.get("existing_binding_modified") is not False:
            return f"记录 {record.get('binding_id')} 检测到来源或绑定修改"
        metadata = record.get("model_metadata")
        if not isinstance(metadata, dict) or metadata.get("structured_output") != "json_schema":
            return f"记录 {record.get('binding_id')} 未使用 JSON Schema 输出"
    return None


def guard(project_root: str | Path, resume_run: str, window_size: int = 1, sleep_seconds: int = 2, runner: Callable[..., dict[str, Any]] = run) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    if window_size != 1:
        raise ValueError("window_size 必须为 1，确保每条记录完成后都先经过保护校验")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds 不能为负数")
    state_path = root / "文档" / "证据" / "全量资料升级运行" / "守护运行状态.json"
    saved_state = _read_json(state_path) if state_path.exists() else {}
    if saved_state.get("initial_run_id") == resume_run and isinstance(saved_state.get("next_index"), int):
        current_run = str(saved_state.get("latest_run_id") or resume_run)
        next_index = int(saved_state["next_index"])
        manifest, records = _records(root, current_run, next_index, 1)
        baseline_count, _ = _binding_summary(root)
    else:
        manifest, records = _records(root, resume_run)
        current_run = resume_run
        next_index = next((index for index, record in enumerate(records) if record.get("terminal_status") not in TERMINAL_STATES), len(records))
        baseline_count = len(records)
    if manifest.get("binding_baseline_sha256") is None:
        raise ValueError("起始运行缺少绑定基线哈希")
    history: list[dict[str, Any]] = []
    status = "running"
    reason: str | None = None
    while next_index < baseline_count:
        count = min(window_size, baseline_count - next_index)
        try:
            result = runner(root, execute=True, resume_run=current_run, start_index=next_index, max_items=count)
        except Exception as exc:
            reason = f"执行器异常：{type(exc).__name__}: {exc}"
            history.append({"run_id": current_run, "start_index": next_index, "item_count": count, "validated_at": _now(), "stop_reason": reason})
            state = {"schema_version": SCHEMA_VERSION, "updated_at": _now(), "status": "stopped", "initial_run_id": resume_run, "latest_run_id": current_run, "next_index": next_index, "window_size": window_size, "stop_reason": reason, "history": history, "formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False}
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            status = "stopped"
            break
        current_run = str(result["run_id"])
        new_manifest, records = _records(root, current_run, next_index, count)
        reason = _validate_window(new_manifest, records, 0, count)
        history.append({"run_id": current_run, "start_index": next_index, "item_count": count, "validated_at": _now(), "stop_reason": reason})
        state = {"schema_version": SCHEMA_VERSION, "updated_at": _now(), "status": "stopped" if reason else "running", "initial_run_id": resume_run, "latest_run_id": current_run, "next_index": next_index + count if not reason else next_index, "window_size": window_size, "stop_reason": reason, "history": history, "formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False}
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if reason:
            status = "stopped"
            break
        next_index += count
        if next_index < baseline_count and sleep_seconds:
            time.sleep(sleep_seconds)
    else:
        status = "completed"
    state = _read_json(state_path) if state_path.exists() else {}
    state.update({"schema_version": SCHEMA_VERSION, "updated_at": _now(), "status": status, "latest_run_id": current_run, "next_index": next_index, "stop_reason": reason, "formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False})
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--resume-run", required=True)
    parser.add_argument("--window-size", type=int, default=1, help="安全默认值为 1；每条记录验证通过后才继续")
    parser.add_argument("--sleep-seconds", type=int, default=2)
    args = parser.parse_args()
    result = guard(args.project_root, args.resume_run, args.window_size, args.sleep_seconds)
    print(json.dumps({key: result.get(key) for key in ("status", "latest_run_id", "next_index", "stop_reason")}, ensure_ascii=False))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())