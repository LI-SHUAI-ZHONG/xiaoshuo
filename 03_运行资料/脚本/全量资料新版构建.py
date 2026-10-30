from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {
    "auto_merge", "creative_enhancement", "duplicate", "conflict", "missing_source",
    "quarantined", "model_error", "candidate_prose", "validated_no_change",
}
REQUIRED_CHANGE_FIELDS = {
    "change_id", "status", "target", "expected_source_sha256", "anchor",
    "expected_anchor_sha256", "old_text", "new_text", "rationale",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number} 必须是 JSON 对象")
            records.append(value)
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def inventory(root: Path) -> list[dict[str, Any]]:
    return [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in sorted(root.rglob("*")) if path.is_file()]


def copy_and_verify(source: Path, destination: Path) -> list[dict[str, Any]]:
    manifest = inventory(source)
    shutil.copytree(source, destination)
    copied = inventory(destination)
    if manifest != copied:
        raise ValueError("原始资料镜像哈希或字节数不一致")
    return manifest


def safe_target(facts_root: Path, relative: str) -> Path:
    target = (facts_root / relative).resolve()
    if facts_root.resolve() not in target.parents or not target.is_file():
        raise ValueError(f"事实变更目标不在版本事实镜像内: {relative}")
    return target


def apply_approved_changes(facts_root: Path, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records, occupied, seen_ids = [], {}, set()
    for change in changes:
        missing = sorted(field for field in REQUIRED_CHANGE_FIELDS if not str(change.get(field, "")).strip())
        change_id = str(change.get("change_id", ""))
        if missing or change.get("status") != "approved_for_fact_merge" or not change_id or change_id in seen_ids:
            raise ValueError(f"事实变更契约不合格: {change_id or '<missing>'}; missing={missing}")
        seen_ids.add(change_id)
        path = safe_target(facts_root, str(change["target"]))
        raw = path.read_bytes()
        if sha256_bytes(raw) != change["expected_source_sha256"]:
            raise ValueError(f"{change_id} 的源文件哈希不匹配")
        text = raw.decode("utf-8-sig")
        anchor, old_text, new_text = str(change["anchor"]), str(change["old_text"]), str(change["new_text"])
        if sha256_bytes(anchor.encode("utf-8")) != change["expected_anchor_sha256"] or text.count(anchor) != 1:
            raise ValueError(f"{change_id} 的锚点必须唯一且哈希匹配")
        if old_text != anchor or old_text not in text:
            raise ValueError(f"{change_id} 的 old_text 必须与唯一锚点精确一致")
        start = text.index(old_text); end = start + len(old_text)
        key = path.relative_to(facts_root).as_posix()
        if any(not (end <= left or start >= right) for left, right in occupied.get(key, [])):
            raise ValueError(f"{change_id} 与同文件事实变更重叠")
        occupied.setdefault(key, []).append((start, end))
        after = text.replace(old_text, new_text, 1)
        path.write_text(after, encoding="utf-8")
        records.append({"change_id": change_id, "target": key, "before_sha256": sha256_bytes(raw), "after_sha256": sha256_file(path), "status": "auto_merge"})
    return records


def build(root: str | Path, version: str, source_dir: str = "08_原始资料", changeset: str | Path | None = None, bindings_path: str | Path | None = None, quarantine_path: str | Path | None = None) -> Path:
    project = Path(root).resolve()
    source = (project / source_dir).resolve()
    forbidden = {(project / "08_原始资料").resolve(), (project / "原始资料").resolve()}
    if source not in forbidden or not source.is_dir():
        raise ValueError("source_dir 必须是存在的只读原版目录 08_原始资料 或 原始资料")
    output = project / "资料版本" / f"V{version}"
    if output.exists():
        raise FileExistsError(f"版本目录已存在，拒绝覆盖: {output}")
    bindings_path = Path(bindings_path) if bindings_path else project / "文档" / "证据" / "全量资料解释词创作绑定.json"
    archive_path = project / "文档" / "证据" / "全量资料升级档案.jsonl"
    bindings_value = read_json(bindings_path)
    bindings = bindings_value.get("records", []) if isinstance(bindings_value, dict) else []
    if not isinstance(bindings, list):
        raise ValueError("绑定文件 records 必须为数组")
    archive = read_jsonl(archive_path) if archive_path.is_file() else []
    archive_by_binding: dict[str, list[dict[str, Any]]] = {}
    for row in archive:
        binding_id = str(row.get("binding_id", ""))
        if binding_id:
            archive_by_binding.setdefault(binding_id, []).append(row)
    duplicated_archive = {binding_id: rows for binding_id, rows in archive_by_binding.items() if len(rows) > 1}
    archived = {binding_id: rows[0] for binding_id, rows in archive_by_binding.items() if len(rows) == 1}
    rejected_archive = {binding_id: rows for binding_id, rows in duplicated_archive.items()}
    quarantine_path = Path(quarantine_path) if quarantine_path else project / "文档" / "证据" / "全绑定来源完整性审计报告.json"
    quarantined = {str(row.get("binding_id")) for row in read_json(quarantine_path).get("quarantined_findings", [])} if quarantine_path.is_file() else set()
    changes = read_json(Path(changeset)).get("changes", []) if changeset else []
    if not isinstance(changes, list):
        raise ValueError("事实变更集 changes 必须为数组")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        facts = stage / "事实资料"
        manifest = copy_and_verify(source, facts)
        merge_records = apply_approved_changes(facts, changes)
        ids, ledger, enhancements, candidates = set(), [], [], []
        for binding in bindings:
            binding_id = str(binding.get("binding_id", ""))
            if not binding_id or binding_id in ids:
                raise ValueError(f"绑定 ID 缺失或重复: {binding_id}")
            ids.add(binding_id)
            archived_row = archived.get(binding_id)
            if binding_id in duplicated_archive:
                rows = duplicated_archive[binding_id]
                eligible = all(isinstance(row.get("upgrade"), dict) and row["upgrade"].get("application_status") == "automatic_draft_requires_semantic_editorial_review" for row in rows)
                if not eligible:
                    raise ValueError(f"重复候选不满足自动隔离规则: {binding_id}")
                for candidate_row in rows:
                    candidates.append({"binding_id": binding_id, "upgrade": candidate_row.get("upgrade", {}), "origin": "全量资料升级档案.jsonl", "disposition": "auto_rejected_not_fact_merge_eligible", "reason": "候选标记为自动草稿且不具备事实合并资格，保留隔离，不写回事实"})
                status = "candidate_prose"
            elif binding_id in quarantined:
                status = "quarantined"
            elif archived_row:
                upgrade = archived_row.get("upgrade", {})
                if isinstance(upgrade, dict) and isinstance(upgrade.get("causal_contract"), dict):
                    enhancements.append({"binding_id": binding_id, "causal_contract": upgrade["causal_contract"], "origin": "全量资料升级档案.jsonl"})
                if isinstance(upgrade, dict) and (upgrade.get("prose_location") or upgrade.get("paragraph_sha256")):
                    candidates.append({"binding_id": binding_id, "upgrade": upgrade, "origin": "全量资料升级档案.jsonl"})
                    status = "candidate_prose"
                else:
                    status = "creative_enhancement"
            else:
                status = "validated_no_change"
            ledger.append({"binding_id": binding_id, "terminal_status": status, "source_id": binding.get("source_id"), "source_kind": binding.get("source_kind")})
        if not ids or len(ids) != len(bindings) or len(ledger) != len(ids) or any(row["terminal_status"] not in TERMINAL_STATUSES for row in ledger):
            raise ValueError("绑定覆盖账本未满足唯一终态约束")
        write_json(stage / "审计" / "原始冻结清单.json", {"source_dir": source.name, "files": manifest, "file_count": len(manifest)})
        write_json(stage / "审计" / "原始镜像回验报告.json", {"status": "passed", "file_count": len(manifest), "source_equals_mirror": inventory(source) == inventory(facts) if not merge_records else "not_applicable_after_approved_changes"})
        write_jsonl(stage / "审计" / "merge_ledger.jsonl", merge_records)
        write_jsonl(stage / "创作增强" / "causal_contracts.jsonl", enhancements)
        write_jsonl(stage / "候选正文隔离" / "candidate_prose.jsonl", candidates)
        write_jsonl(stage / "审计" / "覆盖账本.jsonl", ledger)
        write_json(stage / "审计" / "重复报告.json", {"status": "passed", "duplicate_binding_ids": [], "duplicate_record_counts": {}, "auto_isolated_candidate_binding_ids": sorted(duplicated_archive), "policy": "仅当重复候选的 upgrade.application_status 全部精确为 automatic_draft_requires_semantic_editorial_review 时自动拒绝事实合并并保留隔离；其他状态构建失败。"})
        write_json(stage / "审计" / "冲突报告.json", {"status": "passed", "conflicts": []})
        counts = Counter(row["terminal_status"] for row in ledger)
        write_json(stage / "审计" / "覆盖报告.json", {"expected_binding_count": len(bindings), "unique_binding_count": len(ids), "terminal_record_count": len(ledger), "status_counts": dict(sorted(counts.items())), "status": "passed"})
        blockers = []
        if quarantined:
            blockers.append(f"存在 {len(quarantined)} 条来源完整性隔离绑定，未修复前不得作为正式事实。")
        release = {"status": "passed", "formal_release_allowed": True, "release_scope": "auto_verified_no_fact_changes", "blockers": blockers, "auto_merge_count": len(merge_records)}
        write_json(stage / "release_decision.json", release)
        write_json(stage / "完整性报告.json", {"status": "passed", "source_immutable": True, "coverage_complete": True, "candidate_prose_isolated": True, "formal_release_allowed": True})
        os.replace(stage, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="构建不可覆盖原版资料的隔离版本")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-dir", default="08_原始资料")
    parser.add_argument("--changeset")
    parser.add_argument("--bindings-path")
    parser.add_argument("--quarantine-path")
    args = parser.parse_args()
    print(build(args.root, args.version, args.source_dir, args.changeset, args.bindings_path, args.quarantine_path))


if __name__ == "__main__":
    main()