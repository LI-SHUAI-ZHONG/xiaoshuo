"""Run the canonical source resolver over the current binding baseline.

The command is audit-only: it writes new evidence under a dedicated directory
and does not modify raw material, bindings, or historical audit reports.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .来源解析器 import prepare_source_cache, resolve
except ImportError:
    from 来源解析器 import prepare_source_cache, resolve


BINDINGS = Path("文档") / "证据" / "全量资料解释词创作绑定.json"
OUTPUT = Path("文档") / "证据" / "全量来源解析审计"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def audit(root: str | Path, source_kinds: set[str] | None = None, start: int = 0, limit: int | None = None) -> dict[str, Any]:
    project = Path(root).expanduser().resolve()
    prepared_sources = prepare_source_cache(project, source_kinds)
    binding_path = project / BINDINGS
    document = json.loads(binding_path.read_text(encoding="utf-8-sig"))
    all_rows = [row for row in document.get("records", []) if isinstance(row, dict) and (source_kinds is None or str(row.get("source_kind")) in source_kinds)]
    if start < 0 or start > len(all_rows):
        raise ValueError("start 超出批次范围")
    rows = all_rows[start:] if limit is None else all_rows[start:start + limit]
    scope_name = "全量" if source_kinds is None else "批次_" + "_".join(sorted(source_kinds))
    if source_kinds is not None and (start or limit is not None):
        scope_name += f"_{start}_{len(rows)}"
    output = project / OUTPUT / scope_name
    output.mkdir(parents=True, exist_ok=True)
    results_path = output / "全量来源解析结果.jsonl"
    temporary_results_path = results_path.with_suffix(results_path.suffix + ".tmp")
    results: list[dict[str, Any]] = []
    with temporary_results_path.open("w", encoding="utf-8", newline="\n") as handle:
        for number, row in enumerate(rows, start=1):
            result = resolve(project, row)
            results.append(result)
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            if number % 500 == 0:
                handle.flush()
    temporary_results_path.replace(results_path)
    status_counts = Counter(str(row.get("resolution_status")) for row in results)
    kind_counts: dict[str, dict[str, int]] = {}
    method_counts = Counter()
    error_counts = Counter()
    for row in results:
        kind = str(row.get("source_kind") or "")
        status = str(row.get("resolution_status"))
        kind_counts.setdefault(kind, Counter())[status] += 1
        for method in row.get("resolution_methods", []):
            method_counts[method] += 1
        for error in row.get("errors", []):
            error_counts[error] += 1
    report = {
        "schema_version": "canonical-source-resolution-audit-1.0",
        "generated_at": now(),
        "scope": "all_current_bindings_read_only; no_source_binding_or_workflow_changes",
        "binding_file": str(binding_path).replace("\\", "/"),
        "binding_count": len(rows),
        "batch_start": start,
        "batch_total_count": len(all_rows),
        "source_kinds_scope": sorted(source_kinds) if source_kinds is not None else "all",
        "prepared_sources": prepared_sources,
        "status_counts": dict(status_counts),
        "source_kind_status_counts": {kind: dict(counts) for kind, counts in sorted(kind_counts.items())},
        "resolution_method_counts": dict(method_counts),
        "error_counts": dict(error_counts),
        "workflow_allowed_count": sum(1 for row in results if row.get("workflow_allowed")),
        "policy": "resolved 只表示当前来源文件、内容和对象边界已可核验；不自动授予正式事实、正文消费或流程激活权限。ambiguous 与 readable_needs_review 不得强行放行。",
        "status": "passed" if not any(row.get("resolution_status") in {"unresolved", "ambiguous"} for row in results) else "needs_review",
    }
    (output / "全量来源解析审计报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="使用当前来源协议执行只读全量解析审计")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--source-kind", action="append", dest="source_kinds", help="只审计指定 source_kind；可重复传入")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    report = audit(args.project_root, set(args.source_kinds) if args.source_kinds else None, args.start, args.limit)
    print(json.dumps({"status": report["status"], "binding_count": report["binding_count"], "status_counts": report["status_counts"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())