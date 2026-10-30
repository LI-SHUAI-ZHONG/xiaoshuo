from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 全量资料升级运行报告 import build_report


class UpgradeRunReportTests(unittest.TestCase):
    def test_summarizes_records_and_detects_manifest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档/证据/全量资料升级运行/RUN-1"
            evidence.mkdir(parents=True)
            records = [
                {"binding_id": "A", "source_kind": "资料库", "terminal_status": "validated_no_change", "errors": []},
                {"binding_id": "B", "source_kind": "类型系统", "terminal_status": "quarantined", "errors": ["对象边界不足"]},
            ]
            (evidence / "records.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
            (evidence / "manifest.json").write_text(json.dumps({"run_id": "RUN-1", "records_file": "records.jsonl", "processed_count": 2, "status_counts": {"validated_no_change": 1, "quarantined": 1}}, ensure_ascii=False), encoding="utf-8")
            report = build_report(root, "RUN-1")
            self.assertEqual("consistent", report["status"])
            self.assertEqual(1, report["source_kind_status_counts"]["类型系统"]["quarantined"])
            self.assertEqual("对象边界不足", report["top_errors"][0]["error"])
            manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
            manifest["processed_count"] = 3
            (evidence / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            self.assertEqual("inconsistent", build_report(root, "RUN-1")["status"])