"""Validate the binding contract for future full-source model improvement batches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONTRACT_FILE = Path("配置") / "全量模型资料改进方案.json"
SOURCE_KINDS = {"资料库", "动态网络", "静态网络", "锚点网络", "类型系统", "类型系统来源块", "类型连接"}
WORKFLOW = [
    "unified_resource_registration_and_integrity_gate", "original_object_readback_and_hash",
    "model_diagnosis", "model_revision_candidate_for_diagnosed_issue_only",
    "deterministic_safety_provenance_and_consistency_validation", "automatic_derived_material_batch",
    "original_upgrade_object_mapping_and_field_level_fusion",
    "project_adoption_and_scene_translation", "automatic_prose_and_material_release_gates",
]
METHOD_ORDER = [
    "unified_resource_registration_and_integrity_gate", "full_source_object_readback",
    "model_source_diagnosis_and_candidate_improvement", "automatic_candidate_validation_and_derived_batch",
    "original_upgrade_object_mapping_and_field_level_fusion",
    "project_adoption_decision", "scene_translation_and_consumption_evidence",
    "automatic_prose_and_release_gates",
]


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根对象必须为对象: {path}")
    return value


def validate(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    contract = _read(root / CONTRACT_FILE)
    errors: list[str] = []
    governing = contract.get("governing_method", {})
    if governing.get("primary_plan") != "文档/修补方案/创作资料全量调取修补主计划.md" or governing.get("immutable_method_order") != METHOD_ORDER:
        errors.append("模型必须嵌入既有全量调取主方法，且不得改变方法顺序")
    scope = contract.get("scope", {})
    if scope.get("coverage_mode") != "every_registered_binding":
        errors.append("改进范围必须覆盖每条已登记绑定")
    if set(scope.get("included_source_kinds", [])) != SOURCE_KINDS:
        errors.append("改进范围必须包含全部七类资料，包括全部类型资料")
    readback = contract.get("source_object_readback", {})
    required_input = {"binding_id", "source_id", "source_kind", "source_ref", "original_object", "original_object_sha256", "existing_creation_binding"}
    if readback.get("required") is not True or not required_input.issubset(set(readback.get("required_input_fields", []))) or readback.get("forbid_summary_only_model_input") is not True:
        errors.append("模型改进必须回读带哈希的原始对象，且禁止仅摘要输入")
    boundary = contract.get("type_boundary", {})
    if any(boundary.get(key) is not True for key in ("all_type_material_is_included_in_improvement", "project_type_confirmation_required_only_for_activation", "forbid_inferred_type_combination")):
        errors.append("类型资料改进与项目类型激活边界不完整")
    if contract.get("workflow") != WORKFLOW:
        errors.append("改进工作流必须按资源门、原始对象、诊断、候选、自动校验、派生批次、场景转译和发布门顺序执行")
    model = contract.get("model_requirements", {})
    if any(model.get(key) is not True for key in ("diagnosis_before_revision", "revision_only_for_diagnosed_issue", "forbid_invented_facts", "unknown_or_unverified_must_remain_explicit", "resumable_by_binding_id")):
        errors.append("模型诊断、候选修订与事实边界不完整")
    assurance = contract.get("automatic_assurance", {})
    required_gates = {"contract_validation_before_model_call", "resource_registry_path_and_hash_match", "binding_coverage_and_uniqueness", "source_ref_resolution_and_original_object_hash", "model_input_hash_matches_locked_object", "candidate_schema_and_diagnosis_link", "no_invented_or_unverified_facts", "source_kind_specific_required_fields", "cross_item_duplicate_and_conflict_detection", "derived_batch_manifest_and_append_only_evidence", "downstream_adoption_scene_and_release_gates"}
    if assurance.get("human_review_is_not_a_required_stage") is not True or set(assurance.get("required_gates", [])) != required_gates or "恰有一个终态" not in str(assurance.get("completion_rule", "")):
        errors.append("自动验收、全量终态覆盖或失败隔离约束不完整")
    derived = contract.get("derived_batch_requirements", {})
    if any(derived.get(key) is not expected for key, expected in (("versioned_batch_id_required", True), ("original_sources_immutable", True), ("existing_bindings_immutable", True), ("release_eligible_only_after_all_automatic_gates", True), ("formal_fact_eligible_before_approval", False), ("formal_publication_allowed_before_release_gate", False))):
        errors.append("派生批次的版本化或不可变边界不完整")
    fusion = contract.get("fusion_requirements", {})
    required_actions = {"retain", "correct", "complete", "extend", "restructure", "conflict"}
    required_layers = {"material_fused", "validated_overlay", "index_derived", "project_consumption"}
    required_artifacts = {"manifest.json", "field_changes.jsonl", "unresolved_conflicts.jsonl", "merge_preview.json"}
    required_fusion_gates = {"original_object_readback", "original_object_sha256_match", "upgrade_source_ref_and_sha256", "canonical_object_identity_match", "field_schema_validation", "dependency_and_conflict_validation", "project_consumption_isolation"}
    required_units = {"scalar", "set_member", "relation", "condition", "effect", "constraint", "exception", "guarantee_boundary", "structure"}
    required_unit_fields = {"unit_id", "unit_kind", "field_path", "semantic_key", "baseline_value", "candidate_value", "source_refs", "derivation_rule"}
    required_same_source_checks = {"baseline_object_sha256_match", "entry_id_and_dependency_target_exist", "no_self_dependency", "dependency_cycle_detection", "semantic_key_duplicate_and_conflict_detection", "source_locator_and_derivation_rule"}
    semantic_keys = fusion.get("source_kind_semantic_keys", {})
    same_source = fusion.get("same_source_derived_improvement", {})
    if fusion.get("required") is not True or governing.get("fusion_plan") != "文档/修补方案/原版升级资料字段级融合固定方案.md" or fusion.get("object_identity_field") != "canonical_object_id" or set(fusion.get("allowed_field_actions", [])) != required_actions or set(fusion.get("output_layers", [])) != required_layers or set(fusion.get("required_artifacts", [])) != required_artifacts or set(fusion.get("direct_merge_requires", [])) != required_fusion_gates or fusion.get("original_sources_immutable") is not True or fusion.get("project_consumption_must_not_enter_material_fused") is not True or fusion.get("semantic_merge_required") is not True or fusion.get("forbid_untyped_array_append") is not True or fusion.get("resolved_material_view_required") is not True or set(fusion.get("semantic_unit_kinds", [])) != required_units or set(fusion.get("rule_unit_required_fields", [])) != required_unit_fields or not all(kind in semantic_keys for kind in ("资料库", "静态网络", "动态网络", "类型连接", "锚点网络")) or same_source.get("allowed") is not True or same_source.get("source_class") != "same_source_derived_improvement" or same_source.get("may_enter") != "validated_overlay" or same_source.get("must_not_auto_enter") != "material_fused" or set(same_source.get("required_checks", [])) != required_same_source_checks:
        errors.append("原版升级资料字段级融合边界或必需工件不完整")
    legacy = contract.get("legacy_experiment", {})
    if legacy.get("classification") != "experimental_nonrelease" or legacy.get("may_not_enter_derived_batch") is not True:
        errors.append("摘要候选实验必须永久标为不可发布")
    return {"schema_version": "full-model-material-improvement-contract-validation-1.0", "status": "passed" if not errors else "blocked", "error_count": len(errors), "errors": errors, "execution_allowed": not errors, "formal_release_allowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())