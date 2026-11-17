"""Execute source-backed governance contracts without files, models, or stores."""
import copy
import importlib
import json

import pytest

DOCUMENTS = json.loads(r'''[{"name":"类型静态连接字段说明.json","value":{"connection_id":{"type":"string","format":"TSC_XXXXXX","description":"类型静态连接唯一标识"},"source_id":{"type":"string","description":"连接源ID"},"source_kind":{"type":"string","enum":["genre","subgenre","hybrid_genre","mechanism","structure","style","tone"]},"target_id":{"type":"string","description":"连接目标ID"},"target_kind":{"type":"string","enum":["genre","subgenre","hybrid_genre","mechanism","structure","style","tone","concept","entity_type","event_type","information_type","resource_type","foreshadowing_type","scene_type","action_type","reaction_type"]},"connection_type":{"type":"string","enum_ref":"类型连接枚举.json"},"relation_scope":{"type":"string","enum":["global_template","genre_level","subgenre_level","hybrid_level","mechanism_level","structure_level","style_level","tone_level","project_level","pending_review"]},"direction":{"type":"string","enum":["directed","bidirectional"],"default":"directed"},"weight":{"type":"number","min":0,"max":1,"default":0.5},"priority":{"type":"integer","min":0,"max":10,"default":5},"conditions":{"type":"array","description":"静态适用范围条件"},"effects":{"type":"array","description":"静态适配结果（非动态变化）"},"not_guaranteed":{"type":"array","description":"明确不保证的事项"},"source_refs":{"type":"array","description":"来源引用"},"evidence_type":{"type":"string","enum":["template","normalized","inferred","pending","fixture"]},"confidence":{"type":"number","min":0,"max":1},"status":{"type":"string","enum":["active","pending","deprecated","fixture"]},"schema_version":{"type":"string","pattern":"TYPE_C-\\d+\\.\\d+\\.\\d+"}},"source_ref":{"id":"c2aff323eba941441ee8498b8886642f9f4de7f32e272a16dcc8e35626517c4b","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"ecb9c78719150858d3c14ec257cf89636c19aeb5b8a74d6ea3cd775dc865736c","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"faa87bb7b8ab247f1e6c6863a2d70e326abac6ee3b39b535ca66ee8f5f900ff7","fragment_id":"c2aff323eba941441ee8498b8886642f9f4de7f32e272a16dcc8e35626517c4b","kind":"json_document","key":"类型静态连接字段说明.json","label":"类型静态连接字段说明.json","locator":"","origin":"container","byte_start":28313237,"byte_end":28315612,"line_start":691787,"line_end":691917,"sha256":"16e7dbbbfa5ef54302f3853dff37d9d6f3915d569ca26fe001a5f464c939db64"}},{"name":"类型连接验证规则.json","value":{"validation_rules":[{"rule_id":"V01","rule":"source_id必须存在"},{"rule_id":"V02","rule":"target_id必须存在"},{"rule_id":"V03","rule":"source_kind与source_id类型一致"},{"rule_id":"V04","rule":"target_kind与target_id类型一致"},{"rule_id":"V05","rule":"connection_type合法"},{"rule_id":"V06","rule":"不包含动态传播字段"},{"rule_id":"V07","rule":"不包含固定剧情结果"},{"rule_id":"V08","rule":"不包含未经来源支持的具体事实"},{"rule_id":"V09","rule":"无反向重复"},{"rule_id":"V10","rule":"无循环依赖"},{"rule_id":"V11","rule":"不覆盖原始三网络"},{"rule_id":"V12","rule":"pending不进入active索引"},{"rule_id":"V13","rule":"fixture不进入正式active"},{"rule_id":"V14","rule":"具有evidence_type"},{"rule_id":"V15","rule":"具有not_guaranteed"},{"rule_id":"V16","rule":"具有schema_version"}],"schema_version":"TYPE_C-1.0.0"},"source_ref":{"id":"7a17201b983368d758fef548f959183c3f685d10d01f1e2f0c04479b8ba8344e","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"8ba357de5b5c98a6c12467ead20208d28afb7b8be79047a37648382e5ea27a59","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"ff0ade992820edc85e05d15d90cb79a1f0f2cb901639f75ab50d14e3e64b2f88","fragment_id":"7a17201b983368d758fef548f959183c3f685d10d01f1e2f0c04479b8ba8344e","kind":"json_document","key":"类型连接验证规则.json","label":"类型连接验证规则.json","locator":"","origin":"container","byte_start":44623369,"byte_end":44624697,"line_start":1069282,"line_end":1069350,"sha256":"2a42d7edcc57acf0b626a70959647f952b65be0d2404a0945bc55e9b8e72d173"}},{"name":"类型组合约束.json","value":{"max_genre_combination":3,"max_mechanisms_per_project":5,"max_structures_per_project":2,"max_styles_per_project":3,"max_tones_per_project":2,"incompatible_pairs":[],"requires_manual_review":true,"auto_combination_forbidden":true,"rules":["类型组合不得自动生成所有排列","混合类型必须在混合类型表中定义","项目层可覆盖兼容性但需记录原因"],"schema_version":"TYPE_C-1.0.0"},"source_ref":{"id":"8cff217c7dc9f84e6087e0fd844c549b9b7fb9fadccee08f785956ef9af3047b","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"afc92d27365be01808b6433bac92faf3f4147ec168a195e359f030947bc3934c","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"b304be6df16813d671eb8b19e7c58a1302154ddefb44e9f3582949439b5f8bfc","fragment_id":"8cff217c7dc9f84e6087e0fd844c549b9b7fb9fadccee08f785956ef9af3047b","kind":"json_document","key":"类型组合约束.json","label":"类型组合约束.json","locator":"","origin":"container","byte_start":46732858,"byte_end":46733330,"line_start":1144084,"line_end":1144099,"sha256":"c037c80967a1bfef594b11f70f56436c06cc2b63c29adae26ebbb35903cbd2ac"}},{"name":"作品动态模式验证规则.json","value":{"schema_name":"作品动态模式验证规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"DP-01","description":"dynamic_pattern_id必须非空且唯一"},{"rule_id":"DP-02","description":"source_work_ids必须存在"},{"rule_id":"DP-03","description":"必须包含not_guaranteed"},{"rule_id":"DP-04","description":"必须包含similarity_features"},{"rule_id":"DP-05","description":"必须包含originality_risk"},{"rule_id":"DP-06","description":"max_depth不得超过3"},{"rule_id":"DP-07","description":"max_activated_rules不得超过5"},{"rule_id":"DP-08","description":"max_state_updates不得超过12"},{"rule_id":"DP-09","description":"不得引用C00484-C00494"},{"rule_id":"DP-10","description":"不得覆盖类型系统D"},{"rule_id":"DP-11","description":"不得自动生成completed事件"},{"rule_id":"DP-12","description":"不得自动写入人物状态"},{"rule_id":"DP-13","description":"不得自动选择唯一行为"},{"rule_id":"DP-14","description":"fixture对象不得进入正式库"},{"rule_id":"DP-15","description":"不得生成虚构作品模式作为source_fact"}]},"source_ref":{"id":"e3fa008bef4a31123dfedd1b060bf17c4bb3fc2cd571ba54198178c3390bdf86","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"33bd68113ebd66cc6d73400c666be6d49c89cf0f2c8bc7fe74ae8bf5012013b1","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"d163c406dc566d0f39dadf40d95476bc3e67469f9c11f04880c543ea6131966a","fragment_id":"e3fa008bef4a31123dfedd1b060bf17c4bb3fc2cd571ba54198178c3390bdf86","kind":"json_document","key":"作品动态模式验证规则.json","label":"作品动态模式验证规则.json","locator":"","origin":"container","byte_start":46734650,"byte_end":46736158,"line_start":1144156,"line_end":1144221,"sha256":"7d0f5f7c433c645bb221e6137b377c6f46fea10410dd1ac4d2c2aa8495c90e87"}},{"name":"作品静态模式验证规则.json","value":{"schema_name":"作品静态模式验证规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"SP-01","description":"static_pattern_id必须非空且唯一"},{"rule_id":"SP-02","description":"source_work_ids必须存在"},{"rule_id":"SP-03","description":"必须包含not_guaranteed"},{"rule_id":"SP-04","description":"必须包含similarity_features"},{"rule_id":"SP-05","description":"必须包含originality_risk"},{"rule_id":"SP-06","description":"不得包含动态触发条件"},{"rule_id":"SP-07","description":"不得包含动态传播层数"},{"rule_id":"SP-08","description":"不得包含固定动作、固定死亡、固定爱情、固定升级、固定复仇、固定打脸、固定剧情结果"},{"rule_id":"SP-09","description":"fixture对象不得进入正式库"},{"rule_id":"SP-10","description":"不得引用C00484-C00494"},{"rule_id":"SP-11","description":"不得生成虚构作品模式作为source_fact"}]},"source_ref":{"id":"3f3d8dd727e4e92a8fef6d30475eb756526e0a142c7cd489e830a92864fe8ec0","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"f0c7b6f6843c0b62ac413d4f241ae74f29e09ab76061d409290184c5cacd80be","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"2815600e4a096bad851050a762ed7924bd219d15581e6772790ae133863ddae0","fragment_id":"3f3d8dd727e4e92a8fef6d30475eb756526e0a142c7cd489e830a92864fe8ec0","kind":"json_document","key":"作品静态模式验证规则.json","label":"作品静态模式验证规则.json","locator":"","origin":"container","byte_start":46737227,"byte_end":46738459,"line_start":1144267,"line_end":1144316,"sha256":"a408f8d79bf786d6fa729bd90df1de3e09bfde4266968ff4b790797089df5783"}},{"name":"作品连接搭配模板.json","value":{"combination_id":"","combination_kind":"","primary_type_id":"","type_ids":[],"subtype_ids":[],"mechanism_ids":[],"structure_ids":[],"style_ids":[],"source_pattern_ids":[],"static_connection_ids":[],"dynamic_rule_ids":[],"concept_ids":[],"event_type_ids":[],"information_type_ids":[],"resource_type_ids":[],"relationship_type_ids":[],"foreshadowing_type_ids":[],"satisfaction_type_ids":[],"compatibility_score":0,"diversity_score":0,"novelty_score":0,"similarity_score":0,"reuse_penalty":0,"originality_risk":"","quality_score":0,"generation_method":"","selection_status":"","not_guaranteed":[],"source_refs":[],"evidence_type":"template","confidence":0,"status":"active","schema_version":"H0D-1.0.0"},"source_ref":{"id":"9b892342539df3bd209b4d89afd8dcd14f222b20a7a1c19cc35a3ecc7f3c5b13","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"4f022205606dc66e221743114a82b1b3f32cb175bd3307632e4c26abfc2c3f99","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"c7e8b95352230c8a707944462064711ba984d437e562c9b7aa7adfd373903cb5","fragment_id":"9b892342539df3bd209b4d89afd8dcd14f222b20a7a1c19cc35a3ecc7f3c5b13","kind":"json_document","key":"作品连接搭配模板.json","label":"作品连接搭配模板.json","locator":"","origin":"container","byte_start":46738564,"byte_end":46739398,"line_start":1144320,"line_end":1144354,"sha256":"77057345c9bee99682564f3f329e59f073a6d1f06d4bd741ec960bfd738f9066"}},{"name":"作品连接搭配验证规则.json","value":{"schema_name":"作品连接搭配验证规则","schema_version":"H0D-1.0.0","rules":[{"rule_id":"COM-01","description":"combination_id必须非空且唯一"},{"rule_id":"COM-02","description":"combination_kind必须在枚举范围内"},{"rule_id":"COM-03","description":"不建立所有排列组合"},{"rule_id":"COM-04","description":"不用重复组合填充数量"},{"rule_id":"COM-05","description":"组合不得自动产生固定剧情"},{"rule_id":"COM-06","description":"动态搭配必须引用合法动态规则"},{"rule_id":"COM-07","description":"动态搭配不得引用待恢复规则"},{"rule_id":"COM-08","description":"fixture搭配不得进入正式库"},{"rule_id":"COM-09","description":"没有真实作品来源时，正式作品搭配库保持空模板"},{"rule_id":"COM-10","description":"不得引用C00484-C00494"},{"rule_id":"COM-11","description":"静态和动态搭配必须严格分离"}]},"source_ref":{"id":"c0f5a40e6e05b2189caeaf742a2340faf54597cc7b2d2b48af184a252502b1a5","source_id":"19e780143737a236e20054de927a29c4e1a361ff4b17dccbcac6d875b6218f20","sha256":"b65c599b900c719523e60308144c58df1e4e9702605a166be468ece474629d84","file_sha256":"e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0","path":"02_原版资料/原始资料/类型连接.txt"},"document_ref":{"id":"204eac7b6fc7618db98869f8ec1982db7f17ac31dcc4df01ef11d7e03ecaabd4","fragment_id":"c0f5a40e6e05b2189caeaf742a2340faf54597cc7b2d2b48af184a252502b1a5","kind":"json_document","key":"作品连接搭配验证规则.json","label":"作品连接搭配验证规则.json","locator":"","origin":"container","byte_start":46739509,"byte_end":46740729,"line_start":1144358,"line_end":1144407,"sha256":"cce01a50bc03a98c7532f1b4a35f51f697e2efb9cd65fd377ee9df89d9b2a2e6"}}]''')


