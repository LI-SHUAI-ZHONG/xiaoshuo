"""Isolate unsafe derived-material consumption evidence without retaining prose."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_ID = "20260816T061711Z-fb0cf077"
LEAKAGE_FIELDS = ("source_id", "source_kind", "source_ref", "matched_terms")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def run(project_root: str | Path) -> dict[str, Any]:
    """Return metadata-only failure samples; paragraph values are never read."""
    root = Path(project_root).expanduser().resolve()
    source = root / "文档" / "证据" / "派生资料正文消费证据.json"
    document = _read(source)
    errors: list[str] = []
    samples: list[dict[str, Any]] = []
    if document.get("run_id") != RUN_ID:
        errors.append("消费证据 run_id 不匹配")
    if document.get("release_status") != "draft_only":
        errors.append("消费证据未保持 draft_only")
    records = document.get("records")
    if not isinstance(records, list):
        errors.append("消费证据 records 无效")
        records = []
    for row in records:
        if not isinstance(row, dict):
            errors.append("消费证据包含非对象记录")
            continue
        quality = str(row.get("quality_status") or "")
        release = str(row.get("release_status") or "")
        leakage = [f"source_metadata_field:{field}" for field in LEAKAGE_FIELDS if field in row]
        reasons: list[str] = []
        if quality == "blocked":
            reasons.append("blocked_consumption")
        if release != "draft_only":
            reasons.append("release_status_not_draft_only")
        reasons.extend(leakage)
        if reasons:
            samples.append({
                "consumption_id": str(row.get("consumption_id") or ""),
                "binding_id": str(row.get("binding_id") or ""),
                "quality_status": quality,
                "release_status": release,
                "isolation_reasons": reasons,
            })
    blocked = sum(sample["quality_status"] == "blocked" for sample in samples)
    return {
        "schema_version": "derived-material-failure-sample-isolation-1.0",
        "run_id": RUN_ID,
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "consumption_evidence_metadata_only_no_prose_retained",
        "quality_status": "blocked" if errors or samples else "passed",
        "formal_release_allowed": False,
        "source_evidence": str(source),
        "counts": {"input_records": len(records), "isolated_samples": len(samples), "blocked_samples": blocked},
        "errors": errors,
        "failure_samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.project_root)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["quality_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())