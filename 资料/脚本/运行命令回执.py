"""Run Windows verification commands one at a time with durable receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 运行清单复核 import finalize_run, initialize_run, register_artifact


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def execute(project_root: str | Path, run_id: str, commands: list[str], *, stage: str = "verification") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    initialize_run(root, run_id)
    command_dir = root / "文档" / "证据" / "运行" / run_id / "command_logs"
    command_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, command in enumerate(commands, 1):
        started_at = _now()
        completed = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, encoding="utf-8", errors="replace")
        log = command_dir / f"{index:02d}_{stage}.log"
        log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        register_artifact(root, run_id, log, kind="command_log", module_id=stage, status="passed" if completed.returncode == 0 else "failed", exit_code=completed.returncode)
        records.append({"command": command, "started_at": started_at, "finished_at": _now(), "exit_code": completed.returncode, "relative_log_path": str(log.relative_to(root)).replace("\\", "/"), "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
        if completed.returncode != 0:
            finalize_run(root, run_id, status="failed", exit_code=completed.returncode, failed_stage=stage, cleanup_actions=["未继续执行后续验证命令"])
            return {"status": "failed", "run_id": run_id, "records": records}
    finalize_run(root, run_id, status="passed", exit_code=0)
    return {"status": "passed", "run_id": run_id, "records": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", default="verification")
    parser.add_argument("--command", action="append", required=True)
    args = parser.parse_args()
    report = execute(args.project_root, args.run_id, args.command, stage=args.stage)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())