from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from 资料运行准入准备 import prepare


class RuntimeAdmissionPreparationTests(unittest.TestCase):
    def _write_json(self, root: Path, relative_path: str, value: dict) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def test_deferred_bindings_are_not_reported_as_scene_assigned_or_prose_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "原始资料" / "资料库.txt"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("source", encoding="utf-8")
            self._write_json(root, "配置/project_config.json", {
                "project_id": "p1", "target_chapter_count": 1, "target_words": 100,
                "chapter_plan": [{"chapter_id": "CH01", "target_words": 100, "scenes": [{"scene_id": "CH01-S01"}]}],
            })
            self._write_json(root, "文档/证据/小说资料选择清单.json", {"project_id": "p1"})
            self._write_json(root, "文档/证据/资源注册表.json", {
                "source_quality": "complete",
                "resources": {"library": {"relative_path": "原始资料/资料库.txt"}},
            })
            self._write_json(root, "文档/证据/全量资料解释词创作绑定.json", {
                "records": [{
                    "binding_id": "TB-1", "source_id": "library-1", "source_kind": "资料库",
                    "source_ref": {"file": "原始资料/资料库.txt", "locator": "1"},
                    "translation_status": "translated",
                }],
            })
            self._write_json(root, "文档/证据/全书资料激活矩阵.json", {
                "project_id": "p1", "assignments": [{"binding_id": "TB-1", "status": "deferred", "scene_id": None}],
            })

            report = prepare(root)["report"]

            self.assertEqual("文档/证据/全书资料激活矩阵.json", report["activation_matrix_path"])
            self.assertEqual(1, report["translated_binding_count"])
            self.assertEqual(0, report["scene_assigned_binding_count"])
            self.assertEqual(1, report["deferred_binding_count"])
            self.assertEqual(0, report["allowed_source_count"])
            self.assertEqual("scene_selection_pending", report["runtime_scope"])
            self.assertEqual("no_scene_sources_admitted", report["admission_decision"])


if __name__ == "__main__":
    unittest.main()