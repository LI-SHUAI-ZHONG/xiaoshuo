from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("模型辅助来源资格评估.py")
SPEC = importlib.util.spec_from_file_location("model_qualification_review", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ModelQualificationReviewTests(unittest.TestCase):
    def _root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        evidence = root / "文档" / "证据"
        snapshots = {kind: {"sha256": "a" * 64} for kind in ("资料库", "类型系统", "类型连接", "动态网络", "静态网络", "锚点网络")}
        inventory = {"input_snapshots": snapshots, "by_source_kind": {kind: {"resolved_by_intrinsic_id": 1} for kind in MODULE.SOURCE_FILE_BY_KIND}}
        quality = {"sources": [{"source": file, "parse_status": "parseable", "extractable_rate": 1, "identity_coverage": 1, "evidence_coverage": 1, "source_report_status": "complete", "usage_level": "draft_usable", "missing_fields": [], "governance_evidence": {}, "improvement_actions": []} for file in set(MODULE.SOURCE_FILE_BY_KIND.values())]}
        (evidence / "严格资料升级" / "全量资料激活前置条件盘点").mkdir(parents=True)
        (evidence / "严格资料升级" / "全量资料激活前置条件盘点" / "全量资料激活前置条件盘点报告.json").write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
        (evidence / "来源质量自主分析报告.json").write_text(json.dumps(quality, ensure_ascii=False), encoding="utf-8")
        return root

    def test_model_result_cannot_grant_permissions(self) -> None:
        def generator(*_: object) -> tuple[dict, dict]:
            return {"recommendation": "insufficient_evidence", "confidence": "high", "evidence_ids": ["E1", "E6"], "rationale": "缺少确认", "blocking_gaps": ["来源确认"], "human_review_actions": ["核验版本"]}, {"provider": "test", "model": "test"}
        report = MODULE.review(self._root(), execute_model=True, generator=generator)
        self.assertEqual(0, report["permission_isolation_failure_count"])
        self.assertEqual(7, report["execution_status_counts"]["completed"])

    def test_rejects_model_evidence_outside_package(self) -> None:
        def generator(*_: object) -> tuple[dict, dict]:
            return {"recommendation": "insufficient_evidence", "confidence": "low", "evidence_ids": ["invented"], "rationale": "x", "blocking_gaps": [], "human_review_actions": []}, {}
        report = MODULE.review(self._root(), execute_model=True, generator=generator)
        self.assertEqual(7, report["execution_status_counts"]["model_error"])


if __name__ == "__main__":
    unittest.main()