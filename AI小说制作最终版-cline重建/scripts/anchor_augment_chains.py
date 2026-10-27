"""Augment the eight BC-only chains with mechanically matched anchor evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CHAINS_PATH = WORKSPACE_ROOT / "bc_only.jsonl"
ANCHORS_PATH = WORKSPACE_ROOT / "08_原始资料" / "锚点网络.txt"
OUTPUT_PATH = WORKSPACE_ROOT / "augmented_chains.jsonl"

CHINESE_KEYWORDS = re.compile(r"[\u4e00-\u9fa5]{2,}")


def extract_keywords(text: str) -> list[str]:
    return CHINESE_KEYWORDS.findall(text)


def parse_anchor_rows(path: Path) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            stripped = line.strip()
            if not stripped.startswith("|") or stripped.count("|") < 4:
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) != 4 or cells[0] in {"编号", "------"}:
                continue
            if all(set(cell) <= {"-", ":", " "} for cell in cells):
                continue
            anchors.append(
                {
                    "id": cells[0],
                    "name": cells[1],
                    "content": cells[2],
                    "condition": cells[3],
                }
            )
    return anchors


def load_chains(path: Path) -> list[dict[str, object]]:
    chains: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if line.strip() and line.strip() != "[]":
                try:
                    chains.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"候选链 JSONL 第 {line_number} 行无效") from exc
    return chains


def augment_chain(
    chain: dict[str, object], anchors: list[dict[str, str]]
) -> tuple[dict[str, object], str]:
    effects = chain["effects"]
    conditions = chain["conditions"]
    effect_keywords = extract_keywords(effects[0])
    condition_keywords = extract_keywords(conditions[1])

    full_matches: list[dict[str, object]] = []
    partial_matches: list[dict[str, object]] = []
    for anchor in anchors:
        trigger_hits = [
            keyword for keyword in effect_keywords if keyword in anchor["condition"]
        ]
        content_hits = [
            keyword for keyword in condition_keywords if keyword in anchor["content"]
        ]
        match = {
            "id": anchor["id"],
            "content_hits": content_hits,
            "trigger_hits": trigger_hits,
        }
        if trigger_hits and content_hits:
            full_matches.append(match)
        elif trigger_hits or content_hits:
            partial_matches.append(match)

    if full_matches:
        status = "found"
        matches = full_matches
    elif partial_matches:
        status = "partial"
        matches = partial_matches
    else:
        status = "not_found"
        matches = []

    enhanced = dict(chain)
    enhanced["ab_anchor_ids"] = [match["id"] for match in matches]
    enhanced["ab_anchor_evidence"] = "; ".join(
        ", ".join(match["content_hits"]) for match in matches if match["content_hits"]
    )
    enhanced["augmentation_status"] = status
    return enhanced, status


def main() -> None:
    chains = load_chains(CHAINS_PATH)
    anchors = parse_anchor_rows(ANCHORS_PATH)
    enhanced_chains: list[dict[str, object]] = []
    counts = {"found": 0, "partial": 0, "not_found": 0}

    for chain in chains:
        enhanced, status = augment_chain(chain, anchors)
        enhanced_chains.append(enhanced)
        counts[status] += 1

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for chain in enhanced_chains:
            output.write(json.dumps(chain, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")

    samples = "; ".join(
        f"{chain['chain_id']} {chain['ab_anchor_ids']}"
        for chain in enhanced_chains[:2]
    )
    print(f"处理链数：{len(chains)}")
    print(f"找到完整锚点支撑的 AB 边数：{counts['found']}")
    print(f"部分匹配的 AB 边数：{counts['partial']}")
    print(f"未找到的 AB 边数：{counts['not_found']}")
    print(f"前 2 条增强后的链：{samples}")


if __name__ == "__main__":
    main()