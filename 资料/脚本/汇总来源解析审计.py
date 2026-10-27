"""Merge completed canonical source-resolution audit batches without re-resolving."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("文档") / "证据" / "全量来源解析审计"
EXPECTED = {"资料库": 568, "静态网络": 1341, "动态网络": 1824, "锚点网络": 1790, "类型系统": 15, "类型系统来源块": 449, "类型连接": 7358}


def merge(project_root: str | Path) -> dict:
    root = Path(project_root).expanduser().resolve() / ROOT
    reports = []
    for path in root.glob("批次_*/全量来源解析审计报告.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        kinds = report.get("source_kinds_scope", [])
        if len(kinds) == 1:
            reports.append((path, report, str(kinds[0])))
    status_counts, kind_counts = Counter(), {kind: Counter() for kind in EXPECTED}
    coverage = {kind: [] for kind in EXPECTED}
    for path, report, kind in reports:
        for status, count in report.get("status_counts", {}).items():
            status_counts[status] += int(count)
            kind_counts[kind][status] += int(count)
        coverage[kind].append({"directory": path.parent.name, "start": int(report.get("batch_start", 0)), "count": int(report.get("binding_count", 0)), "status": report.get("status")})
    coverage_checks = {}
    for kind, pages in coverage.items():
        pages.sort(key=lambda item: item["start"])
        cursor = 0
        valid = bool(pages)
        for page in pages:
            valid = valid and page["start"] == cursor
            cursor += page["count"]
        coverage_checks[kind] = {"expected": EXPECTED[kind], "covered": cursor, "contiguous": valid, "complete": valid and cursor == EXPECTED[kind], "pages": pages}
    all_covered = all(check["complete"] for check in coverage_checks.values())
    result = {
        "schema_version": "canonical-source-resolution-merged-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "read-only merge of completed current-binding audit batches",
        "expected_binding_count": sum(EXPECTED.values()),
        "covered_binding_count": sum(check["covered"] for check in coverage_checks.values()),
        "status_counts": dict(status_counts),
        "source_kind_status_counts": {kind: dict(counts) for kind, counts in kind_counts.items()},
        "coverage": coverage_checks,
        "policy": "ambiguous/readable_needs_review are retained as non-authorizing states even where file reachability and raw content recovery succeed.",
        "status": "passed" if all_covered and not status_counts["unresolved"] and not status_counts["ambiguous"] else "needs_review",
    }
    (root / "当前绑定来源解析总报告.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = merge(args.project_root)
    print(json.dumps({"status": report["status"], "covered_binding_count": report["covered_binding_count"], "status_counts": report["status_counts"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())