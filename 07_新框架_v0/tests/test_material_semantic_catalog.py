"""Real tiny catalogs exercise discovery fidelity without models or projects."""
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sqlite3

import pytest

from nw.materials.catalog import build_catalog
from nw.materials.unit_catalog import index_units
from nw.materials.work_catalog import SourceDesk
from test_material_catalog import _manifest
from test_material_stage_integration import pins_for


def api():
    try:
        return importlib.import_module("nw.materials.semantic_catalog")
    except ModuleNotFoundError:
        pytest.fail("Semantic source catalog is not implemented")


def tiny_catalog(tmp_path: Path, *, include_work_knowledge: bool = False) -> tuple[Path, str]:
    value = {"adaptation_id": "ADAPT_ONE", "object_kind": "冲突类型适配_adapter",
             "rule": "先核对当前人物能力，再设计动作", "max_depth": 3,
             "unclassified_native": "原文未解释的独立限制", "status": "pending",
             "confidence": 0, "empty": [], "optional": None}
    text = "SOURCE: 冲突类型适配.json\n=====\n" + json.dumps(value, ensure_ascii=False)
    if include_work_knowledge:
        text += '\n\nSOURCE: 作品知识库\\作品拆解\\商业深度拆解字段.json\n=====\n{"fields":["主题"]}\n'
    raw = text.encode()
    manifest = _manifest(tmp_path / "originals", tmp_path, [("types.txt", "types", raw)])
    workspace = tmp_path / "workspace"
    build_catalog(workspace, tmp_path / "originals", manifest)
    index_units(workspace, None)
    with sqlite3.connect(workspace / "materials/catalog.db") as db:
        owner = db.execute("SELECT id FROM material_units WHERE kind='record' AND key='ADAPT_ONE'").fetchone()[0]
    return workspace, owner


def test_context_keeps_current_owner_and_complete_review_not_its_old_guidance(tmp_path, monkeypatch):
    pin = pins_for(tmp_path, monkeypatch,
                   "### 1.1_动作\n【指令】每个主要动作前应有动因。\n", ["1.1_动作"])[0]
    with sqlite3.connect(tmp_path / "materials/adjudication.db") as db:
        review = json.loads(db.execute("SELECT payload_json FROM contracts WHERE owner_id=?", (pin["id"],)).fetchone()[0])
        review["contract"]["guidance"] = "错误旧指导：把元数据变身体信号"
        review["layer_contract"] = {"policy": "fixture-layer", "pairs": []}
        db.execute("UPDATE contracts SET payload_json=? WHERE owner_id=?",
                   (json.dumps(review, ensure_ascii=False), pin["id"]))
    source = SourceDesk(tmp_path).read(pin["id"])
    context = api().source_context(tmp_path, source)
    assert context["source_ref"]["id"] == pin["id"]
    assert context["source_ref"]["fragment_key"] == "1.1_动作"
    assert context["source_ref"]["byte_start"] == 0
    assert context["source_ref"]["line_start"] == 1
    assert context["source_context"]["family"] == "library"
    assert context["adjudication_contract"]["source_refs"] == review["source_refs"]
    assert context["adjudication_contract"]["layer_contract"] == review["layer_contract"]
    assert context["adjudication_contract"]["contract"] == review["contract"]
    from nw.materials.source_semantics import compile_semantics
    contract = compile_semantics(source, context)
    assert any("每个主要动作前应有动因" in str(x["value"]) for x in contract["obligations"])
    assert all("身体信号" not in str(x["value"]) for x in contract["obligations"])


def test_audit_writes_complete_field_ledger_and_discovery_index_without_approval(tmp_path):
    workspace, owner = tiny_catalog(tmp_path)
    details = tmp_path / "details.json"
    before = sha256((workspace / "materials/catalog.db").read_bytes()).hexdigest()
    summary = api().audit_semantic_sources(workspace, write_index=True, details_path=details)
    assert summary["status"] == "COMPILED_SOURCE_FIDELITY_AUDITED"
    assert summary["fidelity_failures"] == 0
    assert summary["semantic_effects_verified"] == 0
    assert summary["source_clause_count"] > summary["deterministic_clause_count"] > 0
    assert summary["native_or_semantic_review_count"] > 0
    assert summary["source_issue_counts"]["compilation:unclassified_original_field"] > 0
    assert summary["read_verification"]["fragments_verified"] == 1
    assert sha256((workspace / "materials/catalog.db").read_bytes()).hexdigest() == before
    saved = json.loads(details.read_text(encoding="utf-8"))
    row = next(x for x in saved["rows"] if x["source_id"] == owner)
    by_path = {x["locator"]: x["disposition"] for x in row["field_dispositions"]}
    assert by_path["/rule"] == "source_clause"
    assert by_path["/unclassified_native"] == "source_clause"
    assert by_path["/status"] == "original_metadata"
    assert by_path["/empty"] == "empty_container"
    assert by_path["/optional"] == "empty_value"
    assert row["source_state"] == "not_adjudicated"
    metadata = api().load_semantic_metadata(workspace)
    assert metadata[owner]["semantic_disposition"] == "project_method"
    assert metadata[owner]["execution_stages"] == ["type_adaptation","plot_design"]
    assert metadata[owner]["source_state"] == "not_adjudicated"
    assert metadata[owner]["semantic_contract_sha256"] == row["contract"]["sha256"]
    assert "can_offer_for_design" not in metadata[owner]


