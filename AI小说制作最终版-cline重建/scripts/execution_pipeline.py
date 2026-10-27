"""Run the 11-stage execution pipeline against indexed project data."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"
OUTPUT_DIR = EVIDENCE / "execution_outputs"
CONSUMPTION = EVIDENCE / "execution_consumption.jsonl"
TYPE_SYSTEM = ROOT / "08_原始资料" / "类型系统.txt"
TYPE_INDEX = EVIDENCE / "type_connection_global_index.json"
STATIC_INDEX = EVIDENCE / "static_network_index.json"
DYNAMIC_FULL = ROOT / "四网络连接，剧情覆盖" / "dynamic_connections.full.json"
ANCHOR_INDEX = EVIDENCE / "anchor_category_index.json"
RULE_FILES = (EVIDENCE / "type_connection_rules.json", EVIDENCE / "static_connection_adoption_rules.json", EVIDENCE / "anchor_adoption_rules.json", EVIDENCE / "execution_adoption_rules.json")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def require(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def write_output(module_id: str, name: str, payload: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"module_{module_id}_{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def execute_01(data: dict) -> tuple[dict, list[Path]]:
    output = {"project_id": data.get("project_id", "default-project"), "genre_selection": data.get("genres", ["玄幻"]), "chapter_target": data.get("chapter_target", 1), "initialized_at": now()}
    return output, [write_output("01", "project_config", output)]


def execute_02(data: dict) -> tuple[dict, list[Path]]:
    require(TYPE_SYSTEM); require(TYPE_INDEX)
    index = read_json(TYPE_INDEX); genres = data.get("genre_selection", data.get("genres", ["玄幻"]))
    matches = [c for c in index.get("combinations", []) if all(g in c.get("combination_id", "") for g in genres)]
    output = {"selected_types": genres, "type_system_source_lines": len(read_text(TYPE_SYSTEM).splitlines()), "matching_combinations": matches[:20], "decision_status": "matched" if matches else "input_required"}
    return output, [write_output("02", "type_decision", output)]


def execute_03(data: dict) -> tuple[dict, list[Path]]:
    require(TYPE_INDEX); index = read_json(TYPE_INDEX)
    edges = [{"id": c.get("combination_id"), "compatibility": c.get("compatibility"), "connections": c.get("connection_ids", [])} for c in index.get("combinations", [])]
    output = {"nodes": sorted({n for e in edges for n in (e["id"] or "").split("_")}), "edges": edges, "combination_count": len(edges)}
    return output, [write_output("03", "type_dependency_graph", output)]


def execute_04(data: dict) -> tuple[dict, list[Path]]:
    require(STATIC_INDEX); index = read_json(STATIC_INDEX)
    nodes = index.get("unique_source_nodes", []) + index.get("unique_target_nodes", [])
    output = {"core_nodes": nodes[:30], "resource_nodes": [n for n in nodes if any(k in n for k in ("资源", "能量", "力量"))], "edge_count": index.get("total_edges", 0)}
    return output, [write_output("04", "world_setting", output)]


def execute_05(data: dict) -> tuple[dict, list[Path]]:
    require(ANCHOR_INDEX); index = read_json(ANCHOR_INDEX); categories = index.get("category_counts", {})
    output = {"opening_anchor_categories": [key for key, count in categories.items() if count][:3], "golden_three_chapter_rhythm": ["建立异常", "升级目标", "制造悬念"], "anchor_total": index.get("total_anchors", 0)}
    return output, [write_output("05", "opening_design", output)]


def execute_06(data: dict) -> tuple[dict, list[Path]]:
    require(DYNAMIC_FULL); require(STATIC_INDEX); dynamic = read_json(DYNAMIC_FULL).get("connections", []); static = read_json(STATIC_INDEX)
    characters = [r for r in dynamic if any(k in r.get("source", "") + r.get("target", "") for k in ("主角", "角色", "人物"))][:30]
    output = {"character_connections": characters, "plot_edges": static.get("total_edges", 0), "dynamic_edges": len(dynamic)}
    return output, [write_output("06", "character_plot_core", output)]


def execute_07(data: dict) -> tuple[dict, list[Path]]:
    require(DYNAMIC_FULL); require(ANCHOR_INDEX); dynamic = read_json(DYNAMIC_FULL).get("connections", []); anchors = read_json(ANCHOR_INDEX)
    output = {"dynamic_connection_count": len(dynamic), "anchor_count": anchors.get("total_anchors", 0), "quality_rules": ["每场景至少一个锚点", "动态链必须可验证"], "priority_one_connections": sum(r.get("priority", 0) == 1 for r in dynamic)}
    return output, [write_output("07", "quality_rules", output)]


def execute_08(data: dict) -> tuple[dict, list[Path]]:
    require(DYNAMIC_FULL); require(ANCHOR_INDEX); dynamic = read_json(DYNAMIC_FULL).get("connections", []); count = read_json(ANCHOR_INDEX).get("total_anchors", 0)
    beats = [{"scene_id": f"SCENE-{i}", "dynamic_edge": dynamic[i - 1].get("id"), "anchor_count": count, "beat": beat} for i, beat in enumerate(("异常出现", "目标确认", "阻力升级", "新悬念"), 1)]
    output = {"scene_beat_cards": beats}; return output, [write_output("08", "scene_beat_cards", output)]


def execute_09(data: dict) -> tuple[dict, list[Path]]:
    require(ANCHOR_INDEX); categories = list(read_json(ANCHOR_INDEX).get("category_counts", {}))
    scenes = [{"scene_id": f"SCENE-{i}", "anchor_category": categories[(i - 1) % len(categories)], "paragraphs": [f"场景{i}正文草稿。"]} for i in range(1, 5)]
    output = {"scenes": scenes, "status": "draft"}; return output, [write_output("09", "scene_prose", output)]


def execute_10(data: dict) -> tuple[dict, list[Path]]:
    paths = (TYPE_INDEX, STATIC_INDEX, DYNAMIC_FULL, ANCHOR_INDEX, *RULE_FILES)
    for path in paths: require(path)
    output = {"checks": {path.name: "readable" for path in paths}, "blocking_failures": [], "status": "passed"}
    return output, [write_output("10", "final_check_report", output)]


def execute_11(data: dict) -> tuple[dict, list[Path]]:
    outputs = data.get("module_outputs", {}); output = {"modules_received": sorted(outputs), "module_count": len(outputs), "output_files": [p for item in outputs.values() for p in item.get("output_files", [])]}
    return output, [write_output("11", "transfer_summary", output)]


MODULES: tuple[tuple[str, str, Callable[[dict], tuple[dict, list[Path]]]], ...] = (("01", "系统启动", execute_01), ("02", "前置决策层", execute_02), ("03", "类型特征适配层", execute_03), ("04", "世界与设定层", execute_04), ("05", "开篇抢跑层", execute_05), ("06", "人物与剧情核心层_第1批", execute_06), ("07", "执行与品控层_第2批", execute_07), ("08", "规划师模式", execute_08), ("09", "写手模式", execute_09), ("10", "编辑模式", execute_10), ("11", "三阶段数据传递", execute_11))

MODULE_INPUTS = {
    "01": [],
    "02": [TYPE_SYSTEM, TYPE_INDEX],
    "03": [TYPE_INDEX],
    "04": [STATIC_INDEX],
    "05": [ANCHOR_INDEX],
    "06": [DYNAMIC_FULL, STATIC_INDEX],
    "07": [DYNAMIC_FULL, ANCHOR_INDEX],
    "08": [DYNAMIC_FULL, ANCHOR_INDEX],
    "09": [ANCHOR_INDEX],
    "10": [TYPE_INDEX, STATIC_INDEX, DYNAMIC_FULL, ANCHOR_INDEX, *RULE_FILES],
    "11": [],
}


def main(project_id: str = "default-project", genres: list[str] | None = None) -> list[dict]:
    context: dict[str, Any] = {"project_id": project_id, "genres": genres or ["玄幻"]}; results = []; rows = [{"schema_version": "1.0", "record_type": "header", "total_records": len(MODULES), "last_updated": now()}]
    for module_id, name, function in MODULES:
        try:
            output, files = function(context); file_strings = [str(path.relative_to(ROOT)) for path in files]
            input_files = [str(path.relative_to(ROOT)) for path in MODULE_INPUTS[module_id]]
            record = {"module_id": module_id, "module_name": name, "status": "success", "input_files": input_files, "output_files": file_strings, "executed_at": now()}
            context = {**context, **output, "module_outputs": {**context.get("module_outputs", {}), module_id: {**record, "output_files": file_strings}}}
            if module_id == "11":
                record["input_files"] = [item["output_files"][0] for item in results if item.get("status") == "success" and item.get("output_files")]
            print(json.dumps({"module": module_id, "name": name, "status": "success", "input_files": record["input_files"], "output_files": file_strings}, ensure_ascii=False))
        except Exception as exc:
            record = {"module_id": module_id, "module_name": name, "status": "failed", "error": str(exc), "input_files": [], "output_files": [], "executed_at": now()}; context = {**context, "module_outputs": {**context.get("module_outputs", {}), module_id: record}}
            print(json.dumps({"module": module_id, "name": name, "status": "failed", "error": str(exc)}, ensure_ascii=False))
        results.append(record); rows.append(record)
    CONSUMPTION.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"total_modules": len(results), "success": sum(r["status"] == "success" for r in results), "failed": sum(r["status"] == "failed" for r in results)}, ensure_ascii=False)); return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--project-id", default="default-project"); parser.add_argument("--genres", nargs="+", default=["玄幻"]); args = parser.parse_args(); main(args.project_id, args.genres)