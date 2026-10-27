"""Analyze source quality and produce granular usage permissions.

The analyzer deliberately separates parseability, evidence completeness and
project confirmation. A partial source can therefore support a draft without
being promoted to a formal fact source.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"待补充|待确认|未确认|暂无|TBD|TODO|示例内容|这里填写")
SOURCE_KINDS = {
    "资料库.txt": "资料库",
    "类型系统.txt": "类型系统",
    "类型连接.txt": "类型连接",
    "动态网络.txt": "动态网络",
    "静态网络.txt": "静态网络",
    "锚点网络.txt": "锚点网络",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value or "")


def _level(item: dict[str, Any]) -> str:
    if item["parse_status"] != "parseable":
        return "blocked"
    if item["identity_coverage"] < 0.8 or item["evidence_coverage"] < 0.5:
        return "candidate"
    if item["missing_fields"] or item["placeholder_count"]:
        return "draft_usable"
    return "verified"


def _jsonl_count(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            if isinstance(json.loads(line), dict):
                count += 1
        except json.JSONDecodeError:
            continue
    return count


def _jsonl_ids(path: Path, key: str) -> set[str]:
    """Return stable object IDs only when every JSONL row provides one."""
    if not path.is_file():
        return set()
    identifiers: set[str] = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            return set()
        identifier = str(item.get(key) or "").strip() if isinstance(item, dict) else ""
        if not identifier or identifier in identifiers:
            return set()
        identifiers.add(identifier)
    return identifiers


def _coverage_evidence(root: Path, source: str, total: int) -> dict[str, Any]:
    """Return only evidence that can be traced to an existing derived view."""
    evidence = root / "文档" / "证据"
    governance = read_json(evidence / "全量资料治理" / "全量检查报告.json", {})
    kind = SOURCE_KINDS.get(source, "")
    governance_item = (governance.get("summary", {}) or {}).get(kind, {})
    governed = (
        governance_item.get("status") == "passed"
        and int(governance_item.get("pending", 0) or 0) == 0
        and int(governance_item.get("blocking", 0) or 0) == 0
    )
    covered_fields: set[str] = set()
    traces: list[str] = []
    if source == "资料库.txt":
        dependency_ids = _jsonl_ids(evidence / "资料库依赖分类日志.jsonl", "entry_id")
        example_ids = _jsonl_ids(evidence / "资料库示例修复日志.jsonl", "entry_id")
        if len(dependency_ids) >= total:
            covered_fields.add("dependencies")
            traces.append("文档/证据/资料库依赖分类日志.jsonl")
        if len(example_ids) >= total:
            covered_fields.add("examples")
            traces.append("文档/证据/资料库示例修复日志.jsonl")
    elif source == "类型系统.txt":
        profiles = read_json(root / "配置" / "类型配置模板.json", {}).get("types", {})
        if isinstance(profiles, dict) and len(profiles) >= total:
            covered_fields.update({"core_elements", "style_constraints"})
            traces.append("配置/类型配置模板.json")
    elif source == "类型连接.txt":
        rows = read_json(evidence / "全量资料治理" / "类型连接_规范化.json", [])
        if isinstance(rows, list) and len(rows) >= total and all(item.get("source_connection_id") and item.get("source_ref") for item in rows if isinstance(item, dict)):
            covered_fields.add("source_connection_id")
            traces.append("文档/证据/全量资料治理/类型连接_规范化.json")
    elif source == "锚点网络.txt":
        scene_ids = _jsonl_ids(evidence / "锚点网络场景绑定日志.jsonl", "anchor_id")
        definition_ids = _jsonl_ids(evidence / "锚点网络定义日志.jsonl", "anchor_id")
        location_ids = _jsonl_ids(evidence / "锚点网络文本位置日志.jsonl", "anchor_id")
        if len(definition_ids) >= total:
            covered_fields.add("anchor_definition")
            traces.append("文档/证据/锚点网络定义日志.jsonl")
        if len(scene_ids) >= total:
            covered_fields.add("scene_binding")
            traces.append("文档/证据/锚点网络场景绑定日志.jsonl")
        if len(location_ids) >= total:
            covered_fields.add("text_location")
            traces.append("文档/证据/锚点网络文本位置日志.jsonl")
    elif source == "锚点网络.txt":
        rows = read_json(evidence / "全量资料治理" / "锚点网络_规范化.json", [])
        if isinstance(rows, list) and len(rows) >= total and all(item.get("anchor_definition") and item.get("source_ref") for item in rows if isinstance(item, dict)):
            covered_fields.add("anchor_definition")
            traces.append("文档/证据/全量资料治理/锚点网络_规范化.json")
    return {
        "governance_passed": governed,
        "covered_fields": sorted(covered_fields),
        "traces": traces,
    }


def analyze(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    depth = read_json(evidence / "来源深度检查报告.json", {})
    registry = read_json(evidence / "资源注册表.json", {})
    sources: list[dict[str, Any]] = []
    for raw in depth.get("sources", []):
        if not isinstance(raw, dict):
            continue
        total = max(int(raw.get("total_items", 0) or 0), 1)
        extractable = int(raw.get("extractable", 0) or 0)
        coverage = _coverage_evidence(root, str(raw.get("source", "unknown")), total)
        missing = [
            str(field) for field in raw.get("missing_fields", [])
            if str(field) not in coverage["covered_fields"]
        ]
        # The legacy deep report counts marker strings over entire source files.
        # It is preserved for auditability but is not an object-level pending count.
        legacy_placeholders = int(raw.get("placeholder_count", 0) or 0)
        placeholders = 0 if coverage["governance_passed"] else legacy_placeholders
        identity = 1.0 if raw.get("unique_ids", raw.get("total_items", 0)) else 0.0
        evidence_coverage = max(0.0, 1.0 - min(1.0, len(missing) / 5))
        item = {
            "source": str(raw.get("source", "unknown")),
            "parse_status": "parseable" if extractable == int(raw.get("total_items", extractable) or extractable) else "partial_parse",
            "extractable_rate": round(extractable / total, 4),
            "identity_coverage": round(identity, 4),
            "evidence_coverage": round(evidence_coverage, 4),
            "missing_fields": missing,
            "placeholder_count": placeholders,
            "placeholder_rate": round(placeholders / total, 4),
            "legacy_placeholder_count": legacy_placeholders,
            "governance_evidence": coverage,
            "source_report_status": "complete" if (
                extractable == int(raw.get("total_items", extractable) or extractable)
                and coverage["governance_passed"]
                and not missing
                and not placeholders
            ) else "partial",
        }
        item["usage_level"] = _level(item)
        item["allowed_uses"] = {
            "search_and_retrieval": item["usage_level"] in {"candidate", "draft_usable", "verified"},
            "brainstorming": item["usage_level"] in {"candidate", "draft_usable", "verified"},
            "draft_structure": item["usage_level"] in {"draft_usable", "verified"},
            "draft_prose": item["usage_level"] in {"draft_usable", "verified"},
            "formal_fact": item["usage_level"] == "verified",
        }
        actions = []
        actions.extend({"field": field, "action": "补齐字段并附可核验 source_ref"} for field in missing)
        if placeholders:
            actions.append({"field": "placeholder_content", "action": "逐条替换占位内容，或显式标记为 unknown"})
        if item["source_report_status"] == "partial":
            actions.append({"field": "source_confirmation", "action": "确认原始来源、版本、责任人和适用范围"})
        item["improvement_actions"] = actions
        sources.append(item)

    confirmation = registry.get("resources", {}).get("project_source_confirmation", {})
    confirmed = confirmation.get("source_quality") == "complete"
    for item in sources:
        if item["usage_level"] == "verified" and not confirmed:
            item["usage_level"] = "draft_usable"
            item["allowed_uses"]["formal_fact"] = False
            item["improvement_actions"].append({"field": "project_confirmation", "action": "完成项目来源确认后才能升级 verified"})
    counts = Counter(item["usage_level"] for item in sources)
    report = {
        "schema_version": "source-quality-analysis-1.0",
        "generated_at": now(),
        "policy": "分层放宽创作使用，不把未核验资料标记为正式事实",
        "levels": {
            "blocked": "不可使用，必须先修复解析或身份问题",
            "candidate": "可检索、比较和头脑风暴，不得直接写成事实",
            "draft_usable": "可进入大纲、分纲、场景和草稿，必须保留 source_ref 与不确定性",
            "verified": "可作为正式事实，仅在字段完整、无占位且项目来源已确认时成立",
        },
        "source_count": len(sources),
        "level_counts": dict(counts),
        "sources": sources,
        "next_actions": sorted({action["action"] for item in sources for action in item["improvement_actions"]}),
    }
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "来源质量自主分析报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = analyze(args.project_root)
    print(json.dumps({"status": "passed", "source_count": report["source_count"], "level_counts": report["level_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())