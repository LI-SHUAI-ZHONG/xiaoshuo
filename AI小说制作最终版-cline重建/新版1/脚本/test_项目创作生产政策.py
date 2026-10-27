from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("project_policy", SCRIPT_DIR / "项目创作生产政策.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProjectCreativeProductionPolicyTests(unittest.TestCase):
    def test_policy_is_present_and_covers_all_source_kinds(self) -> None:
        root = Path(__file__).parents[1]
        policy = MODULE.validate_policy(root)
        self.assertEqual(MODULE.SOURCE_KINDS, set(policy["source_kinds"]))
        self.assertTrue(policy["hard_boundaries"]["model_required_for_quality_candidate"])
        self.assertTrue(policy["hard_boundaries"]["automatic_validation_required_before_derived_batch"])
        self.assertFalse(policy["hard_boundaries"]["automatic_draft_requires_semantic_and_literary_review"])

    def test_incomplete_binding_is_rejected_before_prose(self) -> None:
        policy = {
            "source_kinds": {kind: "" for kind in MODULE.SOURCE_KINDS},
        }
        with self.assertRaisesRegex(ValueError, "creative_strategy"):
            MODULE.validate_bindings(policy, {"records": [{"source_kind": "资料库", "creation_binding": {}}]})

    def test_type_connections_remain_unconfirmed(self) -> None:
        policy = {"source_kinds": {kind: "" for kind in MODULE.SOURCE_KINDS}}
        strategy = {field: field for field in MODULE.REQUIRED_STRATEGY_FIELDS}
        bindings = {"type_combination_adopted": True, "records": [{
            "source_kind": "类型连接",
            "creation_binding": {"creative_strategy": strategy},
        }]}
        with self.assertRaisesRegex(ValueError, "类型连接"):
            MODULE.validate_bindings(policy, bindings)


if __name__ == "__main__":
    unittest.main()