"""ASCII-named wrapper for launching one strict upgrade smoke batch on Windows."""
from __future__ import annotations

import contextlib
import faulthandler
import json
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

import 严格全量资料模型升级 as strict


RUN_ID = "20260817T000000Z-strict-smoke-03"
PARENT_RUN_ID = "20260816T161500Z-strict-micro-retry-02"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    evidence = root / "文档" / "证据" / "全量资料升级运行"
    stdout = evidence / f"{RUN_ID}.stdout.log"
    stderr = evidence / f"{RUN_ID}.stderr.log"
    launcher = evidence / f"{RUN_ID}.launcher.log"
    launcher.write_text(f"started={timestamp()}\n", encoding="utf-8")
    try:
        with stdout.open("w", encoding="utf-8", newline="\n") as out, stderr.open("w", encoding="utf-8", newline="\n") as err:
            faulthandler.enable(file=err)
            watchdog = threading.Timer(120, lambda: faulthandler.dump_traceback(file=err, all_threads=True))
            watchdog.daemon = True
            watchdog.start()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                manifest = strict.run(root, RUN_ID, PARENT_RUN_ID, 5, 5)
                print(json.dumps(manifest, ensure_ascii=False))
            watchdog.cancel()
        launcher.write_text(f"started={timestamp()}\nfinished={timestamp()}; exit_code=0\n", encoding="utf-8")
        return 0
    except Exception:
        with stderr.open("a", encoding="utf-8", newline="\n") as err:
            traceback.print_exc(file=err)
        launcher.write_text(f"started={timestamp()}\nfinished={timestamp()}; exit_code=1\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())