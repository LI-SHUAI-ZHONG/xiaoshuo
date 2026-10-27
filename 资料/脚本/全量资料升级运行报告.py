"""Summarize immutable full-source upgrade evidence without changing its status."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UPGRADE_DIR = Path("文档") / "证据" / "全量资料升级运行"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _run_directory(root: Path, run_id: str | None) -> Path:
    parent = root / UPGRADE_DIR
    if run_id:
        if Path(run_id).name != run_id:
            raise ValueError("run_id 必须是运行目录名称")
        return parent / run_id
    candidates = [path for path in parent.iterdir() if path.is_dir()] if parent.is_dir() else []
    if not candidates:
        raise ValueError("不存在全量资料升级运行")
    return sorted(candidates)[-1]


def build_report(project_root: str | Path, run_id: str | None = None) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    directory = _run_directory(root, run_id)
    manifest = _read(directory / "manifest.json", {})
    if not isinstance(manifest, dict) or manifest.get("run_id") != directory.name:
        raise ValueError("运行清单不存在或 run_id 不匹配")
    records_file = directory / str(manifest.get("records_file") or "records.jsonl")
    rows: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    try:
        lines = records_file.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ValueError("运行缺少 records.jsonl") from exc
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            parse_errors.append(f"records.jsonl 第 {number} 行不是有效 JSON")
            continue
        if not isinstance(row, dict):
            parse_errors.append(f"records.jsonl 第 {number} 行不是对象")
            continue
        rows.append(row)
    status_counts = Counter(str(row.get("terminal_status") or "missing") for row in rows)
    kind_counts = Counter(str(row.get("source_kind") or "missing") for row in rows)
    kind_status_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    error_counts = Counter()
    duplicate_ids = Counter(str(row.get("binding_id") or "missing") for row in rows)
    for row in rows:
        kind_status_counts[str(row.get("source_kind") or "missing")][str(row.get("terminal_status") or "missing")] += 1
        for error in row.get("errors", []) if isinstance(row.get("errors"), list) else []:
            error_counts[str(error)] += 1
    findings = parse_errors[:]
    if manifest.get("processed_count") != len(rows):
        findings.append("manifest processed_count 与 records.jsonl 记录数不一致")
    if any(count > 1 for count in duplicate_ids.values()):
        findings.append("records.jsonl 存在重复 binding_id")
    if dict(status_counts) != manifest.get("status_counts"):
        findings.append("manifest status_counts 与 records.jsonl 不一致")
    report = {
        "schema_version": "full-source-material-upgrade-run-report-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": manifest["run_id"],
        "parent_run_id": manifest.get("parent_run_id"),
        "execution_mode": manifest.get("execution_mode"),
        "binding_baseline_sha256": manifest.get("binding_baseline_sha256"),
        "processed_count": len(rows),
        "status_counts": dict(status_counts),
        "source_kind_counts": dict(kind_counts),
        "source_kind_status_counts": {kind: dict(counts) for kind, counts in sorted(kind_status_counts.items())},
        "top_errors": [{"error": error, "count": count} for error, count in error_counts.most_common(20)],
        "evidence_integrity_findings": findings,
        "status": "consistent" if not findings else "inconsistent",
        "formal_creation_allowed": False,
    }
    target = directory / "run_report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    report = build_report(args.project_root, args.run_id)
    print(json.dumps({key: report[key] for key in ("run_id", "processed_count", "status_counts", "status")}, ensure_ascii=False))
    return 0 if report["status"] == "consistent" else 2


if __name__ == "__main__":
    raise SystemExit(main())