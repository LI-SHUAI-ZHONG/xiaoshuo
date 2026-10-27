"""Diagnose upgrade-chain contract fields without retaining source content."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

RUN_ID = "20260816T061711Z-fb0cf077"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def _rows(path: Path) -> list[dict[str, Any]]:
    return [row for row in (json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()) if isinstance(row, dict)]


def _hash_paths(row: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("original_object_sha256", "derived_original_object_sha256"):
        if len(str(row.get(key) or "")) == 64:
            paths.append(key)
    original = row.get("original_object")
    if isinstance(original, dict) and len(str(original.get("derived_original_object_sha256") or "")) == 64:
        paths.append("original_object.derived_original_object_sha256")
    source_ref = row.get("source_ref")
    mapping = source_ref.get("derived_mapping") if isinstance(source_ref, dict) else None
    if isinstance(mapping, dict) and len(str(mapping.get("derived_original_object_sha256") or "")) == 64:
        paths.append("source_ref.derived_mapping.derived_original_object_sha256")
    return paths


def run(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    runs = root / "文档" / "证据" / "全量资料升级运行"
    chain: list[tuple[str, dict[str, Any]]] = []
    current, seen = RUN_ID, set()
    while current and current not in seen:
        seen.add(current)
        manifest = _read_json(runs / current / "manifest.json")
        chain.append((current, manifest))
        current = str(manifest.get("parent_run_id") or "")
    merged: dict[str, dict[str, Any]] = {}
    for run_id, _ in reversed(chain):
        for row in _rows(runs / run_id / "records.jsonl"):
            binding_id = str(row.get("binding_id") or "")
            if binding_id:
                merged[binding_id] = row
    missing = []
    for binding_id, row in merged.items():
        paths = _hash_paths(row)
        if not paths:
            missing.append({
                "binding_id": binding_id,
                "terminal_status": str(row.get("terminal_status") or row.get("status") or ""),
                "top_level_fields": sorted(row.keys()),
                "original_object_fields": sorted(row["original_object"].keys()) if isinstance(row.get("original_object"), dict) else [],
                "source_ref_fields": sorted(row["source_ref"].keys()) if isinstance(row.get("source_ref"), dict) else [],
            })
    manifests = []
    for run_id, manifest in reversed(chain):
        statuses = manifest.get("status_counts")
        manifests.append({
            "run_id": run_id,
            "parent_run_id": manifest.get("parent_run_id"),
            "baseline_binding_count": manifest.get("baseline_binding_count"),
            "processed_count": manifest.get("processed_count"),
            "records_mode": manifest.get("records_mode"),
            "status_counts": statuses,
            "status_count_total": sum(value for value in statuses.values() if isinstance(value, int)) if isinstance(statuses, dict) else None,
        })
    return {"schema_version": "full-source-material-upgrade-diagnostic-1.0", "run_id": RUN_ID,
            "scope": "metadata_only_no_source_content", "chain": manifests,
            "merged_binding_count": len(merged), "missing_object_hash_count": len(missing),
            "missing_object_hash_samples": missing, "terminal_statuses": dict(Counter(str(row.get("terminal_status") or row.get("status") or "") for row in merged.values()))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.project_root)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"merged_binding_count": report["merged_binding_count"], "missing_object_hash_count": report["missing_object_hash_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())