"""Write verified semantic dependency upgrades into 原始资料/资料库.txt."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


LOG_PATH = Path("文档/证据/资料库语义依赖修复日志-二版.jsonl")
LIBRARY_PATH = Path("原始资料/资料库.txt")
AUDIT_ROOT = Path("文档/证据/原版资料库依赖升级回写")
HEADING = re.compile(r"^### (?P<entry_id>\S+)", re.MULTILINE)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def replacement_for(entry_id: str, dependencies: list[dict]) -> str:
    seen: set[tuple[str, str]] = set()
    lines = ["【依赖关系】"]
    for dependency in dependencies:
        target = dependency.get("entry_id")
        relation_type = dependency.get("type")
        if not isinstance(target, str) or not isinstance(relation_type, str):
            raise ValueError(f"{entry_id} 的依赖关系格式非法")
        key = (target, relation_type)
        if key in seen:
            raise ValueError(f"{entry_id} 存在重复依赖关系: {target} / {relation_type}")
        seen.add(key)
        lines.append(f"- {target}（{relation_type}）")
    return "\n".join(lines) + "\n\n"


def writeback(project_root: str | Path, run_id: str) -> dict:
    root = Path(project_root).resolve()
    if Path(run_id).name != run_id:
        raise ValueError("run_id 非法")
    audit_dir = root / AUDIT_ROOT / run_id
    if audit_dir.exists():
        raise FileExistsError(f"审计目录已存在，拒绝覆盖: {audit_dir}")
    log_path = root / LOG_PATH
    library_path = root / LIBRARY_PATH
    logs = read_jsonl(log_path)
    upgrades: dict[str, list[dict]] = {}
    for row in logs:
        entry_id = row.get("entry_id")
        dependencies = row.get("dependencies")
        if not isinstance(entry_id, str) or not isinstance(dependencies, list) or entry_id in upgrades:
            raise ValueError("升级日志包含非法或重复 entry_id")
        upgrades[entry_id] = dependencies

    before_bytes = library_path.read_bytes()
    text = before_bytes.decode("utf-8-sig")
    matches = list(HEADING.finditer(text))
    bounds = {match.group("entry_id"): (match.start(), matches[index + 1].start() if index + 1 < len(matches) else len(text)) for index, match in enumerate(matches)}
    missing = sorted(set(upgrades) - set(bounds))
    if missing:
        raise ValueError(f"原版资料缺少升级目标: {missing[:5]}")

    replacements: list[tuple[int, int, str, str]] = []
    for entry_id, dependencies in upgrades.items():
        if not dependencies:
            continue
        start, end = bounds[entry_id]
        block = text[start:end]
        if "【依赖关系】" in block:
            raise ValueError(f"{entry_id} 已存在依赖关系字段，拒绝重复回写")
        anchor = block.find("【关联板块】")
        if anchor < 0:
            anchor = block.find("【调用标签】")
        if anchor < 0:
            anchor = block.rfind("\n---")
        if anchor < 0:
            raise ValueError(f"{entry_id} 缺少可用字段锚点或条目分隔符，无法保持字段顺序")
        insertion = replacement_for(entry_id, dependencies)
        absolute = start + anchor
        replacements.append((absolute, absolute, insertion, entry_id))

    for start, end, replacement, _ in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    library_path.write_text(text, encoding="utf-8")

    updated = library_path.read_text(encoding="utf-8")
    written_relations = 0
    for _, _, replacement, entry_id in replacements:
        block_start = updated.index(f"### {entry_id}")
        block_end = updated.find("\n### ", block_start + 1)
        block = updated[block_start:block_end if block_end >= 0 else len(updated)]
        if replacement not in block:
            raise AssertionError(f"{entry_id} 的依赖关系未正确写入")
        written_relations += len(upgrades[entry_id])
    audit_dir.mkdir(parents=True)
    audit = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": str(LIBRARY_PATH).replace("\\", "/"),
        "source_sha256_before": sha256_bytes(before_bytes),
        "source_sha256_after": sha256_bytes(library_path.read_bytes()),
        "upgrade_log": str(LOG_PATH).replace("\\", "/"),
        "upgrade_log_entry_count": len(upgrades),
        "upgraded_entry_count": len(replacements),
        "written_relation_count": written_relations,
        "field": "依赖关系",
        "entries": sorted(upgrades),
    }
    (audit_dir / "manifest.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="回写资料库的已验证依赖关系升级")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(writeback(args.project_root, args.run_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())