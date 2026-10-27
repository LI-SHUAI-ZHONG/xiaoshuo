from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 严格隔离可恢复性评估 import _disposition


class StrictQuarantineRecoverabilityTests(unittest.TestCase):
    def test_named_object_block_still_requires_identity_confirmation(self) -> None:
        disposition, _ = _disposition({"category_id": "locator_invalid_or_out_of_range"})
        self.assertEqual("requires_replacement_or_explicit_project_confirmation", disposition)

    def test_unbounded_multi_line_reference_requires_replacement(self) -> None:
        disposition, _ = _disposition({"category_id": "object_boundary_missing"})
        self.assertEqual("permanently_unsuitable_unless_replaced", disposition)


if __name__ == "__main__":
    unittest.main()