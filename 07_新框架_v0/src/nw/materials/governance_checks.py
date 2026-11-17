
"""Evaluate frozen governance against explicit inputs and bound review evidence."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import math
import re

from nw.materials.governance_contracts import fingerprint, validate_compiled_governance
from nw.materials.dynamic_refs import LEGACY_RESTORE_IDS, matches_current_rule

_IDS = {"connections": "connection_id", "dynamic_patterns": "dynamic_pattern_id",
        "static_patterns": "static_pattern_id", "combinations": "combination_id"}
_SCORES = {"compatibility_score", "diversity_score", "novelty_score", "similarity_score",
           "reuse_penalty", "quality_score", "confidence"}
_LIMITS = {"max_genre_combination": "genre_ids", "max_mechanisms_per_project": "mechanism_ids",
           "max_structures_per_project": "structure_ids", "max_styles_per_project": "style_ids",
           "max_tones_per_project": "tone_ids"}
_REFERENCE_REGISTRIES = {"source_pattern_ids": "patterns", "static_connection_ids": "static_connections",
                        "dynamic_rule_ids": "dynamic_rules", "source_work_ids": "works"}


def governance_scope_fingerprint(inputs: dict) -> str:
    """Bind review to all current inputs, excluding the evidence containers themselves."""
    return fingerprint({key: value for key, value in inputs.items()
                        if key not in {"semantic_evidence", "reviews", "artifacts", "author_review"}})


def _out(status: str, reason: str, *fields: str) -> tuple:
    return status, [reason], list(fields)


def _proof(value: object) -> bool:
    return (isinstance(value, dict) and isinstance(value.get("source_id"), str)
            and bool(value["source_id"]) and isinstance(value.get("sha256"), str)
            and re.fullmatch("[0-9a-f]{64}", value["sha256"]) is not None
            and bool(value.get("locator", value.get("json_pointer", value.get("document_id")))))


def _resolve(inputs: dict, registry: str, ident: object) -> tuple:
    if not isinstance(ident, str) or not ident:
        return _out("failed", "引用ID缺失或不是非空字符串", registry)
    registries = inputs.get("registries")
    values = registries.get(registry) if isinstance(registries, dict) else None
    if not isinstance(values, dict):
        return _out("waiting", "缺确切注册集合：" + registry, registry)
    value = values.get(ident)
    if value is None:
        return _out("failed", "引用未在显式注册集合存在：" + ident, registry)
    if not isinstance(value, dict) or not _proof(value.get("source_ref")):
        return _out("waiting", "引用缺冻结来源和位置：" + ident, registry)
    return "pass", [value], []


def _references(inputs: dict, subject: dict, field: str, registry: str) -> tuple:
    values = subject.get(field)
    if not isinstance(values, list):
        return _out("failed", "引用字段缺失或不是显式数组", field)
    if not values:
        return _out("not_applicable", "显式空引用数组；没有本类引用实例", field)
    for value in values:
        status, findings, fields = _resolve(inputs, registry, value)
        if status != "pass":
            return status, findings, fields
        entry = findings[0]
        if registry == "works" and entry.get("real_work") is not True:
            return _out("failed", "作品来源未确认为真实作品，不能作来源事实", field)
        if registry == "dynamic_rules" and entry.get("status") != "approved":
            return _out("failed", "动态引用未取得当前执行资格", field)
    return _out("pass", "逐引用解析到确切来源、身份及资格", field)


def _semantic(req: dict, inputs: dict, subject: dict, subject_id: str) -> tuple:
    evidence = inputs.get("semantic_evidence")
    if not isinstance(evidence, list):
        return _out("waiting", "缺该实际对象的独立/作者语义证据；读取、ID或关键词不算通过")
    statuses, scope_hash = [], governance_scope_fingerprint(inputs)
    for item in evidence:
        if not isinstance(item, dict) or item.get("requirement_key") != req["requirement_key"]:
            continue
        if (item.get("subject_id") != subject_id or item.get("subject_sha256") != fingerprint(subject)
                or item.get("source_document_sha256") != req["source_ref"]["document_sha256"]
                or item.get("stage") != inputs["scope"]["stage"]
                or item.get("scope_fingerprint") != scope_hash):
            continue
        artifacts, reviews = inputs.get("artifacts"), inputs.get("reviews")
        if not isinstance(artifacts, list) or not isinstance(reviews, list):
            continue
        artifact = next((a for a in artifacts if isinstance(a, dict) and a.get("id") == item.get("artifact_id")), None)
        review = next((r for r in reviews if isinstance(r, dict) and r.get("id") == item.get("review_id")), None)
        if not artifact or not review or not isinstance(artifact.get("text"), str) or not artifact["text"].strip():
            continue
        approvals = inputs.get("author_review")
        approvals = [approvals] if isinstance(approvals, dict) else approvals if isinstance(approvals, list) else []
        author = review.get("role") == "author" and any(
            isinstance(a, dict) and a.get("id") == review.get("id") and a.get("approved") is True
            and a.get("scope_fingerprint") == scope_hash and a.get("reason")
            and a.get("source_document_sha256") == req["source_ref"]["document_sha256"]
            and a.get("subject_sha256") == fingerprint(subject) for a in approvals)
        independent = (review.get("role") == "independent_review"
                       and isinstance(review.get("run_id"), str) and bool(review["run_id"])
                       and isinstance(review.get("writer_run_id"), str) and bool(review["writer_run_id"])
                       and review["run_id"] != review["writer_run_id"])
        if not (author or independent) or review.get("scope_fingerprint") != scope_hash:
            continue
        digest = sha256(artifact["text"].encode("utf-8")).hexdigest()
        if (digest != artifact.get("sha256") or digest != item.get("artifact_sha256")
                or review.get("artifact_sha256") != digest or review.get("completed") is not True
                or review.get("role") not in {"author", "independent_review"}
                or review.get("subject_sha256") != fingerprint(subject)
                or item.get("evidence_location") != "/text" or not item.get("reason")):
            continue
        if item.get("status") in {"pass", "failed"}:
            statuses.append(item["status"])
    if "failed" in statuses:
        return _out("failed", "同对象/源版本/阶段/真实产物hash绑定的评审判定失败")
    if statuses:
        return _out("pass", "同对象/源版本/阶段/真实产物hash绑定的独立或作者评审通过")
    return _out("waiting", "证据缺失、过期、无定位或未绑定实际产物；不能以通用说明通过")


def _identity(req: dict, subject: dict, group: list) -> tuple:
    field = _IDS[req["subject_kind"]]
    value = subject.get(field)
    if not isinstance(value, str) or not value.strip():
        return _out("failed", "标识必须非空", field)
    if sum(isinstance(s, dict) and s.get(field) == value for s in group) != 1:
        return _out("failed", "显式集合内标识不唯一", field)
    return _out("pass", "标识非空且在本次明确集合唯一", field)


def check_dynamic_references(inputs: dict, subject: dict, current_rules: dict[str, dict]) -> tuple | None:
    fields = []
    registries = inputs.get("registries")
    dynamic_rules = registries.get("dynamic_rules") if isinstance(registries, dict) else None
    subject_hash = fingerprint(subject)
    refs = subject.get("source_refs")
    if isinstance(refs, list):
        for ref in refs:
            if isinstance(ref, dict) and ref.get("source_type") == "pending_restore":
                if any(isinstance(ref.get(key), str) and ref[key] in LEGACY_RESTORE_IDS
                       for key in ("rule_id", "original_id", "id")):
                    return _out("failed", "来源引用明确指向旧待恢复规则", "source_refs")
    for field in ("dynamic_rule_ids", "source_rule_ids"):
        values = subject.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            return _out("failed", "规则引用必须是非空字符串组成的数组", field)
        for value in values:
            if value not in LEGACY_RESTORE_IDS:
                continue
            entry = dynamic_rules.get(value) if isinstance(dynamic_rules, dict) else None
            approved_subjects = entry.get("subject_sha256s") if isinstance(entry, dict) else None
            if (subject.get("source_type") == "pending_restore" or value not in current_rules
                    or not matches_current_rule(entry, current_rules[value])
                    or not isinstance(approved_subjects, list) or subject_hash not in approved_subjects):
                return _out("failed", f"{value} 在旧隔离区间内，缺本对象的现用原件与关系资格证据", field)
            fields.append(field)
    if fields:
        return _out("pass", "已核对现用动网的原件版本、位置、关系两端和类型", *dict.fromkeys(fields))
    return None


def _formal_fixture(inputs: dict, subject: dict) -> tuple:
    if inputs["scope"].get("target") not in {"formal", "formal_active"}:
        return _out("waiting", "须显式给出正式/候选目标作用域", "scope.target")
    if subject.get("status") == "fixture" or subject.get("evidence_type") == "fixture":
        return _out("failed", "fixture不得进入正式库/正式active", "status", "evidence_type")
    if "status" not in subject or "evidence_type" not in subject:
        return _out("waiting", "缺来源角色/状态，不能排除fixture", "status", "evidence_type")
    return _out("pass", "本次正式作用域对象未声明fixture", "status", "evidence_type")


def _dynamic_limit(req: dict, inputs: dict, subject: dict, subject_id: str) -> tuple:
    field, maximum, actual = {"DP-06": ("max_depth", 3, "max_observed_depth"),
                             "DP-07": ("max_activated_rules", 5, "activated_rule_ids"),
                             "DP-08": ("max_state_updates", 12, "state_updates")}[req["rule_id"]]
    value = subject.get(field)
    if type(value) is not int or value < 0 or value > maximum:
        return _out("failed", "声明的运行上限非法或超过原文上限" + str(maximum), field)
    trace = inputs.get("execution_trace")
    if (not isinstance(trace, dict) or trace.get("complete") is not True
            or trace.get("scene_id") != inputs["scope"].get("scene_id")
            or not trace.get("scene_id") or not isinstance(trace.get("subject_hashes"), dict)
            or trace["subject_hashes"].get(subject_id) != fingerprint(subject)):
        return _out("waiting", "缺同场/实际对象hash绑定的完整运行轨迹", "execution_trace")
    observed = trace.get(actual)
    if actual == "max_observed_depth":
        definition = trace.get("depth_definition")
        if not (isinstance(definition, dict) and definition.get("root_depth") in (0, 1)
                and definition.get("approved") is True and _proof(definition.get("source_ref"))
                and isinstance(definition.get("definition"), str)):
            return _out("waiting", "原文未定义深度起点；不得从depth=0空模板推定", "depth_definition")
        count = observed
    else:
        if not isinstance(observed, list):
            return _out("waiting", "缺实际每场激活/状态更新集合", actual)
        if actual == "activated_rule_ids" and any(not isinstance(r, str) or not r for r in observed):
            return _out("failed", "实际激活集合包含非法规则ID，不能计为真实激活", actual)
        count = len(observed)
    if type(count) is not int or count < 0:
        return _out("failed", "实际计量不是非负整数", actual)
    return _out("failed" if count > value else "pass", "实际计量=" + str(count) + "，声明上限=" + str(value), field, actual)


def _field(req: dict, inputs: dict, subject: dict, enums: dict) -> tuple:
    field, spec = req["rule_id"][6:], req["source_value"]
    if field not in subject:
        return _out("not_applicable", "schema未声明required；必填要求由V14–V16另验", field)
    value, expected = subject[field], spec.get("type")
    valid = {"string": isinstance(value, str), "array": isinstance(value, list),
             "integer": type(value) is int, "number": type(value) in (int, float),
             "boolean": type(value) is bool, "object": isinstance(value, dict)}.get(expected, False)
    if not valid:
        return _out("failed", "字段类型不符原schema", field)
    allowed = spec.get("enum")
    if spec.get("enum_ref"):
        allowed = enums.get(field)
        if not isinstance(allowed, list):
            return _out("waiting", "缺确切枚举来源", field)
    if isinstance(allowed, list) and value not in allowed:
        return _out("failed", "字段值不在原枚举", field)
    if type(value) in (int, float) and (not math.isfinite(value) or value < spec.get("min", -math.inf) or value > spec.get("max", math.inf)):
        return _out("failed", "字段数值不在原范围", field)
    if isinstance(spec.get("pattern"), str) and re.fullmatch(spec["pattern"], value) is None:
        return _out("failed", "字段不符合原pattern", field)
    if spec.get("format"):
        return _out("waiting", "format只给TSC_XXXXXX描述，X字符定义未提供，不自造正则", field)
    if spec.get("description") or field in {"weight", "priority", "confidence", "status", "relation_scope", "direction"}:
        return _semantic(req, inputs, subject, str(subject.get("connection_id", "")))
    return _out("pass", "确切type/enum/range/pattern结构检查通过；不代表正文效果", field)


def _template(req: dict, inputs: dict, subject: dict, subject_id: str) -> tuple:
    field, default = req["rule_id"][9:], req["source_value"]
    if field not in subject:
        return _out("not_applicable", "该模板槽不是必填schema，本次未实例化", field)
    value = subject[field]
    if field in _SCORES:
        usage = inputs.get("field_usage")
        usage = usage.get(subject_id) if isinstance(usage, dict) else None
        if isinstance(usage, dict) and usage.get(field) is False:
            return _out("not_applicable", "本次明确不使用此可选评分槽，默认0不作为效果/选配结论", field)
        return _out("waiting", "模板0不是已计算/校准分数；须有确切算法及实际计算证据", field)
    if field in _REFERENCE_REGISTRIES:
        return _references(inputs, subject, field, _REFERENCE_REGISTRIES[field])
    if field.endswith("_ids") or field == "primary_type_id":
        values = [value] if field == "primary_type_id" and value else value
        if not values:
            return _out("not_applicable", "模板槽显式未填/未选，不生成项目事实", field)
        if not isinstance(values, list):
            return _out("waiting", "模板填值无法按明确引用数组消费", field)
        for ident in values:
            status, findings, fields = _resolve(inputs, "entities", ident)
            if status != "pass":
                return status, findings, fields
        return _out("pass", "已填引用槽能回查明确身份；不等于正式采用", field)
    if value == default and value in ("", []):
        return _out("not_applicable", "原模板默认槽未填，不当作真实效果或事实", field)
    if field in {"status", "evidence_type", "schema_version"} and value == default:
        return _out("pass", "保留原模板角色/状态/版本，仍无正文或状态提交权限", field)
    return _semantic(req, inputs, subject, subject_id)


def _config(req: dict, inputs: dict, subject: dict) -> tuple:
    field, value = req["rule_id"][7:], req["source_value"]
    if field in _LIMITS:
        selected = subject.get(_LIMITS[field])
        if not isinstance(selected, list) or any(not isinstance(x, str) or not x for x in selected):
            return _out("waiting", "缺明确已选ID数组，不能当空集", _LIMITS[field])
        return _out("failed" if len(set(selected)) > value else "pass", "实际已选唯一ID数=" + str(len(set(selected))) + "，原上限=" + str(value), _LIMITS[field])
    if field == "schema_version":
        return _out("pass", "原政策版本已按冻结源编译；仅元数据")
    if field == "incompatible_pairs":
        return _out("not_applicable", "此版本未列相斥对；不推导所有组合兼容")
    if field in {"auto_combination_forbidden", "requires_manual_review"}:
        return _out("waiting", "与工作流自动设计/人工复核的适用对象及动作须作者明确裁定", field)
    return _semantic(req, inputs, subject, "project_config")


def _rule(req: dict, inputs: dict, subject: dict, group: list, enums: dict, subject_id: str,
          current_rules: dict[str, dict]) -> tuple:
    ident = req["rule_id"]
    if ident in {"V01", "V02", "V03", "V04"}:
        field = "source_id" if ident in {"V01", "V03"} else "target_id"
        status, findings, fields = _resolve(inputs, "entities", subject.get(field))
        if status != "pass":
            return status, findings, fields
        if ident in {"V03", "V04"} and subject.get(field.replace("_id", "_kind")) != findings[0].get("kind"):
            return _out("failed", "端点实际kind与声明不一致", field)
        return _out("pass", "端点存在且按实际注册身份核对", field)
    if ident == "V05":
        value = subject.get("connection_type")
        return _out("pass" if value in enums.get("connection_type", []) and value not in enums.get("forbidden_connection_type", []) else "failed", "按同源确切连接枚举核对", "connection_type")
    if ident in {"V14", "V15", "V16", "DP-03", "DP-04", "DP-05", "SP-03", "SP-04", "SP-05"}:
        field = {"V14": "evidence_type", "V15": "not_guaranteed", "V16": "schema_version"}.get(ident)
        field = field or {"03": "not_guaranteed", "04": "similarity_features", "05": "originality_risk"}[ident[-2:]]
        if field not in subject:
            return _out("failed", "原文要求包含字段", field)
        if ident in {"DP-04", "DP-05", "SP-04", "SP-05"}:
            return _semantic(req, inputs, subject, subject_id)
        return _out("pass", "原文要求的字段存在；结构存在不冒充内容效果", field)
    if ident == "V12":
        if inputs["scope"].get("target") not in {"formal", "formal_active"}:
            return _out("waiting", "缺active目标范围", "scope.target")
        return _out("failed" if subject.get("status") == "pending" else "pass" if "status" in subject else "waiting", "pending不得进入active索引", "status")
    if ident in {"V13", "DP-14", "SP-09", "COM-08"}:
        return _formal_fixture(inputs, subject)
    if ident in {"DP-01", "SP-01", "COM-01"}:
        return _identity(req, subject, group)
    if ident in {"DP-02", "SP-02"}:
        return _references(inputs, subject, "source_work_ids", "works")
    if ident in {"DP-06", "DP-07", "DP-08"}:
        return _dynamic_limit(req, inputs, subject, subject_id)
    if ident in {"DP-09", "SP-10", "COM-07", "COM-10"}:
        forbidden = check_dynamic_references(inputs, subject, current_rules) or _semantic(req, inputs, subject, subject_id)
        if forbidden[0] == "failed" or ident != "COM-07":
            return forbidden
        return _references(inputs, subject, "dynamic_rule_ids", "dynamic_rules")
    if ident in {"DP-11", "DP-12", "DP-13"}:
        return _out("waiting", "模式/规则筛选不直接提交状态；与正文证据接受事务的作用域须独立裁定")
    if ident in {"DP-15", "SP-11"}:
        if "evidence_type" not in subject:
            return _out("waiting", "缺来源角色，不能推定不是source_fact", "evidence_type")
        if subject["evidence_type"] == "source_fact" and not subject.get("source_work_ids"):
            return _out("failed", "没有真实作品来源，不能声明source_fact", "source_work_ids")
        return _references(inputs, subject, "source_work_ids", "works") if subject["evidence_type"] == "source_fact" else _out("not_applicable", "本对象未声明为source_fact")
    if ident == "COM-02":
        registries = inputs.get("registries")
        enums_registry = registries.get("enums") if isinstance(registries, dict) else None
        declared = enums_registry.get("combination_kind") if isinstance(enums_registry, dict) else None
        if not (isinstance(declared, dict) and declared.get("complete") is True and _proof(declared.get("source_ref")) and isinstance(declared.get("values"), list)):
            return _out("waiting", "缺combination_kind完整枚举原件；不从容器实例猜", "combination_kind")
        return _out("pass" if subject.get("combination_kind") in declared["values"] else "failed", "按确切完整枚举核对", "combination_kind")
    if ident == "COM-06":
        if subject.get("dynamic_rule_ids") == [] and subject.get("combination_kind") == "动态":
            return _out("failed", "动态搭配必须实际引用合法动态规则", "dynamic_rule_ids")
        if subject.get("dynamic_rule_ids") == [] and subject.get("combination_kind") != "动态":
            return _out("not_applicable", "本对象无动态搭配引用")
        return _references(inputs, subject, "dynamic_rule_ids", "dynamic_rules")
    if ident == "COM-09" and inputs["scope"].get("library_kind") == "source_work_combinations":
        if not subject.get("source_work_ids"):
            return _out("failed", "没有真实作品来源时正式作品搭配库必须保持空模板", "source_work_ids")
        return _references(inputs, subject, "source_work_ids", "works")
    return _semantic(req, inputs, subject, subject_id)


def evaluate_governance(contract: dict, inputs: dict, *, current_rules: dict[str, dict] | None = None) -> dict:
    """Return per-source checks; never writes data or invents semantic verdicts."""
    contract = validate_compiled_governance(contract)
    current_rules = current_rules or {}
    checks = []
    scope = inputs.get("scope") if isinstance(inputs, dict) else None
    safe_scope = (isinstance(scope, dict) and scope.get("stage") in {"source_validation", "design", "scene", "review", "accept", "state"}
                  and isinstance(scope.get("action"), str) and bool(scope["action"]) and isinstance(scope.get("document_names"), list))
    enums = contract.get("dependencies", {}).get("connection_enums", {}).get("value", {})
    subjects = inputs.get("subjects") if isinstance(inputs, dict) else None
    for req in contract.get("requirements", []):
        kind = req["subject_kind"]
        group = inputs.get("project_config") if kind == "project_config" and isinstance(inputs, dict) else subjects.get(kind) if isinstance(subjects, dict) else None
        group = [group] if kind == "project_config" and isinstance(group, dict) else group
        if req["status"] != "ready":
            outcome, group = _out("waiting", "原句/字段/源版本未审定"), [None]
        elif not safe_scope or scope.get("source_id") != req["source_ref"]["source_id"] or req["document_name"] not in scope["document_names"]:
            outcome, group = _out("waiting", "缺确切来源/阶段/动作/合同适用范围"), [None]
        elif not isinstance(group, list):
            outcome, group = _out("waiting", "必需输入集合缺失或类型错误；不能当[]", kind), [None]
        elif not group:
            outcome, group = _out("not_applicable", "显式空集合，本次范围无实际实例；不计语义pass", kind), [None]
        else:
            outcome = None
        for index, subject in enumerate(group):
            current = outcome
            subject_id = str(subject.get(_IDS.get(kind, ""), "project_config")) if isinstance(subject, dict) else None
            try:
                subject_hash = fingerprint(subject) if subject is not None else None
            except (ValueError, TypeError):
                subject_hash, current = None, _out("failed", "实际输入含非有限数或不可冻结内容", kind)
            if current is None:
                if not isinstance(subject, dict):
                    current = _out("failed", "实际条目不是对象", kind)
                elif req["handler"] == "field":
                    current = _field(req, inputs, subject, enums)
                elif req["handler"] == "template":
                    current = _template(req, inputs, subject, subject_id)
                elif kind == "project_config":
                    current = _config(req, inputs, subject)
                else:
                    current = _rule(req, inputs, subject, group, enums, subject_id, current_rules)
            status, findings, fields = current
            checks.append({**{k: deepcopy(req[k]) for k in ("requirement_key", "rule_id", "document_name", "source_ref", "source_text")},
                           "status": status, "findings": findings, "affected_fields": fields,
                           "checked_input": {"subject": {"kind": kind, "index": index, "id": subject_id, "sha256": subject_hash},
                                             "scope": deepcopy(scope)}})
    statuses = Counter(row["status"] for row in checks)
    status = "failed" if statuses["failed"] else "waiting" if statuses["waiting"] or contract.get("issues") else "pass" if statuses["pass"] else "not_applicable"
    return {"policy": contract.get("policy"), "contract_fingerprint": contract.get("fingerprint"),
            "status": status, "checks": checks, "summary": dict(statuses),
            "input_snapshot": deepcopy(inputs), "issues": deepcopy(contract.get("issues", [])),
            **({"dynamic_rule_evidence": deepcopy(current_rules)} if current_rules else {}),
            "blocked_actions": [scope.get("action")] if safe_scope and status in {"failed", "waiting"} else [],
            "authority": "governance_only", "formal_prose_effects_verified": 0}
