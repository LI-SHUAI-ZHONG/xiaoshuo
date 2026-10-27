# -*- coding: utf-8 -*-
"""Classify material-network records by callable creation stage.

Material-layer only. The output is a routing audit, not a story bible and not
chapter content. A network rule is never promoted to a story fact here.
"""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料"
DATA = ROOT / "四网络连接，剧情覆盖"
OUT = ROOT / "阶段状态" / "资料网络调用分类.json"
INDEX_OUT = ROOT / "00_资料索引" / "资料网络调用路由索引.json"

STAGES = ["直接调用", "大纲", "细纲", "情节", "待剧情筛选", "待细纲筛选", "待情节筛选", "禁止直接调用"]


def fenced_json_blocks(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    values = []
    for block in blocks:
        try:
            values.append(json.loads(block))
        except json.JSONDecodeError:
            pass
    return values


def fenced_json(path):
    """Backward-compatible first-block accessor for single-block sources."""
    values = fenced_json_blocks(path)
    return values[0] if values else None


def find_connection_list(value):
    if isinstance(value, dict):
        if isinstance(value.get("连接列表"), list):
            return value["连接列表"]
        for child in value.values():
            result = find_connection_list(child)
            if result is not None:
                return result
    elif isinstance(value, list):
        for child in value:
            result = find_connection_list(child)
            if result is not None:
                return result
    return None


def find_records(value, key):
    found = []
    if isinstance(value, dict):
        if key in value and isinstance(value[key], str):
            found.append(value)
        for child in value.values():
            found.extend(find_records(child, key))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_records(child, key))
    return found


def collect_target_edges(value, source=None, block_index=None):
    """Expand static source_index blocks into one record per source-target occurrence.

    Repeated edges are meaningful here: the same source-target pair can occur in
    different source blocks or with different original metadata. Do not collapse
    them into a set.
    """
    edges = []
    if isinstance(value, dict):
        if "targets" in value and isinstance(value["targets"], list) and source:
            for target_index, target in enumerate(value["targets"], 1):
                if isinstance(target, dict):
                    edge = dict(target)
                    edge["source"] = source
                    edge["source_index"] = source
                    edge["target_index"] = target_index
                    edge["block_index"] = block_index
                    edges.append(edge)
                elif isinstance(target, str):
                    edges.append({
                        "source": source,
                        "source_index": source,
                        "target": target,
                        "target_index": target_index,
                        "block_index": block_index,
                    })
        for key, child in value.items():
            if key not in {"targets"} and isinstance(child, (dict, list)):
                next_source = key if isinstance(child, dict) and "targets" in child else source
                edges.extend(collect_target_edges(child, next_source, block_index))
    elif isinstance(value, list):
        for child in value:
            edges.extend(collect_target_edges(child, source, block_index))
    return edges


def collect_all_static_edges(values):
    edges = []
    for block_index, value in enumerate(values, 1):
        edges.extend(collect_target_edges(value, block_index=block_index))
    return edges


def collect_static_edges_from_text(text):
    """Recover every source_index target occurrence from mixed JSON/prose text."""
    edges = []
    in_source_index = False
    source_depth = None
    source = None
    block_index = 0
    target_index = 0
    depth = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        if '"source_index"' in line:
            in_source_index = True
            source_depth = None
            source = None
            target_index = 0
            block_index += 1
        if in_source_index and source is None:
            source_match = re.match(r'^\s*"([^"]+)"\s*:\s*\{\s*$', line)
            if source_match:
                source = source_match.group(1)
                target_index = 0
        if in_source_index and source:
            target_match = re.search(
                r'"target"\s*:\s*"([^"]+)"\s*,\s*'
                r'"type"\s*:\s*"([^"]+)"\s*,\s*'
                r'"condition"\s*:\s*"([^"]+)"\s*,\s*'
                r'"priority"\s*:\s*(\d+)',
                line,
            )
            if target_match:
                target_index += 1
                edges.append({
                    "source": source,
                    "source_index": source,
                    "target": target_match.group(1),
                    "type": target_match.group(2),
                    "condition": target_match.group(3),
                    "priority": int(target_match.group(4)),
                    "block_index": block_index,
                    "target_index": target_index,
                    "source_line": line_number,
                })
        open_count = line.count("{")
        close_count = line.count("}")
        if in_source_index:
            if source_depth is None:
                source_depth = depth + 1
            depth += open_count - close_count
            if depth < source_depth:
                in_source_index = False
                source = None
        else:
            depth += open_count - close_count
    return edges


