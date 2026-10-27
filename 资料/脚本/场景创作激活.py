"""Build auditable, category-aware prose candidates from scene creative briefs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 项目创作生产政策 import REQUIRED_STRATEGY_FIELDS, validate_bindings, validate_policy
from 全量资料输入与正文授权 import authorized_bindings
from 资料资格与合同注册 import build_qualification_ledger, resolve_contract_fields
from 运行资料包契约 import build_package, validate_package, write_package
from 运行清单复核 import register_artifact


BRIEF_FILE = Path("配置") / "首章场景创作简报.json"
# Type names and type-combination relationships are not project facts. The
# source blocks behind the type system are the bindable material layer.
TYPE_CONNECTION_KINDS = {"类型连接", "类型系统"}
# Backwards-compatible export for validators that consume the activation module.
TYPE_ISOLATED_KINDS = TYPE_CONNECTION_KINDS
GENERIC_TERMS = {"选择", "代价", "风险", "证据", "异常", "玄幻", "修炼", "宗门"}
SOURCE_CANDIDATE_USES = {
    "资料库": "narrative_translation_constraint",
    "动态网络": "state_transition_constraint",
    "静态网络": "relationship_cost_constraint",
    "锚点网络": "decision_observation_constraint",
}


def _material_duty(row: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    binding = row.get("creation_binding", {})
    binding = binding if isinstance(binding, dict) else {}
    role = _text(binding.get("material_role"))
    stages = [str(item) for item in binding.get("applicable_stage", binding.get("stages", [])) if str(item).strip()]
    dimensions = [str(item) for item in binding.get("required_writing_dimensions", []) if str(item).strip()]
    requested = [str(item) for item in scene.get("required_writing_dimensions", []) if str(item).strip()]
    if not requested and _text(scene.get("stage")) in stages and _text(row.get("source_kind")) not in TYPE_CONNECTION_KINDS:
        requested = list(dimensions)
    authorization = resolve_contract_fields(row | {
        "activation_conditions_met": scene.get("activation_conditions_met"),
        "activation_evidence": scene.get("activation_evidence", []),
    }, "authorization_contract")
    matched = bool(role and stages and dimensions and _text(scene.get("stage")) in stages and set(dimensions) & set(requested))
    # Selection and model-input eligibility are not prose authorization. The
    # explicit material-duty contract alone determines whether paragraph-level
    # evidence is required; runtime package authorization remains separate.
    legacy_duty = not requested and not role and not stages and not dimensions
    prose_allowed = bool(
        (matched and binding.get("prose_evidence_required", True) is True)
        or legacy_duty
    )
    return {
        "material_role": role or "unknown",
        "applicable_stage": stages,
        "required_writing_dimensions": dimensions,
        "scene_required_writing_dimensions": requested,
        "prose_evidence_required": prose_allowed,
        "authorization_contract_errors": authorization.get("missing", []) + authorization.get("conflicts", []) + ([authorization.get("version_error")] if authorization.get("version_error") else []),
        "deferred_reason": "" if matched and prose_allowed else (
            "旧绑定缺少职责合同字段，不能推导正文消费要求；已记录为递延。"
            if not role or not stages or not dimensions else
            "本场景仅使用资料的设计或约束职责，未要求正文逐段证明。"
        ),
    }


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    return str(value or "").strip()


def _terms(row: dict[str, Any]) -> set[str]:
    semantic = row.get("semantic_interpretation", {})
    binding = row.get("creation_binding", {})
    return set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", _text([
        row.get("name"), row.get("source_id"), semantic.get("semantic_terms", []) if isinstance(semantic, dict) else [],
        semantic.get("source_meaning") if isinstance(semantic, dict) else "",
        binding.get("creative_object") if isinstance(binding, dict) else "",
        binding.get("creative_action") if isinstance(binding, dict) else "",
    ])))


def _valid_strategy(row: dict[str, Any]) -> bool:
    strategy = row.get("creation_binding", {}).get("creative_strategy", {})
    return isinstance(strategy, dict) and all(_text(strategy.get(key)) for key in REQUIRED_STRATEGY_FIELDS)


def _source_provenance(row: dict[str, Any], matched_terms: list[str]) -> dict[str, Any] | None:
    source_ref = _text(row.get("source_ref"))
    # A serialized locator object is not a usable provenance record. It must be
    # repaired in the registry before it can become a writing candidate.
    if ":" not in source_ref or source_ref.startswith("{"):
        return None
    if row.get("source_kind") == "类型系统来源块" and not re.fullmatch(r"原始资料/类型系统\.txt:SOURCE\[\d+\]", source_ref):
        return None
    strategy = row["creation_binding"]["creative_strategy"]
    return {
        "source_ref": source_ref,
        "source_semantic_anchor": strategy["semantic_anchor"],
        "matched_retrieval_terms": matched_terms,
        "project_type_inference_forbidden": row.get("source_kind") == "类型系统来源块",
    }


def build_plan(bindings: dict[str, Any], brief: dict[str, Any], grants: dict[str, Any] | set[str] | None = None, limit_per_kind: int = 2, formal_creation_allowed: bool = True, allowed_scene_ids: set[str] | None = None, activation_version: str = "unbound") -> dict[str, Any]:
    if brief.get("status") != "authorial_draft" or brief.get("release_status") != "draft_only":
        raise ValueError("场景创作简报必须保持 authorial_draft 和 draft_only")
    scenes = brief.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("场景创作简报缺少 scenes")
    records = [row for row in bindings.get("records", []) if isinstance(row, dict)]
    planned: list[dict[str, Any]] = []
    excluded = Counter()
    scene_gaps: list[dict[str, Any]] = []
    # A binding is a single source object, so it may be dispatched to only one
    # scene. Keep the highest-scoring match and retain the rejected matches for
    # auditability instead of letting package validation discover the collision.
    binding_winners: dict[str, tuple[int, int, str]] = {}
    deferred_collisions: list[dict[str, Any]] = []
    for scene in scenes:
        required = set(scene.get("required_source_kinds", []))
        if not scene.get("activation_conditions_met") or not _text(scene.get("creative_need")) or not _text(scene.get("stage")):
            raise ValueError(f"场景 {scene.get('scene_id')} 缺少激活条件、创作需求或阶段")
        query = set(scene.get("retrieval_terms", []))
        selected: dict[str, list[tuple[int, dict[str, Any], list[str]]]] = defaultdict(list)
        for row in records:
            kind, binding_id = _text(row.get("source_kind")), _text(row.get("binding_id"))
            if kind in TYPE_CONNECTION_KINDS:
                excluded[kind] += 1
                continue
            if kind not in required or not _valid_strategy(row):
                continue
            matched = sorted(query & _terms(row))
            specific_matches = [term for term in matched if term not in GENERIC_TERMS]
            if len(matched) >= 2 and specific_matches:
                provenance = _source_provenance(row, matched)
                if provenance is not None:
                    selected[kind].append((len(matched), row, matched, provenance))
        for kind in sorted(required):
            if not selected[kind]:
                scene_gaps.append({"scene_id": scene["scene_id"], "source_kind": kind, "reason": "该场景要求此资料类别，但没有资料完整且语义匹配的候选资料"})
            for score, row, matched, provenance in sorted(selected[kind], key=lambda item: (-item[0], _text(item[1].get("binding_id"))))[:limit_per_kind]:
                binding_id = _text(row.get("binding_id"))
                winner = binding_winners.get(binding_id)
                scene_order = scenes.index(scene)
                candidate_key = (score, -scene_order, _text(scene.get("scene_id")))
                if winner is not None and candidate_key <= (winner[0], winner[1], winner[2]):
                    deferred_collisions.append({
                        "binding_id": binding_id,
                        "scene_id": scene.get("scene_id"),
                        "winner_scene_id": winner[2],
                        "match_score": score,
                        "reason": "同一绑定已在更高优先级场景中选中",
                    })
                    continue
                if winner is not None:
                    planned = [item for item in planned if item.get("binding_id") != binding_id]
                    deferred_collisions.append({
                        "binding_id": binding_id,
                        "scene_id": winner[2],
                        "winner_scene_id": scene.get("scene_id"),
                        "match_score": winner[0],
                        "reason": "同一绑定改由更高匹配分数场景使用",
                    })
                binding_winners[binding_id] = (score, -scene_order, _text(scene.get("scene_id")))
                strategy = row["creation_binding"]["creative_strategy"]
                grant = grants.get(_text(row.get("binding_id")), {}) if isinstance(grants, dict) else {}
                grant = grant if isinstance(grant, dict) else {}
                authorization = resolve_contract_fields(row | grant | scene, "authorization_contract")
                material_duty = _material_duty(row | grant, scene)
                contract_supplied = bool(grant) or isinstance(row.get("contracts"), dict)
                planned.append({
                    "candidate_id": f"CAND-{scene['scene_id']}-{row['binding_id']}",
                    "scene_id": scene["scene_id"], "chapter_id": scene.get("chapter_id"),
                    "binding_id": row["binding_id"], "source_id": row["source_id"], "source_kind": kind,
                    "candidate_use": SOURCE_CANDIDATE_USES.get(kind, "source_derived_creation_constraint"),
                    "status": "ready_for_draft_creation",
                    "model_input_eligible": (
                        authorization["passed"] and authorization["fields"].get("model_input_eligible") is True
                        if contract_supplied else True
                    ),
                    "prose_write_allowed": material_duty["prose_evidence_required"],
                    "activation": {"creative_need": scene["creative_need"], "matched_stage": scene["stage"], "matched_project_terms": matched, "activation_reason": f"命中场景检索词：{'、'.join(matched)}", "activation_evidence": scene["activation_evidence"], "match_score": score},
                    "source_provenance": provenance,
                    "material_duty": material_duty,
                    "causal_contract": {"semantic_anchor": strategy["semantic_anchor"], "trigger": strategy["source_specific_trigger"], "required_action": strategy["observable_action"], "required_result": strategy["observable_result"], "required_cost_or_change": strategy["cost_or_change"]},
                })
                if planned[-1]["material_duty"].get("authorization_contract_errors"):
                    planned[-1]["status"] = "deferred_contract_error"
    allowed_records = [row for row in planned if row["model_input_eligible"]]
    status = "ready_for_draft_creation" if allowed_records and not scene_gaps else "needs_creative_brief_refinement"
    return {"schema_version": "full-source-draft-creation-candidate-plan-1.0", "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "release_status": "draft_only", "formal_fact_status": brief.get("formal_fact_status"), "policy": "创作候选由资料完整性、语义匹配、来源溯源和因果契约决定；不要求逐条授权。类型系统来源块可作为规则资料绑定，不得据此推断或确认项目类型；正文消费、队列、批次和消费证据须在后续生成及审校验证完成后单独建立。", "formal_creation_allowed": bool(allowed_records), "scene_count": len(scenes), "queued_count": len(allowed_records), "source_kind_counts": dict(Counter(row["source_kind"] for row in allowed_records)), "isolated_counts": dict(excluded), "required_source_kind_gaps": scene_gaps, "deferred_binding_collisions": deferred_collisions, "status": status, "candidate_records": planned, "records": []}


def evaluate(project_root: str | Path, limit_per_kind: int = 2) -> dict[str, Any]:
    """Calculate activation candidates without changing the production surface."""
    root = Path(project_root).expanduser().resolve()
    runtime_policy_fallback = False
    try:
        policy = validate_policy(root)
    except ValueError as exc:
        policy_path = root / Path("配置") / "项目创作生产政策.json"
        if policy_path.exists():
            raise
        # A missing project policy blocks formal production, but it must not
        # prevent auditing a draft-only candidate plan from existing inputs.
        runtime_policy_fallback = True
        policy = {"source_kinds": {kind: kind for kind in SOURCE_CANDIDATE_USES}}
    evidence = root / "文档" / "证据"
    bindings = _read(evidence / "全量资料解释词创作绑定.json", {})
    binding_records = [row for row in bindings.get("records", []) if isinstance(row, dict)]
    qualification_ledger = build_qualification_ledger(root, binding_records)
    executable_ids = {row["binding_id"] for row in qualification_ledger["records"] if row.get("executable_entry")}
    if not executable_ids:
        raise ValueError("当前资格账本没有 executable_entry；不能把绑定数量或 selected 推导为可执行资料")
    bindings = dict(bindings)
    bindings["records"] = [row for row in binding_records if row.get("binding_id") in executable_ids]
    validate_bindings(policy, bindings)
    baseline_hash = hashlib.sha256(json.dumps(bindings, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    brief = _read(root / BRIEF_FILE, {})
    # Draft creation is governed by material and creative evidence, not approval.
    plan = build_plan(bindings, brief, None, limit_per_kind, activation_version=baseline_hash)
    plan["activation_version"] = baseline_hash
    plan["creation_admission"] = {"status": "material_and_evidence_based", "authorization_required": False, "formal_release_allowed": False}
    plan["runtime_policy_fallback"] = runtime_policy_fallback
    plan["contract_version"] = qualification_ledger["contract_version"]
    plan["qualification_ledger_sha256"] = qualification_ledger["ledger_sha256"]
    plan["qualification_counts"] = qualification_ledger["counts"]
    if runtime_policy_fallback:
        plan["creation_admission"]["warning"] = "缺少项目创作生产政策；当前仅能形成 draft_only 候选"
    return plan


def run(project_root: str | Path, limit_per_kind: int = 2) -> dict[str, Any]:
    """Evaluate candidates without creating prose-consumption projections."""
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    plan = evaluate(root, limit_per_kind)
    return plan


def build_runtime_material_package(project_root: str | Path, run_id: str, plan: dict[str, Any] | None = None, scene_contexts: list[dict[str, Any]] | None = None, frozen_bindings: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Persist only condition-met, explicitly authorized scene selections.

    Candidate ordering never activates a binding.  This adapter is deliberately
    default-deny so callers cannot promote a retrieval candidate into prose use.
    """
    root = Path(project_root).expanduser().resolve()
    bindings = _read(root / "文档" / "证据" / "全量资料解释词创作绑定.json", {})
    records = bindings.get("records", []) if isinstance(bindings, dict) else []
    grants = authorized_bindings(root, records)
    if frozen_bindings is None:
        raise ValueError("运行资料包必须接收模块08冻结的 action_chain.binding_id 集合")
    if not frozen_bindings:
        raise ValueError("模块08未冻结任何 action_chain.binding_id，禁止生成运行资料包")
    selections = []
    for candidate in frozen_bindings:
        if not isinstance(candidate, dict):
            raise ValueError("模块08冻结绑定记录必须是对象")
        activation = candidate.get("activation", {}) if isinstance(candidate.get("activation"), dict) else {}
        selections.append({
            "scene_id": candidate.get("scene_id"), "binding_id": candidate.get("binding_id"),
            "stage": candidate.get("stage") or "正文",
            "required_writing_dimensions": candidate.get("required_writing_dimensions", []),
            # Candidate planning already filters on the brief's scene-level
            # activation condition; preserve that fact in the run package.
            "activation_conditions_met": candidate.get("activation_conditions_met") is True,
            "activation_evidence": activation.get("activation_evidence", []),
            "selection_rationale": candidate.get("selection_rationale") or "场景条件、来源语义和创作目标均已匹配。",
        })
    package = build_package(root, run_id, records, selections, grants=grants, scene_contexts=scene_contexts)
    validation = validate_package(root, package, "scene")
    package_path = write_package(root, package)
    register_artifact(root, run_id, package_path, kind="material_package", module_id="08", status="passed" if validation["passed"] else "failed", exit_code=0 if validation["passed"] else 1)
    return package, validation


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--limit-per-kind", type=int, default=2)
    args = parser.parse_args(); plan = run(args.project_root, args.limit_per_kind)
    print(json.dumps({"status": plan["status"], "queued_count": plan["queued_count"], "source_kind_counts": plan["source_kind_counts"], "release_status": plan["release_status"]}, ensure_ascii=False)); return 0 if plan["status"] == "ready_for_draft_creation" else 2


if __name__ == "__main__":
    raise SystemExit(main())