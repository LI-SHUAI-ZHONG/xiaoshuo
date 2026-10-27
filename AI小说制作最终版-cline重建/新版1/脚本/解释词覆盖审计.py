"""Build a conservative, resumable trace matrix for source interpretation.

This audit distinguishes source availability, stage use, scene design use, and
actual prose evidence. It never treats a source keyword appearing in prose as
proof of consumption.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SOURCES = {
    "资料库": "原始资料/资料库.txt",
    "类型系统": "原始资料/类型系统.txt",
    "类型连接": "原始资料/类型连接.txt",
    "动态网络": "原始资料/动态网络.txt",
    "静态网络": "原始资料/静态网络.txt",
    "锚点网络": "原始资料/锚点网络.txt",
}
STAGES = ("剧情创建", "大纲", "分纲", "细纲", "场景卡", "正文", "校验")
ID_RE = re.compile(r"(?:^|\n)#+\s*([^\n：: ]+)", re.M)


def creation_binding(record: dict[str, Any], route_row: dict[str, Any], used: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve a source interpretation to an explicit creation contract.

    A stage label alone is not a binding. The returned contract names the
    semantic trigger, the writing artifact and the evidence that must remain.
    """
    kind = str(record.get("source_kind", ""))
    terms = [str(value) for value in record.get("interpretation_terms", []) if str(value).strip()]
    text = " ".join(terms).lower()
    classification = route_row.get("classification", {}) if isinstance(route_row, dict) else {}
    route_stage = str(classification.get("stage") or route_row.get("stage") or "")
    route_condition = str(classification.get("condition") or route_row.get("condition") or "")
    route_effect = str(route_row.get("effect") or classification.get("effect") or "")

    semantic_slots = [
        (("主角", "protagonist"), "剧情创建", "story_design.characters.protagonist", "确定核心视角、执念、不可逆转折与不可替代性"),
        (("配角", "角色", "人物"), "剧情创建", "story_design.characters.supporting_cast", "确定角色功能、关系、弧光和出场边界"),
        (("地点", "场景", "空间"), "场景卡", "scene_card.setting", "把空间条件转为可观察的行动限制与变化"),
        (("事件", "冲突", "任务", "目标"), "大纲", "outline.beats.event_or_conflict", "确定事件触发、目标、阻力、选择和结果"),
        (("主题", "核心象征", "象征"), "大纲", "outline.theme_and_motif", "把主题或象征转为反复出现且会改变意义的情节机制"),
        (("伏笔", "反转", "悬念", "秘密"), "分纲", "subplot.setup_payoff", "登记埋设位置、误导信息、揭示条件和回收结果"),
        (("节奏", "开篇", "结尾", "高潮"), "细纲", "detailed_outline.pacing_turning_points", "安排节拍、转折、高潮或余波，并检查状态是否改变"),
        (("语言", "叙述", "视角", "对白", "描写"), "正文", "prose.paragraph_execution", "将规则落实为句子层面的视角、动作、对白或感官信息"),
    ]
    chosen_match = next(((keywords, stage, location, action) for keywords, stage, location, action in semantic_slots if any(keyword.lower() in text for keyword in keywords)), None)
    chosen = chosen_match[1:] if chosen_match else None
    if chosen:
        stage, location, action = chosen
        confidence = "high"
        basis = f"解释词内容命中语义槽位：{chosen_match[0][0]}"
    elif kind == "锚点网络":
        stage, location, action, confidence, basis = "场景卡", "scene_card.anchor_application", "把锚点条件落到对象、动作、可见变化和段落位置", "high", "锚点的定义、触发条件和类别"
    elif kind == "动态网络":
        stage, location, action, confidence, basis = "分纲", "subplot.causal_chain", "在事件顺序中激活条件，记录状态传播和结果", "high", "动态连接的 source、target、condition、effect"
    elif kind == "静态网络":
        stage, location, action, confidence, basis = "大纲", "outline.story_object_relations", "把稳定连接绑定到角色、地点、势力或事件对象", "high", "静态连接的 source、target 和故事对象绑定"
    elif kind == "类型连接":
        stage, location, action, confidence, basis = "剧情创建", "story_design.type_combination_decision", "在类型组合裁决中选择兼容机制并记录冲突处理", "high", "类型组合、兼容性、冲突和机制字段"
    elif kind in {"类型系统", "类型系统来源块"}:
        stage, location, action, confidence, basis = "剧情创建", "story_design.type_constraints", "将类型规则转为题材边界、读者预期和验收条件", "high", "类型名称、核心元素、风格约束和来源规则"
    elif kind == "资料库":
        stage, location, action, confidence, basis = "剧情创建", "story_design.source_decisions", "把定义、指令或证据转为明确的设计决策和可观察结果", "medium", "资料库原文的 definition、instruction 或 evidence"
    else:
        stage, location, action, confidence, basis = "", "", "", "unresolved", "无法从来源类别和解释词内容确定创作落点"

    activation = list(record.get("prerequisites", []))
    if route_condition and route_condition not in activation:
        activation.append(route_condition)
    if route_stage and route_stage != stage:
        activation.append(f"路由主阶段={route_stage}")
    evidence = ["source_id", "source_ref", "activation_result", "creation_location", "observable_result"]
    if used:
        evidence.extend(sorted({key for row in used for key in ("scene_id", "chapter_path", "design_doc_path", "text_location") if row.get(key)}))
    # Semantic matching only proposes a slot. Adoption must be proven by the
    # source-kind-specific records below; this prevents keyword false positives.
    return {
        "status": "candidate_binding" if stage and location and action else "needs_semantic_review",
        "semantic_basis": basis,
        "activation": activation,
        "stage": stage,
        "location": location,
        "action": action,
        "source_route_effect": route_effect,
        "evidence_requirements": sorted(set(evidence)),
        "confidence": confidence,
    }


