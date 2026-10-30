from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from 原版新版资料合并 import run


class OriginalMaterialMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "原始资料" / "资料库.txt"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("## 条目\n旧定义\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _changeset(self, change: dict) -> Path:
        path = self.root / "配置" / "changes.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"schema_version": "original-material-merge-changeset-1.0", "changes": [change]}, ensure_ascii=False), encoding="utf-8")
        return path

    def _change(self, **overrides: object) -> dict:
        original = self.source.read_text(encoding="utf-8")
        change = {
            "change_id": "M-1", "kind": "revision", "target": "资料库.txt",
            "expected_source_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "anchor": "旧定义", "expected_anchor_sha256": hashlib.sha256("旧定义".encode()).hexdigest(),
            "before_context": "## 条目\n", "after_context": "\n", "replacement": "新定义",
            "rationale": "补齐已确认定义", "semantic_contract": {"preserved": ["conditions", "tags", "relations", "state_transitions"], "revised": []},
        }
        change.update(overrides)
        return change

    def test_preview_never_writes_source(self) -> None:
        original = self.source.read_text(encoding="utf-8")
        path = self._changeset(self._change())
        result = run(self.root, path)
        self.assertEqual("previewed", result["status"])
        self.assertIn("-旧定义", result["diff"])
        self.assertEqual(original, self.source.read_text(encoding="utf-8"))

    def test_apply_creates_rollback_and_manifest(self) -> None:
        original = self.source.read_text(encoding="utf-8")
        path = self._changeset(self._change(kind="addition", anchor="旧定义\n", expected_anchor_sha256=hashlib.sha256("旧定义\n".encode()).hexdigest(), after_context="", position="after", content="补充条件\n"))
        result = run(self.root, path, apply=True)
        self.assertEqual("applied", result["status"])
        self.assertIn("补充条件", self.source.read_text(encoding="utf-8"))
        manifest = self.root / result["manifest"]
        self.assertTrue(manifest.is_file())
        self.assertEqual(original, next((manifest.parent / "rollback").rglob("资料库.txt")).read_text(encoding="utf-8"))
        full_backup = manifest.parent / "backup-manifest.json"
        self.assertTrue(full_backup.is_file())
        backup_data = json.loads(full_backup.read_text(encoding="utf-8"))
        self.assertEqual(1, backup_data["file_count"])
        self.assertEqual(original, (manifest.parent / "原始资料" / "资料库.txt").read_text(encoding="utf-8"))

    def test_rejects_stale_source_hash(self) -> None:
        path = self._changeset(self._change(expected_source_sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "expected_source_sha256"):
            run(self.root, path)

    def test_rejects_duplicate_addition_and_context_drift(self) -> None:
        duplicate = self._changeset(self._change(kind="addition", anchor="旧定义\n", expected_anchor_sha256=hashlib.sha256("旧定义\n".encode()).hexdigest(), after_context="", position="after", content="## 条目\n旧定义\n"))
        with self.assertRaisesRegex(ValueError, "重复"):
            run(self.root, duplicate)
        drift = self._changeset(self._change(before_context="错误上下文"))
        with self.assertRaisesRegex(ValueError, "before_context"):
            run(self.root, drift)

    def test_rejects_incomplete_semantic_contract(self) -> None:
        path = self._changeset(self._change(semantic_contract={"preserved": ["conditions"], "revised": []}))
        with self.assertRaisesRegex(ValueError, "逐项声明"):
            run(self.root, path)

    def test_rejects_empty_changeset_apply(self) -> None:
        path = self.root / "配置" / "empty.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"schema_version": "original-material-merge-changeset-1.0", "changes": []}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "变更集为空"):
            run(self.root, path, apply=True)

    def test_rejects_type_system_target(self) -> None:
        type_source = self.root / "原始资料" / "类型系统.txt"
        type_source.write_text("类型定义", encoding="utf-8")
        change = self._change(target="类型系统.txt")
        path = self._changeset(change)
        with self.assertRaisesRegex(ValueError, "非类型原版资料白名单"):
            run(self.root, path)

    def test_rejects_creative_or_report_source_reference(self) -> None:
        change = self._change(rationale="依据文档/证据/候选正文裁决队列.jsonl")
        path = self._changeset(change)
        with self.assertRaisesRegex(ValueError, "创作内容或报告目录"):
            run(self.root, path)


if __name__ == "__main__":
    unittest.main()