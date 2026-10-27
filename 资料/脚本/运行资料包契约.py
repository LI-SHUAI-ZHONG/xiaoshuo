"""Immutable, run-scoped material package for scene and prose execution.

The package is a runtime boundary, not an authorization producer.  It binds a
selected source object to its on-disk hash, scene condition, reason, dual-use
grant and later consumption evidence under exactly one ``run_id``.
"""
from __future__ import annotations

import hashlib
import json
import ast
from pathlib import Path
from typing import Any
from 资料资格与合同注册 import CONTRACT_FIELD_VERSION, load_qualification_ledger, resolve_contract_fields, validate_contract_fields


SCHEMA_VERSION = "runtime-material-package-1.0"
MATERIAL_DUTY_STATUSES = frozenset({"design_used", "scene_constraint_used", "prose_used", "deferred"})


def _text(value: Any) -> str:
    return str(value or "").strip()


def _material_duty(row: dict[str, Any], selection: dict[str, Any], grant: dict[str, Any]) -> dict[str, Any]:
    """Project the binding duty into the run package without granting prose by selection."""
    binding = row.get("creation_binding") if isinstance(row.get("creation_binding"), dict) else {}
    role = _text(binding.get("material_role"))
    stages = [_text(value) for value in binding.get("applicable_stage", binding.get("stages", [])) if _text(value)]
    dimensions = [_text(value) for value in binding.get("required_writing_dimensions", []) if _text(value)]
    requested = [_text(value) for value in selection.get("required_writing_dimensions", []) if _text(value)]
    stage = _text(selection.get("stage") or "正文")
    contract_input = row | grant | selection
    contract_supplied = isinstance(contract_input.get("contracts"), dict) and isinstance(contract_input.get("contracts", {}).get("authorization_contract"), dict)
    authorization = validate_contract_fields(contract_input, "authorization_contract")
    contract_allows_prose = binding.get("prose_evidence_required") is True
    dimension_match = bool(set(dimensions) & set(requested)) if requested else bool(dimensions)
    explicitly_granted = authorization["passed"] and authorization["fields"].get("model_input_eligible") is True and grant.get("prose_write_allowed") is True
    prose_allowed = bool(
        selection.get("activation_conditions_met") is True
        and role
        and stage in stages
        and contract_allows_prose
        and dimension_match
        and explicitly_granted
    )
    if not role or not stages or not dimensions:
        deferred_reason = "资料绑定缺少 material_role、applicable_stage 或 required_writing_dimensions"
    elif not contract_allows_prose:
        deferred_reason = "资料职责未要求正文逐段证据，仅保留设计或场景约束职责"
    elif not dimension_match:
        deferred_reason = "本场景未匹配资料要求的写作维度"
    elif selection.get("activation_conditions_met") is not True:
        deferred_reason = "场景激活条件未满足"
    elif not explicitly_granted:
        deferred_reason = "授权合同未显式授予正文写回"
    else:
        deferred_reason = ""
    return {
        "material_role": role,
        "applicable_stage": stages,
        "required_writing_dimensions": dimensions,
        "scene_required_writing_dimensions": requested,
        "prose_evidence_required": prose_allowed,
        "deferred_reason": deferred_reason,
        "contract_version": authorization.get("contract_version", ""),
        "contract_field_version": CONTRACT_FIELD_VERSION,
        "contract_errors": authorization.get("missing", []) + authorization.get("conflicts", []) + ([authorization.get("version_error")] if authorization.get("version_error") else []),
        "authorization_contract": authorization,
        "contract_supplied": contract_supplied,
    }


def _source_path(root: Path, source_ref: Any) -> Path | None:
    ref = _text(source_ref).replace("\\", "/")
    relative = ref.split(":", 1)[0]
    candidate = (root / relative).resolve()
    return candidate if relative and candidate.is_file() and root in candidate.parents else None


