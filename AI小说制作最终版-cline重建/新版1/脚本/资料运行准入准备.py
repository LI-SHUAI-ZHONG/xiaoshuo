"""Create reproducible system runtime admission without fabricating human approval.

This prepares source material for prose generation. It does not upgrade partial
source material into verified external facts and does not inspect prose outputs.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION = "runtime-source-admission-1.0"
KIND_RESOURCE_KEYS = {
    "资料库": "library", "静态网络": "static_network", "动态网络": "dynamic_network",
    "锚点网络": "anchor_network", "类型系统": "type_system", "类型系统来源块": "type_system",
    "类型连接": "type_connections",
}


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _source_ref(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def prepare(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence, config_dir = root / "文档" / "证据", root / "配置"
    config_path, selection_path = config_dir / "project_config.json", evidence / "小说资料选择清单.json"
    registry_path, bindings_path = evidence / "资源注册表.json", evidence / "全量资料解释词创作绑定.json"
    matrix_path = evidence / "全书资料激活矩阵.json"
    config, selection = _read(config_path, {}), _read(selection_path, {})
    registry, bindings, matrix = _read(registry_path, {}), _read(bindings_path, {}), _read(matrix_path, {})
    if not all(isinstance(value, dict) for value in (config, selection, registry, bindings, matrix)):
        raise ValueError("运行准入输入必须全部是 JSON 对象")
    if not config.get("project_id") or selection.get("project_id") != config.get("project_id") or matrix.get("project_id") != config.get("project_id"):
        raise ValueError("项目配置、资料选择清单和激活矩阵的 project_id 必须一致")
    chapters = [chapter for chapter in config.get("chapter_plan", []) if isinstance(chapter, dict)]
    scene_count = sum(len([scene for scene in chapter.get("scenes", []) if isinstance(scene, dict)]) for chapter in chapters)
    if not chapters or not scene_count:
        raise ValueError("运行准入要求项目配置具有非空章节和场景计划")
    calibration = {"applied": False, "policy": "每场景 1500 字的运行预算；仅用于生成容量控制，不代表人工定稿篇幅"}
    if config.get("target_chapter_count") != len(chapters):
        config["target_chapter_count"] = len(chapters)
        calibration = calibration | {"applied": True, "target_chapter_count": len(chapters)}
    if not isinstance(config.get("target_words"), int) or config["target_words"] <= 0 or any(not isinstance(chapter.get("target_words"), int) or chapter["target_words"] <= 0 for chapter in chapters):
        for chapter in chapters:
            chapter["target_words"] = 1500 * len([scene for scene in chapter.get("scenes", []) if isinstance(scene, dict)])
        config["target_words"] = sum(chapter["target_words"] for chapter in chapters)
        config["project_mode"] = "system_runtime_planned"
        calibration = calibration | {"applied": True, "target_words": config["target_words"]}
    if calibration["applied"]:
        config["project_mode"] = "system_runtime_planned"
        config["runtime_calibration"] = calibration
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    binding_records = [row for row in bindings.get("records", []) if isinstance(row, dict)]
    assignments = [row for row in matrix.get("assignments", []) if isinstance(row, dict)]
    translated = {str(row.get("binding_id")) for row in binding_records if row.get("binding_id") and row.get("translation_status") in {"translated", "narrativized"}}
    assigned = {str(row.get("binding_id")) for row in assignments if row.get("binding_id")}
    missing = sorted(translated - assigned)
    duplicate_ids = len({str(row.get("source_id")) for row in binding_records if row.get("source_id")}) != len(binding_records)
    if missing or duplicate_ids:
        raise ValueError("全量绑定必须具有唯一 source_id 且每个已转译 binding_id 必须进入激活矩阵")

    allowed_sources = []
    for row in binding_records:
        source_id = str(row.get("source_id") or "")
        ref = _source_ref(row.get("source_ref"))
        source_path = str(ref.get("file") or ref.get("path") or "").replace("\\", "/")
        location = str(ref.get("locator") or ref.get("location") or ref.get("line_start") or "")
        resource_key = KIND_RESOURCE_KEYS.get(str(row.get("source_kind") or ""))
        resource = (registry.get("resources") or {}).get(resource_key, {}) if resource_key else {}
        if not source_path and isinstance(resource, dict):
            source_path = str(resource.get("relative_path") or "").replace("\\", "/")
        if not location:
            location = source_id
        if not source_id or not source_path or not location or not (root / source_path).is_file():
            raise ValueError(f"绑定来源不可复核：{source_id or 'missing-id'}")
        allowed_sources.append({
            "source_id": source_id, "source_kind": row.get("source_kind") or "unknown",
            "source_path": source_path, "source_status": "draft_usable", "draft_prose": True,
            "selection_rationale": "system runtime admission: translated binding assigned by activation matrix",
            "runtime_only": True, "formal_fact_usable": False,
        })

    snapshot_paths = {"配置/project_config.json", "文档/证据/小说资料选择清单.json", "文档/证据/资源注册表.json", "文档/证据/全量资料解释词创作绑定.json", "文档/证据/全书资料激活矩阵.json"}
    for item in (registry.get("resources") or {}).values():
        if isinstance(item, dict) and item.get("relative_path"):
            snapshot_paths.add(str(item["relative_path"]).replace("\\", "/"))
    generated_outputs = {"配置/project_source_confirmation.json", "文档/证据/资料运行质量报告.json", "文档/证据/project_planning.json"}
    snapshot_files = [{"path": path, "sha256": _sha256(root / path)} for path in sorted(snapshot_paths - generated_outputs) if (root / path).is_file()]
    input_hashes = {"config_sha256": _sha256(config_path), "selection_sha256": _sha256(selection_path), "registry_sha256": _sha256(registry_path), "bindings_sha256": _sha256(bindings_path), "activation_matrix_sha256": _sha256(matrix_path)}
    report = {
        "schema_version": "runtime-source-admission-1.0", "project_id": config["project_id"],
        "status": "system_runtime_approved", "approval_actor": "system", "policy_version": POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "input_hashes": input_hashes,
        "translated_binding_count": len(translated), "assigned_binding_count": len(assigned),
        "allowed_source_count": len(allowed_sources), "missing_assignment_ids": missing,
        "runtime_scope": "prose_generation", "formal_fact_approval": False,
        "source_quality": registry.get("source_quality", "unknown"),
        "quality_notice": "partial/candidate sources remain runtime-only creative inputs and are not upgraded to verified facts.",
        "configuration_calibration": calibration,
    }
    report["report_sha256"] = _json_sha256(report)
    report_path = evidence / "资料运行质量报告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    confirmation = {"schema_version": "project-source-confirmation-1.1", "project_id": config["project_id"], "status": "system_runtime_confirmed", "source_quality_ack": True, "approval_actor": "system", "policy_version": POLICY_VERSION, "runtime_report": str(report_path.relative_to(root)).replace("\\", "/"), "runtime_report_sha256": _sha256(report_path), "formal_fact_approval": False}
    confirmation_path = config_dir / "project_source_confirmation.json"
    confirmation_path.write_text(json.dumps(confirmation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    blueprint = {"schema_version": "project-planning-1.1", "project_id": config["project_id"], "approval": {"status": "system_runtime_approved", "actor": "system", "policy_version": POLICY_VERSION, "runtime_report_sha256": _sha256(report_path)}, "source_snapshot": {"selection_sha256": input_hashes["selection_sha256"], "files": snapshot_files}, "chapter_plan": config.get("chapter_plan", []), "allowed_sources": allowed_sources, "runtime_admission": {"report_path": str(report_path.relative_to(root)).replace("\\", "/"), "report_sha256": _sha256(report_path), "input_hashes": input_hashes, "matrix_run_id": matrix.get("run_id"), "formal_fact_approval": False}}
    blueprint_path = evidence / "project_planning.json"
    blueprint_path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"report": report, "paths": [report_path, confirmation_path, blueprint_path]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare auditable system runtime admission for prose generation.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    result = prepare(parser.parse_args().project_root)
    print(json.dumps({"status": result["report"]["status"], "allowed_source_count": result["report"]["allowed_source_count"], "paths": [str(path) for path in result["paths"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()