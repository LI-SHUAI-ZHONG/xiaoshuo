from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "原始资料"
BACKUP_ROOT = ROOT / "文档" / "合并升级" / f"raw-material-transfer-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
TARGETS = {
    "资料库.txt",
    "静态网络.txt",
    "动态网络.txt",
    "锚点网络.txt",
    "类型系统.txt",
    "类型连接.txt",
}
EXTENSIONS = {".json", ".jsonl", ".md", ".txt"}
SOURCE_ROOTS = [
    ROOT / "文档" / "资料融合工作区" / "输入冻结V1" / "严格升级批次",
    ROOT / "文档" / "归档" / "2026-08-17_历史运行与废弃资料" / "正文" / "全量资料升级" / "批次",
    ROOT / "文档" / "证据" / "全量资料升级派生定位",
    ROOT / "文档" / "证据" / "全量资料增量升级" / "20260817T061417Z-c75fb8a7",
    ROOT / "文档" / "证据" / "资料融合版本" / "V2",
    ROOT / "文档" / "证据" / "资料融合版本" / "V3",
    ROOT / "文档" / "证据" / "资料融合版本" / "V6",
    ROOT / "文档" / "证据" / "原版资料升级执行" / "首对象审查候选V5",
]
EXCLUDED_NAMES = {
    "manifest.json",
    "merge_preview.json",
    "审查报告.json",
    "backup-manifest.json",
    "changes.diff",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_sources() -> list[Path]:
    result: list[Path] = []
    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            if path.name in EXCLUDED_NAMES:
                continue
            if any(part in {"审计", "执行日志", "__pycache__", "backup-20260817T160416Z"} for part in path.parts):
                continue
            result.append(path)
    return result


def target_for(path: Path, text: str) -> str:
    counts = {name: 0 for name in TARGETS}
    tokens = {
        "动态网络.txt": ("动态网络", "dynamic", "动态连接"),
        "静态网络.txt": ("静态网络", "static", "静态连接"),
        "锚点网络.txt": ("锚点网络", "anchor", "锚点"),
        "类型系统.txt": ("类型系统", "type_system", "类型本体", "类型总表"),
        "类型连接.txt": ("类型连接", "type_connection", "类型连接"),
        "资料库.txt": ("资料库", "library", "资料库", "dependencies", "field_changes"),
    }
    for name, values in tokens.items():
        counts[name] = sum(text.count(value) for value in values)
    best = max(counts, key=counts.get)
    return best if counts[best] else "资料库.txt"


def main() -> int:
    sources = iter_sources()
    unique: list[tuple[Path, bytes, str]] = []
    seen: set[str] = set()
    for path in sources:
        data = path.read_bytes()
        digest = sha256(data)
        if digest in seen:
            continue
        seen.add(digest)
        unique.append((path, data, digest))

    BACKUP_ROOT.mkdir(parents=True, exist_ok=False)
    backup_dir = BACKUP_ROOT / "原始资料"
    shutil.copytree(ORIGINAL, backup_dir)
    records: list[dict[str, Any]] = []
    grouped: dict[str, list[tuple[Path, bytes, str]]] = {name: [] for name in TARGETS}
    for path, data, digest in unique:
        target = target_for(path, data.decode("utf-8-sig", errors="replace"))
        grouped[target].append((path, data, digest))

    for target, items in grouped.items():
        if not items:
            continue
        destination = ORIGINAL / target
        with destination.open("ab") as handle:
            for path, data, digest in items:
                relative = path.relative_to(ROOT).as_posix()
                header = (
                    f"\n\n===== 原样搬入升级资料开始 =====\n"
                    f"来源: {relative}\n"
                    f"来源SHA256: {digest}\n"
                    f"搬入时间: {datetime.now(timezone.utc).isoformat()}\n"
                    f"===== 原样搬入升级资料内容 =====\n"
                ).encode("utf-8")
                handle.write(header)
                handle.write(data)
                if not data.endswith(b"\n"):
                    handle.write(b"\n")
                handle.write("===== 原样搬入升级资料结束 =====\n".encode("utf-8"))
                records.append({"source": relative, "source_sha256": digest, "target": target, "bytes": len(data)})

    manifest = {
        "schema_version": "raw-upgrade-material-transfer-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "raw_content_append",
        "source_roots": [p.relative_to(ROOT).as_posix() for p in SOURCE_ROOTS if p.is_dir()],
        "source_file_count": len(records),
        "source_bytes": sum(r["bytes"] for r in records),
        "backup_directory": BACKUP_ROOT.relative_to(ROOT).as_posix(),
        "records": records,
    }
    manifest_path = BACKUP_ROOT / "transfer-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "applied", "source_file_count": len(records), "source_bytes": manifest["source_bytes"], "backup": str(BACKUP_ROOT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())