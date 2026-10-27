"""Analyze the index/consumption scheme and audit raw sources against it.

This is a read-only audit. It deliberately reports both syntactic extraction
and runtime-consumable extraction because an index hit is not an adoption.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "08_原始资料"
ANALYSIS_OUT = ROOT / "docs" / "analysis" / "new_scheme_analysis.md"
REPORT_OUT = ROOT / "docs" / "evidence" / "source_depth_check_report.json"
PLAN_OUT = ROOT / "docs" / "evidence" / "completion_plan.json"

SOURCES = {
    "资料库.txt": {
        "components": ["docs/library_index.jsonl", "docs/library_adoption.jsonl", "docs/evidence/adoption_rules.json"],
        "kind": "library",
    },
    "类型系统.txt": {"components": ["config/type_profile_template.json"], "kind": "type"},
    "类型连接.txt": {
        "components": ["docs/evidence/type_connection_global_index.json", "docs/evidence/type_connection_rules.json", "docs/evidence/type_connection_adoption_schema.json", "docs/evidence/type_connection_adoption.jsonl"],
        "kind": "connection",
    },
    "动态网络.txt": {
        "components": ["state_dictionary.jsonl", "validated_by_tags.jsonl", "docs/evidence/dynamic_chain_index.jsonl", "docs/evidence/dynamic_chain_consumption_rules.json", "docs/evidence/dynamic_chain_consumption.jsonl"],
        "kind": "dynamic",
    },
    "静态网络.txt": {
        "components": ["docs/evidence/static_network_index.json", "docs/evidence/static_connection_adoption_rules.json", "docs/evidence/static_connection_consumption.jsonl"],
        "kind": "static",
    },
    "锚点网络.txt": {
        "components": ["docs/evidence/anchor_category_index.json", "docs/evidence/anchor_adoption_rules.json", "docs/evidence/anchor_consumption.jsonl"],
        "kind": "anchor",
    },
}

PLACEHOLDER = re.compile(r"(?:无|暂无|待补充|待确认|未确认|待实现|空数组|placeholder|pending|unconfirmed)", re.I)
ANCHOR = re.compile(r"(?<![A-Za-z0-9])(ID|M|S|P|B|E|C|T|D|A|L|U)\d+\.\d+(?![A-Za-z0-9])")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def load_json(path: Path):
    try:
        return json.loads(read_text(path))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def component_status(paths: list[str]) -> dict:
    present = [p for p in paths if (ROOT / p).is_file()]
    return {"expected": paths, "present": present, "missing": [p for p in paths if p not in present]}


def jsonl_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records = []
    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
        except json.JSONDecodeError:
            continue
    return records


def raw_stats(name: str, kind: str) -> dict:
    path = RAW / name
    text = read_text(path) if path.is_file() else ""
    lines = text.splitlines()
    placeholders = len(PLACEHOLDER.findall(text))
    stats = {"source": name, "total_items": 0, "extractable": 0, "not_extractable": 0, "missing_fields": [], "placeholder_count": placeholders, "status": "blocked" if not path.is_file() else "partial", "line_count": len(lines), "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
    if kind == "library":
        headings = re.findall(r"^###\s+(\d+\.\d+_[^\n]+)", text, re.M)
        index = jsonl_records(ROOT / "docs/library_index.jsonl")
        stats.update(total_items=len(headings), extractable=sum(bool(re.match(r"^\d+\.\d+_", x)) for x in headings), indexed_items=len(index), indexed_missing_dependencies=sum(not x.get("dependencies") for x in index), indexed_missing_examples=sum(not x.get("has_examples") for x in index))
        stats["missing_fields"] = ["dependencies" if stats["indexed_missing_dependencies"] else "", "examples" if stats["indexed_missing_examples"] else ""]
        stats["missing_fields"] = [x for x in stats["missing_fields"] if x]
    elif kind == "type":
        template = load_json(ROOT / "config/type_profile_template.json") or {}
        types = template.get("types", {})
        stats.update(total_items=len(types), extractable=sum(bool(name) for name in types), type_names=sorted(types), complete_profiles=sum(bool(v.get("core_elements") and v.get("reader_params") and v.get("style_constraints")) for v in types.values() if isinstance(v, dict)), source_type_tokens=len(set(re.findall(r"(?:类型|题材)[：:]\s*([^\n，。；]+)", text))))
        stats["missing_fields"] = ["core_elements", "reader_params", "style_constraints"]
    elif kind == "connection":
        ids = re.findall(r'"(?:组合_id|combination|类型组合|combination_id|dynamic_combination_id)"\s*:\s*"([^"]+)"', text)
        stats.update(total_items=len(ids), extractable=len(set(ids)), unique_ids=len(set(ids)), conflict_records=len(re.findall(r"冲突", text)), recommendation_records=len(re.findall(r"推荐|mechanism_ids|recommended_mechanisms", text, re.I)), source_index_count=len((load_json(ROOT / "docs/evidence/type_connection_global_index.json") or {}).get("combinations", [])))
        stats["missing_fields"] = ["conflict_details", "recommended_mechanism_explanation", "source_connection_id"]
    elif kind == "dynamic":
        records = re.findall(r'"source"\s*:\s*"([^"]+)".*?"target"\s*:\s*"([^"]+)"', text, re.S)
        conditions = re.findall(r'"condition"\s*:\s*(null|"[^"]*")', text)
        effects = re.findall(r'"effect"\s*:\s*(null|"[^"]*")', text)
        indexed = jsonl_records(ROOT / "docs/evidence/dynamic_chain_index.jsonl")
        stats.update(total_items=len(records), extractable=sum(bool(s and t) for s, t in records), nonempty_condition=sum(x != "null" and len(x) > 2 for x in conditions), nonempty_effect=sum(x != "null" and len(x) > 2 for x in effects), indexed_items=len(indexed), state_layers={layer: text.lower().count(layer) for layer in ("original", "derived", "candidate", "reconstructed")})
        stats["missing_fields"] = [field for field, count in (("condition", stats["nonempty_condition"]), ("effect", stats["nonempty_effect"]), ("type", len(re.findall(r'"type"\s*:', text)))) if count == 0]
    elif kind == "static":
        sources = re.findall(r'"source_index"\s*:\s*\{', text)
        pairs = re.findall(r'\{"target"\s*:\s*"([^"]+)"\s*,\s*"type"\s*:\s*"([^"]+)"\s*,\s*"condition"\s*:\s*"([^"]*)"', text)
        index = load_json(ROOT / "docs/evidence/static_network_index.json") or {}
        stats.update(total_items=len(pairs), extractable=sum(bool(t and typ and condition) for t, typ, condition in pairs), indexed_edges=index.get("total_edges", 0), source_blocks=len(sources), bound_target_type_count=len(re.findall(r"bound_to|目标类型|对象类型", text)), mainline_mark_count=len(re.findall(r"主线|mainline", text, re.I)))
        stats["missing_fields"] = ["bound_target_type", "mainline_level"]
    elif kind == "anchor":
        ids = list(dict.fromkeys(ANCHOR.findall(text)))
        full_ids = list(dict.fromkeys(m.group(0) for m in ANCHOR.finditer(text)))
        categories = Counter(x.split(".", 1)[0].rstrip("0123456789") for x in full_ids)
        index = load_json(ROOT / "docs/evidence/anchor_category_index.json") or {}
        stats.update(total_items=len(full_ids), extractable=len(full_ids), unique_ids=len(full_ids), category_extractable=len(full_ids), category_counts=dict(categories), indexed_anchors=index.get("total_anchors", 0), id_format="prefix+major.minor")
        stats["missing_fields"] = ["anchor_definition", "scene_binding", "text_location"]
    stats["status"] = "complete" if stats["total_items"] and not stats["missing_fields"] and not stats["placeholder_count"] else stats["status"]
    return stats


def analysis_markdown(report: list[dict]) -> str:
    return f'''# 新方案分析与原始资料深度检查\n\n生成时间：`{now()}`\n\n## 一、方案逻辑\n\n数据流为：`08_原始资料/*.txt` 只读进入解析器或派生生成器；解析器按稳定标题、字段、ID 和来源位置切分条目，生成全局索引；规则文件声明消费条件、证据要求、状态和阻断级别；执行任务先加载索引与规则，按依赖顺序选择条目，再把选择结果写入项目消费记录；执行管道读取已验证的消费记录，将数据依次传递给类型、连接、静态网络、动态网络、锚点和正文执行模块，最终把设计、正文位置和验证结果回写项目。\n\n文字数据流：\n\n`原始资料 → 解析器/生成器 → 全局索引 → 规则文件校验 → 项目消费记录 → 执行管道 → 设计/章节/正文 → 结果验证`\n\n依赖顺序是：类型系统先于类型连接；静态网络先于动态网络；动态网络先于锚点网络；所有有效证据最终进入执行正文清单。索引命中、读取或提及都不等于消费，必须经过消费记录和可定位证据。\n\n## 二、组件职责\n\n- **全局索引**：为每条原始资料建立机器可读摘要，提供稳定 ID、名称、类别、字段、来源位置和状态，支持按 ID、名称、类型、关键词和关系查询。\n- **规则文件**：定义何时允许选择、需要哪些字段、怎样绑定设计或正文、证据达到什么等级，以及缺失时 warning 还是 block。\n- **消费记录**：记录项目、任务、索引项、状态、决策影响、设计路径、章节路径、正文位置、时间和来源哈希，形成可复核证据链。\n- **执行管道**：加载并校验这些输入，按依赖顺序调用模块，向下游传递结构化结果，并在正文前后执行阻断和落点检查。\n\n## 三、字段与格式要求\n\n### 索引\n\n- 资料库 JSONL：`entry_id`、`name`、`type`、`key_attributes`、`dependencies`、`source_ref`、`source_sha256`、`line_start`、`line_end`、`status`；可选 `examples`、`conditions`、`placeholder_flags`。\n- 类型 JSON：`type_id/name`、`core_elements`、`reader_expectations`、`style_constraints`、`length_rhythm`、`source_ref`、`source_status`。\n- 类型连接：`connection_id`、`combination_id`、`types`、`conflicts`、`recommended_mechanisms`、`resolutions`、`source_ref`、`status`。\n- 动态链：`chain_id`、`source`、`target`、`type`、`condition`、`effect`、`state_layer`、`validation_status`、`source_ref`。\n- 静态连接：`edge_id`、`source`、`target`、`type`、`bound_target_types`、`mainline_level`、`source_ref`。\n- 锚点：`anchor_id`、`category`、`name/definition`、`format_valid`、`source_ref`。\n\n### 规则\n\n每条规则至少需要 `rule_id`、`name`、`condition`、`action`、`required_fields`、`evidence_requirements`、`blocking_level`、`failure_status`。规则还应声明输入索引、输出记录和验证方式。\n\n### 消费记录\n\n每条记录至少需要 `record_id`、`project_id`、`task_id`、`item_id`、`status`、`used_in_design`、`used_in_chapter`、`decision_statement`、`source_ref`、`confidence`、`consumed_at`、`source_sha256`。不同网络还需分别记录 chain、edge 或 anchor 的绑定对象和正文位置。\n\n## 四、运行方式\n\n1. 管道读取索引，校验 JSON/JSONL、唯一 ID、来源文件、哈希和状态。\n2. 管道读取规则，按任务和当前项目状态选择适用条目；`candidate`、`template`、`pending`、`needs_review` 和 `unconfirmed` 不得约束正文。\n3. 类型模块输出类型约束，连接模块消费类型约束并输出组合裁决；静态模块输出稳定关系，动态模块基于静态关系输出状态变化，锚点模块把动态结果落到场景。\n4. 每个模块输出结构化数据和 `source_trace`，管道在进入下一阶段前写入对应消费记录。\n5. 正文生成前，缺少类型连接记录、主线静态连接、章节动态链、场景锚点或执行清单时按规则触发阻断；正文生成后，缺少正文位置或锚点落点时至少触发 warning，关键链路缺失则 block。\n\n## 五、深检摘要\n\n| 资料 | 总量 | 可提取 | 占位数 | 目标组件缺口 | 状态 |\n|---|---:|---:|---:|---|---|\n{chr(10).join(f"| {x['source']} | {x['total_items']} | {x['extractable']} | {x['placeholder_count']} | {', '.join(x['missing_fields']) or '无'} | {x['status']} |" for x in report)}\n\n可提取率只表示字段或结构可以被扫描器识别，不代表已经通过规则验证或被项目消费。\n'''


def make_plan(stats: list[dict]) -> dict:
    return {"schema_version": "source-completion-plan-1.0", "generated_at": now(), "policy": "原始资料只读；补全先产生派生索引或标记pending，不直接改写事实来源。", "plans": [
        {"source": "资料库.txt", "priority": "P0", "scope": ["核心角色、欲望/目标、冲突、能力、场景、叙事和正文规则板块", "所有缺少dependencies、examples、conditions的索引条目"], "fields": ["entry_id", "name", "type", "dependencies", "examples", "conditions", "source_ref", "placeholder_flags"], "completion_source": "从标题和定义提取；依赖从调用标签/相关条目推导；无法证明的字段标记pending", "acceptance": "每条索引有可定位来源，依赖可解析，pending不进入runtime_usable；采用记录包含任务、决策和正文/设计位置。"},
        {"source": "类型系统.txt", "priority": "P0", "scope": ["模板中的全部类型，当前至少覆盖玄幻、仙侠、科幻、悬疑、言情、都市、历史、军事、游戏、体育、灵异、同人、二次元、耽美、轻小说"], "fields": ["type_name", "core_elements", "reader_expectations", "style_constraints", "length_rhythm", "source_ref", "source_status"], "completion_source": "从类型定义、风格表达和篇幅/节奏段落提取；缺失读者参数不得猜测，标记pending", "acceptance": "每个实际可用类型具有非空核心元素、读者期待和风格约束，并可定位到原文。"},
        {"source": "类型连接.txt", "priority": "P0", "scope": ["全部组合段落和动态组合记录", "当前全局索引为空的组合"], "fields": ["connection_id", "combination_id", "types", "conflicts", "recommended_mechanisms", "resolutions", "source_ref"], "completion_source": "扩展解析键名和结构边界；冲突/机制从同一组合块提取，无法确认的组合标candidate", "acceptance": "全局索引有稳定 ID；采用记录绑定source_connection_ids；拒绝和冲突都有理由；正文前通过阻断校验。"},
        {"source": "动态网络.txt", "priority": "P0", "scope": ["所有 source-target 记录", "condition/effect 为空或仅模板的记录", "original/derived/candidate/reconstructed 混合记录"], "fields": ["chain_id", "source", "target", "type", "condition", "effect", "state_layer", "validation_status", "source_ref"], "completion_source": "原始记录保留original；静态派生标derived并绑定契约；候选和回溯内容分别标candidate/reconstructed", "acceptance": "condition/effect非空才可消费；重复按 source+target+condition+effect+type 去重；章节消费记录含chain_id和置信度。"},
        {"source": "静态网络.txt", "priority": "P1", "scope": ["全部静态边", "缺少故事对象绑定类型的边", "缺少主线级别的边"], "fields": ["edge_id", "source", "target", "type", "bound_target_types", "mainline_level", "source_ref"], "completion_source": "从网络边字段和索引节点类别映射绑定类型；主线级别由主线设计任务显式声明，不能从名称臆测", "acceptance": "每个项目主线至少3条有效边，每条绑定角色/地点/势力/事件及项目对象ID，并写入消费记录。"},
        {"source": "锚点网络.txt", "priority": "P1", "scope": ["全部合法 anchor_id", "ID格式不统一或类别缺失的锚点"], "fields": ["anchor_id", "category", "name", "definition", "source_ref", "format_valid"], "completion_source": "统一为 prefix+major.minor；类别由前缀映射，语义类别从定义块提取，缺失类别标pending", "acceptance": "每个场景至少1个有效锚点，消费记录绑定场景/章节/正文位置，正文后验证落点。"}
    ], "total_planned_scope": sum(len(p["scope"]) for p in []), "global_blockers": ["修复目标文件路径漂移", "实现真实执行管道而非placeholder", "所有消费记录改为逐条记录而非total_records摘要"]}


def main() -> None:
    stats = [raw_stats(name, spec["kind"]) | {"components": component_status(spec["components"])} for name, spec in SOURCES.items()]
    ANALYSIS_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_OUT.write_text(analysis_markdown(stats), encoding="utf-8", newline="\n")
    REPORT_OUT.write_text(json.dumps({"schema_version": "source-depth-check-1.0", "generated_at": now(), "sources": stats, "summary": {"source_count": len(stats), "extractable_rate": {x["source"]: round(x["extractable"] / x["total_items"], 4) if x["total_items"] else 0 for x in stats}}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    plan = make_plan(stats)
    plan["total_planned_scope"] = sum(len(p["scope"]) for p in plan["plans"])
    PLAN_OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    rates = "、".join(f"{x['source']}={x['extractable'] / x['total_items']:.1%}" if x["total_items"] else f"{x['source']}=0.0%" for x in stats)
    print("第一阶段：新方案分析完成，输出文件：" + str(ANALYSIS_OUT))
    print("第二阶段：6 份资料深度检查完成，各资料可提取率：" + rates)
    print("第三阶段：补全计划已生成，待补全条目总数：" + str(plan["total_planned_scope"]))
    print(json.dumps({"analysis": str(ANALYSIS_OUT), "report": str(REPORT_OUT), "plan": str(PLAN_OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()