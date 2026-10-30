from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离内容分流 import _route


class StrictQuarantineContentRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = {
            "category_id": "candidate_identity_missing", "upgrade_id": "SU-1", "consumption_id": "PC-1", "binding_id": "TB-1",
            "source_id": "legacy.json:1", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:类型静态搭配库.json[1]",
            "source_ref_sha256": "a" * 64, "source_item_sha256": "b" * 64,
        }

    def test_bounded_content_object_creates_confirmation_candidate_without_admission(self) -> None:
        route = _route(self.record, {"dynamic_combination_id": "DYNAMIC-1", "status": "candidate"}, None)
        self.assertEqual("candidate_content_mapping_requires_independent_confirmation", route["disposition"])
        self.assertEqual("DYNAMIC-1", route["candidate_replacement_object_id"])
        self.assertFalse(route["formal_fact_eligible"])
        self.assertFalse(route["prose_write_allowed"])

    def test_unbounded_or_unresolved_content_requires_replacement(self) -> None:
        self.record["category_id"] = "object_boundary_missing"
        route = _route(self.record, None, "source_ref 不具备可精确回读的受控定位格式")
        self.assertEqual("replacement_source_required", route["disposition"])
        self.assertIsNone(route["candidate_replacement_object_id"])
        self.assertFalse(route["formal_fact_eligible"])


if __name__ == "__main__":
    unittest.main()