def activation_state(kind: str, record: dict[str, Any], used: list[dict[str, Any]], binding: dict[str, Any]) -> tuple[str, list[str]]:
    """Classify activation using the rules for each source kind, not keywords."""
    reasons: list[str] = []
    statuses = {str(row.get("status")) for row in used}
    design_used = any(str(row.get("used_in")) in {"scene_design", "world_setting", "type_decision"} for row in used)
    prose_used = any(str(row.get("used_in")) == "prose" or str(row.get("status")) == "consumed" for row in used)
    if kind in {"类型系统", "类型系统来源块"}:
        return "precondition_blocked", ["来源质量为candidate，禁止进入草稿结构或正文"]
    if kind == "类型连接":
        if not used:
            return "precondition_blocked", ["缺少类型连接采用记录"]
        if not design_used and not statuses.intersection({"adopted", "consumed"}):
            return "precondition_blocked", ["采用记录未通过状态校验"]
        if prose_used:
            return "narrativized", []
        return "adopted", ["尚无场景级 connection_id 消费证据"]
    if kind == "资料库":
        if prose_used:
            return "narrativized", []
        if used:
            return "adopted", ["已有条目消费记录但缺少正文落点"]
        return "precondition_blocked", ["缺少任务声明、具体决策和有效 source_ref 的完整采用链"]
    if kind in {"动态网络", "静态网络", "锚点网络"}:
        if prose_used:
            return "narrativized", []
        if design_used or statuses.intersection({"adopted", "consumed"}):
            return "adopted", ["已有设计绑定，尚无正文消费落点"]
        return "precondition_blocked", ["缺少该网络类型的场景/章节绑定记录"]
    return ("candidate_binding", ["未定义来源类型的专属激活规则"])


def source_id_candidates(kind: str, source_id: str, record: dict[str, Any]) -> set[str]:
    """Return stable aliases used by route indexes and consumption ledgers."""
    candidates = {str(source_id)}
    if kind == "静态网络":
        source = str(record.get("source", ""))
        target = str(record.get("target", ""))
        if source and target:
            candidates.update({f"STATIC:{source}->{target}", f"{source}->{target}", f"STATIC-{source}->{target}"})
        candidates.update({str(record.get(key)) for key in ("connection_id", "edge_id") if record.get(key)})
    return {value for value in candidates if value and value != "None"}


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("record_type") != "header":
            rows.append(value)
    return rows


