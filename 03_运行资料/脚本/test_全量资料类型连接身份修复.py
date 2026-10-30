from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("全量资料类型连接身份修复.py")
SPEC = importlib.util.spec_from_file_location("type_connection_identity_repair", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TypeConnectionIdentityRepairTests(unittest.TestCase):
    def test_repairs_each_precisely_located_object_with_hash_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); evidence = root / "文档" / "证据"; evidence.mkdir(parents=True); source = root / "原始资料"; source.mkdir()
            (source / "类型连接.txt").write_text("# Type Connections\n\nSOURCE: a.json\n====\n[{\"connection_id\": \"A-1\"}, {\"name\": \"no-id\"}]\n", encoding="utf-8")
            (evidence / "bindings.json").write_text(json.dumps({"records": [{"binding_id": "TB-1"}, {"binding_id": "TB-2"}]}), encoding="utf-8")
            audit = {"status_counts": {"passed": 0, "quarantined": 2}, "source_kind_status_counts": {"类型连接": {"passed": 0, "quarantined": 2}}, "quarantined_findings": [{"binding_id": "TB-1", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:a.json[1]", "errors": [MODULE.MISSING_ID_ERROR]}, {"binding_id": "TB-2", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:a.json[2]", "errors": [MODULE.MISSING_ID_ERROR]}]}
            (evidence / "audit.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            output = MODULE.repair_type_connection_identity(root, "repair", evidence / "bindings.json", evidence / "audit.json")
            revised = json.loads((output / "全绑定来源完整性审计报告.类型连接身份修复.json").read_text(encoding="utf-8"))
            self.assertEqual(2, revised["status_counts"]["passed"])
            self.assertEqual([], revised["quarantined_findings"])
            ledger = json.loads((output / "类型连接身份修复账本.json").read_text(encoding="utf-8"))
            self.assertNotEqual(ledger["repaired"][0]["stable_source_identity"], ledger["repaired"][1]["stable_source_identity"])

    def test_repairs_root_object_only_at_index_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); evidence = root / "文档" / "证据"; evidence.mkdir(parents=True); source = root / "原始资料"; source.mkdir()
            (source / "类型连接.txt").write_text("SOURCE: schema.json\n====\n{\"type\": \"object\"}\n", encoding="utf-8")
            (evidence / "bindings.json").write_text(json.dumps({"records": [{"binding_id": "TB-1"}, {"binding_id": "TB-2"}]}), encoding="utf-8")
            findings = [{"binding_id": "TB-1", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:schema.json[1]", "errors": [MODULE.INVALID_ARRAY_ERROR]}, {"binding_id": "TB-2", "source_kind": "类型连接", "source_ref": "原始资料/类型连接.txt:schema.json[2]", "errors": [MODULE.INVALID_ARRAY_ERROR]}]
            audit = {"status_counts": {"passed": 0, "quarantined": 2}, "source_kind_status_counts": {"类型连接": {"passed": 0, "quarantined": 2}}, "quarantined_findings": findings}
            (evidence / "audit.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            output = MODULE.repair_type_connection_identity(root, "repair", evidence / "bindings.json", evidence / "audit.json")
            revised = json.loads((output / "全绑定来源完整性审计报告.类型连接身份修复.json").read_text(encoding="utf-8"))
            self.assertEqual(1, revised["status_counts"]["passed"])
            self.assertEqual("TB-2", revised["quarantined_findings"][0]["binding_id"])


if __name__ == "__main__":
    unittest.main()