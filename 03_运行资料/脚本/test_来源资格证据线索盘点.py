from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("来源资格证据线索盘点.py")
SPEC = importlib.util.spec_from_file_location("source_qualification_clues", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceQualificationClueTests(unittest.TestCase):
    def _root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "原始资料").mkdir()
        source = root / "原始资料" / "动态网络.txt"
        source.write_text("source material\n", encoding="utf-8")
        record = {"source_kind": "动态网络", "source_file": "动态网络.txt", "input_snapshot_sha256": MODULE._sha256(source), "evidence_package": {"evidence": [{"name": "input_snapshot", "value": {"path": "原始资料/动态网络.txt", "sha256": MODULE._sha256(source)}}]}}
        assessment = root / "文档/证据/严格资料升级/模型辅助来源资格评估"
        assessment.mkdir(parents=True)
        (assessment / "模型辅助来源资格评估清单.jsonl").write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
        return root

    def test_local_snapshot_is_not_qualification_evidence(self) -> None:
        root = self._root()
        report = MODULE.build(root)
        self.assertEqual(1, report["source_kind_count"])
        self.assertEqual(0, report["qualification_sufficient_evidence_field_count"])
        output = root / "文档/证据/严格资料升级/模型辅助来源资格评估/来源资格人工裁决/来源资格证据线索/来源资格证据线索清单.jsonl"
        row = json.loads(output.read_text(encoding="utf-8").strip())
        self.assertTrue(row["observed_metadata"]["local_snapshot"]["hash_matches_model_review_input"])
        self.assertFalse(row["evidence_field_clues"]["origin_locator"]["qualification_sufficient"])
        self.assertIsNone(row["evidence_field_clues"]["responsible_party"]["value"])

    def test_hash_drift_is_reported_without_permission_change(self) -> None:
        root = self._root()
        (root / "原始资料" / "动态网络.txt").write_text("changed\n", encoding="utf-8")
        MODULE.build(root)
        output = root / "文档/证据/严格资料升级/模型辅助来源资格评估/来源资格人工裁决/来源资格证据线索/来源资格证据线索清单.jsonl"
        row = json.loads(output.read_text(encoding="utf-8").strip())
        self.assertFalse(row["observed_metadata"]["local_snapshot"]["hash_matches_model_review_input"])
        self.assertFalse(row["prose_write_allowed"])


if __name__ == "__main__":
    unittest.main()