def _canonical_source_ref(root: Path, row: dict[str, Any]) -> str:
    """Normalize legacy library locators only after exact index verification."""
    value = row.get("source_ref")
    if isinstance(value, str) and not value.lstrip().startswith("{"):
        return value.strip()
    if row.get("source_kind") != "资料库" or not isinstance(value, str):
        return ""
    try:
        legacy = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return ""
    if not isinstance(legacy, dict):
        return ""
    expected_file = str(legacy.get("file") or "").replace("\\", "/")
    locator = str(legacy.get("locator") or "").strip()
    try:
        line_start = int(legacy.get("line_start"))
    except (TypeError, ValueError):
        return ""
    index_path = root / "文档" / "资料库索引.jsonl"
    try:
        lines = index_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return ""
    source_id = str(row.get("source_id") or "").strip()
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        source_ref = item.get("source_ref") if isinstance(item, dict) else None
        if not isinstance(source_ref, dict):
            continue
        try:
            indexed_line_start = int(source_ref.get("line_start", -1))
        except (TypeError, ValueError):
            continue
        if (
            str(item.get("entry_id") or item.get("name") or "").strip() == source_id
            and str(source_ref.get("file") or "").replace("\\", "/") == expected_file
            and str(source_ref.get("locator") or "").strip() == locator
            and indexed_line_start == line_start
        ):
            return f"{expected_file}:{locator}"
    return ""


def _sha256(path: Path | None) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None


def _qualification_ledger(root: Path) -> dict[str, Any] | None:
    value, _ = load_qualification_ledger(root)
    return value


