# -*- coding: utf-8 -*-
"""Validate network data from actual arrays and write audit reports."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "四网络连接，剧情覆盖"
REPORTS = ROOT / "reports"
PRIORITIES = {1, 2, 3, 4}
REQUIRED_DYNAMIC_FIELDS = ("id", "source", "target", "type", "direction", "strength", "condition", "valid_types", "priority", "effect", "generated_from_static", "needs_review")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def contains_fence(path):
    try:
        return "```" in path.read_text(encoding="utf-8")
    except OSError:
        return True


def ids_are_continuous(connections):
    return [item["id"] for item in connections] == [f"C{i:05d}" for i in range(1, len(connections) + 1)]


def record_key(item):
    return item.get("source", ""), item.get("target", ""), item.get("type", "")


def duplicate_count(records, include_condition=False):
    values = [record_key(x) + ((x.get("condition", ""),) if include_condition else ()) for x in records]
    return len(values) - len(set(values))


def index_errors(dynamic, records):
    expected = {"by_source": defaultdict(list), "by_target": defaultdict(list), "by_type": defaultdict(list)}
    for item in records:
        for index_name, value in (("by_source", item["source"]), ("by_target", item["target"]), ("by_type", item["type"])):
            expected[index_name][value].append(item["id"])
    errors = []
    for index_name, groups in expected.items():
        if dynamic.get("index", {}).get(index_name, {}) != dict(groups):
            errors.append({"index": index_name, "expected_groups": len(groups), "actual_groups": len(dynamic.get("index", {}).get(index_name, {}))})
    return errors


def source_index_errors(static):
    expected = Counter((x["source"], x["target"], x["type"], x.get("condition", ""), x.get("priority")) for x in static["connections"])
    actual = Counter((source, target.get("target", ""), target.get("type", ""), target.get("condition", ""), target.get("priority")) for source, entry in static.get("source_index", {}).items() for target in entry.get("targets", []))
    return [] if expected == actual else [{"expected": sum(expected.values()), "actual": sum(actual.values()), "missing": sum((expected - actual).values()), "extra": sum((actual - expected).values())}]


def validate():
    static = load("static_connections.full.json")
    dynamic = load("dynamic_connections.full.json")
    aliases = load("node_aliases.json")
    dynamic_only_report = json.loads((REPORTS / "dynamic_only_connections.json").read_text(encoding="utf-8"))
    generated_review = json.loads((REPORTS / "generated_connections_review.json").read_text(encoding="utf-8"))
    static_records = static["connections"]
    dynamic_records = dynamic["connections"]
    static_keys = {record_key(x) for x in static_records}
    dynamic_keys = {record_key(x) for x in dynamic_records}
    generated_records = [x for x in dynamic_records if x.get("generated_from_static") is True]
    original_records = [x for x in dynamic_records if x.get("generated_from_static") is False]
    invalid = []
    missing_fields = []
    for network, records in (("static", static_records), ("dynamic", dynamic_records)):
        for item in records:
            if not item.get("source") or not item.get("target"):
                invalid.append({"network": network, "reason": "empty source or target", "record": item})
            if item.get("priority") not in PRIORITIES:
                invalid.append({"network": network, "reason": "invalid priority", "record": item})
            if network == "dynamic":
                absent = [field for field in REQUIRED_DYNAMIC_FIELDS if field not in item]
                if absent:
                    missing_fields.append({"id": item.get("id"), "fields": absent})
    missing_generation_sources = [x["id"] for x in generated_records if not isinstance(x.get("field_source"), dict)]
    fence_files = [str(path) for path in (DATA / "static_connections.full.json", DATA / "dynamic_connections.full.json") if contains_fence(path)]
    static_priority_map = {}
    dynamic_priority_map = {}
    for item in static_records:
        static_priority_map.setdefault((item["source"], item["target"], item["type"]), set()).add(item["priority"])
    for item in dynamic_records:
        dynamic_priority_map.setdefault((item["source"], item["target"], item["type"]), set()).add(item["priority"])
    priority_conflicts = []
    dynamic_only = sorted(dynamic_keys - static_keys)
    static_only = sorted(static_keys - dynamic_keys)
    review_reasons = Counter(x.get("review_reason", "unspecified") for x in dynamic_records if x.get("needs_review"))
    for key in sorted(set(static_priority_map) & set(dynamic_priority_map)):
        sp = static_priority_map[key]
        dp = dynamic_priority_map[key]
        if sp != dp:
            priority_conflicts.append({"key": list(key), "static": sorted(sp), "dynamic": sorted(dp)})
    conflicts = []
    grouped = {}
    for item in dynamic_records:
        grouped.setdefault((item["source"], item["target"], item["type"]), []).append(item)
    for key, records in grouped.items():
        signatures = {(x.get("condition"), x.get("effect"), x.get("strength"), tuple(x.get("valid_types", []))) for x in records}
        if len(signatures) > 1:
            conflicts.append({"key": list(key), "record_count": len(records)})
    audit = {
        "static_actual_connections": len(static_records),
        "dynamic_original_connections": len(original_records),
        "dynamic_generated_connections": len(generated_records),
        "dynamic_final_connections": len(dynamic_records),
        "static_only_connections": len(static_only),
        "dynamic_only_connections": len(dynamic_only),
        "dynamic_only_classification_counts": dynamic_only_report.get("classification_counts", {}),
        "dynamic_original_actual": len(original_records),
        "dynamic_generated_actual": len(generated_records),
        "duplicate_count": duplicate_count(static_records, True) + duplicate_count(dynamic_records),
        "invalid_count": len(invalid),
        "unresolved_node_alias_count": len(aliases.get("unresolved_similar", [])),
        "needs_review_count": sum(1 for x in dynamic_records if x.get("needs_review")),
        "needs_review_reason_counts": dict(review_reasons),
        "priority_conflict_count": len(priority_conflicts),
        "dynamic_id_continuous": ids_are_continuous(dynamic_records),
        "index_error_count": len(index_errors(dynamic, dynamic_records)),
        "source_index_error_count": len(source_index_errors(static)),
        "missing_dynamic_fields_count": len(missing_fields),
        "conflicting_record_count": len(conflicts),
        "generated_missing_field_source_count": len(missing_generation_sources),
        "markdown_fence_file_count": len(fence_files),
        "formal_static_candidate_count": len(static_records),
        "details": {"invalid": invalid[:100], "dynamic_only": dynamic_only[:100], "static_only": static_only[:100], "index_errors": index_errors(dynamic, dynamic_records), "source_index_errors": source_index_errors(static), "priority_conflicts": priority_conflicts[:100], "conflicts": conflicts[:100], "missing_dynamic_fields": missing_fields[:100], "unresolved_aliases": aliases.get("unresolved_similar", [])[:100]},
    }
    blocking = [audit["duplicate_count"], audit["invalid_count"], audit["index_error_count"], audit["source_index_error_count"], audit["missing_dynamic_fields_count"], audit["priority_conflict_count"], audit["conflicting_record_count"], audit["generated_missing_field_source_count"], audit["markdown_fence_file_count"]]
    audit["status"] = "PASS" if audit["dynamic_id_continuous"] and not any(blocking) and not dynamic_only and not audit["needs_review_count"] else "REVIEW_REQUIRED"
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "network_connection_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Network Connection Audit", "", f"- status: **{audit['status']}**", f"- static actual connections: {audit['static_actual_connections']}", f"- dynamic original connections: {audit['dynamic_original_connections']}", f"- dynamic generated connections: {audit['dynamic_generated_connections']}", f"- dynamic final connections: {audit['dynamic_final_connections']}", f"- static-only connections: {audit['static_only_connections']}", f"- dynamic-only connections: {audit['dynamic_only_connections']}", f"- needs review: {audit['needs_review_count']}", f"- unresolved aliases: {audit['unresolved_node_alias_count']}", "", "## Reasons", ""]
    if audit["needs_review_count"]:
        lines.append("- Static-derived dynamic records have unknown semantic fields and require review.")
    if audit["unresolved_node_alias_count"]:
        lines.append("- Node names with the same numeric prefix were not merged automatically.")
    if dynamic_only:
        lines.append("- Dynamic-only records are not present in the static source map.")
    lines.append(f"- Dynamic-only classification counts: {json.dumps(dynamic_only_report.get('classification_counts', {}), ensure_ascii=False)}")
    lines.append(f"- Generated field-source gaps: {audit['generated_missing_field_source_count']}")
    (REPORTS / "network_connection_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(validate())