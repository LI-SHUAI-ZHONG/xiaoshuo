"""Create a tamper-evident, non-release registry for legacy prose consumption."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "full-source-legacy-consumption-quarantine-1.0"
REGISTRY_FILE = "全量资料历史消费隔离清单.json"
CONSUMPTION_FILE = "全量资料正文消费证据.json"
ARCHIVE_FILE = "全量资料升级档案.jsonl"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _canonical_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: str | Path, include_unregistered_archive: bool = False) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    consumption_path = evidence / CONSUMPTION_FILE
    archive_path = evidence / ARCHIVE_FILE
    consumption_doc = _read(consumption_path, {})
    consumption = [row for row in consumption_doc.get("records", []) if isinstance(row, dict)] if isinstance(consumption_doc, dict) else []
    archive = _jsonl(archive_path)
    archive_by_id = {row.get("consumption_id"): row for row in archive if row.get("consumption_id")}
    existing = _read(evidence / REGISTRY_FILE, {})
    prior_entries = existing.get("entries", []) if isinstance(existing, dict) else []
    prior_ids = {row.get("consumption_id") for row in prior_entries if isinstance(row, dict) and isinstance(row.get("consumption_id"), str)}
    # The first run freezes the pre-existing corpus as legacy. Later runs must
    # not silently reclassify newly authorized production as historical.
    historical_ids = prior_ids or {row.get("consumption_id") for row in consumption if isinstance(row.get("consumption_id"), str)}
    # An interrupted historical migration can leave immutable upgrade records
    # outside the first freeze. This opt-in repair path is deliberately limited
    # to records already present in the legacy archive, never live production.
    if include_unregistered_archive:
        historical_ids |= {
            row.get("consumption_id")
            for row in archive
            if isinstance(row.get("consumption_id"), str)
        }
    consumption_by_id = {row.get("consumption_id"): row for row in consumption if isinstance(row.get("consumption_id"), str)}
    entries = []
    for consumption_id in sorted(historical_ids):
        row = consumption_by_id.get(consumption_id)
        archive_row = archive_by_id.get(consumption_id)
        prior_entry = next((entry for entry in prior_entries if isinstance(entry, dict) and entry.get("consumption_id") == consumption_id), None)
        if not isinstance(consumption_id, str) or not isinstance(archive_row, dict):
            raise ValueError(f"历史消费记录无法与升级档案一一对应: {consumption_id!r}")
        # A frozen historical record is deliberately absent from the current
        # consumption evidence. Its retained archive hash remains auditable.
        if not isinstance(row, dict):
            if isinstance(prior_entry, dict):
                current_archive_hash = _canonical_hash(archive_row)
                if prior_entry.get("archive_record_sha256") != current_archive_hash:
                    prior_entry = {
                        **prior_entry,
                        "archive_integrity_status": "historical_archive_drift_nonrelease",
                        "observed_archive_record_sha256": current_archive_hash,
                    }
                entries.append(prior_entry)
                continue
            if not include_unregistered_archive:
                raise ValueError(f"历史消费记录已缺失，无法首次建立隔离: {consumption_id!r}")
            source = archive_row.get("source", {})
            entries.append({
                "consumption_id": consumption_id,
                "binding_id": archive_row.get("binding_id"),
                "source_id": source.get("source_id") if isinstance(source, dict) else None,
                "consumption_record_sha256": None,
                "archive_record_sha256": _canonical_hash(archive_row),
                "quarantine_status": "historical_unverified_nonrelease",
                "prose_write_allowed": False,
                "formal_release_allowed": False,
            })
            continue
        if row.get("binding_id") != archive_row.get("binding_id") or row.get("source_id") != archive_row.get("source", {}).get("source_id"):
            raise ValueError(f"历史消费与升级档案身份不一致: {consumption_id}")
        entries.append({
            "consumption_id": consumption_id,
            "binding_id": row.get("binding_id"),
            "source_id": row.get("source_id"),
            "consumption_record_sha256": _canonical_hash(row),
            "archive_record_sha256": _canonical_hash(archive_row),
            "quarantine_status": "historical_unverified_nonrelease",
            "prose_write_allowed": False,
            "formal_release_allowed": False,
        })
    registry = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": "本清单在首次建立时冻结历史未授权消费；后续运行仅复核已冻结记录，不将新增的已授权生产重新归类为历史。登记记录不得进入当前生产计划、生产队列或生产批次。",
        "source_files": {
            CONSUMPTION_FILE: _file_hash(consumption_path),
            ARCHIVE_FILE: _file_hash(archive_path),
        },
        "quarantined_record_count": len(entries),
        "entries": entries,
    }
    target = evidence / REGISTRY_FILE
    target.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--include-unregistered-archive", action="store_true")
    args = parser.parse_args()
    registry = build(args.project_root, include_unregistered_archive=args.include_unregistered_archive)
    print(json.dumps({"quarantined_record_count": registry["quarantined_record_count"], "output": REGISTRY_FILE}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())