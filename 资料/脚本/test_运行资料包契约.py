from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("运行资料包契约.py")
SPEC = importlib.util.spec_from_file_location("runtime_material_package", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class RuntimeMaterialPackageTests(unittest.TestCase):
    def _root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        source = root / "原始资料" / "资料库.txt"
        source.parent.mkdir(parents=True)
        source.write_text("可复核的来源对象", encoding="utf-8")
        return root

    def _binding(self, root: Path) -> dict:
        source = root / "原始资料" / "资料库.txt"
        return {
            "binding_id": "B-1",
            "source_id": "SRC-1",
            "source_kind": "资料库",
            "source_ref": "原始资料/资料库.txt:SOURCE[1]",
            "creation_binding": {
                "creative_strategy": {"semantic_anchor": "异常痕迹"},
                "material_role": "scene_constraint",
                "applicable_stage": ["正文"],
                "required_writing_dimensions": ["trigger"],
                "prose_evidence_required": True,
            },
            "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }

    def _write_ledger(self, root: Path, executable: bool = True) -> Path:
        path = root / "文档" / "证据" / "资料资格账本.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema_version": "source-qualification-ledger-1.0",
            "records": [{"binding_id": "B-1", "qualification": "source_complete", "executable_entry": executable}],
        }, ensure_ascii=False), encoding="utf-8")
        return path

    def test_scene_package_does_not_require_authorization_file(self) -> None:
        root = self._root()
        package = MODULE.build_package(
            root, "run-test", [self._binding(root)],
            [{"scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"}],
            {},
        )
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertTrue(result["passed"])

    def test_package_binds_current_qualification_ledger(self) -> None:
        root = self._root()
        ledger_path = self._write_ledger(root)
        package = MODULE.build_package(
            root, "run-test", [self._binding(root)],
            [{"scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"}],
        )
        self.assertEqual("source_complete", package["records"][0]["qualification"])
        self.assertTrue(package["records"][0]["executable_entry"])
        self.assertEqual(hashlib.sha256(ledger_path.read_bytes()).hexdigest(), package["qualification_ledger_sha256"])
        self.assertTrue(MODULE.validate_package(root, package, stage="scene")["passed"])

        tampered = dict(package)
        tampered["qualification_ledger_sha256"] = "0" * 64
        result = MODULE.validate_package(root, tampered, stage="scene")
        self.assertFalse(result["passed"])
        self.assertIn("资料包资格账本哈希不一致", result["errors"])

        self._write_ledger(root, executable=False)
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertTrue(any("资格账本未授予 executable_entry" in error for error in result["errors"]))

    def test_prose_validation_requires_same_run_and_translation_result(self) -> None:
        root = self._root()
        grant = {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}}
        package = MODULE.build_package(
            root, "run-test", [self._binding(root)],
            [{"scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"}],
            grant,
        )
        missing_effect = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "run-test", "scene_id": "S1", "binding_id": "B-1", "source_id": "SRC-1", "prose_location": "S1#paragraphs[0]",
        }])
        self.assertFalse(missing_effect["passed"])
        self.assertIn("B-1 缺少 translation_evidence.result、场景或正文消费定位", missing_effect["errors"])
        wrong_run = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "other-run", "scene_id": "S1", "binding_id": "B-1", "source_id": "SRC-1", "prose_location": "S1#paragraphs[0]", "translation_evidence_result": "主角改变调查顺序",
        }])
        self.assertFalse(wrong_run["passed"])
        self.assertIn("B-1 缺少同一 run_id 的消费证据", wrong_run["errors"])
        valid = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "run-test", "scene_id": "S1", "binding_id": "B-1", "source_id": "SRC-1", "prose_location": "S1#paragraphs[0]", "translation_evidence_result": "主角改变调查顺序",
        }])
        self.assertTrue(valid["passed"])

    def test_selected_binding_without_explicit_prose_grant_is_deferred(self) -> None:
        root = self._root()
        binding = self._binding(root)
        package = MODULE.build_package(root, "run-test", [binding], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }])
        record = package["records"][0]
        self.assertFalse(record["prose_write_allowed"])
        self.assertEqual("deferred", record["duty_status"])
        self.assertTrue(record["deferred_reason"])
        result = MODULE.validate_package(root, package, stage="prose", consumption_records=[])
        self.assertTrue(result["passed"])

    def test_prose_write_requires_duty_contract_and_matching_dimension(self) -> None:
        root = self._root()
        binding = self._binding(root)
        package = MODULE.build_package(root, "run-test", [binding], [{
            "scene_id": "S1", "binding_id": "B-1", "stage": "正文",
            "required_writing_dimensions": ["relationship_change"],
            "activation_conditions_met": True, "activation_evidence": ["现场异常"],
            "selection_rationale": "匹配场景目标",
        }], {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}})
        record = package["records"][0]
        self.assertFalse(record["prose_write_allowed"])
        self.assertEqual("deferred", record["duty_status"])

    def test_detects_source_hash_drift(self) -> None:
        root = self._root()
        grant = {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}}
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }], grant)
        (root / "原始资料" / "资料库.txt").write_text("已漂移", encoding="utf-8")
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertTrue(any(error.startswith("B-1 ") for error in result["errors"]))

    def test_rejects_cross_scene_binding(self) -> None:
        root = self._root()
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [
            {"scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"},
            {"scene_id": "S2", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"},
        ])
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertTrue(any(error.startswith("B-1 跨场景绑定") for error in result["errors"]))

    def test_rejects_binding_source_mismatch_in_consumption(self) -> None:
        root = self._root()
        grant = {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}}
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }], grant)
        result = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "run-test", "scene_id": "S1", "binding_id": "B-1", "source_id": "OTHER",
            "prose_location": "S1#paragraphs[0]", "translation_evidence_result": "主角改变调查顺序",
        }])
        self.assertFalse(result["passed"])
        self.assertIn("B-1 消费证据缺少来源、场景或段落定位", result["errors"])

    def test_rejects_binding_scene_mismatch_in_consumption(self) -> None:
        root = self._root()
        grant = {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}}
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }], grant)
        result = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "run-test", "scene_id": "S2", "binding_id": "B-1", "source_id": "SRC-1",
            "prose_location": "S2#paragraphs[0]", "translation_evidence_result": "主角改变调查顺序",
        }])
        self.assertFalse(result["passed"])
        self.assertIn("B-1 消费证据缺少来源、场景或段落定位", result["errors"])

    def test_rejects_cross_scene_binding(self) -> None:
        root = self._root()
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [
            {"scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"},
            {"scene_id": "S2", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"},
        ])
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])

    def test_rejects_binding_source_mismatch_in_consumption(self) -> None:
        root = self._root()
        grant = {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}}
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }], grant)
        result = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "run-test", "scene_id": "S1", "binding_id": "B-1", "source_id": "OTHER",
            "prose_location": "S1#paragraphs[0]", "translation_evidence_result": "主角改变调查顺序",
        }])
        self.assertFalse(result["passed"])
        self.assertIn("B-1 消费证据缺少来源、场景或段落定位", result["errors"])

    def test_normalizes_verified_legacy_library_locator(self) -> None:
        root = self._root()
        index = root / "文档" / "资料库索引.jsonl"
        index.parent.mkdir(parents=True)
        index.write_text(
            '{"entry_id":"SRC-1","name":"SRC-1","source_ref":{"file":"原始资料/资料库.txt","locator":"SRC-1","line_start":1}}\n',
            encoding="utf-8",
        )
        binding = self._binding(root)
        binding["source_ref"] = "{'file': '原始资料/资料库.txt', 'locator': 'SRC-1', 'line_start': 1}"
        package = MODULE.build_package(root, "run-test", [binding], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }])
        self.assertEqual("原始资料/资料库.txt:SRC-1", package["records"][0]["source_ref"])
        self.assertTrue(MODULE.validate_package(root, package, stage="scene")["passed"])

    def test_freezes_chapter_scene_and_continuity_state(self) -> None:
        root = self._root()
        contexts = [
            {"chapter_id": "C1", "scene_id": "S1", "scene_sequence": 1, "state_before": "未查证", "state_after": "发现异常"},
            {"chapter_id": "C1", "scene_id": "S2", "scene_sequence": 2, "state_before": "发现异常", "state_after": "决定追查", "previous_scene_id": "S1", "previous_state_after": "发现异常"},
        ]
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "chapter_id": "C1", "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }], scene_contexts=contexts)
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertIn("场景缺少运行资料包记录：S2", result["errors"])
        self.assertEqual("C1", package["records"][0]["chapter_id"])
        self.assertTrue(package["records"][0]["continuity_hash"])

        broken = dict(package)
        broken["scene_contexts"] = [dict(row) for row in package["scene_contexts"]]
        broken["scene_contexts"][1]["previous_state_after"] = "被篡改"
        result = MODULE.validate_package(root, broken, stage="scene")
        self.assertFalse(result["passed"])
        self.assertIn("S2 前后状态未衔接", result["errors"])

    def test_continuity_package_identifiers_are_required_for_prose_consumption(self) -> None:
        root = self._root()
        contexts = [{"chapter_id": "C1", "scene_id": "S1", "scene_sequence": 1, "state_before": "未查证", "state_after": "发现异常"}]
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
            "required_writing_dimensions": ["trigger"],
        }], {"B-1": {"model_input_eligible": True, "prose_write_allowed": True}}, scene_contexts=contexts)
        record = package["records"][0]
        consumption = [{
            "run_id": "run-test", "chapter_id": "C1", "scene_id": "S1", "binding_id": "B-1", "source_id": "SRC-1",
            "package_id": "wrong-package", "continuity_hash": record["continuity_hash"],
            "prose_location": "S1#paragraphs[0]", "translation_evidence_result": "主角改变调查顺序",
        }]
        result = MODULE.validate_package(root, package, stage="prose", consumption_records=consumption)
        self.assertFalse(result["passed"])
        self.assertIn("B-1 消费证据缺少来源、场景或段落定位", result["errors"])

    def test_rejects_frozen_binding_set_drift(self) -> None:
        root = self._root()
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }])
        package["frozen_binding_ids"] = ["other-binding"]
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertIn("资料包冻结 binding_id 集合与记录集合不一致", result["errors"])

    def test_rejects_missing_scene_runtime_record(self) -> None:
        root = self._root()
        contexts = [
            {"chapter_id": "C1", "scene_id": "S1", "scene_sequence": 1, "state_before": "未查证", "state_after": "发现异常"},
            {"chapter_id": "C1", "scene_id": "S2", "scene_sequence": 2, "state_before": "发现异常", "state_after": "决定追查", "previous_scene_id": "S1", "previous_state_after": "发现异常"},
        ]
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [{
            "chapter_id": "C1", "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }], scene_contexts=contexts)
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertIn("场景缺少运行资料包记录：S2", result["errors"])

    def test_rejects_cross_scene_binding_reuse(self) -> None:
        root = self._root()
        package = MODULE.build_package(root, "run-test", [self._binding(root)], [
            {"scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标"},
            {"scene_id": "S2", "binding_id": "B-1", "activation_conditions_met": True, "activation_evidence": ["后续异常"], "selection_rationale": "匹配场景目标"},
        ])
        result = MODULE.validate_package(root, package, stage="scene")
        self.assertFalse(result["passed"])
        self.assertIn("B-1 跨场景绑定：S1, S2", result["errors"])

    def test_rejects_non_prose_duty_in_prose_stage(self) -> None:
        root = self._root()
        binding = self._binding(root)
        binding["creation_binding"]["prose_evidence_required"] = False
        package = MODULE.build_package(root, "run-test", [binding], [{
            "scene_id": "S1", "binding_id": "B-1", "activation_conditions_met": True,
            "activation_evidence": ["现场异常"], "selection_rationale": "匹配场景目标",
        }])
        result = MODULE.validate_package(root, package, stage="prose", consumption_records=[{
            "run_id": "run-test", "scene_id": "S1", "binding_id": "B-1",
        }])
        self.assertFalse(result["passed"])
        self.assertIn("B-1 非正文职责资料进入正文消费链", result["errors"])

if __name__ == "__main__":
    unittest.main()