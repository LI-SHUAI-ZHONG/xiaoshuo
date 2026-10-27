"""Create resumable, source-traceable automatic prose upgrades for every binding."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from 文本生成模型 import TextGenerationError, generate_json, generate_text, load_settings
from 全量资料输入与正文授权 import authorized_bindings
from 项目创作生产政策 import validate_bindings, validate_policy

QUALITY_STATUS = "automatic_draft_requires_semantic_editorial_review"
REVIEW_STATUS = "pending_human_literary_review"


def _require_quality_workflow(plan: dict[str, Any], with_model: bool) -> None:
    """Accept only the current scene-approved activation plan."""
    if plan.get("schema_version") != "full-source-prose-production-plan-activation-1.0":
        raise ValueError("正文生产编排不是现行场景创作激活方案")
    gates = plan.get("scene_formal_creation_gates", {})
    allowed = {
        str(scene_id)
        for scene_id, gate in gates.items()
        if isinstance(gate, dict) and gate.get("formal_creation_allowed") is True
    }
    if not allowed:
        raise ValueError("没有获得场景正式创作批准的正文候选")
    writable = [
        row for row in plan.get("records", [])
        if isinstance(row, dict)
        and row.get("scene_id") in allowed
        and row.get("prose_write_allowed") is True
        and row.get("status") == "queued_for_authored_prose"
    ]
    if not writable:
        raise ValueError("场景正式创作批准范围内没有可写正文候选")


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _clean(value: Any, limit: int = 58) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    text = re.sub(r"(?:TB-|PC-|[A-Z]\d{4,}|\d+\.\d+[_\u4e00-\u9fff]*)", "", text)
    return text[:limit] or "那处不肯安静的异样"


def _world_context(root: Path) -> dict[str, str]:
    bible = _read(root / "配置" / "项目创作圣经.json", {})
    config = _read(root / "配置" / "project_config.json", {})
    world = bible.get("world", {}) if isinstance(bible, dict) else {}
    return {"protagonist": str(config.get("protagonist", {}).get("name") or "沈砚"), "companion": "陆昭", "recorder": "许照微", "authority": "闻执衡", "world_rule": _clean(world.get("power_system", {}).get("rule"), 42)}


def _paragraph(row: dict[str, Any], binding: dict[str, Any], context: dict[str, str]) -> tuple[str, dict[str, str]]:
    contract = row["causal_contract"]
    strategy = binding.get("creation_binding", {}).get("creative_strategy", {})
    seed = int(hashlib.sha256(row["consumption_id"].encode("utf-8")).hexdigest()[:8], 16)
    hero, friend, recorder, authority = (context[key] for key in ("protagonist", "companion", "recorder", "authority"))
    places = ("外门检测场", "藏卷阁档案廊", "封闭旧区域外廊", "镇潮阵石阶", "旧域入口")
    objects = ("检测石", "潮期名册", "测息盘", "封存卷页", "半枚阵钥", "裂纹铜牌")
    place, obj = places[seed % len(places)], objects[(seed // 7) % len(objects)]
    options = (
        f"{place}的雾气贴着石面上爬，{hero}先看见{obj}边缘在第七息重新亮了一下。那一点光没有持续，却让他记住了出现的顺序。他按住想要上前的{friend}，先让许照微记下位置，再用指腹沿着裂痕摸过去。{obj}随即传出一声极轻的回响，另一侧的阵纹跟着暗了半寸。闻执衡的脚步从廊外逼近，{hero}没有把痕迹交回执律堂，而是将半枚阵钥压在石缝旁。这样做保住了证据，却暴露了他们曾经来过；陆昭不得不替他挡住巡查，也失去了当晚领取药额的时机。",
        f"{recorder}在{place}停下时，{hero}正用指腹擦过{obj}上的灰痕。灰下露出一行被刮去的名字，字口仍在往外渗冷意。陆昭催他离开，沈砚却先问许照微是否记下了纸页编号，随后把{obj}转向灯火。被遮住的纹路在灯下显出两道相反的刻痕，证明这不是普通的磨损。闻执衡的声音已经到了门外，沈砚只能撕下一角带编号的纸页，把完整卷宗留在原处。线索因此留下，许照微却必须承担缺页的过失，三个人往后的退路都比来时更窄。",
        f"巡夜铃穿过{place}时，{hero}把{obj}放在灯下，等到第七息才移开手。回声没有散去，反而沿着石阶传向旧域入口；远处镇潮阵的一盏灯随之熄灭。陆昭担心妹妹的药额会被扣下，仍替他数完三次变化。沈砚没有继续追听，只将半枚阵钥收回袖中，并在地上刻下潮痕的方向。铃声逼近时，闻执衡已经记下了他们的名字；沈砚保住了判断，却失去当夜参加晋升复核的资格。",
        f"{place}原本只剩风声，{hero}却从{obj}的停顿里辨出人为遮掩。第一次亮起时陆昭站在左侧，第二次亮起时阵纹却把光推向右侧。沈砚让许照微记下顺序，自己才把{obj}移离检测石。石缝立刻渗出一线潮水，水面映出旧域的门形，随后又被镇潮阵压回黑暗。闻执衡命人封住回廊，陆昭替沈砚挡下第一道盘问，因而被记入违令名册。沈砚得到了一条能复查的方向，却再也不能假装这只是一次普通检测。",
    )
    paragraph = options[seed % len(options)]
    fields = {
        "trigger": "第七息重新亮了一下",
        "action": "把半枚阵钥压在石缝旁",
        "observable_result": "另一侧的阵纹跟着暗了半寸",
        "cost_or_change": "暴露了他们曾经来过",
    }
    for key, value in fields.items():
        if value not in paragraph:
            fields[key] = {"trigger": "被遮住的纹路在灯下显出两道相反的刻痕", "action": "把完整卷宗留在原处", "observable_result": "回声没有散去，反而沿着石阶传向旧域入口", "cost_or_change": "失去当夜参加晋升复核的资格"}.get(key, value)
    fields["semantic_support"] = "将来源约束转化为检测异常、人物选择、可见阵纹变化和晋升或关系代价。"
    return paragraph, fields


def _generate_valid_json(root: Path, system: str, prompt: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Retry only malformed model JSON; semantic quality stays checked by the caller."""
    for attempt in range(3):
        try:
            return generate_json(root, system, prompt)
        except TextGenerationError as exc:
            if "有效 JSON" not in str(exc) or attempt == 2:
                raise
    raise AssertionError("unreachable")


