"""Audit whether the complete source system can support quality generation.

This is a capability gate, not a chapter-quality check. It distinguishes a
translated record from a usable creative contract and keeps deferred material
explicit instead of treating assignment counts as proof of readiness.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_KINDS = ("资料库", "类型系统", "类型连接", "动态网络", "静态网络", "锚点网络")
RESOURCE_KEYS = {
    "资料库": "library", "类型系统": "type_system", "类型连接": "type_connections",
    "动态网络": "dynamic_network", "静态网络": "static_network", "锚点网络": "anchor_network",
}
TEMPLATE_MARKERS = ("沈砚在宗门秩序", "当前开篇场景", "宗门秩序与能量异常")
REQUIRED_CONTRACTS = {"creative_object", "creative_action", "activation_policy", "evidence_contract"}
QUALITY_STRATEGY_FIELDS = ("source_specific_trigger", "observable_action", "observable_result", "cost_or_change")
GENERIC_STRATEGY_MARKERS = (
    "前置产物出现与该资料意义相符的具体问题",
    "角色选择或场景状态发生可追踪变化",
    "把条目意义转成角色选择、冲突后果和可观察细节",
)
STRATEGY_REQUIRED_FIELDS = (*QUALITY_STRATEGY_FIELDS, "semantic_anchor", "evidence_location", "quality_rule")


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "；".join(_text(item) for item in value)
    return str(value or "").strip()


def _has_value(value: Any) -> bool:
    return bool(_text(value)) if not isinstance(value, dict) else bool(value)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _activation_policy_errors(policy: Any, prerequisite_record: dict[str, Any] | None) -> list[str]:
    if not isinstance(policy, dict):
        return ["activation_policy 必须为结构化对象"]
    errors = []
    conditions = policy.get("conditions")
    if not isinstance(conditions, list) or not all(isinstance(item, str) and item.strip() for item in conditions):
        errors.append("activation_policy.conditions 必须为非空文本数组")
        conditions = []
    if not _has_value(policy.get("mode")):
        errors.append("activation_policy 缺少 mode")
    if not isinstance(policy.get("activation_evidence"), list) or not policy["activation_evidence"]:
        errors.append("activation_policy 缺少 activation_evidence")
    if not prerequisite_record:
        return errors
    policy_text = " ".join([_text(policy.get("mode")), *conditions])
    semantic = [item for item in prerequisite_record.get("activation_prerequisites", []) if item.get("kind") != "source_qualification"]
    if semantic and not any(token in policy_text for token in ("条件", "选择", "匹配", "触发", "类型", "关系", "机制", "结构")):
        errors.append("activation_policy 未声明原资料的选择、匹配或触发语义门")
    for item in semantic:
        requirement = _text(item.get("requirement"))
        if requirement == "project_selection_required" and not any(token in policy_text for token in ("选择", "确定", "匹配")):
            errors.append("activation_policy 未覆盖 project_selection_required")
        elif item.get("kind") == "material_context_match":
            keyword = requirement[:2]
            if keyword and keyword not in policy_text and "匹配" not in policy_text:
                errors.append(f"activation_policy 未覆盖上下文条件：{requirement}")
        elif item.get("kind") == "material_semantic_condition" and requirement not in policy_text:
            errors.append(f"activation_policy 未覆盖来源条件：{requirement}")
    return list(dict.fromkeys(errors))


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    registry = _read(evidence / "资源注册表.json", {})
    bindings = _read(evidence / "全量资料解释词创作绑定.json", {})
    matrix = _read(evidence / "全书资料激活矩阵.json", {})
    governance = _read(evidence / "全量资料治理" / "全量检查报告.json", {})
    prerequisite_rows = _read_jsonl(evidence / "严格资料升级" / "资料激活前置条件审计" / "资料激活前置条件清单.jsonl")
    prerequisites_by_binding = {str(row.get("binding_id")): row for row in prerequisite_rows}
    records = bindings.get("records", []) if isinstance(bindings, dict) else []
    resources = registry.get("resources", {}) if isinstance(registry, dict) else {}
    summary: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    source_quality_notices: list[dict[str, str]] = []
    for kind in REQUIRED_KINDS:
        resource = resources.get(RESOURCE_KEYS[kind], {}) if isinstance(resources, dict) else {}
        rows = [row for row in records if row.get("source_kind") == kind]
        governance_item = (governance.get("summary", {}) or {}).get(kind, {})
        counts = Counter()
        for row in rows:
            if row.get("translation_status") == "translated":
                counts["translated"] += 1
            meaning = row.get("semantic_interpretation", {})
            binding = row.get("creation_binding", {})
            contract = row.get("evidence_contract", {})
            strategy = binding.get("creative_strategy", {})
            row_errors = []
            if row.get("translation_status") != "translated" or not _has_value(meaning.get("source_meaning")):
                row_errors.append("缺少可审阅语义解释")
            if any(marker in json.dumps(binding, ensure_ascii=False) for marker in TEMPLATE_MARKERS):
                row_errors.append("创作绑定仍含项目特例模板")
            if not all(_has_value(binding.get(field)) for field in ("creative_object", "creative_action")):
                row_errors.append("缺少创作对象或创作动作")
            row_errors.extend(_activation_policy_errors(binding.get("activation_policy"), prerequisites_by_binding.get(str(row.get("binding_id")))))
            if not all(_has_value(contract.get(field)) for field in ("design_required", "scene_required", "prose_required")):
                row_errors.append("缺少阶段证据契约")
            if not all(_has_value(strategy.get(field)) for field in STRATEGY_REQUIRED_FIELDS):
                row_errors.append("缺少逐条资料的触发、行动、结果或代价变化策略")
            if any(marker in json.dumps(strategy, ensure_ascii=False) for marker in GENERIC_STRATEGY_MARKERS):
                row_errors.append("创作策略仍是通用占位句，不能证明已完成作品化升级")
            anchor = _text(strategy.get("semantic_anchor"))
            source_text = " ".join(_text(row.get(field)) for field in ("name", "source_id", "source_ref"))
            semantic_values = [
                _text(meaning.get("source_meaning")),
                _text(meaning.get("source_semantic_anchor")),
                *[_text(item) for item in meaning.get("semantic_terms", [])],
            ]
            semantic_match = any(
                value and (anchor in value or value in anchor or value.startswith(anchor) or anchor.startswith(value))
                for value in semantic_values
            )
            if not anchor or len(anchor) < 2 or (anchor not in source_text and not semantic_match):
                row_errors.append("创作策略缺少可回链到该条资料的语义锚点")
            if row_errors:
                counts["failed"] += 1
                if len(failures) < 200:
                    failures.append({"binding_id": row.get("binding_id"), "source_kind": kind, "source_id": row.get("source_id"), "errors": row_errors})
            else:
                counts["ready"] += 1
            counts[str(row.get("activation_status", "unknown"))] += 1
        if not rows:
            counts["failed"] += 1
            failures.append({"source_kind": kind, "errors": ["没有对应的全量绑定记录"]})
        if governance_item.get("pending", 0) or governance_item.get("blocking", 0):
            failures.append({"source_kind": kind, "errors": ["全量治理仍有 pending 或 blocking 条目"]})
        if resource.get("source_quality") != "complete":
            source_quality_notices.append({
                "source_kind": kind,
                "source_quality": str(resource.get("source_quality", "unknown")),
                "notice": "来源证据尚未达到 complete；保持正式事实资格关闭，但不以此删除已回链的创作合同。",
            })
        summary[kind] = {
            "source_records": len(rows),
            "ready_contracts": counts["ready"],
            "quality_ready_contracts": counts["ready"],
            "translated_contracts": counts["translated"],
            "failed_contracts": counts["failed"],
            "activation_status_counts": {key: value for key, value in counts.items() if key not in {"ready", "failed"}},
            "governance": governance_item,
            "resource_quality": resource.get("source_quality", "unknown"),
            "status": "passed" if rows and counts["failed"] == 0 and not governance_item.get("pending", 0) and not governance_item.get("blocking", 0) else "failed",
        }
    duplicate_ids = [source_id for source_id, count in Counter(str(row.get("source_id")) for row in records).items() if count > 1 and source_id != "None"]
    if duplicate_ids:
        failures.append({"scope": "bindings", "errors": [f"source_id 重复：{len(duplicate_ids)} 条"]})
    assigned = matrix.get("assignments", matrix.get("records", [])) if isinstance(matrix, dict) else []
    report = {
        "schema_version": "source-production-capability-1.0",
        "project_id": _read(root / "配置" / "project_config.json", {}).get("project_id"),
        "policy": "全量资料必须可解释、可执行、可激活、可验收；未激活资料只能进入递延队列，不得被计为已消费。来源资格不足必须作为风险保留，不得据此静默删除已回链的创作合同或提升正式事实资格。",
        "required_source_kinds": list(REQUIRED_KINDS),
        "binding_count": len(records),
        "activation_assignment_count": len(assigned) if isinstance(assigned, list) else 0,
        "kind_summary": summary,
        "source_quality_notices": source_quality_notices,
        "failure_count": len(failures),
        "failures": failures,
        "status": "passed" if not failures and all(item["status"] == "passed" for item in summary.values()) else "failed",
        "production_status": "draft_only_quality_generation_allowed" if not failures else "blocked_until_source_contracts_fixed",
    }
    target = evidence / "全资料生产能力报告.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = audit(args.project_root)
    print(json.dumps({"status": report["status"], "production_status": report["production_status"], "failure_count": report["failure_count"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())