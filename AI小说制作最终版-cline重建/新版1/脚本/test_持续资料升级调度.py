from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 持续资料升级调度 import _action, _ledger_row


class ContinuousSourceUpgradeLedgerTests(unittest.TestCase):
    def test_confirmation_categories_use_confirmation_queue(self) -> None:
        action, evidence, _ = _action({"category_id": "candidate_requires_project_confirmation"})
        self.assertEqual("submit_explicit_project_confirmation", action)
        self.assertIn("严格隔离项目确认", evidence)

    def test_identity_missing_uses_bounded_replacement_reaudit(self) -> None:
        action, evidence, _ = _action({"category_id": "candidate_identity_missing"})
        self.assertEqual("submit_independent_bounded_replacement_source", action)
        self.assertIn("严格隔离替代来源重审", evidence)

    def test_missing_boundary_requires_new_replacement(self) -> None:
        row = _ledger_row({"upgrade_id": "SU-1", "category_id": "object_boundary_missing"})
        self.assertEqual("obtain_independent_replacement_source", row["next_action"])
        self.assertFalse(row["formal_fact_eligible"])
        self.assertFalse(row["model_input_eligible"])
        self.assertFalse(row["prose_write_allowed"])

    def test_unknown_category_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            _action({"category_id": "unknown"})


if __name__ == "__main__":
    unittest.main()