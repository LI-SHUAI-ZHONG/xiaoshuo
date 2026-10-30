"""Validate non-forgeable receipts for the 2026-08-22--26 daily patch replay.

Pipeline-level tests prove the current isolated tree works.  They cannot prove
that historical patches were applied in order.  This validator intentionally
requires the latter evidence and never upgrades a missing receipt to success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "daily-main-material-patch-replay-receipts-1.0"
REQUIRED_DATES = ("2026-08-22", "2026-08-23", "2026-08-24", "2026-08-25", "2026-08-26")
RECEIPT_PATH = "文档/证据/20260822_20260826_逐日主资料补丁重放回执.json"
RECOVERY_STATUS_FIELDS = (
    "file_restored",
    "content_hash_verified",
    "source_reviewed",
    "creative_consumption_verified",
)


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def recovery_gate_status(statuses: Any) -> str:
    """Return the recovery gate without inferring any missing evidence."""
    if not isinstance(statuses, dict) or any(
        not isinstance(statuses.get(field), bool) for field in RECOVERY_STATUS_FIELDS
    ):
        return "blocked"
    return "verified" if all(statuses[field] for field in RECOVERY_STATUS_FIELDS) else "deferred"


def validate(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    path = root / RECEIPT_PATH
    document = _read(path, None)
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"schema_version": SCHEMA_VERSION, "status": "blocked", "receipt_path": RECEIPT_PATH,
                "required_dates": list(REQUIRED_DATES), "verified_dates": [],
                "errors": ["缺少或无法解析逐日主资料补丁重放回执"]}
    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append("回执 schema_version 不匹配")
    recovery_status = document.get("recovery_status")
    if not isinstance(recovery_status, dict):
        errors.append("缺少独立恢复状态 recovery_status")
    else:
        for field in RECOVERY_STATUS_FIELDS:
            if not isinstance(recovery_status.get(field), bool):
                errors.append(f"恢复状态 {field} 必须显式为布尔值")
    receipts = document.get("receipts")
    if not isinstance(receipts, list):
        errors.append("receipts 必须是数组")
        receipts = []
    ordered = sorted((item for item in receipts if isinstance(item, dict)), key=lambda item: item.get("sequence", -1))
    if len(ordered) != len(receipts):
        errors.append("receipts 含非对象条目")
    previous_post: str | None = None
    seen_dates: set[str] = set()
    for expected_sequence, receipt in enumerate(ordered, 1):
        label = f"回执#{expected_sequence}"
        if receipt.get("sequence") != expected_sequence:
            errors.append(f"{label} sequence 必须从 1 连续递增")
        date = receipt.get("date")
        if date not in REQUIRED_DATES:
            errors.append(f"{label} date 不在要求范围内")
        else:
            seen_dates.add(date)
        if not str(receipt.get("patch_id", "")).strip() or not _is_sha256(receipt.get("patch_sha256")):
            errors.append(f"{label} 缺少可校验的 patch_id/patch_sha256")
        if receipt.get("status") != "applied" or receipt.get("exit_code") != 0:
            errors.append(f"{label} 未记录成功应用（status=applied 且 exit_code=0）")
        pre_hash, post_hash = receipt.get("pre_state_sha256"), receipt.get("post_state_sha256")
        if not _is_sha256(pre_hash) or not _is_sha256(post_hash):
            errors.append(f"{label} 缺少前后状态 SHA-256")
        elif previous_post is not None and pre_hash.lower() != previous_post.lower():
            errors.append(f"{label} 的前状态哈希未衔接上一回执后状态哈希")
        if _is_sha256(post_hash):
            previous_post = post_hash
    missing_dates = [date for date in REQUIRED_DATES if date not in seen_dates]
    if missing_dates:
        errors.append("缺少每日成功回执：" + "、".join(missing_dates))
    final_state = document.get("final_state")
    if not isinstance(final_state, dict) or not isinstance(final_state.get("files"), list):
        errors.append("缺少可校验的 final_state.files")
    else:
        if previous_post is None or final_state.get("state_sha256", "").lower() != previous_post.lower():
            errors.append("最终状态哈希未与最后一条回执后状态哈希一致")
        for item in final_state["files"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not _is_sha256(item.get("sha256")):
                errors.append("final_state.files 含无效文件哈希条目")
                continue
            file_path = root / item["path"]
            if not file_path.is_file() or _sha256(file_path).lower() != item["sha256"].lower():
                errors.append(f"最终工作树文件哈希不匹配：{item['path']}")
    gate_status = recovery_gate_status(recovery_status)
    if gate_status == "blocked" and not errors:
        errors.append("恢复状态无法形成准入结论")
    return {"schema_version": SCHEMA_VERSION, "status": "verified" if not errors else "blocked",
            "receipt_path": RECEIPT_PATH, "required_dates": list(REQUIRED_DATES),
            "verified_dates": [] if errors else list(REQUIRED_DATES),
            "recovery_status": recovery_status if isinstance(recovery_status, dict) else {},
            "recovery_gate_status": gate_status,
            "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate daily main-material patch replay receipts.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    report = validate(parser.parse_args().project_root)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())