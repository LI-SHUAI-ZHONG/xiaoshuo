"""Derive read-only, hash-locked locator mappings for upgrade exceptions.

This tool never changes bindings, source material, or terminal statuses.  A
mapping is emitted only when the full original-object boundary is proved from
the source text; all other exception records remain explicitly unresolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "full-source-material-derived-locator-mapping-1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _library_object(root: Path, item: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    raw = item.get("source_ref", {}).get("raw") if isinstance(item.get("source_ref"), dict) else None
    try:
        ref = __import__("ast").literal_eval(raw)
    except (SyntaxError, ValueError, TypeError):
        return None, "source_ref 不能解析为结构化定位"
    if not isinstance(ref, dict) or ref.get("file") != "原始资料/资料库.txt" or not isinstance(ref.get("locator"), str):
        return None, "资料库 source_ref 不满足受控定位格式"
    locator = ref["locator"]
    number, separator, label = locator.partition("_")
    if not separator or not number.isdigit():
        return None, "资料库 locator 不具备板块编号与标题"
    expected = f"## 板块{number} {label.replace('_', ' ')}"
    path = root / ref["file"]
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    matches = [index for index, line in enumerate(lines) if line.strip() == expected]
    if len(matches) != 1:
        return None, f"资料库完整标题精确命中数为 {len(matches)}"
    start = matches[0]
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## 板块")), len(lines))
    original = {
        "file": ref["file"], "locator": locator, "derived_heading": expected,
        "line_start": start + 1, "line_end": end, "content": "\n".join(lines[start:end]),
    }
    return original, None


def _type_connection_object(root: Path, item: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    raw = item.get("source_ref", {}).get("raw") if isinstance(item.get("source_ref"), dict) else None
    match = re.fullmatch(r"原始资料/类型连接\.txt:([^\[\]:]+)\[(\d+)\]", raw or "")
    if not match:
        return None, "类型连接 source_ref 不满足源块 JSON 数组定位格式"
    block_name, index_text = match.groups()
    array_index = int(index_text)
    if array_index < 1:
        return None, "类型连接数组坐标必须从 1 开始"
    path = root / "原始资料" / "类型连接.txt"
    text = path.read_text(encoding="utf-8-sig")
    headers = list(re.finditer(r"^SOURCE: (.+)$", text, re.MULTILINE))
    matches = [header for header in headers if header.group(1) == block_name]
    if len(matches) != 1:
        return None, f"类型连接 SOURCE 标题精确命中数为 {len(matches)}"
    header = matches[0]
    next_start = next((candidate.start() for candidate in headers if candidate.start() > header.start()), len(text))
    block_text = text[header.end():next_start]
    payload = block_text.lstrip("= \t\r\n")
    try:
        value, consumed = json.JSONDecoder().raw_decode(payload)
    except json.JSONDecodeError:
        return None, "类型连接 SOURCE 分块不是有效 JSON"
    if payload[consumed:].strip():
        return None, "类型连接 SOURCE 分块含有 JSON 后附加内容"
    if not isinstance(value, list) or array_index > len(value):
        return None, "类型连接 SOURCE 分块不是目标数组或数组坐标越界"
    selected = value[array_index - 1]
    source_id = str(item.get("source_id") or "")
    positional_id = f"{block_name}:{array_index}"
    if source_id == positional_id:
        identity = "绑定 source_id 与 SOURCE 标题及 1 基数组坐标精确一致"
    elif isinstance(selected, dict) and source_id == repr(selected):
        identity = "绑定 source_id 与规范回读的首个 JSON 对象精确一致"
    else:
        return None, "类型连接绑定 source_id 无法与受控源块对象建立一致身份"
    original = {
        "file": "原始资料/类型连接.txt",
        "source_block": block_name,
        "array_index_one_based": array_index,
        "object": selected,
        "object_sha256": _canonical_hash(selected),
    }
    return original, identity


def build(project_root: str | Path, run_id: str, output_name: str | None = None) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence_root = root / "文档" / "证据" / "全量资料升级运行"
    audit_path = evidence_root / f"{run_id}-异常审计" / "exceptions.jsonl"
    if not audit_path.is_file():
        raise ValueError("缺少对应运行的异常审计证据")
    exceptions = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    output = evidence_root / (output_name or f"{run_id}-定位映射")
    output.mkdir(parents=True, exist_ok=False)
    mappings = []
    for item in exceptions:
        result = {
            "binding_id": item.get("binding_id"), "source_id": item.get("source_id"),
            "source_kind": item.get("source_kind"), "prior_terminal_status": item.get("terminal_status"),
            "prior_error_signature": item.get("error_signature"), "mapping_status": "unresolved",
            "automatic_reprocess_allowed": False,
        }
        if item.get("source_kind") == "资料库" and item.get("terminal_status") == "quarantined":
            original, error = _library_object(root, item)
            if original is not None:
                source_path = root / original["file"]
                result.update({
                    "mapping_status": "verified_candidate",
                    "source_file_sha256": _file_hash(source_path),
                    "derived_original_object": original,
                    "derived_original_object_sha256": _canonical_hash(original),
                    "verification": "标题唯一精确命中；对象边界为下一板块标题或文件结尾",
                })
            else:
                result["unresolved_reason"] = error
        elif item.get("source_kind") == "类型系统":
            result["unresolved_reason"] = "matched_lines 跨多个分散对象，现有证据不能导出唯一完整对象边界"
        elif item.get("source_kind") == "类型连接":
            original, identity = _type_connection_object(root, item)
            if original is not None:
                source_path = root / original["file"]
                result.update({
                    "mapping_status": "verified_candidate",
                    "source_file_sha256": _file_hash(source_path),
                    "derived_original_object": original,
                    "derived_original_object_sha256": _canonical_hash(original),
                    "verification": f"SOURCE 标题唯一；数组整体严格 JSON 解析；{identity}；对象规范哈希已锁定",
                })
            else:
                result["unresolved_reason"] = str(identity)
        else:
            result["unresolved_reason"] = "非定位隔离项；不适用派生 locator 修复"
        mappings.append(result)
    mappings_path = output / "mappings.jsonl"
    mappings_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in mappings), encoding="utf-8")
    counts = Counter(item["mapping_status"] for item in mappings)
    manifest = {
        "schema_version": SCHEMA_VERSION, "generated_at": _now(), "audited_run_id": run_id,
        "mapping_counts": dict(counts), "automatic_reprocess_allowed": False,
        "formal_fact_eligible": False, "prose_write_allowed": False, "formal_release_allowed": False,
        "mappings_file": "mappings.jsonl",
    }
    manifest["manifest_sha256"] = _canonical_hash(manifest)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-name")
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.run_id, args.output_name), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())