def test_discovery_cache_is_versioned_and_rejects_changed_compiler_or_source_set(tmp_path, monkeypatch):
    workspace, owner = tiny_catalog(tmp_path)
    mod = api()
    first = Path(mod.audit_semantic_sources(workspace, write_index=True)["index_path"])
    second = Path(mod.audit_semantic_sources(workspace, write_index=True)["index_path"])
    assert first != second and first.is_file() and second.is_file()
    assert owner in mod.load_semantic_metadata(workspace)
    import nw.materials.source_semantics as compiler
    with monkeypatch.context() as patch:
        patch.setattr(compiler, "POLICY", "compiler-new-version")
        assert mod.load_semantic_metadata(workspace) == {}
    with sqlite3.connect(workspace / "materials/catalog.db") as db:
        db.execute("UPDATE sources SET status='CHANGED'")
    assert mod.load_semantic_metadata(workspace) == {}


def test_missing_or_incomplete_discovery_index_returns_empty_metadata(tmp_path):
    workspace, _ = tiny_catalog(tmp_path)
    mod = api()
    assert mod.load_semantic_metadata(workspace) == {}
    result = mod.audit_semantic_sources(workspace, write_index=True)
    with sqlite3.connect(result["index_path"]) as db:
        db.execute("UPDATE metadata SET value_json='false' WHERE key='complete'")
    assert mod.load_semantic_metadata(workspace) == {}


def test_index_round_trip_excludes_work_knowledge_from_writing_sources(tmp_path):
    workspace, owner = tiny_catalog(tmp_path, include_work_knowledge=True)
    mod = api()
    original = SourceDesk(workspace)
    assert owner in original.by_id
    assert all('商业深度拆解字段' not in row['fragment_key'] for row in original.rows)
    result = mod.audit_semantic_sources(workspace, write_index=True)
    assert result['status'] == 'COMPILED_SOURCE_FIDELITY_AUDITED'
    assert result['work_knowledge_only_count'] > 0
    assert set(mod.load_semantic_metadata(workspace)) == original.by_id.keys()


def test_audit_checks_parent_fragment_hash_even_when_unit_slice_is_unchanged(tmp_path):
    workspace, owner = tiny_catalog(tmp_path)
    import nw.materials.work_catalog as desk_module
    original_reader = desk_module.show_fragment
    with sqlite3.connect(workspace / "materials/catalog.db") as db:
        ident, raw = db.execute("SELECT id,payload FROM fragments LIMIT 1").fetchone()
        db.execute("UPDATE fragments SET payload=? WHERE id=?", (b"X" + raw[1:], ident))
    assert SourceDesk(workspace).read(owner)["source"]["id"] == owner
    with pytest.raises(ValueError, match="hash"):
        api().audit_semantic_sources(workspace, write_index=True)
    assert desk_module.show_fragment is original_reader
    assert api().load_semantic_metadata(workspace) == {}


@pytest.mark.parametrize("mutation", ["wrong_value", "missing_field"])
def test_audit_rejects_wrong_json_values_and_unaccounted_fields(tmp_path, monkeypatch, mutation):
    workspace, _ = tiny_catalog(tmp_path)
    mod = api()
    original = mod.compile_semantics
    def broken(source, context):
        result = original(source, context)
        if source["original_text"].lstrip().startswith("{"):
            if mutation == "wrong_value":
                next(x for x in result["obligations"] if x["locator"].endswith("/max_depth"))["value"] = 999
            else:
                result["obligations"] = [x for x in result["obligations"] if not x["locator"].endswith("/unclassified_native")]
        from nw.task_models import content_sha256
        result["sha256"] = content_sha256({k:v for k,v in result.items() if k != "sha256"})
        return result
    monkeypatch.setattr(mod, "compile_semantics", broken)
    result = mod.audit_semantic_sources(workspace, write_index=True)
    assert result["status"] == "SOURCE_FIDELITY_FAILED"
    assert result["fidelity_failures"] > 0
    assert api().load_semantic_metadata(workspace) == {}

