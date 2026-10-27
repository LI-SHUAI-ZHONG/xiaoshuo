"""Build raw A->B->C candidates from the original dynamic network records."""

from __future__ import annotations

import json
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = WORKSPACE_ROOT / "08_原始资料" / "动态网络.txt"
OUTPUT_PATH = WORKSPACE_ROOT / "candidates_raw.jsonl"


def load_connections(path: Path) -> list[dict[str, object]]:
    """Extract the JSON document embedded in the Markdown source file."""
    text = path.read_text(encoding="utf-8")
    json_start = text.find("{", text.find("```json"))
    if json_start == -1:
        raise ValueError(f"未找到 JSON 文档: {path}")

    document = json.JSONDecoder().raw_decode(text[json_start:])[0]
    try:
        connections = document["动态网络连接_完整版"]["连接列表"]
    except (KeyError, TypeError) as exc:
        raise ValueError("JSON 中未找到 动态网络连接_完整版.连接列表") from exc

    if not isinstance(connections, list):
        raise ValueError("连接列表不是数组")
    return connections


def build_record_map(
    connections: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Keep only the requested original fields, indexed by record ID."""
    record_map: dict[str, dict[str, object]] = {}
    for record in connections:
        record_id = record.get("id")
        if not isinstance(record_id, str):
            raise ValueError("连接记录缺少字符串 id")
        record_map[record_id] = {
            field: record.get(field)
            for field in ("source", "target", "condition", "effect", "type", "priority")
        }
    return record_map


def build_chains(
    connections: list[dict[str, object]],
    record_map: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Enumerate every ordered three-record path without inference."""
    by_source: dict[object, list[str]] = {}
    for record_id, record in record_map.items():
        by_source.setdefault(record["source"], []).append(record_id)

    chains: list[dict[str, object]] = []
    for first in connections:
        first_id = first["id"]
        for second_id in by_source.get(first.get("target"), []):
            second = record_map[second_id]
            for third_id in by_source.get(second["target"], []):
                third = record_map[third_id]
                records = (first, second, third)
                chains.append(
                    {
                        "chain_id": f"TPL-{len(chains) + 1:05d}",
                        "ids": [first_id, second_id, third_id],
                        "sources": [record["source"] for record in records],
                        "targets": [record["target"] for record in records],
                        "conditions": [record["condition"] for record in records],
                        "effects": [record["effect"] for record in records],
                        "types": [record["type"] for record in records],
                        "priority": first.get("priority"),
                    }
                )
    return chains


def main() -> None:
    connections = load_connections(INPUT_PATH)
    record_map = build_record_map(connections)
    chains = build_chains(connections, record_map)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for chain in chains:
            output.write(json.dumps(chain, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")

    print(f"总候选链数量：{len(chains)}")
    print("文件 candidates_raw.jsonl 已生成")
    samples = "; ".join(
        f"{chain['chain_id']} {chain['ids']}" for chain in chains[:2]
    )
    print(f"前 2 条候选链：{samples}")


if __name__ == "__main__":
    main()