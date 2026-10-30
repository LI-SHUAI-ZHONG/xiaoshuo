"""Replace loose scene activation with an auditable, default-deny quality workflow."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 场景创作激活 as activation
import 全资料生产能力门 as capability
import 全量资料严格隔离审计 as isolation
import 章节质量资料就绪度门 as readiness
from 项目创作生产政策 import validate_creation_inputs, validate_policy


WORKFLOW_FILE = Path("配置") / "全流程创作质量方案.json"
PLAN_FILE = Path("文档") / "证据" / "全量资料正文生产编排.json"
CHARACTER_PERFORMANCE_FILE = Path("文档") / "证据" / "全流程人物表现结果.json"
CHARACTER_PERFORMANCE_FIELDS = (
    "distinctive_choice",
    "information_boundary",
    "pressure_response",
    "dialogue_function",
    "relationship_effect",
)


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _text(value: Any) -> str:
    return str(value or "").strip()


def _scene_terms(scene: dict[str, Any]) -> set[str]:
    generic = {"选择", "代价", "风险", "证据", "异常", "玄幻", "修炼", "宗门"}
    return {term for term in scene.get("retrieval_terms", []) if _text(term) and term not in generic}


def _candidate_write_allowed(status: str) -> bool:
    return status == "approved_for_model_candidate_generation"


def validate_character_performance_results(results: Any) -> dict[str, Any]:
    """Validate scene-level character results without inferring literary quality.

    Each result must point to a paragraph, or explicitly explain why that item
    is deferred.  A keyword, label, or boolean alone is never evidence.
    """
    records = results.get("records", []) if isinstance(results, dict) else results
    if not isinstance(records, list) or not records:
        return {
            "status": "deferred",
            "contract_status": "deferred",
            "record_count": 0,
            "deferred_count": 0,
            "errors": [],
            "policy": "缺少当前步骤 10/11 人物表现结果，不推断为已通过。",
        }
    errors: list[dict[str, str]] = []
    deferred_count = 0
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            errors.append({"record": str(index), "field": "record", "message": "人物表现记录必须是对象"})
            continue
        record_id = _text(record.get("result_id")) or _text(record.get("scene_id")) or f"record-{index}"
        results_by_field = record.get("performance_results")
        if not isinstance(results_by_field, dict):
            errors.append({"record": record_id, "field": "performance_results", "message": "缺少五项人物表现结果对象"})
            continue
        for field in CHARACTER_PERFORMANCE_FIELDS:
            item = results_by_field.get(field)
            if not isinstance(item, dict):
                errors.append({"record": record_id, "field": field, "message": "缺少结构化结果；关键词或布尔值不能单独通过"})
                continue
            location = _text(item.get("prose_location"))
            deferred_reason = _text(item.get("deferred_reason"))
            if not location and not deferred_reason:
                errors.append({"record": record_id, "field": field, "message": "必须提供 prose_location 或 deferred_reason；关键词不能单独作为证据"})
            elif deferred_reason and not location:
                deferred_count += 1
            elif location and not (_text(item.get("paragraph_index")) or item.get("paragraph_index") == 0):
                errors.append({"record": record_id, "field": field, "message": "prose_location 必须绑定 paragraph_index"})
    status = "blocked" if errors else "passed"
    return {
        "status": "deferred" if status == "passed" and deferred_count else status,
        "contract_status": status,
        "record_count": len(records),
        "deferred_count": deferred_count,
        "errors": errors,
        "checked_fields": list(CHARACTER_PERFORMANCE_FIELDS),
        "policy": "每个场景创作对象的五项表现结果必须绑定段落定位；尚未具备依据时只能填写 deferred_reason，不得以关键词命中替代证据。",
    }


def _write_active_production_projection(evidence: Path, records: list[dict[str, Any]]) -> None:
    """Keep active queue and batch manifests as exact projections of approved candidates."""
    queue = evidence / "全量资料正文生产队列.jsonl"
    batches = evidence / "全量资料正文生产批次.jsonl"
    queue.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    grouped: dict[str, list[str]] = {}
    for row in records:
        batch_id = _text(row.get("batch_id"))
        consumption_id = _text(row.get("consumption_id"))
        if batch_id and consumption_id:
            grouped.setdefault(batch_id, []).append(consumption_id)
    batches.write_text("".join(json.dumps({"batch_id": batch_id, "consumption_ids": consumption_ids}, ensure_ascii=False) + "\n" for batch_id, consumption_ids in sorted(grouped.items())), encoding="utf-8")


def _decision_errors(brief: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    scenes = brief.get("scenes", [])
    for index, scene in enumerate(scenes if isinstance(scenes, list) else [], 1):
        scene_id = _text(scene.get("scene_id")) or f"scene-{index}"
        for field in ("creative_need", "stage", "title"):
            if not _text(scene.get(field)):
                errors.append({"scene_id": scene_id, "rule": "scene_decision", "message": f"缺少 {field}"})
        if not _scene_terms(scene):
            errors.append({"scene_id": scene_id, "rule": "scene_specificity", "message": "缺少非通用的场景特异检索词"})
    return errors


def _activation_errors(plan: dict[str, Any], brief: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    by_scene = {str(scene.get("scene_id")): scene for scene in brief.get("scenes", []) if isinstance(scene, dict)}
    for row in plan.get("candidate_records", []):
        if not isinstance(row, dict):
            continue
        scene = by_scene.get(str(row.get("scene_id")), {})
        matched = set(row.get("activation", {}).get("matched_project_terms", []))
        specific = matched & _scene_terms(scene)
        if len(matched) < 2 or not specific:
            errors.append({"scene_id": str(row.get("scene_id")), "candidate_id": str(row.get("candidate_id")), "rule": "semantic_activation", "message": "候选必须命中至少两个检索词，且至少一个为场景特异词；通用词单命中不足"})
        if row.get("source_kind") in activation.TYPE_CONNECTION_KINDS:
            errors.append({"scene_id": str(row.get("scene_id")), "candidate_id": str(row.get("candidate_id")), "rule": "unselected_type_isolation", "message": "未确认项目类型时，类型名称和类型连接不得进入候选正文任务；应绑定类型系统来源块资料"})
    return errors


def _revoke_old_plan(root: Path, old: dict[str, Any], reason: str) -> None:
    if not old.get("records") or old.get("status") == "superseded_by_full_quality_workflow":
        return
    evidence = root / "文档" / "证据"
    archive = {"schema_version": "superseded-scene-activation-archive-1.0", "revoked_at": datetime.now(timezone.utc).isoformat(), "reason": reason, "prose_write_allowed": False, "release_status": "revoked_nonrelease", "prior_plan": old}
    revoked_file = evidence / "已废止场景激活任务.json"
    revoked_file.parent.mkdir(parents=True, exist_ok=True)
    revoked_file.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evidence / "场景创作激活任务.jsonl").write_text("", encoding="utf-8")


def run(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    policy = validate_policy(root)
    config = _read(root / "配置" / "project_config.json", {})
    mode_errors = validate_creation_inputs(config, config.get("creation_inputs", []) if isinstance(config, dict) else [])
    workflow = _read(root / WORKFLOW_FILE, {})
    if workflow.get("default_decision") != "deny" or not workflow.get("gates"):
        raise ValueError("全流程创作质量方案不完整或不是默认拒绝")
    evidence = root / "文档" / "证据"
    old = _read(root / PLAN_FILE, {})
    _revoke_old_plan(root, old, "旧激活计划只验证类别和关键词，未满足统一场景充分性与全流程质量门")
    brief = _read(root / activation.BRIEF_FILE, {})
    decision_errors = _decision_errors(brief)
    capability_report = capability.audit(root)
    readiness_report = readiness.audit(root)
    # Activation evaluation is intentionally read-only.  The quality gate owns
    # the active production projection and must audit only its final state.
    candidate_plan = activation.evaluate(root)
    activation_errors = _activation_errors(candidate_plan, brief)
    performance_path = root / CHARACTER_PERFORMANCE_FILE
    performance_document = _read(performance_path, {}) if performance_path.is_file() else []
    character_performance = validate_character_performance_results(performance_document)
    blockers = {
        "source_authorization": [] if policy else ["项目生产政策无效"],
        "material_capability": [name for name, report in (("全资料生产能力门", capability_report), ("章节质量资料就绪度门", readiness_report)) if report.get("status") != "passed"],
        "chapter_scene_decision": decision_errors,
        "semantic_activation": activation_errors + candidate_plan.get("required_source_kind_gaps", []),
        "character_performance": character_performance.get("errors", []) if character_performance.get("status") == "blocked" else [],
    }
    blockers["source_authorization"].extend(mode_errors)
    eligible_candidates = [
        row for row in candidate_plan.get("candidate_records", [])
        if isinstance(row, dict) and row.get("model_input_eligible") is True and row.get("prose_write_allowed") is False
    ]
    if not eligible_candidates:
        blockers["semantic_activation"].append("没有通过逐条授权与逐场创作门的候选资料")
    status = "blocked_pending_quality_workflow" if any(blockers.values()) else "approved_for_model_candidate_generation"
    approved_candidates = eligible_candidates if _candidate_write_allowed(status) else []
    result = {
        "schema_version": "scene-to-release-quality-plan-1.0", "workflow_id": workflow["workflow_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(), "release_status": "draft_only",
        "formal_fact_status": "not_confirmed", "creation_mode": config.get("creation_mode"), "creation_mode_errors": mode_errors, "status": status, "model_input_allowed": _candidate_write_allowed(status),
        "prose_write_allowed": False, "policy": "默认拒绝。仅当模型候选前置门全部通过时才允许作为 draft_only 模型输入；双审校、消费验证和正式发布仍为后续独立门。",
        "inherited_policy_requirements": workflow["inherited_policy_requirements"], "gates": workflow["gates"],
        "gate_blockers": blockers, "character_performance": character_performance, "candidate_plan_summary": {"candidate_count": candidate_plan.get("queued_count", 0), "required_source_kind_gaps": candidate_plan.get("required_source_kind_gaps", []), "isolated_counts": candidate_plan.get("isolated_counts", {})}, "candidate_records": approved_candidates, "records": []
    }
    # Write the quality-plan shape before the isolation audit so a blocked plan
    # is audited as inactive rather than as a live legacy production queue.
    (root / PLAN_FILE).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_active_production_projection(evidence, [])
    (evidence / "场景创作激活任务.jsonl").write_text("", encoding="utf-8")
    isolation_report = isolation.audit(root)
    if isolation_report.get("status") != "passed" or isolation_report.get("future_production_allowed") is not True:
        result["candidate_isolation_failure"] = {
            "issue_count": isolation_report.get("issue_count", 0),
            "issues": isolation_report.get("issues", []),
        }
        result["status"] = "blocked_pending_quality_workflow"
        result["model_input_allowed"] = False
        result["prose_write_allowed"] = False
        result["candidate_records"] = []
        result["records"] = []
        _write_active_production_projection(evidence, [])
        # Persist the cleared plan before re-auditing.  Otherwise the report can
        # describe a queue that this run has already revoked.
        (root / PLAN_FILE).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        isolation_report = isolation.audit(root)
        result["gate_blockers"]["material_capability"].append("生产面已重置；需重新运行质量门")
    if isolation_report.get("status") != "passed" or isolation_report.get("future_production_allowed") is not True:
        result["gate_blockers"]["material_capability"].append("严格隔离审计")
    result["gate_blockers"]["material_capability"] = sorted(set(result["gate_blockers"]["material_capability"]))
    (root / PLAN_FILE).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True)
    report = run(parser.parse_args().project_root)
    print(json.dumps({"status": report["status"], "model_input_allowed": report["model_input_allowed"], "blocker_groups": sum(bool(value) for value in report["gate_blockers"].values())}, ensure_ascii=False))
    return 0 if report["model_input_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())