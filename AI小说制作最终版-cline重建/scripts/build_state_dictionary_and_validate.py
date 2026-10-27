"""Build a keyword state dictionary and validate dynamic A->B->C chains."""

from __future__ import annotations

import json
import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DYNAMIC_NETWORK_PATH = WORKSPACE_ROOT / "08_原始资料" / "动态网络.txt"
CANDIDATES_PATH = WORKSPACE_ROOT / "candidates_raw.jsonl"
DICTIONARY_PATH = WORKSPACE_ROOT / "state_dictionary.jsonl"
VALIDATED_PATH = WORKSPACE_ROOT / "validated_by_tags.jsonl"

TAG_KEYWORDS = {
    "身体": ["饥饿", "疲惫", "受伤", "脱水", "睡眠", "体温", "体力", "疼痛", "颤抖", "僵硬", "痉挛", "出汗", "呼吸", "心跳", "瞳孔"],
    "情绪": ["愤怒", "恐惧", "悲伤", "喜悦", "惊讶", "厌恶", "焦虑", "愧疚", "羞耻", "渴望", "嫉妒", "爱", "信任", "希望", "绝望", "孤独", "归属"],
    "认知": ["注意", "记忆", "理解", "判断", "确认偏误", "锚定", "偏差", "信念", "心智模型", "认知失调", "预期", "框架"],
    "决策": ["权衡", "果断", "犹豫", "冲动", "冒险", "保守", "代价", "成本", "选择", "后果", "后悔"],
    "资源": ["食物", "水", "能量", "货币", "道具", "价值", "稀缺", "采集", "交易", "存储", "资源"],
    "时间": ["紧迫", "漫长", "短暂", "停滞", "锚点", "时间感知", "时间压力"],
    "行动": ["移动", "攻击", "防御", "采集", "制作", "交谈", "探索", "搜索", "使用", "操作", "投掷", "攀爬"],
    "社会": ["合作", "竞争", "对抗", "同盟", "交易", "信任", "隐瞒", "欺骗", "立场", "身份", "阶层", "权力", "责任"],
}
CHINESE_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")


def load_dynamic_records() -> list[dict[str, object]]:
    text = DYNAMIC_NETWORK_PATH.read_text(encoding="utf-8")
    json_start = text.find("{", text.find("```json"))
    if json_start < 0:
        raise ValueError(f"未找到动态网络 JSON: {DYNAMIC_NETWORK_PATH}")
    document = json.JSONDecoder().raw_decode(text[json_start:])[0]
    records = document["动态网络连接_完整版"]["连接列表"]
    if not isinstance(records, list):
        raise ValueError("动态网络连接列表不是数组")
    return records


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path} 第 {line_number} 行不是对象")
            rows.append(value)
    return rows


def tags_for(text: object) -> list[str]:
    value = str(text or "")
    # Keep the character-run extraction explicit: matching is substring-only,
    # with no tokenization, stemming, or semantic interpretation.
    segments = CHINESE_RUN.findall(value)
    searchable = "\n".join(segments)
    tags = [tag for tag, keywords in TAG_KEYWORDS.items() if any(keyword in searchable for keyword in keywords)]
    return tags or ["未分类"]


def build_dictionary(records: list[dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    dictionary: dict[tuple[str, str], dict[str, object]] = {}
    for record in records:
        for field, source in (("condition", "condition"), ("effect", "effect")):
            text = record.get(field)
            if not isinstance(text, str) or not text.strip():
                continue
            key = (text, source)
            dictionary[key] = {"text": text, "tags": tags_for(text), "source": source}
    return dictionary


def validate_chain(chain: dict[str, object], dictionary: dict[tuple[str, str], dict[str, object]]) -> dict[str, object] | None:
    effects = chain.get("effects")
    conditions = chain.get("conditions")
    ids = chain.get("ids")
    if not isinstance(effects, list) or not isinstance(conditions, list) or len(effects) < 3 or len(conditions) < 3:
        return None
    effect_ab = set(tags_for(effects[0]))
    condition_bc = set(tags_for(conditions[1]))
    effect_bc = set(tags_for(effects[1]))
    condition_cd = set(tags_for(conditions[2]))
    ab_overlap = sorted(effect_ab & condition_bc)
    bc_overlap = sorted(effect_bc & condition_cd)
    if not ab_overlap or not bc_overlap:
        return None
    validated = dict(chain)
    validated["tag_validation"] = {
        "ab_effect_tags": sorted(effect_ab),
        "bc_condition_tags": sorted(condition_bc),
        "bc_effect_tags": sorted(effect_bc),
        "cd_condition_tags": sorted(condition_cd),
        "ab_overlap": ab_overlap,
        "bc_overlap": bc_overlap,
    }
    return validated


def main() -> int:
    records = load_dynamic_records()
    chains = load_jsonl(CANDIDATES_PATH)
    state_dictionary = build_dictionary(records)
    validated: list[dict[str, object]] = []
    ab_count = 0
    bc_count = 0
    for chain in chains:
        effects = chain.get("effects", [])
        conditions = chain.get("conditions", [])
        if not isinstance(effects, list) or not isinstance(conditions, list) or len(effects) < 3 or len(conditions) < 3:
            continue
        ab_passed = bool(set(tags_for(effects[0])) & set(tags_for(conditions[1])))
        bc_passed = bool(set(tags_for(effects[1])) & set(tags_for(conditions[2])))
        ab_count += int(ab_passed)
        bc_count += int(bc_passed)
        if ab_passed and bc_passed:
            item = validate_chain(chain, state_dictionary)
            if item is not None:
                validated.append(item)

    with DICTIONARY_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for item in state_dictionary.values():
            output.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    with VALIDATED_PATH.open("w", encoding="utf-8", newline="\n") as output:
        for item in validated:
            output.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"总候选链数：{len(chains)}")
    print(f"AB 通过数量：{ab_count}")
    print(f"BC 通过数量：{bc_count}")
    print(f"双边通过数量：{len(validated)}")
    print("前 5 条通过链：" + "; ".join(f"{item['chain_id']} {item['ids']}" for item in validated[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())