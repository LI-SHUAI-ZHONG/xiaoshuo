# -*- coding: utf-8 -*-
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "四网络连接，剧情覆盖"
REPORTS = ROOT / "reports"


class NetworkIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = [
            DATA / "static_connections.full.json",
            DATA / "dynamic_connections.full.json",
            DATA / "node_aliases.json",
        ]
        if not all(path.is_file() for path in required):
            sys.path.insert(0, str(ROOT / "scripts"))
            import generate_network_connections
            generate_network_connections.build_outputs()
        cls.static = json.loads((DATA / "static_connections.full.json").read_text(encoding="utf-8"))
        cls.dynamic = json.loads((DATA / "dynamic_connections.full.json").read_text(encoding="utf-8"))
        cls.aliases = json.loads((DATA / "node_aliases.json").read_text(encoding="utf-8"))
        cls.dynamic_only = json.loads((REPORTS / "dynamic_only_connections.json").read_text(encoding="utf-8"))
        cls.generated = json.loads((REPORTS / "generated_connections_review.json").read_text(encoding="utf-8"))

    def test_dynamic_ids_are_continuous(self):
        self.assertEqual([x["id"] for x in self.dynamic["connections"]], [f"C{i:05d}" for i in range(1, len(self.dynamic["connections"]) + 1)])

    def test_dynamic_original_and_generated_counts_use_arrays(self):
        records = self.dynamic["connections"]
        original = sum(x.get("generated_from_static") is False for x in records)
        generated = sum(x.get("generated_from_static") is True for x in records)
        self.assertGreater(original, 0)
        self.assertGreater(generated, 0)
        self.assertEqual(original + generated, len(records))

    def test_generated_records_use_explicit_derivation_contract(self):
        generated = [x for x in self.dynamic["connections"] if x.get("generated_from_static")]
        self.assertTrue(generated)
        self.assertTrue(all(x.get("needs_review") is False for x in generated))
        self.assertTrue(all(x.get("validation_status") == "derived_contract_validated" for x in generated))
        self.assertTrue(all(x.get("derivation_contract") == "NET-DYNAMIC-DERIVATION-CONTRACT-1.0" for x in generated))

    def test_generated_records_are_complete_contract_rules(self):
        generated = [x for x in self.dynamic["connections"] if x.get("generated_from_static")]
        self.assertEqual(len(generated), 1341)
        self.assertTrue(all(x.get("effect", "").strip() for x in generated))
        self.assertTrue(all(x.get("valid_types") for x in generated))
        self.assertTrue(all(x.get("condition", "").strip() for x in generated))
        self.assertTrue(all(x.get("source_refs") for x in generated))

    def test_aliases_do_not_merge_parent_child_nodes(self):
        exact = self.aliases.get("exact_alias", {})
        self.assertFalse(any("_" in str(k) and "_" in str(v) and k.split("_", 1)[0] == v.split("_", 1)[0] for k, v in exact.items()))
        self.assertTrue(any("身体状态" in " ".join(x["names"]) for x in self.aliases.get("unresolved_similar", [])))

    def test_dynamic_only_classifications_are_explicit(self):
        allowed = {"confirmed_alias_match", "likely_alias_match", "missing_static_connection", "conflicting_semantics", "invalid_or_unclear"}
        self.assertEqual(self.dynamic_only["total"], len(self.dynamic_only["connections"]))
        self.assertTrue(all(x["classification"] in allowed for x in self.dynamic_only["connections"]))

    def test_static_candidates_are_not_formal_connections(self):
        candidates = json.loads((REPORTS / "static_connection_candidates.json").read_text(encoding="utf-8"))
        formal = {(x["source"], x["target"], x["type"]) for x in self.static["connections"]}
        self.assertTrue(all((x["source"], x["target"], x["type"]) in formal for x in candidates["candidates"]))

    def test_index_and_source_index_are_present(self):
        self.assertIn("index", self.dynamic)
        self.assertEqual(len(self.static["connections"]), self.static["total_connections"])
        self.assertEqual(len(self.dynamic["connections"]), self.dynamic["total_connections"])

    def test_original_files_are_not_in_data_outputs(self):
        for path in DATA.glob("*.txt"):
            self.assertNotEqual(path.name, "静态网络.txt")
            self.assertNotEqual(path.name, "动态网络.txt")


if __name__ == "__main__":
    unittest.main()