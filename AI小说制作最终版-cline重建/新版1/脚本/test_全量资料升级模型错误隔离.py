from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import 全量资料升级模型错误隔离 as isolate


class ModelErrorIsolationTests(unittest.TestCase):
    def test_isolates_only_existing_model_error_without_model_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "文档" / "证据" / "全量资料升级运行" / "parent"
            parent.mkdir(parents=True)
            parent_manifest = {"run_id": "parent", "parent_run_id": "", "baseline_binding_count": 1,
                               "binding_baseline_sha256": "a" * 64}
            parent_record = {"run_id": "parent", "binding_id": "TB-00008", "terminal_status": "model_error",
                             "automatic_validation": {"errors": ["TimeoutError"]},
                             "model_metadata": {"executed": True}, "original_object_sha256": "b" * 64}
            (parent / "manifest.json").write_text(json.dumps(parent_manifest), encoding="utf-8")
            (parent / "records.jsonl").write_text(json.dumps(parent_record) + "\n", encoding="utf-8")
            manifest = isolate.run(root, "isolated", "parent", "TB-00008")
            record = json.loads((root / "文档" / "证据" / "全量资料升级运行" / "isolated" / "records.jsonl").read_text(encoding="utf-8"))
        self.assertEqual({"quarantined": 1}, manifest["status_counts"])
        self.assertEqual("quarantined", record["terminal_status"])
        self.assertFalse(record["model_metadata"]["executed"])
        self.assertEqual("parent", record["model_metadata"]["isolation_source_run_id"])


if __name__ == "__main__":
    unittest.main()