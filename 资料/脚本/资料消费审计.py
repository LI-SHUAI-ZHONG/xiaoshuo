"""Audit whether indexed source objects reach project prose.

The audit is intentionally conservative: loaded or indexed data is not
treated as consumed until it has a project-scoped scene/prose reference.
"""
from __future__ import annotations

import json
import re
import argparse
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any


LOG_NAMES = {
    "type_connection": "类型连接采用.jsonl",
    "dynamic_chain": "动态链消费.jsonl",
    "static_connection": "静态连接消费.jsonl",
    "anchor": "锚点消费.jsonl",
}

FORMAL_FACT_EVIDENCE_LAYER = "original_source"
NETWORK_CONSUMPTION_KINDS = frozenset({"dynamic_chain", "static_connection", "anchor"})
NETWORK_CONSUMPTION_REQUIRED_FIELDS = (
    "condition", "decision_statement", "used_in", "scene_id", "chapter_id", "source_ref",
)


def _qualification_ledger(root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    path = root / "文档" / "证据" / "资料资格账本.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, ""
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        return {}, ""
    records = {
        str(row.get("binding_id")): row for row in payload["records"]
        if isinstance(row, dict) and row.get("binding_id")
    }
    return records, hashlib.sha256(path.read_bytes()).hexdigest()
MATERIAL_DUTY_STATUSES = frozenset({"design_used", "scene_constraint_used", "prose_used", "deferred"})


def audit_material_duty_records(
    records: list[dict[str, Any]],
    run_id: str = "",
    stage: str = "正文",
) -> dict[str, Any]:
    """Audit explicit material-duty receipts without inferring prose rights."""
    violations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            violations.append({"record_index": index, "reason": "职责回执不是对象"})
            continue
        duty = record.get("material_duty")
        receipt = record.get("duty_receipt")
        if not isinstance(duty, dict):
            violations.append({"record_index": index, "reason": "缺少 material_duty，不能推导资料职责"})
            continue
        status = str(record.get("duty_status") or (receipt.get("status") if isinstance(receipt, dict) else "")).strip()
        identity = record.get("binding_id") or record.get("source_id") or ""
        record_valid = True
        if status not in MATERIAL_DUTY_STATUSES:
            violations.append({"record_index": index, "source_id": identity, "reason": "职责状态必须显式为 design_used、scene_constraint_used、prose_used 或 deferred"})
            continue
        if run_id and str(record.get("run_id") or "") != run_id:
            violations.append({"record_index": index, "source_id": identity, "reason": "职责回执 run_id 与当前运行不一致"})
            record_valid = False
        if stage not in {str(value) for value in duty.get("applicable_stage", [])} and status != "deferred":
            violations.append({"record_index": index, "source_id": identity, "reason": f"职责合同不适用于阶段：{stage}"})
            record_valid = False
        if status == "prose_used":
            if duty.get("prose_evidence_required") is not True:
                violations.append({"record_index": index, "source_id": identity, "reason": "未获得正文职责合同，不得回执 prose_used"})
                record_valid = False
            if not str(record.get("prose_location") or "").strip() or not str(record.get("paragraph_sha256") or "").strip():
                violations.append({"record_index": index, "source_id": identity, "reason": "prose_used 缺少正文位置或段落哈希"})
                record_valid = False
        if status == "deferred" and not str(record.get("deferred_reason") or duty.get("deferred_reason") or "").strip():
            violations.append({"record_index": index, "source_id": identity, "reason": "deferred 职责回执缺少 deferred_reason"})
            record_valid = False
        if record_valid:
            counts[status] += 1
    return {
        "schema_version": "material-duty-receipt-audit-1.0",
        "run_id": run_id,
        "stage": stage,
        "record_count": len(records),
        "status_counts": dict(counts),
        "violations": violations,
        "passed": not violations,
        "prose_used_count": counts.get("prose_used", 0),
        "deferred_count": counts.get("deferred", 0),
    }


def audit_network_consumption_contract(kind: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate explicit, scene-scoped adoption evidence for network objects."""
    violations: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    adopted: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            violations.append({"record_index": index, "reason": "消费记录不是对象"})
            continue
        status = str(record.get("status") or "").strip()
        identity = record.get("chain_id") or record.get("connection_id") or record.get("anchor_id") or ""
        if record.get("fallback_used"):
            missing_fallback_fields = [
                field for field in ("fallback_reason", "original_required_kind")
                if not str(record.get(field) or "").strip()
            ]
            reason = "检测到回退消费；跨源替代默认禁止，必须进入阻断/人工复核清单"
            if missing_fallback_fields:
                reason += "；缺少字段：" + ", ".join(missing_fallback_fields)
            violations.append({"record_index": index, "source_id": identity, "reason": reason})
            continue
        if status == "deferred":
            reason = str(record.get("deferred_reason") or "").strip()
            if not reason:
                violations.append({"record_index": index, "source_id": identity, "reason": "deferred 记录缺少 deferred_reason"})
            else:
                deferred.append({"record_index": index, "source_id": identity, "deferred_reason": reason})
            continue
        if status not in {"adopted", "consumed"}:
            violations.append({"record_index": index, "source_id": identity, "reason": "网络消费状态必须为 adopted、consumed 或 deferred"})
            continue
        missing = [field for field in NETWORK_CONSUMPTION_REQUIRED_FIELDS if not record.get(field)]
        source_ref = record.get("source_ref")
        if source_ref and (not isinstance(source_ref, dict) or not str(source_ref.get("path") or "").strip() or not str(source_ref.get("location") or "").strip()):
            missing.append("source_ref.path/location")
        if missing:
            violations.append({"record_index": index, "source_id": identity, "reason": "采用记录缺少字段：" + ", ".join(dict.fromkeys(missing))})
            continue
        adopted.append({"record_index": index, "source_id": identity, "status": status})
    return {"kind": kind, "candidate_count": len(records), "adopted_or_consumed_count": len(adopted), "deferred_count": len(deferred), "adopted_or_consumed_records": adopted, "deferred_records": deferred, "violations": violations, "passed": not violations}


def audit_formal_fact_evidence(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep source facts separate from generated, configured, or runtime artifacts."""
    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        source_ref = record.get("source_ref") if isinstance(record.get("source_ref"), dict) else {}
        layer = record.get("evidence_layer")
        reference_path = str(source_ref.get("path") or "").replace("\\", "/")
        locator = source_ref.get("location") or source_ref.get("locator")
        reason = ""
        if layer != FORMAL_FACT_EVIDENCE_LAYER:
            reason = "evidence_layer 不是 original_source"
        elif not reference_path.startswith("原始资料/"):
            reason = "original_source 记录未引用原始资料路径"
        elif not locator:
            reason = "original_source 记录缺少可复核定位"
        item = {
            "record_index": index,
            "source_id": record.get("source_id") or record.get("library_entry_id") or "",
            "evidence_layer": layer or "",
            "source_path": reference_path,
            "locator": locator or "",
        }
        if reason:
            item["exclusion_reason"] = reason
            excluded.append(item)
        else:
            accepted.append(item)
    return {
        "policy": "只有 evidence_layer=original_source 且具备原始资料路径和可复核定位的记录可计入正式事实；运行产物、配置、正文和历史记录只能作为派生证据保留。",
        "candidate_count": len(records),
        "counted_original_source": len(accepted),
        "excluded_count": len(excluded),
        "counted_records": accepted,
        "excluded_records": excluded,
        "formal_fact_usable": bool(records) and not excluded,
    }


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("record_type") != "header":
            rows.append(row)
    return rows


def _library_ids(path: Path) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig")
    return re.findall(r"^#+\s*(\d+(?:\.\d+)?)(?:[_：: ]|$)", text, re.M)


def _prose_text(prose: dict[str, Any]) -> str:
    return "\n".join(str(p) for scene in prose.get("scenes", []) for p in scene.get("paragraphs", []))


def _known_ids(root: Path) -> dict[str, set[str]]:
    """Collect runtime IDs so a consumption row cannot cite an invented object."""
    evidence = root / "文档" / "证据"
    result = {"dynamic": set(), "static": set(), "anchor": set(), "library": set()}
    dynamic = _read_json(root / "网络完整数据" / "动态连接完整数据.json", {})
    stack = [dynamic]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key in ("id", "edge_id", "dynamic_edge_id", "chain_id"):
                if value.get(key):
                    result["dynamic"].add(str(value[key]))
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    static = _read_json(root / "网络完整数据" / "静态连接完整数据.json", {})
    stack = [static]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if value.get("source") and value.get("target"):
                result["static"].add(f"STATIC:{value['source']}->{value['target']}")
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    normalized_anchors = _read_json(evidence / "全量资料治理" / "锚点网络_规范化.json", [])
    if isinstance(normalized_anchors, list):
        result["anchor"].update(
            str(row.get("normalized_id")) for row in normalized_anchors
            if isinstance(row, dict) and row.get("normalized_id")
        )
    if not result["anchor"]:
        anchor_text = (root / "原始资料" / "锚点网络.txt").read_text(encoding="utf-8-sig") if (root / "原始资料" / "锚点网络.txt").is_file() else ""
        result["anchor"].update(re.findall(r"\b(?:M|S|P|B|E|C|T|D|A|L|ID|U)\d+\.\d+\b", anchor_text))
    # The runtime library index lives under 文档/, while other evidence indexes
    # live under 文档/证据/. Keep this explicit so indexed library IDs are not
    # silently treated as unknown.
    for row in _jsonl(root / "文档" / "资料库索引.jsonl"):
        item_id = row.get("item_id") or row.get("entry_id")
        if item_id:
            result["library"].add(str(item_id))
    return result


def audit_project(project_root: str | Path, project_config: dict[str, Any], prose: dict[str, Any]) -> dict[str, Any]:
    root = Path(project_root).resolve()
    evidence = root / "文档" / "证据"
    qualification_by_binding, qualification_ledger_sha256 = _qualification_ledger(root)
    from 项目执行边界 import validate_execution_contract
    contract = validate_execution_contract(root)
    project_id = project_config.get("project_id") or project_config.get("project_name") or ""
    depth_report = _read_json(evidence / "来源深度检查报告.json", {})
    known = _known_ids(root)
    scenes = prose.get("scenes", []) if isinstance(prose, dict) else []
    scene_ids = {str(scene.get("scene_id")) for scene in scenes}
    chapter_ids = {str(scene.get("chapter_id")) for scene in scenes if scene.get("chapter_id")}
    prose_records = [record for scene in scenes for record in scene.get("source_records", [])]
    formal_fact_evidence = audit_formal_fact_evidence(prose_records)
    text = _prose_text(prose)
    paragraphs = [str(p).strip() for scene in scenes for p in scene.get("paragraphs", []) if str(p).strip()]
    normalized = [re.sub(r"\s+", "", paragraph) for paragraph in paragraphs]
    duplicate_sentences = [value for value, count in Counter(normalized).items() if count > 1]

    consumption: dict[str, Any] = {}
    for kind, filename in LOG_NAMES.items():
        rows = _jsonl(evidence / filename)
        run_ids = {str(row.get("run_id")) for row in rows if row.get("project_id") == project_id and row.get("run_id")}
        latest_run_id = max(run_ids) if run_ids else ""
        current = [row for row in rows if row.get("project_id") == project_id and row.get("run_id") == latest_run_id and row.get("status") not in {"test_placeholder", "history"}]
        invalid = [row for row in rows if row not in current]
        required = {"run_id", "project_id", "module_id", "used_in", "purpose", "decision_statement", "source_ref"}
        if kind == "dynamic_chain":
            required |= {"chain_id", "chapter_id", "scene_id"}
        elif kind == "anchor":
            required |= {"anchor_id", "chapter_id", "scene_id"}
        elif kind == "static_connection":
            required |= {"connection_id", "source", "target"}
        else:
            required |= {"connection_id", "combination_id"}
        malformed = [row for row in current if not required.issubset(row)]
        linked = [row for row in current if row not in malformed]
        network_contract = audit_network_consumption_contract(kind, linked) if kind in NETWORK_CONSUMPTION_KINDS else None
        id_key = {"dynamic_chain": "chain_id", "anchor": "anchor_id", "static_connection": "connection_id", "type_connection": "connection_id"}[kind]
        unknown = []
        if kind == "dynamic_chain":
            unknown = [row.get(id_key) for row in linked if str(row.get(id_key)) not in known["dynamic"]]
        elif kind == "anchor":
            unknown = [row.get(id_key) for row in linked if str(row.get(id_key)) not in known["anchor"]]
        elif kind == "static_connection":
            unknown = [row.get(id_key) for row in linked if str(row.get(id_key)) not in known["static"]]
        elif kind == "type_connection":
            normalized = _read_json(evidence / "全量资料治理" / "类型连接_规范化.json", [])
            valid_connections = {
                str(item.get("normalized_id")) for item in normalized
                if isinstance(item, dict) and item.get("normalized_id")
            }
            if not valid_connections:
                combinations = _read_json(evidence / "类型连接全局索引.json", {}).get("combinations", [])
                valid_connections = {str(cid) for item in combinations for cid in item.get("connection_ids", [])}
            unknown = [row.get(id_key) for row in linked if str(row.get(id_key)) not in valid_connections]
        weak = []
        for row in linked:
            rationale = row.get("selection_rationale") if isinstance(row.get("selection_rationale"), dict) else {}
            source_ref = row.get("source_ref") if isinstance(row.get("source_ref"), dict) else {}
            if not source_ref.get("project_id") or not source_ref.get("path") or not source_ref.get("location"):
                weak.append({"id": row.get(id_key), "reason": "source_ref incomplete"})
            if kind in {"dynamic_chain", "static_connection", "anchor"} and row.get("used_in") == "scene_design":
                if not rationale.get("id") or not rationale.get("matched_tokens") or not rationale.get("score", 0):
                    weak.append({"id": row.get(id_key), "reason": "selection rationale has no positive evidence"})
                if not row.get("scene_id") or not row.get("chapter_id"):
                    weak.append({"id": row.get(id_key), "reason": "scene/chapter target missing"})
        linked_scene_count = len({row.get("scene_id") for row in linked if row.get("scene_id") in scene_ids})
        consumption[kind] = {
            "file": filename,
            "loaded": len(rows),
            "current_project": len(current),
            "invalid_or_placeholder": len(invalid),
            "malformed": len(malformed),
            "unknown_source_objects": unknown,
            "weak_evidence": weak,
            "network_consumption_contract": network_contract,
            "scene_linked": linked_scene_count,
            "coverage": round(linked_scene_count / len(scene_ids), 4) if scene_ids else 0.0,
            "valid": bool(current) and not invalid and not malformed and not unknown and not weak and (network_contract is None or network_contract["passed"]),
        }

    library_ids = _library_ids(root / "原始资料" / "资料库.txt")
    indexed = _jsonl(root / "文档" / "资料库索引.jsonl")
    indexed_ids = [str(row.get("entry_id")) for row in indexed if row.get("entry_id")]
    library_ids = sorted(set(library_ids) | set(indexed_ids))
    used_library_ids = {record.get("library_entry_id") for record in prose_records if record.get("library_entry_id")}
    used_library_ids = {str(value) for value in used_library_ids}
    used_library_blocks = {value.split(".", 1)[0] for value in used_library_ids}
    interpretation_registry = _read_json(evidence / "execution_outputs/module_00_source_interpretation_registry.json", {})
    interpretation_records = interpretation_registry.get("records", []) if isinstance(interpretation_registry, dict) else []
    translated_records = [row for row in interpretation_records if row.get("source_status") == "translated"]
    missing_translation_records = [row for row in interpretation_records if row.get("source_status") != "translated"]
    def library_reference_matches(value: str) -> bool:
        return value in library_ids or any(entry_id == value or entry_id.split(".", 1)[0] == value for entry_id in library_ids)
    valid_used_library_ids = {value for value in used_library_ids if library_reference_matches(value)}
    invalid_used_library_ids = sorted(used_library_ids - valid_used_library_ids)
    scene_library_ids = {
        str(record.get("library_entry_id"))
        for scene in scenes
        for record in scene.get("source_records", [])
        if record.get("library_entry_id") and record.get("prose_location")
    }
    prose_library_ids = {
        str(record.get("library_entry_id"))
        for record in prose_records
        if record.get("library_entry_id") and record.get("prose_location")
    }
    coverage = {
        "资料库": {
            "读取": len(library_ids), "已结构化": len(indexed),
            "已进入场景": len({x for x in scene_library_ids if library_reference_matches(x)}),
            "已进入正文": len({x for x in prose_library_ids if library_reference_matches(x)}),
            "无效引用": invalid_used_library_ids,
        },
        "类型连接": consumption["type_connection"],
        "动态网络": consumption["dynamic_chain"],
        "静态网络": consumption["static_connection"],
        "锚点网络": consumption["anchor"],
    }
    prose_binding_failures = []
    for scene in scenes:
        for record in scene.get("source_records", []):
            binding_id = str(record.get("binding_id") or "").strip()
            if qualification_by_binding:
                qualification = qualification_by_binding.get(binding_id)
                if not qualification:
                    prose_binding_failures.append({"scene_id": scene.get("scene_id"), "paragraph_index": record.get("paragraph_index"), "reason": "正文来源 binding_id 不在当前资格账本"})
                elif qualification.get("executable_entry") is not True:
                    prose_binding_failures.append({"scene_id": scene.get("scene_id"), "paragraph_index": record.get("paragraph_index"), "binding_id": binding_id, "reason": "正文来源未获当前资格账本 executable_entry"})
            bindings = record.get("design_bindings") or {}
            for kind in ("dynamic_chain", "static_edge", "anchor", "type_connection"):
                binding = bindings.get(kind) if isinstance(bindings, dict) else None
                if not binding or not binding.get("source_id") or not record.get("prose_location"):
                    prose_binding_failures.append({"scene_id": scene.get("scene_id"), "paragraph_index": record.get("paragraph_index"), "kind": kind, "reason": "missing source_id or prose_location"})
                rationale = binding.get("selection_rationale", {}) if isinstance(binding, dict) else {}
                if binding and (not rationale.get("matched_tokens") or not rationale.get("score", 0)):
                    prose_binding_failures.append({"scene_id": scene.get("scene_id"), "paragraph_index": record.get("paragraph_index"), "kind": kind, "reason": "zero-score prose binding"})
        if not scene.get("anchor_ids_used") or not scene.get("chain_id_used"):
            prose_binding_failures.append({"scene_id": scene.get("scene_id"), "reason": "scene missing required anchor or dynamic chain"})
    blockers = []
    if contract["status"] != "passed":
        blockers.append("项目执行边界未通过：" + "；".join(contract["errors"]))
    run_id = str(prose.get("run_id") or "") if isinstance(prose, dict) else ""
    if not run_id:
        blockers.append("审计输入不是带 run_id 的模块09运行产物")
    if not project_id:
        blockers.append("项目缺少 project_id/project_name")
    if any(item["invalid_or_placeholder"] or item["malformed"] for item in consumption.values()):
        blockers.append("消费日志包含其他项目、占位记录或缺少必需字段")
    if not interpretation_records or missing_translation_records:
        blockers.append("全部资料尚未完成解释词转译")
    if any(item["unknown_source_objects"] for item in consumption.values()):
        blockers.append("消费记录引用了索引中不存在的来源对象")
    if invalid_used_library_ids:
        blockers.append("正文来源记录引用了资料库索引中不存在的条目")
    if not formal_fact_evidence["formal_fact_usable"]:
        blockers.append("正式事实证据仅接受带 original_source 层、原始资料路径和可复核定位的记录")
    if any(item["weak_evidence"] for item in consumption.values()) or prose_binding_failures:
        blockers.append("资料绑定缺少正向匹配证据、完整来源引用或正文段落定位")
    if any(item.get("network_consumption_contract") and not item["network_consumption_contract"]["passed"] for item in consumption.values()):
        blockers.append("网络资料消费缺少场景采用条件、正向决策、定位或合规递延理由")
    fallback_records = [
        {
            "kind": kind,
            "source_id": row.get("chain_id") or row.get("connection_id") or row.get("anchor_id"),
            "fallback_reason": row.get("fallback_reason", ""),
            "original_required_kind": row.get("original_required_kind", ""),
        }
        for kind, filename in LOG_NAMES.items()
        for row in _jsonl(evidence / filename)
        if row.get("project_id") == project_id and row.get("fallback_used")
    ]
    if fallback_records:
        blockers.append("检测到动态/静态跨源回退记录，已列入人工复核阻断清单")
    if duplicate_sentences:
        blockers.append("正文存在跨场景重复段落")
    partial_sources = [source.get("source") for source in depth_report.get("sources", []) if source.get("status") == "partial"]
    pending_sources = [source.get("source") for source in depth_report.get("sources", []) if source.get("missing_fields") or source.get("placeholder_count", 0)]
    governance = _read_json(evidence / "全量资料治理" / "全量检查报告.json", {})
    governance_summary = governance.get("summary", {}) if isinstance(governance, dict) else {}
    normalized_evidence_ready = (
        bool(governance_summary)
        and all(item.get("status") == "passed" and item.get("pending", 0) == 0 for item in governance_summary.values())
        and not any(item.get("blocking", 0) for item in governance_summary.values())
    )
    if (partial_sources or pending_sources) and not normalized_evidence_ready:
        blockers.append("原始资料仍有 partial/pending 或占位字段，且没有通过全量治理的规范化证据")
    return {
        "schema_version": "source-consumption-audit-1.1",
        "project_id": project_id, "scene_count": len(scene_ids), "chapter_count": len(chapter_ids),
        "coverage": coverage, "consumption": consumption,
        "prose_binding_failures": prose_binding_failures,
        "duplicate_paragraphs": duplicate_sentences,
        "prose_paragraph_count": len(paragraphs), "prose_source_record_count": len(prose_records),
        "formal_fact_evidence": formal_fact_evidence,
        "qualification_ledger": {
            "present": bool(qualification_by_binding),
            "sha256": qualification_ledger_sha256,
            "binding_count": len(qualification_by_binding),
            "non_executable_prose_binding_failure_count": sum(
                1 for item in prose_binding_failures
                if item.get("reason") == "正文来源未获当前资格账本 executable_entry"
            ),
        },
        "source_depth": {"partial_sources": partial_sources, "pending_or_placeholder_sources": pending_sources, "normalized_evidence_used": normalized_evidence_ready},
        "interpretation_coverage": {"registry_records": len(interpretation_records), "translated_records": len(translated_records), "missing_translation_records": len(missing_translation_records), "scope": "all_sources", "scene_and_prose_consumption_is_separate": True},
        "runtime_boundary": {"run_id": run_id, "run_ids": sorted({str(row.get("run_id")) for rows in consumption.values() for row in _jsonl(evidence / rows["file"]) if row.get("project_id") == project_id and row.get("run_id")}), "known_source_id_counts": {key: len(value) for key, value in known.items()}},
        "fallback_review_records": fallback_records,
        "draft_passed": bool(run_id and scene_ids and paragraphs),
        "coverage_passed": not invalid_used_library_ids and not prose_binding_failures,
        "delivery_ready": not blockers,
        "status": "failed" if blockers else "passed", "blocking_failures": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="审计资料从来源到场景卡和正文的证据链")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--config", default="配置/project_config.json")
    parser.add_argument("--prose", default="文档/证据/execution_outputs/module_09_scene_prose.json")
    parser.add_argument("--output", default="文档/证据/资料消费审计报告.json")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    config = _read_json(root / args.config, {})
    prose = _read_json(root / args.prose, {})
    report = audit_project(root, config, prose)
    output = root / args.output if report["status"] == "passed" else root / "文档" / "证据" / "失败运行" / f"{str(prose.get('run_id') or 'invalid')}_资料消费审计报告.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "blocking_failures": report["blocking_failures"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())