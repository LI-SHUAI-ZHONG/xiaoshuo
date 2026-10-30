"""Recompute a bounded derived-network result and compare it read-only."""
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


def load_root(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    payload = fenced.group(1) if fenced else text
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        value, _ = json.JSONDecoder().raw_decode(payload.lstrip())
        return value


def find_static(value: Any, source: str, target: str, relation: str) -> dict[str, Any]:
    if isinstance(value, dict):
        for child in value.values():
            result = find_static(child, source, target, relation)
            if result:
                return result
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, dict) and child.get("source") == source and child.get("target") == target and child.get("type") == relation:
                return child
            result = find_static(child, source, target, relation)
            if result:
                return result
    return {}


def find_dynamic(value: Any, object_id: str) -> dict[str, Any]:
    if isinstance(value, dict):
        if value.get("id") == object_id:
            return value
        for child in value.values():
            result = find_dynamic(child, object_id)
            if result:
                return result
    elif isinstance(value, list):
        for child in value:
            result = find_dynamic(child, object_id)
            if result:
                return result
    return {}


def expected_binding(static: dict[str, Any], dynamic: dict[str, Any]) -> dict[str, str] | None:
    if static.get("type") != "绑定":
        return None
    condition = f"{static.get('condition', '')}；且当前故事明确采用该静态关系"
    effect = "当起点成立时，起点与终点保持绑定关系，终点状态随起点状态更新。"
    return {"condition": condition, "effect": effect}


def first_jsonl(path: Path, predicate) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
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
    binding_path = root / "文档" / "证据" / "严格升级原版对象绑定" / "bindings.jsonl"
    static = load_root(static_path)
    dynamic = load_root(dynamic_path)
    binding = first_jsonl(binding_path, lambda row: row.get("binding_id") == "TB-01910")
    source = "1.1_主角"
    target = "130_核心悬念"
    relation = "绑定"
    static_object = find_static(static, source, target, relation)
    dynamic_object = find_dynamic(dynamic, "C00001")
    expected = expected_binding(static_object, dynamic_object)
    actual = {field: dynamic_object.get(field) for field in ("condition", "effect")}
    field_matches = {field: bool(expected) and actual[field] == expected[field] for field in actual}
    result = "consistent" if expected and all(field_matches.values()) else "manual_review_required"
    report = {
        "schema_version": "derived-result-recompute-check-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "review_only": True,
        "original_sources_modified": False,
        "subject": {"dynamic_object_id": "C00001", "binding_id": binding.get("binding_id"), "source": source, "target": target, "type": relation},
        "static_input": static_object,
        "dynamic_actual": actual,
        "dynamic_expected": expected,
        "field_matches": field_matches,
        "checks": {
            "static_object_found": bool(static_object),
            "dynamic_object_found": bool(dynamic_object),
            "binding_verified": binding.get("binding_status") == "verified",
            "derived_marker_present": dynamic_object.get("generated_from_static") is True,
            "contract_marker_present": dynamic_object.get("derivation_contract") == "NET-DYNAMIC-DERIVATION-CONTRACT-1.0",
        },
        "result": result,
        "ruling": {
            "candidate_action": "close_quarantine" if result == "consistent" else "keep_quarantine",
            "model_call_allowed": False,
            "fusion_allowed": False,
            "writeback_allowed": False,
            "reason": "当前动态对象与静态绑定规则的固定派生结果一致；不需要正文升级或模型重写。" if result == "consistent" else "派生结果无法由当前固定契约完整重算，需人工审查，禁止猜测或写回。",
        },
        "source_hashes": {str(path.relative_to(root)): sha256(path) for path in (static_path, dynamic_path, binding_path)},
    }
    output.mkdir(parents=True)
    (output / "recompute-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps({
        "schema_version": report["schema_version"],
        "generated_at": report["generated_at"],
        "review_only": True,
        "original_sources_modified": False,
        "result": result,
        "ruling": report["ruling"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="重算并校验派生动态网络对象")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.project_root, args.run_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())