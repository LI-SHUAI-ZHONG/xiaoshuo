"""Write evidence for, then terminate, a non-progressing strict smoke process."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROCESS_ID = 25788
RUN_ID = "20260817T000000Z-strict-smoke-03"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def exists(pid: int) -> bool:
    return subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, check=False).stdout.strip() != "INFO: No tasks are running which match the specified criteria."


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    evidence = root / "文档" / "证据" / "全量资料升级运行"
    anomaly = {
        "recorded_at": now(),
        "run_id": RUN_ID,
        "process_id": PROCESS_ID,
        "reason": "no progress after baseline-lock phase; no run artifact or active Ollama model",
        "process_exists_before_termination": exists(PROCESS_ID),
        "action": "taskkill /PID 25788 /F",
    }
    (evidence / f"{RUN_ID}.execution-anomaly.json").write_text(json.dumps(anomaly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if anomaly["process_exists_before_termination"]:
        subprocess.run(["taskkill", "/PID", str(PROCESS_ID), "/F"], check=True, capture_output=True, text=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())