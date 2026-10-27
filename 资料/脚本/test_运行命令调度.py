from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from 运行命令调度 import execute_commands
from 运行清单复核 import verify_manifest


class CommandExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_failed_command_preserves_exit_code_and_stops_sequence(self) -> None:
        result = execute_commands(self.root, "run-command-failure", ["exit /b 7", "echo must-not-run"])

        output_path = self.root / "文档" / "证据" / "运行" / "run-command-failure" / "command_execution.json"
        persisted = json.loads(output_path.read_text(encoding="utf-8"))
        report = verify_manifest(self.root, "run-command-failure", required_kinds={"command_log", "failure_receipt"})
        self.assertEqual(7, result["exit_code"])
        self.assertEqual(1, result["executed_command_count"])
        self.assertEqual(7, persisted["commands"][0]["exit_code"])
        self.assertEqual("failed", report["manifest"]["run_status"])
        self.assertEqual(7, report["manifest"]["exit_code"])

    def test_successful_commands_keep_zero_exit_code(self) -> None:
        result = execute_commands(self.root, "run-command-success", ["echo first", "echo second"])

        report = verify_manifest(self.root, "run-command-success", required_kinds={"command_log"})
        self.assertEqual(0, result["exit_code"])
        self.assertEqual(2, result["executed_command_count"])
        self.assertTrue(report["passed"])
        self.assertEqual("passed", report["manifest"]["run_status"])