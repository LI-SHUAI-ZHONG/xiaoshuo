"""Rebuild current project runtime evidence from the fused source materials.

The six files in 原始资料 are read-only. This script replaces only derived
indexes, rules, project configuration, and evidence that were tied to older
pre-fusion source hashes.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "原始资料"
EVIDENCE = ROOT / "文档" / "证据"
CONFIG = ROOT / "配置"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def source_blocks(path: Path) -> list[tuple[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\\r\\n", "\n").replace("\\n", "\n")
    pattern = re.compile(r"^SOURCE:\s*([^\n]+)\n=+\n(.*?)(?=\nSOURCE:|\Z)", re.MULTILINE | re.DOTALL)
    rows: list[tuple[str, Any]] = []
    for name, body in pattern.findall(text):
        try:
            rows.append((name.strip(), json.loads(body.strip())))
        except json.JSONDecodeError:
            continue
    return rows


def library_index() -> list[dict[str, Any]]:
    text = (RAW / "资料库.txt").read_text(encoding="utf-8-sig").replace("\\r\\n", "\n").replace("\\n", "\n")
    pattern = re.compile(r"^(?:###\s*(\d+(?:\.\d+)?)[_：: ]([^\n]+)|##\s*板块\s*(\d+(?:\.\d+)?)[_：: ]([^\n]+))\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    rows = []
    seen: dict[str, int] = {}
    for index, match in enumerate(matches):
        number, name = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
        if not number or not name:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start():end]
        entry_id = f"{number}_{name.strip()}"
        line_start = text[:match.start()].count("\n") + 1
        # The fused library contains repeated copies of some title blocks.
        # The first occurrence is the callable canonical entry; every later
        # occurrence is retained in the duplicate-location audit, not indexed.
        if entry_id in seen:
            continue
        seen[entry_id] = line_start
        rows.append({
            "entry_id": entry_id,
            "name": name.strip(),
            "type": "method_or_rule",
            "key_attributes": [label for label in ("定义", "调用条件", "指令", "设计指令", "写作指令", "示例") if f"【{label}】" in body],
            "dependencies": [],
            "has_examples": "【示例】" in body,
            "has_conditions": "【调用条件】" in body,
            "source_ref": {"file": "原始资料/资料库.txt", "locator": entry_id, "line_start": line_start},
            "source_status": "raw_indexed",
        })
    return rows


def library_duplicate_audit() -> dict[str, Any]:
    text = (RAW / "资料库.txt").read_text(encoding="utf-8-sig").replace("\\r\\n", "\n").replace("\\n", "\n")
    pattern = re.compile(r"^(?:###\s*(\d+(?:\.\d+)?)[_：: ]([^\n]+)|##\s*板块\s*(\d+(?:\.\d+)?)[_：: ]([^\n]+))\s*$", re.MULTILINE)
    locations: dict[str, list[int]] = {}
    for match in pattern.finditer(text):
        number, name = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
        if number and name:
            locations.setdefault(f"{number}_{name.strip()}", []).append(text[:match.start()].count("\n") + 1)
    duplicates = [{"entry_id": entry_id, "canonical_line_start": lines[0], "duplicate_line_starts": lines[1:]} for entry_id, lines in locations.items() if len(lines) > 1]
    return {"schema_version": "fused-library-duplicate-title-audit-1.0", "source_sha256": sha(RAW / "资料库.txt"), "heading_count": sum(len(lines) for lines in locations.values()), "canonical_entry_count": len(locations), "duplicate_title_count": len(duplicates), "duplicate_occurrence_count": sum(len(row["duplicate_line_starts"]) for row in duplicates), "policy": "同名块不作为独立可调用条目；首个出现位置为规范索引对象，其余位置保留为只读审计证据。", "duplicates": duplicates}


def source_snapshot() -> list[dict[str, str]]:
    paths = [
        "原始资料/资料库.txt", "原始资料/类型系统.txt", "原始资料/类型连接.txt",
        "原始资料/静态网络.txt", "原始资料/动态网络.txt", "原始资料/锚点网络.txt",
    ]
    return [{"path": item, "sha256": sha(ROOT / item)} for item in paths]


def scene_action_chain(scene_id: str) -> list[dict[str, str]]:
    chains = {
        "CH01-S01": [
            {"beat": "入场", "event": "沈砚进入外门检测场，先观察值守弟子的记录顺序和检测石的旧痕。", "pressure": "今日检测决定晋升资格，任何质疑都会被记为扰乱秩序。"},
            {"beat": "异常", "event": "第七息回亮时，检测石的细纹与镇潮阵方向同时发白。", "pressure": "执律堂将异象归为修行不稳，要求他立刻离台。"},
            {"beat": "试探", "event": "沈砚用不带指控的问题追问检测记录的间隔，陆昭替他遮住旁人的视线。", "pressure": "陆昭的药额依赖宗门考核，不愿被他的追查拖入禁令。"},
            {"beat": "取证", "event": "他趁记录册翻页时记下被药灰填过的刻痕和第七息的偏差。", "pressure": "若被发现私留读数，晋升资格会当场冻结。"},
            {"beat": "钩子", "event": "沈砚把异常读数藏进袖中，决定去档案廊寻找潮灾前的原始记录。", "pressure": "他失去当场申诉的机会，只能在规则之外继续追查。"},
        ],
        "CH01-S02": [
            {"beat": "入场", "event": "沈砚进入藏卷阁档案廊，先确认封存柜、旧册和巡查路线的位置。", "pressure": "越权接触潮灾卷宗会连累当值录事。"},
            {"beat": "对话", "event": "他以缺失页码为由向许照微提问，不直接说出镇潮阵异常。", "pressure": "许照微必须在守规与保留线索之间选择。"},
            {"beat": "缺页", "event": "许照微让他看见被整齐切走的一页，页边仍留有潮期编号。", "pressure": "缺页只能证明删改存在，无法解释谁在删改。"},
            {"beat": "取证", "event": "沈砚把页边刻痕与检测石读数并列记下，发现两者的时段重合。", "pressure": "他不能留下会暴露许照微的抄录痕迹。"},
            {"beat": "钩子", "event": "许照微把缺页留给他，同时要求他不得提及自己的名字。", "pressure": "下一轮检测即将开始，证据必须在被收回前找到用途。"},
        ],
        "CH01-S03": [
            {"beat": "门前", "event": "沈砚带着缺页回到封存室外，禁线已把回廊灯火隔在身后。", "pressure": "执律堂正在追查缺失读数，陆昭被叫去问话。"},
            {"beat": "分歧", "event": "陆昭要求他交回证据保住药额，沈砚承认自己尚未掌握真相。", "pressure": "两人的利益第一次正面冲突，任何承诺都无法消除风险。"},
            {"beat": "验证", "event": "沈砚按缺页上的节拍叩门，第三次回声来自旧域更深处。", "pressure": "这一步会留下触碰禁线的可追查痕迹。"},
            {"beat": "选择", "event": "他没有交回异常读数，而是把可复核的刻痕与缺页一同藏起。", "pressure": "陆昭因此被记为协助者，药额和晋升资格都可能受影响。"},
            {"beat": "代价", "event": "执律堂宣布暂缓沈砚的晋升资格，夜里的镇潮阵再次回响。", "pressure": "退路变窄后，他必须决定是否继续进入旧域。"},
        ],
    }
    return chains[scene_id]


def project_config(bible: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    world = bible.get("world", {}) if isinstance(bible.get("world"), dict) else {}
    characters = [row for row in bible.get("characters", []) if isinstance(row, dict)]
    protagonist = next((row for row in characters if row.get("name") == "沈砚"), characters[0] if characters else {})
    scenes_by_id = {str(row.get("scene_id")): row for row in brief.get("scenes", []) if isinstance(row, dict)}
    scene_details = {
        "CH01-S01": {"location": "栖云宗外门检测场", "character_goal": "通过检测并确认第七息异常是否来自自身", "obstacle": "执律堂将异常归为修行不稳，陆昭要求他不要公开追问", "new_information": "第七息回亮与镇潮阵的灵息回声同步", "state_before": "沈砚只怀疑检测有误", "state_after": "沈砚确认异常可被复核且可能来自阵法", "ending": "他把异常读数藏入袖中，失去当场申诉的机会", "hook": "档案廊是否留有潮灾前的原始记录"},
        "CH01-S02": {"location": "栖云宗藏卷阁档案廊", "character_goal": "取得能证明异常存在的旧档案缺页", "obstacle": "许照微以禁令阻拦，越权查档会连累她", "new_information": "潮灾名册中存在被刻意抹去的名字与检测记录", "state_before": "沈砚只拥有一条异常读数", "state_after": "沈砚获得不能解释真相但足以继续追查的缺页", "ending": "许照微留下缺页后要求他不得提及自己的名字", "hook": "缺页上的刻痕指向下一轮检测"},
        "CH01-S03": {"location": "栖云宗外门回廊与封存室外", "character_goal": "保留异常证据并避免陆昭因协助受罚", "obstacle": "执律堂追查缺失读数，陆昭的药额与晋升资格都受牵连", "new_information": "交回证据会让异常被归档，保留证据会立刻触犯宗门秩序", "state_before": "沈砚仍能在规则内调查", "state_after": "沈砚决定越界保留证据，陆昭承担可见风险", "ending": "沈砚的晋升资格被暂缓，退路正式变窄", "hook": "镇潮阵下一次回响将在夜间出现"},
    }
    scenes = []
    for scene_id in ("CH01-S01", "CH01-S02", "CH01-S03"):
        source = scenes_by_id.get(scene_id, {})
        detail = scene_details[scene_id]
        scenes.append({"scene_id": scene_id, "purpose": str(source.get("creative_need") or detail["character_goal"]), "action_chain": scene_action_chain(scene_id), **detail})
    chapter = {"chapter_id": "CH01", "chapter_goal": "沈砚在外门检测中发现镇潮阵异常，取得第一份证据，并为保留它付出晋升资格受损的代价。", "target_words": 4500, "scenes": scenes}
    return {
        "schema_version": "project-config-1.0", "project_id": str(bible.get("project_id") or "trial-玄幻-沈砚"),
        "project_name": "衡渊-潮痕入骨", "project_mode": "system_runtime_planned", "status": "runtime_baseline_ready",
        "created_at": now(), "primary_type": "玄幻", "genre_selection": ["玄幻", "悬疑"],
        "theme_combination": ["悬疑"], "type_combination": {"combination_id": "玄幻+悬疑", "status": "author_confirmed_for_draft_only"},
        "type_selection_policy": {"mode": "draft_only", "formal_release_allowed": False},
        "target_words": 4500, "target_chapter_count": 1,
        "book_title": "潮痕入骨", "world_stage": str(world.get("present_condition") or "衡渊的镇潮阵维持秩序，也遮蔽了灵脉异常的代价。"),
        "mainline_conflict": str(world.get("central_question") or "沈砚追查镇潮阵的隐秘代价，并在秩序与真相之间承担选择后果。"),
        "core_mystery": str((world.get("power_system") or {}).get("hidden_truth") or "镇潮阵为何持续抽取低阶修士的灵息。"),
        "protagonist": {"name": str(protagonist.get("name") or "沈砚"), "personality": ["谨慎", "追问", "重视证据"], "desire": str(protagonist.get("want") or "取得内门晋升资格。"), "obsession": "查清父亲在潮期死亡的真相", "decision_tendency": ["先取证", "以细节逼人表态"], "blind_spots": ["容易把盟友推入被动"], "emotional_reactions": ["面对规则说谎时急于追查"], "dynamic_aliases": ["沈砚"], "dynamic_node_id": "1.1", "dynamic_node_name": "主角"},
        "chapter_plan": [chapter], "source_basis": {"story_bible": "配置/项目创作圣经.json", "scene_brief": "配置/首章场景创作简报.json", "material_snapshots": source_snapshot()},
    }


def main() -> int:
    bible = read_json(CONFIG / "项目创作圣经.json", {})
    brief = read_json(CONFIG / "首章场景创作简报.json", {})
    profiles = read_json(CONFIG / "类型配置模板.json", {})
    if not isinstance(bible, dict) or not isinstance(brief, dict) or not isinstance(profiles, dict):
        raise ValueError("项目圣经、场景简报或类型配置不可解析")
    config = project_config(bible, brief)
    write_json(CONFIG / "project_config.json", config)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    profiles_by_type = profiles.get("types", {}) if isinstance(profiles.get("types"), dict) else {}
    selected_profiles = {
        name: profiles_by_type[name]
        for name in config["genre_selection"]
        if isinstance(profiles_by_type.get(name), dict)
    }
    write_json(EVIDENCE / "小说资料选择清单.json", {
        "schema_version": "novel-source-selection-1.1",
        "generated_at": now(),
        "project_id": config["project_id"],
        "selection_inputs": {
            "primary_type": config["primary_type"],
            "theme_combination": config["theme_combination"],
            "target_words": config["target_words"],
            "target_chapter_count": config["target_chapter_count"],
        },
        "selected_type_profiles": selected_profiles,
        "selected_type_combination": config["type_combination"],
        "shared_sources": [
            "原始资料/资料库.txt",
            "原始资料/静态网络.txt",
            "原始资料/动态网络.txt",
            "原始资料/锚点网络.txt",
        ],
        "selection_policy": "只读取当前融合资料；类型选择仅授予 draft_only 创作范围，正式发布仍需独立审批。",
        "status": "draft_only",
    })
    library = library_index()
    write_jsonl(ROOT / "文档" / "资料库索引.jsonl", library)
    write_json(EVIDENCE / "资料库重复标题审计.json", library_duplicate_audit())

    static = read_json(RAW / "静态网络.txt", {})
    static_rows = []
    for source, group in (static.get("source_index", {}) if isinstance(static, dict) else {}).items():
        for index, target in enumerate((group or {}).get("targets", [])):
            if isinstance(target, dict):
                static_rows.append({"edge_id": f"STATIC:{source}->{target.get('target')}#{len(static_rows) + 1}", "source": source, **target, "source_ref": {"file": "原始资料/静态网络.txt", "locator": f"source_index.{source}.targets[{index}]"}})
    dynamic_doc = read_json(RAW / "动态网络.txt", {})
    dynamic_rows = dynamic_doc.get("动态网络连接_完整版", {}).get("连接列表", []) if isinstance(dynamic_doc, dict) else []
    anchors = []
    anchor_pattern = re.compile(r"^\|\s*((?:ID|[MSPBECTDALU])\d+\.\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|")
    for line_number, line in enumerate((RAW / "锚点网络.txt").read_text(encoding="utf-8-sig").splitlines(), 1):
        match = anchor_pattern.match(line.strip())
        if match:
            anchor_id, name, definition, trigger, category = match.groups()
            anchors.append({"anchor_id": anchor_id, "name": name.strip(), "definition": definition.strip(), "trigger": trigger.strip(), "category": category.strip(), "source_ref": {"file": "原始资料/锚点网络.txt", "locator": anchor_id, "line": line_number}})
    write_json(EVIDENCE / "静态网络索引.json", {"schema_version": "current-fused-static-index-1.0", "source_sha256": sha(RAW / "静态网络.txt"), "total_edges": len(static_rows), "edges": static_rows})
    write_json(EVIDENCE / "静态网络绑定摘要.json", {
        "schema_version": "current-fused-static-binding-summary-1.0",
        "source_sha256": sha(RAW / "静态网络.txt"),
        "total_edges": len(static_rows),
        "edge_type_counts": {kind: sum(str(row.get("type") or "") == kind for row in static_rows) for kind in sorted({str(row.get("type") or "") for row in static_rows})},
        "policy": "当前融合静态网络的只读绑定摘要；项目采用仍须按场景与来源证据单独记录。",
    })
    write_jsonl(EVIDENCE / "动态链索引.jsonl", [{"chain_id": row.get("id"), "source": row.get("source"), "target": row.get("target"), "type": row.get("type"), "condition": row.get("condition"), "effect": row.get("effect"), "source_ref": {"file": "原始资料/动态网络.txt", "locator": f"动态网络连接_完整版.连接列表[{index}]"}, "status": "raw_indexed"} for index, row in enumerate(dynamic_rows) if isinstance(row, dict)])
    write_json(EVIDENCE / "动态网络状态摘要.json", {"schema_version": "current-fused-dynamic-summary-1.0", "source_sha256": sha(RAW / "动态网络.txt"), "total_connections": len(dynamic_rows), "usable_condition_effect_count": sum(bool(row.get("condition")) and bool(row.get("effect")) for row in dynamic_rows if isinstance(row, dict))})
    write_json(EVIDENCE / "锚点分类索引.json", {"schema_version": "current-fused-anchor-index-1.0", "source_sha256": sha(RAW / "锚点网络.txt"), "total_anchors": len(anchors), "category_counts": {key: sum(row["anchor_id"].startswith(key) for row in anchors) for key in ("M", "S", "P", "B", "E", "C", "T", "D", "A", "L", "ID", "U")}, "anchors": anchors})

    type_records = []
    for name, payload in source_blocks(RAW / "类型连接.txt"):
        values = payload if isinstance(payload, list) else [payload]
        for index, item in enumerate(values, 1):
            if isinstance(item, dict):
                identifier = str(item.get("connection_id") or item.get("dynamic_combination_id") or item.get("stable_id") or f"{name}:{index}")
                type_records.append({"connection_id": identifier, "types": [value for key, value in item.items() if key in {"primary_type_id", "source_type", "target_type"} and isinstance(value, str)], "source_ref": {"file": "原始资料/类型连接.txt", "locator": f"{name}[{index}]"}, "status": "raw_indexed"})
    write_json(EVIDENCE / "类型连接全局索引.json", {"schema_version": "current-fused-type-connection-index-1.0", "source_sha256": sha(RAW / "类型连接.txt"), "combinations": type_records})
    rules = {
        "类型连接规则.json": {"schema_version": "runtime-rule-1.0", "rules": []},
        "静态连接采用规则.json": {"schema_version": "runtime-rule-1.0", "rules": []},
        "动态链消费规则.json": {"schema_version": "runtime-rule-1.0", "rules": []},
        "锚点采用规则.json": {"schema_version": "runtime-rule-1.0", "rules": []},
        "执行采用规则.json": {"schema_version": "runtime-rule-1.0", "rules": []},
        "采用规则.json": {"schema_version": "runtime-rule-1.0", "rules": []},
        "类型连接采用结构.json": {"schema_version": "runtime-structure-1.0", "records": []},
    }
    for name, value in rules.items():
        write_json(EVIDENCE / name, value)
    for name in ("类型连接采用.jsonl", "动态链消费.jsonl", "静态连接消费.jsonl", "锚点消费.jsonl", "执行消费.jsonl"):
        write_jsonl(EVIDENCE / name, [{"record_type": "header", "schema_version": "1.0", "total_records": 0, "last_updated": now()}])
    write_json(EVIDENCE / "来源深度检查报告.json", {"schema_version": "current-fused-source-baseline-1.0", "generated_at": now(), "policy": "当前融合资料的哈希基线；旧 docs 报告不作为运行依据。", "sources": [{"source": path.name, "sha256": sha(path), "bytes": path.stat().st_size, "status": "current_fused_unreviewed"} for path in sorted(RAW.glob("*.txt"))]})
    write_json(EVIDENCE / "当前资料运行基线.json", {"schema_version": "current-fused-runtime-baseline-1.0", "generated_at": now(), "project_id": config["project_id"], "source_snapshots": source_snapshot(), "derived_outputs": ["文档/资料库索引.jsonl", "文档/证据/类型连接全局索引.json", "文档/证据/静态网络索引.json", "文档/证据/动态链索引.jsonl", "文档/证据/锚点分类索引.json"], "delivery_status": "draft_only"})
    print(json.dumps({"status": "rebuilt", "project_id": config["project_id"], "library_entries": len(library), "static_edges": len(static_rows), "dynamic_chains": len(dynamic_rows), "anchors": len(anchors), "type_connections": len(type_records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
