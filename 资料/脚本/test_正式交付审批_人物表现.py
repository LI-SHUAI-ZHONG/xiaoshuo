from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("正式交付审批.py")
SPEC = importlib.util.spec_from_file_location("formal_release_performance", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CharacterPerformanceReleaseGateTests(unittest.TestCase):
    def _write_run_evidence(self, root: Path, run_id: str) -> None:
        run_dir = root / "文档" / "证据" / "运行" / run_id
        (run_dir / "module_outputs").mkdir(parents=True)
        (run_dir / "执行消费.jsonl").write_text("{}\n", encoding="utf-8")
        (run_dir / "module_outputs" / "module_09_scene_prose.json").write_text("{}", encoding="utf-8")

    def test_missing_performance_results_block_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                ["缺少步骤 10/11 人物表现结果；交付保持 blocked"],
                MODULE._character_performance_errors(Path(directory)),
            )

    def test_deferred_performance_results_block_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "文档" / "证据" / "全流程人物表现结果.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"status": "deferred", "deferred_count": 5}), encoding="utf-8")
            self.assertEqual(["人物表现结果门未通过或仍存在 deferred 项"], MODULE._character_performance_errors(Path(directory)))

    def test_complete_performance_results_do_not_add_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "文档" / "证据" / "全流程人物表现结果.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"status": "passed", "deferred_count": 0}), encoding="utf-8")
            self.assertEqual([], MODULE._character_performance_errors(Path(directory)))

    def test_capability_layers_keep_literary_review_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_id = "run-test"
            self._write_run_evidence(root, run_id)
            (root / "文档" / "证据" / "三章金样本").mkdir(parents=True)
            (root / "文档" / "证据" / "三章金样本" / "三章金样本验证报告.json").write_text(json.dumps({
                "chapter_count": 3,
                "status": "planning_gate_passed",
                "cross_chapter_gate": {"status": "passed"},
            }), encoding="utf-8")
            performance = root / "文档" / "证据" / "全流程人物表现结果.json"
            performance.write_text(json.dumps({"status": "passed", "deferred_count": 0}), encoding="utf-8")
            manifest = {"run_id": run_id, "used_sources": [{"source_id": "s1"}], "prose_files": [{"relative_path": "正文/运行/run-test/chapter.json"}]}
            layers = MODULE._capability_layers(root, manifest, [], [])
            self.assertTrue(layers["structural_review_passed"]["passed"])
            self.assertFalse(layers["literary_review"]["passed"])
            self.assertEqual("literary_review_pending", layers["literary_review_status"])
            self.assertEqual("release_blocked", layers["release_status"])

    def test_capability_layers_accept_only_same_run_literary_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_id = "run-test"
            self._write_run_evidence(root, run_id)
            report = root / "文档" / "证据" / "运行" / run_id / "文学审校.json"
            report.write_text(json.dumps({"run_id": "old-run", "status": "passed"}), encoding="utf-8")
            manifest = {"run_id": run_id, "used_sources": [{"source_id": "s1"}], "prose_files": [{"relative_path": "正文/运行/run-test/chapter.json"}]}
            layers = MODULE._capability_layers(root, manifest, [], [])
            self.assertEqual("literary_review_pending", layers["literary_review_status"])
            self.assertIn("文学审校报告未绑定当前 run_id", layers["literary_review"]["blockers"])


if __name__ == "__main__":
    unittest.main()