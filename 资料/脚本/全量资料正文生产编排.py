"""Maintain the authorized source pool without prematurely binding it to prose.

Authorization makes source material retrievable for creative work. It does not
assign a chapter, character, scene, or prose task. A separate consumption record
must establish a concrete creative need, matching activation conditions, and a
target stage or scene before any material may enter a prose queue.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 全量资料输入与正文授权 import authorized_bindings


TYPE_SOURCE_KINDS = {"类型系统", "类型系统来源块", "类型连接"}


def _material_duty(row: dict[str, Any]) -> dict[str, Any]:
    binding = row.get("creation_binding", {})
    if not isinstance(binding, dict):
        binding = {}
    role = str(binding.get("material_role") or "").strip()
    stages = [str(item) for item in binding.get("applicable_stage", binding.get("stages", [])) if str(item).strip()]
    dimensions = [str(item) for item in binding.get("required_writing_dimensions", []) if str(item).strip()]
    if not role or not stages or not dimensions:
        return {
            "material_role": role or "unknown",
            "applicable_stage": stages,
            "required_writing_dimensions": dimensions,
            "deferred_reason": "旧绑定缺少职责合同字段，不能推导正文消费要求。",
            "prose_evidence_required": False,
        }
    return {
        "material_role": role,
        "applicable_stage": stages,
        "required_writing_dimensions": dimensions,
        "deferred_reason": str(binding.get("deferred_reason") or ""),
        "prose_evidence_required": False,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _text(value: Any) -> str:
    return str(value or "").replace("\n", " ").strip()


def build_plan(
    bindings: dict[str, Any],
    batch_size: int = 24,
    authorized_binding_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build an unbound, condition-aware creative-material pool.

    This planner deliberately has no prose dispatch path. It is a proof that
    authorization coverage is complete while no consumption evidence exists.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    records = bindings.get("records", []) if isinstance(bindings, dict) else []
    authorized_binding_ids = authorized_binding_ids or set()
    pending_activation: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []

    for row in records:
        if not isinstance(row, dict) or not row.get("binding_id") or not row.get("source_id"):
            continue
        binding_id = str(row["binding_id"])
        source_kind = _text(row.get("source_kind"))
        if binding_id not in authorized_binding_ids:
            quarantined.append({
                "binding_id": binding_id,
                "source_id": str(row["source_id"]),
                "source_kind": source_kind,
                "status": "quarantined_pending_prose_authorization",
            })
            continue

        creation_binding = row.get("creation_binding", {})
        creation_binding = creation_binding if isinstance(creation_binding, dict) else {}
        policy = creation_binding.get("activation_policy", {})
        policy = policy if isinstance(policy, dict) else {}
        is_type_material = source_kind in TYPE_SOURCE_KINDS
        pending_activation.append({
            "binding_id": binding_id,
            "source_id": str(row["source_id"]),
            "source_kind": source_kind,
            "status": (
                "prepared_unbound_type_material"
                if is_type_material
                else "authorized_pending_matched_creative_need"
            ),
            "activation_conditions": policy.get("conditions", []),
            "allowed_stages": creation_binding.get("stages", []),
            "material_duty": _material_duty(row),
            "binding_boundary": (
                "类型资料当前不绑定类型组合、章节、人物或场景；待后续创作选择时再建立可审计关联。"
                if is_type_material
                else "待具体创作需求、匹配阶段和场景证据齐备后再绑定。"
            ),
        })

    pending_by_kind = Counter(row["source_kind"] for row in pending_activation)
    unbound_type_count = sum(row["source_kind"] in TYPE_SOURCE_KINDS for row in pending_activation)
    return {
        "schema_version": "full-source-prose-production-plan-1.1",
        "generated_at": _now(),
        "policy": "逐条授权仅使资料可被检索和调度，不自动绑定章节、场景或正文。类型资料保持已准备未绑定；所有资料均须在具体创作需求、激活条件和阶段/场景证据齐备后才可进入正文候选队列。",
        "source_count": len(pending_activation) + len(quarantined),
        "authorized_source_count": len(pending_activation),
        "queued_count": 0,
        "pending_activation_count": len(pending_activation),
        "prepared_unbound_type_material_count": unbound_type_count,
        "quarantined_count": len(quarantined),
        "quarantined_records": quarantined,
        "realized_count": 0,
        "batch_size": batch_size,
        "batch_count": 0,
        "source_kind_counts": dict(pending_by_kind),
        "records": [],
        "pending_activation_records": pending_activation,
    }


def build_activation_work_batches(plan: dict[str, Any], batch_size: int) -> list[dict[str, Any]]:
    """Split the unbound pool into review/retrieval work batches, never prose jobs."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    pending = plan.get("pending_activation_records", [])
    if not isinstance(pending, list):
        raise ValueError("pending_activation_records must be a list")
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(pending), batch_size):
        members = pending[offset:offset + batch_size]
        batch_number = len(batches) + 1
        batches.append({
            "schema_version": "creative-material-activation-work-batch-1.0",
            "activation_batch_id": f"ACT-{batch_number:04d}",
            "batch_number": batch_number,
            "status": "ready_for_retrieval_and_matched_creative_need_review",
            "purpose": "按批支持后续检索、审核和具体创作需求匹配；不是正文生产任务。",
            "binding_boundary": "本批不绑定章节、场景、人物、类型组合或正文；不得据此生成正文。",
            "item_count": len(members),
            "binding_ids": [str(row["binding_id"]) for row in members],
            "source_kind_counts": dict(Counter(str(row.get("source_kind") or "未分类") for row in members)),
            "allowed_stages_union": sorted({str(stage) for row in members for stage in row.get("allowed_stages", [])}),
        })
    return batches


def run(project_root: str | Path, batch_size: int = 24) -> tuple[dict[str, Any], list[Path]]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    bindings = _read_json(evidence / "全量资料解释词创作绑定.json", {})
    records = bindings.get("records", []) if isinstance(bindings, dict) else []
    grants = authorized_bindings(root, records)
    plan = build_plan(bindings, batch_size, set(grants))
    output = evidence / "全量资料正文生产编排.json"
    queue = evidence / "全量资料正文生产队列.jsonl"
    batches = evidence / "全量资料正文生产批次.jsonl"
    activation_work_batches = evidence / "全量资料激活工作批次.jsonl"
    work_batches = build_activation_work_batches(plan, batch_size)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    queue.write_text("", encoding="utf-8")
    batches.write_text("", encoding="utf-8")
    activation_work_batches.write_text(
        "".join(json.dumps(batch, ensure_ascii=False) + "\n" for batch in work_batches),
        encoding="utf-8",
    )
    plan["activation_work_batch_count"] = len(work_batches)
    plan["activation_work_batch_item_count"] = sum(batch["item_count"] for batch in work_batches)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan, [output, queue, batches, activation_work_batches]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--batch-size", type=int, default=24)
    args = parser.parse_args()
    plan, _ = run(args.project_root, args.batch_size)
    print(json.dumps({
        "status": "passed",
        "queued_count": plan["queued_count"],
        "batch_count": plan["batch_count"],
        "pending_activation_count": plan["pending_activation_count"],
        "activation_work_batch_count": plan["activation_work_batch_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())