"""Project-scoped execution contracts that cannot be bypassed by a caller.

Automation agents must not infer source permission from context.  This module
revalidates the immutable selection and approved blueprint at every boundary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SELECTION = Path("文档/证据/小说资料选择清单.json")
BLUEPRINT = Path("文档/证据/project_planning.json")
RUNTIME_REPORT = Path("文档/证据/资料运行质量报告.json")
RUNTIME_POLICY_VERSION = "runtime-source-admission-1.0"
ALLOWED_SOURCE_STATUSES = {"verified", "cross_confirmed", "draft_usable", "parseable", "translated"}
DRAFT_SOURCE_STATUSES = ALLOWED_SOURCE_STATUSES | {"unverified", "candidate"}


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contract_paths(root: str | Path) -> tuple[Path, Path, Path]:
    project_root = Path(root).expanduser().resolve()
    return project_root / "配置" / "project_config.json", project_root / SELECTION, project_root / BLUEPRINT


def _normal_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def _chapter_errors(chapters: Any, config: dict[str, Any]) -> list[str]:
    if not isinstance(chapters, list) or not chapters:
        return ["project_planning 缺少章节树"]
    errors: list[str] = []
    chapter_ids = [str(item.get("chapter_id") or "") for item in chapters if isinstance(item, dict)]
    if len(chapter_ids) != len(chapters) or not all(chapter_ids) or len(set(chapter_ids)) != len(chapter_ids):
        errors.append("章节 chapter_id 必须非空且唯一")
    scene_ids = [str(scene.get("scene_id") or "") for chapter in chapters if isinstance(chapter, dict) for scene in chapter.get("scenes", []) if isinstance(scene, dict)]
    if not scene_ids or not all(scene_ids) or len(set(scene_ids)) != len(scene_ids):
        errors.append("场景 scene_id 必须非空且全局唯一")
    try:
        budget = sum(int(chapter.get("target_words")) for chapter in chapters if isinstance(chapter, dict))
    except (TypeError, ValueError):
        errors.append("章节 target_words 必须是正整数")
    else:
        if any(not isinstance(chapter, dict) or not isinstance(chapter.get("target_words"), int) or chapter["target_words"] <= 0 for chapter in chapters):
            errors.append("章节 target_words 必须是正整数")
        elif budget != config.get("target_words"):
            errors.append("章节 target_words 总和与项目 target_words 不一致")
    return errors


def _snapshot_errors(root: Path, snapshot: Any) -> list[str]:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("files"), list) or not snapshot["files"]:
        return ["project_planning 缺少可复核的资料文件快照"]
    errors = []
    for item in snapshot["files"]:
        if not isinstance(item, dict):
            errors.append("资料文件快照格式错误")
            continue
        relative_path, expected = _normal_path(item.get("path")), str(item.get("sha256") or "")
        path = (root / relative_path).resolve()
        if not relative_path or path == root or root not in path.parents:
            errors.append(f"资料文件快照路径非法：{relative_path or 'missing-path'}")
        elif not path.is_file():
            errors.append(f"资料文件快照目标缺失：{relative_path}")
        elif len(expected) != 64 or sha256_file(path) != expected:
            errors.append(f"资料文件快照已漂移：{relative_path}")
    return errors


def _runtime_approval_errors(root: Path, blueprint: dict[str, Any]) -> list[str]:
    approval = blueprint.get("approval") if isinstance(blueprint.get("approval"), dict) else {}
    if approval.get("status") == "approved":
        return []
    if approval.get("status") == "pending":
        return ["project_planning 未获人工批准"]
    if approval.get("status") != "system_runtime_approved":
        return ["project_planning 未获人工批准或系统运行批准"]
    report_path = root / RUNTIME_REPORT
    report = read_json(report_path, {})
    admission = blueprint.get("runtime_admission") if isinstance(blueprint.get("runtime_admission"), dict) else {}
    if approval.get("actor") != "system" or approval.get("policy_version") != RUNTIME_POLICY_VERSION:
        return ["系统运行批准签发主体或规则版本无效"]
    if not isinstance(report, dict) or report.get("status") != "system_runtime_approved" or report.get("approval_actor") != "system" or report.get("policy_version") != RUNTIME_POLICY_VERSION:
        return ["系统运行批准报告无效"]
    if not report_path.is_file() or approval.get("runtime_report_sha256") != sha256_file(report_path) or admission.get("report_sha256") != sha256_file(report_path):
        return ["系统运行批准报告哈希不匹配"]
    hashes = report.get("input_hashes") if isinstance(report.get("input_hashes"), dict) else {}
    expected = {"config_sha256": root / "配置" / "project_config.json", "selection_sha256": root / SELECTION, "registry_sha256": root / "文档" / "证据" / "资源注册表.json", "bindings_sha256": root / "文档" / "证据" / "全量资料解释词创作绑定.json", "activation_matrix_sha256": root / "文档" / "证据" / "全书资料激活矩阵.json"}
    if any(not path.is_file() or hashes.get(key) != sha256_file(path) for key, path in expected.items()) or admission.get("input_hashes") != hashes:
        return ["系统运行批准输入已漂移"]
    if report.get("formal_fact_approval") is True or admission.get("formal_fact_approval") is True:
        return ["系统运行批准不得伪称正式事实批准"]
    return []


def validate_execution_contract(root: str | Path, require_blueprint: bool = True, phase: str = "delivery") -> dict[str, Any]:
    """Validate creation inputs or the stricter post-generation delivery contract.

    ``phase=creation`` deliberately accepts an unapproved or stale blueprint:
    it is sufficient that the configured project and selected source scope can
    be read. Approval, snapshots and per-source permission are delivery
    evidence, never prerequisites for producing an isolated draft.
    """
    config_path, selection_path, blueprint_path = contract_paths(root)
    config = read_json(config_path, {})
    selection = read_json(selection_path, {})
    blueprint = read_json(blueprint_path, {})
    errors: list[str] = []
    if not isinstance(config, dict):
        errors.append("项目配置不可解析")
    if not isinstance(selection, dict):
        errors.append("缺少或不可解析的项目资料选择清单")
    project_id = config.get("project_id") if isinstance(config, dict) else None
    if not project_id:
        errors.append("项目配置缺少 project_id")
    if isinstance(selection, dict) and selection.get("project_id") != project_id:
        errors.append("资料选择清单 project_id 与项目配置不一致")
    if isinstance(selection, dict):
        selected = set((selection.get("selected_type_profiles") or {}).keys())
        configured = set(config.get("genre_selection") or []) if isinstance(config, dict) else set()
        if not selected or selected != configured:
            errors.append("资料选择清单的已选类型与项目配置不一致")
    if phase not in {"creation", "delivery"}:
        errors.append("phase 必须为 creation 或 delivery")
    if phase == "delivery" and isinstance(config, dict) and config.get("project_mode") == "input_only":
        errors.append("项目仍处于 input_only；正式交付前必须建立并批准 project_planning 蓝图")
    if require_blueprint and phase == "delivery":
        if not isinstance(blueprint, dict):
            errors.append("缺少或不可解析的 project_planning 蓝图")
        else:
            if blueprint.get("schema_version") != "project-planning-1.1":
                errors.append("project_planning schema_version 不匹配")
            if blueprint.get("project_id") != project_id:
                errors.append("project_planning project_id 与项目配置不一致")
            errors.extend(_runtime_approval_errors(Path(root).expanduser().resolve(), blueprint))
            snapshot = blueprint.get("source_snapshot", {})
            if snapshot.get("selection_sha256") != (sha256_file(selection_path) if selection_path.is_file() else None):
                errors.append("project_planning 的资料选择快照已过期")
            chapters = blueprint.get("chapter_plan")
            if not isinstance(chapters, list) or len(chapters) != config.get("target_chapter_count"):
                errors.append("project_planning 章节数与 target_chapter_count 不一致")
            errors.extend(_chapter_errors(chapters, config))
            if chapters != config.get("chapter_plan"):
                errors.append("project_planning 章节树与项目配置不一致")
            allowed_sources = blueprint.get("allowed_sources")
            if not isinstance(allowed_sources, list) or not allowed_sources:
                errors.append("project_planning 缺少结构化 allowed_sources")
            else:
                seen_ids = set()
                for item in allowed_sources:
                    if not isinstance(item, dict):
                        errors.append("allowed_sources 必须是对象数组")
                        continue
                    source_id, source_path = str(item.get("source_id") or ""), _normal_path(item.get("source_path"))
                    if not source_id or source_id in seen_ids:
                        errors.append("allowed_sources.source_id 必须非空且唯一")
                    seen_ids.add(source_id)
                    if not source_path or not isinstance(item.get("source_status"), str) or item.get("source_status") not in ALLOWED_SOURCE_STATUSES or item.get("draft_prose") is not True:
                        errors.append(f"allowed_sources 条目不具备正文许可：{source_id or 'missing-id'}")
            errors.extend(_snapshot_errors(Path(root).expanduser().resolve(), blueprint.get("source_snapshot")))
    return {"status": "passed" if not errors else "failed", "errors": errors, "config": config, "selection": selection, "blueprint": blueprint}


def source_permission_errors(root: str | Path, source_records: list[dict[str, Any]], phase: str = "delivery") -> list[str]:
    """Validate source evidence without allowing draft records to impersonate delivery permission."""
    if phase not in {"creation", "delivery"}:
        return ["来源权限 phase 必须为 creation 或 delivery"]
    contract = validate_execution_contract(root, require_blueprint=phase == "delivery", phase=phase)
    if contract["status"] != "passed":
        return ["项目执行契约无效：" + "；".join(contract["errors"])]
    blueprint = contract["blueprint"]
    allowed = {str(item.get("source_id")): item for item in blueprint.get("allowed_sources", []) if isinstance(item, dict)}
    errors: list[str] = []
    for record in source_records:
        source_id = str(record.get("source_id") or record.get("library_entry_id") or record.get("anchor_id") or "")
        source_ref = record.get("source_ref") if isinstance(record.get("source_ref"), dict) else {}
        source_path = str(source_ref.get("path") or source_ref.get("file") or "").replace("\\", "/")
        status = str(record.get("source_status") or record.get("status") or "")
        if not isinstance(record.get("source_ref"), dict) or not source_path or not source_ref.get("location") or source_ref.get("project_id") != contract["config"].get("project_id"):
            errors.append(f"正文来源证据不完整：{source_id or 'missing-id'}")
        if phase == "creation":
            if not source_id or status not in DRAFT_SOURCE_STATUSES:
                errors.append(f"草稿来源状态无效：{source_id or 'missing-id'}（{status or 'missing-status'}）")
            continue
        if not source_id or source_id not in allowed:
            errors.append(f"正文来源未获蓝图许可：{source_id or 'missing-id'}")
            continue
        expected = allowed[source_id]
        if source_path != _normal_path(expected.get("source_path")):
            errors.append(f"正文来源路径与蓝图许可不一致：{source_id}")
        if status != expected.get("source_status") or status not in ALLOWED_SOURCE_STATUSES or record.get("draft_prose") is not True:
            errors.append(f"正文来源权限不足：{source_id}（{status or 'missing-status'}）")
    return errors