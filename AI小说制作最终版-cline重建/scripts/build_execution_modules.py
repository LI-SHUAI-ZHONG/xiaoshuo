"""Extract execution step/module headings into a compact module list."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "执行正文.txt"
OUTPUT = ROOT / "docs" / "evidence" / "execution_modules.json"

STEP_PATTERN = re.compile(r"(?:步骤|模块)\s*([0-9]+(?:\s*第\s*[0-9]+\s*批)?|[0-9]+(?:\s*\+\s*[0-9]+)+)\s*[:：：-]\s*(.+?)\s*$")
HEADING_PATTERN = re.compile(r"^\s*##\s*([0-9]+)\.\s*(.+?)\s*$")


def clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().rstrip("。"))


def extract_modules(text: str) -> list[dict[str, str]]:
    modules: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = STEP_PATTERN.search(line) or HEADING_PATTERN.match(line)
        if not match:
            continue
        module_id = re.sub(r"\s+", "", match.group(1))
        name = clean_name(match.group(2))
        if not name or module_id in seen:
            continue
        seen.add(module_id)
        modules.append({"module_id": module_id, "name": name})
    return modules


def main() -> None:
    modules = extract_modules(SOURCE.read_text(encoding="utf-8", errors="replace"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(modules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"找到的模块总数：{len(modules)}")
    print("前 5 个模块名称：" + ("、".join(item["name"] for item in modules[:5]) if modules else "无"))
    print(f"输出文件路径：{OUTPUT}")


if __name__ == "__main__":
    main()