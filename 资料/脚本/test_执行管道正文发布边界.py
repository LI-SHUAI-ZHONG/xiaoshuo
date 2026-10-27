from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("执行管道.py")
SPEC = importlib.util.spec_from_file_location("execution_pipeline_release_boundary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExecutionPipelineReleaseBoundaryTests(unittest.TestCase):
    def _run(self, root: Path, *, failed: bool, approved: bool) -> dict:
        MODULE.PROJECT_ROOT = root
        MODULE.ROOT = root
        MODULE.EVIDENCE = root / "文档" / "证据"
        MODULE.RUN_ID = "run-test-27a"
        MODULE.RUN_EVIDENCE_DIR = MODULE.EVIDENCE / "运行" / MODULE.RUN_ID
        MODULE.OUTPUT_DIR = MODULE.RUN_EVIDENCE_DIR / "module_outputs"
        MODULE.CONSUMPTION = MODULE.RUN_EVIDENCE_DIR / "执行消费.jsonl"
        MODULE.RUN_EVIDENCE_DIR.mkdir(parents=True)
        evidence_file = MODULE.RUN_EVIDENCE_DIR / "evidence.json"
        evidence_file.write_text("{}", encoding="utf-8")
        outputs = {
            f"{number:02d}": {"status": "failed" if failed and number == 9 else "success", "output_files": [str(evidence_file)]}
            for number in range(1, 11)
        }
        final = {
            "status": "success",
            "formal_delivery_status": "approved" if approved else "blocked",
            "formal_release": {
                "status": "approved" if approved else "blocked",
                "formal_release_allowed": approved,
                "delivery_ready": approved,
                "blockers": [] if approved else ["正式审批未通过"],
            },
        }
        return MODULE.execute_11({"module_outputs": outputs, "module_10_output": final})[0]

    def test_blocked_run_writes_only_blocked_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self._run(root, failed=True, approved=False)
            run_dir = root / "文档" / "证据" / "运行" / "run-test-27a"
            blocked = run_dir / "chapter_publication_blocked.json"
            self.assertEqual("blocked", result["release_decision"])
            self.assertTrue(blocked.is_file())
            self.assertFalse((run_dir / "chapter_publication.json").exists())
            self.assertFalse(json.loads(blocked.read_text(encoding="utf-8"))["formal_prose_written"])

    def test_approved_run_writes_released_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self._run(root, failed=False, approved=True)
            run_dir = root / "文档" / "证据" / "运行" / "run-test-27a"
            self.assertEqual("released", result["release_decision"])
            self.assertTrue((run_dir / "chapter_publication.json").is_file())
            self.assertFalse((run_dir / "chapter_publication_blocked.json").exists())


if __name__ == "__main__":
    unittest.main()