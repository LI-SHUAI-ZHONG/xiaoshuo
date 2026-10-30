"""Verify source bindings against scene cards and actual prose.

This validator is deliberately conservative. A binding is not prose evidence
just because its terms resemble a paragraph. The writer must emit a source_id
or binding_id in a scene/prose evidence record, and the evidence must point to
an existing scene and paragraph. Source quality is reported separately from
creative coverage so draft use cannot be promoted to formal delivery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from 项目执行边界 import source_permission_errors, validate_execution_contract

SOURCE_ROLE_SPECS: tuple[dict[str, str], ...] = (
    {"role": "library", "relative_path": "原始资料/资料库.txt", "format": "text", "required_markers": "资料库\u0000【定义】"},
    {"role": "type_system", "relative_path": "原始资料/类型系统.txt", "format": "text", "required_markers": "MASTER DOCUMENT ASSEMBLED FROM SOURCE FILES\u0000SOURCE:"},
    {"role": "type_connections", "relative_path": "原始资料/类型连接.txt", "format": "text", "required_markers": "MASTER DOCUMENT ASSEMBLED FROM SOURCE FILES\u0000SOURCE:"},
    {"role": "static_network", "relative_path": "原始资料/静态网络.txt", "format": "json", "required_markers": "source_index"},
    {"role": "dynamic_network", "relative_path": "原始资料/动态网络.txt", "format": "json", "required_markers": "动态网络连接_完整版"},
    {"role": "anchor_network", "relative_path": "原始资料/锚点网络.txt", "format": "text", "required_markers": "锚点网络\u0000具体锚点表"},
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("record_type") != "header":
            rows.append(value)
    return rows


def _source_role_markers(spec: dict[str, str]) -> list[str]:
    return [marker for marker in str(spec.get("required_markers") or "").split("\0") if marker]


def review_source_roles(
    project_root: str | Path,
    source_specs: tuple[dict[str, str], ...] = SOURCE_ROLE_SPECS,
    output_name: str = "逐角色资料审查报告.json",
) -> dict[str, Any]:
    """Audit source-role availability without treating source text as project fact."""
    root = Path(project_root).expanduser().resolve()
    records: list[dict[str, Any]] = []
    for spec in source_specs:
        relative_path = str(spec["relative_path"]).replace("\\", "/")
        path = (root / relative_path).resolve()
        record: dict[str, Any] = {
            "role": spec["role"],
            "relative_path": relative_path,
            "evidence_layer": "original_source",
            "required_markers": _source_role_markers(spec),
            "read_status": "",
            "status": "unconfirmed",
            "sha256": "",
            "locators": [],
            "reason": "",
            "formal_fact_usable": False,
        }
        if root not in path.parents or not path.is_file():
            record.update(read_status="read_error", reason="原始资料文件不存在或路径越界")
            records.append(record)
            continue
        try:
            payload = path.read_bytes()
            text = payload.decode("utf-8-sig")
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["read_status"] = "read"
        except (OSError, UnicodeError) as exc:
            record.update(read_status="read_error", reason=f"原始资料读取失败：{type(exc).__name__}")
            records.append(record)
            continue
        markers = record["required_markers"]
        if spec.get("format") == "json":
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                record.update(status="unconfirmed", reason="文件可读取但 JSON 结构无效，不能确认资料角色")
                records.append(record)
                continue
            if not isinstance(parsed, dict):
                record.update(status="unconfirmed", reason="文件可读取但 JSON 根对象不是映射，不能确认资料角色")
                records.append(record)
                continue
            present = [marker for marker in markers if marker in parsed]
            record["locators"] = [f"$.{marker}" for marker in present]
        else:
            lines = text.splitlines()
            present = [marker for marker in markers if marker in text]
            record["locators"] = [f"line:{next(index for index, line in enumerate(lines, 1) if marker in line)}" for marker in present]
        if len(present) == len(markers):
            record.update(status="confirmed", reason="成功读取且具备该资料角色的全部最小结构标识")
        elif not present:
            record.update(status="not_found", reason="成功读取但未找到该资料角色的任何最小结构标识")
        else:
            record.update(status="unconfirmed", reason="成功读取但资料角色结构不完整，不能支撑后续创作审查")
        records.append(record)
    counts = Counter(record["status"] for record in records)
    report = {
        "schema_version": "source-role-review-1.0",
        "generated_at": now(),
        "policy": "仅审查原始资料的可读取性和资料角色结构；不确认人物或项目事实，不授予正文或正式交付许可。",
        "status_counts": {status: counts.get(status, 0) for status in ("confirmed", "not_found", "unconfirmed")},
        "status": "passed" if counts.get("unconfirmed", 0) == 0 else "failed",
        "formal_fact_usable": False,
        "delivery_ready": False,
        "records": records,
    }
    output = root / "文档" / "证据" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["output"] = str(output)
    return report


def _evidence_rows(scene: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key in ("source_records", "source_evidence", "binding_evidence", "evidence"):
        value = scene.get(key)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))
    for paragraph in scene.get("paragraphs", []):
        if isinstance(paragraph, dict):
            value = paragraph.get("source_records") or paragraph.get("evidence") or []
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
    return rows


def _quality(root: Path) -> dict[str, Any]:
    registry = read_json(root / "文档" / "证据" / "资源注册表.json", {})
    confirmation = read_json(root / "配置" / "project_source_confirmation.json", None)
    resources = registry.get("resources", {}) if isinstance(registry, dict) else {}
    partial = sorted(name for name, item in resources.items() if isinstance(item, dict) and item.get("source_quality") in {"partial", "unconfirmed"})
    confirmation_status = confirmation.get("status") if isinstance(confirmation, dict) else ""
    confirmed = isinstance(confirmation, dict) and confirmation_status in {"confirmed", "system_runtime_confirmed"} and confirmation.get("source_quality_ack") is True
    return {
        "source_quality": registry.get("source_quality", "unknown"),
        "partial_or_unconfirmed_resources": partial,
        "project_source_confirmed": confirmed,
        "formal_delivery_allowed": confirmed and not partial and registry.get("source_quality") == "complete",
        "runtime_prose_allowed": confirmed,
        "confirmation_status": confirmation_status,
        "blocking_reasons": (["项目来源确认未完成"] if not confirmed else []) + (["存在 partial/unconfirmed 来源资源；仅可作为运行期创作输入"] if partial else []),
    }


def verify(
    project_root: str | Path,
    output_name: str = "资料写作证据验证报告.json",
    run_id: str = "",
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    binding = read_json(evidence / "全量资料解释词创作绑定.json", {})
    effective_run_id = str(run_id).strip()
    if not effective_run_id or Path(effective_run_id).name != effective_run_id:
        return {
            "status": "blocked",
            "run_id": effective_run_id,
            "runtime_prose_status": "failed",
            "blocking_failures": ["写作资料证据验证必须显式提供当前 run_id"],
            "records": [],
            "status_counts": {},
        }
    run_outputs = evidence / "运行" / effective_run_id / "module_outputs"
    prose = read_json(run_outputs / "module_09_scene_prose.json", {})
    cards = read_json(run_outputs / "module_08_scene_beat_cards.json", {})
    bindings = binding.get("records", []) if isinstance(binding, dict) else []
    contract = validate_execution_contract(root)
    selection = {"scenes": cards.get("scenes", [])} if isinstance(cards, dict) else {"scenes": cards}
    card_scenes = cards if isinstance(cards, list) else cards.get("scenes", []) if isinstance(cards, dict) else []
    selected_by_binding: dict[str, set[str]] = defaultdict(set)
    selected_by_source: dict[str, set[str]] = defaultdict(set)
    for scene_selection in selection.get("scenes", []) if isinstance(selection, dict) else []:
        if not isinstance(scene_selection, dict):
            continue
        scene_id = str(scene_selection.get("scene_id") or "")
        for item in scene_selection.get("selected_bindings", scene_selection.get("design_bindings", [])):
            if not isinstance(item, dict):
                continue
            if item.get("binding_id"):
                selected_by_binding[str(item["binding_id"])].add(scene_id)
            if item.get("source_id"):
                selected_by_source[str(item["source_id"])].add(scene_id)
        card = next((card for card in card_scenes if isinstance(card, dict) and str(card.get("scene_id")) == scene_id), None)
        if isinstance(card, dict):
            for source_id in card.get("library_entry_ids", []):
                if source_id:
                    selected_by_source[str(source_id)].add(scene_id)
    # Coverage retains every interpreted creative input. Blueprint permission
    # mismatches are delivery findings and must not erase draft evidence.
    scenes = prose.get("scenes", []) if isinstance(prose, dict) else []
    scene_ids = {str(scene.get("scene_id")) for scene in scenes if scene.get("scene_id")}
    card_ids = {str(scene.get("scene_id")) for scene in card_scenes if scene.get("scene_id")}
    evidence_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scene in scenes:
        for row in _evidence_rows(scene):
            for key in (
                "source_id", "source_id_used", "binding_id", "source_ref",
                "anchor_id", "source_anchor_id", "chain_id", "source_chain_id", "library_entry_id",
            ):
                value = row.get(key)
                if isinstance(value, dict):
                    value = value.get("source_id") or value.get("binding_id") or value.get("locator")
                if value:
                    evidence_by_id[str(value)].append({"scene_id": str(scene.get("scene_id")), "row": row})
            design_bindings = row.get("design_bindings", {})
            if isinstance(design_bindings, dict):
                for design in design_bindings.values():
                    if isinstance(design, dict) and design.get("source_id"):
                        evidence_by_id[str(design["source_id"])].append({"scene_id": str(scene.get("scene_id")), "row": row})
            for binding_id in row.get("matrix_binding_ids", []):
                if binding_id:
                    evidence_by_id[str(binding_id)].append({"scene_id": str(scene.get("scene_id")), "row": row})
    activation_rows = jsonl(evidence / "资料绑定激活审计.jsonl")
    activation_by_id = {str(row.get("binding_id")): row for row in activation_rows if row.get("binding_id")}
    records = []
    for item in bindings:
        source_id = str(item.get("source_id", ""))
        binding_id = str(item.get("binding_id", ""))
        hits = evidence_by_id.get(source_id, []) + evidence_by_id.get(binding_id, [])
        valid_hits = [hit for hit in hits if hit["scene_id"] in scene_ids and hit["scene_id"] in card_ids]
        prose_hits = []
        for hit in valid_hits:
            row = hit["row"]
            location = str(row.get("prose_location", ""))
            result = str(row.get("observable_result") or row.get("result") or row.get("translation_evidence", {}).get("result", ""))
            trigger = str(row.get("trigger") or row.get("translation_evidence", {}).get("trigger", ""))
            if location and result and trigger:
                prose_hits.append({"scene_id": hit["scene_id"], "prose_location": location, "trigger": trigger, "observable_result": result})
        selected_scenes = selected_by_binding.get(binding_id, set()) | selected_by_source.get(source_id, set())
        selected_hits = [hit for hit in prose_hits if hit["scene_id"] in selected_scenes]
        status = "used" if selected_hits else ("selected" if selected_scenes else "deferred")
        activation = activation_by_id.get(binding_id, {})
        binding_meta = item.get("creation_binding", {})
        records.append({
            "binding_id": binding_id, "source_kind": item.get("source_kind"), "source_id": source_id,
            "source_ref": item.get("source_ref"), "planned": True,
            "scene_consumed": bool(valid_hits), "prose_effective": bool(prose_hits),
            "status": status, "selected_scene_ids": sorted(selected_scenes), "scene_evidence": valid_hits[:10], "prose_evidence": selected_hits[:10],
            "binding_class": binding_meta.get("binding_class", "candidate_retrieval"),
            "activation_status": activation.get("activation_status", "awaiting_stage_evidence"),
            "activation_reason": activation.get("activation_reason", "未生成激活审计"),
            "next_activation_conditions": activation.get("next_activation_conditions", binding_meta.get("activation_policy", {}).get("conditions", [])),
        })
    counts = Counter(row["status"] for row in records)
    pending_by_kind = Counter(row["source_kind"] or "unknown" for row in records if row["status"] == "deferred")
    pending_by_stage = Counter(
        str(item.get("creation_binding", {}).get("primary_stage") or "unknown")
        for item, row in zip(bindings, records)
        if row["status"] == "deferred"
    )
    quality = _quality(root)
    blockers = []
    if contract["status"] != "passed":
        blockers.append("项目执行边界未通过：" + "；".join(contract["errors"]))
    if not records:
        blockers.append("没有可验证的已转译创作资料")
    if any(not row["source_id"] for row in records):
        blockers.append("存在缺少 source_id 的绑定")
    if not scenes:
        blockers.append("没有可验证的正文场景")
    if not selected_by_binding and not selected_by_source:
        blockers.append("场景卡没有任何已选资料")
    unrealized = [row["binding_id"] for row in records if row["status"] == "selected"]
    if unrealized:
        blockers.append("已选资料未形成完整正文效果证据：" + ", ".join(unrealized[:20]))
    for source_id, selected_scenes in selected_by_source.items():
        selected_hits = [
            hit for hit in evidence_by_id.get(source_id, [])
            if hit["scene_id"] in selected_scenes
            and str(hit["row"].get("prose_location") or "")
            and str(hit["row"].get("translation_evidence", {}).get("trigger") or hit["row"].get("trigger") or "")
            and str(hit["row"].get("translation_evidence", {}).get("result") or hit["row"].get("result") or "")
        ]
        if not selected_hits:
            blockers.append(f"已选资料未在指定场景形成完整正文证据：{source_id}")
    prose_records = [row for scene in scenes for row in _evidence_rows(scene)]
    source_consumption_status_counts = dict(Counter(
        str(row.get("source_consumption_status") or "source_consumption_status_missing")
        for row in prose_records
    ))
    # A draft can retain traceable unapproved material. Formal release is
    # determined later by the version-bound manifest, item attestations, and
    # human signature; a planning-blueprint allowlist cannot replace that gate.
    draft_provenance_errors = source_permission_errors(root, prose_records, phase="creation")
    delivery_permission_errors: list[str] = []
    blockers.extend(draft_provenance_errors)
    for scene in scenes:
        paragraphs = scene.get("paragraphs", []) if isinstance(scene.get("paragraphs"), list) else []
        for row in _evidence_rows(scene):
            index = row.get("paragraph_index")
            expected_hash = str(row.get("paragraph_sha256") or "")
            if not isinstance(index, int) or index < 0 or index >= len(paragraphs) or not expected_hash:
                blockers.append(f"正文证据缺少可验证段落位置或哈希：{scene.get('scene_id')}")
                continue
            actual_hash = hashlib.sha256(str(paragraphs[index]).encode("utf-8")).hexdigest()
            if actual_hash != expected_hash:
                blockers.append(f"正文段落哈希与来源证据不一致：{scene.get('scene_id')}#paragraphs[{index}]")
    prose_files = prose.get("prose_files", []) if isinstance(prose, dict) else []
    for item in prose_files:
        if not isinstance(item, dict):
            blockers.append("模块09正文文件清单格式错误")
            continue
        relative_path = str(item.get("relative_path") or "").replace("\\", "/")
        path = (root / relative_path).resolve()
        if not relative_path or not path.is_file():
            blockers.append(f"正文文件不存在：{relative_path}")
            continue
        if item.get("sha256") and hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            blockers.append(f"正文文件哈希与模块09证据不一致：{relative_path}")
    report = {
        "schema_version": "writing-source-evidence-1.0", "generated_at": now(),
        "run_id": effective_run_id,
        "module_output_root": str(run_outputs.relative_to(root)).replace("\\", "/"),
        "prose_files": prose_files,
        "policy": "场景卡已选资料必须具备段落级效果证据；未选资料必须显式递延。",
        "binding_count": len(records), "scene_count": len(scene_ids), "scene_card_count": len(card_ids),
        "status_counts": dict(counts),
        "source_consumption_status_counts": source_consumption_status_counts,
        "activation_status_counts": dict(Counter(row["activation_status"] for row in records)),
        "binding_class_counts": dict(Counter(row["binding_class"] for row in records)),
        "pending_by_source_kind": dict(pending_by_kind),
        "pending_by_primary_stage": dict(pending_by_stage),
        "quality_gate": quality, "blocking_failures": blockers,
        "draft_provenance_errors": draft_provenance_errors,
        "delivery_permission_errors": delivery_permission_errors,
        "formal_delivery_status": "pending_formal_release_approval" if not blockers else "blocked",
        "draft_passed": bool(scenes and prose_files), "coverage_passed": not unrealized,
        "delivery_ready": False,
        "status": "failed" if blockers else "passed", "records": records,
    }
    target = evidence / output_name if not blockers else evidence / "失败运行" / output_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    detail = evidence / "资料写作证据逐条清单.jsonl"
    detail.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    queue = evidence / "资料后续写作消费队列.jsonl"
    queue.write_text(
        "".join(json.dumps({
            "queue_status": "pending_activation_or_prose",
            "binding_id": row["binding_id"],
            "source_kind": row["source_kind"],
            "source_id": row["source_id"],
            "source_ref": row["source_ref"],
            "binding_class": row["binding_class"],
            "activation_status": row["activation_status"],
            "activation_reason": row["activation_reason"],
            "next_activation_conditions": row["next_activation_conditions"],
            "required_evidence": ["scene_id", "trigger", "observable_result", "prose_location"],
        }, ensure_ascii=False) + "\n" for row in records if row["status"] == "deferred"),
        encoding="utf-8",
    )
    report["output"] = str(target)
    report["detail_output"] = str(detail)
    report["queue_output"] = str(queue)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--review-source-roles", action="store_true")
    args = parser.parse_args()
    if args.review_source_roles:
        report = review_source_roles(args.project_root)
        print(json.dumps({"status": report["status"], "status_counts": report["status_counts"], "output": report["output"]}, ensure_ascii=False))
        return 0 if report["status"] == "passed" else 2
    report = verify(args.project_root, run_id=args.run_id)
    print(json.dumps({"status": report["status"], "status_counts": report["status_counts"], "quality_gate": report["quality_gate"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())