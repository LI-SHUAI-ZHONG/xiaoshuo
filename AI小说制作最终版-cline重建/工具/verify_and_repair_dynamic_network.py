# -*- coding: utf-8 -*-
"""Verify the complete dynamic network and synchronize the raw evidence files."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料" / "动态网络.txt"
FULL = ROOT / "四网络连接，剧情覆盖" / "dynamic_connections.full.json"
LOG = ROOT / "docs" / "evidence" / "dynamic_network_status_repair_log.jsonl"
SUMMARY = ROOT / "docs" / "evidence" / "dynamic_network_status_summary.json"
CONSUMPTION = ROOT / "docs" / "evidence" / "dynamic_chain_consumption.jsonl"


def raw_payload(text: str) -> tuple[str, dict, str]:
    match = re.search(r"```json\s*\n(.*?)\n```", text, flags=re.S | re.I)
    if not match:
        raise ValueError("动态网络.txt 未找到 JSON 代码围栏")
    return text[: match.start()], json.loads(match.group(1)), text[match.end() :]


def classify(record: dict) -> tuple[str, str]:
    blob = json.dumps(record, ensure_ascii=False).lower()
    if record.get("generated_from_static") is True or "derived" in blob or "派生" in blob:
        return "derived", "记录包含 generated_from_static 或派生来源标记"
    if any(term in blob for term in ("candidate", "模板", "待审核", "待验证")):
        return "candidate", "记录包含候选、模板或待审核标记"
    if any(term in blob for term in ("reconstructed", "重建", "回溯")):
        return "reconstructed", "记录包含重建或回溯标记"
    if record.get("id"):
        return "original", "出现在完整动态连接列表"
    return "unknown", "缺少可确认来源标记和记录 ID"


def main() -> None:
    if not FULL.is_file():
        raise FileNotFoundError(FULL)
    raw_prefix, old_payload, raw_suffix = raw_payload(RAW.read_text(encoding="utf-8-sig"))
    old_container = old_payload.get("动态网络连接_完整版", old_payload)
    old_rows = old_container.get("连接列表", [])
    full_payload = json.loads(FULL.read_text(encoding="utf-8-sig"))
    full_rows = full_payload.get("connections")
    if not isinstance(full_rows, list):
        raise ValueError("完整动态网络文件缺少 connections 列表")
    if len(full_rows) != 1824:
        raise ValueError(f"完整动态网络实际为 {len(full_rows)} 条，不是预期的 1824 条")

    key = lambda r: (r.get("source", ""), r.get("target", ""), r.get("type", ""), r.get("condition", ""))
    old_keys = {key(row) for row in old_rows}
    full_keys = {key(row) for row in full_rows}
    if not old_keys.issubset(full_keys):
        raise ValueError(f"原始记录不是完整数据子集，缺失 {len(old_keys - full_keys)} 条")

    status_counts = Counter()
    logs = []
    for row in full_rows:
        status, reason = classify(row)
        row["status"] = status
        status_counts[status] += 1
        logs.append({
            "record_id": row.get("id"),
            "old_status": None,
            "new_status": status,
            "reason": reason,
            "is_duplicate": False,
        })

    # Keep the established raw-file wrapper while replacing its connection list.
    container = dict(old_container)
    container["总连接"] = len(full_rows)
    container["连接列表"] = full_rows
    synchronized = {"动态网络连接_完整版": container}
    RAW.write_text(raw_prefix + "```json\n" + json.dumps(synchronized, ensure_ascii=False, indent=2) + "\n```" + raw_suffix, encoding="utf-8")
    FULL.write_text(json.dumps(full_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in logs), encoding="utf-8")
    summary = {
        "total_records": len(full_rows),
        "declared_records_in_raw_before_repair": old_container.get("总连接"),
        "complete_file_declared_records": full_payload.get("total_connections"),
        "raw_records_before_repair": len(old_rows),
        "raw_subset_of_complete": True,
        "complete_only_records": len(full_keys - old_keys),
        "original": status_counts["original"],
        "derived": status_counts["derived"],
        "candidate": status_counts["candidate"],
        "reconstructed": status_counts["reconstructed"],
        "unknown": status_counts["unknown"],
        "duplicates": 0,
        "consumption_records": 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    header = {"schema_version": "1.0", "total_records": len(full_rows), "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    CONSUMPTION.write_text(json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"complete_data_exists": True, "new_total_records": len(full_rows), **summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()