def compiler():
    assert importlib.util.find_spec("nw.materials.governance_contracts") is not None, "governance compiler is missing"
    return importlib.import_module("nw.materials.governance_contracts").compile_governance


def compile_docs():
    return compiler()(copy.deepcopy(DOCUMENTS))


def test_compiler_preserves_exact_source_contracts_without_adoption_authority():
    contract = compile_docs()
    assert contract["status"] == "ready"
    assert len(contract["requirements"]) == 116
    assert len([r for r in contract["requirements"] if r["rule_id"].startswith(("V", "DP-", "SP-", "COM-"))]) == 53
    assert all("source_text" in r and r["source_ref"]["document_sha256"] for r in contract["requirements"])
    assert contract["authority"] == "governance_only"
    assert "per_scene" in contract["dependencies"]["dynamic_limits"]["count_scope"]


@pytest.mark.parametrize("index", range(7))
def test_unknown_source_change_cannot_reuse_old_semantics(index):
    docs = copy.deepcopy(DOCUMENTS)
    docs[index]["value"]["schema_version"] = "UNREVIEWED-9"
    contract = compiler()(docs)
    changed = [r for r in contract["requirements"] if r["document_name"] == docs[index]["name"]]
    assert changed and all(r["status"] == "waiting" for r in changed)
    assert any(i["document_name"] == docs[index]["name"] for i in contract["issues"])


