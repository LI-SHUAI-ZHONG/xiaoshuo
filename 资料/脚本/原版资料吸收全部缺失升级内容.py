from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "原始资料"
BASELINE = ROOT / "文档" / "合并升级" / "raw-material-transfer-20260818T051048Z" / "原始资料"
RUN = ROOT / "文档" / "合并升级" / f"material-absorption-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
TARGETS = ("资料库.txt", "静态网络.txt", "动态网络.txt", "锚点网络.txt", "类型系统.txt", "类型连接.txt")
SOURCE_ROOTS = (
    ROOT / "文档" / "资料融合工作区" / "输入冻结V1" / "严格升级批次",
    ROOT / "文档" / "归档" / "2026-08-17_历史运行与废弃资料" / "正文" / "全量资料升级" / "批次",
    ROOT / "文档" / "证据" / "全量资料升级派生定位",
    ROOT / "文档" / "证据" / "全量资料增量升级" / "20260817T061417Z-c75fb8a7",
    ROOT / "文档" / "证据" / "资料融合版本" / "V2",
    ROOT / "文档" / "证据" / "资料融合版本" / "V3",
    ROOT / "文档" / "证据" / "资料融合版本" / "V6",
    ROOT / "文档" / "证据" / "原版资料升级执行" / "首对象审查候选V5",
)
EXTENSIONS = {".json", ".jsonl", ".md", ".txt"}
EXCLUDED_NAMES = {"manifest.json", "merge_preview.json", "审查报告.json", "backup-manifest.json", "changes.diff", "pending_evidence.jsonl", "unresolved_conflicts.jsonl"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def target_for(path: Path, text: str) -> str:
    value = f"{path.as_posix()}\n{text}"
    scores = {
        "动态网络.txt": ("动态网络", "dynamic", "动态连接", "dynamic_rule"),
        "静态网络.txt": ("静态网络", "static", "静态连接", "static_relation"),
        "锚点网络.txt": ("锚点网络", "anchor", "锚点网络", "anchor_id"),
        "类型系统.txt": ("类型系统", "type_system", "类型本体", "类型总表", "type_id"),
        "类型连接.txt": ("类型连接", "type_connection", "类型组合", "dynamic_combination_id", "connection_id"),
        "资料库.txt": ("资料库", "library", "资料库", "dependencies", "entry_id"),
    }
    counts = {target: sum(value.count(token) for token in tokens) for target, tokens in scores.items()}
    best = max(counts, key=counts.get)
    return best if counts[best] else "资料库.txt"


def source_files() -> list[Path]:
    paths: list[Path] = []
    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in EXTENSIONS and path.name not in EXCLUDED_NAMES:
                paths.append(path)
    return paths


def main() -> int:
    if not BASELINE.is_dir():
        raise FileNotFoundError(f"缺少第一次搬运前的原版基线备份: {BASELINE}")
    RUN.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ORIGINAL, RUN / "当前资料备份")

    baseline_text = {target: (BASELINE / target).read_text(encoding="utf-8-sig") for target in TARGETS}
    grouped: dict[str, list[tuple[Path, bytes, str]]] = defaultdict(list)
    seen: set[str] = set()
    records: list[dict[str, object]] = []

    for path in source_files():
        data = path.read_bytes()
        file_hash = digest(data)
        relative = path.relative_to(ROOT).as_posix()
        target = target_for(path, data.decode("utf-8-sig", errors="replace"))
        if file_hash in seen:
            records.append({"source": relative, "sha256": file_hash, "target": target, "action": "deduplicated_same_source_content"})
            continue
        seen.add(file_hash)
        text = data.decode("utf-8-sig", errors="replace")
        if text and text in baseline_text[target]:
            records.append({"source": relative, "sha256": file_hash, "target": target, "action": "already_present_in_original_baseline", "bytes": len(data)})
            continue
        grouped[target].append((path, data, file_hash))
        records.append({"source": relative, "sha256": file_hash, "target": target, "action": "absorbed_missing_content", "bytes": len(data)})

    for target in TARGETS:
        destination = ORIGINAL / target
        destination.write_text(baseline_text[target], encoding="utf-8")
        with destination.open("ab") as handle:
            for path, data, file_hash in grouped[target]:
                relative = path.relative_to(ROOT).as_posix()
                method = path.stem or path.name
                header = (
                    "\n\n===== 缺失升级资料吸收开始 =====\n"
                    f"升级方法/资料格式: {method}\n"
                    f"来源: {relative}\n"
                    f"来源SHA256: {file_hash}\n"
                    "===== 升级资料完整内容 =====\n"
                ).encode("utf-8")
                handle.write(header + data)
                if not data.endswith(b"\n"):
                    handle.write(b"\n")
                handle.write("===== 缺失升级资料吸收结束 =====\n".encode("utf-8"))

    manifest = {
        "schema_version": "original-material-missing-upgrade-absorption-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": str(BASELINE.relative_to(ROOT)).replace("\\", "/"),
        "source_roots": [path.relative_to(ROOT).as_posix() for path in SOURCE_ROOTS if path.is_dir()],
        "source_file_count": len(records),
        "absorbed_count": sum(record["action"] == "absorbed_missing_content" for record in records),
        "already_present_count": sum(record["action"] == "already_present_in_original_baseline" for record in records),
        "deduplicated_count": sum(record["action"] == "deduplicated_same_source_content" for record in records),
        "target_counts": {target: sum(record["action"] == "absorbed_missing_content" and record["target"] == target for record in records) for target in TARGETS},
        "records": records,
        "after_sha256": {target: digest((ORIGINAL / target).read_bytes()) for target in TARGETS},
    }
    (RUN / "absorption-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "applied", "absorbed_count": manifest["absorbed_count"], "already_present_count": manifest["already_present_count"], "deduplicated_count": manifest["deduplicated_count"], "target_counts": manifest["target_counts"], "run": str(RUN)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())