"""Register project source files and verify their identity before execution.

The registry is deliberately independent from the writing pipeline. It makes
path selection, file identity, parseability and source-quality status explicit
so later modules cannot silently consume a different fallback file.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from 项目来源确认 import validate_confirmation


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_status(path: Path) -> tuple[str, int, str | None]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(value, dict):
                count = len(value.get("connections", value.get("items", value.get("combinations", []))))
            elif isinstance(value, list):
                count = len(value)
            else:
                count = 1
            return "parseable", count, None
        if suffix == ".jsonl":
            count = 0
            for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                if not line.strip():
                    continue
                json.loads(line)
                count += 1
            return "parseable", count, None
        text = path.read_text(encoding="utf-8-sig")
        return "parseable", len(text.splitlines()), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return "invalid", 0, f"{type(exc).__name__}: {exc}"


def _resolve(root: Path, *relative_candidates: str) -> Path | None:
    for relative in relative_candidates:
        path = root / relative
        if path.is_file():
            return path
    return None


def _library_index_integrity(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Validate the entry-level index used by prose provenance checks."""
    summary: dict[str, Any] = {
        "status": "missing",
        "row_count": 0,
        "unique_entry_count": 0,
        "duplicate_entry_ids": [],
        "malformed_lines": [],
        "invalid_source_refs": [],
    }
    errors: list[str] = []
    if not path.is_file():
        errors.append("资料库条目索引缺失：文档/资料库索引.jsonl")
        return summary, errors
    ids: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            summary["malformed_lines"].append(line_number)
            continue
        entry_id = row.get("entry_id") if isinstance(row, dict) else None
        source_ref = row.get("source_ref") if isinstance(row, dict) else None
        if not entry_id:
            summary["malformed_lines"].append(line_number)
            continue
        ids.append(str(entry_id))
        summary["row_count"] += 1
        if source_ref is not None and (not isinstance(source_ref, dict) or not source_ref.get("file") or not source_ref.get("locator")):
            summary["invalid_source_refs"].append({"line": line_number, "entry_id": str(entry_id)})
    duplicates = sorted(entry_id for entry_id, count in Counter(ids).items() if count > 1)
    summary["unique_entry_count"] = len(set(ids))
    summary["duplicate_entry_ids"] = duplicates
    summary["status"] = "passed" if not summary["malformed_lines"] and not duplicates and not summary["invalid_source_refs"] else "failed"
    if summary["malformed_lines"]:
        errors.append(f"资料库条目索引存在非法行：{summary['malformed_lines'][:10]}")
    if duplicates:
        errors.append(f"资料库条目索引存在重复entry_id：{duplicates[:10]}")
    if summary["invalid_source_refs"]:
        errors.append("资料库条目索引存在不完整source_ref")
    return summary, errors


