"""Build verifiable, non-entity references for structural type-connection objects."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .严格资料升级 import _resolve_ref
except ImportError:
    from 严格资料升级 import _resolve_ref


BINDING_FILE = Path("文档") / "证据" / "全量资料解释词创作绑定.json"
SOURCE_FILE = "原始资料/类型连接.txt"
STRUCTURAL_BLOCK_CLASSES = {
    "类型静态搭配库.json": "type_static_combination",
    "类型静态连接字段说明.json": "type_connection_field_definition",
    "类型连接枚举.json": "type_connection_enum",
    "类型连接验证规则.json": "type_connection_validation_rule",
    "类型组合约束.json": "type_combination_constraint",
}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("绑定基线根对象必须为 JSON 对象")
    return value


def _ref_parts(source_ref: str) -> tuple[str, int | None]:
    match = re.fullmatch(r"[^:]+:([^\[]+)\[(\d+)\]", source_ref)
    return (match.group(1), int(match.group(2))) if match else ("", None)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _class_for(block: str, item: Any) -> str:
    if block in STRUCTURAL_BLOCK_CLASSES:
        return STRUCTURAL_BLOCK_CLASSES[block]
    if isinstance(item, dict):
        if any(key.endswith("_rule_ids") or key.endswith("_rules") for key in item):
            return "connection_rule_set"
        if any(key.endswith("_template_id") or key == "template" for key in item):
            return "connection_template_reference"
    return "structural_connection_object"


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    rows = [row for row in _read(root / BINDING_FILE).get("records", []) if isinstance(row, dict) and row.get("source_kind") == "类型连接"]
    findings: list[dict[str, Any]] = []
    hashes = Counter()
    for row in rows:
        source_ref = str(row.get("source_ref") or "")
        block, index = _ref_parts(source_ref)
        item, error = _resolve_ref(root, source_ref)
        object_hash = _hash(item) if error is None else None
        if object_hash:
            hashes[(block, object_hash)] += 1
        object_class = _class_for(block, item)
        protocol_ref = {
            "source_file": SOURCE_FILE,
            "source_block": block or None,
            "array_index_zero_based": index,
            "object_sha256": object_hash,
            "object_class": object_class,
        }
        findings.append({
            "binding_id": row.get("binding_id"),
            "legacy_source_id": row.get("source_id"),
            "source_ref": source_ref,
            "resolution_error": error,
            "protocol_reference": protocol_ref,
            "decision": "structural_reference_ready" if error is None and block else "remain_quarantined",
            "permitted_use": "structural_rule_audit_only" if error is None and block else "quarantine_only",
        })
    decision_counts = Counter(row["decision"] for row in findings)
    block_counts: dict[str, dict[str, int]] = {}
    for row in findings:
        block = str(row["protocol_reference"].get("source_block") or "<unparsed>")
        block_counts.setdefault(block, {})[row["decision"]] = block_counts.setdefault(block, {}).get(row["decision"], 0) + 1
    duplicate_hashes = sorted(f"{block}:{digest}" for (block, digest), count in hashes.items() if count > 1)
    report = {
        "schema_version": "type-connection-structural-reference-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "type_connection_bindings_only; read_only; no_binding_or_source_changes",
        "binding_count": len(rows),
        "decision_counts": dict(decision_counts),
        "source_block_decision_counts": block_counts,
        "protocol": {
            "reference_fields": ["source_file", "source_block", "array_index_zero_based", "object_sha256", "object_class"],
            "array_position_is_identity": False,
            "allowed_classes": sorted(set(STRUCTURAL_BLOCK_CLASSES.values()) | {"connection_rule_set", "connection_template_reference", "structural_connection_object"}),
            "permitted_use": "规则、约束和模板的来源级审计；不得作为实体稳定身份、项目类型确认或正文事实依据。",
        },
        "duplicate_object_hashes_within_block": duplicate_hashes,
        "findings": findings,
    }
    target = root / "文档" / "证据" / "类型连接结构对象引用审计报告.json"
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