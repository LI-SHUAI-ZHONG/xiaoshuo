from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("执行管道.py")
SPEC = importlib.util.spec_from_file_location("execution_pipeline_prose_bypass", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProseRuntimeProvenanceTests(unittest.TestCase):
    def _package(self, run_id: str = "run-test") -> tuple[dict, dict]:
        record = {
            "binding_id": "B-1", "source_id": "S-1", "source_ref": "原始资料/资料库.txt:entry-1",
            "scene_id": "S01", "activation_status": "selected",
        }
        packet_hash = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        package = {"schema_version": "runtime-material-package-1.0", "run_id": run_id, "records": [record]}
        scene = {"scene_id": "S01", "source_records": [{
            "run_id": run_id, "scene_id": "S01", "binding_id": "B-1", "source_packet_sha256": packet_hash,
            "translation_evidence": {"trigger": "雨声", "result": "脚步停住"},
        }]}
        return package, scene

    def test_accepts_same_run_package_provenance(self) -> None:
        package, scene = self._package()
        report = MODULE.audit_prose_runtime_provenance([scene], package, "run-test")
        self.assertTrue(report["passed"])
        self.assertFalse(report["template_bypass_detected"])

    def test_template_bypass_detected_blocks_old_or_missing_provenance(self) -> None:
        package, scene = self._package()
        scene["source_records"][0]["run_id"] = "old-run"
        report = MODULE.audit_prose_runtime_provenance([scene], package, "run-test")
        self.assertFalse(report["passed"])
        self.assertTrue(report["template_bypass_detected"])
        self.assertIn("run_id 不一致", " ".join(report["errors"]))


if __name__ == "__main__":
    unittest.main()