"""Classify raw third-party chains using mechanical Chinese substring matching."""

from __future__ import annotations

import json
import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = WORKSPACE_ROOT / "candidates_raw.jsonl"

OUTPUT_PATHS = {
    "both": WORKSPACE_ROOT / "both_passed.jsonl",
    "ab": WORKSPACE_ROOT / "ab_only.jsonl",
    "bc": WORKSPACE_ROOT / "bc_only.jsonl",
}

CHINESE_KEYWORDS = re.compile(r"[\u4e00-\u9fa5]{2,}")


def extract_keywords(text: str) -> list[str]:
    """Return unchanged continuous Chinese strings of length at least two."""
    return CHINESE_KEYWORDS.findall(text)


def has_substring_overlap(effect: str, condition: str) -> bool:
    """Pass when any complete extracted condition keyword occurs in the effect."""
    return any(keyword in effect for keyword in extract_keywords(condition))


def load_chains() -> list[dict[str, object]]:
    chains: list[dict[str, object]] = []
    with INPUT_PATH.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if line.strip():
                try:
                    chains.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"候选链 JSONL 第 {line_number} 行无效") from exc
    return chains


def write_jsonl(path: Path, chains: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        if not chains:
            output.write("[]\n")
            return
        for chain in chains:
            output.write(json.dumps(chain, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")


def main() -> None:
    chains = load_chains()
    both_passed: list[dict[str, object]] = []
    ab_only: list[dict[str, object]] = []
    bc_only: list[dict[str, object]] = []

    for chain in chains:
        effects = chain["effects"]
        conditions = chain["conditions"]
        ab_passed = has_substring_overlap(effects[0], conditions[1])
        bc_passed = has_substring_overlap(effects[1], conditions[2])

        if ab_passed and bc_passed:
            both_passed.append(chain)
        elif ab_passed:
            ab_only.append(chain)
        elif bc_passed:
            bc_only.append(chain)

    write_jsonl(OUTPUT_PATHS["both"], both_passed)
    write_jsonl(OUTPUT_PATHS["ab"], ab_only)
    write_jsonl(OUTPUT_PATHS["bc"], bc_only)

    samples = "; ".join(
        f"{chain['chain_id']} {chain['ids']}" for chain in both_passed[:2]
    )
    print(f"候选链总数：{len(chains)}")
    print(f"AB 通过数量：{len(both_passed) + len(ab_only)}")
    print(f"BC 通过数量：{len(both_passed) + len(bc_only)}")
    print(f"双边都通过数量：{len(both_passed)}")
    if both_passed:
        print(f"示例（双边都通过的前 2 条）：{samples}")
    else:
        fallback = "; ".join(
            f"{chain['chain_id']} {chain['ids']}" for chain in ab_only[:2]
        )
        print("示例（双边都通过的前 2 条）：样例：无")
        print(f"替代参考（ab_only 前 2 条）：{fallback}")


if __name__ == "__main__":
    main()