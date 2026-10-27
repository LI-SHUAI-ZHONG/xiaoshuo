"""Validate authored full-source prose consumption without accepting templates."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED = ("prose_location", "paragraph_sha256", "trigger", "action", "observable_result", "cost_or_change", "semantic_support")
QUALITY_APPROVED = "semantic_editorial_review_passed"
INTERNAL_TERMS = (
    "source→target", "source", "target", "binding_id", "source_id", "资料ID", "创作合同",
    "读者能看到", "由受影响的故事对象", "可记录的选择", "前置状态", "语义支持",
)
PLACEHOLDER_PATTERN = re.compile(r"(?:\{[^{}]+\}|\[[^\[\]]+\]|<[^<>]+>|TODO|N/?A|待填写|未填写)", re.IGNORECASE)
REGISTRY_FILE = "全量资料历史消费隔离清单.json"


def _text_errors(row: dict[str, Any], assignment: dict[str, Any] | None, paragraph: str) -> list[str]:
    errors = []
    normalized = re.sub(r"\s+", "", paragraph)
    hits = [term for term in INTERNAL_TERMS if term.lower() in normalized.lower()]
    if hits:
        errors.append("正文泄漏内部术语或元叙述：" + ", ".join(hits))
    if PLACEHOLDER_PATTERN.search(paragraph):
        errors.append("正文含占位符或未填写字段")
    if not re.search(r"[。！？!?]$", normalized):
        errors.append("正文疑似截断，未以完整句末标点结束")
    if re.search(r"([。！？!?])\1", normalized):
        errors.append("正文含异常重复句末标点")
    for field in ("trigger", "action", "observable_result", "cost_or_change"):
        value = str(row.get(field) or "").strip()
        if value and value not in paragraph:
            errors.append(f"证据字段与正文不一致：{field}")
    if assignment:
        contract = assignment.get("causal_contract", {})
        anchor = str(contract.get("semantic_anchor") or "").strip()
        if len(anchor) >= 12 and anchor in paragraph:
            errors.append("正文复述资料或规则原文，未完成场景化转译")
    return errors


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _historical_ids(evidence: Path) -> set[str]:
    registry = _read(evidence / REGISTRY_FILE, {})
    return {
        str(row.get("consumption_id"))
        for row in registry.get("entries", [])
        if isinstance(row, dict)
        and row.get("quarantine_status") == "historical_unverified_nonrelease"
        and row.get("consumption_id")
    }


def _paragraph_from_location(root: Path, location: str) -> str:
    match = re.fullmatch(r"(.+)#lines\[(\d+)\]", location)
    if not match:
        return ""
    path = root / match.group(1)
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    line_number = int(match.group(2))
    return lines[line_number - 1] if 0 < line_number <= len(lines) else ""


def validate(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    plan = _read(evidence / "全量资料正文生产编排.json", {})
    realized = _read(evidence / "全量资料正文消费证据.json", {"records": []})
    scene_gates = plan.get("scene_formal_creation_gates", {})
    expected = {
        str(row.get("consumption_id")): row
        for row in plan.get("records", [])
        if isinstance(row, dict)
        and row.get("status") == "queued_for_authored_prose"
        and row.get("prose_write_allowed") is True
        and isinstance(scene_gates.get(row.get("scene_id")), dict)
        and scene_gates[row.get("scene_id")].get("formal_creation_allowed") is True
    }
    historical_ids = _historical_ids(evidence)
    findings: list[dict[str, Any]] = []
    passed: set[str] = set()
    for row in realized.get("records", []) if isinstance(realized, dict) else []:
        if not isinstance(row, dict):
            continue
        consumption_id = str(row.get("consumption_id") or "")
        if consumption_id in historical_ids:
            continue
        errors = []
        assignment = expected.get(consumption_id)
        if not assignment:
            # Historical and non-approved-scene evidence is deliberately kept
            # outside the active consumption verdict.
            continue
        elif assignment.get("binding_id") != row.get("binding_id") or assignment.get("source_id") != row.get("source_id"):
            errors.append("消费证据与生产编排的 binding_id/source_id 不一致")
        for field in REQUIRED:
            if not str(row.get(field) or "").strip():
                errors.append(f"缺少 {field}")
        paragraph = str(row.get("paragraph") or "")
        if len(paragraph) < 80:
            errors.append("正文段落不足80字，无法承载完整行动链")
        errors.extend(_text_errors(row, assignment, paragraph))
        if paragraph and row.get("paragraph_sha256") != hashlib.sha256(paragraph.encode("utf-8")).hexdigest():
            errors.append("正文段落哈希不一致")
        located_paragraph = _paragraph_from_location(root, str(row.get("prose_location") or ""))
        if not located_paragraph:
            errors.append("正文位置不存在或无法解析")
        elif located_paragraph != paragraph:
            errors.append("证据段落与正文位置不一致")
        if assignment:
            anchor = str(assignment.get("causal_contract", {}).get("semantic_anchor") or "")
            support = str(row.get("semantic_support") or "")
            if len(support) < 8 or not anchor:
                errors.append("缺少可审阅的来源语义支持")
        if row.get("quality_status") != QUALITY_APPROVED or row.get("literary_review_status") != QUALITY_APPROVED:
            errors.append("未通过来源语义与叙事质量审校，不得标记 prose_realized")
        if errors:
            findings.append({"consumption_id": consumption_id, "errors": errors})
        else:
            passed.add(consumption_id)
    missing = sorted(set(expected) - passed)
    scene_gate_results = {
        scene_id: scene_gates.get(scene_id, {})
        for scene_id in {str(row.get("scene_id")) for row in expected.values()}
    }
    for scene_id, gate in scene_gate_results.items():
        if not gate["formal_creation_allowed"]:
            findings.append({"consumption_id": None, "errors": [f"场景正式创作门未通过（{scene_id}）：" + "; ".join(gate["blockers"]) ]})
    report = {
        "schema_version": "full-source-prose-consumption-validation-1.0",
        "policy": "不得以编排、模板或资料关键词替代正文消费；每条记录必须有独立段落、因果字段、语义支持、可复算哈希，并通过来源语义与叙事质量审校。",
        "planned_count": len(expected),
        "prose_realized_count": len(passed),
        "queued_or_missing_count": len(missing),
        "status_counts": dict(Counter({"prose_realized": len(passed), "queued_or_missing": len(missing), "invalid_evidence": len(findings)})),
        "missing_consumption_ids": missing,
        "findings": findings,
        "scene_formal_creation_gates": scene_gate_results,
        "status": "passed" if expected and not missing and not findings else "in_progress",
    }
    target = evidence / "全量资料正文消费验证报告.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = validate(args.project_root)
    print(json.dumps({"status": report["status"], "planned_count": report["planned_count"], "prose_realized_count": report["prose_realized_count"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())