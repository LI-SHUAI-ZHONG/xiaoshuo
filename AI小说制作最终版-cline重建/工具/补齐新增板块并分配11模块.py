# -*- coding: utf-8 -*-
"""Add the post-128 library sections and assign the complete index to 11 modules."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "资料库.txt"
INDEX = ROOT / "docs" / "library_index.jsonl"
EVIDENCE = ROOT / "docs" / "evidence"
LOG = EVIDENCE / "library_module_assignment_log.jsonl"
SUMMARY = EVIDENCE / "library_module_assignment_summary.json"


def fields(text: str) -> list[str]:
    names = []
    for match in re.finditer(r"^【([^】]+)】|^\*\*([^*]+)\*\*$", text, re.M):
        name = (match.group(1) or match.group(2)).strip()
        if name and name not in names and name not in {"示例", "反面案例"}:
            names.append(name)
    return names


def record(entry_id: str, name: str, body: str) -> dict:
    deps = sorted(
        set(re.findall(r"(?<![\w.])(\d+(?:\.\d+)*_[^\s，。；：、（）()【】\[\]{}<>]+)", body)),
        key=lambda value: ([int(x) for x in value.split("_", 1)[0].split(".")], value),
    )
    deps = [dep for dep in deps if dep != entry_id]
    attrs = fields(body)
    return {
        "entry_id": entry_id,
        "name": name,
        "type": "模板" if "清单" in name or "规则" in name else "概念",
        "key_attributes": attrs or ["定义"],
        "dependencies": [{"entry_id": dep, "type": "功能关联"} for dep in deps],
        "has_examples": "【示例】" in body or "**示例**" in body,
        "has_conditions": "【调用条件】" in body,
    }


def extract_new() -> list[dict]:
    text = SOURCE.read_text(encoding="utf-8-sig")
    section_matches = list(re.finditer(r"^## 板块(129|130|131|132|133|134|135|136|137|138|139|140|141|142|143|144|145|146|147|148|149|150|151|152|153|154)\s+([^\r\n]+)", text, re.M))
    result: list[dict] = []
    for i, match in enumerate(section_matches):
        end = section_matches[i + 1].start() if i + 1 < len(section_matches) else text.find("## 一、你资料库已有的", match.end())
        if end < 0:
            end = len(text)
        number = match.group(1)
        name = match.group(2).strip()
        result.append(record(f"{number}_{name}", name, text[match.end():end]))

    supplement = re.search(r"^### 板块155 情节缓冲与节奏过渡(.+)$", text, re.M | re.S)
    if not supplement:
        raise RuntimeError("找不到板块155-162补充资料")
    supplement_text = supplement.group(0)
    sub_matches = list(re.finditer(r"^\*\*((15[5-9]|16[0-2])\.\d+)\s+([^*]+)\*\*", supplement_text, re.M))
    for i, match in enumerate(sub_matches):
        end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(supplement_text)
        entry_id = match.group(1)
        name = match.group(3).strip()
        result.append(record(f"{entry_id}_{name}", name, supplement_text[match.end():end]))
    return result


def module_for(entry_id: str) -> tuple[str, str]:
    prefix = int(entry_id.split("_", 1)[0].split(".", 1)[0])
    exact = {
        129: ("02", "新增命名与术语体系，属于前置决策层"),
        130: ("02", "核心悬念与核心谜题属于前置决策层"),
        131: ("01", "灵感来源与素材库属于系统启动"),
        132: ("01", "创作意图与承诺属于系统启动"),
        133: ("01", "章节预览与摘要属于系统启动"),
        134: ("10", "草稿版本与迭代属于编辑模式"),
        135: ("10", "试读反馈属于编辑模式"),
        136: ("10", "卡文诊断与解困属于编辑模式"),
        137: ("00", "分配方案未指定写作节奏与作息的阶段"),
        138: ("00", "分配方案未指定章节与场景命名的阶段"),
        139: ("11", "多媒介改编预留属于三阶段数据传递"),
        140: ("06", "角色未知性属于人物与剧情核心层"),
        141: ("06", "未知性与探索性属于人物与剧情核心层"),
        142: ("06", "人称视角未知性属于人物与剧情核心层"),
        143: ("06", "不确定性属于人物与剧情核心层"),
        144: ("06", "配角级别出场分类属于人物与剧情核心层"),
        145: ("06", "五节点链条含动作节点，属于人物与剧情核心层"),
        146: ("06", "人格外化表现属于人物与剧情核心层"),
        147: ("06", "他人视角与人格锚点属于人物与剧情核心层"),
        148: ("06", "观察、细节、做法属于人物与剧情核心层"),
        149: ("06", "权衡、判断、立场属于人物与剧情核心层"),
        150: ("06", "人性博弈属于人物与剧情核心层"),
        151: ("06", "背景身份运用属于人物与剧情核心层"),
        152: ("06", "方法策略与手段套路属于人物与剧情核心层"),
        153: ("06", "对立关系设计属于人物与剧情核心层"),
        154: ("06", "主线支线与任务目标属于人物与剧情核心层"),
    }
    if prefix in exact:
        return exact[prefix]
    special = {
        "155.1": ("07", "情绪缓冲规则属于执行与品控层"),
        "155.2": ("05", "共情铺垫属于开篇抢跑层"),
        "155.3": ("07", "情感密度匹配属于执行与品控层"),
        "156": ("09", "审美与感官设计属于写手模式"),
        "156.1": ("09", "用词审美属于写手模式"),
        "156.2": ("09", "描述审美属于写手模式"),
        "156.3": ("09", "外貌审美属于写手模式"),
        "156.4": ("09", "场景审美属于写手模式"),
        "156.5": ("09", "动作审美属于写手模式"),
        "157": ("07", "对话占比与行动推进点密度属于执行与品控层"),
        "158.1": ("05", "认知五阶梯属于开篇抢跑层"),
        "158.2": ("09", "认知反转属于写手模式"),
        "158.3": ("09", "回忆设计属于写手模式"),
        "159.1": ("08", "事前计划显性化属于规划师模式"),
        "159.2": ("09", "行动中思想描写属于写手模式"),
        "159.3": ("09", "执行后复盘与归因属于写手模式"),
        "160": ("09", "审美情感与道德审美属于写手模式"),
        "160.1": ("09", "审美情感的分类与运用属于写手模式"),
        "160.2": ("09", "道德审美属于写手模式"),
        "161": ("09", "对比审美与节奏审美属于写手模式"),
        "161.1": ("09", "对比审美属于写手模式"),
        "161.2": ("09", "节奏审美属于写手模式"),
        "162.1": ("09", "审美映射属于写手模式"),
        "162.2": ("10", "审美检查清单属于编辑模式"),
    }
    key = entry_id.split("_", 1)[0]
    if key in special:
        return special[key]
    if prefix <= 19 or 41 <= prefix <= 45 or 67 <= prefix <= 76 or 80 <= prefix <= 82 or prefix == 118 or prefix == 121:
        return "06", "既有分配方案：人物与剧情核心层"
    if 20 <= prefix <= 40:
        return "04", "既有分配方案：世界与设定层"
    if 46 <= prefix <= 48 or 61 <= prefix <= 62 or 77 <= prefix <= 79 or 83 <= prefix <= 86 or prefix in (115, 120, 122, 125, 157):
        return "07", "既有分配方案：执行与品控层"
    if 49 <= prefix <= 60 or prefix == 88:
        return "09", "既有分配方案：写手模式"
    if 64 <= prefix <= 66 or prefix in range(89, 109) or prefix in (116, 117, 134, 135, 136):
        return "10", "既有分配方案：编辑模式"
    if prefix in (87, 159):
        return "08", "既有分配方案：规划师模式"
    if prefix == 90 or 126 <= prefix <= 128:
        return "11", "既有分配方案：三阶段数据传递"
    if prefix in (112, 113, 119):
        return "05", "既有分配方案：开篇抢跑层"
    if prefix in (114, 123, 124, 129, 130):
        return "02", "既有分配方案：前置决策层"
    return "00", "分配方案未覆盖"


def main() -> None:
    existing = [json.loads(line) for line in INDEX.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    existing_ids = {item["entry_id"] for item in existing}
    additions = [item for item in extract_new() if item["entry_id"] not in existing_ids]
    records = existing + additions
    counters: Counter[str] = Counter()
    logs = []
    for item in records:
        module, basis = module_for(item["entry_id"])
        counters[module] += 1
        item["assigned_to_module"] = module
        item["load_order"] = counters[module]
        logs.append({"entry_id": item["entry_id"], "assigned_to_module": module, "load_order": counters[module], "basis": basis})
    INDEX.write_text("\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in records) + "\n", encoding="utf-8")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in logs) + "\n", encoding="utf-8")
    summary = {"total_entries": len(records), "added_entries": len(additions), "module_counts": {f"{i:02d}": counters[f"{i:02d}"] for i in range(1, 12)}, "unassigned_count": counters["00"], "new_entry_ids": [item["entry_id"] for item in additions]}
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total_entries": len(records), "added_entries": len(additions), "module_counts": summary["module_counts"], "unassigned_count": counters["00"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()