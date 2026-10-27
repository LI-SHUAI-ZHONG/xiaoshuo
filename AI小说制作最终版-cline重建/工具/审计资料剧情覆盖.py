# -*- coding: utf-8 -*-
"""Audit whether the registered material networks can cover story dimensions.

This is a material-layer audit only. It deliberately excludes chapter text,
chapter designs, project snapshots, and chapter state.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料"
INDEX = ROOT / "00_资料索引" / "多维资料索引.yaml"
OUT = ROOT / "阶段状态" / "资料网络剧情覆盖.json"

DIMENSIONS = [
    "题材", "类型", "读者需求", "故事核心", "世界观", "人物", "人物关系",
    "冲突", "目标与代价", "主线", "支线", "情绪", "爽点或吸引力", "节奏",
    "场景", "事件", "伏笔", "叙事结构", "文风", "正文表达",
]

MODULES = {
    "MOD-TYPE": ("类型系统.txt", {"题材", "类型", "读者需求", "情绪", "爽点或吸引力", "文风"}),
    "MOD-CONNECTION": ("类型连接.txt", {"类型", "世界观", "冲突", "情绪", "场景", "事件", "伏笔", "正文表达"}),
    "MOD-STATIC": ("静态网络.txt", {"世界观", "人物", "人物关系", "主线", "支线", "叙事结构"}),
    "MOD-DYNAMIC": ("动态网络.txt", {"冲突", "目标与代价", "主线", "支线", "情绪", "事件", "伏笔", "节奏"}),
    "MOD-ANCHOR": ("锚点网络.txt", {"人物", "情绪", "场景", "事件", "节奏", "文风", "正文表达"}),
}


def read(path):
    return path.read_text(encoding="utf-8", errors="replace")


def extract_json(text):
    candidates = re.findall(r"```json\s*(.*?)```", text, flags=re.S | re.I)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def count_dynamic(value):
    if isinstance(value, dict):
        for key in ("连接列表", "connections", "items"):
            if isinstance(value.get(key), list):
                return len(value[key]), value
        for child in value.values():
            result = count_dynamic(child)
            if result[0]:
                return result
    return 0, value


def count_static(value):
    if isinstance(value, dict):
        source_index = value.get("source_index")
        if isinstance(source_index, dict):
            blocks = sum(1 for item in source_index.values() if isinstance(item, dict))
            edges = sum(len(item.get("targets", [])) for item in source_index.values() if isinstance(item, dict))
            return blocks, edges
        for child in value.values():
            result = count_static(child)
            if result[0]:
                return result
    return 0, 0


def count_anchor(text):
    match = re.search(r"合计\s*\|\s*\*\*(?:约)?([0-9,]+)", text)
    declared = int(match.group(1).replace(",", "")) if match else None
    rows = len(re.findall(r"^\|\s*[A-Z]\d+\.\d+\s*\|", text, flags=re.M))
    return declared, rows


def count_type_records(text):
    return len(re.findall(r'"dynamic_combination_id"\s*:', text)), text.count('"status": "candidate"')


def main():
    files = {name: RAW / name for name, _ in MODULES.values()}
    dynamic_text = read(files["动态网络.txt"])
    static_text = read(files["静态网络.txt"])
    anchor_text = read(files["锚点网络.txt"])
    type_text = read(files["类型连接.txt"])

    dynamic_value = extract_json(dynamic_text)
    dynamic_count, _ = count_dynamic(dynamic_value)
    static_value = extract_json(static_text)
    static_blocks, static_edges = count_static(static_value)
    anchor_declared, anchor_rows = count_anchor(anchor_text)
    type_records, type_candidates = count_type_records(type_text)

    coverage = {}
    for module, (_, dimensions) in MODULES.items():
        coverage[module] = {
            "source_file": f"08_原始资料/{MODULES[module][0]}",
            "declared_dimensions": sorted(dimensions),
            "covered_dimensions": sorted(dimensions),
            "uncovered_dimensions": sorted(set(DIMENSIONS) - dimensions),
            "coverage_status": "dimension_registered",
        }
    all_covered = set().union(*(item["covered_dimensions"] for item in coverage.values()))

    result = {
        "schema_version": "material-story-coverage-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "workspace_root": str(ROOT),
            "raw_root": "08_原始资料",
            "index": "00_资料索引/多维资料索引.yaml",
            "excluded": ["05_正文", "章节设计", "章节状态", "项目快照"],
        },
        "network_inventory": {
            "dynamic": {"file": "08_原始资料/动态网络.txt", "declared_connections": 2817, "parsed_connections": dynamic_count, "status": "parsed" if dynamic_count else "blocked_parse"},
            "static": {"file": "08_原始资料/静态网络.txt", "blocks": static_blocks, "edges": static_edges, "status": "parsed" if static_edges else "blocked_parse"},
            "anchor": {"file": "08_原始资料/锚点网络.txt", "declared_anchors": anchor_declared, "parsed_table_rows": anchor_rows, "status": "declared_and_sampled"},
            "type_connection": {"file": "08_原始资料/类型连接.txt", "records_detected": type_records, "candidate_records": type_candidates, "status": "candidate_records_only"},
        },
        "story_dimension_coverage": {
            "required_dimensions": DIMENSIONS,
            "covered_dimensions": sorted(all_covered),
            "uncovered_dimensions": sorted(set(DIMENSIONS) - all_covered),
            "coverage_ratio": round(len(all_covered) / len(DIMENSIONS), 4),
            "by_module": coverage,
        },
        "blocking_findings": [
            {"id": "COVERAGE-001", "status": "blocked", "reason": "动态网络原文声明2817条，但只有成功解析的连接才能进入可调用覆盖；解析量必须等于声明量。"}
            if dynamic_count != 2817 else
            {"id": "COVERAGE-001", "status": "pass", "reason": "动态网络声明连接数与解析连接数一致。"},
            {"id": "COVERAGE-002", "status": "blocked", "reason": "锚点网络包含模板化说明；声明数量不等于逐条可验证锚点数量。"},
            {"id": "COVERAGE-003", "status": "blocked", "reason": "类型连接含空块或candidate/template记录，不能作为已确认剧情连接。"},
            {"id": "COVERAGE-004", "status": "blocked", "reason": "本报告只证明资料网络覆盖剧情维度，不把候选连接升级为故事事实。"},
        ],
        "status": "blocked_until_network_records_are_verified",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "dynamic": dynamic_count, "static_edges": static_edges, "anchor_rows": anchor_rows, "type_records": type_records, "status": result["status"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()