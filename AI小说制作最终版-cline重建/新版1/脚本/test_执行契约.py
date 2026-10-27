from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 项目执行边界 import sha256_file, source_permission_errors, validate_execution_contract
from 正式交付审批 import MATERIAL_BATCH_RELEASE_SCOPE, validate_formal_release
import 执行管道 as execution_pipeline
from 全量资料正文生产编排 import build_plan


class ExecutionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._write("原始资料/资料库.txt", "library")
        self._write("原始资料/类型系统.txt", "types")
        self._write("原始资料/锚点网络.txt", "anchors")
        self._write("网络完整数据/动态连接完整数据.json", "{}")
        self._write("网络完整数据/静态连接完整数据.json", "{}")
        selection = {"project_id": "p1", "selected_type_profiles": {"玄幻": {}}, "shared_sources": ["原始资料/资料库.txt"]}
        self._json("文档/证据/小说资料选择清单.json", selection)
        chapter = {"chapter_id": "1", "target_words": 100, "scenes": [{"scene_id": "1-S1"}]}
        config = {"project_id": "p1", "genre_selection": ["玄幻"], "type_combination": {"combination_id": "玄幻_悬疑"}, "project_mode": "planned", "target_chapter_count": 1, "target_words": 100, "chapter_plan": [chapter]}
        self._json("配置/project_config.json", config)
        files = ["文档/证据/小说资料选择清单.json", "原始资料/资料库.txt", "原始资料/类型系统.txt", "原始资料/锚点网络.txt", "网络完整数据/动态连接完整数据.json", "网络完整数据/静态连接完整数据.json"]
        snapshot = {"selection_sha256": sha256_file(self.root / files[0]), "files": [{"path": name, "sha256": sha256_file(self.root / name)} for name in files]}
        blueprint = {"schema_version": "project-planning-1.1", "project_id": "p1", "approval": {"status": "approved"}, "source_snapshot": snapshot, "chapter_plan": [chapter], "allowed_source_ids": ["lib-1"], "allowed_sources": [{"source_kind": "library", "source_id": "lib-1", "source_path": "原始资料/资料库.txt", "source_status": "verified", "draft_prose": True, "selection_rationale": "chapter rule"}]}
        self._json("文档/证据/project_planning.json", blueprint)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, name: str, content: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _json(self, name: str, value: dict) -> None:
        self._write(name, json.dumps(value, ensure_ascii=False))

    def test_rejects_source_snapshot_drift(self) -> None:
        self.assertEqual("passed", validate_execution_contract(self.root)["status"])
        self._write("原始资料/资料库.txt", "tampered")
        self.assertIn("资料文件快照已漂移：原始资料/资料库.txt", validate_execution_contract(self.root)["errors"])

    def test_rejects_incomplete_prose_provenance(self) -> None:
        record = {"source_id": "lib-1", "source_status": "verified", "draft_prose": True, "source_ref": {"project_id": "p1", "path": "原始资料/资料库.txt"}}
        self.assertTrue(source_permission_errors(self.root, [record]))

    def test_creation_phase_allows_unapproved_delivery_blueprint(self) -> None:
        blueprint_path = self.root / "文档/证据/project_planning.json"
        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
        blueprint["approval"]["status"] = "pending"
        blueprint_path.write_text(json.dumps(blueprint, ensure_ascii=False), encoding="utf-8")
        self.assertEqual("passed", validate_execution_contract(self.root, require_blueprint=False, phase="creation")["status"])
        self.assertIn("project_planning 未获人工批准", validate_execution_contract(self.root, phase="delivery")["errors"])

    def test_creation_keeps_draft_provenance_separate_from_delivery_permission(self) -> None:
        record = {"source_id": "draft-only", "source_status": "unverified", "draft_prose": False, "source_ref": {"project_id": "p1", "path": "原始资料/资料库.txt", "location": "87.1"}}
        self.assertEqual([], source_permission_errors(self.root, [record], phase="creation"))
        self.assertIn("正文来源未获蓝图许可：draft-only", source_permission_errors(self.root, [record], phase="delivery"))

    def test_rejects_system_runtime_approval_when_report_hash_drifts(self) -> None:
        blueprint_path = self.root / "文档/证据/project_planning.json"
        report_path = self.root / "文档/证据/资料运行质量报告.json"
        report = {"status": "system_runtime_approved", "approval_actor": "system", "policy_version": "runtime-source-admission-1.0", "formal_fact_approval": False, "input_hashes": {"config_sha256": sha256_file(self.root / "配置/project_config.json"), "selection_sha256": sha256_file(self.root / "文档/证据/小说资料选择清单.json"), "registry_sha256": "", "bindings_sha256": "", "activation_matrix_sha256": ""}}
        for name in ("资源注册表.json", "全量资料解释词创作绑定.json", "全书资料激活矩阵.json"):
            self._write("文档/证据/" + name, "{}")
        report["input_hashes"].update({"registry_sha256": sha256_file(self.root / "文档/证据/资源注册表.json"), "bindings_sha256": sha256_file(self.root / "文档/证据/全量资料解释词创作绑定.json"), "activation_matrix_sha256": sha256_file(self.root / "文档/证据/全书资料激活矩阵.json")})
        self._json("文档/证据/资料运行质量报告.json", report)
        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
        blueprint["approval"] = {"status": "system_runtime_approved", "actor": "system", "policy_version": "runtime-source-admission-1.0", "runtime_report_sha256": sha256_file(report_path)}
        blueprint["runtime_admission"] = {"report_sha256": sha256_file(report_path), "input_hashes": report["input_hashes"], "formal_fact_approval": False}
        blueprint_path.write_text(json.dumps(blueprint, ensure_ascii=False), encoding="utf-8")
        self.assertEqual("passed", validate_execution_contract(self.root)["status"])
        self._write("文档/证据/资料运行质量报告.json", "{}")
        self.assertIn("系统运行批准报告无效", validate_execution_contract(self.root)["errors"])

    def test_formal_release_requires_version_bound_item_attestation_and_approval(self) -> None:
        run_id = "run-test"
        self._json(f"文档/证据/运行/{run_id}/run_input_snapshot.json", {"run_id": run_id})
        self._json(f"文档/证据/运行/{run_id}/scene_source_selection.json", {"run_id": run_id})
        self._json(f"文档/证据/运行资料使用记录/{run_id}.json", {"run_id": run_id})
        self._json("文档/证据/execution_outputs/module_09_scene_prose.json", {"run_id": run_id})
        self._write(f"正文/运行/{run_id}/章节_1.md", "prose")
        source_ref = {"project_id": "p1", "path": "原始资料/资料库.txt", "location": "1.1"}
        evidence = {"run_id": run_id, "runtime_prose_status": "passed", "records": [{"status": "used", "source_id": "lib-1", "source_kind": "library", "source_status": "verified", "source_ref": source_ref}], "prose_files": [{"relative_path": f"正文/运行/{run_id}/章节_1.md", "sha256": sha256_file(self.root / f"正文/运行/{run_id}/章节_1.md")}]} 
        blocked = validate_formal_release(self.root, evidence)
        self.assertEqual("blocked", blocked["status"])
        item = blocked["manifest"]["used_sources"][0]
        attestation = {"schema_version": "source-item-attestation-1.0", "source_id": "lib-1", "source_ref_sha256": item["source_ref_sha256"], "source_content_sha256": item["source_content_sha256"], "decision": "approved", "reviewed_by": "reviewer", "reviewed_at": "2026-08-13T00:00:00Z", "missing_fields": [], "placeholder_matches": []}
        self._write("文档/证据/来源条目认证.jsonl", json.dumps(attestation, ensure_ascii=False) + "\n")
        approval = {"schema_version": "formal-release-approval-1.0", "status": "approved", "approved_by": "reviewer", "approved_at": "2026-08-13T00:00:00Z", "run_id": run_id, "manifest_sha256": blocked["manifest"]["manifest_sha256"], "accepted_fields": ["project_id", "genre_selection", "book_title", "world_stage", "mainline_conflict", "core_mystery", "protagonist", "chapter_plan"], "approved_source_ids": ["lib-1"]}
        self._json("配置/formal_release_approval.json", approval)
        self.assertEqual("approved", validate_formal_release(self.root, evidence)["status"])
        self._write(f"正文/运行/{run_id}/章节_1.md", "changed")
        self.assertEqual("blocked", validate_formal_release(self.root, evidence)["status"])

    def test_formal_release_normalizes_legacy_string_source_ref(self) -> None:
        run_id = "run-legacy-ref"
        self._json(f"文档/证据/运行/{run_id}/run_input_snapshot.json", {"run_id": run_id})
        self._json(f"文档/证据/运行/{run_id}/scene_source_selection.json", {"run_id": run_id})
        self._json(f"文档/证据/运行资料使用记录/{run_id}.json", {"run_id": run_id})
        self._json("文档/证据/execution_outputs/module_09_scene_prose.json", {"run_id": run_id})
        self._write(f"正文/运行/{run_id}/章节_1.md", "prose")
        evidence = {
            "run_id": run_id,
            "runtime_prose_status": "passed",
            "records": [{"status": "used", "source_id": "lib-1", "source_kind": "library", "source_ref": "原始资料/资料库.txt:1.1"}],
            "prose_files": [{"relative_path": f"正文/运行/{run_id}/章节_1.md", "sha256": sha256_file(self.root / f"正文/运行/{run_id}/章节_1.md")}],
        }
        release = validate_formal_release(self.root, evidence)
        self.assertEqual("blocked", release["status"])
        self.assertEqual({"path": "原始资料/资料库.txt", "locator": "1.1"}, release["manifest"]["used_sources"][0]["source_ref"])

    def test_formal_release_requires_confirmed_type_combination(self) -> None:
        run_id = "run-type-selection"
        config_path = self.root / "配置/project_config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["type_combination"] = None
        config["type_selection_policy"] = {"mode": "single_type_draft", "formal_release_allowed": False}
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        self._json(f"文档/证据/运行/{run_id}/run_input_snapshot.json", {"run_id": run_id})
        self._json(f"文档/证据/运行/{run_id}/scene_source_selection.json", {"run_id": run_id})
        self._json(f"文档/证据/运行资料使用记录/{run_id}.json", {"run_id": run_id})
        self._json("文档/证据/execution_outputs/module_09_scene_prose.json", {"run_id": run_id})
        self._write(f"正文/运行/{run_id}/章节_1.md", "prose")
        evidence = {"run_id": run_id, "runtime_prose_status": "passed", "records": [{"status": "used", "source_id": "lib-1", "source_kind": "library", "source_status": "verified", "source_ref": "原始资料/资料库.txt:1.1"}], "prose_files": [{"relative_path": f"正文/运行/{run_id}/章节_1.md", "sha256": sha256_file(self.root / f"正文/运行/{run_id}/章节_1.md")}]} 
        release = validate_formal_release(self.root, evidence)
        self.assertEqual("blocked", release["status"])
        self.assertIn("项目尚未确认 type_combination；完整写作运行不得正式交付", release["blockers"])

    def test_formal_release_defaults_to_authored_run_delivery(self) -> None:
        run_id = "run-default-scope"
        self._json(f"文档/证据/运行/{run_id}/run_input_snapshot.json", {"run_id": run_id})
        self._json(f"文档/证据/运行/{run_id}/scene_source_selection.json", {"run_id": run_id})
        self._json(f"文档/证据/运行资料使用记录/{run_id}.json", {"run_id": run_id})
        self._json("文档/证据/execution_outputs/module_09_scene_prose.json", {"run_id": run_id})
        self._write(f"正文/运行/{run_id}/章节_1.md", "prose")
        evidence = {"run_id": run_id, "runtime_prose_status": "passed", "records": [{"status": "used", "source_id": "lib-1", "source_kind": "library", "source_status": "verified", "source_ref": "原始资料/资料库.txt:1.1"}], "prose_files": [{"relative_path": f"正文/运行/{run_id}/章节_1.md", "sha256": sha256_file(self.root / f"正文/运行/{run_id}/章节_1.md")}]} 
        release = validate_formal_release(self.root, evidence)
        self.assertEqual("authored_run_delivery", release["release_scope"])

    def test_material_batch_scope_is_rejected_by_authored_run_approval(self) -> None:
        release = validate_formal_release(self.root, {}, MATERIAL_BATCH_RELEASE_SCOPE)
        self.assertEqual("blocked", release["status"])
        self.assertEqual(MATERIAL_BATCH_RELEASE_SCOPE, release["release_scope"])
        self.assertIn("全量资料发布预检.py", release["blockers"][0])

    def test_transfer_ignores_non_blocking_final_check_warnings(self) -> None:
        original_root = execution_pipeline.PROJECT_ROOT
        execution_pipeline.set_project_root(self.root)
        try:
            output, _ = execution_pipeline.execute_11({
                "module_outputs": {
                    f"{number:02d}": {"status": "success", "output_files": [str(self.root / "配置/project_config.json")]}
                    for number in range(1, 11)
                },
                "final_check": {
                    "status": "passed",
                    "failed_count": 3,
                    "blocking_failures": [],
                    "formal_delivery_status": "blocked",
                    "formal_release": {"blockers": ["等待人工认证"]},
                },
            })
        finally:
            execution_pipeline.set_project_root(original_root)
        self.assertEqual("passed", output["transfer_status"])
        self.assertEqual(["等待人工认证"], output["delivery_gate"]["formal_release_blockers"])

    def test_scene_prose_integrity_requires_auditable_causal_contract(self) -> None:
        expected = {
            "character_goal": "取得线索", "obstacle": "权限受限", "new_information": "线索可追踪",
            "state_before": "怀疑", "state_after": "确认", "ending": "留下代价", "hook": "进入下一场",
        }
        scene = {
            "paragraphs": ["甲" * 45, "乙" * 45, "丙" * 45, "丁" * 45],
            "source_records": [
                {"source_id": "lib-1", "paragraph_index": index, "prose_location": f"1-S1#paragraphs[{index}]", "translation_evidence": {"trigger": "发现异常", "result": "改变选择"}}
                for index in range(4)
            ],
        }
        result = execution_pipeline.evaluate_scene_prose_integrity(scene, expected)
        self.assertTrue(result["passed"])

        scene["source_records"][3]["paragraph_index"] = 1
        result = execution_pipeline.evaluate_scene_prose_integrity(scene, expected)
        self.assertFalse(result["passed"])
        self.assertEqual([0, 1, 2, 1], result["record_indexes"])

    def test_full_source_prose_plan_quarantines_unauthorized_bindings(self) -> None:
        bindings = {"records": [
            {"binding_id": "TB-1", "source_id": "A", "source_kind": "锚点网络", "name": "回声", "creation_binding": {"creative_strategy": {"semantic_anchor": "声音折返", "source_specific_trigger": "听见回声", "observable_action": "停步辨认", "observable_result": "发现方向", "cost_or_change": "暴露位置", "quality_rule": "进入因果"}}},
            {"binding_id": "TB-2", "source_id": "B", "source_kind": "锚点网络", "name": "裂纹", "model_input_eligible": True, "prose_write_allowed": True, "creation_binding": {"creative_strategy": {"semantic_anchor": "裂纹扩张", "source_specific_trigger": "看见裂纹", "observable_action": "触碰石壁", "observable_result": "禁线松动", "cost_or_change": "手掌受伤", "quality_rule": "进入因果"}}},
        ]}
        plan = build_plan(bindings, batch_size=1, authorized_binding_ids={"TB-2"})
        self.assertEqual(0, plan["queued_count"])
        self.assertEqual(0, plan["batch_count"])
        self.assertEqual(1, plan["quarantined_count"])
        self.assertEqual("TB-1", plan["quarantined_records"][0]["binding_id"])
        self.assertEqual("TB-2", plan["pending_activation_records"][0]["binding_id"])
        self.assertEqual("authorized_pending_matched_creative_need", plan["pending_activation_records"][0]["status"])
        self.assertEqual([], plan["records"])


if __name__ == "__main__":
    unittest.main()