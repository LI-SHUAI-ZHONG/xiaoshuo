from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PATH = Path(__file__).with_name("原版资料升级执行.py")
sys.path.insert(0, str(PATH.parent))
SPEC = importlib.util.spec_from_file_location("upgrade_execute", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OriginalMaterialUpgradeExecutionTests(unittest.TestCase):
    def test_creates_review_only_before_after_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "原始资料" / "动态网络.txt"
            source.parent.mkdir(parents=True)
            before = {"connection_id": "C1", "condition": "条件"}
            source.write_text(json.dumps({"connections": [before]}, ensure_ascii=False), encoding="utf-8")
            bindings = root / MODULE.BINDINGS_PATH
            bindings.parent.mkdir(parents=True)
            bindings.write_text(json.dumps({"binding_status": "verified", "original_object_id": "O1", "original_source_file": "原始资料/动态网络.txt", "original_object_sha256": MODULE._hash(before), "source_id": "C1", "binding_id": "B1", "upgrade_id": "U1"}, ensure_ascii=False) + "\n", encoding="utf-8")
            def fake(_: Path, __: str, ___: str) -> tuple[dict[str, Any], dict[str, str]]:
                return {"rationale": "补充边界", "changes": [{"field_path": "condition", "operation": "replace", "before": "条件", "after": "更明确条件", "reason": "测试"}]}, {"model": "fake"}
            report = MODULE.execute(root, "RUN-1", generator=fake)
            self.assertEqual({"requires_human_review": 1}, report["status_counts"])
            self.assertTrue(report["completed"])
            row = json.loads((root / MODULE.OUTPUT_ROOT / "RUN-1" / "upgrade_records.jsonl").read_text(encoding="utf-8"))
            self.assertFalse(row["writeback_allowed"])
            self.assertEqual("更明确条件", row["upgraded_object"]["condition"])
            self.assertNotIn("field_source", MODULE._review_context({"field_source": {}, "condition": "条件"}))


if __name__ == "__main__":
    unittest.main()