from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("来源语义审校.py")
SPEC = importlib.util.spec_from_file_location("full_source_semantic_editorial_review", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SemanticEditorialReviewTests(unittest.TestCase):
    def _audit(self, paragraph: str) -> tuple[dict, dict]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"; evidence.mkdir(parents=True)
            row = {"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1", "prose_location": "正文/第一章.md#lines[1]", "paragraph": paragraph, "paragraph_sha256": hashlib.sha256(paragraph.encode("utf-8")).hexdigest(), "quality_status": "automatic_draft_requires_semantic_editorial_review", "trigger": "雨声敲在瓦上", "action": "沈砚合上木匣", "observable_result": "门外脚步停住", "cost_or_change": "他失去了退路", "semantic_support": "把规则转化为门外脚步停住的危机。"}
            plan = {"records": [{"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1"}]}
            (evidence / "全量资料正文生产编排.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            (evidence / "全量资料正文消费证据.json").write_text(json.dumps({"records": [row]}, ensure_ascii=False), encoding="utf-8")
            prose = root / "正文" / "第一章.md"; prose.parent.mkdir(parents=True); prose.write_text(paragraph + "\n", encoding="utf-8")
            report = MODULE.audit(root)
            updated = json.loads((evidence / "全量资料正文消费证据.json").read_text(encoding="utf-8"))
            return report, updated["records"][0]

    def test_passes_complete_traceable_draft(self) -> None:
        paragraph = "雨声敲在瓦上，沈砚合上木匣，门外脚步停住。他知道有人已经守在廊下，只能从后窗翻出，至此他失去了退路。" * 4
        report, row = self._audit(paragraph)
        self.assertEqual("passed", report["status"])
        self.assertEqual("semantic_editorial_review_passed", row["quality_status"])

    def test_blocks_internal_rule_leakage(self) -> None:
        paragraph = ("雨声敲在瓦上，沈砚合上木匣，门外脚步停住。他失去了退路。未确认的类型偏好不得自动写入正文。" * 3)
        report, row = self._audit(paragraph)
        self.assertEqual("blocked", report["status"])
        self.assertIn("内部术语或规则", str(report["findings"]))
        self.assertEqual("automatic_draft_requires_semantic_editorial_review", row["quality_status"])


if __name__ == "__main__":
    unittest.main()