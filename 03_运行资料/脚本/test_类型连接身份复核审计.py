from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 类型连接身份复核审计 import audit


class TypeConnectionIdentityReviewTests(unittest.TestCase):
    def test_requires_exact_intrinsic_id_match_and_never_allows_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            (root / "原始资料/类型连接.txt").write_text(
                "SOURCE: 类型动态搭配库.json\n===\n[{\"dynamic_combination_id\": \"D-1\"}, {\"dynamic_combination_id\": \"D-2\"}]\n",
                encoding="utf-8",
            )
            records = [
                {"binding_id": "B-1", "source_id": "D-1", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:类型动态搭配库.json[1]"},
                {"binding_id": "B-2", "source_id": "wrong", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:类型动态搭配库.json[2]"},
            ]
            (root / "文档/证据/全量资料解释词创作绑定.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")
            report = audit(root)
            self.assertEqual({"identity_verified": 1, "remain_quarantined": 1}, report["decision_counts"])
            self.assertTrue(report["findings"][0]["matching_identity_fields"])
            self.assertFalse(report["findings"][0]["migration_allowed"])


if __name__ == "__main__":
    unittest.main()