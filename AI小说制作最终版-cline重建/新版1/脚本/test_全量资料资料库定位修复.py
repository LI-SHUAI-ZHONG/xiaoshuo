from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("全量资料资料库定位修复.py")
SPEC = importlib.util.spec_from_file_location("library_locator_repair", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LibraryLocatorRepairTests(unittest.TestCase):
    def test_repairs_only_verified_library_locator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); evidence = root / "文档" / "证据"; evidence.mkdir(parents=True)
            original = root / "原始资料"; original.mkdir()
            (original / "资料库.txt").write_text("## 板块129 命名与术语体系\n内容\n", encoding="utf-8")
            records = [{"binding_id": "TB-1", "source_id": "129_命名与术语体系", "source_kind": "资料库", "source_ref": "{'file': '原始资料/资料库.txt', 'locator': '129_命名与术语体系', 'line_start': 1}"}, {"binding_id": "TB-2", "source_kind": "类型连接"}]
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")
            audit = {"status_counts": {"passed": 0, "quarantined": 2}, "source_kind_status_counts": {"资料库": {"passed": 0, "quarantined": 1}}, "quarantined_findings": [{"binding_id": "TB-1", "source_kind": "资料库", "errors": [MODULE.LOCATOR_ERROR]}, {"binding_id": "TB-2", "source_kind": "类型连接", "errors": ["缺少标识"]}]}
            (evidence / "全绑定来源完整性审计报告.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            output = MODULE.repair_library_locators(root, "repair")
            revised = json.loads((output / "全绑定来源完整性审计报告.资料库定位修复.json").read_text(encoding="utf-8"))
            self.assertEqual(1, revised["status_counts"]["quarantined"])
            self.assertEqual("TB-2", revised["quarantined_findings"][0]["binding_id"])


if __name__ == "__main__":
    unittest.main()