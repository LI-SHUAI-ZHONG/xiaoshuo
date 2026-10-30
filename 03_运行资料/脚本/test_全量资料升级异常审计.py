from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 全量资料升级异常审计 import audit


class ExceptionAuditTests(unittest.TestCase):
    def test_delta_scope_requires_and_audits_exact_selected_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "文档/证据/全量资料升级运行/run-a"
            evidence.mkdir(parents=True)
            bindings = root / "文档/证据/全量资料升级运行/绑定清单索引.jsonl"
            bindings.write_text(json.dumps({"binding_id": "TB-1"}) + "\n", encoding="utf-8")
            manifest = {"run_id": "run-a", "binding_baseline_sha256": "a" * 64, "status_counts": {"quarantined": 1}}
            record = {"binding_id": "TB-1", "terminal_status": "quarantined", "source_id": "A", "source_kind": "资料库", "source_ref": {}, "errors": ["source_ref 无效"]}
            (evidence / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (evidence / "records.jsonl").write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            ids = root / "ids.txt"
            ids.write_text("TB-1\n", encoding="utf-8")
            import 全量资料升级异常审计 as module
            original_summary = module._binding_summary
            module._binding_summary = lambda _root: (1, "a" * 64)
            try:
                result = audit(root, "run-a", ids)
            finally:
                module._binding_summary = original_summary
        self.assertEqual("binding_id_file", result["audit_scope"])
        self.assertEqual(1, result["selected_binding_id_count"])
        self.assertEqual(1, result["exception_count"])


if __name__ == "__main__":
    unittest.main()