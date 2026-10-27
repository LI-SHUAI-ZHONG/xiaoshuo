from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from 运行清单复核 import initialize_run, register_artifact, register_read, verify_full_pipeline_manifest, verify_manifest, write_failure_receipt


class RunManifestReadAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.first = self.root / "原始资料" / "first.txt"
        self.second = self.root / "文档" / "证据" / "index.json"
        self.first.parent.mkdir(parents=True)
        self.second.parent.mkdir(parents=True)
        self.first.write_text("first", encoding="utf-8")
        self.second.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _initialize(self, paths: list[str]) -> None:
        initialize_run(self.root, "run-test", input_snapshot_paths=paths)

    def test_matching_registered_reads_pass(self) -> None:
        self._initialize(["原始资料/first.txt", "文档/证据/index.json"])
        register_read(self.root, "run-test", self.first, evidence_layer="original_source")
        register_read(self.root, "run-test", self.second, evidence_layer="historical_artifact")

        report = verify_manifest(self.root, "run-test")

        self.assertTrue(report["passed"])

    def test_missing_registered_read_blocks(self) -> None:
        self._initialize(["原始资料/first.txt", "文档/证据/index.json"])
        register_read(self.root, "run-test", self.first, evidence_layer="original_source")

        report = verify_manifest(self.root, "run-test")

        self.assertFalse(report["passed"])
        self.assertIn("实际读取集合与输入快照集合不一致", report["errors"])

    def test_extra_registered_read_blocks(self) -> None:
        self._initialize(["原始资料/first.txt"])
        register_read(self.root, "run-test", self.first, evidence_layer="original_source")
        register_read(self.root, "run-test", self.second, evidence_layer="historical_artifact")

        report = verify_manifest(self.root, "run-test")

        self.assertFalse(report["passed"])
        self.assertIn("实际读取集合与输入快照集合不一致", report["errors"])

    def test_hash_drift_after_registration_blocks(self) -> None:
        self._initialize(["原始资料/first.txt"])
        register_read(self.root, "run-test", self.first, evidence_layer="original_source")
        self.first.write_text("changed", encoding="utf-8")

        report = verify_manifest(self.root, "run-test")

        self.assertFalse(report["passed"])
        self.assertIn("实际读取输入不存在、越界或哈希漂移：原始资料/first.txt", report["errors"])

    def test_runtime_derived_read_is_recorded_without_expanding_frozen_inputs(self) -> None:
        self._initialize(["原始资料/first.txt"])
        register_read(self.root, "run-test", self.first, evidence_layer="original_source")
        register_read(self.root, "run-test", self.second, evidence_layer="runtime_derived")

        report = verify_manifest(self.root, "run-test")

        self.assertTrue(report["passed"])
        reads = report["manifest"]["actual_reads"]
        self.assertEqual("runtime_derived", next(row["evidence_layer"] for row in reads if row["relative_path"] == "文档/证据/index.json"))

    def test_artifact_outside_current_run_directory_blocks(self) -> None:
        self._initialize([])
        artifact = self.root / "文档" / "证据" / "module_outputs" / "module_09_scene_prose.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps({"run_id": "run-test"}), encoding="utf-8")
        register_artifact(self.root, "run-test", artifact, kind="module_output")

        report = verify_manifest(self.root, "run-test")

        self.assertFalse(report["passed"])
        self.assertIn("运行产物不在当前运行目录：文档/证据/module_outputs/module_09_scene_prose.json", report["errors"])

    def test_artifact_with_other_run_id_blocks(self) -> None:
        self._initialize([])
        artifact = self.root / "文档" / "证据" / "运行" / "run-test" / "module_outputs" / "module_09_scene_prose.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_text(json.dumps({"run_id": "old-run"}), encoding="utf-8")
        register_artifact(self.root, "run-test", artifact, kind="module_output")

        report = verify_manifest(self.root, "run-test")

        self.assertFalse(report["passed"])
        self.assertIn("运行产物 run_id 不一致或缺失：文档/证据/运行/run-test/module_outputs/module_09_scene_prose.json", report["errors"])

    def test_same_path_preserves_specialized_and_module_attestations(self) -> None:
        self._initialize([])
        artifact = self.root / "文档" / "证据" / "运行" / "run-test" / "scene_source_selection.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps({"run_id": "run-test"}), encoding="utf-8")
        register_artifact(self.root, "run-test", artifact, kind="scene_selection", module_id="08", status="passed", exit_code=0)
        register_artifact(self.root, "run-test", artifact, kind="module_output", module_id="08", status="success", exit_code=0)

        report = verify_manifest(self.root, "run-test", required_kinds={"scene_selection", "module_output"})

        self.assertTrue(report["passed"])
        rows = [row for row in report["manifest"]["artifacts"] if row["relative_path"].endswith("scene_source_selection.json")]
        self.assertEqual({"scene_selection", "module_output"}, {row["kind"] for row in rows})

    def test_activation_audit_is_run_scoped(self) -> None:
        self._initialize([])
        path = self.root / "文档" / "证据" / "运行" / "run-test" / "资料绑定激活审计.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"run_id": "run-test"}) + """\n""", encoding="utf-8")
        register_artifact(self.root, "run-test", path, kind="activation_audit", status="success", exit_code=0)
        report = verify_manifest(self.root, "run-test", required_kinds={"activation_audit"})
        self.assertTrue(report["passed"])

        self._initialize([])

        receipt_path = write_failure_receipt(
            self.root, "run-test", status="failed", failed_stage="module_execution", exit_code=2,
            errors=["deliberate failure"], cleanup_actions=["production access withheld"],
        )

        report = verify_manifest(self.root, "run-test", required_kinds={"failure_receipt"})
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual("failed", report["manifest"]["run_status"])
        self.assertEqual(2, report["manifest"]["exit_code"])
        self.assertEqual("module_execution", report["manifest"]["failed_stage"])
        self.assertEqual("run-test", receipt["run_id"])
        self.assertEqual("failed", receipt["status"])


class FullPipelineManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.run_id = "run-full"
        initialize_run(self.root, self.run_id, input_snapshot_paths=[])
        self.run_dir = self.root / "文档" / "证据" / "运行" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _artifact(self, name: str, kind: str, module_id: str = "", exit_code: int = 0) -> None:
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"run_id": self.run_id, "artifact": name}), encoding="utf-8")
        register_artifact(self.root, self.run_id, path, kind=kind, module_id=module_id, exit_code=exit_code)

    def _register_complete(self) -> None:
        self._artifact("run_input_snapshot.json", "input_snapshot")
        for module_id in [f"{number:02d}" for number in range(12)]:
            self._artifact(f"module_outputs/module_{module_id}_output.json", "module_output", module_id)
        for kind, name in (
            ("material_package", "运行资料包.json"),
            ("consumption_log", "执行消费.jsonl"),
            ("prose", "正文.json"),
            ("structural_quality", "结构质量.json"),
            ("literary_review", "文学审校.json"),
            ("delivery_report", "交付报告.json"),
        ):
            self._artifact(name, kind)

    def test_full_pipeline_profile_passes_only_with_all_modules_and_artifact_kinds(self) -> None:
        self._register_complete()

        report = verify_full_pipeline_manifest(self.root, self.run_id)

        self.assertTrue(report["passed"])
        self.assertEqual("full_pipeline", report["profile"])

    def test_full_pipeline_profile_blocks_missing_module_even_when_kinds_exist(self) -> None:
        self._register_complete()
        manifest_path = self.root / "文档" / "证据" / "运行" / self.run_id / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"] = [
            row for row in manifest["artifacts"]
            if not (row.get("kind") == "module_output" and row.get("module_id") == "07")
        ]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = verify_full_pipeline_manifest(self.root, self.run_id)

        self.assertFalse(report["passed"])
        self.assertIn("运行清单缺少必需模块输出：07", report["errors"])

    def test_full_pipeline_profile_blocks_nonzero_artifact_exit_code(self) -> None:
        self._register_complete()
        manifest_path = self.root / "文档" / "证据" / "运行" / self.run_id / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target = next(row for row in manifest["artifacts"] if row.get("kind") == "literary_review")
        target["exit_code"] = 2
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = verify_full_pipeline_manifest(self.root, self.run_id)

        self.assertFalse(report["passed"])
        self.assertTrue(any("运行产物退出码非零" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()