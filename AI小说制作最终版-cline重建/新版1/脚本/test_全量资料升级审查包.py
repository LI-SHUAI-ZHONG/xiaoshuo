from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("全量资料升级审查包.py")
SPEC = importlib.util.spec_from_file_location("upgrade_review_package", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class UpgradeReviewPackageTests(unittest.TestCase):
    def test_keeps_candidates_and_quarantine_out_of_fact_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); evidence = root / "文档" / "证据"; evidence.mkdir(parents=True)
            rows = [
                {"binding_id": "TB-1", "consumption_id": "A", "upgrade": {"application_status": "automatic_draft_requires_semantic_editorial_review", "literary_review_status": "pending_human_literary_review"}},
                {"binding_id": "TB-1", "consumption_id": "B", "upgrade": {"application_status": "automatic_draft_requires_semantic_editorial_review", "literary_review_status": "pending_human_literary_review"}},
            ]
            (evidence / "全量资料升级档案.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            (evidence / "全绑定来源完整性审计报告.json").write_text(json.dumps({"quarantined_findings": [{"binding_id": "TB-2", "errors": ["缺少稳定标识"]}]}, ensure_ascii=False), encoding="utf-8")
            output = MODULE.build_review_package(root, "review")
            overview = json.loads((output / "审查总览.json").read_text(encoding="utf-8"))
            template = json.loads((output / "正式事实变更集模板.json").read_text(encoding="utf-8"))
            self.assertEqual(1, overview["duplicate_group_count"])
            self.assertEqual(1, overview["quarantined_binding_count"])
            self.assertFalse(overview["all_archive_records_fact_merge_eligible"])
            self.assertEqual([], template["changes"])


if __name__ == "__main__":
    unittest.main()