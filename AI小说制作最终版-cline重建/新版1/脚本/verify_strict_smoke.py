"""Run compile, unit, and parent-chain preflight checks with auditable output."""
from __future__ import annotations

import json
import py_compile
import unittest
from pathlib import Path

import 严格全量资料模型升级 as strict
import 严格全量资料连续编排 as continuous


PARENT_RUN_ID = "20260817T000000Z-strict-smoke-03"


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    scripts = root / "脚本"
    evidence = root / "文档" / "证据" / "全量资料升级运行"
    report_path = evidence / "20260817T000000Z-strict-smoke-03.verification.json"
    try:
        for name in ("严格全量资料模型升级.py", "严格全量资料连续编排.py", "run_strict_smoke.py"):
            py_compile.compile(scripts / name, doraise=True)
        suite = unittest.defaultTestLoader.discover(str(scripts), pattern="test_严格全量资料连续编排.py")
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not result.wasSuccessful():
            raise RuntimeError(f"连续编排单元测试失败: {len(result.failures)} failures, {len(result.errors)} errors")
        bindings = continuous.load_bindings(root)
        completed = strict.chain_records(root, PARENT_RUN_ID)
        pending = continuous.pending_indexes(bindings, completed)
        start, count = continuous.next_window(pending, 10)
        report = {
            "compiled": True,
            "unit_tests": result.testsRun,
            "baseline": len(bindings),
            "completed": len(completed),
            "next_window": {"start": start, "count": count},
            "first_pending_id": bindings[start]["binding_id"],
            "parent_run_id": PARENT_RUN_ID,
            "formal_fact_eligible": False,
            "prose_write_allowed": False,
            "formal_release_allowed": False,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    except Exception as error:
        report_path.write_text(json.dumps({"passed": False, "error": f"{type(error).__name__}: {error}"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())