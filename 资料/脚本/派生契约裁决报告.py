"""Issue a read-only ruling for a derived dynamic-network candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json_or_fenced(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    payload = match.group(1) if match else text
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        # Some original material files contain one complete JSON root followed
        # by legacy appended blocks.  Only the first root is authoritative for
        # this object-level ruling; never interpret the trailing blocks as one
        # merged document.
        decoder = json.JSONDecoder()
        try:
            value, _ = decoder.raw_decode(payload.lstrip())
            return value
        except json.JSONDecodeError:
            raise exc


def find_connection(payload: Any, source: str, target: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        for value in payload.values():
            found = find_connection(value, source, target)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            if isinstance(value, dict) and value.get("source") == source and value.get("target") == target and value.get("type") == "绑定":
                return value
            found = find_connection(value, source, target)
            if found:
                return found
    return {}


def find_dynamic(payload: Any, object_id: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        if payload.get("id") == object_id:
            return payload
        for value in payload.values():
            found = find_dynamic(value, object_id)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_dynamic(value, object_id)
            if found:
                return found
    return {}


def first_jsonl(path: Path, predicate) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if predicate(value):
            return value
    return {}


def run(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    output = root / "文档" / "合并升级" / run_id
    if output.exists() or Path(run_id).name != run_id:
        raise ValueError("run_id 非法或输出目录已存在")

    static_path = root / "原始资料" / "静态网络.txt"
    dynamic_path = root / "原始资料" / "动态网络.txt"
    bindings_path = root / "文档" / "证据" / "严格升级原版对象绑定" / "bindings.jsonl"
    candidate_path = root / "文档" / "证据" / "原版资料升级执行" / "首对象审查候选V5" / "upgrade_records.jsonl"
    static_payload = load_json_or_fenced(static_path)
    dynamic_payload = load_json_or_fenced(dynamic_path)
    binding = first_jsonl(bindings_path, lambda row: row.get("binding_id") == "TB-01910")
    candidate = first_jsonl(candidate_path, lambda row: row.get("source_id") == "C00001")
    static_source = find_connection(static_payload, "1.1_主角", "130_核心悬念")
    dynamic_object = find_dynamic(dynamic_payload, "C00001")
    source_condition = static_source.get("condition")
    dynamic_condition = dynamic_object.get("condition")
    dynamic_effect = dynamic_object.get("effect")
    report = {
        "schema_version": "derived-contract-ruling-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "review_only": True,
        "original_sources_modified": False,
        "subject": {
            "dynamic_object_id": "C00001",
            "binding_id": "TB-01910",
            "source": "1.1_主角",
            "target": "130_核心悬念",
            "type": "绑定",
        },
        "evidence": {
            "static_source": {"condition": source_condition, "object": static_source},
            "dynamic_object": {"condition": dynamic_condition, "effect": dynamic_effect, "object": dynamic_object},
            "binding": binding,
            "candidate_changes": candidate.get("changes", []),
        },
        "checks": {
            "static_source_found": bool(static_source),
            "dynamic_object_found": bool(dynamic_object),
            "binding_verified": binding.get("binding_status") == "verified",
            "dynamic_marked_as_derived": dynamic_object.get("generated_from_static") is True,
            "dynamic_fields_point_to_derivation": all(
                str(dynamic_object.get("field_source", {}).get(field, "")).find("静态网络") >= 0
                or "派生" in str(dynamic_object.get("field_source", {}).get(field, ""))
                for field in ("condition", "effect")
            ),
            "candidate_changes_static_source": bool(candidate.get("changes")),
            "source_has_field_level_upgrade": False,
        },
        "ruling": {
            "static_network": "no_upgrade_evidence",
            "dynamic_network": "derived_result_must_be_recomputed",
            "candidate": "permanently_quarantined",
            "model_call_allowed": False,
            "fusion_allowed": False,
            "writeback_allowed": False,
            "reason": "动态字段由静态网络绑定规则派生；当前候选没有独立的静态源字段变更，不能把派生结果当作正文升级。",
        },
        "source_hashes": {str(path.relative_to(root)): sha256(path) for path in (static_path, dynamic_path, bindings_path, candidate_path)},
    }
    output.mkdir(parents=True)
    (output / "ruling.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps({
        "schema_version": report["schema_version"],
        "generated_at": report["generated_at"],
        "review_only": True,
        "original_sources_modified": False,
        "ruling": report["ruling"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="生成静态/动态网络派生候选的只读裁决报告")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.project_root, args.run_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())