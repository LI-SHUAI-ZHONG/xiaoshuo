"""Generate evidence-backed completeness logs for shared non-type sources.

The raw source files remain read-only. This only exposes existing normalized
fields with their original locators; it never creates story facts or grants
any source, model-input, or prose permission.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"规范化资料必须为对象数组：{path}")
    return value


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    governance = evidence / "全量资料治理"
    library = _read_json(governance / "资料库_规范化.json")
    anchors = _read_json(governance / "锚点网络_规范化.json")

    dependency_records = []
    example_records = []
    for item in library:
        entry_id = str(item.get("entry_id") or "").strip()
        source_ref = item.get("source_ref")
        if not entry_id or not isinstance(source_ref, dict):
            raise ValueError("资料库规范化条目缺少 entry_id 或 source_ref")
        dependency_records.append({
            "entry_id": entry_id,
            "dependencies": item.get("dependencies", []),
            "source_ref": source_ref,
            "evidence_kind": "explicit_or_normalized_dependency",
        })
        example_records.append({
            "entry_id": entry_id,
            "has_examples": bool(item.get("has_examples")),
            "source_ref": source_ref,
            "evidence_kind": "labeled_example_section_presence",
        })

    scene_binding_records = []
    text_location_records = []
    definition_records = []
    for item in anchors:
        anchor_id = str(item.get("anchor_id") or item.get("normalized_id") or "").strip()
        source_ref = item.get("source_ref")
        if not anchor_id or not isinstance(source_ref, dict):
            raise ValueError("锚点网络规范化条目缺少 anchor_id 或 source_ref")
        scene_binding_records.append({
            "anchor_id": anchor_id,
            "scene_binding": {
                "trigger_condition": item.get("trigger_condition"),
                "category": item.get("category"),
                "callable_only": True,
            },
            "source_ref": source_ref,
            "evidence_kind": "source_declared_trigger_condition",
        })
        definition_records.append({
            "anchor_id": anchor_id,
            "anchor_definition": item.get("anchor_definition"),
            "source_ref": source_ref,
            "evidence_kind": "normalized_anchor_definition",
        })
        text_location_records.append({
            "anchor_id": anchor_id,
            "text_location": source_ref,
            "evidence_kind": "normalized_raw_locator",
        })

    staging = evidence / ".非类型资料证据_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    outputs = {
        "资料库依赖分类日志.jsonl": dependency_records,
        "资料库示例修复日志.jsonl": example_records,
        "锚点网络场景绑定日志.jsonl": scene_binding_records,
        "锚点网络定义日志.jsonl": definition_records,
        "锚点网络文本位置日志.jsonl": text_location_records,
    }
    for name, records in outputs.items():
        _write_jsonl(staging / name, records)
    report = {
        "schema_version": "non-type-source-evidence-backfill-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "normalized_shared_non_type_sources_only; no_project_facts_or_permissions_modified",
        "library_record_count": len(library),
        "anchor_record_count": len(anchors),
        "outputs": {name: len(records) for name, records in outputs.items()},
        "type_sources_touched": False,
        "formal_fact_eligible": False,
        "model_input_eligible": False,
        "prose_write_allowed": False,
    }
    (staging / "非类型资料证据补全报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name in (*outputs, "非类型资料证据补全报告.json"):
        (evidence / name).unlink(missing_ok=True)
        (staging / name).replace(evidence / name)
    shutil.rmtree(staging, ignore_errors=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = build(args.project_root)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())