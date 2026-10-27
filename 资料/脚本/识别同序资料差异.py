"""Inspect frozen source-upgrade batches against ordered original material data."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FREEZE_ROOT = Path("文档/资料融合工作区/输入冻结V1")
KIND_TO_FILE = {
    "动态网络": "动态网络.txt",
    "类型系统": "类型系统.txt",
    "类型系统来源块": "类型系统.txt",
    "类型连接": "类型连接.txt",
    "资料库": "资料库.txt",
    "锚点网络": "锚点网络.txt",
    "静态网络": "静态网络.txt",
}
REF_PATTERN = re.compile(r"^(?P<file>[^:]+):(?P<path>.+)$")
PATH_TOKEN = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\[(?P<index>\d+)\]")
FENCED_JSON = re.compile(r"```json\s*(?P<json>.*?)\s*```", re.DOTALL)


def canonical_hash(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def material_document(path: Path) -> tuple[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    try:
        return "json", json.loads(text)
    except json.JSONDecodeError:
        fenced = FENCED_JSON.search(text)
        if fenced:
            return "fenced_json", json.loads(fenced.group("json"))
        return "markdown_or_assembled_text", text


def records(batch_directory: Path) -> list[dict[str, Any]]:
    result = []
    for path in sorted(batch_directory.glob("SOURCE-UPGRADE-*.json")):
        document = load_json(path)
        result.extend(document["records"])
    return result


def resolve_source_ref(root: Path, reference: str, document_cache: dict[Path, Any]) -> tuple[str, Any] | str | None:
    match = REF_PATTERN.match(reference)
    if not match:
        return None
    source = root / match.group("file")
    if not source.is_file():
        return None
    if source not in document_cache:
        try:
            document_cache[source] = load_json(source)
        except json.JSONDecodeError:
            document_cache[source] = None
    value = document_cache[source]
    if value is None:
        return "historical_source_not_json"
    for token in PATH_TOKEN.finditer(match.group("path")):
        if not isinstance(value, dict) or token.group("key") not in value:
            return None
        items = value[token.group("key")]
        index = int(token.group("index"))
        if not isinstance(items, list) or index >= len(items):
            return None
        value = items[index]
    return source.relative_to(root).as_posix(), value


def original_shape(materials: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path in sorted(materials.glob("*.txt")):
        format_name, value = material_document(path)
        arrays = ({
            key: len(item) for key, item in value.items()
            if isinstance(value, dict) and isinstance(item, list)
        } if isinstance(value, dict) else {})
        text = value if isinstance(value, str) else None
        result[path.name] = {
            "format": format_name,
            "top_level_type": type(value).__name__,
            "top_level_keys": sorted(value) if isinstance(value, dict) else None,
            "top_level_array_lengths": arrays,
            "source_block_count": len(re.findall(r"(?m)^SOURCE:\s+", text)) if text else 0,
            "heading_count": len(re.findall(r"(?m)^#{1,6}\s+", text)) if text else 0,
            "line_count": len(text.splitlines()) if text else None,
        }
    return result


def build(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    freeze = root / FREEZE_ROOT
    materials = freeze / "原版资料"
    batches = freeze / "严格升级批次"
    if not materials.is_dir() or not batches.is_dir():
        raise FileNotFoundError("找不到输入冻结副本")
    rows = records(batches)
    material_shapes = original_shape(materials)
    positions: dict[str, int] = defaultdict(int)
    results = []
    document_cache: dict[Path, Any] = {}
    for row in rows:
        kind = str(row["source_kind"])
        positions[kind] += 1
        resolved = resolve_source_ref(root, str(row["source_ref"]), document_cache)
        if not isinstance(resolved, tuple):
            comparison = resolved or "historical_source_unavailable"
            actual_hash = None
            source_file = None
        else:
            source_file, value = resolved
            actual_hash = canonical_hash(value)
            comparison = "source_item_hash_matches" if actual_hash == row["source_item_sha256"] else "source_item_hash_differs"
        results.append({
            "sequence": positions[kind],
            "upgrade_id": row["upgrade_id"],
            "source_kind": kind,
            "original_material_file": KIND_TO_FILE.get(kind),
            "source_id": row["source_id"],
            "source_ref": row["source_ref"],
            "recorded_source_item_sha256": row["source_item_sha256"],
            "resolved_source_file": source_file,
            "resolved_source_item_sha256": actual_hash,
            "comparison": comparison,
            "status": row["status"],
            "permitted_use": row["permitted_use"],
            "prose_write_allowed": row["prose_write_allowed"],
            "fusion_assessment": "no_candidate_value_in_batch_record",
        })
    output = freeze / "同序差异识别"
    output.mkdir(exist_ok=True)
    (output / "同序对象对照.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in results), encoding="utf-8"
    )
    report = {
        "schema_version": "ordered-material-difference-report-1.0",
        "scope": "按 source_kind 保持 SOURCE-UPGRADE 记录顺序；只识别可验证差异，不向原版写入内容。",
        "original_material_shapes": material_shapes,
        "record_count": len(results),
        "ordered_record_counts": dict(sorted(positions.items())),
        "comparison_counts": dict(sorted(Counter(row["comparison"] for row in results).items())),
        "status_counts": dict(sorted(Counter(row["status"] for row in results).items())),
        "candidate_value_count": 0,
        "fusion_ready_count": 0,
        "reason": "SOURCE-UPGRADE 记录提供对象顺序、来源定位、哈希和审计状态，但不含可写入的升级字段值。",
        "detail_file": "同序对象对照.jsonl",
    }
    (output / "同序差异报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="按顺序识别原版资料与升级批次的差异")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    result = build(args.project_root)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())