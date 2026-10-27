"""Build the global type-combination index from the source document only."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "08_原始资料" / "类型连接.txt"
OUTPUT = ROOT / "docs" / "evidence" / "type_connection_global_index.json"

# Match only the three source keys requested by the index contract.
COMBINATION_PATTERN = re.compile(
    r'"(?:组合_id|combination|类型组合)"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"'
)


def extract_combinations(text: str) -> list[str]:
    combinations: list[str] = []
    seen: set[str] = set()
    for match in COMBINATION_PATTERN.finditer(text):
        value = json.loads('"' + match.group(1) + '"').strip()
        if value and value not in seen:
            seen.add(value)
            combinations.append(value)
    return combinations


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    combinations = extract_combinations(text)
    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "combinations": combinations,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"提取到的组合数量：{len(combinations)}")
    print("前 5 个组合名称：" + ("、".join(combinations[:5]) if combinations else "无"))
    print("脚本已生成")
    print("脚本运行结果：成功")


if __name__ == "__main__":
    main()