from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load(name: str):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BACKFILL = load("资料库条目补全.py")
PACKAGE = load("运行资料包契约.py")


class LibraryEntryBackfillTests(unittest.TestCase):
    def test_projects_instruction_fields_and_package_consumes_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "原始资料"; raw.mkdir(parents=True)
            (raw / "资料库.txt").write_text(
                "### 1.1_主角\n【定义】定义主角。\n【调用条件】出现主角设计问题。\n【指令】必须有代价。\n【示例】一次选择。\n",
                encoding="utf-8",
            )
            result = BACKFILL.build(root)
            self.assertEqual(1, result["entry_count"])
            row = json.loads((root / "文档" / "资料库索引.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual("source_complete", row["usage_method"]["status"])
            binding = {"binding_id": "TB-1", "source_id": row["entry_id"], "source_kind": "资料库", "source_ref": "原始资料/资料库.txt:1.1_主角", **{key: row[key] for key in ("definition", "call_condition", "usage_method", "examples", "forbidden_use")}}
            package = PACKAGE.build_package(root, "run-test", [binding], [{"binding_id": "TB-1", "scene_id": "S01", "activation_conditions_met": True, "activation_evidence": ["test"]}])
            self.assertEqual(row["usage_method"], package["records"][0]["usage_method"])
            self.assertEqual("原始资料/资料库.txt:1.1_主角", package["records"][0]["source_ref"])


if __name__ == "__main__":
    unittest.main()