def collect_dynamic_index_refs(value):
    """Collect dynamic IDs from both reverse-index maps without duplicating IDs."""
    refs = {}
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"按来源分组", "按目标分组"} and isinstance(child, dict):
                for group, ids in child.items():
                    if isinstance(ids, list):
                        for item in ids:
                            if isinstance(item, str) and re.fullmatch(r"C\d+", item):
                                refs.setdefault(item, {"index_groups": []})["index_groups"].append({"map": key, "group": group})
            else:
                for item_id, record in collect_dynamic_index_refs(child).items():
                    refs.setdefault(item_id, {"index_groups": []})["index_groups"].extend(record["index_groups"])
    elif isinstance(value, list):
        for child in value:
            for item_id, record in collect_dynamic_index_refs(child).items():
                refs.setdefault(item_id, {"index_groups": []})["index_groups"].extend(record["index_groups"])
    return refs


def classify_dynamic(record):
    source_layer = record.get("source_layer")
    target_layer = record.get("target_layer")
    kind = record.get("type", "")
    condition = record.get("condition", "")
    # Route every parsed rule to a primary creation stage. Indexability and
    # adoption are separate: a routed rule is searchable, not automatically
    # written into a story.
    if source_layer == "引擎层" and target_layer == "引擎层":
        stage = "直接调取"
        reuse_stages = ["大纲", "分纲", "细纲", "情节"]
    elif target_layer in {"根基层", "组织层"}:
        stage = "大纲"
        reuse_stages = ["分纲", "细纲", "情节"]
    elif target_layer == "生成层" or source_layer in {"根基层", "组织层"}:
        stage = "分纲"
        reuse_stages = ["细纲", "情节"]
    elif target_layer == "执行层" or kind in {"演化链", "冲突链"}:
        stage = "细纲"
        reuse_stages = ["情节"]
    elif target_layer == "交互层":
        stage = "情节"
        reuse_stages = []
    elif target_layer in {"表达层", "读者层"}:
        stage = "正文前"
        reuse_stages = []
    else:
        stage = "待剧情筛选"
        reuse_stages = ["大纲", "分纲", "细纲", "情节"]
    return {
        "stage": stage,
        "index_access": "可检索调取",
        "callability": "stage_routed_rule",
        "reuse_stages": reuse_stages,
        "reason": "按 source_layer、target_layer 和 type 分配主阶段；调取记录不等于采用或写入剧情。",
        "required_inputs": ["confirmed_type", "story_objects", "current_states", "trigger_condition", "intended_effect"],
        "source_layer": source_layer,
        "target_layer": target_layer,
        "connection_type": kind,
        "condition": condition,
    }


def classify_type(record):
    status = str(record.get("status", ""))
    evidence = str(record.get("evidence_type", ""))
    method = str(record.get("generation_method", ""))
    if status in {"active", "confirmed"} and evidence not in {"template", "candidate"} and method != "template":
        stage = "待剧情筛选"
        callability = "conditional_only"
    else:
        stage = "禁止直接调用"
        callability = "candidate_or_template"
    return {
        "stage": stage,
        "callability": callability,
        "reason": "类型组合记录用于候选筛选；template/candidate/空 source_refs 不能作为已确认故事连接。",
        "required_inputs": ["confirmed_type", "story_core", "target_effect", "conflict_constraints"],
        "status": status,
        "evidence_type": evidence,
        "generation_method": method,
        "source_refs_count": len(record.get("source_refs", [])) if isinstance(record.get("source_refs"), list) else None,
    }


def classify_static(record):
    relation = record.get("type", "")
    target = record.get("target", "")
    if relation in {"绑定", "依赖", "包含", "组成"}:
        stage = "大纲"
    elif relation in {"触发", "共振", "演化"}:
        stage = "待细纲筛选"
    else:
        stage = "待剧情筛选"
    return {
        "stage": stage,
        "callability": "structure_rule_only",
        "reason": "静态连接说明对象依赖或触发关系，必须绑定当前故事对象后才能进入大纲或细纲。",
        "required_inputs": ["story_objects", "confirmed_type", "world_rules", "relationship_purpose"],
        "connection_type": relation,
        "target": target,
    }


def classify_anchor(row):
    name = row.group(2).strip()
    condition = row.group(4).strip()
    return {
        "stage": "待情节筛选",
        "callability": "concretization_candidate",
        "reason": "锚点只能把已选事件具体化，不能单独生成事件或角色事实。",
        "required_inputs": ["selected_event", "location_or_object", "character_state", "sensory_goal"],
        "anchor_name": name,
        "condition": condition,
    }


