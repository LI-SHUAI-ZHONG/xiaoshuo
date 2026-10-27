from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("历史改进资料化.py")
SPEC = importlib.util.spec_from_file_location("historical_materialization", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HistoricalMaterializationTests(unittest.TestCase):
    def test_covers_every_history_window_and_never_opens_raw_writeback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in MODULE.SOURCE_FILES.values():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source", encoding="utf-8")
            report = MODULE.build(root)
            rows = [json.loads(line) for line in (root / MODULE.OUTPUT_ROOT / "历史改进资料化清单.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(23, report["history_record_count"])
        self.assertEqual([f"{number:03d}" for number in range(1, 24)], [row["history_id"] for row in rows])
        self.assertEqual(0, report["raw_source_writeback_allowed_count"])
        self.assertTrue(all(not row["raw_source_writeback_allowed"] for row in rows))
        self.assertEqual("not_applicable", rows[20]["status"])


if __name__ == "__main__":
    unittest.main()