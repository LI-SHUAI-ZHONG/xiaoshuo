"""Run a bounded model review of source-qualification evidence.

Model conclusions are recommendations for human review only. This module never
changes source qualification, project selection, fact admission, model-input,
or prose-writing permissions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from 文本生成模型 import TextGenerationError, generate_json


SCHEMA_VERSION = "model-assisted-source-qualification-review-1.0"
SOURCE_FILE_BY_KIND = {
    "资料库": "资料库.txt", "类型系统": "类型系统.txt", "类型系统来源块": "类型系统.txt",
    "类型连接": "类型连接.txt", "动态网络": "动态网络.txt", "静态网络": "静态网络.txt", "锚点网络": "锚点网络.txt",
}
ALLOWED_RECOMMENDATIONS = {"insufficient_evidence", "ready_for_human_qualification_review"}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根对象必须为对象: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evidence_package(kind: str, quality: dict[str, Any], snapshot: dict[str, Any], binding_count: int) -> dict[str, Any]:
    return {
        "source_kind": kind,
        "binding_count": binding_count,
        "evidence": [
            {"evidence_id": "E1", "name": "input_snapshot", "value": snapshot},
            {"evidence_id": "E2", "name": "parse_and_coverage", "value": {
                key: quality.get(key) for key in ("parse_status", "extractable_rate", "identity_coverage", "evidence_coverage", "source_report_status", "usage_level")
            }},
            {"evidence_id": "E3", "name": "known_missing_fields", "value": quality.get("missing_fields", [])},
            {"evidence_id": "E4", "name": "governance_evidence", "value": quality.get("governance_evidence", {})},
            {"evidence_id": "E5", "name": "required_improvements", "value": quality.get("improvement_actions", [])},
            {"evidence_id": "E6", "name": "project_source_confirmation", "value": "pending_or_unconfirmed"},
        ],
    }


def _system_prompt() -> str:
    return """你是资料治理复核助手。只依据用户提供的 evidence 数组评估“是否可提交人工来源资格复核”。