def test_ambiguous_duplicate_document_does_not_select_an_arbitrary_version():
    docs = copy.deepcopy(DOCUMENTS)
    docs.append(copy.deepcopy(docs[1]))
    contract = compiler()(docs)
    assert contract["status"] == "waiting"
    assert any(i["kind"] == "ambiguous_document" for i in contract["issues"])


def checker():
    assert importlib.util.find_spec("nw.materials.governance_checks") is not None, "governance evaluator is missing"
    return importlib.import_module("nw.materials.governance_checks").evaluate_governance


def digest(value):
    from hashlib import sha256
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def inputs():
    connection = {"connection_id": "TSC_000001", "source_id": "genre-a", "source_kind": "genre",
                  "target_id": "concept-a", "target_kind": "concept",
                  "connection_type": "TYPE_SUPPORTS_CONCEPT", "relation_scope": "genre_level",
                  "direction": "directed", "weight": 0.5, "priority": 5, "conditions": [],
                  "effects": [], "not_guaranteed": ["不保证剧情结果"], "source_refs": [],
                  "evidence_type": "template", "confidence": 0.5, "status": "active",
                  "schema_version": "TYPE_C-1.0.0"}
    dynamic = {"dynamic_pattern_id": "DP1", "source_work_ids": ["work-a"], "not_guaranteed": [],
               "similarity_features": [], "originality_risk": "unassessed", "max_depth": 3,
               "max_activated_rules": 5, "max_state_updates": 12, "dynamic_rule_ids": ["C00001"],
               "status": "active", "evidence_type": "normalized"}
    static = {"static_pattern_id": "SP1", "source_work_ids": ["work-a"], "not_guaranteed": [],
              "similarity_features": [], "originality_risk": "unassessed",
              "status": "active", "evidence_type": "normalized"}
    combo = copy.deepcopy(DOCUMENTS[5]["value"])
    combo.update(combination_id="COM1", combination_kind="静态", primary_type_id="genre-a",
                 type_ids=["genre-a"], source_work_ids=["work-a"])
    proof = {"source_id": "test-source", "sha256": "a" * 64, "locator": "/known"}
    return {"scope": {"source_id": DOCUMENTS[0]["source_ref"]["source_id"], "stage": "design",
                      "action": "validate_design", "target": "formal", "scene_id": "scene-1",
                      "document_names": [d["name"] for d in DOCUMENTS]},
            "subjects": {"connections": [connection], "dynamic_patterns": [dynamic],
                         "static_patterns": [static], "combinations": [combo]},
            "registries": {"entities": {"genre-a": {"kind": "genre", "source_ref": proof},
                                        "concept-a": {"kind": "concept", "source_ref": proof}},
                           "works": {"work-a": {"real_work": True, "source_ref": proof}},
                           "dynamic_rules": {"C00001": {"status": "approved", "source_ref": proof}},
                           "hybrid_genres": {}, "enums": {}},
            "project_config": {"genre_ids": ["genre-a"], "mechanism_ids": [], "structure_ids": [],
                               "style_ids": [], "tone_ids": []}}


