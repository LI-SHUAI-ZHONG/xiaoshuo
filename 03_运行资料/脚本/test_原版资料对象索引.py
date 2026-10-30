from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("原版资料对象索引.py")
SPEC = importlib.util.spec_from_file_location("object_index", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OriginalMaterialObjectIndexTests(unittest.TestCase):
    def test_indexes_headings_source_blocks_json_and_anchor_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "原始资料"
            source.mkdir()
            for name in MODULE.ORIGINAL_FILES:
                (source / name).write_text("", encoding="utf-8")
            (source / "资料库.txt").write_text("### 1.1_主角\n内容\n", encoding="utf-8")
            (source / "类型系统.txt").write_text("SOURCE: 样本.json\n===\n{}\n", encoding="utf-8")
            (source / "静态网络.txt").write_text('{"包装":{"connections":[{"id":"C1"}]}}', encoding="utf-8")
            (source / "锚点网络.txt").write_text("| M1.1 | 道具 | 内容 |\n", encoding="utf-8")
            report = MODULE.index(root)
            self.assertEqual(4, report["object_count"])
            rows = (root / "文档" / "证据" / "原版资料对象索引" / "对象索引.jsonl").read_text(encoding="utf-8")
            self.assertIn("1.1_主角", rows)
            self.assertIn("样本.json", rows)
            self.assertIn("connections[0]", rows)
            self.assertIn("M1.1", rows)


if __name__ == "__main__":
    unittest.main()