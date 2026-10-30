"""Inventory semantic activation prerequisites for all bound source materials.

The inventory is evidence only. Resolving an object or extracting a condition
does not approve a source, admit it as a formal fact, or permit prose writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "bound-material-activation-prerequisite-inventory-1.0"
SOURCE_BLOCK_RE = re.compile(r"^SOURCE:\s*(?P<name>[^\r\n]+)\r?\n=+\r?\n(?P<body>.*?)(?=\r?\nSOURCE:|\Z)", re.MULTILINE | re.DOTALL)
LIBRARY_ENTRY_RE = re.compile(r"^#{2,3}\s+(?P<id>\d+(?:\.\d+)?_[^\r\n]+)\r?\n(?P<body>.*?)(?=^#{2,3}\s+\d+(?:\.\d+)?_|\Z)", re.MULTILINE | re.DOTALL)
LIBRARY_SECTION_RE = re.compile(r"^##\s+板块(?P<number>\d+)\s+(?P<title>[^\r\n]+)\r?\n(?P<body>.*?)(?=^##\s+板块|\Z)", re.MULTILINE | re.DOTALL)
ANCHOR_ROW_RE = re.compile(r"^\|\s*(?P<id>[A-Z]+\d+(?:\.\d+)?)\s*\|\s*(?P<name>[^|]+)\|\s*(?P<content>[^|]+)\|\s*(?P<condition>[^|]+)\|", re.MULTILINE)
INDEXED_SOURCE_REF_RE = re.compile(r"类型连接\.txt:(?P<name>[^\[]+)\[(?P<index>\d+)\]$")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _snapshot(path: Path, root: Path, record_count: int | None = None) -> dict[str, Any]:
    content = path.read_bytes()
    snapshot: dict[str, Any] = {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }
    if record_count is None:
        snapshot["line_count"] = len(content.decode("utf-8-sig").splitlines())
    else:
        snapshot["record_count"] = record_count
    return snapshot


def _source_blocks(path: Path) -> list[tuple[str, Any]]:
    blocks = []
    for match in SOURCE_BLOCK_RE.finditer(path.read_text(encoding="utf-8-sig")):
        try:
            blocks.append((match.group("name").strip(), json.loads(match.group("body").strip())))
        except json.JSONDecodeError:
            continue
    return blocks


def _source_block_texts(path: Path) -> list[tuple[str, str]]:
    """Keep block boundaries even where an assembled JSON payload is malformed."""
    return [(match.group("name").strip(), match.group("body").strip()) for match in SOURCE_BLOCK_RE.finditer(path.read_text(encoding="utf-8-sig"))]


def _collect_conditions(value: Any, output: list[str]) -> None:
    keys = {"condition", "conditions", "trigger_condition_ids", "selection_constraints", "valid_types", "requires", "prerequisites"}
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and child not in (None, "", [], {}):
                output.extend(str(item) for item in child) if isinstance(child, list) else output.append(str(child))
            _collect_conditions(child, output)
    elif isinstance(value, list):
        for child in value:
            _collect_conditions(child, output)


def _requirements(value: Any) -> list[dict[str, str]]:
    conditions: list[str] = []
    _collect_conditions(value, conditions)
    return [
        {"kind": "material_semantic_condition", "requirement": item}
        for item in dict.fromkeys(item.strip() for item in conditions if item.strip() and item.strip() != "无")
    ]


def _matches_object_identifier(value: Any, source_id: str) -> bool:
    return isinstance(value, dict) and any(
        key.endswith("_id") and candidate == source_id
        for key, candidate in value.items()
        if isinstance(candidate, str)
    )


def _validate_rows(rows: list[dict[str, Any]], expected_count: int) -> dict[str, int]:
    duplicate_binding_count = len(rows) - len({row["binding_id"] for row in rows})
    missing_locator_count = sum(not row["resolved_locator"] for row in rows)
    empty_source_ref_count = sum(not row["source_ref"] for row in rows)
    semantic_invariant_failure_count = sum(
        (row["semantic_activation_status"] == "conditions_declared") != bool(row["activation_prerequisites"])
        for row in rows
    )
    permission_isolation_failure_count = sum(
        not (
            row["source_qualification_status"] == "not_assessed"
            and row["project_selection_status"] == "not_assessed"
            and not row["formal_fact_eligible"]
            and not row["model_input_eligible"]
            and not row["prose_write_allowed"]
        )
        for row in rows
    )
    checks = {
        "expected_bound_record_count": expected_count,
        "actual_bound_record_count": len(rows),
        "duplicate_binding_count": duplicate_binding_count,
        "missing_locator_count": missing_locator_count,
        "empty_source_ref_count": empty_source_ref_count,
        "semantic_invariant_failure_count": semantic_invariant_failure_count,
        "permission_isolation_failure_count": permission_isolation_failure_count,
    }
    if any((len(rows) != expected_count, duplicate_binding_count, missing_locator_count, empty_source_ref_count, semantic_invariant_failure_count, permission_isolation_failure_count)):
        raise ValueError(f"盘点完整性校验失败: {checks}")
    return checks


def _validate_binding_manifest(manifest: dict[str, Any], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    actual_source_kind_counts = dict(sorted(Counter(str(row.get("source_kind")) for row in bindings).items()))
    actual_stage_counts = dict(sorted(Counter(str(row.get("creation_binding", {}).get("primary_stage")) for row in bindings).items()))
    translated_record_count = sum(row.get("translation_status") == "translated" for row in bindings)
    declared_record_counts = {
        "source_count": manifest.get("source_count"),
        "translated_count": manifest.get("translated_count"),
        "binding_count": manifest.get("binding_count"),
    }
    checks = {
        "declared_record_counts": declared_record_counts,
        "actual_record_count": len(bindings),
        "actual_translated_record_count": translated_record_count,
        "declared_source_kind_counts": manifest.get("source_kind_counts"),
        "actual_source_kind_counts": actual_source_kind_counts,
        "declared_stage_counts": manifest.get("stage_counts"),
        "actual_stage_counts": actual_stage_counts,
    }
    valid = (
        all(count == len(bindings) for count in declared_record_counts.values())
        and translated_record_count == len(bindings)
        and manifest.get("source_kind_counts") == actual_source_kind_counts
        and manifest.get("stage_counts") == actual_stage_counts
    )
    if not valid:
        raise ValueError(f"创作绑定清单元数据校验失败: {checks}")
    return checks


def _load_objects(root: Path) -> dict[str, dict[str, Any]]:
    raw = root / "原始资料"
    objects: dict[str, dict[str, Any]] = {}
    library_text = (raw / "资料库.txt").read_text(encoding="utf-8-sig")
    for match in LIBRARY_ENTRY_RE.finditer(library_text):
        entry_id, body = match.group("id").strip(), match.group("body")
        call = re.search(r"【调用条件】\s*\r?\n(?P<value>.*?)(?=\r?\n\r?\n【|\Z)", body, re.DOTALL)
        objects[f"资料库:{entry_id}"] = {"locator": entry_id, "source_object": body, "requirements": _requirements({"condition": call.group("value").strip() if call else ""})}
    for match in LIBRARY_SECTION_RE.finditer(library_text):
        entry_id = f"{match.group('number')}_{match.group('title').strip()}"
        body = match.group("body")
        call = re.search(r"【调用条件】\s*\r?\n(?P<value>.*?)(?=\r?\n\r?\n【|\Z)", body, re.DOTALL)
        objects[f"资料库:{entry_id}"] = {"locator": f"板块{match.group('number')} {match.group('title').strip()}", "source_object": body, "requirements": _requirements({"condition": call.group("value").strip() if call else ""})}
    static = _read_json(raw / "静态网络.txt")
    index = 0
    for source, source_data in static.get("source_index", {}).items():
        for target in source_data.get("targets", []):
            index += 1
            source_id = f"STATIC:{source}->{target.get('target')}#{index}"
            objects[f"静态网络:{source_id}"] = {"locator": f"source_index[{source}].targets[{index}]", "source_object": target, "requirements": _requirements(target)}
    dynamic_text = (raw / "动态网络.txt").read_text(encoding="utf-8-sig")
    dynamic_payload = json.loads(re.search(r"```json\s*(?P<body>.*?)\s*```", dynamic_text, re.DOTALL).group("body"))
    for item in dynamic_payload["动态网络连接_完整版"]["连接列表"]:
        objects[f"动态网络:{item['id']}"] = {"locator": f"连接列表[{item['id']}]", "source_object": item, "requirements": _requirements(item)}
    anchor_text = (raw / "锚点网络.txt").read_text(encoding="utf-8-sig")
    for match in ANCHOR_ROW_RE.finditer(anchor_text):
        item = match.groupdict()
        objects[f"锚点网络:{item['id']}"] = {"locator": f"line:{anchor_text[:match.start()].count(chr(10)) + 1}", "source_object": item, "requirements": _requirements({"condition": item['condition'].strip()})}
    type_blocks = _source_block_texts(raw / "类型系统.txt")
    for number, (name, body) in enumerate(type_blocks, 1):
        try:
            value = json.loads(body)
        except json.JSONDecodeError:
            value = None
        objects[f"类型系统来源块:TYPE-SOURCE:{number}"] = {"locator": f"SOURCE:{name}", "source_object": value, "requirements": _requirements(value) if value is not None else []}
        if value is None:
            continue
        for item in _walk_dicts(value):
            names = {str(item.get(key, "")) for key in ("canonical_name", "display_name", "name", "type_name")}
            for source_id in names - {""}:
                objects.setdefault(f"类型系统:{source_id}", {"locator": f"SOURCE:{name}", "source_object": item, "requirements": _requirements(item)})
    connection_id_candidates: dict[str, list[dict[str, Any]]] = {}
    for name, body in _source_block_texts(raw / "类型连接.txt"):
        try:
            entries = json.loads(body)
        except json.JSONDecodeError:
            entries = None
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            objects[f"类型连接引用:{name}[1]"] = {"locator": f"SOURCE:{name}", "source_object": None, "requirements": []}
            continue
        for index, item in enumerate(entries, 1):
            if not isinstance(item, dict):
                continue
            data = {"locator": f"SOURCE:{name}[{index}]", "source_object": item, "requirements": _requirements(item)}
            for key, value in item.items():
                if key.endswith("_id") and isinstance(value, str) and value.strip():
                    connection_id_candidates.setdefault(value, []).append(data)
            objects[f"类型连接引用:{name}[{index}]"] = data
    for source_id, candidates in connection_id_candidates.items():
        if len(candidates) == 1:
            objects[f"类型连接:{source_id}"] = candidates[0]
    return objects


def _walk_dicts(value: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_dicts(child))
    return found


def inventory(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    binding_path = evidence / "全量资料解释词创作绑定.json"
    binding_manifest = _read_json(binding_path)
    bindings = binding_manifest.get("records", [])
    binding_manifest_validation = _validate_binding_manifest(binding_manifest, bindings)
    raw = root / "原始资料"
    input_snapshots = {
        "创作绑定": _snapshot(binding_path, root, len(bindings)),
        "资料库": _snapshot(raw / "资料库.txt", root),
        "类型系统": _snapshot(raw / "类型系统.txt", root),
        "类型连接": _snapshot(raw / "类型连接.txt", root),
        "动态网络": _snapshot(raw / "动态网络.txt", root),
        "静态网络": _snapshot(raw / "静态网络.txt", root),
        "锚点网络": _snapshot(raw / "锚点网络.txt", root),
    }
    objects = _load_objects(root)
    rows = []
    for binding in bindings:
        kind, source_id = str(binding.get("source_kind")), str(binding.get("source_id"))
        object_data = objects.get(f"{kind}:{source_id}")
        identity_status = "resolved_by_intrinsic_id" if object_data else "identity_unverified"
        if object_data is None and kind == "类型连接":
            match = INDEXED_SOURCE_REF_RE.search(str(binding.get("source_ref", "")))
            if match:
                object_data = objects.get(f"类型连接引用:{match.group('name')}[{match.group('index')}]")
                if object_data:
                    identity_status = "resolved_by_intrinsic_id" if _matches_object_identifier(object_data["source_object"], source_id) else "resolved_by_binding_locator"
        requirements = object_data["requirements"] if object_data else []
        if object_data:
            resolution_status = identity_status
        elif kind == "锚点网络" and source_id.startswith("ID"):
            resolution_status = "identity_recovery_or_replacement_required"
        else:
            resolution_status = "unresolved"
        rows.append({
            "schema_version": SCHEMA_VERSION,
            "binding_id": binding.get("binding_id"),
            "source_kind": kind,
            "source_id": source_id,
            "source_ref": binding.get("source_ref"),
            "object_resolution_status": resolution_status,
            "resolved_locator": object_data["locator"] if object_data else None,
            "semantic_activation_status": "conditions_declared" if requirements else "no_explicit_conditions_declared",
            "activation_prerequisites": requirements,
            "source_qualification_status": "not_assessed",
            "project_selection_status": "not_assessed",
            "recommended_governance_disposition": "identity_recovery_or_replacement_required" if resolution_status == "identity_recovery_or_replacement_required" else "no_identity_remediation_indicated",
            "formal_fact_eligible": False,
            "model_input_eligible": False,
            "prose_write_allowed": False,
        })
    resolution = Counter(row["object_resolution_status"] for row in rows)
    semantic = Counter(row["semantic_activation_status"] for row in rows)
    validation = _validate_rows(rows, len(bindings))
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "bound_source_semantic_prerequisites_only; no_qualification_or_creative_artifact_modified",
        "bound_record_count": len(rows),
        "input_snapshots": input_snapshots,
        "binding_manifest_validation": binding_manifest_validation,
        "object_resolution_status_counts": dict(sorted(resolution.items())),
        "semantic_activation_status_counts": dict(sorted(semantic.items())),
        "by_source_kind": {kind: dict(Counter(row["object_resolution_status"] for row in rows if row["source_kind"] == kind)) for kind in sorted({row["source_kind"] for row in rows})},
        "identity_recovery_queue_count": sum(row["recommended_governance_disposition"] != "no_identity_remediation_indicated" for row in rows),
        "integrity_validation": validation,
        "policy": "对象解析或条件提取不构成来源资格批准、正式事实准入、模型输入准入或正文写作许可。",
        "formal_fact_eligible_count": 0,
        "model_input_eligible_count": 0,
        "prose_write_allowed": False,
        "project_artifacts_modified": False,
    }
    output = evidence / "严格资料升级" / "全量资料激活前置条件盘点"
    staging = output.parent / ".全量资料激活前置条件盘点_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "全量资料激活前置条件盘点报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "全量资料激活前置条件清单.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    recovery_rows = [row for row in rows if row["recommended_governance_disposition"] != "no_identity_remediation_indicated"]
    (staging / "身份恢复与替代来源队列.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in recovery_rows), encoding="utf-8")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps(inventory(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())