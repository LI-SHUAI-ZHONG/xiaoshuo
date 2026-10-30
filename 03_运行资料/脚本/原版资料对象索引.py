"""Create a hash-locked, read-only object index for the six original materials."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "original-material-object-index-1.0"
ORIGINAL_FILES = ("动态网络.txt", "类型系统.txt", "类型连接.txt", "资料库.txt", "锚点网络.txt", "静态网络.txt")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def _row(file_name: str, kind: str, locator: str, start: int, end: int, content: str, identity: str | None = None) -> dict[str, Any]:
    return {
        "object_id": f"原始资料/{file_name}#{locator}",
        "identity": identity or locator,
        "source_file": f"原始资料/{file_name}",
        "object_kind": kind,
        "locator": locator,
        "line_start": start,
        "line_end": end,
        "content_sha256": _hash(content),
        "write_boundary": {"mode": "replace_exact_line_range", "line_start": start, "line_end": end},
    }


def _heading_objects(file_name: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    matches = [(index, match) for index, line in enumerate(lines) if (match := re.match(r"^###\s+(.+?)\s*$", line))]
    objects = []
    for position, (start, match) in enumerate(matches):
        end = matches[position + 1][0] if position + 1 < len(matches) else len(lines)
        label = match.group(1)
        objects.append(_row(file_name, "markdown_entry", label, start + 1, end, "\n".join(lines[start:end]), label))
    return objects


def _source_blocks(file_name: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    matches = [(index, match.group(1)) for index, line in enumerate(lines) if (match := re.match(r"^SOURCE:\s+(.+?)\s*$", line))]
    objects = []
    for position, (start, name) in enumerate(matches):
        end = matches[position + 1][0] if position + 1 < len(matches) else len(lines)
        objects.append(_row(file_name, "source_json_block", name, start + 1, end, "\n".join(lines[start:end]), name))
    return objects


def _json_payload(text: str) -> Any | None:
    fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _json_objects(file_name: str, text: str) -> list[dict[str, Any]]:
    payload = _json_payload(text)
    if not isinstance(payload, (dict, list)):
        return []
    objects = []

    collection_keys = {"connections", "连接列表", "items", "types", "combinations"}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if key in collection_keys and isinstance(child, list):
                    visit(child, child_path)
                elif isinstance(child, dict):
                    visit(child, child_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                locator = f"{path}[{index}]"
                if isinstance(item, dict):
                    identity = next((str(item[key]) for key in ("stable_id", "connection_id", "id", "source_id", "source") if item.get(key) is not None), None)
                    objects.append(_row(file_name, "json_object", locator, 1, len(text.splitlines()), json.dumps(item, ensure_ascii=False, sort_keys=True), identity))

    visit(payload, "")
    return objects


def _anchor_rows(file_name: str, text: str) -> list[dict[str, Any]]:
    objects = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\|\s*([A-Z]\d+(?:\.\d+)?)\s*\|\s*([^|]+)", line)
        if match:
            anchor_id, name = match.groups()
            objects.append(_row(file_name, "anchor_table_row", anchor_id, number, number, line, anchor_id))
    return objects


def index(root: str | Path, output_name: str = "原版资料对象索引") -> dict[str, Any]:
    project = Path(root).expanduser().resolve()
    output = project / "文档" / "证据" / output_name
    if output.exists():
        raise FileExistsError(f"对象索引输出已存在，拒绝覆盖: {output}")
    rows: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for file_name in ORIGINAL_FILES:
        path = project / "原始资料" / file_name
        if not path.is_file():
            raise FileNotFoundError(f"缺少原版资料: {path}")
        text = path.read_text(encoding="utf-8-sig")
        extracted = _heading_objects(file_name, text) + _source_blocks(file_name, text) + _json_objects(file_name, text) + _anchor_rows(file_name, text)
        deduplicated = {row["object_id"]: row for row in extracted}
        rows.extend(deduplicated.values())
        files.append({"source_file": f"原始资料/{file_name}", "sha256": _hash(path.read_bytes()), "object_count": len(deduplicated)})
    duplicate_ids = [object_id for object_id, count in Counter(row["object_id"] for row in rows).items() if count > 1]
    if duplicate_ids:
        raise ValueError(f"稳定对象 ID 重复: {duplicate_ids[:3]}")
    rows.sort(key=lambda row: row["object_id"])
    output.mkdir(parents=True)
    (output / "对象索引.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "source_file_count": len(files),
        "object_count": len(rows),
        "object_kind_counts": dict(sorted(Counter(row["object_kind"] for row in rows).items())),
        "files": files,
        "objects_file": "对象索引.jsonl",
        "original_sources_modified": False,
    }
    (output / "索引清单.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="建立六份原版资料的稳定对象索引")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-name", default="原版资料对象索引")
    args = parser.parse_args()
    print(json.dumps(index(args.project_root, args.output_name), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())