def build_registry(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    specs = {
        "type_system": ("原始资料/类型系统.txt",),
        "type_connections": ("文档/证据/类型连接全局索引.json",),
        "type_connection_rules": ("文档/证据/类型连接规则.json", "文档/证据/类型连接采用结构.json"),
        "library": ("原始资料/资料库.txt",),
        "library_index": ("文档/资料库索引.jsonl",),
        "library_adoption_rules": ("文档/证据/采用规则.json",),
        "static_network": ("网络完整数据/静态连接完整数据.json", "原始资料/静态网络.txt"),
        "static_network_index": ("文档/证据/静态网络索引.json",),
        "static_adoption_rules": ("文档/证据/静态连接采用规则.json",),
        "dynamic_network": ("网络完整数据/动态连接完整数据.json", "原始资料/动态网络.txt"),
        "dynamic_network_index": ("文档/证据/动态链索引.jsonl",),
        "dynamic_adoption_rules": ("文档/证据/动态链消费规则.json",),
        "anchor_network": ("原始资料/锚点网络.txt",),
        "anchor_index": ("文档/证据/锚点分类索引.json",),
        "anchor_adoption_rules": ("文档/证据/锚点采用规则.json",),
        "execution_rules": ("文档/证据/执行采用规则.json",),
        "source_depth_report": ("文档/证据/来源深度检查报告.json",),
    }
    resources: dict[str, Any] = {}
    errors: list[str] = []
    partial: list[str] = []
    for resource_id, candidates in specs.items():
        path = _resolve(root, *candidates)
        if path is None:
            resources[resource_id] = {"status": "missing", "candidates": list(candidates)}
            errors.append(f"缺少资源：{resource_id}；候选路径：{', '.join(candidates)}")
            continue
        parse_status, item_count, parse_error = _parse_status(path)
        source_status = "complete"
        if resource_id == "source_depth_report":
            try:
                report = json.loads(path.read_text(encoding="utf-8-sig"))
                source_status = "partial" if any(item.get("status") == "partial" for item in report.get("sources", [])) else "complete"
                partial.extend(
                    f"source_depth:{item.get('source', 'unknown')}"
                    for item in report.get("sources", [])
                    if item.get("status") == "partial"
                )
            except (OSError, UnicodeError, json.JSONDecodeError):
                source_status = "unknown"
        if source_status == "partial" and resource_id != "source_depth_report":
            partial.append(resource_id)
        if parse_status != "parseable":
            errors.append(f"资源不可解析：{resource_id}；{parse_error}")
        resources[resource_id] = {
            "status": parse_status,
            "source_quality": source_status,
            "path": str(path),
            "relative_path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "item_or_line_count": item_count,
        }
    depth_by_source: dict[str, dict[str, Any]] = {}
    depth_path = resources.get("source_depth_report", {}).get("path")
    if depth_path:
        try:
            depth_report = json.loads(Path(depth_path).read_text(encoding="utf-8-sig"))
            depth_by_source = {str(item.get("source")): item for item in depth_report.get("sources", []) if isinstance(item, dict)}
        except (OSError, UnicodeError, json.JSONDecodeError):
            depth_by_source = {}
    resource_source_map = {
        "library": "资料库.txt", "type_system": "类型系统.txt", "type_connections": "类型连接.txt",
        "dynamic_network": "动态网络.txt", "static_network": "静态网络.txt", "anchor_network": "锚点网络.txt",
    }
    for resource_id, source_name in resource_source_map.items():
        resource = resources.get(resource_id)
        depth = depth_by_source.get(source_name, {})
        if not resource:
            continue
        missing_fields = list(depth.get("missing_fields", []))
        placeholder_count = int(depth.get("placeholder_count", 0) or 0)
        source_quality = str(depth.get("status") or resource.get("source_quality") or "unknown")
        resource.update({
            "source_quality": source_quality,
            "missing_fields": missing_fields,
            "placeholder_count": placeholder_count,
            "runtime_usable_for_draft": resource.get("status") == "parseable" and source_quality in {"complete", "partial"},
            "formal_fact_usable": source_quality == "complete" and not missing_fields and placeholder_count == 0,
            "quality_reason": "可作为规则/候选来源进入草稿链，但存在缺失字段或占位内容" if source_quality == "partial" else "完整来源",
        })
    library_index_path = Path(resources.get("library_index", {}).get("path", root / "文档" / "资料库索引.jsonl"))
    library_index_integrity, library_index_errors = _library_index_integrity(library_index_path)
    errors.extend(library_index_errors)
    registry = {
        "schema_version": "source-registry-1.1",
        "project_root": str(root).replace("\\", "/"),
        "generated_at": now(),
        "resource_count": len(resources),
        "resources": resources,
        "source_quality": "partial" if partial else "complete",
        "partial_resources": partial,
        "blocking_errors": errors,
        "quality_blocking_errors": ([
            "来源深度为 partial，禁止正式交付；必须先完成来源确认或明确降级为 draft_only。"
        ] if partial else []),
        "status": "failed" if errors else "passed",
        "delivery_status": "draft_only" if errors or partial else "project_delivery_candidate",
        "usage_policy": {
            "blocked": "不可消费，先修复解析或身份问题",
            "candidate": "可检索、比较和头脑风暴，不得直接写成事实",
            "draft_usable": "可进入创作草稿，必须保留 source_ref 和不确定性",
            "verified": "可作为正式事实，仅限字段完整且来源已确认的对象",
        },
        "quality_analysis_report": "文档/证据/来源质量自主分析报告.json",
        "library_index_integrity": library_index_integrity,
    }
    confirmation = validate_confirmation(root)
    resources["project_source_confirmation"] = {
        "status": "parseable" if confirmation["status"] == "confirmed" else "pending",
        "source_quality": "complete" if confirmation["allow_formal_pipeline"] else "unconfirmed",
        "path": str(root / "配置" / "project_source_confirmation.json"),
        "relative_path": "配置/project_source_confirmation.json",
        "report_path": "文档/证据/项目来源确认报告.json",
    }
    quality_report = evidence / "来源质量自主分析报告.json"
    source_aliases = {
        "type_system": "类型系统.txt",
        "type_connections": "类型连接.txt",
        "library": "资料库.txt",
        "static_network": "静态网络.txt",
        "dynamic_network": "动态网络.txt",
        "anchor_network": "锚点网络.txt",
    }
    authoritative_ids: set[str] = set()
    if quality_report.is_file():
        try:
            quality = json.loads(quality_report.read_text(encoding="utf-8-sig"))
            by_source = {str(item.get("source")): item for item in quality.get("sources", []) if isinstance(item, dict)}
            for resource_id, resource in resources.items():
                source = source_aliases.get(resource_id, Path(str(resource.get("relative_path", ""))).name)
                item = by_source.get(source)
                if item:
                    # The quality analysis is the authoritative object-level
                    # result. Do not retain a stale whole-file deep-check state.
                    resource["source_quality"] = item.get("source_report_status", resource.get("source_quality"))
                    resource["missing_fields"] = item.get("missing_fields", resource.get("missing_fields", []))
                    resource["placeholder_count"] = item.get("placeholder_count", resource.get("placeholder_count", 0))
                    resource["legacy_placeholder_count"] = item.get("legacy_placeholder_count")
                    resource["governance_evidence"] = item.get("governance_evidence", {})
                    resource["formal_fact_usable"] = (
                        resource["source_quality"] == "complete"
                        and not resource["missing_fields"]
                        and resource["placeholder_count"] == 0
                    )
                    resource["quality_reason"] = (
                        "完整对象级来源，仍须完成项目来源确认才能作为正式项目事实"
                        if resource["formal_fact_usable"] else "存在对象级缺失字段或未确认内容"
                    )
                    resource["usage_level"] = item.get("usage_level")
                    resource["allowed_uses"] = item.get("allowed_uses", {})
                    resource["improvement_actions"] = item.get("improvement_actions", [])
                    authoritative_ids.add(resource_id)
            registry["quality_level_counts"] = quality.get("level_counts", {})
        except (OSError, UnicodeError, json.JSONDecodeError):
            registry["quality_analysis_error"] = "来源质量自主分析报告不可解析"
    authoritative_partial = sorted(
        resource_id for resource_id in authoritative_ids
        if resources.get(resource_id, {}).get("source_quality") != "complete"
    )
    registry["source_quality"] = "partial" if authoritative_partial else "complete"
    registry["partial_resources"] = authoritative_partial
    registry["quality_blocking_errors"] = ([
        "存在对象级质量未完成的来源，禁止正式交付；必须补齐可核验来源字段或明确保持 draft_only。"
    ] if authoritative_partial else [])
    registry["delivery_status"] = "draft_only" if errors or authoritative_partial else "project_delivery_candidate"
    if not confirmation["allow_formal_pipeline"]:
        registry["quality_blocking_errors"].append("项目来源确认未完成：派生输入不得作为正式项目事实；只能保持 draft_only。")
        registry["delivery_status"] = "draft_only"
    registry["resource_count"] = len(resources)
    registry["resources"] = resources
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "资源注册表.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    registry = build_registry(args.project_root)
    print(json.dumps(registry, ensure_ascii=False))
    return 0 if registry["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())