from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from 资料消费审计 import audit_formal_fact_evidence, audit_material_duty_records, audit_network_consumption_contract


class FormalFactEvidenceTests(unittest.TestCase):
    def test_counts_only_located_original_source_records(self) -> None:
        report = audit_formal_fact_evidence([
            {
                "source_id": "155.2",
                "evidence_layer": "original_source",
                "source_ref": {"path": "原始资料/资料库.txt", "location": "line:12"},
            }
        ])

        self.assertEqual(1, report["counted_original_source"])
        self.assertEqual(0, report["excluded_count"])
        self.assertTrue(report["formal_fact_usable"])

    def test_excludes_missing_or_derived_evidence_layers_from_formal_facts(self) -> None:
        report = audit_formal_fact_evidence([
            {"source_id": "missing", "source_ref": {"path": "原始资料/资料库.txt", "location": "line:12"}},
            {
                "source_id": "derived",
                "evidence_layer": "runtime_artifact",
                "source_ref": {"path": "文档/证据/execution_outputs/module_09_scene_prose.json", "location": "scenes[0]"},
            },
        ])

        self.assertEqual(0, report["counted_original_source"])
        self.assertEqual(2, report["excluded_count"])
        self.assertFalse(report["formal_fact_usable"])
        self.assertTrue(all("evidence_layer 不是 original_source" == row["exclusion_reason"] for row in report["excluded_records"]))

    def test_excludes_original_source_without_a_recheckable_locator(self) -> None:
        report = audit_formal_fact_evidence([
            {
                "source_id": "unlocated",
                "evidence_layer": "original_source",
                "source_ref": {"path": "原始资料/资料库.txt"},
            }
        ])

        self.assertEqual("original_source 记录缺少可复核定位", report["excluded_records"][0]["exclusion_reason"])
        self.assertFalse(report["formal_fact_usable"])


class NetworkConsumptionContractTests(unittest.TestCase):
    def test_accepts_scene_scoped_consumption_with_positive_reason(self) -> None:
        report = audit_network_consumption_contract("dynamic_chain", [{
            "chain_id": "D1", "status": "consumed", "condition": "冲突触发",
            "decision_statement": "主角选择承担代价", "used_in": "prose",
            "scene_id": "scene-01", "chapter_id": "chapter-01",
            "source_ref": {"path": "module_08.json", "location": "scenes[0]"},
        }])
        self.assertTrue(report["passed"])
        self.assertEqual(1, report["adopted_or_consumed_count"])

    def test_rejects_adopted_record_without_positive_condition(self) -> None:
        report = audit_network_consumption_contract("anchor", [{
            "anchor_id": "A1", "status": "adopted", "decision_statement": "落入正文",
            "used_in": "scene_design", "scene_id": "scene-01", "chapter_id": "chapter-01",
            "source_ref": {"path": "x.json", "location": "rows[0]"},
        }])
        self.assertFalse(report["passed"])
        self.assertIn("condition", report["violations"][0]["reason"])

    def test_requires_reason_for_deferred_record(self) -> None:
        report = audit_network_consumption_contract("static_connection", [{"connection_id": "S1", "status": "deferred"}])
        self.assertFalse(report["passed"])
        self.assertIn("deferred_reason", report["violations"][0]["reason"])

    def test_rejects_missing_source_location(self) -> None:
        report = audit_network_consumption_contract("anchor", [{
            "anchor_id": "A1", "status": "consumed", "condition": "环境压力",
            "decision_statement": "锚点呈现压力", "used_in": "prose",
            "scene_id": "scene-01", "chapter_id": "chapter-01",
            "source_ref": {"path": "module_09.json"},
        }])
        self.assertFalse(report["passed"])
        self.assertIn("source_ref.path/location", report["violations"][0]["reason"])


class MaterialDutyReceiptTests(unittest.TestCase):
    def _duty(self, *, prose: bool = True) -> dict[str, object]:
        return {
            "material_role": "scene_constraint",
            "applicable_stage": ["正文"],
            "required_writing_dimensions": ["trigger"],
            "prose_evidence_required": prose,
        }

    def test_accepts_design_scene_prose_and_deferred_receipts(self) -> None:
        records = [
            {"run_id": "run-1", "binding_id": "D", "material_duty": self._duty(prose=False), "duty_status": "design_used"},
            {"run_id": "run-1", "binding_id": "S", "material_duty": self._duty(prose=False), "duty_status": "scene_constraint_used"},
            {"run_id": "run-1", "binding_id": "P", "material_duty": self._duty(), "duty_status": "prose_used", "prose_location": "S#paragraphs[0]", "paragraph_sha256": "a" * 64},
            {"run_id": "run-1", "binding_id": "F", "material_duty": {"deferred_reason": "缺少正文职责"}, "duty_status": "deferred", "deferred_reason": "缺少正文职责"},
        ]
        report = audit_material_duty_records(records, "run-1")
        self.assertTrue(report["passed"])
        self.assertEqual({"design_used": 1, "scene_constraint_used": 1, "prose_used": 1, "deferred": 1}, report["status_counts"])

    def test_rejects_prose_receipt_without_explicit_prose_duty(self) -> None:
        report = audit_material_duty_records([{
            "run_id": "run-1", "binding_id": "D", "material_duty": self._duty(prose=False),
            "duty_status": "prose_used", "prose_location": "S#paragraphs[0]", "paragraph_sha256": "a" * 64,
        }], "run-1")
        self.assertFalse(report["passed"])
        self.assertIn("未获得正文职责合同", report["violations"][0]["reason"])


if __name__ == "__main__":
    unittest.main()