"""Version-bound approval gate for an authored novel run.

This gate is separate from material-batch publication. A draft may be useful
for review without being eligible for delivery. Formal delivery requires stable
run evidence, approved source-item attestations, and a human approval bound to
that exact manifest.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from 运行清单复核 import verify_manifest
from 资料消费审计 import audit_material_duty_records
from 资料资格与合同注册 import CONTRACT_VERSION, CONTRACT_FIELD_VERSION, load_qualification_ledger, resolve_contract_fields

AUTHORED_RUN_DELIVERY_SCOPE = "authored_run_delivery"
MATERIAL_BATCH_RELEASE_SCOPE = "material_batch_release"
MANIFEST_SCHEMA = "formal-release-manifest-1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(data)


def _normal_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def _source_ref(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        path = _normal_path(value.get("path") or value.get("file"))
        locator = str(value.get("locator") or value.get("location") or "").strip()
        resource_root = str(value.get("resource_root") or value.get("resourceRoot") or "").strip()
    else:
        text = str(value or "").replace("\\", "/").strip()
        path, separator, locator = text.rpartition(":")
        resource_root = ""
        if not separator:
            path, locator = text, ""
    result = {"path": path, "locator": locator}
    if resource_root:
        result["resource_root"] = resource_root
    return result


def _source_content_sha256(root: Path, ref: dict[str, str], configured_resource_root: Path | None = None) -> tuple[str | None, Path | None]:
    relative = _normal_path(ref.get("path"))
    roots = [(root, "project")]
    if configured_resource_root is not None and configured_resource_root != root:
        roots.append((configured_resource_root, "shared"))
    requested_root = str(ref.get("resource_root") or "").strip()
    for candidate_root, _ in roots:
        if requested_root and candidate_root != Path(requested_root).expanduser().resolve():
            continue
        path = (candidate_root / relative).resolve()
        if relative and path != candidate_root and candidate_root in path.parents and path.is_file():
            return _sha256_bytes(path.read_bytes()), path
    return None, None


def _build_manifest(root: Path, evidence: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    run_id = str(evidence.get("run_id") or "").strip()
    if not run_id or Path(run_id).name != run_id:
        blockers.append("写作证据缺少有效 run_id")
    evidence_dir = root / "文档" / "证据"
    if run_id:
        for path in (
            evidence_dir / "运行" / run_id / "执行消费.jsonl",
            evidence_dir / "运行" / run_id / "scene_source_selection.json",
            evidence_dir / "运行" / run_id / "运行资料包.json",
            evidence_dir / "运行" / run_id / "module_outputs" / "module_09_scene_prose.json",
        ):
            if not path.is_file():
                blockers.append(f"缺少本次运行证据：{path.relative_to(root)}")
        run_manifest = verify_manifest(root, run_id, required_kinds={"input_snapshot", "scene_selection", "material_package", "material_use", "prose_file", "module_output"})
        if not run_manifest["passed"]:
            blockers.extend("运行清单：" + error for error in run_manifest["errors"])
    if evidence.get("runtime_prose_status") != "passed":
        blockers.append("运行期正文证据未通过")

    used_sources: list[dict[str, Any]] = []
    configured_resource_root = None
    config_for_sources = _read_json(root / "配置" / "project_config.json", {})
    if isinstance(config_for_sources, dict) and config_for_sources.get("resource_root"):
        configured_resource_root = Path(str(config_for_sources["resource_root"])).expanduser().resolve()
    registry_for_sources = _read_json(root / "配置" / "项目注册表.json", {})
    registered_resource_root = configured_resource_root
    if isinstance(registry_for_sources, dict):
        for item in registry_for_sources.get("projects", []):
            if isinstance(item, dict) and item.get("project_id") == config_for_sources.get("project_id") and item.get("resource_root"):
                registered_resource_root = Path(str(item["resource_root"])).expanduser().resolve()
                break
    if configured_resource_root and registered_resource_root and configured_resource_root != registered_resource_root:
        blockers.append("项目配置 resource_root 与注册表不一致")
    seen: set[tuple[str, str, str]] = set()
    for record in evidence.get("records", []):
        if not isinstance(record, dict) or record.get("status") != "used":
            continue
        source_id = str(record.get("source_id") or "").strip()
        ref = _source_ref(record.get("source_ref"))
        source_hash, source_path = _source_content_sha256(root, ref, registered_resource_root)
        if not source_id:
            blockers.append("已使用来源缺少 source_id")
            continue
        if not ref["path"] or not ref["locator"]:
            blockers.append(f"已使用来源缺少精确 source_ref：{source_id}")
            continue
        if source_hash is None:
            blockers.append(f"已使用来源文件不存在或路径非法：{source_id}")
            continue
        key = (source_id, ref["path"], ref["locator"])
        if key in seen:
            continue
        seen.add(key)
        used_sources.append({
            "source_id": source_id,
            "source_kind": str(record.get("source_kind") or ""),
            "source_status": str(record.get("source_status") or ""),
            "source_ref": ref,
            "source_ref_sha256": _sha256_json(ref),
            "source_content_sha256": source_hash,
            "contracts": record.get("contracts") if isinstance(record.get("contracts"), dict) else {},
            "formal_authorization_contract": record.get("formal_authorization_contract") if isinstance(record.get("formal_authorization_contract"), dict) else {},
        })
    if not used_sources:
        blockers.append("本次运行没有可认证的已使用来源")

    prose_files: list[dict[str, str]] = []
    for item in evidence.get("prose_files", []):
        if not isinstance(item, dict):
            blockers.append("正文文件证据格式错误")
            continue
        relative = _normal_path(item.get("relative_path"))
        expected = str(item.get("sha256") or "")
        path = (root / relative).resolve()
        if not run_id or not relative.startswith(f"正文/运行/{run_id}/"):
            blockers.append(f"正文文件不属于本次运行：{relative}")
        elif not path.is_file() or _sha256_bytes(path.read_bytes()) != expected:
            blockers.append(f"正文文件哈希不匹配：{relative}")
        else:
            prose_files.append({"relative_path": relative, "sha256": expected})
    if not prose_files:
        blockers.append("本次运行没有可验证的正文文件")

    config = _read_json(root / "配置" / "project_config.json", {})
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "generated_at": _now(),
        "run_id": run_id,
        "project_id": config.get("project_id") if isinstance(config, dict) else None,
        "genre_selection": config.get("genre_selection") if isinstance(config, dict) else None,
        "type_combination": config.get("type_combination") if isinstance(config, dict) else None,
        "used_sources": used_sources,
        "prose_files": prose_files,
    }
    immutable = {key: value for key, value in manifest.items() if key not in {"generated_at", "manifest_sha256"}}
    manifest["manifest_sha256"] = _sha256_json(immutable)
    return manifest, blockers


def _attestation_errors(root: Path, used_sources: list[dict[str, Any]]) -> list[str]:
    approved = {
        (str(row.get("source_id") or ""), str(row.get("source_ref_sha256") or ""), str(row.get("source_content_sha256") or ""))
        for row in _read_jsonl(root / "文档" / "证据" / "来源条目认证.jsonl")
        if row.get("schema_version") == "source-item-attestation-1.0"
        and row.get("decision") == "approved"
        and str(row.get("reviewed_by") or "").strip()
        and str(row.get("reviewed_at") or "").strip()
        and not row.get("missing_fields")
        and not row.get("placeholder_matches")
    }
    return [
        f"缺少当前版本来源条目认证：{item['source_id']}"
        for item in used_sources
        if (item["source_id"], item["source_ref_sha256"], item["source_content_sha256"]) not in approved
    ]


def _formal_contract_errors(used_sources: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for source in used_sources:
        result = resolve_contract_fields(source, "formal_authorization_contract")
        if not result["passed"]:
            details = result["missing"] + result["conflicts"]
            if result.get("version_error"):
                details.append(result["version_error"])
            errors.append(
                "正式授权合同不完整或不兼容："
                + str(source.get("source_id") or "missing-source")
                + "（" + ", ".join(str(item) for item in details) + "）"
            )
    return errors


def _approval_errors(root: Path, manifest: dict[str, Any]) -> list[str]:
    approval = _read_json(root / "配置" / "formal_release_approval.json", {})
    if not isinstance(approval, dict):
        return ["缺少正式交付人工批准凭证"]
    errors: list[str] = []
    if approval.get("schema_version") != "formal-release-approval-1.0" or approval.get("status") != "approved":
        errors.append("正式交付人工批准凭证无效")
    if not str(approval.get("approved_by") or "").strip() or not str(approval.get("approved_at") or "").strip():
        errors.append("正式交付人工批准凭证缺少审批人或时间")
    if approval.get("run_id") != manifest.get("run_id") or approval.get("manifest_sha256") != manifest.get("manifest_sha256"):
        errors.append("正式交付人工批准未精确绑定当前运行清单")
    required = {"project_id", "genre_selection", "book_title", "world_stage", "mainline_conflict", "core_mystery", "protagonist", "chapter_plan"}
    if not required.issubset({str(item) for item in approval.get("accepted_fields", [])}):
        errors.append("正式交付人工批准未覆盖项目事实字段")
    source_ids = {item["source_id"] for item in manifest.get("used_sources", [])}
    if not source_ids.issubset({str(item) for item in approval.get("approved_source_ids", [])}):
        errors.append("正式交付人工批准未覆盖全部已使用来源")
    return errors


def _golden_three_chapter_errors(root: Path) -> list[str]:
    """Require the independent three-chapter progression gate before release review."""
    path = root / "文档" / "证据" / "三章金样本" / "三章金样本验证报告.json"
    if not path.is_file():
        return ["缺少三章金样本跨章质量报告"]
    report = _read_json(path, {})
    if not isinstance(report, dict):
        return ["缺少三章金样本跨章质量报告"]
    errors: list[str] = []
    if report.get("chapter_count") != 3:
        errors.append("三章金样本未完成三章逐章检查")
    if report.get("status") != "planning_gate_passed":
        errors.append("三章金样本逐章质量门未通过")
    cross_chapter = report.get("cross_chapter_gate")
    if not isinstance(cross_chapter, dict) or cross_chapter.get("status") != "passed":
        errors.append("三章金样本跨章状态递进门未通过")
    return errors


def _long_lineage_errors(root: Path) -> list[str]:
    """Require explicit long-form scope and author-confirmed story core."""
    config = _read_json(root / "配置" / "project_config.json", {})
    if not isinstance(config, dict):
        return ["缺少有效项目配置，无法确认长线创作范围和故事核心"]
    errors: list[str] = []
    chapter_count = config.get("target_chapter_count")
    if not isinstance(chapter_count, int) or isinstance(chapter_count, bool) or chapter_count < 3:
        errors.append("正式交付要求 target_chapter_count 至少为 3；当前长线范围不足")
    confirmation = config.get("story_core_confirmation")
    if not isinstance(confirmation, dict) or confirmation.get("status") != "confirmed":
        errors.append("故事核心尚未取得作者确认；灵感候选和规划产物不得升级为项目事实")
    else:
        required = ("confirmation_id", "confirmed_by", "confirmed_at")
        missing = [key for key in required if not str(confirmation.get(key) or "").strip()]
        if missing:
            errors.append("故事核心作者确认缺少字段：" + ", ".join(missing))
        if confirmation.get("project_id") and confirmation.get("project_id") != config.get("project_id"):
            errors.append("故事核心作者确认未绑定当前 project_id")
    return errors


def _character_performance_errors(root: Path) -> list[str]:
    path = root / "文档" / "证据" / "全流程人物表现结果.json"
    if not path.is_file():
        return ["缺少步骤 10/11 人物表现结果；交付保持 blocked"]
    report = _read_json(path, {})
    if not isinstance(report, dict):
        return ["步骤 10/11 人物表现结果格式无效"]
    if report.get("status") != "passed" or report.get("deferred_count"):
        return ["人物表现结果门未通过或仍存在 deferred 项"]
    return []


def _capability_layers(root: Path, manifest: dict[str, Any], contract_blockers: list[str], all_blockers: list[str]) -> dict[str, Any]:
    """Expose independent capability states; no layer may infer another."""
    run_id = str(manifest.get("run_id") or "").strip()
    run_dir = root / "文档" / "证据" / "运行" / run_id if run_id else root / "文档" / "证据" / "运行"
    contract_errors = list(contract_blockers)
    source_errors = []
    if not run_id:
        source_errors.append("来源证据缺少当前 run_id")
    if not manifest.get("used_sources"):
        source_errors.append("来源证据没有可认证的已使用来源")
    if not manifest.get("prose_files"):
        source_errors.append("来源证据没有可验证的当前正文文件")
    if not any(path.is_file() for path in (run_dir / "执行消费.jsonl", run_dir / "module_outputs" / "module_09_scene_prose.json")):
        source_errors.append("缺少当前运行的正文消费证据")

    structural_errors = _golden_three_chapter_errors(root)
    performance_errors = _character_performance_errors(root)
    literary_errors: list[str] = []
    literary_report = None
    for path in (run_dir / "文学审校.json", root / "文档" / "证据" / "全量资料文学审校报告.json"):
        if path.is_file():
            literary_report = _read_json(path, {})
            if isinstance(literary_report, dict):
                break
    if not isinstance(literary_report, dict):
        literary_errors.append("缺少当前运行文学审校报告")
    else:
        if literary_report.get("run_id") != run_id:
            literary_errors.append("文学审校报告未绑定当前 run_id")
        if literary_report.get("status") != "passed":
            literary_errors.append("文学审校尚未通过")
        literary_errors.extend(str(item) for item in literary_report.get("blockers", []) if item)
        if literary_report.get("pending_consumption_ids"):
            literary_errors.append("文学审校仍存在 pending 消费记录")

    def layer(passed: bool, failed_status: str, errors: list[str], passed_status: str = "passed") -> dict[str, Any]:
        return {"passed": passed and not errors, "status": passed_status if passed and not errors else failed_status, "blockers": list(dict.fromkeys(errors))}

    contract = layer(not contract_errors, "blocked", contract_errors)
    source = layer(not source_errors, "blocked", source_errors)
    structural = layer(not structural_errors, "blocked", structural_errors)
    literary = layer(not literary_errors, "literary_review_pending", literary_errors, "literary_review_passed")
    release_errors = list(dict.fromkeys(all_blockers + source_errors + structural_errors + performance_errors + literary_errors))
    return {
        "contract_passed": contract,
        "source_evidence_passed": source,
        "structural_review_passed": structural,
        "literary_review": literary,
        "literary_review_status": "literary_review_passed" if literary["passed"] else "literary_review_pending",
        "character_performance_passed": not performance_errors,
        "release_status": "release_approved" if not release_errors else "release_blocked",
        "release_blockers": release_errors,
    }


def validate_formal_release(
    project_root: str | Path,
    writing_evidence: dict[str, Any],
    release_scope: str = AUTHORED_RUN_DELIVERY_SCOPE,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    if release_scope == MATERIAL_BATCH_RELEASE_SCOPE:
        return {
            "status": "blocked",
            "release_scope": release_scope,
            "formal_release_allowed": False,
            "blockers": ["全量资料发布预检.py 是资料批次发布的唯一入口；正式交付审批.py 不处理该范围。"],
            "manifest": {"schema_version": MANIFEST_SCHEMA, "used_sources": [], "manifest_sha256": ""},
        }
    if release_scope != AUTHORED_RUN_DELIVERY_SCOPE:
        return {
            "status": "blocked",
            "release_scope": release_scope,
            "formal_release_allowed": False,
            "blockers": ["未知正式交付范围"],
            "manifest": {"used_sources": [], "manifest_sha256": ""},
        }

    manifest, blockers = _build_manifest(root, writing_evidence if isinstance(writing_evidence, dict) else {})
    ledger, ledger_sha256 = load_qualification_ledger(root)
    if ledger is None:
        blockers.append("缺少当前版本资料资格账本")
    contract_blockers = list(blockers)
    run_id = str(manifest.get("run_id") or "")
    prose_paths = (
        root / "文档" / "证据" / "运行" / run_id / "module_outputs" / "module_09_scene_prose.json",
    )
    prose = next((_read_json(path, {}) for path in prose_paths if path.is_file()), {})
    prose_records = [
        record
        for scene in prose.get("scenes", []) if isinstance(scene, dict)
        for record in scene.get("source_records", []) if isinstance(record, dict)
    ] if isinstance(prose, dict) else []
    duty_audit = audit_material_duty_records(prose_records, str(manifest.get("run_id") or ""), "正文")
    has_authored_scenes = isinstance(prose, dict) and any(
        isinstance(scene, dict) and (scene.get("paragraphs") or scene.get("source_records"))
        for scene in prose.get("scenes", [])
    )
    if has_authored_scenes and not prose_records:
        blockers.append("缺少本次运行正文资料职责回执")
    elif has_authored_scenes and not duty_audit["passed"]:
        blockers.extend("资料职责合同：" + item["reason"] for item in duty_audit["violations"])
    config = _read_json(root / "配置" / "project_config.json", {})
    confirmation = _read_json(root / "配置" / "project_source_confirmation.json", {})
    confirmation_report = _read_json(root / "文档" / "证据" / "项目来源确认报告.json", {})
    required_confirmation_fields = {"project_id", "genre_selection", "book_title", "world_stage", "mainline_conflict", "core_mystery", "protagonist", "chapter_plan"}
    confirmation_status = confirmation.get("status") if isinstance(confirmation, dict) else ""
    reported_status = confirmation_report.get("status") if isinstance(confirmation_report, dict) else ""
    formal_confirmation_allowed = (
        confirmation.get("allow_formal_pipeline") is True
        or confirmation_report.get("allow_formal_pipeline") is True
    ) if isinstance(confirmation, dict) and isinstance(confirmation_report, dict) else False
    if not isinstance(confirmation, dict) or confirmation.get("schema_version") != "project-source-confirmation-1.0" or confirmation_status != "confirmed":
        blockers.append("作者来源确认未完成；系统运行确认不得替代正式确认")
    elif confirmation.get("project_id") != config.get("project_id") or (reported_status and reported_status != "confirmed"):
        blockers.append("作者来源确认未绑定当前 project_id 或确认报告状态不一致")
    elif not formal_confirmation_allowed or not required_confirmation_fields.issubset({str(item) for item in confirmation.get("accepted_fields", [])}):
        blockers.append("作者来源确认未授予当前项目正式管道或未覆盖项目事实")
    if not isinstance(config, dict) or not config.get("type_combination"):
        blockers.append("项目尚未确认 type_combination；完整写作运行不得正式交付")
    elif isinstance(config.get("type_selection_policy"), dict) and config["type_selection_policy"].get("formal_release_allowed") is False:
        blockers.append("项目类型选择策略未授予正式交付许可")
    blockers.extend(_attestation_errors(root, manifest["used_sources"]))
    blockers.extend(_formal_contract_errors(manifest["used_sources"]))
    blockers.extend(_approval_errors(root, manifest))
    blockers.extend(_golden_three_chapter_errors(root))
    blockers.extend(_long_lineage_errors(root))
    blockers.extend(_character_performance_errors(root))
    blockers = list(dict.fromkeys(blockers))
    capability_layers = _capability_layers(root, manifest, contract_blockers, blockers)
    return {
        "status": "approved" if not blockers else "blocked",
        "release_scope": release_scope,
        "formal_release_allowed": not blockers,
        "delivery_ready": not blockers,
        "delivery_status": capability_layers["release_status"],
        "contract_passed": capability_layers["contract_passed"]["passed"],
        "source_evidence_passed": capability_layers["source_evidence_passed"]["passed"],
        "structural_review_passed": capability_layers["structural_review_passed"]["passed"],
        "literary_review_status": capability_layers["literary_review_status"],
        "capability_layers": capability_layers,
        "material_duty_audit": duty_audit,
        "contract_registry_version": CONTRACT_VERSION,
        "contract_field_version": CONTRACT_FIELD_VERSION,
        "qualification_ledger_sha256": ledger_sha256,
        "blockers": blockers,
        "manifest": manifest,
    }
