from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("writing_source_evidence", SCRIPT_DIR / "写作资料证据验证.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceRoleReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.specs = (
            {"role": "text_role", "relative_path": "原始资料/a.txt", "format": "text", "required_markers": "alpha\0beta"},
            {"role": "json_role", "relative_path": "原始资料/b.json", "format": "json", "required_markers": "items"},
        )
        (self.root / "原始资料").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_confirms_readable_sources_with_required_role_markers(self) -> None:
        (self.root / "原始资料" / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        (self.root / "原始资料" / "b.json").write_text(json.dumps({"items": []}), encoding="utf-8")

        report = MODULE.review_source_roles(self.root, self.specs)

        self.assertEqual("passed", report["status"])
        self.assertEqual(2, report["status_counts"]["confirmed"])
        self.assertTrue(Path(report["output"]).is_file())
        self.assertFalse(report["delivery_ready"])

    def test_missing_marker_is_not_found_only_after_successful_read(self) -> None:
        (self.root / "原始资料" / "a.txt").write_text("unrelated", encoding="utf-8")
        (self.root / "原始资料" / "b.json").write_text("{not json", encoding="utf-8")

        report = MODULE.review_source_roles(self.root, self.specs)

        by_role = {record["role"]: record for record in report["records"]}
        self.assertEqual("not_found", by_role["text_role"]["status"])
        self.assertEqual("unconfirmed", by_role["json_role"]["status"])
        self.assertEqual("read", by_role["json_role"]["read_status"])

    def test_read_failure_is_unconfirmed_never_not_found(self) -> None:
        report = MODULE.review_source_roles(self.root, self.specs)

        self.assertEqual("failed", report["status"])
        self.assertTrue(all(record["status"] == "unconfirmed" for record in report["records"]))
        self.assertTrue(all(record["read_status"] == "read_error" for record in report["records"]))


if __name__ == "__main__":
    unittest.main()