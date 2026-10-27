#!/usr/bin/env python3
"""Standard-library runtime for the material routing contract."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from 资料证据层 import build_evidence_bundle


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_records(text):
    records = []
    current = None
    for line in text.splitlines():
        match = re.match(r"\s*- id:\s*[\"']([^\"']+)[\"']", line)
        if match:
            if current:
                records.append(current)
            current = {"id": match.group(1), "body": []}
        elif current:
            current["body"].append(line)
    if current:
        records.append(current)
    return [{"id": r["id"], "text": "\n".join(r["body"])} for r in records]


def field(text, name):
    match = re.search(r"^\s*" + re.escape(name) + r":\s*(.*)$", text, re.M)
    return match.group(1).strip().strip("\"'") if match else ""


def list_field(text, name):
    value = field(text, name)
    if not value.startswith("["):
        return []
    return [x.strip().strip("\"'") for x in value[1:-1].split(",") if x.strip()]


def flatten_static(value, source=""):
    """Flatten the static source_index shape into searchable edge summaries."""
    rows = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "targets" and isinstance(child, list):
                for target in child:
                    if isinstance(target, dict):
                        rows.append({"source": source, **target})
            elif isinstance(child, (dict, list)):
                rows.extend(flatten_static(child, key if key != "source_index" else source))
    elif isinstance(value, list):
        for child in value:
            rows.extend(flatten_static(child, source))
    return rows


def terms_match(item, terms):
    haystack = json.dumps(item, ensure_ascii=False).lower()
    return any(term in haystack for term in terms)


def retrieve_network_evidence(root, request, limit=50):
    contract_path = root / "00_资料索引" / "网络派生索引契约.json"
    contract = read_json(contract_path)
    terms = [term for term in re.findall(r"[\u4e00-\u9fffA-Za-z0-9_.-]+", request.lower()) if len(term) > 1]
    results = []
    artifacts = []
    for artifact in contract["artifacts"]:
        path = root / Path(artifact["path"])
        if not path.exists():
            artifacts.append({"id": artifact["id"], "path": artifact["path"], "status": "blocked", "reason": "missing_file"})
            continue
        payload = read_json(path)
        artifacts.append({"id": artifact["id"], "path": artifact["path"], "kind": artifact["kind"],
                          "status": artifact["default_status"], "bytes": path.stat().st_size})
        if artifact.get("metadata_only"):
            if terms_match(payload, terms):
                results.append({"artifact_id": artifact["id"], "path": artifact["path"], "status": "selected",
                                "evidence_level": artifact["evidence_level"], "summary": payload})
            continue
        record_path = artifact.get("record_path", "")
        records = payload.get(record_path, []) if record_path else payload
        if artifact["kind"] == "static_connections":
            records = flatten_static(records)
        if not isinstance(records, list):
            records = []
        for record in records:
            if not isinstance(record, dict) or (terms and not terms_match(record, terms)):
                continue
            needs_review = record.get("needs_review") is True
            status = "candidate" if needs_review or artifact["default_status"] != "selected" else "selected"
            result = {"artifact_id": artifact["id"], "path": artifact["path"], "status": status,
                      "evidence_level": artifact["evidence_level"], "record": record}
            if artifact.get("migration_only"):
                result["warning"] = "migration_only: 仅用于旧 ID 审计，不恢复历史事实"
            if artifact.get("alias_only"):
                result["warning"] = "alias_only: 未决别名不能自动合并节点"
            if needs_review:
                result["warning"] = "needs_review: 需人工或证据链审核后才能采用"
            results.append(result)
            if len(results) >= limit:
                return {"contract": str(contract_path.relative_to(root)).replace("\\", "/"),
                        "query_terms": terms, "artifacts": artifacts, "matches": results, "truncated": True}
    gaps = []
    metrics_path = root / "四网络连接，剧情覆盖" / "network_generation_metrics.json"
    if metrics_path.is_file():
        metrics = read_json(metrics_path)
        if metrics.get("dynamic_original_connections") != metrics.get("dynamic_final_connections"):
            gaps.append({"network": "动态网络", "reason": "派生总量包含需复核生成记录", "original": metrics.get("dynamic_original_connections"), "final": metrics.get("dynamic_final_connections")})
    return {"contract": str(contract_path.relative_to(root)).replace("\\", "/"),
            "query_terms": terms, "artifacts": artifacts, "matches": results, "truncated": False}


def choose(records, request):
    terms = set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", request.lower()))
    selected, decisions = [], []
    core = {"MOD-INDEX-MAPPING", "MOD-TYPE", "MOD-CONNECTION", "MOD-EXECUTION"}
    for record in records:
        rid, text = record["id"], record["text"]
        if rid.startswith("MOD-LEGACY-"):
            decisions.append({"id": rid, "status": "not_applicable", "reason": "migration_only"})
            continue
        dimensions = set(list_field(text, "dimensions"))
        mandatory = field(text, "mandatory") == "true" or field(text, "pre_generation_required") == "true"
        hit = sorted(terms.intersection(set(dimensions)))
        if rid in core or mandatory or hit:
            status = "selected" if rid in core or mandatory else "candidate"
            selected.append({"id": rid, "path": field(text, "path") or field(text, "source_file"),
                             "status": status, "matched_dimensions": hit,
                             "role": field(text, "function"), "related": list_field(text, "related") + list_field(text, "related_records")})
            decisions.append({"id": rid, "status": status, "matched_dimensions": hit})
        else:
            decisions.append({"id": rid, "status": "not_applicable", "reason": "no_task_or_state_match"})
    return selected, decisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--mode", default="Audit", choices=["Audit", "Plan", "Verify"])
    parser.add_argument("--request", default="继续当前小说项目，设计并生成下一章")
    parser.add_argument("--project-path", default="")
    parser.add_argument("--output-path", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    index_path = root / "00_资料索引" / "多维资料索引.yaml"
    contract_path = root / "00_资料索引" / "索引调用映射契约.json"
    network_contract_path = root / "00_资料索引" / "网络派生索引契约.json"
    layer_path = root / "阶段状态" / "规范化资料层.json"
    records = parse_records(index_path.read_text(encoding="utf-8"))
    contract = read_json(contract_path)
    network_evidence = retrieve_network_evidence(root, args.request)
    layer = read_json(layer_path)
    selected, decisions = choose(records, args.request)
    evidence_bundle = build_evidence_bundle(root, args.request, [item["id"] for item in selected])
    ids = {item["id"] for item in selected}
    edges = []
    for item in selected:
        for dependency in item["related"]:
            if dependency in ids:
                edges.append({"from": dependency, "to": item["id"], "relation": "indexed_dependency"})
    output = Path(args.output_path) if args.output_path else root / "docs" / ("资料闭环-" + args.mode.lower() + ".json")
    network_blocked = any(item.get("status") == "blocked" for item in network_evidence["artifacts"])
    review_records = sum(1 for item in network_evidence["matches"] if item.get("status") == "candidate")
    result = {
        "schema_version": "2.4",
        "run_id": "RUN-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "mode": args.mode,
        "request": args.request,
        "project_path": str(Path(args.project_path).resolve()) if args.project_path else None,
        "source_scope": {"root": "08_原始资料", "external_paths_allowed": False, "indexed_records": len(records),
                         "contract": str(contract_path.relative_to(root)).replace("\\", "/"),
                         "network_contract": str(network_contract_path.relative_to(root)).replace("\\", "/"),
                         "network_artifacts": len(network_evidence["artifacts"]), "layer_status": layer.get("status")},
        "selected_modules": selected,
        "selection_decisions": decisions,
        "dependency_edges": edges,
        "selected_network_evidence": network_evidence,
        "evidence_bundle": evidence_bundle,
        "routing_contract": contract["routing_contract"],
        "retrieval_indexes": contract["retrieval_indexes"],
        "evidence_contract": contract["evidence_rules"],
        "synthesis_contract": {"required_inputs": ["task_context", "project_snapshot", "selected_evidence"],
                               "required_outputs": ["decisions", "conflicts", "state_changes", "writing_requirements", "source_trace", "not_used_reasons"],
                               "handoff_chain": ["task_context", "evidence_bundle", "synthesis", "chapter_design", "execution_manifest", "chapter_text", "state_update", "verification"]},
         "status": "BLOCKED_WITH_REVIEW" if network_blocked or review_records else ("READY" if evidence_bundle["usable_evidence_ids"] else "PARTIAL")
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OUTPUT=" + str(output.resolve()))
    print("RECORDS=%d; SELECTED=%d; EDGES=%d" % (len(records), len(selected), len(edges)))
    print("STATUS=" + result["status"])


if __name__ == "__main__":
    main()