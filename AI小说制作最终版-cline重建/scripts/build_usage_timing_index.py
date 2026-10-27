"""Classify source-material items by when they are used in the writing workflow."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "08_原始资料"
OUTPUT = ROOT / "docs" / "analysis" / "usage_timing_index.jsonl"

TIMINGS = ("pre_writing", "during_writing", "post_writing", "multi_phase")
PRE_WORDS = re.compile(r"人物|角色|主角|配角|世界|设定|类型|主线|结构|欲望|执念|能力|势力|资源|关系|历史|种族|职业|悬念|伏笔|主题|情节|剧情|冲突|弧光|目标")
DURING_WORDS = re.compile(r"语言|表达|对白|对话|场景|镜头|感官|五感|描写|写作|正文|节拍卡|实时|调用|输出|叙述|视角|动作|节奏|情感曲线")
POST_WORDS = re.compile(r"检查|验证|校验|一致性|品控|审美|反馈|复盘|统计|风险|禁用词|重复|完成后|生成后|审查|纠错")


def record(source: str, section: str, text: str, depends_on: list[str] | None = None, used_by: list[str] | None = None) -> dict:
    pre = bool(PRE_WORDS.search(text))
    during = bool(DURING_WORDS.search(text))
    post = bool(POST_WORDS.search(text))
    flags = sum((pre, during, post))
    if flags > 1:
        timing = "multi_phase"
        reason = "条目同时包含设计、写作应用或完成后检查相关内容"
        uncertain = False
    elif pre:
        timing = "pre_writing"
        reason = "条目内容属于动笔前需要确定的设计或结构信息"
        uncertain = False
    elif during:
        timing = "during_writing"
        reason = "条目内容属于写作过程中需要实时参考或应用的规则"
        uncertain = False
    elif post:
        timing = "post_writing"
        reason = "条目内容属于写作完成后执行的检查或验证"
        uncertain = False
    else:
        timing = "multi_phase"
        reason = "条目文本未提供足以单独确定使用时机的字段，按跨阶段资料记录"
        uncertain = True
    item = {
        "source": source,
        "section": section,
        "timing": timing,
        "reason": reason,
        "depends_on": depends_on or [],
        "used_by": used_by or [],
    }
    if uncertain:
        item["classification_note"] = "无法从当前条目文本确定唯一使用时机"
    return item


def add_unique(items: list[dict], seen: set[tuple[str, str]], item: dict) -> None:
    key = (item["source"], item["section"])
    if key not in seen:
        seen.add(key)
        items.append(item)


def extract_library(items: list[dict], seen: set[tuple[str, str]]) -> None:
    path = SOURCE_DIR / "资料库.txt"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    headings = [(i, m.group(1).strip()) for i, line in enumerate(lines) if (m := re.match(r"^###\s+([^\s].*?)\s*$", line)) and re.match(r"\d+\.\d+_", m.group(1))]
    for pos, (start, section) in enumerate(headings):
        end = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
        text = "\n".join(lines[start:end])
        add_unique(items, seen, record("资料库.txt", section, text))


def extract_dynamic(items: list[dict], seen: set[tuple[str, str]]) -> None:
    path = SOURCE_DIR / "动态网络.txt"
    text = path.read_text(encoding="utf-8", errors="replace")
    for match in re.finditer(r'"id"\s*:\s*"(C\d+)"(?P<body>.*?)(?=\n\s*\},|\n\s*\{)', text, re.S):
        chain_id = match.group(1)
        add_unique(items, seen, record("动态网络.txt", chain_id, match.group(0), ["资料库.txt"], ["执行正文.txt"]))


def extract_static(items: list[dict], seen: set[tuple[str, str]]) -> None:
    path = SOURCE_DIR / "静态网络.txt"
    text = path.read_text(encoding="utf-8", errors="replace")
    current_source = None
    for line in text.splitlines():
        source_match = re.search(r'"([^"]+)"\s*:\s*\{\s*$', line)
        if source_match and not source_match.group(1).startswith(("target", "type")):
            current_source = source_match.group(1)
        edge_match = re.search(r'"target"\s*:\s*"([^"]+)".*?"type"\s*:\s*"([^"]+)"', line)
        if current_source and edge_match:
            target, edge_type = edge_match.groups()
            section = f"{current_source}->{target} ({edge_type})"
            add_unique(items, seen, record("静态网络.txt", section, line, ["资料库.txt"], ["执行正文.txt"]))


def extract_anchors(items: list[dict], seen: set[tuple[str, str]]) -> None:
    text = (SOURCE_DIR / "锚点网络.txt").read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"(?<![A-Za-z0-9])(ID|M|S|P|B|E|C|T|D|A|L|U)\d+\.\d+(?![A-Za-z0-9])")
    for anchor_id in dict.fromkeys(pattern.findall(text)):
        # findall returns only the prefix with the grouped expression; recover the full token.
        pass
    for match in dict.fromkeys(m.group(0) for m in pattern.finditer(text)):
        add_unique(items, seen, record("锚点网络.txt", match, match, ["资料库.txt"], ["执行正文.txt"]))


def extract_id_values(source_name: str, items: list[dict], seen: set[tuple[str, str]], patterns: tuple[str, ...]) -> None:
    text = (SOURCE_DIR / source_name).read_text(encoding="utf-8", errors="replace")
    for pattern in patterns:
        for match in dict.fromkeys(re.findall(pattern, text)):
            add_unique(items, seen, record(source_name, match, match, ["资料库.txt"], ["执行正文.txt"]))


def extract_execution(items: list[dict], seen: set[tuple[str, str]]) -> None:
    text = (SOURCE_DIR / "执行正文.txt").read_text(encoding="utf-8", errors="replace")
    patterns = (
        r"板块\s*(?:\d+|155|156|157|158|159|160|161|162)[：:][^\n】]+",
        r"步骤\s*[0-9]+(?:\s*第\s*[0-9]+\s*批)?[：:][^\n】]+",
        r"能力\d+：[^\n]+",
    )
    for pattern in patterns:
        for section in dict.fromkeys(re.findall(pattern, text)):
            add_unique(items, seen, record("执行正文.txt", section.strip(), section, ["资料库.txt"], ["执行正文.txt"]))


def main() -> None:
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    extract_library(items, seen)
    extract_dynamic(items, seen)
    extract_static(items, seen)
    extract_anchors(items, seen)
    extract_id_values("类型系统.txt", items, seen, (r'"stable_id"\s*:\s*"([^"]+)"', r'"schema_name"\s*:\s*"([^"]+)"'))
    extract_id_values("类型连接.txt", items, seen, (r'"dynamic_combination_id"\s*:\s*"([^"]+)"', r'"stable_id"\s*:\s*"([^"]+)"'))
    extract_execution(items, seen)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as stream:
        for item in items:
            stream.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    counts = Counter(item["timing"] for item in items)
    uncertain = sum("classification_note" in item for item in items)
    print(f"已分类条目总数：{len(items)}")
    print("各时机数量分布（" + ", ".join(f"{timing}: {counts[timing]}" for timing in TIMINGS) + "）")
    print(f"无法确定时机的条目数及原因：{uncertain}；条目文本未提供足以单独确定使用时机的字段，已按multi_phase记录并附classification_note")


if __name__ == "__main__":
    main()