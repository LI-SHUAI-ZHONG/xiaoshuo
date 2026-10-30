"""Read-only retrieval validation for the library and type-connection sources.

This validator separates file reachability, object recovery and workflow policy.
It never changes the raw sources or the binding baseline.  A recovered object is
kept usable for retrieval even when a legacy locator or business identity is
not exact.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BINDINGS = Path("文档") / "证据" / "全量资料解释词创作绑定.json"
OUTPUT_DIR = Path("文档") / "证据" / "资料调取验证"
LIBRARY_HEADING = re.compile(r"^(?P<marks>#{2,3})\s*(?:板块\s*)?(?P<id>\d+(?:\.\d+)?)[_：: ](?P<title>.+?)\s*$")
TYPE_HEADER = re.compile(r"^SOURCE:\s*(?P<name>[^\r\n]+)\r?$", re.MULTILINE)
TYPE_REF = re.compile(r"^原始资料/类型连接\.txt:(?P<block>[^\[\]:]+)\[(?P<index>\d+)\]$")
TYPE_ROOT_REF = re.compile(r"^原始资料/类型连接\.txt:SOURCE:\s*(?P<block>[^\r\n]+)$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_ref(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else parsed


def norm(value: Any) -> str:
    text = str(value or "").strip().replace("　", " ")
    text = re.sub(r"\s+", " ", text)
    return text.replace("_", " ").replace("：", ":").strip().lower()


def library_entries(path: Path) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = LIBRARY_HEADING.match(line.strip())
        if match:
            headers.append((index, match))
    entries: list[dict[str, Any]] = []
    by_line: dict[int, dict[str, Any]] = {}
    for position, (start, match) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        entry_id = f"{match.group('id')}_{match.group('title').strip()}"
        item = {
            "entry_id": entry_id,
            "line_start": start + 1,
            "line_end": end,
            "heading": lines[start].strip(),
            "content": "\n".join(lines[start:end]),
            "title_key": norm(entry_id),
        }
        entries.append(item)
        by_line[start + 1] = item
    return entries, by_line


def resolve_library(root: Path, row: dict[str, Any], entries: list[dict[str, Any]], by_line: dict[int, dict[str, Any]]) -> dict[str, Any]:
    path = root / "原始资料" / "资料库.txt"
    ref = parse_ref(row.get("source_ref"))
    locator = ref.get("locator") if isinstance(ref, dict) else None
    line_start = ref.get("line_start") if isinstance(ref, dict) else None
    candidates = [item for item in entries if locator and item["title_key"] == norm(locator)]
    method = "exact_heading" if len(candidates) == 1 else None
    if not candidates and isinstance(line_start, int) and line_start in by_line:
        candidates = [by_line[line_start]]
        method = "line_heading_recovery"
    if not candidates and isinstance(line_start, int):
        nearby = [item for item in entries if abs(item["line_start"] - line_start) <= 3]
        if len(nearby) == 1:
            candidates = nearby
            method = "line_neighborhood_recovery"
    if len(candidates) != 1:
        return {"retrieval_status": "ambiguous" if len(candidates) > 1 else "unresolved", "candidates": [item["entry_id"] for item in candidates], "reason": "资料库标题、行号邻域无法唯一确定对象"}
    item = candidates[0]
    return {"retrieval_status": "exact" if method == "exact_heading" else "recovered", "retrieval_method": method, "resolved_locator": item["entry_id"], "line_start": item["line_start"], "line_end": item["line_end"], "content_sha256": hashlib.sha256(item["content"].encode("utf-8")).hexdigest(), "content_preview": item["content"][:240]}


def type_sections(path: Path) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    headers = list(TYPE_HEADER.finditer(text))
    sections: dict[str, dict[str, Any]] = {}
    for position, header in enumerate(headers):
        end = headers[position + 1].start() if position + 1 < len(headers) else len(text)
        body = text[header.end():end].lstrip("= \t\r\n")
        name = header.group("name").strip()
        value: Any = None
        parse_status = "raw_text_only"
        try:
            value = json.JSONDecoder().raw_decode(body)[0]
            parse_status = "structured"
        except json.JSONDecodeError:
            pass
        sections[name] = {"text": body, "value": value, "parse_status": parse_status, "header_index": position + 1}
    return sections


def resolve_type(row: dict[str, Any], sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_ref = str(row.get("source_ref") or "")
    root_match = TYPE_ROOT_REF.fullmatch(source_ref)
    if root_match:
        block = root_match.group("block").strip()
        section = sections.get(block)
        if section is None:
            return {"retrieval_status": "unresolved", "reason": f"不存在 SOURCE 块: {block}"}
        value = section["value"]
        if section["parse_status"] == "structured":
            preview = json.dumps(value, ensure_ascii=False)
            return {"retrieval_status": "exact", "retrieval_method": "source_block_root_reference", "source_block": block, "source_index": 1, "object_type": type(value).__name__, "object_keys": sorted(value) if isinstance(value, dict) else [], "content_sha256": hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(), "content_preview": preview[:400]}
        return {"retrieval_status": "raw_text_reachable", "retrieval_method": "source_block_root_raw_text", "source_block": block, "source_index": 1, "object_type": "raw_text", "content_sha256": hashlib.sha256(section["text"].encode("utf-8")).hexdigest(), "content_preview": section["text"][:400], "reason": "SOURCE 根块可读取，但结构化 JSON 未成功解析"}
    match = TYPE_REF.fullmatch(source_ref)
    if not match:
        return {"retrieval_status": "unresolved", "reason": "类型连接 source_ref 不是受控 SOURCE 块数组格式"}
    block, index = match.group("block"), int(match.group("index"))
    section = sections.get(block)
    if section is None:
        return {"retrieval_status": "unresolved", "reason": f"不存在 SOURCE 块: {block}"}
    value = section["value"]
    if isinstance(value, list) and 1 <= index <= len(value):
        item = value[index - 1]
        return {"retrieval_status": "exact" if section["parse_status"] == "structured" else "recovered", "retrieval_method": "source_block_array", "source_block": block, "source_index": index, "object_type": type(item).__name__, "object_keys": sorted(item) if isinstance(item, dict) else [], "content_sha256": hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(), "content_preview": json.dumps(item, ensure_ascii=False)[:400]}
    if isinstance(value, dict) and index == 1:
        return {"retrieval_status": "exact", "retrieval_method": "source_block_root", "source_block": block, "source_index": 1, "object_type": "dict", "object_keys": sorted(value), "content_sha256": hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(), "content_preview": json.dumps(value, ensure_ascii=False)[:400]}
    if section["parse_status"] == "raw_text_only":
        return {"retrieval_status": "raw_text_reachable", "retrieval_method": "source_block_raw_text", "source_block": block, "source_index": index, "object_type": "raw_text", "content_sha256": hashlib.sha256(section["text"].encode("utf-8")).hexdigest(), "content_preview": section["text"][:400], "reason": "SOURCE 块可读取，但结构化 JSON 未成功解析，需按原文复核数组边界"}
    return {"retrieval_status": "unresolved", "reason": f"SOURCE 块 {block} 不含索引 {index}"}


def usage(kind: str, content: str) -> list[str]:
    if kind == "资料库":
        labels = ["创作检索"]
        if re.search(r"命名|术语|名称|称谓", content):
            labels += ["人物命名", "术语规范"]
        return labels
    if re.search(r"字段说明|枚举|验证规则|模板|模式库|搭配库", content, re.I):
        return ["类型连接规则检索", "模板与字段说明参考"]
    labels = ["类型关系检索", "机制与冲突设计"]
    if re.search(r"condition|trigger|条件|触发", content, re.I):
        labels.append("激活条件参考")
    if re.search(r"cost|代价|冲突|限制", content, re.I):
        labels.append("代价与约束参考")
    return labels


def run(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    bindings_path = root / BINDINGS
    document = json.loads(bindings_path.read_text(encoding="utf-8-sig"))
    rows = [row for row in document.get("records", []) if isinstance(row, dict) and row.get("source_kind") in {"资料库", "类型连接"}]
    library_path = root / "原始资料" / "资料库.txt"
    type_path = root / "原始资料" / "类型连接.txt"
    library = library_entries(library_path) if library_path.is_file() else ([], {})
    sections = type_sections(type_path) if type_path.is_file() else {}
    results = []
    for row in rows:
        kind = row["source_kind"]
        result = resolve_library(root, row, library[0], library[1]) if kind == "资料库" else resolve_type(row, sections)
        preview = " ".join((str(result.get("content_preview") or ""), str(row.get("source_id") or ""), str(row.get("source_ref") or "")))
        result.update({"binding_id": row.get("binding_id"), "source_id": row.get("source_id"), "source_kind": kind, "source_ref": row.get("source_ref"), "source_file_status": "reachable" if (library_path if kind == "资料库" else type_path).is_file() else "missing", "usage_scope": usage(kind, preview), "audit_status": "not_a_workflow_permission_decision", "formal_prose_consumption": False})
        results.append(result)
    counts = Counter((row["source_kind"], row["retrieval_status"]) for row in results)
    report = {"schema_version": "source-retrieval-validation-1.0", "generated_at": now(), "scope": "library_and_type_connection_retrieval_only", "raw_sources": {"library": {"path": str((library_path).relative_to(root)).replace("\\", "/"), "sha256": sha256(library_path) if library_path.is_file() else None, "entry_count": len(library[0])}, "type_connections": {"path": str(type_path.relative_to(root)).replace("\\", "/"), "sha256": sha256(type_path) if type_path.is_file() else None, "source_block_count": len(sections)}}, "binding_count": len(results), "status_counts": {f"{kind}:{status}": count for (kind, status), count in sorted(counts.items())}, "policy": "调取可用性与审计/授权/正文消费状态分离；可回读的原始资料不因派生审计状态而失去检索用途。", "status": "passed" if all(row["retrieval_status"] not in {"unresolved", "ambiguous"} for row in results) else "needs_review"}
    output = root / OUTPUT_DIR
    output.mkdir(parents=True, exist_ok=True)
    (output / "资料库与类型连接调取验证报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "资料库与类型连接调取结果.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = run(args.project_root)
    print(json.dumps({"status": report["status"], "binding_count": report["binding_count"], "status_counts": report["status_counts"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())