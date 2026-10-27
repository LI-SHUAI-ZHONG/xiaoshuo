from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("全量资料输入与正文授权.py")
SPEC = importlib.util.spec_from_file_location("full_source_use_authorization", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FullSourceUseAuthorizationTests(unittest.TestCase):
    def _root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        evidence = root / "文档" / "证据"
        evidence.mkdir(parents=True)
        (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": [{
            "binding_id": "TB-1", "source_id": "S-1", "source_ref": "原始资料/a.txt:SOURCE[1]",
        }]}, ensure_ascii=False), encoding="utf-8")
        return root

    def test_audit_emits_only_complete_explicit_dual_permission(self) -> None:
        root = self._root()
        MODULE.initialize_submission_template(root)
        template = root / "文档/证据/全量资料输入与正文授权/待授权提交模板.jsonl"
        row = json.loads(template.read_text(encoding="utf-8").strip())
        row.update({
            "model_input_eligible": True, "prose_write_allowed": True, "authorization_scope": "本项目指定资料输入与候选正文",
            "authorized_by": "authorized-reviewer", "authorized_at": "2026-08-13T00:00:00Z", "authorization_rationale": "已核验对象范围与可用权限。",
        })
        submission = root / "submission.jsonl"
        submission.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        report = MODULE.audit(root, submission)
        self.assertEqual(1, report["authorized_binding_count"])
        self.assertEqual({"TB-1"}, set(MODULE.authorized_bindings(root, [{"binding_id": "TB-1", "source_id": "S-1", "source_ref": "原始资料/a.txt:SOURCE[1]"}])))

    def test_rejects_single_permission_and_binding_drift(self) -> None:
        root = self._root()
        MODULE.initialize_submission_template(root)
        template = root / "文档/证据/全量资料输入与正文授权/待授权提交模板.jsonl"
        row = json.loads(template.read_text(encoding="utf-8").strip())
        row.update({"model_input_eligible": True, "prose_write_allowed": False, "source_id": "S-other"})
        submission = root / "submission.jsonl"
        submission.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        report = MODULE.audit(root, submission)
        self.assertEqual(0, report["authorized_binding_count"])
        result = (root / "文档/证据/全量资料输入与正文授权/授权审计清单.jsonl").read_text(encoding="utf-8")
        self.assertIn("不可变绑定不匹配: source_id", result)
        self.assertIn("必须同时明确授权", result)

    def test_template_initialization_refuses_to_replace_existing_audit_directory(self) -> None:
        root = self._root()
        MODULE.initialize_submission_template(root)
        with self.assertRaisesRegex(FileExistsError, "拒绝覆盖"):
            MODULE.initialize_submission_template(root)


if __name__ == "__main__":
    unittest.main()