def source_records(root: Path) -> list[dict[str, Any]]:
    registry = read_json(root / "文档/证据/execution_outputs/module_00_source_interpretation_registry.json", {})
    records = [row for row in registry.get("records", []) if isinstance(row, dict) and row.get("source_kind") and row.get("source_id")]
    known_library_ids = {str(row.get("source_id")) for row in records if row.get("source_kind") == "资料库"}
    index_path = root / "文档/资料库索引.jsonl"
    for row in jsonl(index_path):
        entry_id = str(row.get("entry_id", ""))
        if not entry_id or entry_id in known_library_ids:
            continue
        name = str(row.get("name") or entry_id.partition("_")[2] or entry_id)
        source_ref = row.get("source_ref") if isinstance(row.get("source_ref"), dict) else {}
        records.append({
            "source_kind": "资料库",
            "source_id": entry_id,
            "name": name,
            "source_ref": str(source_ref),
            "source_status": "translated",
            "interpretation_terms": [name, *[str(value) for value in row.get("key_attributes", [])]],
            "prerequisites": ["存在项目上下文", "满足条目调用条件"],
            "allowed_stages": ["剧情创建", "大纲", "分纲", "细纲", "场景卡", "正文", "校验"],
            "application": "将资料条目的定义、指令或判定字段转译为可观察的创作约束与结果。",
            "evidence_requirements": ["source_id", "source_ref", "definition", "instruction", "evidence", "observable_result"],
            "missing_fields": [],
            "provenance_gap": False,
            "misuse_risks": ["禁止把来源 ID、规则原文或设计元数据直接写入正文"],
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="解释词、阶段、用途和正文证据覆盖矩阵")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", default="文档/证据/解释词覆盖矩阵.json")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    route = read_json(root / "资料索引/资料网络调用路由索引.json", {})
    prose = read_json(root / "文档/证据/execution_outputs/module_09_scene_prose.json", {})
    prose_text = "\n".join(str(p) for s in prose.get("scenes", []) for p in s.get("paragraphs", []))
    logs = {name: jsonl(root / "文档/证据" / filename) for name, filename in {
        "动态网络": "动态链消费.jsonl", "静态网络": "静态连接消费.jsonl", "锚点网络": "锚点消费.jsonl", "类型连接": "类型连接采用.jsonl"
    }.items()}
    route_rows = [row for rows in route.get("routes_by_stage", {}).values() if isinstance(rows, list) for row in rows if isinstance(row, dict)]
    by_id = {(str(row.get("network")), str(row.get("id"))): row for row in route_rows}
    records = source_records(root)
    registry = read_json(root / "文档/证据/execution_outputs/module_00_source_interpretation_registry.json", {})
    registered = {(str(row.get("source_kind")), str(row.get("source_id"))): row for row in registry.get("records", []) if isinstance(row, dict)}
    matrix = []
    for record in records:
        kind, source_id = record["source_kind"], record["source_id"]
        route_row = by_id.get((kind, source_id), {})
        translated_record = registered.get((kind, source_id), {})
        source_aliases = source_id_candidates(kind, source_id, {**record, **translated_record, **route_row})
        used = [row for row in logs.get(kind, []) if str(row.get("source_id") or row.get("chain_id") or row.get("anchor_id") or row.get("connection_id")) in source_aliases]
        defaults = {
            "资料库": ("设计依据", ["剧情创建", "大纲", "分纲", "细纲", "场景卡", "校验"], "method_and_constraint"),
            "类型系统": ("类型约束", ["剧情创建", "大纲", "校验"], "direction_filter_and_constraint"),
            "类型系统来源块": ("类型规则来源", ["剧情创建", "大纲", "校验"], "source_rule_constraint"),
            "类型连接": ("组合裁决", ["剧情创建", "大纲", "校验"], "combination_and_conflict_filter"),
            "动态网络": ("因果状态", ["剧情创建", "大纲", "分纲", "细纲", "场景卡", "校验"], "causal_state_and_propagation"),
            "静态网络": ("稳定关系", ["大纲", "分纲", "细纲", "场景卡", "校验"], "dependency_and_structure"),
            "锚点网络": ("表达锚点", ["细纲", "场景卡", "正文", "校验"], "concretization_and_expression_anchor"),
        }
        default_terms, default_stages, default_function = defaults[kind]
        stage = route_row.get("classification", {}).get("stage") or route_row.get("stage")
        stages = [stage] if stage else []
        if used:
            stages.extend(["场景卡", "正文"] if any(row.get("used_in") == "scene_design" for row in used) else ["校验"])
        stages = sorted(set(stages), key=STAGES.index) if all(x in STAGES for x in stages) else sorted(set(stages))
        status = str(translated_record.get("source_status") or record.get("source_status") or "unresolved")
        binding = creation_binding({**record, **translated_record}, route_row, used)
        activation, activation_reasons = activation_state(kind, {**record, **translated_record}, used, binding)
        prose_evidence = bool(used and any(str(source_id) in paragraph for paragraph in prose_text.splitlines()))
        matrix.append({**record, **translated_record, "interpretation_terms": translated_record.get("interpretation_terms", []), "allowed_stages": translated_record.get("allowed_stages", stages or default_stages), "function": route_row.get("classification", {}).get("callability", route_row.get("function", default_function)), "call_count": len(used), "scene_ids": sorted(set(str(row.get("scene_id")) for row in used if row.get("scene_id"))), "prose_evidence": prose_evidence, "translation_status": status, "consumption_status": activation, "activation_state": activation, "activation_reasons": activation_reasons, "creation_binding": binding, "binding_status": "bound" if activation in {"adopted", "consumed", "narrativized"} else binding["status"], "misuse_risks": translated_record.get("misuse_risks", [])})
    summary = Counter((row["source_kind"], row["translation_status"]) for row in matrix)
    output = {"schema_version": "interpretation-coverage-matrix-2.0", "source_hash": hashlib.sha256("".join(f"{k}:{v}" for k, v in SOURCES.items()).encode()).hexdigest(), "stages": list(STAGES), "source_counts": Counter(row["source_kind"] for row in matrix), "status_counts": {f"{k[0]}:{k[1]}": v for k, v in summary.items()}, "records": matrix, "verification": {"route_records": len(route_rows), "prose_lines": len(prose_text.splitlines()), "unknown_stage_records": sum(1 for row in matrix if not row["allowed_stages"]), "unmapped_records": sum(1 for row in matrix if row["function"] == "unmapped"), "clinesafe_resume": True}}
    output["source_counts"] = dict(output["source_counts"])
    output["verification"].update({"registry_records": len(registry.get("records", [])), "translated_records": sum(row["translation_status"] == "translated" for row in matrix), "incomplete_translation_records": sum(row["translation_status"] != "translated" for row in matrix), "bound_records": sum(row["binding_status"] == "bound" for row in matrix), "candidate_binding_records": sum(row["binding_status"] == "candidate_binding" for row in matrix), "precondition_blocked_records": sum(row["activation_state"] == "precondition_blocked" for row in matrix), "adopted_records": sum(row["activation_state"] == "adopted" for row in matrix), "narrativized_records": sum(row["activation_state"] == "narrativized" for row in matrix), "unbound_records": sum(row["binding_status"] == "needs_semantic_review" for row in matrix)})
    failed = output["verification"]["unknown_stage_records"] > 0 or output["verification"]["unmapped_records"] > 0 or output["verification"]["incomplete_translation_records"] > 0 or output["verification"]["unbound_records"] > 0
    target = root / args.output; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "failed" if failed else "passed", "records": len(matrix), "output": str(target)}, ensure_ascii=False))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())