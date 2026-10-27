from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 类型连接对象分类审计 import audit


class TypeConnectionObjectClassificationTests(unittest.TestCase):
    def test_separates_stable_entities_from_structural_objects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            source = "SOURCE: 类型连接.json\n===\n[{\"connection_id\": \"C-1\"}, {\"rule\": \"condition\"}]\n"
            (root / "原始资料/类型连接.txt").write_text(source, encoding="utf-8")
            records = [
                {"binding_id": "B-1", "source_id": "C-1", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:类型连接.json[1]"},
                {"binding_id": "B-2", "source_id": "类型连接.json:2", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:类型连接.json[2]"},
            ]
            (root / "文档/证据/全量资料解释词创作绑定.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")
            report = audit(root)
            self.assertEqual({"eligible_for_identity_review": 1, "remain_quarantined": 1}, report["decision_counts"])
            saved = json.loads((root / "文档/证据/类型连接对象分类审计报告.json").read_text(encoding="utf-8"))
            self.assertEqual(2, saved["binding_count"])


if __name__ == "__main__":
    unittest.main()