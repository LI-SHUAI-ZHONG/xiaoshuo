from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from nw.cli import main
from nw.materials.catalog import build_catalog, list_catalog, show_fragment
from nw.materials.adjudication import build_adjudications
from nw.materials.unit_catalog import index_units, list_units
from nw.materials.work_catalog import SourceDesk, original_text


TYPE_PATH = "02_原版资料/原始资料/类型系统.txt"
TYPE_SHA = "aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582"


@pytest.fixture(scope="module")
def work_catalog(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    content = (root / TYPE_PATH).read_bytes()
    assert sha256(content).hexdigest() == TYPE_SHA
    temp = tmp_path_factory.mktemp("work-knowledge")
    manifest = temp / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "catalog_inputs": [{
        "path": TYPE_PATH, "family": "types", "layer": "baseline",
        "sha256": TYPE_SHA, "bytes": len(content),
    }]}), encoding="utf-8")
    workspace = temp / "workspace"
    source_id = build_catalog(workspace, root, manifest)["sources"][0]["source_id"]
    blocks = [row for row in list_catalog(workspace, source_id, None)["fragments"]
              if row["kind"] == "source_block"]
    assert len(blocks) == 449
    return workspace, blocks


def read_fixture(catalog, number):
    workspace, blocks = catalog
    original = show_fragment(workspace, blocks[number - 1]["fragment_id"])
    assert original["key"].startswith("作品知识库\\测试夹具\\")
    _, _, body = original["text"].split("\n", 2)
    return original_text(body.strip())[1]


def call_cli(workspace, capsys, *options):
    result = main(["--workspace", str(workspace), "materials", "work-knowledge", *options])
    console = capsys.readouterr()
    assert result == 0, console.err
    return json.loads(console.out)


@pytest.mark.parametrize(("stage", "numbers"), [
    ("intake", [382, 383, 384, 387]),
    ("breakdown", [60, 80, 388, 389, 390, 391, 392, 393]),
    ("abstraction", [385, 386]),
    ("review", [373, 374]),
    ("archive", [349, 356]),
])
def test_work_knowledge_cli_reads_only_the_step_own_sources(work_catalog, capsys, stage, numbers):
    workspace, blocks = work_catalog
    result = call_cli(workspace, capsys, "--stage", stage)
    assert [item["source_block"] for item in result["materials"]] == numbers
    for item, number in zip(result["materials"], numbers, strict=True):
        frozen = blocks[number - 1]
        assert item["key"] == frozen["key"]
        assert item["sha256"] == frozen["sha256"]
        assert item["line_start"] == frozen["line_start"]
        assert item["original"]
        assert item["usage"]
    if stage == "breakdown":
        by_block = {item["source_block"]: item["original"] for item in result["materials"]}
        assert by_block[80]["batch_size"] == 5
        assert len(by_block[389]["dimensions"]) == 56
        assert by_block[393]["analyses"] == []
    if stage == "archive":
        assert result["use"] == "provenance_only"
        archive = {item["source_block"]: item["original"] for item in result["materials"]}
        assert archive[349]["verification_status"] == "pending_review"
        assert archive[356]["active_adapter"] == "disabled"


FIXTURE_CASES = (
    (83, "intake", "source_template", "valid", None),
    (84, "intake", "source", "valid", None),
    (85, "intake", "source", "waiting", "missing_retrieved_at"),
    (86, "intake", "source", "waiting", "missing_metric_scope"),
    (87, "intake", "metric_comparison", "invalid", "not_comparable"),
    (88, "intake", "source_conflict", "waiting", "source_conflict"),
    (89, "intake", "source", "invalid", "copyright_risk"),
    (90, "intake", "source", "waiting", "source_locator"),
    (91, "breakdown", "analysis", "valid", None),
    (92, "breakdown", "analysis", "invalid", "missing_required"),
    (93, "breakdown", "analysis", "invalid", "missing_required"),
    (94, "breakdown", "analysis", "invalid", "incomplete_ratio"),
    (95, "breakdown", "analysis", "invalid", "incomplete_statistic"),
    (96, "breakdown", "analysis", "invalid", "missing_required"),
    (97, "breakdown", "analysis", "invalid", "copyright_risk"),
    (98, "breakdown", "analysis", "invalid", "duplicate_id"),
    (99, "breakdown", "analysis", "invalid", "empty_id"),
    (100, "breakdown", "analysis", "valid", None),
    (101, "abstraction", "type_case", "valid", None),
    (102, "abstraction", "style_case", "valid", None),
    (103, "abstraction", "static_pattern", "valid", None),
    (104, "abstraction", "dynamic_pattern", "valid", None),
    (105, "abstraction", "combination", "valid", None),
    (106, "abstraction", "dynamic_pattern", "invalid", "propagation_limit"),
    (107, "abstraction", "dynamic_pattern", "invalid", "excluded_reference"),
    (108, "abstraction", "type_case", "invalid", "missing_required"),
    (109, "abstraction", "index", "invalid", "full_object_in_index"),
    (110, "abstraction", "style_case", "invalid", "copyright_risk"),
    (111, "abstraction", "type_case", "invalid", "duplicate_id"),
    (112, "abstraction", "type_case", "invalid", "empty_id"),
    (113, "intake", "work", "valid", None),
    (114, "intake", "work", "waiting", "source_locator"),
    (115, "intake", "work", "invalid", "copyright_risk"),
)


def fixture_input(catalog, number, kind):
    entry = read_fixture(catalog, number)
    records = entry["items"] if "items" in entry else [entry]
    if kind == "metric_comparison":
        comparison = deepcopy(entry)
        comparison["source_record_id"] = "FIXTURE_H0B_COMPARE"
        comparison["platform"] = "test_platform_b"
        records.append(comparison)
    return {"kind": kind, "records": records}


