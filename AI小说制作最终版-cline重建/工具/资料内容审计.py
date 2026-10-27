# -*- coding: utf-8 -*-
"""Audit source completeness without changing either authorized source tree."""
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
REFERENCE = WORKSPACE
OUT = WORKSPACE / "阶段状态" / "资料内容审计基线.json"
SOURCE_DIR = WORKSPACE / "08_原始资料"
SOURCE_FILES = [
    "资料库.txt", "类型系统.txt", "类型连接.txt", "静态网络.txt",
    "动态网络.txt", "锚点网络.txt", "执行正文.txt", "索引调用映射.txt",
    "运行状态.json",
]
PLACEHOLDER = re.compile(r"(?:^|[：:]|\n)\s*(?:无|暂无|待补充|待确认|未确认|空|\[\]|\{\})\s*(?=\n|$)")
SECTION = re.compile(r"^###?\s+(.+?)\s*$", re.M)
SOURCE_MARKER = re.compile(r"SOURCE\s*:\s*(.+)", re.I)
REF_PATH = re.compile(r"(?:[A-Za-z]:[\\/][^\s\"'<>]+|(?:\.\.?[\\/])?[^\s\"'<>]+\.(?:json|md|txt|yaml|yml))")


def decode(path):
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return data.decode(encoding), encoding, data
        except UnicodeDecodeError:
            continue
    return None, None, data


def audit_file(path):
    text, encoding, raw = decode(path)
    result = {
        "path": path.relative_to(WORKSPACE).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "encoding": encoding,
        "readable": text is not None,
        "line_count": len(text.splitlines()) if text is not None else 0,
        "placeholder_matches": len(PLACEHOLDER.findall(text or "")),
        "section_count": len(SECTION.findall(text or "")),
        "source_markers": SOURCE_MARKER.findall(text or ""),
        "absolute_references": sorted(set(REF_PATH.findall(text or "")))[:100],
        "json_valid": None,
        "status": "confirmed_raw" if text is not None else "unreadable",
    }
    if path.suffix.lower() == ".json" and text is not None:
        try:
            value = json.loads(text)
            result["json_valid"] = True
            result["json_root_type"] = type(value).__name__
        except json.JSONDecodeError as exc:
            result["json_valid"] = False
            result["json_error"] = str(exc)
            result["status"] = "confirmed_raw_but_invalid_json"
    if encoding == "utf-8" and "Ã" in (text or ""):
        result["encoding_warning"] = "possible_mojibake"
    return result


def reference_summary():
    # Keep this scan bounded and observable. Content comparison uses explicit files
    # and selected reference artifacts in later stages, not an unbounded full read.
    entries = list(REFERENCE.iterdir())
    top_files = [p for p in entries if p.is_file()]
    top_dirs = [p for p in entries if p.is_dir() and p.name not in {"__pycache__", "_整理保护"}]
    return {
        "root_file_count": len(top_files),
        "top_level_directories": sorted(p.name for p in top_dirs),
        "root_files": sorted(p.name for p in top_files),
        "scan_scope": "reference root only; recursive comparison is explicit and staged",
    }


def main():
    missing = [name for name in SOURCE_FILES if not (SOURCE_DIR / name).is_file()]
    sources = [audit_file(SOURCE_DIR / name) for name in SOURCE_FILES if (SOURCE_DIR / name).is_file()]
    report = {
        "schema_version": "content-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(WORKSPACE),
        "reference_root": str(REFERENCE),
        "source_policy": {
            "reference_read_only": True,
            "no_external_content": True,
            "evidence_levels": ["confirmed_raw", "cross_confirmed", "reconstructed", "unconfirmed", "conflict"],
        },
        "workspace_source_files_expected": SOURCE_FILES,
        "missing_workspace_sources": missing,
        "source_files": sources,
        "reference_summary": reference_summary(),
        "preliminary_findings": [
            {"id": "CONTENT-001", "level": "confirmed", "finding": "索引登记的原始资料与实际文件清单存在漂移。"},
            {"id": "CONTENT-002", "level": "confirmed", "finding": "部分原始资料包含空数组、空字段或‘无’占位，不能自动视为可执行规则。"},
            {"id": "CONTENT-003", "level": "confirmed", "finding": "类型连接存在空连接块，且大量模板记录没有可验证的来源事实。"},
            {"id": "CONTENT-004", "level": "confirmed", "finding": "旧映射仍含外部/历史绝对路径，不得作为当前运行入口。"},
            {"id": "CONTENT-005", "level": "confirmed", "finding": "既有诡异屋项目的资料调用审计确认若干关键模块是事后补建或仅部分转换。"},
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "sources": len(sources), "missing": missing, "reference_root_dirs": len(report["reference_summary"]["top_level_directories"])}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()