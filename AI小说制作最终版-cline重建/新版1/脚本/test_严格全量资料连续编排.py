from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from 严格全量资料连续编排 import binding_baseline, load_bindings, next_window, parent_chain_summary, pending_indexes, require_matching_baseline, review_entry, review_records
import 严格全量资料模型升级 as strict


class StrictContinuousUpgradeTests(unittest.TestCase):
    def test_preparing_campaign_state_is_resumable_after_interruption(self) -> None:
        self.assertIn("preparing_parent_index", {"stopped", "preparing_parent_index"})

    def test_pending_indexes_skip_all_terminal_predecessors(self) -> None:
        bindings = [{"binding_id": "TB-1"}, {"binding_id": "TB-2"}, {"binding_id": "TB-3"}]
        self.assertEqual([1], pending_indexes(bindings, {"TB-1": "validated_no_change", "TB-3": "validated_no_change"}))

    def test_pending_indexes_defers_model_error_to_final_quarantine_stage(self) -> None:
        bindings = [{"binding_id": "TB-1"}, {"binding_id": "TB-2"}, {"binding_id": "TB-3"}]
        completed = {
            "TB-1": "validated_no_change",
            "TB-2": "model_error",
            "TB-3": "quarantined",
        }
        self.assertEqual([], pending_indexes(bindings, completed))

    def test_pending_indexes_resume_range_ignores_old_parent_terminals(self) -> None:
        bindings = [{"binding_id": f"TB-{index:05d}"} for index in range(1, 16)]
        statuses = {str(binding["binding_id"]): "validated_no_change" for binding in bindings}
        self.assertEqual([10, 11, 12, 13, 14], pending_indexes(bindings, {}, resume_start=10))
        self.assertEqual([], pending_indexes(bindings, statuses, resume_start=10))

    def test_review_entry_preserves_fail_closed_gates(self) -> None:
        entry = review_entry({"run_id": "R", "binding_id": "TB-1", "terminal_status": "model_error",
                              "deterministic_validation": {"errors": []}, "automatic_validation": {"errors": ["timeout"]},
                              "model_metadata": {"response_sha256": "a" * 64}})
        self.assertEqual("model_error", entry["terminal_status"])
        self.assertEqual(["timeout"], entry["automatic_errors"])
        self.assertFalse(entry["formal_fact_eligible"])
        self.assertFalse(entry["prose_write_allowed"])
        self.assertFalse(entry["formal_release_allowed"])

    def test_review_entry_carries_campaign_baseline(self) -> None:
        baseline = {"baseline_binding_count": 13345, "binding_baseline_sha256": "a" * 64}
        entry = review_entry({"run_id": "R", "binding_id": "TB-1", "terminal_status": "model_error"}, baseline)
        self.assertEqual(baseline["baseline_binding_count"], entry["baseline_binding_count"])
        self.assertEqual(baseline["binding_baseline_sha256"], entry["binding_baseline_sha256"])

    def test_review_entry_handles_null_model_metadata_in_parent_record(self) -> None:
        entry = review_entry({"run_id": "R", "binding_id": "TB-1", "terminal_status": "quarantined",
                              "model_metadata": None})
        self.assertIsNone(entry["response_sha256"])

    def test_parent_chain_summary_streams_statuses_and_latest_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = root / "文档" / "证据" / "全量资料升级运行"
            for run_id, parent, records in (
                ("base", "", [{"binding_id": "TB-1", "terminal_status": "model_error", "model_metadata": None}]),
                ("child", "base", [{"binding_id": "TB-1", "terminal_status": "quarantined"},
                                  {"binding_id": "TB-2", "terminal_status": "validated_no_change"}]),
            ):
                run_dir = runs / run_id
                run_dir.mkdir(parents=True)
                (run_dir / "manifest.json").write_text(json.dumps({"run_id": run_id, "parent_run_id": parent}), encoding="utf-8")
                (run_dir / "records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            statuses, reviews = parent_chain_summary(root, "child", {"baseline_binding_count": 2})
        self.assertEqual({"TB-1": "quarantined", "TB-2": "validated_no_change"}, statuses)
        self.assertEqual(["TB-1"], [entry["binding_id"] for entry in reviews])
        self.assertEqual("quarantined", reviews[0]["terminal_status"])

    def test_baseline_mismatch_fails_closed(self) -> None:
        expected = {"baseline_binding_count": 13345, "binding_baseline_sha256": "a" * 64}
        with self.assertRaises(ValueError):
            require_matching_baseline(expected, {"baseline_binding_count": 13345, "binding_baseline_sha256": "b" * 64}, "test")

    def test_binding_baseline_is_deterministic(self) -> None:
        bindings = [{"binding_id": "TB-1"}, {"binding_id": "TB-2"}]
        self.assertEqual(binding_baseline(bindings), binding_baseline(bindings))

    def test_executor_baseline_drift_prevents_parent_read_and_model_side_effects(self) -> None:
        bindings = [{"binding_id": f"TB-{index:05d}"} for index in range(13345)]
        expected = {"baseline_binding_count": 13345, "binding_baseline_sha256": "0" * 64}
        def loaded_document(path: Path) -> dict[str, object]:
            if path.name == "全量模型资料改进方案.json":
                return {"schema_version": strict.POLICY_SCHEMA, "scope": {"expected_binding_count": 13345}}
            return {"binding_count": 13345, "records": bindings}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(strict, "load_json", side_effect=loaded_document), \
                    patch.object(strict, "validate_chain") as chain, \
                    patch.object(strict, "ollama") as model:
                with self.assertRaisesRegex(ValueError, "冻结基线不一致"):
                    strict.run(root, "child", "parent", 0, 1, expected_baseline=expected)
        chain.assert_not_called()
        model.assert_not_called()

    def test_model_error_completes_first_pass_before_final_quarantine(self) -> None:
        self.assertIn("model_error", __import__("严格全量资料连续编排").COMPLETED_STATUSES)

    def test_bounded_ollama_terminates_a_timed_out_worker(self) -> None:
        class FakeQueue:
            def close(self) -> None:
                pass

        class FakeProcess:
            terminated = False
            exitcode = None

            def start(self) -> None:
                pass

            def join(self, _timeout: object = None) -> None:
                pass

            def is_alive(self) -> bool:
                return True

            def terminate(self) -> None:
                self.terminated = True

        process = FakeProcess()

        class FakeContext:
            queue_maxsize: int | None = None

            def Queue(self, maxsize: int) -> FakeQueue:
                self.queue_maxsize = maxsize
                return FakeQueue()

            def Process(self, **_kwargs: object) -> FakeProcess:
                return process

        context = FakeContext()
        with patch.object(strict.multiprocessing, "get_context", return_value=context):
            reply, error, raw = strict.bounded_ollama({"ollama": {"timeout_seconds": 1}}, {"input": "x"})
        self.assertIsNone(reply)
        self.assertEqual("", raw)
        self.assertIn("TimeoutError", str(error))
        self.assertTrue(process.terminated)
        self.assertEqual(1, context.queue_maxsize)

    def test_review_records_includes_failed_parent_terminal_records(self) -> None:
        records = {
            "TB-8": {"run_id": "parent", "binding_id": "TB-8", "terminal_status": "model_error",
                     "deterministic_validation": {"errors": []}, "automatic_validation": {"errors": ["truncated"]},
                     "model_metadata": {"response_sha256": "b" * 64}},
            "TB-9": {"run_id": "parent", "binding_id": "TB-9", "terminal_status": "validated_no_change"},
        }
        entries = review_records(records)
        self.assertEqual(1, len(entries))
        self.assertEqual("TB-8", entries[0]["binding_id"])
        self.assertEqual("model_error", entries[0]["terminal_status"])

    def test_model_call_error_is_written_as_terminal_model_error(self) -> None:
        bindings = [{"binding_id": f"TB-{index:05d}", "source_ref": {"file": "source.md", "locator": "# Item", "line_start": 1}}
                    for index in range(5)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir()
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (root / "配置" / "全量模型资料改进方案.json").write_text(
                '{"schema_version": "full-source-model-assisted-material-improvement-2.0", "scope": {"expected_binding_count": 5}}', encoding="utf-8")
            (root / "配置" / "文本生成模型.json").write_text('{"ollama": {"model": "test"}}', encoding="utf-8")
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"binding_count": 5, "records": bindings}), encoding="utf-8")
            (root / "source.md").write_text("# Item\ncontent\n", encoding="utf-8")
            with patch.object(strict, "validate_chain"), patch.object(strict, "bounded_ollama", return_value=(None, "TimeoutError", "")):
                manifest = strict.run(root, "child", "parent", 0, 5)
            record = strict.rows(root / "文档" / "证据" / "全量资料升级运行" / "child" / "records.jsonl")[0]
        self.assertEqual("model_error", record["terminal_status"])
        self.assertEqual(["TimeoutError"], record["automatic_validation"]["errors"])
        self.assertEqual({"model_error": 5}, manifest["status_counts"])

    def test_unreadable_source_is_written_as_quarantined_record(self) -> None:
        bindings = [{"binding_id": f"TB-{index:05d}", "source_ref": {"file": "missing.md", "locator": "# Missing", "line_start": 1}}
                    for index in range(5)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "配置").mkdir()
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (root / "配置" / "全量模型资料改进方案.json").write_text(
                '{"schema_version": "full-source-model-assisted-material-improvement-2.0", "scope": {"expected_binding_count": 5}}', encoding="utf-8")
            (root / "配置" / "文本生成模型.json").write_text('{"ollama": {"model": "test"}}', encoding="utf-8")
            (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"binding_count": 5, "records": bindings}), encoding="utf-8")
            with patch.object(strict, "validate_chain"):
                manifest = strict.run(root, "child", "parent", 0, 5)
            records = strict.rows(evidence / "全量资料升级运行" / "child" / "records.jsonl")
        self.assertEqual(5, len(records))
        self.assertEqual({"quarantined": 5}, manifest["status_counts"])

    def test_next_window_requires_contiguous_policy_sized_bindings(self) -> None:
        self.assertEqual((5, 5), next_window([5, 6, 7, 8, 9], 10))
        with self.assertRaises(ValueError):
            next_window([5, 7, 8, 9, 10], 5)
        with self.assertRaises(ValueError):
            next_window([5, 6, 7, 8], 10)

    def test_load_bindings_requires_complete_records_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (evidence / "全量资料解释词创作绑定.json").write_text(
                '{"binding_count": 13345, "records": [{"binding_id": "TB-1"}]}', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_bindings(root)


if __name__ == "__main__":
    unittest.main()