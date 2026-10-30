"""Inventory locally observable source-provenance clues without qualifying use.

This creates a reviewer aid only. A local snapshot, generated metadata, or
content-derived scope is never treated as a human source-qualification decision.
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


SCHEMA_VERSION = "source-qualification-evidence-clue-inventory-1.0"
REQUIRED_EVIDENCE = ("origin_locator", "version_identifier", "responsible_party", "applicability_scope")
DERIVED_FILES = {
    "动态网络": "网络完整数据/动态连接完整数据.json",
    "静态网络": "网络完整数据/静态连接完整数据.json",
}
VERSION_RE = re.compile(r"(?:^|[\s>#\"'])((?:schema_)?version|版本)\s*[：:]\s*[\"']?([^\s\"',}]+)", re.IGNORECASE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("模型资格评估清单的 JSONL 行必须为对象")
        rows.append(value)
    return rows


def _snapshot(record: dict[str, Any]) -> dict[str, Any]:
    package = record.get("evidence_package") or {}
    for item in package.get("evidence", []):
        if isinstance(item, dict) and item.get("name") == "input_snapshot" and isinstance(item.get("value"), dict):
            return item["value"]
    raise ValueError(f"{record.get('source_kind')} 缺少输入快照证据")


def _safe_file(root: Path, relative: str) -> Path | None:
    path = (root / relative).resolve()
    return path if root in path.parents and path.is_file() else None


def _first_version(path: Path) -> str | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError):
        value = None
    if isinstance(value, dict) and isinstance(value.get("version"), str) and value["version"].strip():
        return value["version"].strip()
    match = VERSION_RE.search(path.read_text(encoding="utf-8-sig", errors="replace")[:200_000])
    return match.group(2).strip() if match else None


def _derived_metadata(root: Path, source_kind: str) -> dict[str, Any] | None:
    relative = DERIVED_FILES.get(source_kind)
    path = _safe_file(root, relative) if relative else None
    if not path:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError):
        return {"path": relative, "sha256": _sha256(path), "parse_status": "unparseable"}
    metadata = {"path": relative, "sha256": _sha256(path), "parse_status": "parseable"}
    if isinstance(value, dict):
        for key in ("version", "source_file", "total_sources", "total_connections", "total_blocks"):
            if key in value:
                metadata[key] = value[key]
    return metadata


def _record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot(record)
    relative = str(snapshot.get("path") or "")
    path = _safe_file(root, relative)
    expected_hash = str(snapshot.get("sha256") or "")
    actual_hash = _sha256(path) if path else None
    snapshot_matches = bool(path and actual_hash == expected_hash)
    version = _first_version(path) if snapshot_matches and path else None
    observed = {
        "local_snapshot": {"path": relative, "expected_sha256": expected_hash, "actual_sha256": actual_hash, "hash_matches_model_review_input": snapshot_matches},
        "snapshot_version_hint": version,
        "related_derived_metadata": _derived_metadata(root, str(record.get("source_kind"))),
    }
    fields = {
        "origin_locator": {"status": "local_snapshot_only" if snapshot_matches else "unavailable", "value": f"{relative}#sha256={actual_hash}" if snapshot_matches else None, "qualification_sufficient": False},
        "version_identifier": {"status": "observed_unverified" if version else "unavailable", "value": version, "qualification_sufficient": False},
        "responsible_party": {"status": "unavailable", "value": None, "qualification_sufficient": False},
        "applicability_scope": {"status": "unavailable", "value": None, "qualification_sufficient": False},
    }
    missing = [key for key, value in fields.items() if not value["qualification_sufficient"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "source_kind": record.get("source_kind"),
        "source_file": record.get("source_file"),
        "input_snapshot_sha256": record.get("input_snapshot_sha256"),
        "observed_metadata": observed,
        "evidence_field_clues": fields,
        "still_required_from_authorized_reviewer": missing,
        "reviewer_instruction": "仅可将原始出处、版本发布记录、责任主体声明和适用范围/许可的可核验定位填入人工裁决提交；本清单不能替代其中任何一项。",
        "source_qualification_status": "not_assessed",
        "formal_fact_eligible": False,
        "model_input_eligible": False,
        "prose_write_allowed": False,
    }


def build(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    assessment = root / "文档" / "证据" / "严格资料升级" / "模型辅助来源资格评估" / "模型辅助来源资格评估清单.jsonl"
    records = _read_jsonl(assessment)
    if not records:
        raise ValueError("模型资格评估清单缺失或为空")
    clues = [_record(root, record) for record in records]
    output = assessment.parent / "来源资格人工裁决" / "来源资格证据线索"
    staging = output.parent / ".来源资格证据线索_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    statuses = Counter(item["evidence_field_clues"][field]["status"] for item in clues for field in REQUIRED_EVIDENCE)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local_observation_only; no_human_decision_or_source_or_usage_permission_modified",
        "model_assessment_path": str(assessment.relative_to(root)).replace("\\", "/"),
        "model_assessment_sha256": _sha256(assessment),
        "source_kind_count": len(clues),
        "evidence_field_status_counts": dict(sorted(statuses.items())),
        "qualification_sufficient_evidence_field_count": 0,
        "formal_fact_eligible_count": 0,
        "model_input_eligible_count": 0,
        "prose_write_allowed": False,
    }
    (staging / "来源资格证据线索清单.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in clues), encoding="utf-8")
    (staging / "来源资格证据线索报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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