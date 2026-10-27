"""Create and approve versioned project-planning blueprints.

The tool never invents a novel from an input-only project.  A human or a
separate generation step supplies a concrete draft; this tool snapshots its
selected sources and makes approval explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 项目执行边界 import BLUEPRINT, contract_paths, read_json, sha256_file


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _snapshot(root: Path, selection_path: Path) -> dict[str, Any]:
    paths = [
        selection_path,
        root / "原始资料" / "资料库.txt",
        root / "原始资料" / "类型系统.txt",
        root / "原始资料" / "类型连接.txt",
        root / "原始资料" / "锚点网络.txt",
        root / "网络完整数据" / "动态连接完整数据.json",
        root / "网络完整数据" / "静态连接完整数据.json",
    ]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError("不能批准缺失的执行资料：" + "；".join(missing))
    return {"files": [{"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path)} for path in paths]}


def _allowed_sources(draft: dict[str, Any], selection: dict[str, Any]) -> list[dict[str, Any]]:
    sources = draft.get("allowed_sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("规划草案必须提供非空结构化 allowed_sources")
    selected_paths = {str(path).replace("\\", "/") for path in selection.get("shared_sources", [])}
    normalized = []
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("allowed_sources 必须是对象数组")
        source_id = str(item.get("source_id") or "").strip()
        source_path = str(item.get("source_path") or "").replace("\\", "/").lstrip("./")
        if not source_id or not source_path or not item.get("source_kind") or item.get("source_status") not in {"verified", "cross_confirmed", "draft_usable", "parseable", "translated"} or item.get("draft_prose") is not True or not str(item.get("selection_rationale") or "").strip():
            raise ValueError(f"allowed_sources 条目不完整或未获正文许可：{source_id or 'missing-id'}")
        if source_path not in selected_paths:
            raise ValueError(f"allowed_sources 来源不在项目选择清单：{source_path}")
        normalized.append({"source_kind": str(item["source_kind"]), "source_id": source_id, "source_path": source_path, "source_status": item["source_status"], "draft_prose": True, "selection_rationale": str(item["selection_rationale"])})
    if len({item["source_id"] for item in normalized}) != len(normalized):
        raise ValueError("allowed_sources.source_id 不得重复")
    return sorted(normalized, key=lambda item: item["source_id"])


def create(project_root: str | Path, draft_path: str | Path, approved_by: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    config_path, selection_path, target = contract_paths(root)
    config = read_json(config_path, {})
    selection = read_json(selection_path, {})
    draft = read_json(Path(draft_path), {})
    if not isinstance(config, dict) or not isinstance(selection, dict) or not isinstance(draft, dict):
        raise ValueError("项目配置、选择清单和规划草案必须是 JSON 对象")
    existing = read_json(target, {}) if target.is_file() else {}
    if isinstance(existing, dict) and existing.get("approval", {}).get("status") == "approved":
        raise ValueError("已有已批准规划，禁止隐式覆盖；请使用显式修订流程")
    chapters = draft.get("chapter_plan")
    if not isinstance(chapters, list) or len(chapters) != config.get("target_chapter_count"):
        raise ValueError("规划草案的 chapter_plan 必须与 target_chapter_count 完全一致")
    allowed = _allowed_sources(draft, selection)
    total = sum(int(chapter.get("target_words", 0)) for chapter in chapters if isinstance(chapter, dict))
    if total != config.get("target_words"):
        raise ValueError("章节 target_words 总和必须等于 target_words")
    blueprint = {
        "schema_version": "project-planning-1.1", "project_id": config.get("project_id"), "version": 1,
        "planning_transaction_id": "planning-" + uuid.uuid4().hex,
        "planning_commit_status": "committed",
        "generated_at": now(), "chapter_plan": chapters, "allowed_source_ids": [item["source_id"] for item in allowed], "allowed_sources": allowed,
        "story_bible": draft.get("story_bible", {}),
        "source_snapshot": {"selection_path": str(selection_path.relative_to(root)).replace("\\", "/"), "selection_sha256": sha256_file(selection_path), **_snapshot(root, selection_path)},
        "approval": {"status": "approved", "approved_by": approved_by, "approved_at": now()},
    }
    required_config_fields = ("book_title", "world_stage", "mainline_conflict", "core_mystery", "protagonist")
    missing = [field for field in required_config_fields if not draft.get(field)]
    if missing:
        raise ValueError("规划草案缺少项目事实：" + "、".join(missing))
    for field in required_config_fields:
        config[field] = draft[field]
    config["chapter_plan"] = chapters
    config["project_mode"] = "planned"
    config["status"] = "planning_approved"
    config["planning_ref"] = str(target.relative_to(root)).replace("\\", "/")
    config["planning_version"] = blueprint["version"]
    config["planning_transaction_id"] = blueprint["planning_transaction_id"]
    config["planning_commit_status"] = blueprint["planning_commit_status"]
    # Both documents carry the same planning version. Atomic replacement avoids
    # partially written JSON; contract validation detects interruption between files.
    _atomic_write(target, blueprint)
    _atomic_write(config_path, config)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--approved-by", required=True)
    args = parser.parse_args()
    target = create(args.project_root, args.draft, args.approved_by)
    print(json.dumps({"status": "approved", "output": str(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())