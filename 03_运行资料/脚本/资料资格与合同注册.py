"""Shared contracts and conservative source qualification ledger.

Qualification is derived from current records, never from historical counts or
the existence of a binding.  The ledger is intentionally read-only so it can be
used by admission, activation, and audit stages without becoming an authority
producer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "material-contract-registry-1.0"
CONTRACT_FIELD_VERSION = "material-contract-fields-1.0"
LEDGER_SCHEMA_VERSION = "source-qualification-ledger-1.0"
CONTRACTS = {
    "runtime_admission_contract": {
        "required_fields": ("binding_id", "source_id", "source_kind", "source_ref"),
        "meaning": "允许进入当前运行资料评估，不代表进入正文",
    },
    "authorization_contract": {
        "required_fields": ("model_input_eligible", "activation_conditions_met", "activation_evidence"),
        "meaning": "允许编译为当前场景任务，不代表正文已消费",
    },
    "formal_authorization_contract": {
        "required_fields": ("source_id", "source_ref_sha256", "source_content_sha256"),
        "meaning": "正式交付的来源认证条件，不由系统准入代填",
    },
}

# The nested ``contracts`` object is the canonical representation.  The flat
# fields remain readable as a legacy representation, but are never allowed to
# silently override a canonical value.
_CONTRACT_FIELD_ALIASES = {
    "runtime_admission_contract": {
        "binding_id": ("binding_id",), "source_id": ("source_id",),
        "source_kind": ("source_kind",), "source_ref": ("source_ref",),
    },
    "authorization_contract": {
        "model_input_eligible": ("model_input_eligible",),
        "activation_conditions_met": ("activation_conditions_met",),
        "activation_evidence": ("activation_evidence",),
    },
    "formal_authorization_contract": {
        "source_id": ("source_id",),
        "source_ref_sha256": ("source_ref_sha256",),
        "source_content_sha256": ("source_content_sha256",),
    },
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _index_status(root: Path, row: dict[str, Any]) -> tuple[str, str]:
    """Use the current library index only when the row can be uniquely found."""
    if _text(row.get("source_kind")) != "资料库":
        return "registered", "非资料库条目由来源解析器负责定位"
    path = root / "文档" / "资料库索引.jsonl"
    if not path.is_file():
        return "pending", "缺少当前资料库索引"
    source_id = _text(row.get("source_id"))
    matches = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and _text(item.get("entry_id") or item.get("name")) == source_id:
            matches.append(item)
    if len(matches) != 1:
        return "pending", "资料库索引无法唯一定位当前 source_id"
    usage = matches[0].get("usage_method")
    if not isinstance(usage, dict) or usage.get("status") != "source_complete":
        return "pending", "资料库条目 usage_method 未达到 source_complete"
    return "source_complete", "当前资料库索引与 usage_method 均可复核"


def build_qualification_ledger(root: str | Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    ledger: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        binding_id = _text(row.get("binding_id"))
        source_id = _text(row.get("source_id"))
        missing = [field for field in CONTRACTS["runtime_admission_contract"]["required_fields"] if not row.get(field)]
        status, status_reason = _index_status(root_path, row)
        if not binding_id or not source_id:
            qualification = "registered"
            reason = "缺少稳定 binding_id 或 source_id"
        elif missing:
            qualification = "registered"
            reason = "运行准入合同缺少字段：" + ", ".join(missing)
        elif status == "pending":
            qualification = "pending"
            reason = status_reason
        elif row.get("navigation_only"):
            qualification = "navigation_only"
            reason = "记录显式标记为导航资料"
        elif row.get("research_only"):
            qualification = "research_only"
            reason = "记录显式标记为研究资料"
        elif status == "source_complete" or _text(row.get("source_kind")) != "资料库":
            qualification = "source_complete"
            reason = status_reason
        else:
            qualification = "registered"
            reason = status_reason
        executable = qualification == "source_complete" and bool(row.get("creation_binding"))
        ledger.append({
            "binding_id": binding_id, "source_id": source_id,
            "source_kind": _text(row.get("source_kind")),
            "qualification": qualification,
            "executable_entry": executable,
            "source_status_reason": reason,
            "excluded": not executable,
            "exclusion_reason": "" if executable else reason,
            "source_ref_sha256": _sha256(row.get("source_ref")),
            "fields_read": {
                "runtime_admission_contract": list(CONTRACTS["runtime_admission_contract"]["required_fields"]),
                "authorization_contract": list(CONTRACTS["authorization_contract"]["required_fields"]),
                "formal_authorization_contract": list(CONTRACTS["formal_authorization_contract"]["required_fields"]),
            },
        })
    counts = {key: sum(item["qualification"] == key for item in ledger) for key in ("registered", "source_complete", "executable_entry", "navigation_only", "research_only", "pending")}
    counts["executable_entry"] = sum(item["executable_entry"] for item in ledger)
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "contracts": CONTRACTS,
        "record_count": len(ledger),
        "counts": counts,
        "records": ledger,
        "ledger_sha256": _sha256(ledger),
        "policy": "资格集合由当前明细重算；selected、绑定数量和资料包存在性不得推导 executable_entry 或正文消费。",
    }


def load_qualification_ledger(root: str | Path) -> tuple[dict[str, Any] | None, str]:
    """Load the one current qualification ledger and return its file hash.

    Consumers must use this interface so a missing, malformed, or incompatible
    ledger cannot silently turn into an empty qualification set.
    """
    path = Path(root).expanduser().resolve() / "文档" / "证据" / "资料资格账本.json"
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, ""
    if not isinstance(value, dict) or value.get("schema_version") != LEDGER_SCHEMA_VERSION or not isinstance(value.get("records"), list):
        return None, hashlib.sha256(raw).hexdigest()
    return value, hashlib.sha256(raw).hexdigest()


def validate_contract_fields(row: dict[str, Any], contract_name: str) -> dict[str, Any]:
    resolved = resolve_contract_fields(row, contract_name)
    return {
        "passed": resolved["passed"], "missing": resolved["missing"],
        "conflicts": resolved["conflicts"], "contract_version": CONTRACT_VERSION,
        "field_version": CONTRACT_FIELD_VERSION, "version_error": resolved.get("version_error", ""), "contract": contract_name,
        "fields": resolved.get("fields", {}),
    }


def resolve_contract_fields(row: dict[str, Any], contract_name: str) -> dict[str, Any]:
    """Read one contract with deterministic canonical/legacy precedence.

    Canonical input is ``row['contracts'][name]['fields']``.  A flat row is a
    legacy input.  Both may coexist only when their values agree; otherwise the
    caller receives an explicit conflict instead of a silent fallback.
    """
    contract = CONTRACTS.get(contract_name)
    if not contract:
        return {"passed": False, "missing": [], "conflicts": [], "fields": {}, "error": "未知合同：" + contract_name}
    nested = row.get("contracts") if isinstance(row.get("contracts"), dict) else {}
    entry = nested.get(contract_name) if isinstance(nested.get(contract_name), dict) else {}
    canonical = entry.get("fields") if isinstance(entry.get("fields"), dict) else entry
    fields: dict[str, Any] = {}
    missing: list[str] = []
    conflicts: list[str] = []
    for field in contract["required_fields"]:
        canonical_present = field in canonical and canonical.get(field) not in (None, "", [], {})
        legacy_keys = _CONTRACT_FIELD_ALIASES.get(contract_name, {}).get(field, (field,))
        legacy_present = any(key in row and row.get(key) not in (None, "", [], {}) for key in legacy_keys)
        canonical_value = canonical.get(field) if canonical_present else None
        legacy_value = next((row.get(key) for key in legacy_keys if key in row and row.get(key) not in (None, "", [], {})), None)
        if canonical_present and legacy_present and canonical_value != legacy_value:
            conflicts.append(field)
        if canonical_present:
            fields[field] = canonical_value
        elif legacy_present:
            fields[field] = legacy_value
        else:
            missing.append(field)
    declared_version = entry.get("field_version") or entry.get("version")
    version_error = ""
    if declared_version and declared_version != CONTRACT_FIELD_VERSION:
        version_error = f"{contract_name} 字段版本不兼容：{declared_version}"
    return {
        "passed": not missing and not conflicts and not version_error,
        "missing": missing, "conflicts": conflicts, "fields": fields,
        "contract_version": CONTRACT_VERSION, "field_version": CONTRACT_FIELD_VERSION,
        "version_error": version_error,
    }