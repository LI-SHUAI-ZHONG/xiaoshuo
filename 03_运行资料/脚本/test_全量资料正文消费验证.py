from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("全量资料正文消费验证.py")
SPEC = importlib.util.spec_from_file_location("full_source_prose_consumption_validation", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FullSourceProseConsumptionValidationTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def _record(self, paragraph: str) -> dict[str, object]:
        return {"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "prose_location": "正文/第一章.md#lines[1]", "paragraph": paragraph, "paragraph_sha256": hashlib.sha256(paragraph.encode("utf-8")).hexdigest(), "quality_status": "semantic_editorial_review_passed", "literary_review_status": "semantic_editorial_review_passed", "trigger": "雨声敲在瓦上", "action": "沈砚合上木匣", "observable_result": "门外脚步停住", "cost_or_change": "他失去了退路", "semantic_support": "把规则转化为门外脚步停住的危机。"}

    def _validate(self, paragraph: str, mutate=None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self._record(paragraph)
            if mutate:
                mutate(row)
            self._write(root, "文档/证据/全量资料正文生产编排.json", {
                "scene_formal_creation_gates": {"S01": {"formal_creation_allowed": True, "blockers": []}},
                "records": [{
                    "consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "scene_id": "S01",
                    "status": "queued_for_authored_prose", "prose_write_allowed": True,
                    "causal_contract": {"semantic_anchor": "雨声敲在瓦上，门外脚步停住，危机逼近"},
                }],
            })
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [row]})
            prose = root / "正文/第一章.md"; prose.parent.mkdir(parents=True); prose.write_text(str(row["paragraph"]) + "\n", encoding="utf-8")
            return MODULE.validate(root)

    def test_rejects_metadata_rule_repetition_and_truncation(self) -> None:
        for paragraph, expected in (("雨声敲在瓦上，沈砚合上木匣，门外脚步停住，他失去了退路。source", "内部术语"), ("雨声敲在瓦上，门外脚步停住，危机逼近。沈砚合上木匣，门外脚步停住，他失去了退路。", "复述资料"), ("雨声敲在瓦上，沈砚合上木匣，门外脚步停住，他失去了退路", "截断")):
            with self.subTest(expected=expected):
                report = self._validate(paragraph)
                self.assertIn(expected, str(report["findings"]))

    def test_rejects_forged_review_and_hash_mismatch(self) -> None:
        paragraph = "雨声敲在瓦上，沈砚合上木匣，门外脚步停住，他失去了退路。"
        report = self._validate(paragraph, lambda row: row.update({"quality_status": "semantic_editorial_review_passed", "literary_review_status": "pending_human_literary_review", "paragraph_sha256": "0" * 64}))
        self.assertIn("哈希不一致", str(report["findings"]))
        self.assertIn("未通过来源语义与叙事质量审校", str(report["findings"]))

    def test_scene_approval_does_not_require_full_material_release_gate(self) -> None:
        paragraph = "雨声敲在瓦上，沈砚合上木匣，门外脚步停住，他失去了退路。随后他把沾水的木匣塞进衣襟，绕开了守在廊下的巡夜弟子，许照微在后方替他拖住了问话。"
        report = self._validate(paragraph)
        self.assertEqual(1, report["planned_count"])
        self.assertNotIn("正式创作门未通过", str(report["findings"]))

    def test_run_scoped_validation_rejects_missing_or_wrong_packet(self) -> None:
        paragraph = "雨声敲在瓦上，沈砚合上木匣，门外脚步停住，他失去了退路。随后他把木匣藏入衣襟，转身走向唯一亮着灯的长廊。"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self._record(paragraph)
            row.update({"scene_id": "S01", "run_id": "run-current", "package_id": "packet-current", "continuity_hash": "chain-current"})
            self._write(root, "文档/证据/全量资料正文生产编排.json", {
                "scene_formal_creation_gates": {"S01": {"formal_creation_allowed": True, "blockers": []}},
                "records": [{"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "scene_id": "S01", "status": "queued_for_authored_prose", "prose_write_allowed": True, "causal_contract": {"semantic_anchor": ""}}],
            })
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [row]})
            self._write(root, "文档/证据/运行/run-current/全量资料正文生产编排.json", {
                "scene_formal_creation_gates": {"S01": {"formal_creation_allowed": True, "blockers": []}},
                "records": [{"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "scene_id": "S01", "status": "queued_for_authored_prose", "prose_write_allowed": True, "causal_contract": {"semantic_anchor": ""}}],
            })
            self._write(root, "文档/证据/运行/run-current/全量资料正文消费证据.json", {"records": [row]})
            prose = root / "正文/第一章.md"; prose.parent.mkdir(parents=True); prose.write_text(paragraph + "\n", encoding="utf-8")
            result = MODULE.validate(root, "run-current")
            self.assertIn("缺少运行资料包", str(result["findings"]))
            packet = root / "文档/证据/运行/run-current/运行资料包.json"
            packet.parent.mkdir(parents=True, exist_ok=True)
            packet.write_text(json.dumps({"run_id": "run-current", "package_id": "packet-other", "records": [{"binding_id": "TB-1", "scene_id": "S01", "package_id": "packet-other", "duty_status": "prose_used", "prose_write_allowed": True, "material_duty": {"prose_evidence_required": True}}]}, ensure_ascii=False), encoding="utf-8")
            result = MODULE.validate(root, "run-current")
            self.assertIn("package_id 与当前冻结资料包不一致", str(result["findings"]))


if __name__ == "__main__":
    unittest.main()