"""核对已吸收升级内容与同文件原版对象的对应关系。

本脚本只读当前 ``原始资料``，不会删除、移动或修改任何资料文件。
严格来源升级批次是审计/草稿记录，不会被误判为正文字段变更；
只有明确提供字段候选或对象替换值的记录才标记为可融合候选。
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATERIAL_DIR = ROOT / "原始资料"
OUTPUT_DIR = ROOT / "文档" / "合并升级"
START = "===== 缺失升级资料吸收开始 ====="
END = "===== 缺失升级资料吸收结束 ====="
PAYLOAD_MARKER = "===== 升级资料完整内容 ====="


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def has_any(value: Any, names: set[str]) -> bool:
    if isinstance(value, dict):
        if names.intersection(value):
            return True
        return any(has_any(item, names) for item in value.values())
    if isinstance(value, list):
        return any(has_any(item, names) for item in value)
    return False


def get_nested(record: dict[str, Any], *path: str) -> Any:
    value: Any = record
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def classify(record: Any) -> tuple[str, str]:
    if not isinstance(record, dict):
        return "unparsed", "升级 payload 不是 JSON 对象"
    if record.get("schema_version") == "strict-source-upgrade-batch-1.0":
        return "linked_audit_only", "严格升级方法明确禁止正文写入"
    if record.get("category") == "reused_unchanged":
        return "linked_unchanged", "升级方法判定原对象未变化，无需正文写入"
    if record.get("action") == "retain" and record.get("resolution") == "already_present_in_baseline":
        return "already_present", "升级内容已存在于对应原版对象，无需重复写入"
    if record.get("review_status") == "pending":
        return "pending_review", "存在字段候选但仍处于待审查状态"
    if has_any(record, {"candidate_value", "candidate_fields", "field_path", "upgrade_units", "changes"}):
        return "field_fusion_candidate", "存在字段级候选数据"
    if has_any(record, {"before", "after", "upgraded_object"}):
        return "object_fusion_candidate", "存在对象级替换数据"
    if record.get("replacement_mapping") or record.get("derived_original_object"):
        return "object_mapping_only", "只有原版对象定位，没有可写入字段值"
    return "unresolved", "未找到对象定位或字段候选"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for material in sorted(MATERIAL_DIR.glob("*.txt")):
        text = material.read_text(encoding="utf-8-sig", errors="replace")
        for sequence, block in enumerate(text.split(START)[1:], 1):
            body = block.split(END, 1)[0]
            if PAYLOAD_MARKER not in body:
                records.append({"material": material.name, "sequence": sequence, "status": "unparsed", "reason": "缺少升级 payload 分隔符"})
                continue
            header, payload_text = body.split(PAYLOAD_MARKER, 1)
            source = next((line.split(":", 1)[1].strip() for line in header.splitlines() if line.startswith("来源:")), None)
            method = next((line.split(":", 1)[1].strip() for line in header.splitlines() if line.startswith("升级方法/资料格式:")), None)
            try:
                payload = json.loads(payload_text.strip())
            except json.JSONDecodeError as exc:
                # 吸收脚本原样搬入了 JSONL/多行 Markdown。逐行解析 JSONL，
                # 不把“格式不同”误报成“升级内容无效”。
                jsonl_records = []
                for line_number, line in enumerate(payload_text.splitlines(), 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        jsonl_records = []
                        break
                    if isinstance(item, dict):
                        jsonl_records.append((line_number, item))
                if jsonl_records:
                    for line_number, item in jsonl_records:
                        status, reason = classify(item)
                        records.append({
                            "material": material.name,
                            "sequence": sequence,
                            "payload_line": line_number,
                            "method": method,
                            "source": source,
                            "source_id": item.get("source_id"),
                            "binding_id": item.get("binding_id"),
                            "upgrade_id": item.get("upgrade_id"),
                            "target_object_id": item.get("target_object_id"),
                            "field_path": item.get("field_path"),
                            "semantic_key": item.get("semantic_key"),
                            "resolution": item.get("resolution"),
                            "status": status,
                            "reason": reason,
                        })
                else:
                    records.append({"material": material.name, "sequence": sequence, "source": source, "method": method, "status": "unparsed", "reason": str(exc)})
                continue
            status, reason = classify(payload)
            mapping = payload.get("replacement_mapping", {}) if isinstance(payload, dict) else {}
            original = mapping.get("derived_original_object", {}) if isinstance(mapping, dict) else {}
            if not isinstance(original, dict):
                original = {}
            records.append({
                "material": material.name,
                "sequence": sequence,
                "method": method,
                "source": source,
                "source_id": payload.get("source_id") if isinstance(payload, dict) else None,
                "binding_id": payload.get("binding_id") if isinstance(payload, dict) else None,
                "upgrade_id": payload.get("upgrade_id") if isinstance(payload, dict) else None,
                "original_file": original.get("file"),
                "original_locator": original.get("locator") or original.get("source_block"),
                "original_object_sha256": mapping.get("derived_original_object_sha256") if isinstance(mapping, dict) else None,
                "status": status,
                "reason": reason,
            })
    summary = Counter(item["status"] for item in records)
    report = {
        "schema_version": "original-upgrade-correspondence-preview-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "read_only": True,
        "material_directory": str(MATERIAL_DIR),
        "record_count": len(records),
        "status_counts": dict(summary),
        "records_sha256": sha256(json.dumps(records, ensure_ascii=False, sort_keys=True)),
    }
    output = OUTPUT_DIR / "原版升级对应关系预览.json"
    output.write_text(json.dumps({"summary": report, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())