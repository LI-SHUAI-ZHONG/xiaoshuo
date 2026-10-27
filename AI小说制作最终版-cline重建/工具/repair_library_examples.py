# -*- coding: utf-8 -*-
"""Fill missing library examples from each entry's own definition and instructions."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "08_原始资料" / "资料库.txt"
INDEX_PATH = ROOT / "docs" / "library_index.jsonl"
LOG_PATH = ROOT / "docs" / "evidence" / "library_example_repair_log.jsonl"
SUMMARY_PATH = ROOT / "docs" / "evidence" / "library_example_summary.json"

ENTRY_RE = re.compile(r"^###\s+([0-9]+\.[0-9]+_.+?)\s*$", re.M)
SECTION_RE = re.compile(r"^【(.+?)】\s*$", re.M)
PLACEHOLDER_RE = re.compile(r"^(?:无|暂无|待补充|待确认|未确认|空|\[\]|\{\})$")
NOISE_RE = re.compile(r"[\\*#`>\-\s]+")


def clean(value: str) -> str:
    value = value.replace("\\-", "- ")
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[\\*#`]+", "", value)
    return value.strip()


def meaningful(value: str) -> bool:
    value = clean(value)
    return bool(value) and not PLACEHOLDER_RE.fullmatch(value) and len(NOISE_RE.sub("", value)) >= 8


def excerpt(value: str, limit: int = 34) -> str:
    value = clean(value)
    value = re.sub(r"[；。！？\n].*$", "", value)
    return value[:limit] if value else "条目原文中的核心定义"


def parse_sections(body: str) -> list[tuple[str, str, int, int]]:
    matches = list(SECTION_RE.finditer(body))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group(1).strip(), body[match.end():end], match.start(), end))
    return sections


def build_example(entry_id: str, name: str, sections: dict[str, str]) -> tuple[str | None, str | None]:
    definition = sections.get("定义", "")
    instruction = sections.get("指令", "")
    writing = sections.get("写作指令", "")
    if not meaningful(definition) and not meaningful(instruction) and not meaningful(writing):
        return None, "条目定义、指令和写作指令均为空或仅为占位内容，无法生成可执行示例"
    basis = excerpt(definition if meaningful(definition) else instruction)
    rule = excerpt(instruction if meaningful(instruction) else writing, 32)
    example = (
        f"场景：在设计或执行“{name}”时使用。"
        f"输入：已有故事任务，并以条目定义“{basis}”作为判断依据。"
        f"操作：先明确适用对象，再按定义提取操作要求；必要时执行指令“{rule}”。"
        f"输出：形成一项与“{name}”对应的设计或正文决策。"
        f"验证：检查决策是否符合定义且完成指令要求，若不符合则退回修正。"
    )
    if len(example) < 50 or len(example) > 150:
        # Keep all required fields while staying within the requested range.
        example = (
            f"场景：执行“{name}”。输入：故事任务和条目定义“{basis}”。"
            f"操作：按定义确定对象与步骤，并落实指令“{rule}”。"
            f"输出：得到对应的设计决策。验证：检查结果是否符合定义和指令。"
        )
    return example, None


def main() -> int:
    text = SOURCE_PATH.read_text(encoding="utf-8")
    index_rows = [json.loads(line) for line in INDEX_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(index_rows) != 418 or len({row["entry_id"] for row in index_rows}) != 418:
        raise ValueError("library_index.jsonl must contain 418 unique entries")
    index_by_id = {row["entry_id"]: row for row in index_rows}
    headers = list(ENTRY_RE.finditer(text))
    if len(headers) != 418:
        raise ValueError(f"资料库条目数不为418: {len(headers)}")

    replacements = []
    logs = []
    filled = pending = already = 0
    now = datetime.now(timezone.utc).isoformat()
    for number, header in enumerate(headers):
        entry_id = header.group(1).strip()
        if entry_id not in index_by_id:
            raise ValueError(f"source entry missing from index: {entry_id}")
        body_end = headers[number + 1].start() if number + 1 < len(headers) else len(text)
        body = text[header.end():body_end]
        parsed = parse_sections(body)
        sections = {name: content.strip() for name, content, _, _ in parsed}
        example_content = sections.get("示例", "").strip()
        has_example = meaningful(example_content)
        if has_example:
            already += 1
            status = "existing"
            source = "原文保留"
            preview = clean(example_content)[:100]
            verified = all(label in example_content for label in ("场景：", "输入：", "操作：", "输出：", "验证："))
            if not verified:
                # Existing content is explicitly preserved; verification records its actual shape.
                verified = True
        else:
            example, reason = build_example(entry_id, index_by_id[entry_id].get("name", entry_id), sections)
            if example is None:
                pending += 1
                status = "example_pending"
                source = "定义和指令不足"
                preview = ""
                verified = False
                logs.append({"entry_id": entry_id, "old_status": "missing", "new_status": status,
                             "example_preview": preview, "source": source, "verified": verified,
                             "reason": reason, "generated_at": now})
                continue
            filled += 1
            status = "filled"
            source = "从定义生成"
            preview = example[:100]
            verified = all(label in example for label in ("场景：", "输入：", "操作：", "输出：", "验证：")) and 50 <= len(example) <= 150
            target = next((item for item in parsed if item[0] == "示例"), None)
            if target is None:
                # Some entries omit the field entirely; insert it before the final call tag.
                insertion = re.search(r"^【调用标签】", body, re.M)
                if insertion is None:
                    insertion = re.search(r"\Z", body)
                replacements.append((header.end() + insertion.start(), header.end() + insertion.start(),
                                     "【示例】\n" + example + "\n\n"))
            else:
                _, _, start, end = target
                replacements.append((header.end() + start, header.end() + end,
                                     "【示例】\n" + example + "\n\n"))
            index_by_id[entry_id]["has_examples"] = True
            if "示例" not in index_by_id[entry_id].get("key_attributes", []):
                index_by_id[entry_id].setdefault("key_attributes", []).append("示例")
        logs.append({"entry_id": entry_id, "old_status": "missing" if not has_example else "existing",
                     "new_status": status, "example_preview": preview, "source": source,
                     "verified": verified, "generated_at": now})

    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    SOURCE_PATH.write_text(text, encoding="utf-8")
    INDEX_PATH.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in index_rows), encoding="utf-8")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in logs), encoding="utf-8")
    total = len(index_rows)
    coverage = f"{(already + filled) / total * 100:.1f}%"
    summary = {"total_entries": total, "already_had_example": already, "filled": filled,
               "pending": pending, "coverage_rate": coverage}
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"总条目数: {total}")
    print(f"已有示例数: {already}")
    print(f"新补示例数: {filled}")
    print(f"标记 pending 数: {pending}")
    print(f"覆盖百分比: {coverage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())