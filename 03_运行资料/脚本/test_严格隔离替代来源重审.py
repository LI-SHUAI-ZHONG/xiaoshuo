from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离替代来源重审 import _audit_row, _canonical_hash


class StrictQuarantineReplacementReauditTests(unittest.TestCase):
    def test_valid_replacement_is_only_a_later_review_candidate(self) -> None:
        source_object = {"id": "replacement-1", "content": "bounded content"}
        digest = _canonical_hash(source_object)
        baseline = {
            "RD-1": {
                "content_object_sha256": digest,
            }
        }
        row = {
            "replacement_draft_id": "RD-1",
            "replacement_source_id": "external-source-1",
            "exact_locator": "https://example.invalid/source#replacement-1",
            "source_object_id": "replacement-1",
            "source_object": source_object,
            "source_object_sha256": digest,
            "source_rights_or_approval": "rights-record-1",
            "scope": "project research only",
            "reviewed_by": "authorized-reviewer",
            "reviewed_at": "2026-08-13T00:00:00Z",
            "review_rationale": "independent bounded source and rights record verified",
        }

        self.assertEqual([], _audit_row(row, baseline, set()))

    def test_mismatched_replacement_object_is_rejected(self) -> None:
        source_object = {"id": "replacement-1", "content": "submitted content"}
        baseline = {
            "RD-1": {
                "content_object_sha256": _canonical_hash({"id": "replacement-1", "content": "expected content"}),
            }
        }
        row = {
            "replacement_draft_id": "RD-1",
            "replacement_source_id": "external-source-1",
            "exact_locator": "https://example.invalid/source#replacement-1",
            "source_object_id": "replacement-1",
            "source_object": source_object,
            "source_object_sha256": _canonical_hash(source_object),
            "source_rights_or_approval": "rights-record-1",
            "scope": "project research only",
            "reviewed_by": "authorized-reviewer",
            "reviewed_at": "2026-08-13T00:00:00Z",
            "review_rationale": "independent bounded source and rights record verified",
        }

        self.assertIn("提交对象哈希与对应草案的有界内容对象不一致", _audit_row(row, baseline, set()))


if __name__ == "__main__":
    unittest.main()