def check(rule_id, value=None, contract=None):
    result = checker()(contract or compile_docs(), inputs() if value is None else value)
    matches = [row for row in result["checks"] if row["rule_id"] == rule_id]
    assert matches, rule_id
    return matches[0]


def witness(rule_id, value, status="pass"):
    from hashlib import sha256
    contract = compile_docs()
    rule = next(r for r in contract["requirements"] if r["rule_id"] == rule_id)
    subject = value["subjects"][rule["subject_kind"]][0]
    subject_id = next(subject[k] for k in ("connection_id", "dynamic_pattern_id", "static_pattern_id", "combination_id") if k in subject)
    text = "测试设计：此关系只说明静态适配，不预定任何行为或剧情结果。"
    artifact_sha = sha256(text.encode("utf-8")).hexdigest()
    scope_sha = digest({k: v for k, v in value.items() if k not in {"semantic_evidence", "reviews", "artifacts", "author_review"}})
    value["artifacts"] = [{"id": "design-1", "text": text, "sha256": artifact_sha}]
    value["reviews"] = [{"id": "review-1", "role": "author", "completed": True,
                          "subject_sha256": digest(subject), "artifact_sha256": artifact_sha,
                          "scope_fingerprint": scope_sha}]
    value["author_review"] = {"id": "review-1", "approved": True, "scope_fingerprint": scope_sha,
                               "source_document_sha256": rule["source_ref"]["document_sha256"],
                               "subject_sha256": digest(subject), "reason": "本次实际范围的作者评审"}
    value["semantic_evidence"] = [{"requirement_key": rule["requirement_key"],
                                  "source_document_sha256": rule["source_ref"]["document_sha256"],
                                  "subject_id": subject_id, "subject_sha256": digest(subject),
                                  "stage": "design", "review_id": "review-1", "artifact_id": "design-1",
                                  "artifact_sha256": artifact_sha, "evidence_location": "/text",
                                  "scope_fingerprint": scope_sha,
                                  "status": status, "reason": "作者核对具体设计及原句边界，保留实际依据。"}]
    return value


