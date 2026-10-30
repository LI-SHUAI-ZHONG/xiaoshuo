"""Build hash-locked source-object mappings for legacy upgrade exceptions."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIXTURE_ID = "TB-05637"
TYPE_IDS = {"二次元", "仙侠", "体育", "军事", "历史", "同人", "悬疑", "游戏", "灵异", "玄幻", "科幻", "耽美", "言情", "轻小说", "都市"}


def _hash(value: Any) -> str:
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _blocks(path: Path) -> list[tuple[str, Any, int, int]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    starts = [(number, line[8:]) for number, line in enumerate(lines) if line.startswith("SOURCE: ")]
    output = []
    for position, (start, name) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        try:
            output.append((name, json.loads("\n".join(lines[start + 2:end]).strip()), start + 1, end))
        except json.JSONDecodeError:
            continue
    return output


def _type_object(type_id: str, legacy_lines: set[int], candidates: list[tuple[str, Any, int, int]]) -> tuple[str, Any, int, int] | None:
    scored = []
    for candidate in candidates:
        name, value, start, end = candidate
        text = name + "\n" + json.dumps(value, ensure_ascii=False, sort_keys=True)
        if not re.search(rf"(?<![\u4e00-\u9fffA-Za-z0-9]){re.escape(type_id)}(?![\u4e00-\u9fffA-Za-z0-9])", text):
            continue
        scored.append((sum(start <= line <= end for line in legacy_lines), int(type_id in name), -(end - start), candidate))
    if not scored:
        return None
    scored.sort(reverse=True, key=lambda item: item[:3])
    if scored[0][0] == 0 and scored[0][1] == 0:
        return None
    if len(scored) > 1 and scored[0][:3] == scored[1][:3]:
        return None
    return scored[0][3]


def build(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    binding_path = evidence / "全量资料解释词创作绑定.json"
    binding_rows = json.loads(binding_path.read_text(encoding="utf-8-sig"))["records"]
    bindings = {str(row["binding_id"]): row for row in binding_rows if isinstance(row, dict) and row.get("binding_id")}
    exceptions_path = evidence / "全量资料升级运行" / "20260816T101311Z-295bb554-异常审计" / "exceptions.jsonl"
    exceptions = [json.loads(line) for line in exceptions_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    type_file, connection_file = root / "原始资料" / "类型系统.txt", root / "原始资料" / "类型连接.txt"
    type_blocks = _blocks(type_file)
    connection_blocks = {name: (value, start, end) for name, value, start, end in _blocks(connection_file)}
    mappings, unresolved = [], []
    for issue in exceptions:
        binding_id, source_id, kind = str(issue["binding_id"]), str(issue["source_id"]), str(issue["source_kind"])
        if binding_id == FIXTURE_ID:
            continue
        if kind == "类型系统":
            try:
                legacy_lines = {int(line) for line in ast.literal_eval(issue["source_ref"]["raw"]).get("matched_lines", [])}
            except (SyntaxError, ValueError, TypeError, KeyError):
                legacy_lines = set()
            found = _type_object(source_id, legacy_lines, type_blocks)
            source_file = type_file
        elif kind == "类型连接":
            name = "类型静态连接字段说明.json" if binding_id == "TB-11278" else source_id.rsplit(":", 1)[0]
            connection_found = connection_blocks.get(name)
            found = (name, *connection_found) if connection_found is not None else None
            source_file = connection_file
        else:
            found = None
            source_file = type_file
        if found is None:
            unresolved.append({"binding_id": binding_id, "reason": "无法唯一回读可解析的原始 SOURCE 对象"})
            continue
        name, value, start, end = found
        if binding_id == "TB-11278":
            if name != "类型静态连接字段说明.json" or not isinstance(value, dict) or value.get("connection_id") != ast.literal_eval(source_id):
                unresolved.append({"binding_id": binding_id, "reason": "字段定义内容无法与旧 source_id 精确对应"})
                continue
            name, value = f"{name}#connection_id", {"connection_id": value["connection_id"]}
        original = {"file": str(source_file.relative_to(root)).replace("\\", "/"), "source_block": name, "line_start": start, "line_end": end, "object": value}
        mappings.append({"schema_version": "full-source-derived-location-mapping-1.0", "binding_id": binding_id, "source_id": source_id, "mapping_status": "verified_candidate", "automatic_reprocess_allowed": False, "source_file_sha256": _hash(source_file.read_bytes()), "derived_original_object": original, "derived_original_object_sha256": _hash(original), "derivation_method": "parsed_SOURCE_block_with_legacy_identity_cross_check", "legacy_binding_sha256": _hash({key: bindings[binding_id].get(key) for key in ("binding_id", "source_id", "source_kind", "source_ref")})})
    output = evidence / "全量资料升级派生定位"
    output.mkdir(parents=True, exist_ok=True)
    mapping_path = output / "已验证候选映射.jsonl"
    mapping_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in mappings), encoding="utf-8")
    exclusion = {"schema_version": "full-source-formal-baseline-exclusion-1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "binding_file_sha256": _hash(binding_path.read_bytes()), "records": [{"binding_id": FIXTURE_ID, "source_id": "TYPE-SOURCE:99", "quarantine_status": "fixture_only_excluded_from_formal_baseline", "reason": "原始对象标记 fixture_only，测试夹具不得进入正式基线", "original_binding_sha256": _hash({key: bindings[FIXTURE_ID].get(key) for key in ("binding_id", "source_id", "source_kind", "source_ref")})}]}
    (evidence / "全量资料正式基线排除清单.json").write_text(json.dumps(exclusion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"schema_version": "full-source-derived-location-rebuild-report-1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "mapping_count": len(mappings), "unresolved_count": len(unresolved), "unresolved": unresolved, "mapping_file": str(mapping_path.relative_to(root)).replace("\\", "/"), "fixture_excluded_binding_id": FIXTURE_ID, "status": "passed" if len(mappings) == 38 and not unresolved else "blocked"}
    (output / "重建报告.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    print(json.dumps(build(parser.parse_args().project_root), ensure_ascii=False))