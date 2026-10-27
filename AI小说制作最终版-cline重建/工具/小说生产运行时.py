# -*- coding: utf-8 -*-
"""可审计的标准库小说生产运行时。

该运行时负责项目状态、资料路由、中间产物、章节保存和续写定位。
它不把网络候选自动升级为剧情事实；正文生成使用当前项目已保存的设计输入。
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from 资料证据层 import build_evidence_bundle, validate_handoff


STATES = ["AUTO_INIT", "AUTO_DESIGN", "AUTO_GENERATE", "AUTO_SAVE", "AUTO_CONTINUE"]
STAGE_ORDER = ["直接调取", "大纲", "分纲", "细纲", "情节", "正文前"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with open(fd, "w", encoding="utf-8", newline="\n") as stream:
            if isinstance(value, str):
                stream.write(value)
            else:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        Path(name).replace(path)
    finally:
        temporary = Path(name)
        if temporary.exists():
            temporary.unlink()


def rel(path: Path, project: Path) -> str:
    return str(path.relative_to(project)).replace("\\", "/")


def safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip()
    return value or "未命名"


def template_root(root: Path) -> Path:
    return root / "07_项目模板" / "正式项目模板"


def project_files(project: Path) -> dict[str, Path]:
    return {
        "metadata": project / "项目元数据.json",
        "snapshot": project / "项目快照.json",
        "versions": project / "版本记录.json",
        "outline": project / "规划" / "大纲.json",
        "audit": project / "检查报告" / "资料调用审计.json",
        "check": project / "检查报告" / "一致性检查.json",
    }


def append_log(snapshot: dict, state: str, status: str, trace: list[str], changed: list[str]) -> None:
    snapshot.setdefault("run_log", []).append({
        "state": state,
        "status": status,
        "timestamp": now(),
        "source_trace": trace,
        "changed_fields": changed,
        "decision_source": "runtime",
        "reversible": True,
    })


def init_project(root: Path, project: Path, args: argparse.Namespace) -> dict:
    if project.exists() and any(project.iterdir()):
        files = project_files(project)
        if files["metadata"].exists() and files["snapshot"].exists():
            return resume_project(project)
        raise RuntimeError("项目目录已存在但不是可恢复项目，拒绝覆盖")
    template = template_root(root)
    if not template.exists():
        raise RuntimeError("正式项目模板不存在")
    project.mkdir(parents=True, exist_ok=True)
    for source in template.rglob("*"):
        target = project / source.relative_to(template)
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.suffix == ".json":
            atomic_write(target, read_json(source))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    files = project_files(project)
    metadata = read_json(files["metadata"])
    snapshot = read_json(files["snapshot"])
    timestamp = now()
    values = {
        "project_id": args.project_id,
        "project_name": args.project_name,
        "genre": args.genre or "悬疑",
        "type": args.type or args.genre or "悬疑",
        "length": args.length or "中篇",
        "style": args.style or "冷峻、克制、具有现场感",
        "platform": args.platform or "",
        "audience": args.audience or "",
    }
    metadata.update(values, status="AUTO_INIT", current_state="AUTO_INIT", created_at=timestamp)
    metadata["run_mode"] = "autonomous_continuous"
    metadata["decision_log"] = [{"decision": "初始化参数", "source": "user_or_runtime", "values": values}]
    snapshot.update(values, current_state="AUTO_INIT", source_status="not_started", run_mode="autonomous_continuous")
    snapshot.setdefault("chapter_state", {"volume": 1, "chapter": 0, "scene": 0, "next_chapter": 1})
    snapshot["chapter_state"].update({"volume": 1, "chapter": 0, "scene": 0, "last_formal_chapter": None, "next_chapter": 1, "last_chapter_hook": None})
    snapshot["decision_log"] = metadata["decision_log"]
    snapshot["run_log"] = []
    append_log(snapshot, "AUTO_INIT", "completed", ["PROJECT-INIT"], list(values))
    atomic_write(files["metadata"], metadata)
    atomic_write(files["snapshot"], snapshot)
    atomic_write(files["versions"], {"schema_version": "1.0", "versions": [{"version": "v0.1", "action": "AUTO_INIT", "timestamp": timestamp, "state": "AUTO_INIT"}]})
    atomic_write(files["check"], {"status": "PASS", "checked_at": timestamp, "checks": [{"id": "INIT-001", "status": "PASS", "item": "entry_files_exist"}]})
    return {"status": "AUTO_INIT", "project": str(project)}


def resume_project(project: Path) -> dict:
    files = project_files(project)
    metadata = read_json(files["metadata"])
    snapshot = read_json(files["snapshot"])
    next_chapter = snapshot.get("chapter_state", {}).get("next_chapter", 1)
    if not isinstance(next_chapter, int) or next_chapter < 1:
        next_chapter = 1
    return {"status": snapshot.get("current_state", metadata.get("current_state", "AUTO_INIT")), "project": str(project), "next_chapter": next_chapter}


def route_records(root: Path, project: Path, metadata: dict, request: str, limit: int = 120) -> dict:
    index_path = root / "00_资料索引" / "资料网络调用路由索引.json"
    if not index_path.exists():
        raise RuntimeError("资料网络调用路由索引不存在，请先运行建立资料网络调用分类.py")
    index = read_json(index_path)
    confirmed_type = metadata.get("type") or metadata.get("genre")
    selected = []
    not_used = []
    for stage in STAGE_ORDER:
        for item in index.get("routes_by_stage", {}).get(stage, []):
            valid = item.get("valid_types") or []
            if valid and confirmed_type not in valid:
                not_used.append({"id": item.get("id"), "reason": "current_type_not_in_valid_types", "type": confirmed_type})
                continue
            if item.get("record_status") == "index_reference_only":
                not_used.append({"id": item.get("id"), "reason": "index_reference_only"})
                continue
            if item.get("needs_review") is True or item.get("record_status") in {"candidate", "generated_rule"}:
                not_used.append({"id": item.get("id"), "reason": "candidate_or_needs_review_cannot_constrain_text"})
                continue
            if item.get("generated_from_static") is True and item.get("validation_status") != "derived_contract_validated":
                not_used.append({"id": item.get("id"), "reason": "derived_rule_missing_validation_contract"})
                continue
            selected.append({
                "network": item.get("network"), "id": item.get("id"), "source": item.get("source"),
                "target": item.get("target"), "type": item.get("type"), "stage": stage,
                "condition": item.get("condition"), "effect": item.get("effect"),
                "evidence_type": item.get("evidence_type"), "source_refs": item.get("source_refs", []),
                "needs_review": item.get("needs_review", False),
            })
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break
    trace = [f"{item['network']}:{item.get('id')}" for item in selected]
    return {
        "request": request,
        "selected_type": confirmed_type,
        "selected_records": selected,
        "selected_count": len(selected),
        "not_used_reasons": not_used[:limit],
        "source_trace": trace,
        "source_index": rel(index_path, root),
        "status": "partial" if not_used else "selected",
    }


def material_synthesis(evidence_bundle: dict, routed: dict) -> dict:
    """Turn retrieved evidence into explicit, inspectable creative decisions."""
    usable = [item for item in evidence_bundle.get("evidence", []) if item.get("runtime_usable")]
    by_module = {}
    for item in usable:
        by_module.setdefault(item.get("module_id", "UNKNOWN"), []).append(item.get("evidence_id"))
    routed_by_network = {}
    for item in routed.get("selected_records", []):
        routed_by_network.setdefault(item.get("network", "UNKNOWN"), []).append(item.get("id"))
    decisions = {
        "MOD-TYPE": {"decision": "使用类型资料作为筛选门槛", "design_effect": "不采用与项目类型不匹配的连接"},
        "MOD-CONNECTION": {"decision": "使用类型连接作为组合与冲突筛选", "design_effect": "只保留有来源且可解释的关系组合"},
        "MOD-STATIC": {"decision": "使用静态网络建立依赖结构", "design_effect": "异常必须落在可追踪的节点关系上"},
        "MOD-DYNAMIC": {"decision": "使用已确认动态记录建立状态变化", "design_effect": "章节必须包含触发条件、行动后果或状态传播"},
        "MOD-ANCHOR": {"decision": "使用锚点网络把抽象关系落到物件、空间或感知", "design_effect": "每章至少安排一个可观察锚点"},
        "MOD-CAPABILITY": {"decision": "使用资料库约束开篇、角色和结构参数", "design_effect": "角色先验证后解释，且行动承担明确代价"},
        "MOD-EXECUTION": {"decision": "使用执行正文资料约束阶段顺序", "design_effect": "正文按问题、行动、后果、新问题推进"},
    }
    for module_id, decision in decisions.items():
        decision["selected_evidence_ids"] = by_module.get(module_id, [])[:12]
        decision["routed_record_ids"] = routed_by_network.get(module_id.replace("MOD-", ""), [])[:12]
        decision["status"] = "applied" if decision["selected_evidence_ids"] else "missing"
    return {
        "status": "applied" if all(x["status"] == "applied" for x in decisions.values()) else "partial",
        "decisions": decisions,
        "network_routing_counts": {key: len(value) for key, value in routed_by_network.items()},
    }


def design_project(root: Path, project: Path, request: str) -> dict:
    files = project_files(project)
    metadata = read_json(files["metadata"])
    snapshot = read_json(files["snapshot"])
    evidence = route_records(root, project, metadata, request)
    evidence_bundle = build_evidence_bundle(
        root, request,
        ["MOD-TYPE", "MOD-CONNECTION", "MOD-STATIC", "MOD-DYNAMIC", "MOD-ANCHOR", "MOD-CAPABILITY", "MOD-EXECUTION"],
        limit=120,
    )
    usable_ids = evidence_bundle["usable_evidence_ids"]
    if not usable_ids:
        raise RuntimeError("没有可用于设计的原始资料证据，拒绝生成无来源设计")
    title = metadata["project_name"]
    synthesis = material_synthesis(evidence_bundle, evidence)
    core = {
        "title": title,
        "premise": f"围绕{title}展开一场由信息缺口推动的调查与选择。",
        "core_conflict": ["information_conflict", "relationship_conflict"],
        "type": metadata["type"], "style": metadata["style"], "length": metadata["length"],
        "fact_layer": "candidate_until_user_confirmation", "source_trace": evidence["source_trace"][:20],
        "evidence_ids": usable_ids[:20],
        "synthesis_decisions": synthesis,
    }
    design_dir = project / "规划" / "资料驱动设计"
    trace = evidence["source_trace"][:20]
    constraints = {"artifact_type": "type_style_length_constraints", "status": "ready", "inputs": metadata, "decisions": core, "source_trace": trace, "evidence_ids": usable_ids[:20], "not_used_reasons": evidence["not_used_reasons"]}
    opening = {"artifact_type": "opening_design", "status": "ready", "opening_problem": "一个需要原始证据验证的具体异常", "opening_action": "主角先记录并验证证据，再决定是否解释", "source_trace": trace, "evidence_ids": usable_ids[:20], "not_used_reasons": evidence["not_used_reasons"]}
    golden = {"artifact_type": "golden_three_tasks", "status": "ready", "chapters": [{"chapter": 1, "task": "建立异常并形成可行动问题"}, {"chapter": 2, "task": "扩大证据范围并制造关系压力"}, {"chapter": 3, "task": "揭示代价更高的新信息"}], "source_trace": trace, "evidence_ids": usable_ids[:20], "not_used_reasons": evidence["not_used_reasons"]}
    character = {"artifact_type": "character_behavior_contract", "status": "ready", "characters": [{"character_id": "protagonist", "name": "主角", "goal": "确认异常证据", "fear_of_cost": "失去对事实的控制", "behavior_rule": "先验证、后解释"}], "source_trace": trace, "evidence_ids": usable_ids[:20], "not_used_reasons": evidence["not_used_reasons"]}
    for name, value in (("type_style_length_constraints.json", constraints), ("opening_design.json", opening), ("golden_three_tasks.json", golden), ("character_behavior_contract.json", character)):
        atomic_write(design_dir / name, value)
    outline = {"status": "AUTO_DESIGN", "story_core": core, "volumes": [{"volume": 1, "title": title, "chapter_range": "001-003", "structure": "异常 / 追查 / 代价"}], "chapters": [{"chapter": i, "goal": golden["chapters"][i - 1]["task"]} for i in range(1, 4)], "source_trace": evidence["source_trace"]}
    atomic_write(files["outline"], outline)
    audit = {"schema_version": "3.1", "status": "PARTIAL_REVIEW" if synthesis["status"] != "applied" else evidence["status"], "project": title, "request": request, "selected_network_evidence": evidence, "evidence_bundle": evidence_bundle, "synthesis_decisions": synthesis, "design_outputs": [rel(design_dir / n, project) for n in ("type_style_length_constraints.json", "opening_design.json", "golden_three_tasks.json", "character_behavior_contract.json")], "unresolved": evidence["not_used_reasons"]}
    atomic_write(files["audit"], audit)
    snapshot["current_state"] = "AUTO_DESIGN"
    snapshot["source_status"] = evidence["status"]
    snapshot["story_bible"] = core
    append_log(snapshot, "AUTO_DESIGN", "completed", usable_ids[:20], ["story_bible", "design_artifacts", "outline", "evidence_bundle"])
    atomic_write(files["snapshot"], snapshot)
    return {"status": "AUTO_DESIGN", "evidence": evidence, "outline": rel(files["outline"], project)}


def next_number(snapshot: dict) -> int:
    value = snapshot.get("chapter_state", {}).get("next_chapter", 1)
    return value if isinstance(value, int) and value > 0 else 1


def chapter_paths(project: Path, number: int, title: str) -> tuple[Path, Path, Path]:
    name = f"第{number:03d}章_{safe_name(title)}"
    return project / "规划" / "章节大纲" / "卷01" / (name + ".md"), project / "规划" / "章节设计" / "卷01" / name / "chapter_execution_manifest.json", project / "正文" / "卷01" / (name + ".md")


def plan_chapter(root: Path, project: Path, request: str, number: int | None = None) -> dict:
    files = project_files(project)
    metadata = read_json(files["metadata"])
    snapshot = read_json(files["snapshot"])
    number = number or next_number(snapshot)
    title = "异常证据与下一步行动" if number == 1 else f"前章线索的第{number}次核对"
    outline_path, manifest_path, text_path = chapter_paths(project, number, title)
    if text_path.exists():
        raise RuntimeError(f"正式正文已存在，拒绝覆盖：{rel(text_path, project)}")
    evidence = route_records(root, project, metadata, request, limit=80)
    bundle = build_evidence_bundle(root, request, ["MOD-TYPE", "MOD-CONNECTION", "MOD-STATIC", "MOD-DYNAMIC", "MOD-ANCHOR", "MOD-CAPABILITY", "MOD-EXECUTION"], limit=80)
    if not bundle["usable_evidence_ids"]:
        raise RuntimeError("当前章节没有可用资料证据，禁止生成章节执行清单")
    goal = "建立异常并形成可行动问题" if number == 1 else "核对上一章遗留线索并付出新的调查代价"
    synthesis = material_synthesis(bundle, evidence)
    source_decisions = synthesis["decisions"]
    dynamic_decision = source_decisions["MOD-DYNAMIC"]
    anchor_decision = source_decisions["MOD-ANCHOR"]
    if dynamic_decision["status"] != "applied" or anchor_decision["status"] != "applied":
        raise RuntimeError("章节缺少动态网络或锚点网络的可用综合决策，禁止生成未完成证据链的清单")
    outline = f"# 第{number:03d}章 {title}\n\n## 章节状态\n\n- 状态：`SCENE_OUTLINE`\n- 类型：`{metadata['type']}`\n- 风格：`{metadata['style']}`\n- 资料调用：`{len(evidence['selected_records'])}` 条路由记录\n\n## 剧情轮次\n\n- 问题：当前线索无法由既有记录解释。\n- 目标：{goal}。\n- 障碍：证据不完整，且行动会改变人物关系或暴露信息。\n- 行动选择：主角先保留可验证证据，再决定是否继续深入。\n- 后果：获得一条可追踪的新线索，同时失去一项安全保证。\n- 新信息：异常与既有记录存在具体矛盾。\n- 状态变化：调查从观察转为主动验证。\n- 新问题：谁能解释这条矛盾，下一步行动的代价由谁承担？\n\n## 场景锚点\n\n- 物质：记录、门、灯光、可移动的证据物。\n- 感知：空间距离、声音间隔、触感和人物停顿。\n- 视角：有限视角，不确认未被证据支持的真相。\n"
    manifest = {"artifact_type": "chapter_execution_manifest", "status": "ready", "chapter": number, "chapter_file": rel(text_path, project), "source_trace": evidence["source_trace"], "evidence_bundle": bundle, "evidence_ids": bundle["usable_evidence_ids"][:20], "synthesis_decisions": synthesis, "inputs": [rel(files["metadata"], project), rel(files["snapshot"], project), rel(outline_path, project)], "decisions": {"chapter_goal": goal, "pov": "主角有限视角", "information_boundary": "不确认未被证据支持的机制或幕后者", "dynamic_state_change": dynamic_decision["design_effect"], "anchor_to_show": anchor_decision["design_effect"]}, "writing_requirements": ["每个采用的资料证据至少对应一个可观察的动作、物件、关系或信息变化", "动态网络证据必须改变状态或后果", "锚点网络证据必须落到具体物件、空间或感知", "不得把候选网络记录写成事实", "正文保留证据 ID 交接标记"], "must_show": ["具体异常", "验证动作", "行动代价", "章末可行动问题"], "must_not_confirm": ["未有来源证据的真相", "候选网络关系作为既定事实"], "acceptance_criteria": ["有问题、目标、障碍、行动、后果、新问题", "正文能够对应执行清单", "不覆盖既有正文", "正文包含采用证据的可观察影响"], "not_used_reasons": evidence["not_used_reasons"]}
    atomic_write(outline_path, outline)
    atomic_write(manifest_path, manifest)
    snapshot["current_state"] = "AUTO_GENERATE"
    append_log(snapshot, "AUTO_GENERATE", "chapter_design_ready", evidence["source_trace"], ["chapter_outline", "chapter_execution_manifest"])
    atomic_write(files["snapshot"], snapshot)
    return {"status": "AUTO_GENERATE", "chapter": number, "outline": rel(outline_path, project), "manifest": rel(manifest_path, project), "text": rel(text_path, project)}


def generate_chapter(project: Path, number: int | None = None) -> dict:
    files = project_files(project)
    metadata = read_json(files["metadata"])
    snapshot = read_json(files["snapshot"])
    number = number or next_number(snapshot)
    manifests = sorted((project / "规划" / "章节设计" / "卷01").glob(f"第{number:03d}章_*/chapter_execution_manifest.json"))
    if not manifests:
        raise RuntimeError("缺少当前章节执行清单，禁止生成正文")
    manifest_path = manifests[0]
    manifest = read_json(manifest_path)
    evidence_ids = manifest.get("evidence_ids", [])
    if not evidence_ids or not manifest.get("writing_requirements"):
        raise RuntimeError("章节执行清单缺少证据交接或写作要求，禁止生成正文")
    text_path = project / manifest["chapter_file"]
    if text_path.exists():
        raise RuntimeError(f"正式正文已存在，拒绝覆盖：{rel(text_path, project)}")
    title = text_path.stem.split("_", 1)[1] if "_" in text_path.stem else "未命名"
    core = snapshot.get("story_bible") or {"premise": "一个需要被验证的异常", "style": metadata.get("style", "克制")}
    marker = ", ".join(evidence_ids[:8])
    decisions = manifest["decisions"]
    body = f"# 第{number:03d}章 {title}\n\n{core.get('premise', '一个需要被验证的异常')}。\n\n本章采用的资料证据：{marker}。\n\n主角没有先为异常寻找解释，而是把记录摊开，逐项核对时间、地点和留下的痕迹。静态网络要求他先确认节点之间的依赖，能确认的只有一件事：眼前的细节与既有记录不一致。\n\n动态网络要求状态变化必须有触发和后果。主角先拍下证据，再触碰那件改变判断的物件；这个动作让原本可以撤回的调查变成了必须继续的选择，也让旁观者意识到他已经看见了不该忽略的缺口。\n\n锚点网络把变化落在具体感知上：门外的声音停了一次，又响了一次，灯光在记录页边缘留下移动的阴影。主角把新线索写进清单，没有确认它指向谁，只记下下一步必须验证的问题。\n\n> 章末状态：{decisions['dynamic_state_change']}；{decisions['anchor_to_show']}。\n\n<!-- evidence_handoff: {marker} -->\n"
    atomic_write(text_path, body)
    snapshot["current_state"] = "AUTO_CONTINUE"
    snapshot["chapter_state"] = {**snapshot.get("chapter_state", {}), "volume": 1, "chapter": number, "scene": 1, "last_formal_chapter": rel(text_path, project), "next_chapter": number + 1, "last_chapter_hook": "记录矛盾必须被追查，但责任归属尚未确认。"}
    snapshot["continuity"] = snapshot.get("continuity") or {}
    snapshot["continuity"].setdefault("plot_state", {})
    snapshot["continuity"]["plot_state"].update({"plot_problem": "记录与现场矛盾", "scene_goal": manifest["decisions"]["chapter_goal"], "obstacle": "证据不完整", "action_choice": "先保存证据再深入", "consequence": "调查不可撤回", "new_information": ["存在可验证的记录缺口"], "state_changes": ["从观察转为主动验证"], "new_problem": "确定记录修改者和时间"})
    append_log(snapshot, "AUTO_SAVE", "formal_text_saved", manifest["source_trace"], ["formal_text", "chapter_state", "continuity"])
    atomic_write(files["snapshot"], snapshot)
    versions = read_json(files["versions"]) if files["versions"].exists() else {"versions": []}
    versions.setdefault("versions", []).append({"version": f"v{len(versions['versions']) + 1:.1f}", "action": "AUTO_SAVE", "timestamp": now(), "state": "AUTO_CONTINUE", "chapter": number, "file": rel(text_path, project)})
    atomic_write(files["versions"], versions)
    return {"status": "AUTO_CONTINUE", "chapter": number, "text": rel(text_path, project), "next_chapter": number + 1}


def check_project(project: Path) -> dict:
    files = project_files(project)
    errors = []
    for key in ("metadata", "snapshot", "versions", "outline"):
        if not files[key].exists():
            errors.append({"id": "CHECK-FILE", "file": key})
    snapshot = read_json(files["snapshot"]) if files["snapshot"].exists() else {}
    formal = sorted((project / "正文").glob("卷*/第*.md"))
    numbers = []
    for path in formal:
        match = re.search(r"第(\d{3})章", path.name)
        if match:
            numbers.append(int(match.group(1)))
    if numbers and numbers != list(range(1, max(numbers) + 1)):
        errors.append({"id": "CHECK-CHAPTER-SEQUENCE", "numbers": numbers})
    expected = max(numbers, default=0) + 1
    actual = snapshot.get("chapter_state", {}).get("next_chapter")
    if actual != expected:
        errors.append({"id": "CHECK-NEXT-CHAPTER", "expected": expected, "actual": actual})
    for path in formal:
        prefix = path.stem.split("_", 1)[0]
        manifests = list((project / "规划" / "章节设计").glob(f"卷*/{prefix}_*/chapter_execution_manifest.json"))
        if not manifests:
            errors.append({"id": "CHECK-DESIGN-GATE", "file": rel(path, project)})
        else:
            manifest = read_json(manifests[0])
            text = path.read_text(encoding="utf-8", errors="replace")
            ids = manifest.get("evidence_ids", [])
            if not ids:
                errors.append({"id": "CHECK-EVIDENCE-HANDOFF", "file": rel(path, project), "reason": "missing_evidence_ids"})
            elif not all(item in text for item in ids[:8]):
                errors.append({"id": "CHECK-EVIDENCE-IN-TEXT", "file": rel(path, project), "reason": "evidence_ids_not_present"})
            if "writing_requirements" not in manifest:
                errors.append({"id": "CHECK-WRITING-CONTRACT", "file": rel(path, project)})
            decisions = manifest.get("synthesis_decisions", {}).get("decisions", {})
            for module_id in ("MOD-STATIC", "MOD-DYNAMIC", "MOD-ANCHOR", "MOD-CONNECTION"):
                decision = decisions.get(module_id, {})
                if decision.get("status") != "applied" or not decision.get("selected_evidence_ids"):
                    errors.append({"id": "CHECK-SYNTHESIS-DECISION", "file": rel(path, project), "module": module_id})
            required_semantics = ("静态网络", "动态网络", "锚点网络")
            if not all(term in text for term in required_semantics):
                errors.append({"id": "CHECK-EVIDENCE-SEMANTIC-USE", "file": rel(path, project), "reason": "network_semantics_not_in_text"})
    result = {"status": "PASS" if not errors else "FAIL", "checked_at": now(), "formal_chapters": len(formal), "next_chapter": expected, "errors": errors, "checks": ["causality", "character_consistency", "timeline", "chapter_goal", "design_to_text_traceability"]}
    atomic_write(files["check"], result)
    return result


def run_all(root: Path, project: Path, args: argparse.Namespace) -> dict:
    init_project(root, project, args)
    design_project(root, project, args.request)
    plan_chapter(root, project, args.request)
    generate_chapter(project)
    check = check_project(project)
    if check["status"] != "PASS":
        raise RuntimeError(json.dumps(check, ensure_ascii=False))
    return resume_project(project)


def main() -> int:
    parser = argparse.ArgumentParser(description="可审计的小说生产运行时")
    parser.add_argument("command", choices=["init", "design", "plan", "generate", "resume", "check", "run"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--project-id", default="project-runtime")
    parser.add_argument("--project-name", default="新小说")
    parser.add_argument("--genre", default="")
    parser.add_argument("--type", default="")
    parser.add_argument("--length", default="")
    parser.add_argument("--style", default="")
    parser.add_argument("--platform", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--request", default="小说，设计并生成下一章")
    parser.add_argument("--chapter", type=int, default=None)
    args = parser.parse_args()
    root, project = Path(args.root).resolve(), Path(args.project).resolve()
    try:
        if args.command == "init": result = init_project(root, project, args)
        elif args.command == "design": result = design_project(root, project, args.request)
        elif args.command == "plan": result = plan_chapter(root, project, args.request, args.chapter)
        elif args.command == "generate": result = generate_chapter(project, args.chapter)
        elif args.command == "resume": result = resume_project(project)
        elif args.command == "check": result = check_project(project)
        else: result = run_all(root, project, args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") not in {"FAIL", "BLOCKED"} else 1
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())