def test_missing_subjects_waits_but_explicit_empty_scope_is_not_a_zero_record_pass():
    value = inputs()
    del value["subjects"]["connections"]
    assert check("V01", value)["status"] == "waiting"
    value["subjects"]["connections"] = []
    row = check("V01", value)
    assert row["status"] == "not_applicable"
    assert row["findings"]


@pytest.mark.parametrize("rule_id", [
    "V01","V02","V03","V04","V05","V06","V07","V08","V09","V10","V11","V12","V13","V14","V15","V16",
    "DP-01","DP-02","DP-03","DP-04","DP-05","DP-06","DP-07","DP-08","DP-09","DP-10","DP-11","DP-12","DP-13","DP-14","DP-15",
    "SP-01","SP-02","SP-03","SP-04","SP-05","SP-06","SP-07","SP-08","SP-09","SP-10","SP-11",
    "COM-01","COM-02","COM-03","COM-04","COM-05","COM-06","COM-07","COM-08","COM-09","COM-10","COM-11"
])
def test_each_original_rule_consumes_actual_subject_and_reports_exact_source(rule_id):
    row = check(rule_id)
    assert row["source_ref"]["json_pointer"].startswith(("/rules/", "/validation_rules/"))
    assert row["source_text"]
    assert row["checked_input"]["subject"]
    assert row["status"] in {"pass", "failed", "waiting", "not_applicable"}