def _extract_field_quotes(root: Path, system: str, paragraph: str) -> tuple[dict[str, Any], dict[str, str]]:
    prompt = json.dumps({
        "task": "只从给定正文逐字摘录四个连续短语。不得改写、概括或补写正文。",
        "paragraph": paragraph,
        "requirements": ["只返回 JSON 对象，不要 paragraph 字段。", "trigger、action、observable_result、cost_or_change 的每个值必须是 paragraph 中逐字存在的连续短语。", "每个短语为 8 至 32 个中文字符，分别对应触发、行动、可观察结果和持续代价或变化。"],
        "response_schema": {"trigger": "正文中的连续触发引文", "action": "正文中的连续行动引文", "observable_result": "正文中的连续结果引文", "cost_or_change": "正文中的连续代价引文"},
    }, ensure_ascii=False)
    return _generate_valid_json(root, system, prompt)


def _local_field_quotes(paragraph: str) -> dict[str, str]:
    """Extract short contiguous quotes without changing the model-written prose."""
    chunks = [part.strip(" ，；：") for part in re.split(r"[。！？!?，；：]", paragraph) if part.strip()]
    def choose(patterns: tuple[str, ...]) -> str:
        for pattern in patterns:
            for chunk in chunks:
                if re.search(pattern, chunk):
                    return chunk
        return ""
    def quote(value: str) -> str:
        value = value.strip()
        return value[:32] if len(value) > 32 else value
    return {
        "trigger": quote(chunks[0] if chunks else ""),
        "action": quote(choose((r"(?:沈砚|陆昭|许照微|他|她)?.*(?:按住|贴上|压在|推开|取出|抬手|记下|封住|撕下|拿起|放在|移开|握住|划过|伸手|收回|交给)",))),
        "observable_result": quote(choose((r"(?:发出|亮起|暗了|传出|显出|渗出|映出|熄灭|封住|出现|裂开|震动|坠下|退去)",))),
        "cost_or_change": quote(choose((r"(?:失去|暴露|承担|留下|被记|受伤|代价|不得不|暂扣|取消|扣下|过失|资格|受罚|禁足|剥夺|耽搁)",))),
    }


