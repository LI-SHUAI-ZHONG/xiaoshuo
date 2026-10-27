"""Build a lightweight index from the full static connection export."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CANDIDATES = (
    ROOT / "03_网络派生" / "静态派生" / "static_connections.full.json",
    ROOT / "四网络连接，剧情覆盖" / "static_connections.full.json",
)
OUTPUT = ROOT / "docs" / "evidence" / "static_network_index.json"


def source_path() -> Path:
    for candidate in SOURCE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("static_connections.full.json not found")


def main() -> None:
    data = json.loads(source_path().read_text(encoding="utf-8"))
    edges = data["connections"]
    source_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    pair_type_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    unique_sources: set[str] = set()
    unique_targets: set[str] = set()

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        edge_type = edge["type"]
        unique_sources.add(source)
        unique_targets.add(target)
        source_counts[source] += 1
        type_counts[edge_type] += 1
        pair_type_counts[(source, target)][edge_type] += 1

    top_sources = []
    for source, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))[:50]:
        pairs = []
        for (pair_source, target), type_counts_for_pair in pair_type_counts.items():
            if pair_source != source:
                continue
            pairs.append({
                "target": target,
                "type_distribution": dict(sorted(type_counts_for_pair.items(), key=lambda item: (-item[1], item[0]))),
                "count": sum(type_counts_for_pair.values()),
            })
        pairs.sort(key=lambda item: (-item["count"], item["target"]))
        top_sources.append({"node": source, "count": count, "pairs_by_type": pairs})

    output = {
        "total_edges": len(edges),
        "unique_sources": len(unique_sources),
        "unique_targets": len(unique_targets),
        "unique_source_nodes": sorted(unique_sources),
        "unique_target_nodes": sorted(unique_targets),
        "type_distribution": dict(sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))),
        "top_sources": top_sources,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"总边数：{len(edges)}")
    print(f"唯一 source 数量：{len(unique_sources)}")
    print(f"唯一 target 数量：{len(unique_targets)}")
    print("前 3 个最活跃的 source 节点：" + "、".join(f"{item['node']}({item['count']})" for item in top_sources[:3]))
    print("索引文件已生成")


if __name__ == "__main__":
    main()