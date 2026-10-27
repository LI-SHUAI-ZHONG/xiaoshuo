from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("升级成果追溯审计.py")
SPEC = importlib.util.spec_from_file_location("trace_audit", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpgradeArtifactTraceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence = self.root / "文档" / "证据"
        self.evidence.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_separates_revisions_from_advisory_and_runtime_evidence(self) -> None:
        rows = [
            {"upgrade_id": "UPG-1", "binding_id": "TB-1", "source_id": "S-1", "upgraded_content": "升级后资料"},
            {"candidate_id": "MIC-TB-2", "binding_id": "TB-2", "model_assessment": {"suggested_revision": "人工复核建议"}},
            {"consumption_id": "C-3", "binding_id": "TB-3", "upgrade": {"causal_contract": {"trigger": "触发"}}},
            {"upgrade_id": "UPG-4", "binding_id": "TB-4", "status": "upgraded_for_draft_audit"},
        ]
        (self.evidence / "升级记录.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        report = MODULE.audit(self.root)
        self.assertEqual(0, report["recoverable_material_revision_count"])
        self.assertEqual(1, report["advisory_material_revision_count"])
        self.assertEqual("regenerate_structured_material_revisions", report["next_route"])
        recovered = (self.evidence / "升级成果追溯审计" / "可融合升级成果.jsonl").read_text(encoding="utf-8")
        self.assertEqual("", recovered)
        missing = (self.evidence / "升级成果追溯审计" / "升级成果缺失清单.jsonl").read_text(encoding="utf-8")
        self.assertIn("creative_contract_only", missing)
        self.assertIn("audit_metadata_only", missing)


if __name__ == "__main__":
    unittest.main()