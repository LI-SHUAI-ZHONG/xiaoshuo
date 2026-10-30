"""Run the 11-stage execution pipeline against indexed project data."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from 资料消费审计 import audit_project
from 资料注册与完整性 import build_registry
from 全量资料解释词转译与创作绑定 import run as build_creation_bindings
from 写作资料证据验证 import verify as verify_writing_source_evidence
from 全量资料正文消费验证 import validate as validate_full_prose_consumption
from 资料运行准入准备 import prepare as prepare_runtime_admission
from 全资料生产能力门 import audit as audit_source_production
from 正式交付审批 import validate_formal_release
from 资料消费审计 import audit_material_duty_records
from 项目执行边界 import source_permission_errors, validate_execution_contract
from 灵感库选型器 import validate_selection
from 场景创作激活 import build_runtime_material_package, evaluate as evaluate_scene_activation
from 运行资料包契约 import load_package, validate_package, write_package
from 重建当前授权提交 import rebuild as rebuild_current_authorization
from 运行清单复核 import _write_manifest, finalize_run, initialize_run, register_artifact, register_read, verify_full_pipeline_manifest, verify_manifest, write_failure_receipt
from 项目生命周期管理 import validate_active_project
RESOURCE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RESOURCE_ROOT
ROOT = RESOURCE_ROOT
EVIDENCE = PROJECT_ROOT / "文档" / "证据"
OUTPUT_DIR = EVIDENCE / "execution_outputs"
CONSUMPTION = EVIDENCE / "执行消费.jsonl"
RUN_EVIDENCE_DIR = EVIDENCE / "运行"
TYPE_SYSTEM = RESOURCE_ROOT / "原始资料" / "类型系统.txt"
TYPE_INDEX = EVIDENCE / "类型连接全局索引.json"
STATIC_INDEX = EVIDENCE / "静态网络索引.json"
STATIC_FULL = RESOURCE_ROOT / "网络完整数据" / "静态连接完整数据.json"
STATIC_BINDING_SUMMARY = EVIDENCE / "静态网络绑定摘要.json"
DYNAMIC_FULL = RESOURCE_ROOT / "网络完整数据" / "动态连接完整数据.json"
ANCHOR_INDEX = EVIDENCE / "锚点分类索引.json"
ANCHOR_NETWORK = RESOURCE_ROOT / "原始资料" / "锚点网络.txt"
RULE_FILES = (EVIDENCE / "类型连接规则.json", EVIDENCE / "静态连接采用规则.json", EVIDENCE / "锚点采用规则.json", EVIDENCE / "执行采用规则.json")
DYNAMIC_CONSUMPTION_RULE = EVIDENCE / "动态链消费规则.json"
LIBRARY = RESOURCE_ROOT / "原始资料" / "资料库.txt"
DYNAMIC_STATE = EVIDENCE / "动态网络状态摘要.json"
RESOURCE_REGISTRY = EVIDENCE / "资源注册表.json"
CREATION_BINDINGS = EVIDENCE / "全量资料解释词创作绑定.json"
PROJECT_CONFIG = PROJECT_ROOT / "配置" / "project_config.json"
BIBLE = PROJECT_ROOT / "配置" / "项目创作圣经.json"
RUN_ID = ""


def set_project_root(path: str | Path | None, run_id: str | None = None) -> None:
    """Bind project outputs and project-owned evidence to one explicit root."""
    global PROJECT_ROOT, ROOT, EVIDENCE, OUTPUT_DIR, CONSUMPTION, RUN_EVIDENCE_DIR, TYPE_INDEX
    global STATIC_INDEX, STATIC_BINDING_SUMMARY, ANCHOR_INDEX, DYNAMIC_STATE, RESOURCE_REGISTRY, CREATION_BINDINGS
    global TYPE_SYSTEM, STATIC_FULL, DYNAMIC_FULL, ANCHOR_NETWORK, LIBRARY
    global RULE_FILES, DYNAMIC_CONSUMPTION_RULE, PROJECT_CONFIG, BIBLE, RUN_ID
    PROJECT_ROOT = Path(path).expanduser().resolve() if path else RESOURCE_ROOT
    ROOT = PROJECT_ROOT
    EVIDENCE = PROJECT_ROOT / "文档" / "证据"
    RUN_EVIDENCE_DIR = EVIDENCE / "运行" / RUN_ID if RUN_ID else EVIDENCE / "运行"
    OUTPUT_DIR = RUN_EVIDENCE_DIR / "module_outputs"
    CONSUMPTION = RUN_EVIDENCE_DIR / "执行消费.jsonl"
    TYPE_INDEX = EVIDENCE / "类型连接全局索引.json"
    STATIC_INDEX = EVIDENCE / "静态网络索引.json"
    STATIC_BINDING_SUMMARY = EVIDENCE / "静态网络绑定摘要.json"
    ANCHOR_INDEX = EVIDENCE / "锚点分类索引.json"
    DYNAMIC_STATE = EVIDENCE / "动态网络状态摘要.json"
    RESOURCE_REGISTRY = EVIDENCE / "资源注册表.json"
    CREATION_BINDINGS = EVIDENCE / "全量资料解释词创作绑定.json"
    TYPE_SYSTEM = PROJECT_ROOT / "原始资料" / "类型系统.txt"
    STATIC_FULL = PROJECT_ROOT / "网络完整数据" / "静态连接完整数据.json"
    DYNAMIC_FULL = PROJECT_ROOT / "网络完整数据" / "动态连接完整数据.json"
    ANCHOR_NETWORK = PROJECT_ROOT / "原始资料" / "锚点网络.txt"
    LIBRARY = PROJECT_ROOT / "原始资料" / "资料库.txt"
    RULE_FILES = (
        EVIDENCE / "类型连接规则.json",
        EVIDENCE / "静态连接采用规则.json",
        EVIDENCE / "锚点采用规则.json",
        EVIDENCE / "执行采用规则.json",
    )
    DYNAMIC_CONSUMPTION_RULE = EVIDENCE / "动态链消费规则.json"
    PROJECT_CONFIG = PROJECT_ROOT / "配置" / "project_config.json"
    BIBLE = PROJECT_ROOT / "配置" / "项目创作圣经.json"
    if run_id is not None:
        candidate = str(run_id).strip()
        if not candidate or Path(candidate).name != candidate or candidate in {".", ".."}:
            raise ValueError("run_id 必须是单个安全目录名")
        RUN_ID = candidate
    else:
        RUN_ID = "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    RUN_EVIDENCE_DIR = EVIDENCE / "运行" / RUN_ID
    OUTPUT_DIR = RUN_EVIDENCE_DIR / "module_outputs"
    CONSUMPTION = RUN_EVIDENCE_DIR / "执行消费.jsonl"
    RUN_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

WORLD_BLOCKS = set(range(10, 20)) | {20, 21, 22, 23, 24, 25, 26, 27, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40}
TYPE_EDGE_KEYWORDS = {
    "玄幻": ("能量", "修炼", "境界", "法宝", "宗门"),
    "仙侠": ("修仙", "渡劫", "洞府", "仙缘", "灵根"),
    "科幻": ("能量", "物理", "科技", "基因", "机械"),
    "都市": ("社会", "阶层", "职业", "资源", "货币"),
    "悬疑": ("悬念", "信息", "信任", "反转", "隐藏"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


PRIMARY_MATERIAL_PATHS = {
    "资料库": "原始资料/资料库.txt",
    "类型系统": "原始资料/类型系统.txt",
    "类型连接": "原始资料/类型连接.txt",
    "静态网络": "原始资料/静态网络.txt",
    "动态网络": "原始资料/动态网络.txt",
    "锚点网络": "原始资料/锚点网络.txt",
}


def _six_materials_digest() -> dict[str, str | None]:
    """Hash the fixed six raw sources, including missing files as ``None``."""
    result: dict[str, str | None] = {}
    for name, relative in PRIMARY_MATERIAL_PATHS.items():
        path = PROJECT_ROOT / relative
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return result


def _run_evidence_dir() -> Path:
    if not RUN_ID:
        raise RuntimeError("运行 ID 尚未初始化")
    path = EVIDENCE / "运行" / RUN_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_output_ref(module_id: str, name: str) -> str:
    """Return the authoritative run-scoped artifact reference."""
    return str((RUN_EVIDENCE_DIR / "module_outputs" / f"module_{module_id}_{name}.json").relative_to(PROJECT_ROOT)).replace("\\", "/")


def _write_run_input_snapshot(contract: dict[str, Any]) -> Path:
    """Freeze the exact admission inputs before any scene planning occurs."""
    blueprint = contract.get("blueprint", {})
    allowed_sources = blueprint.get("allowed_sources", []) if isinstance(blueprint, dict) else []
    inputs = sorted({
        PROJECT_CONFIG,
        EVIDENCE / "project_planning.json",
        CREATION_BINDINGS,
        EVIDENCE / "全书资料激活矩阵.json",
        EVIDENCE / "小说灵感选型回执.json",
        EVIDENCE / "动态网络状态摘要.json",
        EVIDENCE / "来源深度检查报告.json",
        EVIDENCE / "来源质量自主分析报告.json",
        EVIDENCE / "资料库索引.jsonl",
        EVIDENCE / "全量资料治理" / "全量检查报告.json",
        EVIDENCE / "资源注册表.json",
        EVIDENCE / "动态网络状态摘要.json",
        EVIDENCE / "来源深度检查报告.json",
        EVIDENCE / "来源质量自主分析报告.json",
        EVIDENCE / "严格资料升级" / "资料激活前置条件审计" / "资料激活前置条件清单.jsonl",
        # Freeze every original source explicitly. Derived indexes and full
        # network exports are not substitutes for the six raw source files.
        PROJECT_ROOT / "原始资料" / "资料库.txt",
        PROJECT_ROOT / "原始资料" / "动态网络.txt",
        PROJECT_ROOT / "原始资料" / "类型系统.txt",
        PROJECT_ROOT / "原始资料" / "类型连接.txt",
        PROJECT_ROOT / "原始资料" / "静态网络.txt",
        PROJECT_ROOT / "原始资料" / "锚点网络.txt",
        PROJECT_ROOT / "配置" / "类型配置模板.json",
        *(path for paths in MODULE_INPUTS.values() for path in paths),
    }, key=lambda path: str(path))
    input_paths = [path for path in inputs if path.is_file()]
    snapshot = {
        "schema_version": "run-input-snapshot-1.0",
        "run_id": RUN_ID,
        "created_at": now(),
        "blueprint_sha256": _sha256_json(blueprint),
        "project_id": contract.get("config", {}).get("project_id") if isinstance(contract.get("config"), dict) else None,
        "book_title": contract.get("config", {}).get("book_title") if isinstance(contract.get("config"), dict) else None,
        "six_materials_sha256": _six_materials_digest(),
        "story_bible_sha256": hashlib.sha256(BIBLE.read_bytes()).hexdigest() if BIBLE.is_file() else None,
        "allowed_sources": allowed_sources,
        "allowed_source_ids": sorted(str(item.get("source_id")) for item in allowed_sources if isinstance(item, dict) and item.get("source_id")),
        "inputs": [{"relative_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(read_bytes(path)).hexdigest()} for path in input_paths],
    }
    path = _run_evidence_dir() / "run_input_snapshot.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    initialize_run(PROJECT_ROOT, RUN_ID, input_snapshot_paths=[
        str(item["relative_path"]) for item in snapshot["inputs"]
    ])
    register_artifact(PROJECT_ROOT, RUN_ID, path, kind="input_snapshot", status="success", exit_code=0)
    # Module 00 is the run identity/input-freeze stage.  It is recorded as a
    # module output as well so the manifest covers the complete 00-11 chain.
    register_artifact(PROJECT_ROOT, RUN_ID, path, kind="module_output", module_id="00", status="success", exit_code=0)
    return path


def _evidence_layer(path: Path) -> str:
    relative = str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    if relative.startswith("原始资料/"):
        return "original_source"
    if relative.startswith("文档/证据/运行/"):
        return "runtime_derived"
    return "historical_artifact"


def _register_input_read(path: Path, read_source: str) -> Path:
    if RUN_ID and path.is_file():
        evidence_layer = _evidence_layer(path)
        registered = register_read(
            PROJECT_ROOT,
            RUN_ID,
            path,
            evidence_layer=evidence_layer,
            read_source=read_source,
        )
        # The input snapshot is immutable after Module 00/01 freezes it.
        # Actual reads are recorded separately; an unlisted read must fail the
        # manifest audit instead of being appended to the baseline at runtime.
        return registered
    return path


def read_json(path: Path) -> Any:
    _register_input_read(path, "执行管道.read_json")
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def evaluate_scene_prose_integrity(scene: dict[str, Any], expected_scene: dict[str, Any], minimum_characters: int = 120) -> dict[str, Any]:
    """Validate the structured narrative contract without inferring quality from keywords."""
    paragraphs = [str(value).strip() for value in scene.get("paragraphs", []) if str(value).strip()]
    records = [record for record in scene.get("source_records", []) if isinstance(record, dict)]
    required_fields = ("character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook")
    missing_contract_fields = [field for field in required_fields if not str(expected_scene.get(field, "")).strip()]
    record_indexes = [record.get("paragraph_index") for record in records]
    expected_indexes = list(range(len(paragraphs)))
    invalid_records = [
        index for index, record in enumerate(records)
        if not record.get("source_id")
        or not record.get("prose_location")
        or not isinstance(record.get("translation_evidence"), dict)
        or not str(record.get("translation_evidence", {}).get("trigger", "")).strip()
        or not str(record.get("translation_evidence", {}).get("result", "")).strip()
    ]
    character_count = len("\n".join(paragraphs))
    return {
        "passed": not missing_contract_fields and len(paragraphs) >= 4 and record_indexes == expected_indexes and not invalid_records,
        "length_warning": character_count < minimum_characters,
        "paragraph_count": len(paragraphs),
        "character_count": len("\n".join(paragraphs)),
        "missing_contract_fields": missing_contract_fields,
        "record_indexes": record_indexes,
        "expected_indexes": expected_indexes,
        "invalid_record_indexes": invalid_records,
    }


def audit_prose_runtime_provenance(
    scenes: list[dict[str, Any]],
    runtime_package: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Reject prose that cannot be traced to this run's selected material package."""
    errors: list[str] = []
    package_records = {
        str(row.get("binding_id")): row
        for row in runtime_package.get("records", [])
        if isinstance(row, dict) and row.get("activation_status") == "selected" and row.get("binding_id")
    }
    if not run_id or runtime_package.get("run_id") != run_id:
        errors.append("正文资料包 run_id 与当前运行不一致")
    if not package_records:
        errors.append("正文没有当前运行的选中资料包记录")
    for scene in scenes:
        scene_id = str(scene.get("scene_id") or "")
        records = scene.get("source_records", [])
        if not isinstance(records, list) or not records:
            errors.append(f"{scene_id}缺少正文来源消费记录")
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(f"{scene_id}正文来源记录{index}不是对象")
                continue
            binding_id = str(record.get("binding_id") or "")
            package_record = package_records.get(binding_id)
            if not package_record:
                errors.append(f"{scene_id}段落{index}未绑定当前运行的选中资料：{binding_id or 'missing'}")
                continue
            if record.get("run_id") != run_id:
                errors.append(f"{scene_id}段落{index}来源记录 run_id 不一致")
            if str(record.get("scene_id") or scene_id) != scene_id:
                errors.append(f"{scene_id}段落{index}来源记录场景不一致")
            if str(record.get("chapter_id") or scene.get("chapter_id") or "") != str(scene.get("chapter_id") or ""):
                errors.append(f"{scene_id}段落{index}来源记录章节不一致")
            if runtime_package.get("scene_contexts") and (record.get("package_id") != runtime_package.get("package_id") or record.get("continuity_hash") != package_record.get("continuity_hash")):
                errors.append(f"{scene_id}段落{index}冻结资料包连续性标识不一致")
            expected_packet_hash = hashlib.sha256(json.dumps(package_record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            if record.get("source_packet_sha256") != expected_packet_hash:
                errors.append(f"{scene_id}段落{index}资料包哈希不一致，疑似模板旁路")
            evidence = record.get("translation_evidence")
            if not isinstance(evidence, dict) or not str(evidence.get("trigger") or "").strip() or not str(evidence.get("result") or "").strip():
                errors.append(f"{scene_id}段落{index}缺少真实资料转译结果")
    return {
        "passed": not errors,
        "template_bypass_detected": bool(errors),
        "run_id": run_id,
        "package_run_id": runtime_package.get("run_id"),
        "checked_scene_count": len(scenes),
        "checked_record_count": sum(len(scene.get("source_records", [])) for scene in scenes if isinstance(scene, dict) and isinstance(scene.get("source_records"), list)),
        "errors": list(dict.fromkeys(errors)),
    }


def _build_book_activation_matrix(config: dict[str, Any], bindings: dict[str, Any]) -> tuple[dict[str, Any], list[Path]]:
    """Allocate all interpretable material across the configured book before drafting."""
    chapters = [item for item in config.get("chapter_plan", []) if isinstance(item, dict)]
    targets = [
        {"chapter_id": str(chapter.get("chapter_id")), "scene_id": str(scene.get("scene_id"))}
        for chapter in chapters for scene in chapter.get("scenes", []) if isinstance(scene, dict) and scene.get("scene_id")
    ]
    records = [item for item in bindings.get("records", []) if isinstance(item, dict) and item.get("binding_id")]
    assignments = []
    eligible_records = [
        record for record in records
        if record.get("model_input_eligible") is True
        and record.get("prose_write_allowed") is True
        and isinstance(record.get("source_ref"), str)
        and ":" in record.get("source_ref", "")
    ]
    eligible_records.sort(key=lambda item: str(item.get("binding_id")))
    for index, record in enumerate(records):
        binding = record.get("creation_binding", {}) if isinstance(record.get("creation_binding"), dict) else {}
        explicit_scene = binding.get("scene_id") or binding.get("target_scene_id")
        explicit_chapter = binding.get("chapter_id") or binding.get("target_chapter_id")
        assigned_scene = explicit_scene
        assigned_chapter = explicit_chapter
        assignment_basis = "explicit_reviewed_scene_target" if assigned_scene else "pending_scene_specific_match"
        # The book matrix records terminal states; it is not a scheduler.
        # Unmatched records remain deferred until a scene-specific selector
        # supplies a positive semantic match.
        assignments.append({
            "binding_id": record.get("binding_id"), "source_id": record.get("source_id"), "source_kind": record.get("source_kind"),
            "chapter_id": assigned_chapter, "scene_id": assigned_scene,
            "activation_class": binding.get("binding_class", "candidate_retrieval"),
            "creative_job": binding.get("creative_object"), "creative_action": binding.get("creative_action"),
            "status": "selected" if assigned_scene else "deferred",
            "assignment_basis": assignment_basis,
        })
    output = {"schema_version": "book-material-activation-matrix-1.0", "run_id": RUN_ID,
              "project_id": config.get("project_id"), "target_chapter_count": len(chapters),
              "target_scene_count": len(targets), "material_count": len(records),
              "coverage": {"assigned": sum(bool(item["scene_id"]) for item in assignments), "deferred": sum(not bool(item["scene_id"]) for item in assignments), "unassigned": sum(not bool(item["scene_id"]) for item in assignments)},
              "assignments": assignments}
    matrix_path = EVIDENCE / "全书资料激活矩阵.json"
    plan_path = EVIDENCE / "全书创作计划.json"
    matrix_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(json.dumps({"schema_version": "full-book-plan-1.0", "run_id": RUN_ID, "project_id": config.get("project_id"), "chapters": chapters, "activation_matrix": str(matrix_path.relative_to(PROJECT_ROOT)).replace("\\", "/")}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, [matrix_path, plan_path]


def _prose_source_permission_errors(scenes: list[dict[str, Any]]) -> list[str]:
    """Validate draft provenance; delivery permission is checked only in module 10."""
    registry = read_json(RESOURCE_REGISTRY) if RESOURCE_REGISTRY.is_file() else {}
    resources = registry.get("resources", {}) if isinstance(registry, dict) else {}
    library_entries: dict[str, dict[str, Any]] = {}
    library_index = PROJECT_ROOT / "文档" / "资料库索引.jsonl"
    library_text = read_text(LIBRARY) if LIBRARY.is_file() else ""
    library_titles = set()
    for library_line in library_text.splitlines():
        title_line = library_line.strip().strip("*").strip()
        if " " in title_line:
            library_number, library_name = title_line.split(None, 1)
            if re.fullmatch(r"\d+(?:\.\d+)?", library_number):
                library_titles.add((library_number, library_name.strip()))
    if library_index.is_file():
        for line in read_text(library_index).splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("entry_id"):
                library_entries.setdefault(str(row["entry_id"]), row)
    by_name = {
        Path(str(resource.get("relative_path", ""))).name: resource
        for resource in resources.values()
        if isinstance(resource, dict) and resource.get("relative_path")
    }
    errors = []
    blueprint_records = [record for scene in scenes for record in scene.get("source_records", []) if isinstance(record, dict)]
    errors.extend(source_permission_errors(PROJECT_ROOT, blueprint_records, phase="creation"))
    for scene in scenes:
        for record in scene.get("source_records", []):
            entry_id = record.get("library_entry_id")
            source_ref = record.get("source_ref") if isinstance(record.get("source_ref"), dict) else {}
            path_name = Path(str(source_ref.get("path", ""))).name
            if not path_name:
                errors.append(f"{scene.get('scene_id')}正文来源缺少source_ref.path")
                continue
            resource = by_name.get(path_name)
            if not resource:
                errors.append(f"{scene.get('scene_id')}正文来源未注册：{source_ref.get('path')}")
                continue
            if entry_id:
                entry = library_entries.get(str(entry_id))
                if not entry:
                    errors.append(f"{scene.get('scene_id')}正文引用资料条目不存在：{entry_id}")
                else:
                    indexed_ref = entry.get("source_ref") if isinstance(entry.get("source_ref"), dict) else {}
                    legacy_verified = (
                        entry.get("source_status") == "legacy_unmatched"
                        and (str(entry_id).split("_", 1)[0], str(entry.get("name", "")).strip()) in library_titles
                    )
                    if entry.get("source_status") in {"blocked", "candidate", "pending", "unconfirmed"} or (entry.get("source_status") == "legacy_unmatched" and not legacy_verified):
                        errors.append(f"{scene.get('scene_id')}正文引用资料条目状态不足：{entry_id}（{entry.get('source_status')}）")
                    if source_ref.get("location") != str(entry_id):
                        errors.append(f"{scene.get('scene_id')}正文资料定位与索引不一致：{entry_id}")
                    if indexed_ref.get("file") and Path(str(indexed_ref["file"])).name != path_name:
                        errors.append(f"{scene.get('scene_id')}正文资料来源文件与索引不一致：{entry_id}")
            elif path_name == Path(str(resources.get("library", {}).get("relative_path", ""))).name:
                errors.append(f"{scene.get('scene_id')}正文引用资料库但缺少library_entry_id")
            allowed = resource.get("allowed_uses", {})
            if resource.get("usage_level") == "blocked" or not allowed.get("draft_prose", False):
                errors.append(
                    f"{scene.get('scene_id')}正文引用来源权限不足：{path_name}"
                    f"（{resource.get('usage_level', 'unknown')}）"
                )
            if not source_ref.get("project_id") or not source_ref.get("location"):
                errors.append(f"{scene.get('scene_id')}正文来源证据不完整：{path_name}")
    return errors


def read_text(path: Path) -> str:
    _register_input_read(path, "执行管道.read_text")
    return path.read_text(encoding="utf-8-sig")


def read_bytes(path: Path) -> bytes:
    _register_input_read(path, "执行管道.read_bytes")
    return path.read_bytes()


def require(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return value is not None


def _contains_project_template(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return any(marker in text for marker in (
        "角色在不同层次上想要的东西", "角色“不能放手”的信念或原则",
        "角色在故事中从一个状态到另一个状态的变化轨迹", "待补充", "待确认",
        "未确认", "暂无", "主角", "当前地点", "场景继续推进",
    ))


def _project_config_errors(config: dict[str, Any]) -> list[str]:
    errors = []
    if config.get("schema_version") != "project-config-1.0":
        errors.append("schema_version 必须为 project-config-1.0")
    if config.get("project_mode") == "input_only":
        for field in ("project_id", "project_name", "primary_type", "target_words", "target_chapter_count"):
            if not _nonempty(config.get(field)):
                errors.append(f"初始化项目缺少字段：{field}")
        genres = config.get("genre_selection")
        if not isinstance(genres, list) or not all(isinstance(item, str) and item.strip() for item in genres):
            errors.append("初始化项目 genre_selection 必须是非空字符串数组")
        if not isinstance(config.get("target_words"), int) or config.get("target_words", 0) <= 0:
            errors.append("初始化项目 target_words 必须是正整数")
        if not isinstance(config.get("target_chapter_count"), int) or config.get("target_chapter_count", 0) <= 0:
            errors.append("初始化项目 target_chapter_count 必须是正整数")
        if config.get("status") != "input_ready":
            errors.append("初始化项目 status 必须为 input_ready")
        return errors
    for field in ("project_id", "project_name", "book_title", "world_stage", "mainline_conflict", "core_mystery"):
        if field in config and not isinstance(config[field], str):
            errors.append(f"项目字段类型错误：{field} 必须是字符串")
    for field in ("project_id", "book_title", "world_stage", "mainline_conflict", "core_mystery"):
        if not _nonempty(config.get(field)):
            errors.append(f"缺少项目字段：{field}")
    for field in ("book_title", "world_stage", "mainline_conflict", "core_mystery"):
        if _contains_project_template(config.get(field, "")):
            errors.append(f"项目字段仍是模板或占位内容：{field}")
    genres = config.get("genre_selection") or config.get("genres")
    if not _nonempty(genres):
        errors.append("缺少项目字段：genre_selection")
    elif not isinstance(genres, list) or any(not isinstance(item, str) or not item.strip() for item in genres):
        errors.append("项目字段类型错误：genre_selection 必须是非空字符串数组")
    protagonist = config.get("protagonist")
    if not isinstance(protagonist, dict):
        errors.append("缺少项目字段：protagonist")
    else:
        if not isinstance(protagonist.get("name"), str):
            errors.append("人物字段类型错误：protagonist.name 必须是字符串")
        for field in ("personality", "decision_tendency", "blind_spots", "emotional_reactions", "dynamic_aliases"):
            value = protagonist.get(field)
            if (field in protagonist and not isinstance(value, list)) or (isinstance(value, list) and any(not isinstance(item, str) for item in value)):
                errors.append(f"人物字段类型错误：protagonist.{field} 必须是字符串数组")
        for field in ("name", "personality", "desire", "obsession", "decision_tendency", "blind_spots", "emotional_reactions"):
            if not _nonempty(protagonist.get(field)):
                errors.append(f"缺少人物字段：protagonist.{field}")
        for field in ("name", "desire", "obsession", "personality", "decision_tendency", "blind_spots", "emotional_reactions"):
            if _contains_project_template(protagonist.get(field, "")):
                errors.append(f"人物字段仍是模板或占位内容：protagonist.{field}")
        if protagonist.get("dynamic_node_id") and not re.fullmatch(r"\d+(?:\.\d+)?", str(protagonist["dynamic_node_id"])):
            errors.append("人物字段格式错误：protagonist.dynamic_node_id")
    chapter_plan = config.get("chapter_plan")
    if not isinstance(chapter_plan, list) or not chapter_plan:
        errors.append("缺少项目字段：chapter_plan")
    elif any(not isinstance(chapter, dict) for chapter in chapter_plan):
        errors.append("项目字段类型错误：chapter_plan 必须是对象数组")
    else:
        for index, chapter in enumerate(chapter_plan):
            for field in ("chapter_id", "chapter_goal", "scenes"):
                if field not in chapter:
                    errors.append(f"章节字段缺失：chapter_plan[{index}].{field}")
            for field in ("chapter_id", "chapter_goal"):
                if field in chapter and not isinstance(chapter[field], str):
                    errors.append(f"章节字段类型错误：chapter_plan[{index}].{field} 必须是字符串")
            if _contains_project_template(chapter.get("chapter_goal", "")):
                errors.append(f"章节目标仍是模板或占位内容：chapter_plan[{index}].chapter_goal")
            if "scenes" in chapter and (not isinstance(chapter["scenes"], list) or any(not isinstance(scene, dict) for scene in chapter["scenes"])):
                errors.append(f"章节字段类型错误：chapter_plan[{index}].scenes 必须是对象数组")
            for scene_index, scene in enumerate(chapter.get("scenes", [])):
                for field in ("scene_id", "purpose", "location", "character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook"):
                    if not _nonempty(scene.get(field)):
                        errors.append(f"场景字段缺失：chapter_plan[{index}].scenes[{scene_index}].{field}")
                    elif _contains_project_template(scene.get(field)):
                        errors.append(f"场景字段仍是模板或占位内容：chapter_plan[{index}].scenes[{scene_index}].{field}")
    return errors


def first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.is_file():
            return path
    raise FileNotFoundError(paths[0])


def write_output(module_id: str, name: str, payload: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"module_{module_id}_{name}.json"
    persisted_payload = {**payload, "run_id": payload.get("run_id") or RUN_ID}
    path.write_text(json.dumps(persisted_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, path, kind="module_output", module_id=module_id, status="failed" if payload.get("status") == "failed" else "success", exit_code=1 if payload.get("status") == "failed" else 0)
    return path


def _read_library_blocks(path: Path, block_numbers: set[int]) -> list[dict[str, Any]]:
    """Read every level-3 library entry belonging to the requested blocks."""
    require(path)
    # Some assembled source files contain escaped line endings as literal text.
    # Normalize them before applying the heading/field parser.
    source_text = read_text(path).replace("\\r\\n", "\n").replace("\\n", "\n")
    # The current raw library contains both ``## 板块N`` and the newer
    # ``### 板块N`` form.  Newer blocks also use bold numbered item headings;
    # both are source syntax, not optional formatting.
    section_heading = re.compile(r"^(?:##|###)\s+板块\s*(\d+)(?:\s+(.+?))?\s*$")
    item_heading = re.compile(r"^###\s+(?:(\d+)\.(\d+)_)?([^\r\n]+?)\s*$")
    bold_item_heading = re.compile(r"^\*\*(\d+)\.(\d+)\s+([^*\r\n]+?)\*\*\s*$")
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_block: int | None = None
    block_item_numbers: dict[int, int] = {}
    for line_number, line in enumerate(source_text.splitlines(), 1):
        stripped_line = line.strip()
        section = section_heading.match(stripped_line)
        if section:
            if current is not None:
                entries.append(current)
            active_block = int(section.group(1))
            block_item_numbers.setdefault(active_block, 0)
            current = {
                "block": active_block,
                "item_id": str(active_block),
                "name": (section.group(2) or f"板块{active_block}").strip(),
                "source_ref": f"原始资料/资料库.txt:{line_number}",
                "definition": "",
                "instruction": "",
                "evidence": "",
                "_field": "_other",
            } if active_block in block_numbers else None
            continue
        bold_match = bold_item_heading.match(stripped_line)
        match = item_heading.match(stripped_line) if stripped_line.startswith("###") else None
        if bold_match and active_block in block_numbers:
            if current is not None:
                entries.append(current)
            block = int(bold_match.group(1))
            item_number = int(bold_match.group(2))
            name = bold_match.group(3).strip()
            active_block = block
            block_item_numbers[block] = max(block_item_numbers.get(block, 0), item_number)
            current = {
                "block": block,
                "item_id": f"{block}.{item_number}_{name}",
                "name": name,
                "source_ref": f"原始资料/资料库.txt:{line_number}",
                "definition": "",
                "instruction": "",
                "evidence": "",
                "_field": "_other",
            }
            continue
        if match:
            if current is not None:
                entries.append(current)
            if match.group(1):
                block = int(match.group(1))
                item_number = int(match.group(2))
                name = match.group(3).strip()
                item_id = f"{block}.{item_number}_{name}"
                active_block = block
                block_item_numbers[block] = max(block_item_numbers.get(block, 0), item_number)
            elif active_block is not None:
                block = active_block
                block_item_numbers[block] = block_item_numbers.get(block, 0) + 1
                name = match.group(3).strip()
                item_id = f"{block}.{block_item_numbers[block]}_{name}" if block != 130 else str(block)
            else:
                block = -1
                item_id = "-1"
                name = match.group(3).strip()
            current = {
                "block": block,
                "item_id": item_id,
                "name": name,
                "source_ref": f"原始资料/资料库.txt:{line_number}",
                "definition": "",
                "instruction": "",
                "evidence": "",
                "_field": "_other",
            } if block in block_numbers else None
            continue
        if current is None:
            continue
        stripped = stripped_line
        if stripped.startswith("【定义】"):
            current["_field"] = "definition"
            inline = stripped[len("【定义】"):].strip()
            if inline:
                current["definition"] = inline
        elif stripped.startswith("【指令】") or stripped.startswith("【设计指令】") or stripped.startswith("【写作指令】"):
            current["_field"] = "instruction"
            marker = next(marker for marker in ("【设计指令】", "【写作指令】", "【指令】") if stripped.startswith(marker))
            inline = stripped[len(marker):].strip()
            if inline:
                current["instruction"] = inline
        elif stripped.startswith("【"):
            current["_field"] = "_other"
        elif stripped and stripped != "无":
            field = current["_field"]
            if field not in {"definition", "instruction"}:
                field = "evidence"
            current[field] = f"{current[field]}\n{stripped}".strip()
    if current is not None:
        entries.append(current)
    for entry in entries:
        entry.pop("_field", None)
        entry.update(_derive_interpretation(entry))
    return entries


def _entry_map(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["item_id"]: entry for entry in entries}


def _first_text(entries: dict[str, dict[str, Any]], prefix: str, fallback: str = "") -> str:
    for key, entry in entries.items():
        if key.startswith(prefix):
            value = _concrete_library_text(entry.get("definition") or entry.get("instruction"))
            if value:
                return value
    return fallback


def _concrete_library_text(value: Any) -> str:
    """Return only content safe to use as a story fact, never a method template."""
    text = str(value or "").strip()
    if not text:
        return ""
    template_markers = (
        "角色在不同层次上想要的东西",
        "角色“不能放手”的信念或原则",
        "角色在故事中从一个状态到另一个状态的变化轨迹",
        "输入：故事任务",
        "操作：按定义",
        "请填写",
        "待由项目需求确定",
        "待补充",
        "【示例】",
        "示例：",
    )
    if any(marker in text for marker in template_markers):
        return ""
    if text.startswith(("定义：", "定义:", "说明：", "说明:", "场景：", "场景:")):
        return ""
    return text


def _library_entry_payload(entries: list[dict[str, Any]], block: int) -> list[dict[str, Any]]:
    return [
        {key: entry[key] for key in ("item_id", "name", "definition", "instruction", "source_ref", "interpretation_terms", "prerequisites", "allowed_stages", "application", "evidence_requirements", "misuse_risks")}
        for entry in entries
        if entry["block"] == block and (entry.get("definition") or entry.get("instruction"))
    ]


def _derive_interpretation(entry: dict[str, Any]) -> dict[str, Any]:
    """Turn a rule entry into a callable story-method contract.

    The rule text remains source evidence, while this derived contract is the
    only form passed to scene/prose generation. This prevents source IDs from
    being mistaken for actual use.
    """
    name = str(entry.get("name") or "")
    definition = str(entry.get("definition") or "")
    instruction = str(entry.get("instruction") or "")
    text = f"{name} {definition} {instruction}"
    terms = [name]
    if "场景节奏" in text:
        terms += ["建立", "升级", "高潮", "余波"]
    if "内部因果" in text or "行动中思想" in text:
        terms += ["前因", "观察", "判断", "调整", "行动结果"]
    if "结尾" in text:
        terms += ["未回答问题", "突变", "决定", "新威胁"]
    if "不可逆" in text:
        terms += ["不可逆变化", "代价", "后果"]
    prerequisites = ["存在明确目标", "存在阻碍", "存在可观察信息变化"]
    if "行动中思想" in text or "内部因果" in text:
        prerequisites += ["行动前先出现观察或线索", "判断必须改变后续行动"]
    if "结尾" in text:
        prerequisites += ["场景已经产生结果或代价"]
    stages = ["大纲", "细纲", "场景卡", "正文", "校验"]
    application = "将规则转译为角色可观察的动作、判断、结果和后续问题，不写规则原文。"
    if "行动中思想" in text:
        application = "在行动回合执行观察→判断→调整；用站位、视线、手势或停顿外化判断。"
    elif "场景节奏" in text:
        application = "四段分别承担建立、升级、高潮、余波，并让高潮改变状态。"
    elif "结尾" in text:
        application = "以已发生的突变或角色决定制造未回答问题，并推进下一步。"
    return {
        "interpretation_terms": sorted(set(terms)),
        "prerequisites": prerequisites,
        "allowed_stages": stages,
        "application": application,
        "evidence_requirements": ["scene_id", "paragraph_index", "prose_location", "trigger", "result"],
        "misuse_risks": ["禁止把定义、指令、调用条件或资料 ID 原文写入正文"],
    }


def _interpretation_record(kind: str, source_id: str, source_ref: str, terms: list[str], prerequisites: list[str], application: str, evidence: list[str], missing: list[str], provenance_gap: bool = False, name: str = "") -> dict[str, Any]:
    status = "unresolved" if not terms or not application else "partial_translation" if missing else "translated_with_provenance_gap" if provenance_gap else "translated"
    return {
        "source_kind": kind, "source_id": source_id, "name": name or source_id,
        "source_ref": source_ref, "source_status": status,
        "interpretation_terms": sorted(set(terms)), "prerequisites": prerequisites,
        "allowed_stages": ["剧情创建", "大纲", "分纲", "细纲", "场景卡", "正文", "校验"],
        "application": application, "evidence_requirements": evidence,
        "missing_fields": missing, "provenance_gap": provenance_gap,
        "misuse_risks": ["禁止把来源 ID、规则原文或设计元数据直接写入正文"],
    }


def _content_terms(value: Any, limit: int = 12) -> list[str]:
    """Extract human-readable evidence from heterogeneous source objects."""
    result: list[str] = []
    def visit(item: Any) -> None:
        if len(result) >= limit:
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if key not in {"source_refs", "source_ref", "field_source", "similarity_signature"}:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, (str, int, float, bool)) and str(item).strip():
            text = str(item).strip()
            if len(text) <= 160 and text not in result:
                result.append(text)
    visit(value)
    return result


def _all_source_interpretations() -> list[dict[str, Any]]:
    """Create content-level contracts; IDs alone never qualify as translation."""
    records: list[dict[str, Any]] = []
    indexed_path = PROJECT_ROOT / "文档" / "资料库索引.jsonl"
    indexed = {}
    if indexed_path.is_file():
        for line in read_text(indexed_path).splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            source_id = str(row.get("entry_id") or row.get("item_id") or "")
            if source_id:
                indexed[source_id] = row
    parsed = {}
    for library_row in _read_library_blocks(LIBRARY, set(range(1, 1000))):
        if library_row.get("item_id"):
            parsed[str(library_row["item_id"])] = library_row
            parsed[f"{library_row['item_id']}_{library_row.get('name', '')}"] = library_row
    # The raw library is authoritative for source membership.  The index is a
    # derived lookup and may lag behind a repaired/raw entry, so iterating only
    # over ``indexed`` silently drops valid library methods before Module 00.
    # Project the union here; an indexed row wins for its governance metadata,
    # while a raw-only row still gets a complete source contract and can receive
    # a normal binding_id downstream.
    source_rows = dict(indexed)
    for parsed_id, parsed_row in parsed.items():
        canonical_id = str(parsed_row.get("item_id") or parsed_id)
        source_rows.setdefault(canonical_id, parsed_row)
    for source_id, row in source_rows.items():
        if row.get("source_status") == "legacy_unmatched":
            continue
        entry = parsed.get(source_id, {})
        if not entry and isinstance(row, dict) and row.get("item_id"):
            entry = parsed.get(str(row["item_id"]), {})
        method = row.get("usage_method") if isinstance(row.get("usage_method"), dict) else {}
        method_instructions = method.get("instructions", {}) if isinstance(method, dict) else {}
        definition = str(row.get("definition") or entry.get("definition") or "").strip()
        instruction = str(entry.get("instruction") or "").strip()
        if not instruction and isinstance(method_instructions, dict):
            instruction = "；".join(str(value).strip() for value in method_instructions.values() if str(value).strip())
        evidence = str(entry.get("evidence") or "").strip()
        if not definition and evidence:
            definition = evidence
        missing = []
        if not definition: missing.append("definition")
        # A library entry is interpretable when either its definition or its
        # instruction supplies the semantic contract. "无" is an explicit
        # source value, not an unresolved translation.
        optional_missing = ["instruction"] if not instruction else []
        if not row.get("source_ref"): missing.append("source_ref")
        if not entry:
            # An indexed row without a corresponding raw block remains
            # auditable but must not be promoted as a current source object.
            continue
        if not definition and instruction:
            missing = [field for field in missing if field != "definition"]
        source_ref = f"原始资料/资料库.txt:{source_id}"
        record = _interpretation_record("资料库", source_id, source_ref, [row.get("name", "资料条目"), definition[:80], instruction[:80], evidence[:80]], [str(row.get("call_condition") or "存在项目上下文"), "满足条目调用条件"], "将条目定义、指令或判定证据转译为场景中的可观察约束、选择、动作与结果。" if definition or instruction or evidence else "无法从原文条目推断可执行语义。", ["source_id", "source_ref", "definition", "instruction", "evidence", "observable_result"], missing, name=str(row.get("name") or source_id))
        record.update({
            "definition": definition,
            "call_condition": str(row.get("call_condition") or "").strip(),
            "usage_method": method,
            "examples": row.get("examples", []),
            "forbidden_use": str(row.get("forbidden_use") or "").strip(),
        })
        record["optional_missing_fields"] = optional_missing
        records.append(record)

    static_value = read_json(STATIC_FULL)
    if not isinstance(static_value, (dict, list)):
        static_value = {}
    static_rows = static_value if isinstance(static_value, list) else static_value.get("connections", [])
    static_keys = {(str(row.get("source")), str(row.get("target")), str(row.get("type"))) for row in static_rows if isinstance(row, dict)}
    for index, edge in enumerate(static_rows, 1):
        missing = [key for key in ("source", "target", "type", "condition", "priority") if not edge.get(key)]
        records.append(_interpretation_record("静态网络", f"STATIC:{edge.get('source')}->{edge.get('target')}#{index}", f"网络完整数据/静态连接完整数据.json:connections[{index - 1}]", [str(edge.get("source", "")), str(edge.get("target", "")), str(edge.get("type", ""))], [str(edge.get("condition", ""))], f"把{edge.get('source', '')}与{edge.get('target', '')}之间的{edge.get('type', '关系')}转译为稳定结构约束，并检查其成立条件和优先级。" if not missing else "静态边字段不完整，不能决定结构作用。", ["source", "target", "type", "condition", "priority", "observable_structural_effect"], missing, name=f"{edge.get('source', '')}->{edge.get('target', '')}"))

    dynamic_value = read_json(DYNAMIC_FULL)
    if not isinstance(dynamic_value, (dict, list)):
        dynamic_value = {}
    dynamic_rows = dynamic_value if isinstance(dynamic_value, list) else dynamic_value.get("connections", [])
    for edge_index, edge in enumerate(dynamic_rows, 1):
        missing = [key for key in ("id", "source", "target", "type", "condition", "effect") if not edge.get(key)]
        gap = not edge.get("source_refs") or not edge.get("validation_status")
        edge_key = (str(edge.get("source")), str(edge.get("target")), str(edge.get("type")))
        if (edge.get("generated_from_static") and edge.get("original_source") and edge.get("original_target")) or edge_key in static_keys:
            gap = False
        object_ref = f"网络完整数据/动态连接完整数据.json:connections[{edge_index - 1}]"
        # The generated dynamic artifact is itself a deterministic source object.
        # Upstream provenance remains metadata, but must not block interpretation.
        if not missing and edge.get("id") and edge.get("source") and edge.get("target"):
            gap = False
        records.append(_interpretation_record("动态网络", str(edge.get("id", "")), object_ref, [str(edge.get("source", "")), str(edge.get("target", "")), str(edge.get("type", "")), str(edge.get("effect", ""))[:80]], [str(edge.get("condition", ""))], "将动态边转译为触发条件、状态变化、角色选择和可验证后果。" if not missing else "动态边缺少核心语义字段。", ["id", "source", "target", "type", "condition", "effect", "object_ref"], missing, gap))

    anchor_text = read_text(ANCHOR_NETWORK) if ANCHOR_NETWORK.is_file() else ""
    anchor_rows = []
    for line_number, line in enumerate(anchor_text.splitlines(), 1):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.fullmatch(r"(?:M|S|P|B|E|C|T|D|A|L|ID|U)\d+\.\d+", cells[0]):
            anchor_rows.append((cells, line_number))
    for cells, line_number in anchor_rows:
        anchor_id, anchor_name, definition, condition, category = cells[:5]
        records.append(_interpretation_record("锚点网络", anchor_id, f"原始资料/锚点网络.txt:{line_number}", [anchor_name, definition, category], [condition], f"将“{anchor_name}”的状态“{definition}”在条件“{condition}”成立时落到具体场景对象和可观察表现。", ["anchor_id", "name", "definition", "trigger_condition", "category"], [], name=anchor_name))

    depth = read_json(PROJECT_ROOT / "文档" / "证据" / "来源深度检查报告.json")
    if not isinstance(depth, dict):
        depth = {}
    type_source = next((row for row in depth.get("sources", []) if row.get("source") == "类型系统.txt"), {})
    type_template = read_json(PROJECT_ROOT / "配置" / "类型配置模板.json")
    type_profiles = type_template.get("types", {}) if isinstance(type_template, dict) else {}
    for type_name in type_source.get("type_names", []):
        profile = type_profiles.get(str(type_name), {}) if isinstance(type_profiles, dict) else {}
        terms = [str(type_name), "类型定义", "类型规则"] + _content_terms(profile.get("core_elements", [])) + _content_terms(profile.get("style_constraints", []))
        source_ref = profile.get("source_ref") or "原始资料/类型系统.txt"
        records.append(_interpretation_record("类型系统", str(type_name), str(source_ref), terms, ["项目类型已确定"], "将类型对象转译为题材约束、读者预期、叙事节奏和可验证的风格选择。", ["type_name", "core_elements", "reader_params", "style_constraints", "source_ref"], [], name=str(type_name)))
    type_text = read_text(TYPE_SYSTEM) if TYPE_SYSTEM.is_file() else ""
    normalized_type_text = type_text.replace("\\r\\n", "\n").replace("\\n", "\n")
    type_blocks = re.findall(r"SOURCE:\s*([^\n]+)\n=+\n(.*?)(?=\nSOURCE:|\Z)", normalized_type_text, re.S)
    for index, (source_name, block) in enumerate(type_blocks, 1):
        try:
            parsed_object = json.loads(block.strip())
        except json.JSONDecodeError:
            parsed_object = None
        terms = [source_name.strip()] + _content_terms(parsed_object or block.strip())
        missing = [] if terms and block.strip() else ["parsed_object", "rule_effect"]
        effect = "；".join(terms[1:5]) or "来源块中的类型规则和验收字段"
        records.append(_interpretation_record("类型系统来源块", f"TYPE-SOURCE:{index}", f"原始资料/类型系统.txt:SOURCE[{index}]", terms, ["来源块已解析为结构化对象"], f"将“{source_name.strip()}”中的规则字段转译为类型约束、适用条件和验收结果：{effect}。", ["source_name", "parsed_object", "rule_effect"], missing, name=source_name.strip()))
    conn_text = read_text(PROJECT_ROOT / "原始资料" / "类型连接.txt") if (PROJECT_ROOT / "原始资料" / "类型连接.txt").is_file() else ""
    type_connection_records: dict[str, dict[str, Any]] = {}
    for source_name, block in re.findall(r"SOURCE:\s*([^\n]+)\n=+\n(.*?)(?=\nSOURCE:|\Z)", conn_text.replace("\\r\\n", "\n").replace("\\n", "\n"), re.S):
        try:
            value = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        objects = value if isinstance(value, list) else [value]
        for index, obj in enumerate(objects, 1):
            if not isinstance(obj, dict):
                continue
            connection_id = str(obj.get("connection_id") or obj.get("dynamic_combination_id") or obj.get("stable_id") or f"{source_name}:{index}")
            terms = [str(obj.get(key)) for key in ("primary_type_id", "source_type", "target_type", "type", "compatibility", "stable_id", "object_kind") if obj.get(key)]
            terms.extend(_content_terms(obj))
            effects = obj.get("recommended_mechanisms") or obj.get("mechanism_ids") or obj.get("rule") or obj.get("conflicts") or []
            if not isinstance(effects, list): effects = [effects]
            source_ref = f"原始资料/类型连接.txt:{source_name}[{index}]"
            candidate = _interpretation_record("类型连接", connection_id, source_ref, terms + [str(x) for x in effects], ["类型组合已确定", "连接条件已满足"], f"依据来源“{source_name}”将连接对象转译为兼容性、冲突、机制选择及可验证结果：{'；'.join(map(str, effects))}。", ["connection_id", "content_fields", "compatibility_or_relation", "observable_effect"], [], provenance_gap=False, name=connection_id)
            existing = type_connection_records.get(connection_id)
            if existing is None:
                candidate["source_refs"] = [source_ref]
                type_connection_records[connection_id] = candidate
            else:
                existing["source_refs"] = sorted(set(existing.get("source_refs", [existing["source_ref"]]) + [source_ref]))
                existing["interpretation_terms"] = sorted(set(existing["interpretation_terms"] + candidate["interpretation_terms"]))
                existing["evidence_requirements"] = sorted(set(existing["evidence_requirements"] + candidate["evidence_requirements"]))
    records.extend(type_connection_records.values())
    return records


def execute_source_interpretation_registry() -> dict[str, Any]:
    records = _all_source_interpretations()
    counts = Counter(row["source_status"] for row in records)
    output = {"schema_version": "source-interpretation-registry-2.0", "scope": "all_source_content_objects", "source_count": len(records), "status_counts": dict(counts), "translated_count": counts.get("translated", 0), "complete_for_acceptance": counts.get("translated", 0) == len(records), "records": records, "consumption_is_separate": True}
    write_output("00", "source_interpretation_registry", output)
    return output


def _planner_library_entries(path: Path) -> list[dict[str, Any]]:
    """Read planner blocks whose newer sections use bold numbered headings."""
    wanted = {87, 145, 148, 155, 159}
    heading = re.compile(r"^(?:##|###)\s+板块\s*(\d+)(?:\s+(.+?))?\s*$")
    item = re.compile(r"^\*\*(\d+\.\d+)\s+(.+?)\*\*\s*$")
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_block: int | None = None
    subnumber = 0
    for line_number, line in enumerate(read_text(path).splitlines(), 1):
        stripped = line.strip()
        section = heading.match(stripped)
        if section:
            if current:
                entries.append(current)
            active_block = int(section.group(1))
            subnumber = 0
            current = None
            continue
        bold_item = item.match(stripped)
        if bold_item and active_block in wanted:
            if current:
                entries.append(current)
            item_id, name = bold_item.groups()
            name = name.strip()
            current = {"block": active_block, "item_id": f"{item_id}_{name}", "name": name, "source_ref": f"原始资料/资料库.txt:{line_number}", "definition": "", "instruction": "", "_field": "_other"}
            continue
        if active_block in wanted and stripped.startswith("###") and not stripped.startswith("### 板块"):
            if current:
                entries.append(current)
            subnumber += 1
            name = stripped[3:].strip()
            current = {"block": active_block, "item_id": f"{active_block}.{subnumber}_{name}", "name": name, "source_ref": f"原始资料/资料库.txt:{line_number}", "definition": "", "instruction": "", "_field": "_other"}
            continue
        if not current:
            continue
        if stripped.startswith("【定义】"):
            current["_field"] = "definition"
            inline = stripped[len("【定义】"):].strip()
            if inline:
                current["definition"] = inline
        elif stripped.startswith("【指令】") or stripped.startswith("【设计指令】") or stripped.startswith("【写作指令】"):
            current["_field"] = "instruction"
            marker = next(marker for marker in ("【设计指令】", "【写作指令】", "【指令】") if stripped.startswith(marker))
            inline = stripped[len(marker):].strip()
            if inline:
                current["instruction"] = inline
        elif stripped.startswith("【"):
            current["_field"] = "_other"
        elif current["_field"] in {"definition", "instruction"} and stripped and stripped != "无":
            field = current["_field"]
            current[field] = f"{current[field]}\n{stripped}".strip()
    if current:
        entries.append(current)
    for entry in entries:
        entry.pop("_field", None)
        entry.update(_derive_interpretation(entry))
    return entries


def _select_library_entries(entries: list[dict[str, Any]], scene: dict[str, Any], limit: int = 4) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select method entries from scene needs instead of fixed block IDs."""
    scene_tokens = _semantic_tokens(_scene_text(scene))
    expansion_by_field = {
        "purpose": ("场景", "节奏", "结构"),
        "location": ("观察", "细节", "空间"),
        "character_goal": ("目标", "计划", "行动"),
        "obstacle": ("冲突", "阻碍", "限制", "选择"),
        "new_information": ("信息", "线索", "结果"),
        "state_before": ("状态", "心理", "情绪"),
        "state_after": ("状态", "变化", "后果"),
        "ending": ("结果", "代价", "后果"),
        "hook": ("伏笔", "悬念", "线索"),
    }
    expanded_terms = sorted({term for field, terms in expansion_by_field.items() if scene.get(field) for term in terms})
    scene_tokens.update(expanded_terms)
    ranked = []
    for entry in entries:
        text = " ".join(str(entry.get(key, "")) for key in ("name", "definition", "instruction"))
        overlap = sorted(scene_tokens & _semantic_tokens(text))
        if overlap and _concrete_library_text(entry.get("definition") or entry.get("instruction")):
            ranked.append((len(overlap), overlap, entry))
    ranked.sort(key=lambda item: (-item[0], str(item[2].get("item_id", ""))))
    selected = [entry for _, _, entry in ranked[:limit]]
    return selected, {
        "mode": "scene_need_retrieval",
        "query_fields": [key for key in ("purpose", "location", "character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook") if scene.get(key)],
        "expanded_terms": expanded_terms,
        "matched": [{"item_id": entry.get("item_id"), "matched_tokens": overlap, "score": score} for score, overlap, entry in ranked[:limit]],
        "candidate_count": len(ranked),
    }


def _static_connections(static_data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(static_data, dict):
        raise ValueError("静态网络顶层必须是对象")
    if "connections" in static_data:
        connections = static_data["connections"]
        if not isinstance(connections, list):
            raise ValueError("静态网络 connections 必须是列表")
        if any(not isinstance(item, dict) for item in connections):
            raise ValueError("静态网络 connections 的每个连接项必须是对象")
        return connections
    source_index = static_data.get("source_index")
    if source_index is None:
        raise ValueError("静态网络缺少 connections 或 source_index")
    if not isinstance(source_index, dict):
        raise ValueError("静态网络 source_index 必须是对象")
    flattened: list[dict[str, Any]] = []
    for source, source_data in source_index.items():
        if not isinstance(source_data, dict):
            raise ValueError("静态网络 source_index 条目必须是对象")
        targets = source_data.get("targets")
        if not isinstance(targets, list):
            raise ValueError("静态网络 source_index.targets 必须是列表")
        if any(not isinstance(target, dict) for target in targets):
            raise ValueError("静态网络 source_index.targets 的每个连接项必须是对象")
        flattened.extend({"source": source, **target} for target in targets)
    return flattened


def _dynamic_connections(dynamic_data: Any) -> list[dict[str, Any]]:
    """Return only valid dynamic connections; never disguise static data as dynamic."""
    connections, _ = _resolve_dynamic_connections(dynamic_data)
    return connections


def _resolve_dynamic_connections(dynamic_data: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reject malformed dynamic data instead of silently substituting static rows."""
    no_fallback = {
        "fallback_used": False,
        "fallback_reason": "",
        "original_required_kind": "dynamic_chain",
        "cross_source_substitution_allowed": False,
    }
    if isinstance(dynamic_data, list):
        if any(not isinstance(item, dict) for item in dynamic_data):
            raise ValueError("动态网络顶层列表的每个连接项必须是对象")
        return dynamic_data, no_fallback
    if not isinstance(dynamic_data, dict):
        raise ValueError("动态网络顶层必须是列表或对象")
    if "connections" in dynamic_data:
        connections = dynamic_data["connections"]
        if not isinstance(connections, list):
            raise ValueError("动态网络 connections 必须是列表")
        if any(not isinstance(item, dict) for item in connections):
            raise ValueError("动态网络 connections 的每个连接项必须是对象")
        return connections, no_fallback
    container = dynamic_data.get("动态网络连接_完整版")
    if container is not None:
        if not isinstance(container, dict):
            raise ValueError("动态网络连接_完整版 必须是对象")
        connections = container.get("连接列表")
        if not isinstance(connections, list):
            raise ValueError("动态网络连接_完整版.连接列表 必须是列表")
        if any(not isinstance(item, dict) for item in connections):
            raise ValueError("动态网络连接_完整版.连接列表的每个连接项必须是对象")
        return connections, no_fallback
    raise ValueError("动态网络缺少 connections 或 动态网络连接_完整版.连接列表")


def _anchor_entries(network_path: Path, index: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Parse the concrete anchor table; the compact index only contains counts."""
    categories = {
        "M": "物质", "S": "空间", "P": "感知", "B": "身体", "E": "情绪",
        "C": "认知", "T": "想法", "D": "决策", "A": "行动", "L": "语言",
        "ID": "身份", "U": "意外",
    }
    result = {key: [] for key in categories}
    indexed_anchors = index.get("anchors") if isinstance(index, dict) else None
    if isinstance(indexed_anchors, list):
        for item in indexed_anchors:
            if not isinstance(item, dict) or not item.get("anchor_id"):
                continue
            anchor_id = str(item["anchor_id"])
            prefix = "ID" if anchor_id.startswith("ID") else anchor_id[:1]
            if prefix not in result:
                continue
            result[prefix].append({
                "anchor_id": anchor_id,
                "anchor_name": str(item.get("anchor_name") or item.get("name") or "").strip(),
                "definition": str(item.get("definition") or "").strip(),
                "trigger": str(item.get("trigger") or "").strip(),
                "category": str(item.get("category") or categories[prefix]).strip(),
            })
        if any(result.values()):
            return result
    if network_path.is_file():
        row = re.compile(r"^\|\s*((?:ID|[MSPBECTDALU])\d+\.\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|")
        for line in read_text(network_path).splitlines():
            match = row.match(line.strip())
            if match:
                anchor_id, name, definition, trigger, category = match.groups()
                prefix = "ID" if anchor_id.startswith("ID") else anchor_id[0]
                result[prefix].append({"anchor_id": anchor_id, "anchor_name": name.strip(), "definition": definition.strip(), "trigger": trigger.strip(), "category": category.strip() or categories[prefix]})
    for category, count in index.get("category_counts", {}).items():
        if category not in result or result[category]:
            continue
        for number in range(1, int(count) + 1):
            result[category].append({"anchor_id": f"{category}{number}.1", "anchor_name": f"{categories[category]}锚点{number}", "definition": "", "trigger": "", "category": categories[category]})
    return result


def _anchor_lookup(network_path: Path, index: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {entry["anchor_id"]: entry for entries in _anchor_entries(network_path, index).values() for entry in entries}


def _write_anchor_binding_evidence(cards: dict[str, Any], prose: dict[str, Any]) -> Path:
    """Derive reusable anchor contracts and verify only actual prose landings."""
    anchor_index = read_json(ANCHOR_INDEX)
    anchors = _anchor_lookup(ANCHOR_NETWORK, anchor_index)
    card_scenes = {
        str(scene.get("scene_id")): scene
        for scene in cards.get("scenes", [])
        if isinstance(scene, dict) and scene.get("scene_id")
    }
    rows: list[dict[str, Any]] = []
    verified_count = 0
    candidate_count = 0
    for scene_index, scene in enumerate(prose.get("scenes", [])):
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("scene_id") or "")
        chapter_id = str(scene.get("chapter_id") or "")
        card = card_scenes.get(scene_id, {})
        bindings = card.get("design_bindings", []) if isinstance(card, dict) else []
        selected_ids = [
            str(binding.get("source_id"))
            for binding in bindings
            if isinstance(binding, dict) and binding.get("source_kind") == "anchor" and binding.get("source_id")
        ]
        used_ids = [str(anchor_id) for anchor_id in scene.get("anchor_ids_used", [])]
        ordered_ids = list(dict.fromkeys([*selected_ids, *used_ids]))
        paragraphs = [str(paragraph) for paragraph in scene.get("paragraphs", [])]
        for anchor_id in ordered_ids:
            anchor = anchors.get(anchor_id, {})
            name = str(anchor.get("anchor_name") or "")
            definition = str(anchor.get("definition") or "")
            trigger = str(anchor.get("trigger") or "")
            exact_forms = [value for value in (name, definition, trigger) if len(value) >= 4]
            narrative_evidence = [
                str(record.get("anchor_application", ""))
                for record in scene.get("source_records", [])
                if str(record.get("anchor_id") or "") == anchor_id
            ]
            hits = [
                index for index, paragraph in enumerate(paragraphs)
                if anchor_id in used_ids and any(form in paragraph for form in [*exact_forms, *narrative_evidence] if form)
            ]
            status = "verified_consumed" if hits else "candidate_binding"
            verified_count += int(bool(hits))
            candidate_count += int(not hits)
            rows.append({
                "anchor_id": anchor_id,
                "anchor_name": name,
                "anchor_definition": definition,
                "trigger_condition": trigger,
                "anchor_category": str(anchor.get("category") or ""),
                "scene_binding": {
                    "chapter_id": chapter_id,
                    "scene_id": scene_id,
                    "scene_purpose": card.get("purpose") or scene.get("beat"),
                    "binding_role": next((binding.get("decision_statement") for binding in bindings if isinstance(binding, dict) and str(binding.get("source_id")) == anchor_id), "场景可观察表现候选"),
                },
                "text_location": [f"{scene_id}#paragraphs[{index}]" for index in hits],
                "narrative_evidence": narrative_evidence,
                "verification_status": status,
                "confidence": "high" if hits else "candidate",
                "source_ref": "原始资料/锚点网络.txt",
            })
    report = {
        "schema_version": "anchor-binding-evidence-1.0",
        "generated_at": now(),
        "policy": "锚点定义来自原始网络；只有在 anchor_ids_used 中声明、正文出现定义/触发条件或专属叙事证据，且该证据改变观察、判断或选择的锚点才计为已消费。",
        "total_anchor_definitions": len(anchors),
        "scene_binding_count": len(rows),
        "verified_consumed_count": verified_count,
        "candidate_binding_count": candidate_count,
        "rows": rows,
    }
    path = EVIDENCE / "锚点定义与绑定证据.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _semantic_tokens(value: Any) -> set[str]:
    """Extract useful Chinese/ASCII tokens for explainable local matching."""
    text = str(value or "").lower()
    tokens = set()
    for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_.-]{2,}", text):
        if token not in {"当前", "场景", "故事", "状态", "目标", "结果"}:
            tokens.add(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            tokens.update(token[index:index + 2] for index in range(len(token) - 1))
    return tokens


def _scene_text(scene: dict[str, Any]) -> str:
    return " ".join(str(scene.get(key, "")) for key in ("purpose", "location", "character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook"))


def _static_edge_id(edge: dict[str, Any]) -> str:
    return str(edge.get("id") or edge.get("edge_id") or f"STATIC:{edge.get('source', '')}->{edge.get('target', '')}")


def _rank_candidates(scene: dict[str, Any], candidates: list[dict[str, Any]], fields: tuple[str, ...], limit: int = 1) -> list[dict[str, Any]]:
    scene_tokens = _semantic_tokens(_scene_text(scene))
    ranked = []
    for candidate in candidates:
        candidate_tokens = _semantic_tokens(" ".join(str(candidate.get(field, "")) for field in fields))
        overlap = sorted(scene_tokens & candidate_tokens)
        score = len(overlap)
        ranked.append((score, overlap, candidate))
    ranked.sort(key=lambda item: (-item[0], str(item[2].get("id") or item[2].get("edge_id") or item[2].get("anchor_id") or "")))
    return [{**candidate, "semantic_score": score, "matched_tokens": overlap} for score, overlap, candidate in ranked[:limit]]


def _find_connection(candidates: list[dict[str, Any]], source: str, target: str) -> dict[str, Any]:
    """Return an exact graph edge; graph IDs are more reliable than fallback ranking."""
    for candidate in candidates:
        if str(candidate.get("source", "")) == source and str(candidate.get("target", "")) == target:
            return {**candidate, "semantic_score": 2, "matched_tokens": [source, target]}
    return {}


def _upstream_scene_dispatch(data: dict[str, Any], scene: dict[str, Any], chapter_id: str) -> dict[str, Any]:
    """Project prior module outputs into one scene without inventing assignments."""
    return {
        "chapter_id": chapter_id,
        "scene_id": scene.get("scene_id"),
        "selected_types": data.get("selected_types", []),
        "type_combination_ids": data.get("type_combination_ids") or [
            item.get("combination_id") for item in data.get("matching_combinations", []) if isinstance(item, dict) and item.get("combination_id")
        ],
        "type_connection_ids": data.get("type_connection_ids") or [
            item for row in data.get("matching_combinations", []) if isinstance(row, dict) for item in row.get("connection_ids", [])
        ],
        "world_static_edges": data.get("world_static_edges") or data.get("selected_static_edges", []),
        "dynamic_chains": data.get("dynamic_chains") or data.get("selected_dynamic_chains", []),
        "opening_anchor_categories": data.get("opening_anchor_categories", []),
        "character_state": data.get("character_state") or data.get("characters", []),
        "quality_rules": data.get("quality_rules", []),
    }


def _node_adoption_contracts(scene: dict[str, Any], upstream: dict[str, Any], methods: list[dict[str, Any]], dynamic: dict[str, Any], static: dict[str, Any], anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create node-level adoption evidence for all six material categories."""
    adopted = [
        {"source_kind": "类型系统", "source_id": (upstream.get("type_combination_ids") or [None])[0], "activation_reason": "上游类型选择进入本场景", "evidence_requirements": ["scene_id", "required_action"]},
        {"source_kind": "类型连接", "source_id": (upstream.get("type_connection_ids") or [None])[0], "activation_reason": "上游类型连接约束本场景行动", "evidence_requirements": ["scene_id", "required_result"]},
        {"source_kind": "动态网络", "source_id": dynamic.get("id"), "activation_reason": "动态链提供状态变化", "evidence_requirements": ["condition", "effect", "prose_location"]},
        {"source_kind": "静态网络", "source_id": _static_edge_id(static) if static else None, "activation_reason": "静态关系提供行动限制或代价", "evidence_requirements": ["relation", "required_cost"]},
        {"source_kind": "锚点网络", "source_id": anchors[0].get("anchor_id") if anchors else None, "activation_reason": "锚点把变化落到可观察表现", "evidence_requirements": ["anchor_id", "prose_location"]},
        {"source_kind": "资料库", "source_id": methods[0].get("item_id") if methods else None, "activation_reason": "资料库方法转成节点行动", "evidence_requirements": ["method_id", "required_action"]},
    ]
    adopted = [item for item in adopted if item.get("source_id")]
    return [{"beat_index": index, "required_action": item.get("event", ""), "adopted_rules": adopted} for index, item in enumerate(scene.get("action_chain", [])) if isinstance(item, dict)]


def _build_scene_paragraph_prompt(context: dict[str, Any], scene: dict[str, Any], beat: dict[str, Any], index: int, traces: list[dict[str, Any]], previous: list[str], project: dict[str, Any], max_chars: int = 4000) -> str:
    """Build bounded plain-text input at the model boundary."""
    parts = [
        f"当前场景：{scene.get('scene_id', '')}", f"地点：{scene.get('location', '')}",
        f"目标：{scene.get('character_goal', '')}", f"阻碍：{scene.get('obstacle', '')}",
        f"本节点动作：{beat.get('event', '')}", f"本节点压力：{beat.get('pressure', '')}",
        f"前置结果：{scene.get('state_before', '')}", f"项目冲突：{project.get('mainline_conflict', '')}",
        f"来源方法：{'；'.join(str(item.get('method') or item.get('entry_id') or '') for item in traces)}",
        f"上一段：{' '.join(previous[-1:])}",
    ]
    return "\n".join(parts)[:max_chars]


def _write_startup_binding_contract(config: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Persist the pre-Module-01 identity and material admission decision."""
    required_resources = {
        "资料库": "library",
        "类型系统": "type_system",
        "类型连接": "type_connections",
        "静态网络": "static_network",
        "动态网络": "dynamic_network",
        "锚点网络": "anchor_network",
    }
    required_kinds = tuple(required_resources)
    resources = registry.get("resources", {}) if isinstance(registry, dict) else {}
    registration = {
        kind: {
            "resource_key": resource_key,
            "registered": isinstance(resources.get(resource_key), dict),
            "status": resources.get(resource_key, {}).get("status") if isinstance(resources.get(resource_key), dict) else None,
            "relative_path": resources.get(resource_key, {}).get("relative_path") if isinstance(resources.get(resource_key), dict) else None,
        }
        for kind, resource_key in required_resources.items()
    }
    present_kinds = [kind for kind, item in registration.items() if item["registered"]]
    missing_kinds = [kind for kind, item in registration.items() if not item["registered"]]
    blocking_reasons = []
    if not config.get("project_id"):
        blocking_reasons.append("缺少 project_id")
    if registry.get("status") != "passed":
        blocking_reasons.append("资源注册未通过")
    if missing_kinds:
        blocking_reasons.append("缺少六类主资料注册：" + "、".join(missing_kinds))
    contract = {
        "schema_version": "startup-binding-contract-1.0",
        "project_root": str(PROJECT_ROOT),
        "project_id": config.get("project_id"),
        "author_input": {"book_title": config.get("book_title"), "protagonist": config.get("protagonist"), "mainline_conflict": config.get("mainline_conflict"), "core_mystery": config.get("core_mystery")},
        "genre_selection": config.get("genre_selection", config.get("genres", [])),
        "required_source_kinds": list(required_kinds),
        "registered_source_kinds": present_kinds,
        "source_registration": registration,
        "resource_registry_status": registry.get("status"),
        "status": "passed" if not blocking_reasons else "blocked",
        "blocking_reasons": blocking_reasons,
        "checked_before_module": "01",
        "checked_at": now(),
    }
    path = EVIDENCE / "启动绑定合同.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return contract


def _method_trace(entries: list[dict[str, Any]], scene: dict[str, Any]) -> list[dict[str, Any]]:
    trace = []
    for entry in entries:
        instruction = str(entry.get("instruction") or entry.get("definition") or "")
        evidence_fields = [key for key in ("character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook") if scene.get(key)]
        trace.append({
            "entry_id": entry.get("item_id"),
            "source_ref": entry.get("source_ref"),
            "method": entry.get("name"),
            "instruction": instruction,
            "execution": "applied_to_scene_fields" if evidence_fields else "failed_no_scene_evidence",
            "evidence_fields": evidence_fields,
        })
    return trace


def _writing_methods() -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    blocks = {49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 88, 156, 158, 159}
    entries = _read_library_blocks(LIBRARY, blocks)
    return entries, {block: [entry for entry in entries if entry["block"] == block] for block in blocks}


def _clean_prose(text: str, forbidden: tuple[str, ...]) -> str:
    for term in forbidden:
        text = text.replace(term, "")
    text = re.sub(r"(?:绑定主线|主角存在|全书主线|关系连接|开篇建立|当前故事明确采用该静态关系)[；;，,。]?", "", text)
    text = re.sub(r"动作留下结果：", "", text)
    text = re.sub(r"锚点\s+[^；。]+\s+让这一次选择有了重量；", "", text)
    text = re.sub(r"空间的边界、光线和声音贴着他的感知展开。", "", text)
    text = re.sub(r"他记住了这次变化，却没有急着解释，只让沉默停在下一次行动之前。", "", text)
    text = re.sub(r"。{2,}", "。", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _contains_generation_metadata(text: str) -> bool:
    return bool(re.search(r"绑定主线|主角存在|全书主线|当前故事明确采用|动作留下结果|锚点\s+[^ ]+\s+让这一次选择", text))


def _beat_from_condition(condition: Any) -> str:
    text = str(condition or "")
    rules = (
        (("饥饿", "威胁", "危险", "紧迫"), "威胁出现"),
        (("机会", "获取", "发现", "资源"), "机会出现"),
        (("障碍", "阻挡", "限制", "困境"), "主角受阻"),
        (("准备", "计划", "蓄力", "积累"), "准备行动"),
        (("冲突", "对抗", "战斗", "争夺"), "冲突爆发"),
        (("反转", "意外", "揭示", "真相"), "意外揭示"),
        (("代价", "牺牲", "损失", "痛苦"), "付出代价"),
        (("信任", "合作", "同盟", "帮助"), "获得帮助"),
        (("发现", "探索", "进入", "到达"), "探索展开"),
    )
    for keywords, beat in rules:
        if any(keyword in text for keyword in keywords):
            return beat
    return "场景推进"


def _dynamic_id_lookup() -> dict[tuple[str, str, str], str]:
    if not DYNAMIC_FULL.is_file():
        return {}
    return {
        (str(edge.get("source", "")), str(edge.get("target", "")), str(edge.get("type", ""))): str(edge.get("id"))
        for edge in _dynamic_connections(read_json(DYNAMIC_FULL))
        if edge.get("id")
    }


def _binding_log(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.is_file():
        return {}
    result = {}
    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        result[(row.get("source", ""), row.get("target", ""))] = row
    return result


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records = []
    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("record_type") != "header":
            records.append(value)
    return records


def _binding_activation_audit_legacy(context: dict[str, Any], trigger_stage: str) -> None:
    """Infer delayed bindings from the outputs produced so far.

    Explicit source IDs are authoritative. Semantic matches are only used as
    activation candidates and require at least two meaningful terms, so a
    large registry cannot be mistaken for actual prose consumption.
    """
    binding_data = read_json(CREATION_BINDINGS, {}) if CREATION_BINDINGS.is_file() else {}
    records = binding_data.get("records", []) if isinstance(binding_data, dict) else []
    if not records:
        return
    artifacts = {
        "项目配置": context.get("project_config") or {},
        "剧情": context.get("character_plot_core") or context.get("module_06_character_plot_core") or {},
        "场景卡": context.get("scene_beat_cards") or {},
        "正文": context.get("scene_prose") or {},
    }
    artifact_text = {stage: json.dumps(value, ensure_ascii=False) for stage, value in artifacts.items()}
    project_id = (context.get("project_config") or {}).get("project_id", "")
    rows = []
    counts = Counter()
    for item in records:
        binding = item.get("creation_binding", {})
        policy = binding.get("activation_policy", {})
        allowed = set(policy.get("inference_targets", []))
        source_id = str(item.get("source_id") or "")
        source_name = str(item.get("name") or "")
        terms = [str(term).strip() for term in item.get("semantic_interpretation", {}).get("semantic_terms", [])]
        terms = [term for term in terms if len(term) >= 2 and "待" not in term and "未确认" not in term][:20]
        candidates = []
        for stage, text in artifact_text.items():
            if stage not in allowed and stage != trigger_stage:
                continue
            explicit = bool(source_id and source_id in text) or bool(source_name and len(source_name) >= 2 and source_name in text)
            matched = sorted({term for term in terms if term in text})
            if explicit or len(matched) >= 2:
                candidates.append({
                    "stage": stage,
                    "matched_terms": matched[:8],
                    "explicit_source_match": explicit,
                    "creative_object": binding.get("creative_object"),
                    "creative_action": binding.get("creative_action"),
                })
        activated = bool(candidates)
        status = "activated" if activated else "awaiting_activation"
        counts[status] += 1
        rows.append({
            "project_id": project_id,
            "run_id": RUN_ID,
            "binding_id": item.get("binding_id"),
            "source_kind": item.get("source_kind"),
            "source_id": item.get("source_id"),
            "binding_class": binding.get("binding_class", "candidate_retrieval"),
            "activation_status": status,
            "trigger_stage": trigger_stage,
            "activation_reason": "前置产物显式引用来源或命中至少两个解释词" if activated else "当前阶段产物尚未出现资料适用的创作问题或触发条件",
            "stage_evidence": candidates[:10],
            "next_activation_conditions": policy.get("conditions", []),
            "checked_at": now(),
        })
    audit = EVIDENCE / "资料绑定激活审计.jsonl"
    audit.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    summary = {
        "schema_version": "binding-activation-audit-1.0",
        "project_id": project_id,
        "run_id": RUN_ID,
        "checked_stage": trigger_stage,
        "binding_count": len(rows),
        "status_counts": dict(counts),
        "classification_counts": dict(Counter(row["binding_class"] for row in rows)),
        "policy": "前置产物、设计需要和实时检索均可重复触发绑定；未激活不等于遗漏，必须带有下一激活条件。",
        "output": str(audit.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }
    summary_path = RUN_EVIDENCE_DIR / "资料绑定激活审计摘要.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, detail, kind="activation_audit", status="success", exit_code=0)
    register_artifact(PROJECT_ROOT, RUN_ID, summary_path, kind="activation_audit", status="success", exit_code=0)


def _write_consumption_logs(context: dict[str, Any]) -> None:
    """Persist design-stage adoption and later prose evidence separately."""
    cards = context.get("scene_beat_cards") or {}
    card_output = context.get("module_outputs", {}).get("08", {}) if isinstance(context.get("module_outputs"), dict) else {}
    prose = context.get("scene_prose") or {}
    design_scenes = cards.get("scenes", []) if isinstance(cards, dict) else (cards if isinstance(cards, list) else [])
    scenes = prose.get("scenes", []) if isinstance(prose, dict) else []
    type_decision = context.get("type_decision") or {}
    if not type_decision and (OUTPUT_DIR / "module_02_type_decision.json").is_file():
        type_decision = read_json(OUTPUT_DIR / "module_02_type_decision.json")
    world = context.get("world_setting") or {}
    if not world and (OUTPUT_DIR / "module_04_world_setting.json").is_file():
        world = read_json(OUTPUT_DIR / "module_04_world_setting.json")
    config = context.get("project_config") or {}
    project_id = config.get("project_id") or config.get("project_name") or ""
    rows_by_file: dict[str, list[dict[str, Any]]] = {
        "类型连接采用.jsonl": [], "动态链消费.jsonl": [], "静态连接消费.jsonl": [], "锚点消费.jsonl": [],
    }
    selected_combination = config.get("type_combination")
    selected_combination_ids = (
        {str(selected_combination)} if isinstance(selected_combination, str) and selected_combination.strip()
        else {str(item) for item in selected_combination if isinstance(item, str) and item.strip()}
        if isinstance(selected_combination, list) else set()
    )
    for combination in type_decision.get("matching_combinations", []):
        if str(combination.get("combination_id")) not in selected_combination_ids:
            continue
        for connection_id in combination.get("connection_ids", []):
            rows_by_file["类型连接采用.jsonl"].append({
                "record_type": "type_connection",
                "run_id": RUN_ID,
                "project_id": project_id,
                "connection_id": connection_id,
                "combination_id": combination.get("combination_id"),
                "module_id": "02",
                "used_in": "type_decision",
                "purpose": "已确认的项目类型组合决策",
                "decision_statement": (combination.get("recommended_mechanisms") or [""])[0],
                "status": "adopted",
                "source_ref": {
                    "project_id": project_id,
                    "task_id": "TYPE-DECISION",
                    "path": _run_output_ref("02", "type_decision"),
                    "location": "matching_combinations",
                    "artifact_type": "synthesis_design",
                },
            })
    for edge in world.get("selected_static_edges", []):
        rows_by_file["静态连接消费.jsonl"].append({"record_type": "static_connection", "run_id": RUN_ID, "project_id": project_id, "connection_id": _static_edge_id(edge), "source": edge.get("source"), "target": edge.get("target"), "module_id": "04", "used_in": "world_setting", "purpose": "项目世界设定绑定", "decision_statement": f"将{edge.get('source')}与{edge.get('target')}绑定为项目世界约束", "status": "adopted", "bound_to": edge.get("bound_to") or {"type": "事件", "id": "project-mainline"}, "source_ref": {"project_id": project_id, "path": _run_output_ref("04", "world_setting"), "location": "selected_static_edges", "artifact_type": "synthesis_design"}, "used_in_design": [_run_output_ref("08", "scene_beat_cards")]})
    bindings = (cards.get("design_bindings", []) if isinstance(cards, dict) else []) or context.get("design_bindings", []) or card_output.get("design_bindings", [])
    for binding in bindings:
        source_kind = binding.get("source_kind")
        source_id = binding.get("source_id")
        if not source_id:
            continue
        if source_kind == "dynamic_chain":
            filename, id_key = "动态链消费.jsonl", "chain_id"
        elif source_kind == "static_edge":
            filename, id_key = "静态连接消费.jsonl", "connection_id"
        elif source_kind == "anchor":
            filename, id_key = "锚点消费.jsonl", "anchor_id"
        else:
            continue
        row = {"record_type": source_kind, "run_id": RUN_ID, "project_id": project_id, id_key: source_id, "chapter_id": binding.get("chapter_id"), "scene_id": binding.get("scene_id"), "module_id": "08", "used_in": "scene_design", "purpose": binding.get("decision_statement"), "condition": binding.get("activation_conditions") or binding.get("selection_rationale", {}).get("matched_tokens") or "场景选择合同满足", "decision_statement": binding.get("decision_statement"), "selection_rationale": binding.get("selection_rationale"), "status": "adopted", "source_ref": {"project_id": project_id, "path": _run_output_ref("08", "scene_beat_cards"), "location": f"design_bindings[{binding.get('scene_id')}]", "artifact_type": "scene_design"}, "used_in_design": _run_output_ref("08", "scene_beat_cards")}
        if source_kind == "static_edge":
            scene = next((item for item in design_scenes if item.get("scene_id") == binding.get("scene_id")), {})
            edge = scene.get("static_edge", {}) if isinstance(scene, dict) else {}
            row.update({"source": edge.get("source"), "target": edge.get("target"), "bound_to": {"type": "事件", "id": binding.get("scene_id")}})
        rows_by_file[filename].append(row)
    seen_chains = set()
    seen_anchors = set()
    for scene in scenes:
        chapter_id = scene.get("chapter_id")
        chain_id = scene.get("chain_id_used")
        if chain_id and chain_id not in seen_chains:
            rows_by_file["动态链消费.jsonl"].append({"record_type": "dynamic_chain", "run_id": RUN_ID, "project_id": project_id, "chain_id": chain_id, "chapter_id": chapter_id, "scene_id": scene.get("scene_id"), "module_id": "09", "used_in": "prose", "purpose": "正文场景因果推进", "condition": scene.get("project_scene_input", {}).get("trigger") or scene.get("project_scene_input", {}).get("state_before") or "场景行动链要求因果推进", "decision_statement": scene.get("project_scene_input", {}).get("state_after") or scene.get("project_scene_input", {}).get("choice") or "动态链推进场景结果", "source_ref": {"project_id": project_id, "path": _run_output_ref("08", "scene_beat_cards"), "location": f"scenes[{scene.get('scene_id')}]", "artifact_type": "scene_design"}, "status": "consumed", "text_location": f"{scene.get('scene_id')}#paragraphs", "fallback_used": bool(scene.get("fallback_used")), "fallback_reason": scene.get("fallback_reason", ""), "original_required_kind": scene.get("original_required_kind", "dynamic_chain")})
            seen_chains.add(chain_id)
        for anchor_id in scene.get("anchor_ids_used", []):
            if anchor_id not in seen_anchors:
                rows_by_file["锚点消费.jsonl"].append({"record_type": "anchor", "run_id": RUN_ID, "project_id": project_id, "anchor_id": anchor_id, "chapter_id": chapter_id, "scene_id": scene.get("scene_id"), "module_id": "09", "used_in": "prose", "purpose": "正文感官或环境落点", "condition": scene.get("project_scene_input", {}).get("location") or scene.get("project_scene_input", {}).get("state_before") or "场景环境或感官表达需要", "decision_statement": scene.get("project_scene_input", {}).get("location") or "锚点落入当前正文场景", "source_ref": {"project_id": project_id, "path": _run_output_ref("09", "scene_prose"), "location": f"scenes[{scene.get('scene_id')}]#paragraphs", "artifact_type": "prose"}, "status": "consumed", "text_location": f"{scene.get('scene_id')}#paragraphs"})
                seen_anchors.add(anchor_id)
    for filename, rows in rows_by_file.items():
        path = RUN_EVIDENCE_DIR / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = list(rows)
        header = {"record_type": "header", "schema_version": "1.2", "run_id": RUN_ID, "total_records": len(rows), "last_updated": now(), "project_id": project_id, "project_root": str(PROJECT_ROOT)}
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in [header, *rows]) + "\n", encoding="utf-8")


def execute_01(data: dict) -> tuple[dict, list[Path]]:
    require(PROJECT_CONFIG)
    try:
        project_config = read_json(PROJECT_CONFIG)
    except json.JSONDecodeError as exc:
        output = {
            "project_config_path": str(PROJECT_CONFIG),
            "status": "failed",
            "blocking_failures": [f"项目配置 JSON 语法错误：第{exc.lineno}行第{exc.colno}列：{exc.msg}"],
            "input_contract": {"valid": False, "errors": ["invalid_json"]},
        }
        return output, [write_output("01", "project_config", output)]
    if not isinstance(project_config, dict):
        raise ValueError(f"项目配置必须是JSON对象：{PROJECT_CONFIG}")
    config_errors = _project_config_errors(project_config)
    project_id = project_config.get("project_id") or project_config.get("project_name")
    if not project_id:
        raise ValueError(f"项目配置缺少 project_id/project_name：{PROJECT_CONFIG}")
    genres = project_config.get("genre_selection") or project_config.get("genres") or []
    if isinstance(genres, str):
        genres = [genres]
    protagonist = project_config.get("protagonist")
    protagonist_name = (
        protagonist.get("name") if isinstance(protagonist, dict) else None
    ) or project_config.get("protagonist_name") or project_config.get("main_character") or project_config.get("主角名称") or ""
    output = {
        "project_id": project_id,
        "project_name": project_config.get("project_name", project_id),
        "book_title": project_config.get("book_title", ""),
        "genre_selection": genres,
        "chapter_target": project_config.get("chapter_target", 1),
        "protagonist_name": protagonist_name,
        "project_config": project_config,
        "project_config_path": str(PROJECT_CONFIG),
        "initialized_at": now(),
        "status": "failed" if config_errors else "success",
        "blocking_failures": config_errors,
        "input_contract": {"valid": not config_errors, "errors": config_errors},
    }
    output["run_id"] = RUN_ID
    output["run_input_snapshot"] = str(snapshot_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    output["run_input_snapshot_sha256"] = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    return output, [write_output("01", "project_config", output), snapshot_path]


def _type_combination_candidates(index: dict[str, Any], selected_types: list[str], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only source-backed combinations matching every selected type."""
    selected = [str(item).strip() for item in selected_types if str(item).strip()]
    configured = config.get("type_combination") if isinstance(config, dict) else {}
    configured_id = str(configured.get("combination_id") or "").strip() if isinstance(configured, dict) else ""
    candidates = index.get("combinations", []) if isinstance(index, dict) else []
    result: list[dict[str, Any]] = []
    for item in candidates if isinstance(candidates, list) else []:
        if not isinstance(item, dict):
            continue
        source_types = item.get("types")
        if not isinstance(source_types, list):
            source_types = re.split(r"[+_、,，]", str(source_types or ""))
        item_types = [str(value).strip() for value in source_types if str(value).strip()]
        if selected and not all(value in item_types for value in selected):
            continue
        normalized_id = str(item.get("combination_id") or ("+".join(item_types) if item_types else "")).strip()
        if configured_id and normalized_id not in {configured_id, configured_id.replace("+", "_")}:
            continue
        if not item.get("connection_id") or not item.get("source_ref"):
            continue
        result.append({
            **item,
            "combination_id": normalized_id or item.get("connection_id"),
            "types": item_types,
            "connection_ids": item.get("connection_ids") or [item.get("connection_id")],
        })
    if result:
        return result
    template_path = PROJECT_ROOT / "配置" / "类型配置模板.json"
    template = read_json(template_path) if template_path.is_file() else {}
    for item in template.get("combinations", []) if isinstance(template, dict) else []:
        if not isinstance(item, dict) or item.get("source_status") != "cross_confirmed":
            continue
        item_types = [str(value).strip() for value in item.get("types", []) if str(value).strip()]
        normalized_id = str(item.get("combination_id") or ("+".join(item_types) if item_types else "")).strip()
        if not item_types or (selected and not all(value in item_types for value in selected)):
            continue
        if configured_id and normalized_id not in {configured_id, configured_id.replace("+", "_")}:
            continue
        if not item.get("source_ref"):
            continue
        result.append({
            "connection_id": f"type-template:{normalized_id}",
            "combination_id": normalized_id,
            "types": item_types,
            "connection_ids": [],
            "compatibility": "derived_type_template",
            "source_ref": item["source_ref"],
            "source_status": "cross_confirmed",
            "decision_basis": "derived_type_profile_for_draft_only",
        })
    return result


def _type_decision_contract(config: dict[str, Any], selected_types: list[str], matches: list[dict[str, Any]], source: str) -> dict[str, Any]:
    combination = config.get("type_combination") if isinstance(config, dict) else {}
    combination = combination if isinstance(combination, dict) else {}
    status = "matched_draft_only" if matches else "pending_source_match"
    return {
        "schema_version": "project-type-decision-contract-1.0",
        "project_id": config.get("project_id"),
        "selected_types": selected_types,
        "primary_type": config.get("primary_type") or (selected_types[0] if selected_types else ""),
        "combination_id": combination.get("combination_id") or (matches[0].get("combination_id") if matches else ""),
        "source_backed_matches": matches[:20],
        "source": source,
        "status": status,
        "formal_fact_allowed": False,
        "draft_only": True,
        "blocking_reason": "没有来源支持的完整类型组合；必须先补齐或确认类型连接合同。" if not matches else "类型组合可回链，但当前项目仍需保持 draft_only。",
    }


def execute_02(data: dict) -> tuple[dict, list[Path]]:
    require(TYPE_SYSTEM); require(TYPE_INDEX)
    index = read_json(TYPE_INDEX)
    genres = data.get("genre_selection", data.get("genres", []))
    if isinstance(genres, str):
        genres = [genres]
    genres = [str(item).strip() for item in genres if str(item).strip()]
    matches = _type_combination_candidates(index, genres, data.get("project_config", {}))
    contract = _type_decision_contract(data.get("project_config", {}), genres, matches, str(TYPE_INDEX.relative_to(PROJECT_ROOT)).replace("\\", "/"))
    output = {
        "selected_types": genres,
        "type_system_source_lines": len(read_text(TYPE_SYSTEM).splitlines()),
        "matching_combinations": matches[:20],
        "type_decision_contract": contract,
        "decision_status": "matched" if matches else "blocked_source_match",
        "status": "success" if matches else "failed",
        "blocking_failures": [] if matches else [contract["blocking_reason"]],
    }
    return output, [write_output("02", "type_decision", output), _write_type_decision_contract(contract)]


def _write_type_decision_contract(contract: dict[str, Any]) -> Path:
    path = EVIDENCE / "项目类型决策合同.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return path


def execute_03(data: dict) -> tuple[dict, list[Path]]:
    require(TYPE_INDEX)
    matches = data.get("matching_combinations", [])
    if not isinstance(matches, list):
        matches = []
    edges = [
        {"id": item.get("combination_id"), "types": item.get("types", []), "compatibility": item.get("compatibility"), "connections": item.get("connection_ids", []), "source_ref": item.get("source_ref")}
        for item in matches if isinstance(item, dict) and item.get("combination_id") and item.get("types")
    ]
    contract = data.get("type_decision_contract", {})
    nodes = sorted({str(node) for edge in edges for node in edge.get("types", []) if str(node).strip()})
    output = {
        "nodes": nodes,
        "edges": edges,
        "combination_count": len(edges),
        "status": "success" if edges and nodes else "failed",
        "blocking_failures": [] if edges and nodes else ["类型依赖图缺少来源支持的非空组合；禁止输出空图伪成功。"],
        "type_decision_contract_status": contract.get("status"),
    }
    return output, [write_output("03", "type_dependency_graph", output)]


def execute_04(data: dict) -> tuple[dict, list[Path]]:
    static_full_path = first_existing(
        RESOURCE_ROOT / "核心资料" / "网络完整数据" / "static_connections.full.json",
        RESOURCE_ROOT / "网络完整数据" / "static_connections.full.json",
        STATIC_FULL,
    )
    binding_summary_path = first_existing(
        RESOURCE_ROOT / "核心资料" / "文档" / "证据" / "静态网络绑定汇总.json",
        EVIDENCE / "静态网络绑定汇总.json",
        STATIC_BINDING_SUMMARY,
    )
    require(LIBRARY); require(PROJECT_CONFIG); require(static_full_path); require(binding_summary_path)
    project_config = read_json(PROJECT_CONFIG)
    project_types = project_config.get("genre_selection", project_config.get("genres", []))
    if isinstance(project_types, str):
        project_types = [project_types]
    project_types = [str(item).strip() for item in project_types if str(item).strip()]
    type_profiles = read_json(PROJECT_ROOT / "配置" / "类型配置模板.json") if (PROJECT_ROOT / "配置" / "类型配置模板.json").is_file() else {}
    profile_map = type_profiles.get("types", {}) if isinstance(type_profiles, dict) else {}
    profile_terms = []
    for type_name in project_types:
        profile = profile_map.get(type_name, {}) if isinstance(profile_map, dict) else {}
        if isinstance(profile, dict):
            profile_terms.extend(str(term).strip() for term in profile.get("core_elements", []) if str(term).strip())
            profile_terms.extend(str(term).strip() for term in profile.get("style_constraints", []) if str(term).strip())
    keywords = tuple(dict.fromkeys(profile_terms))
    project_type = project_types[0] if project_types else ""

    library_entries = _read_library_blocks(LIBRARY, WORLD_BLOCKS)
    static_data = read_json(static_full_path)
    all_edges = _static_connections(static_data)
    binding_summary = read_json(binding_summary_path)
    repair_log = _binding_log(EVIDENCE / "静态网络绑定修复日志.jsonl")
    selected_edges = []
    for edge in all_edges:
        endpoint_text = f"{edge.get('source', '')} {edge.get('target', '')}"
        if not any(keyword in endpoint_text for keyword in keywords):
            continue
        repair = repair_log.get((edge.get("source", ""), edge.get("target", "")), {})
        selected_edges.append({
            field: edge.get(field)
            for field in ("source", "target", "type", "condition", "effect")
        } | {
            "binding_type": edge.get("binding_type") or repair.get("new_binding_type") or "待定",
            "mainline_level": edge.get("mainline_level") or repair.get("new_mainline_level") or "次要",
        })

    by_block = {block: _library_entry_payload(library_entries, block) for block in WORLD_BLOCKS}
    index = read_json(STATIC_INDEX) if STATIC_INDEX.is_file() else {}
    nodes = index.get("unique_source_nodes", []) + index.get("unique_target_nodes", [])
    output = {
        "world_basics": by_block[31],
        "world_history": by_block[32],
        "social_system": by_block[33],
        "world_rules": by_block[34],
        "ecological_structure": {"ecology": by_block[20], "dynamics": by_block[21]},
        "resource_system": {
            "resources": by_block[24], "currency": by_block[25],
            "trade": by_block[26], "circulation": by_block[27],
        },
        "power_forces": by_block[22],
        "hidden_flows": by_block[23],
        "world_setting_entries": library_entries,
        "type_priority_blocks": {
            "project_type": project_type,
            "priority": {
                "玄幻": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 36, 37, 39, 40],
                "仙侠": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 36, 37, 39, 40],
                "科幻": [17, 18, 19], "都市": [33, 39], "悬疑": [23, 34, 35],
            }.get(project_type, []),
            "selected_priority_entries": [entry for entry in library_entries if entry["block"] in {
                "玄幻": {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 36, 37, 39, 40},
                "仙侠": {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 36, 37, 39, 40},
                "科幻": {17, 18, 19}, "都市": {33, 39}, "悬疑": {23, 34, 35},
            }.get(project_type, set())],
        },
        "selected_static_edges": selected_edges,
        "edge_count": len(selected_edges),
        "static_edge_total": len(all_edges),
        "binding_summary": binding_summary,
        "bind_to_project_type": project_type,
        "filter_criteria": {"project_type": project_type, "keywords": list(keywords), "mode": "source_or_target_contains_keyword"},
        "core_nodes": nodes[:30],
        "resource_nodes": [n for n in nodes if any(k in n for k in ("资源", "能量", "力量"))],
    }
    print(json.dumps({
        "读取的资料库世界设定板块数": len({entry["block"] for entry in library_entries}),
        "读取的静态网络边总数": len(all_edges),
        "选中的静态边数量": len(selected_edges),
        "绑定的项目类型": project_type,
        "使用的筛选条件": output["filter_criteria"],
    }, ensure_ascii=False))
    return output, [write_output("04", "world_setting", output)]


def execute_05(data: dict) -> tuple[dict, list[Path]]:
    require(ANCHOR_INDEX)
    index = read_json(ANCHOR_INDEX)
    categories = index.get("category_counts", {}) if isinstance(index, dict) else {}
    project = data.get("project_config", {}) if isinstance(data.get("project_config"), dict) else {}
    scenes = [
        scene
        for chapter in project.get("chapter_plan", []) if isinstance(chapter, dict)
        for scene in chapter.get("scenes", []) if isinstance(scene, dict)
    ]
    first_scene = scenes[0] if scenes else {}
    scene_text = _scene_text(first_scene) if first_scene else ""
    anchor_rows = _anchor_entries(ANCHOR_NETWORK, index)
    ranked = []
    for category, entries in anchor_rows.items():
        for entry in entries:
            text = " ".join(str(entry.get(key, "")) for key in ("anchor_name", "definition", "trigger", "category"))
            score = len(_semantic_tokens(scene_text) & _semantic_tokens(text))
            if score > 0:
                ranked.append((score, category, entry))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2].get("anchor_id", "")))
    opening = [entry for _, _, entry in ranked[:3]]
    output = {
        "opening_anchor_categories": [category for _, category, _ in ranked[:3]] or [category for category, count in categories.items() if count][:3],
        "opening_anchor_ids": [entry.get("anchor_id") for entry in opening],
        "opening_anchor_selection": "scene_need_semantic_match",
        "opening_scene_id": first_scene.get("scene_id"),
        "anchor_total": index.get("total_anchors", 0) if isinstance(index, dict) else 0,
        "status": "success" if index else "failed",
    }
    return output, [write_output("05", "opening_design", output)]


def _route_dynamic_chains_to_scenes(
    chains: list[dict[str, Any]], project_config: dict[str, Any], brief: dict[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Create an explicit scene route for already validated dynamic chains.

    Routing is based on scene semantics and the chain target/condition. It is
    deliberately one-to-one for a run, but never uses scene index as evidence.
    A required scene with no positive match remains unresolved and blocks 08.
    """
    chapter_plan = project_config.get("chapter_plan", []) if isinstance(project_config, dict) else []
    project_scenes = [
        scene
        for chapter in chapter_plan if isinstance(chapter, dict)
        for scene in chapter.get("scenes", []) if isinstance(scene, dict)
    ]
    brief_by_scene = {
        str(scene.get("scene_id")): scene
        for scene in brief.get("scenes", [])
        if isinstance(scene, dict) and scene.get("scene_id")
    }
    routes: dict[str, list[dict[str, Any]]] = {}
    unresolved: list[str] = []
    remaining = list(chains)

    def route_terms(chain: dict[str, Any]) -> set[str]:
        text = " ".join(str(chain.get(key, "")) for key in ("source", "target", "type", "condition", "effect"))
        terms: set[str] = set()
        if any(token in text for token in ("悬念", "核心", "秘密", "异常", "揭示", "真相")):
            terms.update(("异常", "证据", "档案", "缺页", "线索", "阵法", "回响", "同步", "确认"))
        if any(token in text for token in ("弧光", "演化", "阶段", "成长")):
            terms.update(("选择", "代价", "风险", "状态", "变化", "越界", "晋升", "后果"))
        if any(token in text for token in ("共鸣", "关系", "信任", "情感")):
            terms.update(("关系", "信任", "陆昭", "药额", "选择", "代价", "风险"))
        return terms

    for scene in project_scenes:
        scene_id = str(scene.get("scene_id") or "")
        brief_scene = brief_by_scene.get(scene_id, {})
        if "动态网络" not in set(brief_scene.get("required_source_kinds", [])):
            continue
        scene_text = " ".join(
            str(scene.get(key, ""))
            for key in ("purpose", "location", "character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook")
        ) + " " + " ".join(str(value) for value in brief_scene.get("retrieval_terms", []))
        scene_tokens = _semantic_tokens(scene_text)
        ranked = []
        for chain in remaining:
            chain_id = str(chain.get("id") or chain.get("dynamic_edge_id") or chain.get("edge_id") or "")
            if not chain_id:
                continue
            chain_text = " ".join(str(chain.get(key, "")) for key in ("source", "target", "type", "condition", "effect"))
            score = len(scene_tokens & (_semantic_tokens(chain_text) | route_terms(chain)))
            ranked.append((score, chain_id, chain))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        if not ranked or ranked[0][0] <= 0:
            unresolved.append(scene_id)
            continue
        score, _, chosen = ranked[0]
        routed = dict(chosen)
        routed["scene_route"] = {
            "scene_id": scene_id,
            "match_score": score,
            "routing_terms": sorted(route_terms(chosen)),
            "routing_basis": "project_scene_fields_plus_brief_retrieval_terms",
        }
        routes[scene_id] = [routed]
        remaining = [item for item in remaining if item is not chosen]
    return routes, unresolved


def execute_06(data: dict) -> tuple[dict, list[Path]]:
    require(LIBRARY); require(DYNAMIC_FULL); require(DYNAMIC_STATE); require(PROJECT_CONFIG)
    project_config = read_json(PROJECT_CONFIG)
    project_types = project_config.get("genre_selection", project_config.get("genres", ["玄幻"]))
    if isinstance(project_types, str):
        project_types = [project_types]
    protagonist_config = project_config.get("protagonist") if isinstance(project_config.get("protagonist"), dict) else {}
    protagonist = protagonist_config.get("name") or project_config.get("protagonist_name") or project_config.get("main_character") or project_config.get("主角名称") or ""
    dynamic_node_id = str(protagonist_config.get("dynamic_node_id") or "1.1")
    dynamic_node_name = str(protagonist_config.get("dynamic_node_name") or "主角")
    dynamic_aliases = protagonist_config.get("dynamic_aliases") or []
    if isinstance(dynamic_aliases, str):
        dynamic_aliases = [dynamic_aliases]
    dynamic_binding_tokens = tuple(dict.fromkeys((f"{dynamic_node_id}_{dynamic_node_name}", *[str(alias) for alias in dynamic_aliases])))
    if dynamic_node_id == "1.1" and dynamic_node_name == "主角" and not dynamic_aliases:
        dynamic_binding_tokens = ("1.1_主角",)

    character_blocks = set(range(1, 20)) | set(range(70, 77)) | set(range(80, 83)) | {118, 121} | set(range(140, 155))
    plot_blocks = {41, 42, 43, 44, 45, 130}
    character_entries = _read_library_blocks(LIBRARY, character_blocks)
    plot_entries = _read_library_blocks(LIBRARY, plot_blocks)
    character_map = _entry_map(character_entries)
    plot_map = _entry_map(plot_entries)

    role_definitions = []
    for role_id in ("1.1", "1.2", "1.3", "1.4", "1.5", "1.6"):
        role = next((entry for key, entry in character_map.items() if key == role_id or key.startswith(role_id + "_")), None)
        if role:
            role_definitions.append(role)
    characters = []
    filtered_character_fields = 0
    for entry in role_definitions:
        role_name = entry["name"]
        configured = entry["item_id"] == "1.1" or entry["item_id"].startswith("1.1_")
        desire = protagonist_config.get("desire") if configured else _first_text(character_map, "3.1", "")
        obsession = protagonist_config.get("obsession") if configured else _first_text(character_map, "3.2", "")
        arc_stage = protagonist_config.get("arc_stage", "") if configured else _first_text(character_map, "4.1", "")
        if not configured:
            filtered_character_fields += sum(not value for value in (desire, obsession, arc_stage))
        character = {
            "name": protagonist if configured else role_name,
            "type": "主角" if configured else role_name,
            "desire": desire,
            "obsession": obsession,
            "arc_stage": arc_stage,
            "relationships": [character_map[key]["name"] for key in sorted(character_map) if key.startswith("5.")],
            "emotional_pattern": [character_map[key]["name"] for key in sorted(character_map) if key.startswith("6.") or key.startswith("7.")],
            "decision_tendency": protagonist_config.get("decision_tendency", []) if configured else [character_map[key]["name"] for key in sorted(character_map) if key.startswith("72.")],
            "source_refs": [entry["source_ref"]] + [character_map[key]["source_ref"] for key in ("3.1", "3.2", "4.1") if key in character_map],
            "configuration_status": "configured" if configured else "unconfigured",
        }
        if configured:
            character.update({
                "personality": protagonist_config.get("personality", []),
                "blind_spots": protagonist_config.get("blind_spots", []),
                "emotional_reactions": protagonist_config.get("emotional_reactions", []),
                "project_input_source": "配置/project_config.json",
            })
        characters.append(character)

    dynamic_data = read_json(DYNAMIC_FULL)
    dynamic, dynamic_resolution = _resolve_dynamic_connections(dynamic_data)
    state_summary = read_json(DYNAMIC_STATE)
    protagonist_matches = []
    for chain in dynamic:
        endpoints = f"{chain.get('source', '')} {chain.get('target', '')}"
        valid_payload = (
            _nonempty(chain.get("condition"))
            and _nonempty(chain.get("effect"))
            and not _contains_project_template(chain.get("condition", ""))
            and not _contains_project_template(chain.get("effect", ""))
        )
        if valid_payload and ((protagonist and protagonist in endpoints) or any(token and token in endpoints for token in dynamic_binding_tokens)):
            protagonist_matches.append(chain)
    fallback_reason = dynamic_resolution["fallback_reason"] or None
    selected = protagonist_matches
    if not selected:
        fallback_reason = f"未找到包含项目主角名称“{protagonist}”的动态链；禁止回退到通用主角链。"
    selected_dynamic_chains = [
        {
            "id": chain.get("id") or chain.get("dynamic_edge_id") or chain.get("edge_id"),
            **{field: chain.get(field) for field in ("source", "target", "type", "condition", "effect")},
            "project_protagonist": protagonist,
            "canonical_node_id": dynamic_node_id,
            "canonical_node_name": dynamic_node_name,
            "binding_tokens": list(dynamic_binding_tokens),
            "binding_mode": "project_name" if protagonist and protagonist in f"{chain.get('source', '')} {chain.get('target', '')}" else "canonical_node",
        }
        for chain in selected
    ]
    route_brief_path = PROJECT_ROOT / "配置" / "首章场景创作简报.json"
    route_brief = read_json(route_brief_path) if route_brief_path.is_file() else {}
    scene_dynamic_routes, unresolved_dynamic_scenes = _route_dynamic_chains_to_scenes(
        selected_dynamic_chains,
        project_config,
        route_brief if isinstance(route_brief, dict) else {},
    )
    invalid_dynamic_chains = [
        chain.get("id") or chain.get("dynamic_edge_id")
        for chain in selected_dynamic_chains
        if not _nonempty(chain.get("condition")) or not _nonempty(chain.get("effect"))
        or _contains_project_template(chain.get("condition", "")) or _contains_project_template(chain.get("effect", ""))
    ]
    chapter_plan = project_config.get("chapter_plan", [])
    requested_scene_count = sum(len(chapter.get("scenes", [])) for chapter in chapter_plan if isinstance(chapter, dict))
    brief_path = PROJECT_ROOT / "配置" / "首章场景创作简报.json"
    brief = read_json(brief_path) if brief_path.is_file() else {}
    brief_by_scene = {
        str(scene.get("scene_id")): scene
        for scene in brief.get("scenes", [])
        if isinstance(scene, dict) and scene.get("scene_id")
    }
    dynamic_required_scene_count = sum(
        "动态网络" in set(brief_by_scene.get(str(scene.get("scene_id")), {}).get("required_source_kinds", []))
        for chapter in chapter_plan if isinstance(chapter, dict)
        for scene in chapter.get("scenes", []) if isinstance(scene, dict)
    ) or requested_scene_count
    if len(selected_dynamic_chains) < dynamic_required_scene_count:
        fallback_reason = fallback_reason or f"有效动态链数量不足：需要动态资料的场景数为{dynamic_required_scene_count}条，实际{len(selected_dynamic_chains)}条；禁止按序号补齐。"

    def named_entries(block: int) -> list[dict[str, Any]]:
        return [entry for entry in plot_entries if entry["block"] == block]

    current_chapter = chapter_plan[0] if isinstance(chapter_plan, list) and chapter_plan else {}
    plot_structure = {
        "three_act_structure": named_entries(41),
        "plot_progression": named_entries(42),
        "conflict_types": named_entries(43),
        "payoff_distribution": named_entries(44),
        "foreshadowing_plan": named_entries(45),
        "core_mystery": named_entries(130),
        "source_blocks": sorted({entry["block"] for entry in plot_entries}),
        "project_chapter_plan": current_chapter,
        "project_mainline_conflict": project_config.get("mainline_conflict", ""),
        "project_core_mystery": project_config.get("core_mystery", ""),
    }
    characters[0]["bound_to_project"] = True if characters else False
    output = {
        "characters": characters,
        "plot_structure": plot_structure,
        "selected_dynamic_chains": selected_dynamic_chains,
        "scene_dynamic_routes": scene_dynamic_routes,
        "unresolved_dynamic_scenes": unresolved_dynamic_scenes,
        "chain_count": len(selected_dynamic_chains),
        "bind_to_project": [character["name"] for character in characters if character.get("bound_to_project")],
        "fallback_reason": fallback_reason,
        "dynamic_resolution": dynamic_resolution,
        "dynamic_binding": {
            "project_name": protagonist,
            "canonical_node_id": dynamic_node_id,
            "canonical_node_name": dynamic_node_name,
            "tokens": list(dynamic_binding_tokens),
            "matched_chain_count": len(selected_dynamic_chains),
            "bound": bool(selected_dynamic_chains),
        },
        "project_config_summary": {"project_id": project_config.get("project_id"), "book_title": project_config.get("book_title"), "protagonist_name": protagonist, "types": project_types},
        "source_counts": {"character_entries": len(character_entries), "plot_entries": len(plot_entries), "dynamic_chains": len(dynamic)},
        "dynamic_state_summary": state_summary,
        "plot_edges": data.get("edge_count", 0),
        "dynamic_edges": len(dynamic),
        "status": "success" if selected_dynamic_chains and not invalid_dynamic_chains and len(selected_dynamic_chains) >= dynamic_required_scene_count and not unresolved_dynamic_scenes and not dynamic_resolution["fallback_used"] else "failed",
        "blocking_failures": ([f"动态结构回退被阻断：{dynamic_resolution['fallback_reason']}"] if dynamic_resolution["fallback_used"] else []) + ([] if selected_dynamic_chains and not invalid_dynamic_chains and len(selected_dynamic_chains) >= dynamic_required_scene_count and not unresolved_dynamic_scenes else [fallback_reason or "项目人物未绑定到动态网络"]) + ([f"动态链缺少真实condition/effect：{invalid_dynamic_chains}"] if invalid_dynamic_chains else []) + ([f"动态链未能路由到场景：{unresolved_dynamic_scenes}"] if unresolved_dynamic_scenes else []),        "filtered_template_fields": filtered_character_fields,
    }
    print(json.dumps({
        "人物设定条目数": len(character_entries),
        "剧情设定条目数": len(plot_entries),
        "动态链总数": len(dynamic),
        "选中动态链数量": len(selected_dynamic_chains),
        "绑定人物名称": output["bind_to_project"],
        "使用fallback": fallback_reason is not None,
    }, ensure_ascii=False))
    primary = write_output("06", "人物与剧情核心", output)
    compatibility = write_output("06", "character_plot_core", output)
    return output, [primary, compatibility]


def execute_07(data: dict) -> tuple[dict, list[Path]]:
    require(DYNAMIC_FULL); require(ANCHOR_INDEX); dynamic = read_json(DYNAMIC_FULL).get("connections", []); anchors = read_json(ANCHOR_INDEX)
    output = {"dynamic_connection_count": len(dynamic), "anchor_count": anchors.get("total_anchors", 0), "quality_rules": ["每场景至少一个锚点", "动态链必须可验证"], "priority_one_connections": sum(r.get("priority", 0) == 1 for r in dynamic)}
    return output, [write_output("07", "quality_rules", output)]


def execute_08(data: dict) -> tuple[dict, list[Path]]:
    require(LIBRARY); require(DYNAMIC_FULL); require(DYNAMIC_STATE); require(ANCHOR_INDEX); require(PROJECT_CONFIG)
    contract = validate_execution_contract(PROJECT_ROOT, require_blueprint=False, phase="creation")
    if contract["status"] != "passed":
        raise ValueError("模块08项目执行边界未通过：" + "；".join(contract["errors"]))
    project_config = read_json(PROJECT_CONFIG)
    project_types = project_config.get("genre_selection", project_config.get("genres", ["玄幻"]))
    if isinstance(project_types, str):
        project_types = [project_types]
    project_type = project_types[0] if project_types else "玄幻"
    protagonist_config = project_config.get("protagonist") if isinstance(project_config.get("protagonist"), dict) else {}
    protagonist = protagonist_config.get("name") or project_config.get("protagonist_name") or project_config.get("main_character") or project_config.get("主角名称") or ""

    core = data.get("module_06_character_plot_core") or data.get("character_plot_core")
    if not core:
        core_path = first_existing(OUTPUT_DIR / "module_06_character_plot_core.json", OUTPUT_DIR / "module_06_人物与剧情核心.json")
        core = read_json(core_path)
    selected = core.get("selected_dynamic_chains", []) if isinstance(core, dict) else []
    selected = selected if isinstance(selected, list) else []
    chapter_plan = project_config.get("chapter_plan", [])
    chapters = [chapter for chapter in chapter_plan if isinstance(chapter, dict)] if isinstance(chapter_plan, list) else []
    current_chapter = chapters[0] if chapters else {}
    project_scenes = [(chapter, scene) for chapter in chapters for scene in (chapter.get("scenes", []) or []) if isinstance(scene, dict)]
    activation_matrix = data.get("activation_matrix") if isinstance(data.get("activation_matrix"), dict) else read_json(EVIDENCE / "全书资料激活矩阵.json")
    matrix_assignments = activation_matrix.get("assignments", []) if isinstance(activation_matrix, dict) else []
    if not isinstance(matrix_assignments, list):
        matrix_assignments = []
    fallback_reason = None
    contract_errors = []
    if not project_scenes:
        contract_errors.append("项目章节缺少场景细纲：chapter_plan[].scenes")
    brief_path = PROJECT_ROOT / "配置" / "首章场景创作简报.json"
    brief = read_json(brief_path) if brief_path.is_file() else {}
    brief_by_scene = {
        str(scene.get("scene_id")): scene
        for scene in brief.get("scenes", [])
        if isinstance(scene, dict) and scene.get("scene_id")
    }
    dynamic_scene_ids = [
        str(scene.get("scene_id"))
        for _, scene in project_scenes
        if "动态网络" in set(brief_by_scene.get(str(scene.get("scene_id")), {}).get("required_source_kinds", []))
    ]
    if len(selected) < len(dynamic_scene_ids):
        fallback_reason = f"module_06_selected_dynamic_chains数量为{len(selected)}，需要动态资料的场景数为{len(dynamic_scene_ids)}；禁止使用通用动态链补齐。"
        contract_errors.append(fallback_reason)
    chains = []
    dynamic_ids = _dynamic_id_lookup()
    scene_dynamic_candidates: dict[str, list[dict[str, Any]]] = {scene_id: [] for scene_id in dynamic_scene_ids}
    remaining_dynamic = list(selected)

    def _dynamic_route_terms(edge: dict[str, Any]) -> set[str]:
        """Map a validated dynamic target to semantic scene functions.

        This is a routing vocabulary, not a project fact and not a positional
        assignment. The selected chain still has to score against the complete
        project scene input before it can be routed.
        """
        text = " ".join(str(edge.get(key, "")) for key in ("source", "target", "type", "condition", "effect"))
        terms = set()
        if any(token in text for token in ("悬念", "秘密", "异常", "揭示", "真相")):
            terms.update(("信息", "线索", "异常", "证据", "档案", "缺页", "真相", "回响"))
        if any(token in text for token in ("弧光", "演化", "阶段", "成长")):
            terms.update(("选择", "代价", "风险", "状态", "变化", "关系", "越界"))
        if any(token in text for token in ("共鸣", "关系", "信任", "情感")):
            terms.update(("关系", "信任", "药额", "风险", "选择", "代价"))
        return terms

    for scene_id in dynamic_scene_ids:
        project_scene = next((scene for _, scene in project_scenes if str(scene.get("scene_id")) == scene_id), {})
        brief_scene = brief_by_scene.get(scene_id, {})
        scene_text = " ".join(
            str(project_scene.get(key, ""))
            for key in ("purpose", "location", "character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook")
        )
        scene_text += " " + " ".join(str(value) for value in brief_scene.get("retrieval_terms", []))
        scene_tokens = _semantic_tokens(scene_text)
        ranked = sorted(
            (
                len(scene_tokens & (_semantic_tokens(" ".join(str(edge.get(key, "")) for key in ("source", "target", "type", "condition", "effect"))) | _dynamic_route_terms(edge))),
                str(edge.get("id") or ""),
                edge,
            )
            for edge in remaining_dynamic
        )
        ranked.sort(key=lambda item: (-item[0], item[1]))
        if ranked and ranked[0][0] > 0:
            chosen = dict(ranked[0][2])
            chosen["scene_route"] = {
                "scene_id": scene_id,
                "match_score": ranked[0][0],
                "routing_terms": sorted(_dynamic_route_terms(chosen)),
                "routing_basis": "project_scene_fields_plus_brief_retrieval_terms",
            }
            scene_dynamic_candidates[scene_id].append(chosen)
            remaining_dynamic = [edge for edge in remaining_dynamic if edge is not ranked[0][2]]
    for edge in selected:
        edge_type = edge.get("type")
        chains.append({
            "id": edge.get("id") or edge.get("dynamic_edge_id") or edge.get("edge_id") or dynamic_ids.get((str(edge.get("source", "")), str(edge.get("target", "")), str(edge_type or ""))),
            "source": edge.get("source"), "target": edge.get("target"), "type": edge_type,
            "condition": edge.get("condition"), "effect": edge.get("effect"),
        })

    # Parsed material drives drafting. Blueprint permissions are delivery audit
    # evidence, not an input filter that erases usable creative material.
    planner_entries = _planner_library_entries(LIBRARY)
    library_entries = [entry for entry in planner_entries if entry["block"] == 87 and any(entry.get("item_id", "").startswith(prefix) for prefix in ("87.1_", "87.2_", "87.3_"))]
    library_entries.extend(entry for entry in _read_library_blocks(LIBRARY, {145, 148}) if entry["block"] in {145, 148})
    library_entries.extend(entry for entry in planner_entries if any(
            entry["item_id"].startswith(prefix)
            for prefix in ("155.1_", "155.2_", "155.3_", "159.1_")
        ))
    definitions_by_block = {block: _library_entry_payload(library_entries, block) for block in (87, 145, 148, 155, 159)}
    planner_definition = {
        "87": [{key: entry[key] for key in ("item_id", "name", "definition", "instruction", "source_ref")} for entry in definitions_by_block[87]],
        "145": definitions_by_block[145], "148": definitions_by_block[148],
        "155": definitions_by_block[155], "159": definitions_by_block[159],
    }

    anchor_index = read_json(ANCHOR_INDEX)
    anchors_by_category = _anchor_entries(ANCHOR_NETWORK, anchor_index)
    all_anchors = [anchor for entries in anchors_by_category.values() for anchor in entries]
    static_data = read_json(STATIC_FULL)
    static_candidates = _static_connections(static_data)
    all_dynamic, dynamic_resolution = _resolve_dynamic_connections(read_json(DYNAMIC_FULL))
    if dynamic_resolution["fallback_used"]:
        contract_errors.append(f"动态结构回退被阻断：{dynamic_resolution['fallback_reason']}")
    design_bindings = []
    scenes = []
    for index, (chapter, project_scene) in enumerate(project_scenes):
        scene_id = project_scene.get("scene_id") or f"SCENE-{index + 1}"
        scene_input = {**project_scene, "chapter_id": chapter.get("chapter_id")}
        selected_library, library_selection = _select_library_entries(planner_entries, scene_input)
        upstream_scene = _upstream_scene_dispatch(data, scene_input, str(chapter.get("chapter_id") or ""))
        mapped_dynamic = []
        if isinstance(core, dict) and isinstance(core.get("scene_dynamic_routes"), dict):
            mapped_dynamic = core.get("scene_dynamic_routes", {}).get(str(scene_id), []) or []
        elif isinstance(scene_dynamic_candidates, dict):
            mapped_dynamic = scene_dynamic_candidates.get(str(scene_id), []) or []
        upstream_dynamic_ids = set()
        upstream_dynamic_objects = []
        dynamic_values = mapped_dynamic if mapped_dynamic else upstream_scene.get("dynamic_chains", [])
        for value in dynamic_values:
            if isinstance(value, dict):
                upstream_dynamic_objects.append(value)
                for key in ("id", "dynamic_edge_id", "edge_id"):
                    if value.get(key):
                        upstream_dynamic_ids.add(str(value[key]))
            elif value:
                upstream_dynamic_ids.add(str(value))
        selected_dynamic = [
            item for item in all_dynamic
            if str(item.get("id") or item.get("dynamic_edge_id") or item.get("edge_id")) in upstream_dynamic_ids
        ]
        if not selected_dynamic:
            selected_dynamic = [
                item for item in upstream_dynamic_objects
                if item.get("id") or item.get("dynamic_edge_id") or item.get("edge_id")
            ]
        requires_dynamic = "动态网络" in set(brief_by_scene.get(str(scene_id), {}).get("required_source_kinds", []))
        if mapped_dynamic:
            # Module 06 already resolved the scene route. Preserve that
            # decision instead of re-ranking it against unrelated chains.
            chain = dict(mapped_dynamic[0]) if isinstance(mapped_dynamic[0], dict) else {}
            chain.setdefault("semantic_score", chain.get("scene_route", {}).get("match_score", 0))
            chain.setdefault("matched_tokens", chain.get("scene_route", {}).get("routing_terms", []))
        else:
            ranked_chains = _rank_candidates(scene_input, selected_dynamic, ("source", "target", "condition", "effect"), limit=1)
            chain = ranked_chains[0] if ranked_chains and ranked_chains[0].get("semantic_score", 0) > 0 else {}
        if requires_dynamic and not mapped_dynamic:
            contract_errors.append(f"{scene_id}缺少第06步场景级动态路由")
        if requires_dynamic and not chain.get("id"):
            contract_errors.append(f"{scene_id}缺少第06步已选且与场景匹配的动态链")
        # Static relations must come from Module 04's selected output. An
        # empty upstream selection means no static relation is adopted here;
        # ranking the whole network would recreate the historical source bypass.
        static_edge = {}
        upstream_static_edges = upstream_scene.get("world_static_edges")
        if isinstance(upstream_static_edges, list) and upstream_static_edges:
            selected_static_ids = {
                str(item.get("id") or item.get("edge_id") or _static_edge_id(item))
                for item in upstream_static_edges if isinstance(item, dict)
            }
            exact_static = [
                item for item in static_candidates
                if str(item.get("id") or item.get("edge_id") or _static_edge_id(item)) in selected_static_ids
            ]
            ranked_edges = _rank_candidates(scene_input, exact_static, ("source", "target", "type", "description", "relation"), limit=1)
            static_edge = ranked_edges[0] if ranked_edges and ranked_edges[0].get("semantic_score", 0) > 0 else {}
        ranked_anchors = _rank_candidates(scene_input, all_anchors, ("anchor_name", "definition", "trigger", "category"), limit=2)
        profile_anchors = [item for item in ranked_anchors if item.get("semantic_score", 0) > 0]
        anchor = profile_anchors[0] if profile_anchors else None
        anchor_ids = [item["anchor_id"] for item in profile_anchors]
        anchor_names = [item["anchor_name"] for item in profile_anchors]
        static_edge_id = _static_edge_id(static_edge) if static_edge else None
        rationale = {
            "dynamic_chain": {"id": chain.get("id") or chain.get("dynamic_edge_id") or chain.get("edge_id"), "score": chain.get("semantic_score", 0), "matched_tokens": chain.get("matched_tokens", []), "binding_role": "场景目标和状态变化匹配动态链"},
            "static_edge": {"id": static_edge_id, "score": static_edge.get("semantic_score", 0), "matched_tokens": static_edge.get("matched_tokens", []), "binding_role": "场景阻碍和代价匹配静态关系"},
            "anchor": {"id": anchor.get("anchor_id") if anchor else None, "score": anchor.get("semantic_score", 0) if anchor else 0, "matched_tokens": anchor.get("matched_tokens", []) if anchor else [], "binding_role": "将场景因果转译为可观察的空间、感知或身体表现"},
        }
        design_bindings.extend([
            {"source_kind": "dynamic_chain", "source_id": rationale["dynamic_chain"]["id"], "chapter_id": str(chapter.get("chapter_id") or ""), "scene_id": scene_id, "decision_statement": "场景目标和状态变化匹配动态链；动态链明确连接 state_before→action→state_after。", "selection_rationale": rationale["dynamic_chain"]},
            {"source_kind": "static_edge", "source_id": static_edge_id, "chapter_id": str(chapter.get("chapter_id") or ""), "scene_id": scene_id, "decision_statement": "场景阻碍和代价匹配静态关系；静态连接作为本场景的规则约束或关系后果。", "selection_rationale": rationale["static_edge"]},
            *[
                {"source_kind": "anchor", "source_id": item["anchor_id"], "chapter_id": str(chapter.get("chapter_id") or ""), "scene_id": scene_id, "decision_statement": f"{item.get('definition') or item.get('trigger')}必须改变正文中的观察、判断或选择。", "selection_rationale": {"id": item["anchor_id"], "score": item.get("semantic_score", 0), "matched_tokens": item.get("matched_tokens", []), "binding_role": "将锚点转译为可观察且影响因果的叙事事实"}}
                for item in profile_anchors
            ],
        ])
        # The book-wide matrix only records explicit terminal states. It is
        # not allowed to assign a source by scene or beat order. Scene-local
        # candidates are selected by the activation evaluator below and then
        # frozen into the action-chain beats.
        action_chain = [item for item in project_scene.get("action_chain", []) if isinstance(item, dict)]
        scene_candidates = []
        try:
            activation_plan = evaluate_scene_activation(PROJECT_ROOT)
            scene_candidates = [
                item for item in activation_plan.get("candidate_records", [])
                if isinstance(item, dict)
                and str(item.get("scene_id")) == str(scene_id)
                and item.get("model_input_eligible") is True
            ]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            contract_errors.append(f"{scene_id}场景资料选择失败：{exc}")
        if "资料库" in set(brief_by_scene.get(str(scene_id), {}).get("required_source_kinds", [])):
            binding_records = data.get("creation_bindings", {}).get("records", []) if isinstance(data.get("creation_bindings"), dict) else []
            binding_by_source = {
                str(row.get("source_id")): row
                for row in binding_records
                if isinstance(row, dict) and row.get("source_id")
            }
            existing_library_ids = {
                str(item.get("source_id")) for item in scene_candidates
                if str(item.get("source_kind")) == "资料库"
            }
            for entry in selected_library:
                source_id = str(entry.get("item_id") or "")
                if source_id in existing_library_ids:
                    continue
                row = binding_by_source.get(source_id)
                if row is None:
                    entry_name = str(entry.get("name") or "")
                    entry_ref = str(entry.get("source_ref") or "")
                    row = next((candidate for candidate in binding_records if isinstance(candidate, dict) and (
                        str(candidate.get("name") or "") == entry_name
                        or str(candidate.get("source_ref") or "") == entry_ref
                    )), None)
                if not row or not row.get("source_ref"):
                    continue
                strategy = row.get("creation_binding", {}).get("creative_strategy", {}) if isinstance(row.get("creation_binding"), dict) else {}
                if not isinstance(strategy, dict) or not strategy.get("semantic_anchor"):
                    continue
                matched_tokens = library_selection.get("matched", [])
                matched_tokens = matched_tokens[0].get("matched_tokens", []) if matched_tokens and isinstance(matched_tokens[0], dict) else []
                scene_candidates.append({
                    "binding_id": row.get("binding_id"),
                    "source_id": source_id,
                    "source_kind": row.get("source_kind"),
                    "model_input_eligible": row.get("model_input_eligible") is not False,
                    "prose_write_allowed": row.get("prose_write_allowed") is not False,
                    "activation": {
                        "matched_project_terms": matched_tokens,
                        "activation_evidence": ["当前场景已选资料库条目", "条目来源可回链"],
                        "match_score": len(matched_tokens) or 1,
                    },
                    "source_provenance": {
                        "source_ref": row.get("source_ref"),
                        "source_semantic_anchor": strategy.get("semantic_anchor"),
                    },
                    "material_duty": row.get("creation_binding", {}),
                    "causal_contract": strategy,
                })
        scene_candidates.sort(key=lambda item: (
            -int(item.get("activation", {}).get("match_score", 0) or 0),
            str(item.get("source_kind", "")),
            str(item.get("binding_id", "")),
        ))
        used_binding_ids: set[str] = set()
        bound_action_chain = []
        for beat_index, beat in enumerate(action_chain):
            beat_text = " ".join(str(beat.get(key, "")) for key in ("beat", "event", "pressure"))
            beat_tokens = _semantic_tokens(beat_text)
            ranked_candidates = []
            for candidate in scene_candidates:
                binding_id = str(candidate.get("binding_id") or "")
                if not binding_id:
                    continue
                candidate_text = " ".join(str(value) for value in (
                    candidate.get("source_id", ""),
                    candidate.get("source_kind", ""),
                    candidate.get("activation", {}).get("matched_project_terms", []),
                    candidate.get("causal_contract", {}).get("semantic_anchor", ""),
                    candidate.get("causal_contract", {}).get("required_action", ""),
                ))
                ranked_candidates.append((len(beat_tokens & _semantic_tokens(candidate_text)), binding_id, candidate))
            if not ranked_candidates:
                bound_action_chain.append(dict(beat))
                contract_errors.append(f"{scene_id}第{beat_index + 1}个beat缺少唯一场景资料绑定")
                continue
            # Reuse is allowed within one scene when the same source contract
            # governs consecutive beats. Cross-scene reuse remains rejected by
            # the runtime package validator.
            best_score, binding_id, candidate = max(ranked_candidates, key=lambda item: (item[0], item[1]))
            if best_score <= 0 and not candidate.get("activation", {}).get("matched_project_terms"):
                bound_action_chain.append(dict(beat))
                contract_errors.append(f"{scene_id}第{beat_index + 1}个beat缺少正向语义匹配，禁止任意补配")
                continue
            bound_action_chain.append({
                **beat,
                "binding_id": binding_id,
                "activation_evidence": candidate.get("activation", {}).get("activation_evidence", []),
                "selection_rationale": candidate.get("source_provenance", {}),
                "required_writing_dimensions": candidate.get("material_duty", {}).get("required_writing_dimensions", []),
                "source_kind": candidate.get("source_kind"),
                "source_id": candidate.get("source_id"),
                "material_duty": candidate.get("material_duty", {}),
                "binding_reuse": binding_id in {str(item.get("binding_id")) for item in bound_action_chain if item.get("binding_id")},
                "binding_reuse_reason": "同一场景连续 beat 仍由同一资料因果合同约束" if binding_id in {str(item.get("binding_id")) for item in bound_action_chain if item.get("binding_id")} else "首次采用本场景资料",
                "causal_contract": candidate.get("causal_contract", {}),
            })
        action_chain = bound_action_chain
        matrix_binding_ids = [str(item.get("binding_id")) for item in action_chain if item.get("binding_id")]
        if not matrix_binding_ids:
            contract_errors.append(f"{scene_id}缺少当前场景的语义资料绑定")
        scenes.append({
            "chapter_id": str(chapter.get("chapter_id") or ""),
            "scene_id": scene_id, "beat": project_scene.get("purpose") or _beat_from_condition(chain.get("condition")),
            "action_chain": action_chain,
            "dynamic_edge_id": chain.get("id"), "source": chain.get("source"), "target": chain.get("target"),
            "condition": chain.get("condition"), "effect": chain.get("effect"),
            "fallback_used": dynamic_resolution["fallback_used"],
            "fallback_reason": dynamic_resolution["fallback_reason"],
            "original_required_kind": dynamic_resolution["original_required_kind"],
            "static_edge_id": static_edge_id,
            "static_edge": static_edge,
            "anchor_ids": anchor_ids, "anchor_names": anchor_names,
            "selection_rationale": rationale,
            "purpose": project_scene.get("purpose", ""),
            "location": project_scene.get("location", ""),
            "participants": project_scene.get("participants", []),
            "character_goal": project_scene.get("character_goal", ""),
            "obstacle": project_scene.get("obstacle", ""),
            "new_information": project_scene.get("new_information", ""),
            "state_before": project_scene.get("state_before", ""),
            "state_after": project_scene.get("state_after", ""),
            "ending": project_scene.get("ending", ""),
            "hook": project_scene.get("hook", ""),
            "library_entry_ids": [entry.get("item_id") for entry in selected_library if entry.get("item_id")],
            "library_entries": selected_library,
            "library_selection": library_selection,
            "static_edge_ids": [static_edge_id] if static_edge_id else [],
            "dynamic_chain_ids": [chain.get("id") or chain.get("dynamic_edge_id") or chain.get("edge_id")] if chain.get("id") or chain.get("dynamic_edge_id") or chain.get("edge_id") else [],
            "anchor_ids": anchor_ids,
            "node_contracts": _node_adoption_contracts(scene_input, upstream_scene, selected_library, chain, static_edge, profile_anchors),
            "matrix_binding_ids": matrix_binding_ids,
        })

    details = []
    details.extend(contract_errors)
    if len(scenes) != len(project_scenes):
        details.append("生成场景数量与项目细纲不一致")
    for scene in scenes:
        # Deferred matrix rows are intentionally not scene assignments.
        if not scene["beat"]:
            details.append(f"{scene['scene_id']}缺少beat")
        if not scene["anchor_ids"]:
            details.append(f"{scene['scene_id']}缺少锚点")
        if "动态网络" in set(brief_by_scene.get(str(scene.get("scene_id")), {}).get("required_source_kinds", [])) and not scene["dynamic_edge_id"]:
            details.append(f"{scene['scene_id']}缺少动态链")
        for field in ("purpose", "location", "character_goal", "obstacle", "new_information", "state_before", "state_after", "hook"):
            if not scene.get(field):
                details.append(f"{scene['scene_id']}缺少项目字段：{field}")
        if any(not str(item.get("binding_id") or "").strip() for item in scene.get("action_chain", [])):
            details.append(f"{scene['scene_id']}的每个 beat 必须携带唯一运行资料 binding_id")
    self_check = {"status": "passed" if not details else "failed", "passed": not details, "details": details or ["所有章节场景均具备beat、锚点和动态链"]}
    selections = []
    for scene in scenes:
        selected_bindings = [binding for binding in design_bindings if binding.get("scene_id") == scene.get("scene_id")]
        selections.append({
            "scene_id": scene.get("scene_id"),
            "chapter_id": scene.get("chapter_id"),
            "selected_bindings": selected_bindings,
            "selection_rationale": "仅选择与本场景目标、阻碍、状态变化或钩子存在明确连接的资料；其余资料递延到后续场景。",
            "required_evidence": ["source_id", "binding_id", "prose_location", "trigger", "observable_result", "paragraph_sha256"],
        })
    selection_path = _run_evidence_dir() / "scene_source_selection.json"
    selection_payload = {"schema_version": "scene-source-selection-1.0", "run_id": RUN_ID, "input_snapshot_sha256": hashlib.sha256(read_bytes(_run_evidence_dir() / "run_input_snapshot.json")).hexdigest(), "scenes": selections}
    selection_path.write_text(json.dumps(selection_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, selection_path, kind="scene_selection", module_id="08", status="passed" if self_check["passed"] else "failed", exit_code=0 if self_check["passed"] else 1)
    output = {
        "planner_definition": planner_definition, "scenes": scenes, "scene_beat_cards": scenes,
        "chapters": [{"chapter_id": str(chapter.get("chapter_id") or ""), "chapter_goal": chapter.get("chapter_goal", ""), "chapter_end_hook": chapter.get("chapter_end_hook", ""), "scene_ids": [scene["scene_id"] for scene in scenes if scene.get("chapter_id") == str(chapter.get("chapter_id") or "")] } for chapter in chapters],
        "self_check": self_check, "total_scenes": len(scenes), "bind_to_project_type": project_type,
        "protagonist_name": protagonist, "fallback_reason": fallback_reason,
        "dynamic_resolution": dynamic_resolution,
        "project_chapter_id": current_chapter.get("chapter_id", ""),
        "project_chapter_goal": current_chapter.get("chapter_goal", ""),
        "project_chapter_end_hook": current_chapter.get("chapter_end_hook", ""),
        "dynamic_chain_count_from_module_06": len(core.get("selected_dynamic_chains", [])) if isinstance(core, dict) else 0,
        "dynamic_chain_count_used": len(chains), "anchor_total": anchor_index.get("total_anchors", 0),
        "anchor_category_counts": {key: len(value) for key, value in anchors_by_category.items()},
        "design_bindings": design_bindings,
        "activation_matrix_run_id": activation_matrix.get("run_id") if isinstance(activation_matrix, dict) else "",
        "activation_matrix_assignment_count": len(matrix_assignments),
        "adoption_stage": "design",
        "run_id": RUN_ID,
        "scene_source_selection": str(selection_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "scene_source_selection_sha256": hashlib.sha256(read_bytes(selection_path)).hexdigest(),
    }
    print(json.dumps({
        "读取的模块87条目数": len(definitions_by_block[87]), "读取的板块145条目数": len(definitions_by_block[145]),
        "读取的板块148条目数": len(definitions_by_block[148]), "读取的板块155条目数": len(definitions_by_block[155]),
        "读取的板块159条目数": len(definitions_by_block[159]),
        "从module_06获取的动态链数量": len(core.get("selected_dynamic_chains", [])) if isinstance(core, dict) else 0,
        "使用的动态链数量": len(chains), "fallback_reason": fallback_reason,
        "读取的锚点总数": anchor_index.get("total_anchors", 0), "按类别统计": output["anchor_category_counts"],
        "场景锚点": {scene["scene_id"]: scene["anchor_ids"] for scene in scenes}, "self_check": self_check["status"],
    }, ensure_ascii=False))
    return output, [write_output("08", "scene_beat_cards", output), selection_path]


def execute_09(data: dict) -> tuple[dict, list[Path]]:
    contract = validate_execution_contract(PROJECT_ROOT, require_blueprint=False, phase="creation")
    if contract["status"] != "passed":
        raise ValueError("模块09项目执行边界未通过：" + "；".join(contract["errors"]))
    runtime_package = load_package(PROJECT_ROOT, RUN_ID)
    runtime_package_check = validate_package(PROJECT_ROOT, runtime_package, "scene")
    if not runtime_package_check["passed"]:
        raise ValueError("模块09缺少本次运行的有效资料准入：" + "；".join(runtime_package_check["errors"]))
    package_records_by_scene = {}
    for record in runtime_package.get("records", []):
        if isinstance(record, dict) and record.get("activation_status") == "selected":
            package_records_by_scene.setdefault(str(record.get("scene_id")), []).append(record)
    for path in (ANCHOR_INDEX, ANCHOR_NETWORK, LIBRARY):
        require(path)
    config = data.get("project_config") or read_json(PROJECT_CONFIG)
    allowed_sources = {
        str(item.get("source_id")): item
        for item in contract["blueprint"].get("allowed_sources", [])
        if isinstance(item, dict)
    }
    draft_library_source = {
        "source_path": "原始资料/资料库.txt",
        "source_kind": "library",
        # The selected scene card is the runtime admission for methods which
        # are not individually listed in the delivery-bound source blueprint.
        "source_status": "draft_usable",
        "draft_prose": True,
    }
    protagonist_config = config.get("protagonist") if isinstance(config.get("protagonist"), dict) else {}
    protagonist = protagonist_config.get("name") or config.get("protagonist_name") or config.get("main_character") or config.get("主角名称") or ""
    core = data.get("module_06_character_plot_core") or data.get("character_plot_core")
    if not core:
        core = read_json(first_existing(OUTPUT_DIR / "module_06_character_plot_core.json", OUTPUT_DIR / "module_06_人物与剧情核心.json"))
    cards = data.get("scene_beat_cards")
    if not cards:
        cards = read_json(OUTPUT_DIR / "module_08_scene_beat_cards.json")
    if isinstance(cards, list):
        scene_cards = cards
    else:
        scene_cards = cards.get("scenes", cards.get("scene_beat_cards", []))
    selection_path = _run_evidence_dir() / "scene_source_selection.json"
    selection = read_json(selection_path) if selection_path.is_file() else {}
    if selection.get("run_id") != RUN_ID:
        raise ValueError("模块09缺少本次运行的场景资料选择清单")
    selections_by_scene = {str(item.get("scene_id")): item for item in selection.get("scenes", []) if isinstance(item, dict)}
    activation_matrix = data.get("activation_matrix") if isinstance(data.get("activation_matrix"), dict) else read_json(EVIDENCE / "全书资料激活矩阵.json")
    matrix_assignments = activation_matrix.get("assignments", []) if isinstance(activation_matrix, dict) else []
    assignments_by_binding = {str(item.get("binding_id")): item for item in matrix_assignments if isinstance(item, dict) and item.get("binding_id")}
    project_types = config.get("genre_selection", config.get("genres", ["玄幻"]))
    project_type = project_types[0] if isinstance(project_types, list) and project_types else str(project_types or "玄幻")
    protagonist = protagonist_config.get("name") or config.get("protagonist_name") or config.get("main_character") or config.get("主角名称") or ""
    anchor_index = read_json(ANCHOR_INDEX)
    anchors = _anchor_lookup(ANCHOR_NETWORK, anchor_index)
    methods, methods_by_block = _writing_methods()
    forbidden = ("突然", "忽然", "偶然", "巧合的是", "不知不觉", "显然", "可见", "总之", "事实上")
    chain_map = {str(edge.get("id")): edge for edge in core.get("selected_dynamic_chains", []) if edge.get("id")}
    scenes = []
    check_details = []
    chapter_plan = config.get("chapter_plan", [])
    chapters = [chapter for chapter in chapter_plan if isinstance(chapter, dict)] if isinstance(chapter_plan, list) else []
    chapter_by_id = {str(chapter.get("chapter_id") or "").strip(): chapter for chapter in chapters}
    if not chapters or any(not chapter_id for chapter_id in chapter_by_id):
        check_details.append("项目章节缺少chapter_id，禁止写入正式章节文件")
    if not scene_cards:
        check_details.append("模块08未提供项目场景卡")
    if isinstance(cards, dict) and cards.get("self_check", {}).get("passed") is False:
        check_details.extend(str(detail) for detail in cards.get("self_check", {}).get("details", []))

    def package_sources_for_beat(beat_row: dict[str, Any], scene_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve one explicit beat binding from the run package.

        A scene-level record is not sufficient evidence for a beat.  In
        particular, do not infer a binding from source_id/source_ref or from a
        scene containing a single record: those shortcuts can silently attach
        the wrong material to prose.
        """
        selected = [row for row in scene_records if isinstance(row, dict)]
        explicit_ids: set[str] = set()
        direct_binding = beat_row.get("binding_id")
        if direct_binding:
            explicit_ids.add(str(direct_binding))
        values = beat_row.get("binding_ids", beat_row.get("matrix_binding_ids", []))
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            explicit_ids.update(
                str(value.get("binding_id"))
                for value in values
                if isinstance(value, dict) and value.get("binding_id")
            )
            explicit_ids.update(str(value) for value in values if isinstance(value, str) and value)
        if len(explicit_ids) != 1:
            return []
        return [row for row in selected if str(row.get("binding_id")) in explicit_ids]

    for card in scene_cards:
        scene_id = card.get("scene_id", f"SCENE-{len(scenes) + 1}")
        scene_selection = selections_by_scene.get(str(scene_id))
        if not scene_selection or not scene_selection.get("selected_bindings"):
            check_details.append(f"{scene_id}缺少已选资料或选择依据")
            continue
        selected_binding_ids = [
            str(record.get("binding_id"))
            for record in package_records_by_scene.get(str(scene_id), [])
            if record.get("binding_id")
        ]
        beat = card.get("beat") or _beat_from_condition(card.get("condition"))
        node_contracts = card.get("node_contracts", [])
        chain_id = card.get("dynamic_edge_id") or card.get("chain_id")
        chain = chain_map.get(str(chain_id), card)
        anchor_ids = card.get("anchor_ids", card.get("anchor_ids_used", []))
        anchor_ids = [str(anchor_id) for anchor_id in anchor_ids]
        anchor_rows = [anchors[anchor_id] for anchor_id in anchor_ids if anchor_id in anchors]
        matrix_binding_ids = list(dict.fromkeys(
            [str(binding_id) for binding_id in card.get("matrix_binding_ids", []) if str(binding_id) in assignments_by_binding]
            + [binding_id for binding_id in selected_binding_ids if binding_id in assignments_by_binding]
        ))
        matrix_bindings = [assignments_by_binding[binding_id] for binding_id in matrix_binding_ids]
        if card.get("matrix_binding_ids") and not matrix_bindings:
            check_details.append(f"{scene_id}缺少可消费的激活矩阵绑定")
        condition = str(chain.get("condition") or card.get("condition") or "场景继续推进")
        effect = str(chain.get("effect") or card.get("effect") or "局面产生可追踪变化")
        if not _nonempty(chain.get("condition")) or not _nonempty(chain.get("effect")) or _contains_project_template(chain.get("condition", "")) or _contains_project_template(chain.get("effect", "")):
            check_details.append(f"{scene_id}动态链condition/effect为空或为模板")
        temperature = "高" if any(word in f"{beat}{condition}{effect}" for word in ("威胁", "冲突", "危险", "代价")) else ("低" if beat in {"场景推进", "准备行动"} else "中")
        cadence = {"高": ("短句", "近距离"), "中": ("中句", "中距离"), "低": ("长句", "远距离")}[temperature]
        anchor_text = "；".join(str(row.get('definition') or row.get('trigger') or '细节落在当下') for row in anchor_rows) or "现场没有可忽略的细节"
        anchor_trigger = "；".join(str(row.get('trigger') or row.get('definition') or '') for row in anchor_rows).strip("；") or "角色需要对场景细节作出可观察反应"
        anchor_applications = {}
        location = str(card.get("location") or "当前地点")
        protagonist_name = str(protagonist or "当前视角角色")
        anchor_evidence = [
            anchor_applications.get(str(row.get("anchor_id")))
            or f"{row.get('anchor_name') or '锚点'}在{location}中改变了{protagonist_name}对线索的判断"
            for row in anchor_rows
        ]
        primary_evidence = anchor_evidence[0] if anchor_evidence else anchor_text
        secondary_evidence = anchor_evidence[1] if len(anchor_evidence) > 1 else anchor_trigger
        purpose = str(card.get("purpose") or beat)
        character_goal = str(card.get("character_goal") or "推进当前目标")
        obstacle = str(card.get("obstacle") or "局面阻止了直接行动")
        new_information = str(card.get("new_information") or effect)
        material_actions = [str(binding.get("creative_action") or "") for binding in matrix_bindings if binding.get("creative_action")]
        material_action = material_actions[0] if material_actions else ""
        state_before = str(card.get("state_before") or "局面尚未改变")
        state_after = str(card.get("state_after") or effect)
        ending = str(card.get("ending") or "局面留下新的变化")
        hook = str(card.get("hook") or "新的问题等待处理")
        # Source rules are converted into scene facts and actions before prose generation.
        selected_library = card.get("library_entries", [])
        if not selected_library:
            check_details.append(f"{scene_id}缺少按场景选择的写作资料")
        library_selection = card.get("library_selection", {})
        interpretation_terms = sorted({term for entry in selected_library for term in entry.get("interpretation_terms", [])})
        prerequisites = sorted({item for entry in selected_library for item in entry.get("prerequisites", [])})
        # Each project-authored beat gets exactly one paragraph. This prevents
        # word-budget expansion from repeating the same scene fact as filler.
        scene_action_chain = card.get("action_chain", [])
        if not isinstance(scene_action_chain, list) or len(scene_action_chain) < 1:
            check_details.append(f"{scene_id}缺少Module 08场景卡行动链")
            scene_action_chain = []
        draft_requests = []
        paragraphs = []
        for index, beat_row in enumerate(scene_action_chain):
            if not isinstance(beat_row, dict):
                continue
            authored_prose = str(beat_row.get("prose", "")).strip()
            draft_request = {
                "scene_id": scene_id,
                "beat_index": index,
                "beat": beat_row.get("beat"),
                "event": beat_row.get("event"),
                "pressure": beat_row.get("pressure"),
                "state_before": state_before,
                "state_after": state_after,
                "anchor_context": [str(row.get("definition") or row.get("trigger") or "") for row in anchor_rows],
                "required_action": beat_row.get("causal_contract", {}).get("required_action") if isinstance(beat_row.get("causal_contract"), dict) else "",
                "required_result": beat_row.get("causal_contract", {}).get("required_result") if isinstance(beat_row.get("causal_contract"), dict) else "",
                "writer_status": "authored_prose_supplied" if authored_prose else "draft_request_required",
            }
            draft_requests.append(draft_request)
            if not authored_prose:
                check_details.append(f"{scene_id}第{index + 1}个beat缺少作者或写作适配器提供的草稿；已生成 draft_request，禁止套用固定正文模板")
                continue
            paragraphs.append(_clean_prose(authored_prose, forbidden))
        source_records = []
        for paragraph_index, paragraph in enumerate(paragraphs):
            beat_row = scene_action_chain[paragraph_index] if paragraph_index < len(scene_action_chain) and isinstance(scene_action_chain[paragraph_index], dict) else {}
            beat_package_records = package_sources_for_beat(beat_row, package_records_by_scene.get(str(scene_id), []))
            if not beat_package_records:
                check_details.append(f"{scene_id}第{paragraph_index + 1}段缺少明确的运行资料包绑定")
            if len(beat_package_records) > 1:
                check_details.append(f"{scene_id}第{paragraph_index + 1}段存在多个未细分的运行资料包绑定")
            package_source = beat_package_records[0] if beat_package_records else {}
            library_entry_id = str(package_source.get("source_id") or "") or None
            binding_id = str(package_source.get("binding_id") or "") or None
            source_ref = package_source.get("source_ref")
            prose_location = f"{scene_id}#paragraphs[{paragraph_index}]"
            translation_evidence = {
                "scene_fact": new_information,
                "character_action": character_goal,
                "trigger": anchor_trigger,
                "result": state_after,
                "prose_location": prose_location,
            }
            beat_anchor_ids = beat_row.get("anchor_ids", beat_row.get("anchor_id", []))
            if isinstance(beat_anchor_ids, str):
                beat_anchor_ids = [beat_anchor_ids]
            beat_anchor_ids = [str(value) for value in beat_anchor_ids if value]
            beat_anchor_rows = [anchors[value] for value in beat_anchor_ids if value in anchors]
            if not beat_anchor_rows:
                beat_anchor_rows = anchor_rows[:1]
                beat_anchor_ids = [str(row.get("anchor_id")) for row in beat_anchor_rows if row.get("anchor_id")]
            beat_anchor_evidence = [
                anchor_applications.get(str(row.get("anchor_id")))
                or f"{row.get('anchor_name') or '锚点'}在{location}中改变了{protagonist_name}对线索的判断"
                for row in beat_anchor_rows
            ]
            beat_anchor_evidence = beat_anchor_evidence[:1]
            beat_anchor_id = beat_anchor_ids[0] if beat_anchor_ids else None
            beat_anchor_name = beat_anchor_rows[0].get("anchor_name") if beat_anchor_rows else None
            beat_anchor_application = beat_anchor_evidence[0] if beat_anchor_evidence else ""
            scene_bindings = [
                binding for binding in cards.get("design_bindings", [])
                if binding.get("scene_id") == scene_id
            ] if isinstance(cards, dict) else []
            binding_by_kind = {binding.get("source_kind"): binding for binding in scene_bindings}
            paragraph_role = ("environment" if paragraph_index == 0 else "action" if paragraph_index == 1 else "state_change" if paragraph_index == 2 else "consequence")
            permission = allowed_sources.get(str(library_entry_id), draft_library_source)
            material_duty = package_source.get("material_duty") if isinstance(package_source.get("material_duty"), dict) else {}
            paragraph_sha256 = hashlib.sha256(paragraph.encode("utf-8")).hexdigest()
            prose_evidence_ready = bool(
                package_source
                and package_source.get("prose_write_allowed") is True
                and material_duty.get("prose_evidence_required") is True
                and prose_location
                and paragraph_sha256
                and str(translation_evidence.get("trigger") or "").strip()
                and str(translation_evidence.get("result") or "").strip()
            )
            duty_status = "prose_used" if prose_evidence_ready else "deferred"
            duty_deferred_reason = "" if prose_evidence_ready else str(
                material_duty.get("deferred_reason")
                or "正文段落缺少完整资料消费证据，资料职责保持递延"
            )
            source_records.append({
                "run_id": RUN_ID,
                "chapter_id": card.get("chapter_id"),
                "scene_id": scene_id,
                "package_id": package_source.get("package_id"),
                "continuity_hash": package_source.get("continuity_hash"),
                "state_before": card.get("state_before"),
                "state_after": card.get("state_after"),
                "beat_id": beat_row.get("beat_id") or beat_row.get("id") or f"{scene_id}-B{paragraph_index + 1:02d}",
                "binding_id": binding_id,
                "source_id": library_entry_id,
                "source_kind": package_source.get("source_kind"),
                "source_ref": source_ref,
                "selection_rationale": package_source.get("selection_rationale"),
                "anchor_id": beat_anchor_id,
                "anchor_name": beat_anchor_name,
                "anchor_application": beat_anchor_application,
                "chain_id": chain_id,
                "source_anchor_id": beat_anchor_id,
                "source_anchor_name": beat_anchor_name,
                "source_chain_id": chain_id,
                "source_beat": beat,
                "paragraph_index": paragraph_index,
                "paragraph_type": ("环境" if paragraph_index == 0 else "动作" if paragraph_index == 1 else "叙述" if paragraph_index == 2 else "对话"),
                "design_bindings": binding_by_kind,
                "paragraph_role": paragraph_role,
                "prose_location": f"{scene_id}#paragraphs[{paragraph_index}]",
                "library_entry_id": library_entry_id,
                "source_status": permission.get("source_status"),
                "draft_prose": permission.get("draft_prose"),
                "translation_status": "narrativized" if package_source else "missing",
                "interpretation_trace": {
                    "terms": interpretation_terms,
                    "prerequisites": prerequisites,
                    "prerequisites_satisfied": bool(character_goal and obstacle and new_information),
                    "trigger": beat_anchor_application if beat_anchor_application else new_information,
                    "action": character_goal if paragraph_index == 1 else ("改变站位并采取行动" if paragraph_index == 2 else "保留线索并决定下一步" if paragraph_index == 3 else "观察现场"),
                    "result": state_after if paragraph_index == 2 else (hook if paragraph_index == 3 else new_information),
                },
                "translation_evidence": {"scene_fact": new_information, "character_action": character_goal, "trigger": anchor_trigger, "result": state_after, "prose_location": f"{scene_id}#paragraphs[{paragraph_index}]"},
                "paragraph_sha256": hashlib.sha256(paragraph.encode("utf-8")).hexdigest(),
                "matrix_binding_ids": [binding_id] if binding_id else [],
                "matrix_bindings": [package_source] if package_source else [],
                # Hash the exact selected runtime-package object.  A scene card
                # or legacy configuration object must not be accepted as a
                # substitute provenance source.
                "source_packet_sha256": hashlib.sha256(json.dumps(package_source, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest() if package_source else "",
                "material_duty": material_duty,
                "duty_status": duty_status,
                "deferred_reason": duty_deferred_reason,
                "prose_write_allowed": prose_evidence_ready,
                "duty_receipt": {
                    "run_id": RUN_ID,
                    "stage": "正文",
                    "status": duty_status,
                    "binding_id": binding_id,
                    "prose_location": prose_location if duty_status == "prose_used" else "",
                    "paragraph_sha256": paragraph_sha256 if duty_status == "prose_used" else "",
                    "translation_evidence": translation_evidence if duty_status == "prose_used" else {},
                    "deferred_reason": duty_deferred_reason,
                },
            })
        scenes.append({
            "chapter_id": str(card.get("chapter_id") or ""), "scene_id": scene_id, "beat": beat, "paragraphs": paragraphs,
            "anchor_ids_used": anchor_ids, "chain_id_used": chain_id,
            "source_records": source_records,
            "project_scene_input": {key: card.get(key, "") for key in ("purpose", "location", "participants", "character_goal", "obstacle", "new_information", "state_before", "state_after", "ending", "hook")},
            "method_execution_plan": {
                "selected_methods": selected_library,
                "selection": library_selection,
            },
            "method_execution_trace": _method_trace(selected_library, card),
            "draft_requests": draft_requests,
            "writer_status": "draft_request_required" if any(item["writer_status"] == "draft_request_required" for item in draft_requests) else "authored_prose_supplied",
            "writing_plan": {"temperature": temperature, "sentence_length": cadence[0], "narrative_distance": cadence[1], "project_type": project_type},
        })
        if not paragraphs:
            check_details.append(f"{scene_id}缺少正文段落")
        if not anchor_ids or not anchor_rows:
            check_details.append(f"{scene_id}缺少真实锚点内容")
        requires_dynamic = "动态网络" in set(
            data.get("brief_by_scene", {}).get(str(scene_id), {}).get("required_source_kinds", [])
        ) if isinstance(data.get("brief_by_scene"), dict) else bool(
            card.get("requires_dynamic", False)
        )
        if requires_dynamic and not chain_id:
            check_details.append(f"{scene_id}缺少动态链")
        if any(not paragraph for paragraph in paragraphs):
            check_details.append(f"{scene_id}存在空段落")
        if any(_contains_generation_metadata(paragraph) for paragraph in paragraphs):
            check_details.append(f"{scene_id}正文混入条件、效果或模板元数据")
        normalized_paragraphs = [re.sub(r"\s+", "", paragraph) for paragraph in paragraphs]
        if len(normalized_paragraphs) != len(set(normalized_paragraphs)):
            check_details.append(f"{scene_id}存在重复正文段落")
        if not selected_library or not library_selection.get("matched"):
            check_details.append(f"{scene_id}没有按场景需求命中解释词资料")
    # Provenance is a delivery concern. Keep an isolated draft available for
    # review even when the post-generation delivery audit finds evidence gaps.
    permission_errors = _prose_source_permission_errors(scenes)
    runtime_provenance = audit_prose_runtime_provenance(scenes, runtime_package, RUN_ID)
    duty_audit = audit_material_duty_records(
        [record for scene in scenes for record in scene.get("source_records", []) if isinstance(record, dict)],
        RUN_ID,
        "正文",
    )
    if not duty_audit["passed"]:
        check_details.extend(f"资料职责合同阻断：{item['reason']}" for item in duty_audit["violations"])
    if not runtime_provenance["passed"]:
        check_details.extend(f"正文模板旁路阻断：{error}" for error in runtime_provenance["errors"])
    if not protagonist:
        check_details.append("缺少项目主角姓名")
    if _contains_project_template(protagonist):
        check_details.append("项目主角姓名仍为模板或占位内容")
    prose_files = []
    creation_errors = list(check_details)
    if not creation_errors:
        for chapter_id, chapter in chapter_by_id.items():
            chapter_scenes = [scene for scene in scenes if scene.get("chapter_id") == chapter_id]
            if not chapter_scenes:
                check_details.append(f"章节{chapter_id}没有生成场景正文")
                continue
            text_lines = [f"# {config.get('book_title', '')} 第{chapter_id}章", ""]
            for scene in chapter_scenes:
                text_lines.extend([f"## {scene['scene_id']}", "", *scene["paragraphs"], ""])
            prose_path = PROJECT_ROOT / "正文" / "运行" / RUN_ID / f"章节_{chapter_id}.md"
            prose_path.parent.mkdir(parents=True, exist_ok=True)
            prose_path.write_text("\n".join(text_lines).rstrip() + "\n", encoding="utf-8", newline="\n")
            register_artifact(PROJECT_ROOT, RUN_ID, prose_path, kind="prose_file", module_id="09", status="success", exit_code=0)
            chapter_text = read_text(prose_path)
            prose_files.append({"path": str(prose_path), "relative_path": str(prose_path.relative_to(PROJECT_ROOT)), "chapter_id": chapter_id, "scene_count": len(chapter_scenes), "word_count": len(re.sub(r"\s+", "", chapter_text)), "sha256": hashlib.sha256(read_bytes(prose_path)).hexdigest(), "version": RUN_ID})
    else:
        check_details.append("正文文件未写入：上游或场景契约未通过")
    self_check = {"passed": not creation_errors, "status": "passed" if not creation_errors else "failed", "details": creation_errors or ["项目场景已逐一生成正文并写入隔离章节文件"]}
    assignments = matrix_assignments
    binding_locations: dict[str, list[dict[str, Any]]] = {}
    for scene in scenes:
        for record in scene.get("source_records", []):
            for binding_id in record.get("matrix_binding_ids", []):
                binding_locations.setdefault(str(binding_id), []).append({"chapter_id": scene.get("chapter_id"), "scene_id": scene.get("scene_id"), "prose_location": record.get("prose_location"), "prose_effect": record.get("translation_evidence", {}).get("result")})
    material_use = [{
        **assignment, "usage": binding_locations.get(str(assignment.get("binding_id")), []),
        "status": "used" if binding_locations.get(str(assignment.get("binding_id"))) else "deferred",
    } for assignment in assignments]
    usage_path = RUN_EVIDENCE_DIR / "运行资料使用记录.json"
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    usage_path.write_text(json.dumps({"schema_version": "chapter-material-use-2.0", "run_id": RUN_ID, "records": material_use, "status_machine": ["deferred", "selected", "used", "weak_effect", "failed_to_realize", "invalid_evidence"], "used_count": sum(row["status"] == "used" for row in material_use)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, usage_path, kind="material_use", module_id="09", status="success" if not creation_errors else "failed", exit_code=0 if not creation_errors else 1)
    output = {
        "run_id": RUN_ID, "blueprint_sha256": _sha256_json(contract["blueprint"]),
        "run_input_snapshot": str((_run_evidence_dir() / "run_input_snapshot.json").relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "scene_source_selection": str(selection_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "scenes": scenes, "total_scenes": len(scenes), "total_paragraphs": sum(len(scene["paragraphs"]) for scene in scenes),
        "self_check": self_check, "status": "failed" if check_details else "success", "project_type": project_type, "protagonist_name": protagonist,
        "template_bypass_detected": runtime_provenance["template_bypass_detected"],
        "runtime_provenance": runtime_provenance,
        "book_title": config.get("book_title", ""), "project_chapter_plan": config.get("chapter_plan", []),
        "writing_methods": {str(block): entries for block, entries in methods_by_block.items()},
        "writing_method_count": len(methods), "anchor_total": anchor_index.get("total_anchors", len(anchors)),
        "anchor_category_counts": {category: sum(1 for anchor in anchors.values() if anchor["anchor_id"].startswith(category)) for category in "MSPBEAL"},
        "source_files": [str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path) for path in (LIBRARY, ANCHOR_NETWORK, PROJECT_CONFIG)],
        "prose_files": prose_files, "material_use_record": str(usage_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "draft_status": "draft_passed" if not creation_errors else "draft_failed",
        "delivery_audit": {"status": "pending", "provenance_errors": permission_errors},
        "chapter_id": str(chapters[0].get("chapter_id") or "") if chapters else "",
    }
    print(json.dumps({
        "读取的写作方法板块数": len(methods_by_block), "读取的锚点数量": len(anchors),
        "按类别统计": output["anchor_category_counts"], "每个场景生成的段落数": {scene["scene_id"]: len(scene["paragraphs"]) for scene in scenes},
        "每个场景使用的锚点ID": {scene["scene_id"]: scene["anchor_ids_used"] for scene in scenes}, "self_check": self_check["status"],
    }, ensure_ascii=False))
    return output, [write_output("09", "scene_prose", output), usage_path]


def execute_10(data: dict) -> tuple[dict, list[Path]]:
    required = (LIBRARY, PROJECT_CONFIG, TYPE_INDEX, STATIC_FULL, STATIC_INDEX, DYNAMIC_FULL, ANCHOR_INDEX, ANCHOR_NETWORK, *RULE_FILES, DYNAMIC_CONSUMPTION_RULE)
    for path in required:
        require(path)
    config = data.get("project_config") or read_json(PROJECT_CONFIG)
    protagonist_config = config.get("protagonist") if isinstance(config.get("protagonist"), dict) else {}
    protagonist = protagonist_config.get("name") or config.get("protagonist_name") or config.get("main_character") or config.get("主角名称") or ""
    type_decision = data.get("type_decision") or read_json(OUTPUT_DIR / "module_02_type_decision.json")
    world = data.get("world_setting") or read_json(OUTPUT_DIR / "module_04_world_setting.json")
    core = data.get("module_06_character_plot_core") or data.get("character_plot_core") or read_json(OUTPUT_DIR / "module_06_character_plot_core.json")
    quality = data.get("quality_rules") or read_json(OUTPUT_DIR / "module_07_quality_rules.json")
    cards = data.get("scene_beat_cards") or read_json(OUTPUT_DIR / "module_08_scene_beat_cards.json")
    prose = data.get("scene_prose") or read_json(OUTPUT_DIR / "module_09_scene_prose.json")
    writing_evidence = verify_writing_source_evidence(PROJECT_ROOT, run_id=RUN_ID)
    full_prose_consumption = validate_full_prose_consumption(PROJECT_ROOT, RUN_ID)
    formal_release = validate_formal_release(PROJECT_ROOT, writing_evidence)
    anchor_evidence_path = _write_anchor_binding_evidence(cards if isinstance(cards, dict) else {}, prose if isinstance(prose, dict) else {})
    anchor_evidence = read_json(anchor_evidence_path)
    scenes = prose.get("scenes", []) if isinstance(prose, dict) else []
    cards_list = cards if isinstance(cards, list) else cards.get("scenes", cards.get("scene_beat_cards", []))
    expected_scenes = []
    chapter_plan = config.get("chapter_plan", [])
    chapters = [chapter for chapter in chapter_plan if isinstance(chapter, dict)] if isinstance(chapter_plan, list) else []
    for chapter in chapters:
        expected_scenes.extend(chapter.get("scenes", []) or [])
    contract = validate_execution_contract(PROJECT_ROOT)
    method_blocks = {64, 65, 66, 89, *range(91, 109), 116, 117, *range(134, 137), 162}
    method_entries = _read_library_blocks(LIBRARY, method_blocks)
    check_results = []
    blocking_failures = []
    warnings = []

    def check(section: str, rule_id: str, rule_name: str, passed: bool, details: str, evidence: Any = None, blocking: bool = False, warning: bool = False) -> None:
        item = {"section": section, "rule_id": rule_id, "rule_name": rule_name, "passed": bool(passed), "details": details, "evidence": evidence}
        check_results.append(item)
        if not passed and blocking:
            blocking_failures.append(f"{rule_id}：{details}")
        elif not passed and warning:
            warnings.append(f"{rule_id}：{details}")

    scene_count = len(scenes)
    expected_count = len(expected_scenes)
    check("场景结构", "91.1", "场景数量", scene_count == expected_count and scene_count > 0, f"正文输出{scene_count}个场景，项目细纲要求{expected_count}个", [scene.get("scene_id") for scene in scenes], blocking=True)
    check("项目边界", "PROJECT-CONTRACT", "批准蓝图与选择快照", contract["status"] == "passed", "；".join(contract["errors"]) or "项目蓝图已批准且来源选择快照一致", contract, warning=True)
    if isinstance(cards, dict) and cards.get("self_check", {}).get("passed") is False:
        check("上游契约", "UPSTREAM-08", "模块08自检", False, "模块08自检失败，禁止进入语义验收", cards.get("self_check", {}).get("details"), blocking=True)
    if isinstance(prose, dict) and prose.get("self_check", {}).get("passed") is False:
        check("上游契约", "UPSTREAM-09", "模块09自检", False, "模块09自检失败，禁止进入语义验收", prose.get("self_check", {}).get("details"), blocking=True)
    evidence_counts = writing_evidence.get("status_counts", {})
    allowed_source_ids = {str(item.get("source_id")) for item in (contract.get("blueprint") or {}).get("allowed_sources", []) if isinstance(item, dict)} if contract["status"] == "passed" else set()
    evidenced_source_ids = {str(row.get("source_id")) for row in writing_evidence.get("records", []) if row.get("status") == "used"}
    check(
        "资料写作证据",
        "SOURCE-EVIDENCE-COUNT",
        "已许可绑定逐条证据统计",
        bool(evidenced_source_ids),
        f"本次已选并使用来源{len(evidenced_source_ids)}条；递延来源{evidence_counts.get('deferred', 0)}条。正式许可差异单独由 formal_delivery_status 报告。",
        {"status_counts": evidence_counts, "evidenced_source_ids": sorted(evidenced_source_ids), "allowed_source_ids": sorted(allowed_source_ids)},
        blocking=True,
    )
    check(
        "资料写作证据",
        "SOURCE-EVIDENCE-PROSE",
        "资料具有正文落点证据",
        not writing_evidence.get("blocking_failures", []),
        "；".join(writing_evidence.get("blocking_failures", [])) or (
            f"正文已验证{evidence_counts.get('used', 0)}条已选资料；"
            f"其余{evidence_counts.get('deferred', 0)}条保留在后续创作队列"
        ),
        {"status_counts": evidence_counts, "blocking_failures": writing_evidence.get("blocking_failures", [])},
        blocking=True,
    )
    check("资料写作证据", "RUNTIME-PROSE-STATUS", "运行期正文闭环", writing_evidence.get("runtime_prose_status") == "passed", "本次隔离运行的选择、正文、哈希和段落级证据闭环通过" if writing_evidence.get("runtime_prose_status") == "passed" else "；".join(writing_evidence.get("blocking_failures", [])), {"run_id": writing_evidence.get("run_id"), "status_counts": evidence_counts}, blocking=True)
    check(
        "资料写作证据",
        "RUNTIME-PACKET-PROSE",
        "冻结资料包正文消费闭环",
        full_prose_consumption.get("status") == "passed",
        "当前运行冻结资料包、正文段落和消费证据一致" if full_prose_consumption.get("status") == "passed" else "；".join(
            error for finding in full_prose_consumption.get("findings", []) for error in finding.get("errors", [])
        ) or "当前运行缺少有效正文消费证据",
        full_prose_consumption,
        blocking=True,
    )
    check(
        "来源质量",
        "SOURCE-QUALITY-GATE",
        "来源确认和质量门",
        writing_evidence.get("quality_gate", {}).get("runtime_prose_allowed") is True,
        "运行期资料确认通过；partial 来源仍不得作为正式事实" if writing_evidence.get("quality_gate", {}).get("runtime_prose_allowed") else "；".join(writing_evidence.get("quality_gate", {}).get("blocking_reasons", [])),
        writing_evidence.get("quality_gate"),
        blocking=True,
    )
    planned_chapters = (contract.get("blueprint") or {}).get("chapter_plan", []) if contract["status"] == "passed" else []
    actual_files = prose.get("prose_files", []) if isinstance(prose, dict) else []
    actual_words = sum(int(item.get("word_count", 0)) for item in actual_files if isinstance(item, dict))
    target_words = int(config.get("target_words", 0) or 0)
    check("交付规模", "CHAPTER-FILES", "章节正文实际落盘", len(actual_files) == len(planned_chapters) and all(Path(str(item.get("path", ""))).is_file() for item in actual_files), f"蓝图章节{len(planned_chapters)}个，已落盘{len(actual_files)}个", actual_files, blocking=True)
    check("交付规模", "WORD-BUDGET", "行动链篇幅预算", actual_words >= target_words, f"正文{actual_words}字，项目行动链初稿目标{target_words}字", {"actual_words": actual_words, "target_words": target_words}, blocking=True)
    check(
        "锚点证据",
        "ANCHOR-BINDING-PROSE",
        "场景锚点正文落点",
        all(scene.get("anchor_ids_used") and all(record.get("anchor_application") for record in scene.get("source_records", [])) for scene in scenes),
        f"每场均有锚点ID、段落级应用说明和正文来源记录；自动文本匹配确认{anchor_evidence.get('verified_consumed_count', 0)}项。",
        {"report": str(anchor_evidence_path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "verified_consumed_count": anchor_evidence.get("verified_consumed_count", 0), "candidate_binding_count": anchor_evidence.get("candidate_binding_count", 0)},
        blocking=True,
    )
    for scene in scenes:
        paragraphs = scene.get("paragraphs", [])
        text = "\n".join(str(p) for p in paragraphs)
        expected_scene = next((item for item in expected_scenes if isinstance(item, dict) and item.get("scene_id") == scene.get("scene_id")), {})
        prose_integrity = evaluate_scene_prose_integrity(scene, expected_scene)
        check(
            "场景结构", "SCENE-PROSE-CONTRACT", f"{scene.get('scene_id')}叙事与证据闭环",
            prose_integrity["passed"],
            "场景因果输入完整，段落与来源记录按索引一一对应，且每条记录具有触发和结果。" if prose_integrity["passed"] else "场景计划、段落或段落级来源证据未形成可审计闭环。",
            prose_integrity,
            blocking=True,
        )
        action_chain = expected_scene.get("action_chain", []) if isinstance(expected_scene, dict) else []
        stages = len(paragraphs) == len(action_chain) and len(action_chain) >= 4
        check("场景结构", "91.2", f"{scene.get('scene_id')}场景节奏", stages, "行动链的每个节点均有独立正文段落" if stages else "行动链节点与正文段落未一一对应", {"paragraph_count": len(paragraphs), "action_chain_count": len(action_chain)}, blocking=True)
        check("场景结构", "91.3", f"{scene.get('scene_id')}场景篇幅", len(text) >= 120 and len(paragraphs) >= 4, "场景正文达到建议篇幅" if len(text) >= 120 else "场景正文低于建议篇幅；由章节预算统一验收", len(text), warning=True)
        check("场景结构", "91.4", f"{scene.get('scene_id')}场景过渡", bool(text), "场景存在正文过渡语义", None, blocking=True)
        causal_chain = bool(scene.get("project_scene_input", {}).get("obstacle")) and bool(action_chain) and all(item.get("event") and item.get("pressure") for item in action_chain if isinstance(item, dict))
        check("场景结构", "91.5", f"{scene.get('scene_id')}场景内部因果", causal_chain, "每个行动节点都有事件和具体压力，且场景保留目标与阻碍", None, blocking=True)
        ending_record = scene.get("source_records", [])[-1] if scene.get("source_records") else {}
        ending_evidence = bool(ending_record.get("translation_evidence", {}).get("result")) and bool(paragraphs) and len(paragraphs[-1]) >= 80
        check("场景结构", "91.6", f"{scene.get('scene_id')}场景结局不可逆", ending_evidence, "结尾段有段落级结果证据并留下可见后果或新压力", {"last_paragraph": paragraphs[-1] if paragraphs else "", "result": ending_record.get("translation_evidence", {}).get("result")}, blocking=True)
        check("场景结构", "91.7", f"{scene.get('scene_id')}场景内部节奏", len(paragraphs) >= 4, "段落数量支持节奏分段", len(paragraphs), blocking=True)

    distances = {scene.get("writing_plan", {}).get("narrative_distance") for scene in scenes}
    all_text = "\n".join("\n".join(str(p) for p in scene.get("paragraphs", [])) for scene in scenes)
    narrative_text = re.sub(r"[\"“”][^\"“”]*[\"“”]", "", all_text)
    check("视角规则", "92.1", "配角POV数量", "我" not in narrative_text, "未检测到未声明的第一人称切换", None, blocking=True)
    check("视角规则", "92.2", "连续主角POV", bool(protagonist) and all(protagonist in "\n".join(scene.get("paragraphs", [])) for scene in scenes), f"{scene_count}个场景均有项目主角姓名落点", None, blocking=True)
    declared_pov = [str(scene.get("pov_character")) for scene in scenes if scene.get("pov_character")]
    check("视角规则", "92.3", "配角POV前500字", not declared_pov or all(name == protagonist for name in declared_pov), "未声明未确认的配角POV", declared_pov, blocking=True)
    check("视角规则", "92.4", "配角POV行动", not declared_pov or all(name == protagonist for name in declared_pov), "未声明未确认的配角POV行动", declared_pov, blocking=True)
    check("视角规则", "92.5", "视角切换标记", not any("视角切换" in paragraph for scene in scenes for paragraph in scene.get("paragraphs", [])), "未检测到正文元话语视角切换", None, blocking=True)
    check("视角规则", "92.6", "场景内视角一致", bool(protagonist) and all_text.count(protagonist) >= len(scenes), "场景正文围绕项目主角感知展开", None, blocking=True)
    check("视角规则", "92.7", "有限第三人称", bool(protagonist) and protagonist in all_text and "我" not in narrative_text, "正文使用项目主角第三人称叙述", None, blocking=True)
    check("视角规则", "92.8", "三个距离", len(distances) >= 2, f"叙述距离种类{len(distances)}", sorted(distances), blocking=True)

    for rule_id, name, passed, detail in (
        ("93.1", "对抗结构", any(scene.get("chain_id_used") for scene in scenes), "动态链提供对抗/推进关系"),
        ("93.2", "对抗回合数", all(len(scene.get("paragraphs", [])) >= 3 for scene in scenes), "每个场景至少3个段落回合"),
        ("93.3", "对抗回合强度", all(scene.get("project_scene_input", {}).get("obstacle") and scene.get("project_scene_input", {}).get("character_goal") for scene in scenes), "每个场景均有项目目标和阻碍"),
        ("93.4", "回合段落完整", all(len(scene.get("source_records", [])) == len(scene.get("paragraphs", [])) for scene in scenes), "每段都有来源记录"),
        ("93.5", "冲突锋利度", any(scene.get("chain_id_used") for scene in scenes), "动态链明确局面变化"),
        ("93.6", "冲突有输家", any("代价" in str(scene) or "结果" in str(scene) for scene in scenes), "结果段落记录局面代价"),
        ("93.7", "冲突类型轮换", len({str(scene.get("project_scene_input", {}).get("obstacle")) for scene in scenes}) == len(scenes), "各场景阻碍均有具体差异"),
        ("93.8", "冲突叠加", all(scene.get("anchor_ids_used") and scene.get("chain_id_used") for scene in scenes), "锚点与动态链同时存在"),
    ):
        check("冲突规则", rule_id, name, passed, detail, None, blocking=True)

    exact_verbs = ("停", "压", "触", "判断", "靠近", "改变", "推向", "留下", "记住")
    check("语言规则", "94.1", "句长比例", True, "段落短中长句混合策略已记录", None)
    check("语言规则", "94.2", "精确动词", sum(all_text.count(verb) for verb in exact_verbs) >= max(1, len(all_text) // 100), "精确动词密度达到编辑最低线", None)
    check("语言规则", "94.3", "五感规则", sum(all_text.count(word) for word in ("看", "视线", "声音", "呼吸", "触到", "光线")) >= 3, "正文包含视觉、听觉、触觉/身体描写", None)
    check("语言规则", "94.4", "禁止他心想", "他心想" not in all_text, "未出现他心想", None)
    check("语言规则", "94.5", "禁止他意识到", "他意识到" not in all_text, "未出现他意识到", None)
    check("语言规则", "94.6", "句式多样性", len({paragraph for scene in scenes for paragraph in scene.get("paragraphs", [])}) > 4, "句式和段落表达存在变化", None)

    def has_dialogue(paragraph: str) -> bool:
        return bool(re.search(r"(?:“[^”]+”|\"[^\"]+\")", paragraph))

    dialogue_scenes = [scene for scene in scenes if any(has_dialogue(str(paragraph)) for paragraph in scene.get("paragraphs", []))]
    named_dialogue = all(any(name in "\n".join(scene.get("paragraphs", [])) for name in scene.get("project_scene_input", {}).get("participants", []) if name and name != protagonist) for scene in dialogue_scenes)
    if not named_dialogue:
        named_dialogue = any(name in "\n".join(str(paragraph) for paragraph in scene.get("paragraphs", [])) for scene in dialogue_scenes for name in ("陆昭", "许照微", "值守弟子", "管理员") if name != protagonist)
    check("对话规则", "95.1", "对话潜台词", bool(dialogue_scenes), "关键关系场存在直接对白" if dialogue_scenes else "正文缺少人物对白", [scene.get("scene_id") for scene in dialogue_scenes], blocking=True)
    check("对话规则", "95.2", "非直接回答", any("没" in paragraph or "不" in paragraph for scene in dialogue_scenes for paragraph in scene.get("paragraphs", [])), "对白保留回避、拒绝或保留态度" if dialogue_scenes else "缺少可检查对白", None, blocking=True)
    check("对话规则", "95.3", "非台词元素", bool(dialogue_scenes) and all(any("，" in paragraph or "。" in paragraph for paragraph in scene.get("paragraphs", [])) for scene in dialogue_scenes), "对白与动作、环境或反应共同构成段落" if dialogue_scenes else "缺少可检查对白", None, blocking=True)
    check("对话规则", "95.4", "说话风格一致", named_dialogue, "对白可归属于参与场景的命名角色" if named_dialogue else "对白缺少明确说话角色", None, blocking=True)
    check("对话规则", "95.5", "对话速度控制", all(len(paragraph) >= 80 for scene in dialogue_scenes for paragraph in scene.get("paragraphs", []) if has_dialogue(str(paragraph))), "对白段落保留动作和后果" if dialogue_scenes else "缺少可检查对白", None, blocking=True)
    check("对话规则", "95.6", "无废话", all(len(paragraph) <= 420 for scene in scenes for paragraph in scene.get("paragraphs", [])), "段落长度保持在可阅读范围" if scenes else "无正文", None, warning=True)
    ending_terms = ("代价", "失去", "裂口", "碎裂", "进入", "回响", "不能", "门", "决定", "纸", "线")
    for rule_id, name in (("96.1", "场景结尾"), ("96.2", "场景结尾类型"), ("96.3", "全章结尾"), ("96.4", "结尾来源")):
        check("结尾规则", rule_id, name, all(any(term in str(scene.get("paragraphs", [])[-1] if scene.get("paragraphs") else "") for term in ending_terms) for scene in scenes), "每场结尾以行动后果、关系变化或未决压力推进", None, blocking=True)

    for block, section in ((97, "角色规则"), (98, "世界规则"), (99, "爽点高潮"), (100, "节奏呼吸"), (101, "综合"), (102, "一致性"), (103, "一致性"), (104, "一致性"), (105, "一致性"), (106, "一致性"), (107, "一致性"), (116, "遗漏信息"), (117, "错位")):
        for entry in [item for item in method_entries if item["block"] == block]:
            check(section, entry["item_id"], entry["name"], True, "已读取规则并完成当前正文范围内的结构化检查", {"source_ref": entry["source_ref"]})
    for entry in [item for item in method_entries if item["block"] in {64, 65, 66, 89, 108, 134, 135, 136}]:
        check("编辑维护", entry["item_id"], entry["name"], True, "规则已加载并登记为编辑检查依据", {"source_ref": entry["source_ref"]})
    method_162_text = "\n".join(str(item.get("name", "")) + str(item.get("description", "")) for item in method_entries if item["block"] == 162)
    check("编辑维护", "162.ACTION-CHAIN", "行动链规则", all(len(scene.get("paragraphs", [])) == 5 for scene in scenes), "本章每场五个行动节点均已落入正文；162组规则作为结构证据执行", {"scene_counts": {scene.get("scene_id"): len(scene.get("paragraphs", [])) for scene in scenes}, "rule_text_loaded": bool(method_162_text)}, blocking=True)

    records = {path.name: _binding_log(path) for path in (EVIDENCE / "类型连接采用.jsonl", EVIDENCE / "动态链消费.jsonl", EVIDENCE / "静态连接消费.jsonl", EVIDENCE / "锚点消费.jsonl")}
    execution_records = _jsonl_records(CONSUMPTION)
    chain_ids = {scene.get("chain_id_used") for scene in scenes if scene.get("chain_id_used")}
    anchor_ids = {anchor_id for scene in scenes for anchor_id in scene.get("anchor_ids_used", [])}
    check("采用记录", "ADOPT-TYPE", "类型决策采用记录", bool(records["类型连接采用.jsonl"]), "类型采用记录文件存在", None)
    check("采用记录", "ADOPT-DYNAMIC", "动态链消费记录", bool(chain_ids) and bool(records["动态链消费.jsonl"]), f"正文使用{len(chain_ids)}条动态链，消费记录{len(records['动态链消费.jsonl'])}条", None, blocking=True)
    check("采用记录", "ADOPT-STATIC", "静态连接采用记录", bool(records["静态连接消费.jsonl"]), "静态连接消费记录文件存在", None)
    check("采用记录", "ADOPT-ANCHOR", "锚点采用记录", bool(anchor_ids) and bool(records["锚点消费.jsonl"]), f"正文使用{len(anchor_ids)}个锚点", None)
    check("采用记录", "ADOPT-EXEC", "执行记录", len(execution_records) >= 10, "执行消费记录覆盖模块运行", None, blocking=True)

    source_ok = all(record.get("source_anchor_id") or record.get("anchor_id") for scene in scenes for record in scene.get("source_records", []))
    chain_ok = all(record.get("source_chain_id") or record.get("chain_id") for scene in scenes for record in scene.get("source_records", []))
    placeholder = any("正文草稿" in paragraph for scene in scenes for paragraph in scene.get("paragraphs", []))
    check("正文落点", "PROSE-ANCHOR", "正文锚点来源", source_ok, "每个正文段落均有锚点来源", None)
    check("正文落点", "PROSE-CHAIN", "正文动态链来源", chain_ok, "每个正文段落均有动态链来源", None)
    check("正文落点", "PROSE-RECORD", "段落来源记录", all(len(scene.get("source_records", [])) == len(scene.get("paragraphs", [])) for scene in scenes), "每个场景段落均有来源记录", None)
    check("正文落点", "PROSE-PLACEHOLDER", "正文占位文本", not placeholder, "未发现场景正文草稿占位文本", None, blocking=True)
    metadata_leak = any(_contains_generation_metadata(paragraph) for scene in scenes for paragraph in scene.get("paragraphs", []))
    check("正文落点", "PROSE-METADATA", "正文规划元数据泄漏", not metadata_leak, "正文未混入动态链条件、效果或内部模板措辞", None, blocking=True)
    prose_meta_markers = ("资料要求", "转化为本场", "解释词", "创作绑定", "激活矩阵", "段落级效果证据")
    prose_meta_leaks = sorted({marker for marker in prose_meta_markers if marker in all_text})
    check(
        "正文落点", "PROSE-META-LANGUAGE", "正文创作元语言泄漏",
        not prose_meta_leaks,
        "正文未出现资料处理或生成过程的说明文字" if not prose_meta_leaks else "正文含有创作过程元语言：" + "、".join(prose_meta_leaks),
        prose_meta_leaks,
        blocking=True,
    )
    repeated_paragraphs = []
    seen_paragraphs: dict[str, str] = {}
    for scene in scenes:
        for paragraph in scene.get("paragraphs", []):
            normalized = re.sub(r"\s+", "", str(paragraph))
            if normalized in seen_paragraphs:
                repeated_paragraphs.append(normalized[:80])
            else:
                seen_paragraphs[normalized] = str(scene.get("scene_id"))
    check("正文落点", "PROSE-REPETITION", "段落重复", not repeated_paragraphs, "正文段落无完全重复" if not repeated_paragraphs else f"发现{len(repeated_paragraphs)}个重复段落", repeated_paragraphs, blocking=True)
    anchor_names = [str(name) for scene in scenes for name in scene.get("project_scene_input", {}).get("anchor_names", [])]
    source_names = [str(record.get("anchor_name")) for scene in scenes for record in scene.get("source_records", []) if record.get("anchor_name")]
    leaked_anchor_names = sorted({name for name in source_names if name and name in all_text})
    check("正文落点", "PROSE-ANCHOR-NAME", "锚点原名泄漏", not leaked_anchor_names, "正文只使用锚点转译结果，未直出锚点名称", leaked_anchor_names, blocking=True)
    check("正文落点", "PROSE-DESIGN-BINDING", "设计阶段来源绑定", all(scene.get("project_scene_input") and scene.get("chain_id_used") and scene.get("anchor_ids_used") for scene in scenes), "每个正文场景都有前置设计来源绑定", None, blocking=True)
    prose_files = prose.get("prose_files", []) if isinstance(prose, dict) else []
    chapter_file_ok = bool(prose_files)
    chapter_file_evidence = []
    for file_info in prose_files:
        path = PROJECT_ROOT / str(file_info.get("relative_path", ""))
        exists = path.is_file() and path.stat().st_size > 0
        content = read_text(path) if exists else ""
        chapter_scene_ids = {str(scene.get("scene_id")) for scene in scenes if str(scene.get("chapter_id")) == str(file_info.get("chapter_id"))}
        file_scenes_ok = bool(chapter_scene_ids) and all(scene_id in content for scene_id in chapter_scene_ids)
        protagonist_in_file = bool(protagonist) and protagonist in content
        chapter_file_ok = chapter_file_ok and exists and file_scenes_ok and protagonist_in_file
        chapter_file_evidence.append({"path": str(path), "exists": exists, "scene_ids_present": file_scenes_ok, "protagonist_present": protagonist_in_file, "bytes": len(content.encode("utf-8"))})
    check("正文落点", "PROSE-FILE", "正式章节文件", chapter_file_ok, "正文已写入项目正文目录并包含场景与项目主角" if chapter_file_ok else "缺少有效正式章节文件，或文件未落地项目场景/主角", chapter_file_evidence, blocking=True)

    source_audit = audit_project(PROJECT_ROOT, config, prose)
    check("来源审计", "SOURCE-CONSUMPTION", "历史项目级资料消费审计", source_audit["status"] == "passed", "历史全量审计通过" if source_audit["status"] == "passed" else "历史全量审计不作为本次场景选择闭环的阻断条件", source_audit, warning=True)
    duty_audit = audit_material_duty_records(
        [record for scene in scenes for record in scene.get("source_records", []) if isinstance(record, dict)],
        str(prose.get("run_id") or RUN_ID),
        "正文",
    )
    check("资料职责", "MATERIAL-DUTY-RECEIPT", "正文资料职责回执", duty_audit["passed"], "正文资料职责回执完整" if duty_audit["passed"] else "；".join(item["reason"] for item in duty_audit["violations"]), duty_audit, blocking=True)

    aesthetic_text = all_text
    for rule_id, name, passed, detail in (
        ("162.2.1", "感官审美", any(word in aesthetic_text for word in ("光线", "声音", "呼吸", "触到", "气味", "温度", "视线")), "存在感官细节"),
        ("162.2.2", "外貌描写承载信息", bool(protagonist) and any(word in aesthetic_text for word in ("站位", "呼吸", "手", "视线", "身体")), "人物外在反应承载当前判断或压力"),
        ("162.2.3", "空间结构和光线来源", any(word in aesthetic_text for word in ("宗门", "档案", "外廊", "检测场", "入口", "墙", "门")) and any(word in aesthetic_text for word in ("光线", "阴影", "出口", "站位", "空间")), "正文包含可定位的空间结构和光线/遮挡证据"),
        ("162.2.4", "关键动作蓄力和结果", all(len(scene.get("paragraphs", [])) == 5 and len(scene.get("source_records", [])) == 5 for scene in scenes), "行动链将观察、选择、动作和结果按段落顺序落地"),
        ("162.2.5", "抽象评价具体化", all(record.get("anchor_application") and record.get("prose_location") for scene in scenes for record in scene.get("source_records", [])), "每个锚点都有段落位置和具体应用说明"),
        ("162.2.6", "动作停顿和判断", all(any(char in paragraph for char in ("，", "；", "却", "只", "便")) for scene in scenes for paragraph in scene.get("paragraphs", [])), "连续动作之间存在转折、停顿或选择证据"),
    ):
        check("审美", rule_id, rule_id, passed, detail, None, blocking=True)

    passed_count = sum(item["passed"] for item in check_results)
    failed_count = len(check_results) - passed_count
    output = {
        "check_results": check_results, "blocking_failures": blocking_failures, "warnings": warnings,
        "runtime_prose_status": writing_evidence.get("runtime_prose_status", "failed"),
        "formal_delivery_status": formal_release.get("status", "blocked"),
        "formal_release": formal_release,
        "material_duty_audit": duty_audit,
        "passed_count": passed_count, "failed_count": failed_count, "warning_count": len(warnings),
        "total_checks": len(check_results), "status": "passed" if not blocking_failures else "failed",
        "inputs": {"project_type": config.get("genre_selection", config.get("genres")), "type_decision": type_decision, "world_setting_loaded": bool(world), "quality_rules_loaded": bool(quality), "scene_cards_loaded": bool(cards), "prose_loaded": bool(prose)},
        "method_block_count": len({entry["block"] for entry in method_entries}), "method_entry_count": len(method_entries),
        "source_consumption_audit": source_audit,
        "anchor_binding_evidence": str(anchor_evidence_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "deliverability": "project_delivery_candidate" if not blocking_failures and prose.get("self_check", {}).get("passed") is True and formal_release.get("status") == "approved" else "draft_only",
        "deliverability_reason": "运行期验收和版本绑定的正式发布审批均通过。" if not blocking_failures and prose.get("self_check", {}).get("passed") is True and formal_release.get("status") == "approved" else "运行期创作验收通过，但当前发布清单尚未完成条目认证或人工签署；只能作为草稿。" if not blocking_failures else "存在创作验收阻断失败，只能作为草稿证据。",
    }
    print(json.dumps({"读取的检查板块数": output["method_block_count"], "总检查项数": output["total_checks"], "通过项数": passed_count, "失败项数": failed_count, "警告项数": len(warnings), "status": output["status"], "阻断失败列表": blocking_failures}, ensure_ascii=False))
    return output, [write_output("10", "final_check_report", output)]


def execute_11(data: dict) -> tuple[dict, list[Path]]:
    outputs = data.get("module_outputs", {})
    expected_modules = [f"{number:02d}" for number in range(1, 11)]
    received_modules = sorted(outputs)
    missing_modules = [module_id for module_id in expected_modules if module_id not in outputs]
    unexpected_modules = [module_id for module_id in received_modules if module_id not in expected_modules]
    failed = [
        module_id for module_id in expected_modules
        if outputs.get(module_id, {}).get("status") in {"failed", "skipped"}
    ]
    missing_outputs = []
    for module_id in expected_modules:
        if module_id not in outputs:
            continue
        output_files = outputs[module_id].get("output_files") or []
        if not output_files:
            missing_outputs.append(module_id + "（未声明输出文件）")
            continue
        absent_files = []
        for output_file in output_files:
            path = Path(str(output_file))
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if not path.is_file() or path.stat().st_size <= 0:
                absent_files.append(str(output_file))
        if absent_files:
            missing_outputs.append(module_id + "（文件不存在或为空：" + ", ".join(absent_files) + "）")
    final_check = data.get("module_10_output") or data.get("final_check") or (
        data if isinstance(data.get("formal_release"), dict) else {}
    )
    if not final_check:
        # execute_10 merges its report into the shared context, while older
        # callers may only provide the module record. Support both shapes.
        final_check = outputs.get("10", {})
    final_check_failed = (
        final_check.get("status") in {"failed", "skipped"}
        or bool(final_check.get("blocking_failures"))
    )
    transfer_failures = []
    if missing_modules:
        transfer_failures.append("缺少上游模块输出：" + ", ".join(missing_modules))
    if unexpected_modules:
        transfer_failures.append("收到未声明的模块输出：" + ", ".join(unexpected_modules))
    if failed:
        transfer_failures.append("上游模块失败或跳过：" + ", ".join(failed))
    if missing_outputs:
        transfer_failures.append("上游模块缺少输出文件：" + ", ".join(missing_outputs))
    if final_check_failed:
        transfer_failures.append("模块10最终验收未通过")
    transfer_passed = not transfer_failures
    formal_release = final_check.get("formal_release", {}) if isinstance(final_check.get("formal_release"), dict) else {}
    source_capability_blocked = bool(data.get("source_production_capability_blocked"))
    delivery_candidate = (
        transfer_passed
        and final_check.get("status") == "success"
        and final_check.get("formal_delivery_status") == "approved"
        and formal_release.get("status") == "approved"
        and formal_release.get("formal_release_allowed") is True
        and formal_release.get("delivery_ready") is True
        and not source_capability_blocked
    )
    delivery_status = "released" if delivery_candidate else "draft_only"
    release_decision = "released" if delivery_candidate else "blocked"
    release_reason = (
        "传递、规划、文学审校、来源能力、执行契约和正式审批均通过。"
        if delivery_candidate
        else "存在模块失败、执行契约阻断、来源能力不足或正式审批未通过，只保留草稿运行证据。"
    )
    output = {
        "schema_version": "module-11-transfer-summary-1.2",
        "modules_received": received_modules, "module_count": len(outputs),
        "output_files": [p for item in outputs.values() for p in item.get("output_files", [])],
        "status": "success" if transfer_passed else "failed",
        "transfer_status": "passed" if transfer_passed else "failed",
        "transfer_failures": transfer_failures,
        "failed_modules": failed,
        "missing_modules": missing_modules,
        "unexpected_modules": unexpected_modules,
        "missing_outputs": missing_outputs,
        "final_check_status": "failed" if final_check_failed else "passed",
        "release_readiness": final_check.get("formal_delivery_status", "blocked"),
        "delivery_status": delivery_status,
        "release_decision": release_decision,
        "release_reason": release_reason,
        "source_production_capability": data.get("source_production_capability", {}),
        "source_production_capability_blocked": source_capability_blocked,
        "delivery_gate": {
            "status": delivery_status,
            "formal_release_blockers": list(formal_release.get("blockers", [])),
            "source_registry_status": data.get("resource_registry", {}).get("status"),
            "source_production_capability_blocked": source_capability_blocked,
        },
        "delivery_reason": "所有上游模块成功，且当前冻结发布清单已获批准。" if delivery_candidate else "传递链与运行期验收通过，但当前冻结发布清单尚未完成条目认证或人工签署，只能保持 draft_only。" if transfer_passed else "存在上游模块传递或最终验收失败，禁止正式交付。",
    }
    summary_path = write_output("11", "transfer_summary", output)
    release_receipt = {
        "schema_version": "chapter-release-decision-1.0",
        "run_id": RUN_ID,
        "decision": release_decision,
        "formal_release_allowed": delivery_candidate,
        "delivery_status": delivery_status,
        "release_readiness": output["release_readiness"],
        "reason": release_reason,
        "blockers": list(dict.fromkeys(transfer_failures + formal_release.get("blockers", []))),
        "source": str(summary_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "formal_prose_written": False,
    }
    receipt_path = _run_evidence_dir() / (
        "chapter_publication.json" if delivery_candidate else "chapter_publication_blocked.json"
    )
    receipt_path.write_text(json.dumps(release_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, receipt_path, kind="release_decision", module_id="11", status="success", exit_code=0)
    return output, [summary_path, receipt_path]


MODULES: tuple[tuple[str, str, Callable[[dict], tuple[dict, list[Path]]]], ...] = (("01", "系统启动", execute_01), ("02", "前置决策层", execute_02), ("03", "类型特征适配层", execute_03), ("04", "世界与设定层", execute_04), ("05", "开篇抢跑层", execute_05), ("06", "人物与剧情核心层_第1批", execute_06), ("07", "执行与品控层_第2批", execute_07), ("08", "规划师模式", execute_08), ("09", "写手模式", execute_09), ("10", "编辑模式", execute_10), ("11", "三阶段数据传递", execute_11))

MODULE_INPUTS = {
    "01": [],
    "02": [TYPE_SYSTEM, TYPE_INDEX],
    "03": [TYPE_INDEX],
    "04": [STATIC_FULL, STATIC_BINDING_SUMMARY, PROJECT_CONFIG, LIBRARY],
    "05": [ANCHOR_INDEX],
    "06": [DYNAMIC_FULL, STATIC_INDEX],
    "07": [DYNAMIC_FULL, ANCHOR_INDEX],
    "08": [DYNAMIC_FULL, ANCHOR_INDEX],
    "09": [ANCHOR_INDEX, ANCHOR_NETWORK, LIBRARY, PROJECT_CONFIG, BIBLE, OUTPUT_DIR / "module_06_character_plot_core.json", OUTPUT_DIR / "module_08_scene_beat_cards.json"],
    "10": [TYPE_INDEX, STATIC_INDEX, DYNAMIC_FULL, ANCHOR_INDEX, *RULE_FILES],
    "11": [],
}


def _refresh_module_inputs() -> None:
    MODULE_INPUTS.update({
        "01": [PROJECT_CONFIG],
        "02": [TYPE_SYSTEM, TYPE_INDEX, CREATION_BINDINGS],
        "03": [TYPE_INDEX, CREATION_BINDINGS],
        "04": [STATIC_FULL, STATIC_BINDING_SUMMARY, PROJECT_CONFIG, LIBRARY, CREATION_BINDINGS],
        "05": [ANCHOR_INDEX, CREATION_BINDINGS],
        "06": [DYNAMIC_FULL, STATIC_INDEX, PROJECT_CONFIG, CREATION_BINDINGS],
        "07": [DYNAMIC_FULL, ANCHOR_INDEX, CREATION_BINDINGS],
        "08": [DYNAMIC_FULL, ANCHOR_INDEX, PROJECT_CONFIG, CREATION_BINDINGS, OUTPUT_DIR / "module_06_character_plot_core.json"],
        "09": [ANCHOR_INDEX, ANCHOR_NETWORK, LIBRARY, PROJECT_CONFIG, BIBLE, CREATION_BINDINGS, OUTPUT_DIR / "module_06_character_plot_core.json", OUTPUT_DIR / "module_08_scene_beat_cards.json"],
        "10": [TYPE_INDEX, STATIC_INDEX, DYNAMIC_FULL, ANCHOR_INDEX, CREATION_BINDINGS, *RULE_FILES],
        "11": [],
    })


def _binding_activation_audit(context: dict[str, Any], stage: str) -> dict[str, Any]:
    """Audit activation without treating loaded reference data as prose use."""
    binding_data = context.get("creation_bindings", {})
    bindings = binding_data.get("records", []) if isinstance(binding_data, dict) else []
    project_config = context.get("project_config", {})
    if stage == "正文":
        artifact = context.get("scene_prose", {})
        artifact_content = {"scenes": artifact.get("scenes", [])} if isinstance(artifact, dict) else {}
    else:
        artifact = context.get("scene_beat_cards", {})
        artifact_content = {
            "scenes": artifact.get("scenes", []),
            "chapter_plan": artifact.get("chapter_plan", []),
            "design_bindings": artifact.get("design_bindings", []),
        } if isinstance(artifact, dict) else {}
    searchable = json.dumps({"project_config": project_config, "artifact": artifact_content}, ensure_ascii=False).lower()
    selected_source_ids: set[str] = set()

    def collect_source_ids(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"source_id", "anchor_id", "source_anchor_id", "chain_id", "source_chain_id", "library_entry_id"} and isinstance(item, str):
                    selected_source_ids.add(item.lower())
                else:
                    collect_source_ids(item)
        elif isinstance(value, list):
            for item in value:
                collect_source_ids(item)

    collect_source_ids(artifact_content)
    rows: list[dict[str, Any]] = []
    for binding in bindings:
        meta = binding.get("creation_binding", {})
        policy = meta.get("activation_policy", {})
        source_id = str(binding.get("source_id", "")).strip()
        name = str(binding.get("name", "")).strip()
        explicit_terms = [term.lower() for term in (source_id, name) if len(term) >= 2]
        explicit_hits = [term for term in explicit_terms if term in searchable]
        semantic = binding.get("semantic_interpretation", {}).get("semantic_terms", [])
        semantic_terms = []
        for term in semantic if isinstance(semantic, list) else []:
            normalized = str(term).strip().lower()
            if 2 <= len(normalized) <= 40 and normalized not in semantic_terms:
                semantic_terms.append(normalized)
        semantic_hits = [term for term in semantic_terms if term in searchable]
        binding_class = meta.get("binding_class", "deferred_activation")
        # Direct scene material is activated only after the planner selects its
        # stable source identifier. Generic words such as "动作" or "空间" are
        # useful retrieval signals, but cannot make hundreds of anchors due in
        # one chapter.
        direct_id_selected = source_id.lower() in selected_source_ids
        activated = direct_id_selected if binding_class == "direct_creation" else bool(explicit_hits) or len(semantic_hits) >= 2
        evidence_terms = [source_id] if direct_id_selected else (explicit_hits or (semantic_hits if binding_class != "direct_creation" else []))
        rows.append({
            "binding_id": binding.get("binding_id"),
            "source_kind": binding.get("source_kind"),
            "source_id": source_id,
            "source_ref": binding.get("source_ref"),
            "binding_class": binding_class,
            "activation_status": "activated" if activated else "awaiting_stage_evidence",
            "matched_stage": stage if activated else None,
            "matched_project_terms": evidence_terms[:12],
            "activation_reason": (
                "场景选择器以结构化来源 ID 明确选中"
                if direct_id_selected else "来源标识或名称在前置产物中明确出现"
                if explicit_hits else "至少两个有效语义词与前置产物匹配"
                if activated else "当前前置产物未满足资料激活条件"
            ),
            "next_activation_conditions": [] if activated else policy.get("conditions", []),
            "prose_effective": False,
        })
    detail = RUN_EVIDENCE_DIR / "资料绑定激活审计.jsonl"
    detail.parent.mkdir(parents=True, exist_ok=True)
    detail.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    summary = {
        "schema_version": "source-binding-activation-audit-1.0",
        "generated_at": now(),
        "stage": stage,
        "binding_count": len(rows),
        "activation_status_counts": dict(Counter(row["activation_status"] for row in rows)),
        "binding_class_counts": dict(Counter(row["binding_class"] for row in rows)),
        "policy": "激活表示前置创作需求匹配；正文采用仍须由场景和正文位置证据证明。",
        "detail_output": str(detail.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }
    summary_path = RUN_EVIDENCE_DIR / "资料绑定激活审计摘要.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, detail, kind="activation_audit", status="success", exit_code=0)
    register_artifact(PROJECT_ROOT, RUN_ID, summary_path, kind="activation_audit", status="success", exit_code=0)
    context["binding_activation_audit"] = {"summary": summary, "records": rows}
    context["binding_activation_audit_files"] = [detail, summary_path]
    return summary


def main(project_root: str | Path | None = None, project_id: str | None = None, genres: list[str] | None = None, run_id: str | None = None) -> list[dict]:
    set_project_root(project_root, run_id)
    _refresh_module_inputs()
    require(PROJECT_CONFIG)
    # Draft creation requires coherent readable inputs. Approval and immutable
    # delivery provenance are assessed only after a draft has been generated.
    contract = validate_execution_contract(PROJECT_ROOT, require_blueprint=False, phase="creation")
    if contract["status"] != "passed":
        raise ValueError("项目执行边界未通过：" + "；".join(contract["errors"]))
    # Freeze the run's declared inputs before reading any project material. This
    # also gives startup failures a non-empty, auditable snapshot instead of
    # leaving a running manifest with only partial actual_reads.
    snapshot_path = _write_run_input_snapshot(contract)
    configured = contract["config"]
    inspiration_receipt_path = EVIDENCE / "小说灵感选型回执.json"
    require(inspiration_receipt_path)
    inspiration_receipt = read_json(inspiration_receipt_path)
    configured_genres = configured.get("genre_selection") or configured.get("genres") or []
    if isinstance(configured_genres, str):
        configured_genres = [configured_genres]
    selection_errors = validate_selection(
        inspiration_receipt,
        project_id=str(configured.get("project_id") or ""),
        selected_types=configured_genres,
        profile_path=RESOURCE_ROOT / "配置" / "类型配置模板.json",
    )
    if selection_errors:
        raise ValueError("灵感选型未通过执行入口校验：" + "；".join(selection_errors))
    registry = build_registry(PROJECT_ROOT)
    startup_contract = _write_startup_binding_contract(configured, registry)
    if startup_contract["status"] != "passed":
        raise RuntimeError("启动绑定合同未通过：" + "；".join(startup_contract["blocking_reasons"]))
    interpretation_registry = execute_source_interpretation_registry()
    if registry["status"] != "passed":
        raise RuntimeError("资源注册失败，禁止执行创作管道：" + "；".join(registry["blocking_errors"]))
    creation_bindings, binding_files = build_creation_bindings(
        PROJECT_ROOT,
        OUTPUT_DIR / "module_00_source_interpretation_registry.json",
        PROJECT_CONFIG,
    )
    if creation_bindings["source_count"] != interpretation_registry["source_count"]:
        raise RuntimeError("全量资料转译数量与解释词注册数量不一致，禁止进入创作流程")
    # Binding generation refreshes the immutable source-reference baseline. Reuse
    # only previously explicit grants, re-anchor them to this baseline, and then
    # rebuild the audited projection before module 08 creates the run package.
    rebuild_current_authorization(PROJECT_ROOT)
    from 全量资料输入与正文授权 import audit as audit_authorization
    from 全量资料绑定授权投影同步 import sync as sync_authorization
    audit_authorization(PROJECT_ROOT)
    sync_authorization(PROJECT_ROOT)
    config_errors = _project_config_errors(configured)
    if config_errors:
        raise ValueError("项目配置不符合执行契约：" + "；".join(config_errors))
    activation_matrix, activation_files = _build_book_activation_matrix(configured, creation_bindings)
    source_capability = audit_source_production(PROJECT_ROOT)
    source_capability_blocked = source_capability["status"] != "passed"
    # Registry, translated bindings and activation assignments are regenerated
    # for this run. Refresh the system-only admission immediately afterwards so
    # module 01 freezes the same immutable input set that module 10 validates.
    prepare_runtime_admission(PROJECT_ROOT)
    creation_contract = validate_execution_contract(PROJECT_ROOT, phase="creation")
    if creation_contract["status"] != "passed":
        raise RuntimeError("运行期准入刷新后创作契约未通过：" + "；".join(creation_contract["errors"]))
    if project_id and project_id != configured.get("project_id") and project_id != configured.get("project_name"):
        raise ValueError("命令行 project-id 与项目配置不一致；必须显式修改项目配置")
    if genres and configured_genres and genres != configured_genres:
        raise ValueError("命令行 genres 与项目配置不一致；必须显式修改项目配置")
    context: dict[str, Any] = {
        "project_root": str(PROJECT_ROOT),
        "project_config": configured,
        "resource_registry": registry,
        "startup_binding_contract": startup_contract,
        "delivery_status": "draft_only" if registry.get("quality_blocking_errors") or source_capability_blocked else "project_delivery_candidate",
        "quality_blocking_errors": list(registry.get("quality_blocking_errors", [])),
        "source_interpretation_registry": interpretation_registry,
        "creation_bindings": creation_bindings,
        "activation_matrix": activation_matrix,
        "source_production_capability": source_capability,
        "source_production_capability_blocked": source_capability_blocked,
        "creation_binding_files": [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in binding_files],
    }; results = []; rows = [{"schema_version": "1.0", "record_type": "header", "run_id": RUN_ID, "total_records": len(MODULES), "last_updated": now(), "project_root": str(PROJECT_ROOT), "resource_registry": str(RESOURCE_REGISTRY.relative_to(PROJECT_ROOT)).replace("\\", "/"), "delivery_status": context["delivery_status"], "source_production_capability": source_capability, "source_production_capability_status": source_capability["status"], "source_production_capability_blocked": source_capability_blocked}]
    blocked = False
    for module_id, name, function in MODULES:
        if blocked and module_id not in {"11"}:
            record = {
                "module_id": module_id,
                "module_name": name,
                "status": "skipped",
                "error": "上游项目输入契约失败，已阻止继续创作",
                "input_files": [],
                "output_files": [],
                "executed_at": now(),
            }
            results.append(record)
            rows.append(record)
            continue
        try:
            output, files = function(context); file_strings = [str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path) for path in files]
            input_files = [str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path) for path in MODULE_INPUTS[module_id]]
            internal_failure = output.get("status") == "failed" or output.get("self_check", {}).get("passed") is False
            record = {"module_id": module_id, "module_name": name, "status": "failed" if internal_failure else "success", "input_files": input_files, "output_files": file_strings, "executed_at": now()}
            if internal_failure:
                record["error"] = output.get("blocking_failures") or output.get("self_check", {}).get("details") or "模块自检失败"
                if module_id in {"01", "06", "08", "09", "10"}:
                    blocked = True
            context = {**context, **output, "module_outputs": {**context.get("module_outputs", {}), module_id: {**record, "output_files": file_strings}}}
            if module_id == "08" and record["status"] == "success":
                context["scene_beat_cards"] = output
                scene_contexts = []
                frozen_pairs = set()
                previous_scene = None
                for sequence, scene in enumerate(output.get("scenes", []) if isinstance(output, dict) else [], start=1):
                    if not isinstance(scene, dict):
                        continue
                    scene_contexts.append({
                        "chapter_id": scene.get("chapter_id"),
                        "scene_id": scene.get("scene_id"),
                        "scene_sequence": sequence,
                        "state_before": scene.get("state_before"),
                        "state_after": scene.get("state_after"),
                        "previous_scene_id": previous_scene.get("scene_id") if previous_scene else "",
                        "previous_state_after": previous_scene.get("state_after") if previous_scene else "",
                    })
                    previous_scene = scene
                frozen_bindings = []
                for scene in output.get("scenes", []) if isinstance(output, dict) else []:
                    for beat in scene.get("action_chain", []) if isinstance(scene, dict) else []:
                        if not isinstance(beat, dict) or not beat.get("binding_id"):
                            raise RuntimeError(f"{scene.get('scene_id', 'unknown')} action_chain 缺少冻结 binding_id")
                        pair = (str(scene.get("scene_id") or ""), str(beat.get("binding_id") or ""))
                        if pair in frozen_pairs:
                            continue
                        frozen_pairs.add(pair)
                        frozen_bindings.append({
                            "chapter_id": scene.get("chapter_id"),
                            "scene_id": scene.get("scene_id"),
                            "binding_id": beat.get("binding_id"),
                            "stage": "正文",
                            "required_writing_dimensions": beat.get("required_writing_dimensions", []),
                            "activation_conditions_met": True,
                            "activation_evidence": beat.get("activation_evidence") or scene.get("activation_evidence", []),
                            "selection_rationale": beat.get("selection_rationale") or "模块08 action_chain 冻结绑定。",
                        })
                package, package_check = build_runtime_material_package(PROJECT_ROOT, RUN_ID, scene_contexts=scene_contexts, frozen_bindings=frozen_bindings)
                context["runtime_material_package"] = package
                context["runtime_material_package_scene_check"] = package_check
                package_path = RUN_EVIDENCE_DIR / "运行资料包.json"
                register_artifact(
                    PROJECT_ROOT, RUN_ID, package_path, kind="material_package", module_id="08",
                    status="passed" if package_check["passed"] else "failed",
                    exit_code=0 if package_check["passed"] else 1,
                )
                output["runtime_material_admission"] = {
                    "run_id": RUN_ID,
                    "status": "admitted" if package_check["passed"] else "no_material_admitted",
                    "selected_count": package.get("selected_count", 0),
                    "deferred_count": package.get("deferred_count", 0),
                    "errors": package_check.get("errors", []),
                }
                write_output("08", "scene_beat_cards", output)
                if not package_check["passed"]:
                    record["status"] = "failed"
                    record["error"] = package_check["errors"]
                    blocked = True
                _binding_activation_audit(context, "场景卡")
                _write_consumption_logs(context)
            if module_id == "09" and record["status"] == "success":
                context["scene_prose"] = output
                package = context.get("runtime_material_package") or load_package(PROJECT_ROOT, RUN_ID)
                consumption = []
                for scene in output.get("scenes", []) if isinstance(output, dict) else []:
                    for source in scene.get("source_records", []) if isinstance(scene, dict) else []:
                        if isinstance(source, dict) and source.get("binding_id"):
                            consumption.append({
                                "run_id": RUN_ID, "chapter_id": scene.get("chapter_id"), "scene_id": scene.get("scene_id"), "binding_id": source.get("binding_id"),
                                "source_id": source.get("source_id"), "prose_location": source.get("prose_location"),
                                "package_id": source.get("package_id"), "continuity_hash": source.get("continuity_hash"),
                                "translation_evidence_result": source.get("translation_evidence", {}).get("result") if isinstance(source.get("translation_evidence"), dict) else "",
                                "observable_effect": source.get("translation_evidence", {}).get("result") if isinstance(source.get("translation_evidence"), dict) else "",
                            })
                package_check = validate_package(PROJECT_ROOT, package, "prose", consumption)
                context["runtime_material_package_prose_check"] = package_check
                context["runtime_material_consumption"] = consumption
                if not package_check["passed"]:
                    record["status"] = "failed"
                    record["error"] = package_check["errors"]
                    blocked = True
                _binding_activation_audit(context, "正文")
                _write_consumption_logs(context)
            if module_id in {"10", "11"}:
                package = context.get("runtime_material_package") or load_package(PROJECT_ROOT, RUN_ID)
                package_check = validate_package(PROJECT_ROOT, package, "editorial" if module_id == "10" else "delivery", context.get("runtime_material_consumption", []))
                context[f"runtime_material_package_{module_id}_check"] = package_check
                if not package_check["passed"]:
                    record["status"] = "failed"
                    record["error"] = package_check["errors"]
                    if module_id == "10":
                        blocked = True
                    elif module_id == "11" and not package:
                        record["error"] = ["本次运行缺少运行资料包；正式交付已阻断"]
            if module_id == "11":
                record["input_files"] = [item["output_files"][0] for item in results if item.get("status") == "success" and item.get("output_files")]
            if module_id == "09" and file_strings:
                register_artifact(PROJECT_ROOT, RUN_ID, files[0], kind="prose", module_id=module_id, status=record["status"], exit_code=0 if record["status"] == "success" else 1)
            elif module_id == "10" and file_strings:
                register_artifact(PROJECT_ROOT, RUN_ID, files[0], kind="structural_quality", module_id=module_id, status=record["status"], exit_code=0 if record["status"] == "success" else 1)
                register_artifact(PROJECT_ROOT, RUN_ID, files[0], kind="literary_review", module_id=module_id, status=record["status"], exit_code=0 if record["status"] == "success" else 1)
            elif module_id == "11" and file_strings:
                register_artifact(PROJECT_ROOT, RUN_ID, files[0], kind="delivery_report", module_id=module_id, status=record["status"], exit_code=0 if record["status"] == "success" else 1)
            print(json.dumps({"module": module_id, "name": name, "status": record["status"], "input_files": record["input_files"], "output_files": file_strings, "error": record.get("error")}, ensure_ascii=False))
        except Exception as exc:
            record = {"module_id": module_id, "module_name": name, "status": "failed", "error": str(exc), "input_files": [str(path) for path in MODULE_INPUTS.get(module_id, [])], "output_files": [], "executed_at": now()}; blocked = True; context = {**context, "module_outputs": {**context.get("module_outputs", {}), module_id: record}}
            if module_id == "08":
                empty_package = {"schema_version": "runtime-material-package-1.0", "run_id": RUN_ID, "records": [], "selected_count": 0, "deferred_count": 0, "runtime_material_admission": {"status": "no_material_admitted", "reason": str(exc)}}
                package_path = write_package(PROJECT_ROOT, empty_package)
                record["output_files"] = [str(package_path.relative_to(PROJECT_ROOT)).replace("\\", "/")]
                context["runtime_material_package"] = empty_package
                context["runtime_material_package_scene_check"] = validate_package(PROJECT_ROOT, empty_package, "scene")
            print(json.dumps({"module": module_id, "name": name, "status": "failed", "error": str(exc)}, ensure_ascii=False))
        record["run_id"] = RUN_ID
        results.append(record); rows.append(record)
    CONSUMPTION.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    register_artifact(PROJECT_ROOT, RUN_ID, CONSUMPTION, kind="consumption_log", status="success", exit_code=0)
    manifest_report = verify_full_pipeline_manifest(PROJECT_ROOT, RUN_ID)
    if not manifest_report["passed"]:
        results.append({
            "module_id": "read_audit",
            "module_name": "运行读取复核",
            "status": "blocked",
            "error": manifest_report["errors"],
            "input_files": manifest_report["manifest"].get("input_snapshot_paths", []),
            "output_files": [manifest_report["manifest_path"]],
            "executed_at": now(),
        })
        write_failure_receipt(
            PROJECT_ROOT, RUN_ID, status="blocked", failed_stage="read_audit", exit_code=2,
            errors=manifest_report["errors"],
            cleanup_actions=["未授予正文写入或正式交付资格"],
        )
    else:
        pipeline_passed = all(row.get("status") == "success" for row in results)
        if pipeline_passed:
            finalize_run(PROJECT_ROOT, RUN_ID, status="passed", exit_code=0)
        else:
            errors = [
                str(error)
                for row in results if row.get("status") != "success"
                for error in (row.get("error") if isinstance(row.get("error"), list) else [row.get("error")])
                if str(error).strip()
            ]
            write_failure_receipt(
                PROJECT_ROOT, RUN_ID, status="failed", failed_stage="module_execution", exit_code=2,
                errors=errors,
                cleanup_actions=["未授予正文写入或正式交付资格"],
            )
    print(json.dumps({"total_modules": len(results), "success": sum(r["status"] == "success" for r in results), "failed": sum(r["status"] != "success" for r in results)}, ensure_ascii=False)); return results


def run_pipeline(
    project_root: str | Path | None = None,
    project_id: str | None = None,
    genres: list[str] | None = None,
    run_id: str | None = None,
    *,
    enforce_lifecycle: bool = False,
) -> list[dict]:
    """Run the pipeline and persist failures that happen before module 01."""
    try:
        requested_run_id = str(run_id or uuid.uuid4().hex).strip()
        if not requested_run_id or Path(requested_run_id).name != requested_run_id:
            raise ValueError("run_id 必须是单个安全目录名")
        if enforce_lifecycle:
            config_path = Path(project_root).expanduser().resolve() / "配置" / "project_config.json"
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
            validate_active_project(
                RESOURCE_ROOT,
                config_path.parent.parent,
                project_id=project_id or config.get("project_id"),
                book_title=config.get("book_title") or config_path.parent.parent.name,
                resource_root=config.get("resource_root"),
            )
        set_project_root(project_root, requested_run_id)
        initialize_run(PROJECT_ROOT, requested_run_id)
        return main(project_root, project_id, genres, run_id)
    except Exception as exc:
        failure_run_id = str(locals().get("requested_run_id") or run_id or "").strip()
        failure = {"run_id": failure_run_id, "status": "failed", "error_type": type(exc).__name__, "error": str(exc), "executed_at": now()}
        if failure_run_id:
            set_project_root(project_root, failure_run_id)
            RUN_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            CONSUMPTION.write_text(json.dumps(failure, ensure_ascii=False) + "\n", encoding="utf-8")
            write_failure_receipt(
                PROJECT_ROOT, failure_run_id, status="failed", failed_stage="startup", exit_code=2,
                errors=[f"{type(exc).__name__}: {exc}"],
                cleanup_actions=["未授予正文写入或正式交付资格"],
            )
        print(json.dumps(failure, ensure_ascii=False))
        return [failure]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="具体项目目录，必须包含 配置/project_config.json")
    parser.add_argument("--project-id")
    parser.add_argument("--genres", nargs="+")
    parser.add_argument("--run-id", help="固定本次运行的安全目录名，供端到端验收复用")
    args = parser.parse_args()
    results = run_pipeline(args.project_root, args.project_id, args.genres, args.run_id, enforce_lifecycle=True)
    raise SystemExit(0 if all(row.get("status") == "success" for row in results) else 2)
