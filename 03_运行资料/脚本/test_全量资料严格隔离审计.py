from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
PATH = Path(__file__).with_name("全量资料严格隔离审计.py")
SPEC = importlib.util.spec_from_file_location("full_source_strict_isolation_audit", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
QUARANTINE_PATH = Path(__file__).with_name("全量资料历史消费隔离.py")
QUARANTINE_SPEC = importlib.util.spec_from_file_location("full_source_legacy_quarantine", QUARANTINE_PATH)
assert QUARANTINE_SPEC and QUARANTINE_SPEC.loader
QUARANTINE = importlib.util.module_from_spec(QUARANTINE_SPEC)
QUARANTINE_SPEC.loader.exec_module(QUARANTINE)
SYNC_PATH = Path(__file__).with_name("全量资料绑定授权投影同步.py")
SYNC_SPEC = importlib.util.spec_from_file_location("full_source_permission_projection_sync", SYNC_PATH)
assert SYNC_SPEC and SYNC_SPEC.loader
SYNC = importlib.util.module_from_spec(SYNC_SPEC)
SYNC_SPEC.loader.exec_module(SYNC)


class FullSourceStrictIsolationAuditTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, value: object, jsonl: bool = False) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in value) if jsonl else json.dumps(value, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")

    def test_empty_audited_authorization_and_empty_queues_are_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding = {"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": False, "prose_write_allowed": False}
            self._write(root, "文档/证据/全量资料解释词创作绑定.json", {"records": [binding]})
            self._write(root, "文档/证据/全量资料正文生产编排.json", {"records": []})
            self._write(root, "文档/证据/全量资料输入与正文授权/已审计授权清单.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产队列.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产批次.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": []})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [], jsonl=True)

            report = MODULE.audit(root)
            self.assertEqual("passed", report["status"])
            self.assertTrue(report["future_production_allowed"])
            self.assertFalse(report["formal_release_allowed"])

    def test_requires_registered_historical_consumption_to_remain_nonrelease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding = {"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": False, "prose_write_allowed": False}
            self._write(root, "文档/证据/全量资料解释词创作绑定.json", {"records": [binding]})
            self._write(root, "文档/证据/全量资料正文生产编排.json", {"records": []})
            self._write(root, "文档/证据/全量资料输入与正文授权/已审计授权清单.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产队列.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产批次.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [{"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1"}]})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [], jsonl=True)

            report = MODULE.audit(root)
            self.assertEqual("failed", report["status"])
            self.assertTrue(report["future_production_allowed"])
            self.assertFalse(report["formal_release_allowed"])
            self.assertEqual("failed", report["legacy_quarantine_status"])

    def test_registered_historical_consumption_is_not_a_current_production_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding = {"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": False, "prose_write_allowed": False}
            consumption = {"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1"}
            archive = {"consumption_id": "PC-1", "binding_id": "TB-1", "source": {"source_id": "S-1"}}
            self._write(root, "文档/证据/全量资料解释词创作绑定.json", {"records": [binding]})
            self._write(root, "文档/证据/全量资料正文生产编排.json", {"records": []})
            self._write(root, "文档/证据/全量资料输入与正文授权/已审计授权清单.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产队列.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产批次.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [consumption]})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [archive], jsonl=True)
            QUARANTINE.build(root)
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": []})

            report = MODULE.audit(root)
            self.assertEqual("passed", report["legacy_quarantine_status"])
            self.assertTrue(report["future_production_allowed"])
            self.assertFalse(report["formal_release_allowed"])

    def test_rebuild_does_not_quarantine_consumption_added_after_initial_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_consumption = {"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1"}
            first_archive = {"consumption_id": "PC-1", "binding_id": "TB-1", "source": {"source_id": "S-1"}}
            second_consumption = {"consumption_id": "PC-2", "binding_id": "TB-2", "source_id": "S-2"}
            second_archive = {"consumption_id": "PC-2", "binding_id": "TB-2", "source": {"source_id": "S-2"}}
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [first_consumption]})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [first_archive], jsonl=True)

            initial = QUARANTINE.build(root)
            self.assertEqual(["PC-1"], [entry["consumption_id"] for entry in initial["entries"]])

            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [first_consumption, second_consumption]})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [first_archive, second_archive], jsonl=True)
            rebuilt = QUARANTINE.build(root)

            self.assertEqual(1, rebuilt["quarantined_record_count"])
            self.assertEqual(["PC-1"], [entry["consumption_id"] for entry in rebuilt["entries"]])

    def test_opt_in_archive_repair_registers_only_existing_archive_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = {"consumption_id": "RPL-1", "binding_id": "TB-1", "source": {"source_id": "S-1"}}
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": []})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [archive], jsonl=True)

            registry = QUARANTINE.build(root, include_unregistered_archive=True)

            self.assertEqual(1, registry["quarantined_record_count"])
            self.assertEqual("RPL-1", registry["entries"][0]["consumption_id"])
            self.assertIsNone(registry["entries"][0]["consumption_record_sha256"])

    def test_archive_drift_remains_nonrelease_but_is_not_active_production(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding = {"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": False, "prose_write_allowed": False}
            original = {"consumption_id": "PC-1", "binding_id": "TB-1", "source": {"source_id": "S-1"}}
            changed = {"consumption_id": "PC-1", "binding_id": "TB-1", "source": {"source_id": "S-1"}, "legacy_note": "changed"}
            self._write(root, "文档/证据/全量资料解释词创作绑定.json", {"records": [binding]})
            self._write(root, "文档/证据/全量资料正文生产编排.json", {"records": []})
            self._write(root, "文档/证据/全量资料输入与正文授权/已审计授权清单.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产队列.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文生产批次.jsonl", [], jsonl=True)
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": []})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [original], jsonl=True)
            QUARANTINE.build(root, include_unregistered_archive=True)
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [changed], jsonl=True)
            QUARANTINE.build(root)

            report = MODULE.audit(root)
            self.assertEqual("passed", report["legacy_quarantine_status"])
            self.assertTrue(report["future_production_allowed"])

    def test_rejects_historical_record_reentering_current_consumption_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consumption = {"consumption_id": "PC-1", "binding_id": "TB-1", "source_id": "S-1"}
            archive = {"consumption_id": "PC-1", "binding_id": "TB-1", "source": {"source_id": "S-1"}}
            self._write(root, "文档/证据/全量资料正文消费证据.json", {"records": [consumption]})
            self._write(root, "文档/证据/全量资料升级档案.jsonl", [archive], jsonl=True)
            QUARANTINE.build(root)

            errors = MODULE._legacy_quarantine_errors(root / "文档" / "证据", [consumption], [archive], set())
            self.assertIn("历史隔离记录重新进入当前消费证据: PC-1", errors)

    def test_permission_projection_sync_uses_only_the_audited_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding = {"binding_id": "TB-1", "source_id": "S-1", "source_ref": "source/1", "model_input_eligible": False, "prose_write_allowed": False}
            grant = {
                "schema_version": "full-source-model-input-prose-authorization-1.0",
                "binding_id": "TB-1", "source_id": "S-1", "source_ref_sha256": hashlib.sha256(b"source/1").hexdigest(),
                "model_input_eligible": True, "prose_write_allowed": True, "authorization_scope": "test",
                "authorized_by": "tester", "authorized_at": "2026-08-17T00:00:00Z", "authorization_rationale": "test",
            }
            self._write(root, "文档/证据/全量资料解释词创作绑定.json", {"records": [binding]})
            self._write(root, "文档/证据/全量资料输入与正文授权/已审计授权清单.jsonl", [grant], jsonl=True)

            result = SYNC.sync(root)
            projected = json.loads((root / "文档/证据/全量资料解释词创作绑定.json").read_text(encoding="utf-8"))["records"][0]

            self.assertEqual(1, result["authorized_binding_count"])
            self.assertTrue(projected["model_input_eligible"])
            self.assertTrue(projected["prose_write_allowed"])


if __name__ == "__main__":
    unittest.main()