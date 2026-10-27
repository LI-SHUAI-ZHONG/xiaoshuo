"""Initialize a project with global evidence assets and empty consumption logs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil


DEFAULT_ROOT = Path(r"D:/AI小说制作最终版-cline重建")
GLOBAL_EVIDENCE = DEFAULT_ROOT / "docs" / "evidence"
RULE_FILES = (
    "type_connection_rules.json",
    "type_connection_adoption_schema.json",
    "type_connection_global_index.json",
    "dynamic_chain_consumption_rules.json",
    "static_connection_adoption_rules.json",
    "anchor_adoption_rules.json",
    "execution_adoption_rules.json",
)
CONSUMPTION_FILES = (
    "type_connection_adoption.jsonl",
    "dynamic_chain_consumption.jsonl",
    "static_connection_consumption.jsonl",
    "anchor_consumption.jsonl",
    "execution_consumption.jsonl",
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

    config_dir = project_path / "config"
    design_dir = project_path / "design_tasks"
    text_dir = project_path / "05_正文"
    evidence_dir = project_path / "docs" / "evidence"
    for directory in (config_dir, design_dir, text_dir, evidence_dir):
        directory.mkdir(parents=True, exist_ok=True)

    missing = [name for name in RULE_FILES if not (GLOBAL_EVIDENCE / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing global assets: " + ", ".join(missing))
    for name in RULE_FILES:
        shutil.copy2(GLOBAL_EVIDENCE / name, evidence_dir / name)

    timestamp = iso_now()
    header = {"schema_version": "1.0", "total_records": 0, "last_updated": timestamp}
    for name in CONSUMPTION_FILES:
        (evidence_dir / name).write_text(
            json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    config = {
        "project_name": args.name,
        "created_at": timestamp,
        "type_combination": None,
        "status": "initialized",
    }
    (config_dir / "project_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    created_files = 1 + len(RULE_FILES) + len(CONSUMPTION_FILES)
    print(f"项目路径：{project_path}")
    print(f"创建的文件数量：{created_files}")
    print(f"复制规则文件数量：{len(RULE_FILES)}")
    print(f"生成的空消费记录数量：{len(CONSUMPTION_FILES)}")


if __name__ == "__main__":
    main()