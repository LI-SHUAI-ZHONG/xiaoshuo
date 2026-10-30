from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import 运行恢复与幂等验收 as recovery
from 运行清单复核 import finalize_run, initialize_run, register_artifact


class RunRecoveryIdempotencyTests(unittest.TestCase):
    def _run(self, root: Path, run_id: str = "run-test") -> Path:
        target = root / "输入.txt"
        target.write_text("stable", encoding="utf-8")
        initialize_run(root, run_id, input_snapshot_paths=["输入.txt"])
        manifest = json.loads((root / "文档" / "证据" / "运行" / run_id / "run_manifest.json").read_text(encoding="utf-8"))
        manifest["actual_reads"] = [{"relative_path": "输入.txt", "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "evidence_layer": "original_source"}]
        (root / "文档" / "证据" / "运行" / run_id / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        finalize_run(root, run_id, status="failed", exit_code=2, failed_stage="test")
        return target

    def test_resume_requires_unchanged_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = self._run(root)
            target.write_text("drifted", encoding="utf-8")
            report = recovery.resume_audit(root, "run-test")
            self.assertFalse(report["resume_allowed"])
            self.assertIn("输入快照哈希漂移", "；".join(report["errors"]))

    def test_repeated_audit_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._run(root)
            first = recovery.resume_audit(root, "run-test")
            second = recovery.resume_audit(root, "run-test")
            self.assertEqual(first["artifact_count"], second["artifact_count"])
            self.assertTrue(second["idempotent"])

    def test_six_primary_material_drift_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self._run(root)
            snapshot_path = root / "文档" / "证据" / "运行" / "run-test" / "run_input_snapshot.json"
            paths = {
                "资料库": "原始资料/资料库.txt", "类型系统": "原始资料/类型系统.txt",
                "类型连接": "原始资料/类型连接.txt", "静态网络": "原始资料/静态网络.txt",
                "动态网络": "原始资料/动态网络.txt", "锚点网络": "原始资料/锚点网络.txt",
            }
            for relative in paths.values():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")
            snapshot_path.write_text(json.dumps({
                "run_id": "run-test",
                "six_materials_sha256": recovery._six_materials_digest(root),
            }), encoding="utf-8")
            (root / "原始资料" / "类型连接.txt").write_text("drifted", encoding="utf-8")
            report = recovery.resume_audit(root, "run-test")
            self.assertFalse(report["resume_allowed"])
            self.assertIn("输入快照哈希漂移：six_materials_sha256", report["errors"])

    def test_missing_primary_material_after_snapshot_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._run(root)
            snapshot_path = root / "文档" / "证据" / "运行" / "run-test" / "run_input_snapshot.json"
            for relative in recovery.PRIMARY_MATERIAL_PATHS.values():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, encoding="utf-8")
            snapshot_path.write_text(json.dumps({
                "run_id": "run-test",
                "six_materials_sha256": recovery._six_materials_digest(root),
            }), encoding="utf-8")
            (root / "原始资料" / "锚点网络.txt").unlink()
            report = recovery.resume_audit(root, "run-test")
            self.assertFalse(report["resume_allowed"])
            self.assertIn("输入快照哈希漂移：six_materials_sha256", report["errors"])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); initialize_run(root, "run-live")
            result = recovery.terminalize_interrupted_run(root, "run-live", "test interruption")
            manifest = json.loads((root / "文档" / "证据" / "运行" / "run-live" / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("failed", manifest["run_status"])
            self.assertEqual(130, manifest["exit_code"])
            self.assertTrue(Path(result["receipt"]).is_file())


if __name__ == "__main__":
    unittest.main()