# -*- coding: utf-8 -*-
"""Add source status and duplicate evidence to the dynamic network source."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "动态网络.txt"
LOG = ROOT / "docs" / "evidence" / "dynamic_network_status_repair_log.jsonl"
SUMMARY = ROOT / "docs" / "evidence" / "dynamic_network_status_summary.json"
CONSUMPTION = ROOT / "docs" / "evidence" / "dynamic_chain_consumption.jsonl"


def extract_fenced_json(text: str) -> tuple[str, str, str]:
    match = re.search(r"```json\s*\n(.*?)\n```", text, flags=re.S | re.I)
    if not match:
        raise ValueError("动态网络.txt 未找到完整 JSON 代码围栏")
    return text[: match.start()], match.group(1), text[match.end() :]


def source_status(record: dict) -> tuple[str, str]:
    blob = json.dumps(record, ensure_ascii=False).lower()
    if any(term in blob for term in ("derived", "派生", "generated_from_static", "来自静态网络")):
        return "derived", "记录包含派生来源标记"
    if any(term in blob for term in ("candidate", "模板", "待审核", "待验证")):
        return "candidate", "记录包含候选、模板或待审核标记"
    if any(term in blob for term in ("reconstructed", "重建", "回溯")):
        return "reconstructed", "记录包含重建或回溯标记"
    if record.get("id"):
        return "original", "出现在原始连接列表"
    return "unknown", "缺少可确认来源标记和记录 ID"


def main() -> None:
    original_text = SOURCE.read_text(encoding="utf-8-sig")
    prefix, payload_text, suffix = extract_fenced_json(original_text)
    payload = json.loads(payload_text)
    container = payload.get("动态网络连接_完整版", payload)
    records = container.get("连接列表")
    if not isinstance(records, list):
        raise ValueError("未找到动态网络连接_完整版.连接列表")

    seen: dict[tuple[str, str, str, str], str] = {}
    log_rows: list[dict] = []
    status_counts = Counter()
    duplicate_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("连接列表包含非对象记录")
        status, reason = source_status(record)
        key = (record.get("source", ""), record.get("target", ""), record.get("type", ""), record.get("condition", ""))
        is_duplicate = key in seen
        if is_duplicate:
            duplicate_count += 1
            reason += f"；与首条记录 {seen[key]} 的 source+target+type+condition 完全重复"
        else:
            seen[key] = record.get("id", "")
        record["status"] = status
        status_counts[status] += 1
        log_rows.append({
            "record_id": record.get("id"),
            "old_status": None,
            "new_status": status,
            "reason": reason,
            "is_duplicate": is_duplicate,
        })

    SOURCE.write_text(prefix + "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```" + suffix, encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in log_rows), encoding="utf-8")
    summary = {
        "total_records": len(records),
        "original": status_counts["original"],
        "derived": status_counts["derived"],
        "candidate": status_counts["candidate"],
        "reconstructed": status_counts["reconstructed"],
        "unknown": status_counts["unknown"],
        "duplicates": duplicate_count,
        "consumption_records": 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    header = {"schema_version": "1.0", "total_records": 0, "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    CONSUMPTION.write_text(json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    print(json.dumps({**summary, "repair_log": str(LOG), "summary": str(SUMMARY), "source": str(SOURCE), "consumption": str(CONSUMPTION)}, ensure_ascii=False))


if __name__ == "__main__":
    main()