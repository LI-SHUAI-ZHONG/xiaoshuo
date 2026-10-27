from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "原始资料"
STRICT = ROOT / "文档" / "归档" / "2026-08-17_历史运行与废弃资料" / "证据" / "严格资料升级" / "严格资料升级档案.jsonl"
INCREMENTAL = ROOT / "文档" / "证据" / "全量资料增量升级" / "20260817T061417Z-c75fb8a7" / "changes.jsonl"
OVERLAY = ROOT / "文档" / "证据" / "资料融合版本" / "V3" / "validated_overlay.jsonl"
EXECUTION = ROOT / "文档" / "证据" / "原版资料升级执行" / "首对象审查候选V5" / "upgrade_records.jsonl"
RECOVERABLE = ROOT / "文档" / "证据" / "升级成果追溯审计" / "可融合升级成果.jsonl"
RUN = ROOT / "文档" / "合并升级" / f"classified-upgrade-transfer-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
TARGETS = ("资料库.txt", "静态网络.txt", "动态网络.txt", "锚点网络.txt", "类型系统.txt", "类型连接.txt")


def read_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number} 不是 JSON 对象")
                yield line_number, value


def target_from_kind(kind: Any) -> str | None:
    value = str(kind or "")
    for token, target in (("资料库", "资料库.txt"), ("静态网络", "静态网络.txt"), ("动态网络", "动态网络.txt"), ("锚点网络", "锚点网络.txt"), ("类型系统", "类型系统.txt"), ("类型连接", "类型连接.txt")):
        if token in value:
            return target
    return None


def target_from_text(value: Any) -> str | None:
    text = json.dumps(value, ensure_ascii=False)
    return target_from_kind(text)


def binding_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "binding_id" and isinstance(item, str):
                found.add(item)
            elif key == "binding_ids" and isinstance(item, list):
                found.update(item for item in item if isinstance(item, str))
            found.update(binding_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(binding_ids(item))
    return found


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(items: dict[str, list[dict[str, Any]]], targets: set[str], method: str, record_format: str, status: Any, source: Path, line: int, target_basis: str, payload: dict[str, Any]) -> None:
    for target in sorted(targets):
        items[target].append({
            "upgrade_method": method,
            "record_format": record_format,
            "status": status,
            "source": source.relative_to(ROOT).as_posix(),
            "source_line": line,
            "target_basis": target_basis,
            "payload": payload,
        })


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ORIGINAL, RUN / "原始资料")
    items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    binding_targets: dict[str, str] = {}

    for line, record in read_jsonl(STRICT):
        target = target_from_kind(record.get("source_kind")) or "资料库.txt"
        if isinstance(record.get("binding_id"), str):
            binding_targets[record["binding_id"]] = target
        add(items, {target}, "严格来源升级", record.get("schema_version", "strict-source-upgrade-record"), record.get("status"), STRICT, line, "source_kind", record)

    for line, record in read_jsonl(INCREMENTAL):
        target = binding_targets.get(record.get("binding_id"), target_from_text(record) or "资料库.txt")
        add(items, {target}, "全量资料增量升级", "full-source-material-incremental-upgrade-1.0/change", record.get("category"), INCREMENTAL, line, "binding_id -> 严格升级来源类型", record)

    for line, record in read_jsonl(OVERLAY):
        add(items, {"资料库.txt"}, "同源派生字段级融合", "original-upgrade-material-field-fusion-1.0/validated_overlay", record.get("status"), OVERLAY, line, "V3 基线为资料库", record)

    for line, record in read_jsonl(EXECUTION):
        target = target_from_text(record.get("source_file")) or target_from_text(record.get("original_object_id")) or "资料库.txt"
        add(items, {target}, "原始资料对象升级执行", record.get("schema_version", "original-material-upgrade-execution"), record.get("status"), EXECUTION, line, "source_file/original_object_id", record)

    for line, record in read_jsonl(RECOVERABLE):
        ids = binding_ids(record)
        targets = {binding_targets[item] for item in ids if item in binding_targets}
        if not targets:
            target = target_from_kind(record.get("source_kind")) or target_from_text(record.get("source_ref")) or target_from_text(record.get("content")) or "资料库.txt"
            targets = {target}
            basis = "source_kind/source_ref/content 文本"
        else:
            basis = "content 内 binding_id -> 严格升级来源类型"
        add(items, targets, "升级成果追溯可恢复修订", "material-upgrade-artifact-trace-audit-1.0/recoverable_material_revision", record.get("classification"), RECOVERABLE, line, basis, record)

    records: list[dict[str, Any]] = []
    for target in TARGETS:
        destination = ORIGINAL / target
        with destination.open("ab") as handle:
            for index, item in enumerate(items[target], 1):
                payload = json.dumps(item["payload"], ensure_ascii=False, sort_keys=True, indent=2)
                header = (
                    "\n\n===== 分类升级资料开始 =====\n"
                    f"升级方法: {item['upgrade_method']}\n"
                    f"资料格式: {item['record_format']}\n"
                    f"处理状态: {item['status']}\n"
                    f"原始来源: {item['source']}:{item['source_line']}\n"
                    f"目标依据: {item['target_basis']}\n"
                    "===== 原始升级内容(JSON) =====\n"
                )
                handle.write((header + payload + "\n===== 分类升级资料结束 =====\n").encode("utf-8"))
                records.append({"target": target, "sequence": index, **{key: item[key] for key in ("upgrade_method", "record_format", "status", "source", "source_line", "target_basis")}, "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest()})

    manifest = {
        "schema_version": "classified-upgrade-material-transfer-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backup_directory": str((RUN / "原始资料").relative_to(ROOT)).replace("\\", "/"),
        "record_count": len(records),
        "method_counts": dict(Counter(record["upgrade_method"] for record in records)),
        "target_counts": dict(Counter(record["target"] for record in records)),
        "status_counts": dict(Counter(str(record["status"]) for record in records)),
        "records": records,
        "after_sha256": {target: sha256(ORIGINAL / target) for target in TARGETS},
    }
    (RUN / "transfer-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "applied", "record_count": len(records), "method_counts": manifest["method_counts"], "target_counts": manifest["target_counts"], "run": str(RUN)}, ensure_ascii=False))


if __name__ == "__main__":
    main()