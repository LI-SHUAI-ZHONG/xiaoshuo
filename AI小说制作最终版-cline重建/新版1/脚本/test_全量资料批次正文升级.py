from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


PATH = Path(__file__).with_name("全量资料批次正文升级.py")
sys.path.insert(0, str(PATH.parent))
SPEC = importlib.util.spec_from_file_location("full_source_batch_upgrade", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FullSourceBatchUpgradeAuthorizationTests(unittest.TestCase):
    def _model_fixture(self) -> tuple[dict, dict, dict]:
        row = {"consumption_id": "PC-1", "causal_contract": {"semantic_anchor": "门外的雨声"}}
        binding = {"semantic_interpretation": {"source_meaning": "关系变化"}}
        context = {"protagonist": "沈砚", "companion": "陆昭", "recorder": "许照微", "authority": "闻执衡", "world_rule": "灵息有其边界"}
        return row, binding, context

    def test_local_field_quotes_are_nonempty_and_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir(parents=True)
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            row, binding, context = self._model_fixture()
            parts = ["外门检测场的风卷起砂砾，沈砚看见检测石亮起冷光。", "沈砚按住陆昭的手，将半枚阵钥贴上裂纹。", "石缝随即渗出潮水，远处镇潮阵的一盏灯暗了下去。", "陆昭因替他遮掩被记入违令名册，妹妹药额也被暂扣。"]
            paragraph = "".join(parts)
            with patch.object(MODULE, "generate_text", side_effect=[(part, {"model": "test"}) for part in parts]):
                produced, fields, _ = MODULE._model_paragraph(root, row, binding, context)
            self.assertEqual(paragraph, produced)
            for key in ("trigger", "action", "observable_result", "cost_or_change"):
                self.assertTrue(fields[key])
                self.assertIn(fields[key], paragraph)

    def test_model_retries_short_plain_text_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir(parents=True)
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            row, binding, context = self._model_fixture()
            parts = ["外门检测场的风吹得衣角发紧，沈砚看见检测石亮起冷光。", "沈砚按住陆昭的手，将半枚阵钥贴上裂纹。", "石缝随即渗出潮水，镇潮阵的一盏灯暗了下去。"]
            invalid_cost = "闻执衡在廊外停下，陆昭只能继续观察病情。"
            repaired = "陆昭因遮掩被记入违令名册，妹妹当夜的药额也被暂扣。"
            with patch.object(MODULE, "generate_text", side_effect=[*( (part, {}) for part in parts), (invalid_cost, {}), (repaired, {})]) as generate:
                produced, _, _ = MODULE._model_paragraph(root, row, binding, context)
            self.assertEqual("".join(parts) + repaired, produced)
            self.assertEqual(5, generate.call_count)

    def test_model_repairs_missing_action_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir(parents=True)
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            row, binding, context = self._model_fixture()
            trigger = "冷风掠过石阶，沈砚看见阵纹渗出一线幽蓝微光。"
            invalid_action = "陆昭在廊下屏住呼吸，等待他作出决定。"
            result = "石阶上的阵纹随即亮起，回廊尽头的玉灯轻轻震动。"
            cost = "陆昭因替他遮掩被记入违令名册，妹妹药额也被暂扣。"
            repaired_action = "沈砚按住石阶裂纹，将半枚阵钥贴上潮湿符纸。"
            with patch.object(MODULE, "generate_text", side_effect=[(trigger, {}), (invalid_action, {}), (result, {}), (cost, {}), (repaired_action, {})]) as generate:
                produced, fields, metadata = MODULE._model_paragraph(root, row, binding, context)
            self.assertEqual(trigger + repaired_action + result + cost, produced)
            self.assertIn(fields["action"], repaired_action)
            self.assertEqual("four_stage_model_prose_repaired", metadata["generation_strategy"])
            self.assertEqual(5, generate.call_count)

    def test_retries_only_malformed_json_responses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(MODULE, "generate_json", side_effect=[MODULE.TextGenerationError("模型未返回有效 JSON，未写入正文。"), ({"paragraph": "ok"}, {"model": "test"})]) as generate:
                response, metadata = MODULE._generate_valid_json(root, "system", "prompt")
            self.assertEqual("ok", response["paragraph"])
            self.assertEqual("test", metadata["model"])
            self.assertEqual(2, generate.call_count)

    def test_does_not_retry_model_transport_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(MODULE, "generate_json", side_effect=MODULE.TextGenerationError("模型请求失败：timeout")) as generate, self.assertRaisesRegex(MODULE.TextGenerationError, "timeout"):
                MODULE._generate_valid_json(root, "system", "prompt")
            self.assertEqual(1, generate.call_count)

    def test_model_accepts_fields_quoted_from_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir(parents=True)
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            row, binding, context = self._model_fixture()
            parts = ["雨声落在石阶上，沈砚看见门框裂纹渗出冷雾。", "沈砚推开木门，抬手按住裂纹并贴进半枚阵钥。", "门后的阵纹亮起冷光，巡夜铃随即在旧域外廊震动。", "陆昭因替他遮掩被记入违令名册，失去当夜药额资格。"]
            paragraph = "".join(parts)
            with patch.object(MODULE, "generate_text", side_effect=[(part, {"model": "test"}) for part in parts]):
                result = MODULE._model_paragraph(root, row, binding, context)
            self.assertEqual(paragraph, result[0])

    def test_model_prompts_include_each_causal_contract_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir(parents=True)
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            row, binding, context = self._model_fixture()
            row["activation"] = {"creative_need": "保留异常证据并承担晋升资格受损的代价"}
            row["causal_contract"].update({"trigger": "触发约束", "required_action": "行动约束", "required_result": "结果约束", "required_cost_or_change": "代价约束"})
            parts = ["石阶下传来异响，沈砚看见阵纹渗出幽蓝微光，冷意沿着鞋底爬上来。", "沈砚按住裂纹，将半枚阵钥贴上符纸，命陆昭守住廊口。", "玉灯随即亮起，回廊尽头的石阶轻轻震动，墙上旧纹逐寸显出。", "陆昭被记入违令名册，失去当夜晋升复核资格，药额也被暂扣。"]
            with patch.object(MODULE, "generate_text", side_effect=[(part, {"model": "test"}) for part in parts]) as generate:
                MODULE._model_paragraph(root, row, binding, context)
            prompts = [call.args[2] for call in generate.call_args_list]
            for value, prompt in zip(("触发约束", "行动约束", "结果约束", "代价约束"), prompts):
                self.assertIn(value, prompt)

    def test_extracts_quotes_without_rewriting_valid_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir(parents=True)
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            row, binding, context = self._model_fixture()
            parts = ["雨声落在石阶上，沈砚看见门框裂纹渗出冷雾。", "沈砚推开木门，抬手按住裂纹并贴进半枚阵钥。", "门后的阵纹亮起冷光，巡夜铃随即在旧域外廊震动。", "陆昭因替他遮掩被记入违令名册，失去当夜药额资格。"]
            paragraph = "".join(parts)
            with patch.object(MODULE, "generate_text", side_effect=[(part, {"model": "writer"}) for part in parts]) as generate:
                result = MODULE._model_paragraph(root, row, binding, context)
            self.assertEqual(paragraph, result[0])
            self.assertEqual("沈砚推开木门", result[1]["action"])
            self.assertEqual("writer", result[2]["model"])
            self.assertEqual(4, generate.call_count)

    def test_old_or_blocked_plan_cannot_authorize_prose(self) -> None:
        with self.assertRaisesRegex(ValueError, "没有获得场景正式创作批准"):
            MODULE._require_quality_workflow({"schema_version": "full-source-prose-production-plan-activation-1.0"}, False)
        with self.assertRaisesRegex(ValueError, "现行场景创作激活方案"):
            MODULE._require_quality_workflow({"schema_version": "scene-to-release-quality-plan-1.0", "prose_write_allowed": False}, False)

    def test_selected_consumption_id_must_belong_to_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (root / "配置").mkdir()
            (root / "配置" / "文本生成模型.json").write_text(json.dumps({"generation_policy": {"minimum_paragraph_characters": 80}}), encoding="utf-8")
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": []}), encoding="utf-8")
            (evidence / "全量资料正文生产编排.json").write_text(json.dumps({"records": [{"consumption_id": "PC-1", "batch_id": "B-1"}]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "消费记录不存在或不属于所选批次"):
                MODULE.run(root, ["B-1"], consumption_ids=["PC-2"])

    def test_model_requires_approved_quality_gate_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "现行场景创作激活方案"):
            MODULE._require_quality_workflow({"schema_version": "scene-to-release-quality-plan-1.0", "prose_write_allowed": True, "model_input_allowed": True, "status": "ready_for_model_candidates"}, True)

    def test_deterministic_template_is_written_only_to_nonrelease_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"; evidence.mkdir(parents=True)
            row = {"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "scene_id": "SC-1", "batch_id": "BATCH-0001", "status": "queued_for_authored_prose", "model_input_eligible": True, "prose_write_allowed": True, "causal_contract": {}}
            binding = {"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": True, "prose_write_allowed": True, "creation_binding": {}}
            grant = {"schema_version": "full-source-model-input-prose-authorization-1.0", "binding_id": "TB-1", "source_id": "S-1", "source_ref_sha256": hashlib.sha256(b"source/1").hexdigest(), "model_input_eligible": True, "prose_write_allowed": True, "authorization_scope": "第一章场景 SC-1", "authorized_by": "test-editor", "authorized_at": "2026-08-13T00:00:00Z", "authorization_rationale": "测试已审计逐条授权。"}
            (evidence / "全量资料正文生产编排.json").write_text(json.dumps({"records": [row]}, ensure_ascii=False), encoding="utf-8")
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": [binding]}, ensure_ascii=False), encoding="utf-8")
            grant_path = evidence / "全量资料输入与正文授权" / "已审计授权清单.jsonl"; grant_path.parent.mkdir(parents=True); grant_path.write_text(json.dumps(grant, ensure_ascii=False) + "\n", encoding="utf-8")
            result = MODULE.run(root, ["BATCH-0001"])
            self.assertEqual("deterministic_template_nonrelease", result["quality_status"])
            self.assertTrue((root / "非正式草稿" / "全量资料确定性模板" / "BATCH-0001.md").is_file())
            self.assertFalse((evidence / "全量资料正文消费证据.json").exists())
            self.assertFalse((evidence / "全量资料升级档案.jsonl").exists())

    def test_rejects_tampered_plan_without_binding_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            row = {
                "consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "source_kind": "资料库",
                "batch_id": "BATCH-0001", "status": "queued_for_authored_prose", "model_input_eligible": True, "prose_write_allowed": True,
                "causal_contract": {},
            }
            (evidence / "全量资料正文生产编排.json").write_text(json.dumps({"records": [row]}, ensure_ascii=False), encoding="utf-8")
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": [{"binding_id": "TB-1", "model_input_eligible": False, "prose_write_allowed": False}]}, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "绑定未获正文生产授权"):
                MODULE.run(root, ["BATCH-0001"])

    def test_rejects_plan_when_mutable_permissions_lack_audited_grant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            row = {
                "consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "source_kind": "资料库",
                "batch_id": "BATCH-0001", "status": "queued_for_authored_prose", "model_input_eligible": True, "prose_write_allowed": True,
                "causal_contract": {},
            }
            (evidence / "全量资料正文生产编排.json").write_text(json.dumps({"records": [row]}, ensure_ascii=False), encoding="utf-8")
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": [{"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": True, "prose_write_allowed": True}]}, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "缺少已审计的逐条使用授权"):
                MODULE.run(root, ["BATCH-0001"])


if __name__ == "__main__":
    unittest.main()