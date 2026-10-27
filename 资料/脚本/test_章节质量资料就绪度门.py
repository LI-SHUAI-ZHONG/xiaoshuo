from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("chapter_readiness", SCRIPT_DIR / "章节质量资料就绪度门.py")
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def _complete_record(name: str = "黄金三章") -> dict[str, object]:
    return {
        "binding_id": "TB-00001", "source_id": "123.4_黄金三章", "source_kind": "资料库", "name": name,
        "source_ref": "{'file': '原始资料/资料库.txt', 'locator': '123.4_黄金三章'}",
        "semantic_interpretation": {"source_semantic_anchor": "开篇必须建立冲突与行动后果"},
        "creation_binding": {
            "creative_object": "开篇结构", "creative_action": "建立行动、阻碍和后果",
            "creative_strategy": {field: "可验证内容" for field in GATE.STRATEGY_FIELDS},
            "activation_policy": {"mode": "场景需求匹配", "conditions": ["存在开篇场景需求"], "source_declared_conditions": [], "activation_evidence": ["matched_stage"]},
        },
        "evidence_contract": {field: list(required) for field, required in GATE.EVIDENCE_FIELDS.items()},
    }


class ChapterQualityMaterialReadinessTests(unittest.TestCase):
    def _write(self, root: Path, record: dict[str, object]) -> None:
        (root / "原始资料").mkdir(parents=True)
        (root / "原始资料" / "资料库.txt").write_text("source", encoding="utf-8")
        target = root / "文档" / "证据" / "全量资料解释词创作绑定.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"records": [record]}, ensure_ascii=False), encoding="utf-8")

    def test_complete_opening_method_contract_passes_without_formal_fact_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(root, _complete_record())
            report = GATE.audit(root)
            self.assertEqual("passed", report["status"])
            self.assertEqual(1, report["opening_method_materials"]["ready_count"])
            self.assertFalse(report["formal_fact_eligible"])

    def test_missing_observable_result_is_a_material_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = _complete_record("开篇规则")
            del record["creation_binding"]["creative_strategy"]["observable_result"]  # type: ignore[index]
            self._write(root, record)
            report = GATE.audit(root)
            self.assertEqual("needs_material_upgrade", report["status"])
            self.assertEqual(1, report["gap_count"])
            self.assertIn("创作策略缺少 observable_result", report["failures"][0]["errors"])


if __name__ == "__main__":
    unittest.main()