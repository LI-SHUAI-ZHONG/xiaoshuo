"""Regression tests for project-only derived-material adoption."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("派生资料项目采用.py")
SPEC = importlib.util.spec_from_file_location("derived_adoption", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MODULE.RUN_ID = "test-run"


class ProjectOnlyAdoptionTests(unittest.TestCase):
    def _root(self, decision: str | None = "将主角的代价约束写入项目角色弧光设计，并要求后续大纲保留该限制。") -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        evidence = root / "文档" / "证据"
        run = evidence / "全量资料升级运行" / "test-run"
        run.mkdir(parents=True)
        (root / "配置").mkdir()
        (root / "配置" / "project_config.json").write_text('{"project_id":"test"}', encoding="utf-8")
        binding = {"binding_id": "B1", "source_kind": "资料库", "source_id": "source-one", "name": "主角", "source_ref": "资料库.txt:1", "original_object_sha256": "a" * 64}
        (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": [binding]}, ensure_ascii=False), encoding="utf-8")
        (run / "manifest.json").write_text(json.dumps({"run_id": "test-run"}), encoding="utf-8")
        (run / "records.jsonl").write_text(json.dumps({"binding_id": "B1", "status": "validated_candidate", "original_object_sha256": "a" * 64}) + "\n", encoding="utf-8")
        requests = [] if decision is None else [{"binding_id": "B1", "decision_statement": decision}]
        (evidence / MODULE.TASK_FILE).write_text(json.dumps({"project_id": "test", "requests": requests}, ensure_ascii=False), encoding="utf-8")
        return root

    def test_missing_project_request_blocks_without_writing_anything(self) -> None:
        root = self._root(decision=None)
        result = MODULE.run(root, apply=True)
        self.assertEqual("blocked", result["quality_status"])
        self.assertFalse((root / "正文").exists())
        self.assertFalse((root / "文档" / "证据" / "派生资料项目采用").exists())

    def test_apply_writes_project_only_append_only_decision(self) -> None:
        root = self._root()
        result = MODULE.run(root, apply=True)
        self.assertEqual("passed", result["quality_status"])
        output = root / "文档" / "证据" / "派生资料项目采用" / "test-run" / MODULE.DECISION_FILE
        document = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual("project_design_adoption_only", document["scope"])
        self.assertEqual("not_scene_bound_not_consumed_not_narrativized", document["records"][0]["downstream_status"])
        self.assertFalse((root / "正文").exists())

    def test_staging_validation_rejects_tampered_decision(self) -> None:
        root = self._root()
        preflight = MODULE._preflight(root)
        staging = root / "staged.json"
        document = MODULE._build_decision(preflight)
        document["records"][0]["decision_statement"] = "篡改"
        staging.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(MODULE._validate_staging(preflight, str(staging)))

    def test_missing_baseline_hash_uses_locked_upgrade_hash(self) -> None:
        root = self._root()
        binding_path = root / "文档" / "证据" / "全量资料解释词创作绑定.json"
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        binding["records"][0].pop("original_object_sha256")
        binding_path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")
        result = MODULE.run(root, apply=False)
        self.assertEqual("passed", result["quality_status"])

    def test_present_baseline_hash_must_match_locked_upgrade_hash(self) -> None:
        root = self._root()
        binding_path = root / "文档" / "证据" / "全量资料解释词创作绑定.json"
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        binding["records"][0]["original_object_sha256"] = "b" * 64
        binding_path.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")
        result = MODULE.run(root, apply=False)
        self.assertEqual("blocked", result["quality_status"])
        self.assertIn("哈希不一致", result["errors"][0])


if __name__ == "__main__":
    unittest.main()