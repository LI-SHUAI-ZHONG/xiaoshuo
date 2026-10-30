"""Audit source-material activation prerequisites without changing creative artifacts.

This distinguishes an unqualified source from a qualified but dormant material
object. It deliberately never admits a record for formal facts or prose.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "material-activation-prerequisite-audit-1.0"
SOURCE_BLOCK_RE = re.compile(
    r"^SOURCE:\s*(?P<name>[^\r\n]+)\r?\n=+\r?\n(?P<body>.*?)(?=\r?\nSOURCE:|\Z)",
    re.MULTILINE | re.DOTALL,
)
INDEXED_REF_RE = re.compile(r":(?P<collection>[^:\[]+)\[(?P<index>\d+)\]$")


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


def _source_objects(path: Path) -> dict[str, list[Any]]:
    """Read bounded JSON arrays from the assembled type-connection material."""
    objects: dict[str, list[Any]] = {}
    text = path.read_text(encoding="utf-8-sig")
    for match in SOURCE_BLOCK_RE.finditer(text):
        try:
            value = json.loads(match.group("body").strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            objects[match.group("name").strip()] = value
    return objects


def _values(value: Any, key_names: set[str], output: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in key_names and child not in (None, "", [], {}):
                if isinstance(child, list):
                    output.extend(str(item) for item in child if str(item).strip())
                else:
                    output.append(str(child))
            _values(child, key_names, output)
    elif isinstance(value, list):
        for child in value:
            _values(child, key_names, output)


def _bounded_object(row: dict[str, Any], objects: dict[str, list[Any]]) -> tuple[Any | None, str | None]:
    match = INDEXED_REF_RE.search(str(row.get("source_ref", "")))
    if not match:
        return None, "来源定位不是可索引的有界 JSON 对象"
    collection = match.group("collection")
    index = int(match.group("index")) - 1
    entries = objects.get(collection)
    if entries is None:
        return None, f"未找到来源块 {collection}"
    if index < 0 or index >= len(entries):
        return None, f"来源块 {collection} 不含索引 {index + 1}"
    return entries[index], None


def _semantic_prerequisites(source_object: Any) -> list[dict[str, str]]:
    if not isinstance(source_object, dict):
        return []
    conditions: list[str] = []
    _values(source_object, {"condition", "conditions", "trigger_condition_ids", "selection_constraints"}, conditions)
    prerequisites = []
    for condition in dict.fromkeys(item.strip() for item in conditions if item.strip()):
        prerequisites.append({"kind": "material_semantic_condition", "requirement": condition})
    for field, label in (
        ("primary_type_id", "主类型已选择"),
        ("component_type_ids", "组成类型已选择并匹配"),
        ("mechanism_ids", "机制对象已选择并匹配"),
        ("structure_ids", "结构对象已选择并匹配"),
    ):
        if source_object.get(field):
            prerequisites.append({"kind": "material_context_match", "requirement": label})
    return prerequisites


def _source_gate(row: dict[str, Any]) -> dict[str, str]:
    category = row.get("category_id")
    if category == "candidate_identity_missing":
        return {"kind": "source_qualification", "requirement": "独立替代来源、稳定对象标识、范围与权利/审批证据通过严格重审"}
    if category == "pending_requires_project_confirmation":
        return {"kind": "source_qualification", "requirement": "项目级明确确认或独立替代来源；不得以 pending 状态自动采用"}
    return {"kind": "source_qualification", "requirement": "提供单一边界、稳定定位且可核验的替代来源对象"}


def _status(row: dict[str, Any], prerequisites: list[dict[str, str]], resolution_error: str | None) -> tuple[str, str, str, str]:
    """Keep source qualification separate from selection and semantic readiness."""
    category = str(row.get("category_id", ""))
    if category in {"locator_invalid_or_out_of_range", "object_boundary_missing"} or resolution_error:
        return "replacement_required", "unavailable", "unavailable", "external_replacement_required"
    if category == "candidate_identity_missing":
        return "boundary_rereview_required", "unavailable", "conditions_declared" if len(prerequisites) > 1 else "unavailable", "boundary_source_rereview"
    if category in {"candidate_requires_project_confirmation", "pending_requires_project_confirmation"}:
        return "project_confirmation_required", "pending", "conditions_declared" if len(prerequisites) > 1 else "unavailable", "project_selection_pending"
    return "quarantined", "unavailable", "conditions_declared" if len(prerequisites) > 1 else "unavailable", "boundary_source_rereview"


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    strict = root / "文档" / "证据" / "严格资料升级"
    input_path = strict / "严格隔离分类" / "严格隔离分类清单.jsonl"
    rows = _read_jsonl(input_path)
    objects = _source_objects(root / "原始资料" / "类型连接.txt")
    results = []
    for row in rows:
        source_object, resolution_error = _bounded_object(row, objects) if row.get("source_kind") == "类型连接" else (None, "该资料不是可重建的类型连接对象")
        prerequisites = [_source_gate(row)]
        prerequisites.extend(_semantic_prerequisites(source_object))
        source_status, selection_status, semantic_status, classification = _status(row, prerequisites, resolution_error)
        results.append({
            "schema_version": SCHEMA_VERSION,
            "upgrade_id": row.get("upgrade_id"),
            "consumption_id": row.get("consumption_id"),
            "binding_id": row.get("binding_id"),
            "source_kind": row.get("source_kind"),
            "source_id": row.get("source_id"),
            "source_ref": row.get("source_ref"),
            "prior_quarantine_category": row.get("category_id"),
            "activation_interpretation": "已提取语义前置条件，但来源资格门尚未通过；不得将其解释为资料可用或正文许可。" if semantic_status == "conditions_declared" else "无法从现有资料建立可审计的语义激活条件，须先替代或确认来源对象。",
            "source_qualification_status": source_status,
            "project_selection_status": selection_status,
            "semantic_activation_status": semantic_status,
            "recommended_classification": classification,
            "activation_prerequisites": prerequisites,
            "object_resolution_error": resolution_error,
            "formal_fact_eligible": False,
            "model_input_eligible": False,
            "prose_write_allowed": False,
        })
    counts = Counter(item["semantic_activation_status"] for item in results)
    classifications = Counter(item["recommended_classification"] for item in results)
    category_counts = Counter(item["prior_quarantine_category"] for item in results)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "source_material_activation_prerequisites_only; no_project_or_prose_artifact_modified",
        "input": str(input_path.relative_to(root)).replace("\\", "/"),
        "audited_quarantine_count": len(results),
        "semantic_activation_status_counts": dict(sorted(counts.items())),
        "recommended_classification_counts": dict(sorted(classifications.items())),
        "prior_quarantine_category_counts": dict(sorted(category_counts.items())),
        "policy": "来源资格门、项目选择门与语义激活门必须同时满足；已声明语义条件不等同于资料可用，更不提升任何来源或使用资格。",
        "formal_fact_eligible_count": 0,
        "model_input_eligible_count": 0,
        "prose_write_allowed": False,
        "project_artifacts_modified": False,
    }
    output = strict / "资料激活前置条件审计"
    staging = strict / ".资料激活前置条件审计_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "资料激活前置条件审计报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "资料激活前置条件清单.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in results), encoding="utf-8")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())