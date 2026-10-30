from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("原版升级资料字段级融合.py")
SPEC = importlib.util.spec_from_file_location("field_fusion", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FieldFusionPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "原始资料" / "资料库.txt"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("## 板块1 主角\n定义\n", encoding="utf-8")
        original = {"file": "原始资料/资料库.txt", "locator": "1_主角", "content": "## 板块1 主角\n定义"}
        mapping = {
            "binding_id": "TB-1", "source_id": "1_主角", "mapping_status": "verified_candidate",
            "source_file_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "derived_original_object": original,
            "derived_original_object_sha256": MODULE._canonical_hash(original),
            "verification": "fixture",
        }
        path = self.root / MODULE.MAPPINGS_PATH
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(mapping, ensure_ascii=False) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_preview_preserves_pending_evidence_without_fact_change(self) -> None:
        result = MODULE.build(self.root)
        output = Path(result["output"])
        self.assertEqual("blocked_pending_field_evidence", result["status"])
        self.assertEqual(1, result["pending_evidence_count"])
        self.assertEqual("", (output / "field_changes.jsonl").read_text(encoding="utf-8"))
        pending = json.loads((output / "pending_evidence.jsonl").read_text(encoding="utf-8"))
        self.assertEqual("pending_evidence", pending["action"])
        self.assertFalse(json.loads((output / "manifest.json").read_text(encoding="utf-8"))["formal_fact_eligible"])

    def test_rejects_source_hash_drift(self) -> None:
        self.source.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "哈希漂移"):
            MODULE.build(self.root)

    def test_semantic_rule_unit_preserves_condition_and_effect(self) -> None:
        mapping_path = self.root / MODULE.MAPPINGS_PATH
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping["upgrade_units"] = [{
            "unit_id": "RULE-1",
            "unit_kind": "structure",
            "field_path": "rule",
            "semantic_key": "主角->核心悬念#绑定#绑定主线",
            "baseline_value": None,
            "candidate_value": {
                "condition": "绑定主线",
                "effect": "终点状态随起点状态更新",
                "not_guaranteed": ["不保证动态规则必然触发"],
            },
            "action": "complete",
            "source_refs": [{"file": "原始资料/资料库.txt", "locator": "1_主角"}],
            "derivation_rule": "由静态绑定关系派生动态规则，并保留触发边界",
        }]
        mapping_path.write_text(json.dumps(mapping, ensure_ascii=False) + "\n", encoding="utf-8")
        result = MODULE.build(self.root, version="V3")
        output = Path(result["output"])
        changes = json.loads((output / "field_changes.jsonl").read_text(encoding="utf-8"))
        self.assertEqual("structure", changes["unit_kind"])
        self.assertEqual("绑定主线", changes["candidate_value"]["condition"])
        self.assertEqual(["不保证动态规则必然触发"], changes["candidate_value"]["not_guaranteed"])

    def test_rejects_untyped_rule_candidate(self) -> None:
        mapping_path = self.root / MODULE.MAPPINGS_PATH
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping["upgrade_units"] = [{"field_path": "rules", "candidate_value": "追加规则"}]
        mapping_path.write_text(json.dumps(mapping, ensure_ascii=False) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "语义单元缺少字段"):
            MODULE.build(self.root, version="V3")

    def test_same_source_overlay_builds_immutable_resolved_view(self) -> None:
        baseline_path = self.root / MODULE.LIBRARY_BASELINE_PATH
        log_path = self.root / MODULE.DEPENDENCY_REPAIR_LOG_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline = [
            {"entry_id": "1_A", "dependencies": [], "source_ref": {"file": "原始资料/资料库.txt", "locator": "1_A"}},
            {"entry_id": "2_B", "dependencies": [], "source_ref": {"file": "原始资料/资料库.txt", "locator": "2_B"}},
        ]
        baseline_path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"entry_id": "1_A", "dependencies": [{"entry_id": "2_B", "type": "前置条件"}], "reason": "A 使用 B 作为前置条件", "analysis_dimension": "前置条件", "classification": "类型C"}, ensure_ascii=False) + "\n", encoding="utf-8")
        before = baseline_path.read_bytes()
        result = MODULE.build_same_source_overlay(self.root, version="V4")
        output = Path(result["output"])
        self.assertEqual("validated_overlay", result["status"])
        self.assertEqual(before, baseline_path.read_bytes())
        overlay = json.loads((output / "validated_overlay.jsonl").read_text(encoding="utf-8"))
        self.assertEqual("same_source_derived_improvement", overlay["source_class"])
        resolved = json.loads((output / "resolved_material_view" / "资料库_规范化.json").read_text(encoding="utf-8"))
        self.assertEqual({"entry_id": "2_B", "type": "前置条件"}, resolved[0]["dependencies"][-1])

    def test_same_source_overlay_blocks_cycles(self) -> None:
        baseline_path = self.root / MODULE.LIBRARY_BASELINE_PATH
        log_path = self.root / MODULE.DEPENDENCY_REPAIR_LOG_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline = [
            {"entry_id": "1_A", "dependencies": [{"entry_id": "2_B", "type": "功能关联"}], "source_ref": {"file": "原始资料/资料库.txt", "locator": "1_A"}},
            {"entry_id": "2_B", "dependencies": [], "source_ref": {"file": "原始资料/资料库.txt", "locator": "2_B"}},
        ]
        baseline_path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"entry_id": "2_B", "dependencies": [{"entry_id": "1_A", "type": "前置条件"}], "reason": "would cycle"}, ensure_ascii=False) + "\n", encoding="utf-8")
        result = MODULE.build_same_source_overlay(self.root, version="V4")
        output = Path(result["output"])
        self.assertEqual("validated_overlay_with_unresolved_conflicts", result["status"])
        self.assertEqual(0, result["validated_overlay_count"])
        conflict = json.loads((output / "unresolved_conflicts.jsonl").read_text(encoding="utf-8"))
        self.assertEqual("依赖关系会形成循环", conflict["reason"])


if __name__ == "__main__":
    unittest.main()