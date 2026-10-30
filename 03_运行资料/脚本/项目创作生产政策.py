"""Enforce the durable project policy before classified prose production."""
from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any


POLICY_FILE = Path("配置") / "项目创作生产政策.json"
LIFECYCLE_FILE = Path("配置") / "创作资料最终状态规范.json"
SOURCE_KINDS = {
    "资料库", "动态网络", "静态网络", "锚点网络",
    "类型系统", "类型系统来源块", "类型连接",
}
CREATION_MODES = {"generic_novel", "project_bound"}
GENERIC_ALLOWED_LAYERS = {"generic_type", "creative_method", "structure_contract"}
PROJECT_BOUND_LAYERS = GENERIC_ALLOWED_LAYERS | {"project_authorization", "project_fact", "historical_artifact"}
PROJECT_INPUT_ROLES = {"project_authorization", "project_fact", "legacy_prose", "historical_artifact"}
REQUIRED_STRATEGY_FIELDS = {
    "source_specific_trigger", "observable_action", "observable_result",
    "cost_or_change", "semantic_anchor", "evidence_location", "quality_rule",
}


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取项目创作生产政策: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("项目创作生产政策必须是 JSON 对象")
    return value


def creation_mode(config: dict[str, Any]) -> str:
    """Return the explicit creation mode; project_mode is not a substitute."""
    mode = str(config.get("creation_mode") or "").strip()
    if mode not in CREATION_MODES:
        raise ValueError("project_config.creation_mode 必须明确为 generic_novel 或 project_bound")
    return mode


def validate_creation_inputs(config: dict[str, Any], inputs: list[dict[str, Any]]) -> list[str]:
    """Enforce mode-specific inputs before scene activation or prose production."""
    try:
        mode = creation_mode(config)
    except ValueError as exc:
        return [str(exc)]
    allowed_layers = GENERIC_ALLOWED_LAYERS if mode == "generic_novel" else PROJECT_BOUND_LAYERS
    errors: list[str] = []
    for index, row in enumerate(inputs, 1):
        if not isinstance(row, dict):
            errors.append(f"第 {index} 条创作输入不是对象")
            continue
        layer = str(row.get("input_layer") or row.get("evidence_layer") or "").strip()
        role = str(row.get("input_role") or "").strip()
        path = str(row.get("path") or row.get("source_path") or "").strip()
        if layer not in allowed_layers:
            errors.append(f"第 {index} 条输入层级不允许：{layer or 'missing-layer'}（{mode}）")
        if mode == "generic_novel" and (role in PROJECT_INPUT_ROLES or layer in {"project_fact", "project_authorization", "historical_artifact"}):
            errors.append(f"generic_novel 禁止项目输入：{path or role or f'input-{index}'}")
    return errors


def validate_policy(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    policy_path = root / POLICY_FILE
    # Temporary test projects may omit copied configuration; use the checked-in
    # policy beside this module, while real project roots remain authoritative.
    if not policy_path.is_file():
        policy_path = Path(__file__).resolve().parents[1] / POLICY_FILE
    policy = _read(policy_path)
    if policy.get("creation_modes") != sorted(CREATION_MODES):
        raise ValueError("项目创作生产政策缺少完整 creation_modes")
    required = {
        "authorization_is_not_consumption",
        "classification_required_before_activation",
        "matched_creative_need_and_stage_evidence_required",
        "model_required_for_quality_candidate",
        "automatic_validation_required_before_derived_batch",
        "formal_release_requires_project_source_confirmation",
        "type_connection_requires_project_type_confirmation",
        "full_material_improvement_requires_original_object_readback",
        "full_material_improvement_covers_all_source_kinds",
        "type_selection_blocks_activation_not_source_improvement",
        "type_rule_material_binding_does_not_require_project_type_confirmation",
        "experimental_summary_candidates_are_nonrelease",
    }
    boundaries = policy.get("hard_boundaries", {})
    missing = sorted(key for key in required if boundaries.get(key) is not True)
    kinds = set(policy.get("source_kinds", {}))
    if kinds != SOURCE_KINDS:
        missing.append("source_kinds 分类映射不完整")
    strategy_fields = set(policy.get("required_strategy_fields", []))
    missing.extend(sorted(REQUIRED_STRATEGY_FIELDS - strategy_fields))
    improvement_policy = policy.get("full_material_improvement_policy", {})
    if not isinstance(improvement_policy, dict) or improvement_policy.get("required_before_new_improvement_batch") is not True or improvement_policy.get("contract") != "配置/全量模型资料改进方案.json" or improvement_policy.get("validator") != "全量模型资料改进方案.py":
        missing.append("全量模型资料改进方案约束不完整")
    lifecycle_path = root / LIFECYCLE_FILE
    if not lifecycle_path.is_file():
        missing.append("创作资料最终状态规范缺失")
    else:
        lifecycle = _read(lifecycle_path)
        if set(lifecycle.get("canonical_source_kinds", [])) != SOURCE_KINDS - {"类型系统来源块"}:
            missing.append("创作资料最终状态规范的六大主资料不完整")
        if not lifecycle.get("transition_policy", {}).get("no_implicit_promotion"):
            missing.append("创作资料最终状态规范未禁止隐式状态升级")
        if not lifecycle.get("required_object_fields"):
            missing.append("创作资料最终状态规范缺少对象合同字段")
    if missing:
        raise ValueError("项目创作生产政策不完整: " + ", ".join(missing))
    return policy


def validate_bindings(policy: dict[str, Any], bindings: dict[str, Any], *, allow_legacy_test_bindings: bool = False) -> None:
    records = bindings.get("records", []) if isinstance(bindings, dict) else []
    if not isinstance(records, list):
        raise ValueError("创作绑定 records 必须是数组")
    for index, row in enumerate(records, 1):
        if not isinstance(row, dict):
            raise ValueError(f"第 {index} 条创作绑定不是对象")
        kind = str(row.get("source_kind") or "")
        if not kind and allow_legacy_test_bindings:
            continue
        if kind not in SOURCE_KINDS:
            raise ValueError(f"第 {index} 条资料分类未登记: {kind!r}")
        strategy = row.get("creation_binding", {}).get("creative_strategy", {})
        if not isinstance(strategy, dict) or not all(str(strategy.get(field) or "").strip() for field in REQUIRED_STRATEGY_FIELDS):
            raise ValueError(f"第 {index} 条资料缺少分类升级所需的完整 creative_strategy")
        if kind == "类型连接":
            config = bindings.get("type_combination_adopted")
            if config is True:
                raise ValueError("类型连接不得绕过项目类型组合确认")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    policy = validate_policy(root)
    evidence = root / "文档" / "证据"
    bindings = _read(evidence / "全量资料解释词创作绑定.json")
    validate_bindings(policy, bindings)
    print(json.dumps({
        "status": "passed",
        "policy_id": policy["policy_id"],
        "source_kind_count": len(policy["source_kinds"]),
        "binding_count": len(bindings.get("records", [])),
        "release_status": policy["release_status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())