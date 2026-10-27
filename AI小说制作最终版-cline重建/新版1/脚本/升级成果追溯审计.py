"""Trace historical upgrade artifacts and distinguish material revisions from runtime evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = "material-upgrade-artifact-trace-audit-1.0"
DEFAULT_INPUTS = (Path("文档/证据"), Path("文档/归档"))
MATERIAL_FIELDS = ("upgraded_content", "improved_content", "candidate_value", "upgrade_units", "semantic_units", "proposed_changes", "changes")
UPGRADE_NAME_MARKERS = ("升级", "候选", "审校", "改进", "合同")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _nonempty(value: Any) -> bool:
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def _read_records(path: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".jsonl":
            for line_number, line in enumerate(text.splitlines(), 1):
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, dict):
                        yield f"line:{line_number}", value
            return
        value = json.loads(text)
        if isinstance(value, dict):
            yield "root", value
            for key, child in value.items():
                if isinstance(child, list):
                    for index, item in enumerate(child):
                        if isinstance(item, dict):
                            yield f"{key}[{index}]", item
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    yield f"root[{index}]", item
    except (OSError, UnicodeError, json.JSONDecodeError):
        return


def _source_fields(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return {
        "upgrade_id": record.get("upgrade_id") or record.get("candidate_id") or record.get("consumption_id"),
        "binding_id": record.get("binding_id"),
        "source_id": record.get("source_id") or source.get("source_id"),
        "source_kind": record.get("source_kind") or source.get("source_kind"),
        "source_ref": record.get("source_ref") or source.get("source_ref"),
    }


def _classify(record: dict[str, Any]) -> tuple[str, list[str], dict[str, Any] | None]:
    fields = [field for field in MATERIAL_FIELDS if _nonempty(record.get(field))]
    if fields:
        if (
            record.get("source_class") == "same_source_derived_improvement"
            or record.get("status") == "validated_overlay"
            or record.get("resolution") == "already_present_in_baseline"
        ):
            return "validated_derived_overlay", fields, {field: record[field] for field in fields}
        has_target = _nonempty(record.get("target_object_id")) or _nonempty(record.get("source_ref"))
        has_baseline = "baseline_value" in record or "baseline_content" in record
        is_mutation = str(record.get("action") or "").lower() in {"replace", "append", "insert", "complete", "update"}
        if not (has_target and has_baseline and is_mutation):
            return "unbound_structured_change", fields, {field: record[field] for field in fields}
        return "recoverable_material_revision", fields, {field: record[field] for field in fields}
    assessment = record.get("model_assessment")
    if isinstance(assessment, dict) and _nonempty(assessment.get("suggested_revision")):
        return "advisory_material_revision", ["model_assessment.suggested_revision"], assessment
    upgrade = record.get("upgrade")
    if isinstance(upgrade, dict) and isinstance(upgrade.get("causal_contract"), dict):
        return "creative_contract_only", ["upgrade.causal_contract"], upgrade["causal_contract"]
    linkage = _source_fields(record)
    if any(_nonempty(value) for value in linkage.values()):
        return "audit_metadata_only", [], None
    return "not_upgrade_artifact", [], None


def _candidate_paths(directory: Path, deep: bool) -> list[Path]:
    try:
        paths = directory.rglob("*") if deep else directory.glob("*")
        return sorted(
            path for path in paths
            if path.is_file()
            and path.suffix.lower() in {".json", ".jsonl"}
            and (deep or any(marker in path.name for marker in UPGRADE_NAME_MARKERS))
        )
    except OSError:
        return []


def audit(root: str | Path, output_name: str = "升级成果追溯审计", deep: bool = False) -> dict[str, Any]:
    project = Path(root).expanduser().resolve()
    output = project / "文档" / "证据" / output_name
    if output.exists():
        raise FileExistsError(f"审计输出已存在，拒绝覆盖: {output}")
    artifacts: list[dict[str, Any]] = []
    scanned_files = 0
    skipped_files = 0
    for relative in DEFAULT_INPUTS:
        directory = project / relative
        if not directory.is_dir():
            continue
        paths = _candidate_paths(directory, deep)
        if not paths and directory.is_dir():
            skipped_files += 1
        for path in paths:
            scanned_files += 1
            try:
                relative_path = path.relative_to(project).as_posix()
                artifact_sha256 = _sha256(path)
                if artifact_sha256 is None:
                    skipped_files += 1
                    continue
                for locator, record in _read_records(path):
                    classification, content_fields, content = _classify(record)
                    if classification == "not_upgrade_artifact":
                        continue
                    artifacts.append({
                        **_source_fields(record),
                        "classification": classification,
                        "content_fields": content_fields,
                        "content": content,
                        "artifact_path": relative_path,
                        "artifact_locator": locator,
                        "artifact_sha256": artifact_sha256,
                    })
            except (OSError, ValueError):
                skipped_files += 1
    artifacts.sort(key=lambda row: (str(row.get("binding_id") or ""), row["artifact_path"], row["artifact_locator"]))
    recoverable = [row for row in artifacts if row["classification"] == "recoverable_material_revision"]
    advisory = [row for row in artifacts if row["classification"] == "advisory_material_revision"]
    overlays = [row for row in artifacts if row["classification"] == "validated_derived_overlay"]
    missing = [row for row in artifacts if row["classification"] in {"creative_contract_only", "audit_metadata_only", "unbound_structured_change"}]
    output.mkdir(parents=True)
    for name, rows in (("升级成果资产清单.jsonl", artifacts), ("可融合升级成果.jsonl", recoverable), ("人工采用改进建议.jsonl", advisory), ("已验证派生覆盖层.jsonl", overlays), ("升级成果缺失清单.jsonl", missing)):
        (output / name).write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    counts = Counter(row["classification"] for row in artifacts)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "scanned_json_or_jsonl_file_count": scanned_files,
        "skipped_file_count": skipped_files,
        "scan_scope": "all_json_and_jsonl_under_evidence_and_archive" if deep else "top_level_upgrade_named_artifacts_only",
        "artifact_count": len(artifacts),
        "classification_counts": dict(sorted(counts.items())),
        "recoverable_material_revision_count": len(recoverable),
        "advisory_material_revision_count": len(advisory),
        "validated_derived_overlay_count": len(overlays),
        "next_route": "bind_and_merge_recoverable_revisions" if recoverable else "regenerate_structured_material_revisions",
        "boundary": "creative_contract_only 和 audit_metadata_only 不得直接写回原始资料。",
        "files": {
            "assets": "升级成果资产清单.jsonl",
            "recoverable": "可融合升级成果.jsonl",
            "advisory": "人工采用改进建议.jsonl",
            "validated_derived_overlay": "已验证派生覆盖层.jsonl",
            "missing": "升级成果缺失清单.jsonl",
        },
    }
    (output / "升级成果缺失报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="追溯历史升级成果，区分资料改写、人工建议与运行证据")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-name", default="升级成果追溯审计")
    parser.add_argument("--deep", action="store_true", help="扫描证据和归档下全部 JSON/JSONL；默认只扫描升级相关命名资产")
    args = parser.parse_args()
    print(json.dumps(audit(args.project_root, args.output_name, args.deep), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())