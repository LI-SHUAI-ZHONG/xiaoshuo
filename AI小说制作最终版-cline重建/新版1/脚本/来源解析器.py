"""Canonical, read-only resolver for the current source binding protocol.

This module is independent of the historical upgrade scripts.  It resolves
current bindings against the current raw files and keeps retrieval, identity,
version and workflow decisions separate.  It never writes to a source file.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SOURCE_FILES = {
    "资料库": "原始资料/资料库.txt",
    "静态网络": "网络完整数据/静态连接完整数据.json",
    "动态网络": "网络完整数据/动态连接完整数据.json",
    "锚点网络": "原始资料/锚点网络.txt",
    "类型系统": "原始资料/类型系统.txt",
    "类型系统来源块": "原始资料/类型系统.txt",
    "类型连接": "原始资料/类型连接.txt",
}
NETWORK_KIND = {"静态网络", "动态网络"}
TYPE_SOURCE = re.compile(r"^SOURCE:\s*(?P<name>[^\r\n]+)\r?$", re.MULTILINE)
TYPE_SECTION = re.compile(r"^SECTION:\s*(?P<name>[^\r\n]+)\r?$", re.MULTILINE)
TYPE_CONNECTION_REF = re.compile(r"^原始资料/类型连接\.txt:(?:(?:SOURCE:\s*)?(?P<block>[^\[\]:]+)\[(?P<index>\d+)\]|SOURCE:\s*(?P<root>[^\r\n]+))$")
NETWORK_REF = re.compile(r"^(?P<file>[^:]+\.json):(?P<collection>[A-Za-z_][\w-]*)\[(?P<index>\d+)\]$")
_FILE_CACHE: dict[str, tuple[str, Any]] = {}
_BLOCK_CACHE: dict[tuple[str, str], list[dict[str, Any]]] = {}
_LINE_CACHE: dict[str, list[str]] = {}
_LIBRARY_CACHE: dict[str, list[tuple[int, re.Match[str], str]]] = {}
_SOURCE_VALUE_CACHE: dict[tuple[str, str, int], tuple[Any | None, str | None]] = {}


def _cached_file(path: Path, parse_json: bool = False) -> tuple[str, Any | None, str | None]:
    key = f"{path.resolve()}::{parse_json}"
    if key in _FILE_CACHE:
        digest, value = _FILE_CACHE[key]
        return digest, value, None
    if not path.is_file():
        return "", None, "来源文件不存在"
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8-sig")
        value = json.loads(text) if parse_json else text
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return "", None, f"来源内容不可解析: {type(exc).__name__}: {exc}"
    _FILE_CACHE[key] = (digest, value)
    return digest, value, None


def _cached_lines(path: Path, text: str) -> list[str]:
    key = str(path.resolve())
    if key not in _LINE_CACHE:
        _LINE_CACHE[key] = text.splitlines()
    return _LINE_CACHE[key]


def _hash(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_literal(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError, TypeError):
        return None


def _source_ref(row: dict[str, Any]) -> str:
    value = row.get("source_ref")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        if isinstance(raw, str):
            return raw
        if value.get("file") == "原始资料/资料库.txt":
            return repr(value)
    return ""


def _base(kind: str, source_ref: str, path: Path | None) -> dict[str, Any]:
    result = {"source_kind": kind, "source_ref": source_ref, "file_reachable": bool(path and path.is_file()), "content_parseable": False, "object_located": False, "semantic_usable": False, "current_version_confirmed": False, "workflow_allowed": False, "resolution_status": "unresolved", "resolution_methods": [], "candidates": [], "errors": []}
    if path:
        result["source_file"] = str(path).replace("\\", "/")
        if path.is_file():
            result["source_file_sha256"] = _cached_file(path)[0]
    return result


def _finish(result: dict[str, Any], *, item: Any = None, raw: str = "", method: str, parseable: bool = True, semantic: bool = True, identity: dict[str, Any] | None = None) -> dict[str, Any]:
    result["resolution_methods"].append(method)
    result["content_parseable"] = parseable
    result["object_located"] = True
    result["semantic_usable"] = semantic
    result["current_version_confirmed"] = bool(result.get("source_file_sha256"))
    result["resolution_status"] = "resolved" if parseable and semantic else "readable_needs_review"
    if item is not None:
        result["object_type"] = type(item).__name__
        result["object_keys"] = sorted(item) if isinstance(item, dict) else []
        result["object_sha256"] = _hash(item)
        result["content_preview"] = json.dumps(item, ensure_ascii=False)[:500]
    elif raw:
        result["object_type"] = "raw_text"
        result["content_sha256"] = _text_hash(raw)
        result["content_preview"] = raw[:500]
    if identity is not None:
        result["identity"] = identity
    return result


def _json_file(root: Path, relative: str) -> tuple[Path, Any | None, str | None]:
    path = root / relative
    _, value, error = _cached_file(path, parse_json=True)
    return path, value, error


def _resolve_library(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    path = root / SOURCE_FILES["资料库"]
    result = _base("资料库", _source_ref(row), path)
    if not path.is_file():
        result["errors"].append("来源文件不存在")
        return result
    ref = _parse_literal(row.get("source_ref"))
    locator = ref.get("locator") if isinstance(ref, dict) else row.get("source_id")
    line_start = ref.get("line_start") if isinstance(ref, dict) else None
    _, text, error = _cached_file(path)
    if error:
        result["errors"].append(error)
        return result
    lines = _cached_lines(path, str(text))
    cache_key = str(path.resolve())
    headings = _LIBRARY_CACHE.get(cache_key, [])
    pattern = re.compile(r"^(?:###|##\s*板块)\s*(?P<number>\d+(?:\.\d+)?)[_：: ](?P<title>.+?)\s*$")
    if not headings:
        for index, line in enumerate(lines):
            match = pattern.match(line.strip())
            if match:
                headings.append((index, match, line.strip()))
        _LIBRARY_CACHE[cache_key] = headings
    key = str(locator or "").replace("_", " ").replace("　", " ").strip().lower()
    candidates = [(index, match, heading) for index, match, heading in headings if f"{match.group('number')} {match.group('title').strip()}".lower().replace("_", " ") == key]
    if not candidates and isinstance(line_start, int):
        candidates = [(index, match, heading) for index, match, heading in headings if index + 1 == line_start]
        if candidates:
            result["resolution_methods"].append("line_start_recovery")
    if len(candidates) != 1:
        result["candidates"] = [heading for _, _, heading in candidates]
        result["errors"].append(f"资料库对象候选数为 {len(candidates)}")
        result["resolution_status"] = "ambiguous" if len(candidates) > 1 else "unresolved"
        return result
    index, match, heading = candidates[0]
    end = next((other[0] for other in headings if other[0] > index), len(lines))
    content = "\n".join(lines[index:end])
    identity = {"status": "matched" if str(row.get("source_id")) == f"{match.group('number')}_{match.group('title').strip()}" else "review", "source_id": row.get("source_id"), "resolved_locator": f"{match.group('number')}_{match.group('title').strip()}"}
    return _finish(result, raw=content, method="heading_exact" if not result["resolution_methods"] else "heading_plus_line_start", identity=identity) | {"line_start": index + 1, "line_end": end, "resolved_locator": identity["resolved_locator"], "heading": heading}


def _resolve_network(root: Path, row: dict[str, Any], kind: str) -> dict[str, Any]:
    path = root / SOURCE_FILES[kind]
    source_ref = _source_ref(row)
    result = _base(kind, source_ref, path)
    match = NETWORK_REF.fullmatch(source_ref)
    if not match:
        result["errors"].append("网络引用不是 file:collection[index] 格式")
        return result
    ref_file = match.group("file")
    expected_ref = SOURCE_FILES[kind].replace("\\", "/")
    if ref_file.replace("\\", "/") != expected_ref:
        result["errors"].append(f"引用文件 {ref_file} 与当前主文件 {expected_ref} 不一致")
        return result
    _, document, error = _json_file(root, SOURCE_FILES[kind])
    if error:
        result["errors"].append(error)
        return result
    collection, index = match.group("collection"), int(match.group("index"))
    value = document.get(collection) if isinstance(document, dict) else None
    if not isinstance(value, list) or index >= len(value):
        result["errors"].append("网络集合不存在或数组下标越界")
        return result
    item = value[index]
    expected = row.get("source_id")
    identity_value = item.get("id") if kind == "动态网络" and isinstance(item, dict) else None
    if kind == "静态网络" and isinstance(item, dict):
        identity_value = f"STATIC:{item.get('source')}->{item.get('target')}#{index + 1}"
    identity = {"status": "matched" if identity_value is None or str(identity_value) == str(expected) else "mismatch", "expected": expected, "actual": identity_value}
    result = _finish(result, item=item, method="json_collection_index", identity=identity)
    if identity["status"] == "mismatch":
        result["semantic_usable"] = False
        result["resolution_status"] = "readable_needs_review"
        result["errors"].append("source_id 与来源对象身份不一致")
    return result | {"collection": collection, "array_index_zero_based": index}


def _text_blocks(text: str, pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    matches = list(pattern.finditer(text))
    return [{"name": match.group("name").strip(), "start": match.start(), "end": matches[index + 1].start() if index + 1 < len(matches) else len(text), "line_start": text[:match.start()].count("\n") + 1} for index, match in enumerate(matches)]


def _cached_text_blocks(path: Path, text: str, pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    key = (str(path.resolve()), pattern.pattern)
    if key not in _BLOCK_CACHE:
        _BLOCK_CACHE[key] = _text_blocks(text, pattern)
    return _BLOCK_CACHE[key]


def _cached_source_value(path: Path, text: str, block: dict[str, Any]) -> tuple[Any | None, str | None]:
    key = (str(path.resolve()), block["name"], block["start"])
    if key in _SOURCE_VALUE_CACHE:
        return _SOURCE_VALUE_CACHE[key]
    raw = text[block["start"]:block["end"]].strip()
    payload = raw.split("\n", 1)[1].lstrip("= \t\r\n") if "\n" in raw else ""
    try:
        value = json.JSONDecoder().raw_decode(payload)[0]
        result = (value, None)
    except json.JSONDecodeError as exc:
        result = (None, f"SOURCE 块 JSON 不可解析: {exc}")
    _SOURCE_VALUE_CACHE[key] = result
    return result


def prepare_source_cache(root: str | Path, kinds: set[str] | None = None) -> dict[str, Any]:
    """Build read-only file and boundary caches before a large audit."""
    project = Path(root).expanduser().resolve()
    prepared: dict[str, Any] = {}
    selected = set(SOURCE_FILES) if kinds is None else set(kinds)
    for kind, relative in SOURCE_FILES.items():
        if kind not in selected:
            continue
        path = project / relative
        digest, value, error = _cached_file(path, parse_json=kind in NETWORK_KIND)
        item = {"file": relative, "reachable": bool(digest), "sha256": digest or None}
        if error:
            item["error"] = error
        elif kind in {"类型系统", "类型系统来源块", "类型连接"}:
            text = str(value)
            item["source_block_count"] = len(_cached_text_blocks(path, text, TYPE_SOURCE))
            if kind == "类型系统":
                item["section_count"] = len(_cached_text_blocks(path, text, TYPE_SECTION))
        prepared[kind] = item
    return prepared


def _resolve_type_text(root: Path, row: dict[str, Any], kind: str) -> dict[str, Any]:
    path = root / SOURCE_FILES[kind]
    source_ref = _source_ref(row)
    result = _base(kind, source_ref, path)
    if not path.is_file():
        result["errors"].append("来源文件不存在")
        return result
    _, text, error = _cached_file(path)
    if error:
        result["errors"].append(error)
        return result
    text = str(text)
    if kind == "锚点网络":
        line_match = re.search(r":(?P<line>\d+)$", source_ref)
        if not line_match:
            result["errors"].append("锚点网络引用缺少行号")
            return result
        line = int(line_match.group("line")); lines = _cached_lines(path, text)
        if not 1 <= line <= len(lines):
            result["errors"].append("锚点网络行号越界")
            return result
        neighborhood = "\n".join(lines[max(0, line - 3):min(len(lines), line + 4)])
        identity = {"status": "matched" if str(row.get("source_id")) in neighborhood else "review", "source_id": row.get("source_id")}
        return _finish(result, raw=neighborhood, method="line_and_neighborhood", identity=identity) | {"line_start": line, "line_end": min(len(lines), line + 3)}
    if kind == "类型系统来源块":
        match = re.fullmatch(r"原始资料/类型系统\.txt:SOURCE\[(\d+)\]", source_ref)
        blocks = _cached_text_blocks(path, text, TYPE_SOURCE)
        if not match or int(match.group(1)) < 1 or int(match.group(1)) > len(blocks):
            result["errors"].append("类型系统 SOURCE 块索引越界或格式错误")
            return result
        block = blocks[int(match.group(1)) - 1]; raw = text[block["start"]:block["end"]].strip()
        item, parse_error = _cached_source_value(path, text, block)
        try:
            if parse_error:
                raise json.JSONDecodeError(parse_error, raw, 0)
            return _finish(result, item=item, method="source_block_index", identity={"status": "structural", "source_id": row.get("source_id")}) | {"source_block": block["name"], "line_start": block["line_start"]}
        except json.JSONDecodeError:
            return _finish(result, raw=raw, method="source_block_raw_text", parseable=False, semantic=True, identity={"status": "structural_review", "source_id": row.get("source_id")}) | {"source_block": block["name"], "line_start": block["line_start"]}
    if kind == "类型系统":
        match = re.fullmatch(r"原始资料/类型系统\.txt:SECTION:\s*(.+)", source_ref)
        sections = _cached_text_blocks(path, text, TYPE_SECTION)
        candidates = [block for block in sections if match and block["name"] == match.group(1).strip()]
        if not candidates and match:
            legacy_name = match.group(1).strip()
            blocks = _cached_text_blocks(path, text, TYPE_SOURCE)
            candidates = [
                block for block in blocks
                if re.search(rf"(?<![\w]){re.escape(legacy_name)}(?![\w])", text[block["start"]:block["end"]])
            ]
            if len(candidates) == 1:
                block = candidates[0]
                raw = text[block["start"]:block["end"]].strip()
                return _finish(result, raw=raw, method="legacy_section_name_unique_source_block", parseable=True, semantic=True, identity={"status": "legacy_recovered", "source_id": row.get("source_id"), "source_block": block["name"]}) | {"source_block": block["name"], "line_start": block["line_start"], "legacy_name": legacy_name}
        if len(candidates) != 1:
            result["candidates"] = [block["name"] for block in candidates]; result["errors"].append("类型系统 SECTION 无法唯一定位"); result["resolution_status"] = "ambiguous" if len(candidates) > 1 else "unresolved"; return result
        block = candidates[0]; raw = text[block["start"]:block["end"]].strip()
        return _finish(result, raw=raw, method="section_exact", identity={"status": "matched" if str(row.get("source_id")) == block["name"] else "review", "source_id": row.get("source_id")}) | {"section": block["name"], "line_start": block["line_start"]}
    return result


def _resolve_type_connection(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    path = root / SOURCE_FILES["类型连接"]
    source_ref = _source_ref(row)
    result = _base("类型连接", source_ref, path)
    if not path.is_file():
        result["errors"].append("来源文件不存在")
        return result
    match = TYPE_CONNECTION_REF.fullmatch(source_ref)
    if not match:
        result["errors"].append("类型连接引用格式不受支持")
        return result
    _, text, error = _cached_file(path)
    if error:
        result["errors"].append(error)
        return result
    text = str(text)
    blocks = _cached_text_blocks(path, text, TYPE_SOURCE)
    name = (match.group("block") or match.group("root") or "").strip()
    candidates = [block for block in blocks if block["name"] == name]
    if len(candidates) != 1:
        result["candidates"] = [block["name"] for block in candidates]
        result["errors"].append("类型连接 SOURCE 块无法唯一定位")
        result["resolution_status"] = "ambiguous" if len(candidates) > 1 else "unresolved"
        return result
    block = candidates[0]
    raw = text[block["start"]:block["end"]].strip()
    value, parse_error = _cached_source_value(path, text, block)
    try:
        if parse_error:
            raise json.JSONDecodeError(parse_error, raw, 0)
    except json.JSONDecodeError:
        return _finish(result, raw=raw, method="source_block_raw_text", parseable=False, semantic=True, identity={"status": "structural_review", "source_id": row.get("source_id")}) | {"source_block": name, "line_start": block["line_start"]}
    if match.group("root"):
        return _finish(result, item=value, method="source_block_root", identity={"status": "structural", "source_id": row.get("source_id")}) | {"source_block": name, "line_start": block["line_start"]}
    index = int(match.group("index"))
    if isinstance(value, list) and 1 <= index <= len(value):
        item = value[index - 1]
    elif isinstance(value, dict) and index == 1:
        item = value
    else:
        result["errors"].append("类型连接数组下标越界或对象根引用必须使用 [1]")
        return result
    stable_ids = [key for key in ("connection_id", "dynamic_combination_id", "static_connection_id", "id", "rule_id", "template_id") if isinstance(item, dict) and item.get(key)]
    matched = any(str(item[key]) == str(row.get("source_id")) for key in stable_ids)
    identity = {"status": "matched" if matched else ("structural" if not stable_ids else "mismatch"), "stable_id_fields": stable_ids, "source_id": row.get("source_id")}
    resolved = _finish(result, item=item, method="source_block_array_index", identity=identity)
    if identity["status"] == "mismatch":
        resolved["semantic_usable"] = False
        resolved["resolution_status"] = "readable_needs_review"
        resolved["errors"].append("source_id 与类型连接稳定身份不一致")
    return resolved | {"source_block": name, "source_index_one_based": index, "line_start": block["line_start"]}


def resolve(root: str | Path, row: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    kind = str(row.get("source_kind") or "")
    if kind not in SOURCE_FILES:
        return {"source_kind": kind, "source_ref": _source_ref(row), "resolution_status": "unresolved", "errors": ["未知 source_kind"]}
    if kind == "资料库":
        result = _resolve_library(root, row)
    elif kind in NETWORK_KIND:
        result = _resolve_network(root, row, kind)
    elif kind == "类型连接":
        result = _resolve_type_connection(root, row)
    else:
        result = _resolve_type_text(root, row, kind)
    result["binding_id"] = row.get("binding_id")
    result["source_id"] = row.get("source_id")
    result["audit_only"] = True
    return result