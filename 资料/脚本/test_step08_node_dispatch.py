"""Contract tests for the original pipeline's Module 08 node dispatcher."""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import unittest


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("execution_pipeline", SCRIPT_DIR / "执行管道.py")
assert SPEC and SPEC.loader
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class Step08NodeDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = {
            "scene_id": "CH01-S01",
            "purpose": "确认异常是否可复核",
            "location": "检测场",
            "character_goal": "确认读数异常",
            "obstacle": "制度禁止公开追问",
            "new_information": "第七息回亮",
            "state_before": "怀疑检测有误",
            "state_after": "异常可被复核",
            "action_chain": [
                {"beat": "入场", "event": "观察记录顺序", "pressure": "质疑会被记为扰乱秩序"},
                {"beat": "试探", "event": "询问记录间隔", "pressure": "对方不愿公开回应"},
            ],
        }
        self.upstream = {
            "selected_types": ["玄幻", "悬疑"],
            "type_combination_ids": ["玄幻+悬疑"],
            "type_connection_ids": ["TC-01"],
            "world_static_edges": [],
            "opening_anchor_categories": ["C", "S"],
            "dynamic_chains": [],
            "character_state": [],
            "quality_rules": ["每场景至少一个锚点"],
        }
        self.methods = [
            {
                "item_id": "57.1_试探性提问",
                "name": "试探性提问",
                "definition": "以不直接指控的问题推进信息差。",
                "instruction": "让回答保留未说出口的限制。",
                "application": "通过问题与回避制造信息变化。",
                "source_ref": "原始资料/资料库.txt:57",
                "evidence_requirements": ["beat_id", "prose_location", "trigger", "result"],
            }
        ]
        self.dynamic = {"id": "D-01", "condition": "异常已出现", "effect": "怀疑转为可复核线索"}
        self.static = {"source": "检测制度", "target": "公开追问", "type": "限制", "condition": "考核进行中", "effect": "行动受限"}
        self.anchors = [{"anchor_id": "C1.1", "anchor_name": "回亮", "definition": "第七息回亮", "trigger": "读数异常", "category": "认知"}]

    def test_node_contract_keeps_all_upstream_categories(self) -> None:
        contracts = PIPELINE._node_adoption_contracts(
            self.scene, self.upstream, self.methods, self.dynamic, self.static, self.anchors
        )
        self.assertEqual(2, len(contracts))
        for index, contract in enumerate(contracts):
            self.assertEqual(index, contract["beat_index"])
            self.assertEqual(self.scene["action_chain"][index]["event"], contract["required_action"])
            kinds = {item["source_kind"] for item in contract["adopted_rules"]}
            self.assertTrue({"类型系统", "类型连接", "动态网络", "静态网络", "锚点网络", "资料库"}.issubset(kinds))
            self.assertTrue(all(item["activation_reason"] for item in contract["adopted_rules"]))
            self.assertTrue(all(item["evidence_requirements"] for item in contract["adopted_rules"]))

    def test_scene_dispatch_uses_previous_module_outputs(self) -> None:
        data = {
            "selected_types": ["玄幻", "悬疑"],
            "matching_combinations": [{"combination_id": "玄幻+悬疑", "connection_ids": ["TC-01"]}],
            "selected_static_edges": [self.static],
            "opening_anchor_categories": ["C"],
            "selected_dynamic_chains": [self.dynamic],
            "characters": [{"name": "沈砚"}],
            "quality_rules": ["每场景至少一个锚点"],
        }
        result = PIPELINE._upstream_scene_dispatch(data, self.scene, "CH01")
        self.assertEqual(["玄幻", "悬疑"], result["selected_types"])
        self.assertEqual(["玄幻+悬疑"], result["type_combination_ids"])
        self.assertEqual(["TC-01"], result["type_connection_ids"])
        self.assertEqual([self.static], result["world_static_edges"])
        self.assertEqual([self.dynamic], result["dynamic_chains"])
        self.assertEqual(["C"], result["opening_anchor_categories"])

    def test_execute08_no_longer_uses_fixed_profile_or_matrix_as_adoption(self) -> None:
        source = inspect.getsource(PIPELINE.execute_08)
        self.assertNotIn("_scene_binding_profile", source)
        self.assertNotIn("assignments_by_scene", source)
        self.assertIn("_upstream_scene_dispatch", source)
        self.assertIn("_node_adoption_contracts", source)

    def test_execute09_uses_scene_card_chain(self) -> None:
        source = inspect.getsource(PIPELINE.execute_09)
        self.assertIn('card.get("action_chain", [])', source)
        self.assertIn('card.get("node_contracts", [])', source)
        self.assertNotIn("scene_action_chains", source)
        self.assertNotIn("story_bible", source)
    def test_execute09_requires_authored_prose_instead_of_fixed_templates(self) -> None:
        source = inspect.getsource(PIPELINE.execute_09)
        self.assertIn("draft_request_required", source)
        self.assertIn("authored_prose_supplied", source)
        self.assertNotIn("distance_rotation", source)
        self.assertNotIn("anchor_applications = {\n            \"C1.17\"", source)
        self.assertNotIn("leads = {", source)


if __name__ == "__main__":
    unittest.main()