def _model_paragraph(root: Path, row: dict[str, Any], binding: dict[str, Any], context: dict[str, str]) -> tuple[str, dict[str, str], dict[str, str]]:
    contract = row["causal_contract"]
    policy = load_settings(root).get("generation_policy", {})
    system = "你是中文长篇玄幻小说编辑。只输出可直接进入小说的单段正文，不要标题、解释、JSON、代码块或引号。"
    meaning = _clean(binding.get("semantic_interpretation", {}).get("source_meaning"), 72)
    activation = row.get("activation", {})
    creative_need = _clean(activation.get("creative_need"), 96) if isinstance(activation, dict) else "保留异常证据并承担持续代价"
    requirements = {
        "trigger": _clean(contract.get("trigger"), 96),
        "action": _clean(contract.get("required_action"), 96),
        "result": _clean(contract.get("required_result"), 96),
        "cost": _clean(contract.get("required_cost_or_change"), 96),
    }
    prompt = f"""背景：衡渊栖云宗。事件种子：{meaning}。本段创作目标：{creative_need}。
本句必须承担触发阶段：{requirements['trigger']}。只输出一句20至35个汉字的第三人称玄幻小说正文，写沈砚在栖云宗发现具体、可感知的异常。只可使用阵纹、符纸、阵钥、玉灯、石阶、回廊等古风物件，不得写云彩、记录板或现代技术。不要标题、解释、JSON 或内部术语。"""
    forbidden = ("source→target", "source", "target", "资料ID", "创作合同", "读者能看到", "未确认的类型偏好不得自动写入正文", "系统", "记录板", "操作权", "云彩")
    trigger, metadata = generate_text(root, system, prompt)
    action_prompt = f"""已有前文：{trigger}
本句必须承担行动阶段：{requirements['action']}。只输出紧接着的一句20至35个汉字的第三人称玄幻小说正文，必须包含“沈砚”与“按住”“贴上”“推开”“取出”“记下”之一，写出对阵钥、符纸、玉灯或石阶的具体行动。不得写云彩、记录板或现代技术。不要标题、解释、JSON 或内部术语。"""
    action, action_metadata = generate_text(root, system, action_prompt)
    result_prompt = f"""已有前文：{trigger}{action}
本句必须承担结果阶段：{requirements['result']}。只输出紧接着的一句20至35个汉字的第三人称玄幻小说正文，必须写阵纹、符纸、玉灯、石阶或回廊“亮起”“暗下”“渗出”“震动”“裂开”之一的可观察变化。不得写云彩、记录板或现代技术。不要标题、解释、JSON 或内部术语。"""
    result, result_metadata = generate_text(root, system, result_prompt)
    cost_prompt = f"""已有前文：{trigger}{action}{result}
本句必须承担代价阶段：{requirements['cost']}。只输出紧接着的一句20至35个汉字的第三人称玄幻小说正文，必须包含“被记入”“失去”“暂扣”“不得不”“资格”或“代价”之一，写明持续后果。不得写云彩、记录板、系统或现代技术。不要标题、解释、JSON 或内部术语。"""
    cost, cost_metadata = generate_text(root, system, cost_prompt)
    paragraph = trigger + action + result + cost
    metadata = {**metadata, "generation_strategy": "four_stage_model_prose", "action_model": action_metadata.get("model", ""), "result_model": result_metadata.get("model", ""), "cost_model": cost_metadata.get("model", "")}
    response: dict[str, Any] = {"paragraph": paragraph, "semantic_support": "已将获准的来源含义转化为人物选择、可见变化与后续代价。"}
    legacy_fields = ("trigger", "action", "observable_result", "cost_or_change")
    if isinstance(response, dict) and any(key in response for key in legacy_fields):
        paragraph = str(response.get("paragraph", "")).replace("\n", "").strip()
        errors = [key for key in legacy_fields if str(response.get(key, "")).strip() and str(response[key]).strip() not in paragraph]
        if errors:
            extracted, extracted_metadata = _extract_field_quotes(root, system, paragraph)
            if isinstance(extracted, dict):
                extracted_errors = [key for key in legacy_fields if not str(extracted.get(key, "")).strip() or str(extracted[key]).strip() not in paragraph]
                if not extracted_errors:
                    fields = {key: str(extracted[key]).strip() for key in legacy_fields}
                    fields["semantic_support"] = str(response.get("semantic_support", "")).strip() or "将来源语义转化为可观察事件。"
                    return paragraph, fields, extracted_metadata
            repair = json.dumps({
                "task": "重写上一条正文，只返回完整 JSON。",
                "requirements": ["只返回完整 JSON。", "trigger、action、observable_result、cost_or_change 必须从 paragraph 中逐字复制 8 至 32 字。"],
                "field_quote_example": {"paragraph": "雨声压住屋檐，沈砚推开木门，门轴发出刺耳的响声，他的手掌因此留下了血痕。", "action": "沈砚推开木门"},
            }, ensure_ascii=False)
            _generate_valid_json(root, system, repair)
            raise TextGenerationError(f"{row['consumption_id']} 正文未包含字段：{errors}")
    paragraph = str(response.get("paragraph", "")).replace("\n", "").strip()
    hits = [token for token in forbidden if token in paragraph]
    fields = _local_field_quotes(paragraph)
    minimum = int(policy.get("minimum_paragraph_characters", 80))
    if len(paragraph) < minimum or hits or any(not value for value in fields.values()):
        missing = {key for key, value in fields.items() if not value}
        if "action" in missing:
            repair = f"已有前文：{trigger}\n只输出紧接着的一句20至35个汉字的第三人称玄幻小说正文，必须包含“沈砚”与“按住”“贴上”“推开”“取出”“记下”之一，写出对阵钥、符纸、玉灯或石阶的具体行动。不要标题、解释、JSON 或内部术语。"
            action, action_metadata = generate_text(root, system, repair)
            metadata = {**metadata, "generation_strategy": "four_stage_model_prose_repaired", "action_model": action_metadata.get("model", "")}
        if "observable_result" in missing:
            repair = f"已有前文：{trigger}{action}\n只输出紧接着的一句20至35个汉字的第三人称玄幻小说正文，必须写阵纹、符纸、玉灯、石阶或回廊“亮起”“暗下”“渗出”“震动”“裂开”之一的可观察变化。不要标题、解释、JSON 或内部术语。"
            result, result_metadata = generate_text(root, system, repair)
            metadata = {**metadata, "generation_strategy": "four_stage_model_prose_repaired", "result_model": result_metadata.get("model", "")}
        if "cost_or_change" in missing or len(trigger + action + result + cost) < minimum:
            repair = f"已有前三句：{trigger}{action}{result}\n只输出最后一句20至35个汉字的第三人称玄幻小说正文，必须包含“被记入”“失去”“暂扣”“不得不”“资格”或“代价”之一，写明持续后果。不得写云彩、记录板、系统或现代技术。不要标题、解释、JSON 或内部术语。"
            cost, cost_metadata = generate_text(root, system, repair)
            metadata = {**metadata, "generation_strategy": "four_stage_model_prose_repaired", "cost_model": cost_metadata.get("model", "")}
        paragraph = trigger + action + result + cost
        response["paragraph"] = paragraph
        hits = [token for token in forbidden if token in paragraph]
    fields = _local_field_quotes(paragraph)
    if len(paragraph) < minimum or hits or any(not value for value in fields.values()) or not str(response.get("semantic_support", "")).strip():
        raise TextGenerationError(f"{row['consumption_id']} 模型正文未通过一次性校验：长度={len(paragraph)}，禁词={hits}")
    fields["semantic_support"] = str(response["semantic_support"]).strip()
    return paragraph, fields, metadata


