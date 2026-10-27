from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("生成升级能力清单.py")
SPEC = importlib.util.spec_from_file_location("capability_inventory", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpgradeCapabilityInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        increment = self.root / MODULE.INCREMENT_PATH
        increment.mkdir(parents=True)
        changes = [
            {"binding_id": "TB-1", "source_id": "C1", "category": "modified", "fingerprint": {"locator_valid": True, "source_object_sha256": "new", "source_ref_sha256": "ref", "dependency_sha256": "dep"}},
            {"binding_id": "TB-2", "source_id": "bad", "category": "locator_repair", "fingerprint": {"locator_valid": False}},
        ]
        (increment / "changes.jsonl").write_text("".join(json.dumps(row) + "\n" for row in changes), encoding="utf-8")
        mappings = self.root / MODULE.MAPPINGS_PATH
        mappings.parent.mkdir(parents=True)
        mapping = {"binding_id": "TB-1", "mapping_status": "verified_candidate", "derived_original_object_sha256": "old", "derived_original_object": {"file": "原始资料/动态网络.txt", "locator": "C1"}}
        mappings.write_text(json.dumps(mapping, ensure_ascii=False) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_inventory_preserves_evidence_and_blocks_release_without_units(self) -> None:
        result = MODULE.build(self.root)
        self.assertEqual("blocked_pending_verified_upgrade_fields", result["status"])
        rows = [json.loads(line) for line in (Path(result["output"]) / "upgrade_capabilities.jsonl").read_text(encoding="utf-8").splitlines()]
        modified = next(row for row in rows if row["binding_id"] == "TB-1")
        self.assertEqual("dynamic_rule", modified["capability_kind"])
        self.assertEqual("dynamic_rule_capabilities", modified["target_module"])
        self.assertIn("typed_upgrade_semantic_units", modified["required_validation_gates"])
        self.assertEqual("not_eligible", modified["release_eligibility"])

    def test_locator_repair_is_explicitly_blocked(self) -> None:
        result = MODULE.build(self.root)
        rows = [json.loads(line) for line in (Path(result["output"]) / "upgrade_capabilities.jsonl").read_text(encoding="utf-8").splitlines()]
        repair = next(row for row in rows if row["binding_id"] == "TB-2")
        self.assertEqual("blocked_locator_repair", repair["validation_status"])
        self.assertIn("source_ref_resolution", repair["required_validation_gates"])

    def test_readback_verifies_exact_source_range_and_hash(self) -> None:
        source = self.root / "原始资料/动态网络.txt"
        source.parent.mkdir(parents=True)
        source.write_text("SOURCE: C1\n====\n{\"rule_id\": \"C1\", \"effect\": \"change\"}\n", encoding="utf-8")
        mapped_object = {"rule_id": "C1", "effect": "change"}
        mapping = {
            "binding_id": "TB-1", "mapping_status": "verified_candidate", "source_file_sha256": MODULE._file_hash(source),
            "derived_original_object_sha256": MODULE._hash(mapped_object),
            "derived_original_object": {"file": "原始资料/动态网络.txt", "line_start": 1, "line_end": 3, "object": mapped_object},
        }
        mappings = self.root / MODULE.MAPPINGS_PATH
        mappings.write_text(json.dumps(mapping, ensure_ascii=False) + "\n", encoding="utf-8")
        result = MODULE.build(self.root)
        rows = [json.loads(line) for line in (Path(result["output"]) / "upgrade_capabilities.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual("verified_original_object", next(row for row in rows if row["binding_id"] == "TB-1")["original_object_readback"]["status"])

    def test_readback_hash_drift_is_recorded_as_blocking_evidence(self) -> None:
        result = MODULE.build(self.root)
        failures = [json.loads(line) for line in (Path(result["output"]) / "readback_failures.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual("source_file_missing", next(row for row in failures if row["binding_id"] == "TB-1")["reason"])

    def test_valid_mapping_revision_replaces_only_its_bound_base_mapping(self) -> None:
        source = self.root / "原始资料/动态网络.txt"
        source.parent.mkdir(parents=True)
        source.write_text("{\"rule_id\": \"C1\"}\n", encoding="utf-8")
        old_mapping = {"binding_id": "TB-1", "mapping_status": "verified_candidate", "source_file_sha256": MODULE._file_hash(source), "derived_original_object_sha256": "obsolete", "derived_original_object": {"file": "原始资料/动态网络.txt", "line_start": 1, "line_end": 1, "object": {"rule_id": "C1"}}}
        mappings = self.root / MODULE.MAPPINGS_PATH
        mappings.write_text(json.dumps(old_mapping, ensure_ascii=False) + "\n", encoding="utf-8")
        replacement = dict(old_mapping)
        replacement["mapping_status"] = "revalidated_mapping_revision"
        replacement["derived_original_object_sha256"] = MODULE._hash(replacement["derived_original_object"]["object"])
        revision = {"schema_version": "derived-source-mapping-revision-1.0", "binding_id": "TB-1", "superseded_mapping_sha256": MODULE._hash(old_mapping), "replacement_mapping": replacement}
        revision_path = self.root / MODULE.MAPPING_REVISION_PATH
        revision_path.parent.mkdir(parents=True)
        revision_path.write_text(json.dumps(revision, ensure_ascii=False) + "\n", encoding="utf-8")
        result = MODULE.build(self.root)
        rows = [json.loads(line) for line in (Path(result["output"]) / "upgrade_capabilities.jsonl").read_text(encoding="utf-8").splitlines()]
        row = next(row for row in rows if row["binding_id"] == "TB-1")
        self.assertEqual("verified_original_object", row["original_object_readback"]["status"])


if __name__ == "__main__":
    unittest.main()