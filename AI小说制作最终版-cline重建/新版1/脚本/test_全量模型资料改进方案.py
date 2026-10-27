from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("全量模型资料改进方案.py")
SPEC = importlib.util.spec_from_file_location("full_model_improvement_contract", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FullModelMaterialImprovementContractTests(unittest.TestCase):
    def _root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        source = Path(__file__).parents[1] / "配置" / "全量模型资料改进方案.json"
        destination = root / MODULE.CONTRACT_FILE
        destination.parent.mkdir(parents=True)
        destination.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
        return root

    def test_bound_contract_passes(self) -> None:
        report = MODULE.validate(self._root())
        self.assertEqual("passed", report["status"])
        self.assertTrue(report["execution_allowed"])
        self.assertFalse(report["formal_release_allowed"])

    def test_excluding_type_material_is_blocked(self) -> None:
        root = self._root()
        path = root / MODULE.CONTRACT_FILE
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["scope"]["included_source_kinds"].remove("类型连接")
        path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        report = MODULE.validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(any("全部七类资料" in error for error in report["errors"]))

    def test_summary_only_input_is_blocked(self) -> None:
        root = self._root()
        path = root / MODULE.CONTRACT_FILE
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["source_object_readback"]["forbid_summary_only_model_input"] = False
        path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        report = MODULE.validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(any("禁止仅摘要输入" in error for error in report["errors"]))

    def test_missing_automatic_gate_is_blocked(self) -> None:
        root = self._root()
        path = root / MODULE.CONTRACT_FILE
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["automatic_assurance"]["required_gates"].remove("cross_item_duplicate_and_conflict_detection")
        path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        report = MODULE.validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(any("自动验收" in error for error in report["errors"]))

    def test_human_review_is_not_a_required_stage(self) -> None:
        root = self._root()
        contract = json.loads((root / MODULE.CONTRACT_FILE).read_text(encoding="utf-8"))
        self.assertTrue(contract["automatic_assurance"]["human_review_is_not_a_required_stage"])
        self.assertNotIn("human_review", contract["workflow"])

    def test_missing_field_fusion_boundary_is_blocked(self) -> None:
        root = self._root()
        path = root / MODULE.CONTRACT_FILE
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["fusion_requirements"]["project_consumption_must_not_enter_material_fused"] = False
        path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        report = MODULE.validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(any("字段级融合" in error for error in report["errors"]))

    def test_untyped_array_merge_boundary_is_blocked(self) -> None:
        root = self._root()
        path = root / MODULE.CONTRACT_FILE
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["fusion_requirements"]["forbid_untyped_array_append"] = False
        path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        report = MODULE.validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(any("字段级融合" in error for error in report["errors"]))

    def test_same_source_derived_auto_fusion_is_blocked(self) -> None:
        root = self._root()
        path = root / MODULE.CONTRACT_FILE
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["fusion_requirements"]["same_source_derived_improvement"]["must_not_auto_enter"] = "validated_fused"
        path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        report = MODULE.validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(any("字段级融合" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()