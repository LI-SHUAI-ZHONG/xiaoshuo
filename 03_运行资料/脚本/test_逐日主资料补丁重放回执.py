from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 逐日主资料补丁重放回执 import (
    RECEIPT_PATH,
    RECOVERY_STATUS_FIELDS,
    SCHEMA_VERSION,
    recovery_gate_status,
    validate,
)


class DailyMainMaterialPatchReplayReceiptTests(unittest.TestCase):
    def test_missing_receipts_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = validate(directory)
        self.assertEqual("blocked", report["status"])
        self.assertIn("缺少或无法解析逐日主资料补丁重放回执", report["errors"])

    def test_continuous_successful_receipts_and_final_hashes_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "脚本/执行管道.py"
            target.parent.mkdir(parents=True)
            target.write_text("final", encoding="utf-8")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            chain = [hashlib.sha256(f"state-{index}".encode()).hexdigest() for index in range(6)]
            receipts = [{"sequence": index, "date": f"2026-08-{21 + index:02d}", "patch_id": f"patch-{index}",
                         "patch_sha256": hashlib.sha256(f"patch-{index}".encode()).hexdigest(), "status": "applied", "exit_code": 0,
                         "pre_state_sha256": chain[index - 1], "post_state_sha256": chain[index]}
                        for index in range(1, 6)]
            document = {"schema_version": SCHEMA_VERSION, "receipts": receipts,
                        "recovery_status": {field: True for field in RECOVERY_STATUS_FIELDS},
                        "final_state": {"state_sha256": chain[-1], "files": [{"path": "脚本/执行管道.py", "sha256": digest}]}}
            receipt_path = root / RECEIPT_PATH
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            self.assertEqual("verified", validate(root)["status"])
            self.assertEqual("verified", validate(root)["recovery_gate_status"])
            document["receipts"][2]["pre_state_sha256"] = "0" * 64
            receipt_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            self.assertEqual("blocked", validate(root)["status"])

    def test_recovery_gate_does_not_infer_missing_or_partial_evidence(self) -> None:
        self.assertEqual("blocked", recovery_gate_status({}))
        self.assertEqual("deferred", recovery_gate_status({
            **{field: True for field in RECOVERY_STATUS_FIELDS},
            "source_reviewed": False,
        }))

    def test_receipt_without_recovery_status_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_path = root / RECEIPT_PATH
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "receipts": []}), encoding="utf-8")
            report = validate(root)
        self.assertEqual("blocked", report["status"])
        self.assertEqual("blocked", report["recovery_gate_status"])
        self.assertIn("缺少独立恢复状态 recovery_status", report["errors"])


if __name__ == "__main__":
    unittest.main()