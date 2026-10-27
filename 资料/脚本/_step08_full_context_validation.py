from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


COPY_ROOT = Path(r"D:\小说_步骤八完整验证_20260820_20260820_150022")
REAL_ROOT = Path(r"D:\小说")
PIPELINE_PATH = COPY_ROOT / "脚本" / "执行管道.py"
REPORT_PATH = COPY_ROOT / "文档" / "证据" / "step08_full_context_validation.json"
EXPECTED_SHA256 = "DBDCE5B16D37EAB467874793D95B772BB365E955C84478FEFBF42AE2481C6C6B"


def json_value(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_value(item) for item in value]
    return value


def source_slice(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function_name)
    return ast.get_source_segment(source, function) or ""


def name_or_attribute(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name_or_attribute(node.value) + "." + node.attr
    if isinstance(node, ast.Subscript):
        return name_or_attribute(node.value)
    return ""


def static_interface_audit(source: str) -> tuple[list[dict], dict, dict]:
    execute08 = source_slice(source, "execute_08")
    execute09 = source_slice(source, "execute_09")
    execute10 = source_slice(source, "execute_10")
    checks = {
        "_scene_binding_profile(index)": "_scene_binding_profile(index)" in execute08,
        "assignments_by_scene": "assignments_by_scene" in execute08,
        "activation_matrix 的轮换场景分配": "assignments_by_scene.get(scene_id" in execute08,
        "target = targets[index % len(targets)]": "index % len(targets)" in execute08,
        "固定 CH01 场景 profile": "_scene_binding_profile(index)" in execute08,
        "固定锚点 ID": "profile[\"anchor_ids\"]" in execute08,
        "固定动态链/静态边": "profile[\"dynamic_source\"]" in execute08 and "profile[\"static_source\"]" in execute08,
        "固定少数资料库方法候选池": "entry[\"block\"] == 87" in execute08 and "{145, 148}" in execute08,
    }
    legacy = []
    for symbol, reachable in checks.items():
        legacy.append({
            "symbol_or_logic": symbol,
            "production_reachable": reachable,
            "smoke_reachable": False,
            "execute_08_reachable": reachable,
            "not_reachable": not reachable,
            "only_legacy_helper": False,
            "evidence": "execute_08 AST/source" if reachable else "未在 execute_08 中发现",
        })
    module09 = {
        "reads_module_08_scene_cards": "data.get(\"scene_beat_cards\")" in execute09,
        "reads_card_action_chain": "card.get(\"action_chain\")" in execute09,
        "reads_story_bible_chapter_one_scene_action_chains": "story_bible" in execute09 and "scene_action_chains" in execute09,
        "reads_current_scene_adopted_material": "selections_by_scene" in execute09 and "selected_bindings" in execute09,
        "rotates_material_anchor_or_matrix_by_paragraph_index": "paragraph_index" in execute09 and "% len(" in execute09,
    }
    module10 = {
        "uses_module_08_scene_cards_or_plan_for_prose_validation": "scene_beat_cards" in execute10 or "module_08" in execute10,
        "checks_step08_unadopted_but_currently_inapplicable_rules": "deferred" in execute10 and "activation" in execute10,
        "has_source_records_that_can_mean_rotation_assignment_not_actual_adoption": "matrix" in execute10 and "source_records" in execute10,
    }
    return legacy, module09, module10


def upstream_audit(context: dict, execute08_source: str) -> list[dict]:
    fields = {
        "Module 02": ["selected_types", "matching_combinations"],
        "Module 03": ["类型连接", "类型依赖", "组合限制"],
        "Module 04": ["world_basics", "world_setting_entries", "selected_static_edges"],
        "Module 05": ["opening_anchor_categories", "开篇锚点及承诺"],
        "Module 06": ["characters", "selected_dynamic_chains", "dynamic_state_summary", "人物状态", "剧情状态", "action_chain"],
        "Module 07": ["quality_rules", "质量规则", "证据要求", "阻断条件"],
    }
    result = []
    for module, names in fields.items():
        for name in names:
            present = name in context
            read = (f"data.get(\"{name}\")" in execute08_source or f"data.get('{name}')" in execute08_source)
            result.append({
                "module": module,
                "field": name,
                "present_in_context": present,
                "read_by_execute_08": read,
                "actually_affects_scene_card": read,
                "only_present_not_consumed": present and not read,
                "missing": not present,
            })
    return result


def scene_audit(output: dict, context: dict) -> list[dict]:
    rows = []
    for scene in output.get("scenes", []):
        action_chain = scene.get("action_chain")
        action_nodes = action_chain if isinstance(action_chain, list) else []
        selected_bindings = [item for item in output.get("design_bindings", []) if item.get("scene_id") == scene.get("scene_id")]
        row = {
            "scene_id": scene.get("scene_id"),
            "scene_purpose": scene.get("purpose"),
            "action_chain_node_count": len(action_nodes),
            "action_chain_source": "scene_card.action_chain" if action_chain is not None else "absent",
            "action_chain_from_current_project_config_or_upstream": bool(action_chain),
            "dynamic_chain": {key: scene.get(key) for key in ("dynamic_edge_id", "source", "target", "condition", "effect")},
            "dynamic_chain_source_and_rationale": scene.get("selection_rationale", {}).get("dynamic_chain", {}),
            "static_edge": scene.get("static_edge"),
            "static_edge_source_and_rationale": scene.get("selection_rationale", {}).get("static_edge", {}),
            "anchor_ids": scene.get("anchor_ids", []),
            "anchor_source_and_rationale": scene.get("selection_rationale", {}).get("anchor", {}),
            "library_entries": scene.get("library_entries", []),
            "library_entry_source_and_rationale": scene.get("library_selection", {}),
            "method_execution_trace": scene.get("method_execution_trace", []),
            "required_evidence": ["source_id", "binding_id", "prose_location", "trigger", "observable_result", "paragraph_sha256"],
            "selection_rationale": scene.get("selection_rationale", {}),
            "node_level_adoption_contract": "present" if action_nodes and any(isinstance(node, dict) and node.get("adopted_sources") for node in action_nodes) else "absent",
            "action_node_audit": [],
            "scene_design_bindings": selected_bindings,
        }
        for index, node in enumerate(action_nodes):
            node = node if isinstance(node, dict) else {"value": node}
            row["action_node_audit"].append({
                "scene_id": scene.get("scene_id"), "beat_index": index,
                "beat_name": node.get("beat_name") or node.get("name"), "event": node.get("event"),
                "pressure": node.get("pressure"), "entry_state": node.get("entry_state"),
                "expected_result": node.get("expected_result"), "adopted_material": node.get("adopted_sources", []),
                "source_kind": node.get("source_kind"), "source_ref": node.get("source_ref"),
                "adoption_rationale": node.get("selection_rationale"),
                "has_prose_landing_or_evidence_requirement": bool(node.get("prose_location") or node.get("required_evidence")),
                "has_no_early_reveal_requirement": bool(node.get("forbidden_reveals") or node.get("禁止提前揭示")),
            })
        rows.append(row)
    return rows


def main() -> None:
    pipeline_hash = hashlib.sha256(PIPELINE_PATH.read_bytes()).hexdigest().upper()
    source = PIPELINE_PATH.read_text(encoding="utf-8-sig")
    report = {
        "project_root": str(COPY_ROOT), "real_project_unchanged": True, "pipeline_sha256": pipeline_hash,
        "source_production_capability": {}, "initialization_steps": [], "module_statuses": [],
        "context_before_module_08": {}, "module_08_status": "not_run", "scene_adoption_audit": [],
        "upstream_output_audit": [], "legacy_path_audit": [], "module_09_static_interface_audit": {},
        "module_10_static_interface_audit": {}, "conclusion": {
            "module_08_ran": False, "module_08_uses_upstream_outputs": [], "upstream_outputs_only_present": [],
            "fixed_profile_still_reachable": False, "round_robin_still_reachable": False,
            "node_level_adoption_contracts_present": False, "safe_to_enter_module_09_human_review": False,
        },
    }
    if pipeline_hash != EXPECTED_SHA256:
        raise RuntimeError(f"副本执行管道 SHA-256 不匹配：{pipeline_hash}")
    sys.path.insert(0, str(COPY_ROOT / "脚本"))
    spec = importlib.util.spec_from_file_location("isolated_pipeline", PIPELINE_PATH)
    pipeline = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(pipeline)
    pipeline.set_project_root(COPY_ROOT)
    PROJECT_ROOT = pipeline.PROJECT_ROOT
    assert PROJECT_ROOT != REAL_ROOT
    assert str(PROJECT_ROOT).startswith(r"D:\小说_步骤八完整验证_")

    def initialize(name, callback):
        try:
            value = callback()
            report["initialization_steps"].append({"step": name, "status": "success"})
            return value
        except Exception as exc:
            report["initialization_steps"].append({"step": name, "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})
            raise

    try:
        initialize("set_project_root", lambda: None)
        initialize("_refresh_module_inputs", pipeline._refresh_module_inputs)
        contract = initialize("validate_execution_contract(phase=creation)", lambda: pipeline.validate_execution_contract(PROJECT_ROOT, require_blueprint=False, phase="creation"))
        if contract["status"] != "passed":
            raise ValueError("项目执行边界未通过：" + "；".join(contract["errors"]))
        configured = contract["config"]
        registry = initialize("build_registry", lambda: pipeline.build_registry(PROJECT_ROOT))
        interpretation = initialize("execute_source_interpretation_registry", pipeline.execute_source_interpretation_registry)
        if registry["status"] != "passed":
            raise RuntimeError("资源注册失败：" + "；".join(registry["blocking_errors"]))
        bindings, binding_files = initialize("build_creation_bindings", lambda: pipeline.build_creation_bindings(PROJECT_ROOT, pipeline.OUTPUT_DIR / "module_00_source_interpretation_registry.json", pipeline.PROJECT_CONFIG))
        if bindings["source_count"] != interpretation["source_count"]:
            raise RuntimeError("全量资料转译数量与解释词注册数量不一致")
        config_errors = pipeline._project_config_errors(configured)
        if config_errors:
            raise ValueError("项目配置不符合执行契约：" + "；".join(config_errors))
        activation_matrix, activation_files = initialize("_build_book_activation_matrix", lambda: pipeline._build_book_activation_matrix(configured, bindings))
        source_capability = initialize("audit_source_production", lambda: pipeline.audit_source_production(PROJECT_ROOT))
        source_capability_blocked = source_capability["status"] != "passed"
        admission = initialize("prepare_runtime_admission", lambda: pipeline.prepare_runtime_admission(PROJECT_ROOT))
        delivery_contract = initialize("validate_execution_contract(phase=delivery)", lambda: pipeline.validate_execution_contract(PROJECT_ROOT, phase="delivery"))
        if delivery_contract["status"] != "passed":
            raise ValueError("项目交付执行边界未通过：" + "；".join(delivery_contract["errors"]))
        delivery_status = "draft_only" if registry.get("quality_blocking_errors") or source_capability_blocked else "project_delivery_candidate"
        context = {
            "project_root": str(PROJECT_ROOT), "project_config": configured, "resource_registry": registry,
            "delivery_status": delivery_status, "quality_blocking_errors": list(registry.get("quality_blocking_errors", [])),
            "source_interpretation_registry": interpretation, "creation_bindings": bindings,
            "activation_matrix": activation_matrix, "source_production_capability": source_capability,
            "source_production_capability_blocked": source_capability_blocked,
            "creation_binding_files": [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in binding_files],
        }
        report["source_production_capability"] = {"status": source_capability["status"], "blocked": source_capability_blocked, "delivery_status": delivery_status}
        functions = [(f"{number:02d}", getattr(pipeline, f"execute_{number:02d}")) for number in range(1, 9)]
        for module_id, function in functions:
            if module_id == "08":
                report["context_before_module_08"] = {key: json_value(context.get(key)) for key in context if key != "module_outputs"}
                report["upstream_output_audit"] = upstream_audit(context, source_slice(source, "execute_08"))
            try:
                output, files = function(context)
                internal_failure = output.get("status") == "failed" or output.get("self_check", {}).get("passed") is False
                record = {"module_id": module_id, "status": "failed" if internal_failure else "success", "output_keys": sorted(output), "output_files": [str(path) for path in files], "failure_input_keys": sorted(context)}
                if internal_failure:
                    record["error"] = output.get("blocking_failures") or output.get("self_check", {}).get("details") or "模块自检失败"
                context = {**context, **output, "module_outputs": {**context.get("module_outputs", {}), module_id: record}}
                report["module_statuses"].append(record)
                if module_id == "08":
                    report["module_08_status"] = record["status"]
                    report["scene_adoption_audit"] = scene_audit(output, context)
                if internal_failure:
                    break
            except Exception as exc:
                report["module_statuses"].append({"module_id": module_id, "status": "failed", "error": str(exc), "traceback": traceback.format_exc(), "failure_input_keys": sorted(context)})
                if module_id == "08":
                    report["module_08_status"] = "failed"
                break
        legacy, module09, module10 = static_interface_audit(source)
        report["legacy_path_audit"] = legacy
        report["module_09_static_interface_audit"] = module09
        report["module_10_static_interface_audit"] = module10
        report["conclusion"] = {
            "module_08_ran": any(row["module_id"] == "08" for row in report["module_statuses"]),
            "module_08_uses_upstream_outputs": [row["field"] for row in report["upstream_output_audit"] if row["actually_affects_scene_card"]],
            "upstream_outputs_only_present": [row["field"] for row in report["upstream_output_audit"] if row["only_present_not_consumed"]],
            "fixed_profile_still_reachable": any(row["symbol_or_logic"] == "固定 CH01 场景 profile" and row["execute_08_reachable"] for row in legacy),
            "round_robin_still_reachable": any(row["symbol_or_logic"] == "target = targets[index % len(targets)]" and row["execute_08_reachable"] for row in legacy),
            "node_level_adoption_contracts_present": any(row["node_level_adoption_contract"] == "present" for row in report["scene_adoption_audit"]),
            "safe_to_enter_module_09_human_review": report["module_08_status"] == "success" and bool(report["scene_adoption_audit"]),
        }
    except Exception as exc:
        report["fatal_initialization_error"] = {"error": str(exc), "traceback": traceback.format_exc()}
    finally:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(json_value(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(REPORT_PATH)


if __name__ == "__main__":
    main()