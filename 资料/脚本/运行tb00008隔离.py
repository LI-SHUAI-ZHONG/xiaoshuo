"""Start the terminal TB-00008 model-error isolation without shell quoting."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(r"D:\小说")
RUN_ID = "20260817T054000Z-strict-tb00008-isolated-01"


def main() -> int:
    evidence = ROOT / "文档" / "证据" / "全量资料升级运行"
    command = [sys.executable, str(ROOT / "脚本" / "全量资料升级模型错误隔离.py"),
               "--project-root", str(ROOT), "--run-id", RUN_ID,
               "--parent-run-id", "20260817T052000Z-strict-tb00008-recovery-13", "--binding-id", "TB-00008"]
    with (evidence / f"{RUN_ID}.isolation.stdout.log").open("w", encoding="utf-8") as stdout, \
            (evidence / f"{RUN_ID}.isolation.stderr.log").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    (evidence / f"{RUN_ID}.isolation-launch.json").write_text(
        f'{{"run_id":"{RUN_ID}","pid":{process.pid},"launch_mode":"detached_argument_vector"}}\n', encoding="utf-8")
    print(process.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())