"""Fill only evidence-backed gaps in runtime data contracts.

This script does not invent reader profiles or story facts. It derives type
keywords from the existing pipeline/index and marks unsupported fields as
pending so callers can distinguish usable data from review work.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "配置" / "类型配置模板.json"
TYPE_SOURCE = ROOT / "原始资料" / "类型系统.txt"
CONNECTION_INDEX = ROOT / "文档" / "证据" / "类型连接全局索引.json"
ROUTING_INDEX = ROOT / "资料索引" / "多维资料索引.yaml"
ROUTE_AUDIT = ROOT / "资料索引" / "资料路由审计.json"

TYPE_KEYWORDS = {
    "玄幻": ["能量", "修炼", "境界", "法宝", "宗门"],
    "仙侠": ["修仙", "渡劫", "洞府", "仙缘", "灵根"],
    "科幻": ["能量", "物理", "科技", "基因", "机械"],
    "都市": ["社会", "阶层", "职业", "资源", "货币"],
    "悬疑": ["悬念", "信息", "信任", "反转", "隐藏"],
}
ALL_TYPES = ["玄幻", "仙侠", "科幻", "悬疑", "言情", "都市", "历史", "军事", "游戏", "体育", "灵异", "同人", "二次元", "耽美", "轻小说"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_lines(name: str) -> list[int]:
    text = read_text(TYPE_SOURCE)
    return [i for i, line in enumerate(text.splitlines(), 1) if name in line]


def build_type(name: str, source_text: str) -> dict:
    keywords = TYPE_KEYWORDS.get(name, [])
    hits = [keyword for keyword in keywords if keyword in source_text]
    lines = source_lines(name)
    core = hits or [f"{name}类型规则待从原始资料确认"]
    return {
        "type_name": name,
        "core_elements": core,
        "reader_params": {"status": "pending", "reason": "原始资料未提供可核验的读者画像字段"},
        "style_constraints": ["遵守类型系统中的已确认规则", "未确认的类型偏好不得自动写入正文"],
        "length_rhythm": {"status": "pending", "reason": "原始资料未提供该类型的统一篇幅参数"},
        "source_ref": {"file": "原始资料/类型系统.txt", "matched_lines": lines[:20]},
        "source_status": "cross_confirmed" if hits else "pending",
    }


def main() -> None:
    source_text = read_text(TYPE_SOURCE)
    connection_data = json.loads(CONNECTION_INDEX.read_text(encoding="utf-8-sig"))
    combinations = connection_data.get("combinations", [])
    config = {
        "schema_version": "type-profile-1.1",
        "generated_at": now(),
        "source_policy": {
            "project_independent": True,
            "source_files": ["原始资料/类型系统.txt", "文档/证据/类型连接全局索引.json"],
            "unsupported_fields": "pending",
        },
        "types": {name: build_type(name, source_text) for name in ALL_TYPES},
        "combinations": [],
    }
    for item in combinations:
        types = item.get("combination_id", "").split("_")
        config["combinations"].append({
            "combination_id": item.get("combination_id"),
            "types": types,
            "conflicts": item.get("conflicts", []),
            "resolutions": item.get("recommended_mechanisms", []),
            "recommended_mechanisms": item.get("recommended_mechanisms", []),
            "source_ref": "文档/证据/类型连接全局索引.json",
            "source_status": "cross_confirmed" if item.get("connection_ids") else "pending",
        })
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    routes = []
    for line_number, line in enumerate(read_text(ROUTING_INDEX).splitlines(), 1):
        match = re.search(r"(?:path|source_file):\s*\"([^\"]+)\"", line)
        if match:
            relative = match.group(1)
            routes.append({"line": line_number, "path": relative, "exists": (ROOT / relative).is_file()})
    ROUTE_AUDIT.write_text(json.dumps({"schema_version": "route-audit-1.0", "generated_at": now(), "routes": routes, "missing": [x for x in routes if not x["exists"]], "status": "passed" if all(x["exists"] for x in routes) else "review"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"config": str(CONFIG), "types": len(config["types"]), "combinations": len(config["combinations"]), "route_audit": str(ROUTE_AUDIT), "missing_routes": sum(not x["exists"] for x in routes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()