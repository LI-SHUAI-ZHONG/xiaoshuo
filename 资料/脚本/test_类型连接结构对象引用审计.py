from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 类型连接结构对象引用审计 import audit


class StructuralReferenceAuditTests(unittest.TestCase):
    def test_creates_hash_backed_structural_reference_without_identity_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            source = "SOURCE: 类型静态搭配库.json\n===\n[{\"static_combination_id\": \"S-1\", \"status\": \"candidate\"}]\n"
            (root / "原始资料/类型连接.txt").write_text(source, encoding="utf-8")
            records = [{"binding_id": "B-1", "source_id": "类型静态搭配库.json:1", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:类型静态搭配库.json[1]"}]
            (root / "文档/证据/全量资料解释词创作绑定.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")
            report = audit(root)
            finding = report["findings"][0]
            self.assertEqual({"structural_reference_ready": 1}, report["decision_counts"])
            self.assertEqual("type_static_combination", finding["protocol_reference"]["object_class"])
            self.assertTrue(finding["protocol_reference"]["object_sha256"])
            self.assertFalse(report["protocol"]["array_position_is_identity"])
            self.assertEqual("类型静态搭配库.json:1", finding["legacy_source_id"])


if __name__ == "__main__":
    unittest.main()