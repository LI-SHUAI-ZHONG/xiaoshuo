"""Default-deny admission for formal prose creation.

Authorization, runtime admission, semantic translation, or historical prose
consumption never satisfies this gate. A plan lock is created only from a
complete, validated full-source upgrade run and pins every downstream input.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCK_SCHEMA = "formal-creation-plan-lock-1.0"
UPGRADE_DIR = Path("文档") / "证据" / "全量资料升级运行"
STRICT_ACTIVITY_DIR = Path("文档") / "证据" / "严格连续资料升级运行"
LOCK_FILE = Path("文档") / "证据" / "正式创作计划锁.json"
UPGRADE_APPROVAL_FILE = Path("配置") / "formal_material_upgrade_approval.json"
SCENE_APPROVAL_FILE = Path("配置") / "scene_formal_creation_approval.json"
STRICT_AUDIT_SCHEMA = "strict-continuous-source-upgrade-final-audit-1.0"
SAFE_TERMINAL_STATES = {"validated_no_change", "validated_candidate"}


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_scene_formal_creation_gate(project_root: str | Path, scene_id: str, candidates: list[dict[str, Any]], grants: dict[str, Any]) -> dict[str, Any]:
    """Allow a specifically approved scene without treating it as full release."""
    root = Path(project_root).expanduser().resolve()
    approval = _read(root / SCENE_APPROVAL_FILE, {})
    blockers: list[str] = []
    if not isinstance(approval, dict) or approval.get("schema_version") != "scene-formal-creation-approval-1.0":
        blockers.append("缺少场景正式创作批准凭证")
    else:
        required_hashes = {
            "project_config_sha256": root / "配置" / "project_config.json",
            "scene_brief_sha256": root / "配置" / "首章场景创作简报.json",
            "binding_baseline_sha256": root / "文档" / "证据" / "全量资料解释词创作绑定.json",
            "authorization_audit_sha256": root / "文档" / "证据" / "全量资料输入与正文授权" / "授权审计报告.json",
        }
        if approval.get("status") != "approved" or scene_id not in approval.get("approved_scene_ids", []):
            blockers.append("场景未获得正式创作批准")
        if not str(approval.get("approved_by") or "").strip() or not str(approval.get("approved_at") or "").strip():
            blockers.append("场景正式创作批准凭证缺少审批人或时间")
        if approval.get("formal_release_allowed") is not False:
            blockers.append("场景创作批准不得授予正式发布许可")
        for field, path in required_hashes.items():
            if approval.get(field) != _sha256(path):
                blockers.append(f"场景批准输入哈希不匹配：{field}")
    if not candidates:
        blockers.append("场景没有可用的激活候选")
    for candidate in candidates:
        binding_id = str(candidate.get("binding_id") or "")
        activation = candidate.get("activation")
        provenance = candidate.get("source_provenance")
        contract = candidate.get("causal_contract")
        if candidate.get("scene_id") != scene_id or binding_id not in grants:
            blockers.append("场景候选不在逐条授权范围内")
            break
        if not isinstance(activation, dict) or not activation.get("activation_evidence") or not activation.get("matched_project_terms"):
            blockers.append("场景候选缺少激活证据或语义匹配")
            break
        if not isinstance(provenance, dict) or not str(provenance.get("source_ref") or "").strip():
            blockers.append("场景候选缺少来源溯源")
            break
        if not isinstance(contract, dict) or any(not str(contract.get(key) or "").strip() for key in ("semantic_anchor", "trigger", "required_action", "required_result", "required_cost_or_change")):
            blockers.append("场景候选缺少完整因果契约")
            break
    return {
        "status": "allowed" if not blockers else "blocked",
        "formal_creation_allowed": not blockers,
        "formal_release_allowed": False,
        "scene_id": scene_id,
        "candidate_count": len(candidates),
        "blockers": blockers,
    }


def _latest_run(root: Path) -> tuple[Path | None, dict[str, Any]]:
    directory = root / UPGRADE_DIR
    candidates = []
    if directory.is_dir():
        for path in directory.iterdir():
            manifest = _read(path / "manifest.json", {})
            if isinstance(manifest, dict) and manifest.get("run_id"):
                candidates.append((str(manifest["run_id"]), path, manifest))
    if not candidates:
        return None, {}
    _, path, manifest = sorted(candidates)[-1]
    return path, manifest


def _approved_run(root: Path, approval: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    run_id = str(approval.get("upgrade_run_id") or "").strip()
    if not run_id or Path(run_id).name != run_id:
        return None, {}
    path = root / UPGRADE_DIR / run_id
    manifest = _read(path / "manifest.json", {})
    return (path, manifest) if isinstance(manifest, dict) and manifest.get("run_id") == run_id else (None, {})


def _approved_activity(root: Path, approval: dict[str, Any]) -> tuple[Path | None, dict[str, Any], list[str]]:
    campaign_id = str(approval.get("strict_campaign_id") or "").strip()
    if not campaign_id or Path(campaign_id).name != campaign_id:
        return None, {}, ["严格连续活动批准凭证缺少有效活动 ID"]
    directory = root / STRICT_ACTIVITY_DIR / campaign_id
    state = _read(directory / "state.json", {})
    audit = _read(directory / "final-audit.json", {})
    batches = directory / "batches.jsonl"
    blockers: list[str] = []
    if not isinstance(state, dict) or not isinstance(audit, dict):
        return None, {}, ["严格连续活动缺少 state 或最终审核证据"]
    baseline = int(audit.get("baseline_binding_count") or 0)
    counts = audit.get("first_pass_status_counts") if isinstance(audit.get("first_pass_status_counts"), dict) else {}
    terminal_count = sum(int(counts.get(status, 0) or 0) for status in SAFE_TERMINAL_STATES)
    if audit.get("schema_version") != STRICT_AUDIT_SCHEMA or audit.get("campaign_id") != campaign_id:
        blockers.append("严格连续活动最终审核格式或活动 ID 不匹配")
    if audit.get("status") != "audited_complete" or audit.get("resume_start") != 0:
        blockers.append("严格连续活动不是从冻结基线起点完成的审核")
    if baseline <= 0 or audit.get("first_pass_record_count") != baseline or terminal_count != baseline:
        blockers.append("严格连续活动没有完整的安全终态覆盖")
    if any(int(counts.get(status, 0) or 0) for status in ("missing", "model_error", "quarantined")):
        blockers.append("严格连续活动存在未解决的缺失、模型失败或隔离记录")
    if audit.get("model_error_count") != 0 or audit.get("isolation_record_count") != 0 or audit.get("isolation_coverage_exact") is not True:
        blockers.append("严格连续活动异常处置证据不符合正式资格")
    if not batches.is_file() or audit.get("batches_sha256") != _sha256(batches):
        blockers.append("严格连续活动批次账本哈希不匹配")
    if (state.get("schema_version") != "strict-continuous-source-upgrade-1.0" or state.get("campaign_id") != campaign_id
            or state.get("status") != "audited_complete" or state.get("final_audit") != "final-audit.json"
            or state.get("baseline_binding_count") != baseline
            or state.get("binding_baseline_sha256") != audit.get("binding_baseline_sha256")):
        blockers.append("严格连续活动状态与最终审核不一致")
    if approval.get("strict_final_audit_sha256") != _sha256(directory / "final-audit.json"):
        blockers.append("正式事实批准凭证未精确绑定严格连续活动最终审核")
    return (directory, audit, blockers) if not blockers else (None, audit, blockers)


def validate_formal_creation_gate(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    blockers: list[str] = []
    approval = _read(root / UPGRADE_APPROVAL_FILE, {})
    approval_is_shaped = (
        isinstance(approval, dict)
        and approval.get("schema_version") == "formal-material-upgrade-approval-1.0"
        and (
            (bool(approval.get("upgrade_run_id")) and bool(approval.get("upgrade_manifest_sha256")))
            or (bool(approval.get("strict_campaign_id")) and bool(approval.get("strict_final_audit_sha256")))
        )
    )
    activity_requested = isinstance(approval, dict) and bool(approval.get("strict_campaign_id"))
    activity_path: Path | None = None
    if activity_requested:
        activity_path, manifest, activity_blockers = _approved_activity(root, approval)
        blockers.extend(activity_blockers)
        run_path = None
    else:
        run_path, manifest = _approved_run(root, approval) if approval_is_shaped else _latest_run(root)
    if activity_requested:
        if not approval_is_shaped or approval.get("status") != "approved" or not str(approval.get("approved_by") or "").strip() or not str(approval.get("approved_at") or "").strip():
            blockers.append("严格连续活动正式事实批准凭证无效")
    if not run_path and not activity_path and not blockers:
        blockers.append("缺少全量资料升级运行清单")
    elif run_path:
        baseline = int(manifest.get("baseline_binding_count") or 0)
        if manifest.get("complete_full_run") is not True or manifest.get("processed_count") != baseline or baseline <= 0:
            blockers.append("全量资料升级尚未覆盖全部基线绑定")
        counts = manifest.get("status_counts") if isinstance(manifest.get("status_counts"), dict) else {}
        if any(counts.get(state, 0) for state in ("quarantined", "model_error")):
            blockers.append("全量升级存在隔离或模型失败记录")
        if counts.get("validated_no_change", 0) + counts.get("validated_candidate", 0) != baseline:
            blockers.append("全量升级没有为每条绑定形成可验证终态")
        if not approval_is_shaped:
            blockers.append("缺少全量升级批次的正式事实批准凭证")
        elif approval.get("status") != "approved" or not str(approval.get("approved_by") or "").strip() or not str(approval.get("approved_at") or "").strip():
            blockers.append("全量升级批次正式事实批准凭证无效")
        elif approval.get("upgrade_run_id") != manifest.get("run_id") or approval.get("upgrade_manifest_sha256") != _sha256(run_path / "manifest.json"):
            blockers.append("正式事实批准凭证未精确绑定当前升级批次")
    lock = _read(root / LOCK_FILE, {})
    if not isinstance(lock, dict) or lock.get("schema_version") != LOCK_SCHEMA:
        blockers.append("缺少正式创作计划锁")
    else:
        for field, path in (("project_config_sha256", root / "配置" / "project_config.json"), ("binding_baseline_sha256", root / "文档" / "证据" / "全量资料解释词创作绑定.json")):
            if lock.get(field) != _sha256(path):
                blockers.append(f"计划锁输入哈希不匹配：{field}")
        evidence_sha256 = _sha256(run_path / "manifest.json") if run_path else (_sha256(activity_path / "final-audit.json") if activity_path else None)
        if evidence_sha256 and lock.get("upgrade_manifest_sha256") != evidence_sha256:
            blockers.append("计划锁未绑定当前升级批次")
        if lock.get("formal_creation_allowed") is not True:
            blockers.append("计划锁未授予正式创作许可")
    return {"status": "allowed" if not blockers else "blocked", "formal_creation_allowed": not blockers, "blockers": blockers, "upgrade_run_id": manifest.get("run_id"), "strict_campaign_id": manifest.get("campaign_id") if activity_requested else None}


def create_plan_lock(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    gate = validate_formal_creation_gate(root)
    non_lock_blockers = [item for item in gate["blockers"] if "计划锁" not in item]
    if non_lock_blockers:
        raise RuntimeError("正式创作计划锁拒绝创建：" + "; ".join(gate["blockers"]))
    approval = _read(root / UPGRADE_APPROVAL_FILE, {})
    activity_requested = bool(approval.get("strict_campaign_id"))
    if activity_requested:
        evidence_path, manifest, activity_blockers = _approved_activity(root, approval)
        if activity_blockers or evidence_path is None:
            raise RuntimeError("严格连续活动证据无效")
        evidence_hash = _sha256(evidence_path / "final-audit.json")
    else:
        evidence_path, manifest = _approved_run(root, approval)
        assert evidence_path is not None
        evidence_hash = _sha256(evidence_path / "manifest.json")
    config = _read(root / "配置" / "project_config.json", {})
    lock = {"schema_version": LOCK_SCHEMA, "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "project_id": config.get("project_id"), "upgrade_run_id": manifest.get("run_id"), "strict_campaign_id": manifest.get("campaign_id") if activity_requested else None, "upgrade_manifest_sha256": evidence_hash, "project_config_sha256": _sha256(root / "配置" / "project_config.json"), "binding_baseline_sha256": _sha256(root / "文档" / "证据" / "全量资料解释词创作绑定.json"), "type_combination": config.get("type_combination"), "chapter_plan": config.get("chapter_plan"), "chapter_plan_sha256": hashlib.sha256(json.dumps(config.get("chapter_plan"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(), "formal_creation_allowed": True, "formal_release_allowed": False}
    target = root / LOCK_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock