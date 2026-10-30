from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 全绑定来源完整性审计 import audit


class AllBindingSourceIntegrityAuditTests(unittest.TestCase):
    def test_passes_complete_objects_and_keeps_type_index_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            (root / "原始资料/资料库.txt").write_text("### book-1\ncontent\n", encoding="utf-8")
            (root / "原始资料/类型系统.txt").write_text("SOURCE: one.json\n{}\nname\n", encoding="utf-8")
            records = [
                {"binding_id": "B-1", "source_id": "book-1", "source_kind": "资料库", "source_ref": "{'file': '原始资料/资料库.txt', 'locator': 'book-1', 'line_start': 1}"},
                {"binding_id": "T-1", "source_id": "类型名", "source_kind": "类型系统", "source_ref": "{'file': '原始资料/类型系统.txt', 'matched_lines': [3]}"},
            ]
            (root / "文档/证据/全量资料解释词创作绑定.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")
            report = audit(root)
            self.assertEqual("passed", report["status"])
            self.assertEqual("completed", report["audit_state"])
            self.assertEqual(2, report["processed_count"])
            self.assertEqual(1, report["isolated_type_index_count"])
            self.assertEqual({"passed": 1}, report["source_kind_status_counts"]["资料库"])
            saved = json.loads((root / "文档/证据/全绑定来源完整性审计报告.json").read_text(encoding="utf-8"))
            self.assertEqual("completed", saved["audit_state"])

    def test_quarantines_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "原始资料").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            (root / "原始资料/锚点网络.txt").write_text("| M1.1 | 名称 | 内容 | 条件 | 类别 |\n", encoding="utf-8")
            record = {"binding_id": "A-1", "source_id": "M9.9", "source_kind": "锚点网络", "source_ref": "原始资料/锚点网络.txt:1"}
            (root / "文档/证据/全量资料解释词创作绑定.json").write_text(json.dumps({"records": [record]}, ensure_ascii=False), encoding="utf-8")
            report = audit(root)
            self.assertEqual("quarantined", report["status"])
            self.assertIn("source_id 与锚点网络 anchor_id 不一致", report["quarantined_findings"][0]["errors"])

    def test_static_network_identity_uses_one_based_array_position(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "网络完整数据").mkdir()
            (root / "文档/证据").mkdir(parents=True)
            (root / "网络完整数据/静态连接完整数据.json").write_text(
                json.dumps({"connections": [{"source": "甲", "target": "乙", "priority": 99}]}, ensure_ascii=False), encoding="utf-8"
            )
            record = {"binding_id": "S-1", "source_id": "STATIC:甲->乙#1", "source_kind": "静态网络", "source_ref": "网络完整数据/静态连接完整数据.json:connections[0]"}
            (root / "文档/证据/全量资料解释词创作绑定.json").write_text(json.dumps({"records": [record]}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual("passed", audit(root)["status"])


if __name__ == "__main__":
    unittest.main()