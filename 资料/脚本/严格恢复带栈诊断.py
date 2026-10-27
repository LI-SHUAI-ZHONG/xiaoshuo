"""Execute the strict upgrader while persisting a delayed traceback for startup hangs."""
from __future__ import annotations

import faulthandler
import runpy
import sys
from pathlib import Path


ROOT = Path(r"D:\小说")


def main() -> None:
    evidence = ROOT / "文档" / "证据" / "全量资料升级运行"
    marker = evidence / "strict-recovery-startup-marker.log"
    marker.write_text("wrapper_entered\n", encoding="utf-8")
    with (evidence / "strict-recovery-startup-trace.log").open("w", encoding="utf-8") as trace:
        faulthandler.dump_traceback_later(10, repeat=True, file=trace)
        try:
            marker.write_text("before_runpy\n", encoding="utf-8")
            sys.argv[0] = str(ROOT / "脚本" / "严格全量资料模型升级.py")
            runpy.run_path(sys.argv[0], run_name="__main__")
        finally:
            marker.write_text("runpy_finished\n", encoding="utf-8")
            faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    main()