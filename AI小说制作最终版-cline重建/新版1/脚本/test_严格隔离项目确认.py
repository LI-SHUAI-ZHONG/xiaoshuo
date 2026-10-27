from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离项目确认 import SCHEMA_VERSION, _audit_row


class StrictQuarantineProjectConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = {
            "SU-1": {"source_id": "SRC-1", "source_object_id": "SRC-1", "exact_locator": "原始资料/a.txt:SOURCE[1]", "source_ref_sha256": "a" * 64, "source_object_sha256": "b" * 64},
        }
        self.row = {
            "schema_version": SCHEMA_VERSION, "upgrade_id": "SU-1", "source_id": "SRC-1", "source_object_id": "SRC-1",
            "exact_locator": "原始资料/a.txt:SOURCE[1]", "source_ref_sha256": "a" * 64, "source_object_sha256": "b" * 64,
            "intended_scope": "本项目事实核验", "decision": "approved", "approved_by": "审核人",
            "approved_at": "2026-08-13T00:00:00Z", "decision_rationale": "已人工核对来源对象和适用范围。",
        }

    def test_valid_explicit_approval_is_accepted_only_for_later_reaudit(self) -> None:
        self.assertEqual([], _audit_row(self.row, self.expected, set()))

    def test_rejects_mutable_locator(self) -> None:
        self.row["exact_locator"] = "原始资料/a.txt:SOURCE[2]"
        self.assertIn("不可变绑定不匹配: exact_locator", _audit_row(self.row, self.expected, set()))

    def test_rejects_hash_mismatch(self) -> None:
        self.row["source_object_sha256"] = "c" * 64
        self.assertIn("不可变绑定不匹配: source_object_sha256", _audit_row(self.row, self.expected, set()))

    def test_rejects_unconfirmable_identity_missing_record(self) -> None:
        self.row["upgrade_id"] = "SU-NOT-QUEUED"
        self.assertIn("upgrade_id 不在可确认队列中，可能属于未批准状态或缺少身份链接的隔离项", _audit_row(self.row, self.expected, set()))


if __name__ == "__main__":
    unittest.main()