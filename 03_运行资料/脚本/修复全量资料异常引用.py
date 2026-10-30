"""Repair only audited malformed source references after strict readback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from 严格资料升级 import _resolve_ref


AUDIT_RELATIVE = Path("文档") / "证据" / "全量资料升级运行" / "20260817T061512Z-4bdf51c3-异常审计" / "exceptions.jsonl"
BINDINGS_RELATIVE = Path("文档") / "证据" / "全量资料解释词创作绑定.json"


def _replacement(row: dict[str, Any]) -> str:
    raw = row["source_ref"]["raw"]
    if row["source_kind"] == "资料库":
        return raw
    if row["source_kind"] == "类型系统":
        return f"原始资料/类型系统.txt:SECTION: {row['source_id']}"
    if row["source_kind"] == "类型连接":
        # The audit reference preserves the actual SOURCE filename. source_id may
        # be an object payload (for example TB-11278), so it is not a locator.
        locator = str(raw).split(":", 1)[1].rsplit("[", 1)[0]
        return f"原始资料/类型连接.txt:SOURCE: {locator}"
    raise ValueError(f"不支持的异常来源类型：{row['source_kind']}")


def repair(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    audit_rows = [json.loads(line) for line in (root / AUDIT_RELATIVE).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    bindings_path = root / BINDINGS_RELATIVE
    document = json.loads(bindings_path.read_text(encoding="utf-8-sig"))
    bindings = {str(row.get("binding_id")): row for row in document.get("records", []) if isinstance(row, dict)}
    changes: list[dict[str, str]] = []
    for audit in audit_rows:
        binding = bindings.get(str(audit["binding_id"]))
        if binding is None:
            raise ValueError(f"异常 binding_id 不在当前绑定基线：{audit['binding_id']}")
        replacement = _replacement(audit)
        item, error = _resolve_ref(root, replacement)
        if error or item is None:
            raise ValueError(f"{audit['binding_id']} 的修复引用无法完整回读：{error}")
        changes.append({"binding_id": str(audit["binding_id"]), "old_source_ref": str(binding.get("source_ref")), "new_source_ref": replacement})
    for change in changes:
        bindings[change["binding_id"]]["source_ref"] = change["new_source_ref"]
    bindings_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence = {"schema_version": "full-source-reference-repair-1.0", "repaired_count": len(changes), "changes": changes}
    (root / "文档" / "证据" / "全量资料异常引用修复记录.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps({"repaired_count": repair(args.project_root)["repaired_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())