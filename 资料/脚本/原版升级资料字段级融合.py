"""Build a hash-locked, non-destructive field-fusion preview.

Locator mappings establish the original object boundary only. They do not
contain a candidate field value, so this tool records them as pending evidence
instead of inventing a material change.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "original-upgrade-material-field-fusion-1.0"
SEMANTIC_UNIT_KINDS = {
    "scalar", "set_member", "relation", "condition", "effect", "constraint",
    "exception", "guarantee_boundary", "structure",
}
MAPPINGS_PATH = Path("文档") / "证据" / "全量资料升级派生定位" / "已验证候选映射.jsonl"
OUTPUT_ROOT = Path("文档") / "证据" / "资料融合版本"
LIBRARY_BASELINE_PATH = Path("文档") / "证据" / "全量资料治理" / "资料库_规范化.json"
DEPENDENCY_REPAIR_LOG_PATH = Path("文档") / "证据" / "资料库语义依赖修复日志-二版.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} 必须为 JSON 对象")
        records.append(value)
    return records


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_object_id(mapping: dict[str, Any]) -> str:
    original = mapping.get("derived_original_object")
    if not isinstance(original, dict):
        raise ValueError(f"{mapping.get('binding_id')} 缺少 derived_original_object")
    file_name = original.get("file")
    if not isinstance(file_name, str) or not file_name:
        raise ValueError(f"{mapping.get('binding_id')} 缺少原始文件定位")
    locator = original.get("locator") or original.get("source_block")
    if not isinstance(locator, str) or not locator:
        raise ValueError(f"{mapping.get('binding_id')} 缺少对象 locator/source_block")
    return f"{file_name}#{locator}"


def _validate_semantic_unit(unit: dict[str, Any]) -> None:
    required = {"unit_id", "unit_kind", "field_path", "semantic_key", "candidate_value", "source_refs", "derivation_rule"}
    missing = sorted(required - set(unit))
    if missing:
        raise ValueError(f"语义单元缺少字段: {','.join(missing)}")
    if unit["unit_kind"] not in SEMANTIC_UNIT_KINDS:
        raise ValueError(f"不支持的语义单元类型: {unit['unit_kind']}")
    if not isinstance(unit["source_refs"], list) or not unit["source_refs"]:
        raise ValueError(f"语义单元缺少 source_refs: {unit['unit_id']}")
    if not isinstance(unit["derivation_rule"], str) or not unit["derivation_rule"].strip():
        raise ValueError(f"语义单元缺少 derivation_rule: {unit['unit_id']}")


def _semantic_unit_change(mapping: dict[str, Any], unit: dict[str, Any], object_id: str, baseline: dict[str, Any]) -> dict[str, Any]:
    _validate_semantic_unit(unit)
    field_path = str(unit["field_path"])
    old_value = unit.get("baseline_value", baseline.get(field_path))
    action = unit.get("action")
    if action not in {"correct", "complete", "extend", "restructure", "conflict", "retain"}:
        raise ValueError(f"语义单元动作非法: {unit['unit_id']}")
    return {
        "change_id": f"FUSION-{mapping.get('binding_id')}-{unit['unit_id']}",
        "target_object_id": object_id,
        "binding_id": mapping.get("binding_id"),
        "source_id": mapping.get("source_id"),
        "field_path": field_path,
        "unit_id": unit["unit_id"],
        "unit_kind": unit["unit_kind"],
        "semantic_key": unit["semantic_key"],
        "baseline_value": old_value,
        "candidate_value": unit["candidate_value"],
        "action": action,
        "status": "validated_candidate" if action != "conflict" else "unresolved_conflict",
        "evidence": {"source_refs": unit["source_refs"], "derivation_rule": unit["derivation_rule"]},
    }


def _dependency_graph(entries: list[dict[str, Any]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for entry in entries:
        entry_id = entry.get("entry_id")
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError("资料库基线存在缺少 entry_id 的对象")
        dependencies = entry.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"{entry_id} dependencies 必须为数组")
        graph[entry_id] = {
            dependency["entry_id"]
            for dependency in dependencies
            if isinstance(dependency, dict) and isinstance(dependency.get("entry_id"), str)
        }
    return graph


def _dependency_relation_keys(entries: list[dict[str, Any]]) -> dict[str, set[tuple[str, str]]]:
    """Index dependencies by target and relationship type.

    The target entry alone is sufficient for cycle detection, but not for
    semantic deduplication: one entry may relate to the same target through
    multiple independently meaningful dependency types.
    """
    keys: dict[str, set[tuple[str, str]]] = {}
    for entry in entries:
        entry_id = entry["entry_id"]
        dependencies = entry.get("dependencies", [])
        keys[entry_id] = {
            (dependency["entry_id"], dependency["type"])
            for dependency in dependencies
            if isinstance(dependency, dict)
            and isinstance(dependency.get("entry_id"), str)
            and isinstance(dependency.get("type"), str)
        }
    return keys


def _has_path(graph: dict[str, set[str]], start: str, target: str) -> bool:
    pending = [start]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(graph.get(current, set()) - visited)
    return False


def _same_source_candidate(
    entry: dict[str, Any], dependency: dict[str, Any], log: dict[str, Any], line_number: int,
    baseline_file_hash: str, raw_source_hash: str | None,
) -> dict[str, Any]:
    entry_id = entry["entry_id"]
    dependency_id = dependency["entry_id"]
    dependency_type = dependency["type"]
    source_ref = entry.get("source_ref")
    if not isinstance(source_ref, dict):
        raise ValueError(f"{entry_id} 缺少结构化 source_ref")
    refs = [
        {"artifact": "资料库_规范化", "file": str(LIBRARY_BASELINE_PATH).replace("\\", "/"), "entry_id": entry_id, "sha256": _canonical_hash(entry)},
        {"artifact": "资料库语义依赖修复日志-二版", "file": str(DEPENDENCY_REPAIR_LOG_PATH).replace("\\", "/"), "line": line_number, "sha256": _canonical_hash(log)},
        {"artifact": "原始资料", **source_ref},
    ]
    if raw_source_hash:
        refs[-1]["sha256"] = raw_source_hash
    return {
        "overlay_id": f"OVERLAY-DEP-{_canonical_hash([entry_id, dependency_id, dependency_type])[:16]}",
        "source_class": "same_source_derived_improvement",
        "target_object_id": entry_id,
        "baseline_object_sha256": _canonical_hash(entry),
        "baseline_file_sha256": baseline_file_hash,
        "unit_id": f"DEP-{_canonical_hash([entry_id, dependency_id, dependency_type])[:16]}",
        "unit_kind": "relation",
        "field_path": "dependencies",
        "semantic_key": f"{entry_id}|{dependency_id}|{dependency_type}",
        "candidate_value": {"entry_id": dependency_id, "type": dependency_type},
        "derivation_rule": log["reason"],
        "analysis_dimension": log.get("analysis_dimension"),
        "classification": log.get("classification"),
        "source_refs": refs,
    }


def build_same_source_overlay(project_root: str | Path, version: str = "V3") -> dict[str, Any]:
    """Build an append-only dependency overlay and a resolved read-only material view."""
    root = Path(project_root).expanduser().resolve()
    baseline_path = root / LIBRARY_BASELINE_PATH
    log_path = root / DEPENDENCY_REPAIR_LOG_PATH
    if not baseline_path.is_file() or not log_path.is_file():
        raise ValueError("缺少资料库基线或语义依赖修复日志")
    output = root / OUTPUT_ROOT / version
    if output.exists():
        raise ValueError(f"融合版本目录已存在，禁止覆盖: {output}")
    baseline = _read_json(baseline_path)
    if not isinstance(baseline, list) or not all(isinstance(row, dict) for row in baseline):
        raise ValueError("资料库基线必须为对象数组")
    entries = {row.get("entry_id"): row for row in baseline if isinstance(row.get("entry_id"), str)}
    if len(entries) != len(baseline):
        raise ValueError("资料库基线 entry_id 缺失或重复")
    graph = _dependency_graph(baseline)
    relation_keys = _dependency_relation_keys(baseline)
    baseline_file_hash = _file_hash(baseline_path)
    raw_hashes: dict[str, str | None] = {}
    overlays: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seen_keys: dict[str, dict[str, Any]] = {}
    for line_number, log in enumerate(_read_jsonl(log_path), 1):
        entry_id = log.get("entry_id")
        dependencies = log.get("dependencies")
        if not isinstance(entry_id, str) or entry_id not in entries or not isinstance(dependencies, list) or not isinstance(log.get("reason"), str):
            conflicts.append({"line": line_number, "status": "unresolved_conflict", "reason": "日志 schema 无法映射到资料库基线", "candidate": log})
            continue
        entry = entries[entry_id]
        source_file = entry["source_ref"].get("file") if isinstance(entry.get("source_ref"), dict) else None
        if source_file not in raw_hashes:
            raw_path = root / source_file if isinstance(source_file, str) else None
            raw_hashes[source_file] = _file_hash(raw_path) if raw_path and raw_path.is_file() else None
        for dependency in dependencies:
            if not isinstance(dependency, dict) or not isinstance(dependency.get("entry_id"), str) or not isinstance(dependency.get("type"), str):
                conflicts.append({"line": line_number, "target_object_id": entry_id, "status": "unresolved_conflict", "reason": "依赖对象缺少 entry_id 或 type", "candidate": dependency})
                continue
            dependency_id = dependency["entry_id"]
            if dependency_id not in entries:
                conflicts.append({"line": line_number, "target_object_id": entry_id, "status": "unresolved_conflict", "reason": "依赖目标不存在于基线", "candidate": dependency})
                continue
            if dependency_id == entry_id:
                conflicts.append({"line": line_number, "target_object_id": entry_id, "status": "unresolved_conflict", "reason": "禁止自依赖", "candidate": dependency})
                continue
            candidate = _same_source_candidate(entry, dependency, log, line_number, baseline_file_hash, raw_hashes[source_file])
            key = candidate["semantic_key"]
            previous = seen_keys.get(key)
            if previous:
                if previous["derivation_rule"] != candidate["derivation_rule"]:
                    conflicts.append({"line": line_number, "target_object_id": entry_id, "status": "unresolved_conflict", "reason": "同一语义键存在不同推导规则", "candidate": candidate})
                continue
            relation_key = (dependency_id, dependency["type"])
            resolution = "already_present_in_baseline" if relation_key in relation_keys[entry_id] else "applied_to_resolved_view"
            if resolution == "already_present_in_baseline":
                seen_keys[key] = candidate
                candidate["status"] = "validated_overlay"
                candidate["resolution"] = resolution
                overlays.append(candidate)
                changes.append({**candidate, "change_id": candidate["overlay_id"], "action": "retain", "baseline_value": entry.get("dependencies", [])})
                continue
            if _has_path(graph, dependency_id, entry_id):
                conflicts.append({"line": line_number, "target_object_id": entry_id, "status": "unresolved_conflict", "reason": "依赖关系会形成循环", "candidate": candidate})
                continue
            seen_keys[key] = candidate
            graph[entry_id].add(dependency_id)
            relation_keys[entry_id].add(relation_key)
            candidate["status"] = "validated_overlay"
            candidate["resolution"] = resolution
            overlays.append(candidate)
            changes.append({**candidate, "change_id": candidate["overlay_id"], "action": "extend", "baseline_value": entry.get("dependencies", [])})
    resolved = copy.deepcopy(baseline)
    for overlay in overlays:
        if overlay["resolution"] != "applied_to_resolved_view":
            continue
        entry = next(row for row in resolved if row["entry_id"] == overlay["target_object_id"])
        entry.setdefault("dependencies", []).append(overlay["candidate_value"])
    output.mkdir(parents=True)
    view_dir = output / "resolved_material_view"
    view_dir.mkdir()
    _write_json(view_dir / "资料库_规范化.json", resolved)
    _write_json(view_dir / "manifest.json", {
        "version": version,
        "baseline_file": str(LIBRARY_BASELINE_PATH).replace("\\", "/"),
        "baseline_file_sha256": baseline_file_hash,
        "overlay_file": "../validated_overlay.jsonl",
        "overlay_sha256": _canonical_hash(overlays),
        "consumption_contract": "必须显式绑定该 resolved_material_view 版本；不得回写原版。",
    })
    _write_jsonl(output / "validated_overlay.jsonl", overlays)
    _write_jsonl(output / "field_changes.jsonl", changes)
    _write_jsonl(output / "pending_evidence.jsonl", [])
    _write_jsonl(output / "unresolved_conflicts.jsonl", conflicts)
    preview = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "status": "validated_overlay" if not conflicts else "validated_overlay_with_unresolved_conflicts",
        "source_class": "same_source_derived_improvement",
        "material_fused_change_count": 0,
        "validated_overlay_count": len(overlays),
        "resolved_view_applied_count": sum(row["resolution"] == "applied_to_resolved_view" for row in overlays),
        "already_present_count": sum(row["resolution"] == "already_present_in_baseline" for row in overlays),
        "pending_evidence_count": 0,
        "conflict_count": len(conflicts),
    }
    _write_json(output / "merge_preview.json", preview)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "generated_at": _now(),
        "baseline": str(LIBRARY_BASELINE_PATH).replace("\\", "/"),
        "baseline_sha256": baseline_file_hash,
        "upgrade_input": str(DEPENDENCY_REPAIR_LOG_PATH).replace("\\", "/"),
        "upgrade_input_sha256": _file_hash(log_path),
        "source_class": "same_source_derived_improvement",
        "status": preview["status"],
        "formal_fact_eligible": False,
        "formal_release_allowed": False,
        "material_fused": {"change_count": 0, "file": "field_changes.jsonl"},
        "validated_overlay": {"count": len(overlays), "file": "validated_overlay.jsonl"},
        "resolved_material_view": {"path": "resolved_material_view", "file": "资料库_规范化.json"},
        "pending_evidence": {"count": 0, "file": "pending_evidence.jsonl"},
        "unresolved_conflicts": {"count": len(conflicts), "file": "unresolved_conflicts.jsonl"},
        "merge_preview": "merge_preview.json",
    }
    manifest["manifest_sha256"] = _canonical_hash(manifest)
    _write_json(output / "manifest.json", manifest)
    return {"output": str(output), "status": manifest["status"], "validated_overlay_count": len(overlays), "conflict_count": len(conflicts)}


def build(project_root: str | Path, version: str = "V2") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    mappings_path = root / MAPPINGS_PATH
    if not mappings_path.is_file():
        raise ValueError(f"缺少已验证候选映射: {mappings_path}")
    output = root / OUTPUT_ROOT / version
    if output.exists():
        raise ValueError(f"融合版本目录已存在，禁止覆盖: {output}")

    mappings = _read_jsonl(mappings_path)
    if not mappings:
        raise ValueError("已验证候选映射为空，无法建立融合预览")
    pending: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for mapping in mappings:
        if mapping.get("mapping_status") != "verified_candidate":
            continue
        binding_id = mapping.get("binding_id")
        object_id = _canonical_object_id(mapping)
        original = mapping["derived_original_object"]
        source_file = root / str(original["file"])
        if not source_file.is_file():
            raise ValueError(f"{binding_id} 原始文件不存在: {source_file}")
        actual_file_hash = _file_hash(source_file)
        if actual_file_hash != mapping.get("source_file_sha256"):
            raise ValueError(f"{binding_id} 原始文件哈希漂移")
        if _canonical_hash(original) != mapping.get("derived_original_object_sha256"):
            raise ValueError(f"{binding_id} 原始对象哈希漂移")
        record_id = f"FUSION-PENDING-{binding_id}"
        if record_id in seen_ids:
            raise ValueError(f"重复 binding_id: {binding_id}")
        seen_ids.add(record_id)
        units = mapping.get("upgrade_units", [])
        if units:
            if not isinstance(units, list):
                raise ValueError(f"{binding_id} upgrade_units 必须为数组")
            for unit in units:
                change = _semantic_unit_change(mapping, unit, object_id, original)
                (conflicts if change["action"] == "conflict" else changes).append(change)
            continue
        pending.append({
            "change_id": record_id,
            "target_object_id": object_id,
            "binding_id": binding_id,
            "source_id": mapping.get("source_id"),
            "field_path": None,
            "baseline_value": None,
            "candidate_value": None,
            "action": "pending_evidence",
            "status": "excluded_from_material_fused",
            "reason": "映射证明原始对象边界和哈希，但未提供可验证的升级字段值、字段来源或派生规则。",
            "evidence": {
                "source_file": original["file"],
                "locator": original.get("locator") or original.get("source_block"),
                "source_file_sha256": actual_file_hash,
                "baseline_object_sha256": mapping["derived_original_object_sha256"],
                "verification": mapping.get("verification"),
            },
        })
    if not pending and not changes and not conflicts:
        raise ValueError("没有 verified_candidate 映射可进入融合预览")

    output.mkdir(parents=True)
    _write_jsonl(output / "field_changes.jsonl", changes)
    _write_jsonl(output / "unresolved_conflicts.jsonl", conflicts)
    _write_jsonl(output / "pending_evidence.jsonl", pending)
    preview = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "status": "blocked_pending_field_evidence" if not changes else "validated_semantic_preview",
        "material_fused_change_count": len(changes),
        "pending_evidence_count": len(pending),
        "conflict_count": len(conflicts),
        "reason": "候选必须按语义单元提供；未提供候选的映射仍保持待证据。",
    }
    _write_json(output / "merge_preview.json", preview)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "generated_at": _now(),
        "baseline": "original_material",
        "upgrade_input": str(MAPPINGS_PATH).replace("\\", "/"),
        "input_mapping_sha256": _file_hash(mappings_path),
        "status": preview["status"],
        "formal_fact_eligible": False,
        "formal_release_allowed": False,
        "material_fused": {"change_count": len(changes), "file": "field_changes.jsonl"},
        "pending_evidence": {"count": len(pending), "file": "pending_evidence.jsonl"},
        "unresolved_conflicts": {"count": len(conflicts), "file": "unresolved_conflicts.jsonl"},
        "merge_preview": "merge_preview.json",
    }
    manifest["manifest_sha256"] = _canonical_hash(manifest)
    _write_json(output / "manifest.json", manifest)
    return {"output": str(output), "status": manifest["status"], "pending_evidence_count": len(pending)}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成原版与升级资料的字段级融合预览")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--version", default="V2")
    parser.add_argument("--mode", choices=("external_mapping", "same_source_derived"), default="external_mapping")
    args = parser.parse_args()
    runner = build_same_source_overlay if args.mode == "same_source_derived" else build
    print(json.dumps(runner(args.project_root, args.version), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())