from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("全量资料新版构建.py")
SPEC = importlib.util.spec_from_file_location("version_builder", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class VersionBuilderTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        (root / "08_原始资料").mkdir()
        (root / "08_原始资料" / "facts.txt").write_text("旧事实", encoding="utf-8")
        evidence = root / "文档" / "证据"; evidence.mkdir(parents=True)
        (evidence / "全量资料解释词创作绑定.json").write_text(json.dumps({"records": [{"binding_id": "TB-1", "source_id": "A"}, {"binding_id": "TB-2", "source_id": "B"}]}, ensure_ascii=False), encoding="utf-8")
        (evidence / "全量资料升级档案.jsonl").write_text(json.dumps({"binding_id": "TB-1", "upgrade": {"causal_contract": {"trigger": "x"}, "prose_location": "draft.md#1", "paragraph_sha256": "a"}}, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_builds_immutable_mirror_and_isolates_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            output = MODULE.build(root, "test")
            self.assertEqual("旧事实", (root / "08_原始资料" / "facts.txt").read_text(encoding="utf-8"))
            self.assertEqual("旧事实", (output / "事实资料" / "facts.txt").read_text(encoding="utf-8"))
            coverage = json.loads((output / "审计" / "覆盖报告.json").read_text(encoding="utf-8"))
            self.assertEqual(2, coverage["unique_binding_count"])
            self.assertEqual("passed", json.loads((output / "release_decision.json").read_text(encoding="utf-8"))["status"])

    def test_approved_contract_changes_only_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            anchor = "旧事实"
            changes = {"changes": [{"change_id": "C-1", "status": "approved_for_fact_merge", "target": "facts.txt", "expected_source_sha256": hashlib.sha256(anchor.encode()).hexdigest(), "anchor": anchor, "expected_anchor_sha256": hashlib.sha256(anchor.encode()).hexdigest(), "old_text": anchor, "new_text": "新事实", "rationale": "approved"}]}
            changeset = root / "changes.json"; changeset.write_text(json.dumps(changes, ensure_ascii=False), encoding="utf-8")
            output = MODULE.build(root, "changed", changeset=changeset)
            self.assertEqual("旧事实", (root / "08_原始资料" / "facts.txt").read_text(encoding="utf-8"))
            self.assertEqual("新事实", (output / "事实资料" / "facts.txt").read_text(encoding="utf-8"))

    def test_accepts_explicit_derived_audit_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root); evidence = root / "文档" / "证据"
            derived_bindings = evidence / "derived-bindings.json"
            derived_bindings.write_text((evidence / "全量资料解释词创作绑定.json").read_text(encoding="utf-8"), encoding="utf-8")
            derived_audit = evidence / "derived-audit.json"
            derived_audit.write_text(json.dumps({"quarantined_findings": [{"binding_id": "TB-2"}]}, ensure_ascii=False), encoding="utf-8")
            output = MODULE.build(root, "derived", bindings_path=derived_bindings, quarantine_path=derived_audit)
            ledger = (output / "审计" / "覆盖账本.jsonl").read_text(encoding="utf-8")
            self.assertIn('"terminal_status": "quarantined"', ledger)

    def test_ineligible_duplicate_candidates_are_automatically_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root); evidence = root / "文档" / "证据"
            archive = evidence / "全量资料升级档案.jsonl"
            row = json.loads(archive.read_text(encoding="utf-8").splitlines()[0]); row["upgrade"]["application_status"] = "automatic_draft_requires_semantic_editorial_review"
            archive.write_text("\n".join(json.dumps(row, ensure_ascii=False) for _ in range(2)) + "\n", encoding="utf-8")
            output = MODULE.build(root, "rejected")
            coverage = json.loads((output / "审计" / "覆盖报告.json").read_text(encoding="utf-8"))
            candidates = (output / "候选正文隔离" / "candidate_prose.jsonl").read_text(encoding="utf-8")
            self.assertEqual({"candidate_prose": 1, "validated_no_change": 1}, coverage["status_counts"])
            self.assertIn('"disposition": "auto_rejected_not_fact_merge_eligible"', candidates)


if __name__ == "__main__":
    unittest.main()