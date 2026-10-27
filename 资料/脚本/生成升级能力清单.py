"""Build a non-release inventory of material-upgrade capabilities and evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "material-upgrade-capability-inventory-1.0"
INCREMENT_PATH = Path("文档/证据/全量资料增量升级/20260817T061417Z-c75fb8a7")
MAPPINGS_PATH = Path("文档/证据/全量资料升级派生定位/已验证候选映射.jsonl")
MAPPING_REVISION_PATH = Path("文档/证据/全量资料升级派生定位/修订/V1/revalidated_mappings.jsonl")
EXPERIMENT_PATH = Path("文档/证据/隔离归档/experimental_nonrelease/模型辅助资料改进候选")
OUTPUT_ROOT = Path("文档/证据/升级能力清单")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} 必须为 JSON 对象")
        rows.append(value)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_mappings(root: Path) -> tuple[list[dict[str, Any]], str | None]:
    mappings = _read_jsonl(root / MAPPINGS_PATH)
    revision_path = root / MAPPING_REVISION_PATH
    if not revision_path.is_file():
        return mappings, None
    by_binding = {str(row["binding_id"]): row for row in mappings}
    for revision in _read_jsonl(revision_path):
        if revision.get("schema_version") != "derived-source-mapping-revision-1.0":
            raise ValueError(f"不支持的映射修订版本: {revision.get('schema_version')}")
        binding_id = str(revision.get("binding_id"))
        original = by_binding.get(binding_id)
        replacement = revision.get("replacement_mapping")
        if not original or not isinstance(replacement, dict):
            raise ValueError(f"映射修订缺少可替代的基础映射: {binding_id}")
        if revision.get("superseded_mapping_sha256") != _hash(original):
            raise ValueError(f"映射修订未绑定到当前基础映射: {binding_id}")
        if str(replacement.get("binding_id")) != binding_id:
            raise ValueError(f"映射修订 binding_id 不一致: {binding_id}")
        by_binding[binding_id] = replacement
    return list(by_binding.values()), str(MAPPING_REVISION_PATH).replace("\\", "/")


def _read_back_original_object(root: Path, mapping: dict[str, Any], source_cache: dict[Path, tuple[str, list[str]]]) -> tuple[dict[str, Any] | None, str | None]:
    """Reparse the exact mapped source range; a stored mapping snapshot is not readback evidence."""
    original = mapping.get("derived_original_object")
    if not isinstance(original, dict):
        return None, "missing_derived_original_object"
    source_file = root / str(original.get("file", ""))
    if not source_file.is_file():
        return None, "source_file_missing"
    if source_file not in source_cache:
        source_cache[source_file] = (_file_hash(source_file), source_file.read_text(encoding="utf-8-sig").splitlines())
    actual_file_hash, lines = source_cache[source_file]
    expected_file_hash = mapping.get("source_file_sha256")
    if expected_file_hash and actual_file_hash != expected_file_hash:
        return None, "source_file_sha256_mismatch"
    line_start, line_end = original.get("line_start"), original.get("line_end")
    if not isinstance(line_start, int) or not isinstance(line_end, int) or line_start < 1 or line_end < line_start:
        return None, "invalid_source_line_range"
    if line_end > len(lines):
        return None, "source_line_range_out_of_bounds"
    block = "\n".join(lines[line_start - 1:line_end]).strip()
    json_start, json_end = block.find("{"), block.rfind("}")
    if json_start < 0 or json_end < json_start:
        return None, "source_block_json_not_found"
    try:
        readback_object = json.loads(block[json_start:json_end + 1])
    except json.JSONDecodeError:
        return None, "source_block_json_invalid"
    expected_object = original.get("object")
    expected_object_hash = mapping.get("derived_original_object_sha256")
    if not isinstance(expected_object, dict) or not isinstance(expected_object_hash, str):
        return None, "mapped_object_or_hash_missing"
    if _hash(expected_object) != expected_object_hash:
        return None, "mapped_object_sha256_invalid"
    if _hash(readback_object) != expected_object_hash:
        return None, "readback_object_sha256_mismatch"
    return {
        "status": "verified_original_object",
        "file": str(original["file"]).replace("\\", "/"),
        "line_start": line_start,
        "line_end": line_end,
        "source_file_sha256": expected_file_hash,
        "original_object_sha256": expected_object_hash,
    }, None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_kind(mapping: dict[str, Any] | None, source_id: str) -> str:
    if mapping:
        original = mapping.get("derived_original_object", {})
        file_name = original.get("file", "") if isinstance(original, dict) else ""
        if "类型连接" in file_name:
            return "类型连接"
        if "类型系统" in file_name:
            return "类型系统"
        if "锚点" in file_name:
            return "锚点网络"
        if "动态" in file_name:
            return "动态网络"
        if "静态" in file_name:
            return "静态网络"
        if "资料库" in file_name:
            return "资料库"
    if source_id.startswith("TYPE-SOURCE:"):
        return "类型系统来源块"
    return "unclassified"


def _classification(source_kind: str) -> tuple[str, str]:
    table = {
        "资料库": ("content_definition", "library_view"),
        "类型系统": ("type_definition", "type_system_view"),
        "类型系统来源块": ("type_source_structure", "type_system_view"),
        "静态网络": ("relationship", "static_network_view"),
        "动态网络": ("dynamic_rule", "dynamic_rule_capabilities"),
        "锚点网络": ("anchor", "anchor_view"),
        "类型连接": ("type_connection_rule", "type_connection_view"),
    }
    return table.get(source_kind, ("unclassified_candidate", "relationship_graph"))


def _mapping_ref(mapping: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not mapping:
        return []
    original = mapping.get("derived_original_object", {})
    return [{
        "artifact": str(MAPPINGS_PATH).replace("\\", "/"),
        "mapping_status": mapping.get("mapping_status"),
        "file": original.get("file") if isinstance(original, dict) else None,
        "locator": (original.get("locator") or original.get("source_block")) if isinstance(original, dict) else None,
    }]


def _build_increment_row(change: dict[str, Any], mapping: dict[str, Any] | None, readback: dict[str, Any] | None, readback_failure: str | None) -> dict[str, Any]:
    source_id = str(change["source_id"])
    source_kind = _source_kind(mapping, source_id)
    capability_kind, target_module = _classification(source_kind)
    fingerprint = change.get("fingerprint", {})
    locator_valid = fingerprint.get("locator_valid") is True
    has_candidate_units = isinstance(mapping, dict) and bool(mapping.get("upgrade_units"))
    missing = ["original_object_readback", "upgrade_source_ref_and_sha256", "field_schema_validation", "dependency_and_conflict_validation"]
    if not locator_valid:
        missing.insert(0, "source_ref_resolution")
    if not has_candidate_units:
        missing.insert(0, "typed_upgrade_semantic_units")
    status = "pending_field_evidence" if locator_valid else "blocked_locator_repair"
    row = {
        "upgrade_id": f"INC-{change['binding_id']}",
        "upgrade_source_class": "incremental_change_detection",
        "binding_id": change["binding_id"],
        "capability_kind": capability_kind,
        "target_module": target_module,
        "source_kind": source_kind,
        "source_refs": [{"artifact": str(INCREMENT_PATH / "changes.jsonl").replace("\\", "/"), "category": change["category"], "source_id": source_id}] + _mapping_ref(mapping),
        "target_objects": [source_id],
        "baseline_hashes": {"source_object_sha256": fingerprint.get("source_object_sha256"), "source_ref_sha256": fingerprint.get("source_ref_sha256"), "dependency_sha256": fingerprint.get("dependency_sha256"), "mapped_original_object_sha256": mapping.get("derived_original_object_sha256") if mapping else None},
        "semantic_units": mapping.get("upgrade_units", []) if mapping else [],
        "cross_module_refs": [],
        "validation_status": status,
        "required_validation_gates": missing,
        "release_eligibility": "not_eligible",
        "release_reason": "哈希变化或定位映射只证明审计边界，不构成可融合的字段级升级证据。",
    }
    if readback:
        row["original_object_readback"] = readback
    if readback_failure:
        row["original_object_readback"] = {"status": "blocked", "reason": readback_failure}
        if "original_object_readback" not in row["required_validation_gates"]:
            row["required_validation_gates"].append("original_object_readback")
    return row


def _build_experiment_row(candidate: dict[str, Any]) -> dict[str, Any]:
    source_kind = str(candidate.get("source_kind", "unclassified"))
    capability_kind, target_module = _classification(source_kind)
    return {
        "upgrade_id": f"EXP-{candidate['candidate_id']}",
        "upgrade_source_class": "experimental_nonrelease",
        "binding_id": candidate.get("binding_id"),
        "capability_kind": capability_kind,
        "target_module": target_module,
        "source_kind": source_kind,
        "source_refs": [{"artifact": str(EXPERIMENT_PATH / "改进候选台账.jsonl").replace("\\", "/"), "candidate_id": candidate["candidate_id"], "source_ref": candidate.get("source_ref")}],
        "target_objects": [candidate.get("source_id")],
        "baseline_hashes": {"model_input_sha256": candidate.get("input_sha256")},
        "semantic_units": [],
        "cross_module_refs": [],
        "validation_status": "quarantined_summary_only_candidate",
        "required_validation_gates": ["original_object_readback", "original_object_sha256_match", "typed_upgrade_semantic_units", "candidate_schema_and_diagnosis_link"],
        "release_eligibility": "not_eligible",
        "release_reason": "实验候选未回读并锁定原始对象，受 experimental_nonrelease 声明永久隔离。",
    }


def build(project_root: str | Path, version: str = "V1") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    changes = _read_jsonl(root / INCREMENT_PATH / "changes.jsonl")
    mappings, mapping_revision = _load_mappings(root)
    mapping_by_binding = {str(row["binding_id"]): row for row in mappings}
    relevant = [row for row in changes if row.get("category") in {"modified", "locator_repair"}]
    readback_failures: list[dict[str, Any]] = []
    rows = []
    source_cache: dict[Path, tuple[str, list[str]]] = {}
    for change in relevant:
        mapping = mapping_by_binding.get(str(change["binding_id"]))
        readback, failure = _read_back_original_object(root, mapping, source_cache) if mapping else (None, "mapping_missing")
        if failure:
            readback_failures.append({"upgrade_id": f"INC-{change['binding_id']}", "binding_id": change["binding_id"], "source_id": change.get("source_id"), "reason": failure})
        rows.append(_build_increment_row(change, mapping, readback, failure))
    ledger_path = root / EXPERIMENT_PATH / "改进候选台账.jsonl"
    if ledger_path.exists():
        rows.extend(_build_experiment_row(row) for row in _read_jsonl(ledger_path))
    rows.sort(key=lambda row: row["upgrade_id"])
    output = root / OUTPUT_ROOT / version
    output.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output / "upgrade_capabilities.jsonl", rows)
    _write_jsonl(output / "readback_failures.jsonl", readback_failures)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["capability_kind"]] = counts.get(row["capability_kind"], 0) + 1
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "generated_at": _now(),
        "status": "blocked_pending_verified_upgrade_fields",
        "formal_release_allowed": False,
        "input": {"increment_manifest": str(INCREMENT_PATH / "manifest.json").replace("\\", "/"), "increment_change_count": len(relevant), "verified_mapping_count": len(mappings), "mapping_revision": mapping_revision, "experimental_candidate_count": len(rows) - len(relevant)},
        "capability_count": len(rows),
        "capability_kind_counts": counts,
        "release_eligible_count": 0,
        "capabilities_file": "upgrade_capabilities.jsonl",
        "original_object_readback": {"verified_count": len(relevant) - len(readback_failures), "failure_count": len(readback_failures), "failures_file": "readback_failures.jsonl"},
    }
    manifest["manifest_sha256"] = _hash(manifest)
    _write_json(output / "manifest.json", manifest)
    return {"output": str(output), "status": manifest["status"], "capability_count": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成升级资料能力清单")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--version", default="V1")
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.version), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())