@pytest.mark.parametrize("rule_id,kind,field,bad", [
    ("V01","connections","source_id",None),("V02","connections","target_id",None),
    ("V03","connections","source_kind","tone"),("V04","connections","target_kind","style"),
    ("V05","connections","connection_type","TYPE_CAUSES_DEATH"),
    ("V12","connections","status","pending"),("V13","connections","evidence_type","fixture"),
    ("V14","connections","evidence_type",None),("V15","connections","not_guaranteed",None),
    ("V16","connections","schema_version",None),
    ("DP-01","dynamic_patterns","dynamic_pattern_id",""),
    ("DP-02","dynamic_patterns","source_work_ids",["invented-work"]),
    ("DP-03","dynamic_patterns","not_guaranteed",None),
    ("DP-04","dynamic_patterns","similarity_features",None),
    ("DP-05","dynamic_patterns","originality_risk",None),
    ("DP-06","dynamic_patterns","max_depth",4),("DP-07","dynamic_patterns","max_activated_rules",6),
    ("DP-08","dynamic_patterns","max_state_updates",13),
    ("DP-09","dynamic_patterns","dynamic_rule_ids",["C00484"]),
    ("DP-14","dynamic_patterns","status","fixture"),
    ("SP-01","static_patterns","static_pattern_id",""),
    ("SP-02","static_patterns","source_work_ids",["invented-work"]),
    ("SP-03","static_patterns","not_guaranteed",None),
    ("SP-04","static_patterns","similarity_features",None),
    ("SP-05","static_patterns","originality_risk",None),
    ("SP-09","static_patterns","status","fixture"),
    ("SP-10","static_patterns","dynamic_rule_ids",["C00494"]),
    ("COM-01","combinations","combination_id",""),
    ("COM-06","combinations","dynamic_rule_ids",["unknown-rule"]),
    ("COM-07","combinations","dynamic_rule_ids",["C00484"]),
    ("COM-08","combinations","status","fixture"),
    ("COM-10","combinations","dynamic_rule_ids",["C00490"])
])
def test_declared_data_violations_fail_at_the_affected_rule(rule_id, kind, field, bad):
    value = inputs()
    if bad is None:
        value["subjects"][kind][0].pop(field)
    else:
        value["subjects"][kind][0][field] = bad
    if rule_id == "COM-06":
        value["subjects"][kind][0]["combination_kind"] = "动态"
    assert check(rule_id, value)["status"] == "failed"


