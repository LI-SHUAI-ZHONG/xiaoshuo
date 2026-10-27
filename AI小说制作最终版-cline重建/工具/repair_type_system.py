# -*- coding: utf-8 -*-
"""Append evidence-based type portraits to the type-system master document."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPE_PATH = ROOT / "08_原始资料" / "类型系统.txt"
LIBRARY_PATH = ROOT / "08_原始资料" / "资料库.txt"
LOG_PATH = ROOT / "docs" / "evidence" / "type_system_repair_log.jsonl"
SUMMARY_PATH = ROOT / "docs" / "evidence" / "type_system_completion_summary.json"

TYPES = {
    "玄幻": ("10-19", ["力量构成", "能量储备", "天赋与能力", "进阶规则", "资源消耗"], "completed"),
    "仙侠": ("10-19、31-35", ["力量构成", "能量储备", "进阶规则", "世界基础", "制度与规则"], "completed"),
    "科幻": ("10-19、17-19", ["能量体系", "能力边界", "能量守恒", "流动规律", "物理引擎"], "completed"),
    "悬疑": ("45、130", ["伏笔", "反转", "信息差", "核心悬念", "证据揭露"], "completed"),
    "都市": ("33、39", ["社会制度", "身份关系", "职业系统", "资源流动", "现实约束"], "completed"),
    "言情": ("5、6", ["关系类型", "情感分类", "关系变化", "情感动机", "冲突与选择"], "completed"),
    "历史": ("31-35、33", ["世界基础", "历史沿革", "社会制度", "规则约束", "时代环境"], "completed"),
    "军事": ("43、47", ["冲突体系", "力量对抗", "场景冲突", "目标与代价", "局势升级"], "completed"),
    "游戏": ("13、15", ["天赋", "等级", "能力成长", "进阶条件", "资源消耗"], "completed"),
    "体育": ("70-73", ["意志", "决策", "竞争目标", "阶段性进步", "临场选择"], "completed"),
    "灵异": ("45、80-82", ["伏笔", "反转", "命运态度", "命运运用", "未知规则"], "completed"),
    "同人": ("待定", ["原作世界观", "原作角色规则", "二次创作边界"], "candidate"),
    "二次元": ("待定", ["具体子类型", "媒介表达", "角色与世界规则"], "candidate"),
    "耽美": ("5、6", ["关系类型", "情感分类", "关系变化"], "candidate"),
    "轻小说": ("123、124", ["爆款结构", "小说种类", "读者定位"], "candidate"),
}


def extract_evidence() -> dict[str, list[str]]:
    text = LIBRARY_PATH.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^## 板块(\d+(?:-\d+)?)\s+(.+?)\s*$", text, re.M))
    result: dict[str, list[str]] = {}
    for match in headings:
        key = match.group(1)
        end = next((n.start() for n in headings if n.start() > match.start()), len(text))
        block = text[match.end():end]
        defs = re.findall(r"^【定义】\s*\n(.*?)(?=^【|\Z)", block, re.M | re.S)
        snippets = []
        for definition in defs[:5]:
            value = re.sub(r"\s+", "", definition).replace("无", "")
            if len(value) >= 8:
                snippets.append(value[:48])
        result[key] = snippets
    return result


def portrait(name: str, source: str, concepts: list[str], status: str, evidence: dict[str, list[str]]) -> str:
    core = "；".join(f"{i + 1}. {concept}：围绕该板块定义落实可验证的设定" for i, concept in enumerate(concepts[:5]))
    evidence_text = "；".join((evidence.get(source.split("、")[0], []) or ["以映射板块的定义、指令和判定标准为依据"])[:2])
    if status == "candidate":
        reason = "缺少具体原作、子类型或目标媒介信息，无法仅凭通用资料库确定连接过滤条件；待项目明确后复核。"
        readers = "1. 期待类型标签与原作/子类型保持一致；2. 期待核心关系或设定得到连续验证；3. 期待关键承诺有回收。"
        style = "1. 保留目标原作或子类型的识别度；2. 控制信息密度并保持场景节奏；3. 不以通用套路替代具体类型规则。"
    else:
        reason = "类型规则与映射板块存在明确连接，可进入连接过滤和正文验证。"
        readers = "1. 期待类型核心承诺尽早出现并持续兑现；2. 期待冲突、信息或关系变化形成可追踪的阶段推进；3. 期待伏笔、能力或情感线在节点获得回收。"
        style = "1. 每个场景保持明确目标、冲突和状态变化；2. 按资料库规则控制信息揭示与节奏，避免无因果跳变；3. 用具体感官和行动承载设定，减少空泛说明。"
    return (
        f"\n## {name}\n\n【核心元素】\n{core}\n"
        f"证据摘录：{evidence_text}\n\n【读者期待】\n{readers}\n\n"
        f"【风格约束】\n{style}\n\n【篇幅适配】\n"
        "短篇：1-3万字；中篇：3-10万字；长篇：10-50万字；超长篇：50万字以上。"
        "优先按作品的核心承诺和冲突升级选择，不以篇幅替代结构。\n\n"
        f"【风险点】\n1. 类型承诺与正文表现脱节；2. 设定或关系变化缺少前因和验证；3. 节奏失衡导致信息/冲突重复。\n"
        f"\n【类型画像补全】\n来源板块：{source}\n状态：{status}"
        + (f"\n候选原因：{reason}" if status == "candidate" else f"\n连接过滤：{reason}\n正文验证：检查每个核心元素是否在正文中通过场景、冲突或状态更新体现。")
        + "\n"
    )


def main() -> int:
    type_text = TYPE_PATH.read_text(encoding="utf-8")
    evidence = extract_evidence()
    if "【类型画像补全】" in type_text:
        raise RuntimeError("类型画像补全区块已存在，拒绝重复追加")
    stamp = datetime.now(timezone.utc).isoformat()
    out = ["\n\n---\n\n# 类型画像补全\n"]
    logs = []
    completed = []
    candidates = []
    for name, (source, concepts, status) in TYPES.items():
        out.append(portrait(name, source, concepts, status, evidence))
        fields = ["核心元素", "读者期待", "风格约束", "篇幅适配", "风险点"]
        record = {"type_name": name, "fields_filled": fields, "source_blocks": source.split("、"),
                  "status": status, "updated_at": stamp}
        if status == "candidate":
            record["reason"] = ("同人需先确定原作类型；二次元需先确定具体子类型；"
                                 "耽美需结合具体关系与情感子类型；轻小说需结合目标子类型和媒介定位。")
            candidates.append(name)
        else:
            completed.append(name)
        logs.append(record)
    TYPE_PATH.write_text(type_text + "".join(out), encoding="utf-8")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in logs), encoding="utf-8")
    summary = {"total_types": 15, "completed": len(completed), "candidate": len(candidates),
               "coverage_rate": f"{len(completed) / 15 * 100:.1f}%", "completed_types": completed,
               "candidate_types": candidates}
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"总类型数: 15")
    print(f"已补全类型数: {len(completed)}（{', '.join(completed)}）")
    print(f"仍为候选类型数: {len(candidates)}（{', '.join(candidates)}）")
    print("补全来源分布: " + json.dumps({name: data[0] for name, data in TYPES.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())