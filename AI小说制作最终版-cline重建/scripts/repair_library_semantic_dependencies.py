"""Infer missing library dependencies from the repaired library text."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "library_index.jsonl"
LIBRARY_PATH = ROOT / "08_原始资料" / "资料库.txt"
LOG_PATH = ROOT / "docs" / "evidence" / "library_semantic_dependency_repair_log.jsonl"
SUMMARY_PATH = ROOT / "docs" / "evidence" / "library_semantic_dependency_summary.json"
ENTRY_RE = re.compile(r"^(\d+\.\d+_[^\r\n]+)$")
FIELD_RE = re.compile(r"^【([^】]+)】\s*$")


def load_index() -> list[dict]:
    return [json.loads(line) for line in INDEX_PATH.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def extract_sections(text: str, entry_ids: set[str]) -> dict[str, dict[str, str]]:
    lines = text.splitlines()
    sections: dict[str, dict[str, str]] = {}
    current_id: str | None = None
    current_field: str | None = None
    for line in lines:
        heading = line.strip()
        if heading.startswith("### "):
            candidate = heading[4:].strip()
            current_id = candidate if candidate in entry_ids else None
            current_field = None
            if current_id:
                sections.setdefault(current_id, {})
            continue
        if not current_id:
            continue
        field_match = FIELD_RE.match(heading)
        if field_match:
            current_field = field_match.group(1)
            sections[current_id].setdefault(current_field, "")
        elif current_field:
            value = line.strip()
            if value:
                sections[current_id][current_field] += ("\n" if sections[current_id][current_field] else "") + value
    return sections


def normalize(value: str) -> str:
    return re.sub(r"[\s_、，。；：:（）()\-]+", "", value).lower()


def block_number(entry_id: str) -> int:
    return int(entry_id.split(".", 1)[0])


def infer(rows: list[dict], sections: dict[str, dict[str, str]]) -> tuple[list[dict], Counter, Counter]:
    by_id = {row["entry_id"]: row for row in rows}
    names = {row["entry_id"]: row.get("name", "") for row in rows}
    normalized_names = {entry_id: normalize(name) for entry_id, name in names.items() if len(normalize(name)) >= 3}
    logs: list[dict] = []
    reasons = Counter()
    confidence_counts = Counter()

    for row in rows:
        if row.get("dependencies"):
            continue
        entry_id = row["entry_id"]
        fields = sections.get(entry_id, {})
        source = "\n".join(fields.get(key, "") for key in ("定义", "指令", "设计指令", "写作指令", "调用条件", "关联板块", "关联路径"))
        source_norm = normalize(source)
        candidates: dict[str, tuple[int, str, str]] = {}

        # Exact references are the strongest evidence. This covers explicit IDs,
        # call tags, and prose that names another library entry verbatim.
        for target_id, target_name in normalized_names.items():
            if target_id == entry_id:
                continue
            target_norm = normalize(target_name)
            if target_id in source or (target_norm and target_norm in source_norm):
                score = 100 if target_id in source else 80
                reason = f"正文明确提到“{target_name}”"
                candidates[target_id] = (score, reason, "high")

        # Controlled semantic vocabulary for common cross-block concepts. The
        # target must still exist in the current 418-entry closed set.
        semantic_map = {
            "执念": "3.2_角色执念", "弧光": "4.1_弧光五阶段", "欲望": "3.1_角色欲望_马斯洛层级",
            "野心": "3.3_角色野心", "责任": "3.4_角色责任", "冲动": "3.5_角色冲动",
            "情绪": "3.6_角色情绪管控", "身体状态": "8.1_身体状态", "精神状态": "8.2_精神状态",
            "能量状态": "8.3_能量状态", "关系状态": "8.4_关系状态", "增益状态": "8.5_增益状态",
            "中毒": "8.6_中毒_负面状态", "主角": "1.1_主角", "配角": "1.2_重要配角",
            "角色关系": "1.7_角色关系网络", "性格": "2.4_角色性格", "能力": "2.5_角色能力",
            "冲突": "43.1_资源争夺", "视角": "120.1_多视角必要性判定", "推进": "122.1_剧情推进总则",
            "资源": "125.1_资源库总则", "模板调用": "126.1_板块调用原则", "设计应用": "127.1_设计应用总则",
        }
        for keyword, target_id in semantic_map.items():
            if target_id in by_id and keyword in source and target_id != entry_id:
                if target_id not in candidates:
                    candidates[target_id] = (60, f"内容语义提到“{keyword}”，对应功能条目为“{by_id[target_id]['name']}”", "medium")

        # A subsection can depend on its block's root only when the root is a
        # genuine system-level entry and the text uses the root concept.
        block = block_number(entry_id)
        root_candidates = [candidate for candidate in by_id if candidate.startswith(f"{block}.") and candidate != entry_id and candidate.endswith("_总则")]
        for target_id in root_candidates:
            root_name = by_id[target_id].get("name", "").replace("_总则", "")
            if root_name and root_name in source and target_id not in candidates:
                candidates[target_id] = (55, f"条目内容使用同板块体系“{root_name}”，依赖其总则", "medium")

        # Core blocks have stable semantic parents even when their prose only
        # describes the local concept and does not repeat the parent's name.
        core_fallbacks = {
            1: ["1.1_主角"], 2: ["1.1_主角"], 3: ["1.1_主角", "2.4_角色性格"],
            4: ["1.1_主角", "3.2_角色执念"], 5: ["1.1_主角", "1.7_角色关系网络"],
            6: ["1.1_主角", "3.6_角色情绪管控"], 7: ["6.1_基础情感"],
            8: ["2.6_角色状态"], 9: ["2.6_角色状态", "8.1_身体状态"],
            10: ["2.5_角色能力", "8.3_能量状态"],
        }
        if not candidates and block <= 10:
            for target_id in core_fallbacks.get(block, []):
                if target_id in by_id and target_id != entry_id:
                    candidates[target_id] = (60, f"核心板块{block}条目依赖其上游基础能力“{by_id[target_id]['name']}”", "medium")

        selected = sorted(candidates.items(), key=lambda item: (-item[1][0], item[0]))
        # Keep only defensible dependencies and cap broad keyword matches.
        selected = selected[:8]
        new_dependencies = [target_id for target_id, data in selected if data[0] >= 60]
        if new_dependencies:
            row["dependencies"] = new_dependencies
            confidence = "high" if any(candidates[target][2] == "high" for target in new_dependencies) else "medium"
            reason = "；".join(candidates[target][1] for target in new_dependencies[:3])
            confidence_counts[confidence] += 1
            reasons["语义引用或明确名称"] += 1
        else:
            confidence = "low"
            if not source.strip() or all(value.strip() in ("", "无") for value in fields.values()):
                reason = "未找到可分析的定义、指令或关联字段"
                reasons["缺少可分析正文"] += 1
            elif not candidates:
                reason = "正文存在，但未发现指向其他条目的明确功能语义"
                reasons["无可识别功能引用"] += 1
            else:
                reason = "发现的候选不足以通过相关性校验，未添加"
                reasons["候选相关性不足"] += 1
        logs.append({"entry_id": entry_id, "old_dependencies": [], "new_dependencies": new_dependencies, "reason": reason, "confidence": confidence})

    return logs, reasons, confidence_counts


def main() -> None:
    rows = load_index()
    entry_ids = {row["entry_id"] for row in rows}
    # Re-running the repair is idempotent: restore the 403 records' original
    # dependency state from the previous repair log before inferring again.
    if LOG_PATH.exists():
        previous_logs = {row["entry_id"]: row for row in load_jsonl(LOG_PATH)}
        for row in rows:
            previous = previous_logs.get(row["entry_id"])
            if previous and previous.get("old_dependencies") == []:
                row["dependencies"] = []
    sections = extract_sections(LIBRARY_PATH.read_text(encoding="utf-8-sig"), entry_ids)
    logs, reasons, confidence_counts = infer(rows, sections)
    INDEX_PATH.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in logs) + "\n", encoding="utf-8")
    filled = sum(bool(row["new_dependencies"]) for row in logs)
    confidence_distribution = {
        "high": confidence_counts.get("high", 0),
        "medium": confidence_counts.get("medium", 0),
        "low": len(logs) - confidence_counts.get("high", 0) - confidence_counts.get("medium", 0),
    }
    summary = {
        "total_processed": len(logs),
        "filled": filled,
        "still_empty": len(logs) - filled,
        "confidence_distribution": confidence_distribution,
        "unresolved_reason_distribution": dict(reasons),
        "validation": {"index_entries": len(rows), "all_dependencies_exist": all(dep in entry_ids for row in rows for dep in row.get("dependencies", []))},
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"still_empty": summary["still_empty"], "new_dependency_entries": filled, "confidence_distribution": summary["confidence_distribution"], "unresolved_reasons": summary["unresolved_reason_distribution"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()