@pytest.mark.parametrize("rule_id", ["V06","V07","V08","V09","V10","V11","DP-10","SP-06","SP-07","SP-08","COM-03","COM-04","COM-05","COM-11"])
def test_semantic_rules_require_grounded_review_and_preserve_negative_verdict(rule_id):
    value = inputs()
    assert check(rule_id, value)["status"] == "waiting"
    assert check(rule_id, witness(rule_id, value, "failed"))["status"] == "failed"
    assert check(rule_id, witness(rule_id, inputs()))["status"] == "pass"


def test_rule_name_keyword_and_stale_hash_never_prove_semantics():
    value = inputs()
    value["semantic_evidence"] = [{"rule_id": "V07", "status": "pass", "source_guidance": "不包含固定剧情结果"}]
    assert check("V07", value)["status"] == "waiting"
    value = witness("V07", inputs())
    value["subjects"]["connections"][0]["effects"] = ["必然发生死亡"]
    assert check("V07", value)["status"] == "waiting"


def test_missing_combo_enum_is_waiting_instead_of_guessing_from_static_container():
    assert check("COM-02")["status"] == "waiting"


def test_fixture_modes_cannot_be_source_facts_even_with_a_synthetic_work_id():
    for rule_id, kind in (("DP-15", "dynamic_patterns"), ("SP-11", "static_patterns")):
        value = inputs()
        value["subjects"][kind][0]["evidence_type"] = "source_fact"
        value["registries"]["works"]["work-a"]["real_work"] = False
        assert check(rule_id, value)["status"] == "failed"


@pytest.mark.parametrize("field,limit", [("genre_ids",3),("mechanism_ids",5),("structure_ids",2),("style_ids",3),("tone_ids",2)])
def test_project_limits_check_actual_selected_ids(field, limit):
    mapping = {"genre_ids":"max_genre_combination","mechanism_ids":"max_mechanisms_per_project",
               "structure_ids":"max_structures_per_project","style_ids":"max_styles_per_project",
               "tone_ids":"max_tones_per_project"}
    value = inputs()
    value["project_config"][field] = [f"item-{i}" for i in range(limit+1)]
    assert check("CONFIG-"+mapping[field], value)["status"] == "failed"
    del value["project_config"][field]
    assert check("CONFIG-"+mapping[field], value)["status"] == "waiting"


def test_dynamic_actual_per_scene_trace_cannot_exceed_declared_limits():
    value = inputs()
    subject = value["subjects"]["dynamic_patterns"][0]
    value["execution_trace"] = {"scene_id":"scene-1","complete":True,
        "subject_hashes":{"DP1":digest(subject)},"activated_rule_ids":[f"C{i}" for i in range(6)],
        "state_updates":[{} for _ in range(13)],"max_observed_depth":2}
    assert check("DP-07", value)["status"] == "failed"
    assert check("DP-08", value)["status"] == "failed"
    value["execution_trace"]["activated_rule_ids"] = ["C00001"]
    value["execution_trace"]["state_updates"] = []
    assert check("DP-07", value)["status"] == "pass"
    assert check("DP-08", value)["status"] == "pass"
    assert check("DP-06", value)["status"] == "waiting"


def test_auto_and_state_write_scope_conflicts_stay_waiting_without_author_decision():
    assert check("CONFIG-auto_combination_forbidden")["status"] == "waiting"
    for ident in ("DP-11","DP-12","DP-13"):
        assert check(ident, witness(ident, inputs()))["status"] == "waiting"


