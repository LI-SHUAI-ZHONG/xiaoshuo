"""Translate every registered source item into an explicit creation contract.

The contract is deliberately concrete: a source item gets an interpretation,
an intended creative job, a stage binding, and an observable writing strategy.
It does not claim that every item is already present in prose; prose evidence is
added only by the prose stage after the contract has been used.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = ("剧情创建", "剧情", "大纲", "分纲", "细纲", "场景卡", "正文", "校验")
KIND_DEFAULTS = {
    "资料库": ("剧情创建", "故事结构与写作执行", "把条目意义转成角色选择、冲突后果和可观察细节"),
    "类型系统": ("剧情", "类型机制", "把类型规则转成世界运行限制和付出代价的行动"),
    "类型连接": ("剧情创建", "类型组合决策", "把组合关系转成兼容机制与冲突处理"),
    "动态网络": ("分纲", "因果链", "把状态变化转成事件顺序、触发条件和结果"),
    "静态网络": ("大纲", "世界对象关系", "把稳定关系转成角色、势力、地点或事件的约束"),
    "锚点网络": ("场景卡", "可观察表现", "把抽象状态转成感官、空间、身体或动作细节"),
}

ACTIVATION_CLASSES = {
    "direct_creation": "直接创作",
    "indirect_constraint": "间接约束",
    "candidate_retrieval": "背景候选",
    "deferred_activation": "延迟激活",
}

ROLE_DEFAULTS = {
    "资料库": ("design_inspiration", ("choice", "consequence")),
    "类型系统": ("structural_constraint", ("constraint", "consequence")),
    "类型连接": ("structural_constraint", ("constraint", "conflict")),
    "动态网络": ("scene_constraint", ("trigger", "state_change", "consequence")),
    "静态网络": ("scene_constraint", ("relationship", "constraint")),
    "锚点网络": ("scene_constraint", ("observation", "action", "sensory_detail")),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "；".join(_text(item) for item in value)
    return str(value or "").strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z][a-zA-Z0-9_.-]{2,}", text.lower())


def _meaning(record: dict[str, Any]) -> dict[str, Any]:
    definition = _text(record.get("definition"))
    instruction = _text(record.get("instruction"))
    application = _text(record.get("application"))
    usage_method = record.get("usage_method") if isinstance(record.get("usage_method"), dict) else {}
    method_text = _text(usage_method.get("definition") or usage_method.get("call_condition"))
    method_instructions = usage_method.get("instructions", {}) if isinstance(usage_method, dict) else {}
    if isinstance(method_instructions, dict):
        instruction = instruction or _text(list(method_instructions.values()))
    terms = [_text(item) for item in record.get("interpretation_terms", []) if _text(item)]
    body = "；".join(part for part in (definition, method_text, instruction, application) if part)
    return {
        "source_meaning": definition or method_text or (terms[0] if terms else record.get("name", "")),
        "operational_meaning": instruction or application or "把该资料的约束转成创作中的因果变化",
        "usage_method": usage_method,
        "examples": record.get("examples", []),
        "forbidden_use": _text(record.get("forbidden_use")),
        "semantic_terms": sorted(set(terms + _tokens(body)))[:24],
        "source_semantic_anchor": _semantic_anchor(record),
        "forbidden_shortcut": "不得把资料名称、ID、规则原文或元数据直接写入正文",
    }


def _semantic_anchor(record: dict[str, Any]) -> str:
    """Keep a short, source-derived phrase in the contract for human review."""
    generic = {
        "将条目定义、指令或判定证据转译为场景中的可观察约束、选择、动作与结果。",
        "将资料条目的定义、指令或判定字段转译为可观察的创作约束与结果。",
    }
    specific_terms = [
        _text(item) for item in record.get("interpretation_terms", [])
        if _text(item) and _text(item) not in generic and not _text(item).startswith("场景：执行")
    ]
    candidates = (
        _text(record.get("definition")),
        _text(record.get("instruction")),
        *sorted(specific_terms, key=len, reverse=True),
        _text(record.get("name") or record.get("source_id")),
    )
    value = next((item for item in candidates if item and item not in generic), "")
    value = re.sub(r"\s+", " ", value).strip("；。 ")
    return value[:96]


def _source_conditions(value: Any) -> list[str]:
    """Extract declared source constraints without turning them into approvals."""
    condition_keys = {
        "condition", "conditions", "trigger_condition", "trigger_condition_ids",
        "selection_constraints", "valid_types", "requires", "prerequisites",
        "require_selection", "require_validation",
    }
    values: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in condition_keys and child not in (None, "", [], {}):
                if isinstance(child, bool):
                    values.append(f"{key}: {child}")
                elif isinstance(child, list):
                    values.extend(_text(item) for item in child if _text(item))
                else:
                    text = _text(child)
                    if text:
                        values.append(text)
            values.extend(_source_conditions(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(_source_conditions(child))
    return list(dict.fromkeys(item for item in values if item))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _creative_strategy(record: dict[str, Any], kind: str, action: str) -> dict[str, str]:
    """Turn this record's own semantic anchor into a reviewable draft strategy.

    This is a contract for later scene writing, not invented scene evidence. The
    source anchor prevents a generic default sentence from being counted as a
    quality-ready contract.
    """
    title = _text(record.get("name") or record.get("source_id"))
    anchor = _semantic_anchor(record) or title
    trigger_field = _text(record.get("trigger") or record.get("condition") or record.get("trigger_condition"))
    result_field = _text(record.get("effect") or record.get("observable_result"))
    if kind == "动态网络":
        trigger = f"当动态关系的触发条件“{trigger_field or anchor}”在前置状态中成立时，检查 {title} 的 source→target 传播。"
        observable_action = f"由受影响的故事对象根据“{anchor}”采取一次可记录的选择，使状态沿该关系从 source 推向 target。"
        result = f"读者能看到 target 或相关局势出现“{result_field or anchor}”对应的变化，并留下下一步因果约束。"
        cost = "传播会消耗行动窗口或暴露关系来源，后续对象必须在已改变的状态上重新决策。"
    elif kind == "静态网络":
        trigger = f"当场景需要处理“{anchor}”所描述的稳定关系时，先让关系双方的利益或权限发生可观察碰撞。"
        observable_action = f"由关系中的一方调用、拒绝或重新解释该连接，具体执行“{action}”，而不是解释关系名称。"
        result = f"空间、势力或人物之间的可达性/信任/约束按“{result_field or anchor}”产生可验证改变。"
        cost = "关系被重新确认后，至少一方失去原有权限、资源或安全余量，新的关系边界限制后续行动。"
    elif kind == "锚点网络":
        trigger = f"当视角对象进入“{anchor}”规定的触发条件“{trigger_field or anchor}”时，先呈现一个可感知的异常细节。"
        observable_action = f"让视角内的角色对该细节作出身体、空间或物件层面的动作，落实“{action}”。"
        result = f"该动作留下可回看的感官或空间结果，与“{result_field or anchor}”相符，并改变角色下一次观察。"
        cost = "角色为确认或避开该锚点付出时间、暴露位置或承受身体不适，场景状态因此不可完全复原。"
    elif kind in {"类型系统", "类型连接"}:
        trigger = f"当创作阶段遇到“{anchor}”规定的类型期待或兼容冲突时，明确该机制对当前选择的限制。"
        observable_action = f"让角色、制度或事件执行一次受该机制约束的选择，落实“{action}”，并记录被放弃的替代方案。"
        result = f"冲突或机制在故事对象上产生“{result_field or anchor}”可观察的后果，读者能据此预测下一次约束。"
        cost = "遵守机制会牺牲资源、自由度或短期收益；若违背，则立即增加风险并改变后续类型承诺。"
    else:
        trigger = f"当前置产物出现与“{anchor}”直接相关的具体创作问题时，锁定 {title} 的调用条件“{trigger_field or '满足条目调用条件'}”。"
        observable_action = f"让承担该问题的角色或系统围绕“{anchor}”作出一次具体选择并执行，动作必须体现该语义而非复述资料定义。"
        result = f"通过信息、关系、资源、风险或行为的可观察变化呈现“{result_field or anchor}”，并能改变后续选择。"
        cost = "该选择至少牺牲一项资源、信任、时间、安全或旧状态，代价在下一次行动前保持有效。"
    return {
        "source_specific_trigger": trigger,
        "observable_action": observable_action,
        "observable_result": result,
        "cost_or_change": cost,
        "semantic_anchor": anchor,
        "evidence_location": "对应阶段产物；进入正文时必须定位到 scene_id#paragraphs[index] 并提供段落哈希",
        "quality_rule": "不得只复述资料定义；触发必须进入情境，行动必须由角色或系统执行，结果必须能改变后续选择",
    }


def _binding(record: dict[str, Any]) -> dict[str, Any]:
    kind = _text(record.get("source_kind"))
    title = _text(record.get("name") or record.get("source_id"))
    definition = _text(record.get("definition"))
    instruction = _text(record.get("instruction"))
    body = f"{title} {definition} {instruction}"
    stage, object_name, action = KIND_DEFAULTS.get(kind, KIND_DEFAULTS["资料库"])
    rules = (
        (("主角", "人物", "配角", "角色"), "角色行为与弧光", "让角色在目标、判断、动作和代价中体现该意义"),
        (("冲突", "事件", "任务", "目标", "阻碍"), "剧情冲突", "把它变成一次选择，并明确选择改变了什么状态"),
        (("世界", "地理", "地点", "空间", "规则", "势力"), "世界设定与关系", "把它作为限制行动的环境条件，并通过探索逐步显现"),
        (("伏笔", "悬念", "秘密", "反转", "信息"), "悬念与回收", "安排埋设、误导、触发和揭示后的新问题"),
        (("语言", "对白", "叙述", "描写", "节奏", "情绪"), "正文表达", "转成视角、句式、对白、感官细节或段落节奏"),
        (("场景", "观察", "细节", "动作", "五节点"), "场景节拍", "落实为观察、想法、心理、动作、结果的可追踪回合"),
    )
    for keywords, candidate, candidate_action in rules:
        if any(keyword in body for keyword in keywords):
            object_name, action = candidate, candidate_action
            if stage in {"剧情创建", "剧情"} and candidate in {"正文表达", "场景节拍"}:
                stage = "场景卡"
            break
    all_stages = list(record.get("allowed_stages") or STAGES)
    stages = [item for item in STAGES if item in all_stages]
    if stage not in stages:
        stages.insert(0, stage)
    prerequisites = _source_conditions(record)
    if kind in {"动态网络", "静态网络"}:
        binding_class = "indirect_constraint"
        activation_mode = "前置剧情状态或场景状态匹配后激活"
        targets = ["剧情", "大纲", "分纲", "细纲", "场景卡", "正文"]
    elif kind == "锚点网络":
        binding_class = "direct_creation"
        activation_mode = "场景需要具体感官、空间、身体或动作表现时激活"
        targets = ["场景卡", "正文"]
    elif kind in {"类型系统", "类型连接", "类型系统来源块"}:
        binding_class = "deferred_activation"
        activation_mode = "项目类型选择、风格选择或类型冲突条件匹配后激活"
        targets = ["剧情创建", "剧情", "大纲", "分纲", "校验"]
    else:
        binding_class = "candidate_retrieval"
        activation_mode = "前置产物出现匹配创作问题，或实时检索命中场景需求时激活"
        targets = ["剧情创建", "剧情", "大纲", "分纲", "细纲", "场景卡", "正文"]
    condition = "；".join(prerequisites) or activation_mode
    source_trigger = (
        _text(record.get("trigger"))
        or _text(record.get("condition"))
        or (_text(record.get("anchor_definition")) and _text(record.get("trigger_condition")))
        or "前置产物出现与该资料意义相符的具体问题"
    )
    source_result = (
        _text(record.get("effect"))
        or _text(record.get("observable_result"))
        or _text(record.get("application"))
        or "角色选择或场景状态发生可追踪变化"
    )
    story_binding = {
        "资料库": "把该条目的意义转成项目角色、冲突、世界限制或表达选择，并保留其来源边界。",
        "类型系统": "把该类型机制转成故事中的运行限制、读者预期和必须支付的代价。",
        "类型连接": "把类型之间的兼容点与冲突点转成可执行的组合机制和冲突处理。",
        "动态网络": "把状态变化转成有触发条件、行动顺序和可观察结果的因果链。",
        "静态网络": "把稳定关系转成势力、人物、地点或制度对行动的持续约束。",
        "锚点网络": "把抽象要求转成视角内可感知的空间、身体、感官、动作或物件细节。",
    }.get(kind, "把资料意义转成项目上下文中的可观察选择、限制、动作与结果。")
    return {
        "primary_stage": stage,
        "stages": stages or [stage],
        "creative_object": object_name,
        "creative_action": action,
        "story_binding": story_binding,
        "scene_strategy": "在与项目问题匹配的场景中安排触发条件，先呈现可观察现象，再让角色或系统作出行动，最后留下状态变化。",
        "prose_strategy": "通过当前视角可感知的环境、身体反应、动作、对白或结果体现，不暴露解释词本身。",
        "creative_strategy": _creative_strategy(record, kind, action),
        "planned_scene_scope": "由项目阶段、场景需求和激活条件共同确定，不预设章节或主角。",
        "binding_class": binding_class,
        "binding_class_name": ACTIVATION_CLASSES[binding_class],
        "material_role": ROLE_DEFAULTS.get(kind, ("design_inspiration", ("choice", "consequence")))[0],
        "applicable_stage": stages or [stage],
        "required_writing_dimensions": list(ROLE_DEFAULTS.get(kind, ("design_inspiration", ("choice", "consequence")))[1]),
        # Only source kinds that can become concrete scene material require
        # paragraph-level prose evidence. Type rules remain design-time inputs.
        "prose_evidence_required": bool("正文" in (stages or [stage]) and kind not in {"类型系统", "类型连接", "类型系统来源块"}),
        "deferred_reason": "尚未形成同时满足阶段、场景需求和正文写作维度的证据。",
        "activation_policy": {
            "mode": activation_mode,
            "conditions": [condition],
            "source_declared_conditions": prerequisites,
            "candidate_effect_policy": (
                "候选组合只能作为待验证的创作约束；必须先完成项目选择与场景验证，候选效果不得写成既定世界状态。"
                if kind == "类型连接" and any("candidate" in item.lower() or "候选" in item for item in prerequisites)
                else "不适用"
            ),
            "inference_targets": targets,
            "allow_repeated_inference": True,
            "activation_evidence": ["matched_stage", "matched_project_terms", "creative_need", "activation_reason"],
        },
    }


def _requires_candidate_gate(record: dict[str, Any], prerequisites: list[str]) -> bool:
    """Keep candidate or explicitly gated source objects out of model input."""
    status = _text(record.get("status") or record.get("source_status") or "").lower()
    text = " ".join(prerequisites).lower()
    return status in {"candidate", "pending", "needs_review", "unconfirmed", "quarantined"} or any(
        marker in text for marker in ("require_selection", "require_validation", "候选", "待确认", "未确认")
    )


def build_bindings(
    registry: dict[str, Any], project_config: dict[str, Any],
    activation_prerequisites: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    records = registry.get("records", []) if isinstance(registry, dict) else []
    policy = project_config.get("activation_policy", {}) if isinstance(project_config, dict) else {}
    enabled_classes = set(policy.get("enabled_binding_classes", ACTIVATION_CLASSES))
    bindings = []
    for index, source in enumerate(records, 1):
        meaning = _meaning(source)
        binding = _binding(source)
        audited_conditions = (activation_prerequisites or {}).get(f"TB-{index:05d}", [])
        if audited_conditions:
            policy = binding["activation_policy"]
            declared = list(dict.fromkeys([*policy["source_declared_conditions"], *audited_conditions]))
            policy["source_declared_conditions"] = declared
            policy["conditions"] = ["；".join(declared)]
        if binding["binding_class"] not in enabled_classes:
            binding["activation_policy"]["mode"] = "项目配置暂未启用该绑定类别"
            binding["activation_policy"]["conditions"] = ["项目配置启用该绑定类别后重新检查"]
        gated = _requires_candidate_gate(source, [*_source_conditions(source), *audited_conditions])
        bindings.append({
            "binding_id": f"TB-{index:05d}",
            "source_kind": source.get("source_kind", ""),
            "source_id": source.get("source_id", ""),
            "name": source.get("name", ""),
            "source_ref": source.get("source_ref", ""),
            "definition": source.get("definition", ""),
            "call_condition": source.get("call_condition", ""),
            "usage_method": source.get("usage_method", {}),
            "examples": source.get("examples", []),
            "forbidden_use": source.get("forbidden_use", ""),
            # 创作阶段不要求外部授权；可用性由注册表、来源快照和阶段证据决定。
            "model_input_eligible": not gated,
            "prose_write_allowed": not gated,
            "translation_status": "translated" if meaning["source_meaning"] else "needs_review",
            "semantic_interpretation": meaning,
            "creation_binding": binding,
            "evidence_contract": {
                "design_required": ["stage", "creative_object", "creative_action", "source_ref"],
                "scene_required": ["scene_id", "trigger", "action", "observable_result", "cost_or_change"],
                "prose_required": ["prose_location", "trigger", "action", "observable_result", "paragraph_sha256"],
            },
            "activation_status": "awaiting_stage_evidence",
            "project_context": {
                "project_id": project_config.get("project_id", ""),
                "protagonist": project_config.get("protagonist", {}).get("name", "沈砚"),
            },
        })
    stage_counts = Counter(item["creation_binding"]["primary_stage"] for item in bindings)
    kind_counts = Counter(item["source_kind"] for item in bindings)
    return {
        "schema_version": "source-translation-binding-1.2",
        "generated_at": _now(),
        "scope": "every_registered_source_item",
        "source_count": len(bindings),
        "translated_count": sum(item["translation_status"] == "translated" for item in bindings),
        "binding_count": len(bindings),
        "stage_counts": dict(stage_counts),
        "source_kind_counts": dict(kind_counts),
        "coverage_policy": "每条资料必须完成语义反推和分类；只有满足激活条件并产生阶段或场景证据后，才标记为 activated 或 narrativized。",
        "activation_policy": policy,
        "records": bindings,
    }


def run(project_root: str | Path, registry_path: str | Path, project_config_path: str | Path) -> tuple[dict[str, Any], list[Path]]:
    root = Path(project_root).resolve()
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8-sig"))
    config = json.loads(Path(project_config_path).read_text(encoding="utf-8-sig"))
    prerequisite_path = root / "文档" / "证据" / "严格资料升级" / "资料激活前置条件审计" / "资料激活前置条件清单.jsonl"
    activation_prerequisites = {
        str(row.get("binding_id")): [
            _text(item.get("requirement"))
            for item in row.get("activation_prerequisites", [])
            if item.get("kind") != "source_qualification" and _text(item.get("requirement"))
        ]
        for row in _read_jsonl(prerequisite_path)
    }
    output = build_bindings(registry, config, activation_prerequisites)
    evidence = root / "文档" / "证据"
    target = evidence / "全量资料解释词创作绑定.json"
    summary = evidence / "全量资料解释词创作绑定汇总.json"
    stage_dir = evidence / "创作流程绑定"
    target.parent.mkdir(parents=True, exist_ok=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary.write_text(json.dumps({k: output[k] for k in ("schema_version", "generated_at", "scope", "source_count", "translated_count", "binding_count", "stage_counts", "source_kind_counts", "coverage_policy", "activation_policy")}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [target, summary]
    for stage in STAGES:
        rows = [row for row in output["records"] if stage in row["creation_binding"]["stages"]]
        stage_file = stage_dir / f"{stage}.jsonl"
        stage_file.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        files.append(stage_file)
    output["stage_files"] = {stage: str((stage_dir / f"{stage}.jsonl").relative_to(root)).replace("\\", "/") for stage in STAGES}
    output["stage_record_counts"] = {stage: sum(stage in row["creation_binding"]["stages"] for row in output["records"]) for stage in STAGES}
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, files


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--registry", default="文档/证据/execution_outputs/module_00_source_interpretation_registry.json")
    parser.add_argument("--config", default="配置/project_config.json")
    args = parser.parse_args()
    result, _ = run(args.project_root, Path(args.project_root) / args.registry, Path(args.project_root) / args.config)
    print(json.dumps({"status": "passed", "source_count": result["source_count"], "output": "文档/证据/全量资料解释词创作绑定.json"}, ensure_ascii=False))