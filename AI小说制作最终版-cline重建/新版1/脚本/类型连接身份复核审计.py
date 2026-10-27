"""Verify entity-like type-connection IDs without migrating any binding."""
from __future__ import annotations

import argparse
import json
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
STABLE_ID_FIELDS = ("connection_id", "dynamic_combination_id", "static_connection_id", "id", "rule_id", "template_id")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("绑定基线根对象必须为 JSON 对象")
    return value


def _ref_block(source_ref: str) -> str | None:
    marker = ":"
    if marker not in source_ref:
        return None
    value = source_ref.rsplit(marker, 1)[-1]
    return value.split("[", 1)[0] if "[" in value else None


def _stable_ids(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        return {}
    return {field: str(item[field]).strip() for field in STABLE_ID_FIELDS if isinstance(item.get(field), str) and item[field].strip()}


def audit(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    bindings = _read(root / BINDING_FILE).get("records", [])
    rows = [row for row in bindings if isinstance(row, dict) and row.get("source_kind") == "类型连接"]
    findings: list[dict[str, Any]] = []
    for row in rows:
        source_ref = str(row.get("source_ref") or "")
        item, resolution_error = _resolve_ref(root, source_ref)
        stable_ids = _stable_ids(item) if resolution_error is None else {}
        source_id = str(row.get("source_id") or "")
        matching_fields = [field for field, value in stable_ids.items() if value == source_id]
        errors: list[str] = []
        if resolution_error:
            errors.append(resolution_error)
        if not stable_ids:
            errors.append("来源对象缺少受控稳定身份字段")
        if not matching_fields:
            errors.append("绑定 source_id 未匹配来源对象稳定身份")
        decision = "identity_verified" if not errors else "remain_quarantined"
        findings.append({
            "binding_id": row.get("binding_id"),
            "source_id": row.get("source_id"),
            "source_ref": source_ref,
            "source_block": _ref_block(source_ref),
            "stable_id_fields": sorted(stable_ids),
            "stable_ids": stable_ids,
            "matching_identity_fields": matching_fields,
            "errors": errors,
            "decision": decision,
            "migration_allowed": False,
            "activation_allowed": False,
        })
    decision_counts = Counter(row["decision"] for row in findings)
    field_counts = Counter(field for row in findings if row["decision"] == "identity_verified" for field in row["matching_identity_fields"])
    report = {
        "schema_version": "type-connection-identity-review-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "type_connection_bindings_only; read_only_identity_verification; no_binding_or_source_changes",
        "binding_count": len(rows),
        "decision_counts": dict(decision_counts),
        "matching_identity_field_counts": dict(field_counts),
        "stable_id_fields_considered": list(STABLE_ID_FIELDS),
        "policy": "只有对象自带稳定 ID 且绑定 source_id 精确匹配时才标记 identity_verified；该标记不等于迁移、项目采用或正文激活许可。",
        "source_file": SOURCE_FILE,
        "findings": findings,
    }
    target = root / "文档" / "证据" / "类型连接身份复核审计报告.json"
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