# -*- coding: utf-8 -*-
"""Generate static and dynamic network packages from the all-effective-pairs rule.

The requested rule is deliberately broad: every distinct ordered pair of nodes
is a possible connection because every pair can produce at least one structural,
state, or plot effect. Existing static/dynamic records are used only to retain
their richer metadata; source files are never modified.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = Path(r"D:\AI小说创作系统\AI小说制作最终版")
NODES_PATH = LEGACY / "静态网络" / "静态节点.json"
STATIC_PATH = LEGACY / "静态网络" / "静态连接.json"
DYNAMIC_PATH = LEGACY / "动态网络" / "已确认动态连接.json"
OUT = ROOT / "阶段状态" / "三网络全效果生成"
BATCH_SIZE = 5000
VALID_TYPES = ["玄幻", "仙侠", "都市", "科幻", "悬疑", "言情", "历史", "军事", "游戏", "体育", "灵异", "同人", "二次元", "耽美", "轻小说"]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def node_layer(node):
    block = str(node.get("block", ""))
    match = re.match(r"(\d+)", block)
    number = int(match.group(1)) if match else 0
    if number <= 4:
        return "引擎层"
    if number <= 10:
        return "组织层"
    if number <= 16:
        return "生成层"
    if number <= 23:
        return "执行层"
    if number <= 27:
        return "交互层"
    return "表达层"


def relation_for(source, target):
    source_block = str(source.get("block", ""))
    target_block = str(target.get("block", ""))
    source_match = re.match(r"(\d+)", source_block)
    target_match = re.match(r"(\d+)", target_block)
    source_no = int(source_match.group(1)) if source_match else 0
    target_no = int(target_match.group(1)) if target_match else 0
    if source_no == target_no:
        return "共振链", "同一板块内的节点相互增强"
    if source_no < target_no:
        return "触发链", "来源节点产生状态或结构变化，激活目标节点"
    return "转化链", "来源节点的变化向目标节点传递并形成新的效果"


def strength_for(relation):
    return {"共振链": "中", "触发链": "强", "转化链": "中"}[relation]


def make_static(source, target, existing):
    key = (source["original_name"], target["original_name"])
    if key in existing:
        record = dict(existing[key])
        record["generation_method"] = "source_preserved"
        record["record_status"] = "confirmed_source"
        return record
    relation, effect = relation_for(source, target)
    return {
        "connection_id": None,
        "source": source["original_name"],
        "source_internal_id": source["internal_id"],
        "target": target["original_name"],
        "target_internal_id": target["internal_id"],
        "connection_type": relation,
        "condition": "源节点与目标节点同时进入当前场景",
        "effect": effect,
        "priority": 1 if relation == "触发链" else 2,
        "scope": "全量候选",
        "block": source.get("block", ""),
        "generation_method": "all_effective_pairs",
        "record_status": "generated_rule",
    }


def make_dynamic(static_record, source, target, dynamic_existing):
    key = (source["original_name"], target["original_name"])
    original = dynamic_existing.get(key)
    if original:
        record = dict(original)
        record["generation_method"] = "source_preserved"
        record["record_status"] = "confirmed_source"
        return record
    relation = static_record["connection_type"]
    return {
        "id": None,
        "source": source["original_name"],
        "source_layer": node_layer(source),
        "target": target["original_name"],
        "target_layer": node_layer(target),
        "type": relation,
        "direction": "单向",
        "strength": strength_for(relation),
        "condition": static_record["condition"],
        "valid_types": VALID_TYPES,
        "priority": static_record["priority"],
        "effect": static_record["effect"],
        "generation_method": "all_effective_pairs",
        "record_status": "generated_rule",
    }


def write_batches(name, records):
    paths = []
    for batch_number, offset in enumerate(range(0, len(records), BATCH_SIZE), 1):
        batch = records[offset:offset + BATCH_SIZE]
        path = OUT / f"{name}_批次{batch_number:04d}.json"
        path.write_text(json.dumps({"batch_number": batch_number, "records": batch}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(str(path.relative_to(ROOT)))
    return paths


def main():
    nodes = load_json(NODES_PATH)["nodes"]
    static_source = load_json(STATIC_PATH)["connections"]
    dynamic_source = load_json(DYNAMIC_PATH)["规则列表"]
    static_existing = {(x.get("source"), x.get("target")): x for x in static_source}
    dynamic_existing = {(x.get("原始起点"), x.get("原始终点")): {
        "id": x.get("规则ID"), "source": x.get("原始起点"), "source_layer": x.get("起点层级"),
        "target": x.get("原始终点"), "target_layer": x.get("终点层级"), "type": x.get("关系类型"),
        "direction": x.get("方向"), "strength": x.get("强度"), "condition": x.get("自然语言条件"),
        "valid_types": x.get("适用类型", VALID_TYPES), "priority": x.get("优先级"), "effect": x.get("效果说明"),
    } for x in dynamic_source if x.get("原始起点") and x.get("原始终点") not in {None, "未知"}}
    static_records = []
    dynamic_records = []
    for source in nodes:
        for target in nodes:
            if source["internal_id"] == target["internal_id"]:
                continue
            static = make_static(source, target, static_existing)
            static["connection_id"] = f"S{len(static_records) + 1:06d}"
            dynamic = make_dynamic(static, source, target, dynamic_existing)
            dynamic["id"] = dynamic.get("id") or f"D{len(dynamic_records) + 1:06d}"
            static_records.append(static)
            dynamic_records.append(dynamic)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "all-effective-pairs-network-package-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rule": "所有不同节点的有向组合均视为可产生效果，因此全部建立连接；同节点自环排除。",
        "node_count": len(nodes),
        "expected_connection_count": len(nodes) * (len(nodes) - 1),
        "static_connection_count": len(static_records),
        "dynamic_connection_count": len(dynamic_records),
        "static_batches": write_batches("静态网络连接", static_records),
        "dynamic_batches": write_batches("动态网络连接", dynamic_records),
        "dynamic_runtime": {"max_hops": 3, "max_candidates_per_scene": 5, "max_state_updates": 12, "cycle_guard": "visited_nodes"},
        "status": "generated_all_effective_pairs",
    }
    (OUT / "三网络全效果生成总包.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()