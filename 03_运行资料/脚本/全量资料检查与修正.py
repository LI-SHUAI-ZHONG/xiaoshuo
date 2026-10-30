"""Check and normalize every source object without inventing story facts.

The six raw source files are immutable. This command creates a complete,
project-independent ledger and normalized evidence views. A field is repaired
only when its value can be derived from the source or an existing index;
otherwise it remains pending and blocks formal delivery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCES = {
    "资料库": ("原始资料/资料库.txt", "library"),
    "类型系统": ("原始资料/类型系统.txt", "type"),
    "类型连接": ("原始资料/类型连接.txt", "connection"),
    "动态网络": ("原始资料/动态网络.txt", "dynamic"),
    "静态网络": ("原始资料/静态网络.txt", "static"),
    "锚点网络": ("原始资料/锚点网络.txt", "anchor"),
}
PLACEHOLDER = re.compile(r"(?:^|[：:])\s*(?:无|暂无|待补充|待确认|未确认|待实现|pending|placeholder)\s*$", re.I)
ANCHOR = re.compile(r"\b(?:ID|M|S|P|B|E|C|T|D|A|L|U)\d+\.\d+\b")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(read(path))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    for line_no, line in enumerate(read(path).splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("record_type") != "header":
            value["_line"] = line_no
            rows.append(value)
    return rows


def is_empty(value: Any) -> bool:
    if value is None or value == "" or value == [] or value == {}:
        return True
    return isinstance(value, str) and bool(PLACEHOLDER.search(value.strip()))


def issue(ledger: list[dict[str, Any]], source: str, object_id: str, field: str,
          kind: str, action: str, before: Any, after: Any, evidence: str,
          status: str) -> None:
    ledger.append({"source": source, "object_id": object_id, "field": field,
                   "issue": kind, "action": action, "before": before,
                   "after": after, "evidence": evidence, "status": status})


def library_rows(root: Path, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = read(root / SOURCES["资料库"][0])
    # Only numbered entry headings are source objects. Section headings such
    # as "板块156 ..." are document structure, not library entries.
    raw_ids = set()
    for match in re.finditer(
        r"^(?:###\s*(?P<h3_number>\d+(?:\.\d+)?)[_：: ](?P<h3_name>[^\r\n]+)|"
        r"##\s*板块\s*(?P<section_number>\d+(?:\.\d+)?)[_：: ](?P<section_name>[^\r\n]+)|"
        r"\*\*(?P<bold_number>\d+(?:\.\d+)?)\s+(?P<bold_name>[^*\r\n]+)\*\*)\s*$",
        source,
        re.M,
    ):
        number = match.group("h3_number") or match.group("section_number") or match.group("bold_number")
        name = (match.group("h3_name") or match.group("section_name") or match.group("bold_name")).strip()
        if match.group("section_number") and not 129 <= float(number) <= 154:
            continue
        raw_ids.add(f"{number}_{name}")
    indexed = jsonl(root / "文档/资料库索引.jsonl")
    rows = []
    indexed_by_id = {str(x.get("entry_id")): x for x in indexed if x.get("entry_id")}
    for object_id in sorted(raw_ids | set(indexed_by_id)):
        source_row = indexed_by_id.get(object_id, {})
        row = dict(source_row)
        row["entry_id"] = object_id
        legacy_only = object_id not in raw_ids
        if legacy_only:
            row["source_status"] = "legacy_unmatched"
            row["quality_scope"] = "compatibility_only"
            rows.append(row)
            continue
        if not row.get("source_ref"):
            row["source_ref"] = {"file": "原始资料/资料库.txt", "locator": object_id}
            issue(ledger, "资料库", object_id, "source_ref", "missing", "derive", None, row["source_ref"], "资料库索引 entry_id 与原始资料条目标题对应", "repaired")
        for field in ("dependencies", "has_examples", "has_conditions"):
            if field not in row:
                issue(ledger, "资料库", object_id, field, "missing_index_record", "retain_pending", None, None, "原文条目存在但资料库索引没有该 entry_id", "pending")
        row["runtime_status"] = "candidate" if row.get("has_examples") is True else "pending"
        rows.append(row)
    return rows


def type_rows(root: Path, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    config = load_json(root / "配置/类型配置模板.json", {})
    rows = []
    for name, raw in (config.get("types") or {}).items():
        row = dict(raw) if isinstance(raw, dict) else {}
        row["type_name"] = name
        row["source_ref"] = row.get("source_ref") or {"file": "原始资料/类型系统.txt", "locator": name}
        for field in ("core_elements", "reader_params", "style_constraints", "length_rhythm"):
            if is_empty(row.get(field)):
                issue(ledger, "类型系统", name, field, "missing_or_pending", "retain_pending", row.get(field), row.get(field), "原始资料未提供可核验值", "pending")
        row["formal_fact_usable"] = not any(is_empty(row.get(f)) for f in ("core_elements", "style_constraints")) and row.get("source_status") == "cross_confirmed"
        rows.append(row)
    return rows


def recursive_objects(value: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(value, dict):
        if any(value.get(k) for k in ("id", "connection_id", "chain_id", "edge_id", "dynamic_edge_id")) or (value.get("source") and value.get("target")):
            found.append(value)
        for child in value.values():
            found.extend(recursive_objects(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursive_objects(child))
    return found


def connection_rows(root: Path, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize actual source connection objects, not just genre combinations."""
    source_path = root / SOURCES["类型连接"][0]
    source_text = read(source_path)
    decoder = json.JSONDecoder()
    rows = []
    seen: set[str] = set()
    position = 0
    id_fields = ("connection_id", "dynamic_combination_id", "static_combination_id", "rule_id")
    while position < len(source_text):
        start = source_text.find("{", position)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(source_text[start:])
        except json.JSONDecodeError:
            position = start + 1
            continue
        position = start + max(end, 1)
        if not isinstance(value, dict):
            continue
        object_id = next((str(value[field]) for field in id_fields if value.get(field)), "")
        if not object_id or object_id in seen:
            continue
        seen.add(object_id)
        line = source_text.count("\n", 0, start) + 1
        row = dict(value)
        row["normalized_id"] = object_id
        row["source_connection_id"] = object_id
        row["source_ref"] = {"file": SOURCES["类型连接"][0], "line": line, "locator": object_id}
        row["connection_kind"] = next((field.removesuffix("_id") for field in id_fields if value.get(field)), "connection")
        if not row.get("source_refs"):
            issue(ledger, "类型连接", object_id, "source_refs", "missing_or_pending", "retain_pending", None, None, "原始类型连接对象未提供来源回链", "pending")
        rows.append(row)
    if not rows:
        issue(ledger, "类型连接", "source", "object_extraction", "unparseable", "retain_pending", None, None, "未从原始资料提取到 JSON 连接对象", "pending")
    return rows


