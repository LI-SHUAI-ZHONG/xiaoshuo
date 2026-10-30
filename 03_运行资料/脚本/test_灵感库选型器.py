from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SELECTOR = load("灵感库选型器")
INITIALIZER = load("初始化小说项目")


class InspirationSelectionTests(unittest.TestCase):
    def test_initializer_connects_selection_to_project_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = INITIALIZER.initialize_project(directory, "玄幻", ["悬疑"], 4500, 1)
            config = json.loads((root / "配置" / "project_config.json").read_text(encoding="utf-8"))
            receipt = json.loads((root / "文档" / "证据" / "小说灵感选型回执.json").read_text(encoding="utf-8"))
            self.assertEqual(config["project_id"], receipt["project_id"])
            self.assertEqual(config["inspiration_selection"]["selection_id"], receipt["selection_id"])
            self.assertEqual(["玄幻", "悬疑"], receipt["selected_types"])
            self.assertEqual("selected_for_draft_only", receipt["selection_status"])
            self.assertFalse(receipt["formal_release_allowed"])

    def test_execution_admission_rejects_project_or_selection_drift(self) -> None:
        receipt = SELECTOR.build_selection(
            SCRIPT_DIR.parent / "配置" / "类型配置模板.json",
            "project-a",
            "玄幻",
            ["悬疑"],
            target_words=1000,
            target_chapter_count=1,
        )
        errors = SELECTOR.validate_selection(
            receipt,
            project_id="project-b",
            selected_types=["玄幻", "悬疑"],
            profile_path=SCRIPT_DIR.parent / "配置" / "类型配置模板.json",
        )
        self.assertTrue(any("project_id" in error for error in errors))
        receipt["selected_types"] = ["玄幻"]
        errors = SELECTOR.validate_selection(
            receipt,
            project_id="project-a",
            selected_types=["玄幻", "悬疑"],
            profile_path=SCRIPT_DIR.parent / "配置" / "类型配置模板.json",
        )
        self.assertTrue(any("selected_types" in error for error in errors))

    def test_selector_does_not_create_project_facts(self) -> None:
        receipt = SELECTOR.build_selection(
            SCRIPT_DIR.parent / "配置" / "类型配置模板.json",
            "project-a",
            "玄幻",
            [],
            target_words=1000,
            target_chapter_count=1,
        )
        self.assertEqual("uncreated", receipt["project_facts_status"])
        self.assertNotIn("book_title", receipt)
        self.assertNotIn("protagonist", receipt)


if __name__ == "__main__":
    unittest.main()