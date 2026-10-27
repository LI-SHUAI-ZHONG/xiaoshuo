"""Rebuild the library index from the raw entry blocks, preserving legacy rows.

The raw library is read-only. The runtime index is backed up before writing.
No dependency or example text is invented: dependencies come from explicit
references in the entry block, while example/condition flags are derived from
their corresponding labeled sections.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "原始资料" / "资料库.txt"
INDEX = ROOT / "文档" / "资料库索引.jsonl"
EVIDENCE = ROOT / "文档" / "证据"
BACKUP_DIR = EVIDENCE / "回归历史"

ENTRY_RE = re.compile(
    r"^(?:###\s*(?P<h3_number>\d+(?:\.\d+)?)[_：: ](?P<h3_name>[^\r\n]+)|"
    r"##\s*板块\s*(?P<section_number>\d+(?:\.\d+)?)[_：: ](?P<section_name>[^\r\n]+)|"
    r"\*\*(?P<bold_number>\d+(?:\.\d+)?)\s+(?P<bold_name>[^*\r\n]+)\*\*)\s*$",
    re.M,
)
FIELD_RE = re.compile(r"^【([^】]+)】\s*$", re.M)
ID_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?_[^\s，。；：:】、)]+)")
FIELD_NAMES = ("定义", "调用条件", "指令", "设计指令", "写作指令", "分级标准", "场景变体", "判定标准", "修正指南", "示例", "反面案例", "关联板块", "关联路径", "优先级", "例外处理", "调用标签")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_index() -> list[dict]:
    rows = []
    if INDEX.is_file():
        for line in INDEX.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and value.get("entry_id"):
                rows.append(value)
    return rows


def section_values(block: str) -> dict[str, str]:
    matches = list(FIELD_RE.finditer(block))
    values = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        if name not in FIELD_NAMES:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        values[name] = block[match.end():end].strip()
    return values


def meaningful(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip() not in {"无", "暂无", "待补充", "待确认"})


def sort_key(entry_id: str) -> tuple[float, str]:
    number, _, name = entry_id.partition("_")
    return (float(number), name)


def parse_raw() -> dict[str, dict]:
    text = RAW.read_text(encoding="utf-8-sig")
    matches = list(ENTRY_RE.finditer(text))
    parsed = {}
    for index, match in enumerate(matches):
        number = match.group("h3_number") or match.group("section_number") or match.group("bold_number")
        name = (match.group("h3_name") or match.group("section_name") or match.group("bold_name")).strip()
        if match.group("section_number") and not 129 <= float(number) <= 154:
            continue
        entry_id = f"{number}_{name}"
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start():end]
        fields = section_values(block)
        explicit_ids = []
        for value in (fields.get("关联板块", ""), fields.get("关联路径", ""), fields.get("调用条件", ""), fields.get("指令", "")):
            explicit_ids.extend(ID_RE.findall(value or ""))
        dependencies = []
        for candidate in explicit_ids:
            if candidate != entry_id and candidate not in dependencies:
                dependencies.append(candidate)
        if "关联板块" in fields and meaningful(fields["关联板块"]):
            parent = re.search(r"\b(\d+)\.", fields["关联板块"])
            if parent:
                parent_id = parent.group(1) + ".1"
                if parent_id != entry_id and parent_id not in dependencies:
                    dependencies.append(parent_id)
        section = entry_id.split(".", 1)[0]
        key_attributes = [name for name in FIELD_NAMES if meaningful(fields.get(name))]
        parsed[entry_id] = {
            "entry_id": entry_id,
            "name": entry_id.split("_", 1)[1] if "_" in entry_id else entry_id,
            "type": "规则" if meaningful(fields.get("判定标准")) or meaningful(fields.get("修正指南")) else "概念",
            "key_attributes": key_attributes,
            "dependencies": [{"entry_id": item, "type": "原文明确引用"} for item in dependencies],
            "has_examples": meaningful(fields.get("示例")),
            "has_conditions": meaningful(fields.get("调用条件")),
            "source_ref": {"file": "原始资料/资料库.txt", "locator": entry_id, "line_start": text[:match.start()].count("\n") + 1},
            "source_status": "raw_indexed",
            "raw_section": section,
        }
    return parsed


def main() -> int:
    raw = parse_raw()
    old_rows = load_index()
    old_by_id = {str(row["entry_id"]): row for row in old_rows}
    merged = []
    changes = []
    for entry_id in sorted(set(raw) | set(old_by_id), key=sort_key):
        if entry_id in raw:
            row = dict(old_by_id.get(entry_id, {}))
            generated = raw[entry_id]
            for field, value in generated.items():
                if field in {"entry_id", "source_ref", "source_status", "raw_section"} or field not in row or row.get(field) in (None, ""):
                    before = row.get(field)
                    row[field] = value
                    if before != value:
                        changes.append({"entry_id": entry_id, "field": field, "before": before, "after": value, "reason": "从原始资料条目块确定性提取"})
            row.setdefault("assigned_to_module", "pending")
            row.setdefault("load_order", 0)
            row["source_status"] = "raw_indexed"
            row.pop("legacy_reason", None)
        else:
            row = dict(old_by_id[entry_id])
            row["source_status"] = "legacy_unmatched"
            row["legacy_reason"] = "旧索引存在，但当前原始资料没有同名条目标题；保留以兼容既有运行引用"
            changes.append({"entry_id": entry_id, "field": "source_status", "before": old_by_id[entry_id].get("source_status"), "after": "legacy_unmatched", "reason": "兼容保留，不删除"})
        merged.append(row)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"资料库索引_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    shutil.copy2(INDEX, backup)
    INDEX.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in merged) + "\n", encoding="utf-8", newline="\n")
    report = {"schema_version": "library-index-repair-1.0", "generated_at": now(), "raw_entry_count": len(raw), "old_index_count": len(old_rows), "new_index_count": len(merged), "raw_missing_before": len(set(raw) - set(old_by_id)), "legacy_preserved": len(set(old_by_id) - set(raw)), "backup": str(backup).replace("\\", "/"), "changes": changes}
    (EVIDENCE / "资料库索引修复报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "资料库索引修复日志.jsonl").write_text("\n".join(json.dumps(change, ensure_ascii=False) for change in changes) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("raw_entry_count", "old_index_count", "new_index_count", "raw_missing_before", "legacy_preserved", "backup")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())