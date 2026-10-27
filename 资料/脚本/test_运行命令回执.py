from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("运行命令回执.py")
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("command_receipts", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CommandReceiptTests(unittest.TestCase):
    def test_failure_stops_later_commands_and_preserves_actual_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = MODULE.execute(root, "run-test", ['py -c "import sys; sys.exit(7)"', 'py -c "raise SystemExit(0)"'])
            self.assertEqual("failed", report["status"])
            self.assertEqual(7, report["records"][0]["exit_code"])
            self.assertEqual(1, len(report["records"]))
            manifest = json.loads((root / "文档" / "证据" / "运行" / "run-test" / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("failed", manifest["run_status"])
            self.assertEqual(7, manifest["exit_code"])

    def test_success_has_one_hashed_log_per_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = MODULE.execute(root, "run-test", ['py -c "print(1)"', 'py -c "print(2)"'])
            self.assertEqual("passed", report["status"])
            self.assertEqual(2, len(report["records"]))
            self.assertTrue(all(len(row["log_sha256"]) == 64 for row in report["records"]))


if __name__ == "__main__":
    unittest.main()