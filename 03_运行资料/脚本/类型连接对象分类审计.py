"""Classify type-connection references without changing the binding baseline."""
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .严格资料升级 import _resolve_ref
except ImportError:  # Supports direct execution from the scripts directory.
    from 严格资料升级 import _resolve_ref


BINDING_FILE = Path("文档") / "证据" / "全量资料解释词创作绑定.json"
SOURCE_FILE = "原始资料/类型连接.txt"
STABLE_ID_FIELDS = ("connection_id", "dynamic_combination_id", "static_connection_id", "id", "rule_id", "template_id")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("绑定基线根对象必须为 JSON 对象")
    return value


def _ref_parts(source_ref: str) -> tuple[str, int | None]:
    match = re.fullmatch(r"[^:]+:([^\[]+)\[(\d+)\]", source_ref)
    if not match:
        return "", None
    return match.group(1), int(match.group(2))


def _identity(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"stable_id_fields": [], "stable_ids": {}, "classification": "non_object"}
    values = {field: item[field] for field in STABLE_ID_FIELDS if isinstance(item.get(field), str) and item[field].strip()}
    if values:
        return {"stable_id_fields": sorted(values), "stable_ids": values, "classification": "entity_with_stable_id"}
    return {"stable_id_fields": [], "stable_ids": {}, "classification": "structural_object_without_stable_id"}


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    rows = [row for row in _read(root / BINDING_FILE).get("records", []) if isinstance(row, dict) and row.get("source_kind") == "类型连接"]
    findings: list[dict[str, Any]] = []
    for row in rows:
        source_ref = str(row.get("source_ref") or "")
        block, index = _ref_parts(source_ref)
        item, error = _resolve_ref(root, source_ref)
        identity = _identity(item) if error is None else {"stable_id_fields": [], "stable_ids": {}, "classification": "unresolved"}
        findings.append({
            "binding_id": row.get("binding_id"),
            "source_id": row.get("source_id"),
            "source_ref": source_ref,
            "source_block": block,
            "array_index_zero_based": index,
            "status": "quarantined" if error else "classified",
            "resolution_error": error,
            "object_keys": sorted(item) if isinstance(item, dict) else [],
            **identity,
            "migration_decision": "eligible_for_identity_review" if error is None and identity["classification"] == "entity_with_stable_id" else "remain_quarantined",
        })
    counts = Counter(item["migration_decision"] for item in findings)
    by_block: dict[str, dict[str, int]] = {}
    for item in findings:
        block = item["source_block"] or "<unparsed>"
        by_block.setdefault(block, {})[item["migration_decision"]] = by_block.setdefault(block, {}).get(item["migration_decision"], 0) + 1
    report = {
        "schema_version": "type-connection-object-classification-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "type_connection_bindings_only; read_only_classification; no_binding_or_source_changes",
        "binding_count": len(rows),
        "decision_counts": dict(counts),
        "source_block_decision_counts": by_block,
        "stable_id_fields_considered": list(STABLE_ID_FIELDS),
        "policy": "规则、枚举、字段说明和模板等结构对象不能用数组位置伪造实体身份；只有来源对象自带稳定标识且完整回读成功的记录，才进入后续身份复核候选。",
        "findings": findings,
    }
    target = root / "文档" / "证据" / "类型连接对象分类审计报告.json"
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = audit(args.project_root)
    print(json.dumps({"binding_count": report["binding_count"], "decision_counts": report["decision_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())