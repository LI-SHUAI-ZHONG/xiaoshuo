# -*- coding: utf-8 -*-
"""Build the executable global index for core type combinations."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "类型连接.txt"
TYPE_SUMMARY = ROOT / "docs" / "evidence" / "type_system_completion_summary.json"
GLOBAL = ROOT / "docs" / "evidence" / "type_connection_global_index.json"
LOG = ROOT / "docs" / "evidence" / "type_connection_repair_log.jsonl"
SUMMARY = ROOT / "docs" / "evidence" / "type_connection_summary.json"

CORE = ["玄幻", "仙侠", "科幻", "悬疑", "都市", "言情", "历史", "军事", "游戏", "体育", "灵异"]
INTERNAL = {
    "玄幻": "XUANHUAN", "仙侠": "XIANXIA", "科幻": "KEHUAN", "悬疑": "XUANYI",
    "都市": "DUSHI", "言情": "YANQING", "历史": "LISHI", "军事": "JUNSHI",
    "游戏": "YOUXI", "体育": "TIYU", "灵异": "LINGYI",
}


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b), key=CORE.index))


def scan_source() -> tuple[set[tuple[str, str]], dict[tuple[str, str], list[str]], dict[tuple[str, str], list[str]]]:
    text = SOURCE.read_text(encoding="utf-8")
    found: set[tuple[str, str]] = set()
    raw_conflicts: dict[tuple[str, str], list[str]] = {}
    raw_mechanisms: dict[tuple[str, str], list[str]] = {}
    # Capture explicit pair-like strings and JSON arrays containing two core genre IDs.
    name_alt = "|".join(map(re.escape, CORE))
    for match in re.finditer(rf"({name_alt})\s*(?:_|\\+|\+|-|×|x|X|/|、)\s*({name_alt})", text):
        a, b = match.group(1), match.group(2)
        if a != b:
            found.add(pair_key(a, b))
    id_to_name = {value: key for key, value in INTERNAL.items()}
    for match in re.finditer(r'"(?:component_type_ids|type_ids|type)"\s*:\s*\[(.*?)\]', text, re.S):
        ids = re.findall(r'"([A-Z][A-Z0-9_]+)"', match.group(1))
        names = list(dict.fromkeys(id_to_name[x] for x in ids if x in id_to_name))
        for a, b in combinations(names, 2):
            found.add(pair_key(a, b))
    # Explicit text is retained only when it is attached to a discovered pair.
    for match in re.finditer(rf"({name_alt})\s*(?:_|\\+|\+|-|×|x|X|/|、)\s*({name_alt})(.{{0,500}})", text, re.S):
        key = pair_key(match.group(1), match.group(2))
        tail = match.group(3)
        for field, target in (("冲突", raw_conflicts), ("机制", raw_mechanisms), ("推荐", raw_mechanisms)):
            hit = re.search(rf"{field}[^：:\n]*[：:]\s*([^\n}}]+)", tail)
            if hit:
                target.setdefault(key, []).append(hit.group(1).strip())
    return found, raw_conflicts, raw_mechanisms


def profile_data() -> dict[str, dict]:
    # The completed summary establishes the authoritative eligible set.
    data = json.loads(TYPE_SUMMARY.read_text(encoding="utf-8"))
    eligible = set(data.get("completed_types", [])) & set(CORE)
    if len(eligible) != 11:
        raise ValueError(f"expected 11 completed core types, got {len(eligible)}")
    profiles = {
        "玄幻": ("力量体系、个人成长、能力突破", "成长逆袭、能力展示、阶段性爽点", "规则清晰、升级有代价、冲突递进"),
        "仙侠": ("力量体系、世界基础、历史制度、规则约束", "问道逍遥、境界成长、世界观展开", "节奏舒展但节点明确、设定有因果、避免空泛说明"),
        "科幻": ("能量体系、能力边界、能量守恒、流动规律", "新奇设定、逻辑自洽、未知探索", "技术规则可验证、信息逐步揭示、避免无因果奇迹"),
        "悬疑": ("伏笔、反转、信息差、核心悬念", "持续猜测、证据推进、反转回收", "控制信息释放、线索可追溯、结论必须有证据"),
        "都市": ("社会制度、身份关系、职业系统、现实约束", "代入现实、职业成长、关系变化", "场景具体、因果现实、节奏贴近生活冲突"),
        "言情": ("关系类型、情感分类、关系变化、情感动机", "情感推进、关系确认、关键选择", "情绪有铺垫、关系变化可验证、避免强行误会"),
        "历史": ("世界基础、历史沿革、社会制度、时代环境", "时代沉浸、制度影响、人物选择", "尊重时代约束、信息嵌入行动、避免现代观念直译"),
        "军事": ("冲突体系、力量对抗、场景冲突、局势升级", "战术博弈、目标推进、代价承担", "行动有指挥链、资源与信息可追踪、冲突逐级升级"),
        "游戏": ("天赋、等级、能力成长、进阶条件、资源消耗", "可见成长、规则博弈、阶段奖励", "数值规则一致、升级有条件、结果需经过验证"),
        "体育": ("意志、决策、竞争目标、阶段性进步、临场选择", "比赛张力、训练积累、关键决策", "动作与比分具体、节奏跟随比赛、胜负有过程依据"),
        "灵异": ("伏笔、反转、命运态度、命运运用、未知规则", "未知压迫、线索回收、命运选择", "保持未知边界、线索可回溯、超自然规则不能随意改写"),
    }
    return {name: {"elements": e, "readers": r, "style": s} for name, (e, r, s) in profiles.items() if name in eligible}


def main() -> int:
    found, explicit_conflicts, explicit_mechanisms = scan_source()
    profiles = profile_data()
    # A connection index must expose all eligible pairings, including pairs absent in source.
    pairs = sorted(set(combinations(CORE, 2)), key=lambda p: (CORE.index(p[0]), CORE.index(p[1])))
    now = datetime.now(timezone.utc).isoformat()
    entries = []
    logs = []
    distribution = {"high": 0, "medium": 0, "low": 0}
    for number, (a, b) in enumerate(pairs, 1):
        key = pair_key(a, b)
        ea = set(profiles[a]["elements"].split("、")); eb = set(profiles[b]["elements"].split("、"))
        overlap = len(ea & eb)
        compatibility = "high" if overlap >= 2 else "medium" if overlap == 1 else "low"
        distribution[compatibility] += 1
        conflicts = explicit_conflicts.get(key) or [f"{a}的核心元素与{b}的核心元素在规则边界、节奏或因果尺度上可能冲突"]
        mechanisms = explicit_mechanisms.get(key) or [f"以{a}的核心推进线为主体，吸收{b}的核心元素作为世界观或冲突机制，并在正文中逐场景验证"]
        combo = f"{a}_{b}"
        entries.append({"combination_id": combo, "connection_ids": [f"CONN-{combo}-{number:03d}"],
                        "conflict_count": len(conflicts), "mechanism_count": len(mechanisms),
                        "compatibility": compatibility, "conflicts": conflicts,
                        "recommended_mechanisms": mechanisms})
        logs.append({"combination_id": combo, "source_found": key in found,
                     "conflict_source": "source" if key in explicit_conflicts else "derived_from_type_system",
                     "mechanism_source": "source" if key in explicit_mechanisms else "derived_from_type_system",
                     "status": "filled", "updated_at": now})
    GLOBAL.write_text(json.dumps({"last_updated": now, "total_combinations": len(entries), "combinations": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in logs), encoding="utf-8")
    summary = {"total_combinations": len(entries), "with_conflicts": sum(x["conflict_count"] > 0 for x in entries),
               "with_mechanisms": sum(x["mechanism_count"] > 0 for x in entries), "compatibility_distribution": distribution}
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"提取的组合总数: {len(entries)}")
    print(f"已补冲突记录数: {summary['with_conflicts']}")
    print(f"已补推荐机制数: {summary['with_mechanisms']}")
    print(f"兼容性等级分布: {json.dumps(distribution, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())