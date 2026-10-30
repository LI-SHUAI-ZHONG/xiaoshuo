from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("原版资料升级审查闸门.py")
SPEC = importlib.util.spec_from_file_location("upgrade_gate", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OriginalMaterialUpgradeReviewGateTests(unittest.TestCase):
    def test_rejects_changes_to_static_derived_fields_and_preserves_safe_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = root / MODULE.EXECUTION_ROOT / "run-1"
            records.mkdir(parents=True)
            rows = [
                {"upgrade_id": "U1", "original_object_id": "O1", "source_id": "C1", "status": "requires_human_review", "before": {"field_source": {"condition": "静态网络对应记录"}}, "changes": [{"field_path": "condition"}]},
                {"upgrade_id": "U2", "original_object_id": "O2", "source_id": "C2", "status": "requires_human_review", "before": {"field_source": {"description": "人工原版条目"}}, "changes": [{"field_path": "description"}]},
            ]
            (records / "upgrade_records.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            report = MODULE.gate(root, "run-1", "gate-1")
            self.assertEqual({"pending_human_review": 1, "rejected_protected_derived_change": 1}, report["decision_counts"])
            decisions = (root / MODULE.OUTPUT_ROOT / "gate-1" / "decisions.jsonl").read_text(encoding="utf-8")
            self.assertIn("静态网络对应记录", decisions)


if __name__ == "__main__":
    unittest.main()