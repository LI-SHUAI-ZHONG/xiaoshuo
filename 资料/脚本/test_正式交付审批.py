from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("正式交付审批.py")
SPEC = importlib.util.spec_from_file_location("formal_release", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GoldenChapterReleaseGateTests(unittest.TestCase):
    def test_short_project_and_unconfirmed_story_core_block_long_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "配置" / "project_config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({"target_chapter_count": 1}), encoding="utf-8")
            errors = MODULE._long_lineage_errors(root)
            self.assertIn("target_chapter_count 至少为 3", errors[0])
            self.assertIn("故事核心尚未取得作者确认", errors[1])

    def test_confirmed_three_chapter_scope_passes_long_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "配置" / "project_config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({
                "project_id": "p-1",
                "target_chapter_count": 3,
                "story_core_confirmation": {
                    "status": "confirmed",
                    "confirmation_id": "confirm-1",
                    "confirmed_by": "author",
                    "confirmed_at": "2026-08-30T00:00:00Z",
                    "project_id": "p-1",
                },
            }), encoding="utf-8")
            self.assertEqual([], MODULE._long_lineage_errors(root))

    def test_missing_golden_report_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                ["缺少三章金样本跨章质量报告"],
                MODULE._golden_three_chapter_errors(Path(directory)),
            )

    def test_failed_cross_chapter_gate_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "文档" / "证据" / "三章金样本" / "三章金样本验证报告.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "chapter_count": 3,
                "status": "blocked",
                "cross_chapter_gate": {"status": "blocked"},
            }), encoding="utf-8")
            errors = MODULE._golden_three_chapter_errors(Path(directory))
            self.assertIn("三章金样本逐章质量门未通过", errors)
            self.assertIn("三章金样本跨章状态递进门未通过", errors)

    def test_passed_cross_chapter_gate_does_not_add_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "文档" / "证据" / "三章金样本" / "三章金样本验证报告.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "chapter_count": 3,
                "status": "planning_gate_passed",
                "cross_chapter_gate": {"status": "passed"},
            }), encoding="utf-8")
            self.assertEqual([], MODULE._golden_three_chapter_errors(Path(directory)))

    def test_legacy_shared_prose_does_not_satisfy_current_run_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "文档" / "证据" / "execution_outputs" / "module_09_scene_prose.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps({"run_id": "run-legacy", "scenes": [{"paragraphs": ["旧正文"], "source_records": []}]}), encoding="utf-8")
            result = MODULE.validate_formal_release(root, {"run_id": "run-current", "runtime_prose_status": "passed"})
            self.assertFalse(result["formal_release_allowed"])
            self.assertIn("缺少本次运行证据", "；".join(result["blockers"]))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "文档" / "证据" / "运行" / "run-1" / "module_outputs"
            run_dir.mkdir(parents=True)
            (run_dir / "module_09_scene_prose.json").write_text(json.dumps({"run_id": "run-1", "scenes": [{"scene_id": "S1", "paragraphs": ["实际正文段落。"], "source_records": []}]}), encoding="utf-8")
            result = MODULE.validate_formal_release(root, {"run_id": "run-1"})
            self.assertIn("缺少本次运行正文资料职责回执", result["blockers"])
            self.assertFalse(result["formal_release_allowed"])


if __name__ == "__main__":
    unittest.main()