from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).parent / "场景创作激活.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("scene_activation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def binding(binding_id: str, kind: str, terms: list[str]) -> dict:
    strategy = {field: field for field in MODULE.REQUIRED_STRATEGY_FIELDS}
    source_ref = "原始资料/类型系统.txt:SOURCE[1]" if kind == "类型系统来源块" else "原始资料/资料库.txt:SOURCE[1]"
    return {"binding_id": binding_id, "source_id": binding_id, "source_kind": kind, "source_ref": source_ref, "name": " ".join(terms), "semantic_interpretation": {"semantic_terms": terms}, "creation_binding": {"creative_strategy": strategy}}


class SceneActivationTests(unittest.TestCase):
    def test_evaluate_does_not_write_the_production_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            sentinel = '{"preserve":"existing-production-projection"}\n'
            for name in ("全量资料正文生产编排.json", "全量资料正文生产队列.jsonl", "全量资料正文生产批次.jsonl", "场景创作激活任务.jsonl"):
                (evidence / name).write_text(sentinel, encoding="utf-8")
            with mock.patch.object(MODULE, "validate_policy", return_value={}), \
                 mock.patch.object(MODULE, "validate_bindings"), \
                 mock.patch.object(MODULE, "build_qualification_ledger", return_value={"records": [{"binding_id": "TEST", "executable_entry": True}], "counts": {"executable_entry": 1}, "ledger_sha256": "test", "contract_version": "test"}), \
                 mock.patch.object(MODULE, "build_plan", return_value={"records": [], "queued_count": 0}):
                MODULE.evaluate(root)
            for name in ("全量资料正文生产编排.json", "全量资料正文生产队列.jsonl", "全量资料正文生产批次.jsonl", "场景创作激活任务.jsonl"):
                self.assertEqual(sentinel, (evidence / name).read_text(encoding="utf-8"))

    def test_candidates_require_two_terms_including_scene_specific_term(self) -> None:
        bindings = {"records": [{
            "binding_id": "TB-1", "source_id": "S-1", "source_kind": "资料库", "name": "灵息检测",
            "semantic_interpretation": {"semantic_terms": ["灵息"]},
            "creation_binding": {"creative_strategy": {key: "已填写" for key in MODULE.REQUIRED_STRATEGY_FIELDS}},
        }]}
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{
            "scene_id": "S1", "creative_need": "检测异常", "stage": "场景卡",
            "required_source_kinds": ["资料库"], "retrieval_terms": ["灵息", "代价"],
            "activation_conditions_met": True, "activation_evidence": ["test"],
        }]}
        plan = MODULE.build_plan(bindings, brief, {"TB-1"})
        self.assertEqual(plan["queued_count"], 0)

    def test_network_binding_can_use_a_source_specific_term_with_cost(self) -> None:
        rows = [binding("N-1", "动态网络", ["状态变化", "代价"])]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{
            "scene_id": "S1", "creative_need": "检测后的状态变化", "stage": "场景卡",
            "required_source_kinds": ["动态网络"], "retrieval_terms": ["状态变化", "代价"],
            "activation_conditions_met": True, "activation_evidence": ["test"],
        }]}
        plan = MODULE.build_plan({"records": rows}, brief, {"N-1": {}})
        self.assertEqual(plan["status"], "ready_for_draft_creation")
        self.assertEqual(plan["candidate_records"][0]["activation"]["matched_project_terms"], ["代价", "状态变化"])
        self.assertEqual(plan["candidate_records"][0]["candidate_use"], "state_transition_constraint")

    def test_only_matching_authorized_categories_become_tasks(self) -> None:
        rows = [binding("A", "资料库", ["沈砚", "检测"]), binding("B", "动态网络", ["沈砚", "检测"]), binding("C", "类型连接", ["沈砚", "检测"])]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{"scene_id": "S1", "creative_need": "检测", "stage": "场景卡", "required_source_kinds": ["资料库", "动态网络", "类型连接"], "retrieval_terms": ["沈砚", "检测"], "activation_evidence": ["scene"], "activation_conditions_met": True}]}
        plan = MODULE.build_plan({"records": rows}, brief, {"A": {}, "B": {}, "C": {}})
        self.assertEqual({row["binding_id"] for row in plan["candidate_records"]}, {"A", "B"})
        self.assertEqual(plan["isolated_counts"]["类型连接"], 1)
        self.assertEqual(plan["status"], "needs_creative_brief_refinement")

    def test_type_source_blocks_bind_without_project_type_selection(self) -> None:
        rows = [
            binding("TS-1", "类型系统", ["灵息失衡", "代价"]),
            binding("TSB-1", "类型系统来源块", ["灵息失衡", "代价"]),
            binding("TC-1", "类型连接", ["灵息失衡", "代价"]),
        ]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{
            "scene_id": "S1", "creative_need": "灵息失衡造成代价", "stage": "场景卡",
            "required_source_kinds": ["类型系统", "类型系统来源块", "类型连接"],
            "retrieval_terms": ["灵息失衡", "代价"], "activation_evidence": ["scene"],
            "activation_conditions_met": True,
        }]}
        plan = MODULE.build_plan({"records": rows}, brief, {"TS-1": {}, "TSB-1": {}, "TC-1": {}})
        self.assertEqual({"TSB-1"}, {row["binding_id"] for row in plan["candidate_records"]})
        self.assertEqual(1, plan["isolated_counts"]["类型系统"])
        self.assertEqual(1, plan["isolated_counts"]["类型连接"])
        self.assertIn("不得据此推断或确认项目类型", plan["policy"])
        provenance = plan["candidate_records"][0]["source_provenance"]
        self.assertEqual("原始资料/类型系统.txt:SOURCE[1]", provenance["source_ref"])
        self.assertTrue(provenance["project_type_inference_forbidden"])

    def test_type_source_block_requires_complete_source_reference(self) -> None:
        row = binding("TSB-1", "类型系统来源块", ["灵息失衡", "代价"])
        row["source_ref"] = "{'file': '原始资料/类型系统.txt', 'matched_lines': [1]}"
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{
            "scene_id": "S1", "creative_need": "灵息失衡造成代价", "stage": "场景卡",
            "required_source_kinds": ["类型系统来源块"], "retrieval_terms": ["灵息失衡", "代价"], "activation_evidence": ["scene"], "activation_conditions_met": True,
        }]}
        plan = MODULE.build_plan({"records": [row]}, brief, {"TSB-1": {}})
        self.assertEqual("needs_creative_brief_refinement", plan["status"])

    def test_non_draft_brief_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "draft_only"):
            MODULE.build_plan({"records": []}, {"status": "confirmed", "release_status": "ready", "scenes": []}, {})

    def test_all_required_categories_are_needed_for_ready_status(self) -> None:
        rows = [binding("A", "资料库", ["沈砚", "检测"])]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{"scene_id": "S1", "creative_need": "检测", "stage": "场景卡", "required_source_kinds": ["资料库", "类型系统"], "retrieval_terms": ["沈砚", "检测"], "activation_evidence": ["scene"], "activation_conditions_met": True}]}
        plan = MODULE.build_plan({"records": rows}, brief, {"A": {}})
        self.assertEqual(plan["status"], "needs_creative_brief_refinement")
        self.assertEqual(plan["required_source_kind_gaps"][0]["source_kind"], "类型系统")

    def test_draft_creation_does_not_require_formal_approval(self) -> None:
        rows = [binding("A", "资料库", ["沈砚", "检测"])]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{"scene_id": "S1", "creative_need": "检测", "stage": "场景卡", "required_source_kinds": ["资料库"], "retrieval_terms": ["沈砚", "检测"], "activation_evidence": ["scene"], "activation_conditions_met": True}]}
        plan = MODULE.build_plan({"records": rows}, brief, None, formal_creation_allowed=False)
        self.assertEqual("ready_for_draft_creation", plan["status"])
        self.assertEqual(1, plan["queued_count"])
        self.assertTrue(plan["candidate_records"][0]["model_input_eligible"])
        self.assertTrue(plan["candidate_records"][0]["prose_write_allowed"])

    def test_activation_version_distinguishes_current_candidates_from_legacy_ids(self) -> None:
        rows = [binding("A", "资料库", ["沈砚", "检测"])]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{"scene_id": "S1", "creative_need": "检测", "stage": "场景卡", "required_source_kinds": ["资料库"], "retrieval_terms": ["沈砚", "检测"], "activation_evidence": ["scene"], "activation_conditions_met": True}]}
        plan = MODULE.build_plan({"records": rows}, brief, {"A": {}}, activation_version="currentbaseline")
        candidate = plan["candidate_records"][0]
        self.assertEqual("CAND-S1-A", candidate["candidate_id"])
        self.assertEqual("narrative_translation_constraint", candidate["candidate_use"])
        self.assertTrue(candidate["prose_write_allowed"])
        self.assertNotIn("consumption_id", candidate)
        self.assertNotIn("batch_id", candidate)
        self.assertEqual([], plan["records"])

    def test_design_duty_is_deferred_instead_of_becoming_prose_requirement(self) -> None:
        rows = [binding("A", "资料库", ["沈砚", "检测"])]
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{
            "scene_id": "S1", "creative_need": "检测", "stage": "剧情创建",
            "required_source_kinds": ["资料库"], "retrieval_terms": ["沈砚", "检测"],
            "activation_evidence": ["scene"], "activation_conditions_met": True,
            "required_writing_dimensions": ["choice"],
        }]}
        plan = MODULE.build_plan({"records": rows}, brief, {"A": {}})
        duty = plan["candidate_records"][0]["material_duty"]
        self.assertFalse(duty["prose_evidence_required"])
        self.assertIn("旧绑定缺少职责合同字段", duty["deferred_reason"])

    def test_scene_duty_requires_explicit_writing_dimension(self) -> None:
        rows = [binding("A", "锚点网络", ["空间细节", "观察"])]
        rows[0]["creation_binding"].update({"material_role": "scene_constraint", "applicable_stage": ["场景卡"], "required_writing_dimensions": ["observation"]})
        brief = {"status": "authorial_draft", "release_status": "draft_only", "scenes": [{
            "scene_id": "S1", "creative_need": "观察异常", "stage": "场景卡",
            "required_source_kinds": ["锚点网络"], "retrieval_terms": ["空间细节", "观察"],
            "activation_evidence": ["scene"], "activation_conditions_met": True,
            "required_writing_dimensions": ["observation"],
        }]}
        plan = MODULE.build_plan({"records": rows}, brief, {"A": {}})
        self.assertTrue(plan["candidate_records"][0]["material_duty"]["prose_evidence_required"])

    def test_scene_formal_gate_allows_only_hash_bound_approved_scene(self) -> None:
        from 计划锁与正式创作门 import validate_scene_formal_creation_gate
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "配置/project_config.json": {},
                "配置/首章场景创作简报.json": {},
                "文档/证据/全量资料解释词创作绑定.json": {},
                "文档/证据/全量资料输入与正文授权/授权审计报告.json": {},
            }
            hashes = {}
            for name, value in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            approval = {
                "schema_version": "scene-formal-creation-approval-1.0", "status": "approved", "approved_by": "reviewer", "approved_at": "2026-08-17T00:00:00Z",
                "approved_scene_ids": ["S1"], "formal_release_allowed": False,
                "project_config_sha256": hashes["配置/project_config.json"], "scene_brief_sha256": hashes["配置/首章场景创作简报.json"],
                "binding_baseline_sha256": hashes["文档/证据/全量资料解释词创作绑定.json"], "authorization_audit_sha256": hashes["文档/证据/全量资料输入与正文授权/授权审计报告.json"],
            }
            (root / "配置/scene_formal_creation_approval.json").write_text(json.dumps(approval), encoding="utf-8")
            candidate = {"scene_id": "S1", "binding_id": "A", "activation": {"activation_evidence": ["evidence"], "matched_project_terms": ["term"]}, "source_provenance": {"source_ref": "source:1"}, "causal_contract": {key: "value" for key in ("semantic_anchor", "trigger", "required_action", "required_result", "required_cost_or_change")}}
            self.assertTrue(validate_scene_formal_creation_gate(root, "S1", [candidate], {"A": {}})["formal_creation_allowed"])
            candidate["causal_contract"]["trigger"] = ""
            self.assertFalse(validate_scene_formal_creation_gate(root, "S1", [candidate], {"A": {}})["formal_creation_allowed"])


if __name__ == "__main__":
    unittest.main()