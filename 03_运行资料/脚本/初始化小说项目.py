"""Create an empty novel project from the only three required user inputs.

The initializer deliberately does not invent a title, characters, setting, or
plot.  It records the selected type materials so the later planning stage can
retrieve only relevant source contracts before it creates those facts.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from 项目生命周期管理 import register_project, validate_new_project_root
from 灵感库选型器 import build_selection


RESOURCE_ROOT = Path(__file__).resolve().parents[1]

# These markers identify a previously materialized novel, not reusable
# project-independent material. They must never be copied into a new project.
LEGACY_PROJECT_FIELDS = {
    "book_title",
    "world_name",
    "story_bible",
    "mainline_conflict",
    "core_mystery",
    "protagonist",
    "chapter_plan",
}
SHARED_SOURCE_CANDIDATES = [
    "原始资料/资料库.txt",
    "原始资料/静态网络.txt",
    "原始资料/动态网络.txt",
    "原始资料/锚点网络.txt",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", value).strip("-")
    return cleaned[:36] or "novel"


def _selected_connection(profiles: dict[str, Any], selected_types: list[str]) -> dict[str, Any] | None:
    wanted = set(selected_types)
    for row in profiles.get("type_combinations", profiles.get("combinations", [])):
        if isinstance(row, dict) and set(map(str, row.get("types", []))) == wanted:
            return row
    return None


def _assert_empty_project_root(root: Path) -> None:
    """Prevent an existing project or its generated artifacts being reused."""
    if not root.exists():
        return
    if not root.is_dir():
        raise FileExistsError(f"项目输出路径必须是目录：{root}")
    children = list(root.iterdir())
    if children:
        legacy_config = root / "配置" / "project_config.json"
        if legacy_config.is_file():
            try:
                value = read_json(legacy_config)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"目标目录包含不可解析的旧项目配置：{legacy_config}") from exc
            if isinstance(value, dict) and any(value.get(field) for field in LEGACY_PROJECT_FIELDS):
                raise FileExistsError(f"禁止在已有小说项目上重新初始化：{root}")
        raise FileExistsError(f"项目目录必须为空：{root}")


def initialize_project(
    output_root: str | Path,
    primary_type: str,
    themes: list[str],
    target_words: int,
    chapter_count: int,
) -> Path:
    if target_words <= 0:
        raise ValueError("target_words 必须大于 0")
    if chapter_count <= 0:
        raise ValueError("chapter_count 必须大于 0")
    primary_type = primary_type.strip()
    themes = [theme.strip() for theme in themes if theme.strip()]
    if not primary_type:
        raise ValueError("primary_type 不能为空")

    profile_path = RESOURCE_ROOT / "配置" / "类型配置模板.json"
    profiles = read_json(profile_path)
    available_types = profiles.get("types", {}) if isinstance(profiles, dict) else {}
    selected_types = list(dict.fromkeys([primary_type, *themes]))
    unknown = [item for item in selected_types if item not in available_types]
    if unknown:
        raise ValueError("未找到对应类型资料：" + "、".join(unknown))

    root = Path(output_root).expanduser().resolve()
    _assert_empty_project_root(root)
    formal_workspace = RESOURCE_ROOT / "作品"
    if root.parent == formal_workspace.resolve():
        validate_new_project_root(RESOURCE_ROOT, root)
    elif root.is_relative_to(RESOURCE_ROOT):
        raise ValueError("正式根下的新项目必须是作品/<书名>直接子目录")
    (root / "配置").mkdir(parents=True, exist_ok=True)
    (root / "文档" / "证据").mkdir(parents=True, exist_ok=True)
    (root / "正文").mkdir(parents=True, exist_ok=True)

    selected_profiles = {
        type_name: {
            "type_name": profile.get("type_name", type_name),
            "core_elements": profile.get("core_elements", []),
            "style_constraints": profile.get("style_constraints", []),
            "source_ref": profile.get("source_ref", {}),
            "source_status": profile.get("source_status", "unknown"),
        }
        for type_name in selected_types
        for profile in [available_types[type_name]]
        if isinstance(profile, dict)
    }
    combination = _selected_connection(profiles, selected_types)
    project_id = f"novel-{_slug(primary_type)}-{uuid.uuid4().hex[:8]}"
    config = {
        "schema_version": "project-config-1.0",
        "project_id": project_id,
        "project_name": project_id,
        "project_mode": "input_only",
        "creation_mode": "project_bound",
        "run_mode": "full_authored_run",
        "creation_scope": "complete_formal_creation",
        "created_at": now(),
        "genre_selection": selected_types,
        "primary_type": primary_type,
        "theme_combination": themes,
        "target_words": target_words,
        "target_chapter_count": chapter_count,
        "creative_contract": {
            "user_required_inputs": ["primary_type", "theme_combination", "target_words", "target_chapter_count"],
            "project_facts_status": "uncreated",
            "generation_policy": "后续规划阶段只能依据已选类型、题材组合和已注册资料生成项目事实；生成前不得写入书名、人物、世界观或章节情节。",
        },
        "inspiration_selection": {
            "receipt_path": "文档/证据/小说灵感选型回执.json",
            "status": "selected_for_draft_only",
        },
        "book_title": "",
        "world_stage": "",
        "mainline_conflict": "",
        "core_mystery": "",
        "protagonist": {},
        "chapter_plan": [],
        "status": "input_ready",
    }
    selection = {
        "schema_version": "novel-source-selection-1.0",
        "generated_at": now(),
        "project_id": project_id,
        "selection_inputs": {
            "primary_type": primary_type,
            "theme_combination": themes,
            "target_words": target_words,
            "target_chapter_count": chapter_count,
        },
        "selected_type_profiles": selected_profiles,
        "selected_type_combination": combination,
        "shared_sources": SHARED_SOURCE_CANDIDATES,
        "selection_policy": "规划和创作仅从本清单声明的类型资料、组合资料和共享叙事资料检索；未选类型不得作为项目事实或正文约束。",
        "next_stage": "project_planning",
    }
    inspiration_selection = build_selection(
        profile_path,
        project_id,
        primary_type,
        themes,
        target_words=target_words,
        target_chapter_count=chapter_count,
    )
    config["inspiration_selection"]["selection_id"] = inspiration_selection["selection_id"]
    selection["inspiration_selection_id"] = inspiration_selection["selection_id"]
    selection["selection_status"] = inspiration_selection["selection_status"]
    selection["candidate_count"] = inspiration_selection["candidate_count"]
    selection["selected_count"] = inspiration_selection["selected_count"]
    (root / "配置" / "project_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "文档" / "证据" / "小说资料选择清单.json").write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "文档" / "证据" / "小说灵感选型回执.json").write_text(json.dumps(inspiration_selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if root.parent == formal_workspace.resolve():
        register_project(RESOURCE_ROOT, root, project_id)
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description="以类型、题材组合和目标规模初始化空白小说项目")
    parser.add_argument("--output-root", required=True, help="新项目目录，必须不存在或为空")
    parser.add_argument("--type", dest="primary_type", required=True, help="作品主类型，例如 玄幻")
    parser.add_argument("--themes", nargs="*", default=[], help="题材组合中的其他类型，例如 悬疑")
    parser.add_argument("--target-words", required=True, type=int)
    parser.add_argument("--chapters", required=True, type=int)
    args = parser.parse_args()
    root = initialize_project(args.output_root, args.primary_type, args.themes, args.target_words, args.chapters)
    print(json.dumps({"status": "input_ready", "project_root": str(root)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())