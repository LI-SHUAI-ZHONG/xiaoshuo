"""Create append-only revalidated mapping replacements from an audit artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAPPINGS_PATH = Path("文档/证据/全量资料升级派生定位/已验证候选映射.jsonl")
AUDIT_PATH = Path("文档/证据/升级定位映射审计/V3/mapping_audit.jsonl")
OUTPUT_ROOT = Path("文档/证据/全量资料升级派生定位/修订")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build(project_root: str | Path, version: str = "V1") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    mappings = {str(row["binding_id"]): row for row in _read_jsonl(root / MAPPINGS_PATH)}
    audit_rows = _read_jsonl(root / AUDIT_PATH)
    records = []
    excluded = []
    for audit in audit_rows:
        binding_id = str(audit["binding_id"])
        eligible = (audit.get("actual_source_file_sha256") == audit.get("expected_source_file_sha256") and audit.get("calculated_mapped_object_sha256") == audit.get("readback_object_sha256"))
        if not eligible:
            excluded.append({"binding_id": binding_id, "source_id": audit.get("source_id"), "reason": "snapshot_and_readback_object_differ"})
            continue
        original = mappings[binding_id]
        replacement = json.loads(json.dumps(original, ensure_ascii=False))
        replacement["mapping_status"] = "revalidated_mapping_revision"
        replacement["derived_original_object_sha256"] = audit["readback_object_sha256"]
        records.append({"schema_version": "derived-source-mapping-revision-1.0", "binding_id": binding_id, "source_id": original.get("source_id"), "supersedes_artifact": str(MAPPINGS_PATH).replace("\\", "/"), "superseded_mapping_sha256": _hash(original), "audit_artifact": str(AUDIT_PATH).replace("\\", "/"), "audit_readback_object_sha256": audit["readback_object_sha256"], "replacement_mapping": replacement})
    output = root / OUTPUT_ROOT / version
    output.mkdir(parents=True, exist_ok=False)
    (output / "revalidated_mappings.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    (output / "excluded_mappings.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in excluded), encoding="utf-8")
    manifest = {"schema_version": "derived-source-mapping-revision-manifest-1.0", "version": version, "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "base_mapping_artifact": str(MAPPINGS_PATH).replace("\\", "/"), "audit_artifact": str(AUDIT_PATH).replace("\\", "/"), "revalidated_mapping_count": len(records), "excluded_mapping_count": len(excluded), "formal_release_allowed": False, "revalidated_mappings_file": "revalidated_mappings.jsonl", "excluded_mappings_file": "excluded_mappings.jsonl"}
    manifest["manifest_sha256"] = _hash(manifest)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output), "revalidated_mapping_count": len(records), "excluded_mapping_count": len(excluded)}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成升级定位映射修订")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--version", default="V1")
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.version), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())