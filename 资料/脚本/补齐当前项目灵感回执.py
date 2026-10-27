from __future__ import annotations

import argparse
import json
from pathlib import Path

from 灵感库选型器 import build_selection, validate_selection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    config = json.loads((root / "配置" / "project_config.json").read_text(encoding="utf-8-sig"))
    profile = root / "配置" / "类型配置模板.json"
    receipt = build_selection(
        profile,
        str(config["project_id"]),
        str(config["primary_type"]),
        list(config.get("theme_combination", [])),
        target_words=int(config["target_words"]),
        target_chapter_count=int(config["target_chapter_count"]),
    )
    errors = validate_selection(
        receipt,
        project_id=str(config["project_id"]),
        selected_types=list(config.get("genre_selection", [])),
        profile_path=profile,
    )
    if errors:
        raise ValueError("生成的灵感回执未通过当前项目校验：" + ";".join(errors))
    target = root / "文档" / "证据" / "小说灵感选型回执.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "project_id": receipt["project_id"], "selection_id": receipt["selection_id"], "selected_types": receipt["selected_types"], "path": str(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())