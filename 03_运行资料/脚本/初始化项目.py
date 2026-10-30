"""Initialize a project with global evidence assets and empty consumption logs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT
GLOBAL_EVIDENCE = PROJECT_ROOT / "文档" / "证据"
RULE_FILES = (
    "类型连接规则.json",
    "类型连接采用结构.json",
    "类型连接全局索引.json",
    "动态链消费规则.json",
    "静态连接采用规则.json",
    "锚点采用规则.json",
    "执行采用规则.json",
)
INDEX_FILES = (
    "类型连接全局索引.json",
    "静态网络索引.json",
    "静态网络绑定摘要.json",
    "动态网络状态摘要.json",
    "锚点分类索引.json",
)
CONSUMPTION_FILES = (
    "类型连接采用.jsonl",
    "动态链消费.jsonl",
    "静态连接消费.jsonl",
    "锚点消费.jsonl",
    "执行消费.jsonl",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a new writing project.")
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--path", default=str(DEFAULT_ROOT), help="Parent project path")
    return parser.parse_args()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    args = parse_args()
    project_name = args.name.strip()
    if not project_name or project_name in {".", ".."} or Path(project_name).name != project_name:
        raise ValueError("--name must be a non-empty single directory name")

    project_path = Path(args.path).expanduser().resolve() / project_name
    if project_path.exists():
        raise FileExistsError(f"Project path already exists: {project_path}")

    config_dir = project_path / "配置"
    design_dir = project_path / "创作任务"
    text_dir = project_path / "正文"
    evidence_dir = project_path / "文档" / "证据"
    for directory in (config_dir, design_dir, text_dir, evidence_dir):
        directory.mkdir(parents=True, exist_ok=True)

    missing = [name for name in (*RULE_FILES, *INDEX_FILES) if not (GLOBAL_EVIDENCE / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing global assets: " + ", ".join(missing))
    for name in RULE_FILES:
        shutil.copy2(GLOBAL_EVIDENCE / name, evidence_dir / name)
    for name in INDEX_FILES:
        shutil.copy2(GLOBAL_EVIDENCE / name, evidence_dir / name)

    timestamp = iso_now()
    header = {"record_type": "header", "schema_version": "1.0", "total_records": 0, "last_updated": timestamp}
    for name in CONSUMPTION_FILES:
        (evidence_dir / name).write_text(
            json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    config = {
        "schema_version": "project-config-1.0",
        "project_id": project_name,
        "project_name": project_name,
        "book_title": "",
        "created_at": timestamp,
        "genre_selection": [],
        "type_combination": None,
        "world_stage": "",
        "mainline_conflict": "",
        "core_mystery": "",
        "protagonist": {
            "name": "",
            "dynamic_node_id": "1.1",
            "dynamic_node_name": "主角",
            "dynamic_aliases": [],
            "personality": [],
            "desire": "",
            "obsession": "",
            "decision_tendency": [],
            "blind_spots": [],
            "emotional_reactions": [],
        },
        "chapter_plan": [],
        "status": "initialized",
    }
    (config_dir / "project_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    created_files = 1 + len(RULE_FILES) + len(INDEX_FILES) + len(CONSUMPTION_FILES)
    print(f"项目路径：{project_path}")
    print(f"创建的文件数量：{created_files}")
    print(f"复制规则文件数量：{len(RULE_FILES)}")
    print(f"复制索引文件数量：{len(INDEX_FILES)}")
    print(f"生成的空消费记录数量：{len(CONSUMPTION_FILES)}")


if __name__ == "__main__":
    main()
