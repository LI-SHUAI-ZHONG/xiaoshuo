"""Regression tests for material-only full-batch verification."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("派生资料批次回归.py")
SPEC = importlib.util.spec_from_file_location("derived_batch_regression", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MODULE.RUN_ID = "test-run"


class DerivedBatchRegressionTests(unittest.TestCase):
    def _root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        run = root / "文档" / "证据" / "全量资料升级运行" / "test-run"
        run.mkdir(parents=True)
        manifest = {"run_id": "test-run", "contract_status": "passed", "audit_state": "completed", "complete_full_run": True,
                    "prose_write_allowed": False, "formal_release_allowed": False, "baseline_binding_count": 2,
                    "status_counts": {"validated_candidate": 1, "quarantined": 1}}
        (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        rows = [{"binding_id": "B1", "terminal_status": "validated_candidate", "original_object_sha256": "a" * 64},
                {"binding_id": "B2", "terminal_status": "quarantined", "original_object_sha256": "b" * 64}]
        (run / "records.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return root

    def test_valid_full_batch_passes_without_creating_or_reading_prose(self) -> None:
        root = self._root()
        report = MODULE.run(root)
        self.assertEqual("passed", report["quality_status"])
        self.assertEqual(1, report["counts"]["chain_quarantined"])
        self.assertFalse((root / "正文").exists())

    def test_hashless_record_blocks_batch(self) -> None:
        root = self._root()
        path = root / "文档" / "证据" / "全量资料升级运行" / "test-run" / "records.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[0]["original_object_sha256"] = ""
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        report = MODULE.run(root)
        self.assertEqual("blocked", report["quality_status"])
        self.assertIn("缺少 64 位原始对象哈希", report["errors"][0])

    def test_quarantined_unresolved_object_requires_an_error_but_not_a_hash(self) -> None:
        root = self._root()
        path = root / "文档" / "证据" / "全量资料升级运行" / "test-run" / "records.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[1]["original_object_sha256"] = None
        rows[1]["original_object"] = None
        rows[1]["errors"] = ["source_ref 无法解析"]
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        self.assertEqual("passed", MODULE.run(root)["quality_status"])

    def test_quarantined_unresolved_object_without_error_blocks_batch(self) -> None:
        root = self._root()
        path = root / "文档" / "证据" / "全量资料升级运行" / "test-run" / "records.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[1]["original_object_sha256"] = None
        rows[1]["original_object"] = None
        rows[1]["errors"] = []
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        self.assertEqual("blocked", MODULE.run(root)["quality_status"])

    def test_nested_derived_object_hash_is_accepted(self) -> None:
        root = self._root()
        path = root / "文档" / "证据" / "全量资料升级运行" / "test-run" / "records.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[0].pop("original_object_sha256")
        rows[0]["original_object"] = {"derived_original_object_sha256": "a" * 64}
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        self.assertEqual("passed", MODULE.run(root)["quality_status"])

    def test_mapped_derived_object_hash_is_accepted(self) -> None:
        root = self._root()
        path = root / "文档" / "证据" / "全量资料升级运行" / "test-run" / "records.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[0].pop("original_object_sha256")
        rows[0]["source_ref"] = {"derived_mapping": {"derived_original_object_sha256": "a" * 64}}
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        self.assertEqual("passed", MODULE.run(root)["quality_status"])

    def test_snapshot_does_not_require_its_parent_chain(self) -> None:
        root = self._root()
        manifest_path = root / "文档" / "证据" / "全量资料升级运行" / "test-run" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["records_mode"] = "snapshot"
        manifest["parent_run_id"] = "missing-parent"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual("passed", MODULE.run(root)["quality_status"])


if __name__ == "__main__":
    unittest.main()