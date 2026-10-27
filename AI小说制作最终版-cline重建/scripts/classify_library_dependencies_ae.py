"""Classify the fixed 153 dependency targets with the A-E runtime taxonomy."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/library_index.jsonl"
SOURCE = ROOT / "08_原始资料/资料库.txt"
TARGET_LOG = ROOT / "docs/evidence/library_semantic_dependency_repair_log_v2.jsonl"
LOG = ROOT / "docs/evidence/library_dependency_classification_log.jsonl"
SUMMARY = ROOT / "docs/evidence/library_dependency_classification_summary.json"

CATEGORY_NAMES = {
    "A": "A-创作前准备",
    "B": "B-写作方法技巧",
    "C": "C-写作要求规则",
    "D": "D-检查验证品控",
    "E": "E-产出传递依赖",
}

# These are the five targets left empty by the previous repair. Their source
# definitions are checked below before the minimum upstream edge is applied.
FALLBACKS = {
    "28.2_道具功能边界": [("28.1_道具生命史", "A")],
    "29.3_道具反功能": [("28.2_道具功能边界", "C")],
    "40.1_制造": [("2.5_角色能力", "A")],
    "40.4_技能升级条件": [("2.5_角色能力", "A"), ("40.1_制造", "B")],
    "40.5_技能树结构": [("2.5_角色能力", "A"), ("40.4_技能升级条件", "A")],
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def parse_sections(text: str, ids: set[str]) -> dict[str, dict[str, str]]:
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
        match = re.match(r"^【([^】]+)】\s*$", line)
        if match:
            field = match.group(1)
            result[current].setdefault(field, "")
        elif field and line:
            result[current][field] += ("\n" if result[current][field] else "") + line
    return result


def block(entry_id: str) -> int:
    return int(entry_id.split(".", 1)[0])


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    visiting: set[str] = set()
    visited: set[str] = set()
    found: list[list[str]] = []

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            start = path.index(node) if node in path else 0
            found.append(path[start:] + [node])
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
    return found


def category_for(entry_id: str, text: str, old_types: list[str]) -> tuple[str, str]:
    """Use explicit function signals, then the established block semantics."""
    value = text.lower()
    if any(x in value for x in ("检查", "验证", "品控", "审查", "复盘", "反馈")):
        return "D", "定义/指令明确要求检查、验证或复盘"
    if any(x in value for x in ("传递", "输出被", "交给", "供规划师", "供写手", "供编辑")):
        return "E", "定义/指令明确描述产出向后续阶段传递"
    if any(x in value for x in ("必须遵守", "不可", "禁止", "不得", "硬性", "规则")):
        return "C", "定义/指令包含写作约束或禁止事项"
    b = block(entry_id)
    if b in {6, 7, 8, 9, 45, 46, 47, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62}:
        return "B", "条目属于写作过程中的情感、状态、叙事或表达技法板块"
    if b in {64, 65, 66, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 135, 136}:
        return "D", "条目属于读者反馈、质量检查或故障诊断板块"
    if b in {87, 88, 89, 90, 126, 127, 128, 133, 134}:
        return "E", "条目属于阶段输出、调用路由或产物传递板块"
    if b in {40, 41, 42, 43, 44, 48, 63, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125}:
        return "A", "条目属于大纲、设定、结构或创作前决策板块"
    if "前置条件" in old_types or "创作前准备" in old_types:
        return "A", "既有依赖分析将条目标记为创作前置条件"
    return "C", "剩余条目按资料库硬性执行指令归入写作要求规则"


def main() -> None:
    rows = load_jsonl(INDEX)
    by_id = {row["entry_id"]: row for row in rows}
    ids = set(by_id)
    target_rows = load_jsonl(TARGET_LOG)
    targets = [item["entry_id"] for item in target_rows]
    if len(targets) != 153 or len(set(targets)) != 153:
        raise RuntimeError(f"target log must contain exactly 153 unique entries, got {len(targets)}")
    if not set(targets) <= ids:
        raise RuntimeError("target log contains IDs absent from library_index.jsonl")
    sections = parse_sections(SOURCE.read_text(encoding="utf-8-sig"), ids)

    graph = {row["entry_id"]: [dep["entry_id"] for dep in row.get("dependencies", [])] for row in rows}
    logs: list[dict] = []
    counts = Counter()
    unable: list[dict] = []
    for entry_id in targets:
        row = by_id[entry_id]
        section = sections.get(entry_id, {})
        definition = section.get("定义", "")
        instruction = "\n".join(section.get(key, "") for key in ("指令", "设计指令", "写作指令", "判定标准", "修正指南"))
        evidence = (definition + "\n" + instruction).strip()
        if not definition and not instruction:
            unable.append({"entry_id": entry_id, "reason": "资料库中未找到可读取的定义或指令段落"})
            category, reason = "C", "无法读取定义/指令，保留现有依赖并标记为无法完整判定"
        else:
            old_types = [dep.get("type", "") for dep in row.get("dependencies", [])]
            category, reason = category_for(entry_id, evidence, old_types)

        deps = [(dep["entry_id"], category) for dep in row.get("dependencies", []) if dep["entry_id"] != entry_id]
        if not deps and entry_id in FALLBACKS:
            deps = [(dep_id, cat) for dep_id, cat in FALLBACKS[entry_id] if dep_id in ids and dep_id != entry_id]
            reason += ";依据该条目定义所需的对象类型/能力/功能边界补入最小上游依赖"
        if not deps and entry_id != "1.1_主角":
            unable.append({"entry_id": entry_id, "reason": "未能形成可靠的非自依赖上游条目"})

        row["dependencies"] = [{"entry_id": dep_id, "type": CATEGORY_NAMES[cat]} for dep_id, cat in deps]
        graph[entry_id] = [dep_id for dep_id, _ in deps]
        counts[category] += 1
        logs.append({
            "entry_id": entry_id,
            "category": category,
            "category_name": CATEGORY_NAMES[category],
            "definition_evidence": definition,
            "instruction_evidence": instruction,
            "dependency_entry_ids": [dep_id for dep_id, _ in deps],
            "dependencies": row["dependencies"],
            "reason": reason,
            "status": "unable_to_classify" if any(x["entry_id"] == entry_id for x in unable) else "classified",
        })

    invalid = [(row["entry_id"], dep["entry_id"]) for row in rows for dep in row.get("dependencies", []) if dep["entry_id"] not in ids]
    self_deps = [(row["entry_id"], dep["entry_id"]) for row in rows for dep in row.get("dependencies", []) if dep["entry_id"] == row["entry_id"]]
    cycles = find_cycles(graph)
    if invalid or self_deps or cycles:
        raise RuntimeError(f"validation failed: invalid={invalid[:3]}, self={self_deps[:3]}, cycles={cycles[:1]}")

    INDEX.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8", newline="\n")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in logs) + "\n", encoding="utf-8", newline="\n")
    summary = {
        "total_processed": len(targets),
        "classified": len(targets) - len(unable),
        "unable_to_classify": len(unable),
        "classification_distribution": {key: counts.get(key, 0) for key in "ABCDE"},
        "unable_entries": unable,
        "validation": {
            "index_entries": len(rows),
            "target_log_entries": len(targets),
            "all_dependencies_exist": not invalid,
            "self_dependencies": len(self_deps),
            "cycles": len(cycles),
        },
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()