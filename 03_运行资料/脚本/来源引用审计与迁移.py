"""Audit and migrate legacy matched-line references to complete SOURCE blocks."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELECTION_FILE = Path("文档") / "证据" / "小说资料选择清单.json"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("资料选择清单根对象必须为 JSON 对象")
    return value


def _source_boundaries(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    headers = [index for index, line in enumerate(lines) if re.match(r"^SOURCE: .+$", line)]
    return [
        {"index": number + 1, "header": lines[start][len("SOURCE: "):], "line_start": start + 1, "line_end": (headers[number + 1] if number + 1 < len(headers) else len(lines))}
        for number, start in enumerate(headers)
    ]


def _line_to_block(line: int, blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [block for block in blocks if block["line_start"] <= line <= block["line_end"]]
    return matches[0] if len(matches) == 1 else None


def audit_and_migrate(project_root: str | Path, migrate: bool = True) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    selection_path = root / SELECTION_FILE
    selection = _read(selection_path)
    profiles = selection.get("selected_type_profiles", {})
    source_file = root / "原始资料" / "类型系统.txt"
    blocks = _source_boundaries(source_file)
    findings: list[dict[str, Any]] = []
    migrated_profiles = 0
    for profile_name, profile in profiles.items() if isinstance(profiles, dict) else []:
        if not isinstance(profile, dict):
            findings.append({"profile": profile_name, "status": "quarantined", "reason": "类型画像不是对象"})
            continue
        source_ref = profile.get("source_ref")
        if not isinstance(source_ref, dict) or not isinstance(source_ref.get("matched_lines"), list):
            if isinstance(source_ref, dict) and isinstance(source_ref.get("source_refs"), list):
                findings.append({"profile": profile_name, "status": "already_migrated", "source_ref_count": len(source_ref["source_refs"])})
            else:
                findings.append({"profile": profile_name, "status": "quarantined", "reason": "缺少可审计的 matched_lines"})
            continue
        lines = source_ref["matched_lines"]
        if not lines or any(not isinstance(line, int) or line < 1 for line in lines):
            findings.append({"profile": profile_name, "status": "quarantined", "reason": "matched_lines 必须为正整数数组"})
            continue
        resolved = [_line_to_block(line, blocks) for line in lines]
        if any(block is None for block in resolved):
            findings.append({"profile": profile_name, "status": "quarantined", "reason": "存在不能唯一归属 SOURCE 块的行号", "matched_lines": lines})
            continue
        source_refs = []
        for block in resolved:
            ref = f"原始资料/类型系统.txt:SOURCE[{block['index']}]"
            if ref not in source_refs:
                source_refs.append(ref)
        if migrate:
            profile["source_ref"] = {
                "file": "原始资料/类型系统.txt",
                "source_refs": source_refs,
                "legacy_matched_lines": lines,
                "boundary_policy": "每个行号必须唯一落入一个 SOURCE 块；source_refs 为完整来源块引用。",
            }
            migrated_profiles += 1
        findings.append({"profile": profile_name, "status": "migrated" if migrate else "migration_ready", "matched_line_count": len(lines), "source_ref_count": len(source_refs), "source_refs": source_refs})
    report = {
        "schema_version": "source-reference-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "selection_file": str(selection_path),
        "source_file": "原始资料/类型系统.txt",
        "source_block_count": len(blocks),
        "migration_applied": migrate and migrated_profiles > 0,
        "migrated_profile_count": migrated_profiles,
        "findings": findings,
        "status": "passed" if all(item["status"] in {"migrated", "already_migrated", "migration_ready"} for item in findings) else "quarantined",
    }
    if migrate and migrated_profiles:
        selection["schema_version"] = "novel-source-selection-1.1"
        selection["source_reference_policy"] = "类型画像使用完整 SOURCE 块引用；legacy_matched_lines 仅保留审计，不得作为模型或创作定位。"
        selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "文档" / "证据" / "来源引用审计报告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    report = audit_and_migrate(args.project_root, migrate=not args.audit_only)
    print(json.dumps({"status": report["status"], "migration_applied": report["migration_applied"], "migrated_profile_count": report["migrated_profile_count"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())