@pytest.mark.parametrize(("number", "stage", "kind", "status", "finding"), FIXTURE_CASES,
                         ids=[f"SOURCE-{row[0]}" for row in FIXTURE_CASES])
def test_original_work_knowledge_fixtures_run_at_their_own_step(
        work_catalog, number, stage, kind, status, finding):
    from nw.materials.work_knowledge import check_work_inputs

    workspace, _ = work_catalog
    data = fixture_input(work_catalog, number, kind)
    test_result = check_work_inputs(workspace, stage, data, test_mode=True)
    assert test_result["status"] == status, test_result["findings"]
    findings = {item["code"] for item in test_result["findings"]}
    if finding:
        assert finding in findings
    else:
        assert not findings
    normal_result = check_work_inputs(workspace, stage, data)
    assert normal_result["status"] == "invalid"
    assert any(item["code"] == "fixture_only" for item in normal_result["findings"])


def test_intake_level_requires_a_confirmed_source_even_for_a_long_file(work_catalog):
    from nw.materials.work_knowledge import check_work_inputs

    workspace, _ = work_catalog
    data = {"kind": "intake", "records": [{"input_id": "INPUT_X", "work_id": "WORK_X",
             "analysis_level": "LEVEL_3", "word_count": 30000, "source_refs": [],
             "authorization_status": "pending", "verification_status": "pending_review"}]}
    report = check_work_inputs(workspace, "intake", data)
    assert report["status"] == "waiting"
    assert report["analysis_scopes"] == []


def test_intake_level_uses_the_actual_allowed_modules_from_the_selected_rule(work_catalog):
    from nw.materials.work_knowledge import check_work_inputs

    workspace, _ = work_catalog
    data = {"kind": "intake", "records": [{"input_id": "INPUT_X", "work_id": "WORK_X",
             "analysis_level": "LEVEL_0", "source_refs": ["SRC_X"],
             "authorization_status": "confirmed", "verification_status": "verified"}]}
    report = check_work_inputs(workspace, "intake", data)
    assert report["status"] == "valid"
    scope = report["analysis_scopes"][0]
    assert scope["analysis_level"] == "LEVEL_0"
    assert "具体剧情" in scope["blocked_analysis"]
    assert scope["allowed_analysis"] == ["类型定位", "候选拆解模块", "待补充字段", "通用模式方向"]


def test_unfinished_review_cannot_be_treated_as_approved(work_catalog):
    from nw.materials.work_knowledge import check_work_inputs

    workspace, _ = work_catalog
    report = check_work_inputs(workspace, "review", {"kind": "review", "records": [{
        "review_id": "REVIEW_X", "analysis_id": "ANALYSIS_X", "review_status": "approved",
        "approved_for_case_library": True,
    }]})
    assert report["status"] == "waiting"
    assert any(item["code"] == "incomplete_review" for item in report["findings"])


def test_cli_does_not_echo_fixture_payload_on_failed_check(work_catalog, tmp_path, capsys):
    data = fixture_input(work_catalog, 97, "analysis")
    inputs = tmp_path / "analysis.json"
    inputs.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = call_cli(work_catalog[0], capsys, "--stage", "breakdown", "--inputs", str(inputs))
    assert report["input_review"]["status"] == "invalid"
    assert report["input_review"]["findings"][0]["code"] == "fixture_only"
    assert "这是测试正文内容，不应被保存" not in json.dumps(report, ensure_ascii=False)


def test_source_template_checks_the_original_field_layout(work_catalog):
    from nw.materials.work_knowledge import check_work_inputs

    data = read_fixture(work_catalog, 83)
    del data["source_name"]
    result = check_work_inputs(work_catalog[0], "intake", {
        "kind": "source_template", "records": [data],
    }, test_mode=True)
    assert result["status"] == "invalid"
    assert any(finding["path"] == "/records/0/source_name" for finding in result["findings"])


@pytest.mark.parametrize("adjudicated", [False, True])
def test_creative_source_desk_excludes_research_fixture_archive_and_candidate_blocks(
        work_catalog, tmp_path, adjudicated):
    workspace, blocks = work_catalog
    # A small copy of the real original blocks also exercises embedded units.
    documents = [show_fragment(workspace, blocks[n - 1]["fragment_id"]) for n in (63, 83, 126, 349, 373, 413)]
    data = "\n".join(item["text"] for item in documents).encode("utf-8")
    (tmp_path / "types.txt").write_bytes(data)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "catalog_inputs": [{
        "path": "types.txt", "family": "types", "layer": "baseline",
        "sha256": sha256(data).hexdigest(), "bytes": len(data),
    }]}), encoding="utf-8")
    isolated = tmp_path / "workspace"
    source = build_catalog(isolated, tmp_path, manifest)["sources"][0]["source_id"]
    index_units(isolated, source)
    if adjudicated:
        build_adjudications(isolated)
    desk = SourceDesk(isolated)
    search = desk.search("爽点类型适配")
    assert search["total"] > 0
    for excluded in documents[1:]:
        original = list_catalog(isolated, source, excluded["key"])["fragments"][0]
        units = list_units(isolated, source_id=None, fragment_id=original["fragment_id"],
                           key=None, kind=None, limit=500, offset=0)["units"]
        blocked_ids = {original["fragment_id"], *(row["unit_id"] for row in units)}
        returned = desk.search(excluded["key"], limit=40)["items"]
        assert blocked_ids.isdisjoint(row["id"] for row in returned)
        with pytest.raises(ValueError, match="outside the indexed method desk"):
            desk.read(original["fragment_id"])