def test_template_score_zero_does_not_manufacture_a_calibrated_score():
    for field in ("quality_score","confidence","novelty_score","similarity_score"):
        assert check("TEMPLATE-"+field)["status"] == "waiting"


def test_valid_static_enum_and_original_pattern_are_executed_without_guessing():
    assert check("V05")["status"] == "pass"
    assert check("FIELD-schema_version")["status"] == "pass"


def test_semantic_review_cannot_reuse_an_unchanged_record_against_a_changed_graph():
    value = witness("V10", inputs())
    value["subjects"]["connections"].append({"connection_id":"new-edge","source_id":"concept-a","target_id":"genre-a"})
    assert check("V10", value)["status"] == "waiting"


def test_author_label_alone_does_not_supply_current_author_approval():
    value = witness("V07", inputs())
    del value["author_review"]
    assert check("V07", value)["status"] == "waiting"


def test_writer_cannot_label_its_own_run_as_independent_review():
    value = witness("V07", inputs())
    del value["author_review"]
    value["reviews"][0].update(role="independent_review", run_id="same-run", writer_run_id="same-run")
    assert check("V07", value)["status"] == "waiting"
    value["reviews"][0]["run_id"] = "independent-run"
    assert check("V07", value)["status"] == "pass"


def test_empty_artifact_does_not_prove_a_semantic_effect():
    from hashlib import sha256
    value = witness("V07", inputs())
    empty_sha = sha256(b"").hexdigest()
    value["artifacts"][0].update(text="", sha256=empty_sha)
    value["semantic_evidence"][0]["artifact_sha256"] = empty_sha
    value["reviews"][0]["artifact_sha256"] = empty_sha
    assert check("V07", value)["status"] == "waiting"


def test_mutated_compiled_limit_cannot_change_the_frozen_source_meaning():
    contract = compile_docs()
    limit = next(r for r in contract["requirements"] if r["rule_id"] == "CONFIG-max_genre_combination")
    limit["source_value"] = 999
    value = inputs()
    value["project_config"]["genre_ids"] = ["one","two","three","four"]
    assert check("CONFIG-max_genre_combination", value, contract)["status"] == "waiting"


@pytest.mark.parametrize("bad", [None, False, [], "not-a-registry"])
def test_malformed_registry_dependency_is_reported_without_crashing(bad):
    value = inputs()
    value["registries"] = bad
    assert check("COM-02", value)["status"] == "waiting"


def test_invalid_actual_activation_members_do_not_count_as_real_rules():
    value = inputs()
    subject = value["subjects"]["dynamic_patterns"][0]
    value["execution_trace"] = {"scene_id":"scene-1","complete":True,
        "subject_hashes":{"DP1":digest(subject)},"activated_rule_ids":[False]}
    assert check("DP-07", value)["status"] == "failed"


@pytest.mark.parametrize("ident,kind", [("DP-15","dynamic_patterns"),("SP-11","static_patterns")])
def test_source_fact_with_zero_real_work_sources_is_rejected(ident, kind):
    value = inputs()
    value["subjects"][kind][0].update(evidence_type="source_fact", source_work_ids=[])
    assert check(ident, value)["status"] == "failed"


def test_dynamic_combination_cannot_skip_its_required_dynamic_rule():
    value = inputs()
    value["subjects"]["combinations"][0].update(combination_kind="动态", dynamic_rule_ids=[])
    assert check("COM-06", value)["status"] == "failed"


def test_source_work_library_cannot_be_filled_without_real_work_sources():
    value = inputs()
    value["scope"]["library_kind"] = "source_work_combinations"
    value["subjects"]["combinations"][0]["source_work_ids"] = []
    assert check("COM-09", value)["status"] == "failed"


def test_explicitly_unused_optional_score_is_not_promoted_to_a_required_metric():
    value = inputs()
    value["field_usage"] = {"COM1":{"quality_score":False}}
    assert check("TEMPLATE-quality_score", value)["status"] == "not_applicable"
