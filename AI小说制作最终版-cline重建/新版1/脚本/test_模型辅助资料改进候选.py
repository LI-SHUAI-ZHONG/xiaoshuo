from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("模型辅助资料改进候选.py")
sys.path.insert(0, str(PATH.parent))
SPEC = importlib.util.spec_from_file_location("material_improvement_candidates", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MaterialImprovementCandidateTests(unittest.TestCase):
    def _root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        records = [
            {"binding_id": "TB-001", "source_id": "one", "source_kind": "资料库", "source_ref": "source.txt#1", "name": "条目", "semantic_interpretation": {"source_meaning": "约束", "source_semantic_anchor": "有代价"}, "creation_binding": {"primary_stage": "剧情创建", "creative_object": "冲突", "creative_action": "体现代价", "creative_strategy": {"quality_rule": "不得复述"}}},
            {"binding_id": "TB-002", "source_id": "two", "source_kind": "类型连接"},
        ]
        evidence = root / "文档" / "证据"
        evidence.mkdir(parents=True)
        (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")
        return root

    def test_writes_candidate_without_changing_binding(self) -> None:
        def generator(*_: object) -> tuple[dict, dict]:
            return {"assessment": "clarify", "diagnosis": "表达泛化", "suggested_revision": "让选择付出可观察代价。", "risk_flags": ["人工核对"], "human_review_action": "核对是否忠实原意"}, {"provider": "test", "model": "test"}
        root = self._root()
        report = MODULE.run(root, generator=generator)
        self.assertEqual(1, report["eligible_binding_count"])
        self.assertEqual(1, report["deferred_type_selection_count"])
        self.assertEqual(1, report["completed_binding_count"])
        self.assertEqual("experimental_nonrelease", report["classification"])
        self.assertTrue(report["may_not_enter_derived_material_batch"])
        self.assertFalse(report["binding_modified"])
        ledger = root / "文档" / "证据" / "模型辅助资料改进候选" / "改进候选台账.jsonl"
        row = json.loads(ledger.read_text(encoding="utf-8").strip())
        self.assertEqual("ready_for_human_review", row["candidate_status"])
        self.assertEqual("experimental_nonrelease", row["classification"])
        self.assertFalse(row["original_source_modified"])

    def test_resume_does_not_call_model_twice(self) -> None:
        calls = 0
        def generator(*_: object) -> tuple[dict, dict]:
            nonlocal calls
            calls += 1
            return {"assessment": "keep", "diagnosis": "可保留", "suggested_revision": "", "risk_flags": [], "human_review_action": "抽检"}, {}
        root = self._root()
        MODULE.run(root, generator=generator)
        report = MODULE.run(root, generator=generator)
        self.assertEqual(1, calls)
        self.assertEqual(0, report["processed_this_run"])


if __name__ == "__main__":
    unittest.main()