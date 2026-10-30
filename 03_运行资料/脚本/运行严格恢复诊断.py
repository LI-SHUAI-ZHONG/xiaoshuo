"""Start a detached strict recovery with an argument vector and persistent logs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(r"D:\小说")
RUN_ID = "20260817T052000Z-strict-tb00008-recovery-13"


def main() -> int:
    evidence = ROOT / "文档" / "证据" / "全量资料升级运行"
    command = [
        sys.executable, str(ROOT / "脚本" / "严格全量资料模型升级.py"),
        "--project-root", str(ROOT), "--run-id", RUN_ID,
        "--parent-run-id", "20260817T000000Z-strict-smoke-03",
        "--start", "5", "--limit", "5",
        "--baseline-binding-count", "13345",
        "--binding-baseline-sha256", "c8703fc16ffe0bf083d5bf34041fb97763e0a3625ad01e73826ae5bacf564f6d",
    ]
    stdout_path = evidence / f"{RUN_ID}.launcher.stdout.log"
    stderr_path = evidence / f"{RUN_ID}.launcher.stderr.log"
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    (evidence / f"{RUN_ID}.launcher.json").write_text(
        "{\n"
        f'  "run_id": "{RUN_ID}",\n'
        f'  "pid": {process.pid},\n'
        '  "launch_mode": "detached_argument_vector"\n'
        "}\n", encoding="utf-8")
    print(process.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())