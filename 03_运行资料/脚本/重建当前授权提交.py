"""Re-anchor existing explicit authorization to the current binding snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from 全量资料输入与正文授权 import _baseline, _read_jsonl, _row_errors, SCHEMA_VERSION


AUTH_FIELDS = (
    "authorization_scope",
    "authorized_by",
    "authorized_at",
    "authorization_rationale",
)


def rebuild(root: str | Path, source_path: str | Path | None = None, output_path: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    evidence = project_root / "文档" / "证据"
    bindings_path = evidence / "全量资料解释词创作绑定.json"
    source = Path(source_path).expanduser().resolve() if source_path else project_root / "配置" / "全量资料输入与正文授权.jsonl"
    output = Path(output_path).expanduser().resolve() if output_path else project_root / "配置" / "全量资料输入与正文授权.jsonl"
    document = json.loads(bindings_path.read_text(encoding="utf-8-sig"))
    records = document.get("records", []) if isinstance(document, dict) else []
    baseline = _baseline(records)
    current_by_id = {str(row["binding_id"]): row for row in records if isinstance(row, dict) and row.get("binding_id")}
    old_rows = _read_jsonl(source)
    old_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for row in old_rows:
        binding_id = row.get("binding_id") if isinstance(row, dict) else None
        if not isinstance(binding_id, str) or binding_id not in current_by_id:
            continue
        if binding_id in old_by_id:
            duplicate_ids.add(binding_id)
        old_by_id[binding_id] = row

    rebuilt: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for binding_id, current in current_by_id.items():
        old = old_by_id.get(binding_id)
        if old is None:
            rejected.append({"binding_id": binding_id, "reason": "缺少现有显式授权记录"})
            continue
        errors = _row_errors(old, baseline, set())
        authorization_errors = [error for error in errors if not error.startswith("不可变绑定不匹配: source_ref_sha256")]
        if binding_id in duplicate_ids:
            authorization_errors.append("binding_id 在旧提交中重复")
        if old.get("model_input_eligible") is not True or old.get("prose_write_allowed") is not True:
            authorization_errors.append("旧记录未同时授予模型输入与正文写作权限")
        for field in AUTH_FIELDS:
            if not isinstance(old.get(field), str) or not old[field].strip():
                authorization_errors.append(f"旧记录缺少 {field}")
        if authorization_errors:
            rejected.append({"binding_id": binding_id, "reason": authorization_errors})
            continue
        rebuilt.append({
            "schema_version": SCHEMA_VERSION,
            "binding_id": binding_id,
            "source_id": current["source_id"],
            "source_ref_sha256": baseline[binding_id]["source_ref_sha256"],
            "model_input_eligible": True,
            "prose_write_allowed": True,
            **{field: old[field] for field in AUTH_FIELDS},
        })

    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rebuilt), encoding="utf-8")
    report = {
        "schema_version": "current-authorization-submission-rebuild-1.0",
        "source_path": str(source.relative_to(project_root)).replace("\\", "/") if source.is_relative_to(project_root) else str(source),
        "output_path": str(output.relative_to(project_root)).replace("\\", "/") if output.is_relative_to(project_root) else str(output),
        "current_binding_count": len(current_by_id),
        "rebuilt_authorized_count": len(rebuilt),
        "rejected_count": len(rejected),
        "rejected_sample": rejected[:20],
        "policy": "仅重锚定已有完整显式双重授权；不创建授权、不补填授权人、时间、范围或理由。",
    }
    report_path = evidence / "全量资料输入与正文授权" / "当前授权提交重建报告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = rebuild(args.project_root)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["rejected_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())