from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import 严格全量资料升级最终审核 as final_audit
from 计划锁与正式创作门 import validate_formal_creation_gate


class FinalAuditTests(unittest.TestCase):
    def build_campaign(self, root: Path, isolated: bool = True) -> str:
        campaign = "campaign"
        runs = root / "文档" / "证据" / "全量资料升级运行"
        campaign_dir = root / "文档" / "证据" / "严格连续资料升级运行" / campaign
        runs.mkdir(parents=True)
        campaign_dir.mkdir(parents=True)
        baseline = {"baseline_binding_count": 5, "binding_baseline_sha256": "a" * 64}
        records = [{"run_id": "b0000", "binding_id": f"TB-{i}", "terminal_status": "model_error" if i == 3 else "validated_no_change"} for i in range(5)]
        (runs / "b0000").mkdir()
        (runs / "b0000" / "records.jsonl").write_text("".join(json.dumps(x) + "\n" for x in records), encoding="utf-8")
        (runs / "b0000" / "manifest.json").write_text(json.dumps({"run_id": "b0000", "parent_run_id": "parent", **baseline, "processed_count": 5, "status_counts": {"validated_no_change": 4, "model_error": 1}}), encoding="utf-8")
        event = {"run_id": "b0000", "parent_run_id": "parent", "start": 0, "count": 5, **baseline, "status_counts": {"validated_no_change": 4, "model_error": 1}}
        (campaign_dir / "batches.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
        (campaign_dir / "state.json").write_text(json.dumps({"started_at": "start"}), encoding="utf-8")
        if isolated:
            (runs / "campaign-q0000").mkdir()
            record = dict(records[3], run_id="campaign-q0000", terminal_status="quarantined", model_metadata={"executed": False, "isolation_source_run_id": "b0000"})
            (runs / "campaign-q0000" / "records.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
            (runs / "campaign-q0000" / "manifest.json").write_text(json.dumps({"run_id": "campaign-q0000", "parent_run_id": "b0000", "execution_mode": "isolate_model_error", "processed_count": 1, "status_counts": {"quarantined": 1}}), encoding="utf-8")
        return campaign

    def test_audit_updates_stale_state_but_keeps_all_gates_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = final_audit.audit(root, self.build_campaign(root))
            state = json.loads((root / "文档" / "证据" / "严格连续资料升级运行" / "campaign" / "state.json").read_text())
        self.assertEqual("audited_complete", result["status"])
        self.assertTrue(result["isolation_coverage_exact"])
        self.assertEqual(1, result["model_error_count"])
        self.assertEqual("audited_complete", state["status"])
        self.assertFalse(state["formal_release_allowed"])

    def test_audit_rejects_missing_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "一一对应"):
                final_audit.audit(root, self.build_campaign(root, isolated=False))

    def test_audit_rejects_campaign_that_starts_after_baseline_origin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.build_campaign(root)
            batches_path = root / "文档" / "证据" / "严格连续资料升级运行" / campaign / "batches.jsonl"
            event = json.loads(batches_path.read_text(encoding="utf-8").strip())
            event["start"] = 1
            batches_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "必须从冻结基线索引 0 开始"):
                final_audit.audit(root, campaign)

    def test_formal_gate_rejects_tail_activity_even_with_bound_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.build_campaign(root)
            batches_path = root / "文档" / "证据" / "严格连续资料升级运行" / campaign / "batches.jsonl"
            event = json.loads(batches_path.read_text(encoding="utf-8").strip())
            event["start"] = 1
            batches_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            audit = {"schema_version": final_audit.SCHEMA_VERSION, "campaign_id": campaign, "status": "audited_complete", "resume_start": 1,
                     "baseline_binding_count": 5, "binding_baseline_sha256": "a" * 64, "first_pass_record_count": 5,
                     "first_pass_status_counts": {"validated_no_change": 5}, "model_error_count": 0,
                     "isolation_record_count": 0, "isolation_coverage_exact": True,
                     "batches_sha256": __import__("hashlib").sha256(batches_path.read_bytes()).hexdigest()}
            campaign_dir = batches_path.parent
            (campaign_dir / "final-audit.json").write_text(json.dumps(audit), encoding="utf-8")
            (campaign_dir / "state.json").write_text(json.dumps({"schema_version": "strict-continuous-source-upgrade-1.0", "campaign_id": campaign, "status": "audited_complete", "final_audit": "final-audit.json", "baseline_binding_count": 5, "binding_baseline_sha256": "a" * 64}), encoding="utf-8")
            approval = {"schema_version": "formal-material-upgrade-approval-1.0", "status": "approved", "approved_by": "reviewer", "approved_at": "now", "strict_campaign_id": campaign,
                        "strict_final_audit_sha256": __import__("hashlib").sha256((campaign_dir / "final-audit.json").read_bytes()).hexdigest()}
            (root / "配置").mkdir()
            (root / "配置" / "formal_material_upgrade_approval.json").write_text(json.dumps(approval), encoding="utf-8")
            gate = validate_formal_creation_gate(root)
        self.assertEqual("blocked", gate["status"])
        self.assertIn("严格连续活动不是从冻结基线起点完成的审核", gate["blockers"])

    def test_formal_gate_requires_activity_approval_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = self.build_campaign(root)
            result = final_audit.audit(root, campaign)
            campaign_dir = root / "文档" / "证据" / "严格连续资料升级运行" / campaign
            approval = {"strict_campaign_id": campaign, "strict_final_audit_sha256": __import__("hashlib").sha256((campaign_dir / "final-audit.json").read_bytes()).hexdigest()}
            (root / "配置").mkdir()
            (root / "配置" / "formal_material_upgrade_approval.json").write_text(json.dumps(approval), encoding="utf-8")
            gate = validate_formal_creation_gate(root)
        self.assertEqual("audited_complete", result["status"])
        self.assertIn("严格连续活动正式事实批准凭证无效", gate["blockers"])


if __name__ == "__main__":
    unittest.main()