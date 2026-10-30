from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("来源质量自主分析.py")
SPEC = importlib.util.spec_from_file_location("source_quality_analysis", MODULE_PATH)
assert SPEC and SPEC.loader
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


class SourceQualityAnalysisTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def test_library_requires_full_object_level_backfill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            self._write(evidence / "来源深度检查报告.json", "", {})
            (evidence / "资料库依赖分类日志.jsonl").write_text(
                '{"entry_id":"one"}\n', encoding="utf-8"
            )
            (evidence / "资料库示例修复日志.jsonl").write_text(
                '{"entry_id":"one"}\n', encoding="utf-8"
            )
            self._write(
                root,
                "文档/证据/全量资料治理/全量检查报告.json",
                {"summary": {"资料库": {"status": "passed", "pending": 0, "blocking": 0}}},
            )
            coverage = ANALYZER._coverage_evidence(root, "资料库.txt", 2)
            self.assertEqual(coverage["covered_fields"], [])

    def test_duplicate_library_ids_do_not_count_as_complete_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (evidence / "资料库依赖分类日志.jsonl").write_text(
                '{"entry_id":"one"}\n{"entry_id":"one"}\n', encoding="utf-8"
            )
            (evidence / "资料库示例修复日志.jsonl").write_text(
                '{"entry_id":"one"}\n{"entry_id":"two"}\n', encoding="utf-8"
            )
            self._write(root, "文档/证据/全量资料治理/全量检查报告.json", {"summary": {"资料库": {"status": "passed", "pending": 0, "blocking": 0}}})
            coverage = ANALYZER._coverage_evidence(root, "资料库.txt", 2)
            self.assertEqual(coverage["covered_fields"], ["examples"])

    def test_anchor_requires_both_evidence_logs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (evidence / "锚点网络场景绑定日志.jsonl").write_text(
                '{"anchor_id":"A1"}\n{"anchor_id":"A2"}\n', encoding="utf-8"
            )
            (evidence / "锚点网络定义日志.jsonl").write_text(
                '{"anchor_id":"A1"}\n{"anchor_id":"A2"}\n', encoding="utf-8"
            )
            self._write(root, "文档/证据/全量资料治理/全量检查报告.json", {"summary": {"锚点网络": {"status": "passed", "pending": 0, "blocking": 0}}})
            coverage = ANALYZER._coverage_evidence(root, "锚点网络.txt", 2)
            self.assertEqual(coverage["covered_fields"], ["anchor_definition", "scene_binding"])

    def test_type_profile_does_not_claim_unsupported_reader_params(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(
                root,
                "配置/类型配置模板.json",
                {"types": {"玄幻": {"core_elements": ["修炼"], "reader_params": {"status": "pending"}}}},
            )
            self._write(
                root,
                "文档/证据/全量资料治理/全量检查报告.json",
                {"summary": {"类型系统": {"status": "passed", "pending": 0, "blocking": 0}}},
            )
            coverage = ANALYZER._coverage_evidence(root, "类型系统.txt", 1)
            self.assertEqual(coverage["covered_fields"], ["core_elements", "style_constraints"])


if __name__ == "__main__":
    unittest.main()