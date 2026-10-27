from __future__ import annotations

import argparse
import ast
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCATOR_ERROR = "结构化 source_ref 的 locator 未精确命中对象标题"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repair_library_locators(root: str | Path, repair_id: str) -> Path:
    project = Path(root).resolve()
    evidence = project / "文档" / "证据"
    bindings_path = evidence / "全量资料解释词创作绑定.json"
    audit_path = evidence / "全绑定来源完整性审计报告.json"
    library_path = project / "原始资料" / "资料库.txt"
    output = evidence / "来源完整性修复" / repair_id
    if output.exists():
        raise FileExistsError(f"修复输出已存在，拒绝覆盖: {output}")
    bindings_document = read_json(bindings_path)
    bindings = bindings_document.get("records", [])
    if not isinstance(bindings, list):
        raise ValueError("绑定文件 records 必须为数组")
    audit = read_json(audit_path)
    findings = audit.get("quarantined_findings", [])
    library_text = library_path.read_text(encoding="utf-8-sig")
    lines = library_text.splitlines()
    targets = {str(item["binding_id"]): item for item in findings if item.get("source_kind") == "资料库" and LOCATOR_ERROR in item.get("errors", [])}
    repaired, ledger = deepcopy(bindings_document), []
    records_by_id = {str(record.get("binding_id")): record for record in repaired["records"]}
    for binding_id, finding in sorted(targets.items()):
        record = records_by_id.get(binding_id)
        if not record:
            raise ValueError(f"修复目标缺少绑定: {binding_id}")
        source_ref = ast.literal_eval(str(record.get("source_ref", "")))
        line_start = int(source_ref["line_start"])
        actual_heading = lines[line_start - 1].strip()
        expected_heading = "## 板块" + str(record["source_id"]).replace("_", " ", 1)
        if actual_heading != expected_heading:
            raise ValueError(f"{binding_id} 标题不匹配: {actual_heading!r} != {expected_heading!r}")
        old_ref = record["source_ref"]
        source_ref["locator"] = actual_heading.removeprefix("## ")
        record["source_ref"] = repr(source_ref)
        record.setdefault("source_ref_repair", {})
        record["source_ref_repair"] = {"repair_id": repair_id, "old_source_ref": old_ref, "verified_heading": actual_heading, "verified_line": line_start, "source_sha256": sha256_text(library_text)}
        ledger.append({"binding_id": binding_id, "status": "passed", "old_source_ref": old_ref, "new_source_ref": record["source_ref"], "verified_heading": actual_heading, "verified_line": line_start})
    repaired["derived_from"] = {"path": str(bindings_path), "sha256": sha256_text(bindings_path.read_text(encoding="utf-8-sig")), "repair_id": repair_id}
    repaired["generated_at"] = datetime.now(timezone.utc).isoformat()
    revised_audit = deepcopy(audit)
    revised_audit["derived_from"] = {"path": str(audit_path), "repair_id": repair_id}
    revised_audit["generated_at"] = datetime.now(timezone.utc).isoformat()
    revised_audit["quarantined_findings"] = [item for item in findings if str(item.get("binding_id")) not in targets]
    revised_audit["status_counts"]["passed"] += len(targets)
    revised_audit["status_counts"]["quarantined"] -= len(targets)
    revised_audit["source_kind_status_counts"]["资料库"]["passed"] += len(targets)
    revised_audit["source_kind_status_counts"]["资料库"]["quarantined"] -= len(targets)
    revised_audit["partial_repair"] = {"status": "passed", "repaired_binding_count": len(ledger), "remaining_quarantined_binding_count": len(revised_audit["quarantined_findings"]), "scope": "仅修复并复核资料库标题定位；未修改原始资料。"}
    write_json(output / "全量资料解释词创作绑定.资料库定位修复.json", repaired)
    write_json(output / "全绑定来源完整性审计报告.资料库定位修复.json", revised_audit)
    write_json(output / "资料库定位修复账本.json", {"repair_id": repair_id, "source_file": str(library_path), "source_sha256": sha256_text(library_text), "repaired": ledger})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="修复已验证的资料库绑定标题定位，不修改原始资料")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repair-id", required=True)
    args = parser.parse_args()
    print(repair_library_locators(args.root, args.repair_id))


if __name__ == "__main__":
    main()