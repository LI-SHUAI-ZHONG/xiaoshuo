"""Audit whether source contracts are detailed enough for chapter-quality work.

This is a material-readiness gate.  It evaluates every translated source
contract but never creates story facts, chapter plans, or prose.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from pathlib import Path
from typing import Any


OPENING_TERMS = ("黄金三章", "开篇", "场景内部因果", "场景与下一场景因果", "场景结局不可逆", "章尾钩子")
STRATEGY_FIELDS = ("source_specific_trigger", "observable_action", "observable_result", "cost_or_change", "semantic_anchor", "evidence_location", "quality_rule")
EVIDENCE_FIELDS = {
    "design_required": ("stage", "creative_object", "creative_action", "source_ref"),
    "scene_required": ("scene_id", "trigger", "action", "observable_result", "cost_or_change"),
    "prose_required": ("prose_location", "trigger", "action", "observable_result", "paragraph_sha256"),
}


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "；".join(_text(item) for item in value)
    return str(value or "").strip()


def _source_file(source_ref: Any) -> str:
    if isinstance(source_ref, dict):
        return _text(source_ref.get("file"))
    if isinstance(source_ref, str):
        try:
            parsed = ast.literal_eval(source_ref)
        except (SyntaxError, ValueError):
            # Structured JSON sources use ``path:locator`` rather than a
            # dictionary literal; only the filesystem portion is needed here.
            return source_ref.split(":", 1)[0].replace("\\", "/")
        return _text(parsed.get("file")) if isinstance(parsed, dict) else source_ref.split(":", 1)[0].replace("\\", "/")
    return ""


def _contains_all(container: Any, required: tuple[str, ...]) -> bool:
    return isinstance(container, list) and all(item in container for item in required)


def record_errors(root: Path, row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_file = _source_file(row.get("source_ref"))
    if not source_file or not (root / source_file).is_file():
        errors.append("source_ref 未提供可回读的项目内来源文件")
    interpretation = row.get("semantic_interpretation")
    if not isinstance(interpretation, dict) or not _text(interpretation.get("source_semantic_anchor")):
        errors.append("缺少来源语义锚点")
    binding = row.get("creation_binding")
    if not isinstance(binding, dict):
        return [*errors, "缺少结构化创作绑定"]
    if not _text(binding.get("creative_object")) or not _text(binding.get("creative_action")):
        errors.append("缺少明确创作对象或创作动作")
    strategy = binding.get("creative_strategy")
    for field in STRATEGY_FIELDS:
        if not isinstance(strategy, dict) or not _text(strategy.get(field)):
            errors.append(f"创作策略缺少 {field}")
    policy = binding.get("activation_policy")
    if not isinstance(policy, dict):
        errors.append("缺少结构化激活策略")
    else:
        if not _text(policy.get("mode")) or not isinstance(policy.get("conditions"), list) or not any(_text(item) for item in policy["conditions"]):
            errors.append("激活策略缺少模式或条件")
        if not isinstance(policy.get("activation_evidence"), list) or not policy["activation_evidence"]:
            errors.append("激活策略缺少证据要求")
        declared = _text(policy.get("source_declared_conditions"))
        if any(token in declared.lower() for token in ("candidate", "候选", "require_selection", "require_validation")):
            if "candidate_effect_policy" not in policy or not _text(policy.get("candidate_effect_policy")):
                errors.append("候选资料缺少不得提升为既定事实的限制")
    evidence = row.get("evidence_contract")
    for field, required in EVIDENCE_FIELDS.items():
        if not isinstance(evidence, dict) or not _contains_all(evidence.get(field), required):
            errors.append(f"验收合同缺少 {field} 的必要字段")
    return errors


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    bindings = _read(evidence / "全量资料解释词创作绑定.json", {})
    records = [row for row in bindings.get("records", []) if isinstance(row, dict)] if isinstance(bindings, dict) else []
    failures: list[dict[str, Any]] = []
    by_kind: dict[str, Counter[str]] = {}
    opening_records: list[dict[str, Any]] = []
    for row in records:
        kind = _text(row.get("source_kind")) or "unknown"
        counts = by_kind.setdefault(kind, Counter())
        errors = record_errors(root, row)
        counts["total"] += 1
        if errors:
            counts["failed"] += 1
            if len(failures) < 200:
                failures.append({"binding_id": row.get("binding_id"), "source_kind": kind, "source_id": row.get("source_id"), "errors": errors})
        else:
            counts["ready"] += 1
        searchable = " ".join((_text(row.get("name")), _text(row.get("source_id")), _text(row.get("semantic_interpretation"))))
        if any(term in searchable for term in OPENING_TERMS):
            opening_records.append({"binding_id": row.get("binding_id"), "source_id": row.get("source_id"), "name": row.get("name"), "source_ref": row.get("source_ref"), "status": "ready" if not errors else "gap", "errors": errors})
    opening_gaps = [row for row in opening_records if row["status"] != "ready"]
    report = {
        "schema_version": "chapter-quality-material-readiness-1.0",
        "scope": "all_translated_source_contracts; no_story_facts_or_prose_generated",
        "policy": "资料达到章节质量标准，指每条资料具备可回读来源、可执行创作策略、激活边界和可验证验收合同；这不等同于资料已被写入章节，更不授予正式事实资格。",
        "binding_count": len(records),
        "ready_count": sum(counts["ready"] for counts in by_kind.values()),
        "gap_count": sum(counts["failed"] for counts in by_kind.values()),
        "kind_summary": {kind: {"total": counts["total"], "ready": counts["ready"], "gaps": counts["failed"]} for kind, counts in by_kind.items()},
        "opening_method_materials": {"matched_count": len(opening_records), "ready_count": len(opening_records) - len(opening_gaps), "gaps": opening_gaps, "records": opening_records},
        "failures": failures,
        "formal_fact_eligible": False,
        "status": "passed" if records and not failures and not opening_gaps else "needs_material_upgrade",
        "next_step": "仅在后续项目创作请求中按合同检索和激活资料；不得将本报告当作章节已完成或项目事实已确认。",
    }
    (evidence / "章节质量资料就绪度报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = audit(args.project_root)
    print(json.dumps({"status": report["status"], "binding_count": report["binding_count"], "gap_count": report["gap_count"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())