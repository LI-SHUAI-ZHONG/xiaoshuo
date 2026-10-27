"""Read-only integrity audit for every registered source binding."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .严格资料升级 import SOURCE_FILE_BY_KIND, _identity_error, _resolve_ref
except ImportError:  # Supports direct execution from the scripts directory.
    from 严格资料升级 import SOURCE_FILE_BY_KIND, _identity_error, _resolve_ref


BINDING_FILE = Path("文档") / "证据" / "全量资料解释词创作绑定.json"
ISOLATED_KIND = "类型系统"
CHECKPOINT_EVERY = 100


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("绑定基线根对象必须为 JSON 对象")
    return value


def _write_report(path: Path, report: dict[str, Any]) -> None:
    """Replace the report atomically so an interrupted audit leaves valid JSON."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _identity_errors(row: dict[str, Any], item: Any, source_position: int | None = None) -> list[str]:
    kind, source_id = str(row.get("source_kind") or ""), str(row.get("source_id") or "")
    errors: list[str] = []
    if kind == "资料库" and isinstance(item, dict) and item.get("locator") != source_id:
        errors.append("source_id 与资料库 locator 不一致")
    elif kind == "锚点网络" and isinstance(item, dict) and item.get("anchor_id") != source_id:
        errors.append("source_id 与锚点网络 anchor_id 不一致")
    elif kind == "动态网络" and isinstance(item, dict) and item.get("id") != source_id:
        errors.append("source_id 与动态网络 id 不一致")
    elif kind == "静态网络" and isinstance(item, dict):
        if source_position is None:
            errors.append("静态网络 source_ref 未包含可核验的数组位置")
        else:
            expected = f"STATIC:{item.get('source')}->{item.get('target')}#{source_position + 1}"
            if expected != source_id:
                errors.append("source_id 与静态网络 source/target/数组位置不一致")
    else:
        error = _identity_error(kind, source_id, str(row.get("source_ref") or ""), item)
        if error:
            errors.append(error)
    return errors


def audit(project_root: str | Path, checkpoint_every: int = CHECKPOINT_EVERY) -> dict[str, Any]:
    if checkpoint_every < 1:
        raise ValueError("checkpoint_every 必须为正整数")
    root = Path(project_root).expanduser().resolve()
    binding_path = root / BINDING_FILE
    target = root / "文档" / "证据" / "全绑定来源完整性审计报告.json"
    bindings = _read(binding_path)
    rows = [row for row in bindings.get("records", []) if isinstance(row, dict)]
    seen = Counter(str(row.get("binding_id") or "") for row in rows)
    findings: list[dict[str, Any]] = []
    kind_counts: dict[str, Counter[str]] = {}
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def report(state: str, processed_count: int, last_binding_id: str | None = None) -> dict[str, Any]:
        counts = Counter(item["status"] for item in findings)
        return {
            "schema_version": "all-binding-source-integrity-audit-1.1",
            "started_at": started_at,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "audit_state": state,
            "binding_file": str(binding_path),
            "binding_count": len(rows),
            "processed_count": processed_count,
            "last_processed_binding_id": last_binding_id,
            "status_counts": dict(counts),
            "source_kind_status_counts": {kind: dict(counts) for kind, counts in sorted(kind_counts.items())},
            "quarantined_findings": [item for item in findings if item["status"] == "quarantined"],
            "isolated_type_index_count": counts["isolated_legacy_index"],
            "policy": "类型系统名称索引的 matched_lines 保持隔离；其余来源必须具备可回读的完整对象边界和可核验身份。审计不修改来源、绑定或项目类型。",
            "status": "running" if state == "running" else ("passed" if not counts["quarantined"] else "quarantined"),
        }

    _write_report(target, report("running", 0))
    for number, row in enumerate(rows, start=1):
        binding_id, kind, source_ref = str(row.get("binding_id") or ""), str(row.get("source_kind") or ""), str(row.get("source_ref") or "")
        errors: list[str] = []
        if not binding_id or seen[binding_id] != 1:
            errors.append("binding_id 缺失或重复")
        if kind not in SOURCE_FILE_BY_KIND:
            errors.append("未知 source_kind")
        elif SOURCE_FILE_BY_KIND[kind] not in source_ref:
            errors.append("source_ref 与 source_kind 的受控文件映射不一致")
        item, resolution_error = _resolve_ref(root, source_ref)
        if resolution_error:
            errors.append(resolution_error)
        elif kind != ISOLATED_KIND:
            position = None
            if kind == "静态网络" and source_ref.endswith("]"):
                try:
                    position = int(source_ref.rsplit("[", 1)[1][:-1])
                except ValueError:
                    pass
            errors.extend(_identity_errors(row, item, position))
        if kind == ISOLATED_KIND:
            status = "isolated_legacy_index" if "matched_lines" in source_ref else "quarantined"
        else:
            status = "passed" if not errors else "quarantined"
        findings.append({"binding_id": binding_id, "source_id": row.get("source_id"), "source_kind": kind, "source_ref": source_ref, "status": status, "errors": errors})
        kind_counts.setdefault(kind, Counter())[status] += 1
        if number % checkpoint_every == 0:
            _write_report(target, report("running", number, binding_id))
    completed = report("completed", len(rows), str(rows[-1].get("binding_id")) if rows else None)
    _write_report(target, completed)
    return completed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = audit(args.project_root)
    print(json.dumps({key: report[key] for key in ("status", "binding_count", "status_counts", "isolated_type_index_count")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())