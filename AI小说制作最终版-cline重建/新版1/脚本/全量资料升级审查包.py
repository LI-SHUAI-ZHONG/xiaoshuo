from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number} 必须为 JSON 对象")
            records.append(value)
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def build_review_package(root: str | Path, package_id: str) -> Path:
    project = Path(root).resolve()
    evidence = project / "文档" / "证据"
    archive = read_jsonl(evidence / "全量资料升级档案.jsonl")
    integrity = read_json(evidence / "全绑定来源完整性审计报告.json")
    output = project / "文档" / "证据" / "新版资料审查包" / package_id
    if output.exists():
        raise FileExistsError(f"审查包目录已存在，拒绝覆盖: {output}")
    by_binding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in archive:
        binding_id = str(record.get("binding_id", ""))
        if not binding_id:
            raise ValueError("升级档案存在空 binding_id")
        by_binding[binding_id].append(record)
    candidate_groups = []
    for binding_id, records in sorted(by_binding.items()):
        upgrade_statuses = sorted({str(record.get("upgrade", {}).get("application_status", "")) for record in records})
        review_statuses = sorted({str(record.get("upgrade", {}).get("literary_review_status", "")) for record in records})
        candidate_groups.append({
            "binding_id": binding_id,
            "candidate_count": len(records),
            "classification": "duplicate" if len(records) > 1 else "candidate_prose",
            "fact_merge_eligible": False,
            "required_human_decision": "reject_all_or_create_new_approved_fact_changeset",
            "application_statuses": upgrade_statuses,
            "literary_review_statuses": review_statuses,
            "candidates": [{
                "consumption_id": record.get("consumption_id"),
                "source": record.get("source"),
                "prose_location": record.get("upgrade", {}).get("prose_location"),
                "paragraph_sha256": record.get("upgrade", {}).get("paragraph_sha256"),
                "causal_contract": record.get("upgrade", {}).get("causal_contract"),
                "application_status": record.get("upgrade", {}).get("application_status"),
                "literary_review_status": record.get("upgrade", {}).get("literary_review_status"),
            } for record in records],
        })
    findings = integrity.get("quarantined_findings", [])
    if not isinstance(findings, list):
        raise ValueError("来源完整性审计 quarantined_findings 必须为数组")
    repair_queue = []
    for finding in findings:
        errors = finding.get("errors", [])
        if not isinstance(errors, list):
            errors = [str(errors)]
        repair_queue.append({
            "binding_id": finding.get("binding_id"),
            "source_id": finding.get("source_id"),
            "source_kind": finding.get("source_kind"),
            "source_ref": finding.get("source_ref"),
            "current_status": "quarantined",
            "errors": errors,
            "required_resolution": "补齐可核验来源、稳定对象标识或精确定位；重跑来源完整性审计后才可解除隔离。",
            "fact_merge_eligible": False,
        })
    duplicate_groups = [group for group in candidate_groups if group["classification"] == "duplicate"]
    error_counts = Counter(error for record in repair_queue for error in record["errors"])
    kind_counts = Counter(str(record.get("source_kind", "")) for record in repair_queue)
    write_jsonl(output / "候选正文裁决队列.jsonl", candidate_groups)
    write_jsonl(output / "来源隔离修复队列.jsonl", repair_queue)
    write_json(output / "正式事实变更集模板.json", {
        "schema_version": "approved-fact-changeset-1.0",
        "status": "template_only_not_approved",
        "changes": [],
        "required_change_fields": ["change_id", "status", "target", "expected_source_sha256", "anchor", "expected_anchor_sha256", "old_text", "new_text", "rationale"],
        "required_status": "approved_for_fact_merge",
        "policy": "候选正文不得直接复制到此文件。每条事实修订须由人工依据原始资料重新确定精确旧文本、新文本、唯一锚点、哈希与审批记录。",
    })
    write_json(output / "审查总览.json", {
        "schema_version": "material-upgrade-review-package-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "archive_record_count": len(archive),
        "candidate_group_count": len(candidate_groups),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_record_excess": sum(group["candidate_count"] - 1 for group in duplicate_groups),
        "all_archive_records_fact_merge_eligible": False,
        "quarantined_binding_count": len(repair_queue),
        "quarantine_by_source_kind": dict(sorted(kind_counts.items())),
        "quarantine_by_error": dict(sorted(error_counts.items())),
        "formal_fact_changeset": "正式事实变更集模板.json",
        "formal_release_allowed": False,
        "blockers": [
            "历史升级档案全部是待人工审校候选，不具备事实合并资格。",
            "重复候选组必须人工拒绝或基于原始资料建立新的正式事实变更，不能自动择一采用。",
            "来源隔离绑定在审计重新通过前不得作为正式事实。",
        ],
    })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="生成只读升级候选与来源隔离审查包")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--package-id", required=True)
    args = parser.parse_args()
    print(build_review_package(args.root, args.package_id))


if __name__ == "__main__":
    main()