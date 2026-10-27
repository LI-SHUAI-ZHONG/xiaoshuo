"""Static contract tests for Phase A of the Module 08 hand-off."""
from __future__ import annotations

import ast
import importlib.util
import tempfile
from pathlib import Path
import unittest


PIPELINE_PATH = Path(__file__).resolve().parent / "执行管道.py"


def _load_pipeline():
    spec = importlib.util.spec_from_file_location("pipeline_library_parser", PIPELINE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PhaseAActionChainTests(unittest.TestCase):
    def test_module09_uses_scene_card_action_chain_not_story_bible(self) -> None:
        source = PIPELINE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "execute_09"
        )
        function_source = ast.get_source_segment(source, function) or ""
        self.assertIn('card.get("action_chain", [])', function_source)
        self.assertNotIn("scene_action_chains", function_source)
        self.assertNotIn("story_bible", function_source)
        self.assertNotIn("require(BIBLE)", function_source)

    def test_library_parser_accepts_new_block_and_bold_item_headings(self) -> None:
        pipeline = _load_pipeline()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "资料库.txt"
            path.write_text(
                "### 板块155 情节缓冲与节奏过渡\n\n"
                "**155.1 情绪缓冲规则**\n\n"
                "【定义】高强度情节后安排缓冲。\n\n"
                "### 板块159 执行与计划描述系统\n\n"
                "**159.2 行动中思想描写**\n\n"
                "【指令】行动中必须观察、判断、调整。\n",
                encoding="utf-8",
            )
            rows = pipeline._read_library_blocks(path, {155, 159})
            self.assertEqual(
                {"155.1_情绪缓冲规则", "159.2_行动中思想描写"},
                {row["item_id"] for row in rows if "." in row["item_id"]},
            )


if __name__ == "__main__":
    unittest.main()