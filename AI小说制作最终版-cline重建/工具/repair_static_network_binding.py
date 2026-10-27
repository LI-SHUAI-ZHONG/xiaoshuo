# -*- coding: utf-8 -*-
"""Add binding and mainline classifications to the complete static network."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料" / "静态网络.txt"
DERIVED = ROOT / "四网络连接，剧情覆盖" / "static_connections.full.json"
LOG = ROOT / "docs" / "evidence" / "static_network_binding_repair_log.jsonl"
SUMMARY = ROOT / "docs" / "evidence" / "static_network_binding_summary.json"
CONSUMPTION = ROOT / "docs" / "evidence" / "static_connection_consumption.jsonl"


def binding_type(source: str, target: str) -> tuple[str, str]:
    text = source + target
    rules = (
        ("角色", ("主角", "配角", "角色", "人物")),
        ("地点", ("世界", "地理", "地点", "区域")),
        ("势力", ("势力", "宗门", "家族", "组织")),
        ("事件", ("冲突", "事件", "转折")),
        ("概念", ("规则", "概念", "体系", "系统")),
    )
    for value, terms in rules:
        for term in terms:
            if term in source:
                return value, f"source包含'{term}'"
            if term in target:
                return value, f"target包含'{term}'"
    return "待定", "source和target均未命名匹配"


def mainline_level(source: str, target: str) -> tuple[str, str]:
    text = source + target
    for term in ("核心悬念", "核心矛盾", "主线"):
        if term in source:
            return "核心", f"source包含'{term}'"
        if term in target:
            return "核心", f"target包含'{term}'"
    for term in ("重要", "关键", "主要"):
        if term in source:
            return "重要", f"source包含'{term}'"
        if term in target:
            return "重要", f"target包含'{term}'"
    return "次要", "source和target均未命中核心或重要主线关键词"


def main() -> None:
    if not DERIVED.is_file():
        raise FileNotFoundError(f"完整静态派生文件不存在：{DERIVED}")
    payload = json.loads(DERIVED.read_text(encoding="utf-8"))
    source_index = payload.get("source_index")
    if not isinstance(source_index, dict):
        raise ValueError("static_connections.full.json 缺少 source_index")

    rows = []
    for source, block in source_index.items():
        for target_record in block.get("targets", []):
            target_record["source"] = source
            rows.append(target_record)
    if len(rows) != 1341:
        raise ValueError(f"完整静态连接数为 {len(rows)}，不是预期的 1341")

    binding_counts = Counter()
    level_counts = Counter()
    logs = []
    for number, record in enumerate(rows, 1):
        source = record["source"]
        target = record.get("target", "")
        binding, binding_reason = binding_type(source, target)
        level, level_reason = mainline_level(source, target)
        record["binding_type"] = binding
        record["mainline_level"] = level
        binding_counts[binding] += 1
        level_counts[level] += 1
        logs.append({
            "edge_id": f"STATIC-{number:03d}",
            "source": source,
            "target": target,
            "old_binding_type": None,
            "new_binding_type": binding,
            "old_mainline_level": None,
            "new_mainline_level": level,
            "source_rule": f"{binding_reason}；{level_reason}",
        })

    # The raw file is the runtime source; keep the complete generated network in sync.
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DERIVED.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in logs), encoding="utf-8")
    summary = {
        "total_connections": len(rows),
        "binding_type_distribution": {key: binding_counts[key] for key in ("角色", "地点", "势力", "事件", "概念", "待定")},
        "mainline_level_distribution": {key: level_counts[key] for key in ("核心", "重要", "次要")},
        "consumption_records": 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    header = {"schema_version": "1.0", "total_records": 0, "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    CONSUMPTION.write_text(json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "repair_log": str(LOG), "summary": str(SUMMARY), "source": str(RAW)}, ensure_ascii=False))


if __name__ == "__main__":
    main()