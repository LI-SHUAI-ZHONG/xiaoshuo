from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "原始资料"
INPUT = ROOT / "文档" / "归档" / "2026-08-17_历史运行与废弃资料" / "证据" / "严格资料升级" / "严格资料升级档案.jsonl"
RUN = ROOT / "文档" / "合并升级" / f"strict-record-transfer-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
TARGETS = {
    "资料库": "资料库.txt",
    "静态网络": "静态网络.txt",
    "动态网络": "动态网络.txt",
    "锚点网络": "锚点网络.txt",
    "类型系统": "类型系统.txt",
    "类型连接": "类型连接.txt",
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_for(record: dict) -> str:
    kind = str(record.get("source_kind") or "")
    for key, target in TARGETS.items():
        if key in kind:
            return target
    ref = json.dumps(record, ensure_ascii=False)
    for key, target in TARGETS.items():
        if key in ref:
            return target
    return "资料库.txt"


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=False)
    backup = RUN / "原始资料"
    shutil.copytree(ORIGINAL, backup)
    grouped: dict[str, list[dict]] = {target: [] for target in TARGETS.values()}
    with INPUT.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{INPUT}:{line_number} 必须是 JSON 对象")
            record["transfer_source_line"] = line_number
            grouped[target_for(record)].append(record)

    records = []
    for target, items in grouped.items():
        if not items:
            continue
        destination = ORIGINAL / target
        with destination.open("ab") as handle:
            for record in items:
                payload = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
                upgrade_id = record.get("upgrade_id", f"line-{record['transfer_source_line']}")
                header = (
                    "\n\n===== 严格升级记录原样搬入开始 =====\n"
                    f"upgrade_id: {upgrade_id}\n"
                    f"source_kind: {record.get('source_kind', '')}\n"
                    f"source_ref: {record.get('source_ref', '')}\n"
                    "===== 严格升级记录内容(JSON) =====\n"
                ).encode("utf-8")
                handle.write(header + payload + "\n===== 严格升级记录原样搬入结束 =====\n".encode("utf-8"))
                records.append({"upgrade_id": upgrade_id, "target": target, "source_line": record["transfer_source_line"], "bytes": len(payload)})

    manifest = {
        "schema_version": "strict-upgrade-record-transfer-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(INPUT.relative_to(ROOT)).replace("\\", "/"),
        "record_count": len(records),
        "record_bytes": sum(item["bytes"] for item in records),
        "backup_directory": str(backup.relative_to(ROOT)).replace("\\", "/"),
        "targets": {target: sum(1 for item in records if item["target"] == target) for target in TARGETS.values()},
        "records": records,
        "before_sha256": {name: file_sha256(backup / name) for name in TARGETS.values()},
        "after_sha256": {name: file_sha256(ORIGINAL / name) for name in TARGETS.values()},
    }
    (RUN / "transfer-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "applied", "record_count": len(records), "targets": manifest["targets"], "run": str(RUN)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())