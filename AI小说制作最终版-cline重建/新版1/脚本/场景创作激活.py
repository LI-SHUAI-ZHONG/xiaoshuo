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

from 全量资料输入与正文授权 import authorized_bindings
from 项目创作生产政策 import REQUIRED_STRATEGY_FIELDS, validate_bindings, validate_policy
from 计划锁与正式创作门 import validate_formal_creation_gate, validate_scene_formal_creation_gate


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
    if row.get("source_kind") == "类型系统来源块" and not re.fullmatch(r"原始资料/类型系统\.txt:SOURCE\[\d+\]", source_ref):
        return None
    strategy = row["creation_binding"]["creative_strategy"]
    return {
        "source_ref": source_ref,
        "source_semantic_anchor": strategy["semantic_anchor"],
        "matched_retrieval_terms": matched_terms,
        "project_type_inference_forbidden": row.get("source_kind") == "类型系统来源块",
    }


def build_plan(bindings: dict[str, Any], brief: dict[str, Any], grants: dict[str, Any], limit_per_kind: int = 2, formal_creation_allowed: bool = True, allowed_scene_ids: set[str] | None = None, activation_version: str = "unbound") -> dict[str, Any]:
    if brief.get("status") != "authorial_draft" or brief.get("release_status") != "draft_only":
        raise ValueError("场景创作简报必须保持 authorial_draft 和 draft_only")
    scenes = brief.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("场景创作简报缺少 scenes")
    records = [row for row in bindings.get("records", []) if isinstance(row, dict)]
    planned: list[dict[str, Any]] = []
    excluded = Counter()
    scene_gaps: list[dict[str, Any]] = []
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
            if kind not in required or binding_id not in grants or not _valid_strategy(row):
                continue
            matched = sorted(query & _terms(row))
            specific_matches = [term for term in matched if term not in GENERIC_TERMS]
            if len(matched) >= 2 and specific_matches:
                provenance = _source_provenance(row, matched)
                if provenance is not None:
                    selected[kind].append((len(matched), row, matched, provenance))
        for kind in sorted(required):
            if not selected[kind]:
                scene_gaps.append({"scene_id": scene["scene_id"], "source_kind": kind, "reason": "该场景要求此资料类别，但没有已授权且语义匹配的候选资料"})
            for score, row, matched, provenance in sorted(selected[kind], key=lambda item: (-item[0], _text(item[1].get("binding_id"))))[:limit_per_kind]:
                strategy = row["creation_binding"]["creative_strategy"]
                scene_allowed = formal_creation_allowed if allowed_scene_ids is None else scene["scene_id"] in allowed_scene_ids
                planned.append({
                    "candidate_id": f"CAND-{scene['scene_id']}-{row['binding_id']}",
                    "scene_id": scene["scene_id"], "chapter_id": scene.get("chapter_id"),
                    "binding_id": row["binding_id"], "source_id": row["source_id"], "source_kind": kind,
                    "candidate_use": SOURCE_CANDIDATE_USES.get(kind, "authorized_model_input_constraint"),
                    "status": "approved_model_candidate_input" if scene_allowed else "quarantined_formal_creation_gate", "model_input_eligible": scene_allowed, "prose_write_allowed": False,
                    "activation": {"creative_need": scene["creative_need"], "matched_stage": scene["stage"], "matched_project_terms": matched, "activation_reason": f"命中场景检索词：{'、'.join(matched)}", "activation_evidence": scene["activation_evidence"], "match_score": score},
                    "source_provenance": provenance,
                    "causal_contract": {"semantic_anchor": strategy["semantic_anchor"], "trigger": strategy["source_specific_trigger"], "required_action": strategy["observable_action"], "required_result": strategy["observable_result"], "required_cost_or_change": strategy["cost_or_change"]},
                })
    allowed_records = [row for row in planned if row["model_input_eligible"]]
    status = "ready_for_model_candidates" if allowed_records and not scene_gaps else "needs_creative_brief_refinement"
    if planned and not allowed_records:
        status = "formal_creation_blocked"
    return {"schema_version": "full-source-model-input-candidate-plan-1.0", "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "release_status": "draft_only", "formal_fact_status": brief.get("formal_fact_status"), "policy": "候选仅作为已授权模型输入约束；类型系统来源块可作为规则资料绑定，不得据此推断或确认项目类型；类型名称索引与类型连接保持隔离。正文消费、队列、批次和消费证据须在后续生成及审校验证完成后单独建立。", "formal_creation_allowed": bool(allowed_records), "scene_count": len(scenes), "queued_count": len(allowed_records), "source_kind_counts": dict(Counter(row["source_kind"] for row in allowed_records)), "isolated_counts": dict(excluded), "required_source_kind_gaps": scene_gaps, "status": status, "candidate_records": planned, "records": []}


def evaluate(project_root: str | Path, limit_per_kind: int = 2) -> dict[str, Any]:
    """Calculate activation candidates without changing the production surface."""
    root = Path(project_root).expanduser().resolve()
    policy = validate_policy(root)
    evidence = root / "文档" / "证据"
    bindings = _read(evidence / "全量资料解释词创作绑定.json", {})
    validate_bindings(policy, bindings)
    baseline_hash = hashlib.sha256(json.dumps(bindings, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    grants = authorized_bindings(root, bindings.get("records", []))
    brief = _read(root / BRIEF_FILE, {})
    full_gate = validate_formal_creation_gate(root)
    preliminary = build_plan(bindings, brief, grants, limit_per_kind, activation_version=baseline_hash)
    scene_gates = {}
    allowed_scene_ids: set[str] = set()
    for scene in brief.get("scenes", []):
        scene_id = scene.get("scene_id") if isinstance(scene, dict) else None
        if not scene_id:
            continue
        candidates = [row for row in preliminary["candidate_records"] if row["scene_id"] == scene_id]
        gate = validate_scene_formal_creation_gate(root, scene_id, candidates, grants)
        scene_gates[scene_id] = gate
        if gate["formal_creation_allowed"]:
            allowed_scene_ids.add(scene_id)
    plan = build_plan(bindings, brief, grants, limit_per_kind, allowed_scene_ids=allowed_scene_ids, activation_version=baseline_hash)
    plan["activation_version"] = baseline_hash
    plan["formal_creation_gate"] = full_gate
    plan["scene_formal_creation_gates"] = scene_gates
    return plan


def run(project_root: str | Path, limit_per_kind: int = 2) -> dict[str, Any]:
    """Evaluate candidates without creating prose-consumption projections."""
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    plan = evaluate(root, limit_per_kind)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True); parser.add_argument("--limit-per-kind", type=int, default=2)
    args = parser.parse_args(); plan = run(args.project_root, args.limit_per_kind)
    print(json.dumps({"status": plan["status"], "queued_count": plan["queued_count"], "source_kind_counts": plan["source_kind_counts"], "release_status": plan["release_status"]}, ensure_ascii=False)); return 0 if plan["status"] == "ready_for_model_candidates" else 2


if __name__ == "__main__":
    raise SystemExit(main())