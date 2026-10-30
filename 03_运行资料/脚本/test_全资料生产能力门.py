from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRANSLATOR = _load("全量资料解释词转译与创作绑定")
GATE = _load("全资料生产能力门")


class FullSourceProductionCapabilityTests(unittest.TestCase):
    def _write_json(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def test_candidate_constraints_remain_in_creation_contract(self) -> None:
        registry = {"records": [{
            "source_kind": "类型连接",
            "source_id": "combo-1",
            "name": "候选组合",
            "definition": "候选组合必须经过选择和验证。",
            "require_selection": True,
            "require_validation": True,
            "prerequisites": ["候选效果不等于实际状态变化"],
        }]}
        bindings = TRANSLATOR.build_bindings(registry, {"project_id": "p", "activation_policy": {}})
        self.assertFalse(bindings["records"][0]["model_input_eligible"])
        self.assertFalse(bindings["records"][0]["prose_write_allowed"])
        policy = bindings["records"][0]["creation_binding"]["activation_policy"]
        conditions = " ".join(policy["conditions"])
        self.assertIn("require_selection: True", conditions)
        self.assertIn("require_validation: True", conditions)
        self.assertIn("候选效果不等于实际状态变化", conditions)

    def test_audited_semantic_conditions_exclude_source_qualification(self) -> None:
        registry = {"records": [{
            "source_kind": "类型连接", "source_id": "combo-1", "name": "组合", "definition": "组合约束",
        }]}
        bindings = TRANSLATOR.build_bindings(registry, {"project_id": "p", "activation_policy": {}}, {
            "TB-00001": ["主类型已选择", "组成类型已选择并匹配"],
        })
        policy = bindings["records"][0]["creation_binding"]["activation_policy"]
        self.assertIn("主类型已选择", policy["conditions"][0])
        self.assertNotIn("来源资格", policy["conditions"][0])

    def test_partial_source_is_notice_when_every_contract_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for index, kind in enumerate(GATE.REQUIRED_KINDS, 1):
                records.append({
                    "binding_id": f"TB-{index}", "source_id": f"S-{index}", "source_kind": kind,
                    "name": kind, "source_ref": f"source/{index}", "translation_status": "translated",
                    "semantic_interpretation": {"source_meaning": kind, "source_semantic_anchor": kind, "semantic_terms": [kind]},
                    "creation_binding": {
                        "creative_object": "对象", "creative_action": "执行", "activation_policy": {
                            "mode": "条件匹配", "conditions": ["条件匹配"], "activation_evidence": ["matched_stage"],
                        },
                        "creative_strategy": {
                            "source_specific_trigger": "触发", "observable_action": "行动", "observable_result": "结果",
                            "cost_or_change": "代价", "semantic_anchor": kind, "evidence_location": "场景", "quality_rule": "因果",
                        },
                    },
                    "evidence_contract": {"design_required": ["stage"], "scene_required": ["scene_id"], "prose_required": ["prose_location"]},
                    "activation_status": "awaiting_stage_evidence",
                })
            self._write_json(root, "配置/project_config.json", {"project_id": "p"})
            self._write_json(root, "文档/证据/全量资料解释词创作绑定.json", {"records": records})
            self._write_json(root, "文档/证据/资源注册表.json", {"resources": {
                key: {"source_quality": "partial" if key == "library" else "complete"}
                for key in GATE.RESOURCE_KEYS.values()
            }})
            self._write_json(root, "文档/证据/全量资料治理/全量检查报告.json", {"summary": {
                kind: {"pending": 0, "blocking": 0} for kind in GATE.REQUIRED_KINDS
            }})
            report = GATE.audit(root)
            self.assertEqual("passed", report["status"])
            self.assertEqual("draft_only_quality_generation_allowed", report["production_status"])
            self.assertEqual("资料库", report["source_quality_notices"][0]["source_kind"])


if __name__ == "__main__":
    unittest.main()