from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MISSING_ID_ERROR = "类型连接对象缺少可核验标识"
INVALID_ARRAY_ERROR = "source_ref 文本数组或下标无效"
SECTION_PATTERN = re.compile(r"^SOURCE: (.+?)\r?\n=+\r?\n", re.MULTILINE)
REFERENCE_PATTERN = re.compile(r"^原始资料/类型连接\.txt:(.+)\[(\d+)\]$")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_sections(text: str) -> dict[str, Any]:
    matches = list(SECTION_PATTERN.finditer(text))
    sections = {}
    for index, match in enumerate(matches):
        body = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip()
        value = json.loads(body)
        if isinstance(value, (list, dict)):
            sections[match.group(1).strip()] = value
    return sections


def stable_identifier(value: dict[str, Any]) -> tuple[str, str] | None:
    candidates = [(key, item) for key, item in value.items() if key.endswith("_id") and isinstance(item, str) and item.strip()]
    return sorted(candidates)[0] if candidates else None


def repair_type_connection_identity(root: str | Path, repair_id: str, bindings_path: str | Path | None = None, audit_path: str | Path | None = None) -> Path:
    project = Path(root).resolve()
    evidence = project / "文档" / "证据"
    bindings_path = Path(bindings_path) if bindings_path else evidence / "全量资料解释词创作绑定.json"
    audit_path = Path(audit_path) if audit_path else evidence / "全绑定来源完整性审计报告.json"
    source_path = project / "原始资料" / "类型连接.txt"
    output = evidence / "来源完整性修复" / repair_id
    if output.exists():
        raise FileExistsError(f"修复输出已存在，拒绝覆盖: {output}")
    bindings_document = read_json(bindings_path)
    audit = read_json(audit_path)
    source_bytes = source_path.read_bytes()
    sections = source_sections(source_bytes.decode("utf-8-sig"))
    records_by_id = {str(record.get("binding_id")): record for record in bindings_document.get("records", [])}
    repaired_document, revised_audit = deepcopy(bindings_document), deepcopy(audit)
    repaired_by_id = {str(record.get("binding_id")): record for record in repaired_document["records"]}
    remaining, ledger, unresolved = [], [], []
    for finding in audit.get("quarantined_findings", []):
        if finding.get("source_kind") != "类型连接" or not ({MISSING_ID_ERROR, INVALID_ARRAY_ERROR} & set(finding.get("errors", []))):
            remaining.append(finding); continue
        binding_id = str(finding.get("binding_id")); reference = REFERENCE_PATTERN.match(str(finding.get("source_ref", "")))
        if not reference or reference.group(1) not in sections:
            remaining.append(finding); unresolved.append({"binding_id": binding_id, "reason": "source_ref 无法解析到 JSON 数组"}); continue
        source_value, source_index = sections[reference.group(1)], int(reference.group(2))
        if isinstance(source_value, list):
            if source_index < 1 or source_index > len(source_value) or not isinstance(source_value[source_index - 1], dict):
                remaining.append(finding); unresolved.append({"binding_id": binding_id, "reason": "数组下标未命中对象"}); continue
            item, location_kind = source_value[source_index - 1], "array_item"
        elif isinstance(source_value, dict) and source_index == 1:
            item, location_kind = source_value, "root_object"
        else:
            remaining.append(finding); unresolved.append({"binding_id": binding_id, "reason": "对象根引用必须使用 [1]"}); continue
        identifier = stable_identifier(item)
        if binding_id not in repaired_by_id:
            remaining.append(finding); unresolved.append({"binding_id": binding_id, "reason": "对象没有稳定业务 ID 或绑定缺失"}); continue
        object_sha256 = sha256_bytes(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        identity = f"type-connection:{reference.group(1)}:{location_kind}:{source_index}:{object_sha256}"
        repair = {"repair_id": repair_id, "source_file_sha256": sha256_bytes(source_bytes), "source_section": reference.group(1), "location_kind": location_kind, "source_index": source_index, "stable_source_identity": identity, "canonical_object_sha256": object_sha256}
        if identifier:
            repair["business_id_field"], repair["business_id"] = identifier
        repaired_by_id[binding_id]["source_identity_repair"] = repair
        ledger.append({"binding_id": binding_id, "status": "passed", **repair})
    if not ledger:
        raise ValueError("未找到可回读且具有稳定业务 ID 的类型连接隔离项")
    revised_audit["quarantined_findings"] = remaining
    revised_audit["status_counts"]["passed"] += len(ledger)
    revised_audit["status_counts"]["quarantined"] -= len(ledger)
    revised_audit["source_kind_status_counts"]["类型连接"]["passed"] += len(ledger)
    revised_audit["source_kind_status_counts"]["类型连接"]["quarantined"] -= len(ledger)
    revised_audit["status"] = "passed" if not remaining else "quarantined"
    revised_audit["generated_at"] = datetime.now(timezone.utc).isoformat()
    revised_audit["derived_from"] = {"bindings_path": str(bindings_path), "audit_path": str(audit_path), "repair_id": repair_id}
    revised_audit["partial_repair"] = {"status": "passed", "repaired_binding_count": len(ledger), "remaining_quarantined_binding_count": len(remaining), "unresolved": unresolved, "policy": "仅当来源分段、数组元素或 [1] 对象根、规范对象哈希全部可回读时解除隔离；稳定身份由这些证据共同构成，业务 ID 仅为可选附加证据。"}
    repaired_document["generated_at"] = datetime.now(timezone.utc).isoformat()
    repaired_document["derived_from"] = {"path": str(bindings_path), "repair_id": repair_id}
    write_json(output / "全量资料解释词创作绑定.类型连接身份修复.json", repaired_document)
    write_json(output / "全绑定来源完整性审计报告.类型连接身份修复.json", revised_audit)
    write_json(output / "类型连接身份修复账本.json", {"repair_id": repair_id, "source_file": str(source_path), "source_sha256": sha256_bytes(source_bytes), "repaired": ledger, "unresolved": unresolved})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="为可回读类型连接补充稳定身份和对象哈希，不修改原始资料")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repair-id", required=True)
    parser.add_argument("--bindings-path")
    parser.add_argument("--audit-path")
    args = parser.parse_args()
    print(repair_type_connection_identity(args.root, args.repair_id, args.bindings_path, args.audit_path))


if __name__ == "__main__":
    main()