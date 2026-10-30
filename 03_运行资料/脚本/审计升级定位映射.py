"""Audit derived source mappings without changing the immutable mapping evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAPPINGS_PATH = Path("文档/证据/全量资料升级派生定位/已验证候选映射.jsonl")
INCREMENT_PATH = Path("文档/证据/全量资料增量升级/20260817T061417Z-c75fb8a7")
OUTPUT_ROOT = Path("文档/证据/升级定位映射审计")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} 必须为 JSON 对象")
        rows.append(value)
    return rows


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_source_range(root: Path, original: dict[str, Any], cache: dict[Path, tuple[str, list[str]]]) -> tuple[str | None, str | None, str | None]:
    source_file = root / str(original.get("file", ""))
    if not source_file.is_file():
        return None, None, "source_file_missing"
    if source_file not in cache:
        cache[source_file] = (_file_hash(source_file), source_file.read_text(encoding="utf-8-sig").splitlines())
    file_hash, lines = cache[source_file]
    line_start, line_end = original.get("line_start"), original.get("line_end")
    if not isinstance(line_start, int) or not isinstance(line_end, int) or line_start < 1 or line_end < line_start:
        return file_hash, None, "invalid_source_line_range"
    if line_end > len(lines):
        return file_hash, None, "source_line_range_out_of_bounds"
    block = "\n".join(lines[line_start - 1:line_end]).strip()
    start, end = block.find("{"), block.rfind("}")
    if start < 0 or end < start:
        return file_hash, None, "source_block_json_not_found"
    try:
        value = json.loads(block[start:end + 1])
    except json.JSONDecodeError:
        return file_hash, None, "source_block_json_invalid"
    if not isinstance(value, dict):
        return file_hash, None, "source_block_json_not_object"
    return file_hash, _hash(value), None


def _audit_mapping(root: Path, mapping: dict[str, Any], change: dict[str, Any] | None, cache: dict[Path, tuple[str, list[str]]]) -> dict[str, Any]:
    original = mapping.get("derived_original_object")
    if not isinstance(original, dict):
        return {"binding_id": mapping.get("binding_id"), "source_id": mapping.get("source_id"), "status": "blocked", "reason": "missing_derived_original_object"}
    actual_file_hash, actual_source_hash, parse_failure = _read_source_range(root, original, cache)
    mapped_object = original.get("object")
    mapped_hash = mapping.get("derived_original_object_sha256")
    calculated_mapped_hash = _hash(mapped_object) if isinstance(mapped_object, dict) else None
    reasons = []
    if mapping.get("source_file_sha256") != actual_file_hash:
        reasons.append("source_file_sha256_mismatch")
    if calculated_mapped_hash != mapped_hash:
        reasons.append("mapped_object_sha256_invalid")
    if parse_failure:
        reasons.append(parse_failure)
    if actual_source_hash and mapped_hash != actual_source_hash:
        reasons.append("source_object_sha256_mismatch")
    return {
        "binding_id": mapping.get("binding_id"),
        "source_id": mapping.get("source_id"),
        "change_category": change.get("category") if change else None,
        "source_file": original.get("file"),
        "line_start": original.get("line_start"),
        "line_end": original.get("line_end"),
        "expected_source_file_sha256": mapping.get("source_file_sha256"),
        "actual_source_file_sha256": actual_file_hash,
        "mapped_object_sha256": mapped_hash,
        "calculated_mapped_object_sha256": calculated_mapped_hash,
        "readback_object_sha256": actual_source_hash,
        "status": "audited_clean" if not reasons else "blocked",
        "reasons": sorted(set(reasons)),
    }


def build(project_root: str | Path, version: str = "V1") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    mappings = _read_jsonl(root / MAPPINGS_PATH)
    changes = [row for row in _read_jsonl(root / INCREMENT_PATH / "changes.jsonl") if row.get("category") in {"modified", "locator_repair"}]
    mapping_by_binding = {str(row.get("binding_id")): row for row in mappings}
    change_by_binding = {str(row.get("binding_id")): row for row in changes}
    source_cache: dict[Path, tuple[str, list[str]]] = {}
    rows = [_audit_mapping(root, mapping, change_by_binding.get(str(mapping.get("binding_id"))), source_cache) for mapping in mappings]
    missing = [{"binding_id": row.get("binding_id"), "source_id": row.get("source_id"), "category": row.get("category"), "status": "blocked", "reason": "mapping_missing"} for row in changes if str(row.get("binding_id")) not in mapping_by_binding]
    output = root / OUTPUT_ROOT / version
    output.mkdir(parents=True, exist_ok=False)
    (output / "mapping_audit.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (output / "mapping_missing.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in missing), encoding="utf-8")
    counts: dict[str, int] = {}
    for row in rows + missing:
        key = "clean" if row.get("status") == "audited_clean" else (row.get("reason") or ";".join(row.get("reasons", [])) or "blocked")
        counts[key] = counts.get(key, 0) + 1
    manifest = {
        "schema_version": "derived-source-mapping-audit-1.0",
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mapping_input": str(MAPPINGS_PATH).replace("\\", "/"),
        "increment_input": str(INCREMENT_PATH / "changes.jsonl").replace("\\", "/"),
        "mapping_count": len(rows),
        "change_count": len(changes),
        "missing_mapping_count": len(missing),
        "audited_clean_count": sum(row.get("status") == "audited_clean" for row in rows),
        "blocked_mapping_count": sum(row.get("status") != "audited_clean" for row in rows),
        "reason_counts": counts,
        "formal_release_allowed": False,
        "mapping_audit_file": "mapping_audit.jsonl",
        "mapping_missing_file": "mapping_missing.jsonl",
    }
    manifest["manifest_sha256"] = _hash(manifest)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output), "mapping_count": len(rows), "missing_mapping_count": len(missing), "blocked_mapping_count": manifest["blocked_mapping_count"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="审计升级定位映射")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--version", default="V1")
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.version), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())