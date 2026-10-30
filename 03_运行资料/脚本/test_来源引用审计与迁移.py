from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 来源引用审计与迁移 import audit_and_migrate


class SourceReferenceMigrationTests(unittest.TestCase):
    def test_migrates_lines_to_deduplicated_source_refs_and_keeps_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            (root / "原始资料/类型系统.txt").write_text("SOURCE: one.json\na\nb\nSOURCE: two.json\nc\nd\n", encoding="utf-8")
            selection = {"selected_type_profiles": {"甲": {"source_ref": {"file": "原始资料/类型系统.txt", "matched_lines": [2, 3, 4, 4]}}}}
            path = root / "文档/证据/小说资料选择清单.json"
            path.write_text(json.dumps(selection, ensure_ascii=False), encoding="utf-8")
            report = audit_and_migrate(root)
            self.assertEqual("passed", report["status"])
            migrated = json.loads(path.read_text(encoding="utf-8"))["selected_type_profiles"]["甲"]["source_ref"]
            self.assertEqual(["原始资料/类型系统.txt:SOURCE[1]", "原始资料/类型系统.txt:SOURCE[2]"], migrated["source_refs"])
            self.assertEqual([2, 3, 4, 4], migrated["legacy_matched_lines"])

    def test_quarantines_out_of_range_lines_without_modifying_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            (root / "原始资料/类型系统.txt").write_text("SOURCE: one.json\na\n", encoding="utf-8")
            original = {"selected_type_profiles": {"甲": {"source_ref": {"matched_lines": [99]}}}}
            path = root / "文档/证据/小说资料选择清单.json"
            path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
            report = audit_and_migrate(root)
            self.assertEqual("quarantined", report["status"])
            self.assertEqual(original, json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()