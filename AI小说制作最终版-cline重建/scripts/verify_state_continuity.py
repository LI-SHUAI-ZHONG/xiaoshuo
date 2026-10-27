"""Mechanically validate state continuity in raw third-party chain candidates."""

from __future__ import annotations

import json
import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = WORKSPACE_ROOT / "candidates_raw.jsonl"
OUTPUT_PATH = WORKSPACE_ROOT / "validated_chains.jsonl"

STOPWORDS = {
    "被",
    "了",
    "的",
    "在",
    "于",
    "与",
    "或",
    "且",
    "并",
    "等",
    "是",
    "将",
    "从",
    "向",
    "以",
    "对",
    "给",
    "由",
    "为",
    "因",
    "果",
    "之",
    "其",
    "这",
    "那",
    "及",
}

PARENTHESIS_CONTENT = re.compile(r"（[^（）]*）|\([^()]*\)")
SPLIT_MARKS = re.compile(r"[\s，,。．.、；;：:！？!?\-—_/|]+")
CHINESE_WORD = re.compile(r"^[\u4e00-\u9fff]+$")


def extract_stems(text: str) -> set[str]:
    """Extract complete Chinese tokens using only the requested mechanics."""
    without_parentheses = PARENTHESIS_CONTENT.sub(" ", text)
    tokens = SPLIT_MARKS.split(without_parentheses)
    return {
        token
        for token in tokens
        if len(token) >= 2
        and CHINESE_WORD.fullmatch(token)
        and token not in STOPWORDS
    }


def is_state_continuous(chain: dict[str, object]) -> bool:
    effects = chain["effects"]
    conditions = chain["conditions"]
    effect_ab = effects[0]
    condition_bc = conditions[1]
    effect_bc = effects[1]
    condition_cd = conditions[2]

    edge_ab = extract_stems(effect_ab) & extract_stems(condition_bc)
    edge_bc = extract_stems(effect_bc) & extract_stems(condition_cd)
    return bool(edge_ab and edge_bc)


def main() -> None:
    chains: list[dict[str, object]] = []
    with INPUT_PATH.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if line.strip():
                try:
                    chains.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"候选链 JSONL 第 {line_number} 行无效") from exc

    validated = [chain for chain in chains if is_state_continuous(chain)]
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for chain in validated:
            output.write(json.dumps(chain, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")

    samples = "; ".join(
        f"{chain['chain_id']} {chain['ids']}" for chain in validated[:2]
    )
    print(f"候选链总数：{len(chains)}")
    print(f"通过状态验证的链数：{len(validated)}")
    print(f"示例：前 2 条通过验证的链：{samples}")


if __name__ == "__main__":
    main()