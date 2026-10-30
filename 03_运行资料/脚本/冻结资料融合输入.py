"""Freeze original materials and strict-upgrade batches for material fusion."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ORIGINAL_MATERIALS = (
    "动态网络.txt",
    "类型系统.txt",
    "类型连接.txt",
    "资料库.txt",
    "锚点网络.txt",
    "静态网络.txt",
)
BATCH_SOURCE = Path("文档/归档/2026-08-17_历史运行与废弃资料/证据/严格资料升级/批次")
FREEZE_ROOT = Path("文档/资料融合工作区/输入冻结V1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_batch(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    records = document.get("records")
    if document.get("schema_version") != "strict-source-upgrade-batch-1.0" or not isinstance(records, list):
        raise ValueError(f"批次格式无效: {path}")
    if document.get("batch_id") != path.stem:
        raise ValueError(f"批次 ID 与文件名不一致: {path}")
    if len(records) > int(document.get("record_limit", 0)):
        raise ValueError(f"批次记录数超过 record_limit: {path}")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"批次包含非对象记录: {path}")
    return records


def _copy_and_verify(source: Path, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _sha256(source)
    shutil.copy2(source, target)
    target_hash = _sha256(target)
    if source_hash != target_hash:
        raise RuntimeError(f"冻结副本哈希不一致: {source}")
    return {
        "source_path": source.as_posix(),
        "frozen_path": target.as_posix(),
        "bytes": source.stat().st_size,
        "sha256": source_hash,
    }


def freeze(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    output = root / FREEZE_ROOT
    if output.exists():
        raise FileExistsError(f"冻结目录已存在，拒绝覆盖: {output}")

    original_dir = root / "原始资料"
    batch_dir = root / BATCH_SOURCE
    original_paths = [original_dir / name for name in ORIGINAL_MATERIALS]
    missing = [str(path) for path in original_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"缺少原版资料: {missing}")
    batch_paths = sorted(batch_dir.glob("SOURCE-UPGRADE-*.json"))
    if not batch_paths:
        raise FileNotFoundError(f"找不到升级批次: {batch_dir}")

    output.mkdir(parents=True)
    try:
        originals = [
            _copy_and_verify(path, output / "原版资料" / path.name)
            for path in original_paths
        ]
        batches: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        for source in batch_paths:
            batch_records = _read_batch(source)
            batches.append(_copy_and_verify(source, output / "严格升级批次" / source.name))
            records.extend(batch_records)

        duplicate_ids = [
            identifier for identifier, count in Counter(str(row.get("upgrade_id")) for row in records).items()
            if count > 1
        ]
        if duplicate_ids:
            raise ValueError(f"升级记录存在重复 upgrade_id: {duplicate_ids[:3]}")
        manifest = {
            "schema_version": "material-fusion-input-freeze-1.0",
            "frozen_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "policy": "仅将原版资料与严格升级批次作为后续融合输入；原始资料和历史归档均未修改。",
            "original_materials": {
                "source_directory": "原始资料",
                "frozen_directory": "原版资料",
                "file_count": len(originals),
                "files": originals,
            },
            "strict_upgrade_batches": {
                "source_directory": BATCH_SOURCE.as_posix(),
                "frozen_directory": "严格升级批次",
                "batch_file_count": len(batches),
                "upgrade_record_count": len(records),
                "files": batches,
                "source_kind_counts": dict(sorted(Counter(str(row.get("source_kind")) for row in records).items())),
                "status_counts": dict(sorted(Counter(str(row.get("status")) for row in records).items())),
                "permitted_use_counts": dict(sorted(Counter(str(row.get("permitted_use")) for row in records).items())),
                "prose_write_allowed_count": sum(row.get("prose_write_allowed") is True for row in records),
            },
            "verification": {
                "copied_file_hashes_match_sources": True,
                "duplicate_upgrade_id_count": len(duplicate_ids),
                "original_source_modified": False,
                "historical_batch_source_modified": False,
            },
        }
        (output / "输入冻结清单.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="冻结资料融合的原版与严格升级输入")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    result = freeze(args.project_root)
    print(json.dumps({
        "output": str((Path(args.project_root).resolve() / FREEZE_ROOT)),
        "original_file_count": result["original_materials"]["file_count"],
        "batch_file_count": result["strict_upgrade_batches"]["batch_file_count"],
        "upgrade_record_count": result["strict_upgrade_batches"]["upgrade_record_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())