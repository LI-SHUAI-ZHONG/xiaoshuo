"""Run every current test file directly and persist rebuildable regression evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 运行清单复核 import initialize_run, register_artifact


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_regression(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id 必须是单个安全目录名")
    initialize_run(root, run_id)
    started_at = _now()
    output_dir = root / "文档" / "证据" / "测试与回归日志" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    test_files = sorted((root / "脚本").glob("test_*.py"))
    results: list[dict[str, Any]] = []
    for index, test_file in enumerate(test_files, start=1):
        completed = subprocess.run(
            [sys.executable, str(test_file), "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        log_path = output_dir / f"{index:03d}_{test_file.stem}.log"
        log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        output = completed.stdout + completed.stderr
        match = re.search(r"Ran (\d+) tests?", output)
        results.append({
            "index": index,
            "test_file": str(test_file.relative_to(root)).replace("\\", "/"),
            "command": [sys.executable, str(test_file), "-q"],
            "exit_code": completed.returncode,
            "status": "passed" if completed.returncode == 0 else "failed",
            "tests_run": int(match.group(1)) if match else None,
            "log_relative_path": str(log_path.relative_to(root)).replace("\\", "/"),
            "log_sha256": _sha256(log_path),
        })
    summary = {
        "schema_version": "current-source-regression-1.0",
        "run_id": run_id,
        "project_root": str(root),
        "python": sys.executable,
        "python_version": sys.version,
        "started_at": started_at,
        "test_file_count": len(results),
        "passed_file_count": sum(row["exit_code"] == 0 for row in results),
        "failed_file_count": sum(row["exit_code"] != 0 for row in results),
        "total_tests_reported": sum(row["tests_run"] or 0 for row in results),
        "results": results,
        "completed_at": _now(),
    }
    summary_path = output_dir / "regression_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_sha256"] = _sha256(summary_path)
    register_artifact(root, run_id, summary_path, kind="regression_summary", status="success", exit_code=0)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="逐文件执行当前源码测试并保存回归证据")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    summary = run_regression(args.project_root, args.run_id)
    print(json.dumps({key: summary[key] for key in (
        "run_id", "test_file_count", "passed_file_count", "failed_file_count", "total_tests_reported", "summary_sha256"
    )}, ensure_ascii=False))
    return 0 if summary["failed_file_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())