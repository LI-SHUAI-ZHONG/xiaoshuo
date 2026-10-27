"""Produce review-only before/after upgrades for uniquely bound original objects."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from 文本生成模型 import TextGenerationError, generate_json


SCHEMA_VERSION = "original-material-upgrade-execution-1.0"
BINDINGS_PATH = Path("文档/证据/严格升级原版对象绑定/bindings.jsonl")
OUTPUT_ROOT = Path("文档/证据/原版资料升级执行")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _payload(text: str) -> Any:
    fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return json.loads(fenced.group(1) if fenced else text)


def _find_identity(value: Any, identity: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if any(str(value.get(key)) == identity for key in ("stable_id", "connection_id", "id", "source_id", "source")):
            return value
        for child in value.values():
            found = _find_identity(child, identity)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_identity(child, identity)
            if found is not None:
                return found
    return None


def _current_object(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    source_file = root / str(binding["original_source_file"])
    payload = _payload(source_file.read_text(encoding="utf-8-sig"))
    value = _find_identity(payload, str(binding["source_id"]))
    if not isinstance(value, dict):
        raise ValueError(f"无法在当前原版资料中重取对象: {binding['original_object_id']}")
    if _hash(value) != binding.get("original_object_sha256"):
        raise ValueError(f"对象哈希漂移，拒绝生成升级候选: {binding['original_object_id']}")
    return value


def _system_prompt() -> str:
    return """你是资料升级审校助手。只能增强输入对象的清晰性、边界、可验证性或字段完整性；不得捏造项目事实、人物、剧情、来源或许可证。
不得改变 stable_id、connection_id、id、source_id、source 等已有身份字段。只允许修改对象的顶层字段。严格输出 JSON 对象：
{"rationale":"原因","changes":[{"field_path":"顶层字段名","operation":"replace|append|remove","before":任意JSON,"after":任意JSON,"reason":"理由"}]}
若没有可靠改动，changes 必须为空。不要输出完整对象，系统会在冻结 before 上应用经验证的字段变更后生成完整 after。"""


def _review_context(before: dict[str, Any]) -> dict[str, Any]:
    """Keep model context to editable business fields; the full object remains hash-locked locally."""
    excluded = {"field_source", "source_refs", "valid_types", "derivation_contract"}
    return {key: value for key, value in before.items() if key not in excluded}


def _validate(before: dict[str, Any], result: Any) -> dict[str, Any]:
    if not isinstance(result, dict) or not isinstance(result.get("rationale"), str) or not isinstance(result.get("changes"), list):
        raise ValueError("模型升级结果不满足字段变更合同")
    after = copy.deepcopy(before)
    protected = {"stable_id", "connection_id", "id", "source_id", "source"}
    for change in result["changes"]:
        if not isinstance(change, dict):
            raise ValueError("字段变更必须为对象")
        field = change.get("field_path")
        operation = change.get("operation")
        if not isinstance(field, str) or field not in before or "." in field or "[" in field:
            raise ValueError("只允许修改现有顶层字段")
        if field in protected:
            raise ValueError(f"模型试图修改身份字段: {field}")
        if operation not in {"replace", "append", "remove"} or change.get("before") != before[field]:
            raise ValueError("字段变更操作或 before 值不匹配")
        if operation == "replace":
            after[field] = change.get("after")
        elif operation == "remove":
            after.pop(field)
        elif isinstance(before[field], list):
            after[field] = before[field] + [change.get("after")]
        else:
            raise ValueError("append 只允许用于数组字段")
    result["upgraded_object"] = after
    return result


def execute(root: str | Path, run_id: str, max_objects: int | None = None, generator: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = generate_json) -> dict[str, Any]:
    project = Path(root).expanduser().resolve()
    output = project / OUTPUT_ROOT / run_id
    if output.exists() or Path(run_id).name != run_id:
        raise ValueError("run_id 非法或输出目录已存在")
    bindings = [row for row in _read_jsonl(project / BINDINGS_PATH) if row.get("binding_status") == "verified"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for binding in bindings:
        grouped[str(binding["original_object_id"])].append(binding)
    selected = sorted(grouped.items())[:max_objects] if max_objects is not None else sorted(grouped.items())
    output.mkdir(parents=True)
    rows = []
    records_path = output / "upgrade_records.jsonl"
    manifest_path = output / "manifest.json"
    def write_report(completed: bool) -> dict[str, Any]:
        report = {"schema_version": SCHEMA_VERSION, "generated_at": _now(), "run_id": run_id, "selected_object_count": len(selected), "record_count": len(rows), "status_counts": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})}, "writeback_allowed_count": 0, "records_file": "upgrade_records.jsonl", "completed": completed, "original_sources_modified": False}
        manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    records_path.write_text("", encoding="utf-8")
    write_report(completed=False)
    for ordinal, (object_id, object_bindings) in enumerate(selected, 1):
        binding = object_bindings[0]
        before = _current_object(project, binding)
        row: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "upgrade_id": f"OMU-{run_id}-{ordinal:05d}",
            "original_object_id": object_id,
            "source_file": binding["original_source_file"],
            "source_id": binding["source_id"],
            "binding_ids": sorted(str(item["binding_id"]) for item in object_bindings),
            "strict_upgrade_ids": sorted(str(item["upgrade_id"]) for item in object_bindings),
            "before": before,
            "before_sha256": _hash(before),
            "status": "model_error",
            "changes": [],
            "upgraded_object": None,
            "rationale": None,
            "model_metadata": None,
            "writeback_allowed": False,
            "review_status": "pending",
        }
        try:
            result, metadata = generator(project, _system_prompt(), json.dumps({"object_id": object_id, "editable_context": _review_context(before)}, ensure_ascii=False))
            result = _validate(before, result)
            row.update({"status": "requires_human_review", "changes": result["changes"], "upgraded_object": result["upgraded_object"], "rationale": result["rationale"], "model_metadata": metadata, "after_sha256": _hash(result["upgraded_object"])})
        except (TextGenerationError, ValueError) as exc:
            row["error"] = str(exc)
        rows.append(row)
        with records_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        write_report(completed=False)
    return write_report(completed=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成原版资料对象的审查型 before/after 升级成果")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-objects", type=int)
    args = parser.parse_args()
    print(json.dumps(execute(args.project_root, args.run_id, args.max_objects), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())