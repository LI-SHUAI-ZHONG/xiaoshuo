"""Prepare review-only replacement-source drafts for content-routed quarantines.

Draft identifiers are administrative handles, not recovered historical IDs or evidence.
No draft can be consumed until a separately supplied source and approval are re-audited.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import 严格资料升级 as strict_upgrade


SCHEMA_VERSION = "strict-quarantine-replacement-source-plan-1.0"
CONTENT_CANDIDATE = "candidate_content_mapping_requires_independent_confirmation"


def _field_signature(source_item: Any) -> list[str]:
    return sorted(source_item) if isinstance(source_item, dict) else []


def _draft(route: dict[str, Any], source_item: Any, resolution_error: str | None) -> dict[str, Any]:
    content_hash = route.get("content_object_sha256")
    candidate = route["disposition"] == CONTENT_CANDIDATE and isinstance(content_hash, str)
    return {
        "schema_version": SCHEMA_VERSION,
        "replacement_draft_id": f"RSD-{content_hash[:16].upper()}" if candidate else None,
        "upgrade_id": route["upgrade_id"],
        "consumption_id": route["consumption_id"],
        "binding_id": route["binding_id"],
        "source_kind": route["source_kind"],
        "historical_source_id": route["source_id"],
        "historical_source_ref": route["historical_source_ref"],
        "historical_source_ref_sha256": route["historical_source_ref_sha256"],
        "content_object_sha256": content_hash,
        "content_field_signature": _field_signature(source_item) if resolution_error is None else [],
        "draft_kind": "bounded_content_candidate" if candidate else "replacement_required_without_recoverable_boundary",
        "identity_statement": "派生草案 ID 仅用于审阅队列，不是历史 source_id、来源证明或正式事实。",
        "required_submission": {
            "replacement_source_id": None,
            "exact_locator": None,
            "source_object_id": None,
            "source_object_sha256": None,
            "source_rights_or_approval": None,
            "scope": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "review_rationale": None,
        },
        "required_next_step": (
            "核验该有界内容对象与独立替代来源的内容一致性、权利、范围和稳定对象 ID，再提交严格重审。"
            if candidate else "先取得具备单一对象边界和稳定定位的独立替代来源，再建立对象哈希和审阅记录。"
        ),
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
    }


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    source_dir = root / "文档" / "证据" / "严格资料升级"
    input_path = source_dir / "严格隔离内容分流" / "严格隔离内容分流清单.jsonl"
    if not input_path.is_file():
        raise FileNotFoundError(f"找不到内容分流清单: {input_path}")
    routes = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    drafts = []
    for route in routes:
        source_item, resolution_error = strict_upgrade._resolve_ref(root, str(route["historical_source_ref"]))
        drafts.append(_draft(route, source_item, resolution_error))
    groups: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for draft in drafts:
        groups[(draft["draft_kind"], draft["replacement_draft_id"] or draft["historical_source_id"])].append(draft)
    batches = [{
        "batch_id": f"RSB-{index:05d}",
        "draft_kind": exemplar["draft_kind"],
        "replacement_draft_id": exemplar["replacement_draft_id"],
        "historical_source_id": exemplar["historical_source_id"] if exemplar["replacement_draft_id"] is None else None,
        "record_count": len(items),
        "upgrade_ids": [item["upgrade_id"] for item in items],
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
    } for index, (_, items) in enumerate(sorted(groups.items()), start=1) for exemplar in [items[0]]]
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "review_only_replacement_source_drafts; derived_ids_are_not_source_identity",
        "input_content_routing": "文档/证据/严格资料升级/严格隔离内容分流/严格隔离内容分流清单.jsonl",
        "draft_record_count": len(drafts),
        "batch_count": len(batches),
        "draft_kind_counts": dict(Counter(draft["draft_kind"] for draft in drafts)),
        "formal_fact_eligible_count": 0,
        "prose_write_allowed": False,
        "source_status_modified": False,
        "project_confirmation_modified": False,
    }
    output = source_dir / "严格隔离替代来源方案"
    staging = source_dir / ".严格隔离替代来源方案_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    (staging / "严格隔离替代来源方案报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "替代来源草案清单.jsonl").write_text("".join(json.dumps(draft, ensure_ascii=False) + "\n" for draft in drafts), encoding="utf-8")
    (staging / "替代来源审阅批次.jsonl").write_text("".join(json.dumps(batch, ensure_ascii=False) + "\n" for batch in batches), encoding="utf-8")
    if sum(batch["record_count"] for batch in batches) != len(drafts):
        raise RuntimeError("替代来源审阅批次完整性检查失败")
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