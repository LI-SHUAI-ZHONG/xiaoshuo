# -*- coding: utf-8 -*-
"""Produce evidence-based decisions for anchor and dynamic-network gaps.

This tool deliberately does not merge nodes or promote dynamic connections into
the static network. It records the evidence available in the source artifacts so
that a later human decision can be applied without losing provenance.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料"
DATA = ROOT / "四网络连接，剧情覆盖"
REPORTS = ROOT / "reports"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def anchor_rows() -> list[dict]:
    text = (RAW / "锚点网络.txt").read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"^\|\s*([A-Z]+\d+\.\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", re.M)
    return [
        {"id": m.group(1).strip(), "anchor_name": m.group(2).strip(),
         "content": m.group(3).strip(), "condition": m.group(4).strip(),
         "line": text.count("\n", 0, m.start()) + 1}
        for m in pattern.finditer(text)
    ]


def alias_groups(aliases: dict) -> dict[str, int]:
    result = {}
    for index, group in enumerate(aliases.get("unresolved_similar", []), 1):
        for name in group.get("names", []):
            result[name] = index
    return result


def confirm_dynamic() -> dict:
    static = load("static_connections.full.json")["connections"]
    dynamic = load("dynamic_connections.full.json")["connections"]
    aliases = load("node_aliases.json")
    static_nodes = {x["source"] for x in static} | {x["target"] for x in static}
    static_by_pair = {}
    for item in static:
        static_by_pair.setdefault((item["source"], item["target"]), []).append(item)
    groups = alias_groups(aliases)
    original = [x for x in dynamic if x.get("generated_from_static") is False]
    decisions = []
    for item in original:
        source, target = item["source"], item["target"]
        pair = static_by_pair.get((source, target), [])
        source_alias = groups.get(source)
        target_alias = groups.get(target)
        base_type = item["type"].removesuffix("链")
        same_type = [x for x in pair if x.get("type") == base_type]
        if same_type:
            decision = "confirmed_static_equivalent"
            reason = "原始动态连接的两端与静态连接完全相同，且去除动态类型后缀后类型完全相同。"
            action = "retain_dynamic_record; no_merge_needed"
        elif pair:
            decision = "conflicting_semantics"
            reason = "两端节点完全相同，但静态关系类型与动态关系类型不同。"
            action = "retain_separately; human_review_required"
        elif source_alias or target_alias:
            decision = "alias_or_granularity_unresolved"
            reason = "至少一端属于已知同编号/不同粒度别名组；编号相似不足以确认同义。"
            action = "do_not_merge; human_review_required"
        elif source in static_nodes and target in static_nodes:
            decision = "missing_static_connection"
            reason = "两端节点均在静态节点集合中，但静态 source_index 没有该连接。"
            action = "retain_dynamic_only; human_review_required"
        else:
            decision = "unresolved_endpoint"
            reason = "至少一端不在静态节点集合中，且没有可用的明确别名声明。"
            action = "retain_dynamic_only; human_review_required"
        decisions.append({
            "dynamic_id": item["id"], "source": source, "target": target,
            "type": item["type"], "base_static_type": base_type,
            "source_exact_static_node": source in static_nodes,
            "target_exact_static_node": target in static_nodes,
            "source_alias_group": source_alias, "target_alias_group": target_alias,
            "same_endpoint_static_records": len(pair),
            "same_endpoint_same_type_records": len(same_type),
            "decision": decision, "reason": reason, "action": action,
            "needs_review": decision != "confirmed_static_equivalent",
        })
    counts = Counter(x["decision"] for x in decisions)
    return {"total": len(decisions), "decision_counts": dict(counts), "connections": decisions}


def confirm_anchors() -> dict:
    rows = anchor_rows()
    text = (RAW / "锚点网络.txt").read_text(encoding="utf-8", errors="replace")
    declared = 2120
    return {
        "declared_count": declared,
        "parsed_table_rows": len(rows),
        "unique_ids": len({x["id"] for x in rows}),
        "gap": declared - len(rows),
        "declaration_evidence": "| **合计** | **约2,120** | **B级粒度** |",
        "declaration_line": next((i for i, line in enumerate(text.splitlines(), 1) if "约2,120" in line), None),
        "conclusion": "planned_or_unexpanded_template_count",
        "reason": "约2120只出现在分类汇总表；原文没有对应的330个唯一ID、名称、内容和触发条件，无法逐条证明为缺失内容。",
        "action": "do_not_create_anchor_records; human_source_confirmation_required",
        "parsed_prefix_counts": dict(Counter(re.match(r"[A-Z]+", x["id"]).group() for x in rows)),
    }


def main() -> int:
    dynamic = confirm_dynamic()
    anchors = confirm_anchors()
    result = {
        "schema_version": "network-unresolved-review-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "REVIEW_REQUIRED",
        "anchor_review": anchors,
        "dynamic_review": dynamic,
        "policy": "编号相似、同编号不同粒度、以及类型词根相似均不单独构成合并证据。",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "网络未决项逐条确认.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(REPORTS / "网络未决项逐条确认.json"), "status": result["status"], "anchors": anchors["parsed_table_rows"], "anchor_gap": anchors["gap"], "dynamic": dynamic["total"], "dynamic_decisions": dynamic["decision_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())