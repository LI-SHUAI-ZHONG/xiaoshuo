"""Select project-independent type inspiration without creating project facts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "inspiration-selection-receipt-1.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _selection_id(project_id: str, selected_types: list[str], profile_path: str) -> str:
    payload = json.dumps(
        {"project_id": project_id, "selected_types": selected_types, "profile_path": profile_path},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "inspiration-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_selection(
    profile_path: str | Path,
    project_id: str,
    primary_type: str,
    themes: list[str],
    *,
    target_words: int,
    target_chapter_count: int,
) -> dict[str, Any]:
    """Build an auditable selection; it never invents a title, person, or plot."""
    path = Path(profile_path).expanduser().resolve()
    profiles = _read_json(path)
    available = profiles.get("types", {}) if isinstance(profiles, dict) else {}
    selected_types = list(dict.fromkeys([primary_type.strip(), *(item.strip() for item in themes if item.strip())]))
    if not project_id.strip() or not selected_types or not selected_types[0]:
        raise ValueError("项目身份和主类型不能为空")
    unknown = [item for item in selected_types if item not in available]
    if unknown:
        raise ValueError("未找到对应类型候选：" + ", ".join(unknown))
    candidates = []
    for type_name, profile in available.items():
        if not isinstance(profile, dict):
            continue
        candidates.append({
            "type_name": type_name,
            "source_status": profile.get("source_status", "unknown"),
            "source_ref": profile.get("source_ref", {}),
            "selection_state": "selected" if type_name in selected_types else "candidate",
        })
    relative_profile = str(path).replace("\\", "/")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now(),
        "project_id": project_id,
        "selection_id": _selection_id(project_id, selected_types, relative_profile),
        "source": {"path": relative_profile, "source_layer": "generic_type", "project_independent": True},
        "candidate_count": len(candidates),
        "selected_count": len(selected_types),
        "selected_types": selected_types,
        "candidates": candidates,
        "selection_inputs": {
            "primary_type": primary_type,
            "theme_combination": [item for item in themes if item],
            "target_words": target_words,
            "target_chapter_count": target_chapter_count,
        },
        "selection_status": "selected_for_draft_only",
        "author_confirmation": {"required": True, "status": "provided_by_initializer_inputs"},
        "formal_release_allowed": False,
        "project_facts_status": "uncreated",
        "next_stage": "project_planning",
    }


def validate_selection(
    receipt: dict[str, Any],
    *,
    project_id: str,
    selected_types: list[str],
    profile_path: str | Path | None = None,
) -> list[str]:
    """Validate that the current project still uses its own immutable selection."""
    errors: list[str] = []
    if not isinstance(receipt, dict) or receipt.get("schema_version") != SCHEMA_VERSION:
        return ["缺少有效的灵感选型回执"]
    if receipt.get("project_id") != project_id:
        errors.append("灵感选型回执 project_id 与项目配置不一致")
    expected = list(dict.fromkeys(str(item).strip() for item in selected_types if str(item).strip()))
    if receipt.get("selected_types") != expected:
        errors.append("灵感选型回执 selected_types 与项目配置不一致")
    if receipt.get("selection_status") != "selected_for_draft_only":
        errors.append("灵感选型回执状态不允许进入草稿规划")
    if receipt.get("formal_release_allowed") is not False:
        errors.append("灵感选型回执不得授予正式发布资格")
    source = receipt.get("source") if isinstance(receipt.get("source"), dict) else {}
    if source.get("source_layer") != "generic_type" or source.get("project_independent") is not True:
        errors.append("灵感选型来源必须是项目无关的通用类型层")
    if profile_path is not None and Path(source.get("path", "")).resolve() != Path(profile_path).expanduser().resolve():
        errors.append("灵感选型来源文件与当前类型配置模板不一致")
    return errors