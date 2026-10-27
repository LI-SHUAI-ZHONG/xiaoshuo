# -*- coding: utf-8 -*-
"""统一的只读资料证据层。

所有创作运行都通过本模块取得资料证据。它不把候选网络记录升级为事实，
并且为每条证据保存来源文件、哈希、行号和原文片段，避免上下文丢失后只剩
source_trace ID 的假闭环。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


RAW_FILES = {
    "MOD-CAPABILITY": "资料库.txt",
    "MOD-TYPE": "类型系统.txt",
    "MOD-CONNECTION": "类型连接.txt",
    "MOD-STATIC": "静态网络.txt",
    "MOD-DYNAMIC": "动态网络.txt",
    "MOD-ANCHOR": "锚点网络.txt",
    "MOD-EXECUTION": "执行正文.txt",
    "MOD-INDEX-MAPPING": "索引调用映射.txt",
    "MOD-RUNTIME-STATE": "运行状态.json",
}

FORMAL_LEVELS = {"confirmed_raw", "cross_confirmed"}
BLOCKED_TERMS = ("template", "fixture", "pending", "unconfirmed", "candidate")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _terms(request: str) -> list[str]:
    values = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_.-]+", request.lower())
    return list(dict.fromkeys(value for value in values if len(value) > 1))


def _snippet(lines: list[str], line_no: int, radius: int = 2) -> str:
    start = max(0, line_no - 1 - radius)
    end = min(len(lines), line_no + radius)
    return "\n".join(lines[start:end]).strip()


def _status(text: str, evidence_level: str, source_ref: str = "") -> tuple[str, bool]:
    lowered = (text + " " + source_ref).lower()
    if any(term in lowered for term in BLOCKED_TERMS):
        return "candidate", False
    if evidence_level not in FORMAL_LEVELS:
        return "candidate", False
    return "selected", True


def _raw_evidence(root: Path, module_id: str, request: str, limit: int) -> list[dict[str, Any]]:
    name = RAW_FILES.get(module_id)
    if not name:
        return []
    path = root / "08_原始资料" / name
    if not path.is_file():
        return []
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    terms = _terms(request)
    hits: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        lowered = line.lower()
        matched = [term for term in terms if term in lowered]
        if not matched and number > 40:
            continue
        # For a module with no task-specific hit, retain only headings and the
        # first few non-empty records. This keeps large sources bounded while
        # proving the source was actually read.
        if not matched and number > 40:
            continue
        level = "confirmed_raw" if not any(word in lowered for word in BLOCKED_TERMS) else "unconfirmed"
        status, runtime_usable = _status(line, level, f"08_原始资料/{name}#L{number}")
        evidence_id = f"E-{module_id}-{number:06d}"
        hits.append({
            "evidence_id": evidence_id,
            "module_id": module_id,
            "source_path": f"08_原始资料/{name}",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "line_start": number,
            "line_end": min(len(lines), number + 4),
            "matched_terms": matched,
            "evidence_level": level,
            "status": status,
            "runtime_usable": runtime_usable,
            "text": _snippet(lines, number, 2),
        })
        if len(hits) >= limit:
            break
    return hits


def _json_records(root: Path, request: str, limit: int) -> list[dict[str, Any]]:
    contract_path = root / "00_资料索引" / "网络派生索引契约.json"
    if not contract_path.is_file():
        return []
    terms = _terms(request)
    results: list[dict[str, Any]] = []
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    for artifact in contract.get("artifacts", []):
        path = root / Path(artifact["path"])
        if not path.is_file() or artifact.get("metadata_only"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records = payload.get(artifact.get("record_path", ""), []) if artifact.get("record_path") else payload
        if isinstance(records, dict):
            records = list(records.values())
        if not isinstance(records, list):
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            blob = json.dumps(record, ensure_ascii=False).lower()
            if terms and not any(term in blob for term in terms):
                continue
            record_status = record.get("record_status", "")
            level = artifact.get("evidence_level", "unconfirmed")
            derived_valid = record.get("generated_from_static") is True and record.get("validation_status") == "derived_contract_validated" and record.get("derivation_contract") == "NET-DYNAMIC-DERIVATION-CONTRACT-1.0"
            usable = level in FORMAL_LEVELS and not record.get("needs_review") and record_status not in {"candidate", "generated_rule"} and (not record.get("generated_from_static") or derived_valid)
            results.append({
                "evidence_id": f"E-{artifact['id']}-{index + 1:06d}",
                "module_id": artifact["id"],
                "source_path": artifact["path"],
                "source_sha256": _sha(path),
                "record_index": index,
                "evidence_level": level,
                "status": "selected" if usable else "candidate",
                "runtime_usable": usable,
                "record": record,
            })
            if len(results) >= limit:
                return results
    return results


def build_evidence_bundle(root: Path, request: str, module_ids: list[str] | None = None, limit: int = 80) -> dict[str, Any]:
    module_ids = module_ids or list(RAW_FILES)
    evidence: list[dict[str, Any]] = []
    per_module = max(2, limit // max(1, len(module_ids)))
    for module_id in module_ids:
        evidence.extend(_raw_evidence(root, module_id, request, per_module))
    network_records = _json_records(root, request, max(limit, 120))
    evidence.extend(network_records)
    # Keep at least one network candidate visible in bounded bundles. A prefix
    # made only of raw lines can otherwise hide unresolved/generated records.
    if not any(item.get("status") == "candidate" for item in evidence) and network_records:
        candidate = next((item for item in network_records if item.get("status") == "candidate"), None)
        if candidate:
            evidence.append(candidate)
    selected_evidence = evidence[:limit]
    if not any(item.get("status") == "candidate" for item in selected_evidence):
        candidate = next((item for item in evidence if item.get("status") == "candidate"), None)
        if candidate and selected_evidence:
            selected_evidence[-1] = candidate
        elif candidate:
            selected_evidence.append(candidate)
    usable = [item for item in selected_evidence if item.get("runtime_usable")]
    return {
        "schema_version": "evidence-bundle-1.0",
        "request": request,
        "source_scope": {"raw_root": "08_原始资料", "external_paths_allowed": False},
        "evidence": selected_evidence,
        "usable_evidence_ids": [item["evidence_id"] for item in usable[:limit]],
        "candidate_evidence_ids": [item["evidence_id"] for item in selected_evidence if not item.get("runtime_usable")][:limit],
        "read_modules": sorted(set(item["module_id"] for item in evidence)),
        "status": "READY" if usable else "PARTIAL",
        "limitations": [
            "原始资料仍作为只读来源；候选、模板、fixture、needs_review 记录不得约束正文。",
            "证据包只提供可追溯材料，不替代模型对故事事实的综合和冲突裁决。",
        ],
    }


def validate_handoff(bundle: dict[str, Any], required_ids: list[str]) -> list[str]:
    available = {item.get("evidence_id") for item in bundle.get("evidence", [])}
    return [item for item in required_ids if item not in available]