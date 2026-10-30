"""Route strict quarantines into content-based recovery packages without admitting evidence.

Content fingerprints help reviewers group and replace unusable records. They never prove
the historical source identity, change source status, or grant downstream eligibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 严格资料升级 as strict_upgrade


SCHEMA_VERSION = "strict-quarantine-content-routing-1.0"
CONTENT_ROUTABLE_CATEGORIES = {
    "candidate_identity_missing",
    "locator_invalid_or_out_of_range",
}
REPLACEMENT_ONLY_CATEGORIES = {"object_boundary_missing"}


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _locator_parts(source_ref: str) -> tuple[str | None, str | None]:
    match = re.fullmatch(r"([^:]+):([^\[\]:]+)\[\d+\]", source_ref)
    return match.groups() if match else (None, None)


def _object_id(source_item: Any) -> str | None:
    if not isinstance(source_item, dict):
        return None
    for key in ("connection_id", "dynamic_combination_id", "stable_id", "id"):
        value = source_item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _route(record: dict[str, Any], source_item: Any, resolution_error: str | None) -> dict[str, Any]:
    category = str(record["category_id"])
    source_ref = str(record["source_ref"])
    source_block, declared_collection = _locator_parts(source_ref)
    content_hash = _canonical_hash(source_item) if resolution_error is None else None
    detected_id = _object_id(source_item) if resolution_error is None else None
    base = {
        "schema_version": SCHEMA_VERSION,
        "upgrade_id": record["upgrade_id"],
        "consumption_id": record["consumption_id"],
        "binding_id": record["binding_id"],
        "category_id": category,
        "source_id": record["source_id"],
        "source_kind": record["source_kind"],
        "historical_source_ref": source_ref,
        "historical_source_ref_sha256": record["source_ref_sha256"],
        "historical_source_item_sha256": record["source_item_sha256"],
        "content_source_block": source_block,
        "declared_collection": declared_collection,
        "content_object_sha256": content_hash,
        "detected_object_id": detected_id,
        "resolver_error": resolution_error,
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
    }
    if category in CONTENT_ROUTABLE_CATEGORIES and resolution_error is None:
        base.update({
            "disposition": "candidate_content_mapping_requires_independent_confirmation",
            "candidate_mapping_basis": "exact current JSON object canonical SHA-256 and bounded source locator",
            "required_next_step": "人工核验候选对象的来源权利、适用范围和历史标识关系；随后提交独立替代来源或项目确认。",
            "candidate_replacement_object_id": detected_id,
        })
    else:
        base.update({
            "disposition": "replacement_source_required",
            "candidate_mapping_basis": None,
            "required_next_step": "提供具有单一对象边界、稳定定位、对象 ID 和独立 SHA-256 的替代来源；不得由跨行内容拼接推定原对象。",
            "candidate_replacement_object_id": None,
        })
    return base


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    source_dir = root / "文档" / "证据" / "严格资料升级"
    input_path = source_dir / "严格隔离分类" / "严格隔离分类清单.jsonl"
    if not input_path.is_file():
        raise FileNotFoundError(f"找不到隔离分类清单: {input_path}")
    records = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    targets = [record for record in records if record.get("category_id") in CONTENT_ROUTABLE_CATEGORIES | REPLACEMENT_ONLY_CATEGORIES]
    routes = []
    for record in targets:
        source_item, resolution_error = strict_upgrade._resolve_ref(root, str(record["source_ref"]))
        routes.append(_route(record, source_item, resolution_error))

    packages: dict[tuple[str, str | None, str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
    for route in routes:
        key = (route["disposition"], route["content_source_block"], route["declared_collection"], route["content_object_sha256"])
        packages[key].append(route)
    package_rows = []
    for number, (_, items) in enumerate(
        sorted(packages.items(), key=lambda entry: tuple(value or "" for value in entry[0])), start=1
    ):
        exemplar = items[0]
        package_rows.append({
            "package_id": f"CRP-{number:05d}",
            "disposition": exemplar["disposition"],
            "content_source_block": exemplar["content_source_block"],
            "declared_collection": exemplar["declared_collection"],
            "content_object_sha256": exemplar["content_object_sha256"],
            "detected_object_id": exemplar["detected_object_id"],
            "record_count": len(items),
            "upgrade_ids": [item["upgrade_id"] for item in items],
            "required_replacement_manifest_fields": ["replacement_source_id", "exact_locator", "source_object_id", "source_object_sha256", "source_rights_or_approval", "scope", "reviewed_by", "reviewed_at"],
            "formal_fact_eligible": False,
            "prose_write_allowed": False,
        })
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_content_based_routing; content_similarity_is_not_source_identity_proof",
        "input_classification": "文档/证据/严格资料升级/严格隔离分类/严格隔离分类清单.jsonl",
        "routed_record_count": len(routes),
        "candidate_content_mapping_count": sum(route["disposition"] == "candidate_content_mapping_requires_independent_confirmation" for route in routes),
        "replacement_source_required_count": sum(route["disposition"] == "replacement_source_required" for route in routes),
        "package_count": len(package_rows),
        "disposition_counts": dict(Counter(route["disposition"] for route in routes)),
        "formal_fact_eligible_count": 0,
        "prose_write_allowed": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
    }
    output = source_dir / "严格隔离内容分流"
    staging = source_dir / ".严格隔离内容分流_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "严格隔离内容分流报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "严格隔离内容分流清单.jsonl").write_text("".join(json.dumps(route, ensure_ascii=False) + "\n" for route in routes), encoding="utf-8")
    (staging / "替代来源包清单.jsonl").write_text("".join(json.dumps(package, ensure_ascii=False) + "\n" for package in package_rows), encoding="utf-8")
    if sum(package["record_count"] for package in package_rows) != len(routes):
        raise RuntimeError("替代来源包完整性检查失败")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())