"""Tests for metadata-only derived-material failure isolation."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("派生资料失败样本隔离.py")
SPEC = importlib.util.spec_from_file_location("derived_failure_isolation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MODULE.RUN_ID = "test-run"


class FailureSampleIsolationTests(unittest.TestCase):
    def _root(self, quality_status: str = "blocked") -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        evidence = root / "文档" / "证据"
        evidence.mkdir(parents=True)
        record = {"consumption_id": "C1", "binding_id": "B1", "quality_status": quality_status,
                  "release_status": "draft_only", "source_id": "source", "paragraph": "must not be retained"}
        document = {"run_id": "test-run", "release_status": "draft_only", "records": [record]}
        (evidence / "派生资料正文消费证据.json").write_text(json.dumps(document), encoding="utf-8")
        return root

    def test_blocked_source_metadata_is_isolated_without_paragraph(self) -> None:
        report = MODULE.run(self._root())
        self.assertEqual("blocked", report["quality_status"])
        sample = report["failure_samples"][0]
        self.assertIn("blocked_consumption", sample["isolation_reasons"])
        self.assertIn("source_metadata_field:source_id", sample["isolation_reasons"])
        self.assertNotIn("paragraph", sample)
        self.assertNotIn("must not be retained", json.dumps(report))

    def test_clean_draft_record_without_source_metadata_passes(self) -> None:
        root = self._root(quality_status="passed_for_draft_only")
        path = root / "文档" / "证据" / "派生资料正文消费证据.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["records"][0].pop("source_id")
        path.write_text(json.dumps(document), encoding="utf-8")
        report = MODULE.run(root)
        self.assertEqual("passed", report["quality_status"])
        self.assertEqual([], report["failure_samples"])


if __name__ == "__main__":
    unittest.main()