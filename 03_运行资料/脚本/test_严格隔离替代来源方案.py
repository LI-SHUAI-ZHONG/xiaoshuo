from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离替代来源方案 import _draft


class StrictQuarantineReplacementSourcePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.route = {
            "upgrade_id": "SU-1", "consumption_id": "PC-1", "binding_id": "TB-1", "source_kind": "类型连接",
            "source_id": "legacy:1", "historical_source_ref": "原始资料/类型连接.txt:items[1]",
            "historical_source_ref_sha256": "a" * 64, "content_object_sha256": "b" * 64,
            "disposition": "candidate_content_mapping_requires_independent_confirmation",
        }

    def test_bounded_candidate_gets_administrative_draft_id_but_no_eligibility(self) -> None:
        draft = _draft(self.route, {"status": "candidate", "value": 1}, None)
        self.assertEqual("RSD-" + "B" * 16, draft["replacement_draft_id"])
        self.assertEqual(["status", "value"], draft["content_field_signature"])
        self.assertIsNone(draft["required_submission"]["source_object_id"])
        self.assertFalse(draft["formal_fact_eligible"])

    def test_unbounded_record_has_no_derived_id(self) -> None:
        self.route["disposition"] = "replacement_source_required"
        self.route["content_object_sha256"] = None
        draft = _draft(self.route, None, "unresolved")
        self.assertIsNone(draft["replacement_draft_id"])
        self.assertEqual("replacement_required_without_recoverable_boundary", draft["draft_kind"])


if __name__ == "__main__":
    unittest.main()