不得声称读取了未提供的资料，不得推断作者、版权、版本或项目许可。输出严格 JSON：
{"recommendation":"insufficient_evidence|ready_for_human_qualification_review","confidence":"low|medium|high","evidence_ids":["E1"],"rationale":"简短中文依据","blocking_gaps":["缺口"],"human_review_actions":["动作"]}
只允许引用输入中存在的 evidence_id。没有来源确认、版本、责任人或适用范围证据时，必须 recommendation=insufficient_evidence。"""


def _validate_model_result(value: Any, evidence_ids: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("模型结果不是 JSON 对象")
    recommendation = value.get("recommendation")
    cited = value.get("evidence_ids")
    if recommendation not in ALLOWED_RECOMMENDATIONS:
        raise ValueError("模型 recommendation 不在允许集合")
    if not isinstance(cited, list) or not cited or any(not isinstance(item, str) or item not in evidence_ids for item in cited):
        raise ValueError("模型 evidence_ids 缺失或引用了输入外证据")
    for field in ("rationale",):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"模型缺少 {field}")
    for field in ("blocking_gaps", "human_review_actions"):
        if not isinstance(value.get(field), list) or any(not isinstance(item, str) for item in value[field]):
            raise ValueError(f"模型 {field} 格式无效")
    if value.get("confidence") not in {"low", "medium", "high"}:
        raise ValueError("模型 confidence 无效")
    return value


def _normalize_recommendation(value: Any) -> dict[str, Any]:
    """Unknown model wording is conservatively treated as an evidence shortfall."""
    if not isinstance(value, dict):
        return value
    if value.get("recommendation") in ALLOWED_RECOMMENDATIONS:
        return value
    normalized = dict(value)
    # qwen may echo the enum declaration verbatim; its first alternative is
    # the required conservative disposition in this policy.
    if str(value.get("recommendation", "")).split("|")[0] == "insufficient_evidence":
        normalized["recommendation"] = "insufficient_evidence"
        return normalized
    normalized["recommendation"] = "insufficient_evidence"
    return normalized


def _constrain_recommendation(value: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    """Enforce the evidence gate even if the model uses optimistic wording."""
    confirmation = next(item["value"] for item in package["evidence"] if item["evidence_id"] == "E6")
    if confirmation == "pending_or_unconfirmed":
        value = dict(value)
        value["recommendation"] = "insufficient_evidence"
        gaps = list(value["blocking_gaps"])
        if "缺少来源、版本、责任人和适用范围的可核验证据" not in gaps:
            gaps.append("缺少来源、版本、责任人和适用范围的可核验证据")
        value["blocking_gaps"] = gaps
    return value


def review(root: str | Path, execute_model: bool = False, generator: Callable[[str | Path, str, str], tuple[dict[str, Any], dict[str, str]]] = generate_json) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    inventory_path = evidence / "严格资料升级" / "全量资料激活前置条件盘点" / "全量资料激活前置条件盘点报告.json"
    quality_path = evidence / "来源质量自主分析报告.json"
    inventory, quality_report = _read_json(inventory_path), _read_json(quality_path)
    snapshots = inventory.get("input_snapshots", {})
    quality_by_file = {str(row.get("source")): row for row in quality_report.get("sources", []) if isinstance(row, dict)}
    binding_counts = {kind: sum(counts.values()) for kind, counts in inventory.get("by_source_kind", {}).items()}
    records = []
    for kind in sorted(SOURCE_FILE_BY_KIND):
        source_file = SOURCE_FILE_BY_KIND[kind]
        quality = quality_by_file.get(source_file)
        snapshot = snapshots.get(kind) or snapshots.get("类型系统" if kind == "类型系统来源块" else kind)
        if not isinstance(quality, dict) or not isinstance(snapshot, dict):
            raise ValueError(f"缺少 {kind} 的质量或快照证据")
        package = _evidence_package(kind, quality, snapshot, binding_counts.get(kind, 0))
        evidence_ids = {item["evidence_id"] for item in package["evidence"]}
        model_result: dict[str, Any] | None = None
        raw_model_assessment: dict[str, Any] | None = None
        model_metadata: dict[str, str] | None = None
        error: str | None = None
        if execute_model:
            try:
                raw_model_assessment, model_metadata = generator(root, _system_prompt(), json.dumps(package, ensure_ascii=False))
                normalized_model_assessment = _normalize_recommendation(raw_model_assessment)
                model_result = _constrain_recommendation(_validate_model_result(normalized_model_assessment, evidence_ids), package)
            except (TextGenerationError, ValueError) as exc:
                error = str(exc)
        records.append({
            "schema_version": SCHEMA_VERSION,
            "source_kind": kind,
            "source_file": source_file,
            "input_snapshot_sha256": snapshot.get("sha256"),
            "binding_count": binding_counts.get(kind, 0),
            "assessment_execution_status": "completed" if model_result else ("model_error" if execute_model else "not_executed"),
            "evidence_package": package,
            "model_assessment": model_result,
            "raw_model_assessment": raw_model_assessment,
            "model_metadata": model_metadata,
            "model_error": error,
            "source_qualification_status": "not_assessed",
            "project_selection_status": "not_assessed",
            "formal_fact_eligible": False,
            "model_input_eligible": False,
            "prose_write_allowed": False,
        })
    permission_failures = sum(any(row[field] is not expected for field, expected in (("formal_fact_eligible", False), ("model_input_eligible", False), ("prose_write_allowed", False))) or row["source_qualification_status"] != "not_assessed" or row["project_selection_status"] != "not_assessed" for row in records)
    if permission_failures:
        raise ValueError("模型资格评估权限隔离失败")
    output = evidence / "严格资料升级" / "模型辅助来源资格评估"
    staging = output.parent / ".模型辅助来源资格评估_staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "model_assisted_evidence_review_only; no_source_qualification_or_usage_permission_modified",
        "model_execution_requested": execute_model,
        "input_reports": {"inventory": str(inventory_path.relative_to(root)).replace("\\", "/"), "quality": str(quality_path.relative_to(root)).replace("\\", "/"), "inventory_sha256": _sha256(inventory_path), "quality_sha256": _sha256(quality_path)},
        "source_record_count": len(records),
        "execution_status_counts": dict(sorted(Counter(row["assessment_execution_status"] for row in records).items())),
        "recommendation_counts": dict(sorted(Counter((row["model_assessment"] or {}).get("recommendation", "not_available") for row in records).items())),
        "permission_isolation_failure_count": permission_failures,
        "formal_fact_eligible_count": 0,
        "model_input_eligible_count": 0,
        "prose_write_allowed": False,
        "policy": "模型意见仅用于人工资格复核准备；不得直接变更来源资格、项目选择、正式事实、模型输入或正文写作权限。",
    }
    (staging / "模型辅助来源资格评估报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (staging / "模型辅助来源资格评估清单.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    shutil.rmtree(output, ignore_errors=True)
    staging.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--execute-model", action="store_true")
    args = parser.parse_args()
    print(json.dumps(review(args.project_root, args.execute_model), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())