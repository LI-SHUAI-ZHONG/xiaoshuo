"""Merge explicit material changes into the authoritative original sources.

The original-material files stay authoritative.  Audit reports, bindings and
release approvals are intentionally not merge inputs: each change must state
the exact source text it changes and the hash of the file it was reviewed
against.  A dry run produces a unified diff; applying creates rollback copies
and a hash manifest before any source file is replaced.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "original-material-merge-changeset-1.0"
SOURCE_DIR = Path("原始资料")
MERGE_DIR = Path("文档") / "合并升级"
SEMANTIC_ASPECTS = {"conditions", "tags", "relations", "state_transitions"}
ALLOWED_TARGETS = {"资料库.txt", "静态网络.txt", "动态网络.txt", "锚点网络.txt"}
FORBIDDEN_SOURCE_MARKERS = (
    "正文/", "正文\\", "非正式草稿/", "非正式草稿\\",
    "文档/证据/", "文档\\证据\\", "文档/创作深化/", "文档\\创作深化\\",
    "配置/项目创作圣经.json", "配置\\项目创作圣经.json",
    "配置/首章场景创作简报.json", "配置\\首章场景创作简报.json",
)
ID_PATTERNS = (
    re.compile(r'"(?:id|stable_id|connection_id|anchor_id|dynamic_combination_id)"\s*:\s*"([^"]+)"'),
    re.compile(r"^\s*\|\s*([A-Z]+\d+(?:\.\d+)?)\s*\|", re.MULTILINE),
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_changeset(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取变更集: {path}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA:
        raise ValueError(f"变更集 schema_version 必须为 {SCHEMA}")
    if not isinstance(value.get("changes"), list):
        raise ValueError("变更集 changes 必须是数组")
    return value


def _target(root: Path, relative: str) -> Path:
    if relative not in ALLOWED_TARGETS:
        raise ValueError(f"变更目标不在非类型原版资料白名单内: {relative}")
    path = (root / SOURCE_DIR / relative).resolve()
    source_root = (root / SOURCE_DIR).resolve()
    if source_root not in path.parents or path.suffix.lower() != ".txt":
        raise ValueError(f"变更目标必须是原始资料目录内的 .txt 文件: {relative}")
    if not path.is_file():
        raise ValueError(f"变更目标不存在: {relative}")
    return path


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for key, item in value.items() for text in _strings(key) + _strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    return []


def _reject_forbidden_sources(change: dict[str, Any]) -> None:
    for text in _strings(change):
        normalized = text.replace("\\", "/")
        if any(marker.replace("\\", "/") in normalized for marker in FORBIDDEN_SOURCE_MARKERS):
            raise ValueError(f"{change.get('change_id', '未命名变更')} 引用了创作内容或报告目录，不能写入原版资料")


def _normalized(text: str) -> str:
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


def _ids(text: str) -> set[str]:
    return {value for pattern in ID_PATTERNS for value in pattern.findall(text)}


def _validate_contract(change: dict[str, Any]) -> None:
    _reject_forbidden_sources(change)
    contract = change.get("semantic_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{change['change_id']} 缺少 semantic_contract")
    preserved = set(contract.get("preserved", []))
    revised = set(contract.get("revised", []))
    if not preserved.issubset(SEMANTIC_ASPECTS) or not revised.issubset(SEMANTIC_ASPECTS):
        raise ValueError(f"{change['change_id']} 的 semantic_contract 包含未知语义类别")
    if preserved & revised or preserved | revised != SEMANTIC_ASPECTS:
        raise ValueError(f"{change['change_id']} 必须逐项声明条件、标签、关系和状态转换的保留或修订")


def _validate_location(text: str, change: dict[str, Any]) -> None:
    anchor = str(change["anchor"])
    before_context = change.get("before_context")
    after_context = change.get("after_context")
    if not isinstance(before_context, str) or not isinstance(after_context, str):
        raise ValueError(f"{change['change_id']} 必须提供 before_context 和 after_context")
    location = text.index(anchor)
    if text[max(0, location - len(before_context)):location] != before_context:
        raise ValueError(f"{change['change_id']} 的 before_context 与原始资料不一致")
    end = location + len(anchor)
    if text[end:end + len(after_context)] != after_context:
        raise ValueError(f"{change['change_id']} 的 after_context 与原始资料不一致")
    if _sha256(anchor) != change.get("expected_anchor_sha256"):
        raise ValueError(f"{change['change_id']} 的 expected_anchor_sha256 与定位原文不一致")


def _validate_duplicate(before: str, after: str, change: dict[str, Any]) -> None:
    candidate = str(change.get("replacement") if change["kind"] == "revision" else change.get("content"))
    anchor = str(change["anchor"])
    comparable = before.replace(anchor, "", 1) if change["kind"] == "revision" else before
    if _normalized(candidate) and _normalized(candidate) in _normalized(comparable):
        raise ValueError(f"{change['change_id']} 的新增内容与既有资料重复")
    duplicated = sorted(value for value in _ids(after) if value not in _ids(before) and after.count(value) > 1)
    if duplicated:
        raise ValueError(f"{change['change_id']} 引入重复稳定标识: {', '.join(duplicated[:5])}")


def _apply_change(text: str, change: dict[str, Any]) -> str:
    required = {"change_id", "kind", "target", "expected_source_sha256", "expected_anchor_sha256", "anchor", "rationale"}
    missing = sorted(field for field in required if not str(change.get(field) or "").strip())
    if missing:
        raise ValueError(f"变更缺少字段: {', '.join(missing)}")
    kind = change["kind"]
    if kind not in {"revision", "addition"}:
        raise ValueError(f"{change['change_id']} 的 kind 必须为 revision 或 addition")
    anchor = str(change["anchor"])
    if text.count(anchor) != 1:
        raise ValueError(f"{change['change_id']} 的 anchor 必须在目标文件中恰好出现一次")
    _validate_contract(change)
    _validate_location(text, change)
    if kind == "revision":
        replacement = change.get("replacement")
        if not isinstance(replacement, str) or not replacement:
            raise ValueError(f"{change['change_id']} 的 revision 必须提供非空 replacement")
        after = text.replace(anchor, replacement, 1)
        _validate_duplicate(text, after, change)
        return after
    content = change.get("content")
    position = change.get("position")
    if not isinstance(content, str) or not content or position not in {"before", "after"}:
        raise ValueError(f"{change['change_id']} 的 addition 必须提供 content 和 before/after position")
    after = text.replace(anchor, content + anchor if position == "before" else anchor + content, 1)
    _validate_duplicate(text, after, change)
    return after


def build_merge(root: str | Path, changeset_path: str | Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    project_root = Path(root).expanduser().resolve()
    changeset = _read_changeset(Path(changeset_path))
    updated: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for change in changeset["changes"]:
        if not isinstance(change, dict):
            raise ValueError("changes 中的每项必须是对象")
        change_id = str(change.get("change_id") or "")
        if not change_id or change_id in seen_ids:
            raise ValueError("每项变更必须拥有唯一的 change_id")
        seen_ids.add(change_id)
        relative = str(change.get("target") or "")
        path = _target(project_root, relative)
        key = path.relative_to(project_root / SOURCE_DIR).as_posix()
        source_text = path.read_text(encoding="utf-8-sig")
        expected = str(change["expected_source_sha256"])
        if _sha256(source_text) != expected:
            raise ValueError(f"{change_id} 的 expected_source_sha256 与当前原始资料不一致")
        before = updated.get(key)
        if before is None:
            before = source_text
        after = _apply_change(before, change)
        updated[key] = after
        records.append({"change_id": change_id, "kind": change["kind"], "target": f"原始资料/{key}", "before_sha256": _sha256(before), "after_sha256": _sha256(after), "rationale": str(change.get("rationale") or "")})
    for relative, after in updated.items():
        original = (project_root / SOURCE_DIR / relative).read_text(encoding="utf-8-sig")
        duplicate_ids = sorted(value for value in _ids(after) if value not in _ids(original) and after.count(value) > 1)
        if duplicate_ids:
            raise ValueError(f"原始资料/{relative} 的合并结果出现重复稳定标识: {', '.join(duplicate_ids[:5])}")
    return updated, records


def _diff(relative: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"原始资料/{relative}", tofile=f"原始资料/{relative}", lineterm=""))


def create_full_backup(project_root: Path) -> tuple[Path, dict[str, Any]]:
    source_root = project_root / SOURCE_DIR
    if not source_root.is_dir():
        raise ValueError(f"原始资料目录不存在: {source_root}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = project_root / MERGE_DIR / f"backup-{stamp}"
    backup_root = output / "原始资料"
    backup_root.mkdir(parents=True, exist_ok=False)
    files: list[dict[str, Any]] = []
    for source in sorted(source_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root).as_posix()
        saved = backup_root / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, saved)
        files.append({"path": relative, "size": source.stat().st_size, "sha256": _file_sha256(source)})
    manifest = {"schema_version": "original-material-full-backup-1.0", "created_at": _now(), "source_directory": str(source_root), "file_count": len(files), "files": files}
    manifest_path = output / "backup-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for entry in files:
        current = source_root / entry["path"]
        saved = backup_root / entry["path"]
        if current.stat().st_size != entry["size"] or _file_sha256(current) != entry["sha256"] or _file_sha256(saved) != entry["sha256"]:
            raise RuntimeError(f"全量备份校验失败: {entry['path']}")
    return output, manifest


def run(root: str | Path, changeset_path: str | Path, apply: bool = False) -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    updated, records = build_merge(project_root, changeset_path)
    if apply and not records:
        raise ValueError("变更集为空；没有可核验的资料变更，禁止执行空合并")
    diffs: list[str] = []
    for relative, after in updated.items():
        before = (project_root / SOURCE_DIR / relative).read_text(encoding="utf-8-sig")
        diffs.append(_diff(relative, before, after))
    result = {"status": "previewed", "change_count": len(records), "file_count": len(updated), "changes": records, "diff": "\n".join(diff for diff in diffs if diff)}
    if not apply:
        return result
    output, backup_manifest = create_full_backup(project_root)
    backup = output / "rollback"
    backup.mkdir(parents=True, exist_ok=False)
    for relative, after in updated.items():
        source = project_root / SOURCE_DIR / relative
        saved = backup / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, saved)
        temporary = source.with_suffix(source.suffix + ".merge-tmp")
        temporary.write_text(after, encoding="utf-8")
        temporary.replace(source)
    manifest = {"schema_version": "original-material-merge-manifest-1.0", "merged_at": _now(), "changeset": str(Path(changeset_path).resolve()), "full_backup_manifest": str((output / "backup-manifest.json").relative_to(project_root)).replace("\\", "/"), "full_backup_file_count": backup_manifest["file_count"], "rollback_directory": str(backup.relative_to(project_root)).replace("\\", "/"), "changes": records}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "changes.diff").write_text(result["diff"], encoding="utf-8")
    result.update({"status": "applied", "manifest": str((output / "manifest.json").relative_to(project_root)).replace("\\", "/")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="将明确的新版本资料变更合并回原始资料")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--changeset", default="配置/原版新版资料合并变更集.json")
    parser.add_argument("--apply", action="store_true", help="确认写入；省略时仅输出差异预览")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    result = run(root, root / args.changeset, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())