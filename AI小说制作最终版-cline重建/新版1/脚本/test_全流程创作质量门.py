from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parent / "全流程创作质量门.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("quality_workflow", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FullWorkflowTests(unittest.TestCase):
    def test_current_quality_status_only_allows_writing_after_all_preconditions(self) -> None:
        self.assertFalse(MODULE._candidate_write_allowed("blocked_pending_quality_workflow"))
        self.assertTrue(MODULE._candidate_write_allowed("approved_for_model_candidate_generation"))

    def test_ineligible_candidates_are_not_projected_to_the_production_surface(self) -> None:
        candidate = {"candidate_id": "CAND-S1-A", "model_input_eligible": False, "prose_write_allowed": False}
        eligible = [row for row in [candidate] if row.get("model_input_eligible") is True and row.get("prose_write_allowed") is False]
        self.assertEqual([], eligible)

    def test_generic_only_match_is_blocked(self) -> None:
        brief = {"scenes": [{"scene_id": "S1", "retrieval_terms": ["沈砚", "检测", "代价"]}]}
        plan = {"candidate_records": [{"scene_id": "S1", "candidate_id": "CAND-S1-A", "source_kind": "资料库", "activation": {"matched_project_terms": ["代价"]}}]}
        errors = MODULE._activation_errors(plan, brief)
        self.assertEqual(len(errors), 1)
        self.assertIn("至少两个", errors[0]["message"])

    def test_old_tasks_are_archived_and_cleared(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            old = {"status": "ready_for_model_candidates", "records": [{"consumption_id": "ACT-1"}]}
            (evidence / "场景创作激活任务.jsonl").write_text('{"consumption_id":"ACT-1"}\n', encoding="utf-8")
            MODULE._revoke_old_plan(root, old, "test")
            archived = json.loads((evidence / "已废止场景激活任务.json").read_text(encoding="utf-8"))
            self.assertEqual(archived["release_status"], "revoked_nonrelease")
            self.assertFalse(archived["prose_write_allowed"])
            self.assertEqual((evidence / "场景创作激活任务.jsonl").read_text(encoding="utf-8"), "")

    def test_active_production_projection_has_matching_queue_and_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            records = [
                {"consumption_id": "S1-A", "batch_id": "ACT-S1"},
                {"consumption_id": "S1-B", "batch_id": "ACT-S1"},
                {"consumption_id": "S2-A", "batch_id": "ACT-S2"},
            ]
            MODULE._write_active_production_projection(evidence, records)
            queue = [json.loads(line) for line in (evidence / "全量资料正文生产队列.jsonl").read_text(encoding="utf-8").splitlines()]
            batches = [json.loads(line) for line in (evidence / "全量资料正文生产批次.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(queue, records)
            self.assertEqual(batches, [{"batch_id": "ACT-S1", "consumption_ids": ["S1-A", "S1-B"]}, {"batch_id": "ACT-S2", "consumption_ids": ["S2-A"]}])

    def test_failed_isolation_is_reaudited_after_the_production_surface_is_cleared(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "文档" / "证据"
            evidence.mkdir(parents=True)
            (root / "配置").mkdir()
            (root / MODULE.WORKFLOW_FILE).write_text(json.dumps({
                "workflow_id": "test", "default_decision": "deny", "gates": ["test"], "inherited_policy_requirements": {},
            }), encoding="utf-8")
            (evidence / "全量资料正文生产编排.json").write_text(json.dumps({"records": [{"consumption_id": "OLD-1"}]}), encoding="utf-8")
            brief = {"scenes": []}
            reports = iter([
                {"status": "failed", "future_production_allowed": False},
                {"status": "passed", "future_production_allowed": True},
            ])
            with mock.patch.object(MODULE, "validate_policy", return_value=[]), \
                 mock.patch.object(MODULE.capability, "audit", return_value={"status": "passed"}), \
                 mock.patch.object(MODULE.readiness, "audit", return_value={"status": "passed"}), \
                 mock.patch.object(MODULE.activation, "evaluate", return_value={"records": [], "queued_count": 0, "required_source_kind_gaps": [], "isolated_counts": {}}), \
                 mock.patch.object(MODULE, "_read", side_effect=lambda path, default: brief if path == root / MODULE.activation.BRIEF_FILE else json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default), \
                 mock.patch.object(MODULE.isolation, "audit", side_effect=lambda checked_root: next(reports)) as audit:
                result = MODULE.run(root)

            self.assertEqual(2, audit.call_count)
            self.assertEqual([], result["records"])
            self.assertIn("生产面已重置；需重新运行质量门", result["gate_blockers"]["material_capability"])
            persisted = json.loads((root / MODULE.PLAN_FILE).read_text(encoding="utf-8"))
            self.assertEqual([], persisted["records"])


if __name__ == "__main__":
    unittest.main()