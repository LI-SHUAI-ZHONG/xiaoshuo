from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 资料资格与合同注册 import build_qualification_ledger, load_qualification_ledger, validate_contract_fields, resolve_contract_fields, CONTRACT_FIELD_VERSION


class MaterialQualificationLedgerTests(unittest.TestCase):
    def test_recomputes_qualification_without_using_binding_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "文档" / "资料库索引.jsonl"
            index.parent.mkdir(parents=True)
            index.write_text(json.dumps({"entry_id": "complete", "usage_method": {"status": "source_complete"}}, ensure_ascii=False) + "\n", encoding="utf-8")
            ledger = build_qualification_ledger(root, [
                {"binding_id": "B1", "source_id": "complete", "source_kind": "资料库", "source_ref": "raw:1", "creation_binding": {"job": "design"}},
                {"binding_id": "B2", "source_id": "pending", "source_kind": "资料库", "source_ref": "raw:2", "creation_binding": {"job": "design"}},
            ])
            self.assertEqual(1, ledger["counts"]["executable_entry"])
            self.assertEqual(1, ledger["counts"]["pending"])
            self.assertEqual("B2", ledger["records"][1]["binding_id"])
            self.assertTrue(ledger["records"][1]["excluded"])

    def test_contract_missing_fields_are_reported_without_legacy_fallback(self) -> None:
        result = validate_contract_fields({"binding_id": "B1", "source_id": "S1"}, "runtime_admission_contract")
        self.assertFalse(result["passed"])
        self.assertEqual(["source_kind", "source_ref"], result["missing"])
        self.assertEqual("material-contract-registry-1.0", result["contract_version"])

    def test_canonical_contract_wins_when_legacy_fields_are_absent(self) -> None:
        row = {
            "contracts": {
                "authorization_contract": {
                    "field_version": CONTRACT_FIELD_VERSION,
                    "fields": {
                        "model_input_eligible": True,
                        "activation_conditions_met": True,
                        "activation_evidence": ["brief:1"],
                    },
                }
            }
        }
        result = resolve_contract_fields(row, "authorization_contract")
        self.assertTrue(result["passed"])
        self.assertTrue(result["fields"]["model_input_eligible"])

    def test_mixed_contract_conflict_is_rejected(self) -> None:
        row = {
            "model_input_eligible": False,
            "activation_conditions_met": True,
            "activation_evidence": ["brief:1"],
            "contracts": {
                "authorization_contract": {
                    "field_version": CONTRACT_FIELD_VERSION,
                    "fields": {
                        "model_input_eligible": True,
                        "activation_conditions_met": True,
                        "activation_evidence": ["brief:1"],
                    },
                }
            },
        }
        result = validate_contract_fields(row, "authorization_contract")
        self.assertFalse(result["passed"])
        self.assertEqual(["model_input_eligible"], result["conflicts"])

    def test_incompatible_field_version_is_reported(self) -> None:
        row = {"contracts": {"authorization_contract": {"field_version": "material-contract-fields-0.9", "fields": {
            "model_input_eligible": True, "activation_conditions_met": True, "activation_evidence": ["brief:1"]
        }}}}
        result = validate_contract_fields(row, "authorization_contract")
        self.assertFalse(result["passed"])
        self.assertIn("字段版本不兼容", result.get("version_error", ""))

    def test_ledger_loader_rejects_missing_or_incompatible_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, digest = load_qualification_ledger(root)
            self.assertIsNone(ledger)
            self.assertEqual("", digest)
            path = root / "文档" / "证据" / "资料资格账本.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"schema_version": "source-qualification-ledger-0.9", "records": []}), encoding="utf-8")
            ledger, digest = load_qualification_ledger(root)
            self.assertIsNone(ledger)
            self.assertEqual(64, len(digest))


if __name__ == "__main__":
    unittest.main()