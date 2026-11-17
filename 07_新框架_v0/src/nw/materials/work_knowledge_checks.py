"""Structural checks for supplied work knowledge records."""
from collections import Counter
from collections.abc import Iterator
from itertools import combinations


DISALLOWED_TEXT = {"novel_text", "chapter_text", "dialogue_text", "quote_text", "quoted_text", "excerpt_text"}
CASE_IDS = {
    "type_case": "case_id",
    "style_case": "style_case_id",
    "static_pattern": "static_pattern_id",
    "dynamic_pattern": "dynamic_pattern_id",
    "combination": "combination_id",
}
REFERENCE_FIELDS = {
    "dynamic_rule_id", "dynamic_rule_ids", "rule_id", "rule_ids", "source_refs", "component_ids",
}


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, code: str, path: str, source_block: int, *, status: str = "invalid") -> None:
        self.items.append({"code": code, "path": path, "source_block": source_block, "status": status})

    def require(self, row: dict, keys: list[str], path: str, source_block: int,
                code: str = "missing_required") -> None:
        for key in keys:
            if key not in row:
                self.add(code, f"{path}/{key}", source_block)


def _filled(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_filled(item) for item in value)


def _objects(value: object, path: str) -> Iterator[tuple[str, dict]]:
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            pointer = key.replace("~", "~0").replace("/", "~1")
            yield from _objects(item, f"{path}/{pointer}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _objects(item, f"{path}/{index}")


def _fixture_value(value: object) -> bool:
    if isinstance(value, str):
        return value.startswith("FIXTURE_")
    return isinstance(value, list) and any(isinstance(item, str) and item.startswith("FIXTURE_") for item in value)


def _is_fixture(row: dict) -> bool:
    return (row.get("evidence_type") == "fixture" or row.get("status") == "fixture_only"
            or any(_fixture_value(value) for key, value in row.items() if key.endswith(("_id", "_ids"))))


def _review_boundary(row: dict, path: str, kind: str, rules: dict, findings: Findings,
                     *, test_mode: bool) -> bool:
    objects = list(_objects(row, path))
    if not test_mode and any(_is_fixture(item) for _, item in objects):
        findings.add("fixture_only", path, 391 if kind == "analysis" else 386)
        return False
    forbidden = DISALLOWED_TEXT
    if kind == "analysis":
        policy = rules[391]["rules"]["forbidden_content_rule"]
        forbidden = forbidden | set(policy["forbidden_fields"])
    block = 391 if kind == "analysis" else 386 if kind == "abstract_pattern" else 387
    for pointer, item in objects:
        for key in sorted(forbidden.intersection(item)):
            findings.add("copyright_risk", f"{pointer}/{key}", block)
        if (item.get("copyright_safe") is False or item.get("copyright_risk") is True
                or bool(item.get("copyright_risk_fields"))):
            findings.add("copyright_risk", pointer, block)
    return True


def _identifiers(rows: list[tuple[str, dict]], field: str, block: int, findings: Findings) -> None:
    identifiers = Counter(row[field] for _, row in rows if _filled(row.get(field)))
    for path, row in rows:
        value = row.get(field)
        if not _filled(value):
            findings.add("empty_id", f"{path}/{field}", block)
        elif identifiers[value] > 1:
            findings.add("duplicate_id", f"{path}/{field}", block)


def _intake(row: dict, rules: dict, path: str, findings: Findings) -> dict | None:
    findings.require(row, ["input_id", "work_id", "analysis_level"], path, 382)
    levels = rules[384]["levels"]
    level = row.get("analysis_level")
    if not isinstance(level, str) or level not in levels:
        findings.add("unknown_analysis_level", f"{path}/analysis_level", 384)
        return None
    if (row.get("authorization_status") != "confirmed" or row.get("verification_status") != "verified"
            or not _strings(row.get("source_refs"))):
        findings.add("source_unconfirmed", path, 387, status="waiting")
        return None
    return {"record": path, "analysis_level": level, **levels[level]}


def _source(row: dict, path: str, findings: Findings) -> None:
    if not _filled(row.get("source_record_id")) or not _filled(row.get("source_name")):
        findings.add("missing_required", path, 342)
    if not _filled(row.get("source_url")) and not _filled(row.get("source_path")):
        findings.add("source_locator", path, 342, status="waiting")
    if not _filled(row.get("retrieved_at")):
        findings.add("missing_retrieved_at", f"{path}/retrieved_at", 342, status="waiting")
    if row.get("ranking_position") is not None and not _filled(row.get("ranking_scope")):
        findings.add("missing_ranking_scope", f"{path}/ranking_scope", 342, status="waiting")
    if row.get("metric_value") is not None:
        keys = ("metric_name", "metric_unit", "time_scope", "data_as_of")
        for key in keys:
            if not _filled(row.get(key)):
                findings.add("missing_metric_scope", f"{path}/{key}", 342, status="waiting")


def _compare(rows: list[tuple[str, dict]], policy: dict, findings: Findings) -> None:
    if len(rows) < 2:
        findings.add("missing_comparison_record", "/records", 351, status="waiting")
    for (left_path, left), (right_path, right) in combinations(rows, 2):
        names = (left.get("metric_name"), right.get("metric_name"))
        entry = next((row for row in policy["comparisons"]
                      if names in ((row["metric_a"], row["metric_b"]), (row["metric_b"], row["metric_a"]))), None)
        if any(not _filled(record.get(key)) for record in (left, right)
               for key in ("platform", "time_scope", "region", "metric_name", "metric_unit")):
            findings.add("comparison_scope_unconfirmed", right_path, 351, status="waiting")
        elif (entry and entry["comparable"] is False
              or any(left.get(key) != right.get(key) for key in ("platform", "time_scope", "region", "metric_unit"))):
            findings.add("not_comparable", right_path, 351)
        elif not entry:
            findings.add("comparison_rule_unconfirmed", left_path, 351, status="waiting")


def _excluded_references(row: dict, path: str, policy: dict, block: int, findings: Findings) -> None:
    rule = next((value for value in policy.values() if isinstance(value, dict) and "excluded_ids" in value), {})
    excluded = set(rule.get("excluded_ids", []))
    for pointer, item in _objects(row, path):
        for field in sorted(REFERENCE_FIELDS.intersection(item)):
            value = item[field]
            refs = value if isinstance(value, list) else [value]
            if any(isinstance(ref, str) and ref in excluded for ref in refs):
                findings.add("excluded_reference", f"{pointer}/{field}", block)


def _enum(row: dict, fields: tuple[str, ...], path: str, policy: dict,
          block: int, findings: Findings) -> None:
    for key in fields:
        if key in row and row[key] not in policy[f"{key}_enum"]["values"]:
            findings.add("invalid_enum", f"{path}/{key}", block)


def _abstract(row: dict, path: str, policy: dict, findings: Findings) -> None:
    findings.require(row, policy["required_fields"]["fields"], path, 386)
    if not _strings(row.get("source_work_ids")):
        findings.add("missing_work_sources", f"{path}/source_work_ids", 386)
    _enum(row, ("pattern_kind", "evidence_type", "status"), path, policy, 386, findings)
    _excluded_references(row, path, policy, 386, findings)


def _analyses(rows: list[tuple[str, dict]], rules: dict, findings: Findings) -> None:
    policy = rules[391]["rules"]
    abstract_policy = rules[386]["rules"]
    _identifiers(rows, "analysis_id", 391, findings)
    works = {record["work_id"] for _, record in rows if _filled(record.get("work_id"))}
    if len(works) > rules[80]["batch_size"]:
        findings.add("batch_limit", "/records", 80)
    patterns = []
    for path, row in rows:
        findings.require(row, policy["required_fields"]["fields"], path, 391)
        if "work_id" in row and not _filled(row["work_id"]):
            findings.add("empty_id", f"{path}/work_id", 391)
        _enum(row, ("evidence_type", "status", "reviewer_status"), path, policy, 391, findings)
        _excluded_references(row, path, policy, 391, findings)
        for pointer, item in _objects(row, path):
            if {"ratio", "denominator", "numerator"}.intersection(item):
                fields = policy["ratio_field_rule"]["required_keys"]
                findings.require(item, fields, pointer, 391, "incomplete_ratio")
            elif "value" in item and "unit" in item:
                fields = policy["statistical_field_rule"]["required_keys"]
                findings.require(item, fields, pointer, 391, "incomplete_statistic")
        extracted = row.get("extracted_patterns", [])
        if not isinstance(extracted, list):
            findings.add("invalid_patterns", f"{path}/extracted_patterns", 391)
            continue
        for index, pattern in enumerate(extracted):
            pointer = f"{path}/extracted_patterns/{index}"
            if not isinstance(pattern, dict):
                findings.add("invalid_patterns", pointer, 391)
                continue
            _abstract(pattern, pointer, abstract_policy, findings)
            patterns.append((pointer, pattern))
    _identifiers(patterns, "pattern_id", 386, findings)


def _case(row: dict, path: str, kind: str, rules: dict, findings: Findings) -> None:
    block = 363 if kind == "type_case" else 119 if kind == "style_case" else 386
    findings.require(row, ["source_work_ids", "not_guaranteed", "similarity_features", "originality_risk"], path, block)
    _excluded_references(row, path, rules[386]["rules"], block, findings)
    if kind == "dynamic_pattern":
        limits = row.get("propagation_limits")
        if not isinstance(limits, dict):
            findings.add("missing_required", f"{path}/propagation_limits", 27)
            return
        defaults = rules[27]["global_defaults"]
        for field, limit in (("max_depth", "max_propagation_depth"),
                             ("max_activated_rules", "max_activated_rules_per_scene"),
                             ("max_state_updates", "max_state_updates_per_scene")):
            value = limits.get(field)
            if type(value) is not int or not 0 <= value <= defaults[limit]:
                findings.add("propagation_limit", f"{path}/propagation_limits/{field}", 27)


def _review(row: dict, template: dict, path: str, findings: Findings) -> None:
    required = ("review_id", "analysis_id", "reviewer", "reviewed_at", "review_status", "review_notes")
    for key in required:
        if not _filled(row.get(key)):
            findings.add("incomplete_review", f"{path}/{key}", 374, status="waiting")
    for key, value in template.items():
        if isinstance(value, dict) and "passed" in value:
            submitted = row.get(key)
            if not isinstance(submitted, dict) or type(submitted.get("passed")) is not bool:
                findings.add("incomplete_review", f"{path}/{key}/passed", 374, status="waiting")
    if row.get("approved_for_case_library") is True and row.get("review_status") not in (
            "approved", "approved_with_limits"):
        findings.add("review_decision_conflict", f"{path}/approved_for_case_library", 373)


def review_work_input(kind: str, records: list[dict], rules: dict, *, test_mode: bool) -> dict:
    findings = Findings()
    scopes = []
    rows = []
    for index, record in enumerate(records):
        path = f"/records/{index}"
        if _review_boundary(record, path, kind, rules, findings, test_mode=test_mode):
            rows.append((path, record))
    if kind == "analysis":
        _analyses(rows, rules, findings)
    elif kind == "abstract_pattern" or kind in CASE_IDS:
        field = "pattern_id" if kind == "abstract_pattern" else CASE_IDS[kind]
        _identifiers(rows, field, 386, findings)
        for path, record in rows:
            if kind == "abstract_pattern":
                _abstract(record, path, rules[386]["rules"], findings)
            else:
                _case(record, path, kind, rules, findings)
    else:
        for path, record in rows:
            if kind in ("source", "metric_comparison"):
                _source(record, path, findings)
            elif kind == "source_template":
                findings.require(record, rules[342]["template_fields"], path, 342)
            elif kind == "source_conflict" and record.get("resolution_status") in (
                    "unresolved", "pending_review", None):
                findings.add("source_conflict", path, 340, status="waiting")
            elif kind == "work":
                if record.get("source_conflict") is True or record.get("verification_status") == "conflicting":
                    findings.add("source_conflict", path, 340, status="waiting")
                if not _filled(record.get("source_url")) and not _filled(record.get("source_path")):
                    findings.add("source_locator", path, 342, status="waiting")
            elif kind == "index":
                for pointer, item in _objects(record, path):
                    if "full_object" in item:
                        findings.add("full_object_in_index", f"{pointer}/full_object", 109)
            elif kind == "intake":
                before = len(findings.items)
                scope = _intake(record, rules, path, findings)
                if scope and before == len(findings.items) and not any(
                        item["path"] == path or item["path"].startswith(path + "/") for item in findings.items):
                    scopes.append(scope)
            elif kind == "review":
                _review(record, rules[374], path, findings)
        if kind == "metric_comparison" and rows:
            _compare(rows, rules[351], findings)
    status = "valid"
    if any(item["status"] == "invalid" for item in findings.items):
        status = "invalid"
    elif findings.items:
        status = "waiting"
    return {"status": status, "kind": kind, "use": "structural_review",
            "findings": findings.items, "analysis_scopes": scopes}
