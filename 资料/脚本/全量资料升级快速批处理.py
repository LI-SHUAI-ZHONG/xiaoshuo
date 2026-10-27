"""Continue full-source diagnosis in batches without treating recorded exceptions as success."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from 全量资料升级执行器 import _binding_summary, run


SCHEMA_VERSION = "full-source-material-upgrade-fast-batch-1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _state_path(root: Path, resume_run: str) -> Path:
    """Keep resumable state isolated to one immutable parent run chain."""
    if Path(resume_run).name != resume_run:
        raise ValueError("resume_run 必须是运行目录名称")
    return root / "文档" / "证据" / "全量资料升级运行" / f"快速批处理状态-{resume_run}.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取批处理状态：{path}") from exc
    if not isinstance(value, dict):
        raise ValueError("批处理状态必须为对象")
    return value


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def batch_continue(project_root: str | Path, resume_run: str, start_index: int, batch_size: int = 16, derived_mapping_file: str | Path | None = None, runner: Callable[..., dict[str, Any]] = run) -> dict[str, Any]:
    """Process every remaining binding, retaining quarantines/errors for later repair."""
    root = Path(project_root).expanduser().resolve()
    if batch_size < 1 or batch_size > 64:
        raise ValueError("batch_size 必须在 1 到 64 之间")
    count, baseline_hash = _binding_summary(root)
    if start_index < 0 or start_index > count:
        raise ValueError("start_index 超出绑定基线范围")
    state_path = _state_path(root, resume_run)
    state = _read_json(state_path) if state_path.exists() else {}
    if state.get("initial_run_id") == resume_run and state.get("binding_baseline_sha256") == baseline_hash and isinstance(state.get("next_index"), int):
        current_run = str(state.get("latest_run_id") or resume_run)
        next_index = max(start_index, int(state["next_index"]))
        completed_batches = list(state.get("completed_batches", [])) if isinstance(state.get("completed_batches"), list) else []
    else:
        current_run = resume_run
        next_index = start_index
        completed_batches = []
    while next_index < count:
        item_count = min(batch_size, count - next_index)
        try:
            result = runner(root, execute=True, resume_run=current_run, start_index=next_index, max_items=item_count, assume_missing=True, derived_mapping_file=derived_mapping_file)
        except Exception as exc:
            state = {
                "schema_version": SCHEMA_VERSION,
                "updated_at": _now(),
                "status": "stopped",
                "initial_run_id": resume_run,
                "latest_run_id": current_run,
                "next_index": next_index,
                "batch_size": batch_size,
                "binding_baseline_count": count,
                "binding_baseline_sha256": baseline_hash,
                "derived_mapping_file": str(derived_mapping_file) if derived_mapping_file else None,
                "stop_reason": f"执行器异常：{type(exc).__name__}: {exc}",
                "completed_batches": completed_batches,
                "formal_fact_eligible": False,
                "prose_write_allowed": False,
                "formal_release_allowed": False,
            }
            _write_state(state_path, state)
            return state
        current_run = str(result["run_id"])
        next_index += item_count
        completed_batches.append({"run_id": current_run, "start_index": next_index - item_count, "item_count": item_count, "status_counts": result.get("status_counts", {}), "completed_at": _now()})
        state = {
            "schema_version": SCHEMA_VERSION,
            "updated_at": _now(),
            "status": "completed" if next_index == count else "running",
            "initial_run_id": resume_run,
            "latest_run_id": current_run,
            "next_index": next_index,
            "batch_size": batch_size,
            "binding_baseline_count": count,
            "binding_baseline_sha256": baseline_hash,
            "derived_mapping_file": str(derived_mapping_file) if derived_mapping_file else None,
            "stop_reason": None,
            "completed_batches": completed_batches,
            "formal_fact_eligible": False,
            "prose_write_allowed": False,
            "formal_release_allowed": False,
        }
        _write_state(state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--resume-run", required=True)
    parser.add_argument("--start-index", required=True, type=int)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--derived-mapping-file", help="每个窗口使用的只读、哈希锁定派生定位映射")
    args = parser.parse_args()
    result = batch_continue(args.project_root, args.resume_run, args.start_index, args.batch_size, args.derived_mapping_file)
    print(json.dumps({key: result.get(key) for key in ("status", "latest_run_id", "next_index", "stop_reason")}, ensure_ascii=False))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())