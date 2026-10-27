# -*- coding: utf-8 -*-
"""Build a project-independent type profile template from the two type sources."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TYPE_SYSTEM = ROOT / "08_原始资料" / "类型系统.txt"
TYPE_CONNECTIONS = ROOT / "08_原始资料" / "类型连接.txt"
OUTPUT = ROOT / "config" / "type_profile_template.json"

TYPE_NAMES = [
    "玄幻", "仙侠", "科幻", "悬疑", "言情", "都市", "历史", "军事",
    "游戏", "体育", "灵异", "同人", "二次元", "耽美", "轻小说",
]
COMMON_COMBINATIONS = [
    ("玄幻", "仙侠"), ("科幻", "悬疑"), ("都市", "言情"),
    ("历史", "军事"), ("灵异", "悬疑"), ("游戏", "二次元"),
    ("轻小说", "二次元"), ("科幻", "都市"), ("玄幻", "历史"),
    ("言情", "耽美"), ("同人", "二次元"), ("体育", "都市"),
]
CORE_KEYS = ("核心元素", "必备元素", "core_elements", "essential_elements")
READER_KEYS = ("读者期待", "目标读者", "reader_expectations", "target_readers")
CONFLICT_KEYS = ("冲突", "不兼容", "conflicts", "incompatibilities")
RESOLUTION_KEYS = ("解决", "解决方式", "适配", "resolution", "resolutions")
MECHANISM_KEYS = ("推荐机制", "融合方式", "机制", "recommended_mechanisms", "fusion_method")


def read_source(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    # Some assembled source files contain literal escaped CR/LF markers.
    return text.replace("`r`n", "\n").replace("\\r\\n", "\n")


def scalar_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in re.split(r"[、,，;；|/]", value) if part.strip()]
    return []


def walk_json(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def object_cache(roots: list[Any]) -> list[tuple[dict[str, Any], str]]:
    return [(obj, json.dumps(obj, ensure_ascii=False)) for root in roots for obj in walk_json(root) if isinstance(obj, dict)]


def extract_json_values(text: str) -> list[Any]:
    values: list[Any] = []
    decoder = json.JSONDecoder()
    # The assembled files are SOURCE-delimited JSON documents. Decode only
    # the first JSON value in each source block; scanning nested lines again
    # would repeatedly retry large arrays and make indexing unnecessarily slow.
    blocks = re.split(r"(?m)^SOURCE:\s*[^\r\n]*\r?\n", text)[1:]
    if not blocks:
        blocks = [text]
    for block in blocks:
        match = re.search(r"(?m)^\s*(?:\{|\[)", block)
        if not match:
            continue
        try:
            value, _ = decoder.raw_decode(block[match.start() :])
        except json.JSONDecodeError:
            continue
        values.append(value)
    return values


def profile_from_sources(text: str, type_name: str, objects: list[tuple[dict[str, Any], str]] | None = None) -> dict[str, Any]:
    elements: list[str] = []
    readers: dict[str, str] = {}
    evidence = False
    source_objects = objects if objects is not None else object_cache(extract_json_values(text))
    for obj, blob in source_objects:
        if type_name not in blob:
            continue
        local_elements: list[str] = []
        for key in CORE_KEYS:
            local_elements.extend(scalar_list(obj.get(key)))
        if local_elements:
            elements.extend(local_elements)
            evidence = True
        for key in READER_KEYS:
            value = obj.get(key)
            if isinstance(value, dict):
                for field, item in value.items():
                    if isinstance(item, (str, int, float, bool)):
                        readers[str(field)] = str(item)
            elif value not in (None, "", [], {}):
                readers["期望"] = str(value)
                evidence = True
    # Also support plain-text type sections in assembled source documents.
    for match in re.finditer(re.escape(type_name), text):
        window = text[match.start() : match.start() + 1800]
        for label in CORE_KEYS[:2]:
            found = re.search(rf"{re.escape(label)}\s*[：:]\s*([^\n]+)", window)
            if found:
                elements.extend(scalar_list(found.group(1)))
                evidence = True
        for label in READER_KEYS[:2]:
            found = re.search(rf"{re.escape(label)}\s*[：:]\s*([^\n]+)", window)
            if found:
                readers["期望"] = found.group(1).strip()
                evidence = True
    unique_elements = list(dict.fromkeys(elements))
    return {"core_elements": unique_elements, "reader_params": readers, "source_status": "extracted" if evidence else "template"}


def find_combo_records(text: str, objects: list[tuple[dict[str, Any], str]] | None = None) -> dict[tuple[str, str], dict[str, list[str]]]:
    result: dict[tuple[str, str], dict[str, list[str]]] = {}
    source_objects = objects if objects is not None else object_cache(extract_json_values(text))
    for obj, blob in source_objects:
        names = [name for name in TYPE_NAMES if name in blob]
        ids = obj.get("component_type_ids", [])
        if len(names) < 2 and isinstance(ids, list):
            names = [name for name in TYPE_NAMES if any(name.upper() in str(item).upper() for item in ids)]
        if len(names) < 2:
            continue
        pair = tuple(sorted(names[:2]))
        result[pair] = {
            "conflicts": first_values(obj, CONFLICT_KEYS),
            "resolutions": first_values(obj, RESOLUTION_KEYS),
            "recommended_mechanisms": first_values(obj, MECHANISM_KEYS),
        }
    return result


def first_values(obj: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        values = scalar_list(obj.get(key))
        if values:
            return values
    return []


def build_combination(pair: tuple[str, str], profiles: dict[str, dict[str, Any]], extracted: dict[tuple[str, str], dict[str, list[str]]]) -> dict[str, Any]:
    first, second = pair
    source = extracted.get(tuple(sorted(pair)), {})
    conflicts = source.get("conflicts", [])
    resolutions = source.get("resolutions", [])
    mechanisms = source.get("recommended_mechanisms", [])
    if not mechanisms:
        mechanisms = [f"以{first}提供核心驱动，以{second}提供结构或表达机制，并在阶段边界记录融合权重"]
    return {
        "combination_id": f"{first}_{second}",
        "types": [first, second],
        "core_elements": {name: profiles[name]["core_elements"] for name in pair},
        "reader_params": {name: profiles[name]["reader_params"] for name in pair},
        "conflicts": conflicts,
        "resolutions": resolutions,
        "recommended_mechanisms": mechanisms,
        "source_status": "extracted" if source else "template",
    }


def main() -> int:
    system_text = read_source(TYPE_SYSTEM)
    connection_text = read_source(TYPE_CONNECTIONS)
    system_roots = extract_json_values(system_text)
    connection_roots = extract_json_values(connection_text)
    system_objects = object_cache(system_roots)
    connection_objects = object_cache(connection_roots)
    profiles = {name: profile_from_sources(system_text, name, system_objects) for name in TYPE_NAMES}
    extracted = find_combo_records(connection_text, connection_objects)
    combinations = [build_combination(pair, profiles, extracted) for pair in COMMON_COMBINATIONS]
    document = {
        "schema_version": "type-profile-template-1.0",
        "source_policy": {"project_independent": True, "source_files": ["08_原始资料/类型系统.txt", "08_原始资料/类型连接.txt"]},
        "types": profiles,
        "combinations": combinations,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    conflict_count = sum(len(item["conflicts"]) for item in combinations)
    print(f"已处理类型总数：{len(profiles)}")
    print(f"生成的组合配置文件数：{len(combinations)}")
    print(f"冲突点总数：{conflict_count}")
    print("输出的组合列表（前 10 个）：" + "、".join(item["combination_id"] for item in combinations[:10]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())