def main():
    dynamic_value = fenced_json(RAW / "动态网络.txt")
    dynamic = find_connection_list(dynamic_value) or []
    dynamic_by_id = {item.get("id"): item for item in dynamic if item.get("id")}
    dynamic_index = collect_dynamic_index_refs(dynamic_value)
    dynamic_records = []
    for item_id, index_info in dynamic_index.items():
        if item_id in dynamic_by_id:
            record = dict(dynamic_by_id[item_id])
            record["index_groups"] = index_info["index_groups"]
            record["record_status"] = "complete_record"
        else:
            record = {"id": item_id, "index_groups": index_info["index_groups"], "record_status": "index_reference_only"}
        dynamic_records.append(record)
    for item in dynamic:
        if item.get("id") not in dynamic_index:
            record = dict(item)
            record["record_status"] = "complete_record_not_indexed"
            dynamic_records.append(record)
    formal_dynamic_path = DATA / "dynamic_connections.full.json"
    if formal_dynamic_path.is_file():
        formal_dynamic = json.loads(formal_dynamic_path.read_text(encoding="utf-8")).get("connections", [])
        formal_by_id = {item.get("id"): item for item in formal_dynamic if item.get("id")}
        # The formal output owns canonical records. Raw reverse-index entries are
        # retained only when no canonical record exists for that ID.
        merged_dynamic = []
        for item in dynamic_records:
            item_id = item.get("id")
            if item_id in formal_by_id:
                record = dict(formal_by_id[item_id])
                record["record_status"] = "derived_rule" if record.get("generated_from_static") else "complete_record"
                merged_dynamic.append(record)
            else:
                merged_dynamic.append(item)
        known_ids = {item.get("id") for item in merged_dynamic}
        for item in formal_dynamic:
            if item.get("id") not in known_ids:
                record = dict(item)
                record["record_status"] = "derived_rule" if record.get("generated_from_static") else "complete_record"
                merged_dynamic.append(record)
        dynamic_records = merged_dynamic
    dynamic = dynamic_records
    type_value = fenced_json(RAW / "类型连接.txt")
    type_records = find_records(type_value, "dynamic_combination_id") if type_value else []
    type_text = (RAW / "类型连接.txt").read_text(encoding="utf-8", errors="replace")
    # The source contains repeated JSON blocks. Keep every declared combination
    # visible even when one large fenced block is not valid as a whole.
    type_declared = len(re.findall(r'"dynamic_combination_id"\s*:', type_text))
    if not type_records:
        type_records = [
            {"dynamic_combination_id": match.group(1), "status": "unknown", "evidence_type": "unknown", "generation_method": "unknown"}
            for match in re.finditer(r'"dynamic_combination_id"\s*:\s*"([^"]+)"', type_text)
        ]
    static_text = (RAW / "静态网络.txt").read_text(encoding="utf-8", errors="replace")
    static_values = fenced_json_blocks(RAW / "静态网络.txt")
    static_records = collect_static_edges_from_text(static_text)
    if not static_records:
        static_records = collect_all_static_edges(static_values)
    if not static_records:
        static_records = [
            {"target": match.group(1).strip(), "type": match.group(2).strip()}
            for match in re.finditer(r'"target"\s*:\s*"([^"]+)"\s*,\s*"type"\s*:\s*"([^"]+)"', static_text)
        ]
    anchor_text = (RAW / "锚点网络.txt").read_text(encoding="utf-8", errors="replace")
    anchor_matches = re.finditer(r"^\|\s*([A-Z]+\d+\.\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", anchor_text, flags=re.M)

    classified_dynamic = []
    for item in dynamic:
        record = dict(item)
        record.update({
            "relation_kind": "direct",
            "evidence_type": "source_record" if item.get("source") and item.get("target") else "index_reference",
            "derivation_path": [item.get("id")] if item.get("id") else [],
            "match_fields": [field for field in ("source", "target", "type", "condition", "effect", "priority") if item.get(field) not in (None, "")],
            "source_refs": item.get("source_refs") or [{"file": "08_原始资料/动态网络.txt", "record_id": item.get("id")}],
            "classification": classify_dynamic(item),
        })
        classified_dynamic.append(record)
    classified_type = [{"id": item.get("dynamic_combination_id"), "primary_type_id": item.get("primary_type_id"), "classification": classify_type(item)} for item in type_records]
    classified_static = []
    for index, item in enumerate(static_records, 1):
        record = dict(item)
        record.update({
            "id": f"STATIC-{index:05d}",
            "relation_kind": "direct",
            "evidence_type": "source_record",
            "derivation_path": [
                {"file": "08_原始资料/静态网络.txt", "block_index": item.get("block_index"), "source_index": item.get("source_index"), "target_index": item.get("target_index")}
            ],
            "match_fields": [field for field in ("source", "target", "type", "condition", "effect", "priority") if item.get(field) not in (None, "")],
            "source_refs": [{"file": "08_原始资料/静态网络.txt", "block_index": item.get("block_index"), "source_index": item.get("source_index"), "target_index": item.get("target_index")}],
            "record_status": "complete_edge" if item.get("source") and item.get("target") and item.get("type") and item.get("condition") else "edge_without_full_metadata",
            "classification": classify_static(item),
        })
        classified_static.append(record)
    classified_anchor = []
    for match in anchor_matches:
        classified_anchor.append({
            "id": match.group(1).strip(),
            "anchor_name": match.group(2).strip(),
            "content": match.group(3).strip(),
            "condition": match.group(4).strip(),
            "source_ref": {
                "file": "08_原始资料/锚点网络.txt",
                "line": anchor_text.count("\n", 0, match.start()) + 1,
            },
            "record_status": "complete_anchor",
            "classification": classify_anchor(match),
        })

    stage_counts = Counter()
    for item in classified_dynamic:
        stage_counts[item["classification"]["stage"]] += 1
    for item in classified_type:
        stage_counts[item["classification"]["stage"]] += 1
    for item in classified_static:
        stage_counts[item["classification"]["stage"]] += 1
    for item in classified_anchor:
        stage_counts[item["classification"]["stage"]] += 1

    all_records = (
        [{"network": "动态网络", **item} for item in classified_dynamic]
        + [{"network": "静态网络", **item} for item in classified_static]
        + [{"network": "类型连接", **item} for item in classified_type]
        + [{"network": "锚点网络", **item} for item in classified_anchor]
    )
    routes_by_stage = {stage: [] for stage in STAGES + ["分纲", "正文前"]}
    for item in all_records:
        stage = item.get("classification", {}).get("stage", "待剧情筛选")
        routes_by_stage.setdefault(stage, []).append(item)
    routes_by_network = {}
    for item in all_records:
        routes_by_network.setdefault(item["network"], []).append(item)

    issues = [
        {"id": "ROUTE-001", "severity": "critical", "finding": "现有索引只有模块级 call_when，没有记录级 stage、资格和阻断规则；因此不能按连接直接调用。"},
        {"id": "ROUTE-002", "severity": "critical", "finding": f"动态网络声明2817条，但实际索引记录为{len(dynamic)}条（完整连接{sum(1 for item in dynamic if item.get('record_status', '').startswith('complete_record'))}条、索引引用{sum(1 for item in dynamic if item.get('record_status') == 'index_reference_only')}条）；缺口没有可执行记录证据，不能补生成。"},
        {"id": "ROUTE-008", "severity": "critical", "finding": f"静态网络已纳入分类，但只能确认{len(static_records)}条结构连接；不能把静态网络声明或文本大小当成已调用数量。"},
        {"id": "ROUTE-009", "severity": "critical", "finding": f"类型连接检测到{type_declared}个dynamic_combination_id；其中无法验证完整证据的记录必须保持待筛选或禁止直接调用。"},
        {"id": "ROUTE-003", "severity": "high", "finding": "动态连接的 valid_types 覆盖全部类型，缺少项目已确认类型的筛选结果；不能据此宣称适配当前故事。"},
        {"id": "ROUTE-004", "severity": "high", "finding": "类型连接存在 template/candidate 记录和 source_refs 不足；这些只能做待筛选候选，禁止直接进入大纲或情节。"},
        {"id": "ROUTE-005", "severity": "high", "finding": "锚点缺少事件绑定和角色状态绑定时，只能作为情节具体化候选，不能反向生成剧情。"},
        {"id": "ROUTE-006", "severity": "high", "finding": "当前阶段状态没有保存一次调用的输入、命中记录、筛选理由和未采用原因，无法复核网络到剧情的链路。"},
        {"id": "ROUTE-007", "severity": "medium", "finding": "此前0.95维度覆盖率是模块维度并集，不是记录可调用率，已标记为不可用于执行决策。"},
    ]

    result = {
        "schema_version": "material-network-routing-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"included": ["00_资料索引", "08_原始资料", "阶段状态"], "excluded": ["05_正文", "章节设计", "章节状态", "项目快照"]},
        "routing_policy": {
            "index_access": "所有解析成功且有唯一 ID 的动态连接均可检索调取；这不代表全部进入剧情。",
            "direct_call": "引擎层到引擎层的规则作为资料查询直接返回，仍须检查条件。",
            "outline": "根基层/组织层连接用于大纲的世界结构、势力和长期依赖。",
            "sub_outline": "生成层连接用于分纲的阶段方向、发展和演化。",
            "detailed_outline": "执行层连接及冲突/演化链用于细纲的因果、状态与后果。",
            "plot": "交互层连接用于情节的触发、选择、对抗和转折候选。",
            "pre_text": "表达层/读者层连接用于正文前表达与效果检查。",
            "pending": "无法按层级判断的记录仍可检索，但只标为待剧情筛选，不得越级采用。",
            "connection_expansion": {
                "direct": "保留原文显式连接及每次出现记录，允许同一锚点重复连接。",
                "effect_chain": "当前不自动生成；只有存在可追溯的中间记录和明确效果字段时才允许扩展。",
                "inferred_match": "当前不自动生成；禁止仅凭名称相似、全量组合或声明数量补齐。"
            }
        },
        "inventory": {"dynamic_declared": 2817, "dynamic_detail_records": len(dynamic_by_id), "dynamic_index_records": len(dynamic), "dynamic_missing_declared": max(0, 2817 - len(dynamic)), "static_json_blocks": len(static_values), "static_edge_records": len(static_records), "type_declared": type_declared, "type_records": len(type_records), "anchor_rows": len(classified_anchor), "network_record_total": len(dynamic) + len(static_records) + len(type_records) + len(classified_anchor)},
        "stage_counts": dict(stage_counts),
        "dynamic_routing": {
            "record_count": len(classified_dynamic),
            "unique_ids": len({item["id"] for item in classified_dynamic}),
            "all_index_access": all(item["classification"].get("index_access") == "可检索调取" for item in classified_dynamic),
            "stage_count": sum(1 for item in classified_dynamic if item["classification"].get("stage")),
            "complete_record_count": sum(1 for item in classified_dynamic if item.get("record_status") == "complete_record"),
            "index_reference_only_count": sum(1 for item in classified_dynamic if item.get("record_status") == "index_reference_only"),
        },
        "connection_records": {
            "dynamic_connections": [item for item in classified_dynamic if item.get("record_status", "").startswith("complete_record")],
            "dynamic_index_reference_only": [item for item in classified_dynamic if item.get("record_status") == "index_reference_only"],
            "static_connections": classified_static,
        },
        "classified_records": {"dynamic_sample_and_all_ids": classified_dynamic, "static_records": classified_static, "type_records": classified_type, "anchor_records": classified_anchor},
        "execution_chain": [
            {"stage": "直接调取", "allowed": ["引擎层 -> 引擎层"], "output": "rule_lookup", "next": "大纲/分纲/细纲/情节"},
            {"stage": "大纲", "allowed": ["根基层/组织层动态连接", "静态依赖/绑定/组成"], "output": "story_structure_candidates", "next": "分纲"},
            {"stage": "分纲", "allowed": ["生成层动态连接"], "output": "arc_progression_candidates", "next": "细纲"},
            {"stage": "细纲", "allowed": ["执行层动态连接、冲突链、演化链"], "output": "event_causality_candidates", "next": "情节"},
            {"stage": "情节", "allowed": ["交互层动态连接"], "output": "plot_beat_candidates", "next": "正文前"},
            {"stage": "正文前", "allowed": ["表达层/读者层动态连接"], "output": "expression_effect_checks", "next": "不自动升级为剧情"},
        ],
        "issues": issues,
        "status": "record_level_routing_generated",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = {
        "schema_version": "material-network-call-index-1.0",
        "generated_at": result["generated_at"],
        "purpose": "资料网络连接按调用作用和创作阶段的统一路由索引；索引不等于剧情已采用。",
        "source_report": str(OUT),
        "record_total": len(all_records),
        "network_counts": {name: len(items) for name, items in routes_by_network.items()},
        "stage_counts": dict(stage_counts),
        "call_order": ["直接调取", "大纲", "分纲", "细纲", "情节", "正文前", "待剧情筛选", "待细纲筛选", "待情节筛选", "禁止直接调用"],
        "routes_by_stage": routes_by_stage,
        "routes_by_network": routes_by_network,
    }
    INDEX_OUT.parent.mkdir(parents=True, exist_ok=True)
    INDEX_OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "index": str(INDEX_OUT), "dynamic": len(dynamic), "static": len(static_records), "type": len(type_records), "anchors": len(classified_anchor), "total": len(all_records), "status": result["status"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()