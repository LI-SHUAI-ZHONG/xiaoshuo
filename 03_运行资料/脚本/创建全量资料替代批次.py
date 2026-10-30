"""Create a new active prose batch without altering frozen historical consumption."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from 全量资料历史消费隔离 import REGISTRY_FILE
from 全量资料输入与正文授权 import authorized_bindings


PLAN_FILE = "全量资料正文生产编排.json"
QUEUE_FILE = "全量资料正文生产队列.jsonl"
BATCH_FILE = "全量资料正文生产批次.jsonl"
AUTHORIZATION_FILE = "全量资料替代批次授权.json"
SCHEMA_VERSION = "full-source-replacement-prose-plan-1.0"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _text(value: Any) -> str:
    return str(value or "").strip()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"替代生产队列包含无法解析的 JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError("替代生产队列的每行必须是对象")
        rows.append(row)
    return rows


def create(project_root: str | Path, replacement_batch_id: str = "RPL-20260814-01") -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    authorization = _read(evidence / AUTHORIZATION_FILE, {})
    if authorization.get("status") != "authorized" or authorization.get("authorized_by") != "project_owner":
        raise ValueError("缺少项目所有者对替代正文批次的明确授权")

    historical_ids = {
        _text(row.get("consumption_id"))
        for row in _read(evidence / REGISTRY_FILE, {}).get("entries", [])
        if isinstance(row, dict) and row.get("quarantine_status") == "historical_unverified_nonrelease"
    }
    bindings_document = _read(evidence / "全量资料解释词创作绑定.json", {})
    bindings = [row for row in bindings_document.get("records", []) if isinstance(row, dict)]
    grants = authorized_bindings(root, bindings)
    records = _jsonl(evidence / QUEUE_FILE)
    if not records:
        raise ValueError("当前替代生产队列没有可回读记录")

    expected_ids = {f"{replacement_batch_id}-{old_id}" for old_id in historical_ids}
    observed_ids = [_text(row.get("consumption_id")) for row in records]
    if len(observed_ids) != len(set(observed_ids)):
        raise ValueError("替代生产队列存在重复 consumption_id")
    if set(observed_ids) != expected_ids:
        missing = sorted(expected_ids - set(observed_ids))
        unexpected = sorted(set(observed_ids) - expected_ids)
        raise ValueError(f"替代生产队列与历史隔离清单不一一对应: missing={missing}, unexpected={unexpected}")

    for replacement in records:
        old_id = _text(replacement.get("replaces_historical_consumption_id"))
        binding_id = _text(replacement.get("binding_id"))
        if old_id not in historical_ids:
            raise ValueError(f"替代候选不回链到已冻结历史记录: {replacement.get('consumption_id')}")
        if _text(replacement.get("consumption_id")) != f"{replacement_batch_id}-{old_id}":
            raise ValueError(f"替代候选 ID 不符合替代批次规则: {replacement.get('consumption_id')}")
        if _text(replacement.get("batch_id")) != f"{replacement_batch_id}-{_text(replacement.get('scene_id'))}":
            raise ValueError(f"替代候选批次 ID 不符合场景规则: {replacement.get('consumption_id')}")
        if binding_id not in grants:
            raise ValueError(f"替代候选 {old_id} 缺少当前逐条授权")
        if replacement.get("status") != "queued_for_authored_prose" or replacement.get("model_input_eligible") is not True or replacement.get("prose_write_allowed") is not True:
            raise ValueError(f"替代候选不具备已授权的候选生产状态: {replacement.get('consumption_id')}")

    plan = {
        "schema_version": "scene-to-release-quality-plan-1.0",
        "workflow_id": "authorized-historical-replacement-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_status": "draft_only",
        "formal_fact_status": "partially_confirmed",
        "status": "approved_for_model_candidate_generation",
        "model_input_allowed": True,
        "prose_write_allowed": True,
        "policy": "替代批次仅用于生成新的可审校候选。历史消费保持哈希冻结且不可发布；替代候选必须重新通过来源语义审校、具名文学审校、消费验证和正式发布门。",
        "replacement_batch_id": replacement_batch_id,
        "historical_consumption_ids": sorted(historical_ids),
        "records": records,
    }
    (evidence / PLAN_FILE).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evidence / QUEUE_FILE).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    batches: dict[str, list[str]] = {}
    for row in records:
        batches.setdefault(_text(row["batch_id"]), []).append(_text(row["consumption_id"]))
    (evidence / BATCH_FILE).write_text(
        "".join(json.dumps({"batch_id": batch_id, "consumption_ids": ids}, ensure_ascii=False) + "\n" for batch_id, ids in sorted(batches.items())),
        encoding="utf-8",
    )
    return {"status": "created", "replacement_batch_id": replacement_batch_id, "record_count": len(records)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--replacement-batch-id", default="RPL-20260814-01")
    args = parser.parse_args()
    print(json.dumps(create(args.project_root, args.replacement_batch_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())