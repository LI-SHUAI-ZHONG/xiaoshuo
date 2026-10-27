"""Run Windows verification commands individually and persist their real exit codes."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 运行清单复核 import (
    finalize_run,
    initialize_run,
    register_artifact,
    register_command_execution,
    write_failure_receipt,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute_commands(project_root: str | Path, run_id: str, commands: list[str]) -> dict[str, Any]:
    """Execute commands in order; a failed command prevents later commands from running."""
    root = Path(project_root).expanduser().resolve()
    if not commands:
        raise ValueError("至少需要一条 --command")
    initialize_run(root, run_id)
    run_dir = root / "文档" / "证据" / "运行" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        started_at = _now()
        completed = subprocess.run(
            ["cmd", "/d", "/s", "/c", command],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        record = {
            "index": index,
            "command": command,
            "started_at": started_at,
            "completed_at": _now(),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "status": "success" if completed.returncode == 0 else "failed",
        }
        records.append(record)
        if completed.returncode != 0:
            break
    result = {
        "schema_version": "command-execution-1.0",
        "run_id": run_id,
        "project_root": str(root),
        "commands": records,
        "requested_command_count": len(commands),
        "executed_command_count": len(records),
        "status": "passed" if len(records) == len(commands) and all(row["exit_code"] == 0 for row in records) else "failed",
        "exit_code": next((row["exit_code"] for row in records if row["exit_code"] != 0), 0),
        "completed_at": _now(),
    }
    output_path = run_dir / "command_execution.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_command_execution(root, run_id, records)
    register_artifact(root, run_id, output_path, kind="command_log", status="success", exit_code=0)
    if result["exit_code"]:
        write_failure_receipt(
            root, run_id, status="failed", failed_stage="command_execution", exit_code=result["exit_code"],
            errors=[f"命令 {records[-1]['index']} 退出码为 {result['exit_code']}"],
            cleanup_actions=["后续验证命令未执行", "未授予正式交付资格"],
        )
    else:
        finalize_run(root, run_id, status="passed", exit_code=0)
    result["sha256"] = _sha256(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="逐条执行 Windows 验证命令并保留真实退出码")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--command", action="append", required=True)
    args = parser.parse_args()
    result = execute_commands(args.project_root, args.run_id, args.command)
    print(json.dumps(result, ensure_ascii=False))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())