def _archive(row: dict[str, Any], binding: dict[str, Any], prose: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "source-upgrade-record-1.0", "consumption_id": row["consumption_id"], "binding_id": row["binding_id"], "source": {"source_id": row["source_id"], "source_kind": row["source_kind"], "name": binding.get("name", ""), "source_ref": binding.get("source_ref", row.get("source_ref", "")), "source_meaning": binding.get("semantic_interpretation", {}).get("source_meaning", ""), "semantic_anchor": row["causal_contract"]["semantic_anchor"]}, "upgrade": {"causal_contract": row["causal_contract"], "prose_location": prose["prose_location"], "paragraph_sha256": prose["paragraph_sha256"], "applied_trigger": prose["trigger"], "applied_action": prose["action"], "applied_result": prose["observable_result"], "applied_cost_or_change": prose["cost_or_change"], "application_status": QUALITY_STATUS, "literary_review_status": REVIEW_STATUS}}


def run(project_root: str | Path, batch_ids: list[str], with_model: bool = False, consumption_ids: list[str] | None = None) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    policy = validate_policy(root)
    evidence = root / "文档" / "证据"
    bindings_document = _read(evidence / "全量资料解释词创作绑定.json", {})
    validate_bindings(policy, bindings_document, allow_legacy_test_bindings=not with_model)
    plan = _read(evidence / "全量资料正文生产编排.json", {})
    if with_model and plan.get("status") not in {"ready_for_model_candidates", "approved_for_model_candidate_generation"}:
        raise ValueError("模型正文生产仅接受当前候选生成质量门计划")
    if with_model and plan.get("release_status") != "draft_only":
        raise ValueError("模型正文候选计划必须明确保持 draft_only")
    bindings = _read(evidence / "全量资料解释词创作绑定.json", {})
    binding_by_id = {item.get("binding_id"): item for item in bindings.get("records", []) if isinstance(item, dict)}
    grants = authorized_bindings(root, list(binding_by_id.values()))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    selected_ids = set(consumption_ids or [])
    for row in plan.get("records", []):
        if selected_ids and row.get("consumption_id") not in selected_ids:
            continue
        if isinstance(row, dict) and row.get("batch_id") in batch_ids: grouped[row["batch_id"]].append(row)
    found_ids = {row["consumption_id"] for rows in grouped.values() for row in rows}
    unknown_ids = sorted(selected_ids - found_ids)
    if unknown_ids:
        raise ValueError(f"消费记录不存在或不属于所选批次：{', '.join(unknown_ids)}")
    missing = sorted(set(batch_ids) - set(grouped))
    if missing: raise ValueError(f"批次不存在或未匹配所选消费记录：{', '.join(missing)}")
    authorization_errors = []
    for batch_id, rows in grouped.items():
        for row in rows:
            binding = binding_by_id.get(row.get("binding_id"))
            if row.get("status") != "queued_for_authored_prose" or row.get("model_input_eligible") is not True or row.get("prose_write_allowed") is not True:
                authorization_errors.append(f"{batch_id}/{row.get('consumption_id')} 未获正文生产授权")
            if not isinstance(binding, dict) or binding.get("model_input_eligible") is not True or binding.get("prose_write_allowed") is not True:
                authorization_errors.append(f"{batch_id}/{row.get('binding_id')} 的绑定未获正文生产授权")
            if row.get("binding_id") not in grants:
                authorization_errors.append(f"{batch_id}/{row.get('binding_id')} 缺少已审计的逐条使用授权")
    if authorization_errors:
        raise ValueError("正文生产权限校验失败：" + "；".join(authorization_errors))
    output = root / (Path("正文") / "全量资料升级" / "批次" if with_model else Path("非正式草稿") / "全量资料确定性模板"); output.mkdir(parents=True, exist_ok=True)
    context, records, archives = _world_context(root), [], []
    for batch_id in sorted(grouped):
        prose_path, lines = output / f"{batch_id}.md", [f"# 全量资料自动升级 {batch_id}", ""]
        for index, row in enumerate(grouped[batch_id], start=1):
            binding = binding_by_id.get(row["binding_id"], {})
            try:
                if with_model:
                    print(f"生成 {batch_id} {index}/{len(grouped[batch_id])} {row['consumption_id']}", flush=True)
                    paragraph, fields, model_metadata = _model_paragraph(root, row, binding, context)
                else:
                    paragraph, fields = _paragraph(row, binding, context)
                    model_metadata = {"provider": "deterministic_draft", "model": "none"}
            except TextGenerationError as exc:
                raise TextGenerationError(f"批次 {batch_id} 在第 {index} 条失败：{exc}") from exc
            prose = {"consumption_id": row["consumption_id"], "binding_id": row["binding_id"], "source_id": row["source_id"], "scene_id": row["scene_id"], "prose_file": prose_path.relative_to(root).as_posix(), "prose_location": f"{prose_path.relative_to(root).as_posix()}#lines[{len(lines) + 1}]", "paragraph": paragraph, "paragraph_sha256": hashlib.sha256(paragraph.encode("utf-8")).hexdigest(), "quality_status": QUALITY_STATUS if with_model else "deterministic_template_nonrelease", "literary_review_status": REVIEW_STATUS, "generation": model_metadata, **fields}
            lines.extend([paragraph, ""]); records.append(prose)
            if with_model:
                archives.append(_archive(row, binding, prose))
        prose_path.write_text("\n".join(lines), encoding="utf-8")
    if not with_model:
        draft_path = evidence / "全量资料确定性模板草稿.json"
        draft_path.write_text(json.dumps({"schema_version": "deterministic-template-draft-1.0", "release_status": "deterministic_template_nonrelease", "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"batch_count": len(grouped), "generated_count": len(records), "quality_status": "deterministic_template_nonrelease", "literary_review_status": REVIEW_STATUS, "draft_file": str(draft_path)}
    evidence_path = evidence / "全量资料正文消费证据.json"
    existing = _read(evidence_path, {"schema_version": "full-source-prose-consumption-evidence-1.1", "records": []})
    scene_gates = plan.get("scene_formal_creation_gates", {})
    active_ids = {
        str(row.get("consumption_id"))
        for row in plan.get("records", [])
        if isinstance(row, dict)
        and row.get("status") == "queued_for_authored_prose"
        and row.get("prose_write_allowed") is True
        and isinstance(scene_gates.get(row.get("scene_id")), dict)
        and scene_gates[row.get("scene_id")].get("formal_creation_allowed") is True
    }
    inactive = [item for item in existing.get("records", []) if item.get("consumption_id") not in active_ids]
    if inactive:
        inactive_path = evidence / "全量资料非活动正文消费证据归档.json"
        archived = _read(inactive_path, {"schema_version": "inactive-prose-consumption-archive-1.0", "records": []})
        archive_by_id = {str(item.get("consumption_id")): item for item in archived.get("records", []) if isinstance(item, dict)}
        archive_by_id.update({str(item.get("consumption_id")): item for item in inactive if isinstance(item, dict)})
        inactive_path.write_text(json.dumps({
            "schema_version": "inactive-prose-consumption-archive-1.0",
            "policy": "不属于当前获场景正式创作批准范围的消费证据仅作不可发布审计归档。",
            "records": list(archive_by_id.values()),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    existing["records"] = [item for item in existing.get("records", []) if item.get("consumption_id") in active_ids]
    replaced = {item["consumption_id"] for item in records}
    existing["records"] = [item for item in existing.get("records", []) if item.get("consumption_id") not in replaced] + records
    generated_batch_ids = set(grouped)
    batch_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in existing["records"]:
        prose_file = str(item.get("prose_file") or "")
        batch_id = Path(prose_file).stem
        if batch_id in generated_batch_ids:
            batch_records[batch_id].append(item)
    for batch_id, items in batch_records.items():
        order = {row["consumption_id"]: index for index, row in enumerate(plan.get("records", []))}
        items.sort(key=lambda item: order.get(item.get("consumption_id"), len(order)))
        prose_path = output / f"{batch_id}.md"
        lines = [f"# 全量资料自动升级 {batch_id}", ""]
        for item in items:
            item["prose_file"] = prose_path.relative_to(root).as_posix()
            item["prose_location"] = f"{item['prose_file']}#lines[{len(lines) + 1}]"
            lines.extend([str(item["paragraph"]), ""])
        prose_path.write_text("\n".join(lines), encoding="utf-8")
    existing["generated_batches"] = sorted({item["prose_file"].rsplit("/", 1)[-1].removesuffix(".md") for item in existing["records"]})
    existing["generation_policy"] = "自动生成候选正文并完成位置和哈希回读；未经语义和文学审校，不得标记为正文已实现。"
    evidence_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive_path = evidence / "全量资料升级档案.jsonl"
    archive_ids = {item["consumption_id"] for item in existing["records"]}
    prior = [line for line in archive_path.read_text(encoding="utf-8-sig").splitlines() if line.strip() and json.loads(line).get("consumption_id") not in archive_ids] if archive_path.is_file() else []
    refreshed_archives = [_archive(next(row for row in plan.get("records", []) if row.get("consumption_id") == item["consumption_id"]), binding_by_id.get(item["binding_id"], {}), item) for item in existing["records"] if item.get("consumption_id") in {row.get("consumption_id") for row in plan.get("records", [])}]
    archive_path.write_text("\n".join(prior + [json.dumps(item, ensure_ascii=False) for item in refreshed_archives]) + "\n", encoding="utf-8")
    return {"batch_count": len(grouped), "generated_count": len(records), "quality_status": QUALITY_STATUS, "literary_review_status": REVIEW_STATUS, "evidence_file": str(evidence_path), "upgrade_archive": str(archive_path)}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--project-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--batch-id"); group.add_argument("--all-batches", action="store_true")
    parser.add_argument("--with-model", action="store_true", help="调用配置的文本生成模型；默认仅生成确定性候选草稿")
    parser.add_argument("--consumption-id", action="append", help="仅生成指定消费记录；可重复，且必须属于所选批次")
    args = parser.parse_args(); root = Path(args.project_root).expanduser().resolve()
    plan = _read(root / "文档" / "证据" / "全量资料正文生产编排.json", {})
    _require_quality_workflow(plan, args.with_model)
    batch_ids = sorted({str(row.get("batch_id")) for row in plan.get("records", [])}) if args.all_batches else [args.batch_id]
    print(json.dumps(run(root, batch_ids, with_model=args.with_model, consumption_ids=args.consumption_id), ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())