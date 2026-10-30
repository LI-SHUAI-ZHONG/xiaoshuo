"""Public project-scoped launcher for the authored execution pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from 执行管道 import run_pipeline
from 项目生命周期管理 import validate_active_project


def main() -> int:
    parser = argparse.ArgumentParser(description="启动指定项目的完整创作运行")
    parser.add_argument("--project-root", required=True, help="具体项目目录")
    parser.add_argument("--project-id")
    parser.add_argument("--genres", nargs="+")
    parser.add_argument("--run-id", help="固定本次运行的安全目录名")
    args = parser.parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    config_path = project_root / "配置" / "project_config.json"
    if not config_path.is_file():
        raise SystemExit(f"项目配置不存在：{config_path}")
    import json
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"项目配置不可解析：{config_path}") from exc
    try:
        validate_active_project(
            SCRIPT_ROOT.parent,
            project_root,
            project_id=args.project_id or config.get("project_id"),
            book_title=config.get("book_title") or project_root.name,
            resource_root=config.get("resource_root"),
        )
    except ValueError as exc:
        raise SystemExit(f"项目启动前置校验失败：{exc}") from exc
    results = run_pipeline(str(project_root), args.project_id, args.genres, args.run_id, enforce_lifecycle=True)
    return 0 if results and all(row.get("status") == "success" for row in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())