def network_rows(root: Path, name: str, filename: str, ledger: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    data = load_json(root / filename, {})
    if kind == "static" and isinstance(data, dict) and isinstance(data.get("source_index"), dict):
        flattened = []
        for source, block in data["source_index"].items():
            for target in (block or {}).get("targets", []):
                row = dict(target)
                row.setdefault("source", source)
                flattened.append(row)
        data = flattened
    rows = recursive_objects(data)
    normalized = []
    seen = set()
    for index, raw in enumerate(rows, 1):
        row = dict(raw)
        object_id = str(row.get("id") or row.get("edge_id") or row.get("chain_id") or row.get("dynamic_edge_id") or f"{kind}:{index}")
        key = (object_id, str(row.get("source")), str(row.get("target")), str(row.get("type")))
        if key in seen:
            issue(ledger, name, object_id, "identity", "duplicate", "exclude_duplicate", key, None, filename, "repaired")
            continue
        seen.add(key)
        row["normalized_id"] = object_id
        row["source_ref"] = row.get("source_ref") or f"{filename}:{index}"
        required = {"dynamic": ("source", "target", "condition", "effect"), "static": ("source", "target", "type"), "anchor": ()}[kind]
        for field in required:
            if is_empty(row.get(field)):
                issue(ledger, name, object_id, field, "missing_or_pending", "retain_pending", row.get(field), row.get(field), filename, "pending")
        normalized.append(row)
    return normalized


def anchor_rows(root: Path, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract the source anchor table without inventing scene-level evidence."""
    text = read(root / SOURCES["锚点网络"][0])
    rows: dict[str, dict[str, Any]] = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 5 or not ANCHOR.fullmatch(columns[0]):
            continue
        anchor_id, name, definition, trigger, category = columns[:5]
        rows[anchor_id] = {
            "normalized_id": anchor_id,
            "anchor_id": anchor_id,
            "name": name,
            "anchor_definition": definition,
            "trigger_condition": trigger,
            "category": category,
            "source_ref": {"file": SOURCES["锚点网络"][0], "line": line_no, "locator": anchor_id},
        }
    source_ids = sorted(set(ANCHOR.findall(text)))
    for anchor_id in source_ids:
        if anchor_id in rows:
            continue
        rows[anchor_id] = {
            "normalized_id": anchor_id,
            "anchor_id": anchor_id,
            "source_ref": {"file": SOURCES["锚点网络"][0], "locator": anchor_id},
        }
        issue(ledger, "锚点网络", anchor_id, "anchor_definition", "unparsed_source_row", "retain_pending", None, None, "原始锚点资料中存在 ID 但未匹配完整表格行", "pending")
    return [rows[anchor_id] for anchor_id in source_ids]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    out = root / "文档/证据/全量资料治理"
    out.mkdir(parents=True, exist_ok=True)
    ledger: list[dict[str, Any]] = []
    all_rows = {
        "资料库": library_rows(root, ledger),
        "类型系统": type_rows(root, ledger),
        "类型连接": connection_rows(root, ledger),
        "动态网络": network_rows(root, "动态网络", "网络完整数据/动态连接完整数据.json", ledger, "dynamic"),
        "静态网络": network_rows(root, "静态网络", "网络完整数据/静态连接完整数据.json", ledger, "static"),
        "锚点网络": anchor_rows(root, ledger),
    }
    snapshots = {}
    for name, (relative, _) in SOURCES.items():
        path = root / relative
        snapshots[name] = {"path": relative, "sha256": sha(path) if path.is_file() else None, "exists": path.is_file(), "line_count": len(read(path).splitlines()) if path.is_file() else 0}
    summary = {}
    for name, rows in all_rows.items():
        issues = [x for x in ledger if x["source"] == name]
        summary[name] = {"total_objects": len(rows), "repaired": sum(x["status"] == "repaired" for x in issues), "pending": sum(x["status"] == "pending" for x in issues), "blocking": sum(x["status"] == "pending" for x in issues), "status": "pending" if any(x["status"] == "pending" for x in issues) else "passed"}
        (out / f"{name}_规范化.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"schema_version": "full-source-governance-1.0", "generated_at": now(), "policy": "原始资料只读；不可证明字段保持pending；不新增类型组合或项目事实", "snapshots": snapshots, "summary": summary, "ledger_count": len(ledger), "formal_delivery": "blocked" if any(x["status"] == "pending" for x in ledger) else "candidate"}
    (out / "全量修正账本.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in ledger) + ("\n" if ledger else ""), encoding="utf-8")
    (out / "全量检查报告.json").write_text(json.dumps({**report, "issues": ledger}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 六类资料全量检查与修正结果", "", f"生成时间：{report['generated_at']}", "", "| 资料 | 全量对象 | 已修正（确定性） | 待确认/阻断 | 状态 |", "|---|---:|---:|---:|---|"]
    lines += [f"| {n} | {v['total_objects']} | {v['repaired']} | {v['pending']} | {v['status']} |" for n, v in summary.items()]
    lines += ["", "## 规则", "", "原始资料未覆盖；修正仅写入规范化证据视图。`pending` 不得作为正式事实交付。", "", "## 输出", "", "- `全量检查报告.json`：完整条目级报告", "- `全量修正账本.jsonl`：每一条问题、动作和来源依据", "- `*_规范化.json`：去重、补齐可确定来源引用后的派生视图"]
    (out / "全量检查与修正结果.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "summary": summary, "ledger_count": len(ledger)}, ensure_ascii=False))
    return 1 if report["formal_delivery"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())