def build_package(
    project_root: str | Path,
    run_id: str,
    bindings: list[dict[str, Any]],
    selections: list[dict[str, Any]],
    grants: dict[str, dict[str, Any]] | None = None,
    scene_contexts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a deterministic runtime package; selection requires evidence, not authorization."""
    root = Path(project_root).expanduser().resolve()
    ledger = _qualification_ledger(root)
    ledger_by_binding = {
        _text(row.get("binding_id")): row for row in (ledger or {}).get("records", [])
        if isinstance(row, dict) and _text(row.get("binding_id"))
    }
    by_id = {str(row.get("binding_id")): row for row in bindings if isinstance(row, dict) and _text(row.get("binding_id"))}
    contexts = {
        _text(row.get("scene_id")): row
        for row in (scene_contexts or [])
        if isinstance(row, dict) and _text(row.get("scene_id"))
    }
    records: list[dict[str, Any]] = []
    for selection in selections:
        if not isinstance(selection, dict):
            continue
        binding_id = _text(selection.get("binding_id"))
        row = by_id.get(binding_id, {})
        grant = grants.get(binding_id, {}) if isinstance(grants, dict) and isinstance(grants.get(binding_id, {}), dict) else {}
        authorization = resolve_contract_fields(row | grant | selection, "authorization_contract")
        source_ref = _canonical_source_ref(root, row)
        source_path = _source_path(root, source_ref)
        strategy = row.get("creation_binding", {}).get("creative_strategy", {}) if isinstance(row.get("creation_binding"), dict) else {}
        scene_id = _text(selection.get("scene_id"))
        context = contexts.get(scene_id, {})
        records.append({
            "binding_id": binding_id,
            "source_id": _text(row.get("source_id")),
            "source_kind": _text(row.get("source_kind")),
            "source_ref": source_ref,
            "source_file_sha256": _sha256(source_path),
            "object_locator": source_ref.split(":", 1)[1] if ":" in source_ref else "",
            "definition": row.get("definition", ""),
            "call_condition": row.get("call_condition", ""),
            "usage_method": row.get("usage_method", {}),
            "examples": row.get("examples", []),
            "forbidden_use": row.get("forbidden_use", ""),
            "chapter_id": _text(selection.get("chapter_id") or context.get("chapter_id")),
            "scene_id": scene_id,
            "scene_sequence": context.get("scene_sequence"),
            "state_before": _text(selection.get("state_before") or context.get("state_before")),
            "state_after": _text(selection.get("state_after") or context.get("state_after")),
            "previous_scene_id": _text(context.get("previous_scene_id")),
            "previous_state_after": _text(context.get("previous_state_after")),
            "activation_conditions_met": selection.get("activation_conditions_met") is True,
            "activation_evidence": selection.get("activation_evidence") if isinstance(selection.get("activation_evidence"), list) else [],
            "selection_rationale": _text(selection.get("selection_rationale")),
            "semantic_anchor": _text(strategy.get("semantic_anchor")) if isinstance(strategy, dict) else "",
            "model_input_eligible": authorization["passed"] and authorization["fields"].get("model_input_eligible") is True and selection.get("activation_conditions_met") is True,
            "prose_write_allowed": False,
            "material_duty": _material_duty(row, selection, grant),
            "duty_status": "scene_constraint_used" if selection.get("activation_conditions_met") is True else "deferred",
            "deferred_reason": "",
            "activation_status": "selected" if selection.get("activation_conditions_met") is True else "deferred",
            "qualification": ledger_by_binding.get(binding_id, {}).get("qualification", "") if ledger else "",
            "executable_entry": ledger_by_binding.get(binding_id, {}).get("executable_entry") if ledger else None,
            "authorization_contract": {
                "contract_supplied": bool(grant) or isinstance(row.get("contracts"), dict),
                "contract_version": authorization.get("contract_version", ""),
                "field_version": CONTRACT_FIELD_VERSION,
                "fields": authorization.get("fields", {}),
                "missing": authorization.get("missing", []),
                "conflicts": authorization.get("conflicts", []),
                "version_error": authorization.get("version_error", ""),
            },
        })
        records[-1]["prose_write_allowed"] = records[-1]["material_duty"]["prose_evidence_required"]
        records[-1]["deferred_reason"] = records[-1]["material_duty"]["deferred_reason"]
        if not records[-1]["prose_write_allowed"] and records[-1]["duty_status"] == "scene_constraint_used":
            records[-1]["duty_status"] = "deferred"
    scene_context_payload = []
    for scene_id, context in contexts.items():
        scene_context_payload.append({
            "chapter_id": _text(context.get("chapter_id")),
            "scene_id": scene_id,
            "scene_sequence": context.get("scene_sequence"),
            "state_before": _text(context.get("state_before")),
            "state_after": _text(context.get("state_after")),
            "previous_scene_id": _text(context.get("previous_scene_id")),
            "previous_state_after": _text(context.get("previous_state_after")),
        })
    scene_context_payload.sort(key=lambda row: (str(row.get("scene_sequence")), row["scene_id"]))
    package_id = hashlib.sha256(json.dumps({"run_id": _text(run_id), "records": records, "scene_contexts": scene_context_payload}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    for record in records:
        record["package_id"] = package_id
        context = contexts.get(_text(record.get("scene_id")), {})
        normalized_context = next((item for item in scene_context_payload if item["scene_id"] == _text(record.get("scene_id"))), {})
        record["continuity_hash"] = hashlib.sha256(json.dumps(normalized_context, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() if context else ""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": _text(run_id),
        "records": records,
        "frozen_binding_ids": [row["binding_id"] for row in records],
        "frozen_scene_ids": sorted({row["scene_id"] for row in records if row.get("scene_id")}),
        "selected_count": sum(row["activation_status"] == "selected" for row in records),
        "deferred_count": sum(row["activation_status"] == "deferred" for row in records),
        "package_id": package_id,
        "qualification_ledger_sha256": load_qualification_ledger(root)[1] if ledger else "",
        "scene_contexts": scene_context_payload,
    }


def validate_package(
    project_root: str | Path,
    package: dict[str, Any],
    stage: str,
    consumption_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Default-deny validation for scene, prose, editorial and delivery stages."""
    root = Path(project_root).expanduser().resolve()
    ledger = _qualification_ledger(root)
    ledger_by_binding = {
        _text(row.get("binding_id")): row for row in (ledger or {}).get("records", [])
        if isinstance(row, dict) and _text(row.get("binding_id"))
    }
    errors: list[str] = []
    if stage not in {"scene", "prose", "editorial", "delivery"}:
        errors.append("资料包阶段无效")
    if not isinstance(package, dict) or package.get("schema_version") != SCHEMA_VERSION:
        errors.append("资料包版本无效")
        return {"passed": False, "errors": errors, "records": []}
    run_id = _text(package.get("run_id"))
    if not run_id or Path(run_id).name != run_id:
        errors.append("资料包缺少有效 run_id")
    records = package.get("records") if isinstance(package.get("records"), list) else []
    frozen_ids = package.get("frozen_binding_ids") if isinstance(package.get("frozen_binding_ids"), list) else []
    record_ids = [
        _text(row.get("binding_id")) for row in records
        if isinstance(row, dict) and _text(row.get("binding_id"))
    ]
    if set(frozen_ids) != set(record_ids) or len(frozen_ids) != len(set(frozen_ids)):
        errors.append("资料包冻结 binding_id 集合与记录集合不一致")
    if ledger:
        expected_ledger_hash = _sha256(root / "文档" / "证据" / "资料资格账本.json")
        if package.get("qualification_ledger_sha256") != expected_ledger_hash:
            errors.append("资料包资格账本哈希不一致")
    if stage in {"scene", "prose", "editorial", "delivery"} and not any(row.get("activation_status") == "selected" for row in records if isinstance(row, dict)):
        errors.append("资料包没有满足场景条件且有来源证据的选中资料")
    binding_scenes: dict[str, set[str]] = {}
    scene_contexts = package.get("scene_contexts") if isinstance(package.get("scene_contexts"), list) else []
    context_by_scene = {_text(row.get("scene_id")): row for row in scene_contexts if isinstance(row, dict) and _text(row.get("scene_id"))}
    ordered_contexts = sorted(context_by_scene.values(), key=lambda row: (str(row.get("scene_sequence")), _text(row.get("scene_id"))))
    if scene_contexts:
        for index, context in enumerate(ordered_contexts):
            required = ("chapter_id", "scene_id", "scene_sequence", "state_before", "state_after")
            if any(not _text(context.get(field)) for field in required):
                errors.append(f"{_text(context.get('scene_id')) or 'missing-scene'} 连续状态字段不完整")
            if index:
                previous = ordered_contexts[index - 1]
                if _text(context.get("previous_scene_id")) != _text(previous.get("scene_id")) or _text(context.get("previous_state_after")) != _text(previous.get("state_after")):
                    errors.append(f"{_text(context.get('scene_id'))} 前后状态未衔接")
        context_scene_ids = set(context_by_scene)
        record_scene_ids = {_text(row.get("scene_id")) for row in records if isinstance(row, dict) and _text(row.get("scene_id"))}
        missing_scenes = sorted(context_scene_ids - record_scene_ids)
        if missing_scenes:
            errors.append("场景缺少运行资料包记录：" + ", ".join(missing_scenes))
    for row in records:
        if not isinstance(row, dict) or row.get("activation_status") != "selected":
            continue
        binding_id = _text(row.get("binding_id"))
        scene_id = _text(row.get("scene_id"))
        if binding_id and scene_id:
            binding_scenes.setdefault(binding_id, set()).add(scene_id)
    for binding_id, scene_ids in binding_scenes.items():
        if len(scene_ids) > 1:
            errors.append(f"{binding_id} 跨场景绑定：" + ", ".join(sorted(scene_ids)))
    consumption_records = consumption_records or []
    for row in records:
        binding_id = _text(row.get("binding_id")) or "missing-binding"
        if ledger:
            qualification = ledger_by_binding.get(binding_id)
            if not qualification:
                errors.append(f"{binding_id} 不在当前资格账本")
            elif row.get("executable_entry") is not True or qualification.get("executable_entry") is not True:
                errors.append(f"{binding_id} 资格账本未授予 executable_entry")
            elif row.get("qualification") != qualification.get("qualification"):
                errors.append(f"{binding_id} 资料包资格与账本不一致")
        required = ("binding_id", "source_id", "source_ref", "source_file_sha256", "object_locator", "scene_id", "selection_rationale")
        if any(not _text(row.get(field)) for field in required):
            errors.append(f"{binding_id} 资料包对象定位或选择理由不完整")
        source_path = _source_path(root, row.get("source_ref"))
        if _sha256(source_path) != row.get("source_file_sha256"):
            errors.append(f"{binding_id} 来源文件哈希漂移")
        selected = row.get("activation_status") == "selected"
        if scene_contexts:
            context = context_by_scene.get(_text(row.get("scene_id")), {})
            if not context or _text(row.get("chapter_id")) != _text(context.get("chapter_id")) or _text(row.get("state_before")) != _text(context.get("state_before")) or _text(row.get("state_after")) != _text(context.get("state_after")):
                errors.append(f"{binding_id} 章节或连续状态与冻结场景不一致")
            normalized_context = {key: _text(context.get(key)) if key != "scene_sequence" else context.get(key) for key in ("chapter_id", "scene_id", "scene_sequence", "state_before", "state_after", "previous_scene_id", "previous_state_after")}
            expected_continuity = hashlib.sha256(json.dumps(normalized_context, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() if context else ""
            if row.get("continuity_hash") != expected_continuity or row.get("package_id") != package.get("package_id"):
                errors.append(f"{binding_id} 冻结资料包标识不一致")
        if selected and (row.get("activation_conditions_met") is not True or not row.get("activation_evidence")):
            errors.append(f"{binding_id} 场景条件或激活证据缺失")
        authorization = row.get("authorization_contract") if isinstance(row.get("authorization_contract"), dict) else {}
        duty = row.get("material_duty") if isinstance(row.get("material_duty"), dict) else {}
        contract_supplied = bool(duty.get("contract_supplied"))
        if contract_supplied and (not isinstance(authorization, dict) or not authorization.get("contract")):
            errors.append(f"{binding_id} 缺少统一 authorization_contract 校验回执")
        elif contract_supplied and not authorization.get("passed"):
            errors.append(f"{binding_id} authorization_contract 不完整或不兼容：" + ", ".join(str(item) for item in (authorization.get("missing", []) + authorization.get("conflicts", []) + ([authorization.get("version_error")] if authorization.get("version_error") else []))))
        duty_status = _text(row.get("duty_status"))
        if duty_status not in MATERIAL_DUTY_STATUSES:
            errors.append(f"{binding_id} 缺少有效资料职责状态")
        if duty_status == "deferred" and not _text(row.get("deferred_reason") or duty.get("deferred_reason")):
            errors.append(f"{binding_id} 资料职责递延缺少 deferred_reason")
        if row.get("prose_write_allowed") is True and duty.get("prose_evidence_required") is not True:
            errors.append(f"{binding_id} 正文写回授权未获得资料职责合同")
        if stage in {"prose", "editorial", "delivery"} and selected:
            if row.get("prose_write_allowed") is not True:
                if any(isinstance(item, dict) and _text(item.get("binding_id")) == binding_id for item in consumption_records):
                    errors.append(f"{binding_id} 非正文职责资料进入正文消费链")
                continue
            matching = [item for item in consumption_records if isinstance(item, dict) and item.get("binding_id") == binding_id]
            current = [item for item in matching if item.get("run_id") == run_id]
            if not current:
                errors.append(f"{binding_id} 缺少同一 run_id 的消费证据")
            elif not any(
                _text(item.get("source_id")) == _text(row.get("source_id"))
                and _text(item.get("scene_id")) == _text(row.get("scene_id"))
                and (not scene_contexts or (
                    _text(item.get("chapter_id")) == _text(row.get("chapter_id"))
                    and _text(item.get("package_id")) == _text(package.get("package_id"))
                    and _text(item.get("continuity_hash")) == _text(row.get("continuity_hash"))
                ))
                and _text(item.get("prose_location"))
                for item in current
            ):
                errors.append(f"{binding_id} 消费证据缺少来源、场景或段落定位")
            elif not any(
                _text(item.get("translation_evidence_result"))
                and _text(item.get("source_id")) == _text(row.get("source_id"))
                and _text(item.get("scene_id")) == _text(row.get("scene_id"))
                and _text(item.get("prose_location"))
                for item in current
            ):
                errors.append(f"{binding_id} 缺少 translation_evidence.result、场景或正文消费定位")
    return {"passed": not errors, "errors": list(dict.fromkeys(errors)), "records": records, "run_id": run_id}


def write_package(project_root: str | Path, package: dict[str, Any]) -> Path:
    root = Path(project_root).expanduser().resolve()
    run_id = _text(package.get("run_id"))
    target = root / "文档" / "证据" / "运行" / run_id / "运行资料包.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_package(project_root: str | Path, run_id: str) -> dict[str, Any]:
    path = Path(project_root).expanduser().resolve() / "文档" / "证据" / "运行" / _text(run_id) / "运行资料包.json"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}