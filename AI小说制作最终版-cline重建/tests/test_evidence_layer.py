# -*- coding: utf-8 -*-
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "工具"))
from 资料证据层 import build_evidence_bundle, validate_handoff


class EvidenceLayerTests(unittest.TestCase):
    def test_bundle_has_content_location_and_hash(self):
        bundle = build_evidence_bundle(ROOT, "小说，静态网络 动态网络 锚点网络", limit=40)
        self.assertTrue(bundle["usable_evidence_ids"])
        for item in bundle["evidence"][:10]:
            self.assertTrue(item["source_path"])
            self.assertTrue(item["source_sha256"])
            self.assertTrue(item.get("line_start") or item.get("record_index") is not None)
            self.assertTrue(item.get("text") or item.get("record"))

    def test_missing_handoff_is_detected(self):
        bundle = build_evidence_bundle(ROOT, "小说，悬疑", limit=10)
        self.assertEqual(validate_handoff(bundle, ["E-NOT-REAL"]), ["E-NOT-REAL"])

    def test_candidate_records_are_not_runtime_usable(self):
        bundle = build_evidence_bundle(ROOT, "小说，动态网络", limit=120)
        candidates = [item for item in bundle["evidence"] if item["status"] == "candidate"]
        self.assertTrue(candidates)
        self.assertTrue(all(not item["runtime_usable"] for item in candidates))


if __name__ == "__main__":
    unittest.main()