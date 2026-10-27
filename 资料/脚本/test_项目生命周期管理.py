from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from 项目生命周期管理 import archive_project, list_projects, register_project, validate_new_project_root


class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "作品").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_new_project_rejects_non_directories_and_existing_material(self) -> None:
        with self.assertRaisesRegex(ValueError, "直接子目录"):
            validate_new_project_root(self.root, self.root / "其他" / "书")
        project = self.root / "作品" / "新书"
        project.mkdir()
        (project / "旧配置.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "不可识别资料"):
            validate_new_project_root(self.root, project)

    def test_registration_does_not_inherit_old_project(self) -> None:
        old = self.root / "作品" / "旧书"
        old.mkdir()
        (old / "正文").mkdir()
        (old / "正文" / "old.txt").write_text("old", encoding="utf-8")
        record = register_project(self.root, old, "old-id", "旧书")
        self.assertEqual("active", record["status"])
        new = self.root / "作品" / "新书"
        validate_new_project_root(self.root, new)
        new.mkdir()
        self.assertFalse((new / "正文").exists())
        register_project(self.root, new, "new-id", "新书")
        self.assertEqual({"old-id", "new-id"}, {item["project_id"] for item in list_projects(self.root)})

    def test_duplicate_project_id_is_rejected(self) -> None:
        first = self.root / "作品" / "第一本"
        second = self.root / "作品" / "第二本"
        first.mkdir()
        second.mkdir()
        register_project(self.root, first, "same-id", "第一本")
        with self.assertRaisesRegex(ValueError, "project_id"):
            register_project(self.root, second, "same-id", "第二本")

    def test_active_project_validation_requires_registered_identity(self) -> None:
        from 项目生命周期管理 import validate_active_project
        project = self.root / "作品" / "一本书"
        project.mkdir()
        with self.assertRaisesRegex(ValueError, "未登记"):
            validate_active_project(self.root, project, project_id="p1", book_title="一本书")
        register_project(self.root, project, "p1", "一本书")
        record = validate_active_project(self.root, project, project_id="p1", book_title="一本书", resource_root=self.root)
        self.assertEqual("active", record["status"])

    def test_archived_title_cannot_be_reused_and_manifest_is_hashed(self) -> None:
        project = self.root / "作品" / "旧书"
        project.mkdir()
        source = project / "配置.json"
        source.write_text("内容", encoding="utf-8")
        register_project(self.root, project, "project-id", "旧书")
        archive = archive_project(self.root, project)
        manifest = json.loads((archive / "归档文件哈希清单.json").read_text(encoding="utf-8"))
        self.assertEqual("project-id", manifest["project_id"])
        self.assertTrue(any(item["relative_path"] == "配置.json" for item in manifest["files"]))
        with self.assertRaisesRegex(ValueError, "已归档"):
            validate_new_project_root(self.root, self.root / "作品" / "旧书")
        self.assertEqual("archived", list_projects(self.root)[0]["status"])


if __name__ == "__main__":
    unittest.main()