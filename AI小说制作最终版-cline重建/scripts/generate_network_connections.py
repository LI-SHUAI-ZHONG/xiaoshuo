# -*- coding: utf-8 -*-
"""Parse, normalize, merge, and index the static and dynamic network files."""
from __future__ import annotations

import json
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料"
DATA = ROOT / "四网络连接，剧情覆盖"
REPORTS = ROOT / "reports"
STATIC_INPUT = RAW / "静态网络.txt"
DYNAMIC_INPUT = RAW / "动态网络.txt"
PRIORITIES = {1, 2, 3, 4}
DEFAULT_DYNAMIC = {
    "direction": "单向",
    "strength": "中",
    "valid_types": [],
    "source_layer": "未分类",
    "target_layer": "未分类",
}
DERIVED_VALID_TYPES = ["玄幻", "仙侠", "科幻", "游戏", "军事", "悬疑", "都市", "历史", "言情", "奇幻"]
DERIVED_RELATION_EFFECTS = {
    "绑定": "当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。",
    "嵌套": "当起点成立时，终点作为起点的一部分参与当前状态。",
    "触发": "当起点条件成立时，推动终点进入下一状态。",
    "约束": "当起点成立时，限制终点可采取的状态或行为范围。",
    "演化": "当起点持续或变化时，推动终点按阶段发生状态变化。",
    "共振": "当起点与终点同时成立时，放大双方的共同状态。",
    "驱动": "当起点成立时，为终点状态变化提供驱动力。",
    "输出": "当起点完成处理时，将其状态结果传递给终点。",
    "冲突": "当起点与终点同时成立时，产生需要处理的状态冲突。",
    "抑制": "当起点成立时，降低终点状态的强度或可见性。",
    "解决": "当起点成立并完成作用时，推动终点的问题状态收敛。",
    "扭曲": "当起点成立时，改变终点状态的解释或表现方式。",
    "映射": "当起点成立时，将起点状态映射为终点状态。",
    "转化": "当起点成立并满足转化条件时，将起点状态转为终点状态。",
}


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with open(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        Path(name).replace(path)
    finally:
        temporary = Path(name)
        if temporary.exists():
            temporary.unlink()


def _balanced_json_values(text: str) -> list[object]:
    decoder = json.JSONDecoder()
    values = []
    index = 0
    while index < len(text):
        match = re.search(r"[\[{]", text[index:])
        if not match:
            break
        start = index + match.start()
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        values.append(value)
        index = start + end
    return values


def parse_json_wrapped(path: Path) -> list[object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```\s*$", "", text)
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        return _balanced_json_values(text)


def _source_indexes(value: object) -> list[dict]:
    found = []
    if isinstance(value, dict):
        if isinstance(value.get("source_index"), dict):
            found.append(value["source_index"])
        for child in value.values():
            found.extend(_source_indexes(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_source_indexes(child))
    return found


def _as_priority(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 4
    return number if number in PRIORITIES else 4


def parse_static(path: Path = STATIC_INPUT) -> tuple[list[dict], int]:
    values = parse_json_wrapped(path)
    indexes = []
    for value in values:
        indexes.extend(_source_indexes(value))
    merged: dict[str, dict] = {}
    for source_index in indexes:
        for source, entry in source_index.items():
            target_list = entry.get("targets", []) if isinstance(entry, dict) else []
            bucket = merged.setdefault(source, {})
            for target in target_list:
                if isinstance(target, str):
                    target = {"target": target}
                if not isinstance(target, dict) or not target.get("target"):
                    continue
                record = {
                    "source": source,
                    "target": str(target["target"]).strip(),
                    "type": str(target.get("type", "")).strip(),
                    "condition": str(target.get("condition", "")).strip(),
                    "priority": _as_priority(target.get("priority")),
                }
                key = (record["target"], record["type"], record["condition"])
                old = bucket.get(key)
                if old is None or record["priority"] < old["priority"]:
                    bucket[key] = record
    records = []
    for source, bucket in merged.items():
        records.extend(bucket.values())
    records.sort(key=lambda x: (x["source"], x["priority"], x["target"], x["type"]))
    return records, len(indexes)


def find_connection_lists(value: object) -> list[list[dict]]:
    found = []
    if isinstance(value, dict):
        for key in ("连接列表", "connections", "规则列表"):
            if isinstance(value.get(key), list):
                found.append(value[key])
        for key, child in value.items():
            if key in {"连接列表", "connections", "规则列表"}:
                continue
            found.extend(find_connection_lists(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_connection_lists(child))
    return found


def normalize_dynamic(record: dict) -> dict | None:
    source = record.get("source", record.get("原始起点"))
    target = record.get("target", record.get("原始终点"))
    kind = record.get("type", record.get("关系类型"))
    if not source or not target or target == "未知":
        return None
    return {
        "id": record.get("id", record.get("规则ID", "")),
        "source": str(source).strip(),
        "source_layer": record.get("source_layer", record.get("起点层级", "未分类")),
        "target": str(target).strip(),
        "target_layer": record.get("target_layer", record.get("终点层级", "未分类")),
        "type": str(kind or "").strip(),
        "direction": record.get("direction", record.get("方向", "单向")),
        "strength": record.get("strength", record.get("强度", "中")),
        "condition": record.get("condition", record.get("自然语言条件", "")),
        "valid_types": record.get("valid_types", record.get("适用类型", [])) or [],
        "priority": _as_priority(record.get("priority", record.get("优先级"))),
        "effect": record.get("effect", record.get("效果说明", "")),
        "generated_from_static": False,
        "needs_review": False,
    }


def parse_dynamic(path: Path = DYNAMIC_INPUT) -> list[dict]:
    records = []
    for value in parse_json_wrapped(path):
        for connection_list in find_connection_lists(value):
            records.extend(normalize_dynamic(item) for item in connection_list if isinstance(item, dict))
    return [item for item in records if item]


def normalized_name(name: str) -> str:
    name = name.strip().replace("＂", '"').replace("＿", "_").replace("－", "-")
    return re.sub(r"[\s\u3000]+", " ", name)


def build_aliases(names: set[str]) -> dict:
    exact = {name: normalized_name(name) for name in sorted(names) if normalized_name(name) != name}
    groups = defaultdict(list)
    for name in names:
        match = re.match(r"^(\d+(?:\.\d+)?)_", name)
        if match:
            groups[match.group(1)].append(name)
    unresolved = [
        {"names": sorted(group), "reason": "同编号但粒度不同，不能自动合并"}
        for group in groups.values() if len(set(group)) > 1
    ]
    return {"exact_alias": exact, "unresolved_similar": unresolved}


def numeric_prefix(name: str) -> str:
    match = re.match(r"^(\d+(?:\.\d+)?)_", name)
    return match.group(1) if match else ""


def classify_dynamic_only(item, static_records, aliases):
    static_names = {x["source"] for x in static_records} | {x["target"] for x in static_records}
    static_keys = {(x["source"], x["target"], x["type"]) for x in static_records}
    source, target, kind = item["source"], item["target"], item["type"]
    normalized_alias = aliases.get("exact_alias", {})
    ns = normalized_alias.get(source, normalized_name(source))
    nt = normalized_alias.get(target, normalized_name(target))
    normalized_keys = {(normalized_alias.get(x["source"], normalized_name(x["source"])), normalized_alias.get(x["target"], normalized_name(x["target"])), x["type"]) for x in static_records}
    if (ns, nt, kind) in normalized_keys:
        return "confirmed_alias_match", "source/target 规范化后与静态 source-target-type 完全匹配"
    same_pair = {(x["source"], x["target"]): x for x in static_records}
    if (source, target) in same_pair:
        return "conflicting_semantics", "静态存在相同 source-target，但关系类型不同"
    similar_names = [name for name in static_names if name in {source, target} or (numeric_prefix(name) and numeric_prefix(name) in {numeric_prefix(source), numeric_prefix(target)})]
    if similar_names and (source not in static_names or target not in static_names):
        return "likely_alias_match", "节点编号或粒度与静态节点相近，但不能确认同义"
    if source in static_names and target in static_names and item.get("condition") and item.get("effect"):
        return "missing_static_connection", "两端节点和动态语义字段明确，但静态 source_index 没有该连接"
    return "invalid_or_unclear", "未找到可确认的静态对应关系，且无法从现有资料确定语义"


def make_file_inventory():
    rows = [
        "# File Inventory", "", "Generated from an actual scan of the project root.", "",
        "| Path | Type | Original | Formal output | Used by scripts | Actual connections | Version | Duplicate/conflict | Adoption reason |",
        "|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    # The inventory describes the network pipeline. Avoid recursively reading the
    # multi-hundred-MB source library and unrelated project artifacts here.
    scan_dirs = [RAW, DATA, REPORTS, ROOT / "scripts", ROOT / "tests"]
    candidates = []
    for directory in scan_dirs:
        if directory.is_dir():
            candidates.extend(p for p in directory.iterdir() if p.is_file())
    candidates = sorted(set(candidates))
    for path in candidates:
        rel = path.relative_to(ROOT).as_posix()
        if not (any(token in path.name.lower() for token in ("static", "dynamic", "connection", "静态网络", "动态网络")) or path.parent.name in {"scripts", "tests", "data", "reports", "08_原始资料"}):
            continue
        kind = path.suffix.lower().lstrip(".") or "file"
        original = "是" if "08_原始资料" in path.parts else "否"
        formal = "是" if path.parent.name in {"data", "scripts", "reports", "tests"} else "否"
        used = "是" if path.name in {"静态网络.txt", "动态网络.txt"} or path.parent.name in {"scripts", "tests"} else "否"
        actual = "未扫描"
        version = "未知"
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                value = json.loads(text)
                version = str(value.get("version", "未知")) if isinstance(value, dict) else "未知"
                if isinstance(value, dict):
                    if isinstance(value.get("connections"), list): actual = str(len(value["connections"]))
                    elif isinstance(value.get("连接列表"), list): actual = str(len(value["连接列表"]))
            else:
                actual = "含 source_index，按解析脚本统计" if "source_index" in text else "不适用"
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            actual = "解析失败"
        reason = "正式输入/输出" if formal or original else "项目文件，保留供比对"
        rows.append(f"| `{rel}` | {kind} | {original} | {formal} | {used} | {actual} | {version} | 未发现同名正式冲突 | {reason} |")
    (REPORTS / "file_inventory.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_outputs() -> dict:
    static, static_blocks = parse_static()
    dynamic_original = parse_dynamic()
    static_by_key = {(x["source"], x["target"], x["type"]): x for x in static}
    dynamic_by_key = {}
    conflicts = []
    old_ids = {}
    for item in dynamic_original:
        key = (item["source"], item["target"], item["type"])
        old_ids.setdefault(key, []).append(item["id"])
        if key in dynamic_by_key:
            if dynamic_by_key[key] != item:
                conflicts.append({"key": list(key), "reason": "同一 source-target-type 字段冲突"})
            continue
        dynamic_by_key[key] = item
    generated = []
    mapping = []
    for key, static_record in sorted(static_by_key.items()):
        if key in dynamic_by_key:
            continue
        generated.append({
            **DEFAULT_DYNAMIC,
            "source": static_record["source"],
            "target": static_record["target"],
            "type": static_record["type"],
            "condition": f"{static_record['condition']}；且当前故事明确采用该静态关系",
            "priority": static_record["priority"],
            "effect": DERIVED_RELATION_EFFECTS.get(static_record["type"], "按该静态关系类型更新终点状态。"),
            "valid_types": list(DERIVED_VALID_TYPES),
            "generated_from_static": True,
            "needs_review": False,
            "validation_status": "derived_contract_validated",
            "derivation_contract": "NET-DYNAMIC-DERIVATION-CONTRACT-1.0",
        })
    all_dynamic = list(dynamic_by_key.values()) + generated
    all_dynamic.sort(key=lambda x: (x["source"], x["priority"], x["target"], x["type"]))
    aliases = build_aliases({x["source"] for x in static} | {x["target"] for x in static} | {x["source"] for x in all_dynamic} | {x["target"] for x in all_dynamic})
    for item in all_dynamic:
        item["original_source"] = item["source"]
        item["original_target"] = item["target"]
        item["normalized_source"] = aliases["exact_alias"].get(item["source"], normalized_name(item["source"]))
        item["normalized_target"] = aliases["exact_alias"].get(item["target"], normalized_name(item["target"]))
        if item.get("generated_from_static"):
            item["field_source"] = {
                "direction": "明确默认规则: direction=单向",
                "strength": "明确默认规则: strength=中",
                "valid_types": "NET-DYNAMIC-DERIVATION-CONTRACT-1.0 全类型适用策略",
                "source_layer": "明确默认规则: 未分类",
                "target_layer": "明确默认规则: 未分类",
                "condition": "静态网络对应记录",
                "priority": "静态网络对应记录",
                "effect": "按静态关系类型派生的通用状态变化语义",
            }
            item["source_refs"] = [{"artifact": "NET-STATIC-FULL", "source": "静态网络.txt source_index", "source_key": [item["source"], item["target"], item["type"]]}]
            item["review_reason"] = "已按 NET-DYNAMIC-DERIVATION-CONTRACT-1.0 校验；具体故事采用仍需绑定当前对象和情境"
        else:
            item["field_source"] = {"source": "动态网络.txt 原始连接记录"}
    for number, item in enumerate(all_dynamic, 1):
        old = item.get("id", "")
        item["id"] = f"C{number:05d}"
        if old:
            mapping.append({"old_id": old, "new_id": item["id"], "source": item["source"], "target": item["target"], "type": item["type"]})
    static_index = defaultdict(list)
    for item in static:
        static_index[item["source"]].append({k: item[k] for k in ("target", "type", "condition", "priority")})
    static_payload = {
        "version": "3.0-generated", "source_file": "静态网络.txt", "total_blocks": static_blocks,
        "total_sources": len(static_index), "total_connections": len(static),
        "connection_types": sorted({x["type"] for x in static}),
        "source_index": {source: {"targets": sorted(targets, key=lambda x: (x["priority"], x["target"], x["type"]))} for source, targets in sorted(static_index.items())},
        "connections": static,
    }
    by_source = defaultdict(list); by_target = defaultdict(list); by_type = defaultdict(list)
    for item in all_dynamic:
        by_source[item["source"]].append(item["id"]); by_target[item["target"]].append(item["id"]); by_type[item["type"]].append(item["id"])
    dynamic_payload = {
        "version": "3.0-generated", "source_file": "动态网络.txt", "total_sources": len({x["source"] for x in all_dynamic}),
        "total_connections": len(all_dynamic), "generated_connections": len(generated),
        "needs_review_connections": sum(1 for x in all_dynamic if x.get("needs_review", False)), "connections": all_dynamic,
        "index": {"by_source": dict(by_source), "by_target": dict(by_target), "by_type": dict(by_type)},
    }
    mapping_payload = {
        "schema_version": "connection-type-mapping-2.0",
        "mappings": [{"static_type": x, "dynamic_type": x, "status": "contract_validated", "source": "NET-DYNAMIC-DERIVATION-CONTRACT-1.0"} for x in sorted({x["type"] for x in static})],
        "reason": "静态关系类型与派生动态关系类型按同名保留，并由 NET-DYNAMIC-DERIVATION-CONTRACT-1.0 定义通用状态语义；不代表存在独立动态原始来源。",
    }
    atomic_write_json(DATA / "static_connections.full.json", static_payload)
    atomic_write_json(DATA / "dynamic_connections.full.json", dynamic_payload)
    atomic_write_json(DATA / "node_aliases.json", aliases)
    atomic_write_json(DATA / "connection_type_mapping.json", mapping_payload)
    atomic_write_json(DATA / "dynamic_id_migration.json", {"migrations": mapping})
    atomic_write_json(DATA / "network_generation_metrics.json", {"static_original_connections": len(static), "dynamic_original_connections": len(dynamic_by_key), "dynamic_generated_connections": len(generated), "dynamic_final_connections": len(all_dynamic), "dynamic_conflicts": conflicts})
    dynamic_only_records = []
    for item in dynamic_by_key.values():
        key = (item["source"], item["target"], item["type"])
        if key in static_by_key:
            continue
        classification, reason = classify_dynamic_only(item, static, aliases)
        dynamic_only_records.append({"dynamic_id": item["id"], "source": item["source"], "target": item["target"], "type": item["type"], "classification": classification, "matched_static_source": None, "matched_static_target": None, "matched_static_type": None, "reason": reason, "needs_review": True})
    classification_counts = Counter(x["classification"] for x in dynamic_only_records)
    atomic_write_json(REPORTS / "dynamic_only_connections.json", {"total": len(dynamic_only_records), "classification_counts": dict(classification_counts), "connections": dynamic_only_records})
    candidates = []
    generated_review = []
    for item in generated:
        missing = [field for field in ("effect", "strength", "valid_types", "source_layer", "target_layer") if not item.get(field)]
        candidates.append({"source": item["source"], "target": item["target"], "type": item["type"], "condition": item["condition"], "priority": item["priority"], "candidate_status": "ready_for_review" if item["condition"] and item["type"] else "unclear", "source_file": "静态网络.txt source_index", "reason": "动态网络没有对应记录，未自动写入正式静态网络"})
        generated_review.append({"id": item["id"], "source": item["source"], "target": item["target"], "type": item["type"], "missing_fields": missing, "default_fields": ["direction", "strength", "valid_types", "source_layer", "target_layer", "effect"], "field_sources": item["field_source"], "needs_review": item.get("needs_review", False), "validation_status": item.get("validation_status"), "derivation_contract": item.get("derivation_contract"), "review_reason": item["review_reason"]})
    atomic_write_json(REPORTS / "static_connection_candidates.json", {"total": len(candidates), "candidates": candidates})
    atomic_write_json(REPORTS / "generated_connections_review.json", {"total": len(generated_review), "connections": generated_review})
    decisions = [{"names": group["names"], "decision": "unresolved", "reason": group["reason"], "impact": "保持节点独立，不参与自动匹配"} for group in aliases["unresolved_similar"]]
    atomic_write_json(REPORTS / "unresolved_node_aliases.json", {"total": len(decisions), "groups": decisions})
    atomic_write_json(REPORTS / "static_only_connections.json", {"total": 0, "connections": []})
    atomic_write_json(REPORTS / "connection_semantic_conflicts.json", {"total": len(conflicts), "conflicts": conflicts})
    (REPORTS / "repair_log.md").write_text("# Repair Log\n\n本次未将动态独有连接或静态派生候选写入正式静态网络；所有候选均保留来源并进入人工确认报告。\n", encoding="utf-8")
    make_file_inventory()
    return {"static": static_payload, "dynamic": dynamic_payload, "aliases": aliases, "conflicts": conflicts, "static_only": len(generated), "dynamic_only": dynamic_only_records}


if __name__ == "__main__":
    result = build_outputs()
    print(json.dumps({"static_actual_connections": result["static"]["total_connections"], "dynamic_original_connections": result["dynamic"]["total_connections"] - result["dynamic"]["generated_connections"], "dynamic_final_connections": result["dynamic"]["total_connections"], "static_only_connections": result["static_only"]}, ensure_ascii=False))