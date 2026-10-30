"""Register raw material baselines and evidence layers without changing source data.

The current raw-material directory is authoritative. Files found in upgrade,
archive, candidate, acceptance, or runtime locations are recorded as derived
evidence and are never eligible to increase current fact counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "原始资料"
EVIDENCE_ROOT = ROOT / "文档" / "证据"
OUTPUT_ROOT = EVIDENCE_ROOT / "基线与证据登记"

RAW_NAMES = {
    "动态网络.txt",
    "类型系统.txt",
    "类型连接.txt",
    "资料库.txt",
    "锚点网络.txt",
    "静态网络.txt",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _layer_for(path: Path) -> tuple[str, str, bool]:
    relative = _relative(path)
    parts = set(path.relative_to(ROOT).parts)
    name = path.name.lower()

    if path.parent == RAW_ROOT and path.name in RAW_NAMES:
        return "original_source", "current_raw_baseline", True
    if "归档" in parts or "回归历史" in parts or "改进方法" in parts:
        return "historical_artifact", "historical_or_archive", False
    if "候选" in parts or "candidate" in name or "验收" in parts:
        return "candidate", "review_or_acceptance_candidate", False
    if "运行" in parts or "execution_outputs" in parts:
        return "runtime_derived", "current_or_historical_runtime_output", False
    if "合并升级" in parts or "资料版本" in parts:
        return "runtime_derived", "upgrade_or_versioned_projection", False
    if "证据" in parts or "docs" in parts:
        return "runtime_derived", "derived_evidence", False
    if path.suffix.lower() in {".log", ".out", ".err"}:
        return "runtime_derived", "tool_output", False
    return "unknown", "unclassified", False


def _iter_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for base in paths:
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else base.rglob("*")
        for path in candidates:
            if path.is_file() and path not in seen:
                seen.add(path)
                result.append(path)
    return sorted(result, key=lambda item: _relative(item))


def _record(path: Path, generated_at: str) -> dict[str, Any]:
    layer, origin, eligible = _layer_for(path)
    stat = path.stat()
    return {
        "relative_path": _relative(path),
        "evidence_layer": layer,
        "origin_status": origin,
        "fact_count_eligible": eligible,
        "sha256": sha256_file(path),
        "bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "registered_at": generated_at,
    }


def build(root: str | Path = ROOT) -> dict[str, Any]:
    global ROOT, RAW_ROOT, EVIDENCE_ROOT, OUTPUT_ROOT
    ROOT = Path(root).resolve()
    RAW_ROOT = ROOT / "原始资料"
    EVIDENCE_ROOT = ROOT / "文档" / "证据"
    OUTPUT_ROOT = EVIDENCE_ROOT / "基线与证据登记"
    generated_at = datetime.now(timezone.utc).isoformat()

    raw_files = [RAW_ROOT / name for name in sorted(RAW_NAMES)]
    raw_records = [_record(path, generated_at) for path in _iter_files(raw_files)]

    # Include current evidence, version/upgrade trees, archives, and exported
    # chat records. These are provenance records, not additional source facts.
    evidence_paths = [
        EVIDENCE_ROOT,
        ROOT / "文档" / "合并升级",
        ROOT / "资料版本",
        ROOT / "验收",
        ROOT / "改进方法",
    ]
    evidence_records = [
        _record(path, generated_at)
        for path in _iter_files(evidence_paths)
        if path.parent != OUTPUT_ROOT and OUTPUT_ROOT not in path.parents
    ]

    duplicate_materials = [
        record for record in evidence_records if record["relative_path"].lower().endswith("资料库.txt")
    ]
    layer_counts: dict[str, int] = {}
    for record in evidence_records:
        layer = record["evidence_layer"]
        layer_counts[layer] = layer_counts.get(layer, 0) + 1

    baseline = {
        "schema_version": "raw-material-baseline-1.0",
        "generated_at": generated_at,
        "root": str(ROOT),
        "authority": "原始资料",
        "writeback_allowed": False,
        "raw_files": raw_records,
        "raw_file_count": len(raw_records),
        "missing_raw_files": sorted(set(RAW_NAMES) - {Path(item["relative_path"]).name for item in raw_records}),
        "same_name_material_copies": duplicate_materials,
        "policy": {
            "raw_source_is_sole_fact_source": True,
            "derived_files_may_not_increase_fact_counts": True,
            "candidate_and_historical_files_require_review": True,
            "content_writeback_requires_field_level_human_confirmation": True,
        },
    }
    all_records = raw_records + evidence_records
    registry = {
        "schema_version": "evidence-layer-registry-1.0",
        "generated_at": generated_at,
        "root": str(ROOT),
        "records": all_records,
        "record_count": len(all_records),
        "evidence_layer_counts": layer_counts,
        "fact_count_eligible_count": sum(item["fact_count_eligible"] for item in all_records),
        "excluded_from_current_fact_counts": sum(not item["fact_count_eligible"] for item in all_records),
        "policy": "历史聊天、旧运行、升级副本、候选和审计产物只能提供来源线索，不能替代当前原始事实。",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline_path = OUTPUT_ROOT / "原始资料基线.json"
    registry_path = OUTPUT_ROOT / "证据层登记.json"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "passed",
        "raw_file_count": len(raw_records),
        "evidence_record_count": len(all_records),
        "same_name_material_copy_count": len(duplicate_materials),
        "fact_count_eligible_count": registry["fact_count_eligible_count"],
        "baseline": str(baseline_path),
        "registry": str(registry_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    print(json.dumps(build(args.root), ensure_ascii=False))