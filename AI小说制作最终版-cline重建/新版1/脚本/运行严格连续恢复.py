"""Start the resumable strict continuous campaign from the quarantined TB-00008 chain."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(r"D:\AI小说制作最终版-cline重建\新版1")
CAMPAIGN_ID = "20260817T070000Z-strict-resume-from-tb00011"
PARENT_RUN_ID = "20260817T054000Z-strict-tb00008-isolated-01"


def main() -> int:
    evidence = ROOT / "文档" / "证据" / "全量资料升级运行"
    command = [sys.executable, str(ROOT / "脚本" / "严格全量资料连续编排.py"),
               "--project-root", str(ROOT), "--campaign-id", CAMPAIGN_ID,
               "--parent-run-id", PARENT_RUN_ID, "--batch-size", "5", "--sleep-seconds", "0.1",
               "--resume-start", "10"]
    with (evidence / f"{CAMPAIGN_ID}.launcher.stdout.log").open("w", encoding="utf-8") as stdout, \
            (evidence / f"{CAMPAIGN_ID}.launcher.stderr.log").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    (evidence / f"{CAMPAIGN_ID}.launcher.json").write_text(
        f'{{"campaign_id":"{CAMPAIGN_ID}","parent_run_id":"{PARENT_RUN_ID}","pid":{process.pid},'
        '"launch_mode":"detached_argument_vector"}\n', encoding="utf-8")
    print(process.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())