"""Infer typed prerequisite paths for the remaining empty library entries."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "library_index.jsonl"
LIBRARY = ROOT / "08_原始资料" / "资料库.txt"
LOG = ROOT / "docs/evidence/library_semantic_dependency_repair_log_v2.jsonl"
SUMMARY = ROOT / "docs/evidence/library_semantic_dependency_summary_v2.json"
V1_LOG = ROOT / "docs/evidence/library_semantic_dependency_repair_log.jsonl"
ENTRY_RE = re.compile(r"^\d+\.\d+_")
FIELD_RE = re.compile(r"^【([^】]+)】\s*$")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def block(entry_id: str) -> int:
    return int(entry_id.split(".", 1)[0])


def normalize(value: str) -> str:
    return re.sub(r"[\s_、，。；：:（）()\-]+", "", value).lower()


def sections(text: str, ids: set[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current = None
    field = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("### "):
            candidate = line[4:].strip()
            current = candidate if candidate in ids else None
            field = None
            if current:
                result.setdefault(current, {})
            continue
        if not current:
            continue
        match = FIELD_RE.match(line)
        if match:
            field = match.group(1)
            result[current].setdefault(field, "")
        elif field and line:
            result[current][field] += ("\n" if result[current][field] else "") + line
    return result


def typed(entry_id: str, kind: str) -> dict:
    return {"entry_id": entry_id, "type": kind}


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            start = path.index(node) if node in path else 0
            cycles.append(path[start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            visit(dep, path + [dep])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [node])
    return cycles


def break_cycles(rows: list[dict]) -> int:
    """Remove one deterministic edge per cycle until the graph is acyclic."""
    removed = 0
    while True:
        graph = {row["entry_id"]: [item["entry_id"] for item in row.get("dependencies", [])] for row in rows}
        cycles = find_cycles(graph)
        if not cycles:
            return removed
        cycle = cycles[0]
        if len(cycle) < 2:
            return removed
        source = cycle[-2]
        target = cycle[-1]
        row = next(item for item in rows if item["entry_id"] == source)
        before = len(row.get("dependencies", []))
        row["dependencies"] = [item for item in row.get("dependencies", []) if item["entry_id"] != target]
        if len(row["dependencies"]) == before:
            # Defensive fallback for a cycle representation with a repeated
            # node at another position.
            source = cycle[0]
            target = cycle[1]
            row = next(item for item in rows if item["entry_id"] == source)
            row["dependencies"] = [item for item in row.get("dependencies", []) if item["entry_id"] != target]
        removed += 1


def main() -> None:
    rows = load_jsonl(INDEX)
    by_id = {row["entry_id"]: row for row in rows}
    ids = set(by_id)
    text_sections = sections(LIBRARY.read_text(encoding="utf-8-sig"), ids)
    # Restore the last complete v1 inference for the 403 records before v2
    # processing. This also makes reruns recover from an interrupted v2 run.
    v1_rows = load_jsonl(V1_LOG) if V1_LOG.exists() else []
    v1_empty_ids = {old["entry_id"] for old in v1_rows if old.get("old_dependencies") == [] and not old.get("new_dependencies")}
    if V1_LOG.exists():
        for old in v1_rows:
            if old.get("entry_id") in by_id and old.get("old_dependencies") == []:
                by_id[old["entry_id"]]["dependencies"] = [typed(dep, "功能关联") for dep in old.get("new_dependencies", [])]
    names = {row["entry_id"]: row.get("name", "") for row in rows}
    normalized_names = {entry_id: normalize(name) for entry_id, name in names.items() if len(normalize(name)) >= 3}

    # Stable upstream concepts used when a subsection only describes its own
    # operation and therefore has no explicit textual reference.
    parents = {
        11: [("10.1_能量总量", "前置条件")],
        12: [("11.1_游离态", "功能关联")],
        13: [("10.1_能量总量", "前置条件")], 14: [("13.1_等级划分", "前置条件")],
        15: [("13.1_等级划分", "前置条件")], 16: [("10.1_能量总量", "内容引用")],
        17: [("10.1_能量总量", "前置条件")], 18: [("17.1_能量守恒定律", "内容引用")],
        19: [("17.1_能量守恒定律", "前置条件")], 20: [("31.2_地理结构", "前置条件")],
        21: [("20.1_生态系统层级", "前置条件")], 22: [("31.3_核心矛盾", "功能关联")],
        23: [("41.1_三幕结构", "使用场景")], 26: [("24.1_资源类型", "前置条件")],
        28: [("27.1_道具类型", "前置条件")], 29: [("28.1_道具状态", "前置条件")],
        30: [("28.2_道具功能边界", "前置条件")], 31: [("1.1_主角", "创作前准备")],
        32: [("31.3_核心矛盾", "前置条件")], 33: [("31.3_核心矛盾", "功能关联")],
        34: [("31.4_世界基调", "创作前准备")], 35: [("31.3_核心矛盾", "功能关联")],
        36: [("31.1_世界名称", "创作前准备")], 37: [("2.5_角色能力", "功能关联")],
        39: [("1.1_主角", "功能关联")], 40: [("28.1_道具类型", "前置条件")],
        41: [("31.3_核心矛盾", "创作前准备")], 42: [("41.1_三幕结构", "大纲细纲设定")],
        43: [("31.3_核心矛盾", "大纲细纲设定")], 44: [("43.1_资源争夺", "剧情推进需要")],
        122: [("41.1_三幕结构", "大纲细纲设定")], 123: [("41.1_三幕结构", "使用场景")],
        124: [("123.1_爆款定义", "功能关联")], 125: [("31.2_地理结构", "前置条件")],
        126: [("127.1_设计应用总则", "使用场景")], 127: [("41.1_三幕结构", "大纲细纲设定")],
        128: [("126.1_板块调用原则", "使用场景")],
    }

    semantic = {
        "弧光": ("4.1_弧光五阶段", "内容引用"), "执念": ("3.2_角色执念", "内容引用"),
        "欲望": ("3.1_角色欲望_马斯洛层级", "前置条件"), "冲突": ("43.1_资源争夺", "功能关联"),
        "情感": ("6.1_基础情感", "内容引用"), "状态": ("2.6_角色状态", "前置条件"),
        "能量": ("10.1_能量总量", "内容引用"), "世界观": ("31.1_世界名称", "创作前准备"),
        "剧情推进": ("122.1_剧情推进总则", "剧情推进需要"), "场景": ("41.1_三幕结构", "使用场景"),
        "角色": ("1.1_主角", "功能关联"), "道具": ("28.1_道具类型", "前置条件"),
        "资源": ("24.1_资源类型", "内容引用"), "视角": ("120.1_多视角必要性判定", "使用场景"),
    }
    allowed_types = {"前置条件", "内容引用", "功能关联", "使用场景", "创作前准备", "大纲细纲设定", "剧情推进需要", "输出依赖"}
    old_type = "功能关联"
    for row in rows:
        if row.get("dependencies"):
            row["dependencies"] = [item if isinstance(item, dict) else typed(item, old_type) for item in row["dependencies"]]

    # Normalize and make the existing graph acyclic before evaluating new
    # candidates; otherwise an unrelated legacy cycle rejects every candidate.
    preexisting_graph = {row["entry_id"]: [item["entry_id"] for item in row.get("dependencies", [])] for row in rows}
    preexisting_cycles = len(find_cycles(preexisting_graph))
    preexisting_cycles_removed = break_cycles(rows)
    targets = [row for row in rows if row["entry_id"] in v1_empty_ids]

    logs = []
    category_counts = Counter()
    dependency_type_counts = Counter()
    graph = {row["entry_id"]: [item["entry_id"] for item in row.get("dependencies", [])] for row in rows}
    for row in targets:
        entry_id = row["entry_id"]
        fields = text_sections.get(entry_id, {})
        source = "\n".join(fields.get(key, "") for key in ("定义", "指令", "设计指令", "写作指令", "调用条件", "关联板块", "关联路径"))
        source_norm = normalize(source)
        candidates: list[tuple[str, str, str, str]] = []
        # Explicit names/IDs in operational text are content-reference or
        # object prerequisites, and are preferred over broad block fallbacks.
        for target_id, target_name in normalized_names.items():
            if target_id == entry_id:
                continue
            if target_id in source or target_name in source_norm:
                kind = "内容引用"
                if any(word in source for word in ("先", "前置", "需要已有", "必须完成")):
                    kind = "前置条件"
                candidates.append((target_id, kind, f"正文或使用条件明确提到“{names[target_id]}”", "C"))
        for keyword, (target_id, kind) in semantic.items():
            if keyword in source and target_id != entry_id and target_id in ids:
                candidates.append((target_id, kind, f"定义/指令使用“{keyword}”功能概念", "C"))
        for target_id, kind in parents.get(block(entry_id), []):
            if target_id in ids and target_id != entry_id:
                candidates.append((target_id, kind, f"条目属于板块{block(entry_id)}，使用该板块母项作为前置条件", "A"))

        selected: list[tuple[str, str, str, str]] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate[0] in seen:
                continue
            seen.add(candidate[0])
            # Do not introduce an edge that creates a cycle with existing or
            # already selected dependencies.
            trial = {key: list(value) for key, value in graph.items()}
            trial[entry_id] = [item[0] for item in selected] + [candidate[0]]
            if not find_cycles(trial):
                selected.append(candidate)
            if len(selected) >= 5:
                break
        row["dependencies"] = [typed(item[0], item[1]) for item in selected]
        graph[entry_id] = [item[0] for item in selected]
        for item in selected:
            dependency_type_counts[item[1]] += 1
        if selected:
            category = "C" if any(item[3] == "C" for item in selected) else "A"
            category_counts[category] += 1
            logs.append({"entry_id": entry_id, "added_dependencies": [item[0] for item in selected], "dependencies": [typed(item[0], item[1]) for item in selected], "reason": "；".join(item[2] for item in selected[:3]), "analysis_dimension": selected[0][1], "classification": f"类型{category}"})
        else:
            category_counts["D"] += 1
            logs.append({"entry_id": entry_id, "added_dependencies": [], "dependencies": [], "reason": "正文与使用方式不足以确定可靠的上游条件，保持空依赖", "analysis_dimension": "前置条件", "classification": "类型D"})

    cycles_before_repair = len(find_cycles(graph))
    cycles_removed = break_cycles(rows)
    graph = {row["entry_id"]: [item["entry_id"] for item in row.get("dependencies", [])] for row in rows}
    cycles = find_cycles(graph)
    if cycles:
        raise RuntimeError(f"dependency cycles remain after repair: {cycles[:3]}")
    invalid = [(row["entry_id"], item["entry_id"]) for row in rows for item in row.get("dependencies", []) if item["entry_id"] not in ids or item["entry_id"] == row["entry_id"] or item["type"] not in allowed_types]
    if invalid:
        raise RuntimeError(f"invalid dependencies: {invalid[:5]}")

    INDEX.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in logs) + "\n", encoding="utf-8")
    empty = [row["entry_id"] for row in targets if not row["dependencies"]]
    report = {
        "total_processed": len(targets), "filled": len(targets) - len(empty), "still_empty": len(empty),
        "classification_distribution": {key: category_counts.get(key, 0) for key in ("A", "B", "C", "D")},
        "dependency_type_distribution": dict(dependency_type_counts), "empty_entries": empty,
        "validation": {"index_entries": len(rows), "all_dependencies_exist": not invalid, "cycles": len(cycles), "cycles_detected_before_repair": cycles_before_repair, "cycles_removed": cycles_removed + preexisting_cycles_removed, "preexisting_cycles": preexisting_cycles, "self_dependencies": 0},
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    SUMMARY.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"processed": len(targets), "filled": report["filled"], "still_empty": report["still_empty"], "dependency_types": report["dependency_type_distribution"], "classification": report["classification_distribution"], "empty_entries": empty}, ensure_ascii=False))


if __name__ == "__main__":
    main()