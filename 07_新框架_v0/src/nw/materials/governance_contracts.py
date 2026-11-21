"""Compile audited governance originals without inheriting prose authority."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json

POLICY = "governance-source-contract-v1"
SOURCE_ID = "19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20"
NAMES = json.loads(r'''["类型静态连接字段说明.json","类型连接验证规则.json","类型组合约束.json","作品动态模式验证规则.json","作品静态模式验证规则.json","作品连接搭配模板.json","作品连接搭配验证规则.json"]''')
KNOWN = json.loads(r'''{"类型静态连接字段说明.json":{"document_id":"faa87bb7b8ab247f1e6c6863a2d70e326abac6ee3b39b535ca66ee8f5f900ff7","document_sha256":"16e7dbbbfa5ef54302f3853dff37d9d6f3915d569ca26fe001a5f464c939db64","block_sha256":"ecb9c78719150858d3c14ec257cf89636c19aeb5b8a74d6ea3cd775dc865736c","value_sha256":"a91b18e66b7485a181353e9a24bfe3adaa97a7bfc76e68c6ae719e54027a77f8"},"类型连接验证规则.json":{"document_id":"ff0ade992820edc85e05d15d90cb79a1f0f2cb901639f75ab50d14e3e64b2f88","document_sha256":"2a42d7edcc57acf0b626a70959647f952b65be0d2404a0945bc55e9b8e72d173","block_sha256":"8ba357de5b5c98a6c12467ead20208d28afb7b8be79047a37648382e5ea27a59","value_sha256":"414ebd2e98af83dab7f1a62127e9b6afbbe56df59c7e5bafed246d6863975f1c"},"类型组合约束.json":{"document_id":"b304be6df16813d671eb8b19e7c58a1302154ddefb44e9f3582949439b5f8bfc","document_sha256":"c037c80967a1bfef594b11f70f56436c06cc2b63c29adae26ebbb35903cbd2ac","block_sha256":"afc92d27365be01808b6433bac92faf3f4147ec168a195e359f030947bc3934c","value_sha256":"bbcfbf4740b7c8bddd3e9a181cd53d906d6255ab74f97d2475b23fbabbf4c4f2"},"作品动态模式验证规则.json":{"document_id":"d163c406dc566d0f39dadf40d95476bc3e67469f9c11f04880c543ea6131966a","document_sha256":"7d0f5f7c433c645bb221e6137b377c6f46fea10410dd1ac4d2c2aa8495c90e87","block_sha256":"33bd68113ebd66cc6d73400c666be6d49c89cf0f2c8bc7fe74ae8bf5012013b1","value_sha256":"240edfd3ae3bb8aeaa04d298e728e2a3174e3c0a405eb5dc45b6c5f21160e801"},"作品静态模式验证规则.json":{"document_id":"2815600e4a096bad851050a762ed7924bd219d15581e6772790ae133863ddae0","document_sha256":"a408f8d79bf786d6fa729bd90df1de3e09bfde4266968ff4b790797089df5783","block_sha256":"f0c7b6f6843c0b62ac413d4f241ae74f29e09ab76061d409290184c5cacd80be","value_sha256":"84fc07dc320eb88399ddc958af9768f5ec16e4980fd71d393c1e92c9c5313f62"},"作品连接搭配模板.json":{"document_id":"c7e8b95352230c8a707944462064711ba984d437e562c9b7aa7adfd373903cb5","document_sha256":"77057345c9bee99682564f3f329e59f073a6d1f06d4bd741ec960bfd738f9066","block_sha256":"4f022205606dc66e221743114a82b1b3f32cb175bd3307632e4c26abfc2c3f99","value_sha256":"7fa479648199dbe548b70538771e236f53986906324cf4793fcfc19167ae81bc"},"作品连接搭配验证规则.json":{"document_id":"204eac7b6fc7618db98869f8ec1982db7f17ac31dcc4df01ef11d7e03ecaabd4","document_sha256":"cce01a50bc03a98c7532f1b4a35f51f697e2efb9cd65fd377ee9df89d9b2a2e6","block_sha256":"b65c599b900c719523e60308144c58df1e4e9702605a166be468ece474629d84","value_sha256":"fa3e3fe28c6a1dcbe10919c180544e17e1848d0d0f116aa98e5db1566a3ac75c"}}''')
DYNAMIC_LIMITS = json.loads(r'''{"source_id":"6cd30d00d42a5b3410bed51599a705463517ef6316fbfc6c4319c45fc0a3cba5","document_id":"8436e9b89963b2cb182b46503088dca4f3a7055cc33a5b9c6fb72c3223e6831f","document_sha256":"7fc1f580e5cb6d53eedf48d422d2acc666564a310ef2f1b8ccada7118e8392d7","json_pointer":"/global_defaults","count_scope":"per_scene","max_activated_rules_per_scene":5,"max_state_updates_per_scene":12,"max_propagation_depth":3,"depth_origin":"unresolved"}''')

CONNECTION_ENUMS = json.loads(r'''{"value":{"connection_type":["TYPE_SUPPORTS_CONCEPT","TYPE_PRIORITIZES_CONCEPT","TYPE_SUPPORTS_ENTITY","TYPE_SUPPORTS_EVENT","TYPE_SUPPORTS_ACTION","TYPE_SUPPORTS_REACTION","TYPE_SUPPORTS_INFORMATION","TYPE_SUPPORTS_RESOURCE","TYPE_SUPPORTS_FORESHADOWING","TYPE_SUPPORTS_SCENE","TYPE_USES_MECHANISM","TYPE_USES_STRUCTURE","TYPE_USES_STYLE","TYPE_COMPATIBLE_WITH","TYPE_CONFLICTS_WITH","TYPE_REQUIRES_CONTEXT","TYPE_EXCLUDES_CONTEXT","TYPE_REFINES","TYPE_COMBINES_WITH","TYPE_DISTINGUISHED_FROM","TYPE_ALTERNATIVE_TO","TYPE_INDEXES_BY"],"forbidden_connection_type":["TYPE_CAUSES_DEATH","TYPE_CAUSES_LOVE","TYPE_CAUSES_REVENGE","TYPE_CAUSES_UPGRADE","TYPE_CAUSES_BETRAYAL","TYPE_CAUSES_ATTACK","TYPE_CAUSES_RESCUE","TYPE_CAUSES_FIXED_ACTION","TYPE_ALWAYS_REVEALS","TYPE_ALWAYS_HIDES"],"relation_scope":["global_template","genre_level","subgenre_level","hybrid_level","mechanism_level","structure_level","style_level","tone_level","project_level","pending_review"],"evidence_type":["template","normalized","inferred","pending","fixture"],"status":["active","pending","deprecated","fixture"]},"source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","document_ref":{"id":"2c4b793941dd260620f83666261677e07bca5c82a56de87c922f7b0527b3be79","fragment_id":"5c8bb5700e69b228616d9d9c671102f4d1d9a54d0cba93be13fd20138383f5fa","kind":"json_document","key":"类型连接枚举.json","label":"类型连接枚举.json","locator":"","origin":"container","byte_start":44621894,"byte_end":44623264,"line_start":1069216,"line_end":1069278,"sha256":"c05c412d92455bccda5d334dc437c36baf752c54f8b53e642ec76b5b478aa98b"},"source_block_ref":{"id":"5c8bb5700e69b228616d9d9c671102f4d1d9a54d0cba93be13fd20138383f5fa","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","kind":"source_block","key":"类型连接枚举.json","byte_start":44621799,"byte_end":44623268,"line_start":1069214,"line_end":1069279,"sha256":"8068a68b584ee276e581f92561e84dd5b60bdbf25127a7b7b0ace935fed55c8a"}}''')


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value: object) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _requirements(document: dict, ready: bool) -> list[dict]:
    name, value = document["name"], document["value"]
    source, ref = document.get("source_ref", {}), document.get("document_ref", {})
    if not isinstance(value, dict):
        return []
    records = []
    if name == NAMES[0]:
        records = [("FIELD-" + field, "/" + field, spec, "field", "connections")
                   for field, spec in value.items()]
    elif name == NAMES[2]:
        for field, item in value.items():
            if field == "rules" and isinstance(item, list):
                records.extend(("CONFIG-rule-" + str(i), "/rules/" + str(i), rule,
                                "config_rule", "project_config") for i, rule in enumerate(item))
            else:
                records.append(("CONFIG-" + field, "/" + field, item, "config", "project_config"))
    elif name == NAMES[5]:
        records = [("TEMPLATE-" + field, "/" + field, item, "template", "combinations")
                   for field, item in value.items()]
    else:
        key = "validation_rules" if name == NAMES[1] else "rules"
        kind = {NAMES[1]: "connections", NAMES[3]: "dynamic_patterns",
                NAMES[4]: "static_patterns", NAMES[6]: "combinations"}.get(name)
        rules = value.get(key, [])
        if isinstance(rules, list):
            for i, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    continue
                leaf = "rule" if "rule" in rule else "description"
                records.append((str(rule.get("rule_id", "unknown-" + str(i))),
                                "/" + key + "/" + str(i) + "/" + leaf,
                                rule.get(leaf), "rule", kind))
    return [{"requirement_key": str(ref.get("id", name)) + ":" + ident,
             "rule_id": ident, "document_name": name, "handler": handler,
             "subject_kind": kind, "source_value": deepcopy(item),
             "source_text": item if isinstance(item, str) else canonical(item),
             "source_ref": {"source_id": source.get("source_id"),
                            "source_block_id": source.get("id"),
                            "source_block_sha256": source.get("sha256"),
                            "document_id": ref.get("id"),
                            "document_sha256": ref.get("sha256"), "json_pointer": pointer},
             "status": "ready" if ready else "waiting"}
            for ident, pointer, item, handler, kind in records]


def compile_governance(documents: list[dict]) -> dict:
    """Compile only audited frozen meanings; this grants no writing authority."""
    requirements, issues, compiled = [], [], []
    if not isinstance(documents, list):
        documents = []
        issues.append({"kind": "documents_type", "document_name": None, "json_pointer": "",
                       "status": "waiting", "reason": "documents必须是显式文档列表"})
    counts = Counter(d.get("name") for d in documents if isinstance(d, dict)
                     and isinstance(d.get("name"), str))
    for document in documents:
        if not isinstance(document, dict):
            issues.append({"kind": "document_type", "document_name": None,
                           "json_pointer": "", "status": "waiting"})
            continue
        name = document.get("name")
        if name not in KNOWN:
            issues.append({"kind": "unknown_document", "document_name": name,
                           "json_pointer": "", "status": "waiting"})
            continue
        known = KNOWN[name]
        source, ref = document.get("source_ref"), document.get("document_ref")
        try:
            digest = fingerprint(document.get("value"))
        except (ValueError, TypeError):
            digest = None
        identity = (isinstance(source, dict) and isinstance(ref, dict)
                    and source.get("source_id") == SOURCE_ID
                    and source.get("sha256") == known["block_sha256"]
                    and ref.get("id") == known["document_id"]
                    and ref.get("sha256") == known["document_sha256"])
        ready = identity and digest == known["value_sha256"] and counts[name] == 1
        if not ready:
            issues.append({"kind": "ambiguous_document" if counts[name] != 1 else "unreviewed_source",
                           "document_name": name, "json_pointer": "", "status": "waiting",
                           "source_ref": deepcopy(source), "document_ref": deepcopy(ref),
                           "reason": "来源身份、原句/字段值或版本变化未审定，不沿用旧语义自动通过"})
        requirements.extend(_requirements(document, ready))
        compiled.append({"name": name, "value": deepcopy(document.get("value")),
                         "source_ref": deepcopy(source), "document_ref": deepcopy(ref),
                         "status": "ready" if ready else "waiting"})
    if not documents and not issues:
        issues.append({"kind": "empty_documents", "document_name": None,
                       "json_pointer": "", "status": "waiting"})
    return {"policy": POLICY, "status": "waiting" if issues else "ready",
            "authority": "governance_only", "documents": compiled,
            "requirements": requirements, "issues": issues,
            "dependencies": {"dynamic_limits": deepcopy(DYNAMIC_LIMITS),
                             "connection_enums": deepcopy(CONNECTION_ENUMS)},
            "fingerprint": fingerprint({"documents": compiled, "issues": issues})}


def validate_compiled_governance(contract: dict) -> dict:
    """Rebuild source-derived handlers so a mutable cached dict cannot change meaning."""
    if not isinstance(contract, dict):
        return compile_governance([])
    expected = compile_governance(contract.get("documents"))
    saved = contract.get("requirements")
    saved = {r.get("requirement_key"): r for r in saved if isinstance(r, dict)} if isinstance(saved, list) else {}
    altered_dependencies = contract.get("dependencies") != expected["dependencies"]
    altered_fingerprint = contract.get("fingerprint") != expected["fingerprint"]
    for requirement in expected["requirements"]:
        if (saved.get(requirement["requirement_key"]) != requirement
                or altered_dependencies or altered_fingerprint):
            requirement["status"] = "waiting"
            expected["issues"].append({"kind": "compiled_contract_changed", "status": "waiting",
                "document_name": requirement["document_name"], "source_ref": requirement["source_ref"],
                "reason": "编译缓存的字段/handler/依赖/指纹与冻结原件重新编译结果不一致"})
    if expected["issues"]:
        expected["status"] = "waiting"
    # JSON persistence sorts object keys. Recover the original report order
    # from the frozen array after rebuilding and checking each requirement.
    order = {key: i for i, key in enumerate(saved)}
    expected["requirements"].sort(key=lambda requirement: order.get(requirement["requirement_key"], len(order)))
    return expected
