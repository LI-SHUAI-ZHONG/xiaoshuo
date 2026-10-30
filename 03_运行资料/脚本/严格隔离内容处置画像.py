"""Profile bounded quarantine content to choose a review strategy, without admission."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 严格资料升级 as strict_upgrade


SCHEMA_VERSION = "strict-quarantine-content-disposition-profile-1.0"


def _value(value: Any) -> str:
    return value if isinstance(value, str) and value else "<missing>"


def _profile(route: dict[str, Any], item: Any) -> tuple[str, ...]:
    if not isinstance(item, dict):
        return ("unbounded_or_unresolved",)
    return (
        "bounded_json_candidate",
        _value(item.get("status")),
        _value(item.get("evidence_type")),
        _value(item.get("generation_method")),
        _value(item.get("primary_type_id")),
        ",".join(sorted(item)) or "<empty_object>",
    )


def _strategy(key: tuple[str, ...]) -> tuple[str, str]:
    if key[0] == "unbounded_or_unresolved":
        return "independent_replacement_source", "对象边界不可恢复，必须取得新的单对象来源。"
    status, evidence_type, generation_method = key[1:4]
    if status == "candidate" and evidence_type == "template":
        return "template_provenance_and_scope_review", "模板候选需要补充模板来源/权利、适用范围和责任人签署；内容分类不能证明事实。"
    return "independent_replacement_or_explicit_project_review", "对象存在但来源状态或生成链不足，须补独立来源或明确项目级审阅。"


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    source_dir = root / "文档" / "证据" / "严格资料升级"
    source = source_dir / "严格隔离内容分流" / "严格隔离内容分流清单.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"找不到内容分流清单: {source}")
    routes = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for route in routes:
        item, error = strict_upgrade._resolve_ref(root, str(route["historical_source_ref"]))
        groups[_profile(route, item if error is None else None)].append(route)
    profiles = []
    for index, (key, items) in enumerate(sorted(groups.items()), start=1):
        strategy, rationale = _strategy(key)
        profiles.append({
            "profile_id": f"CDP-{index:04d}", "content_shape": key[0],
            "status": key[1] if len(key) > 1 else None,
            "evidence_type": key[2] if len(key) > 2 else None,
            "generation_method": key[3] if len(key) > 3 else None,
            "primary_type_id": key[4] if len(key) > 4 else None,
            "field_signature": key[5].split(",") if len(key) > 5 else [],
            "recommended_strategy": strategy, "rationale": rationale,
            "record_count": len(items), "upgrade_ids": [item["upgrade_id"] for item in items],
            "distinct_content_object_count": len({item.get("content_object_sha256") for item in items}),
            "per_object_hash_verification_required": True,
            "formal_fact_eligible": False, "prose_write_allowed": False,
        })
    report = {
        "schema_version": SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_content_disposition_profiling; profiles_do_not_admit_sources",
        "input_content_routing": "文档/证据/严格资料升级/严格隔离内容分流/严格隔离内容分流清单.jsonl",
        "profiled_record_count": len(routes), "profile_count": len(profiles),
        "strategy_counts": dict(Counter(profile["recommended_strategy"] for profile in profiles)),
        "formal_fact_eligible_count": 0, "prose_write_allowed": False,
        "source_status_modified": False, "project_confirmation_modified": False,
    }
    output = source_dir / "严格隔离内容处置画像"
    staging = source_dir / ".严格隔离内容处置画像_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "严格隔离内容处置画像报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "内容处置画像清单.jsonl").write_text("".join(json.dumps(profile, ensure_ascii=False) + "\n" for profile in profiles), encoding="utf-8")
    if sum(profile["record_count"] for profile in profiles) != len(routes):
        raise RuntimeError("内容处置画像完整性检查失败")
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