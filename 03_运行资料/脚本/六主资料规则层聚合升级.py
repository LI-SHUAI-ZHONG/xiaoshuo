"""Aggregate usable rule-layer upgrades for the six original material files.

This stage is deliberately review-only.  It does not append audit records to
the original files and does not write model output back.  It collects business
rules from the upgrade assets, removes provenance/audit metadata, and creates
bounded packages for the existing text-generation model.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TARGETS = {
    "资料库.txt": ("资料库", "library", "dependencies", "overlay", "field_changes"),
    "静态网络.txt": ("静态网络", "static", "静态连接"),
    "动态网络.txt": ("动态网络", "dynamic", "动态连接"),
    "锚点网络.txt": ("锚点网络", "anchor", "锚点"),
    "类型系统.txt": ("类型系统", "type_system", "类型本体", "类型总表"),
    "类型连接.txt": ("类型连接", "type_connection", "类型连接"),
}
RULE_KEYS = {
    "定义", "调用条件", "指令", "设计指令", "写作指令", "分级标准",
    "场景变体", "判定标准", "修正指南", "关联板块", "关联路径", "优先级",
    "例外处理", "调用标签", "dependencies", "conditions", "effects",
    "constraints", "exceptions", "required_action", "required_result",
    "candidate_value", "upgrade_units", "field_path", "changes",
}
META_KEYS = {
    "schema_version", "generated_at", "created_at", "updated_at", "timestamp",
    "upgrade_id", "consumption_id", "binding_id", "binding_ids", "source_id",
    "source_kind", "source_ref", "source_refs", "source", "source_file",
    "source_line", "source_path", "source_hash", "source_sha256",
    "source_file_sha256", "source_item_sha256", "baseline_file_sha256",
    "baseline_object_sha256", "original_object_sha256", "after_sha256",
    "artifact_sha256", "artifact_path", "artifact_locator", "content_fields",
    "sha256", "hash", "overlay_id", "unit_id", "semantic_key", "status",
    "mapping_status", "resolution", "classification", "permitted_use",
    "prose_write_allowed", "formal_fact_eligible", "formal_release_allowed",
    "project_source_confirmed", "item_attested", "attestation_scope",
    "original_prose_artifacts_modified", "writeback_allowed", "fusion_allowed",
    "review_status", "model_metadata", "derivation_rule", "target_object_id",
    "original_file", "original_locator", "original_object_id", "upgrade_method", "record_format",
    "target_basis", "evidence", "verification", "errors", "reason",
}
TARGET_ALIASES = {name: set(values) | {name} for name, values in TARGETS.items()}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def json_files(root: Path) -> Iterable[Path]:
    # Do not recursively ingest the original text files or every audit/log
    # artifact.  These are the upgrade assets confirmed for this workflow.
    roots = [
        root / "文档" / "合并升级",
        root / "文档" / "资料融合工作区",
        root / "文档" / "证据" / "全量资料升级派生定位" / "已验证候选映射.jsonl",
        root / "文档" / "证据" / "资料融合版本" / "V3" / "validated_overlay.jsonl",
        root / "文档" / "证据" / "升级成果追溯审计" / "可融合升级成果.jsonl",
        root / "文档" / "证据" / "升级成果追溯审计_V2" / "可融合升级成果.jsonl",
        root / "文档" / "证据" / "严格升级原版对象绑定" / "bindings.jsonl",
        root / "文档" / "证据" / "原版资料升级执行" / "首对象审查候选V5" / "upgrade_records.jsonl",
    ]
    for entry in roots:
        if entry.is_file() and entry.suffix in {".json", ".jsonl"}:
            yield entry
        elif entry.is_dir():
            for path in entry.rglob("*"):
                excluded = {"规则层聚合", "快照差异审查"}
                if path.is_file() and path.suffix in {".json", ".jsonl"} and not any(
                    any(part.startswith(prefix) for prefix in excluded) for part in path.parts
                ):
                    yield path


def target_for(value: Any) -> str | None:
    # Structured locators are authoritative.  Do not let a nested summary
    # mentioning all six materials determine the current record's owner.
    locators: list[str] = []
    fields = {"material", "file", "original_source_file", "original_file", "source_file", "original_object_id"}
    def collect(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in fields and isinstance(child, str):
                    locators.append(child.replace("\\", "/"))
                elif key not in {"summary", "records", "source_refs"}:
                    collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)
    collect(value)
    matches = []
    for target in TARGETS:
        stem = target[:-4]
        if any(item == target or item == stem or item.endswith("/" + target) or f"原始资料/{target}" in item for item in locators):
            matches.append(target)
    if len(set(matches)) == 1:
        return matches[0]
    text = json.dumps(value, ensure_ascii=False)
    scores = {target: sum(text.count(alias) for alias in aliases) for target, aliases in TARGET_ALIASES.items()}
    target, score = max(scores.items(), key=lambda item: item[1])
    return target if score else None


def has_rule(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(set(value) & RULE_KEYS) or any(has_rule(item) for item in value.values())
    if isinstance(value, list):
        return any(has_rule(item) for item in value)
    return False


def clean(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        result = {}
        for child_key, child in value.items():
            if child_key in META_KEYS or child_key.lower() in {item.lower() for item in META_KEYS}:
                continue
            cleaned = clean(child, child_key)
            if cleaned not in (None, "", [], {}):
                result[child_key] = cleaned
        return result
    if isinstance(value, list):
        result = [clean(item, key) for item in value]
        return [item for item in result if item not in (None, "", [], {})]
    if isinstance(value, str):
        value = re.sub(r"(?i)(?:sha256|hash|状态|许可|来源路径|source_ref)\s*[:：=]\s*[^,，\n]+", "", value)
        return value.strip()
    return value


def relevant(value: Any) -> bool:
    if not has_rule(value):
        return False
    text = json.dumps(value, ensure_ascii=False)
    return any(key in text for key in RULE_KEYS)


def rule_candidate(value: dict[str, Any]) -> dict[str, Any]:
    """Project an accepted record onto the minimal field-change contract."""
    def first(key: str) -> Any:
        found: list[Any] = []
        def walk(item: Any) -> None:
            if isinstance(item, dict):
                if key in item and item[key] not in (None, "", [], {}):
                    found.append(item[key])
                for child in item.values():
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
        walk(value)
        return found[0] if found else None

    locator = first("original_object_id") or first("target_object_id") or first("semantic_key")
    changes = first("changes")
    if isinstance(changes, list):
        projected = []
        for change in changes:
            if not isinstance(change, dict) or not change.get("field_path"):
                continue
            item = {"field_path": change["field_path"]}
            for key in ("operation", "before", "after", "candidate_value"):
                if change.get(key) not in (None, "", [], {}):
                    item[key] = clean(change[key])
            projected.append(item)
        if projected:
            return {"target_object_locator": locator, "changes": projected}
    units = first("upgrade_units")
    if isinstance(units, list):
        projected = []
        for unit in units:
            if not isinstance(unit, dict) or not unit.get("field_path"):
                continue
            item = {"field_path": unit["field_path"]}
            for key in ("operation", "before", "after", "candidate_value"):
                if unit.get(key) not in (None, "", [], {}):
                    item[key] = clean(unit[key])
            projected.append(item)
        if projected:
            return {"target_object_locator": locator, "changes": projected}
    return {"target_object_locator": locator, "field_path": first("field_path"), "candidate_value": clean(first("candidate_value"))}


def classify(value: Any) -> str:
    """Classify evidence before it can become model input.

    Existing-baseline overlays and locator/binding records are useful for
    diagnostics, but they are not upgrade rules and must not be sent to the
    model as if they were new material.
    """
    if not isinstance(value, dict):
        return "unresolved"
    status = str(value.get("status", ""))
    resolution = str(value.get("resolution", ""))
    if status in {"linked_audit_only", "object_mapping_only", "linked_unchanged", "unresolved", "unparsed"}:
        return "audit_only"
    if resolution == "already_present_in_baseline" or value.get("action") == "retain":
        return "already_present_validation"
    def first(key: str) -> Any:
        found: list[Any] = []
        def walk(item: Any) -> None:
            if isinstance(item, dict):
                if key in item:
                    found.append(item[key])
                for child in item.values():
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
        walk(value)
        return found[0] if found else None
    units = first("upgrade_units")
    changes = first("changes")
    candidate = first("candidate_value")
    def has_nonempty(key: str) -> bool:
        found = False
        def walk(item: Any) -> None:
            nonlocal found
            if found:
                return
            if isinstance(item, dict):
                if item.get(key) not in (None, "", [], {}):
                    found = True
                    return
                for child in item.values():
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
        walk(value)
        return found
    has_target = has_nonempty("target_object_id") or has_nonempty("semantic_key") or has_nonempty("original_object_id")
    has_field_path = has_nonempty("field_path")
    if isinstance(units, list) and units and any(isinstance(item, dict) and item.get("field_path") and item.get("candidate_value") not in (None, "", [], {}) for item in units):
        return "usable_rule"
    if isinstance(changes, list) and has_target and has_field_path and any(isinstance(item, dict) and item.get("field_path") and item.get("after") not in (None, "", []) for item in changes):
        return "usable_rule"
    if candidate not in (None, "", [], {}) and has_target and has_field_path:
        return "usable_rule"
    if value.get("binding_id") or value.get("derived_original_object"):
        return "audit_only"
    if any(first(key) is not None for key in ("content", "field_changes", "upgrade")):
        return "unresolved"
    return "unresolved"


def _missing_rule_fields(value: dict[str, Any]) -> list[str]:
    missing = []
    if not any(value.get(key) not in (None, "", [], {}) for key in ("target_object_id", "semantic_key")):
        missing.append("target_object_id_or_semantic_key")
    if not value.get("field_path"):
        missing.append("field_path")
    if not value.get("changes") and not value.get("upgrade_units"):
        missing.append("changes_or_upgrade_units")
    if value.get("candidate_value") not in (None, "", [], {}) and not value.get("field_path"):
        missing.append("candidate_value_without_field_path")
    return missing or ["usable_rule_contract_not_satisfied"]


def read_records(path: Path) -> Iterable[tuple[int, Any]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return
    if path.suffix == ".jsonl":
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                yield line_number, json.loads(line)
            except json.JSONDecodeError:
                continue
    else:
        try:
            yield 1, json.loads(text)
        except json.JSONDecodeError:
            return


def build(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    output = root / "文档" / "合并升级" / run_id
    if output.exists() or Path(run_id).name != run_id:
        raise ValueError("run_id 非法或输出目录已存在")
    output.mkdir(parents=True)
    packages = {target: [] for target in TARGETS}
    classified = {target: Counter() for target in TARGETS}
    unresolved = {target: [] for target in TARGETS}
    audit_sources = {target: Counter() for target in TARGETS}
    source_counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    scanned = 0
    for path in json_files(root):
        scanned += 1
        for line_number, record in read_records(path):
            target = target_for(record)
            category = classify(record)
            if target:
                classified[target][category] += 1
                audit_sources[target][path.relative_to(root).as_posix()] += 1
            if not target or category != "usable_rule" or not relevant(record):
                if target and category == "unresolved":
                    unresolved[target].append({
                        "evidence": clean(record),
                        "missing": _missing_rule_fields(record),
                        "source_file": path.relative_to(root).as_posix(),
                        "source_line": line_number,
                    })
                continue
            cleaned = rule_candidate(record)
            fingerprint = (target, json.dumps(cleaned, ensure_ascii=False, sort_keys=True))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            packages[target].append({
                "rule_candidate": cleaned,
                "source_material": target,
                "source_kind": "upgrade_rule_candidate",
            })
            source_counts[path.relative_to(root).as_posix()] += 1
    counts = {}
    for target, records in packages.items():
        path = output / f"{target}.rules.jsonl"
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
        counts[target] = len(records)
        (output / f"{target}.unresolved.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in unresolved[target]), encoding="utf-8"
        )
    manifest = {
        "schema_version": "six-primary-material-rule-aggregation-1.0",
        "generated_at": now(),
        "review_only": True,
        "original_sources_modified": False,
        "upgrade_asset_roots": [
            "文档/资料融合工作区",
            "文档/证据",
            "资料版本",
        ],
        "scanned_file_count": scanned,
        "candidate_counts": counts,
        "classification_counts": {target: dict(counter) for target, counter in classified.items()},
        "source_counts": dict(source_counts),
        "classification_sources": {target: dict(counter) for target, counter in audit_sources.items()},
        "unresolved_counts": {target: len(rows) for target, rows in unresolved.items()},
        "metadata_removed": sorted(META_KEYS),
        "packages": {target: f"{target}.rules.jsonl" for target in TARGETS},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="聚合六个主资料的规则层升级候选")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.run_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())