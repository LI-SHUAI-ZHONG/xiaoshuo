from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("文学审校.py")
SPEC = importlib.util.spec_from_file_location("full_source_literary_review", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiteraryReviewTests(unittest.TestCase):
    def _review(self, decision: dict | list[dict] | None) -> tuple[dict, dict]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"; evidence.mkdir(parents=True)
            row = {"consumption_id": "PC-1", "paragraph_sha256": "current-hash", "quality_status": "semantic_editorial_review_passed", "literary_review_status": "pending_human_literary_review"}
            (evidence / "全量资料正文消费证据.json").write_text(json.dumps({"records": [row]}, ensure_ascii=False), encoding="utf-8")
            decisions = decision if isinstance(decision, list) else [decision] if decision else []
            (evidence / "全量资料文学审校裁决.json").write_text(json.dumps({"decisions": decisions}, ensure_ascii=False), encoding="utf-8")
            report = MODULE.review(root)
            updated = json.loads((evidence / "全量资料正文消费证据.json").read_text(encoding="utf-8"))
            return report, updated["records"][0]

    def test_requires_named_human_decision(self) -> None:
        report, row = self._review(None)
        self.assertEqual("in_progress", report["status"])
        self.assertEqual("pending_human_literary_review", row["literary_review_status"])

    def test_applies_explicit_human_approval_only_after_semantic_pass(self) -> None:
        report, row = self._review({"consumption_id": "PC-1", "paragraph_sha256": "current-hash", "decision": "approved", "reviewer": "editor-1", "rationale": "因果、人物视角与语言均已人工复核。"})
        self.assertEqual("passed", report["status"])
        self.assertEqual("semantic_editorial_review_passed", row["literary_review_status"])
        self.assertFalse(report["formal_release_allowed"])

    def test_rejects_approval_bound_to_superseded_paragraph(self) -> None:
        report, row = self._review({"consumption_id": "PC-1", "paragraph_sha256": "old-hash", "decision": "approved", "reviewer": "editor-1", "rationale": "已人工复核。"})
        self.assertEqual("in_progress", report["status"])
        self.assertEqual("pending_human_literary_review", row["literary_review_status"])
        self.assertEqual("人工文学审校裁决未绑定当前正文段落哈希", row["literary_review"]["reason"])

    def test_duplicate_decisions_block_approval(self) -> None:
        approval = {"consumption_id": "PC-1", "paragraph_sha256": "current-hash", "decision": "approved", "reviewer": "editor-1", "rationale": "已人工复核。"}
        report, row = self._review([approval, approval])
        self.assertEqual("in_progress", report["status"])
        self.assertEqual("pending_human_literary_review", row["literary_review_status"])
        self.assertIn("重复 consumption_id", report["blockers"][0])

    def test_named_hash_bound_rejection_is_retained_for_revision(self) -> None:
        report, row = self._review({"consumption_id": "PC-1", "paragraph_sha256": "current-hash", "decision": "rejected", "reviewer": "editor-1", "rationale": "场景冲突不足，退回重写。"})
        self.assertEqual("in_progress", report["status"])
        self.assertEqual(["PC-1"], report["rejected_consumption_ids"])
        self.assertEqual("pending_human_literary_review", row["literary_review_status"])
        self.assertEqual("rejected", row["literary_review"]["status"])
        self.assertEqual("editor-1", row["literary_review"]["reviewer"])


if __name__ == "__main__":
    unittest.main()